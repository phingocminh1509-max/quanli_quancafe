"""
views/attendance_manager.py
══════════════════════════════════════════════════════════════════
Báo Cáo Điểm Danh — bảng báo cáo toàn bộ ca trong ngày.

• Một NV nhiều ca → nhiều dòng riêng, mỗi dòng độc lập
• Hiển thị: Tên NV | Chức vụ | Ca | Giờ ca | Check-in | Check-out
            | Giờ thực | Trạng thái | Ghi chú
• Trạng thái: Chưa đến / Đang làm / Đi trễ / Đã ra / Về sớm / Vắng
• Lọc theo ngày, theo ca, theo trạng thái
• Thống kê nhanh theo từng trạng thái
• Tự động làm mới mỗi 60 giây
• Không có nút check-in / check-out inline
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDateEdit, QWidget, QComboBox, QFrame,
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QColor, QFont

from database.db_config import get_session
from database.models import NhanVien, CaLamViec, PhanCongCaLam, PhienLamViec

# ── Hằng số ──────────────────────────────────────────────────────────────────
CHECKIN_EARLY_MIN  = 15   # phút — cho phép vào sớm trước giờ ca
CHECKOUT_EARLY_MIN = 15   # phút — cho phép ra sớm trước giờ kết thúc

# ── Màu ──────────────────────────────────────────────────────────────────────
BG       = "#1E1E2E"
BG_CARD  = "#2D2D3F"
BG_ALT   = "#252535"
ACCENT   = "#3498DB"
GREEN    = "#27AE60"
ORANGE   = "#E67E22"
RED      = "#E74C3C"
YELLOW   = "#F1C40F"
TEXT     = "#ECF0F1"
TEXT_DIM = "#A1A1AA"
BORDER   = "#3E3E55"

CA_COLOR = {
    "Ca Sáng":  "#F39C12",
    "Ca Chiều": "#2980B9",
    "Ca Tối":   "#8E44AD",
}

STATUS_META = {
    # tên               màu chữ    màu nền badge    icon
    "Chưa đến":      ("#C8C8D4", "#4A4A6040",    "⏳"),
    "Đang làm":      ("#00FF88", "#00C86840",    "🟢"),
    "Đi trễ":        ("#FFB347", "#FF8C0040",    "⚠️"),
    "Đã hoàn thành": ("#4FC3F7", "#0288D140",    "✅"),
    "Về sớm":        ("#FFE066", "#FFD00040",    "⬇️"),
    "Vắng":          ("#FF6B6B", "#E53935 40",   "❌"),
}

STYLE = f"""
QDialog, QWidget  {{ background:{BG}; color:{TEXT}; font-family:'Segoe UI'; }}
QLabel            {{ background:transparent; }}
QTableWidget {{
    background:{BG_CARD}; border:none; border-radius:10px;
    gridline-color:{BORDER}; color:#ECF0F1; font-size:13px;
}}
QTableWidget::item          {{ padding:7px 8px; border-bottom:1px solid {BORDER}; }}
QTableWidget::item:selected {{ background:{ACCENT}44; color:white; }}
QHeaderView::section {{
    background:{BG_ALT}; color:#FFFFFF; padding:9px 8px;
    border:none; font-weight:bold; font-size:13px; letter-spacing:0.5px;
}}
QDateEdit, QComboBox {{
    background:{BG_CARD}; border:1px solid {BORDER};
    border-radius:6px; padding:5px 10px; color:{TEXT}; font-size:13px;
}}
QDateEdit:focus, QComboBox:focus {{ border-color:{ACCENT}; }}
QComboBox::drop-down  {{ border:none; }}
QComboBox QAbstractItemView {{
    background:{BG_CARD}; color:{TEXT};
    selection-background-color:{ACCENT};
}}
QPushButton {{
    border-radius:6px; font-weight:bold; font-size:13px;
    color:white; padding:6px 16px;
}}
QScrollBar:vertical   {{ background:{BG_ALT}; width:7px; border-radius:4px; }}
QScrollBar::handle:vertical {{ background:{BORDER}; border-radius:4px; min-height:20px; }}
"""


# ── Helpers UI ───────────────────────────────────────────────────────────────
def _btn(text: str, color: str, h: int = 36) -> QPushButton:
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setStyleSheet(
        f"background:{color}; color:white; font-weight:bold;"
        f" border-radius:6px; font-size:13px; padding:0 14px;"
    )
    return b


def _lbl(text: str, color: str = TEXT, size: int = 13, bold: bool = False) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"color:{color}; font-size:{size}px;"
        + (" font-weight:bold;" if bold else "")
    )
    return l


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setStyleSheet(f"color:{BORDER};")
    return f


# ── Nghiệp vụ ────────────────────────────────────────────────────────────────
def _combine(d: date, t: dtime) -> datetime:
    return datetime.combine(d, t)


def _fmt_time(dt: datetime | None) -> str:
    return dt.strftime("%H:%M") if dt else "—"


def _fmt_dur(vao: datetime | None, ra: datetime | None) -> str:
    if not vao or not ra:
        return "—"
    mins = int((ra - vao).total_seconds() / 60)
    h, m = divmod(abs(mins), 60)
    return f"{h}g{m:02d}p"


def _calc_status(
    d: date,
    gio_bd: dtime | None, gio_kt: dtime | None,
    vao: datetime | None, ra: datetime | None,
    now: datetime,
) -> str:
    if not gio_bd:
        return "Chưa đến"

    dt_bd = _combine(d, gio_bd)
    dt_kt = (_combine(d, gio_kt) if gio_kt else dt_bd + timedelta(hours=8))
    if gio_kt and gio_kt < gio_bd:          # ca qua đêm
        dt_kt += timedelta(days=1)

    if vao is None:
        return "Vắng" if now > dt_kt else "Chưa đến"

    if ra is None:
        return "Đi trễ" if vao > dt_bd else "Đang làm"

    # đã checkout
    dt_ok = dt_kt - timedelta(minutes=CHECKOUT_EARLY_MIN)
    return "Về sớm" if ra < dt_ok else "Đã hoàn thành"


def _calc_note(
    d: date,
    gio_bd: dtime | None, gio_kt: dtime | None,
    vao: datetime | None, ra: datetime | None,
) -> str:
    if not gio_bd:
        return ""
    parts: list[str] = []
    dt_bd = _combine(d, gio_bd)
    dt_kt = (_combine(d, gio_kt) if gio_kt else None)
    if dt_kt and gio_kt and gio_kt < gio_bd:
        dt_kt += timedelta(days=1)

    if vao:
        diff = int((vao - dt_bd).total_seconds() / 60)
        if diff > 0:
            parts.append(f"Trễ {diff} phút")
        elif diff < -CHECKIN_EARLY_MIN:
            parts.append(f"Vào sớm {-diff} phút")

    if ra and dt_kt:
        diff = int((ra - dt_kt).total_seconds() / 60)
        if diff < -CHECKOUT_EARLY_MIN:
            parts.append(f"Về sớm {-diff} phút")
        elif diff > 0:
            parts.append(f"Tăng ca {diff} phút")

    return "  •  ".join(parts)


def _get_rows(target: date) -> list[dict]:
    """Trả toàn bộ dòng báo cáo cho ngày target."""
    rows: list[dict] = []
    now = datetime.now()
    s   = get_session()
    try:
        pcs = (s.query(PhanCongCaLam)
               .filter(PhanCongCaLam.ngay_lam == target)
               .order_by(PhanCongCaLam.ma_ca, PhanCongCaLam.ma_nv)
               .all())

        for pc in pcs:
            nv = s.query(NhanVien).get(pc.ma_nv)
            ca = s.query(CaLamViec).get(pc.ma_ca)
            if not nv or not ca:
                continue

            gio_bd = ca.gio_bat_dau
            gio_kt = ca.gio_ket_thuc

            # Tìm phiên check-in gần nhất trong cửa sổ ca ± 2 h
            phien = None
            if gio_bd:
                w_start = _combine(target, gio_bd) - timedelta(hours=2)
                w_end   = _combine(target, gio_bd) + timedelta(hours=14)
                phien   = (s.query(PhienLamViec)
                            .filter(
                                PhienLamViec.ma_nv == nv.id,
                                PhienLamViec.thoi_gian_dang_nhap >= w_start,
                                PhienLamViec.thoi_gian_dang_nhap <= w_end,
                            )
                            .order_by(PhienLamViec.thoi_gian_dang_nhap.asc())
                            .first())

            vao = phien.thoi_gian_dang_nhap if phien else None
            ra  = phien.thoi_gian_dang_xuat if phien else None

            rows.append({
                "nv_id":    nv.id,
                "nv_ten":   nv.ten_nv,
                "nv_cv":    nv.chuc_vu or "—",
                "ca_id":    ca.id,
                "ten_ca":   ca.ten_ca,
                "gio_bd":   gio_bd.strftime("%H:%M") if gio_bd else "—",
                "gio_kt":   gio_kt.strftime("%H:%M") if gio_kt else "—",
                "phien_id": phien.id if phien else None,
                "vao":      vao,
                "ra":       ra,
                "status":   _calc_status(target, gio_bd, gio_kt, vao, ra, now),
                "note":     _calc_note(target, gio_bd, gio_kt, vao, ra),
            })
    finally:
        s.close()

    rows.sort(key=lambda r: (r["gio_bd"], r["nv_ten"]))
    return rows


# ── Hàm tiện ích dùng bởi main_window ────────────────────────────────────────
def get_open_shifts_today(nv_id: int) -> list[dict]:
    rows = _get_rows(date.today())
    return [
        {"phien_id": r["phien_id"], "ten_ca": r["ten_ca"],
         "gio_bd": r["gio_bd"], "gio_kt": r["gio_kt"],
         "vao_luc": _fmt_time(r["vao"])}
        for r in rows
        if r["nv_id"] == nv_id and r["vao"] and not r["ra"] and r["phien_id"]
    ]


def auto_checkout_all(nv_id: int) -> list[str]:
    open_s = get_open_shifts_today(nv_id)
    msgs   = []
    now    = datetime.now()
    s      = get_session()
    try:
        for item in open_s:
            phien = s.query(PhienLamViec).get(item["phien_id"])
            if not phien or phien.thoi_gian_dang_xuat:
                msgs.append(f"⚠️ {item['ten_ca']}: Đã checkout hoặc không tìm thấy.")
                continue
            phien.thoi_gian_dang_xuat = now
            phien.dang_hoat_dong      = False
            msgs.append(f"✅ {item['ten_ca']} ({item['gio_bd']}–{item['gio_kt']}): Auto checkout {now.strftime('%H:%M:%S')}")
        s.commit()
    except Exception as e:
        s.rollback()
        msgs.append(f"❌ Lỗi: {e}")
    finally:
        s.close()
    return msgs


# ══════════════════════════════════════════════════════════════════════════════
# BADGE TRẠNG THÁI  (widget thuần — không có nút)
# ══════════════════════════════════════════════════════════════════════════════
class StatusBadge(QWidget):
    def __init__(self, status: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")

        color, bg, icon = STATUS_META.get(status, (TEXT_DIM, "#3E3E5540", "•"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setAlignment(Qt.AlignCenter)

        lbl = QLabel(f"{icon}  {status}")
        lbl.setStyleSheet(
            f"background:{bg}; color:{color}; font-weight:bold; font-size:13px;"
            f" border-radius:5px; padding:4px 10px; border:1px solid {color}88;"
            f" letter-spacing:0.3px;"
        )
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH
# ══════════════════════════════════════════════════════════════════════════════
class AttendanceDialog(QDialog):
    """Bảng báo cáo điểm danh — chỉ xem, không thao tác check-in/out."""

    C_NV     = 0
    C_CV     = 1
    C_CA     = 2
    C_GIO    = 3
    C_VAO    = 4
    C_RA     = 5
    C_DUR    = 6
    C_STATUS = 7
    C_NOTE   = 8
    NCOLS    = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋  Báo Cáo Điểm Danh")
        self.resize(1200, 720)
        self.setStyleSheet(STYLE)
        self._target = date.today()
        self._rows: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ══ HEADER ════════════════════════════════════════════════
        hdr = QHBoxLayout()
        hdr.setSpacing(0)

        title_lbl = _lbl("📋  BÁO CÁO ĐIỂM DANH", ACCENT, 18, True)
        hdr.addWidget(title_lbl)
        hdr.addStretch()

        btn_refresh = _btn("🔄  Làm mới", ACCENT, 36)
        btn_refresh.setFixedWidth(120)
        btn_refresh.clicked.connect(self._load)
        hdr.addWidget(btn_refresh)

        root.addLayout(hdr)

        # ── Đường kẻ ngang dưới header ───────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color:{BORDER}; background:{BORDER}; max-height:1px;")
        root.addWidget(line)

        # ══ TOOLBAR LỌC ═══════════════════════════════════════════
        # Dùng QWidget + QHBoxLayout có background để trông như 1 thanh
        filter_bar = QWidget()
        filter_bar.setStyleSheet(
            f"background:{BG_CARD}; border-radius:8px; border:1px solid {BORDER};"
        )
        filter_bar.setFixedHeight(46)
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(14, 0, 14, 0)
        fb_layout.setSpacing(16)

        def _filter_lbl(text: str) -> QLabel:
            l = QLabel(text)
            l.setStyleSheet(
                f"color:{TEXT_DIM}; font-size:12px; font-weight:bold;"
                f" background:transparent; border:none;"
            )
            return l

        def _filter_sep() -> QFrame:
            f = QFrame()
            f.setFrameShape(QFrame.VLine)
            f.setFixedHeight(22)
            f.setStyleSheet(f"color:{BORDER}; background:{BORDER}; max-width:1px;")
            return f

        def _filter_combo(w: int = 148) -> QComboBox:
            cb = QComboBox()
            cb.setFixedWidth(w)
            cb.setFixedHeight(30)
            cb.setStyleSheet(
                f"QComboBox {{ background:#1E1E2E; border:1px solid {BORDER};"
                f" border-radius:5px; padding:0 8px; color:{TEXT}; font-size:13px; }}"
                f"QComboBox:focus {{ border-color:{ACCENT}; }}"
                f"QComboBox::drop-down {{ border:none; }}"
                f"QComboBox QAbstractItemView {{ background:{BG_CARD}; color:{TEXT};"
                f" selection-background-color:{ACCENT}; }}"
            )
            return cb

        # Ngày
        fb_layout.addWidget(_filter_lbl("Ngày:"))
        self.de = QDateEdit()
        self.de.setCalendarPopup(True)
        self.de.setDate(QDate.currentDate())
        self.de.setDisplayFormat("dd/MM/yyyy")
        self.de.setFixedWidth(120)
        self.de.setFixedHeight(30)
        self.de.setStyleSheet(
            f"QDateEdit {{ background:#1E1E2E; border:1px solid {BORDER};"
            f" border-radius:5px; padding:0 8px; color:{TEXT}; font-size:13px; }}"
            f"QDateEdit:focus {{ border-color:{ACCENT}; }}"
        )
        self.de.dateChanged.connect(self._on_date)
        fb_layout.addWidget(self.de)

        fb_layout.addWidget(_filter_sep())

        # Ca
        fb_layout.addWidget(_filter_lbl("Ca:"))
        self.cb_ca = _filter_combo(148)
        self.cb_ca.currentIndexChanged.connect(self._draw)
        fb_layout.addWidget(self.cb_ca)

        fb_layout.addWidget(_filter_sep())

        # Trạng thái
        fb_layout.addWidget(_filter_lbl("Trạng thái:"))
        self.cb_status = _filter_combo(148)
        self.cb_status.addItem("Tất cả", None)
        for st in STATUS_META:
            self.cb_status.addItem(st, st)
        self.cb_status.currentIndexChanged.connect(self._draw)
        fb_layout.addWidget(self.cb_status)

        fb_layout.addStretch()

        root.addWidget(filter_bar)

        # ══ THỐNG KÊ — 7 thẻ đều nhau, kéo dài full width ════════
        stat_row = QHBoxLayout()
        stat_row.setSpacing(8)
        self._stat_labels: dict[str, QLabel] = {}

        stat_defs = [
            ("Tổng ca",        "#FFFFFF", BG_CARD, BORDER),
            ("Chưa đến",       "#FFFFFF", BG_CARD, BORDER),
            ("Đang làm",       "#FFFFFF", BG_CARD, BORDER),
            ("Đi trễ",         "#FFFFFF", BG_CARD, BORDER),
            ("Đã hoàn thành",  "#FFFFFF", BG_CARD, BORDER),
            ("Về sớm",         "#FFFFFF", BG_CARD, BORDER),
            ("Vắng",           "#FFFFFF", BG_CARD, BORDER),
        ]

        for label, txt_color, bg_color, border_color in stat_defs:
            card = QWidget()
            card.setSizePolicy(
                card.sizePolicy().horizontalPolicy(),
                card.sizePolicy().verticalPolicy(),
            )
            from PySide6.QtWidgets import QSizePolicy as QSP
            card.setSizePolicy(QSP.Expanding, QSP.Fixed)
            card.setFixedHeight(62)
            card.setStyleSheet(
                f"background:{bg_color}; border-radius:8px;"
                f" border:1px solid {border_color};"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(8, 4, 8, 4)
            cl.setSpacing(0)

            num = QLabel("0")
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(
                f"color:{txt_color}; font-size:22px; font-weight:bold;"
                f" background:transparent; border:none;"
            )
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color:{txt_color}99; font-size:10px; font-weight:bold;"
                f" background:transparent; border:none; letter-spacing:0.3px;"
            )
            cl.addWidget(num)
            cl.addWidget(lbl)
            stat_row.addWidget(card)
            self._stat_labels[label] = num

        root.addLayout(stat_row)

        # ══ BẢNG ══════════════════════════════════════════════════
        self.tbl = QTableWidget(0, self.NCOLS)
        self.tbl.setHorizontalHeaderLabels([
            "Nhân Viên", "Chức Vụ", "Ca", "Giờ Ca",
            "Check-In", "Check-Out", "Giờ Làm",
            "Trạng Thái", "Ghi Chú",
        ])
        hh = self.tbl.horizontalHeader()
        # Nhân Viên: cố định nhỏ lại
        hh.setSectionResizeMode(self.C_NV,     QHeaderView.Fixed)
        self.tbl.setColumnWidth(self.C_NV,  170)
        # Chức vụ: cố định
        hh.setSectionResizeMode(self.C_CV,     QHeaderView.Fixed)
        self.tbl.setColumnWidth(self.C_CV,   90)
        # Ca: cố định
        hh.setSectionResizeMode(self.C_CA,     QHeaderView.Fixed)
        self.tbl.setColumnWidth(self.C_CA,   90)
        # Giờ ca: cố định
        hh.setSectionResizeMode(self.C_GIO,    QHeaderView.Fixed)
        self.tbl.setColumnWidth(self.C_GIO,  130)
        # Check-In / Check-Out / Giờ Làm: rộng hơn để chữ rõ
        for col, w in [(self.C_VAO, 90), (self.C_RA, 90), (self.C_DUR, 75)]:
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            self.tbl.setColumnWidth(col, w)
        # Trạng Thái: rộng hơn cho "Đã hoàn thành"
        hh.setSectionResizeMode(self.C_STATUS, QHeaderView.Fixed)
        self.tbl.setColumnWidth(self.C_STATUS, 150)
        # Ghi chú: stretch lấy phần còn lại
        hh.setSectionResizeMode(self.C_NOTE,   QHeaderView.Stretch)

        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setShowGrid(True)
        self.tbl.horizontalHeader().setMinimumSectionSize(60)
        self.tbl.setStyleSheet(
            STYLE +
            f"QTableWidget {{ alternate-background-color:{BG_ALT}; }}"
        )
        root.addWidget(self.tbl, stretch=1)

        # ══ FOOTER ════════════════════════════════════════════════
        footer = QHBoxLayout()
        footer.addStretch()
        btn_close = _btn("✕  Đóng", "#555566", 36)
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        root.addLayout(footer)

        # Auto-refresh mỗi 60 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load)
        self._timer.start(60_000)

        self._load()

    # ── Tải dữ liệu ─────────────────────────────────────────────
    def _on_date(self, qd: QDate):
        self._target = date(qd.year(), qd.month(), qd.day())
        self._load()

    def _load(self):
        self._rows = _get_rows(self._target)
        self._fill_ca_combo()
        self._draw()

    def _fill_ca_combo(self):
        prev = self.cb_ca.currentData()
        self.cb_ca.blockSignals(True)
        self.cb_ca.clear()
        self.cb_ca.addItem("Tất cả ca", None)
        seen: list[str] = []
        for r in self._rows:
            if r["ten_ca"] not in seen:
                seen.append(r["ten_ca"])
                self.cb_ca.addItem(r["ten_ca"], r["ten_ca"])
        idx = self.cb_ca.findData(prev)
        self.cb_ca.setCurrentIndex(max(idx, 0))
        self.cb_ca.blockSignals(False)

    # ── Render bảng ─────────────────────────────────────────────
    def _draw(self):
        ca_f  = self.cb_ca.currentData()
        st_f  = self.cb_status.currentData()

        visible = [
            r for r in self._rows
            if (ca_f is None or r["ten_ca"] == ca_f)
            and (st_f is None or r["status"] == st_f)
        ]

        self.tbl.setRowCount(0)

        prev_ca = None
        for i, r in enumerate(visible):
            self.tbl.insertRow(i)
            self.tbl.setRowHeight(i, 42)

            # Nhóm ca: tô nền header-like khi chuyển ca
            row_bg = None
            if r["ten_ca"] != prev_ca:
                prev_ca = r["ten_ca"]
                row_bg = QColor(CA_COLOR.get(r["ten_ca"], ACCENT) + "18")

            def _cell(text: str, align=Qt.AlignVCenter | Qt.AlignLeft,
                      color: str | None = None, bold: bool = False) -> QTableWidgetItem:
                it = QTableWidgetItem(text)
                it.setTextAlignment(align)
                if color:
                    it.setForeground(QColor(color))
                if bold:
                    f = QFont("Segoe UI", 12, QFont.Bold)
                    it.setFont(f)
                if row_bg:
                    it.setBackground(row_bg)
                return it

            center = Qt.AlignCenter

            self.tbl.setItem(i, self.C_NV,  _cell(r["nv_ten"], bold=True))
            self.tbl.setItem(i, self.C_CV,  _cell(r["nv_cv"],  color=TEXT_DIM))
            self.tbl.setItem(i, self.C_CA,
                             _cell(r["ten_ca"],
                                   color=CA_COLOR.get(r["ten_ca"], ACCENT),
                                   bold=True))
            self.tbl.setItem(i, self.C_GIO,
                             _cell(f"{r['gio_bd']} – {r['gio_kt']}", center, TEXT_DIM))

            # Check-in
            vao_it = _cell(_fmt_time(r["vao"]), center,
                           GREEN if r["vao"] else TEXT_DIM)
            if row_bg:
                vao_it.setBackground(row_bg)
            self.tbl.setItem(i, self.C_VAO, vao_it)

            # Check-out
            ra_it = _cell(_fmt_time(r["ra"]), center,
                          ACCENT if r["ra"] else TEXT_DIM)
            if row_bg:
                ra_it.setBackground(row_bg)
            self.tbl.setItem(i, self.C_RA, ra_it)

            # Giờ làm thực tế
            dur_it = _cell(_fmt_dur(r["vao"], r["ra"]), center,
                           TEXT if r["vao"] and r["ra"] else TEXT_DIM)
            if row_bg:
                dur_it.setBackground(row_bg)
            self.tbl.setItem(i, self.C_DUR, dur_it)

            # Trạng thái — widget badge
            badge = StatusBadge(r["status"])
            self.tbl.setCellWidget(i, self.C_STATUS, badge)

            # Ghi chú
            note_it = _cell(r["note"], color=TEXT if r["note"] else TEXT_DIM)
            if row_bg:
                note_it.setBackground(row_bg)
            self.tbl.setItem(i, self.C_NOTE, note_it)

        self._update_stats(visible)

    # ── Cập nhật thẻ thống kê ────────────────────────────────────
    def _update_stats(self, rows: list[dict]):
        counts: dict[str, int] = {k: 0 for k in STATUS_META}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1

        # "Tổng ca" card
        if "Tổng ca" in self._stat_labels:
            self._stat_labels["Tổng ca"].setText(str(len(rows)))

        # Các trạng thái — key trong stat_labels trùng tên STATUS_META
        for k in STATUS_META:
            if k in self._stat_labels:
                self._stat_labels[k].setText(str(counts.get(k, 0)))