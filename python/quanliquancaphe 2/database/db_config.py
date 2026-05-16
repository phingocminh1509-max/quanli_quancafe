"""
database/db_config.py
Kết nối DB, auto-migrate, seed admin, và các helper ghi nhật ký.
"""
import sqlite3
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base,
    SanPham, KhuyenMai,
    NhanVien, NhatKyHoatDong, NhatKyDangNhap,
    CaLamViec, PhanCongCaLam, PhienLamViec,
    KhachHang, HoaDon, ChiTietHoaDon,
    Voucher, LichSuDiemKH,
    NhatKyHeThong, NhatKyKhuyenMai,
    ChamCong,
)

engine       = create_engine('sqlite:///cafee_pos.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ════════════════════════════════════════════════════════════════════
# 1. SESSION
# ════════════════════════════════════════════════════════════════════
def get_session():
    return SessionLocal()


# ════════════════════════════════════════════════════════════════════
# 2. AUTO-MIGRATE — thêm cột còn thiếu vào bảng cũ
# ════════════════════════════════════════════════════════════════════
def auto_migrate():
    """
    So sánh từng bảng trong models với bảng thực trong DB.
    Với mỗi cột còn thiếu → tự chạy ALTER TABLE ADD COLUMN.
    An toàn khi chạy lặp lại nhiều lần.
    """
    inspector       = inspect(engine)
    existing_tables = inspector.get_table_names()

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # bảng chưa có → create_all sẽ lo

        existing_cols = {col["name"] for col in inspector.get_columns(table.name)}

        with engine.connect() as conn:
            for col in table.columns:
                if col.name in existing_cols:
                    continue

                col_type = col.type.compile(engine.dialect)

                default_clause = ""
                if col.default is not None and col.default.is_scalar:
                    val = col.default.arg
                    if isinstance(val, str):
                        default_clause = f" DEFAULT '{val}'"
                    elif isinstance(val, bool):
                        default_clause = f" DEFAULT {int(val)}"
                    elif val is not None:
                        default_clause = f" DEFAULT {val}"
                elif col.nullable is False and col.default is None:
                    default_clause = (" DEFAULT ''"
                                      if "CHAR" in col_type.upper()
                                      else " DEFAULT 0")

                nullable_clause = "" if col.nullable else " NOT NULL"
                ddl = (
                    f"ALTER TABLE {table.name} "
                    f"ADD COLUMN {col.name} {col_type}"
                    f"{default_clause}{nullable_clause}"
                )
                try:
                    conn.execute(text(ddl))
                    conn.commit()
                    print(f"  [migrate] ✅ {table.name}.{col.name} ({col_type})")
                except Exception as e:
                    print(f"  [migrate] ⚠️  {table.name}.{col.name} → {e}")

    _migrate_luong()


def _migrate_luong():
    """Copy giá trị cột 'luong' cũ → 'luong_co_ban' nếu cần."""
    try:
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("nhan_vien")}
        if "luong" in cols and "luong_co_ban" in cols:
            with engine.connect() as conn:
                conn.execute(text(
                    "UPDATE nhan_vien SET luong_co_ban = luong "
                    "WHERE luong_co_ban IS NULL OR luong_co_ban = 0"
                ))
                conn.commit()
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════
# 3. INIT DB & SEED
# ════════════════════════════════════════════════════════════════════
def init_db_and_seed():
    """
    Khởi động DB:
      1. Tạo bảng mới chưa có
      2. Auto-migrate cột còn thiếu vào bảng cũ
      3. Seed tài khoản Admin nếu DB trắng
    """
    Base.metadata.create_all(bind=engine)
    auto_migrate()

    session = SessionLocal()
    try:
        if session.query(NhanVien).count() == 0:
            print("Đang khởi tạo CSDL trắng...")
            admin = NhanVien(
                ten_nv        = "Chủ Quán",
                ten_dang_nhap = "admin",
                mat_khau      = "123",
                chuc_vu       = "Admin",
                luong_co_ban  = 0,
            )
            session.add(admin)
            session.commit()
            print("✅ Tạo tài khoản admin / mật khẩu: 123")
    finally:
        session.close()


# ════════════════════════════════════════════════════════════════════
# 4. PHIÊN LÀM VIỆC (đăng nhập / đăng xuất hệ thống ca)
# ════════════════════════════════════════════════════════════════════
def dang_nhap(ten_dang_nhap: str, mat_khau: str, ma_ca: int = None):
    """
    Xác thực NV và tạo PhienLamViec mới.
    Trả về (PhienLamViec, NhanVien) hoặc (None, None).
    """
    from datetime import datetime
    session = SessionLocal()
    try:
        nv = (session.query(NhanVien)
              .filter_by(ten_dang_nhap=ten_dang_nhap, mat_khau=mat_khau)
              .first())
        if not nv:
            return None, None

        # Đóng phiên cũ còn treo
        phien_cu = (session.query(PhienLamViec)
                    .filter_by(ma_nv=nv.id, dang_hoat_dong=True)
                    .first())
        if phien_cu:
            phien_cu.thoi_gian_dang_xuat = datetime.now()
            phien_cu.dang_hoat_dong      = False

        phien_moi = PhienLamViec(ma_nv=nv.id, ma_ca=ma_ca)
        session.add(phien_moi)
        session.commit()
        session.refresh(phien_moi)
        return phien_moi, nv
    finally:
        session.close()


def dang_xuat(ma_phien: int):
    """Kết thúc phiên làm việc."""
    from datetime import datetime
    session = SessionLocal()
    try:
        phien = session.query(PhienLamViec).get(ma_phien)
        if phien and phien.dang_hoat_dong:
            phien.thoi_gian_dang_xuat = datetime.now()
            phien.dang_hoat_dong      = False
            session.commit()
    finally:
        session.close()


# ════════════════════════════════════════════════════════════════════
# 5. HELPER GHI NHẬT KÝ
# ════════════════════════════════════════════════════════════════════
def ghi_nhat_ky_dang_nhap(
    ten_dang_nhap: str,
    hanh_dong:     str,
    ket_qua:       str = "Thành công",
    ma_nv:         int = None,
    ghi_chu:       str = None,
):
    """
    Ghi một dòng vào NhatKyDangNhap.
    Gọi từ auth_controller mỗi khi đăng nhập / đăng xuất.

    hanh_dong : 'Đăng nhập' | 'Đăng xuất'
    ket_qua   : 'Thành công' | 'Sai mật khẩu' | 'Tài khoản khóa' | 'Thất bại'
    """
    try:
        session = SessionLocal()
        session.add(NhatKyDangNhap(
            ma_nv         = ma_nv,
            ten_dang_nhap = ten_dang_nhap,
            hanh_dong     = hanh_dong,
            ket_qua       = ket_qua,
            ghi_chu       = ghi_chu,
        ))
        session.commit()
        session.close()
    except Exception:
        pass   # không để log lỗi gây crash app


def ghi_nhat_ky_hoat_dong(
    ma_nv:     int,
    hanh_dong: str,
    mo_ta:     str = "",
    o_dau:     str = "",
    ket_qua:   str = "Thành công",
):
    """
    Ghi một dòng vào NhatKyHoatDong (5 chiều đầy đủ).
    Dùng khắp nơi: admin_settings, customer_manager, product_manager…

    o_dau   : tên màn hình / module (vd: 'Quản lý NV', 'POS Screen')
    ket_qua : 'Thành công' | 'Thất bại' | 'Cảnh báo'
    """
    try:
        session = SessionLocal()
        session.add(NhatKyHoatDong(
            ma_nv     = ma_nv,
            hanh_dong = hanh_dong,
            mo_ta     = mo_ta,
            o_dau     = o_dau,
            ket_qua   = ket_qua,
        ))
        session.commit()
        session.close()
    except Exception:
        pass