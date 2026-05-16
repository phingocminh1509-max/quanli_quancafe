"""
views/khuyen_mai_manager.py
══════════════════════════════════════════════════════════════════
Quản lý Khuyến Mãi:
  • CRUD chương trình khuyến mãi (Đơn hàng / Sản phẩm / Mua X Tặng Y)
  • Giảm theo % hoặc tiền mặt
  • Thiết lập thời hạn, điều kiện, giới hạn lượt dùng
  • Xem lịch sử áp dụng
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFormLayout, QLineEdit, QDateEdit, QComboBox,
    QAbstractItemView, QDoubleSpinBox, QSpinBox, QCheckBox, QFrame,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from database.db_config import get_session
from database.models import KhuyenMai, SanPham, NhatKyKhuyenMai

STYLE = """
QDialog, QWidget { background-color: #1E1E2E; color: white; }
QTabWidget::pane { border: none; }
QTabBar::tab { background:#2D2D3F; color:#A1A1AA; padding:10px 20px;
    border-radius:6px 6px 0 0; font-weight:bold; font-size:13px; }
QTabBar::tab:selected { background:#E67E22; color:white; }
QTabBar::tab:hover    { background:#3E3E55; color:white; }
QTableWidget { background:#2D2D3F; border:none; border-radius:8px;
    gridline-color:#3E3E55; color:white; font-size:13px; }
QTableWidget::item { padding:7px; border-bottom:1px solid #3E3E55; }
QTableWidget::item:selected { background:#E67E22; }
QHeaderView::section { background:#1A1A24; color:#A1A1AA;
    padding:9px; border:none; font-weight:bold; }
QLineEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background:#2D2D3F; border:1px solid #3E3E55; border-radius:6px;
    padding:6px 10px; color:white; font-size:13px; }
QLineEdit:focus, QDateEdit:focus { border-color:#E67E22; }
QComboBox::drop-down { border:none; }
QComboBox QAbstractItemView { background:#2D2D3F; color:white;
    selection-background-color:#E67E22; }
QScrollBar:vertical { background:#1A1A24; width:7px; border-radius:4px; }
QScrollBar::handle:vertical { background:#3E3E55; border-radius:4px; }
QCheckBox { color: white; font-size: 13px; }
QCheckBox::indicator { width:16px; height:16px; border-radius:4px;
    border:1px solid #3E3E55; background:#2D2D3F; }
QCheckBox::indicator:checked { background:#E67E22; border-color:#E67E22; }
"""

def _btn(text, color, h=36):
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setStyleSheet(
        f"background:{color};color:white;font-weight:bold;"
        f"border-radius:6px;font-size:13px;padding:0 14px;"
    )
    return b

def _lbl(text, color="white", size=13, bold=False):
    l = QLabel(text)
    l.setStyleSheet(f"color:{color};font-size:{size}px;"
                    + ("font-weight:bold;" if bold else ""))
    return l


# ═══════════════════════════════════════════════════════════════════════════════
# FORM THÊM / SỬA KHUYẾN MÃI
# ═══════════════════════════════════════════════════════════════════════════════
def _make_section(title: str, color: str = "#3E3E55") -> QFrame:
    """Tạo frame section có tiêu đề màu."""
    f = QFrame()
    f.setStyleSheet(
        f"QFrame {{ background:#2D2D3F; border-radius:8px; border:1px solid {color}; }}"
    )
    return f


class KhuyenMaiForm(QDialog):
    def __init__(self, km_id=None, parent=None):
        super().__init__(parent)
        self.km_id = km_id
        self.setWindowTitle("Thêm Khuyến Mãi" if not km_id else "Sửa Khuyến Mãi")
        self.resize(540, 680)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        root.addWidget(_lbl("THÔNG TIN KHUYẾN MÃI", "#E67E22", 16, True))

        # ── Phần 1: Thông tin chung (luôn hiện) ─────────────────
        def _fl(t):
            l = QLabel(t); l.setStyleSheet("color:#A1A1AA; border:none;"); return l

        form_chung = QFormLayout()
        form_chung.setSpacing(8)

        self.txt_ten  = QLineEdit(); self.txt_ten.setPlaceholderText("VD: Giảm 10% cuối tuần")
        self.txt_code = QLineEdit(); self.txt_code.setPlaceholderText("VD: WEEKEND10 (để trống = tự động)")
        self.cb_tt    = QComboBox(); self.cb_tt.addItems(["Đang chạy", "Tạm dừng"])

        form_chung.addRow(_fl("Tên KM *:"),   self.txt_ten)
        form_chung.addRow(_fl("Mã code:"),     self.txt_code)
        form_chung.addRow(_fl("Trạng thái:"),  self.cb_tt)
        root.addLayout(form_chung)

        # ── Loại KM ─────────────────────────────────────────────
        loai_row = QHBoxLayout()
        loai_row.addWidget(_fl("Loại KM:"))
        self.cb_loai = QComboBox()
        self.cb_loai.addItems(["DonHang", "SanPham", "MuaXTangY"])
        self.cb_loai.setFixedWidth(200)
        loai_row.addWidget(self.cb_loai)
        loai_row.addStretch()
        root.addLayout(loai_row)

        # ── Section: Giảm giá (DonHang / SanPham) ───────────────
        self.sec_giam = QFrame()
        self.sec_giam.setStyleSheet(
            "QFrame { background:#2D2D3F; border-radius:8px; border:1px solid #E67E22; }"
        )
        sg = QVBoxLayout(self.sec_giam)
        sg.setContentsMargins(14, 10, 14, 10); sg.setSpacing(8)
        sg.addWidget(_lbl("⚡ Thiết lập giảm giá", "#E67E22", 13, True))

        form_giam = QFormLayout(); form_giam.setSpacing(8)

        # Sản phẩm áp dụng
        self.cb_sp = QComboBox()
        self.cb_sp.addItem("-- Toàn đơn hàng --", None)
        self._load_products(self.cb_sp)

        # Kiểu & giá trị
        self.cb_kieu = QComboBox()
        self.cb_kieu.addItems(["PhanTram", "TienMat"])
        self.sp_gt = QDoubleSpinBox()
        self.sp_gt.setRange(0, 10_000_000); self.sp_gt.setValue(10)
        self.cb_kieu.currentTextChanged.connect(self._on_kieu_changed)

        self.sp_tran = QDoubleSpinBox()
        self.sp_tran.setRange(0, 10_000_000); self.sp_tran.setSuffix(" đ")
        self.sp_tran.setSpecialValueText("Không giới hạn")

        # Điều kiện đơn tối thiểu
        self.sp_dk = QDoubleSpinBox()
        self.sp_dk.setRange(0, 100_000_000); self.sp_dk.setSuffix(" đ")
        self.sp_dk.setSpecialValueText("Không yêu cầu")

        self.lbl_sp = _fl("Sản phẩm áp dụng:")
        self.lbl_tran = _fl("Trần giảm tối đa:")
        form_giam.addRow(self.lbl_sp,         self.cb_sp)
        form_giam.addRow(_fl("Kiểu giảm:"),   self.cb_kieu)
        form_giam.addRow(_fl("Giá trị giảm:"),self.sp_gt)
        form_giam.addRow(self.lbl_tran,        self.sp_tran)
        form_giam.addRow(_fl("Đơn tối thiểu:"),self.sp_dk)
        sg.addLayout(form_giam)
        root.addWidget(self.sec_giam)

        # ── Section: Mua X Tặng Y ────────────────────────────────
        self.sec_mua = QFrame()
        self.sec_mua.setStyleSheet(
            "QFrame { background:#2D2D3F; border-radius:8px; border:1px solid #27AE60; }"
        )
        sm = QVBoxLayout(self.sec_mua)
        sm.setContentsMargins(14, 10, 14, 10); sm.setSpacing(8)
        sm.addWidget(_lbl("🎁 Thiết lập Mua X Tặng Y", "#27AE60", 13, True))

        form_mua = QFormLayout(); form_mua.setSpacing(8)

        # Sản phẩm phải mua
        self.cb_sp_mua = QComboBox()
        self.cb_sp_mua.addItem("-- Bất kỳ sản phẩm --", None)
        self._load_products(self.cb_sp_mua)

        self.sp_so_mua = QSpinBox(); self.sp_so_mua.setRange(1, 100); self.sp_so_mua.setValue(2)

        # Sản phẩm được tặng
        self.cb_sp_tang = QComboBox()
        self.cb_sp_tang.addItem("-- Chọn sản phẩm tặng --", None)
        self._load_products(self.cb_sp_tang)

        self.sp_so_tang = QSpinBox(); self.sp_so_tang.setRange(1, 100); self.sp_so_tang.setValue(1)

        # Điều kiện đơn tối thiểu cho MuaXTangY
        self.sp_dk_mua = QDoubleSpinBox()
        self.sp_dk_mua.setRange(0, 100_000_000); self.sp_dk_mua.setSuffix(" đ")
        self.sp_dk_mua.setSpecialValueText("Không yêu cầu")

        form_mua.addRow(_fl("Sản phẩm phải mua:"), self.cb_sp_mua)
        form_mua.addRow(_fl("Số lượng mua:"),       self.sp_so_mua)
        form_mua.addRow(_fl("Sản phẩm được tặng:"), self.cb_sp_tang)
        form_mua.addRow(_fl("Số lượng tặng:"),      self.sp_so_tang)
        form_mua.addRow(_fl("Đơn tối thiểu:"),      self.sp_dk_mua)
        sm.addLayout(form_mua)
        root.addWidget(self.sec_mua)

        # ── Thời hạn & lượt dùng ────────────────────────────────
        form_time = QFormLayout(); form_time.setSpacing(8)

        self.chk_bd = QCheckBox("Có ngày bắt đầu")
        self.de_bd  = QDateEdit(QDate.currentDate())
        self.de_bd.setCalendarPopup(True); self.de_bd.setDisplayFormat("dd/MM/yyyy")
        self.de_bd.setEnabled(False)

        self.chk_kt = QCheckBox("Có ngày kết thúc")
        self.de_kt  = QDateEdit(QDate.currentDate())
        self.de_kt.setCalendarPopup(True); self.de_kt.setDisplayFormat("dd/MM/yyyy")
        self.de_kt.setEnabled(False)

        self.chk_luot = QCheckBox("Giới hạn lượt dùng")
        self.sp_luot  = QSpinBox(); self.sp_luot.setRange(1, 100000); self.sp_luot.setValue(100)
        self.sp_luot.setEnabled(False)

        def _hrow(w1, w2):
            c = QWidget(); h = QHBoxLayout(c)
            h.setContentsMargins(0,0,0,0); h.addWidget(w1); h.addWidget(w2); h.addStretch()
            return c

        form_time.addRow(_fl("Ngày bắt đầu:"),  _hrow(self.chk_bd,   self.de_bd))
        form_time.addRow(_fl("Ngày kết thúc:"), _hrow(self.chk_kt,   self.de_kt))
        form_time.addRow(_fl("Lượt dùng:"),     _hrow(self.chk_luot, self.sp_luot))
        root.addLayout(form_time)

        # Kết nối
        self.cb_loai.currentTextChanged.connect(self._on_loai_changed)
        self.chk_bd.toggled.connect(self.de_bd.setEnabled)
        self.chk_kt.toggled.connect(self.de_kt.setEnabled)
        self.chk_luot.toggled.connect(self.sp_luot.setEnabled)

        self._on_loai_changed(self.cb_loai.currentText())
        self._on_kieu_changed(self.cb_kieu.currentText())

        btn = _btn("💾  Lưu Khuyến Mãi", "#27AE60", 44)
        btn.clicked.connect(self._save)
        root.addWidget(btn)

        if km_id:
            self._load()

    def _load_products(self, cb: QComboBox):
        s = get_session()
        try:
            sps = s.query(SanPham).filter(SanPham.trang_thai == "Đang bán").order_by(SanPham.ten_sp).all()
            for sp in sps:
                cb.addItem(sp.ten_sp, sp.id)
        finally:
            s.close()

    def _on_loai_changed(self, loai):
        is_sp  = (loai == "SanPham")
        is_mua = (loai == "MuaXTangY")

        # Hiện section tương ứng
        self.sec_giam.setVisible(not is_mua)
        self.sec_mua.setVisible(is_mua)

        # Dòng sản phẩm chỉ hiện khi SanPham
        self.lbl_sp.setVisible(is_sp)
        self.cb_sp.setVisible(is_sp)

    def _on_kieu_changed(self, kieu):
        is_pt = (kieu == "PhanTram")
        self.lbl_tran.setVisible(is_pt)
        self.sp_tran.setVisible(is_pt)
        if is_pt:
            self.sp_gt.setSuffix(" %")
        else:
            self.sp_gt.setSuffix(" đ")

    def _load(self):
        s = get_session()
        km = s.query(KhuyenMai).get(self.km_id); s.close()
        if not km: return

        self.txt_ten.setText(km.ten_km or "")
        self.txt_code.setText(km.ma_code or "")
        self.cb_tt.setCurrentText(km.trang_thai or "Đang chạy")
        self.cb_loai.setCurrentText(km.loai_km or "DonHang")

        if km.loai_km == "MuaXTangY":
            # Nạp sản phẩm mua
            if km.ma_sp:
                idx = self.cb_sp_mua.findData(km.ma_sp)
                if idx >= 0: self.cb_sp_mua.setCurrentIndex(idx)
            self.sp_so_mua.setValue(km.so_luong_mua or 2)
            # Nạp sản phẩm tặng
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

        if km.ngay_bat_dau:
            self.chk_bd.setChecked(True)
            self.de_bd.setDate(QDate(km.ngay_bat_dau.year, km.ngay_bat_dau.month, km.ngay_bat_dau.day))
        if km.ngay_ket_thuc:
            self.chk_kt.setChecked(True)
            self.de_kt.setDate(QDate(km.ngay_ket_thuc.year, km.ngay_ket_thuc.month, km.ngay_ket_thuc.day))
        if km.so_luot_toi_da:
            self.chk_luot.setChecked(True)
            self.sp_luot.setValue(km.so_luot_toi_da)

    def _save(self):
        ten = self.txt_ten.text().strip()
        if not ten:
            QMessageBox.warning(self, "Thiếu", "Tên khuyến mãi là bắt buộc!"); return

        code = self.txt_code.text().strip() or None
        loai = self.cb_loai.currentText()
        tt   = self.cb_tt.currentText()

        ngay_bd = None
        if self.chk_bd.isChecked():
            qd = self.de_bd.date(); ngay_bd = date(qd.year(), qd.month(), qd.day())
        ngay_kt = None
        if self.chk_kt.isChecked():
            qd = self.de_kt.date(); ngay_kt = date(qd.year(), qd.month(), qd.day())
        luot = self.sp_luot.value() if self.chk_luot.isChecked() else None

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

            if loai == "MuaXTangY":
                km.kieu_giam      = None
                km.gia_tri_giam   = None
                km.toi_da_giam    = None
                km.ma_sp          = self.cb_sp_mua.currentData()
                km.so_luong_mua   = self.sp_so_mua.value()
                km.ma_sp_tang     = self.cb_sp_tang.currentData()
                km.so_luong_tang  = self.sp_so_tang.value()
                km.dk_tong_tien_tu = self.sp_dk_mua.value()
            else:
                km.kieu_giam      = self.cb_kieu.currentText()
                km.gia_tri_giam   = self.sp_gt.value()
                km.toi_da_giam    = self.sp_tran.value() or None
                km.dk_tong_tien_tu = self.sp_dk.value()
                km.ma_sp          = self.cb_sp.currentData() if loai == "SanPham" else None
                km.so_luong_mua   = None
                km.ma_sp_tang     = None
                km.so_luong_tang  = None

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
        self.resize(1000, 600)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Tiêu đề
        root.addWidget(_lbl("🎉 QUẢN LÝ CHƯƠNG TRÌNH KHUYẾN MÃI", "#E67E22", 18, True))

        # Toolbar
        bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm theo tên hoặc mã code...")
        self.txt_search.textChanged.connect(self._load)
        bar.addWidget(self.txt_search)

        self.btn_add  = _btn("➕ Thêm KM",    "#27AE60")
        self.btn_edit = _btn("✏️ Sửa",        "#2980B9")
        self.btn_stop = _btn("⏸ Tạm dừng",   "#E67E22")
        self.btn_del  = _btn("🗑 Xóa",        "#C0392B")
        for b in [self.btn_add, self.btn_edit, self.btn_stop, self.btn_del]:
            bar.addWidget(b)
        root.addLayout(bar)

        # Bảng
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Tên Khuyến Mãi", "Mã Code", "Loại",
            "Giảm", "Điều Kiện", "Hết Hạn", "Trạng Thái"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed); self.table.setColumnWidth(0, 40)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        for c in range(3, 8): hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemDoubleClicked.connect(lambda _: self._edit())
        root.addWidget(self.table)

        # Lịch sử
        self.lbl_history = _lbl("", "#A1A1AA", 12)
        root.addWidget(self.lbl_history)

        # Nút đóng
        btn_close = _btn("Đóng", "#34495E", 38)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close, alignment=Qt.AlignRight)

        # Kết nối
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_stop.clicked.connect(self._toggle_status)
        self.btn_del.clicked.connect(self._delete)
        self.table.itemSelectionChanged.connect(self._on_select)

        self._load()

    def _load(self, keyword=""):
        kw = self.txt_search.text().strip() if hasattr(self, 'txt_search') else keyword
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

                id_item = QTableWidgetItem(str(km.id))
                id_item.setData(Qt.UserRole, km.id)
                self.table.setItem(i, 0, id_item)
                self.table.setItem(i, 1, QTableWidgetItem(km.ten_km or ""))

                code_item = QTableWidgetItem(km.ma_code or "—")
                code_item.setForeground(QColor("#F1C40F"))
                self.table.setItem(i, 2, code_item)

                loai_map = {"DonHang": "Đơn hàng", "SanPham": "Sản phẩm", "MuaXTangY": "Mua X Tặng Y"}
                self.table.setItem(i, 3, QTableWidgetItem(loai_map.get(km.loai_km, km.loai_km or "")))

                if km.loai_km == "MuaXTangY":
                    gt_str = f"Mua {km.so_luong_mua or 1} → Tặng {km.so_luong_tang or 1}"
                elif km.kieu_giam == "PhanTram":
                    gt_str = f"{int(km.gia_tri_giam or 0)}%"
                    if km.toi_da_giam:
                        gt_str += f" (tối đa {int(km.toi_da_giam):,}đ)"
                else:
                    gt_str = f"{int(km.gia_tri_giam or 0):,} đ"
                gt_item = QTableWidgetItem(gt_str)
                gt_item.setForeground(QColor("#2ECC71"))
                self.table.setItem(i, 4, gt_item)

                dk_str = f"Từ {int(km.dk_tong_tien_tu or 0):,}đ" if km.dk_tong_tien_tu else "Không"
                self.table.setItem(i, 5, QTableWidgetItem(dk_str))

                het = km.ngay_ket_thuc.strftime("%d/%m/%Y") if km.ngay_ket_thuc else "Không hạn"
                self.table.setItem(i, 6, QTableWidgetItem(het))

                tt = km.trang_thai or "Đang chạy"
                tt_item = QTableWidgetItem(tt)
                tt_color = {"Đang chạy": "#2ECC71", "Tạm dừng": "#F1C40F", "Hết hạn": "#E74C3C"}.get(tt, "white")
                tt_item.setForeground(QColor(tt_color))
                self.table.setItem(i, 7, tt_item)
        finally:
            s.close()

    def _sel_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một khuyến mãi!"); return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _add(self):
        if KhuyenMaiForm(parent=self).exec():
            self._load()

    def _edit(self):
        km_id = self._sel_id()
        if km_id and KhuyenMaiForm(km_id, self).exec():
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
        finally:
            s.close()
        self._load()

    def _delete(self):
        km_id = self._sel_id()
        if not km_id: return
        row = self.table.currentRow()
        ten = self.table.item(row, 1).text()
        r = QMessageBox.question(
            self, "Xóa?", f"Xóa khuyến mãi <b>{ten}</b>?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r != QMessageBox.Yes: return
        s = get_session()
        try:
            km = s.query(KhuyenMai).get(km_id)
            if km: s.delete(km); s.commit()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()
        self._load()

    def _on_select(self):
        row = self.table.currentRow()
        if row < 0: return
        km_id = self.table.item(row, 0).data(Qt.UserRole)
        s = get_session()
        try:
            count = s.query(NhatKyKhuyenMai).filter_by(ma_km=km_id).count()
            self.lbl_history.setText(f"  📊 Đã dùng: {count} lần")
        finally:
            s.close()