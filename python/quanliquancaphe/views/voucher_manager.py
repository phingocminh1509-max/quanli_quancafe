"""
views/voucher_manager.py
══════════════════════════════════════════════════════════════════
Quản lý Voucher & Điểm Thưởng — tích hợp với KhachHang

3 tab chính:
  1. Voucher Chung   — Admin phát voucher theo đợt cho nhiều KH
  2. Voucher Khách   — Xem/phát voucher riêng từng khách
  3. Đổi Điểm        — Giao diện đổi điểm lấy voucher cho KH
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QWidget, QTabWidget, QComboBox, QLineEdit,
    QDoubleSpinBox, QSpinBox, QDateEdit, QMessageBox, QFormLayout,
    QCheckBox, QGroupBox, QScrollArea,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont

from database.db_config import get_session
from database.models import KhachHang, Voucher, LichSuDiemKH
from controllers.loyalty_controller import (
    BANG_DOI_DIEM,
    lay_bang_doi_diem, lay_voucher_cua_kh, lay_lich_su_diem,
    phat_voucher_chung, doi_diem_lay_voucher,
    lay_thong_tin_kh,
)

# ── Màu sắc ──────────────────────────────────────────────────────
C_BG     = "#1A1A2E"
C_PANEL  = "#252540"
C_CARD   = "#2E2E50"
C_BORDER = "#333360"
C_ACCENT = "#9B59B6"
C_GREEN  = "#27AE60"
C_ORANGE = "#E67E22"
C_RED    = "#E74C3C"
C_YELLOW = "#F1C40F"
C_BLUE   = "#3498DB"
C_TEXT   = "#E8E8F0"
C_MUTED  = "#7070A0"

STYLE = f"""
QDialog, QWidget   {{ background:{C_BG}; color:{C_TEXT}; }}
QTabWidget::pane   {{ border:none; background:{C_BG}; }}
QTabBar::tab       {{ background:{C_PANEL}; color:{C_MUTED}; padding:10px 22px;
    border-radius:6px 6px 0 0; font-weight:bold; font-size:13px; }}
QTabBar::tab:selected {{ background:{C_ACCENT}; color:white; }}
QTabBar::tab:hover    {{ background:{C_CARD}; color:white; }}
QFrame      {{ background:{C_PANEL}; border-radius:10px; border:none; }}
QTableWidget {{ background:{C_CARD}; border:none; border-radius:8px;
    gridline-color:{C_BORDER}; color:{C_TEXT}; font-size:13px; }}
QTableWidget::item {{ padding:8px 6px; border-bottom:1px solid {C_BORDER}; }}
QTableWidget::item:selected {{ background:{C_ACCENT}; color:white; }}
QHeaderView::section {{ background:{C_PANEL}; color:{C_MUTED}; padding:9px 6px;
    border:none; font-weight:bold; font-size:12px;
    border-bottom:2px solid {C_BORDER}; }}
QLineEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background:{C_CARD}; border:1px solid {C_BORDER}; border-radius:6px;
    padding:7px 10px; color:{C_TEXT}; font-size:13px; }}
QLineEdit:focus, QDateEdit:focus {{ border-color:{C_ACCENT}; }}
QComboBox::drop-down {{ border:none; }}
QComboBox QAbstractItemView {{ background:{C_CARD}; color:{C_TEXT};
    selection-background-color:{C_ACCENT}; }}
QGroupBox {{ border:1px solid {C_BORDER}; border-radius:8px; margin-top:10px;
    padding-top:10px; color:{C_MUTED}; font-size:12px; font-weight:bold; }}
QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; }}
QScrollBar:vertical {{ background:{C_BG}; width:6px; border-radius:3px; }}
QScrollBar::handle:vertical {{ background:{C_BORDER}; border-radius:3px; }}
"""


def _lbl(text="", color=C_TEXT, size=13, bold=False):
    l = QLabel(text)
    l.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'bold' if bold else 'normal'};"
        "background:transparent;border:none;"
    )
    l.setWordWrap(True)
    return l


def _btn(text, color=C_ACCENT, h=36):
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:white;font-weight:bold;"
        f"border-radius:8px;font-size:13px;padding:0 14px;border:none;}}"
        f"QPushButton:hover{{background:{color}CC;}}"
        f"QPushButton:pressed{{background:{color}88;}}"
    )
    return b


def _make_table(headers, col_widths=None):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    hh = t.horizontalHeader()
    for i in range(len(headers)):
        hh.setSectionResizeMode(i, QHeaderView.Stretch)
    if col_widths:
        for col, w in col_widths.items():
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            t.setColumnWidth(col, w)
    return t


def _ti(text, color=C_TEXT, align=Qt.AlignLeft, bold=False):
    it = QTableWidgetItem(str(text))
    it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    it.setTextAlignment(align | Qt.AlignVCenter)
    it.setForeground(QColor(color))
    if bold:
        f = it.font(); f.setBold(True); it.setFont(f)
    return it


def _status_color(trang_thai):
    return {
        "Chưa dùng": C_GREEN,
        "Đã dùng":   C_MUTED,
        "Hết hạn":   C_RED,
    }.get(trang_thai, C_TEXT)


# ══════════════════════════════════════════════════════════════════
# TAB 1 — VOUCHER CHUNG (phát hàng loạt)
# ══════════════════════════════════════════════════════════════════
class _TabVoucherChung(QWidget):
    def __init__(self, ma_nv: int):
        super().__init__()
        self.ma_nv = ma_nv
        self.setStyleSheet("background:transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ── Form phát voucher ────────────────────────────────────
        grp = QGroupBox("Phát Voucher Chung cho Khách Hàng")
        grp.setStyleSheet(
            f"QGroupBox{{border:1px solid {C_BORDER};border-radius:8px;"
            f"margin-top:10px;color:{C_ACCENT};font-size:13px;font-weight:bold;}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:12px;padding:0 4px;"
            f"background:{C_BG};}}"
        )
        form_lay = QFormLayout(grp)
        form_lay.setSpacing(10)
        form_lay.setContentsMargins(14, 18, 14, 14)

        # Chọn KH
        self.cmb_kh = QComboBox()
        self.cmb_kh.setMinimumWidth(220)
        self._load_kh()
        form_lay.addRow("Khách hàng:", self.cmb_kh)

        # Tên voucher
        self.txt_ten = QLineEdit()
        self.txt_ten.setPlaceholderText("vd: Sinh nhật tháng 5, Khách VIP...")
        form_lay.addRow("Tên voucher:", self.txt_ten)

        # Loại giảm
        self.cmb_loai = QComboBox()
        self.cmb_loai.addItems(["Tiền mặt (đ)", "Phần trăm (%)"])
        self.cmb_loai.currentIndexChanged.connect(self._on_loai_change)
        form_lay.addRow("Loại giảm:", self.cmb_loai)

        # Giá trị giảm
        self.spn_giam = QDoubleSpinBox()
        self.spn_giam.setRange(0, 10_000_000)
        self.spn_giam.setSingleStep(5_000)
        self.spn_giam.setDecimals(0)
        self.spn_giam.setSuffix(" đ")
        form_lay.addRow("Giá trị giảm:", self.spn_giam)

        # Tối đa giảm (chỉ dùng khi %)
        self.spn_toidagiam = QDoubleSpinBox()
        self.spn_toidagiam.setRange(0, 10_000_000)
        self.spn_toidagiam.setSingleStep(5_000)
        self.spn_toidagiam.setDecimals(0)
        self.spn_toidagiam.setSuffix(" đ")
        self.spn_toidagiam.setToolTip("0 = không giới hạn")
        self.lbl_toida = _lbl("Tối đa giảm:")
        form_lay.addRow(self.lbl_toida, self.spn_toidagiam)

        # Điều kiện tối thiểu
        self.spn_dk = QDoubleSpinBox()
        self.spn_dk.setRange(0, 10_000_000)
        self.spn_dk.setSingleStep(10_000)
        self.spn_dk.setDecimals(0)
        self.spn_dk.setSuffix(" đ")
        form_lay.addRow("Đơn tối thiểu:", self.spn_dk)

        # Hạn dùng
        self.spn_han = QSpinBox()
        self.spn_han.setRange(1, 365)
        self.spn_han.setValue(30)
        self.spn_han.setSuffix(" ngày")
        form_lay.addRow("Hiệu lực:", self.spn_han)

        # Nút phát
        btn_phat = _btn("📤 Phát Voucher", C_ACCENT, 40)
        btn_phat.clicked.connect(self._phat_voucher)
        form_lay.addRow("", btn_phat)

        root.addWidget(grp)

        # ── Bảng voucher chung gần đây ───────────────────────────
        root.addWidget(_lbl("📋  Voucher vừa phát (50 gần nhất)", C_MUTED, 12, True))
        self.table = _make_table(
            ["Mã Code", "Khách hàng", "Tên Voucher", "Giá trị", "Hết hạn", "Trạng thái"],
            {0: 130, 4: 100, 5: 100}
        )
        root.addWidget(self.table, stretch=1)
        self._load_table()

        self._on_loai_change(0)

    def _on_loai_change(self, idx):
        is_pct = idx == 1
        self.lbl_toida.setVisible(is_pct)
        self.spn_toidagiam.setVisible(is_pct)
        if is_pct:
            self.spn_giam.setRange(1, 100)
            self.spn_giam.setSuffix(" %")
            self.spn_giam.setValue(10)
        else:
            self.spn_giam.setRange(0, 10_000_000)
            self.spn_giam.setSuffix(" đ")
            self.spn_giam.setSingleStep(5_000)

    def _load_kh(self):
        self.cmb_kh.clear()
        self._kh_ids = []
        s = get_session()
        try:
            khs = s.query(KhachHang).order_by(KhachHang.ten_kh).all()
            for kh in khs:
                self.cmb_kh.addItem(
                    f"{kh.ten_kh}  ({kh.so_dien_thoai or 'N/A'})  [{kh.hang_thanh_vien}]"
                )
                self._kh_ids.append(kh.id)
        finally:
            s.close()

    def _phat_voucher(self):
        if not self._kh_ids:
            QMessageBox.warning(self, "Thiếu thông tin", "Không có khách hàng nào.")
            return
        ten = self.txt_ten.text().strip()
        if not ten:
            QMessageBox.warning(self, "Thiếu thông tin", "Nhập tên voucher.")
            return

        idx = self.cmb_kh.currentIndex()
        ma_kh = self._kh_ids[idx]
        loai  = "PhanTram" if self.cmb_loai.currentIndex() == 1 else "TienMat"
        giam  = self.spn_giam.value()
        toida = self.spn_toidagiam.value() if loai == "PhanTram" else None
        dk    = self.spn_dk.value()
        han   = self.spn_han.value()

        ok, msg, code = phat_voucher_chung(
            ma_kh=ma_kh, ten_voucher=ten,
            loai_giam=loai, gia_tri_giam=giam,
            toi_da_giam=toida, dieu_kien_toi_thieu=dk,
            han_dung_ngay=han, ma_nv=self.ma_nv,
        )
        if ok:
            QMessageBox.information(self, "✅ Thành công", msg)
            self.txt_ten.clear()
            self._load_table()
        else:
            QMessageBox.critical(self, "Lỗi", msg)

    def _load_table(self):
        self.table.setRowCount(0)
        s = get_session()
        try:
            rows = (s.query(Voucher)
                    .filter(Voucher.ma_code.like("VQ-%"))
                    .order_by(Voucher.ngay_tao.desc())
                    .limit(50).all())
            for v in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, _ti(v.ma_code, C_BLUE, Qt.AlignCenter, True))
                kh_ten = v.khach_hang.ten_kh if v.khach_hang else "?"
                self.table.setItem(r, 1, _ti(kh_ten))
                self.table.setItem(r, 2, _ti(v.ten_voucher or ""))
                giam_str = (
                    f"{int(v.gia_tri_giam):,}đ"
                    if v.loai_giam == "TienMat"
                    else f"{int(v.gia_tri_giam)}%"
                )
                self.table.setItem(r, 3, _ti(giam_str, C_YELLOW, Qt.AlignCenter, True))
                han_str = v.ngay_het_han.strftime("%d/%m/%Y") if v.ngay_het_han else "∞"
                self.table.setItem(r, 4, _ti(han_str, C_MUTED, Qt.AlignCenter))
                sc = _status_color(v.trang_thai or "")
                self.table.setItem(r, 5, _ti(v.trang_thai or "", sc, Qt.AlignCenter, True))
        finally:
            s.close()


# ══════════════════════════════════════════════════════════════════
# TAB 2 — VOUCHER RIÊNG CỦA KHÁCH
# ══════════════════════════════════════════════════════════════════
class _TabVoucherKhach(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        self._ma_kh = None
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Tìm khách
        search_row = QHBoxLayout()
        search_row.addWidget(_lbl("Tìm khách:", C_MUTED, 12))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Tên hoặc SĐT...")
        self.txt_search.setFixedWidth(220)
        search_row.addWidget(self.txt_search)
        btn_search = _btn("🔍", C_BLUE, 34)
        btn_search.setFixedWidth(40)
        btn_search.clicked.connect(self._search_kh)
        search_row.addWidget(btn_search)
        self.cmb_kh = QComboBox()
        self.cmb_kh.setMinimumWidth(260)
        self.cmb_kh.currentIndexChanged.connect(self._on_kh_change)
        search_row.addWidget(self.cmb_kh)
        search_row.addStretch()
        root.addLayout(search_row)

        # Thông tin KH
        self.frm_kh = QFrame()
        self.frm_kh.setStyleSheet(
            f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}"
        )
        kh_lay = QHBoxLayout(self.frm_kh)
        kh_lay.setContentsMargins(16, 10, 16, 10)
        kh_lay.setSpacing(30)
        self.lbl_kh_ten   = _lbl("—", C_TEXT, 14, True)
        self.lbl_kh_hang  = _lbl("—", C_YELLOW, 13)
        self.lbl_kh_diem  = _lbl("0 điểm", C_ACCENT, 16, True)
        self.lbl_kh_vcr   = _lbl("0 voucher", C_GREEN, 13)
        for l in [self.lbl_kh_ten, self.lbl_kh_hang, self.lbl_kh_diem, self.lbl_kh_vcr]:
            kh_lay.addWidget(l)
        kh_lay.addStretch()
        root.addWidget(self.frm_kh)

        # Lọc hiển thị
        fil_row = QHBoxLayout()
        fil_row.addWidget(_lbl("Hiển thị:", C_MUTED, 12))
        self.chk_chi_con = QCheckBox("Chỉ còn hiệu lực")
        self.chk_chi_con.setStyleSheet(f"color:{C_TEXT};font-size:12px;")
        self.chk_chi_con.stateChanged.connect(self._load_voucher)
        fil_row.addWidget(self.chk_chi_con)
        fil_row.addStretch()
        root.addLayout(fil_row)

        # Bảng voucher
        self.tbl_vcr = _make_table(
            ["Mã Code", "Tên Voucher", "Loại", "Giá trị", "ĐK tối thiểu", "Hết hạn", "Trạng thái"],
            {0: 130, 2: 90, 3: 110, 5: 100, 6: 100}
        )
        root.addWidget(self.tbl_vcr, stretch=1)

        # Lịch sử điểm
        root.addWidget(_lbl("📜  Lịch sử tích/tiêu điểm", C_MUTED, 12, True))
        self.tbl_ls = _make_table(
            ["Thời gian", "Loại", "Điểm", "Mô tả", "Hóa đơn"],
            {0: 130, 1: 90, 2: 70, 4: 80}
        )
        self.tbl_ls.setMaximumHeight(180)
        root.addWidget(self.tbl_ls)

        self._load_all_kh()

    def _load_all_kh(self):
        self.cmb_kh.blockSignals(True)
        self.cmb_kh.clear()
        self._kh_ids = []
        s = get_session()
        try:
            khs = s.query(KhachHang).order_by(KhachHang.ten_kh).all()
            for kh in khs:
                self.cmb_kh.addItem(f"{kh.ten_kh}  ({kh.so_dien_thoai or 'N/A'})")
                self._kh_ids.append(kh.id)
        finally:
            s.close()
        self.cmb_kh.blockSignals(False)
        if self._kh_ids:
            self._on_kh_change(0)

    def _search_kh(self):
        q = self.txt_search.text().strip()
        if not q:
            self._load_all_kh()
            return
        self.cmb_kh.blockSignals(True)
        self.cmb_kh.clear()
        self._kh_ids = []
        s = get_session()
        try:
            khs = (s.query(KhachHang)
                   .filter(
                       (KhachHang.ten_kh.ilike(f"%{q}%")) |
                       (KhachHang.so_dien_thoai.ilike(f"%{q}%"))
                   ).all())
            for kh in khs:
                self.cmb_kh.addItem(f"{kh.ten_kh}  ({kh.so_dien_thoai or 'N/A'})")
                self._kh_ids.append(kh.id)
        finally:
            s.close()
        self.cmb_kh.blockSignals(False)
        if self._kh_ids:
            self._on_kh_change(0)
        else:
            QMessageBox.information(self, "Không tìm thấy", f"Không có KH nào khớp '{q}'")

    def _on_kh_change(self, idx):
        if not self._kh_ids or idx < 0:
            return
        self._ma_kh = self._kh_ids[idx]
        info = lay_thong_tin_kh(self._ma_kh)
        if info:
            self.lbl_kh_ten.setText(info["ten_kh"])
            self.lbl_kh_hang.setText(f"🏅 {info['hang']}")
            self.lbl_kh_diem.setText(f"⭐ {info['diem']:,} điểm")
            self.lbl_kh_vcr.setText(f"🎫 {info['voucher_con']} voucher còn hiệu lực")
        self._load_voucher()
        self._load_lich_su()

    def _load_voucher(self):
        if not self._ma_kh:
            return
        chi_con = self.chk_chi_con.isChecked()
        rows = lay_voucher_cua_kh(self._ma_kh, chi_con_hieu_luc=chi_con)
        self.tbl_vcr.setRowCount(0)
        for v in rows:
            r = self.tbl_vcr.rowCount()
            self.tbl_vcr.insertRow(r)
            prefix = "🎁" if v["ma_code"].startswith("VD") else "📤"
            self.tbl_vcr.setItem(r, 0, _ti(f"{prefix} {v['ma_code']}", C_BLUE, Qt.AlignCenter, True))
            self.tbl_vcr.setItem(r, 1, _ti(v["ten_voucher"] or ""))
            loai_str = "%" if v["loai_giam"] == "PhanTram" else "đ"
            self.tbl_vcr.setItem(r, 2, _ti(loai_str, C_MUTED, Qt.AlignCenter))
            giam_str = (
                f"{int(v['gia_tri_giam']):,}đ"
                if v["loai_giam"] == "TienMat"
                else f"{int(v['gia_tri_giam'])}%"
            )
            self.tbl_vcr.setItem(r, 3, _ti(giam_str, C_YELLOW, Qt.AlignRight, True))
            dk_str = f"{int(v['dk_toi_thieu']):,}đ" if v["dk_toi_thieu"] else "Không"
            self.tbl_vcr.setItem(r, 4, _ti(dk_str, C_MUTED, Qt.AlignCenter))
            self.tbl_vcr.setItem(r, 5, _ti(v["ngay_het_han"], C_MUTED, Qt.AlignCenter))
            sc = _status_color(v["trang_thai"])
            self.tbl_vcr.setItem(r, 6, _ti(v["trang_thai"], sc, Qt.AlignCenter, True))

    def _load_lich_su(self):
        if not self._ma_kh:
            return
        rows = lay_lich_su_diem(self._ma_kh, limit=30)
        self.tbl_ls.setRowCount(0)
        for row in rows:
            r = self.tbl_ls.rowCount()
            self.tbl_ls.insertRow(r)
            self.tbl_ls.setItem(r, 0, _ti(row["thoi_gian"], C_MUTED, Qt.AlignCenter))
            loai_c = C_GREEN if row["so_diem"] > 0 else C_RED
            self.tbl_ls.setItem(r, 1, _ti(row["loai"], loai_c, Qt.AlignCenter))
            sign = "+" if row["so_diem"] > 0 else ""
            self.tbl_ls.setItem(r, 2, _ti(f"{sign}{row['so_diem']}", loai_c, Qt.AlignCenter, True))
            self.tbl_ls.setItem(r, 3, _ti(row["mo_ta"]))
            self.tbl_ls.setItem(r, 4, _ti(row["ma_hd"], C_MUTED, Qt.AlignCenter))


# ══════════════════════════════════════════════════════════════════
# TAB 3 — ĐỔI ĐIỂM LẤY VOUCHER
# ══════════════════════════════════════════════════════════════════
class _TabDoiDiem(QWidget):
    def __init__(self, ma_nv: int):
        super().__init__()
        self.ma_nv  = ma_nv
        self._ma_kh = None
        self.setStyleSheet("background:transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # Chọn khách
        top = QHBoxLayout()
        top.addWidget(_lbl("Khách hàng:", C_MUTED, 12))
        self.cmb_kh = QComboBox()
        self.cmb_kh.setMinimumWidth(280)
        self.cmb_kh.currentIndexChanged.connect(self._on_kh_change)
        top.addWidget(self.cmb_kh)
        top.addStretch()
        root.addLayout(top)

        # Thông tin KH
        self.frm_info = QFrame()
        self.frm_info.setStyleSheet(
            f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}"
        )
        info_lay = QHBoxLayout(self.frm_info)
        info_lay.setContentsMargins(18, 12, 18, 12)
        info_lay.setSpacing(32)
        self.lbl_ten  = _lbl("—", C_TEXT, 14, True)
        self.lbl_hang = _lbl("—", C_YELLOW, 13)
        self.lbl_diem = _lbl("0 điểm", C_ACCENT, 20, True)
        for l in [self.lbl_ten, self.lbl_hang, self.lbl_diem]:
            info_lay.addWidget(l)
        info_lay.addStretch()
        root.addWidget(self.frm_info)

        # Bảng gói đổi điểm
        root.addWidget(_lbl("🎁  Chọn gói đổi điểm", C_ACCENT, 13, True))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent;}"
        )
        cards_w = QWidget()
        cards_w.setStyleSheet("background:transparent;")
        self.cards_lay = QVBoxLayout(cards_w)
        self.cards_lay.setSpacing(8)
        self.cards_lay.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(cards_w)
        root.addWidget(scroll, stretch=1)

        self._build_cards()
        self._load_kh()

    def _build_cards(self):
        gois = lay_bang_doi_diem()
        for g in gois:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:{C_CARD};border-radius:10px;"
                f"border:1px solid {C_BORDER};}}"
            )
            card.setFixedHeight(72)
            lay = QHBoxLayout(card)
            lay.setContentsMargins(16, 8, 16, 8)
            lay.setSpacing(16)

            # Icon
            ico = _lbl("🎫", C_TEXT, 22)
            ico.setFixedWidth(32)
            lay.addWidget(ico)

            # Thông tin
            info_v = QVBoxLayout()
            info_v.setSpacing(2)
            info_v.addWidget(_lbl(g["ten"], C_TEXT, 14, True))
            info_v.addWidget(_lbl(g["mo_ta"], C_MUTED, 12))
            lay.addLayout(info_v, stretch=1)

            # Điểm cần
            diem_lbl = _lbl(f"⭐ {g['diem']} điểm", C_YELLOW, 15, True)
            diem_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lay.addWidget(diem_lbl)

            # Nút đổi
            btn = _btn("Đổi ngay", C_ACCENT, 36)
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda _, idx=g["idx"]: self._doi_diem(idx))
            lay.addWidget(btn)

            self.cards_lay.addWidget(card)

        self.cards_lay.addStretch()

    def _load_kh(self):
        self.cmb_kh.blockSignals(True)
        self.cmb_kh.clear()
        self._kh_ids = []
        s = get_session()
        try:
            khs = s.query(KhachHang).order_by(KhachHang.ten_kh).all()
            for kh in khs:
                self.cmb_kh.addItem(
                    f"{kh.ten_kh}  ⭐{kh.diem_tich_luy or 0}đ  [{kh.hang_thanh_vien}]"
                )
                self._kh_ids.append(kh.id)
        finally:
            s.close()
        self.cmb_kh.blockSignals(False)
        if self._kh_ids:
            self._on_kh_change(0)

    def _on_kh_change(self, idx):
        if not self._kh_ids or idx < 0:
            return
        self._ma_kh = self._kh_ids[idx]
        info = lay_thong_tin_kh(self._ma_kh)
        if info:
            self.lbl_ten.setText(info["ten_kh"])
            self.lbl_hang.setText(f"🏅 {info['hang']}")
            self.lbl_diem.setText(f"⭐ {info['diem']:,} điểm")

    def _doi_diem(self, idx_goi: int):
        if not self._ma_kh:
            QMessageBox.warning(self, "Chưa chọn khách", "Vui lòng chọn khách hàng.")
            return

        info = lay_thong_tin_kh(self._ma_kh)
        goi  = lay_bang_doi_diem()[idx_goi]

        if (info["diem"] if info else 0) < goi["diem"]:
            QMessageBox.warning(
                self, "Không đủ điểm",
                f"Cần {goi['diem']} điểm, khách chỉ có {info['diem'] if info else 0} điểm."
            )
            return

        confirm = QMessageBox.question(
            self, "Xác nhận đổi điểm",
            f"Đổi {goi['diem']} điểm → {goi['ten']}\n"
            f"Khách: {info['ten_kh']}\n\nXác nhận?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        ok, msg, code = doi_diem_lay_voucher(
            ma_kh=self._ma_kh,
            idx_bang_doi=idx_goi,
            ma_nv_thuc_hien=self.ma_nv,
        )
        if ok:
            QMessageBox.information(self, "✅ Đổi điểm thành công", msg)
            self._load_kh()  # reload để cập nhật điểm
            # Cập nhật lại idx
            for i, kid in enumerate(self._kh_ids):
                if kid == self._ma_kh:
                    self.cmb_kh.setCurrentIndex(i)
                    self._on_kh_change(i)
                    break
        else:
            QMessageBox.critical(self, "Lỗi", msg)


# ══════════════════════════════════════════════════════════════════
# DIALOG CHÍNH
# ══════════════════════════════════════════════════════════════════
class VoucherManagerDialog(QDialog):
    def __init__(self, parent=None, ma_nv: int = None):
        super().__init__(parent)
        self.setWindowTitle("🎫 Quản lý Voucher & Điểm Thưởng")
        self.resize(1000, 700)
        self.setMinimumSize(860, 580)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl("🎫  VOUCHER & ĐIỂM THƯỞNG", C_ACCENT, 18, True))
        hdr.addStretch()
        btn_close = _btn("✖ Đóng", "#555577", 36)
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.accept)
        hdr.addWidget(btn_close)
        root.addLayout(hdr)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(_TabVoucherChung(ma_nv or 0), "📤  Voucher Chung")
        self.tabs.addTab(_TabVoucherKhach(),             "🎫  Voucher Khách")
        self.tabs.addTab(_TabDoiDiem(ma_nv or 0),        "⭐  Đổi Điểm")
        root.addWidget(self.tabs, stretch=1)