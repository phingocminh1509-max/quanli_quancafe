"""
controllers/pos_controller.py
Xử lý thanh toán, gắn hóa đơn vào PhienLamViec đang hoạt động.
"""
from database.db_config import get_session
from database.models import HoaDon, ChiTietHoaDon, SanPham, PhienLamViec


def get_active_session(session, nhan_vien_id: int) -> PhienLamViec | None:
    """Lấy phiên đang hoạt động của nhân viên. Trả None nếu chưa đăng nhập ca."""
    return (
        session.query(PhienLamViec)
        .filter_by(ma_nv=nhan_vien_id, dang_hoat_dong=True)
        .order_by(PhienLamViec.thoi_gian_dang_nhap.desc())
        .first()
    )


def process_checkout(
    order_items: list,
    nhan_vien_id: int,
    km_id: int = None,
    km_discount: float = 0,
    khach_hang_id: int = None,
) -> tuple[bool, str]:
    """
    Tạo HoaDon + ChiTietHoaDon từ danh sách món đã order.

    order_items   : list of dict {'name', 'qty', 'price', 'note'}
    nhan_vien_id  : id NhanVien đang đăng nhập
    km_id         : id KhuyenMai áp dụng (None = không có)
    km_discount   : số tiền được giảm (đã tính sẵn từ UI)
    khach_hang_id : id KhachHang liên kết (None = khách vãng lai)
    """
    session = get_session()
    try:
        # 1. Lấy / tạo phiên làm việc
        phien = get_active_session(session, nhan_vien_id)
        if not phien:
            phien = PhienLamViec(ma_nv=nhan_vien_id, dang_hoat_dong=True)
            session.add(phien)
            session.flush()

        # 2. Tính tiền
        grand_total = sum(item['qty'] * item['price'] for item in order_items)
        vat         = grand_total * 0.10
        subtotal    = grand_total + vat
        thanh_tien  = max(0.0, subtotal - float(km_discount))

        # 3. Tạo hóa đơn
        hoa_don = HoaDon(
            ma_phien   = phien.id,
            ma_km      = km_id,
            ma_kh      = khach_hang_id,
            tong_tien  = grand_total,
            thue       = vat,
            giam_gia   = float(km_discount),
            thanh_tien = thanh_tien,
            trang_thai = 'Đã thanh toán',
        )
        session.add(hoa_don)
        session.flush()  # lấy hoa_don.id

        # 4. Chi tiết từng món
        for item in order_items:
            # Dòng quà tặng MuaXTangY — tên có thể kèm " (Quà tặng)", price=0
            # Tìm SP theo tên gốc (bỏ hậu tố " (Quà tặng)" nếu có)
            ten_goc = item['name'].replace(" (Quà tặng)", "").strip()
            sp = session.query(SanPham).filter_by(ten_sp=ten_goc).first()
            if not sp:
                # Thử tên nguyên gốc (phòng trường hợp không có hậu tố)
                sp = session.query(SanPham).filter_by(ten_sp=item['name']).first()
            if not sp:
                raise ValueError(f"Không tìm thấy sản phẩm: {item['name']}")
            ct = ChiTietHoaDon(
                ma_hd      = hoa_don.id,
                ma_sp      = sp.id,
                so_luong   = item['qty'],
                don_gia    = item['price'],        # 0 nếu là quà tặng
                thanh_tien = item['qty'] * item['price'],
                ghi_chu    = item.get('note') or None,
            )
            session.add(ct)

        # 5. Tăng lượt dùng KM nếu có
        # Lưu ý: KM MuaXTangY đổi điểm đã được tăng so_luot_da_dung
        # ngay lúc đổi điểm trong _on_dd_double_click → KHÔNG tăng thêm ở đây
        # để tránh đếm 2 lần. Chỉ tăng với KM Chung (không qua đổi điểm).
        if km_id:
            from database.models import KhuyenMai
            km_obj = session.get(KhuyenMai, km_id)
            if km_obj:
                la_doi_diem = int(getattr(km_obj, 'la_doi_diem', 0) or 0)
                if not la_doi_diem:
                    # KM Chung thường — tăng lượt dùng tại đây
                    km_obj.so_luot_da_dung = (km_obj.so_luot_da_dung or 0) + 1

        session.commit()

        # 6. Tích điểm cho khách hàng (sau commit để HoaDon đã tồn tại trong DB)
        _diem_msg = ""
        if khach_hang_id:
            try:
                from controllers.loyalty_controller import tich_diem_hoa_don
                _ok, _diem_msg = tich_diem_hoa_don(hoa_don.id)
            except Exception:
                pass

        _suffix = f" | {_diem_msg}" if _diem_msg else ""
        return True, f"Hóa đơn HD{hoa_don.id:04d} | Tổng: {int(thanh_tien):,} đ{_suffix}"

    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()