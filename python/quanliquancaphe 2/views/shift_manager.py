"""
views/shift_manager.py
══════════════════════════════════════════════════════════════════
Quản lý Ca Làm Việc — 4 tab:
  Tab 0 │ Tạo Ca       — CRUD Ca Sáng/Chiều/Tối, tuỳ chỉnh giờ
  Tab 1 │ Phân Công    — kéo thả NV vào ca theo ngày, chống trùng,
                         cảnh báo thiếu người;
                         ✅ Checkbox multi-select NV
                         ✅ Phân công hàng loạt (nhiều NV × khoảng ngày)
                         ✅ Auto-Fit tự động điền NV còn thiếu
  Tab 2 │ Điểm Danh    — check-in / check-out, tính giờ làm thực tế
  Tab 3 │ Lịch Tuần    — lưới 7 ngày × N ca, hiển thị NV trong từng ô
══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, time as dtime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFormLayout, QLineEdit, QTimeEdit, QComboBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QFrame,
    QDateEdit, QScrollArea, QSizePolicy, QSpinBox, QGridLayout,
    QCheckBox, QButtonGroup, QRadioButton, QGroupBox,
)
from PySide6.QtCore import Qt, QTime, QDate, QMimeData, QByteArray, Signal
from PySide6.QtGui import QColor, QFont, QDrag, QPainter, QPixmap

from database.db_config import get_session
from database.models import NhanVien, CaLamViec, PhanCongCaLam, PhienLamViec

# ── Hằng số ──────────────────────────────────────────────────────────────────
MIN_NV_PER_CA = 2          # cảnh báo nếu ca < số này
WEEKDAYS_VI   = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]

CA_PRESETS = [
    ("Ca Sáng",  "06:00", "14:00", "#F39C12"),
    ("Ca Chiều", "14:00", "22:00", "#2980B9"),
    ("Ca Tối",   "22:00", "06:00", "#8E44AD"),
]

CA_COLOR = {
    "Ca Sáng":  "#F39C12",
    "Ca Chiều": "#2980B9",
    "Ca Tối":   "#8E44AD",
}

STYLE = """
QDialog, QWidget { background-color: #1E1E2E; color: white; }
QTabWidget::pane { border: none; background: #1E1E2E; }
QTabBar::tab {
    background: #2D2D3F; color: #A1A1AA;
    padding: 10px 22px; border-radius: 6px 6px 0 0;
    font-weight: bold; font-size: 13px;
}
QTabBar::tab:selected { background: #3498DB; color: white; }
QTabBar::tab:hover    { background: #3E3E55; color: white; }
QTableWidget {
    background: #2D2D3F; border: none; border-radius: 8px;
    gridline-color: #3E3E55; color: white; font-size: 13px;
}
QTableWidget::item         { padding: 6px; border-bottom: 1px solid #3E3E55; }
QTableWidget::item:selected{ background: #3498DB; }
QHeaderView::section {
    background: #1A1A24; color: #A1A1AA;
    padding: 8px; border: none; font-weight: bold;
}
QLineEdit, QTimeEdit, QDateEdit, QComboBox, QSpinBox {
    background: #2D2D3F; border: 1px solid #3E3E55;
    border-radius: 6px; padding: 6px 10px; color: white; font-size: 13px;
}
QLineEdit:focus, QTimeEdit:focus, QDateEdit:focus { border-color: #3498DB; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background: #2D2D3F; color: white;
    selection-background-color: #3498DB; }
QListWidget {
    background: #2D2D3F; border: 1px solid #3E3E55;
    border-radius: 8px; color: white; font-size: 13px;
}
QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #3E3E55; }
QListWidget::item:selected { background: #3498DB; }
QScrollBar:vertical { background: #1A1A24; width: 7px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #3E3E55; border-radius: 4px; }
QCheckBox { color: white; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px;
    border: 2px solid #3E3E55; background: #1E1E2E; }
QCheckBox::indicator:checked { background: #3498DB; border-color: #3498DB; }
QCheckBox::indicator:hover { border-color: #3498DB; }
QGroupBox { border: 1px solid #3E3E55; border-radius: 8px;
    margin-top: 8px; padding-top: 6px; color: #A1A1AA; font-size: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
"""


def _btn(text: str, color: str, min_h: int = 36) -> QPushButton:
    b = QPushButton(text)
    b.setMinimumHeight(min_h)
    b.setStyleSheet(
        f"background-color:{color}; color:white; font-weight:bold;"
        f" border-radius:6px; font-size:13px; padding:0 14px;"
    )
    return b


def _label(text: str, color: str = "white", size: int = 13, bold: bool = False) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"color:{color}; font-size:{size}px;"
        + (" font-weight:bold;" if bold else "")
    )
    return l


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — TẠO CA
# ══════════════════════════════════════════════════════════════════════════════
class ShiftTab(QWidget):
    """CRUD ca làm việc. Seed 3 ca mặc định nếu DB trống."""

    changed = Signal()   # phát khi có thay đổi để các tab khác reload

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Toolbar ─────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.addWidget(_label("DANH SÁCH CA LÀM VIỆC", "#3498DB", 16, True))
        bar.addStretch()
        self.btn_seed  = _btn("⚡ Tạo 3 ca mặc định", "#16A085")
        self.btn_add   = _btn("➕ Thêm ca",           "#27AE60")
        self.btn_edit  = _btn("✏️ Sửa",               "#2980B9")
        self.btn_del   = _btn("🗑 Xóa",               "#C0392B")
        for b in [self.btn_seed, self.btn_add, self.btn_edit, self.btn_del]:
            bar.addWidget(b)
        root.addLayout(bar)

        # ── Bảng ────────────────────────────────────────────────
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Tên Ca", "Giờ Bắt Đầu", "Giờ Kết Thúc"]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed);   self.table.setColumnWidth(0, 50)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)

        # ── Form inline ─────────────────────────────────────────
        form_frame = QFrame()
        form_frame.setStyleSheet(
            "QFrame{background:#2D2D3F;border-radius:10px;border:1px solid #3E3E55;}"
        )
        fl = QHBoxLayout(form_frame)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        fl.addWidget(_label("Tên ca:"))
        self.txt_ten = QLineEdit(); self.txt_ten.setPlaceholderText("Ca Sáng")
        self.txt_ten.setFixedWidth(200)
        self.txt_ten.setMaxLength(100)
        fl.addWidget(self.txt_ten)

        fl.addWidget(_label("Từ:"))
        self.te_from = QTimeEdit(QTime(6, 0))
        self.te_from.setDisplayFormat("HH:mm"); self.te_from.setFixedWidth(80)
        fl.addWidget(self.te_from)

        fl.addWidget(_label("Đến:"))
        self.te_to = QTimeEdit(QTime(14, 0))
        self.te_to.setDisplayFormat("HH:mm"); self.te_to.setFixedWidth(80)
        fl.addWidget(self.te_to)

        self.btn_save_form = _btn("💾 Lưu", "#27AE60")
        self.btn_cancel    = _btn("✖ Hủy", "#7F8C8D")
        fl.addWidget(self.btn_save_form)
        fl.addWidget(self.btn_cancel)
        fl.addStretch()
        root.addWidget(form_frame)
        self._editing_id = None

        # ── Kết nối ─────────────────────────────────────────────
        self.btn_seed.clicked.connect(self._seed)
        self.btn_add.clicked.connect(self._start_add)
        self.btn_edit.clicked.connect(self._start_edit)
        self.btn_del.clicked.connect(self._delete)
        self.btn_save_form.clicked.connect(self._save_form)
        self.btn_cancel.clicked.connect(self._cancel_form)
        self.table.itemDoubleClicked.connect(self._start_edit)

        self.load()

    # ── Seed ────────────────────────────────────────────────────
    def _seed(self):
        session = get_session()
        try:
            count = session.query(CaLamViec).count()
            if count >= 3:
                QMessageBox.information(self, "Đã có", "Đã có ca trong hệ thống."); return
            for ten, t_from, t_to, _ in CA_PRESETS:
                if session.query(CaLamViec).filter_by(ten_ca=ten).first():
                    continue
                h1, m1 = map(int, t_from.split(":"))
                h2, m2 = map(int, t_to.split(":"))
                session.add(CaLamViec(
                    ten_ca=ten,
                    gio_bat_dau=dtime(h1, m1),
                    gio_ket_thuc=dtime(h2, m2),
                ))
            session.commit()
        finally:
            session.close()
        self.load(); self.changed.emit()

    # ── Load ────────────────────────────────────────────────────
    def load(self):
        self.table.setRowCount(0)
        session = get_session()
        try:
            cas = session.query(CaLamViec).order_by(CaLamViec.id).all()
            for i, ca in enumerate(cas):
                self.table.insertRow(i)
                id_item = QTableWidgetItem(str(ca.id))
                id_item.setData(Qt.UserRole, ca.id)
                self.table.setItem(i, 0, id_item)

                name_item = QTableWidgetItem(ca.ten_ca)
                color = QColor(CA_COLOR.get(ca.ten_ca, "#A1A1AA"))
                name_item.setForeground(color)
                f = name_item.font(); f.setBold(True); name_item.setFont(f)
                self.table.setItem(i, 1, name_item)

                bd = ca.gio_bat_dau.strftime("%H:%M") if ca.gio_bat_dau else "—"
                kt = ca.gio_ket_thuc.strftime("%H:%M") if ca.gio_ket_thuc else "—"
                self.table.setItem(i, 2, QTableWidgetItem(bd))
                self.table.setItem(i, 3, QTableWidgetItem(kt))
        finally:
            session.close()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một ca!"); return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _start_add(self):
        self._editing_id = None
        self.txt_ten.clear(); self.te_from.setTime(QTime(6, 0)); self.te_to.setTime(QTime(14, 0))

    def _start_edit(self, *_):
        ca_id = self._selected_id()
        if not ca_id: return
        session = get_session()
        ca = session.query(CaLamViec).get(ca_id); session.close()
        if not ca: return
        self._editing_id = ca_id
        self.txt_ten.setText(ca.ten_ca)
        if ca.gio_bat_dau: self.te_from.setTime(QTime(ca.gio_bat_dau.hour, ca.gio_bat_dau.minute))
        if ca.gio_ket_thuc: self.te_to.setTime(QTime(ca.gio_ket_thuc.hour, ca.gio_ket_thuc.minute))

    def _cancel_form(self):
        self._editing_id = None
        self.txt_ten.clear()

    def _save_form(self):
        ten = self.txt_ten.text().strip()
        if not ten:
            QMessageBox.warning(self, "Thiếu", "Nhập tên ca!"); return
        qt_from = self.te_from.time(); qt_to = self.te_to.time()
        t_from = dtime(qt_from.hour(), qt_from.minute())
        t_to   = dtime(qt_to.hour(),   qt_to.minute())

        session = get_session()
        try:
            if self._editing_id:
                ca = session.query(CaLamViec).get(self._editing_id)
            else:
                ca = CaLamViec(); session.add(ca)
            ca.ten_ca = ten; ca.gio_bat_dau = t_from; ca.gio_ket_thuc = t_to
            session.commit()
        finally:
            session.close()
        self._cancel_form(); self.load(); self.changed.emit()

    def _delete(self):
        ca_id = self._selected_id()
        if not ca_id: return
        r = QMessageBox.question(self, "Xác nhận", "Xóa ca này? Mọi phân công liên quan sẽ bị xóa theo.",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r != QMessageBox.Yes: return
        session = get_session()
        try:
            session.query(PhanCongCaLam).filter_by(ma_ca=ca_id).delete()
            ca = session.query(CaLamViec).get(ca_id)
            if ca: session.delete(ca)
            session.commit()
        finally:
            session.close()
        self.load(); self.changed.emit()

    def get_shifts(self) -> list[CaLamViec]:
        session = get_session()
        cas = session.query(CaLamViec).order_by(CaLamViec.id).all()
        session.close()
        return cas


# ══════════════════════════════════════════════════════════════════════════════
# DRAG-AND-DROP: Widget NV có thể kéo
# ══════════════════════════════════════════════════════════════════════════════
class DraggableNVItem(QLabel):
    """Nhãn nhân viên kéo được. Gắn emp_id qua property."""

    def __init__(self, ten: str, emp_id: int, color: str = "#3498DB", parent=None):
        super().__init__(f"  👤 {ten}  ", parent)
        self.emp_id = emp_id
        self.ten_nv = ten
        self.setFixedHeight(32)
        self.setCursor(Qt.OpenHandCursor)
        self.setStyleSheet(
            f"background:{color}; color:white; border-radius:6px;"
            f" font-size:12px; font-weight:bold; padding:0 6px;"
        )

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"{self.emp_id}|{self.ten_nv}")
            drag.setMimeData(mime)
            px = QPixmap(self.size())
            self.render(px)
            drag.setPixmap(px)
            drag.exec(Qt.MoveAction)


class DropCaFrame(QFrame):
    """
    Ô nhận kéo thả của một ca trong một ngày.
    Hiển thị danh sách NV đã phân công.
    """
    nv_added   = Signal(int, int, object)   # emp_id, ca_id, ngay
    nv_removed = Signal(int, int, object)   # emp_id, ca_id, ngay

    def __init__(self, ca: CaLamViec, ngay: date, parent=None):
        super().__init__(parent)
        self.ca   = ca
        self.ngay = ngay
        self.setAcceptDrops(True)
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        color = CA_COLOR.get(ca.ten_ca, "#3E3E55")
        self.setStyleSheet(
            f"QFrame{{background:#2D2D3F;border:2px dashed {color};"
            f"border-radius:8px;}} "
            f"QFrame[drag_over='true']{{background:#3E3E55;}}"
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(4)

        lbl_ca = QLabel(ca.ten_ca)
        lbl_ca.setStyleSheet(f"color:{color};font-weight:bold;font-size:11px;border:none;")
        self._layout.addWidget(lbl_ca)

        self._nv_layout = QVBoxLayout()
        self._nv_layout.setSpacing(3)
        self._layout.addLayout(self._nv_layout)
        self._layout.addStretch()

        self._nv_ids: list[int] = []
        self._refresh()

    def _refresh(self):
        # Xoá widget cũ
        while self._nv_layout.count():
            item = self._nv_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self._nv_ids = []
        session = get_session()
        try:
            pcs = (session.query(PhanCongCaLam)
                   .filter_by(ma_ca=self.ca.id, ngay_lam=self.ngay).all())
            for pc in pcs:
                nv = session.query(NhanVien).get(pc.ma_nv)
                if not nv: continue
                self._nv_ids.append(nv.id)
                row = QHBoxLayout()
                lbl = QLabel(f"• {nv.ten_nv}")
                lbl.setStyleSheet("color:#ECF0F1;font-size:11px;border:none;")
                btn_rm = QPushButton("✖")
                btn_rm.setFixedSize(18, 18)
                btn_rm.setStyleSheet(
                    "background:#C0392B;color:white;border-radius:3px;font-size:10px;padding:0;"
                )
                btn_rm.clicked.connect(lambda _, nid=nv.id: self._remove(nid))
                row.addWidget(lbl); row.addStretch(); row.addWidget(btn_rm)
                container = QWidget()
                container.setLayout(row)
                container.setStyleSheet("background:transparent;")
                self._nv_layout.addWidget(container)
        finally:
            session.close()

        # Cảnh báo thiếu người
        if len(self._nv_ids) < MIN_NV_PER_CA:
            warn = QLabel(f"⚠ Cần thêm {MIN_NV_PER_CA - len(self._nv_ids)} NV")
            warn.setStyleSheet("color:#E74C3C;font-size:10px;font-style:italic;border:none;")
            self._nv_layout.addWidget(warn)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
        self.setProperty("drag_over", True); self.style().unpolish(self); self.style().polish(self)

    def dragLeaveEvent(self, e):
        self.setProperty("drag_over", False); self.style().unpolish(self); self.style().polish(self)

    def dropEvent(self, e):
        self.setProperty("drag_over", False); self.style().unpolish(self); self.style().polish(self)
        data = e.mimeData().text()
        if "|" not in data: return
        emp_id_str, ten = data.split("|", 1)
        emp_id = int(emp_id_str)

        # Kiểm tra trùng ca trong ngày
        session = get_session()
        try:
            # Trùng chính ca này?
            exists = session.query(PhanCongCaLam).filter_by(
                ma_nv=emp_id, ma_ca=self.ca.id, ngay_lam=self.ngay
            ).first()
            if exists:
                QMessageBox.warning(self.parent(), "Trùng",
                    f"{ten} đã có trong ca này!"); return

            # Trùng ca KHÁC trong cùng ngày?
            other = (session.query(PhanCongCaLam)
                     .filter(PhanCongCaLam.ma_nv == emp_id,
                             PhanCongCaLam.ngay_lam == self.ngay,
                             PhanCongCaLam.ma_ca    != self.ca.id)
                     .first())
            if other:
                ca_kia = session.query(CaLamViec).get(other.ma_ca)
                ten_ca_kia = ca_kia.ten_ca if ca_kia else "ca khác"
                r = QMessageBox.question(
                    self.parent(), "Cảnh báo trùng ca",
                    f"{ten} đã được phân công <b>{ten_ca_kia}</b> ngày này.<br>"
                    f"Vẫn tiếp tục thêm vào <b>{self.ca.ten_ca}</b>?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if r != QMessageBox.Yes: return

            pc = PhanCongCaLam(ma_nv=emp_id, ma_ca=self.ca.id, ngay_lam=self.ngay)
            session.add(pc); session.commit()
        finally:
            session.close()

        self._refresh()
        e.acceptProposedAction()

    def _remove(self, emp_id: int):
        session = get_session()
        try:
            pc = session.query(PhanCongCaLam).filter_by(
                ma_nv=emp_id, ma_ca=self.ca.id, ngay_lam=self.ngay
            ).first()
            if pc: session.delete(pc); session.commit()
        finally:
            session.close()
        self._refresh()

    def refresh(self):
        self._refresh()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PHÂN CÔNG (kéo thả + checkbox + hàng loạt + auto-fit)
# ══════════════════════════════════════════════════════════════════════════════
class AssignTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setSpacing(10)

        # ── Cột trái: danh sách NV có checkbox ──────────────────
        left = QFrame()
        left.setFixedWidth(220)
        left.setStyleSheet("QFrame{background:#2D2D3F;border-radius:10px;border:1px solid #3E3E55;}")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(10, 10, 10, 10)
        lv.setSpacing(6)

        lv.addWidget(_label("👥 NHÂN VIÊN", "#A1A1AA", 12, True))

        # Nút chọn tất cả / bỏ chọn
        sel_bar = QHBoxLayout()
        self.btn_select_all   = _btn("☑ Tất cả",  "#34495E", 26)
        self.btn_deselect_all = _btn("☐ Bỏ chọn", "#34495E", 26)
        self.btn_select_all.setFixedHeight(26)
        self.btn_deselect_all.setFixedHeight(26)
        sel_bar.addWidget(self.btn_select_all)
        sel_bar.addWidget(self.btn_deselect_all)
        lv.addLayout(sel_bar)

        # Scroll list NV với checkbox
        self.nv_area = QScrollArea()
        self.nv_area.setWidgetResizable(True)
        self.nv_area.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self.nv_container = QWidget()
        self.nv_container.setStyleSheet("background:transparent;")
        self.nv_vbox = QVBoxLayout(self.nv_container)
        self.nv_vbox.setSpacing(4)
        self.nv_vbox.setAlignment(Qt.AlignTop)
        self.nv_area.setWidget(self.nv_container)
        lv.addWidget(self.nv_area)

        # Nhãn đếm đã chọn
        self.lbl_selected = _label("Chưa chọn NV", "#7F8C8D", 11)
        lv.addWidget(self.lbl_selected)

        # Kéo thả (drag) label hint
        lv.addWidget(_label("💡 Kéo thả từng NV hoặc\ndùng nút hàng loạt bên phải",
                            "#7F8C8D", 10))

        root.addWidget(left)

        # ── Cột phải: chọn ngày + toolbar + lưới ca ─────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        # Toolbar ngày
        date_bar = QHBoxLayout()
        date_bar.addWidget(_label("Ngày:"))
        self.de_ngay = QDateEdit(QDate.currentDate())
        self.de_ngay.setCalendarPopup(True)
        self.de_ngay.setDisplayFormat("dd/MM/yyyy")
        self.de_ngay.setFixedWidth(130)
        date_bar.addWidget(self.de_ngay)

        btn_prev = _btn("◀", "#34495E", 32); btn_prev.setFixedWidth(36)
        btn_next = _btn("▶", "#34495E", 32); btn_next.setFixedWidth(36)
        btn_prev.clicked.connect(lambda: self._shift_day(-1))
        btn_next.clicked.connect(lambda: self._shift_day(+1))
        date_bar.addWidget(btn_prev); date_bar.addWidget(btn_next)

        self.lbl_ngay = _label("", "#F1C40F", 13, True)
        date_bar.addWidget(self.lbl_ngay)
        date_bar.addStretch()

        btn_reload = _btn("🔄 Làm mới", "#16A085", 32)
        btn_reload.clicked.connect(self._load_grid)
        date_bar.addWidget(btn_reload)
        right.addLayout(date_bar)

        # ── Toolbar phân công hàng loạt ─────────────────────────
        bulk_frame = QFrame()
        bulk_frame.setStyleSheet(
            "QFrame{background:#1A1A24;border-radius:8px;border:1px solid #3E3E55;}"
        )
        bulk_layout = QHBoxLayout(bulk_frame)
        bulk_layout.setContentsMargins(10, 8, 10, 8)
        bulk_layout.setSpacing(8)

        bulk_layout.addWidget(_label("⚡ Phân công hàng loạt:", "#F1C40F", 12, True))

        # Chọn ca đích
        bulk_layout.addWidget(_label("Ca:", "#A1A1AA", 12))
        self.cb_bulk_ca = QComboBox()
        self.cb_bulk_ca.setFixedWidth(130)
        bulk_layout.addWidget(self.cb_bulk_ca)

        # Chọn khoảng ngày
        bulk_layout.addWidget(_label("Từ:", "#A1A1AA", 12))
        self.de_bulk_from = QDateEdit(QDate.currentDate())
        self.de_bulk_from.setCalendarPopup(True)
        self.de_bulk_from.setDisplayFormat("dd/MM/yyyy")
        self.de_bulk_from.setFixedWidth(120)
        bulk_layout.addWidget(self.de_bulk_from)

        bulk_layout.addWidget(_label("Đến:", "#A1A1AA", 12))
        self.de_bulk_to = QDateEdit(QDate.currentDate().addDays(6))
        self.de_bulk_to.setCalendarPopup(True)
        self.de_bulk_to.setDisplayFormat("dd/MM/yyyy")
        self.de_bulk_to.setFixedWidth(120)
        bulk_layout.addWidget(self.de_bulk_to)

        self.btn_bulk_assign = _btn("📋 Phân công", "#2980B9", 34)
        self.btn_bulk_assign.setToolTip(
            "Phân công các NV đã tick vào ca và khoảng ngày được chọn"
        )
        bulk_layout.addWidget(self.btn_bulk_assign)

        # Auto-fit button
        self.btn_auto_fit = _btn("🤖 Auto-Fit", "#8E44AD", 34)
        self.btn_auto_fit.setToolTip(
            "Tự động điền đủ NV còn thiếu vào các ca trong ngày đang xem"
        )
        bulk_layout.addWidget(self.btn_auto_fit)

        right.addWidget(bulk_frame)

        # Lưới ca (kéo thả)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("QScrollArea{border:none;}")
        self.grid_widget = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.grid_scroll.setWidget(self.grid_widget)
        right.addWidget(self.grid_scroll)
        root.addLayout(right)

        # ── Kết nối ─────────────────────────────────────────────
        self.de_ngay.dateChanged.connect(lambda _: self._load_grid())
        self.btn_select_all.clicked.connect(self._select_all_nv)
        self.btn_deselect_all.clicked.connect(self._deselect_all_nv)
        self.btn_bulk_assign.clicked.connect(self._bulk_assign)
        self.btn_auto_fit.clicked.connect(self._auto_fit)

        # Danh sách NV data (id, ten, checkbox widget)
        self._nv_checkboxes: list[tuple[int, str, QCheckBox]] = []

        self.load()

    # ── Load toàn bộ ────────────────────────────────────────────
    def load(self):
        self._load_nv()
        self._load_grid()
        self._refresh_bulk_ca_combo()

    def _load_nv(self):
        # Xóa cũ
        while self.nv_vbox.count():
            item = self.nv_vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._nv_checkboxes.clear()

        session = get_session()
        try:
            nvs = (session.query(NhanVien)
                   .filter(NhanVien.trang_thai == "Đang làm việc")
                   .order_by(NhanVien.ten_nv).all())
            for nv in nvs:
                row_widget = QWidget()
                row_widget.setStyleSheet("background:transparent;")
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(4)

                # Checkbox
                cb = QCheckBox()
                cb.stateChanged.connect(self._update_selected_label)
                row_layout.addWidget(cb)

                # Draggable label
                drag_w = DraggableNVItem(nv.ten_nv, nv.id)
                drag_w.setFixedHeight(28)
                row_layout.addWidget(drag_w, 1)

                self.nv_vbox.addWidget(row_widget)
                self._nv_checkboxes.append((nv.id, nv.ten_nv, cb))
        finally:
            session.close()

        self._update_selected_label()

    def _refresh_bulk_ca_combo(self):
        self.cb_bulk_ca.clear()
        session = get_session()
        try:
            cas = session.query(CaLamViec).order_by(CaLamViec.id).all()
            for ca in cas:
                self.cb_bulk_ca.addItem(ca.ten_ca, ca.id)
        finally:
            session.close()

    def _update_selected_label(self):
        count = sum(1 for _, _, cb in self._nv_checkboxes if cb.isChecked())
        if count == 0:
            self.lbl_selected.setText("Chưa chọn NV nào")
            self.lbl_selected.setStyleSheet("color:#7F8C8D;font-size:11px;")
        else:
            self.lbl_selected.setText(f"✅ Đã chọn {count} NV")
            self.lbl_selected.setStyleSheet("color:#2ECC71;font-size:11px;font-weight:bold;")

    def _select_all_nv(self):
        for _, _, cb in self._nv_checkboxes:
            cb.setChecked(True)

    def _deselect_all_nv(self):
        for _, _, cb in self._nv_checkboxes:
            cb.setChecked(False)

    def _get_checked_nv(self) -> list[tuple[int, str]]:
        return [(nv_id, ten) for nv_id, ten, cb in self._nv_checkboxes if cb.isChecked()]

    # ── Phân công hàng loạt ─────────────────────────────────────
    def _bulk_assign(self):
        checked = self._get_checked_nv()
        if not checked:
            QMessageBox.warning(self, "Chưa chọn", "Hãy tick chọn ít nhất một nhân viên!"); return

        ca_id = self.cb_bulk_ca.currentData()
        if ca_id is None:
            QMessageBox.warning(self, "Chưa có ca", "Chưa có ca nào. Hãy tạo ca trước!"); return

        qd_from = self.de_bulk_from.date()
        qd_to   = self.de_bulk_to.date()
        if qd_from > qd_to:
            QMessageBox.warning(self, "Ngày lỗi", "Ngày bắt đầu phải ≤ ngày kết thúc!"); return

        date_from = date(qd_from.year(), qd_from.month(), qd_from.day())
        date_to   = date(qd_to.year(),   qd_to.month(),   qd_to.day())

        # Tính số ngày
        delta_days = (date_to - date_from).days + 1
        if delta_days > 60:
            r = QMessageBox.question(
                self, "Xác nhận",
                f"Bạn sắp phân công {len(checked)} NV × {delta_days} ngày. Tiếp tục?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if r != QMessageBox.Yes: return

        ca_ten = self.cb_bulk_ca.currentText()
        ok_count = 0
        skip_count = 0
        session = get_session()
        try:
            for nv_id, ten_nv in checked:
                cur = date_from
                while cur <= date_to:
                    exists = session.query(PhanCongCaLam).filter_by(
                        ma_nv=nv_id, ma_ca=ca_id, ngay_lam=cur
                    ).first()
                    if not exists:
                        session.add(PhanCongCaLam(ma_nv=nv_id, ma_ca=ca_id, ngay_lam=cur))
                        ok_count += 1
                    else:
                        skip_count += 1
                    cur += timedelta(days=1)
            session.commit()
        finally:
            session.close()

        msg = f"✅ Đã phân công {ok_count} lượt.\n"
        if skip_count:
            msg += f"⚠ Bỏ qua {skip_count} lượt đã tồn tại."
        QMessageBox.information(self, "Hoàn tất", msg)
        self._load_grid()

    # ── Auto-Fit: tự điền NV thiếu vào các ca trong ngày ────────
    def _auto_fit(self):
        qd = self.de_ngay.date()
        ngay = date(qd.year(), qd.month(), qd.day())

        session = get_session()
        try:
            cas = session.query(CaLamViec).order_by(CaLamViec.id).all()
            all_nv = (session.query(NhanVien)
                      .filter(NhanVien.trang_thai == "Đang làm việc")
                      .order_by(NhanVien.ten_nv).all())

            if not cas or not all_nv:
                QMessageBox.warning(self, "Không đủ dữ liệu",
                    "Cần có ca làm việc và nhân viên để dùng Auto-Fit."); return

            # Thu thập tình trạng hiện tại
            # nv_load[nv_id] = số ca đã được giao trong ngày
            nv_load: dict[int, int] = {nv.id: 0 for nv in all_nv}
            assigned_today: dict[int, set[int]] = {nv.id: set() for nv in all_nv}  # nv_id -> set(ca_id)

            existing = session.query(PhanCongCaLam).filter_by(ngay_lam=ngay).all()
            for pc in existing:
                if pc.ma_nv in nv_load:
                    nv_load[pc.ma_nv] += 1
                    assigned_today[pc.ma_nv].add(pc.ma_ca)

            # Với mỗi ca, điền thêm NV còn thiếu
            added_total = 0
            plan: list[str] = []  # mô tả để hiển thị preview

            for ca in cas:
                pcs_ca = [pc for pc in existing if pc.ma_ca == ca.id]
                current_count = len(pcs_ca)
                need = max(0, MIN_NV_PER_CA - current_count)
                if need == 0:
                    plan.append(f"✅ {ca.ten_ca}: đủ người ({current_count}/{MIN_NV_PER_CA})")
                    continue

                # Ưu tiên NV chưa có ca nào trong ngày, rồi sắp theo ít ca nhất
                assigned_nv_ids = {pc.ma_nv for pc in pcs_ca}
                candidates = sorted(
                    [nv for nv in all_nv if nv.id not in assigned_nv_ids],
                    key=lambda nv: nv_load[nv.id]
                )

                filled = []
                for nv in candidates:
                    if need <= 0: break
                    # Không cho phép cùng 1 ca trong ngày (đã lọc ở assigned_nv_ids)
                    pc_new = PhanCongCaLam(ma_nv=nv.id, ma_ca=ca.id, ngay_lam=ngay)
                    session.add(pc_new)
                    nv_load[nv.id] += 1
                    assigned_today[nv.id].add(ca.id)
                    filled.append(nv.ten_nv)
                    need -= 1
                    added_total += 1

                if filled:
                    plan.append(f"➕ {ca.ten_ca}: thêm {', '.join(filled)}")
                else:
                    plan.append(f"⚠ {ca.ten_ca}: thiếu {need} NV nhưng không còn ai trống")

            session.commit()
        finally:
            session.close()

        summary = "\n".join(plan)
        if added_total:
            QMessageBox.information(
                self, f"🤖 Auto-Fit — {ngay.strftime('%d/%m/%Y')}",
                f"Đã tự động thêm {added_total} phân công:\n\n{summary}"
            )
        else:
            QMessageBox.information(
                self, "🤖 Auto-Fit",
                f"Tất cả các ca đã đủ người:\n\n{summary}"
            )
        self._load_grid()

    # ── Load lưới ca kéo thả ────────────────────────────────────
    def _load_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        qd = self.de_ngay.date()
        ngay = date(qd.year(), qd.month(), qd.day())
        thu = WEEKDAYS_VI[ngay.weekday()]
        self.lbl_ngay.setText(f"  {thu} — {ngay.strftime('%d/%m/%Y')}")

        session = get_session()
        try:
            cas = session.query(CaLamViec).order_by(CaLamViec.id).all()
        finally:
            session.close()

        if not cas:
            self.grid_layout.addWidget(
                _label("Chưa có ca nào. Hãy tạo ca ở tab 'Tạo Ca'.", "#E74C3C", 14)
            )
            return

        for ca in cas:
            frame = DropCaFrame(ca, ngay)
            self.grid_layout.addWidget(frame)

        self.grid_layout.addStretch()

    def _shift_day(self, delta: int):
        self.de_ngay.setDate(self.de_ngay.date().addDays(delta))

    def refresh_shifts(self):
        self._load_grid()
        self._refresh_bulk_ca_combo()



# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LỊCH TUẦN
# ══════════════════════════════════════════════════════════════════════════════
class WeeklyCalendarTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # ── Toolbar tuần ────────────────────────────────────────
        bar = QHBoxLayout()
        bar.addWidget(_label("LỊCH TUẦN", "#3498DB", 16, True))
        bar.addStretch()
        btn_prev = _btn("◀ Tuần trước", "#34495E", 34)
        btn_next = _btn("Tuần sau ▶",   "#34495E", 34)
        btn_now  = _btn("📅 Tuần này",  "#2980B9", 34)
        btn_prev.clicked.connect(lambda: self._shift_week(-1))
        btn_next.clicked.connect(lambda: self._shift_week(+1))
        btn_now.clicked.connect(self._go_now)
        self.lbl_week = _label("", "#F1C40F", 13, True)
        for w in [btn_prev, btn_now, btn_next, self.lbl_week]:
            bar.addWidget(w)
        root.addLayout(bar)

        # ── Lưới cuộn ───────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea{border:none;}")
        self.inner = QWidget()
        self.inner.setStyleSheet("background:#1E1E2E;")
        self.grid = QGridLayout(self.inner)
        self.grid.setSpacing(6)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll)

        # Ngày đầu tuần (Thứ 2)
        today = date.today()
        self._week_start = today - timedelta(days=today.weekday())
        self.load()

    def load(self):
        # Xóa lưới cũ
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        ws = self._week_start
        we = ws + timedelta(days=6)
        self.lbl_week.setText(
            f"  {ws.strftime('%d/%m/%Y')} — {we.strftime('%d/%m/%Y')}"
        )

        session = get_session()
        try:
            cas = session.query(CaLamViec).order_by(CaLamViec.id).all()
        finally:
            session.close()

        if not cas:
            self.grid.addWidget(
                _label("Chưa có ca nào. Tạo ca ở tab 'Tạo Ca'.", "#E74C3C", 14),
                0, 0
            )
            return

        # ── Header: cột 0 trống, cột 1-7 = ngày ────────────────
        lbl0 = QLabel("Ca \\ Ngày")
        lbl0.setAlignment(Qt.AlignCenter)
        lbl0.setStyleSheet(
            "background:#1A1A24;color:#A1A1AA;font-weight:bold;"
            "border-radius:6px;padding:8px;font-size:12px;"
        )
        self.grid.addWidget(lbl0, 0, 0)

        today = date.today()
        for d in range(7):
            ngay = ws + timedelta(days=d)
            thu  = WEEKDAYS_VI[ngay.weekday()]
            is_today = (ngay == today)
            text = f"<b>{thu}</b><br>{ngay.strftime('%d/%m')}"
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setTextFormat(Qt.RichText)
            bg = "#2980B9" if is_today else "#2D2D3F"
            lbl.setStyleSheet(
                f"background:{bg};color:white;border-radius:6px;"
                f"padding:8px 4px;font-size:12px;"
            )
            self.grid.addWidget(lbl, 0, d + 1)

        # ── Các hàng ca ─────────────────────────────────────────
        for row, ca in enumerate(cas, start=1):
            # Nhãn ca
            color = CA_COLOR.get(ca.ten_ca, "#3E3E55")
            bd = ca.gio_bat_dau.strftime("%H:%M")  if ca.gio_bat_dau  else ""
            kt = ca.gio_ket_thuc.strftime("%H:%M") if ca.gio_ket_thuc else ""
            ca_lbl = QLabel(f"<b>{ca.ten_ca}</b><br><small>{bd}–{kt}</small>")
            ca_lbl.setTextFormat(Qt.RichText)
            ca_lbl.setAlignment(Qt.AlignCenter)
            ca_lbl.setStyleSheet(
                f"background:{color};color:white;border-radius:6px;"
                f"padding:8px 6px;font-size:12px;"
            )
            self.grid.addWidget(ca_lbl, row, 0)

            # Ô từng ngày
            for d in range(7):
                ngay = ws + timedelta(days=d)
                cell = self._make_cell(ca, ngay, today)
                self.grid.addWidget(cell, row, d + 1)

        # Stretch cuối
        self.grid.setRowStretch(len(cas) + 1, 1)
        for c in range(8):
            self.grid.setColumnStretch(c, 1)

    def _make_cell(self, ca: CaLamViec, ngay: date, today: date) -> QFrame:
        is_today = (ngay == today)
        border_color = "#3498DB" if is_today else "#3E3E55"

        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame{{background:#2D2D3F;border:1px solid {border_color};"
            f"border-radius:6px;}} "
        )
        vb = QVBoxLayout(frame)
        vb.setContentsMargins(4, 4, 4, 4)
        vb.setSpacing(2)

        session = get_session()
        try:
            pcs = (session.query(PhanCongCaLam)
                   .filter_by(ma_ca=ca.id, ngay_lam=ngay).all())
            if not pcs:
                lbl = QLabel("—")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color:#3E3E55;font-size:11px;border:none;")
                vb.addWidget(lbl)
            else:
                for pc in pcs:
                    nv = session.query(NhanVien).get(pc.ma_nv)
                    if not nv: continue
                    tt  = pc.trang_thai_dd or "Chưa điểm danh"
                    tt_color = {
                        "Đã check-in":     "#2ECC71",
                        "Đã check-out":    "#F1C40F",
                        "Vắng":            "#E74C3C",
                        "Chưa điểm danh": "#A1A1AA",
                    }.get(tt, "#A1A1AA")
                    lbl = QLabel(f"• {nv.ten_nv}")
                    lbl.setStyleSheet(
                        f"color:{tt_color};font-size:11px;border:none;"
                    )
                    vb.addWidget(lbl)

                # Cảnh báo thiếu người
                if len(pcs) < MIN_NV_PER_CA:
                    w = QLabel(f"⚠ thiếu {MIN_NV_PER_CA - len(pcs)} NV")
                    w.setStyleSheet("color:#E74C3C;font-size:10px;font-style:italic;border:none;")
                    vb.addWidget(w)
        finally:
            session.close()

        vb.addStretch()
        return frame

    def _shift_week(self, delta: int):
        self._week_start += timedelta(weeks=delta)
        self.load()

    def _go_now(self):
        today = date.today()
        self._week_start = today - timedelta(days=today.weekday())
        self.load()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH
# ══════════════════════════════════════════════════════════════════════════════
class ShiftManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📅 Quản Lý Ca Làm Việc")
        self.resize(1100, 700)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_shift  = ShiftTab()
        self.tab_assign = AssignTab()
        self.tab_week   = WeeklyCalendarTab()

        self.tabs.addTab(self.tab_shift,  "🕐  Tạo Ca")
        self.tabs.addTab(self.tab_assign, "📋  Phân Công")
        self.tabs.addTab(self.tab_week,   "📅  Lịch Tuần")

        root.addWidget(self.tabs)

        btn_close = _btn("Đóng", "#34495E", 40)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close)

        # Khi tab Tạo Ca thay đổi → cập nhật các tab khác
        self.tab_shift.changed.connect(self._on_shifts_changed)

        # Khi chuyển tab → reload
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_shifts_changed(self):
        self.tab_assign.refresh_shifts()
        self.tab_week.load()

    def _on_tab_changed(self, idx: int):
        if idx == 1: self.tab_assign.load()
        elif idx == 2: self.tab_week.load()