"""
views/report_window.py
══════════════════════════════════════════════════════════════════
Báo Cáo Doanh Thu — giao diện tương thích với hệ thống POS Cafe

Các tab:
  1. Tổng quan   — KPI cards + biểu đồ doanh thu theo ngày
  2. Theo giờ    — Doanh thu từng khung giờ trong ngày
  3. Sản phẩm    — Top món bán chạy + tổng số lượng
  4. Nhân viên   — Doanh thu & số đơn theo từng thu ngân
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QWidget, QGridLayout, QSizePolicy, QDateEdit,
    QStackedWidget, QScrollArea,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient

from database.db_config import get_session
from database.models import HoaDon, ChiTietHoaDon, NhanVien, SanPham

# ── Bảng màu ─────────────────────────────────────────────────────────────────
C_BG     = "#12121E"
C_PANEL  = "#1C1C2E"
C_CARD   = "#252538"
C_BORDER = "#2E2E45"
C_ACCENT = "#3498DB"
C_GREEN  = "#2ECC71"
C_ORANGE = "#E67E22"
C_RED    = "#E74C3C"
C_YELLOW = "#F1C40F"
C_PURPLE = "#9B59B6"
C_TEXT   = "#E0E0EE"
C_MUTED  = "#7070A0"

STYLE = f"""
QDialog, QWidget   {{ background:{C_BG}; color:{C_TEXT}; }}
QFrame             {{ background:{C_PANEL}; border-radius:10px; border:none; }}
QTableWidget       {{ background:{C_CARD}; border:none; border-radius:8px;
                      gridline-color:{C_BORDER}; color:{C_TEXT}; font-size:13px; }}
QTableWidget::item {{ padding:8px 6px; border-bottom:1px solid {C_BORDER}; }}
QTableWidget::item:selected {{ background:{C_ACCENT}; color:white; }}
QHeaderView::section {{ background:{C_PANEL}; color:{C_MUTED}; padding:10px 6px;
    border:none; font-weight:bold; font-size:12px;
    border-bottom:2px solid {C_BORDER}; }}
QDateEdit {{
    background:{C_CARD}; border:1px solid {C_BORDER}; border-radius:6px;
    padding:7px 10px; color:{C_TEXT}; font-size:13px; }}
QDateEdit:focus {{ border-color:{C_ACCENT}; }}
QScrollBar:vertical {{ background:{C_BG}; width:6px; border-radius:3px; }}
QScrollBar::handle:vertical {{ background:{C_BORDER}; border-radius:3px; }}
QScrollBar:horizontal {{ background:{C_BG}; height:6px; border-radius:3px; }}
QScrollBar::handle:horizontal {{ background:{C_BORDER}; border-radius:3px; }}
"""


# ── Helpers UI ────────────────────────────────────────────────────────────────
def _lbl(text="", color=C_TEXT, size=13, bold=False, align=Qt.AlignLeft):
    l = QLabel(text)
    w = "bold" if bold else "normal"
    l.setStyleSheet(
        f"color:{color};font-size:{size}px;font-weight:{w};"
        "background:transparent;border:none;"
    )
    l.setAlignment(align)
    l.setWordWrap(True)
    return l


def _btn(text, color=C_ACCENT, h=36):
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:white;font-weight:bold;"
        f"border-radius:8px;font-size:13px;padding:0 16px;border:none;}}"
        f"QPushButton:hover{{background:{color}CC;}}"
        f"QPushButton:pressed{{background:{color}99;}}"
    )
    b.setCursor(Qt.PointingHandCursor)
    return b


def _hline():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"background:{C_BORDER};border:none;max-height:1px;")
    return f


def _kpi_card(icon, title, value, color=C_ACCENT, sub=""):
    """Card KPI nhỏ hiển thị chỉ số tổng quan."""
    f = QFrame()
    f.setStyleSheet(
        f"QFrame{{background:{C_CARD};border-radius:12px;"
        f"border:1px solid {C_BORDER};}}"
    )
    f.setMinimumHeight(100)
    v = QVBoxLayout(f)
    v.setContentsMargins(18, 14, 18, 14)
    v.setSpacing(4)

    top = QHBoxLayout()
    lbl_icon = QLabel(icon)
    lbl_icon.setStyleSheet(f"font-size:22px;background:transparent;border:none;")
    lbl_title = _lbl(title, C_MUTED, 12)
    top.addWidget(lbl_icon)
    top.addWidget(lbl_title)
    top.addStretch()
    v.addLayout(top)

    lbl_val = _lbl(value, color, 22, True)
    lbl_val.setAlignment(Qt.AlignLeft)
    v.addWidget(lbl_val)

    if sub:
        lbl_sub = _lbl(sub, C_MUTED, 11)
        v.addWidget(lbl_sub)

    return f, lbl_val


def _tab_btn(text, active=False):
    color = C_ACCENT if active else C_CARD
    b = QPushButton(text)
    b.setMinimumHeight(38)
    b.setCheckable(True)
    b.setChecked(active)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:{'white' if active else C_MUTED};"
        f"font-weight:{'bold' if active else 'normal'};"
        f"border-radius:8px;font-size:13px;padding:0 18px;border:none;}}"
        f"QPushButton:checked{{background:{C_ACCENT};color:white;font-weight:bold;}}"
        f"QPushButton:hover{{background:{C_ACCENT}55;color:white;}}"
    )
    return b


def _make_table(headers: list[str], col_widths: dict = None) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setAlternatingRowColors(False)
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


# ══════════════════════════════════════════════════════════════════════════════
# BIỂU ĐỒ CỘT ĐƠN GIẢN (vẽ bằng QPainter — không cần thư viện ngoài)
# ══════════════════════════════════════════════════════════════════════════════
class BarChart(QWidget):
    """Biểu đồ cột doanh thu theo ngày/giờ."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[str, float]] = []   # [(label, value), ...]
        self._color = C_ACCENT
        self._title = ""
        self.setMinimumHeight(220)
        self.setStyleSheet(f"background:{C_CARD};border-radius:10px;")

    def set_data(self, data: list[tuple[str, float]], color=C_ACCENT, title=""):
        self._data  = data
        self._color = color
        self._title = title
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H  = self.width(), self.height()
        PAD_L = 64
        PAD_R = 16
        PAD_T = 36
        PAD_B = 48

        chart_w = W - PAD_L - PAD_R
        chart_h = H - PAD_T - PAD_B
        max_val = max((v for _, v in self._data), default=1) or 1

        # Tiêu đề
        if self._title:
            p.setPen(QColor(C_MUTED))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(PAD_L, 20, self._title)

        # Đường kẻ ngang
        p.setPen(QPen(QColor(C_BORDER), 1, Qt.DashLine))
        steps = 4
        for i in range(steps + 1):
            y = PAD_T + chart_h - int(chart_h * i / steps)
            p.drawLine(PAD_L, y, W - PAD_R, y)
            val = max_val * i / steps
            p.setPen(QColor(C_MUTED))
            p.setFont(QFont("Segoe UI", 8))
            if val >= 1_000_000:
                txt = f"{val/1_000_000:.1f}M"
            elif val >= 1_000:
                txt = f"{int(val/1_000)}k"
            else:
                txt = str(int(val))
            p.drawText(0, y - 6, PAD_L - 6, 16, Qt.AlignRight | Qt.AlignVCenter, txt)
            p.setPen(QPen(QColor(C_BORDER), 1, Qt.DashLine))

        # Cột
        n    = len(self._data)
        gap  = max(2, chart_w // (n * 6))
        bw   = max(6, (chart_w - gap * (n + 1)) // n)
        bw   = min(bw, 60)

        grad = QLinearGradient(0, PAD_T, 0, PAD_T + chart_h)
        grad.setColorAt(0, QColor(self._color))
        grad.setColorAt(1, QColor(self._color + "55"))

        for i, (lbl, val) in enumerate(self._data):
            bh   = int(chart_h * val / max_val) if max_val else 0
            x    = PAD_L + gap + i * (bw + gap)
            y    = PAD_T + chart_h - bh

            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(x, y, bw, bh, 4, 4)

            # Giá trị trên cột (chỉ hiện nếu đủ chỗ)
            if bh > 20 and bw > 20:
                p.setPen(QColor("white"))
                p.setFont(QFont("Segoe UI", 7, QFont.Bold))
                if val >= 1_000_000:
                    vtxt = f"{val/1_000_000:.1f}M"
                elif val >= 1_000:
                    vtxt = f"{int(val/1_000)}k"
                else:
                    vtxt = str(int(val))
                p.drawText(x, y - 2, bw, 14, Qt.AlignCenter, vtxt)

            # Nhãn dưới
            p.setPen(QColor(C_MUTED))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(x, PAD_T + chart_h + 6, bw, 20, Qt.AlignCenter, lbl)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# HÀM LẤY DỮ LIỆU
# ══════════════════════════════════════════════════════════════════════════════
def _query_hoadon(session, d_from: date, d_to: date):
    """Trả về list HoaDon đã thanh toán trong khoảng ngày."""
    dt_from = datetime(d_from.year, d_from.month, d_from.day, 0, 0, 0)
    dt_to   = datetime(d_to.year,   d_to.month,   d_to.day,   23, 59, 59)
    return (
        session.query(HoaDon)
        .filter(
            HoaDon.thoi_gian >= dt_from,
            HoaDon.thoi_gian <= dt_to,
            HoaDon.trang_thai == "Đã thanh toán",
        )
        .order_by(HoaDon.thoi_gian)
        .all()
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TỔNG QUAN
# ══════════════════════════════════════════════════════════════════════════════
class _TabOverview(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        # KPI cards
        kpi_row = QHBoxLayout(); kpi_row.setSpacing(12)
        self._card_hd,  self._val_hd  = _kpi_card("🧾", "Tổng hóa đơn",  "0",     C_ACCENT)
        self._card_rev, self._val_rev = _kpi_card("💰", "Doanh thu",      "0 đ",   C_GREEN)
        self._card_avg, self._val_avg = _kpi_card("📊", "Trung bình/đơn", "0 đ",   C_YELLOW)
        self._card_disc,self._val_disc= _kpi_card("🎉", "Tổng giảm giá", "0 đ",   C_ORANGE)
        for f, _ in [
            (self._card_hd, None), (self._card_rev, None),
            (self._card_avg, None),(self._card_disc, None),
        ]:
            kpi_row.addWidget(f)
        root.addLayout(kpi_row)

        # Biểu đồ doanh thu theo ngày
        chart_frame = QFrame()
        chart_frame.setStyleSheet(
            f"QFrame{{background:{C_CARD};border-radius:12px;border:1px solid {C_BORDER};}}"
        )
        cf_lay = QVBoxLayout(chart_frame)
        cf_lay.setContentsMargins(14, 12, 14, 12)
        cf_lay.addWidget(_lbl("📈  Doanh thu theo ngày", C_ACCENT, 13, True))
        self.chart = BarChart()
        cf_lay.addWidget(self.chart)
        root.addWidget(chart_frame)

    def refresh(self, hoadon_list: list):
        total_rev  = sum(hd.thanh_tien or 0 for hd in hoadon_list)
        total_disc = sum(hd.giam_gia   or 0 for hd in hoadon_list)
        n          = len(hoadon_list)
        avg        = total_rev / n if n else 0

        self._val_hd.setText(f"{n:,}")
        self._val_rev.setText(f"{int(total_rev):,} đ")
        self._val_avg.setText(f"{int(avg):,} đ")
        self._val_disc.setText(f"{int(total_disc):,} đ")

        # Gộp doanh thu theo ngày
        by_day: dict[date, float] = defaultdict(float)
        for hd in hoadon_list:
            if hd.thoi_gian:
                by_day[hd.thoi_gian.date()] += float(hd.thanh_tien or 0)

        sorted_days = sorted(by_day.items())
        # Giới hạn 30 cột để không bị chật
        if len(sorted_days) > 30:
            sorted_days = sorted_days[-30:]

        data = [(d.strftime("%d/%m"), v) for d, v in sorted_days]
        self.chart.set_data(data, C_ACCENT, "")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — THEO GIỜ
# ══════════════════════════════════════════════════════════════════════════════
class _TabHourly(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        chart_frame = QFrame()
        chart_frame.setStyleSheet(
            f"QFrame{{background:{C_CARD};border-radius:12px;border:1px solid {C_BORDER};}}"
        )
        cf_lay = QVBoxLayout(chart_frame)
        cf_lay.setContentsMargins(14, 12, 14, 12)
        cf_lay.addWidget(_lbl("🕐  Doanh thu theo khung giờ", C_ACCENT, 13, True))
        self.chart = BarChart()
        self.chart.setMinimumHeight(240)
        cf_lay.addWidget(self.chart)
        root.addWidget(chart_frame)

        # Bảng chi tiết giờ cao điểm
        root.addWidget(_lbl("⚡  Chi tiết từng giờ", C_MUTED, 12, True))
        self.table = _make_table(
            ["Khung giờ", "Số đơn", "Doanh thu", "TB/đơn"],
            {0: 110, 1: 80}
        )
        root.addWidget(self.table, stretch=1)

    def refresh(self, hoadon_list: list):
        by_hour: dict[int, list] = defaultdict(list)
        for hd in hoadon_list:
            if hd.thoi_gian:
                by_hour[hd.thoi_gian.hour].append(float(hd.thanh_tien or 0))

        data = []
        for h in range(24):
            vals = by_hour.get(h, [])
            rev  = sum(vals)
            data.append((f"{h:02d}h", rev))

        self.chart.set_data(data, C_PURPLE, "")

        # Bảng
        self.table.setRowCount(0)
        for h in range(24):
            vals = by_hour.get(h, [])
            if not vals:
                continue
            rev = sum(vals)
            avg = rev / len(vals)
            r   = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, _ti(f"{h:02d}:00 – {h:02d}:59"))
            self.table.setItem(r, 1, _ti(str(len(vals)), C_ACCENT, Qt.AlignCenter))
            self.table.setItem(r, 2, _ti(f"{int(rev):,} đ", C_GREEN, Qt.AlignRight, True))
            self.table.setItem(r, 3, _ti(f"{int(avg):,} đ", C_YELLOW, Qt.AlignRight))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SẢN PHẨM
# ══════════════════════════════════════════════════════════════════════════════
class _TabProduct(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(_lbl("🏆  Top sản phẩm bán chạy", C_ACCENT, 13, True))
        self.table = _make_table(
            ["#", "Tên sản phẩm", "Số lượng", "Doanh thu", "% Doanh thu"],
            {0: 40, 2: 90, 3: 130, 4: 100}
        )
        root.addWidget(self.table, stretch=1)

    def refresh(self, hoadon_list: list, session):
        # Gom từ chi tiết hóa đơn
        sp_qty: dict[str, int]   = defaultdict(int)
        sp_rev: dict[str, float] = defaultdict(float)

        hd_ids = [hd.id for hd in hoadon_list]
        if hd_ids:
            cts = (
                session.query(ChiTietHoaDon)
                .filter(ChiTietHoaDon.ma_hd.in_(hd_ids))
                .all()
            )
            for ct in cts:
                name = ct.san_pham.ten_sp if ct.san_pham else f"SP#{ct.ma_sp}"
                sp_qty[name] += ct.so_luong or 0
                sp_rev[name] += float(ct.thanh_tien or 0)

        total_rev = sum(sp_rev.values()) or 1
        sorted_sp = sorted(sp_qty.items(), key=lambda x: -x[1])

        self.table.setRowCount(0)
        for rank, (name, qty) in enumerate(sorted_sp, 1):
            rev  = sp_rev[name]
            pct  = rev / total_rev * 100
            r    = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, _ti(str(rank), C_MUTED, Qt.AlignCenter))
            self.table.setItem(r, 1, _ti(name, C_TEXT, Qt.AlignLeft, rank <= 3))
            self.table.setItem(r, 2, _ti(f"{qty:,}", C_ACCENT, Qt.AlignCenter, True))
            self.table.setItem(r, 3, _ti(f"{int(rev):,} đ", C_GREEN, Qt.AlignRight, True))
            self.table.setItem(r, 4, _ti(f"{pct:.1f}%", C_YELLOW, Qt.AlignCenter))

            # Màu top 3
            if rank == 1:
                for c in range(5):
                    it = self.table.item(r, c)
                    if it: it.setBackground(QColor(C_YELLOW + "22"))
            elif rank == 2:
                for c in range(5):
                    it = self.table.item(r, c)
                    if it: it.setBackground(QColor(C_MUTED + "22"))
            elif rank == 3:
                for c in range(5):
                    it = self.table.item(r, c)
                    if it: it.setBackground(QColor(C_ORANGE + "22"))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NHÂN VIÊN
# ══════════════════════════════════════════════════════════════════════════════
class _TabStaff(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(_lbl("👤  Doanh thu theo nhân viên", C_ACCENT, 13, True))
        self.chart = BarChart()
        self.chart.setMinimumHeight(200)
        root.addWidget(self.chart)

        self.table = _make_table(
            ["Nhân viên", "Số đơn", "Doanh thu", "TB/đơn", "Giảm giá"],
            {1: 80, 3: 110, 4: 110}
        )
        root.addWidget(self.table, stretch=1)

    def refresh(self, hoadon_list: list):
        nv_orders: dict[str, list] = defaultdict(list)
        nv_disc:   dict[str, float]= defaultdict(float)

        for hd in hoadon_list:
            nv_ten = "Không rõ"
            if hd.phien_lam_viec and hd.phien_lam_viec.nhan_vien:
                nv_ten = hd.phien_lam_viec.nhan_vien.ten_nv
            nv_orders[nv_ten].append(float(hd.thanh_tien or 0))
            nv_disc[nv_ten] += float(hd.giam_gia or 0)

        sorted_nv = sorted(nv_orders.items(), key=lambda x: -sum(x[1]))

        # Biểu đồ
        chart_data = [(name[:8], sum(vals)) for name, vals in sorted_nv[:10]]
        self.chart.set_data(chart_data, C_GREEN, "")

        # Bảng
        self.table.setRowCount(0)
        for name, vals in sorted_nv:
            rev = sum(vals)
            avg = rev / len(vals) if vals else 0
            r   = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, _ti(name, C_TEXT, Qt.AlignLeft, True))
            self.table.setItem(r, 1, _ti(str(len(vals)), C_ACCENT, Qt.AlignCenter))
            self.table.setItem(r, 2, _ti(f"{int(rev):,} đ", C_GREEN, Qt.AlignRight, True))
            self.table.setItem(r, 3, _ti(f"{int(avg):,} đ", C_YELLOW, Qt.AlignRight))
            self.table.setItem(r, 4, _ti(f"{int(nv_disc[name]):,} đ", C_ORANGE, Qt.AlignRight))


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH
# ══════════════════════════════════════════════════════════════════════════════
class ReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Báo Cáo Doanh Thu")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl("📊  BÁO CÁO DOANH THU", C_ACCENT, 18, True))
        hdr.addStretch()

        # Bộ lọc ngày
        hdr.addWidget(_lbl("Từ:", C_MUTED, 12))
        self.de_from = QDateEdit(QDate.currentDate().addDays(-6))
        self.de_from.setCalendarPopup(True)
        self.de_from.setDisplayFormat("dd/MM/yyyy")
        self.de_from.setFixedWidth(115)
        hdr.addWidget(self.de_from)

        hdr.addWidget(_lbl("→", C_MUTED, 12))
        self.de_to = QDateEdit(QDate.currentDate())
        self.de_to.setCalendarPopup(True)
        self.de_to.setDisplayFormat("dd/MM/yyyy")
        self.de_to.setFixedWidth(115)
        hdr.addWidget(self.de_to)

        root.addLayout(hdr)

        # ── Nút lọc nhanh ────────────────────────────────────────────────────
        quick = QHBoxLayout(); quick.setSpacing(8)
        periods = [
            ("Hôm nay",   0,  0),
            ("Hôm qua",  -1, -1),
            ("7 ngày",   -6,  0),
            ("30 ngày", -29,  0),
            ("Tháng này", None, None),
        ]
        self._quick_btns = []
        for label, d_from, d_to in periods:
            b = _btn(label, C_CARD, 32)
            b.setStyleSheet(b.styleSheet().replace(
                f"background:{C_CARD}", f"background:{C_CARD}"
            ))
            b.clicked.connect(
                lambda _, df=d_from, dt=d_to, lb=label: self._set_quick(df, dt, lb)
            )
            quick.addWidget(b)
            self._quick_btns.append((b, label))
        quick.addStretch()

        btn_load = _btn("🔄 Tải báo cáo", C_ACCENT, 32)
        btn_load.clicked.connect(self.load_report)
        quick.addWidget(btn_load)

        root.addLayout(quick)
        root.addWidget(_hline())

        # ── Tabs ─────────────────────────────────────────────────────────────
        tab_row = QHBoxLayout(); tab_row.setSpacing(6)
        self._tabs = []
        tab_labels = ["🏠 Tổng quan", "🕐 Theo giờ", "🍹 Sản phẩm", "👤 Nhân viên"]
        for i, lbl in enumerate(tab_labels):
            b = _tab_btn(lbl, active=(i == 0))
            b.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            tab_row.addWidget(b)
            self._tabs.append(b)
        tab_row.addStretch()
        root.addLayout(tab_row)

        # ── Stack ─────────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget{background:transparent;border:none;}")
        self._tab_overview = _TabOverview()
        self._tab_hourly   = _TabHourly()
        self._tab_product  = _TabProduct()
        self._tab_staff    = _TabStaff()
        for w in [self._tab_overview, self._tab_hourly,
                  self._tab_product, self._tab_staff]:
            self.stack.addWidget(w)
        root.addWidget(self.stack, stretch=1)

        # ── Thanh dưới ───────────────────────────────────────────────────────
        bot = QHBoxLayout()
        self.lbl_status = _lbl("", C_MUTED, 12)
        bot.addWidget(self.lbl_status)
        bot.addStretch()
        btn_close = _btn("✖ Đóng", "#555577", 38)
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        bot.addWidget(btn_close)
        root.addLayout(bot)

        # Load lần đầu
        self.load_report()

    # ── Chuyển tab ───────────────────────────────────────────────────────────
    def _switch_tab(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self._tabs):
            active = (i == idx)
            b.setChecked(active)
            color = C_ACCENT if active else C_CARD
            b.setStyleSheet(
                f"QPushButton{{background:{color};"
                f"color:{'white' if active else C_MUTED};"
                f"font-weight:{'bold' if active else 'normal'};"
                f"border-radius:8px;font-size:13px;"
                f"padding:0 18px;border:none;}}"
                f"QPushButton:hover{{background:{C_ACCENT}55;color:white;}}"
            )

    # ── Lọc nhanh ngày ───────────────────────────────────────────────────────
    def _set_quick(self, d_from_offset, d_to_offset, label):
        today = date.today()
        if d_from_offset is None:
            # Tháng này
            d_from = today.replace(day=1)
            d_to   = today
        else:
            d_from = today + timedelta(days=d_from_offset)
            d_to   = today + timedelta(days=d_to_offset)

        self.de_from.blockSignals(True)
        self.de_to.blockSignals(True)
        self.de_from.setDate(QDate(d_from.year, d_from.month, d_from.day))
        self.de_to.setDate(QDate(d_to.year,   d_to.month,   d_to.day))
        self.de_from.blockSignals(False)
        self.de_to.blockSignals(False)
        self.load_report()

    # ── Load dữ liệu ─────────────────────────────────────────────────────────
    def load_report(self):
        qd_from = self.de_from.date()
        qd_to   = self.de_to.date()
        d_from  = date(qd_from.year(), qd_from.month(), qd_from.day())
        d_to    = date(qd_to.year(),   qd_to.month(),   qd_to.day())

        if d_from > d_to:
            self.lbl_status.setText("⚠  Ngày bắt đầu phải ≤ ngày kết thúc")
            self.lbl_status.setStyleSheet(
                f"color:{C_RED};font-size:12px;background:transparent;border:none;"
            )
            return

        s = get_session()
        try:
            hoadon_list = _query_hoadon(s, d_from, d_to)

            self._tab_overview.refresh(hoadon_list)
            self._tab_hourly.refresh(hoadon_list)
            self._tab_product.refresh(hoadon_list, s)
            self._tab_staff.refresh(hoadon_list)

            n   = len(hoadon_list)
            rev = sum(hd.thanh_tien or 0 for hd in hoadon_list)
            self.lbl_status.setText(
                f"📅 {d_from.strftime('%d/%m/%Y')} → {d_to.strftime('%d/%m/%Y')}  "
                f"| {n} hóa đơn | Doanh thu: {int(rev):,} đ"
            )
            self.lbl_status.setStyleSheet(
                f"color:{C_MUTED};font-size:12px;background:transparent;border:none;"
            )
        except Exception as e:
            self.lbl_status.setText(f"❌ Lỗi tải dữ liệu: {e}")
            self.lbl_status.setStyleSheet(
                f"color:{C_RED};font-size:12px;background:transparent;border:none;"
            )
        finally:
            s.close()