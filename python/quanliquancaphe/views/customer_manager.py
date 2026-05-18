"""
views/customer_manager.py
Sửa:
  • Lỗi không sửa được KH → dùng session riêng biệt, merge đúng cách
  • Xóa KH không mất → cascade delete đúng + dùng session.delete()
  • Thêm nút "Trừ điểm" riêng biệt
  • Enter trong ô tìm → thêm mới nếu không có kết quả
  • Bỏ ngày sinh
"""
from __future__ import annotations
import random, string
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFormLayout, QLineEdit, QComboBox,
    QAbstractItemView, QSpinBox, QDoubleSpinBox, QDateEdit,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from database.db_config import get_session
from database.models import KhachHang, Voucher, LichSuDiemKH

# ── Hạng thành viên ─────────────────────────────────────────────────────────
HANG_CONFIG = [
    ("Kim cương", 10_000_000, "#00BCD4"),
    ("Vàng",       5_000_000, "#F1C40F"),
    ("Bạc",        2_000_000, "#BDC3C7"),
    ("Đồng",               0, "#CD7F32"),
]

STYLE = """
QDialog,QWidget{background-color:#1E1E2E;color:white;}
QTabWidget::pane{border:none;}
QTabBar::tab{background:#2D2D3F;color:#A1A1AA;padding:10px 18px;
    border-radius:6px 6px 0 0;font-weight:bold;font-size:13px;}
QTabBar::tab:selected{background:#3498DB;color:white;}
QTabBar::tab:hover{background:#3E3E55;color:white;}
QTableWidget{background:#2D2D3F;border:none;border-radius:8px;
    gridline-color:#3E3E55;color:white;font-size:13px;}
QTableWidget::item{padding:7px;border-bottom:1px solid #3E3E55;}
QTableWidget::item:selected{background:#3498DB;}
QHeaderView::section{background:#1A1A24;color:#A1A1AA;
    padding:9px;border:none;font-weight:bold;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QDateEdit{
    background:#2D2D3F;border:1px solid #3E3E55;border-radius:6px;
    padding:6px 10px;color:white;font-size:13px;}
QLineEdit:focus{border-color:#3498DB;}
QComboBox::drop-down{border:none;}
QComboBox QAbstractItemView{background:#2D2D3F;color:white;
    selection-background-color:#3498DB;}
QScrollBar:vertical{background:#1A1A24;width:7px;border-radius:4px;}
QScrollBar::handle:vertical{background:#3E3E55;border-radius:4px;}
"""

def _btn(t, c, h=36):
    b = QPushButton(t); b.setMinimumHeight(h)
    b.setStyleSheet(
        f"background:{c};color:white;font-weight:bold;"
        f"border-radius:6px;font-size:12px;padding:0 10px;"
    )
    return b

def _lbl(t, c="white", s=13, bold=False):
    l = QLabel(t)
    l.setStyleSheet(f"color:{c};font-size:{s}px;" + ("font-weight:bold;" if bold else ""))
    return l

def _fl(t):
    l = QLabel(t); l.setStyleSheet("color:#A1A1AA;"); return l

def tinh_hang(chi_tieu: float) -> str:
    for h, n, _ in HANG_CONFIG:
        if chi_tieu >= n: return h
    return "Đồng"

def mau_hang(hang: str) -> str:
    for h, _, c in HANG_CONFIG:
        if h == hang: return c
    return "#CD7F32"

def gen_code(prefix="VC") -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ═══════════════════════════════════════════════════════════════════════════════
# FORM THÊM / SỬA KHÁCH HÀNG
# ═══════════════════════════════════════════════════════════════════════════════
class CustomerForm(QDialog):
    def __init__(self, kh_id=None, ten_mac_dinh="", parent=None):
        super().__init__(parent)
        self.kh_id = kh_id
        self.setWindowTitle("Thêm Khách Hàng" if not kh_id else "Sửa Thông Tin Khách Hàng")
        self.resize(400, 270)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24); root.setSpacing(12)

        form = QFormLayout(); form.setSpacing(10)
        self.txt_ten  = QLineEdit(); self.txt_ten.setPlaceholderText("Nguyễn Văn A")
        from utils.phone_validator import PhoneLineEdit
        self.txt_sdt  = PhoneLineEdit()
        self.txt_mail = QLineEdit(); self.txt_mail.setPlaceholderText("kh@email.com")
        self.txt_note = QLineEdit(); self.txt_note.setPlaceholderText("Ghi chú…")

        if ten_mac_dinh:
            self.txt_ten.setText(ten_mac_dinh)

        form.addRow(_fl("Họ tên *:"),      self.txt_ten)
        form.addRow(_fl("Số điện thoại:"), self.txt_sdt)
        form.addRow(_fl("Email:"),          self.txt_mail)
        form.addRow(_fl("Ghi chú:"),        self.txt_note)
        root.addLayout(form)

        btn = _btn("💾  Lưu", "#27AE60", 44)
        btn.clicked.connect(self._save)
        root.addWidget(btn)

        if kh_id:
            self._load()

    def _load(self):
        # ── FIX: mở session mới, đọc xong đóng ngay ──────────────
        s = get_session()
        try:
            kh = s.query(KhachHang).filter_by(id=self.kh_id).first()
            if not kh:
                return
            ten  = kh.ten_kh or ""
            sdt  = kh.so_dien_thoai or ""
            mail = kh.email or ""
            note = kh.ghi_chu or ""
        finally:
            s.close()

        self.txt_ten.setText(ten)
        self.txt_sdt.setText(sdt)
        self.txt_mail.setText(mail)
        self.txt_note.setText(note)

    def _save(self):
        ten  = self.txt_ten.text().strip()
        if not ten:
            QMessageBox.warning(self, "Thiếu", "Họ tên là bắt buộc!"); return

        if not self.txt_sdt.is_valid():
            QMessageBox.warning(self, "SĐT không hợp lệ",
                "Số điện thoại không hợp lệ!\n"
                "Phải gồm đúng 10 chữ số và đúng đầu số nhà mạng (03x, 05x, 07x, 08x, 09x).")
            self.txt_sdt.setFocus()
            return

        sdt  = self.txt_sdt.text().strip() or None
        mail = self.txt_mail.text().strip() or None
        note = self.txt_note.text().strip() or None

        # ── FIX: luôn dùng session mới, commit, đóng ─────────────
        s = get_session()
        try:
            if self.kh_id:
                # Fetch lại trong session này
                kh = s.query(KhachHang).filter_by(id=self.kh_id).first()
                if not kh:
                    QMessageBox.critical(self, "Lỗi", "Không tìm thấy khách hàng!"); return
            else:
                if sdt and s.query(KhachHang).filter_by(so_dien_thoai=sdt).first():
                    QMessageBox.warning(self, "Trùng SĐT", "Số điện thoại đã tồn tại!"); return
                kh = KhachHang()
                s.add(kh)

            kh.ten_kh        = ten
            kh.so_dien_thoai = sdt
            kh.email         = mail
            kh.ghi_chu       = note
            s.commit()
            self.accept()
        except Exception as e:
            s.rollback()
            QMessageBox.critical(self, "Lỗi DB", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG ĐIỂM: TÍCH hoặc TRỪ
# ═══════════════════════════════════════════════════════════════════════════════
class PointDialog(QDialog):
    """Tích điểm / Cộng điểm thủ công."""
    def __init__(self, kh_id: int, ten_kh: str, diem_hien: int, parent=None):
        super().__init__(parent)
        self.kh_id = kh_id
        self.setWindowTitle(f"⭐ Tích Điểm — {ten_kh}")
        self.resize(360, 210)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20); root.setSpacing(12)
        root.addWidget(_lbl(
            f"⭐ Tích điểm  |  Điểm hiện tại: <b>{diem_hien:,}</b>",
            "#2ECC71", 13, True
        ))

        form = QFormLayout(); form.setSpacing(10)
        self.cb_loai = QComboBox()
        self.cb_loai.addItems(["Tích điểm mua hàng", "Điều chỉnh tăng", "Thưởng điểm"])
        self.sp_diem = QSpinBox()
        self.sp_diem.setRange(1, 999_999); self.sp_diem.setValue(10)
        self.txt_ly  = QLineEdit(); self.txt_ly.setPlaceholderText("Ghi chú thêm…")
        form.addRow(_fl("Loại:"),     self.cb_loai)
        form.addRow(_fl("Số điểm:"),  self.sp_diem)
        form.addRow(_fl("Ghi chú:"),  self.txt_ly)
        root.addLayout(form)

        btn = _btn("✅  Cộng điểm", "#27AE60", 44)
        btn.clicked.connect(self._save)
        root.addWidget(btn)

    def _save(self):
        diem = self.sp_diem.value()
        loai = self.cb_loai.currentText()
        ly   = self.txt_ly.text().strip() or loai
        s = get_session()
        try:
            kh = s.query(KhachHang).filter_by(id=self.kh_id).first()
            if not kh:
                QMessageBox.critical(self, "Lỗi", "Không tìm thấy khách hàng!"); return
            kh.diem_tich_luy   = (kh.diem_tich_luy or 0) + diem
            kh.hang_thanh_vien = tinh_hang(kh.tong_chi_tieu or 0)
            s.add(LichSuDiemKH(ma_kh=self.kh_id, loai="Tích điểm",
                                so_diem=diem, mo_ta=f"{loai}: {ly}"))
            s.commit(); self.accept()
        except Exception as e:
            s.rollback(); QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG ĐỔI ĐIỂM — chọn KM đổi điểm, xem preview ưu đãi
# ═══════════════════════════════════════════════════════════════════════════════
class RedeemDialog(QDialog):
    """
    Đổi điểm tích lũy lấy ưu đãi.
    Hiển thị danh sách KM loại 'DoiDiem' còn hiệu lực,
    cho phép chọn và xác nhận đổi (trừ điểm + ghi log).
    """
    def __init__(self, kh_id: int, ten_kh: str, diem_hien: int, parent=None):
        super().__init__(parent)
        self.kh_id     = kh_id
        self.diem_hien = diem_hien
        self.setWindowTitle(f"🎁 Đổi Điểm — {ten_kh}")
        self.resize(680, 520)
        self.setStyleSheet(STYLE + """
            QFrame#card { background:#252538; border-radius:10px;
                border:1px solid #3E3E55; }
            QFrame#card:hover { border-color:#E67E22; }
            QListWidget { background:#2D2D3F; border:1px solid #3E3E55;
                border-radius:8px; color:white; font-size:13px; }
            QListWidget::item { padding:10px 12px; border-bottom:1px solid #3E3E55; }
            QListWidget::item:selected { background:#E67E22; color:white; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18); root.setSpacing(12)

        # ── Tiêu đề + điểm hiện tại ─────────────────────────────
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl("🎁  ĐỔI ĐIỂM TÍCH LŨY", "#E67E22", 15, True))
        hdr.addStretch()
        self.lbl_diem = _lbl(
            f"Điểm hiện có: <b style='color:#F1C40F;font-size:18px;'>"
            f"{diem_hien:,}</b> điểm",
            "white", 13
        )
        self.lbl_diem.setTextFormat(Qt.RichText)
        hdr.addWidget(self.lbl_diem)
        root.addLayout(hdr)

        # ── Splitter: trái = danh sách KM | phải = preview ──────
        from PySide6.QtWidgets import QSplitter, QListWidget, QListWidgetItem, QScrollArea
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle{background:#3E3E55;}")

        # Trái: lọc + danh sách
        left = QWidget(); left.setStyleSheet("background:transparent;")
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,6,0); lv.setSpacing(8)

        # Thanh lọc
        from PySide6.QtWidgets import QLineEdit as _LE
        self.txt_search = _LE()
        self.txt_search.setPlaceholderText("🔍 Tìm khuyến mãi...")
        self.txt_search.textChanged.connect(self._filter_list)
        lv.addWidget(self.txt_search)

        lv.addWidget(_lbl("Chọn ưu đãi muốn đổi:", "#A1A1AA", 12))
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        self.lst = QListWidget()
        self.lst.currentRowChanged.connect(self._on_select)
        lv.addWidget(self.lst)
        splitter.addWidget(left)

        # Phải: preview card
        right = QWidget(); right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right); rv.setContentsMargins(6,0,0,0); rv.setSpacing(10)
        rv.addWidget(_lbl("👁  XEM TRƯỚC", "#A1A1AA", 11, True))

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview.setWordWrap(True)
        self.preview.setTextFormat(Qt.RichText)
        self.preview.setStyleSheet(
            "background:#1A1A2A;border-radius:10px;"
            "border:1px solid #3E3E55;padding:16px;"
            "color:white;font-size:13px;"
        )
        self.preview.setMinimumHeight(200)
        rv.addWidget(self.preview)

        # Nhập điểm thủ công (hiện khi diem_can = 0)
        self._diem_manual_row = QWidget()
        self._diem_manual_row.setStyleSheet("background:transparent;")
        dr = QHBoxLayout(self._diem_manual_row)
        dr.setContentsMargins(0,0,0,0); dr.setSpacing(8)
        dr.addWidget(_lbl("Số điểm trừ:", "#A1A1AA", 12))
        self.sp_diem_manual = QSpinBox()
        self.sp_diem_manual.setRange(0, 999_999)
        self.sp_diem_manual.setValue(0)
        self.sp_diem_manual.setSuffix(" điểm")
        self.sp_diem_manual.setSpecialValueText("Không trừ điểm")
        self.sp_diem_manual.setStyleSheet(
            "background:#2D2D3F;border:1px solid #3E3E55;border-radius:6px;"
            "padding:6px 10px;color:white;font-size:13px;"
        )
        self.sp_diem_manual.setMaximum(diem_hien)
        self.sp_diem_manual.valueChanged.connect(self._on_manual_diem_changed)
        dr.addWidget(self.sp_diem_manual)
        self._diem_manual_row.setVisible(False)
        rv.addWidget(self._diem_manual_row)

        # Ghi chú thêm
        rv.addWidget(_lbl("Ghi chú (tuỳ chọn):", "#A1A1AA", 11))
        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("VD: Khách đổi quà sinh nhật...")
        rv.addWidget(self.txt_note)
        rv.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([310, 310])
        root.addWidget(splitter, stretch=1)

        # ── Nút xác nhận ────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = _btn("✖ Hủy", "#555577", 44)
        btn_cancel.clicked.connect(self.reject)
        self.btn_redeem = _btn("🎁  Xác nhận đổi điểm", "#E67E22", 44)
        self.btn_redeem.setEnabled(False)
        self.btn_redeem.clicked.connect(self._confirm)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_redeem)
        root.addLayout(btn_row)

        # Load dữ liệu
        self._kms: list = []
        self._filtered: list = []
        self._sel_km = None
        self._load_kms()

    def _load_kms(self):
        """Load tất cả KM đổi điểm còn hiệu lực."""
        from database.models import KhuyenMai
        from datetime import date as _date
        s = get_session()
        try:
            today = _date.today()
            all_kms = s.query(KhuyenMai).filter(
                KhuyenMai.trang_thai == "Đang chạy"
            ).all()

            result = []
            for km in all_kms:
                # ── CHỈ lấy KM đổi điểm (la_doi_diem = 1) ──────────
                if not int(getattr(km, 'la_doi_diem', 0) or 0):
                    continue   # bỏ qua KM chung

                # Kiểm tra ngày
                if km.ngay_bat_dau and km.ngay_bat_dau > today: continue
                if km.ngay_ket_thuc and km.ngay_ket_thuc < today: continue
                # Kiểm tra lượt dùng
                if km.so_luot_toi_da and (km.so_luot_da_dung or 0) >= km.so_luot_toi_da:
                    continue

                diem_can = int(getattr(km, 'diem_can', 0) or 0)
                result.append({
                    "km":       km,
                    "id":       km.id,
                    "ten":      km.ten_km or "—",
                    "mo_ta":    getattr(km, 'mo_ta', '') or "",
                    "diem_can": diem_can,
                    "kieu":     km.kieu_giam or "",
                    "gia_tri":  float(km.gia_tri_giam or 0),
                    "tran":     float(km.toi_da_giam or 0) if km.toi_da_giam else None,
                    "loai_km":  km.loai_km or "DonHang",
                    "gio_tu":   getattr(km, 'gio_tu', None),
                    "gio_den":  getattr(km, 'gio_den', None),
                    "uu_tien":  int(getattr(km, 'uu_tien', 0) or 0),
                })
            # Sắp xếp: diem_can thấp lên trước (dễ đổi hơn), rồi uu_tien
            result.sort(key=lambda x: (x["diem_can"] if x["diem_can"] > 0 else 999_999,
                                        -x["uu_tien"], x["ten"]))
            self._kms = result
        finally:
            s.close()

        self._filtered = self._kms[:]
        self._rebuild_list()

    def _rebuild_list(self):
        self.lst.blockSignals(True)
        self.lst.clear()
        for d in self._filtered:
            du_diem = self.diem_hien >= d["diem_can"] if d["diem_can"] > 0 else True
            icon = "✅" if du_diem else "🔒"
            diem_str = f"  —  cần {d['diem_can']:,} điểm" if d["diem_can"] > 0 else "  —  không cần điểm"
            if d["kieu"] == "PhanTram":
                uu_dai = f"Giảm {int(d['gia_tri'])}%"
            elif d["kieu"] == "TienMat":
                uu_dai = f"Giảm {int(d['gia_tri']):,}đ"
            elif d["loai_km"] == "MuaXTangY":
                uu_dai = "Mua X Tặng Y"
            else:
                uu_dai = "Ưu đãi đặc biệt"
            from PySide6.QtWidgets import QListWidgetItem
            it = QListWidgetItem(f"{icon}  {d['ten']}\n     {uu_dai}{diem_str}")
            it.setData(Qt.UserRole, d)
            if not du_diem:
                it.setForeground(QColor("#7070A0"))
            self.lst.addItem(it)
        self.lst.blockSignals(False)
        # Auto-select first item → trigger preview
        if self.lst.count() > 0:
            self.lst.setCurrentRow(0)
            self._on_select(0)
        else:
            self._sel_km = None
            self.preview.setText(
                "<div style='color:#7070A0;text-align:center;padding:40px;'>"
                "⚠️ Chưa có chương trình đổi điểm nào.<br><br>"
                "<span style='font-size:12px;'>Vào <b>Quản lý Khuyến Mãi</b> → "
                "chọn loại <b>🔢 Đổi Điểm</b> để tạo chương trình.</span>"
                "</div>"
            )
            self.btn_redeem.setEnabled(False)

    def _filter_list(self, text: str):
        kw = text.strip().lower()
        self._filtered = [
            d for d in self._kms
            if kw in d["ten"].lower() or kw in d["mo_ta"].lower()
        ] if kw else self._kms[:]
        self._rebuild_list()

    def _on_manual_diem_changed(self, val: int):
        """Cập nhật preview khi thay số điểm thủ công."""
        if self._sel_km:
            self._update_preview(self._sel_km)

    def _on_select(self, row: int):
        if row < 0 or row >= self.lst.count():
            self._sel_km = None
            self.preview.setText("")
            self.btn_redeem.setEnabled(False)
            self._diem_manual_row.setVisible(False)
            return

        it = self.lst.item(row)
        if not it:
            return
        d = it.data(Qt.UserRole)
        self._sel_km = d

        # Hiện/ẩn ô nhập điểm thủ công
        need_manual = (d["diem_can"] == 0)
        self._diem_manual_row.setVisible(need_manual)
        if need_manual:
            self.sp_diem_manual.setMaximum(self.diem_hien)

        self._update_preview(d)
        du_diem = self.diem_hien >= d["diem_can"] if d["diem_can"] > 0 else True
        self.btn_redeem.setEnabled(du_diem)
        if d["diem_can"] > 0:
            self.btn_redeem.setText(f"🎁  Đổi {d['diem_can']:,} điểm")
        elif self.sp_diem_manual.value() > 0:
            self.btn_redeem.setText(f"🎁  Trừ {self.sp_diem_manual.value():,} điểm")
        else:
            self.btn_redeem.setText("🎁  Áp dụng ưu đãi")

    def _update_preview(self, d: dict):
        # Số điểm thực sự sẽ trừ
        diem_tru_thuc = d["diem_can"] if d["diem_can"] > 0 else (
            self.sp_diem_manual.value() if hasattr(self, 'sp_diem_manual') else 0
        )
        du_diem = self.diem_hien >= d["diem_can"] if d["diem_can"] > 0 else True
        status_color = "#2ECC71" if du_diem else "#E74C3C"
        status_text  = "✅ Đủ điểm" if du_diem else f"❌ Thiếu {d['diem_can'] - self.diem_hien:,} điểm"

        if d["kieu"] == "PhanTram":
            uu_dai_html = f"<b style='color:#E74C3C;font-size:22px;'>{int(d['gia_tri'])}% OFF</b>"
            if d["tran"]:
                uu_dai_html += f"<br><span style='color:#F39C12;font-size:12px;'>Tối đa {int(d['tran']):,}đ</span>"
        elif d["kieu"] == "TienMat":
            uu_dai_html = f"<b style='color:#E74C3C;font-size:22px;'>−{int(d['gia_tri']):,}đ</b>"
        elif d["loai_km"] == "MuaXTangY":
            uu_dai_html = "<b style='color:#2ECC71;font-size:16px;'>🎁 Mua X Tặng Y</b>"
        else:
            uu_dai_html = "<b style='color:#3498DB;'>Ưu đãi đặc biệt</b>"

        if d["diem_can"] > 0:
            con_lai = self.diem_hien - d["diem_can"]
            diem_html = f"""
            <div style='background:#1A1A2E;border-radius:6px;padding:8px 12px;margin:8px 0;'>
              🔢 Điểm cần dùng: <b style='color:#F1C40F;font-size:16px;'>{d['diem_can']:,}</b> điểm<br>
              📊 Điểm hiện có: <b>{self.diem_hien:,}</b> điểm<br>
              💳 Còn lại sau đổi: <b style='color:{"#2ECC71" if con_lai >= 0 else "#E74C3C"};'>
                {max(0, con_lai):,}</b> điểm
            </div>"""
        elif diem_tru_thuc > 0:
            con_lai = self.diem_hien - diem_tru_thuc
            diem_html = f"""
            <div style='background:#1A1A2E;border-radius:6px;padding:8px 12px;margin:8px 0;'>
              🔢 Điểm sẽ trừ: <b style='color:#F1C40F;font-size:16px;'>{diem_tru_thuc:,}</b> điểm<br>
              📊 Điểm hiện có: <b>{self.diem_hien:,}</b> điểm<br>
              💳 Còn lại sau đổi: <b style='color:#2ECC71;'>{max(0, con_lai):,}</b> điểm
            </div>"""
        else:
            diem_html = f"""
            <div style='background:#1A1A2E;border-radius:6px;padding:8px 12px;margin:8px 0;'>
              📊 Điểm hiện có: <b>{self.diem_hien:,}</b> điểm<br>
              <span style='color:#A1A1AA;font-size:12px;'>Nhập số điểm muốn dùng ở ô bên dưới (0 = không trừ điểm)</span>
            </div>"""

        gio_html = ""
        if d["gio_tu"] and d["gio_den"]:
            gio_html = f"<br>🕐 Happy Hour: <b>{d['gio_tu'].strftime('%H:%M')}–{d['gio_den'].strftime('%H:%M')}</b>"

        mo_ta_html = (
            f"<p style='color:#A1A1AA;font-size:12px;margin:4px 0;'>{d['mo_ta']}</p>"
            if d["mo_ta"] else ""
        )

        html = f"""
        <div style='font-family:sans-serif;'>
          <b style='font-size:15px;color:#E8E8F0;'>{d['ten']}</b><br>
          {mo_ta_html}
          <div style='text-align:center;padding:12px 0;'>
            {uu_dai_html}
          </div>
          {diem_html}
          <span style='color:{status_color};font-weight:bold;font-size:13px;'>{status_text}</span>
          {gio_html}
        </div>
        """
        self.preview.setText(html)

    def _confirm(self):
        d = self._sel_km
        if not d:
            return

        # Xác định số điểm thực sự trừ
        if d["diem_can"] > 0:
            diem_tru = d["diem_can"]
        else:
            diem_tru = self.sp_diem_manual.value()  # 0 = không trừ điểm

        note = self.txt_note.text().strip()
        ten  = d["ten"]

        # Kiểm tra đủ điểm
        if diem_tru > 0 and self.diem_hien < diem_tru:
            QMessageBox.warning(
                self, "Không đủ điểm",
                f"Khách chỉ có {self.diem_hien:,} điểm, cần {diem_tru:,} điểm!"
            ); return

        # Xác nhận
        if diem_tru > 0:
            msg = (f"Xác nhận trừ <b>{diem_tru:,} điểm</b> của khách để nhận:<br><br>"
                   f"🎁 <b>{ten}</b>")
        else:
            msg = f"Áp dụng ưu đãi <b>{ten}</b> cho khách (không trừ điểm)?"
        if QMessageBox.question(
            self, "Xác nhận đổi điểm", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return

        s = get_session()
        try:
            kh = s.query(KhachHang).filter_by(id=self.kh_id).first()
            if not kh:
                QMessageBox.critical(self, "Lỗi", "Không tìm thấy khách hàng!"); return

            if diem_tru > 0:
                if (kh.diem_tich_luy or 0) < diem_tru:
                    QMessageBox.warning(
                        self, "Không đủ điểm",
                        f"Khách chỉ còn {kh.diem_tich_luy or 0:,} điểm!"
                    ); return
                kh.diem_tich_luy = (kh.diem_tich_luy or 0) - diem_tru

            kh.hang_thanh_vien = tinh_hang(kh.tong_chi_tieu or 0)

            mo_ta = f"Đổi điểm: {ten}"
            if note: mo_ta += f" — {note}"
            s.add(LichSuDiemKH(
                ma_kh=self.kh_id,
                loai="Đổi điểm",
                so_diem=-diem_tru if diem_tru > 0 else 0,
                mo_ta=mo_ta,
            ))

            # Cập nhật lượt dùng KM
            from database.models import KhuyenMai
            km_obj = s.get(KhuyenMai, d["id"])
            if km_obj:
                km_obj.so_luot_da_dung = (km_obj.so_luot_da_dung or 0) + 1

            s.commit()
            QMessageBox.information(
                self, "✅ Thành công",
                f"Đã đổi {'<b>' + str(diem_tru) + '</b> điểm' if diem_tru > 0 else 'ưu đãi'} "
                f"cho khách!\n\nƯu đãi: {ten}\n"
                f"Điểm còn lại: {kh.diem_tich_luy:,}"
            )
            self.accept()
        except Exception as e:
            s.rollback(); QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG PHÁT VOUCHER — chỉ hiển thị KM loại Voucher Riêng (CaNhan)
# ═══════════════════════════════════════════════════════════════════════════════
class IssueVoucherDialog(QDialog):
    """
    Phát voucher riêng cho khách.
    Chỉ hiển thị KM loại 'CaNhan' đang chạy.
    Tạo từ KM → đồng bộ với hệ thống khuyến mãi.
    """
    def __init__(self, kh_id: int, ten_kh: str, parent=None):
        super().__init__(parent)
        self.kh_id   = kh_id
        self.ten_kh  = ten_kh
        self._km_data: list = []
        self._sel_km: dict | None = None

        self.setWindowTitle(f"🎁 Phát Voucher — {ten_kh}")
        self.resize(660, 520)
        self.setStyleSheet(STYLE + """
            QListWidget { background:#2D2D3F; border:1px solid #3E3E55;
                border-radius:8px; color:white; font-size:13px; }
            QListWidget::item { padding:10px 12px; border-bottom:1px solid #3E3E55; }
            QListWidget::item:selected { background:#27AE60; color:white; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18); root.setSpacing(10)

        # ── Header ──────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl("🎁  PHÁT VOUCHER", "#8E44AD", 15, True))
        hdr.addStretch()
        hdr.addWidget(_lbl(f"Khách: {ten_kh}", "#A1A1AA", 12))
        root.addLayout(hdr)

        # ── Nội dung: Chọn Voucher Riêng ────────────────────────
        from PySide6.QtWidgets import QSplitter
        content_w = QWidget(); content_w.setStyleSheet("background:transparent;")
        vkm = QVBoxLayout(content_w); vkm.setContentsMargins(0, 0, 0, 0); vkm.setSpacing(8)

        vkm.addWidget(_lbl(
            "Chọn voucher riêng để phát cho khách này.",
            "#A1A1AA", 12
        ))

        # Splitter: trái = list KM | phải = preview
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle{background:#3E3E55;}")

        left_w = QWidget(); left_w.setStyleSheet("background:transparent;")
        lv = QVBoxLayout(left_w); lv.setContentsMargins(0,0,4,0); lv.setSpacing(6)
        lv.addWidget(_lbl("Voucher Riêng đang chạy:", "#A1A1AA", 11))

        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        self.lst_km = QListWidget()
        self.lst_km.currentRowChanged.connect(self._on_km_row_changed)
        lv.addWidget(self.lst_km)

        # Hạn sử dụng voucher sẽ phát
        het_row = QHBoxLayout()
        het_row.addWidget(_lbl("Hạn sử dụng voucher:", "#A1A1AA", 11))
        self.de_het_km = QDateEdit(QDate.currentDate().addDays(30))
        self.de_het_km.setCalendarPopup(True)
        self.de_het_km.setDisplayFormat("dd/MM/yyyy")
        het_row.addWidget(self.de_het_km)
        lv.addLayout(het_row)
        splitter.addWidget(left_w)

        right_w = QWidget(); right_w.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right_w); rv.setContentsMargins(4,0,0,0); rv.setSpacing(8)
        rv.addWidget(_lbl("👁  Xem trước:", "#A1A1AA", 11, True))
        self.preview_km = QLabel()
        self.preview_km.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview_km.setWordWrap(True)
        self.preview_km.setTextFormat(Qt.RichText)
        self.preview_km.setStyleSheet(
            "background:#1A1A2A;border-radius:10px;border:1px solid #3E3E55;"
            "padding:16px;color:white;font-size:13px;"
        )
        self.preview_km.setMinimumHeight(180)
        rv.addWidget(self.preview_km, stretch=1)
        splitter.addWidget(right_w)
        splitter.setSizes([300, 300])
        vkm.addWidget(splitter, stretch=1)

        root.addWidget(content_w, stretch=1)

        # ── Nút ─────────────────────────────────────────────────
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_cancel = _btn("✖ Hủy", "#555577", 44)
        btn_cancel.clicked.connect(self.reject)
        self.btn_issue = _btn("🎁  Phát Voucher", "#27AE60", 44)
        self.btn_issue.clicked.connect(self._issue)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_issue)
        root.addLayout(btn_row)

        self._load_kms()

    def _load_kms(self):
        """Load KM loại 'CaNhan' đang chạy để phát voucher riêng."""
        from database.models import KhuyenMai
        from datetime import date as _date
        s = get_session()
        try:
            today = _date.today()
            kms = s.query(KhuyenMai).filter(
                KhuyenMai.trang_thai == "Đang chạy"
            ).all()
            result = []
            for km in kms:
                nhom = getattr(km, 'loai_nhom', 'Chung') or 'Chung'
                # Chỉ lấy CaNhan — bỏ Chung và DoiDiem
                if nhom != 'CaNhan':
                    continue
                if km.ngay_bat_dau and km.ngay_bat_dau > today: continue
                if km.ngay_ket_thuc and km.ngay_ket_thuc < today: continue
                if km.loai_km == "MuaXTangY": continue
                if km.kieu_giam == "PhanTram":
                    uu_dai = f"Giảm {int(km.gia_tri_giam or 0)}%"
                    if km.toi_da_giam:
                        uu_dai += f" (tối đa {int(km.toi_da_giam):,}đ)"
                else:
                    uu_dai = f"Giảm {int(km.gia_tri_giam or 0):,}đ"
                dk_min = float(km.dk_tong_tien_tu or 0)
                result.append({
                    "id":      km.id,
                    "ten":     km.ten_km or "—",
                    "mo_ta":   getattr(km, 'mo_ta', '') or "",
                    "nhom":    nhom,
                    "kieu":    km.kieu_giam or "TienMat",
                    "gia_tri": float(km.gia_tri_giam or 0),
                    "tran":    float(km.toi_da_giam or 0) if km.toi_da_giam else None,
                    "dk_min":  dk_min,
                    "uu_dai":  uu_dai,
                    "het_km":  km.ngay_ket_thuc,
                })
            result.sort(key=lambda x: x["ten"])
            self._km_data = result
        finally:
            s.close()

        from PySide6.QtWidgets import QListWidgetItem
        self.lst_km.clear()
        if not result:
            it = QListWidgetItem("— Chưa có Voucher Riêng nào đang chạy —")
            it.setForeground(QColor("#A1A1AA"))
            it.setFlags(Qt.ItemIsEnabled)
            self.lst_km.addItem(it)
            self.preview_km.setText(
                "<div style='color:#7070A0;padding:30px;text-align:center;'>"
                "Hãy tạo KM loại <b>Voucher Riêng</b> trong<br>"
                "Quản lý Khuyến Mãi → chip <b>👤 Voucher Riêng</b> trước.</div>"
            )
            return
        for d in result:
            dk_str = f"  ·  Đơn ≥{int(d['dk_min']):,}đ" if d["dk_min"] else ""
            it = QListWidgetItem(f"  👤  {d['ten']}  —  {d['uu_dai']}{dk_str}")
            it.setForeground(QColor("#27AE60"))
            it.setData(Qt.UserRole, d)
            self.lst_km.addItem(it)
        self.lst_km.setCurrentRow(0)

    def _on_km_row_changed(self, row: int):
        if row < 0 or row >= len(self._km_data):
            self._sel_km = None
            return
        d = self._km_data[row]
        self._sel_km = d

        # Tự điền hạn = hạn KM hoặc 30 ngày
        if d["het_km"]:
            self.de_het_km.setDate(QDate(d["het_km"].year, d["het_km"].month, d["het_km"].day))

        # Preview
        mo_ta_html = (f"<p style='color:#A1A1AA;font-size:12px;margin:4px 0;'>{d['mo_ta']}</p>"
                      if d["mo_ta"] else "")
        if d["kieu"] == "PhanTram":
            uu_html = f"<b style='color:#E74C3C;font-size:24px;'>{int(d['gia_tri'])}% OFF</b>"
            if d["tran"]:
                uu_html += f"<br><span style='color:#F39C12;font-size:12px;'>Tối đa {int(d['tran']):,}đ</span>"
        else:
            uu_html = f"<b style='color:#E74C3C;font-size:22px;'>−{int(d['gia_tri']):,}đ</b>"

        dk_html = (
            f"<div style='background:#1A1A2E;border-radius:6px;padding:8px 12px;margin:8px 0;"
            f"font-size:12px;'>Đơn tối thiểu: <b>{int(d['dk_min']):,}đ</b></div>"
            if d["dk_min"] else ""
        )
        code_preview = gen_code()
        self.preview_km.setText(f"""
        <div style='font-family:sans-serif;'>
            <b style='font-size:14px;color:#E8E8F0;'>{d['ten']}</b><br>
            {mo_ta_html}
            <div style='text-align:center;padding:10px 0;'>{uu_html}</div>
            {dk_html}
            <div style='background:#2A1A3A;border-radius:6px;padding:8px 12px;font-size:12px;'>
              Voucher sẽ tạo:<br>
              Mã: <b style='color:#F1C40F;font-family:monospace;'>{code_preview}</b><br>
              Khách: <b style='color:#A569BD;'>{self.ten_kh}</b>
            </div>
        </div>
        """)

    def _issue(self):
        if not self._sel_km:
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn một Voucher Riêng!"); return
        d = self._sel_km
        qd = self.de_het_km.date()
        het = date(qd.year(), qd.month(), qd.day())
        s = get_session()
        try:
            code = gen_code()
            v = Voucher(
                ma_kh=self.kh_id,
                ma_code=code,
                ten_voucher=d["ten"],
                loai_giam=d["kieu"],
                gia_tri_giam=d["gia_tri"],
                toi_da_giam=d["tran"],
                dieu_kien_toi_thieu=d["dk_min"] or 0,
                ngay_het_han=het,
            )
            try:
                v.ma_km = d["id"]
            except Exception:
                pass
            s.add(v); s.commit()
            QMessageBox.information(
                self, "✅ Thành công",
                f"Đã phát voucher [{d['ten']}]!\n"
                f"Mã: {code}\n"
                f"Ưu đãi: {d['uu_dai']}\n"
                f"Hạn dùng: {het.strftime('%d/%m/%Y')}"
            )
            self.accept()
        except Exception as e:
            s.rollback(); QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG LỊCH SỬ ĐIỂM
# ═══════════════════════════════════════════════════════════════════════════════
class PointHistoryDialog(QDialog):
    def __init__(self, kh_id: int, ten_kh: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Lịch Sử Điểm — {ten_kh}")
        self.resize(600, 400); self.setStyleSheet(STYLE)

        root = QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Thời Gian", "Loại", "Số Điểm", "Ghi Chú"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)

        btn = _btn("Đóng", "#34495E", 38); btn.clicked.connect(self.accept)
        root.addWidget(btn)

        self._load(kh_id)

    def _load(self, kh_id):
        s = get_session()
        try:
            logs = (s.query(LichSuDiemKH)
                    .filter_by(ma_kh=kh_id)
                    .order_by(LichSuDiemKH.thoi_gian.desc())
                    .limit(200).all())
            for i, log in enumerate(logs):
                self.table.insertRow(i)
                tg = log.thoi_gian.strftime("%H:%M  %d/%m/%Y") if log.thoi_gian else "—"
                self.table.setItem(i, 0, QTableWidgetItem(tg))
                self.table.setItem(i, 1, QTableWidgetItem(log.loai or ""))

                diem_str = f"+{log.so_diem}" if (log.so_diem or 0) > 0 else str(log.so_diem or 0)
                di = QTableWidgetItem(diem_str)
                di.setForeground(QColor("#2ECC71" if (log.so_diem or 0) > 0 else "#E74C3C"))
                self.table.setItem(i, 2, di)
                self.table.setItem(i, 3, QTableWidgetItem(log.mo_ta or ""))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH
# ═══════════════════════════════════════════════════════════════════════════════
class CustomerManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("👥 Quản Lý Khách Hàng Thành Viên")
        self.resize(1080, 660); self.setStyleSheet(STYLE)

        root = QVBoxLayout(self); root.setContentsMargins(10, 10, 10, 10)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._make_list_tab(),    "📋  Danh Sách")
        self.tabs.addTab(self._make_voucher_tab(), "🎁  Voucher")
        root.addWidget(self.tabs)

        btn = _btn("Đóng", "#34495E", 40); btn.clicked.connect(self.accept)
        root.addWidget(btn)

        self.tabs.currentChanged.connect(self._on_tab)

    def showEvent(self, e):
        super().showEvent(e); self._load_kh()

    # ── Tab Danh sách ────────────────────────────────────────────
    def _make_list_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setSpacing(8)

        # Toolbar
        bar = QHBoxLayout()
        bar.addWidget(_lbl("THÀNH VIÊN", "#3498DB", 16, True)); bar.addStretch()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Tên / SĐT  (Enter = thêm mới nếu chưa có)")
        self.txt_search.setFixedWidth(290)
        self.txt_search.textChanged.connect(lambda t: self._load_kh(t))
        self.txt_search.returnPressed.connect(self._search_or_add)
        bar.addWidget(self.txt_search)

        self.btn_add     = _btn("➕ Thêm",     "#27AE60")
        self.btn_edit    = _btn("✏️ Sửa",      "#2980B9")
        self.btn_add_pt  = _btn("⭐ Cộng điểm","#27AE60")
        self.btn_deduct  = _btn("🎁 Đổi điểm", "#E67E22")   # đổi điểm lấy KM
        self.btn_vc      = _btn("🎁 Voucher",  "#8E44AD")
        self.btn_hist    = _btn("📋 Lịch sử",  "#16A085")
        self.btn_del     = _btn("🗑 Xóa",      "#C0392B")

        for b in [self.btn_add, self.btn_edit, self.btn_add_pt,
                  self.btn_deduct, self.btn_vc, self.btn_hist, self.btn_del]:
            bar.addWidget(b)
        v.addLayout(bar)

        # Bảng
        self.tbl_kh = QTableWidget(0, 7)
        self.tbl_kh.setHorizontalHeaderLabels(
            ["ID", "Họ Tên", "SĐT", "Hạng", "Điểm", "Tổng Chi Tiêu", "Ngày Tham Gia"])
        hh = self.tbl_kh.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed); self.tbl_kh.setColumnWidth(0, 40)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in range(2, 7): hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tbl_kh.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_kh.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_kh.verticalHeader().setVisible(False)
        self.tbl_kh.itemDoubleClicked.connect(lambda _: self._edit_kh())
        v.addWidget(self.tbl_kh)

        # Kết nối
        self.btn_add.clicked.connect(self._add_kh)
        self.btn_edit.clicked.connect(self._edit_kh)
        self.btn_add_pt.clicked.connect(lambda: self._open_points('add'))
        self.btn_deduct.clicked.connect(lambda: self._open_points('deduct'))
        self.btn_vc.clicked.connect(self._issue_voucher)
        self.btn_hist.clicked.connect(self._show_history)
        self.btn_del.clicked.connect(self._del_kh)
        return w

    def _search_or_add(self):
        kw = self.txt_search.text().strip()
        if self.tbl_kh.rowCount() > 0:
            self.tbl_kh.selectRow(0)
        else:
            if CustomerForm(ten_mac_dinh=kw, parent=self).exec():
                self.txt_search.clear()
                self._load_kh()

    def _load_kh(self, keyword=""):
        self.tbl_kh.setRowCount(0)
        s = get_session()
        try:
            q = s.query(KhachHang)
            if keyword:
                q = q.filter(
                    KhachHang.ten_kh.ilike(f"%{keyword}%") |
                    KhachHang.so_dien_thoai.ilike(f"%{keyword}%")
                )
            rows = []
            for kh in q.order_by(KhachHang.id.desc()).all():
                rows.append({
                    "id": kh.id, "ten": kh.ten_kh or "",
                    "sdt": kh.so_dien_thoai or "—",
                    "hang": kh.hang_thanh_vien or "Đồng",
                    "diem": kh.diem_tich_luy or 0,
                    "chi_tieu": kh.tong_chi_tieu or 0,
                    "ngay": kh.ngay_tham_gia.strftime("%d/%m/%Y") if kh.ngay_tham_gia else "—",
                })
        finally:
            s.close()  # đóng session trước khi đổ vào UI

        for i, r in enumerate(rows):
            self.tbl_kh.insertRow(i)
            id_it = QTableWidgetItem(str(r["id"])); id_it.setData(Qt.UserRole, r["id"])
            self.tbl_kh.setItem(i, 0, id_it)
            self.tbl_kh.setItem(i, 1, QTableWidgetItem(r["ten"]))
            self.tbl_kh.setItem(i, 2, QTableWidgetItem(r["sdt"]))

            hi = QTableWidgetItem(f"⭐ {r['hang']}")
            hi.setForeground(QColor(mau_hang(r["hang"])))
            self.tbl_kh.setItem(i, 3, hi)

            di = QTableWidgetItem(f"{r['diem']:,} điểm")
            di.setForeground(QColor("#F1C40F"))
            self.tbl_kh.setItem(i, 4, di)

            ti = QTableWidgetItem(f"{int(r['chi_tieu']):,} đ")
            ti.setForeground(QColor("#2ECC71"))
            self.tbl_kh.setItem(i, 5, ti)

            self.tbl_kh.setItem(i, 6, QTableWidgetItem(r["ngay"]))

    def _sel_id(self):
        r = self.tbl_kh.currentRow()
        if r < 0:
            QMessageBox.information(self, "", "Hãy chọn một khách hàng!"); return None
        return self.tbl_kh.item(r, 0).data(Qt.UserRole)

    def _sel_ten(self):
        r = self.tbl_kh.currentRow()
        return self.tbl_kh.item(r, 1).text() if r >= 0 else ""

    def _sel_diem(self) -> int:
        r = self.tbl_kh.currentRow()
        if r < 0: return 0
        txt = self.tbl_kh.item(r, 4).text().replace(",", "").replace(" điểm", "").strip()
        try: return int(txt)
        except: return 0

    def _add_kh(self):
        if CustomerForm(parent=self).exec(): self._load_kh()

    def _edit_kh(self):
        kid = self._sel_id()
        if kid is None: return
        if CustomerForm(kh_id=kid, parent=self).exec():
            self._load_kh()

    def _open_points(self, mode: str):
        kid = self._sel_id()
        if kid is None: return
        if mode == 'add':
            if PointDialog(kid, self._sel_ten(), self._sel_diem(), self).exec():
                self._load_kh()
        else:
            if RedeemDialog(kid, self._sel_ten(), self._sel_diem(), self).exec():
                self._load_kh()

    def _issue_voucher(self):
        kid = self._sel_id()
        if kid is None: return
        if IssueVoucherDialog(kid, self._sel_ten(), self).exec():
            self._load_vouchers()

    def _show_history(self):
        kid = self._sel_id()
        if kid is None: return
        PointHistoryDialog(kid, self._sel_ten(), self).exec()

    def _del_kh(self):
        kid = self._sel_id()
        if kid is None: return
        ten = self._sel_ten()
        r = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Xóa khách hàng <b>{ten}</b>?<br>"
            f"<span style='color:#E74C3C;font-size:12px;'>"
            f"Voucher và lịch sử điểm của khách sẽ bị xóa theo.</span>",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r != QMessageBox.Yes: return

        s = get_session()
        try:
            kh = s.query(KhachHang).filter_by(id=kid).first()
            if not kh:
                QMessageBox.warning(self, "Lỗi", "Không tìm thấy khách hàng!"); return

            # ── FIX: xóa thủ công các bảng liên quan trước ────────
            s.query(LichSuDiemKH).filter_by(ma_kh=kid).delete()
            s.query(Voucher).filter_by(ma_kh=kid).delete()
            s.delete(kh)
            s.commit()

            QMessageBox.information(self, "Đã xóa", f"Đã xóa khách hàng '{ten}'.")
        except Exception as e:
            s.rollback()
            QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()

        self._load_kh()

    # ── Tab Voucher ──────────────────────────────────────────────
    def _make_voucher_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setSpacing(8)
        bar = QHBoxLayout()
        bar.addWidget(_lbl("VOUCHER", "#8E44AD", 16, True)); bar.addStretch()
        btn_exp = _btn("❌ Hủy voucher", "#C0392B")
        btn_exp.clicked.connect(self._cancel_voucher)
        bar.addWidget(btn_exp); v.addLayout(bar)

        self.tbl_vc = QTableWidget(0, 7)
        self.tbl_vc.setHorizontalHeaderLabels(
            ["Mã", "Khách Hàng", "Tên Voucher", "Loại", "Giá Trị", "Hết Hạn", "Trạng Thái"])
        hh2 = self.tbl_vc.horizontalHeader()
        hh2.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(1, QHeaderView.Stretch)
        hh2.setSectionResizeMode(2, QHeaderView.Stretch)
        for c in range(3, 7): hh2.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tbl_vc.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_vc.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_vc.verticalHeader().setVisible(False)
        v.addWidget(self.tbl_vc)

        self._load_vouchers()
        return w

    def _load_vouchers(self):
        self.tbl_vc.setRowCount(0)
        s = get_session()
        try:
            rows = []
            for vc in s.query(Voucher).order_by(Voucher.id.desc()).limit(300).all():
                kh = s.query(KhachHang).filter_by(id=vc.ma_kh).first()
                rows.append({
                    "id": vc.id, "code": vc.ma_code,
                    "kh_ten": kh.ten_kh if kh else "?",
                    "ten": vc.ten_voucher or "",
                    "loai": vc.loai_giam or "",
                    "gt": vc.gia_tri_giam or 0,
                    "het": vc.ngay_het_han.strftime("%d/%m/%Y") if vc.ngay_het_han else "—",
                    "tt": vc.trang_thai or "Chưa dùng",
                })
        finally:
            s.close()

        for i, r in enumerate(rows):
            self.tbl_vc.insertRow(i)
            it = QTableWidgetItem(r["code"]); it.setData(Qt.UserRole, r["id"])
            it.setForeground(QColor("#F1C40F")); self.tbl_vc.setItem(i, 0, it)
            self.tbl_vc.setItem(i, 1, QTableWidgetItem(r["kh_ten"]))
            self.tbl_vc.setItem(i, 2, QTableWidgetItem(r["ten"]))
            self.tbl_vc.setItem(i, 3, QTableWidgetItem(r["loai"]))
            gt = f"{int(r['gt'])}%" if r["loai"] == "PhanTram" else f"{int(r['gt']):,}đ"
            self.tbl_vc.setItem(i, 4, QTableWidgetItem(gt))
            self.tbl_vc.setItem(i, 5, QTableWidgetItem(r["het"]))
            tt_it = QTableWidgetItem(r["tt"])
            tt_it.setForeground(QColor(
                {"Chưa dùng": "#2ECC71", "Đã dùng": "#A1A1AA", "Hết hạn": "#E74C3C"}.get(r["tt"], "white")
            ))
            self.tbl_vc.setItem(i, 6, tt_it)

    def _cancel_voucher(self):
        row = self.tbl_vc.currentRow()
        if row < 0:
            QMessageBox.information(self, "", "Hãy chọn voucher!"); return
        vc_id = self.tbl_vc.item(row, 0).data(Qt.UserRole)
        s = get_session()
        try:
            vc = s.query(Voucher).filter_by(id=vc_id).first()
            if vc: vc.trang_thai = "Hết hạn"; s.commit()
        finally: s.close()
        self._load_vouchers()

    def _on_tab(self, idx):
        if idx == 0: self._load_kh()
        elif idx == 1: self._load_vouchers()