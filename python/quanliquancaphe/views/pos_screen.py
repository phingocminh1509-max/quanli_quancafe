"""
views/pos_screen.py
══════════════════════════════════════════════════════════════════
Màn hình POS bán hàng.

Thay đổi so với bản cũ:
  ✅ Thêm cột "Đơn Giá" cạnh "Thành Tiền"
  ✅ Click 1 lần vào ô SL → QLineEdit inline để nhập số lượng
  ✅ Giữ nguyên đúp chuột → dialog Topping / Đá / Đường / Ghi chú
  ✅ DiscountDialog tích hợp trong file (không import ngoài)
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QScrollArea, QGridLayout, QSizePolicy, QFrame,
    QDialog, QComboBox, QMessageBox, QButtonGroup,
    QRadioButton, QGroupBox, QTextEdit,
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QPixmap, QColor, QIntValidator

from database.db_config import get_session
from database.models import SanPham, KhuyenMai
from controllers.pos_controller import process_checkout

# ── Palette ──────────────────────────────────────────────────────────────────
BG_DARK  = "#1E1E2E"
BG_CARD  = "#2D2D3F"
BG_PANEL = "#252535"
ACCENT   = "#3498DB"
GREEN    = "#27AE60"
ORANGE   = "#E67E22"
RED      = "#E74C3C"
TEXT     = "#ECF0F1"
TEXT_DIM = "#A1A1AA"
GOLD     = "#F1C40F"
BORDER   = "#3E3E55"

STYLE_MAIN = f"""
QWidget      {{ background:{BG_DARK}; color:{TEXT}; font-family:'Segoe UI'; }}
QLabel       {{ background:transparent; }}
QScrollArea  {{ border:none; background:{BG_DARK}; }}
QScrollBar:vertical {{
    background:{BG_PANEL}; width:6px; border-radius:3px; margin:0;
}}
QScrollBar::handle:vertical {{
    background:{BORDER}; border-radius:3px; min-height:20px;
}}
QLineEdit {{
    background:{BG_CARD}; border:1px solid {BORDER};
    border-radius:6px; padding:6px 10px; color:{TEXT}; font-size:13px;
}}
QLineEdit:focus {{ border-color:{ACCENT}; }}
QPushButton {{
    border-radius:6px; font-weight:bold; font-size:13px;
    color:white; padding:6px 14px;
}}
QTableWidget {{
    background:{BG_CARD}; border:none; gridline-color:{BORDER};
    color:{TEXT}; font-size:13px; border-radius:8px;
}}
QTableWidget::item {{ padding:5px; border-bottom:1px solid {BORDER}; }}
QTableWidget::item:selected {{ background:{ACCENT}; color:white; }}
QHeaderView::section {{
    background:{BG_PANEL}; color:{TEXT_DIM}; padding:8px;
    border:none; font-weight:bold; font-size:12px;
}}
"""

STYLE_DLG = f"""
QDialog  {{ background:{BG_DARK}; color:{TEXT}; font-family:'Segoe UI'; }}
QWidget  {{ background:{BG_DARK}; color:{TEXT}; }}
QLabel   {{ background:transparent; color:{TEXT}; }}
QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background:{BG_CARD}; border:1px solid {BORDER};
    border-radius:6px; padding:6px 10px; color:{TEXT}; font-size:13px;
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border-color:{ACCENT}; }}
QComboBox::drop-down {{ border:none; }}
QComboBox QAbstractItemView {{
    background:{BG_CARD}; color:{TEXT};
    selection-background-color:{ACCENT};
}}
QGroupBox {{
    border:1px solid {BORDER}; border-radius:8px;
    margin-top:8px; padding-top:6px;
    color:{TEXT_DIM}; font-size:12px;
}}
QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; }}
QRadioButton {{
    color:{TEXT}; font-size:13px; spacing:6px; background:transparent;
}}
QRadioButton::indicator {{
    width:15px; height:15px; border-radius:8px;
    border:2px solid {BORDER}; background:{BG_DARK};
}}
QRadioButton::indicator:checked {{ background:{ACCENT}; border-color:{ACCENT}; }}
"""


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


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: ÁP DỤNG KHUYẾN MÃI  (tích hợp, không import ngoài)
# ══════════════════════════════════════════════════════════════════════════════
class DiscountDialog(QDialog):
    """
    Dialog áp dụng khuyến mãi — hỗ trợ đầy đủ loại MuaXTangY:
      • Tự đọc hóa đơn hiện tại (invoice_items) để đếm số lượng sp X
      • So khớp tên món trong hóa đơn với sp_mua lưu trong DB (ma_sp)
      • Nếu đủ X → tính ra số lượng quà Y (hỗ trợ nhiều bộ)
      • Preview real-time: ✅ đủ / ⚠️ thiếu bao nhiêu
      • Kết quả trả về:
          - KM tiền: result_discount > 0, result_gift = None
          - KM MuaXTangY: result_gift = {"name": tên_sp_tang, "qty": so_luong}
    """

    def __init__(self, grand_total: float, invoice_items: list[dict], parent=None):
        super().__init__(parent)
        self.grand_total   = grand_total
        # Chỉ lấy các dòng thường, bỏ quà tặng cũ khỏi kiểm tra điều kiện
        self.invoice_items = [it for it in invoice_items if not it.get("is_gift")]
        self.result_km_id    = None
        self.result_discount = 0.0
        self.result_gift     = None   # {"name": str, "qty": int} nếu MuaXTangY
        self._km_list: list  = []

        # Cache tên sp từ DB (ma_sp → ten_sp)
        self._sp_cache: dict[int, str] = {}
        self._load_sp_cache()

        self.setWindowTitle("🎉  Áp Dụng Khuyến Mãi")
        self.resize(460, 320)
        self.setStyleSheet(STYLE_DLG)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        root.addWidget(_lbl("Chọn Khuyến Mãi", ACCENT, 15, True))

        self.cb_km = QComboBox()
        self.cb_km.addItem("— Không áp dụng —", None)

        today = date.today()
        s = get_session()
        try:
            kms = (s.query(KhuyenMai).order_by(KhuyenMai.id.desc()).all())
            for km in kms:
                nhom = getattr(km, 'loai_nhom', 'Chung') or 'Chung'
                if nhom in ('DoiDiem', 'CaNhan'):
                    continue
                try:
                    if not km.con_hieu_luc(today):
                        continue
                except Exception:
                    continue

                loai = getattr(km, 'loai_km', '') or ''
                if loai == "MuaXTangY":
                    ten_x = self._sp_cache.get(km.ma_sp, f"SP#{km.ma_sp}") if km.ma_sp else "?"
                    ten_y = self._sp_cache.get(km.ma_sp_tang, f"SP#{km.ma_sp_tang}") if km.ma_sp_tang else "?"
                    sl_x  = km.so_luong_mua or 1
                    sl_y  = km.so_luong_tang or 1
                    label = f"🎁 {km.ten_km}  (Mua {sl_x}×{ten_x} → Tặng {sl_y}×{ten_y})"
                else:
                    suffix = "%" if getattr(km, 'kieu_giam', '') == "PhanTram" else "đ"
                    label  = f"{km.ten_km}  ({int(getattr(km, 'gia_tri_giam', 0))}{suffix})"

                self.cb_km.addItem(label, km.id)
                self._km_list.append(km)
        finally:
            s.close()

        root.addWidget(_lbl("Khuyến mãi:"))
        root.addWidget(self.cb_km)

        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet(
            f"color:{GOLD}; font-size:13px; font-weight:bold;"
            f" background:{BG_CARD}; border-radius:8px; padding:10px;"
        )
        self.lbl_preview.setMinimumHeight(52)
        root.addWidget(self.lbl_preview)

        self.cb_km.currentIndexChanged.connect(self._preview)
        self._preview()

        root.addStretch()

        row = QHBoxLayout()
        btn_huy = _btn("✖ Hủy",      "#7F8C8D", 40)
        btn_ok  = _btn("✅ Áp dụng", GREEN,      40)
        btn_huy.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._apply)
        row.addWidget(btn_huy)
        row.addWidget(btn_ok)
        root.addLayout(row)

    # ── Cache tên SP từ DB ────────────────────────────────────────
    def _load_sp_cache(self):
        s = get_session()
        try:
            sps = s.query(SanPham).all()
            for sp in sps:
                self._sp_cache[sp.id] = sp.ten_sp
        finally:
            s.close()

    def _sp_name(self, ma_sp) -> str:
        if not ma_sp:
            return "?"
        return self._sp_cache.get(int(ma_sp), f"SP#{ma_sp}")

    # ── Lấy KM đang chọn ─────────────────────────────────────────
    def _current_km(self):
        km_id = self.cb_km.currentData()
        if not km_id:
            return None
        for km in self._km_list:
            if km.id == km_id:
                return km
        return None

    # ── Đếm số lượng món X trong hóa đơn ─────────────────────────
    def _dem_qty_sp_mua(self, ma_sp: int) -> int:
        """Đếm tổng qty của sp có ma_sp trong hóa đơn (so sánh qua tên)."""
        ten_can = self._sp_name(ma_sp)
        total = 0
        for it in self.invoice_items:
            if it.get("name", "").strip() == ten_can.strip():
                total += it.get("qty", 0)
        return total

    # ── Kiểm tra điều kiện MuaXTangY ─────────────────────────────
    def _check_mxy(self, km) -> tuple[bool, str, int]:
        """
        Trả về (ok, thong_bao, so_luong_tang_thuc_te).
        so_luong_tang_thuc_te = (qty_x // so_luong_mua) * so_luong_tang
        """
        ma_sp_mua   = km.ma_sp
        sl_can_mua  = int(km.so_luong_mua or 1)
        sl_tang_1bo = int(km.so_luong_tang or 1)
        ten_x       = self._sp_name(ma_sp_mua)
        ten_y       = self._sp_name(km.ma_sp_tang)

        qty_co = self._dem_qty_sp_mua(ma_sp_mua)
        if qty_co < sl_can_mua:
            con_thieu = sl_can_mua - qty_co
            msg = (
                f"Cần thêm {con_thieu} × {ten_x} nữa\n"
                f"(Yêu cầu: {sl_can_mua},  trong hóa đơn: {qty_co})"
            )
            return False, msg, 0

        so_bo       = qty_co // sl_can_mua   # số bộ đủ điều kiện
        tong_tang   = sl_tang_1bo             # luôn tặng đúng 1 bộ (sl_tang), không nhân
        msg_ok = (
            f"✅  Đủ điều kiện!  ({qty_co} × {ten_x})\n"
            f"Mua {sl_can_mua} {ten_x}  →  Tặng {tong_tang} {ten_y} (miễn phí)"
        )
        return True, msg_ok, tong_tang

    # ── Tính tiền giảm (KM thường) ───────────────────────────────
    def _calc_discount(self, km) -> float:
        kieu = getattr(km, 'kieu_giam', '')
        val  = float(getattr(km, 'gia_tri_giam', 0) or 0)
        if kieu == "PhanTram":
            d = self.grand_total * val / 100.0
            cap = float(getattr(km, 'toi_da_giam', None) or 0)
            if cap:
                d = min(d, cap)
            return d
        return min(val, self.grand_total)

    # ── Preview real-time ────────────────────────────────────────
    def _preview(self):
        km = self._current_km()
        if km is None:
            self.lbl_preview.setText("Tiền giảm:  0 đ")
            self.lbl_preview.setStyleSheet(
                f"color:{TEXT_DIM}; font-size:13px; background:{BG_CARD};"
                f" border-radius:8px; padding:10px;"
            )
            return

        loai = getattr(km, 'loai_km', '') or ''
        if loai == "MuaXTangY":
            ok, msg, _ = self._check_mxy(km)
            color = "#2ECC71" if ok else RED
            self.lbl_preview.setText(msg)
            self.lbl_preview.setStyleSheet(
                f"color:{color}; font-size:13px; font-weight:bold;"
                f" background:{BG_CARD}; border-radius:8px; padding:10px;"
            )
        else:
            disc = self._calc_discount(km)
            self.lbl_preview.setText(f"Tiền giảm:  -{int(disc):,} đ")
            self.lbl_preview.setStyleSheet(
                f"color:{GOLD}; font-size:14px; font-weight:bold;"
                f" background:{BG_CARD}; border-radius:8px; padding:10px;"
            )

    # ── Áp dụng ──────────────────────────────────────────────────
    def _apply(self):
        km = self._current_km()
        if km is None:
            # Bỏ KM
            self.result_km_id    = None
            self.result_discount = 0.0
            self.result_gift     = None
            self.accept()
            return

        loai = getattr(km, 'loai_km', '') or ''
        if loai == "MuaXTangY":
            ok, msg, qty_tang = self._check_mxy(km)
            if not ok:
                QMessageBox.warning(self, "Chưa đủ điều kiện", msg)
                return
            ten_y = self._sp_name(km.ma_sp_tang)
            self.result_km_id    = km.id
            self.result_discount = 0.0
            self.result_gift     = {"name": ten_y, "qty": qty_tang}
        else:
            self.result_km_id    = km.id
            self.result_discount = self._calc_discount(km)
            self.result_gift     = None
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG: TOPPING / ĐÁ / ĐƯỜNG / GHI CHÚ  (nhấn đúp vào dòng hóa đơn)
# ══════════════════════════════════════════════════════════════════════════════
class ToppingDialog(QDialog):
    TOPPINGS   = ["Không topping", "Trân châu đen", "Trân châu trắng",
                  "Thạch cà phê", "Thạch flan", "Kem cheese", "Pudding", "Nha đam"]
    DA_OPTS    = ["Không đá", "Ít đá", "Bình thường", "Nhiều đá"]
    DUONG_OPTS = ["Không đường", "Ít ngọt", "Vừa", "Nhiều đường"]

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(f"🎨  Tùy chỉnh — {item.get('name', '')}")
        self.resize(460, 500)
        self.setStyleSheet(STYLE_DLG)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        root.addWidget(_lbl(f"☕  {item.get('name', '')}", ACCENT, 15, True))

        # Topping
        grp_top = QGroupBox("🧋  Topping")
        vt = QVBoxLayout(grp_top)
        self.cb_topping = QComboBox()
        self.cb_topping.addItems(self.TOPPINGS)
        idx = self.cb_topping.findText(item.get("topping", "Không topping"))
        if idx >= 0:
            self.cb_topping.setCurrentIndex(idx)
        vt.addWidget(self.cb_topping)
        root.addWidget(grp_top)

        # Đá
        grp_da = QGroupBox("🧊  Đá")
        hd = QHBoxLayout(grp_da)
        hd.setSpacing(10)
        self._da_grp = QButtonGroup(self)
        cur_da = item.get("da", "Bình thường")
        for opt in self.DA_OPTS:
            rb = QRadioButton(opt)
            rb.setChecked(opt == cur_da)
            self._da_grp.addButton(rb)
            hd.addWidget(rb)
        root.addWidget(grp_da)

        # Đường
        grp_duong = QGroupBox("🍬  Đường")
        hdu = QHBoxLayout(grp_duong)
        hdu.setSpacing(10)
        self._duong_grp = QButtonGroup(self)
        cur_duong = item.get("duong", "Vừa")
        for opt in self.DUONG_OPTS:
            rb = QRadioButton(opt)
            rb.setChecked(opt == cur_duong)
            self._duong_grp.addButton(rb)
            hdu.addWidget(rb)
        root.addWidget(grp_duong)

        # Ghi chú
        grp_note = QGroupBox("📝  Ghi chú")
        vn = QVBoxLayout(grp_note)
        self.txt_note = QTextEdit()
        self.txt_note.setPlaceholderText("Thêm ghi chú cho món này…")
        self.txt_note.setFixedHeight(72)
        self.txt_note.setText(item.get("note", ""))
        vn.addWidget(self.txt_note)
        root.addWidget(grp_note)

        root.addStretch()

        btn_row = QHBoxLayout()
        btn_huy  = _btn("✖ Hủy",  "#7F8C8D", 40)
        btn_save = _btn("💾 Lưu", GREEN,      40)
        btn_huy.clicked.connect(self.reject)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_huy)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    def _save(self):
        self.item["topping"] = self.cb_topping.currentText()
        b = self._da_grp.checkedButton()
        self.item["da"]    = b.text() if b else "Bình thường"
        b = self._duong_grp.checkedButton()
        self.item["duong"] = b.text() if b else "Vừa"
        self.item["note"]  = self.txt_note.toPlainText().strip()
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG HÓA ĐƠN
# Cột: Tên Món | SL | Đơn Giá | Thành Tiền | −/+
# ══════════════════════════════════════════════════════════════════════════════
class InvoiceTable(QTableWidget):
    """
    • Click vào ô SL  → QLineEdit inline nhập số lượng trực tiếp
    • Đúp vào bất kỳ ô → ToppingDialog (topping / đá / đường / ghi chú)
    • Nút − / + vẫn hoạt động bình thường
    """
    order_changed = Signal()

    COL_NAME  = 0
    COL_QTY   = 1
    COL_PRICE = 2   # Đơn Giá  ← MỚI
    COL_TOTAL = 3   # Thành Tiền
    COL_BTN   = 4   # −/+

    def __init__(self, parent=None):
        super().__init__(0, 5, parent)
        self.setHorizontalHeaderLabels(["Tên Món", "SL", "Đơn Giá", "Thành Tiền", ""])

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(self.COL_NAME,  QHeaderView.Stretch)
        hh.setSectionResizeMode(self.COL_QTY,   QHeaderView.Fixed)
        self.setColumnWidth(self.COL_QTY, 52)
        hh.setSectionResizeMode(self.COL_PRICE, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_TOTAL, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_BTN,   QHeaderView.Fixed)
        self.setColumnWidth(self.COL_BTN, 70)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)

        self._items:    list[dict]       = []
        self._qty_le:   QLineEdit | None = None
        self._qty_row:  int              = -1

        self.cellClicked.connect(self._on_click)
        self.cellDoubleClicked.connect(self._on_double_click)

    # ── Public ──────────────────────────────────────────────────
    def add_item(self, name: str, price: float):
        for it in self._items:
            if it["name"] == name and not it.get("is_gift"):
                it["qty"] += 1
                self._refresh()
                return
        self._items.append({
            "name": name, "qty": 1, "price": price,
            "note": "", "topping": "Không topping",
            "da": "Bình thường", "duong": "Vừa",
            "is_gift": False,
        })
        self._refresh()

    def add_gift(self, name: str, qty: int):
        """Thêm/cập nhật dòng quà tặng MuaXTangY (giá 0, khoá chỉnh sửa)."""
        for it in self._items:
            if it.get("is_gift") and it["name"] == name:
                it["qty"] = qty
                self._refresh()
                return
        self._items.append({
            "name": name, "qty": qty, "price": 0.0,
            "note": "", "topping": "Không topping",
            "da": "Bình thường", "duong": "Vừa",
            "is_gift": True,
        })
        self._refresh()

    def remove_gifts(self):
        """Xoá tất cả dòng quà tặng (gọi trước khi mở lại DiscountDialog)."""
        before = len(self._items)
        self._items = [it for it in self._items if not it.get("is_gift")]
        if len(self._items) != before:
            self._refresh()

    def get_items(self) -> list[dict]:
        return list(self._items)

    def clear_items(self):
        self._items.clear()
        self._refresh()

    def grand_total(self) -> float:
        # Quà tặng price=0 nên không ảnh hưởng, nhưng lọc rõ để chắc chắn
        return sum(it["qty"] * it["price"] for it in self._items if not it.get("is_gift"))

    # ── Render ──────────────────────────────────────────────────
    def _refresh(self):
        self._qty_le  = None
        self._qty_row = -1
        self.setRowCount(0)

        for row, it in enumerate(self._items):
            self.insertRow(row)
            is_gift = it.get("is_gift", False)

            # Tên món
            extras = []
            if is_gift:
                extras.append("🎁 Quà tặng — miễn phí")
            else:
                if it["topping"] != "Không topping": extras.append(it["topping"])
                if it["da"]      != "Bình thường":   extras.append(it["da"])
                if it["duong"]   != "Vừa":           extras.append(it["duong"])
                if it["note"]:                        extras.append(f"📝 {it['note']}")

            display = it["name"]
            row_h   = 40
            if extras:
                display += f"\n  ↳ {', '.join(extras)}"
                row_h    = 54
            self.setRowHeight(row, row_h)

            fg_main = "#2ECC71" if is_gift else TEXT

            name_it = QTableWidgetItem(display)
            name_it.setForeground(QColor(fg_main))
            self.setItem(row, self.COL_NAME, name_it)

            # SL
            qty_it = QTableWidgetItem(str(it["qty"]))
            qty_it.setTextAlignment(Qt.AlignCenter)
            qty_it.setForeground(QColor(fg_main))
            self.setItem(row, self.COL_QTY, qty_it)

            # Đơn Giá
            price_txt = "0 đ  🎁" if is_gift else f"{int(it['price']):,}đ"
            price_it  = QTableWidgetItem(price_txt)
            price_it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            price_it.setForeground(QColor("#2ECC71" if is_gift else TEXT_DIM))
            self.setItem(row, self.COL_PRICE, price_it)

            # Thành Tiền
            total_txt = "0 đ" if is_gift else f"{int(it['qty'] * it['price']):,}đ"
            total_it  = QTableWidgetItem(total_txt)
            total_it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_it.setForeground(QColor("#2ECC71" if is_gift else GOLD))
            self.setItem(row, self.COL_TOTAL, total_it)

            # Nút −/+ hoặc 🔒
            if is_gift:
                lock_w = QWidget()
                lock_w.setStyleSheet("background:transparent;")
                ll = QHBoxLayout(lock_w)
                ll.setContentsMargins(0, 0, 0, 0)
                lbl_lock = QLabel("🔒")
                lbl_lock.setAlignment(Qt.AlignCenter)
                lbl_lock.setStyleSheet("color:#2ECC71; font-size:16px; background:transparent;")
                ll.addWidget(lbl_lock)
                self.setCellWidget(row, self.COL_BTN, lock_w)
            else:
                btn_w = QWidget()
                btn_w.setStyleSheet("background:transparent;")
                hl = QHBoxLayout(btn_w)
                hl.setContentsMargins(2, 2, 2, 2)
                hl.setSpacing(3)
                btn_m = QPushButton("−")
                btn_p = QPushButton("+")
                for b, c in [(btn_m, RED), (btn_p, GREEN)]:
                    b.setFixedSize(28, 28)
                    b.setStyleSheet(
                        f"background:{c}; color:white; font-weight:bold;"
                        f" font-size:15px; border-radius:5px; padding:0;"
                    )
                btn_m.clicked.connect(lambda _, r=row: self._dec(r))
                btn_p.clicked.connect(lambda _, r=row: self._inc(r))
                hl.addWidget(btn_m)
                hl.addWidget(btn_p)
                self.setCellWidget(row, self.COL_BTN, btn_w)

        self.order_changed.emit()

    # ── Click đơn: cột SL → inline edit ─────────────────────────
    def _on_click(self, row: int, col: int):
        if row >= len(self._items) or self._items[row].get("is_gift"):
            return
        if col != self.COL_QTY:
            return
        if self._qty_le is not None and self._qty_row != row:
            self._commit_qty()

        le = QLineEdit(str(self._items[row]["qty"]))
        le.setAlignment(Qt.AlignCenter)
        le.setValidator(QIntValidator(1, 999))
        le.setStyleSheet(
            f"background:{BG_DARK}; color:{TEXT}; font-weight:bold;"
            f" font-size:14px; border:2px solid {ACCENT}; border-radius:4px;"
        )
        le.selectAll()
        le.installEventFilter(self)
        self._qty_le  = le
        self._qty_row = row
        le.editingFinished.connect(self._commit_qty)
        self.setCellWidget(row, self.COL_QTY, le)
        le.setFocus()

    def _commit_qty(self):
        if self._qty_le is None:
            return
        txt = self._qty_le.text().strip()
        row = self._qty_row
        try:
            qty = max(1, int(txt))
        except ValueError:
            qty = self._items[row]["qty"] if row < len(self._items) else 1
        if row < len(self._items):
            self._items[row]["qty"] = qty
        self._qty_le  = None
        self._qty_row = -1
        self._refresh()

    def eventFilter(self, obj, event):
        if (hasattr(self, "_qty_le") and
                self._qty_le is not None and
                obj is self._qty_le):
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self._commit_qty()
                    return True
                if event.key() == Qt.Key_Escape:
                    self._qty_le  = None
                    self._qty_row = -1
                    self._refresh()
                    return True
        return super().eventFilter(obj, event)

    # ── Đúp: mở ToppingDialog ────────────────────────────────────
    def _on_double_click(self, row: int, col: int):
        if row >= len(self._items) or self._items[row].get("is_gift"):
            return
        self._qty_le  = None
        self._qty_row = -1
        dlg = ToppingDialog(self._items[row], parent=self)
        if dlg.exec():
            self._refresh()

    # ── Tăng/giảm SL ────────────────────────────────────────────
    def _inc(self, row: int):
        if row < len(self._items) and not self._items[row].get("is_gift"):
            self._items[row]["qty"] += 1
            self._refresh()

    def _dec(self, row: int):
        if row < len(self._items) and not self._items[row].get("is_gift"):
            if self._items[row]["qty"] <= 1:
                self._items.pop(row)
            else:
                self._items[row]["qty"] -= 1
            self._refresh()


# ══════════════════════════════════════════════════════════════════════════════
# CARD SẢN PHẨM
# ══════════════════════════════════════════════════════════════════════════════
class ProductCard(QPushButton):
    clicked_item = Signal(str, float)

    def __init__(self, ten: str, gia: float, hinh: bytes | None = None, parent=None):
        super().__init__(parent)
        self.ten = ten
        self.gia = gia
        self.setMinimumSize(160, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background:{BG_CARD}; border:1px solid {BORDER};
                border-radius:10px; text-align:left; padding:8px; color:{TEXT};
            }}
            QPushButton:hover   {{ border:2px solid {ACCENT}; background:#33334A; }}
            QPushButton:pressed {{ background:#3E3E55; }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        img_lbl = QLabel()
        img_lbl.setFixedSize(54, 54)
        if hinh:
            pm = QPixmap()
            pm.loadFromData(hinh)
            img_lbl.setPixmap(pm.scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            img_lbl.setStyleSheet("border-radius:6px; background:#3E3E55;")
        else:
            img_lbl.setText("📦")
            img_lbl.setAlignment(Qt.AlignCenter)
            img_lbl.setStyleSheet(
                "border-radius:6px; background:#3E3E55;"
                " font-size:22px; color:#A1A1AA;"
            )
        layout.addWidget(img_lbl)

        info = QVBoxLayout()
        info.setSpacing(3)
        n = QLabel(ten)
        n.setStyleSheet(f"color:{TEXT}; font-weight:bold; font-size:13px;")
        n.setWordWrap(True)
        p = QLabel(f"{int(gia):,} đ")
        p.setStyleSheet(f"color:{GOLD}; font-size:12px; font-weight:bold;")
        info.addWidget(n)
        info.addWidget(p)
        info.addStretch()
        layout.addLayout(info)

        self.clicked.connect(lambda: self.clicked_item.emit(self.ten, self.gia))


# ══════════════════════════════════════════════════════════════════════════════
# MÀN HÌNH POS CHÍNH
# ══════════════════════════════════════════════════════════════════════════════
class POSScreen(QWidget):
    request_checkout = Signal()
    request_logout   = Signal()
    request_history  = Signal()
    request_report   = Signal()
    request_menu     = Signal()
    request_features = Signal()

    def __init__(self, nhan_vien_id: int = 1, ten_nv: str = "admin", parent=None):
        super().__init__(parent)
        self.nhan_vien_id = nhan_vien_id
        self.ten_nv       = ten_nv
        self.km_id        = None
        self.km_discount  = 0.0
        self.setStyleSheet(STYLE_MAIN)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ══ CỘT TRÁI ═════════════════════════════════════════════
        left = QVBoxLayout()
        left.setContentsMargins(12, 10, 6, 10)
        left.setSpacing(8)

        h_left = QHBoxLayout()
        h_left.addWidget(_lbl("📋  DANH MỤC MÓN", ACCENT, 17, True))
        h_left.addStretch()
        btn_co = _btn("⏹ Check-out Ca",           ORANGE, 36)
        btn_lo = _btn(f"🔴  Đăng xuất ({ten_nv})", RED,    36)
        btn_co.clicked.connect(self.request_checkout)
        btn_lo.clicked.connect(self.request_logout)
        h_left.addWidget(btn_co)
        h_left.addWidget(btn_lo)
        left.addLayout(h_left)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Nhập tên món để tìm kiếm nhanh…")
        self.txt_search.textChanged.connect(self._filter_products)
        left.addWidget(self.txt_search)

        self._cat_bar = QHBoxLayout()
        self._cat_bar.setSpacing(6)
        left.addLayout(self._cat_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self._inner = QWidget()
        self._inner.setStyleSheet(f"background:{BG_DARK};")
        self._prod_layout = QVBoxLayout(self._inner)
        self._prod_layout.setSpacing(12)
        self._prod_layout.setContentsMargins(0, 4, 0, 4)
        self.scroll.setWidget(self._inner)
        left.addWidget(self.scroll, stretch=1)

        bot = QHBoxLayout()
        bot.setSpacing(6)
        for text, sig in [
            ("📜 LỊCH SỬ",    self.request_history),
            ("📊 BÁO CÁO",    self.request_report),
            ("⚙️ MENU",        self.request_menu),
            ("≡ CHỨC NĂNG ▼", self.request_features),
        ]:
            b = QPushButton(text)
            b.setMinimumHeight(38)
            b.setStyleSheet(
                f"background:{BG_CARD}; color:{TEXT_DIM}; font-weight:bold;"
                f" border-radius:6px; font-size:12px; border:1px solid {BORDER};"
            )
            b.clicked.connect(sig)
            bot.addWidget(b)
        left.addLayout(bot)

        # ══ ĐƯỜNG KẺ ═════════════════════════════════════════════
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color:{BORDER};")

        # ══ CỘT PHẢI ═════════════════════════════════════════════
        right = QVBoxLayout()
        right.setContentsMargins(6, 10, 12, 10)
        right.setSpacing(8)

        title_r = _lbl("🧾  HÓA ĐƠN", GREEN, 17, True)
        title_r.setAlignment(Qt.AlignCenter)
        right.addWidget(title_r)

        self.invoice = InvoiceTable()
        self.invoice.order_changed.connect(self._update_totals)
        right.addWidget(self.invoice, stretch=1)

        btn_km = _btn("🎉  Áp dụng Khuyến Mãi", ORANGE, 40)
        btn_km.clicked.connect(self._apply_discount)
        right.addWidget(btn_km)

        # Khung tổng tiền
        frame_total = QFrame()
        frame_total.setStyleSheet(
            f"QFrame {{ background:{BG_CARD}; border-radius:10px;"
            f" border:1px solid {BORDER}; padding:2px; }}"
        )
        vt = QVBoxLayout(frame_total)
        vt.setContentsMargins(16, 10, 16, 10)
        vt.setSpacing(4)

        def _trow(text: str, color: str, bold: bool = False) -> QLabel:
            l = QLabel(text)
            l.setAlignment(Qt.AlignRight)
            l.setStyleSheet(
                f"color:{color}; font-size:{'14' if bold else '13'}px;"
                f" background:transparent;"
                + (" font-weight:bold;" if bold else "")
            )
            vt.addWidget(l)
            return l

        self.lbl_subtotal = _trow("Tổng:          0 đ",             TEXT_DIM)
        self.lbl_vat      = _trow("Thuế 10%:      0 đ",             TEXT_DIM)
        self.lbl_discount = _trow("Giảm:          0 đ",             RED)
        self.lbl_total    = _trow("CẦN THANH TOÁN:   0 đ",          GOLD, True)
        right.addWidget(frame_total)

        btn_pay = QPushButton("✅  XUẤT HÓA ĐƠN")
        btn_pay.setMinimumHeight(52)
        btn_pay.setStyleSheet(
            f"background:{GREEN}; color:white; font-size:16px;"
            f" font-weight:bold; border-radius:10px;"
        )
        btn_pay.clicked.connect(self._checkout)
        right.addWidget(btn_pay)

        # Ghép
        left_w = QWidget(); left_w.setLayout(left); left_w.setMinimumWidth(560)
        right_w = QWidget(); right_w.setLayout(right); right_w.setFixedWidth(510)
        root.addWidget(left_w, stretch=1)
        root.addWidget(sep)
        root.addWidget(right_w)

        self._all_products: list[dict]      = []
        self._cat_names:    list[str]       = []   # danh sách tên danh mục (string)
        self._cat_btns:     list[QPushButton] = []
        self._current_cat:  str | None      = None  # tên danh mục đang chọn (string)
        self._load_products()

    # ── Load sản phẩm ────────────────────────────────────────────
    def _load_products(self):
        """Tải sản phẩm từ DB; danh mục là SanPham.danh_muc (string)."""
        s = get_session()
        try:
            sps = (s.query(SanPham)
                   .filter(SanPham.trang_thai == "Đang bán")
                   .order_by(SanPham.danh_muc, SanPham.ten_sp)
                   .all())
            self._all_products = [
                {
                    "name":  sp.ten_sp,
                    "price": float(sp.gia_ban or 0),
                    "cat":   (sp.danh_muc or "Khác").strip(),
                    "hinh":  sp.hinh_anh,
                }
                for sp in sps
            ]
        finally:
            s.close()

        # Gom danh mục duy nhất theo thứ tự xuất hiện
        seen: list[str] = []
        for p in self._all_products:
            if p["cat"] not in seen:
                seen.append(p["cat"])
        self._cat_names = seen

        self._build_cat_bar()
        self._render_products(self._all_products)

    def _build_cat_bar(self):
        while self._cat_bar.count():
            item = self._cat_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cat_btns = []

        btn_all = QPushButton("Tất cả")
        btn_all.setCheckable(True)
        btn_all.setChecked(True)
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.setStyleSheet(self._cs(True))
        btn_all.clicked.connect(lambda: self._set_cat(None, btn_all))
        self._cat_bar.addWidget(btn_all)
        self._cat_btns.append(btn_all)

        for cname in self._cat_names:
            b = QPushButton(cname)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(self._cs(False))
            b.clicked.connect(lambda _, cn=cname, btn=b: self._set_cat(cn, btn))
            self._cat_bar.addWidget(b)
            self._cat_btns.append(b)

        self._cat_bar.addStretch()

    def _cs(self, active: bool) -> str:
        bg = ACCENT if active else BG_CARD
        return (
            f"QPushButton {{ background:{bg}; color:white; border-radius:14px;"
            f" font-size:13px; font-weight:bold; padding:5px 14px;"
            f" border:1px solid {BORDER}; }}"
            f"QPushButton:hover {{ background:{ACCENT}; }}"
        )

    def _set_cat(self, cat_name: str | None, active_btn: QPushButton):
        self._current_cat = cat_name
        for b in self._cat_btns:
            b.setChecked(b is active_btn)
            b.setStyleSheet(self._cs(b is active_btn))
        self._filter_products(self.txt_search.text())

    def _filter_products(self, keyword: str = ""):
        kw = keyword.strip().lower()
        filtered = [
            p for p in self._all_products
            if (self._current_cat is None or p["cat"] == self._current_cat)
            and (not kw or kw in p["name"].lower())
        ]
        self._render_products(filtered)

    def _render_products(self, products: list[dict]):
        while self._prod_layout.count():
            item = self._prod_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Nhóm theo tên danh mục (string)
        by_cat: dict[str, list] = {}
        for p in products:
            by_cat.setdefault(p["cat"], []).append(p)

        for cat_name, items in by_cat.items():
            lbl = QLabel(cat_name)
            lbl.setStyleSheet(
                f"color:{ACCENT}; font-size:14px; font-weight:bold;"
                f" border-bottom:1px solid {BORDER}; padding-bottom:4px;"
            )
            self._prod_layout.addWidget(lbl)

            gw = QWidget()
            gl = QGridLayout(gw)
            gl.setSpacing(8)
            gl.setContentsMargins(0, 0, 0, 0)
            COLS = 3
            for idx, p in enumerate(items):
                card = ProductCard(p["name"], p["price"], p["hinh"])
                card.clicked_item.connect(self.invoice.add_item)
                gl.addWidget(card, idx // COLS, idx % COLS)
            self._prod_layout.addWidget(gw)

        self._prod_layout.addStretch()

    # ── Cập nhật tổng tiền ───────────────────────────────────────
    def _update_totals(self):
        sub   = self.invoice.grand_total()
        vat   = sub * 0.10
        disc  = self.km_discount
        total = max(0.0, sub + vat - disc)
        self.lbl_subtotal.setText(f"Tổng:          {int(sub):,} đ")
        self.lbl_vat.setText(     f"Thuế 10%:      {int(vat):,} đ")
        self.lbl_discount.setText(
            f"Giảm:          -{int(disc):,} đ" if disc else "Giảm:          0 đ"
        )
        self.lbl_total.setText(f"CẦN THANH TOÁN:   {int(total):,} đ")

    # ── Áp dụng khuyến mãi ──────────────────────────────────────
    def _apply_discount(self):
        # Xoá quà tặng cũ trước (tránh tính vào điều kiện kiểm tra)
        self.invoice.remove_gifts()

        dlg = DiscountDialog(
            grand_total   = self.invoice.grand_total(),
            invoice_items = self.invoice.get_items(),
            parent        = self,
        )
        if dlg.exec():
            self.km_id       = dlg.result_km_id
            self.km_discount = dlg.result_discount
            if dlg.result_gift:
                g = dlg.result_gift
                self.invoice.add_gift(g["name"], g["qty"])
            self._update_totals()

    # ── Thanh toán ───────────────────────────────────────────────
    def _checkout(self):
        items = self.invoice.get_items()
        if not items:
            QMessageBox.warning(self, "Trống", "Chưa có món nào trong hóa đơn!")
            return

        order_items = []
        for it in items:
            if it.get("is_gift"):
                order_items.append({
                    "name":  it["name"],
                    "qty":   it["qty"],
                    "price": 0.0,
                    "note":  "🎁 Quà tặng KM",
                })
            else:
                parts = []
                if it["topping"] != "Không topping": parts.append(it["topping"])
                if it["da"]      != "Bình thường":   parts.append(it["da"])
                if it["duong"]   != "Vừa":           parts.append(it["duong"])
                if it["note"]:                        parts.append(it["note"])
                order_items.append({
                    "name":  it["name"],
                    "qty":   it["qty"],
                    "price": it["price"],
                    "note":  " | ".join(parts),
                })

        ok, msg = process_checkout(
            order_items, self.nhan_vien_id,
            self.km_id, self.km_discount,
        )
        if ok:
            QMessageBox.information(self, "✅  Thành công", msg)
            self.invoice.clear_items()
            self.km_id       = None
            self.km_discount = 0.0
            self._update_totals()
        else:
            QMessageBox.critical(self, "❌  Lỗi", msg)