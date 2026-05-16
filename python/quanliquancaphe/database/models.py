from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Time, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, date

Base = declarative_base()

# =================================================================
# PHẦN 1: NHÂN SỰ, CA LÀM & PHIÊN ĐĂNG NHẬP
# =================================================================

class NhanVien(Base):
    """
    Thông tin nhân viên đầy đủ.

    chuc_vu: 'Admin' | 'Quản lý' | 'Thu ngân' | 'Pha chế' | 'Phục vụ'
    trang_thai: 'Đang làm việc' | 'Tạm khóa' | 'Đã nghỉ việc'
    avatar_path: đường dẫn file ảnh trên disk (None = dùng avatar mặc định)
    """
    __tablename__ = 'nhan_vien'

    id            = Column(Integer, primary_key=True, autoincrement=True)
    ten_nv        = Column(String(100), nullable=False)
    ten_dang_nhap = Column(String(50),  unique=True, nullable=False)
    mat_khau      = Column(String(100), nullable=False, default='123456')
    chuc_vu       = Column(String(50),  default='Thu ngân')
    luong_co_ban  = Column(Float,  default=0.0)
    sdt           = Column(String(15),  nullable=True)
    email         = Column(String(100), nullable=True)
    ngay_vao_lam  = Column(Date, default=date.today)
    trang_thai    = Column(String(50),  default='Đang làm việc')
    avatar_path   = Column(String(300), nullable=True)   # đường dẫn ảnh

    phien_lam_viec = relationship("PhienLamViec",   back_populates="nhan_vien")
    nhat_ky        = relationship("NhatKyHoatDong", back_populates="nhan_vien",
                                  order_by="NhatKyHoatDong.thoi_gian.desc()")
    cham_congs     = relationship("ChamCong",       back_populates="nhan_vien",
                                  cascade="all, delete-orphan",
                                  order_by="ChamCong.ngay.desc()")


class NhatKyHoatDong(Base):
    """
    Audit trail đầy đủ 5 chiều:
      Ai (ma_nv)  · Làm gì (hanh_dong)  · Khi nào (thoi_gian)
      Ở đâu (o_dau: module/màn hình)  · Kết quả (ket_qua: Thành công / Thất bại / …)

    hanh_dong ví dụ:
      'Tạo hóa đơn' | 'Hủy hóa đơn' | 'Sửa sản phẩm'
      'Thêm nhân viên' | 'Đổi mật khẩu' | 'Khóa TK' | 'Mở TK'
      'Thêm KH' | 'Tích điểm' | 'Phát voucher'
    """
    __tablename__ = 'nhat_ky_hoat_dong'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    ma_nv       = Column(Integer, ForeignKey('nhan_vien.id'), nullable=False)
    thoi_gian   = Column(DateTime, default=datetime.now, nullable=False)
    hanh_dong   = Column(String(100), nullable=False)
    mo_ta       = Column(String(300), nullable=True)
    o_dau       = Column(String(100), nullable=True)   # module / màn hình
    ket_qua     = Column(String(50),  default='Thành công')
    # 'Thành công' | 'Thất bại' | 'Cảnh báo'

    nhan_vien = relationship("NhanVien", back_populates="nhat_ky")


class NhatKyDangNhap(Base):
    """
    Bảng riêng ghi mỗi lượt đăng nhập / đăng xuất.
    Tách khỏi NhatKyHoatDong để dễ lọc & thống kê độc lập.

    ket_qua: 'Thành công' | 'Sai mật khẩu' | 'Tài khoản khóa'
    hanh_dong: 'Đăng nhập' | 'Đăng xuất'
    """
    __tablename__ = 'nhat_ky_dang_nhap'

    id            = Column(Integer, primary_key=True, autoincrement=True)
    ma_nv         = Column(Integer, ForeignKey('nhan_vien.id'), nullable=True)
    ten_dang_nhap = Column(String(50), nullable=True)   # ghi kể cả khi login thất bại
    hanh_dong     = Column(String(50), nullable=False)  # 'Đăng nhập' | 'Đăng xuất'
    thoi_gian     = Column(DateTime, default=datetime.now, nullable=False)
    ket_qua       = Column(String(50), default='Thành công')
    ghi_chu       = Column(String(200), nullable=True)  # lý do thất bại, thiết bị…


class CaLamViec(Base):
    """Định nghĩa ca (Sáng / Chiều / Tối …)."""
    __tablename__ = 'ca_lam_viec'

    id           = Column(Integer, primary_key=True, autoincrement=True)
    ten_ca       = Column(String(50), nullable=False)
    gio_bat_dau  = Column(Time)
    gio_ket_thuc = Column(Time)

    phien_lam_viec = relationship("PhienLamViec", back_populates="ca_lam_viec")


class PhanCongCaLam(Base):
    """Lịch phân công ca cho từng nhân viên theo ngày."""
    __tablename__ = 'phan_cong_ca_lam'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    ma_nv       = Column(Integer, ForeignKey('nhan_vien.id'))
    ma_ca       = Column(Integer, ForeignKey('ca_lam_viec.id'))
    ngay_lam    = Column(Date, nullable=False)
    trang_thai_dd = Column(String(50), default='Chưa điểm danh')
    # 'Chưa điểm danh' | 'Đã điểm danh' | 'Vắng'


class PhienLamViec(Base):
    """
    Ghi nhận một lượt đăng nhập – đăng xuất của nhân viên.

    Vòng đời:
      • Đăng nhập  → tạo bản ghi, thoi_gian_dang_nhap = now(), dang_hoat_dong = True
      • Đăng xuất  → thoi_gian_dang_xuat = now(), dang_hoat_dong = False
      • Mọi HoaDon tạo trong khoảng thời gian này đều trỏ về ma_phien này,
        giúp truy vấn "lịch sử gọi món của nhân viên X trong ca Y ngày Z".
    """
    __tablename__ = 'phien_lam_viec'

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    ma_nv                = Column(Integer, ForeignKey('nhan_vien.id'), nullable=False)
    ma_ca                = Column(Integer, ForeignKey('ca_lam_viec.id'), nullable=True)
    thoi_gian_dang_nhap  = Column(DateTime, default=datetime.now, nullable=False)
    thoi_gian_dang_xuat  = Column(DateTime, nullable=True)   # NULL = đang trong ca
    dang_hoat_dong       = Column(Boolean, default=True)     # True = chưa đăng xuất

    nhan_vien   = relationship("NhanVien",  back_populates="phien_lam_viec")
    ca_lam_viec = relationship("CaLamViec", back_populates="phien_lam_viec")
    hoa_don     = relationship("HoaDon",    back_populates="phien_lam_viec")


# =================================================================
# PHẦN 2: MENU & KHUYẾN MÃI
#   (Đã bỏ NguyenLieu + CongThuc, thay bằng gia_nhap trực tiếp
#    trên SanPham — đơn giản hóa cho mô hình quán café nhỏ)
# =================================================================

class SanPham(Base):
    """
    Sản phẩm bán ra.
    gia_nhap = giá vốn / chi phí ước tính cho 1 phần.
    Lợi nhuận gộp = gia_ban - gia_nhap.
    """
    __tablename__ = 'san_pham'

    id        = Column(Integer, primary_key=True, autoincrement=True)
    ten_sp    = Column(String(100), nullable=False)
    danh_muc  = Column(String(100), default='Chưa phân loại')  # Cà phê / Trà / Bánh …
    gia_nhap  = Column(Float, default=0.0)   # giá vốn (thay thế NguyenLieu)
    gia_ban   = Column(Float, nullable=False)
    trang_thai = Column(String(50), default='Đang bán')
    # 'Đang bán' | 'Ngừng bán' | 'Hết hàng'

    @property
    def loi_nhuan_gop(self):
        """Lợi nhuận gộp trên 1 đơn vị sản phẩm."""
        return (self.gia_ban or 0) - (self.gia_nhap or 0)


class KhuyenMai(Base):
    """
    Mã / chương trình khuyến mãi.

    loai_km:
      'DonHang'  – giảm trên tổng hóa đơn (điều kiện: tong_tien >= dk_tong_tien_tu)
      'SanPham'  – giảm trực tiếp trên sản phẩm cụ thể (ma_sp != NULL)
      'MuaXTangY'– mua đủ so_luong_mua tặng so_luong_tang (logic xử lý ở tầng service)

    kieu_giam:
      'PhanTram' – giảm theo % (gia_tri_giam = phần trăm, toi_da_giam = trần tiền giảm)
      'TienMat'  – giảm số tiền cố định

    ap_dung_cho_hang_thang:
      NULL = áp dụng mọi lúc; "1,2,12" = chỉ áp dụng tháng 1, 2, 12.

    so_luot_dung_toi_da:
      NULL = không giới hạn; > 0 = giới hạn tổng số lần dùng toàn hệ thống.
    """
    __tablename__ = 'khuyen_mai'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    ten_km          = Column(String(200), nullable=False)
    ma_code         = Column(String(50),  unique=True, nullable=True)  # mã nhập tay, có thể NULL

    # ── Phân loại ──────────────────────────────────────────────
    loai_km         = Column(String(50), default='DonHang')
    # 'DonHang' | 'SanPham' | 'MuaXTangY'

    ma_sp           = Column(Integer, ForeignKey('san_pham.id'), nullable=True)
    # NULL = áp dụng toàn đơn; có giá trị = áp dụng riêng sản phẩm đó
    ma_sp_tang      = Column(Integer, ForeignKey('san_pham.id'), nullable=True)
    # Sản phẩm được tặng trong chương trình MuaXTangY

    # ── Điều kiện kích hoạt ────────────────────────────────────
    dk_tong_tien_tu = Column(Float,   default=0.0)   # tổng đơn tối thiểu
    dk_so_luong_tu  = Column(Integer, default=0)     # số lượng SP tối thiểu (cho MuaXTangY)
    so_luong_mua    = Column(Integer, nullable=True)  # MuaXTangY: mua bao nhiêu
    so_luong_tang   = Column(Integer, nullable=True)  # MuaXTangY: tặng bao nhiêu

    # ── Giá trị giảm ───────────────────────────────────────────
    kieu_giam       = Column(String(50))   # 'PhanTram' | 'TienMat'
    gia_tri_giam    = Column(Float, default=0.0)
    toi_da_giam     = Column(Float, nullable=True)   # trần giảm (dùng cho PhanTram)

    # ── Thời hạn & giới hạn ────────────────────────────────────
    ngay_bat_dau    = Column(Date, nullable=True)
    ngay_ket_thuc   = Column(Date, nullable=True)
    ap_dung_thang   = Column(String(50), nullable=True)  # vd: "1,2,12" hoặc NULL
    so_luot_toi_da  = Column(Integer, nullable=True)     # giới hạn tổng lượt dùng
    so_luot_da_dung = Column(Integer, default=0)         # đếm thực tế đã dùng

    trang_thai      = Column(String(50), default='Đang chạy')
    # 'Đang chạy' | 'Tạm dừng' | 'Hết hạn'

    san_pham      = relationship("SanPham", foreign_keys=[ma_sp])
    san_pham_tang = relationship("SanPham", foreign_keys=[ma_sp_tang])

    def con_hieu_luc(self, ngay_kiem_tra: date = None) -> bool:
        """Kiểm tra nhanh xem KM có còn hiệu lực không."""
        ngay = ngay_kiem_tra or date.today()
        if self.trang_thai != 'Đang chạy':
            return False
        if self.ngay_bat_dau and ngay < self.ngay_bat_dau:
            return False
        if self.ngay_ket_thuc and ngay > self.ngay_ket_thuc:
            return False
        if self.so_luot_toi_da and self.so_luot_da_dung >= self.so_luot_toi_da:
            return False
        return True


# =================================================================
# PHẦN 3: KHÁCH HÀNG, BÁN HÀNG & HÓA ĐƠN
# =================================================================

class KhachHang(Base):
    """
    Khách hàng thành viên.
    diem_tich_luy  : 1 điểm = 1.000đ chi tiêu (tuỳ chỉnh ở service)
    hang_thanh_vien: 'Đồng' | 'Bạc' | 'Vàng' | 'Kim cương'
    """
    __tablename__ = 'khach_hang'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    ten_kh          = Column(String(100), nullable=False)
    so_dien_thoai   = Column(String(15),  unique=True, nullable=True)
    email           = Column(String(100), nullable=True)
    ngay_sinh       = Column(Date,        nullable=True)
    diem_tich_luy   = Column(Integer, default=0)
    tong_chi_tieu   = Column(Float,   default=0.0)
    hang_thanh_vien = Column(String(50), default='Đồng')
    ngay_tham_gia   = Column(Date, default=date.today)
    ghi_chu         = Column(String(300), nullable=True)

    vouchers  = relationship("Voucher",        back_populates="khach_hang",
                             cascade="all, delete-orphan")
    lich_su   = relationship("LichSuDiemKH",   back_populates="khach_hang",
                             order_by="LichSuDiemKH.thoi_gian.desc()")


class Voucher(Base):
    """
    Voucher phát cho khách hàng thành viên.
    loai_giam: 'PhanTram' | 'TienMat'
    trang_thai: 'Chưa dùng' | 'Đã dùng' | 'Hết hạn'
    """
    __tablename__ = 'voucher'

    id           = Column(Integer, primary_key=True, autoincrement=True)
    ma_kh        = Column(Integer, ForeignKey('khach_hang.id'), nullable=False)
    ma_code      = Column(String(50), unique=True, nullable=False)
    ten_voucher  = Column(String(200))
    loai_giam    = Column(String(50), default='TienMat')   # 'PhanTram' | 'TienMat'
    gia_tri_giam = Column(Float, default=0.0)
    toi_da_giam  = Column(Float, nullable=True)
    dieu_kien_toi_thieu = Column(Float, default=0.0)       # đơn tối thiểu
    ngay_het_han = Column(Date, nullable=True)
    trang_thai   = Column(String(50), default='Chưa dùng')
    ngay_tao     = Column(Date, default=date.today)

    khach_hang = relationship("KhachHang", back_populates="vouchers")


class LichSuDiemKH(Base):
    """Lịch sử tích / tiêu điểm của khách hàng."""
    __tablename__ = 'lich_su_diem_kh'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    ma_kh      = Column(Integer, ForeignKey('khach_hang.id'), nullable=False)
    ma_hd      = Column(Integer, ForeignKey('hoa_don.id'),    nullable=True)
    thoi_gian  = Column(DateTime, default=datetime.now)
    loai       = Column(String(50))   # 'Tích điểm' | 'Đổi điểm' | 'Điều chỉnh'
    so_diem    = Column(Integer, default=0)   # > 0 = tích, < 0 = tiêu
    mo_ta      = Column(String(200), nullable=True)

    khach_hang = relationship("KhachHang", back_populates="lich_su")


class NhatKyHeThong(Base):
    """
    Nhật ký hệ thống toàn cục — ghi mọi sự kiện quan trọng.
    Khác NhatKyHoatDong (gắn nhân viên): bảng này dùng cho audit
    không cần đăng nhập (khởi động, lỗi, cấu hình…).
    """
    __tablename__ = 'nhat_ky_he_thong'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    thoi_gian  = Column(DateTime, default=datetime.now, nullable=False)
    loai       = Column(String(50))   # 'INFO' | 'WARN' | 'ERROR' | 'ACTION'
    nguon      = Column(String(100))  # module phát sinh, vd 'pos_controller'
    noi_dung   = Column(String(500), nullable=False)
    ma_nv      = Column(Integer, ForeignKey('nhan_vien.id'), nullable=True)


class NhatKyKhuyenMai(Base):
    """Lịch sử áp dụng / dùng khuyến mãi."""
    __tablename__ = 'nhat_ky_khuyen_mai'

    id        = Column(Integer, primary_key=True, autoincrement=True)
    ma_km     = Column(Integer, ForeignKey('khuyen_mai.id'), nullable=False)
    ma_hd     = Column(Integer, ForeignKey('hoa_don.id'),    nullable=True)
    ma_kh     = Column(Integer, ForeignKey('khach_hang.id'), nullable=True)
    ma_nv     = Column(Integer, ForeignKey('nhan_vien.id'),  nullable=True)
    thoi_gian = Column(DateTime, default=datetime.now)
    so_tien_giam = Column(Float, default=0.0)
    ghi_chu   = Column(String(200), nullable=True)

    khuyen_mai = relationship("KhuyenMai")


class HoaDon(Base):
    """
    Mỗi hóa đơn bắt buộc phải gắn với một PhienLamViec (ma_phien).
    Nhờ đó có thể truy vấn toàn bộ lịch sử gọi món trong ca của nhân viên.
    """
    __tablename__ = 'hoa_don'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    thoi_gian   = Column(DateTime, default=datetime.now)

    # ── Liên kết nhân sự ────────────────────────────────────────
    ma_phien    = Column(Integer, ForeignKey('phien_lam_viec.id'), nullable=False)
    # Phiên đăng nhập đang hoạt động → xác định nhân viên + ca + ngày tự động

    # ── Liên kết khách & khuyến mãi ─────────────────────────────
    ma_kh       = Column(Integer, ForeignKey('khach_hang.id'),   nullable=True)
    ma_km       = Column(Integer, ForeignKey('khuyen_mai.id'),   nullable=True)

    # ── Tiền tệ ──────────────────────────────────────────────────
    tong_tien   = Column(Float, default=0.0)   # tổng trước giảm + thuế
    giam_gia    = Column(Float, default=0.0)   # tổng tiền được giảm
    thue        = Column(Float, default=0.0)   # VAT (nếu có)
    thanh_tien  = Column(Float, default=0.0)   # thực thu = tong_tien - giam_gia + thue

    phuong_thuc_tt = Column(String(50), default='Tiền mặt')
    # 'Tiền mặt' | 'Chuyển khoản' | 'Thẻ'

    trang_thai  = Column(String(50), default='Đã thanh toán')
    # 'Đã thanh toán' | 'Đang chờ' | 'Đã hủy'

    chi_tiet       = relationship("ChiTietHoaDon",  back_populates="hoa_don",
                                  cascade="all, delete-orphan")
    phien_lam_viec = relationship("PhienLamViec",   back_populates="hoa_don")
    khuyen_mai     = relationship("KhuyenMai",      foreign_keys=[ma_km])
    khach_hang     = relationship("KhachHang",       foreign_keys=[ma_kh])


class ChiTietHoaDon(Base):
    """
    Từng dòng món trong hóa đơn.
    thoi_gian_goi: thời điểm khách/NV bấm "Gọi món" — hữu ích để
                   theo dõi tốc độ phục vụ và thứ tự pha chế.
    """
    __tablename__ = 'chi_tiet_hoa_don'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    ma_hd           = Column(Integer, ForeignKey('hoa_don.id'),  nullable=False)
    ma_sp           = Column(Integer, ForeignKey('san_pham.id'), nullable=False)

    so_luong        = Column(Integer, nullable=False, default=1)
    don_gia         = Column(Float,   nullable=False)  # giá tại thời điểm gọi
    giam_gia        = Column(Float,   default=0.0)     # giảm dòng (KM theo SP)
    thanh_tien      = Column(Float,   default=0.0)     # = so_luong*don_gia - giam_gia
    thoi_gian_goi   = Column(DateTime, default=datetime.now)
    # Thời điểm gọi món — tự động gán khi tạo dòng

    ghi_chu         = Column(String(200), nullable=True)
    # Ghi chú riêng cho món: "ít đường", "nhiều đá" …

    hoa_don  = relationship("HoaDon",   back_populates="chi_tiet")
    san_pham = relationship("SanPham")


# =================================================================
# PHẦN 4: CHẤM CÔNG
# =================================================================

class ChamCong(Base):
    """
    Bảng chấm công — MỖI BẢN GHI = 1 CA của nhân viên trong ngày.
    Một nhân viên có thể có nhiều bản ghi cùng ngày (nhiều ca).

    trang_thai:
      'Chua_checkin' – ca được tạo, chưa check-in (do PhanCong hoặc hệ thống tạo sẵn)
      'Dang_lam'     – đã check-in, chưa check-out
      'Hoan_thanh'   – check-out đúng giờ / trong khung cho phép
      'Di_tre'       – check-in sau giờ bắt đầu ca (không ân hạn)
      'Ve_som'       – check-out sớm hơn (gio_ket_thuc - 15 phút)
      'Vang_mat'     – không check-in (vắng)
      'Tang_ca'      – check-out muộn hơn (gio_ket_thuc + 30 phút)
      'Nghi_phep'    – nghỉ phép (đặt thủ công bởi quản lý)
      'Khong_ca'     – admin/owner không có phân công, tự do

    Quy tắc:
      Check-in sớm ≤ 15 phút → Dang_lam (đúng giờ)
      Check-in sau gio_bat_dau → Di_tre (ghi phut_tre)
      Check-out sớm ≤ 15 phút → Hoan_thanh
      Check-out sớm > 15 phút → Ve_som (ghi phut_ve_som)
      Check-out muộn > 30 phút → Tang_ca (ghi phut_tang_ca)
    """
    __tablename__ = 'cham_cong'

    id            = Column(Integer, primary_key=True, autoincrement=True)
    nhan_vien_id  = Column(Integer, ForeignKey('nhan_vien.id'), nullable=False)
    ma_ca         = Column(Integer, ForeignKey('ca_lam_viec.id'), nullable=True)
    # NULL = không có ca phân công (admin/owner)
    ma_phien      = Column(Integer, ForeignKey('phien_lam_viec.id'), nullable=True)

    ngay          = Column(Date, nullable=False)

    # Giờ kế hoạch (copy từ CaLamViec khi tạo để tránh JOIN sau này)
    gio_bd_ca     = Column(Time, nullable=True)   # giờ bắt đầu ca kế hoạch
    gio_kt_ca     = Column(Time, nullable=True)   # giờ kết thúc ca kế hoạch

    # Thực tế
    thoi_gian_vao = Column(DateTime, nullable=True)   # datetime check-in thực tế
    thoi_gian_ra  = Column(DateTime, nullable=True)   # datetime check-out thực tế

    trang_thai    = Column(String(50), default='Chua_checkin')
    phut_tre      = Column(Integer, default=0)   # số phút đi trễ
    phut_ve_som   = Column(Integer, default=0)   # số phút về sớm
    phut_tang_ca  = Column(Integer, default=0)   # số phút tăng ca
    ghi_chu       = Column(String(300), nullable=True)

    nhan_vien   = relationship("NhanVien",     back_populates="cham_congs")
    ca_lam_viec = relationship("CaLamViec")
    phien       = relationship("PhienLamViec")