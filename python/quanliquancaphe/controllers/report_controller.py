"""
controllers/report_controller.py
Tổng hợp doanh thu từ bảng HoaDon + ChiTietHoaDon.
"""
from database.db_config import get_session
from database.models import HoaDon, ChiTietHoaDon, SanPham


def get_revenue_summary(ngay_bat_dau=None, ngay_ket_thuc=None) -> dict:
    """
    Trả về dict:
      total_orders   – số hóa đơn đã thanh toán
      total_revenue  – tổng thanh_tien (đã gồm VAT)
      total_cost     – tổng giá vốn (gia_nhap * so_luong)
      total_tax      – tổng thuế VAT
      net_profit     – lợi nhuận ròng = total_revenue - total_cost - total_tax
    """
    session = get_session()
    try:
        query = session.query(HoaDon).filter(HoaDon.trang_thai == 'Đã thanh toán')

        if ngay_bat_dau:
            query = query.filter(HoaDon.thoi_gian >= ngay_bat_dau)
        if ngay_ket_thuc:
            query = query.filter(HoaDon.thoi_gian <= ngay_ket_thuc)

        orders = query.all()

        total_orders  = len(orders)
        total_revenue = sum(o.thanh_tien or 0 for o in orders)
        total_tax     = sum(o.thue      or 0 for o in orders)

        # Tính chi phí vốn từ chi tiết từng món
        total_cost = 0.0
        for order in orders:
            for ct in order.chi_tiet:
                gia_nhap = ct.san_pham.gia_nhap if ct.san_pham else 0
                total_cost += (gia_nhap or 0) * (ct.so_luong or 0)

        net_profit = total_revenue - total_cost - total_tax

        return {
            'total_orders':  total_orders,
            'total_revenue': total_revenue,
            'total_cost':    total_cost,
            'total_tax':     total_tax,
            'net_profit':    net_profit,
        }
    except Exception as e:
        print(f"[report_controller] Lỗi: {e}")
        return {
            'total_orders': 0, 'total_revenue': 0,
            'total_cost': 0,   'total_tax': 0, 'net_profit': 0,
        }
    finally:
        session.close()


def get_daily_revenue(limit_days: int = 7) -> list[dict]:
    """
    Doanh thu theo ngày, dùng cho biểu đồ.
    Trả về list[{'ngay': 'dd/mm', 'doanh_thu': float}]
    """
    from datetime import date, timedelta
    session = get_session()
    try:
        results = []
        today = date.today()
        for i in range(limit_days - 1, -1, -1):
            d = today - timedelta(days=i)
            orders = (
                session.query(HoaDon)
                .filter(
                    HoaDon.trang_thai == 'Đã thanh toán',
                    HoaDon.thoi_gian >= d,
                    HoaDon.thoi_gian <  d + timedelta(days=1),
                )
                .all()
            )
            results.append({
                'ngay': d.strftime('%d/%m'),
                'doanh_thu': sum(o.thanh_tien or 0 for o in orders),
            })
        return results
    finally:
        session.close()