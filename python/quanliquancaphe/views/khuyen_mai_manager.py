"""
views/khuyen_mai_manager.py
══════════════════════════════════════════════════════════════════
Quản lý Khuyến Mãi — phiên bản nâng cấp:
  • Validation số điện thoại (trong phần điều kiện KH)
  • Preview KM real-time bên phải
  • Điều kiện theo danh mục sản phẩm
  • Khung giờ Happy Hour (gio_tu → gio_den)
  • Thứ tự ưu tiên hệ thống (uu_tien)
  • Mô tả ngắn (mo_ta)
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
import re
from datetime import date, time as dtime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFormLayout, QLineEdit, QDateEdit, QComboBox,
    QAbstractItemView, QDoubleSpinBox, QSpinBox, QCheckBox, QFrame,
    QScrollArea, QTimeEdit, QTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor, QFont

from database.db_config import get_session
from database.models import KhuyenMai, SanPham, NhatKyKhuyenMai

# ── Auto-migrate: thêm cột mới nếu chưa có ──────────────────────
# Các cột mở rộng (mo_ta, gio_tu, gio_den, loai_nhom, diem_can…)
# đã được khai báo trong models.KhuyenMai — db_config.auto_migrate tự thêm khi khởi động.


STYLE = """
QDialog, QWidget  { background-color: #1A1A2E; color: #E8E8F0; }
QTabWidget::pane  { border: none; background: #1A1A2E; }
QTabBar::tab      { background:#252540; color:#8888AA; padding:10px 22px;
    border-radius:6px 6px 0 0; font-weight:bold; font-size:13px; }
QTabBar::tab:selected { background:#E67E22; color:white; }
QTabBar::tab:hover    { background:#333355; color:white; }
QTableWidget {
    background:#1E1E30; border:none; border-radius:8px;
    gridline-color:transparent; color:#E8E8F0; font-size:13px;
    alternate-background-color:#252540; }
QTableWidget::item {
    background:#1E1E30; color:#E8E8F0;
    padding:8px 10px; border-bottom:1px solid #2A2A45; }
QTableWidget::item:alternate {
    background:#252540; color:#E8E8F0; }
QTableWidget::item:selected {
    background:#8E44AD; color:white; }
QTableWidget::item:selected:alternate {
    background:#8E44AD; color:white; }
QHeaderView::section { background:#13132A; color:#9898B8;
    padding:9px 10px; border:none; border-bottom:2px solid #2A2A45;
    font-weight:bold; font-size:12px; }
QLineEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit {
    background:#252540; border:1px solid #333355; border-radius:6px;
    padding:6px 10px; color:#E8E8F0; font-size:13px; }
QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus { border-color:#E67E22; }
QTextEdit { background:#252540; border:1px solid #333355; border-radius:6px;
    padding:6px 10px; color:#E8E8F0; font-size:13px; }
QComboBox::drop-down { border:none; }
QComboBox QAbstractItemView { background:#252540; color:#E8E8F0;
    selection-background-color:#E67E22; }
QScrollBar:vertical { background:#1A1A2E; width:7px; border-radius:4px; }
QScrollBar::handle:vertical { background:#333355; border-radius:4px; }
QCheckBox { color:#E8E8F0; font-size:13px; }
QCheckBox::indicator { width:16px; height:16px; border-radius:4px;
    border:2px solid #444466; background:#252540; }
QCheckBox::indicator:checked { background:#8E44AD; border-color:#8E44AD; }
QCheckBox::indicator:hover   { border-color:#8E44AD; }
QSplitter::handle { background:#333355; width:2px; }
"""


def _btn(text, color, h=36):
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setStyleSheet(
        f"background:{color};color:white;font-weight:bold;"
        f"border-radius:6px;font-size:13px;padding:0 14px;"
        f"border:none;"
    )
    return b


def _lbl(text, color="#E8E8F0", size=13, bold=False):
    l = QLabel(text)
    l.setStyleSheet(
        f"color:{color};font-size:{size}px;background:transparent;border:none;"
        + ("font-weight:bold;" if bold else "")
    )
    return l


def _section_frame(title: str, color: str = "#E67E22") -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setStyleSheet(
        f"QFrame {{ background:#252540; border-radius:8px; border:1px solid {color}; }}"
    )
    v = QVBoxLayout(f)
    v.setContentsMargins(14, 10, 14, 12)
    v.setSpacing(8)
    v.addWidget(_lbl(title, color, 13, True))
    return f, v


def _validate_sdt(sdt: str) -> tuple[bool, str]:
    """Kiểm tra SĐT Việt Nam: 10 chữ số, đầu là 0."""
    sdt = sdt.strip()
    if not sdt:
        return True, ""   # trống = không bắt buộc
    digits = re.sub(r'\D', '', sdt)
    if len(digits) != 10:
        return False, f"Số điện thoại phải đủ 10 chữ số (hiện có {len(digits)})."
    if not digits.startswith('0'):
        return False, "Số điện thoại phải bắt đầu bằng 0."
    valid_prefixes = ('03', '05', '07', '08', '09')
    if not any(digits.startswith(p) for p in valid_prefixes):
        return False, "Đầu số không hợp lệ (phải là 03x, 05x, 07x, 08x, 09x)."
    return True, ""


# ═══════════════════════════════════════════════════════════════════════════════
# FORM THÊM / SỬA KHUYẾN MÃI — layout trái/phải với Preview
# ═══════════════════════════════════════════════════════════════════════════════
class KhuyenMaiForm(QDialog):
    def __init__(self, km_id=None, parent=None, default_nhom: str = 'Chung'):
        super().__init__(parent)
        self.km_id = km_id
        self._default_nhom = default_nhom
        self.setWindowTitle("✨ Thêm Khuyến Mãi" if not km_id else "✏️ Sửa Khuyến Mãi")
        self.resize(1000, 720)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        root.addWidget(_lbl(
            "THÊM KHUYẾN MÃI" if not km_id else "SỬA KHUYẾN MÃI",
            "#E67E22", 16, True
        ))

        # ── Splitter: trái = form, phải = preview ───────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # ── TRÁI: scroll form ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        form_widget = QWidget()
        form_widget.setStyleSheet("background:transparent;")
        self._form_layout = QVBoxLayout(form_widget)
        self._form_layout.setSpacing(10)
        self._form_layout.setContentsMargins(0, 0, 8, 0)
        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)

        # ── PHẢI: preview ───────────────────────────────────────
        preview_wrap = QFrame()
        preview_wrap.setStyleSheet(
            "QFrame { background:#252540; border-radius:10px; border:1px solid #E67E22; }"
        )
        pv = QVBoxLayout(preview_wrap)
        pv.setContentsMargins(16, 14, 16, 14)
        pv.setSpacing(10)
        pv.addWidget(_lbl("👁 XEM TRƯỚC KHUYẾN MÃI", "#E67E22", 13, True))

        self.preview_card = QLabel()
        self.preview_card.setWordWrap(True)
        self.preview_card.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview_card.setTextFormat(Qt.RichText)
        self.preview_card.setStyleSheet(
            "background:#1A1A2E; border-radius:8px; padding:14px;"
            " color:#E8E8F0; font-size:13px; border:none;"
        )
        self.preview_card.setMinimumHeight(180)
        pv.addWidget(self.preview_card)

        # Thống kê / gợi ý
        self.preview_hint = QLabel()
        self.preview_hint.setWordWrap(True)
        self.preview_hint.setAlignment(Qt.AlignTop)
        self.preview_hint.setTextFormat(Qt.RichText)
        self.preview_hint.setStyleSheet(
            "background:transparent; color:#8888AA; font-size:12px; border:none;"
        )
        pv.addWidget(self.preview_hint)
        pv.addStretch()
        splitter.addWidget(preview_wrap)

        splitter.setSizes([600, 360])
        root.addWidget(splitter, stretch=1)

        # ── Nút lưu ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = _btn("✖ Hủy", "#555577", 44)
        btn_cancel.clicked.connect(self.reject)
        btn_save = _btn("💾  Lưu Khuyến Mãi", "#27AE60", 44)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

        # ── Xây form bên trái ───────────────────────────────────
        self._code_edited       = False
        self._mota_edited       = False
        self._block_code_signal = False
        self._block_mota_signal = False
        self._nhom_hien_tai     = self._default_nhom or 'Chung'  # trạng thái nhóm hiện tại
        self._build_form()
        self._connect_preview()

        if km_id:
            self._load_data()
            self._code_edited = True
            self._mota_edited = True
        else:
            # _select_nhom đã được gọi cuối _build_form với _nhom_hien_tai
            self._update_preview()

        # Detect khi user tự gõ (không phải do auto-fill)
        def _on_code_edited():
            if not self._block_code_signal:
                self._code_edited = True
        def _on_mota_edited():
            if not self._block_mota_signal:
                self._mota_edited = True
        self.txt_code.textEdited.connect(_on_code_edited)
        self.txt_mo_ta.textEdited.connect(_on_mota_edited)

    # ─────────────────────────────────────────────────────────────
    def _build_form(self):
        fl = self._form_layout

        def _fl(t):
            l = QLabel(t); l.setStyleSheet("color:#8888AA; border:none;"); return l

        # ── 1. Thông tin chung ───────────────────────────────────
        sec1, v1 = _section_frame("📋 Thông tin chung")
        f1 = QFormLayout(); f1.setSpacing(8)

        self.txt_ten  = QLineEdit(); self.txt_ten.setPlaceholderText("VD: Giảm 10% cuối tuần")
        self.txt_code = QLineEdit(); self.txt_code.setPlaceholderText("VD: WEEKEND10 (để trống = tự động)")
        self.txt_mo_ta = QLineEdit(); self.txt_mo_ta.setPlaceholderText("Mô tả ngắn hiển thị cho khách...")
        self.cb_tt    = QComboBox(); self.cb_tt.addItems(["Đang chạy", "Tạm dừng"])

        f1.addRow(_fl("Tên KM *:"),     self.txt_ten)
        f1.addRow(_fl("Mô tả ngắn:"),   self.txt_mo_ta)
        f1.addRow(_fl("Mã code:"),       self.txt_code)
        f1.addRow(_fl("Trạng thái:"),    self.cb_tt)
        v1.addLayout(f1)
        fl.addWidget(sec1)

        # ── 2. Loại KM ───────────────────────────────────────────
        sec2, v2 = _section_frame("⚡ Loại & Giảm giá", "#3498DB")
        f2 = QFormLayout(); f2.setSpacing(8)

        self.cb_loai = QComboBox()
        self.cb_loai.addItems(["DonHang", "SanPham", "MuaXTangY"])

        # Sản phẩm / danh mục áp dụng
        self.cb_sp = QComboBox()
        self.cb_sp.addItem("-- Toàn đơn hàng --", None)
        self._load_products(self.cb_sp)

        self.cb_danh_muc = QComboBox()
        self.cb_danh_muc.addItem("-- Tất cả danh mục --", None)
        self._load_categories()

        self.cb_kieu = QComboBox()
        self.cb_kieu.addItems(["PhanTram", "TienMat"])

        from PySide6.QtGui import QIntValidator
        _int_val = QIntValidator(0, 100_000_000)

        self.sp_gt = QLineEdit("0")
        self.sp_gt.setValidator(QIntValidator(0, 10_000_000))
        self.sp_gt.setPlaceholderText("Nhập giá trị...")

        self.sp_tran = QLineEdit()
        self.sp_tran.setValidator(_int_val)
        self.sp_tran.setPlaceholderText("Để trống = không giới hạn")

        self.sp_dk = QLineEdit()
        self.sp_dk.setValidator(_int_val)
        self.sp_dk.setPlaceholderText("Để trống = không yêu cầu")

        self.lbl_sp       = _fl("Sản phẩm áp dụng:")
        self.lbl_dm       = _fl("Danh mục áp dụng:")
        self.lbl_tran     = _fl("Trần giảm tối đa:")

        f2.addRow(_fl("Loại KM:"),        self.cb_loai)
        f2.addRow(self.lbl_dm,             self.cb_danh_muc)
        f2.addRow(self.lbl_sp,             self.cb_sp)
        f2.addRow(_fl("Kiểu giảm:"),       self.cb_kieu)
        f2.addRow(_fl("Giá trị giảm:"),    self.sp_gt)
        f2.addRow(self.lbl_tran,            self.sp_tran)
        f2.addRow(_fl("Đơn tối thiểu:"),   self.sp_dk)
        v2.addLayout(f2)
        fl.addWidget(sec2)

        # ── 3. Mua X Tặng Y ─────────────────────────────────────
        self.sec_mua = QFrame()
        self.sec_mua.setStyleSheet(
            "QFrame { background:#252540; border-radius:8px; border:1px solid #27AE60; }"
        )
        sm = QVBoxLayout(self.sec_mua)
        sm.setContentsMargins(14, 10, 14, 12); sm.setSpacing(8)
        sm.addWidget(_lbl("🎁 Thiết lập Mua X Tặng Y", "#27AE60", 13, True))
        f3 = QFormLayout(); f3.setSpacing(8)

        self.cb_sp_mua = QComboBox()
        self.cb_sp_mua.addItem("-- Bất kỳ sản phẩm --", None)
        self._load_products(self.cb_sp_mua)

        self.sp_so_mua = QSpinBox(); self.sp_so_mua.setRange(1, 100); self.sp_so_mua.setValue(2)

        self.cb_sp_tang = QComboBox()
        self.cb_sp_tang.addItem("-- Chọn sản phẩm tặng --", None)
        self._load_products(self.cb_sp_tang)

        self.sp_so_tang = QSpinBox(); self.sp_so_tang.setRange(1, 100); self.sp_so_tang.setValue(1)

        self.sp_dk_mua = QLineEdit()
        self.sp_dk_mua.setValidator(QIntValidator(0, 100_000_000))
        self.sp_dk_mua.setPlaceholderText("Để trống = không yêu cầu")

        f3.addRow(_fl("Sản phẩm phải mua:"), self.cb_sp_mua)
        f3.addRow(_fl("Số lượng mua:"),       self.sp_so_mua)
        f3.addRow(_fl("Sản phẩm được tặng:"), self.cb_sp_tang)
        f3.addRow(_fl("Số lượng tặng:"),      self.sp_so_tang)
        f3.addRow(_fl("Đơn tối thiểu:"),      self.sp_dk_mua)
        sm.addLayout(f3)
        fl.addWidget(self.sec_mua)

        # ── 4. Điều kiện mở rộng ─────────────────────────────────
        sec4, v4 = _section_frame("🕐 Điều kiện & Thời gian", "#9B59B6")
        f4 = QFormLayout(); f4.setSpacing(8)

        # Ngày bắt đầu / kết thúc
        def _hrow(*widgets):
            c = QWidget(); c.setStyleSheet("background:transparent;")
            h = QHBoxLayout(c); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(8)
            for w in widgets: h.addWidget(w)
            h.addStretch(); return c

        self.chk_bd = QCheckBox("Có ngày bắt đầu")
        self.de_bd  = QDateEdit(QDate.currentDate())
        self.de_bd.setCalendarPopup(True); self.de_bd.setDisplayFormat("dd/MM/yyyy")
        self.de_bd.setEnabled(False); self.de_bd.setFixedWidth(130)

        self.chk_kt = QCheckBox("Có ngày kết thúc")
        self.de_kt  = QDateEdit(QDate.currentDate())
        self.de_kt.setCalendarPopup(True); self.de_kt.setDisplayFormat("dd/MM/yyyy")
        self.de_kt.setEnabled(False); self.de_kt.setFixedWidth(130)

        self.chk_luot = QCheckBox("Giới hạn lượt dùng")
        self.sp_luot  = QSpinBox(); self.sp_luot.setRange(1, 100000); self.sp_luot.setValue(100)
        self.sp_luot.setEnabled(False); self.sp_luot.setFixedWidth(100)

        # Happy Hour
        self.chk_gio = QCheckBox("Giới hạn khung giờ (Happy Hour)")
        self.te_tu  = QTimeEdit(QTime(8, 0))
        self.te_tu.setDisplayFormat("HH:mm"); self.te_tu.setEnabled(False)
        self.te_tu.setFixedWidth(90)
        self.lbl_den = _lbl("đến", "#8888AA")
        self.te_den = QTimeEdit(QTime(12, 0))
        self.te_den.setDisplayFormat("HH:mm"); self.te_den.setEnabled(False)
        self.te_den.setFixedWidth(90)

        # ── CHỌN NHÓM KM: 3 nút radio-toggle (chỉ chọn 1) ─────────
        nhom_widget = QWidget(); nhom_widget.setStyleSheet("background:transparent;")
        nhom_h = QHBoxLayout(nhom_widget)
        nhom_h.setContentsMargins(0, 0, 0, 0); nhom_h.setSpacing(0)

        NHOM_DEFS = [
            ("Chung",   "🌐  KM Chung",       "#1A4A80", "#4A9EFF",
             "Áp dụng cho mọi khách, không cần SĐT"),
            ("CaNhan",  "👤  Voucher Riêng",   "#1A3A1A", "#2ECC71",
             "Phát tặng riêng cho từng khách thành viên"),
            ("DoiDiem", "🔢  Đổi Điểm",        "#4A2800", "#E67E22",
             "Khách dùng điểm tích lũy để đổi ưu đãi"),
        ]
        self._nhom_btns: dict[str, QPushButton] = {}

        def _make_nhom_btn(key, label, bg_off, bg_on, tip):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setMinimumHeight(36)
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("nhom_key", key)
            b.setProperty("bg_on",  bg_on)
            b.setProperty("bg_off", bg_off)
            self._style_nhom_btn(b, False)
            return b

        for key, label, bg_off, bg_on, tip in NHOM_DEFS:
            b = _make_nhom_btn(key, label, bg_off, bg_on, tip)
            b.clicked.connect(lambda checked=False, k=key: self._select_nhom(k))
            # Bo góc: trái / giữa / phải
            idx = [d[0] for d in NHOM_DEFS].index(key)
            if idx == 0:
                radius = "border-radius: 8px 0 0 8px;"
            elif idx == len(NHOM_DEFS) - 1:
                radius = "border-radius: 0 8px 8px 0;"
            else:
                radius = "border-radius: 0;"
            b.setProperty("radius", radius)
            nhom_h.addWidget(b)
            self._nhom_btns[key] = b

        f4.addRow(_fl("Loại nhóm *:"), nhom_widget)

        # Ô nhập số điểm — chỉ hiện khi chọn DoiDiem
        self._diem_row_lbl = _fl("Số điểm cần:")
        self.sp_diem_can = QSpinBox()
        self.sp_diem_can.setRange(1, 1_000_000); self.sp_diem_can.setValue(100)
        self.sp_diem_can.setSuffix(" điểm"); self.sp_diem_can.setFixedWidth(140)
        self.sp_diem_can.setToolTip("Số điểm khách cần bỏ ra để đổi ưu đãi này")
        f4.addRow(self._diem_row_lbl, self.sp_diem_can)

        # Checkbox ẩn — giữ để tương thích _on_nhom_changed cũ
        self.chk_doi_diem = QCheckBox(); self.chk_doi_diem.setVisible(False)

        f4.addRow(_fl("Ngày bắt đầu:"),  _hrow(self.chk_bd,   self.de_bd))
        f4.addRow(_fl("Ngày kết thúc:"), _hrow(self.chk_kt,   self.de_kt))
        f4.addRow(_fl("Lượt dùng:"),     _hrow(self.chk_luot, self.sp_luot))
        f4.addRow(_fl("Khung giờ:"),     _hrow(self.chk_gio, self.te_tu, self.lbl_den, self.te_den))

        v4.addLayout(f4)
        fl.addWidget(sec4)

        fl.addStretch()

        # ── Kết nối signals ──────────────────────────────────────
        self.txt_ten.textChanged.connect(self._auto_gen_code)
        self.txt_ten.textChanged.connect(self._auto_fill_mo_ta)
        self.cb_loai.currentTextChanged.connect(self._auto_fill_mo_ta)
        self.cb_kieu.currentTextChanged.connect(self._auto_fill_mo_ta)
        self.sp_gt.textChanged.connect(self._auto_fill_mo_ta)

        self.cb_loai.currentTextChanged.connect(self._on_loai_changed)
        self.cb_kieu.currentTextChanged.connect(self._on_kieu_changed)
        self.chk_bd.toggled.connect(self.de_bd.setEnabled)
        self.chk_kt.toggled.connect(self.de_kt.setEnabled)
        self.chk_luot.toggled.connect(self.sp_luot.setEnabled)
        self.chk_gio.toggled.connect(self.te_tu.setEnabled)
        self.chk_gio.toggled.connect(self.te_den.setEnabled)
        # chk_doi_diem ẩn — không connect nữa

        self._on_loai_changed(self.cb_loai.currentText())
        self._on_kieu_changed(self.cb_kieu.currentText())
        # Khởi tạo nhóm mặc định
        self._select_nhom(self._nhom_hien_tai)

    def _auto_gen_code(self, ten: str):
        """Tự động tạo mã code từ tên KM nếu ô code đang trống hoặc chưa chỉnh."""
        if self.km_id:          # Đang sửa → không ghi đè
            return
        if self._code_edited:   # User đã tự gõ → không ghi đè
            return
        ten = ten.strip()
        if not ten:
            self.txt_code.setText("")
            return

        import unicodedata, re as _re
        # Bỏ dấu tiếng Việt
        nfkd = unicodedata.normalize('NFKD', ten)
        ascii_str = ''.join(c for c in nfkd if not unicodedata.combining(c))
        # Chỉ giữ chữ/số, viết hoa
        words = _re.findall(r'[A-Za-z0-9]+', ascii_str)
        if not words:
            return
        # Lấy chữ cái đầu các từ + thêm số ngẫu nhiên ngắn
        import random
        prefix = ''.join(w[:3].upper() for w in words[:3])
        suffix = str(random.randint(10, 99))
        code = prefix + suffix          # VD: GIA10, CUOITUAN22, KM15
        self._block_code_signal = True
        self.txt_code.setText(code)
        self._block_code_signal = False

    def _auto_fill_mo_ta(self):
        """Tự động gợi ý mô tả nếu ô mô tả đang trống."""
        if self._mota_edited:   # User đã tự gõ → không ghi đè
            return
        ten  = self.txt_ten.text().strip()
        loai = self.cb_loai.currentText()
        kieu = self.cb_kieu.currentText()
        gt   = int(self.sp_gt.text() or 0)

        if not ten:
            return

        if loai == "MuaXTangY":
            so_mua  = self.sp_so_mua.value() if hasattr(self, 'sp_so_mua') else 2
            so_tang = self.sp_so_tang.value() if hasattr(self, 'sp_so_tang') else 1
            mo_ta = f"Mua {so_mua} tặng {so_tang} — {ten}"
        elif kieu == "PhanTram":
            mo_ta = f"Giảm {gt}% cho {ten.lower()}"
        else:
            mo_ta = f"Giảm {gt:,}đ cho {ten.lower()}"

        self._block_mota_signal = True
        self.txt_mo_ta.setText(mo_ta)
        self._block_mota_signal = False

    def _connect_preview(self):
        """Kết nối mọi thay đổi vào _update_preview."""
        for widget in [
            self.txt_ten, self.txt_mo_ta, self.txt_code,
            self.sp_gt, self.sp_tran, self.sp_dk, self.sp_dk_mua,  # QLineEdit
        ]:
            widget.textChanged.connect(self._update_preview)
        for widget in [
            self.cb_loai, self.cb_kieu, self.cb_tt, self.cb_sp,
            self.cb_danh_muc, self.cb_sp_mua, self.cb_sp_tang,
        ]:
            widget.currentIndexChanged.connect(self._update_preview)
        for widget in [
            self.sp_so_mua, self.sp_so_tang, self.sp_diem_can,  # QSpinBox
        ]:
            widget.valueChanged.connect(self._update_preview)
        for widget in [
            self.chk_bd, self.chk_kt, self.chk_luot, self.chk_gio, self.chk_doi_diem,
        ]:
            widget.toggled.connect(self._update_preview)
        self.de_bd.dateChanged.connect(self._update_preview)
        self.de_kt.dateChanged.connect(self._update_preview)
        self.te_tu.timeChanged.connect(self._update_preview)
        self.te_den.timeChanged.connect(self._update_preview)
    def _load_products(self, cb: QComboBox):
        s = get_session()
        try:
            sps = s.query(SanPham).filter(SanPham.trang_thai == "Đang bán").order_by(SanPham.ten_sp).all()
            for sp in sps:
                cb.addItem(sp.ten_sp, sp.id)
        finally:
            s.close()

    def _load_categories(self):
        s = get_session()
        try:
            cats = s.query(SanPham.danh_muc).distinct().order_by(SanPham.danh_muc).all()
            for (cat,) in cats:
                if cat:
                    self.cb_danh_muc.addItem(cat, cat)
        finally:
            s.close()

    def _on_loai_changed(self, loai):
        is_sp  = (loai == "SanPham")
        is_mua = (loai == "MuaXTangY")
        self.sec_mua.setVisible(is_mua)
        # Chỉ show sp/danh_muc khi không phải MuaXTangY
        show_filter = not is_mua
        self.lbl_sp.setVisible(is_sp and show_filter)
        self.cb_sp.setVisible(is_sp and show_filter)
        self.lbl_dm.setVisible(not is_sp and show_filter)
        self.cb_danh_muc.setVisible(not is_sp and show_filter)
        self._update_preview()

    def _on_kieu_changed(self, kieu):
        is_pt = (kieu == "PhanTram")
        self.lbl_tran.setVisible(is_pt)
        self.sp_tran.setVisible(is_pt)
        self._update_preview()

    def _refresh_nhom_badge(self):
        """Cập nhật badge loại KM hiển thị trên section điều kiện."""
        cfg = {
            'Chung':   ("🌍 Khuyến Mãi Chung", "#1D4E89", "#5DADE2"),
            'CaNhan':  ("👤 Voucher Riêng",      "#1D6A39", "#27AE60"),
            'DoiDiem': ("🎁 Đổi Điểm",           "#6E3B12", "#E67E22"),
        }
        nhom = getattr(self, '_nhom_hien_tai',
                       getattr(self, '_default_nhom', 'Chung') or 'Chung')
        label, bg, fg = cfg.get(nhom, cfg['Chung'])
        self._nhom_badge.setText(f"  {label}  ")
        self._nhom_badge.setStyleSheet(
            f"background:{bg}; color:{fg}; font-weight:bold; font-size:12px;"
            f" border-radius:5px; padding:3px 10px; margin:2px 0;"
        )

    def _style_nhom_btn(self, btn: QPushButton, active: bool):
        bg     = btn.property("bg_on")  if active else btn.property("bg_off")
        border = btn.property("bg_on")  if active else "#333355"
        color  = "white"
        radius = btn.property("radius") or "border-radius:8px;"
        btn.setStyleSheet(
            f"QPushButton{{"
            f"  background:{bg}; color:{color}; font-weight:bold;"
            f"  font-size:12px; padding:0 14px; border:2px solid {border};"
            f"  {radius}"
            f"}}"
            f"QPushButton:hover{{ background:{btn.property('bg_on')}CC; }}"
        )
        btn.setChecked(active)

    def _select_nhom(self, key: str):
        """Chọn nhóm KM — chỉ 1 trong 3 nút được active."""
        self._nhom_hien_tai = key
        for k, b in self._nhom_btns.items():
            self._style_nhom_btn(b, k == key)

        # Hiện/ẩn ô nhập điểm
        is_doi_diem = (key == "DoiDiem")
        self._diem_row_lbl.setVisible(is_doi_diem)
        self.sp_diem_can.setVisible(is_doi_diem)

        # Sync chk_doi_diem ẩn để _save vẫn hoạt động
        self.chk_doi_diem.setChecked(is_doi_diem)

        # Cập nhật preview
        self._update_preview()

    def _on_nhom_changed(self):
        """chk_doi_diem toggle → cập nhật nhóm KM và badge."""
        if self.chk_doi_diem.isChecked():
            self._nhom_hien_tai = 'DoiDiem'
        else:
            # Quay về nhóm ban đầu (Chung hoặc CaNhan từ dialog cha)
            self._nhom_hien_tai = getattr(self, '_default_nhom', 'Chung') or 'Chung'
        if hasattr(self, '_nhom_badge'):
            self._refresh_nhom_badge()
        self._update_preview()

    def _update_preview(self):
        """Cập nhật khung preview bên phải."""
        ten   = self.txt_ten.text().strip() or "<i>Chưa đặt tên</i>"
        mo_ta = self.txt_mo_ta.text().strip()
        code  = self.txt_code.text().strip()
        loai  = self.cb_loai.currentText()
        tt    = self.cb_tt.currentText()

        tt_color = {"Đang chạy": "#2ECC71", "Tạm dừng": "#F39C12"}.get(tt, "#888")
        tt_badge = f"<span style='background:{tt_color};color:#fff;padding:2px 8px;" \
                   f"border-radius:10px;font-size:11px;font-weight:bold;'>{tt}</span>"

        # Nội dung giảm
        if loai == "MuaXTangY":
            sp_mua  = self.cb_sp_mua.currentText()
            so_mua  = self.sp_so_mua.value()
            sp_tang = self.cb_sp_tang.currentText()
            so_tang = self.sp_so_tang.value()
            giam_html = (
                f"<div style='background:#1A3A2A;border-radius:6px;padding:8px 12px;"
                f"margin:6px 0;border-left:3px solid #27AE60;'>"
                f"🎁 Mua <b style='color:#2ECC71'>{so_mua}</b> {sp_mua}"
                f" → Tặng <b style='color:#F1C40F'>{so_tang}</b> {sp_tang}"
                f"</div>"
            )
            dk_tien = int(self.sp_dk_mua.text() or 0)
        else:
            kieu = self.cb_kieu.currentText()
            gt   = int(self.sp_gt.text() or 0)
            if kieu == "PhanTram":
                tran = int(self.sp_tran.text() or 0)
                giam_val = f"<b style='color:#E74C3C;font-size:22px;'>{int(gt)}%</b> OFF"
                if tran:
                    giam_val += f" <span style='color:#F39C12;font-size:12px;'>(tối đa {int(tran):,}đ)</span>"
            else:
                giam_val = f"<b style='color:#E74C3C;font-size:20px;'>−{int(gt):,}đ</b>"

            # Phạm vi áp dụng
            if loai == "SanPham":
                pham_vi = f"<span style='color:#3498DB;'>📦 {self.cb_sp.currentText()}</span>"
            else:
                dm = self.cb_danh_muc.currentData()
                pham_vi = (
                    f"<span style='color:#3498DB;'>🗂 {self.cb_danh_muc.currentText()}</span>"
                    if dm else "<span style='color:#3498DB;'>🧾 Toàn đơn hàng</span>"
                )

            giam_html = (
                f"<div style='background:#2A1A1A;border-radius:6px;padding:10px 14px;"
                f"margin:6px 0;border-left:3px solid #E74C3C;text-align:center;'>"
                f"{giam_val}<br>{pham_vi}</div>"
            )
            dk_tien = int(self.sp_dk.text() or 0)

        # Điều kiện
        dk_parts = []
        if dk_tien:
            dk_parts.append(f"🧾 Đơn từ <b>{int(dk_tien):,}đ</b>")
        if self.chk_bd.isChecked():
            dk_parts.append(f"📅 Từ {self.de_bd.date().toString('dd/MM/yyyy')}")
        if self.chk_kt.isChecked():
            dk_parts.append(f"⏳ Đến {self.de_kt.date().toString('dd/MM/yyyy')}")
        if self.chk_luot.isChecked():
            dk_parts.append(f"🔢 Tối đa {self.sp_luot.value()} lượt")
        if self.chk_gio.isChecked():
            dk_parts.append(
                f"🕐 {self.te_tu.time().toString('HH:mm')}–{self.te_den.time().toString('HH:mm')}"
            )
        dk_html = ""
        if dk_parts:
            items = " &nbsp;·&nbsp; ".join(dk_parts)
            dk_html = (
                f"<div style='background:#1A1A2E;border-radius:6px;padding:6px 10px;"
                f"margin-top:6px;font-size:12px;color:#A1A1AA;'>{items}</div>"
            )

        code_html = ""
        if code:
            code_html = (
                f"<div style='text-align:center;margin-top:8px;'>"
                f"<span style='background:#2C3E50;color:#F1C40F;padding:4px 14px;"
                f"border-radius:20px;font-family:monospace;font-size:14px;"
                f"font-weight:bold;letter-spacing:2px;'>🏷 {code}</span></div>"
            )

        mo_ta_html = ""
        if mo_ta:
            mo_ta_html = f"<p style='color:#A1A1AA;font-size:12px;margin:4px 0;'>{mo_ta}</p>"

        # Badge nhóm trong preview
        nhom = getattr(self, '_nhom_hien_tai',
                       getattr(self, '_default_nhom', 'Chung') or 'Chung')
        diem_html = ""
        if nhom == 'DoiDiem' and self.chk_doi_diem.isChecked():
            diem = self.sp_diem_can.value()
            diem_html = (
                f"<div style='background:#2A1A3A;border-radius:6px;padding:6px 12px;"
                f"margin:4px 0;border-left:3px solid #A569BD;font-size:12px;'>"
                f"🌟 Đổi <b style='color:#A569BD'>{diem:,} điểm</b> → nhận ưu đãi này</div>"
            )
        elif nhom == 'CaNhan':
            diem_html = (
                f"<div style='background:#1A3A2A;border-radius:6px;padding:6px 12px;"
                f"margin:4px 0;border-left:3px solid #27AE60;font-size:12px;'>"
                f"👤 <b style='color:#27AE60'>Voucher Riêng</b> — phát riêng từng khách</div>"
            )

        card = f"""
        <div style='font-family:sans-serif;'>
            <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;'>
                <b style='font-size:15px;color:#E8E8F0;'>{ten}</b>
                {tt_badge}
            </div>
            {mo_ta_html}
            {diem_html}
            {giam_html}
            {dk_html}
            {code_html}
        </div>
        """
        self.preview_card.setText(card)

        # Gợi ý
        hints = []
        if not self.txt_ten.text().strip():
            hints.append("⚠️ Cần đặt tên khuyến mãi")
        if loai == "MuaXTangY" and not self.cb_sp_tang.currentData():
            hints.append("⚠️ Chưa chọn sản phẩm tặng")
        if not dk_tien and not self.chk_kt.isChecked():
            hints.append("💡 Nên đặt điều kiện tối thiểu hoặc hạn dùng")
        self.preview_hint.setText("<br>".join(hints) if hints else
                                   "✅ <span style='color:#2ECC71;'>Thông tin hợp lệ</span>")

    # ── Load dữ liệu khi sửa ────────────────────────────────────
    def _load_data(self):
        s = get_session()
        km = s.query(KhuyenMai).get(self.km_id); s.close()
        if not km: return

        self.txt_ten.setText(km.ten_km or "")
        self.txt_code.setText(km.ma_code or "")
        self.cb_tt.setCurrentText(km.trang_thai or "Đang chạy")
        self.cb_loai.setCurrentText(km.loai_km or "DonHang")

        # Mô tả (cột mới — dùng getattr để an toàn)
        self.txt_mo_ta.setText(getattr(km, 'mo_ta', '') or "")

        if km.loai_km == "MuaXTangY":
            if km.ma_sp:
                idx = self.cb_sp_mua.findData(km.ma_sp)
                if idx >= 0: self.cb_sp_mua.setCurrentIndex(idx)
            self.sp_so_mua.setValue(km.so_luong_mua or 2)
            if km.ma_sp_tang:
                idx = self.cb_sp_tang.findData(km.ma_sp_tang)
                if idx >= 0: self.cb_sp_tang.setCurrentIndex(idx)
            self.sp_so_tang.setValue(km.so_luong_tang or 1)
            self.sp_dk_mua.setText(str(int(km.dk_tong_tien_tu or 0)) if km.dk_tong_tien_tu else "")
        else:
            self.cb_kieu.setCurrentText(km.kieu_giam or "PhanTram")
            self.sp_gt.setText(str(int(km.gia_tri_giam or 0)))
            self.sp_tran.setText(str(int(km.toi_da_giam or 0)) if km.toi_da_giam else "")
            self.sp_dk.setText(str(int(km.dk_tong_tien_tu or 0)) if km.dk_tong_tien_tu else "")
            if km.ma_sp:
                idx = self.cb_sp.findData(km.ma_sp)
                if idx >= 0: self.cb_sp.setCurrentIndex(idx)
            # Danh mục
            dm = getattr(km, 'danh_muc', None)
            if dm:
                idx = self.cb_danh_muc.findData(dm)
                if idx >= 0: self.cb_danh_muc.setCurrentIndex(idx)

        if km.ngay_bat_dau:
            self.chk_bd.setChecked(True)
            self.de_bd.setDate(QDate(km.ngay_bat_dau.year, km.ngay_bat_dau.month, km.ngay_bat_dau.day))
        if km.ngay_ket_thuc:
            self.chk_kt.setChecked(True)
            self.de_kt.setDate(QDate(km.ngay_ket_thuc.year, km.ngay_ket_thuc.month, km.ngay_ket_thuc.day))
        if km.so_luot_toi_da:
            self.chk_luot.setChecked(True)
            self.sp_luot.setValue(km.so_luot_toi_da)

        # Khung giờ (cột mới)
        gio_tu  = getattr(km, 'gio_tu', None)
        gio_den = getattr(km, 'gio_den', None)
        if gio_tu and gio_den:
            self.chk_gio.setChecked(True)
            self.te_tu.setTime(QTime(gio_tu.hour, gio_tu.minute))
            self.te_den.setTime(QTime(gio_den.hour, gio_den.minute))

        # Nhóm KM: đọc từ DB → gọi _select_nhom để cập nhật 3 nút radio
        loai_nhom = getattr(km, 'loai_nhom', 'Chung') or 'Chung'
        diem_can  = int(getattr(km, 'diem_can', 0) or 0)
        self._select_nhom(loai_nhom)
        if loai_nhom == 'DoiDiem':
            self.sp_diem_can.setValue(diem_can if diem_can > 0 else 100)

        self._update_preview()

    # ── Lưu ─────────────────────────────────────────────────────
    def _save(self):
        ten = self.txt_ten.text().strip()
        if not ten:
            QMessageBox.warning(self, "Thiếu", "Tên khuyến mãi là bắt buộc!"); return

        code = self.txt_code.text().strip() or None
        loai = self.cb_loai.currentText()
        tt   = self.cb_tt.currentText()

        # Validate khung giờ
        if self.chk_gio.isChecked():
            qt = self.te_tu.time(); qd2 = self.te_den.time()
            if qt >= qd2:
                QMessageBox.warning(self, "Khung giờ sai",
                    "Giờ bắt đầu phải nhỏ hơn giờ kết thúc!"); return

        ngay_bd = ngay_kt = luot = gio_tu = gio_den = None
        if self.chk_bd.isChecked():
            qd = self.de_bd.date(); ngay_bd = date(qd.year(), qd.month(), qd.day())
        if self.chk_kt.isChecked():
            qd = self.de_kt.date(); ngay_kt = date(qd.year(), qd.month(), qd.day())
        if ngay_bd and ngay_kt and ngay_bd > ngay_kt:
            QMessageBox.warning(self, "Ngày sai", "Ngày bắt đầu phải trước ngày kết thúc!"); return
        if self.chk_luot.isChecked():
            luot = self.sp_luot.value()
        if self.chk_gio.isChecked():
            qt = self.te_tu.time(); qd2 = self.te_den.time()
            gio_tu  = dtime(qt.hour(), qt.minute())
            gio_den = dtime(qd2.hour(), qd2.minute())

        s = get_session()
        try:
            if self.km_id:
                km = s.query(KhuyenMai).get(self.km_id)
                if not km:
                    QMessageBox.warning(self, "Lỗi", "Không tìm thấy khuyến mãi!"); return
            else:
                if code and s.query(KhuyenMai).filter_by(ma_code=code).first():
                    QMessageBox.warning(self, "Trùng mã", "Mã code đã tồn tại!"); return
                km = KhuyenMai(); s.add(km)

            km.ten_km         = ten
            km.ma_code        = code
            km.loai_km        = loai
            km.trang_thai     = tt
            km.ngay_bat_dau   = ngay_bd
            km.ngay_ket_thuc  = ngay_kt
            km.so_luot_toi_da = luot

            # Cột mới (dùng setattr an toàn)
            try:
                km.mo_ta    = self.txt_mo_ta.text().strip() or None
                km.gio_tu   = gio_tu
                km.gio_den  = gio_den
                _nhom = getattr(self, '_nhom_hien_tai', 'Chung') or 'Chung'
                _is_dd = self.chk_doi_diem.isChecked()
                if _is_dd:
                    km.loai_nhom   = 'DoiDiem'
                    km.la_doi_diem = 1
                    km.diem_can    = self.sp_diem_can.value()
                elif _nhom == 'CaNhan':
                    km.loai_nhom   = 'CaNhan'
                    km.la_doi_diem = 0
                    km.diem_can    = 0
                else:
                    km.loai_nhom   = 'Chung'
                    km.la_doi_diem = 0
                    km.diem_can    = 0
            except Exception:
                pass

            if loai == "MuaXTangY":
                km.kieu_giam       = None
                km.gia_tri_giam    = None
                km.toi_da_giam     = None
                km.ma_sp           = self.cb_sp_mua.currentData()
                km.so_luong_mua    = self.sp_so_mua.value()
                km.ma_sp_tang      = self.cb_sp_tang.currentData()
                km.so_luong_tang   = self.sp_so_tang.value()
                km.dk_tong_tien_tu = int(self.sp_dk_mua.text() or 0)
                try: km.danh_muc   = None
                except Exception: pass
            else:
                km.kieu_giam      = self.cb_kieu.currentText()
                km.gia_tri_giam   = int(self.sp_gt.text() or 0)
                km.toi_da_giam    = int(self.sp_tran.text()) if self.sp_tran.text() else None
                km.dk_tong_tien_tu = int(self.sp_dk.text() or 0)
                km.ma_sp          = self.cb_sp.currentData() if loai == "SanPham" else None
                km.so_luong_mua   = None
                km.ma_sp_tang     = None
                km.so_luong_tang  = None
                try:
                    km.danh_muc = (
                        self.cb_danh_muc.currentData()
                        if loai != "SanPham" else None
                    )
                except Exception: pass

            s.commit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH: QUẢN LÝ KHUYẾN MÃI — filter bar thay tab
# ═══════════════════════════════════════════════════════════════════════════════

# Cấu hình badge loại KM — dùng chung toàn file
_KM_NHOM_CFG = {
    'Chung':   ('🌍 KM Chung',      '#1D4E89', '#5DADE2'),
    'CaNhan':  ('👤 Voucher riêng', '#1D6A39', '#27AE60'),
    'DoiDiem': ('🎁 Đổi điểm',      '#6E3B12', '#E67E22'),
}

class KhuyenMaiManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎉 Quản Lý Khuyến Mãi")
        self.resize(1160, 680)
        self.setStyleSheet(STYLE)

        self._filter_nhom = None   # None = Tất cả

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        root.addWidget(_lbl("🎉 QUẢN LÝ CHƯƠNG TRÌNH KHUYẾN MÃI", "#E67E22", 18, True))

        # ── Hàng 1: Tìm kiếm + nút CRUD ─────────────────────────
        bar = QHBoxLayout(); bar.setSpacing(8)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Tìm theo tên, mã code, mô tả...")
        self.txt_search.setMinimumWidth(260)
        self.txt_search.textChanged.connect(self._load)
        bar.addWidget(self.txt_search, stretch=1)

        self.btn_add  = _btn("➕ Khuyến Mãi",    "#27AE60")
        self.btn_edit = _btn("✏️ Sửa",            "#2980B9")
        self.btn_stop = _btn("⏸ Áp dụng / Dừng", "#E67E22")
        self.btn_del  = _btn("🗑 Xóa",            "#C0392B")
        for b in [self.btn_add, self.btn_edit, self.btn_stop, self.btn_del]:
            bar.addWidget(b)
        root.addLayout(bar)

        # ── Hàng 2: Filter chip loại KM ──────────────────────────
        filter_row = QHBoxLayout(); filter_row.setSpacing(6)
        filter_row.addWidget(_lbl("Lọc loại:", "#8888AA", 12))

        _CHIPS = [
            (None,       "Tất cả",          "#2D2D50", "#A0A0C0"),
            ('Chung',    "🌍 KM Chung",      "#1D4E89", "#5DADE2"),
            ('DoiDiem',  "🎁 Đổi điểm",     "#6E3B12", "#E67E22"),
            ('CaNhan',   "👤 Voucher Riêng", "#1D6A39", "#27AE60"),
        ]
        self._chip_btns: dict = {}

        def _make_chip(nhom, label, bg, fg):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setMinimumHeight(30)
            b.setStyleSheet(
                f"QPushButton {{ background:{bg}; color:{fg}; font-weight:bold;"
                f" font-size:12px; border-radius:14px; padding:0 14px; border:none; }}"
                f"QPushButton:checked {{ background:{fg}; color:#1A1A2E; }}"
                f"QPushButton:hover   {{ opacity:0.85; }}"
            )
            b.clicked.connect(lambda _, n=nhom: self._set_filter(n))
            self._chip_btns[nhom] = b
            filter_row.addWidget(b)

        for args in _CHIPS:
            _make_chip(*args)
        filter_row.addStretch()
        self._chip_btns[None].setChecked(True)   # mặc định "Tất cả"

        root.addLayout(filter_row)

        # ── Bảng thống nhất ──────────────────────────────────────
        COLS = ["ID", "Loại", "Tên Khuyến Mãi", "Mô tả",
                "Mã Code", "Ưu đãi", "Điều kiện",
                "Khung giờ", "Hết hạn", "Trạng thái"]
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed);  self.table.setColumnWidth(0, 38)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)   # màu xen kẽ được CSS định nghĩa
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.itemDoubleClicked.connect(lambda _: self._edit())
        root.addWidget(self.table, stretch=1)

        # Label thống kê dưới bảng
        self.lbl_history = _lbl("", "#8888AA", 12)
        root.addWidget(self.lbl_history)

        # ── Nút đóng ─────────────────────────────────────────────
        btn_close = _btn("Đóng", "#34495E", 38)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close, alignment=Qt.AlignRight)

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_stop.clicked.connect(self._toggle_status)
        self.btn_del.clicked.connect(self._delete)

        self._load()

    # ── Filter chip ───────────────────────────────────────────────
    def _set_filter(self, nhom):
        self._filter_nhom = nhom
        for k, b in self._chip_btns.items():
            b.setChecked(k == nhom)
        self._load()

    # ── Helper: bảng duy nhất ─────────────────────────────────────
    def _current_table(self) -> QTableWidget:
        return self.table

    # ── Load dữ liệu ─────────────────────────────────────────────
    def _load(self):
        kw   = self.txt_search.text().strip() if hasattr(self, 'txt_search') else ""
        nhom = self._filter_nhom              # None = tất cả
        self.table.setRowCount(0)

        s = get_session()
        try:
            q = s.query(KhuyenMai)
            if nhom is not None:
                try:
                    if nhom == 'Chung':
                        q = q.filter(
                            (KhuyenMai.loai_nhom == 'Chung') |
                            (KhuyenMai.loai_nhom == None)
                        )
                    else:
                        q = q.filter(KhuyenMai.loai_nhom == nhom)
                except Exception:
                    pass
            if kw:
                q = q.filter(
                    KhuyenMai.ten_km.ilike(f"%{kw}%") |
                    KhuyenMai.ma_code.ilike(f"%{kw}%")
                )
            kms = q.order_by(KhuyenMai.id.desc()).all()

            def _it(text, color=None, align=Qt.AlignLeft):
                it = QTableWidgetItem(str(text))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignVCenter)
                if color:
                    it.setForeground(QColor(color))
                return it

            loai_map = {
                "DonHang":   "Đơn hàng",
                "SanPham":   "Sản phẩm",
                "MuaXTangY": "Mua X Tặng Y",
            }

            for i, km in enumerate(kms):
                self.table.insertRow(i)
                self.table.setRowHeight(i, 38)

                # Col 0: ID (ẩn dữ liệu)
                id_it = _it(str(km.id))
                id_it.setData(Qt.UserRole, km.id)
                self.table.setItem(i, 0, id_it)

                # Col 1: Badge loại (widget Label nền màu)
                km_nhom = getattr(km, 'loai_nhom', 'Chung') or 'Chung'
                badge_label, badge_bg, badge_fg = _KM_NHOM_CFG.get(
                    km_nhom, ('🌍 KM Chung', '#1D4E89', '#5DADE2')
                )
                badge_w = QLabel(f"  {badge_label}  ")
                badge_w.setAlignment(Qt.AlignCenter)
                badge_w.setStyleSheet(
                    f"background:{badge_bg}; color:{badge_fg};"
                    f" font-weight:bold; font-size:11px; border-radius:5px;"
                    f" padding:3px 6px; margin:3px 4px;"
                )
                self.table.setCellWidget(i, 1, badge_w)

                # Col 2: Tên
                self.table.setItem(i, 2, _it(km.ten_km or "", "#E8E8F0"))
                # Col 3: Mô tả
                self.table.setItem(i, 3, _it(getattr(km, 'mo_ta', '') or "—", "#8888AA"))
                # Col 4: Mã code
                self.table.setItem(i, 4, _it(km.ma_code or "—", "#F1C40F"))

                # Col 5: Ưu đãi
                if km.loai_km == "MuaXTangY":
                    gt_str = f"Mua {km.so_luong_mua or 1} → Tặng {km.so_luong_tang or 1}"
                    gt_color = "#27AE60"
                elif km.kieu_giam == "PhanTram":
                    gt_str = f"−{int(km.gia_tri_giam or 0)}%"
                    if km.toi_da_giam:
                        gt_str += f"  (max {int(km.toi_da_giam):,}đ)"
                    gt_color = "#2ECC71"
                elif km.kieu_giam == "TienMat":
                    gt_str = f"−{int(km.gia_tri_giam or 0):,}đ"
                    gt_color = "#2ECC71"
                else:
                    gt_str = loai_map.get(km.loai_km, km.loai_km or "—")
                    gt_color = "#8888AA"

                # Nếu là đổi điểm: prepend số điểm cần
                if km_nhom == 'DoiDiem':
                    diem = int(getattr(km, 'diem_can', 0) or 0)
                    gt_str = f"🌟 {diem:,} đ.  →  {gt_str}"

                self.table.setItem(i, 5, _it(gt_str, gt_color))

                # Col 6: Điều kiện
                dk = km.dk_tong_tien_tu
                dk_str = f"≥ {int(dk):,}đ" if dk else "—"
                self.table.setItem(i, 6, _it(dk_str))

                # Col 7: Khung giờ
                gio_tu  = getattr(km, 'gio_tu',  None)
                gio_den = getattr(km, 'gio_den', None)
                gio_str = (
                    f"{gio_tu.strftime('%H:%M')}–{gio_den.strftime('%H:%M')}"
                    if gio_tu and gio_den else "—"
                )
                self.table.setItem(i, 7, _it(gio_str, "#3498DB"))

                # Col 8: Hết hạn
                het = km.ngay_ket_thuc.strftime("%d/%m/%Y") if km.ngay_ket_thuc else "Không hạn"
                self.table.setItem(i, 8, _it(het))

                # Col 9: Trạng thái
                tt = km.trang_thai or "Đang chạy"
                tt_color = {
                    "Đang chạy": "#2ECC71",
                    "Tạm dừng":  "#F1C40F",
                    "Hết hạn":   "#E74C3C",
                }.get(tt, "white")
                self.table.setItem(i, 9, _it(tt, tt_color, Qt.AlignCenter))

        finally:
            s.close()

    # ── Selection handler ─────────────────────────────────────────
    def _on_select(self):
        row = self.table.currentRow()
        if row < 0:
            self.lbl_history.setText("")
            return
        km_id = self.table.item(row, 0).data(Qt.UserRole)
        ten   = self.table.item(row, 2).text()
        s = get_session()
        try:
            count = s.query(NhatKyKhuyenMai).filter_by(ma_km=km_id).count()
            self.lbl_history.setText(
                f"  📊  [{ten}]   Đã dùng: {count} lần"
            )
        finally:
            s.close()

    # ── CRUD ─────────────────────────────────────────────────────
    def _sel_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một khuyến mãi!"); return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _add(self):
        """
        Thêm KM mới.
        Nếu chip "Voucher Riêng" đang bật → default_nhom='CaNhan'.
        Mọi chip khác                      → default_nhom='Chung'.
        """
        nhom = 'CaNhan' if self._filter_nhom == 'CaNhan' else 'Chung'
        if KhuyenMaiForm(parent=self, default_nhom=nhom).exec():
            self._load()

    def _edit(self):
        km_id = self._sel_id()
        # Không truyền default_nhom — _load_data tự đọc loai_nhom từ DB
        if km_id and KhuyenMaiForm(km_id=km_id, parent=self).exec():
            self._load()

    def _toggle_status(self):
        km_id = self._sel_id()
        if not km_id: return
        s = get_session()
        try:
            km = s.query(KhuyenMai).get(km_id)
            if not km: return
            km.trang_thai = "Tạm dừng" if km.trang_thai == "Đang chạy" else "Đang chạy"
            s.commit()
        finally: s.close()
        self._load()

    def _delete(self):
        km_id = self._sel_id()
        if not km_id: return
        row = self.table.currentRow()
        ten = self.table.item(row, 2).text()
        if QMessageBox.question(
            self, "Xóa?", f"Xóa khuyến mãi <b>{ten}</b>?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes: return
        s = get_session()
        try:
            km = s.query(KhuyenMai).get(km_id)
            if km: s.delete(km); s.commit()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
        finally: s.close()
        self._load()


# ── Hàm tiện ích: lấy danh sách KM đổi điểm đang hoạt động ─────
def get_khuyen_mai_doi_diem() -> list:
    """
    Trả về list KhuyenMai loại DoiDiem đang chạy, sắp xếp theo diem_can tăng dần.
    Dùng tại màn hình thanh toán để hiển thị tùy chọn đổi điểm.
    """
    s = get_session()
    try:
        q = s.query(KhuyenMai).filter(KhuyenMai.trang_thai == "Đang chạy")
        try:
            q = q.filter(KhuyenMai.loai_nhom == 'DoiDiem')
        except Exception:
            pass
        return q.order_by(KhuyenMai.id).all()
    finally:
        s.close()


def get_valid_khuyen_mai(tong_tien: float = 0) -> list:
    """
    Trả về list KM Chung hợp lệ tại thời điểm hiện tại.
    Mỗi item: {"km": <KhuyenMai>, "ly_do_loi": "" | "<lý do không đủ điều kiện>"}
    - ly_do_loi == "" → KM hợp lệ
    - ly_do_loi != "" → không đủ điều kiện, hiển thị lý do cho nhân viên
    """
    from datetime import datetime, time as dtime
    now   = datetime.now()
    today = now.date()
    h_now = dtime(now.hour, now.minute)

    s = get_session()
    try:
        q = s.query(KhuyenMai).filter(KhuyenMai.trang_thai == "Đang chạy")
        try:
            q = q.filter(
                (KhuyenMai.loai_nhom == "Chung") |
                (KhuyenMai.loai_nhom == None)
            )
        except Exception:
            pass
        kms = q.order_by(KhuyenMai.id.desc()).all()

        result = []
        for km in kms:
            reasons = []

            # Đơn tối thiểu
            dk_tien = float(km.dk_tong_tien_tu or 0)
            if dk_tien and tong_tien < dk_tien:
                reasons.append(f"Đơn chưa đạt {int(dk_tien):,}đ (hiện {int(tong_tien):,}đ)")

            # Ngày bắt đầu
            if km.ngay_bat_dau and today < km.ngay_bat_dau.date():
                reasons.append(f"Chưa đến ngày áp dụng ({km.ngay_bat_dau.strftime('%d/%m/%Y')})")

            # Ngày kết thúc
            if km.ngay_ket_thuc and today > km.ngay_ket_thuc.date():
                reasons.append(f"Đã hết hạn ({km.ngay_ket_thuc.strftime('%d/%m/%Y')})")

            # Lượt dùng
            luot = km.so_luot_su_dung
            if luot:
                from database.models import NhatKyKhuyenMai as _NK
                used = s.query(_NK).filter_by(ma_km=km.id).count()
                if used >= int(luot):
                    reasons.append(f"Đã hết lượt ({int(luot):,} lượt)")

            # Khung giờ
            gio_tu  = getattr(km, 'gio_tu',  None)
            gio_den = getattr(km, 'gio_den', None)
            if gio_tu and gio_den:
                if not (gio_tu <= h_now <= gio_den):
                    reasons.append(
                        f"Ngoài giờ áp dụng "
                        f"({gio_tu.strftime('%H:%M')}–{gio_den.strftime('%H:%M')})"
                    )

            result.append({
                "km":        km,
                "ly_do_loi": "  ·  ".join(reasons),
            })

        return result
    finally:
        s.close()