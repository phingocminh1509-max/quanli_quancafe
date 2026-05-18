"""
controllers/loyalty_controller.py
══════════════════════════════════════════════════════════════════
Xử lý tích điểm, đổi điểm lấy voucher, phát voucher cho KH.

Quy tắc tích điểm:
  • 10.000đ = 1 điểm  (DIEM_PER_DONG = 1/10000)
  • Làm tròn xuống: 95.000đ → 9 điểm
  • Chỉ tích khi HoaDon.trang_thai == 'Đã thanh toán'

Hạng thành viên (tổng chi tiêu tích lũy):
  Đồng   : < 1.000.000đ
  Bạc    : 1.000.000 – 4.999.999đ
  Vàng   : 5.000.000 – 19.999.999đ
  Kim cương: ≥ 20.000.000đ
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import random, string
from datetime import date, datetime, timedelta
from typing import Optional

from database.db_config import get_session
from database.models import (
    KhachHang, HoaDon, LichSuDiemKH, Voucher, KhuyenMai,
)

# ── Hằng số ──────────────────────────────────────────────────────
DIEM_PER_10K   = 1          # 10.000đ = 1 điểm
DON_VI_DIEM    = 10_000     # 1 điểm tương ứng bao nhiêu đồng

# Bảng đổi điểm → voucher (tuỳ chỉnh)
BANG_DOI_DIEM = [
    {"diem": 50,  "giam": 5_000,   "ten": "Voucher 5k",    "loai": "TienMat"},
    {"diem": 100, "giam": 10_000,  "ten": "Voucher 10k",   "loai": "TienMat"},
    {"diem": 200, "giam": 25_000,  "ten": "Voucher 25k",   "loai": "TienMat"},
    {"diem": 500, "giam": 70_000,  "ten": "Voucher 70k",   "loai": "TienMat"},
    {"diem": 100, "giam": 10,      "ten": "Giảm 10%",      "loai": "PhanTram", "toi_da": 20_000},
    {"diem": 200, "giam": 15,      "ten": "Giảm 15%",      "loai": "PhanTram", "toi_da": 40_000},
]

HANG_MV = [
    ("Kim cương", 20_000_000),
    ("Vàng",       5_000_000),
    ("Bạc",        1_000_000),
    ("Đồng",               0),
]


# ════════════════════════════════════════════════════════════════
# HELPER
# ════════════════════════════════════════════════════════════════
def _tinh_hang(tong_chi_tieu: float) -> str:
    for ten, nguong in HANG_MV:
        if tong_chi_tieu >= nguong:
            return ten
    return "Đồng"


def _gen_ma_voucher(prefix="VCR") -> str:
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{rand}"


def _tinh_diem(thanh_tien: float) -> int:
    """Tính số điểm từ số tiền thanh toán. 10.000đ = 1 điểm, làm tròn xuống."""
    return int(thanh_tien // DON_VI_DIEM)


# ════════════════════════════════════════════════════════════════
# 1. TÍCH ĐIỂM SAU THANH TOÁN (gọi từ pos_controller)
# ════════════════════════════════════════════════════════════════
def tich_diem_hoa_don(ma_hd: int) -> tuple[bool, str]:
    """
    Tích điểm cho KH sau khi hóa đơn hoàn tất.
    Trả (True, mô tả) hoặc (False, lý do bỏ qua/lỗi).
    Hàm này idempotent: nếu đã tích rồi thì bỏ qua.
    """
    session = get_session()
    try:
        hd = session.get(HoaDon, ma_hd)
        if not hd:
            return False, "Không tìm thấy hóa đơn"
        if hd.trang_thai != "Đã thanh toán":
            return False, "Hóa đơn chưa hoàn tất"
        if not hd.ma_kh:
            return False, "Hóa đơn không có khách hàng"

        # Kiểm tra đã tích chưa (idempotent)
        da_tich = (session.query(LichSuDiemKH)
                   .filter_by(ma_hd=ma_hd, loai="Tích điểm").first())
        if da_tich:
            return False, "Đã tích điểm cho hóa đơn này rồi"

        kh = session.get(KhachHang, hd.ma_kh)
        if not kh:
            return False, "Không tìm thấy khách hàng"

        diem_cong = _tinh_diem(hd.thanh_tien or 0)
        if diem_cong <= 0:
            return False, f"Đơn {int(hd.thanh_tien):,}đ chưa đủ để tích điểm"

        kh.diem_tich_luy = (kh.diem_tich_luy or 0) + diem_cong
        kh.tong_chi_tieu = (kh.tong_chi_tieu or 0) + float(hd.thanh_tien or 0)
        kh.hang_thanh_vien = _tinh_hang(kh.tong_chi_tieu)

        session.add(LichSuDiemKH(
            ma_kh     = kh.id,
            ma_hd     = ma_hd,
            loai      = "Tích điểm",
            so_diem   = diem_cong,
            mo_ta     = f"Tích từ HD#{ma_hd:04d} | {int(hd.thanh_tien):,}đ → +{diem_cong} điểm",
        ))
        session.commit()
        return True, f"+{diem_cong} điểm | Tổng: {kh.diem_tich_luy} điểm | Hạng: {kh.hang_thanh_vien}"

    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ════════════════════════════════════════════════════════════════
# 2. ĐỔI ĐIỂM LẤY VOUCHER
# ════════════════════════════════════════════════════════════════
def doi_diem_lay_voucher(
    ma_kh: int,
    idx_bang_doi: int,          # index trong BANG_DOI_DIEM
    ma_nv_thuc_hien: int,
    han_dung_ngay: int = 30,    # voucher có hiệu lực bao nhiêu ngày
) -> tuple[bool, str, Optional[str]]:
    """
    Đổi điểm lấy voucher riêng của khách.
    Trả (ok, message, ma_code_voucher).
    """
    if idx_bang_doi < 0 or idx_bang_doi >= len(BANG_DOI_DIEM):
        return False, "Gói đổi điểm không hợp lệ", None

    goi = BANG_DOI_DIEM[idx_bang_doi]
    session = get_session()
    try:
        kh = session.get(KhachHang, ma_kh)
        if not kh:
            return False, "Không tìm thấy khách hàng", None

        if (kh.diem_tich_luy or 0) < goi["diem"]:
            return False, (
                f"Không đủ điểm. Cần {goi['diem']} điểm, "
                f"hiện có {kh.diem_tich_luy} điểm."
            ), None

        ma_code = _gen_ma_voucher("VD")
        ngay_het_han = date.today() + timedelta(days=han_dung_ngay)

        vcr = Voucher(
            ma_kh        = ma_kh,
            ma_code      = ma_code,
            ten_voucher  = goi["ten"],
            loai_giam    = goi["loai"],
            gia_tri_giam = goi["giam"],
            toi_da_giam  = goi.get("toi_da"),
            dieu_kien_toi_thieu = 0,
            ngay_het_han = ngay_het_han,
            trang_thai   = "Chưa dùng",
        )
        session.add(vcr)

        kh.diem_tich_luy -= goi["diem"]

        session.add(LichSuDiemKH(
            ma_kh   = ma_kh,
            loai    = "Đổi điểm",
            so_diem = -goi["diem"],
            mo_ta   = f"Đổi {goi['diem']} điểm → {goi['ten']} ({ma_code})",
        ))

        session.commit()
        return True, (
            f"✅ Đổi thành công!\n"
            f"Voucher: {ma_code}\n"
            f"Giá trị: {goi['ten']}\n"
            f"Hết hạn: {ngay_het_han.strftime('%d/%m/%Y')}\n"
            f"Điểm còn lại: {kh.diem_tich_luy}"
        ), ma_code

    except Exception as e:
        session.rollback()
        return False, str(e), None
    finally:
        session.close()


# ════════════════════════════════════════════════════════════════
# 3. PHÁT VOUCHER CHUNG (Admin/Quản lý tạo từ KhuyenMai)
# ════════════════════════════════════════════════════════════════
def phat_voucher_chung(
    ma_kh: int,
    ten_voucher: str,
    loai_giam: str,
    gia_tri_giam: float,
    toi_da_giam: float = None,
    dieu_kien_toi_thieu: float = 0,
    han_dung_ngay: int = 30,
    ma_nv: int = None,
) -> tuple[bool, str, Optional[str]]:
    """Phát voucher do quán tạo cho 1 khách hàng cụ thể."""
    session = get_session()
    try:
        kh = session.get(KhachHang, ma_kh)
        if not kh:
            return False, "Không tìm thấy khách hàng", None

        ma_code = _gen_ma_voucher("VQ")
        ngay_het_han = date.today() + timedelta(days=han_dung_ngay)

        vcr = Voucher(
            ma_kh        = ma_kh,
            ma_code      = ma_code,
            ten_voucher  = ten_voucher,
            loai_giam    = loai_giam,
            gia_tri_giam = gia_tri_giam,
            toi_da_giam  = toi_da_giam,
            dieu_kien_toi_thieu = dieu_kien_toi_thieu,
            ngay_het_han = ngay_het_han,
            trang_thai   = "Chưa dùng",
        )
        session.add(vcr)
        session.commit()
        return True, f"✅ Phát voucher {ma_code} cho {kh.ten_kh}", ma_code

    except Exception as e:
        session.rollback()
        return False, str(e), None
    finally:
        session.close()


# ════════════════════════════════════════════════════════════════
# 4. ÁP DỤNG VOUCHER KHI THANH TOÁN
# ════════════════════════════════════════════════════════════════
def ap_dung_voucher(
    ma_code: str,
    tong_tien: float,
    ma_kh: int = None,
) -> tuple[bool, float, str, Optional[int]]:
    """
    Tìm và tính giảm giá từ voucher.
    Trả (ok, so_tien_giam, message, voucher_id).
    Chưa đánh dấu 'Đã dùng' — chỉ tính toán.
    Gọi confirm_su_dung_voucher() sau khi thanh toán thành công.
    """
    session = get_session()
    try:
        vcr = session.query(Voucher).filter_by(ma_code=ma_code).first()
        if not vcr:
            return False, 0, f"Mã voucher '{ma_code}' không tồn tại", None
        if vcr.trang_thai != "Chưa dùng":
            return False, 0, f"Voucher đã {vcr.trang_thai.lower()}", None
        if vcr.ngay_het_han and date.today() > vcr.ngay_het_han:
            return False, 0, "Voucher đã hết hạn", None
        if ma_kh and vcr.ma_kh != ma_kh:
            return False, 0, "Voucher này không thuộc về khách hàng hiện tại", None
        if tong_tien < (vcr.dieu_kien_toi_thieu or 0):
            return False, 0, (
                f"Đơn tối thiểu {int(vcr.dieu_kien_toi_thieu):,}đ "
                f"(hiện: {int(tong_tien):,}đ)"
            ), None

        if vcr.loai_giam == "PhanTram":
            giam = tong_tien * vcr.gia_tri_giam / 100
            if vcr.toi_da_giam:
                giam = min(giam, vcr.toi_da_giam)
        else:
            giam = min(vcr.gia_tri_giam, tong_tien)

        return True, giam, (
            f"✅ {vcr.ten_voucher} | Giảm: {int(giam):,}đ"
        ), vcr.id

    finally:
        session.close()


def confirm_su_dung_voucher(voucher_id: int, ma_hd: int):
    """Đánh dấu voucher đã dùng sau khi hóa đơn commit thành công."""
    session = get_session()
    try:
        vcr = session.get(Voucher, voucher_id)
        if vcr:
            vcr.trang_thai = "Đã dùng"
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


# ════════════════════════════════════════════════════════════════
# 5. QUERY HELPERS (dùng cho UI)
# ════════════════════════════════════════════════════════════════
def lay_voucher_cua_kh(ma_kh: int, chi_con_hieu_luc=False) -> list[dict]:
    """Lấy danh sách voucher của 1 khách hàng."""
    session = get_session()
    try:
        q = session.query(Voucher).filter_by(ma_kh=ma_kh)
        if chi_con_hieu_luc:
            q = q.filter_by(trang_thai="Chưa dùng")
        vcrs = q.order_by(Voucher.ngay_tao.desc()).all()
        return [
            {
                "id":          v.id,
                "ma_code":     v.ma_code,
                "ten_voucher": v.ten_voucher,
                "loai_giam":   v.loai_giam,
                "gia_tri_giam":v.gia_tri_giam,
                "toi_da_giam": v.toi_da_giam,
                "dk_toi_thieu":v.dieu_kien_toi_thieu,
                "ngay_het_han":v.ngay_het_han.strftime("%d/%m/%Y") if v.ngay_het_han else "Không giới hạn",
                "trang_thai":  v.trang_thai,
                "ngay_tao":    v.ngay_tao.strftime("%d/%m/%Y") if v.ngay_tao else "",
            }
            for v in vcrs
        ]
    finally:
        session.close()


def lay_lich_su_diem(ma_kh: int, limit=50) -> list[dict]:
    """Lịch sử tích/tiêu điểm của khách hàng."""
    session = get_session()
    try:
        rows = (session.query(LichSuDiemKH)
                .filter_by(ma_kh=ma_kh)
                .order_by(LichSuDiemKH.thoi_gian.desc())
                .limit(limit).all())
        return [
            {
                "thoi_gian": r.thoi_gian.strftime("%d/%m/%Y %H:%M") if r.thoi_gian else "",
                "loai":      r.loai,
                "so_diem":   r.so_diem,
                "mo_ta":     r.mo_ta or "",
                "ma_hd":     f"HD#{r.ma_hd:04d}" if r.ma_hd else "",
            }
            for r in rows
        ]
    finally:
        session.close()


def lay_thong_tin_kh(ma_kh: int) -> Optional[dict]:
    """Thông tin tổng hợp của khách hàng."""
    session = get_session()
    try:
        kh = session.get(KhachHang, ma_kh)
        if not kh:
            return None
        vcr_con = sum(1 for v in kh.vouchers if v.trang_thai == "Chưa dùng")
        return {
            "id":           kh.id,
            "ten_kh":       kh.ten_kh,
            "so_dien_thoai":kh.so_dien_thoai or "",
            "diem":         kh.diem_tich_luy or 0,
            "tong_chi_tieu":kh.tong_chi_tieu or 0,
            "hang":         kh.hang_thanh_vien or "Đồng",
            "voucher_con":  vcr_con,
        }
    finally:
        session.close()


def lay_bang_doi_diem() -> list[dict]:
    """Trả về bảng đổi điểm để hiển thị UI."""
    return [
        {
            "idx":         i,
            "diem":        g["diem"],
            "ten":         g["ten"],
            "loai":        g["loai"],
            "gia_tri":     g["giam"],
            "toi_da":      g.get("toi_da"),
            "mo_ta": (
                f"Giảm {int(g['giam']):,}đ"
                if g["loai"] == "TienMat"
                else f"Giảm {g['giam']}%"
                     + (f" (tối đa {int(g['toi_da']):,}đ)" if g.get("toi_da") else "")
            ),
        }
        for i, g in enumerate(BANG_DOI_DIEM)
    ]