"""
views/system_log.py
══════════════════════════════════════════════════════════════════
3 tab — chỉ Admin & Quản lý xem được:

  Tab 0 │ 🔐 Nhật Ký Đăng Nhập
           Ai · Làm gì (đăng nhập/xuất) · Khi nào · Kết quả
           Lọc: nhân viên / kết quả / ngày

  Tab 1 │ 👤 Nhật Ký Nhân Viên
           Ai · Làm gì · Khi nào · Ở đâu · Kết quả (5 cột đầy đủ)
           Lọc: nhân viên / hành động / kết quả / ngày

  Tab 2 │ 🏷️ Nhật Ký Khuyến Mãi
           Ai áp dụng · KM nào · Hóa đơn · Khách · Tiền giảm
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QAbstractItemView, QLineEdit, QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QColor, QFont

from database.db_config import get_session
from database.models import (
    NhatKyDangNhap, NhatKyHoatDong, NhatKyKhuyenMai,
    NhanVien, KhuyenMai, KhachHang,
)

# ── Ghi log (import ở nơi khác dùng) ────────────────────────────────────────
from database.db_config import ghi_nhat_ky_dang_nhap, ghi_nhat_ky_hoat_dong  # noqa: F401

# ── Style ────────────────────────────────────────────────────────────────────
STYLE = """
QDialog,QWidget{background-color:#1E1E2E;color:white;}
QTabWidget::pane{border:none;}
QTabBar::tab{background:#2D2D3F;color:#A1A1AA;padding:10px 20px;
    border-radius:6px 6px 0 0;font-weight:bold;font-size:13px;}
QTabBar::tab:selected{background:#3498DB;color:white;}
QTabBar::tab:hover{background:#3E3E55;color:white;}
QTableWidget{background:#2D2D3F;border:none;border-radius:8px;
    gridline-color:#3E3E55;color:white;font-size:12px;}
QTableWidget::item{padding:7px;border-bottom:1px solid #3E3E55;}
QTableWidget::item:selected{background:#3498DB;}
QHeaderView::section{background:#1A1A24;color:#A1A1AA;
    padding:9px;border:none;font-weight:bold;font-size:12px;}
QComboBox,QDateEdit,QLineEdit{background:#2D2D3F;border:1px solid #3E3E55;
    border-radius:6px;padding:5px 8px;color:white;font-size:12px;}
QComboBox::drop-down{border:none;}
QComboBox QAbstractItemView{background:#2D2D3F;color:white;
    selection-background-color:#3498DB;}
QScrollBar:vertical{background:#1A1A24;width:7px;border-radius:4px;}
QScrollBar::handle:vertical{background:#3E3E55;border-radius:4px;}
"""

# Màu kết quả
KQ_COLOR = {
    "Thành công":    "#2ECC71",
    "Sai mật khẩu": "#E74C3C",
    "Tài khoản khóa":"#E74C3C",
    "Thất bại":      "#E74C3C",
    "Cảnh báo":      "#F1C40F",
}

def _btn(t, c="#2980B9", h=32):
    b = QPushButton(t); b.setMinimumHeight(h)
    b.setStyleSheet(
        f"background:{c};color:white;font-weight:bold;"
        f"border-radius:6px;font-size:12px;padding:0 10px;"
    )
    return b

def _lbl(t, c="white", s=12, bold=False):
    l = QLabel(t)
    l.setStyleSheet(f"color:{c};font-size:{s}px;" + ("font-weight:bold;" if bold else ""))
    return l

def _sep():
    """Đường kẻ dọc phân cách."""
    f = QFrame(); f.setFrameShape(QFrame.VLine)
    f.setStyleSheet("color:#3E3E55;"); return f


# ── Load danh sách NV cho combobox ──────────────────────────────────────────
def _load_nv_combo(cb: QComboBox, cur_id=None):
    cb.blockSignals(True)
    cb.clear(); cb.addItem("Tất cả", None)
    s = get_session()
    try:
        for nv in s.query(NhanVien).order_by(NhanVien.ten_nv).all():
            cb.addItem(nv.ten_nv, nv.id)
    finally:
        s.close()
    cb.blockSignals(False)
    if cur_id:
        idx = cb.findData(cur_id)
        if idx >= 0: cb.setCurrentIndex(idx)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 0 — NHẬT KÝ ĐĂNG NHẬP  (thay "Nhật ký Hệ thống")
# Cột: Khi nào · Nhân viên · Hành động · Kết quả · Ghi chú
# ═══════════════════════════════════════════════════════════════════════════════
class LoginLogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setSpacing(8)

        # ── Bộ lọc ──────────────────────────────────────────────
        bar = QHBoxLayout(); bar.setSpacing(6)

        bar.addWidget(_lbl("Nhân viên:"))
        self.cb_nv = QComboBox(); self.cb_nv.setFixedWidth(160)
        bar.addWidget(self.cb_nv)

        bar.addWidget(_sep())
        bar.addWidget(_lbl("Kết quả:"))
        self.cb_kq = QComboBox(); self.cb_kq.setFixedWidth(150)
        self.cb_kq.addItems(["Tất cả", "Thành công", "Sai mật khẩu",
                              "Tài khoản khóa", "Thất bại"])
        bar.addWidget(self.cb_kq)

        bar.addWidget(_sep())
        bar.addWidget(_lbl("Hành động:"))
        self.cb_hd = QComboBox(); self.cb_hd.setFixedWidth(130)
        self.cb_hd.addItems(["Tất cả", "Đăng nhập", "Đăng xuất"])
        bar.addWidget(self.cb_hd)

        bar.addWidget(_sep())
        bar.addWidget(_lbl("Từ:"))
        self.de_from = QDateEdit(QDate.currentDate().addDays(-7))
        self.de_from.setCalendarPopup(True); self.de_from.setDisplayFormat("dd/MM/yyyy")
        bar.addWidget(self.de_from)
        bar.addWidget(_lbl("→"))
        self.de_to = QDateEdit(QDate.currentDate())
        self.de_to.setCalendarPopup(True); self.de_to.setDisplayFormat("dd/MM/yyyy")
        bar.addWidget(self.de_to)

        bar.addWidget(_sep())
        btn_loc = _btn("🔍 Lọc", "#2980B9")
        btn_loc.clicked.connect(self.load)
        bar.addWidget(btn_loc)

        btn_r = _btn("🔄", "#16A085"); btn_r.setFixedWidth(36)
        btn_r.clicked.connect(self.load); bar.addWidget(btn_r)

        btn_xoa = _btn("🗑 Xóa", "#C0392B")
        btn_xoa.clicked.connect(self._clear)
        bar.addWidget(btn_xoa)
        bar.addStretch()
        v.addLayout(bar)

        # ── Thống kê nhanh ──────────────────────────────────────
        stat_bar = QHBoxLayout()
        self.lbl_total    = _lbl("", "#3498DB", 12, True)
        self.lbl_success  = _lbl("", "#2ECC71", 12)
        self.lbl_fail     = _lbl("", "#E74C3C", 12)
        self.lbl_update   = _lbl("", "#A1A1AA", 11)
        for w in [self.lbl_total, self.lbl_success, self.lbl_fail, self.lbl_update]:
            stat_bar.addWidget(w)
        stat_bar.addStretch()
        v.addLayout(stat_bar)

        # ── Bảng 5 cột ──────────────────────────────────────────
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["🕐 Thời Gian", "👤 Nhân Viên", "🔑 Hành Động", "✅ Kết Quả", "📝 Ghi Chú"]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(STYLE + "QTableWidget{alternate-background-color:#252535;}")
        v.addWidget(self.table)

        # Auto-refresh 15 giây
        self._timer = QTimer(self)
        self._timer.setInterval(15_000)
        self._timer.timeout.connect(self.load)

        _load_nv_combo(self.cb_nv)
        self.load()

    def showEvent(self, e):
        super().showEvent(e)
        _load_nv_combo(self.cb_nv, self.cb_nv.currentData())
        self.load(); self._timer.start()

    def hideEvent(self, e):
        super().hideEvent(e); self._timer.stop()

    def load(self):
        self.table.setRowCount(0)
        ma_nv = self.cb_nv.currentData()
        kq    = self.cb_kq.currentText()
        hd    = self.cb_hd.currentText()
        qdf   = self.de_from.date(); qdt = self.de_to.date()
        d0    = datetime(qdf.year(), qdf.month(), qdf.day(), 0, 0, 0)
        d1    = datetime(qdt.year(), qdt.month(), qdt.day(), 23, 59, 59)

        s = get_session()
        try:
            q = s.query(NhatKyDangNhap).filter(
                NhatKyDangNhap.thoi_gian >= d0,
                NhatKyDangNhap.thoi_gian <= d1,
            )
            if ma_nv: q = q.filter(NhatKyDangNhap.ma_nv == ma_nv)
            if kq != "Tất cả": q = q.filter(NhatKyDangNhap.ket_qua == kq)
            if hd != "Tất cả": q = q.filter(NhatKyDangNhap.hanh_dong == hd)
            logs = q.order_by(NhatKyDangNhap.thoi_gian.desc()).limit(500).all()

            # Thống kê
            n_ok   = sum(1 for l in logs if l.ket_qua == "Thành công")
            n_fail = len(logs) - n_ok
            self.lbl_total.setText(f"  📊 Tổng: {len(logs)} bản ghi  ")
            self.lbl_success.setText(f"  ✅ Thành công: {n_ok}  ")
            self.lbl_fail.setText(f"  ❌ Thất bại: {n_fail}  ")
            self.lbl_update.setText(f"  Cập nhật: {datetime.now().strftime('%H:%M:%S')}")

            # Đổ vào bảng
            nv_cache: dict[int, str] = {}
            for i, log in enumerate(logs):
                self.table.insertRow(i)
                self.table.setRowHeight(i, 34)

                # Cột 0: Khi nào
                tg = log.thoi_gian.strftime("%H:%M:%S  %d/%m/%Y") if log.thoi_gian else "—"
                tg_item = QTableWidgetItem(tg)
                tg_item.setForeground(QColor("#A1A1AA"))
                self.table.setItem(i, 0, tg_item)

                # Cột 1: Nhân viên (dùng cache tránh query N lần)
                if log.ma_nv:
                    if log.ma_nv not in nv_cache:
                        nv = s.query(NhanVien).get(log.ma_nv)
                        nv_cache[log.ma_nv] = nv.ten_nv if nv else "?"
                    nv_str = nv_cache[log.ma_nv]
                else:
                    nv_str = log.ten_dang_nhap or "Không xác định"
                nv_item = QTableWidgetItem(nv_str)
                nv_item.setForeground(QColor("#ECF0F1"))
                f = nv_item.font(); f.setBold(True); nv_item.setFont(f)
                self.table.setItem(i, 1, nv_item)

                # Cột 2: Hành động
                hd_item = QTableWidgetItem(log.hanh_dong or "")
                hd_color = "#3498DB" if log.hanh_dong == "Đăng nhập" else "#E67E22"
                hd_item.setForeground(QColor(hd_color))
                self.table.setItem(i, 2, hd_item)

                # Cột 3: Kết quả (màu nổi bật)
                kq_str  = log.ket_qua or "—"
                kq_item = QTableWidgetItem(kq_str)
                kq_item.setForeground(QColor(KQ_COLOR.get(kq_str, "#A1A1AA")))
                f2 = kq_item.font(); f2.setBold(kq_str != "Thành công"); kq_item.setFont(f2)
                self.table.setItem(i, 3, kq_item)

                # Cột 4: Ghi chú
                self.table.setItem(i, 4, QTableWidgetItem(log.ghi_chu or ""))
        finally:
            s.close()

    def _clear(self):
        r = QMessageBox.question(
            self.window(), "Xác nhận",
            "Xóa toàn bộ nhật ký đăng nhập?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r != QMessageBox.Yes: return
        s = get_session()
        try: s.query(NhatKyDangNhap).delete(); s.commit()
        finally: s.close()
        self.load()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NHẬT KÝ NHÂN VIÊN  (5 cột đầy đủ)
# Cột: Khi nào · Ai · Làm gì · Ở đâu · Kết quả + Mô tả
# ═══════════════════════════════════════════════════════════════════════════════
class StaffLogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setSpacing(8)

        # ── Bộ lọc ──────────────────────────────────────────────
        bar = QHBoxLayout(); bar.setSpacing(6)

        bar.addWidget(_lbl("Nhân viên:"))
        self.cb_nv = QComboBox(); self.cb_nv.setFixedWidth(160)
        bar.addWidget(self.cb_nv)

        bar.addWidget(_sep())
        bar.addWidget(_lbl("Hành động:"))
        self.txt_hd = QLineEdit(); self.txt_hd.setPlaceholderText("Tìm hành động…")
        self.txt_hd.setFixedWidth(150)
        bar.addWidget(self.txt_hd)

        bar.addWidget(_sep())
        bar.addWidget(_lbl("Kết quả:"))
        self.cb_kq = QComboBox(); self.cb_kq.setFixedWidth(140)
        self.cb_kq.addItems(["Tất cả", "Thành công", "Thất bại", "Cảnh báo"])
        bar.addWidget(self.cb_kq)

        bar.addWidget(_sep())
        bar.addWidget(_lbl("Từ:"))
        self.de_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.de_from.setCalendarPopup(True); self.de_from.setDisplayFormat("dd/MM/yyyy")
        bar.addWidget(self.de_from)
        bar.addWidget(_lbl("→"))
        self.de_to = QDateEdit(QDate.currentDate())
        self.de_to.setCalendarPopup(True); self.de_to.setDisplayFormat("dd/MM/yyyy")
        bar.addWidget(self.de_to)

        bar.addWidget(_sep())
        btn_loc = _btn("🔍 Lọc", "#2980B9")
        btn_loc.clicked.connect(self.load); bar.addWidget(btn_loc)
        btn_r = _btn("🔄", "#16A085"); btn_r.setFixedWidth(36)
        btn_r.clicked.connect(self._reload_all); bar.addWidget(btn_r)
        bar.addStretch()
        v.addLayout(bar)

        # ── Thống kê ────────────────────────────────────────────
        stat_bar = QHBoxLayout()
        self.lbl_count  = _lbl("", "#3498DB", 12, True)
        self.lbl_update = _lbl("", "#A1A1AA", 11)
        stat_bar.addWidget(self.lbl_count); stat_bar.addWidget(self.lbl_update)
        stat_bar.addStretch()
        v.addLayout(stat_bar)

        # ── Bảng 6 cột (5 chiều + mô tả) ───────────────────────
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "🕐 Thời Gian",
            "👤 Người Thao Tác",
            "⚡ Hành Động",
            "📍 Chức Năng",
            "✅ Kết Quả",
            "📝 Mô Tả Chi Tiết",
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(STYLE + "QTableWidget{alternate-background-color:#252535;}")
        v.addWidget(self.table)

        _load_nv_combo(self.cb_nv)
        self.load()

    def showEvent(self, e):
        super().showEvent(e); self._reload_all()

    def _reload_all(self):
        _load_nv_combo(self.cb_nv, self.cb_nv.currentData()); self.load()

    def load(self):
        self.table.setRowCount(0)
        ma_nv = self.cb_nv.currentData()
        hd_kw = self.txt_hd.text().strip()
        kq    = self.cb_kq.currentText()
        qdf   = self.de_from.date(); qdt = self.de_to.date()
        d0    = datetime(qdf.year(), qdf.month(), qdf.day(), 0, 0, 0)
        d1    = datetime(qdt.year(), qdt.month(), qdt.day(), 23, 59, 59)

        s = get_session()
        try:
            q = s.query(NhatKyHoatDong).filter(
                NhatKyHoatDong.thoi_gian >= d0,
                NhatKyHoatDong.thoi_gian <= d1,
            )
            if ma_nv: q = q.filter(NhatKyHoatDong.ma_nv == ma_nv)
            if hd_kw: q = q.filter(NhatKyHoatDong.hanh_dong.ilike(f"%{hd_kw}%"))
            if kq != "Tất cả": q = q.filter(NhatKyHoatDong.ket_qua == kq)
            logs = q.order_by(NhatKyHoatDong.thoi_gian.desc()).limit(500).all()

            self.lbl_count.setText(f"  📊 {len(logs)} bản ghi  ")
            self.lbl_update.setText(f"  Cập nhật: {datetime.now().strftime('%H:%M:%S')}")

            nv_cache: dict[int, str] = {}
            for i, log in enumerate(logs):
                self.table.insertRow(i)
                self.table.setRowHeight(i, 34)

                # Cột 0: Khi nào
                tg = log.thoi_gian.strftime("%H:%M  %d/%m/%Y") if log.thoi_gian else "—"
                tg_it = QTableWidgetItem(tg); tg_it.setForeground(QColor("#A1A1AA"))
                self.table.setItem(i, 0, tg_it)

                # Cột 1: Ai
                if log.ma_nv not in nv_cache:
                    nv = s.query(NhanVien).get(log.ma_nv)
                    nv_cache[log.ma_nv] = nv.ten_nv if nv else "?"
                nv_it = QTableWidgetItem(nv_cache[log.ma_nv])
                nv_it.setForeground(QColor("#ECF0F1"))
                f = nv_it.font(); f.setBold(True); nv_it.setFont(f)
                self.table.setItem(i, 1, nv_it)

                # Cột 2: Làm gì
                hd_it = QTableWidgetItem(log.hanh_dong or "")
                hd_it.setForeground(QColor("#3498DB"))
                self.table.setItem(i, 2, hd_it)

                # Cột 3: Ở đâu (module/màn hình)
                od_it = QTableWidgetItem(log.o_dau or "—")
                od_it.setForeground(QColor("#9B59B6"))
                self.table.setItem(i, 3, od_it)

                # Cột 4: Kết quả
                kq_str = log.ket_qua or "—"
                kq_it  = QTableWidgetItem(kq_str)
                kq_it.setForeground(QColor(KQ_COLOR.get(kq_str, "#A1A1AA")))
                f2 = kq_it.font(); f2.setBold(kq_str == "Thất bại"); kq_it.setFont(f2)
                self.table.setItem(i, 4, kq_it)

                # Cột 5: Mô tả chi tiết
                self.table.setItem(i, 5, QTableWidgetItem(log.mo_ta or ""))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — NHẬT KÝ KHUYẾN MÃI
# ═══════════════════════════════════════════════════════════════════════════════
class PromoLogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setSpacing(8)

        bar = QHBoxLayout(); bar.setSpacing(6)
        bar.addWidget(_lbl("Từ:"))
        self.de_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.de_from.setCalendarPopup(True); self.de_from.setDisplayFormat("dd/MM/yyyy")
        bar.addWidget(self.de_from)
        bar.addWidget(_lbl("→"))
        self.de_to = QDateEdit(QDate.currentDate())
        self.de_to.setCalendarPopup(True); self.de_to.setDisplayFormat("dd/MM/yyyy")
        bar.addWidget(self.de_to)
        btn_loc = _btn("🔍 Xem", "#2980B9"); btn_loc.clicked.connect(self.load)
        bar.addWidget(btn_loc)
        btn_r = _btn("🔄", "#16A085"); btn_r.setFixedWidth(36)
        btn_r.clicked.connect(self.load); bar.addWidget(btn_r)
        bar.addStretch()
        v.addLayout(bar)

        self.lbl_info = _lbl("", "#A1A1AA", 11); v.addWidget(self.lbl_info)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "🕐 Thời Gian", "🎉 Tên KM", "🧾 Hóa Đơn",
            "👥 Khách Hàng", "👤 Nhân Viên", "💸 Tiền Giảm"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in range(2, 6): hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        v.addWidget(self.table)
        self.load()

    def showEvent(self, e):
        super().showEvent(e); self.load()

    def load(self):
        self.table.setRowCount(0)
        qdf = self.de_from.date(); qdt = self.de_to.date()
        d0  = datetime(qdf.year(), qdf.month(), qdf.day(), 0, 0, 0)
        d1  = datetime(qdt.year(), qdt.month(), qdt.day(), 23, 59, 59)

        s = get_session()
        try:
            logs = (s.query(NhatKyKhuyenMai)
                    .filter(NhatKyKhuyenMai.thoi_gian >= d0,
                            NhatKyKhuyenMai.thoi_gian <= d1)
                    .order_by(NhatKyKhuyenMai.thoi_gian.desc())
                    .limit(500).all())

            total_giam = sum(l.so_tien_giam or 0 for l in logs)
            self.lbl_info.setText(
                f"  {len(logs)} lần sử dụng  •  "
                f"Tổng giảm: {int(total_giam):,} đ  •  "
                f"Cập nhật: {datetime.now().strftime('%H:%M:%S')}"
            )

            km_cache: dict[int, str] = {}
            kh_cache: dict[int, str] = {}
            nv_cache: dict[int, str] = {}

            for i, log in enumerate(logs):
                self.table.insertRow(i)
                self.table.setRowHeight(i, 34)

                tg = log.thoi_gian.strftime("%H:%M  %d/%m/%Y") if log.thoi_gian else "—"
                self.table.setItem(i, 0, QTableWidgetItem(tg))

                if log.ma_km not in km_cache:
                    km = s.query(KhuyenMai).get(log.ma_km)
                    km_cache[log.ma_km] = km.ten_km if km else "?"
                km_it = QTableWidgetItem(km_cache[log.ma_km])
                km_it.setForeground(QColor("#E67E22"))
                self.table.setItem(i, 1, km_it)

                self.table.setItem(i, 2, QTableWidgetItem(
                    f"HD{log.ma_hd:04d}" if log.ma_hd else "—"))

                if log.ma_kh:
                    if log.ma_kh not in kh_cache:
                        kh = s.query(KhachHang).get(log.ma_kh)
                        kh_cache[log.ma_kh] = kh.ten_kh if kh else "?"
                    kh_str = kh_cache[log.ma_kh]
                else:
                    kh_str = "—"
                self.table.setItem(i, 3, QTableWidgetItem(kh_str))

                if log.ma_nv:
                    if log.ma_nv not in nv_cache:
                        nv = s.query(NhanVien).get(log.ma_nv)
                        nv_cache[log.ma_nv] = nv.ten_nv if nv else "?"
                    nv_str = nv_cache[log.ma_nv]
                else:
                    nv_str = "—"
                self.table.setItem(i, 4, QTableWidgetItem(nv_str))

                giam_it = QTableWidgetItem(f"-{int(log.so_tien_giam or 0):,} đ")
                giam_it.setForeground(QColor("#E74C3C"))
                self.table.setItem(i, 5, giam_it)
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH — chỉ Admin & Quản lý
# ═══════════════════════════════════════════════════════════════════════════════
class SystemLogDialog(QDialog):
    def __init__(self, parent=None, chuc_vu: str = "Admin"):
        super().__init__(parent)
        self.setWindowTitle("📋 Nhật Ký Hoạt Động")
        self.resize(1150, 660)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self); root.setContentsMargins(10, 10, 10, 10)

        # ── Tiêu đề ──────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("📋  NHẬT KÝ HOẠT ĐỘNG HỆ THỐNG")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#3498DB;")
        header.addWidget(title); header.addStretch()
        role_lbl = QLabel(f"👁 Chế độ xem: {chuc_vu}")
        role_lbl.setStyleSheet("font-size:12px;color:#A1A1AA;")
        header.addWidget(role_lbl)
        root.addLayout(header)

        self.tabs = QTabWidget()
        self.t0 = LoginLogTab()
        self.t1 = StaffLogTab()
        self.t2 = PromoLogTab()

        self.tabs.addTab(self.t0, "🔐  Nhật Ký Đăng Nhập")   # ← Thay "Hệ thống"
        self.tabs.addTab(self.t1, "👤  Nhật Ký Hoạt Động")
        self.tabs.addTab(self.t2, "🏷️  Nhật Ký Khuyến Mãi")
        root.addWidget(self.tabs)

        self.tabs.currentChanged.connect(self._on_tab)

        btn = QPushButton("Đóng"); btn.setMinimumHeight(38)
        btn.setStyleSheet("background:#34495E;color:white;font-weight:bold;border-radius:6px;")
        btn.clicked.connect(self.accept); root.addWidget(btn)

    def showEvent(self, e):
        super().showEvent(e); self._on_tab(self.tabs.currentIndex())

    def _on_tab(self, idx: int):
        if idx == 0: self.t0.load()
        elif idx == 1: self.t1._reload_all()
        elif idx == 2: self.t2.load()