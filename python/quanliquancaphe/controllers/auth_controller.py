"""
controllers/auth_controller.py — Multi-shift per day
See docstring in file for full spec.
"""
from __future__ import annotations
from datetime import datetime, date, timedelta
from database.db_config import get_session, ghi_nhat_ky_dang_nhap
from database.models import NhanVien, PhienLamViec, CaLamViec, PhanCongCaLam, ChamCong

PHUT_VAO_SOM = 15
PHUT_VE_SOM  = 15
PHUT_TANG_CA = 30


def _tinh_checkin(now: datetime, cc: ChamCong) -> dict:
    if cc.gio_bd_ca is None:
        return {"trang_thai": "Dang_lam", "phut_tre": 0}
    bat_dau_dt = datetime.combine(cc.ngay, cc.gio_bd_ca)
    if now <= bat_dau_dt:
        return {"trang_thai": "Dang_lam", "phut_tre": 0}
    phut_tre = max(0, int((now - bat_dau_dt).total_seconds() // 60))
    return {"trang_thai": "Di_tre", "phut_tre": phut_tre}


def _tinh_checkout(now: datetime, cc: ChamCong) -> dict:
    """
    Tính trạng thái khi check-out.
    - Giữ nguyên phut_tre đã ghi lúc check-in (không trả về, không ghi đè).
    - Ve_som : check-out sớm hơn (gio_kt_ca - PHUT_VE_SOM) phút
    - Tang_ca: check-out muộn hơn (gio_kt_ca + PHUT_TANG_CA) phút
    - Hoan_thanh / Di_tre: trong khoảng cho phép (giữ trạng thái Di_tre nếu đã trễ)
    """
    if cc.gio_kt_ca is None:
        # Không có ca → giữ trạng thái check-in (Di_tre / Dang_lam)
        tt = "Di_tre" if cc.trang_thai == "Di_tre" else "Hoan_thanh"
        return {"trang_thai": tt, "phut_ve_som": 0, "phut_tang_ca": 0}
    ket_thuc_dt = datetime.combine(cc.ngay, cc.gio_kt_ca)
    if cc.gio_bd_ca and cc.gio_kt_ca < cc.gio_bd_ca:
        ket_thuc_dt += timedelta(days=1)
    duoc_ve_som = ket_thuc_dt - timedelta(minutes=PHUT_VE_SOM)
    moc_tang_ca = ket_thuc_dt + timedelta(minutes=PHUT_TANG_CA)
    if now < duoc_ve_som:
        phut = max(0, int((duoc_ve_som - now).total_seconds() // 60))
        # Về sớm + đã trễ → ghi cả 2 (phut_tre giữ nguyên từ check-in)
        tt = "Ve_som"
        return {"trang_thai": tt, "phut_ve_som": phut, "phut_tang_ca": 0}
    elif now > moc_tang_ca:
        phut = max(0, int((now - ket_thuc_dt).total_seconds() // 60))
        # Tăng ca → giữ trạng thái Di_tre nếu đã trễ, ngược lại Tang_ca
        tt = "Di_tre" if cc.trang_thai == "Di_tre" else "Tang_ca"
        return {"trang_thai": tt, "phut_ve_som": 0, "phut_tang_ca": phut}
    else:
        # Đúng giờ → giữ Di_tre nếu đã trễ
        tt = "Di_tre" if cc.trang_thai == "Di_tre" else "Hoan_thanh"
        return {"trang_thai": tt, "phut_ve_som": 0, "phut_tang_ca": 0}


def _ca_khop_gio(ca: CaLamViec, now: datetime) -> bool:
    """
    Ca hợp lệ để check-in khi:
      • now >= (gio_bat_dau − 15 phút)   [cho phép vào sớm tối đa 15 phút]
      • now <= (gio_bat_dau + 60 phút)   [quá 60 phút sau giờ bắt đầu → không nhận nữa]
    Giới hạn 60 phút sau giúp tránh nhân viên ca chiều vô tình check-in nhầm ca sáng.
    """
    if not ca.gio_bat_dau or not ca.gio_ket_thuc:
        return False

    today     = now.date()
    bat_dau   = datetime.combine(today, ca.gio_bat_dau)

    # Cửa sổ hợp lệ: [bat_dau - 15 phút, bat_dau + 60 phút]
    mo_cua    = bat_dau - timedelta(minutes=PHUT_VAO_SOM)   # sớm nhất được check-in
    dong_cua  = bat_dau + timedelta(minutes=60)             # muộn nhất được check-in

    # Xử lý ca qua đêm: nếu gio_ket_thuc < gio_bat_dau thì ca này qua sang ngày hôm sau
    ket_thuc  = datetime.combine(today, ca.gio_ket_thuc)
    if ca.gio_ket_thuc < ca.gio_bat_dau:
        ket_thuc += timedelta(days=1)
        # Ca qua đêm: cửa sổ check-in vẫn tính từ bat_dau ngày hôm nay
        return mo_cua <= now <= dong_cua

    return mo_cua <= now <= dong_cua


def _lay_ca_phan_cong(session, ma_nv: int, today: date) -> list[CaLamViec]:
    pcs = session.query(PhanCongCaLam).filter_by(ma_nv=ma_nv, ngay_lam=today).all()
    cas = []
    for pc in pcs:
        ca = session.get(CaLamViec, pc.ma_ca)
        if ca:
            cas.append(ca)
    cas.sort(key=lambda c: c.gio_bat_dau or __import__('datetime').time.min)
    return cas


def _ensure_cham_cong(session, ma_nv: int, ca: CaLamViec, ngay: date) -> ChamCong:
    """Tạo hoặc lấy bản ghi ChamCong cho 1 ca cụ thể. Không tạo trước ca chưa đến."""
    cc = (session.query(ChamCong)
          .filter_by(nhan_vien_id=ma_nv, ngay=ngay, ma_ca=ca.id).first())
    if cc is None:
        cc = ChamCong(
            nhan_vien_id=ma_nv, ma_ca=ca.id, ngay=ngay,
            gio_bd_ca=ca.gio_bat_dau, gio_kt_ca=ca.gio_ket_thuc,
            trang_thai="Chua_checkin",
        )
        session.add(cc)
    return cc


# ── ĐĂNG NHẬP ────────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str):
    if not username or not password:
        ghi_nhat_ky_dang_nhap(ten_dang_nhap=username or "(trống)",
            hanh_dong="Đăng nhập", ket_qua="Thất bại",
            ghi_chu="Tên đăng nhập hoặc mật khẩu để trống")
        return None

    session = get_session()
    try:
        user = session.query(NhanVien).filter_by(ten_dang_nhap=username).first()
        if user is None:
            ghi_nhat_ky_dang_nhap(ten_dang_nhap=username,
                hanh_dong="Đăng nhập", ket_qua="Sai mật khẩu",
                ghi_chu="Tài khoản không tồn tại")
            return None
        if user.trang_thai == "Tạm khóa":
            ghi_nhat_ky_dang_nhap(ten_dang_nhap=username,
                hanh_dong="Đăng nhập", ket_qua="Tài khoản khóa",
                ma_nv=user.id, ghi_chu=f"'{username}' bị tạm khóa")
            return None
        if user.mat_khau != password:
            ghi_nhat_ky_dang_nhap(ten_dang_nhap=username,
                hanh_dong="Đăng nhập", ket_qua="Sai mật khẩu",
                ma_nv=user.id, ghi_chu="Mật khẩu không đúng")
            return None

        now   = datetime.now()
        today = date.today()
        ma_nv = user.id

        # Lấy ca phân công hôm nay
        cas_hom_nay = _lay_ca_phan_cong(session, ma_nv, today)
        ca_checkin  = next((ca for ca in cas_hom_nay if _ca_khop_gio(ca, now)), None)

        # Tạo PhienLamViec
        phien = PhienLamViec(ma_nv=ma_nv,
                             ma_ca=ca_checkin.id if ca_checkin else None,
                             thoi_gian_dang_nhap=now, dang_hoat_dong=True)
        session.add(phien)
        session.flush()
        ma_phien = phien.id

        ten_ca_log = "Không có ca"
        if cas_hom_nay:
            # Chỉ check-in ca đang trong cửa sổ giờ
            ca_checkin_obj = next((ca for ca in cas_hom_nay if _ca_khop_gio(ca, now)), None)
            if ca_checkin_obj:
                cc = _ensure_cham_cong(session, ma_nv, ca_checkin_obj, today)
                session.flush()
                if cc.thoi_gian_vao is None:
                    info = _tinh_checkin(now, cc)
                    cc.thoi_gian_vao = now
                    cc.trang_thai    = info["trang_thai"]
                    cc.phut_tre      = info["phut_tre"]
                    cc.ma_phien      = ma_phien
                    ten_ca_log = f"{ca_checkin_obj.ten_ca} → {info['trang_thai']}"
                else:
                    ten_ca_log = f"{ca_checkin_obj.ten_ca} (đã check-in)"
            else:
                # Có phân công nhưng chưa đến giờ bất kỳ ca nào
                ten_ca_log = "Có ca nhưng ngoài giờ"
        else:
            # Không có phân công → Khong_ca
            cc_tu_do = (session.query(ChamCong)
                        .filter_by(nhan_vien_id=ma_nv, ngay=today,
                                   ma_ca=None, trang_thai="Khong_ca")
                        .filter(ChamCong.thoi_gian_ra.is_(None)).first())
            if cc_tu_do is None:
                session.add(ChamCong(
                    nhan_vien_id=ma_nv, ma_ca=None, ngay=today,
                    thoi_gian_vao=now, trang_thai="Khong_ca", ma_phien=ma_phien,
                ))

        session.commit()
        ghi_nhat_ky_dang_nhap(ten_dang_nhap=username,
            hanh_dong="Đăng nhập", ket_qua="Thành công", ma_nv=ma_nv,
            ghi_chu=f"Chức vụ: {user.chuc_vu} | Phiên #{ma_phien} | Ca: {ten_ca_log}")

        session.expunge(user)
        return {"user": user, "ma_phien": ma_phien}

    except Exception as e:
        ghi_nhat_ky_dang_nhap(ten_dang_nhap=username,
            hanh_dong="Đăng nhập", ket_qua="Thất bại", ghi_chu=f"Lỗi DB: {e}")
        try: session.rollback()
        except Exception: pass
        return None
    finally:
        session.close()


# ── CHECK-OUT TỪNG CA ─────────────────────────────────────────────────────────
def checkout_ca(ma_cham_cong: int) -> tuple[bool, str]:
    """Check-out 1 ca theo id ChamCong (số nguyên).

    Trả (True, msg) khi thành công, (False, lỗi) khi thất bại.

    Lưu ý: hàm này chỉ nhận ma_cham_cong là int — KHÔNG nhận NhanVien object
    hay ma_phien. UI cần gọi lay_ca_dang_mo() trước để lấy danh sách id.
    """
    # Guard kiểu dữ liệu — bắt lỗi sớm thay vì để crash tận DB
    if not isinstance(ma_cham_cong, int):
        return False, (
            f"ma_cham_cong phải là int, nhận được {type(ma_cham_cong).__name__}. "
            "Hãy truyền cc['id'] từ lay_ca_dang_mo()."
        )

    session = get_session()
    try:
        now = datetime.now()
        cc  = session.get(ChamCong, ma_cham_cong)
        if not cc:
            return False, f"Không tìm thấy bản ghi chấm công #{ma_cham_cong}."
        if cc.thoi_gian_ra is not None:
            return False, "Ca này đã được check-out rồi."
        if cc.thoi_gian_vao is None:
            # Ca tồn tại nhưng chưa check-in (ví dụ Chua_checkin) —
            # ghi thời gian vào = now để tránh kẹt, đánh dấu Hoan_thanh
            cc.thoi_gian_vao = now
            cc.trang_thai    = "Hoan_thanh"
            cc.thoi_gian_ra  = now
            cc.phut_ve_som   = 0
            cc.phut_tang_ca  = 0
            if cc.ma_phien:
                phien = session.get(PhienLamViec, cc.ma_phien)
                if phien and phien.dang_hoat_dong:
                    phien.thoi_gian_dang_xuat = now
                    phien.dang_hoat_dong      = False
            session.commit()
            return True, f"Check-out {now.strftime('%H:%M')} | (Ca chưa check-in — tự động đóng)"

        info = _tinh_checkout(now, cc)
        cc.thoi_gian_ra  = now
        cc.trang_thai    = info["trang_thai"]
        cc.phut_ve_som   = info["phut_ve_som"]
        cc.phut_tang_ca  = info["phut_tang_ca"]
        # Giữ nguyên phut_tre đã ghi lúc check-in — không ghi đè

        if cc.ma_phien:
            phien = session.get(PhienLamViec, cc.ma_phien)
            if phien and phien.dang_hoat_dong:
                phien.thoi_gian_dang_xuat = now
                phien.dang_hoat_dong      = False

        session.commit()
        tong_phut = int((now - cc.thoi_gian_vao).total_seconds() // 60)
        gio, phut = divmod(tong_phut, 60)
        return True, (
            f"Check-out {now.strftime('%H:%M')} | "
            f"Tổng: {gio}h{phut:02d}m | {info['trang_thai']}"
        )
    except Exception as e:
        try: session.rollback()
        except Exception: pass
        return False, f"Lỗi DB: {e}"
    finally:
        session.close()


def checkout_tat_ca_ca(ma_nv: int) -> tuple[bool, str]:
    """Checkout toàn bộ ca đang mở (Dang_lam / Di_tre) của nhân viên hôm nay.

    Đây là hàm tiện ích cho UI gọi khi đăng xuất — thay thế pattern
    gọi checkout_ca(NhanVien, ma_phien=...) sai kiểu cũ.
    Trả (True, tóm_tắt) nếu tất cả thành công, (False, chi_tiết_lỗi) nếu có lỗi.
    """
    cas = lay_ca_dang_mo(ma_nv)
    if not cas:
        return True, "Không có ca đang mở"
    ok_msgs, err_msgs = [], []
    for ca in cas:
        ok, msg = checkout_ca(ca["id"])
        (ok_msgs if ok else err_msgs).append(f"{ca['ten_ca']}: {msg}")
    if err_msgs:
        return False, "Lỗi: " + " | ".join(err_msgs)
    return True, " | ".join(ok_msgs)


def lay_ca_dang_mo(ma_nv: int) -> list[dict]:
    """Ca của NV hôm nay đang Dang_lam / Di_tre (chưa checkout). Không bao gồm Khong_ca."""
    session = get_session()
    try:
        today = date.today()
        ccs   = (session.query(ChamCong)
                 .filter(ChamCong.nhan_vien_id == ma_nv,
                         ChamCong.ngay == today,
                         ChamCong.trang_thai.in_(["Dang_lam", "Di_tre"]),
                         ChamCong.thoi_gian_ra.is_(None)).all())
        result = []
        for cc in ccs:
            ten_ca = "Không rõ"
            if cc.ma_ca:
                ca = session.get(CaLamViec, cc.ma_ca)
                ten_ca = ca.ten_ca if ca else "?"
            result.append({
                "id": cc.id, "ten_ca": ten_ca,
                "gio_bd":  cc.gio_bd_ca.strftime("%H:%M") if cc.gio_bd_ca else "--",
                "gio_kt":  cc.gio_kt_ca.strftime("%H:%M") if cc.gio_kt_ca else "--",
                "vao_luc": cc.thoi_gian_vao.strftime("%H:%M") if cc.thoi_gian_vao else "--",
            })
        return result
    finally:
        session.close()


def lay_tat_ca_hom_nay(ma_nv: int) -> list[dict]:
    """Toàn bộ ca của NV hôm nay — dùng để hiển thị UI."""
    session = get_session()
    try:
        today = date.today()
        ccs   = (session.query(ChamCong)
                 .filter_by(nhan_vien_id=ma_nv, ngay=today)
                 .order_by(ChamCong.gio_bd_ca).all())
        result = []
        for cc in ccs:
            ten_ca = "Không có ca"
            if cc.ma_ca:
                ca = session.get(CaLamViec, cc.ma_ca)
                ten_ca = ca.ten_ca if ca else "?"
            result.append({
                "id": cc.id, "ten_ca": ten_ca,
                "gio_bd":       cc.gio_bd_ca.strftime("%H:%M") if cc.gio_bd_ca else "--",
                "gio_kt":       cc.gio_kt_ca.strftime("%H:%M") if cc.gio_kt_ca else "--",
                "vao_luc":      cc.thoi_gian_vao.strftime("%H:%M") if cc.thoi_gian_vao else "--",
                "ra_luc":       cc.thoi_gian_ra.strftime("%H:%M")  if cc.thoi_gian_ra  else "--",
                "trang_thai":   cc.trang_thai,
                "phut_tre":     cc.phut_tre,
                "phut_ve_som":  cc.phut_ve_som,
                "phut_tang_ca": cc.phut_tang_ca,
            })
        return result
    finally:
        session.close()


# ── ĐĂNG XUẤT ────────────────────────────────────────────────────────────────
def logout_user(user: NhanVien, ma_phien: int = None):
    """
    Đóng phiên làm việc khi đăng xuất.

    Chính sách:
    - KHÔNG tự động checkout ca có lịch (Dang_lam / Di_tre).
      Nhân viên phải tự check-out thủ công qua nút "Check-out Ca".
      (UI sẽ nhắc nhở nhưng KHÔNG bắt buộc trước khi đăng xuất.)
    - Chỉ ghi thoi_gian_ra cho bản ghi Khong_ca (nhân viên tự do, không ca).
    - Đóng PhienLamViec.
    """
    if user:
        ghi_nhat_ky_dang_nhap(ten_dang_nhap=user.ten_dang_nhap,
            hanh_dong="Đăng xuất", ket_qua="Thành công", ma_nv=user.id)
        # Chỉ ghi giờ ra cho bản ghi Khong_ca — không tự checkout ca có lịch
        _ghi_ra_khong_ca(user.id)

    if ma_phien:
        session = get_session()
        try:
            phien = session.get(PhienLamViec, ma_phien)
            if phien and phien.dang_hoat_dong:
                phien.thoi_gian_dang_xuat = datetime.now()
                phien.dang_hoat_dong      = False
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()


def _ghi_ra_khong_ca(ma_nv: int):
    """Ghi thoi_gian_ra cho bản ghi Khong_ca chưa checkout — không đổi trang_thai."""
    session = get_session()
    try:
        now   = datetime.now()
        today = date.today()
        ccs   = (session.query(ChamCong)
                 .filter(ChamCong.nhan_vien_id == ma_nv,
                         ChamCong.ngay == today,
                         ChamCong.trang_thai == "Khong_ca",
                         ChamCong.thoi_gian_ra.is_(None)).all())
        for cc in ccs:
            cc.thoi_gian_ra = now
        if ccs:
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()



# ── KIỂM TRA VẮNG MẶT (quá 50% ca chưa check-in) ────────────────────────────
def kiem_tra_vang_mat():
    """
    Quét tất cả ChamCong hôm nay còn 'Chua_checkin'.
    Nếu now > gio_bd_ca + 50% tổng thời gian ca → đánh dấu 'Vang_mat'.
    Nên gọi định kỳ (mỗi 5-10 phút) hoặc khi mở app.
    """
    session = get_session()
    try:
        now   = datetime.now()
        today = date.today()
        ccs = (session.query(ChamCong)
               .filter(ChamCong.ngay == today,
                       ChamCong.trang_thai == "Chua_checkin",
                       ChamCong.thoi_gian_vao.is_(None)).all())
        changed = 0
        for cc in ccs:
            if not cc.gio_bd_ca or not cc.gio_kt_ca:
                continue
            bat_dau_dt  = datetime.combine(today, cc.gio_bd_ca)
            ket_thuc_dt = datetime.combine(today, cc.gio_kt_ca)
            if cc.gio_kt_ca < cc.gio_bd_ca:          # ca qua đêm
                ket_thuc_dt += timedelta(days=1)
            tong_phut = (ket_thuc_dt - bat_dau_dt).total_seconds() / 60
            if tong_phut <= 0:
                continue
            nguong_vang = bat_dau_dt + timedelta(minutes=tong_phut * 0.5)
            if now >= nguong_vang:
                cc.trang_thai = "Vang_mat"
                cc.ghi_chu    = (cc.ghi_chu or "") + (
                    f" [Tự động: vắng sau {int(tong_phut*0.5)}p không check-in]"
                )
                changed += 1
        if changed:
            session.commit()
        return changed
    except Exception:
        session.rollback()
        return 0
    finally:
        session.close()


# ── TỰ ĐỘNG CHECKOUT CUỐI NGÀY ───────────────────────────────────────────────
def tu_dong_checkout_cuoi_ngay():
    """Đóng ca bị quên chưa checkout của ngày hôm qua. Gọi khi khởi động."""
    from datetime import time as dtime
    session = get_session()
    try:
        yesterday = date.today() - timedelta(days=1)
        ccs = (session.query(ChamCong)
               .filter(ChamCong.ngay == yesterday,
                       ChamCong.trang_thai.in_(["Dang_lam", "Di_tre"]),
                       ChamCong.thoi_gian_ra.is_(None)).all())
        for cc in ccs:
            fake_ra = (datetime.combine(yesterday, cc.gio_kt_ca)
                       if cc.gio_kt_ca
                       else datetime.combine(yesterday, dtime(23, 59)))
            info = _tinh_checkout(fake_ra, cc)
            cc.thoi_gian_ra  = fake_ra
            cc.trang_thai    = info["trang_thai"]
            cc.phut_ve_som   = info["phut_ve_som"]
            cc.phut_tang_ca  = info["phut_tang_ca"]
            cc.ghi_chu       = (cc.ghi_chu or "") + " [Auto checkout cuối ngày]"
            if cc.ma_phien:
                phien = session.get(PhienLamViec, cc.ma_phien)
                if phien and phien.dang_hoat_dong:
                    phien.thoi_gian_dang_xuat = fake_ra
                    phien.dang_hoat_dong      = False
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()