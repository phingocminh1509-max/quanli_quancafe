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
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
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
def _migrate():
    """Thêm các cột mới vào bảng khuyen_mai nếu chưa tồn tại."""
    try:
        from database.db_config import get_session as _gs
        import sqlalchemy as sa
        s = _gs()
        conn = s.bind.connect() if hasattr(s, 'bind') else s.get_bind().connect()
        insp = sa.inspect(conn)
        cols = {c['name'] for c in insp.get_columns('khuyen_mai')}
        new_cols = {
            'mo_ta':        'VARCHAR(500)',
            'danh_muc':     'VARCHAR(200)',
            'gio_tu':       'TIME',
            'gio_den':      'TIME',
            'uu_tien':      'INTEGER DEFAULT 0',
        }
        for col, typ in new_cols.items():
            if col not in cols:
                conn.execute(sa.text(f'ALTER TABLE khuyen_mai ADD COLUMN {col} {typ}'))
        conn.commit()
        conn.close()
        s.close()
    except Exception:
        pass

_migrate()


STYLE = """
QDialog, QWidget  { background-color: #1A1A2E; color: #E8E8F0; }
QTabWidget::pane  { border: none; background: #1A1A2E; }
QTabBar::tab      { background:#252540; color:#8888AA; padding:10px 22px;
    border-radius:6px 6px 0 0; font-weight:bold; font-size:13px; }
QTabBar::tab:selected { background:#E67E22; color:white; }
QTabBar::tab:hover    { background:#333355; color:white; }
QTableWidget { background:#252540; border:none; border-radius:8px;
    gridline-color:#333355; color:#E8E8F0; font-size:13px; }
QTableWidget::item { padding:7px; border-bottom:1px solid #333355; }
QTableWidget::item:selected { background:#E67E22; color:white; }
QHeaderView::section { background:#1A1A2E; color:#8888AA;
    padding:9px; border:none; font-weight:bold; font-size:12px; }
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
    border:1px solid #333355; background:#252540; }
QCheckBox::indicator:checked { background:#E67E22; border-color:#E67E22; }
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
    def __init__(self, km_id=None, parent=None):
        super().__init__(parent)
        self.km_id = km_id
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
        self._code_edited       = False   # True khi user tự gõ mã code
        self._mota_edited       = False   # True khi user tự gõ mô tả
        self._block_code_signal = False
        self._block_mota_signal = False
        self._build_form()
        self._connect_preview()

        if km_id:
            self._load_data()
            self._code_edited = True   # Đang sửa → coi như đã chỉnh
            self._mota_edited = True
        else:
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

        self.sp_uu_tien = QSpinBox()
        self.sp_uu_tien.setRange(0, 100)
        self.sp_uu_tien.setValue(0)
        self.sp_uu_tien.setToolTip("Số càng cao = ưu tiên áp dụng trước (khi nhiều KM cùng hợp lệ)")

        f1.addRow(_fl("Tên KM *:"),     self.txt_ten)
        f1.addRow(_fl("Mô tả ngắn:"),   self.txt_mo_ta)
        f1.addRow(_fl("Mã code:"),       self.txt_code)
        f1.addRow(_fl("Trạng thái:"),    self.cb_tt)
        f1.addRow(_fl("Ưu tiên (0–100):"), self.sp_uu_tien)
        v1.addLayout(f1)
        fl.addWidget(sec1)

        # Nút tạo mã tự động bên cạnh ô code
        self.txt_ten.textChanged.connect(self._auto_gen_code)
        self.txt_ten.textChanged.connect(self._auto_fill_mo_ta)
        self.cb_loai.currentTextChanged.connect(self._auto_fill_mo_ta)
        self.cb_kieu.currentTextChanged.connect(self._auto_fill_mo_ta)
        self.sp_gt.valueChanged.connect(self._auto_fill_mo_ta)

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

        self.sp_gt = QDoubleSpinBox()
        self.sp_gt.setRange(0, 10_000_000); self.sp_gt.setValue(10)

        self.sp_tran = QDoubleSpinBox()
        self.sp_tran.setRange(0, 10_000_000); self.sp_tran.setSuffix(" đ")
        self.sp_tran.setSpecialValueText("Không giới hạn")

        self.sp_dk = QDoubleSpinBox()
        self.sp_dk.setRange(0, 100_000_000); self.sp_dk.setSuffix(" đ")
        self.sp_dk.setSpecialValueText("Không yêu cầu")

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

        self.sp_dk_mua = QDoubleSpinBox()
        self.sp_dk_mua.setRange(0, 100_000_000); self.sp_dk_mua.setSuffix(" đ")
        self.sp_dk_mua.setSpecialValueText("Không yêu cầu")

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

        f4.addRow(_fl("Ngày bắt đầu:"),  _hrow(self.chk_bd,   self.de_bd))
        f4.addRow(_fl("Ngày kết thúc:"), _hrow(self.chk_kt,   self.de_kt))
        f4.addRow(_fl("Lượt dùng:"),     _hrow(self.chk_luot, self.sp_luot))
        f4.addRow(_fl("Khung giờ:"),     _hrow(self.chk_gio, self.te_tu, self.lbl_den, self.te_den))
        v4.addLayout(f4)
        fl.addWidget(sec4)

        fl.addStretch()

        # ── Kết nối signals ──────────────────────────────────────
        self.cb_loai.currentTextChanged.connect(self._on_loai_changed)
        self.cb_kieu.currentTextChanged.connect(self._on_kieu_changed)
        self.chk_bd.toggled.connect(self.de_bd.setEnabled)
        self.chk_kt.toggled.connect(self.de_kt.setEnabled)
        self.chk_luot.toggled.connect(self.sp_luot.setEnabled)
        self.chk_gio.toggled.connect(self.te_tu.setEnabled)
        self.chk_gio.toggled.connect(self.te_den.setEnabled)

        self._on_loai_changed(self.cb_loai.currentText())
        self._on_kieu_changed(self.cb_kieu.currentText())

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
        gt   = int(self.sp_gt.value())

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
        ]:
            widget.textChanged.connect(self._update_preview)
        for widget in [
            self.cb_loai, self.cb_kieu, self.cb_tt, self.cb_sp,
            self.cb_danh_muc, self.cb_sp_mua, self.cb_sp_tang,
        ]:
            widget.currentIndexChanged.connect(self._update_preview)
        for widget in [
            self.sp_gt, self.sp_tran, self.sp_dk, self.sp_dk_mua,
            self.sp_so_mua, self.sp_so_tang, self.sp_uu_tien,
        ]:
            widget.valueChanged.connect(self._update_preview)
        for widget in [
            self.chk_bd, self.chk_kt, self.chk_luot, self.chk_gio,
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
        self.sp_gt.setSuffix(" %" if is_pt else " đ")
        self._update_preview()

    def _update_preview(self):
        """Cập nhật khung preview bên phải."""
        ten   = self.txt_ten.text().strip() or "<i>Chưa đặt tên</i>"
        mo_ta = self.txt_mo_ta.text().strip()
        code  = self.txt_code.text().strip()
        loai  = self.cb_loai.currentText()
        tt    = self.cb_tt.currentText()
        uu    = self.sp_uu_tien.value()

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
            dk_tien = self.sp_dk_mua.value()
        else:
            kieu = self.cb_kieu.currentText()
            gt   = self.sp_gt.value()
            if kieu == "PhanTram":
                tran = self.sp_tran.value()
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
            dk_tien = self.sp_dk.value()

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

        uu_html = ""
        if uu > 0:
            stars = "★" * min(uu // 20 + 1, 5)
            uu_html = f"<p style='color:#F1C40F;font-size:11px;margin:2px 0;'>Ưu tiên: {stars} ({uu})</p>"

        card = f"""
        <div style='font-family:sans-serif;'>
            <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;'>
                <b style='font-size:15px;color:#E8E8F0;'>{ten}</b>
                {tt_badge}
            </div>
            {mo_ta_html}
            {uu_html}
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
        if uu == 0:
            hints.append("💡 Ưu tiên = 0 sẽ áp dụng sau các KM khác")
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

        # Mô tả & ưu tiên (cột mới — dùng getattr để an toàn)
        self.txt_mo_ta.setText(getattr(km, 'mo_ta', '') or "")
        self.sp_uu_tien.setValue(int(getattr(km, 'uu_tien', 0) or 0))

        if km.loai_km == "MuaXTangY":
            if km.ma_sp:
                idx = self.cb_sp_mua.findData(km.ma_sp)
                if idx >= 0: self.cb_sp_mua.setCurrentIndex(idx)
            self.sp_so_mua.setValue(km.so_luong_mua or 2)
            if km.ma_sp_tang:
                idx = self.cb_sp_tang.findData(km.ma_sp_tang)
                if idx >= 0: self.cb_sp_tang.setCurrentIndex(idx)
            self.sp_so_tang.setValue(km.so_luong_tang or 1)
            self.sp_dk_mua.setValue(km.dk_tong_tien_tu or 0)
        else:
            self.cb_kieu.setCurrentText(km.kieu_giam or "PhanTram")
            self.sp_gt.setValue(km.gia_tri_giam or 0)
            self.sp_tran.setValue(km.toi_da_giam or 0)
            self.sp_dk.setValue(km.dk_tong_tien_tu or 0)
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
                km.uu_tien  = self.sp_uu_tien.value()
                km.gio_tu   = gio_tu
                km.gio_den  = gio_den
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
                km.dk_tong_tien_tu = self.sp_dk_mua.value()
                try: km.danh_muc   = None
                except Exception: pass
            else:
                km.kieu_giam      = self.cb_kieu.currentText()
                km.gia_tri_giam   = self.sp_gt.value()
                km.toi_da_giam    = self.sp_tran.value() or None
                km.dk_tong_tien_tu = self.sp_dk.value()
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
# DIALOG CHÍNH: QUẢN LÝ KHUYẾN MÃI
# ═══════════════════════════════════════════════════════════════════════════════
class KhuyenMaiManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎉 Quản Lý Khuyến Mãi")
        self.resize(1060, 620)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        root.addWidget(_lbl("🎉 QUẢN LÝ CHƯƠNG TRÌNH KHUYẾN MÃI", "#E67E22", 18, True))

        bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm theo tên, mã code, mô tả...")
        self.txt_search.textChanged.connect(self._load)
        bar.addWidget(self.txt_search)

        self.btn_add  = _btn("➕ Thêm KM",  "#27AE60")
        self.btn_edit = _btn("✏️ Sửa",      "#2980B9")
        self.btn_stop = _btn("⏸ Tạm dừng", "#E67E22")
        self.btn_del  = _btn("🗑 Xóa",      "#C0392B")
        for b in [self.btn_add, self.btn_edit, self.btn_stop, self.btn_del]:
            bar.addWidget(b)
        root.addLayout(bar)

        # Bảng — thêm cột Mô tả, Ưu tiên, Khung giờ
        COLS = ["ID", "Tên Khuyến Mãi", "Mô tả", "Mã Code",
                "Loại", "Giảm", "Điều Kiện", "Khung Giờ",
                "Ưu tiên", "Hết Hạn", "Trạng Thái"]
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed);   self.table.setColumnWidth(0, 40)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        for c in range(4, len(COLS)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemDoubleClicked.connect(lambda _: self._edit())
        root.addWidget(self.table)

        self.lbl_history = _lbl("", "#8888AA", 12)
        root.addWidget(self.lbl_history)

        btn_close = _btn("Đóng", "#34495E", 38)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close, alignment=Qt.AlignRight)

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_stop.clicked.connect(self._toggle_status)
        self.btn_del.clicked.connect(self._delete)
        self.table.itemSelectionChanged.connect(self._on_select)

        self._load()

    def _load(self):
        kw = self.txt_search.text().strip() if hasattr(self, 'txt_search') else ""
        self.table.setRowCount(0)
        s = get_session()
        try:
            q = s.query(KhuyenMai)
            if kw:
                q = q.filter(
                    KhuyenMai.ten_km.ilike(f"%{kw}%") |
                    KhuyenMai.ma_code.ilike(f"%{kw}%")
                )
            kms = q.order_by(KhuyenMai.id.desc()).all()
            for i, km in enumerate(kms):
                self.table.insertRow(i)

                def _it(text, color=None, align=Qt.AlignLeft):
                    it = QTableWidgetItem(str(text))
                    it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    it.setTextAlignment(align | Qt.AlignVCenter)
                    if color: it.setForeground(QColor(color))
                    return it

                id_item = _it(str(km.id))
                id_item.setData(Qt.UserRole, km.id)
                self.table.setItem(i, 0, id_item)
                self.table.setItem(i, 1, _it(km.ten_km or "", "#E8E8F0"))
                self.table.setItem(i, 2, _it(getattr(km,'mo_ta','') or "—", "#8888AA"))

                code_item = _it(km.ma_code or "—", "#F1C40F")
                self.table.setItem(i, 3, code_item)

                loai_map = {"DonHang": "Đơn hàng", "SanPham": "Sản phẩm", "MuaXTangY": "Mua X Tặng Y"}
                self.table.setItem(i, 4, _it(loai_map.get(km.loai_km, km.loai_km or "")))

                if km.loai_km == "MuaXTangY":
                    gt_str = f"Mua {km.so_luong_mua or 1} → Tặng {km.so_luong_tang or 1}"
                elif km.kieu_giam == "PhanTram":
                    gt_str = f"{int(km.gia_tri_giam or 0)}%"
                    if km.toi_da_giam: gt_str += f" (max {int(km.toi_da_giam):,}đ)"
                else:
                    gt_str = f"{int(km.gia_tri_giam or 0):,}đ"
                self.table.setItem(i, 5, _it(gt_str, "#2ECC71"))

                dk_str = f"≥ {int(km.dk_tong_tien_tu or 0):,}đ" if km.dk_tong_tien_tu else "—"
                self.table.setItem(i, 6, _it(dk_str))

                gio_tu  = getattr(km, 'gio_tu', None)
                gio_den = getattr(km, 'gio_den', None)
                gio_str = (
                    f"{gio_tu.strftime('%H:%M')}–{gio_den.strftime('%H:%M')}"
                    if gio_tu and gio_den else "—"
                )
                self.table.setItem(i, 7, _it(gio_str, "#3498DB"))

                uu = int(getattr(km, 'uu_tien', 0) or 0)
                self.table.setItem(i, 8, _it(str(uu) if uu else "—",
                    "#F1C40F" if uu > 0 else "#555566", Qt.AlignCenter))

                het = km.ngay_ket_thuc.strftime("%d/%m/%Y") if km.ngay_ket_thuc else "Không hạn"
                self.table.setItem(i, 9, _it(het))

                tt = km.trang_thai or "Đang chạy"
                tt_color = {"Đang chạy": "#2ECC71", "Tạm dừng": "#F1C40F",
                            "Hết hạn": "#E74C3C"}.get(tt, "white")
                self.table.setItem(i, 10, _it(tt, tt_color))
        finally:
            s.close()

    def _sel_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một khuyến mãi!"); return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _add(self):
        if KhuyenMaiForm(parent=self).exec(): self._load()

    def _edit(self):
        km_id = self._sel_id()
        if km_id and KhuyenMaiForm(km_id, self).exec(): self._load()

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
        ten = self.table.item(row, 1).text()
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

    def _on_select(self):
        row = self.table.currentRow()
        if row < 0: return
        km_id = self.table.item(row, 0).data(Qt.UserRole)
        s = get_session()
        try:
            count = s.query(NhatKyKhuyenMai).filter_by(ma_km=km_id).count()
            ten   = self.table.item(row, 1).text()
            uu    = self.table.item(row, 8).text()
            self.lbl_history.setText(
                f"  📊 [{ten}]  Đã dùng: {count} lần  |  Ưu tiên: {uu}"
            )
        finally:
            s.close()