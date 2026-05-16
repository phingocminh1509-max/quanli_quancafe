"""
views/category_manager.py
══════════════════════════════════════════════════════════════════
Quản lý Phân Loại Sản Phẩm
  • Xem danh sách phân loại hiện có (lấy từ bảng SanPham)
  • Thêm phân loại mới (tên tuỳ chỉnh)
  • Đổi tên phân loại (cập nhật toàn bộ sản phẩm liên quan)
  • Xóa phân loại (chỉ khi không còn sản phẩm nào dùng)
  • Xem sản phẩm thuộc phân loại
══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QLineEdit, QAbstractItemView, QFrame, QSplitter,
    QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from database.db_config import get_session
from database.models import SanPham

# ── Phân loại mặc định gợi ý ─────────────────────────────────────────────────
DEFAULT_CATEGORIES = [
    "Cà Phê", "Trà", "Sinh Tố", "Nước Ép", "Bánh & Snack",
    "Đồ Ăn", "Nước Ngọt", "Khác",
]

STYLE = """
QDialog, QWidget { background-color: #1E1E2E; color: white; }
QTableWidget {
    background: #2D2D3F; border: none; border-radius: 8px;
    gridline-color: #3E3E55; color: white; font-size: 13px;
}
QTableWidget::item { padding: 7px; border-bottom: 1px solid #3E3E55; }
QTableWidget::item:selected { background: #3498DB; }
QHeaderView::section {
    background: #1A1A24; color: #A1A1AA;
    padding: 9px; border: none; font-weight: bold;
}
QLineEdit {
    background: #2D2D3F; border: 1px solid #3E3E55;
    border-radius: 6px; padding: 6px 10px; color: white; font-size: 13px;
}
QLineEdit:focus { border-color: #3498DB; }
QScrollBar:vertical { background: #1A1A24; width: 7px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #3E3E55; border-radius: 4px; }
QFrame#card {
    background: #2D2D3F; border: 1px solid #3E3E55; border-radius: 10px;
}
"""


def _btn(text: str, color: str, min_h: int = 36) -> QPushButton:
    b = QPushButton(text)
    b.setMinimumHeight(min_h)
    b.setStyleSheet(
        f"background:{color}; color:white; font-weight:bold;"
        f" border-radius:6px; font-size:12px; padding:0 12px;"
    )
    return b


def _lbl(text: str, color: str = "white", size: int = 13, bold: bool = False) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"color:{color}; font-size:{size}px;"
        + (" font-weight:bold;" if bold else "")
    )
    return l


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG THÊM / ĐỔI TÊN PHÂN LOẠI
# ══════════════════════════════════════════════════════════════════════════════
class CategoryNameDialog(QDialog):
    """Dialog nhập tên phân loại — hỗ trợ cả thêm mới và đổi tên."""

    def __init__(self, existing_name: str = "", all_categories: list[str] = None, parent=None):
        super().__init__(parent)
        self.all_categories = [c.strip().lower() for c in (all_categories or [])]
        self.is_edit = bool(existing_name)
        self.setWindowTitle("Đổi Tên Phân Loại" if self.is_edit else "Thêm Phân Loại Mới")
        self.resize(420, 260)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Tiêu đề
        title_color = "#2980B9" if self.is_edit else "#27AE60"
        title_icon  = "✏️ Đổi tên phân loại" if self.is_edit else "➕ Thêm phân loại mới"
        root.addWidget(_lbl(title_icon, title_color, 15, True))

        # Gợi ý (chỉ hiện khi thêm mới)
        if not self.is_edit:
            root.addWidget(_lbl("Gợi ý nhanh:", "#A1A1AA", 12))
            suggest_layout = QHBoxLayout()
            suggest_layout.setSpacing(6)
            for cat in DEFAULT_CATEGORIES:
                btn_s = QPushButton(cat)
                btn_s.setFixedHeight(28)
                btn_s.setStyleSheet(
                    "background:#2D2D3F; color:#A1A1AA; border:1px solid #3E3E55;"
                    " border-radius:4px; font-size:11px; padding:0 8px;"
                )
                btn_s.clicked.connect(lambda _, c=cat: self.txt_name.setText(c))
                suggest_layout.addWidget(btn_s)
            suggest_layout.addStretch()
            root.addLayout(suggest_layout)

        # Ô nhập tên
        lbl_input = _lbl("Tên phân loại *:", "#A1A1AA", 12)
        root.addWidget(lbl_input)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("VD: Cà Phê, Trà Sữa, Đồ Ăn Nhẹ…")
        self.txt_name.setMinimumHeight(40)
        if existing_name:
            self.txt_name.setText(existing_name)
            self.txt_name.selectAll()
        root.addWidget(self.txt_name)

        # Nút hành động
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()
        btn_cancel = _btn("✖ Hủy", "#7F8C8D", 40)
        btn_save   = _btn("💾 Lưu", "#27AE60", 40)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

        self.txt_name.returnPressed.connect(self._save)

    def get_name(self) -> str:
        return self.txt_name.text().strip()

    def _save(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu", "Tên phân loại không được để trống!"); return
        if name.lower() in self.all_categories:
            QMessageBox.warning(self, "Trùng", f"Phân loại '{name}' đã tồn tại!"); return
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH
# ══════════════════════════════════════════════════════════════════════════════
class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏷️ Quản Lý Phân Loại Sản Phẩm")
        self.resize(900, 580)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── Tiêu đề ──────────────────────────────────────────────
        header = QHBoxLayout()
        header.addWidget(_lbl("🏷️  QUẢN LÝ PHÂN LOẠI SẢN PHẨM", "#3498DB", 17, True))
        header.addStretch()
        root.addLayout(header)

        # ── Splitter: trái (danh sách loại) | phải (sản phẩm) ───
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background: #3E3E55; }")

        # ── Panel trái ───────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background:#1A1A24; border-radius:10px;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(10, 10, 10, 10)
        lv.setSpacing(8)

        lv.addWidget(_lbl("DANH SÁCH PHÂN LOẠI", "#3498DB", 13, True))

        # Thanh tìm kiếm
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm phân loại…")
        self.txt_search.textChanged.connect(self._on_search)
        lv.addWidget(self.txt_search)

        # Bảng phân loại
        self.tbl_cat = QTableWidget(0, 3)
        self.tbl_cat.setHorizontalHeaderLabels(["Tên Phân Loại", "Số SP", "Đang Bán"])
        hh = self.tbl_cat.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_cat.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_cat.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_cat.verticalHeader().setVisible(False)
        self.tbl_cat.selectionModel().selectionChanged.connect(self._on_cat_select)
        self.tbl_cat.itemDoubleClicked.connect(self._rename)
        lv.addWidget(self.tbl_cat)

        # Nút CRUD
        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        self.btn_add    = _btn("➕ Thêm",    "#27AE60")
        self.btn_rename = _btn("✏️ Đổi tên", "#2980B9")
        self.btn_del    = _btn("🗑 Xóa",     "#C0392B")
        for b in [self.btn_add, self.btn_rename, self.btn_del]:
            btn_row.addWidget(b)
        lv.addLayout(btn_row)

        self.btn_add.clicked.connect(self._add)
        self.btn_rename.clicked.connect(self._rename)
        self.btn_del.clicked.connect(self._delete)

        splitter.addWidget(left)

        # ── Panel phải ───────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background:#1A1A24; border-radius:10px;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 10, 10, 10)
        rv.setSpacing(8)

        self.lbl_sp_title = _lbl("Chọn phân loại để xem sản phẩm", "#A1A1AA", 13, True)
        rv.addWidget(self.lbl_sp_title)

        self.tbl_sp = QTableWidget(0, 4)
        self.tbl_sp.setHorizontalHeaderLabels(["ID", "Tên Sản Phẩm", "Giá Bán", "Trạng Thái"])
        hh2 = self.tbl_sp.horizontalHeader()
        hh2.setSectionResizeMode(0, QHeaderView.Fixed);  self.tbl_sp.setColumnWidth(0, 50)
        hh2.setSectionResizeMode(1, QHeaderView.Stretch)
        hh2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_sp.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_sp.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_sp.verticalHeader().setVisible(False)
        rv.addWidget(self.tbl_sp)

        # Thống kê nhanh
        self.lbl_stat = _lbl("", "#A1A1AA", 12)
        rv.addWidget(self.lbl_stat)

        splitter.addWidget(right)
        splitter.setSizes([340, 540])
        root.addWidget(splitter, stretch=1)

        # ── Nút đóng ────────────────────────────────────────────
        btn_close = _btn("Đóng", "#34495E", 40)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close)

        self._all_cats: list[dict] = []   # cache [{name, total, active}]
        self._load_cats()

    # ──────────────────────────────────────────────────────────────
    # Load dữ liệu
    # ──────────────────────────────────────────────────────────────
    def _load_cats(self, keep_selection: str | None = None):
        """Đọc danh sách phân loại từ DB (group by danh_muc trong SanPham)."""
        s = get_session()
        try:
            all_sp = s.query(SanPham).all()
        finally:
            s.close()

        # Nhóm theo danh_muc
        cat_map: dict[str, dict] = {}
        for sp in all_sp:
            cat = (sp.danh_muc or "Chưa phân loại").strip()
            if cat not in cat_map:
                cat_map[cat] = {"name": cat, "total": 0, "active": 0}
            cat_map[cat]["total"] += 1
            if sp.trang_thai == "Đang bán":
                cat_map[cat]["active"] += 1

        self._all_cats = sorted(cat_map.values(), key=lambda x: x["name"])
        self._fill_table(self._all_cats)

        # Khôi phục lại dòng đã chọn
        if keep_selection:
            for i in range(self.tbl_cat.rowCount()):
                if self.tbl_cat.item(i, 0) and self.tbl_cat.item(i, 0).text() == keep_selection:
                    self.tbl_cat.selectRow(i)
                    break

    def _fill_table(self, cats: list[dict]):
        self.tbl_cat.setRowCount(0)
        for i, c in enumerate(cats):
            self.tbl_cat.insertRow(i)
            name_it = QTableWidgetItem(c["name"])
            name_it.setData(Qt.UserRole, c["name"])
            self.tbl_cat.setItem(i, 0, name_it)

            tot_it = QTableWidgetItem(str(c["total"]))
            tot_it.setTextAlignment(Qt.AlignCenter)
            tot_it.setForeground(QColor("#A1A1AA"))
            self.tbl_cat.setItem(i, 1, tot_it)

            act_it = QTableWidgetItem(str(c["active"]))
            act_it.setTextAlignment(Qt.AlignCenter)
            act_it.setForeground(QColor("#2ECC71") if c["active"] > 0 else QColor("#E74C3C"))
            self.tbl_cat.setItem(i, 2, act_it)

    def _on_search(self, text: str):
        kw = text.strip().lower()
        filtered = [c for c in self._all_cats if kw in c["name"].lower()] if kw else self._all_cats
        self._fill_table(filtered)

    # ──────────────────────────────────────────────────────────────
    # Chọn phân loại → hiện sản phẩm
    # ──────────────────────────────────────────────────────────────
    def _on_cat_select(self):
        row = self.tbl_cat.currentRow()
        if row < 0:
            self.tbl_sp.setRowCount(0)
            self.lbl_sp_title.setText("Chọn phân loại để xem sản phẩm")
            self.lbl_stat.setText("")
            return
        cat_name = self.tbl_cat.item(row, 0).data(Qt.UserRole)
        self._load_products(cat_name)

    def _load_products(self, cat_name: str):
        self.lbl_sp_title.setText(f"📦  Sản phẩm: {cat_name}")
        self.tbl_sp.setRowCount(0)

        s = get_session()
        try:
            sps = (
                s.query(SanPham)
                .filter(SanPham.danh_muc == cat_name)
                .order_by(SanPham.ten_sp)
                .all()
            )
            rows = [
                {"id": sp.id, "ten": sp.ten_sp, "gia": sp.gia_ban, "tt": sp.trang_thai}
                for sp in sps
            ]
        finally:
            s.close()

        total = len(rows)
        active = sum(1 for r in rows if r["tt"] == "Đang bán")

        for i, r in enumerate(rows):
            self.tbl_sp.insertRow(i)
            id_it = QTableWidgetItem(str(r["id"]))
            id_it.setTextAlignment(Qt.AlignCenter)
            id_it.setForeground(QColor("#A1A1AA"))
            self.tbl_sp.setItem(i, 0, id_it)
            self.tbl_sp.setItem(i, 1, QTableWidgetItem(r["ten"] or ""))

            gia_it = QTableWidgetItem(f"{int(r['gia'] or 0):,} đ")
            gia_it.setForeground(QColor("#F1C40F"))
            self.tbl_sp.setItem(i, 2, gia_it)

            tt_it = QTableWidgetItem(r["tt"] or "")
            tt_it.setForeground(QColor(
                "#2ECC71" if r["tt"] == "Đang bán" else "#E74C3C"
            ))
            self.tbl_sp.setItem(i, 3, tt_it)

        self.lbl_stat.setText(
            f"Tổng: {total} sản phẩm  •  Đang bán: {active}  •  Ngừng bán: {total - active}"
        )

    # ──────────────────────────────────────────────────────────────
    # Lấy tên loại đang chọn
    # ──────────────────────────────────────────────────────────────
    def _selected_name(self) -> str | None:
        row = self.tbl_cat.currentRow()
        if row < 0:
            QMessageBox.information(self, "", "Hãy chọn một phân loại!"); return None
        it = self.tbl_cat.item(row, 0)
        return it.data(Qt.UserRole) if it else None

    def _all_cat_names(self) -> list[str]:
        return [c["name"] for c in self._all_cats]

    # ──────────────────────────────────────────────────────────────
    # THÊM phân loại mới
    # ──────────────────────────────────────────────────────────────
    def _add(self):
        dlg = CategoryNameDialog(
            existing_name="",
            all_categories=self._all_cat_names(),
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        new_name = dlg.get_name()
        if not new_name:
            return

        # Phân loại chưa có sản phẩm nào — chỉ cần ghi nhận bằng cách
        # tạo placeholder hoặc thông báo thành công. Thực ra danh mục tồn tại
        # khi có ít nhất 1 SP gán vào. Ta lưu vào bảng riêng nếu có, còn
        # không thì thông báo để user dùng khi tạo sản phẩm.
        #
        # Kiểm tra xem model có bảng DanhMucSanPham không; nếu không thì
        # lưu vào settings JSON.
        try:
            from database.models import DanhMucSanPham  # type: ignore
            s = get_session()
            try:
                exists = s.query(DanhMucSanPham).filter_by(ten_danh_muc=new_name).first()
                if not exists:
                    dm = DanhMucSanPham(ten_danh_muc=new_name)
                    s.add(dm); s.commit()
            finally:
                s.close()
        except ImportError:
            # Không có bảng riêng — lưu vào file JSON đơn giản
            self._save_extra_category(new_name)

        QMessageBox.information(
            self, "Đã thêm",
            f"✅ Đã thêm phân loại <b>'{new_name}'</b>.<br><br>"
            f"Phân loại sẽ xuất hiện khi có sản phẩm được gán vào."
        )
        self._load_cats()

    # ──────────────────────────────────────────────────────────────
    # ĐỔI TÊN phân loại
    # ──────────────────────────────────────────────────────────────
    def _rename(self):
        old_name = self._selected_name()
        if old_name is None:
            return

        other_cats = [c for c in self._all_cat_names() if c != old_name]
        dlg = CategoryNameDialog(
            existing_name=old_name,
            all_categories=other_cats,
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        new_name = dlg.get_name()
        if not new_name or new_name == old_name:
            return

        # Đổi tên trên toàn bộ sản phẩm
        s = get_session()
        try:
            updated = (
                s.query(SanPham)
                .filter(SanPham.danh_muc == old_name)
                .all()
            )
            count = len(updated)
            for sp in updated:
                sp.danh_muc = new_name
            s.commit()
        except Exception as e:
            s.rollback()
            QMessageBox.critical(self, "Lỗi DB", str(e)); return
        finally:
            s.close()

        QMessageBox.information(
            self, "Đã đổi tên",
            f"✅ Đổi '<b>{old_name}</b>' → '<b>{new_name}</b>'<br>"
            f"({count} sản phẩm đã được cập nhật)"
        )
        self._load_cats(keep_selection=new_name)

    # ──────────────────────────────────────────────────────────────
    # XÓA phân loại
    # ──────────────────────────────────────────────────────────────
    def _delete(self):
        name = self._selected_name()
        if name is None:
            return

        # Kiểm tra còn SP không
        s = get_session()
        try:
            count = s.query(SanPham).filter(SanPham.danh_muc == name).count()
        finally:
            s.close()

        if count > 0:
            ans = QMessageBox.question(
                self, "Còn sản phẩm",
                f"Phân loại '<b>{name}</b>' đang có <b>{count}</b> sản phẩm.<br><br>"
                f"Bạn muốn chuyển tất cả sản phẩm sang loại '<b>Khác</b>' rồi xóa?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return

            # Chuyển tất cả sang "Khác"
            s = get_session()
            try:
                for sp in s.query(SanPham).filter(SanPham.danh_muc == name).all():
                    sp.danh_muc = "Khác"
                s.commit()
            except Exception as e:
                s.rollback()
                QMessageBox.critical(self, "Lỗi DB", str(e)); return
            finally:
                s.close()

            QMessageBox.information(
                self, "Đã xóa",
                f"✅ Đã xóa phân loại '<b>{name}</b>'.<br>"
                f"{count} sản phẩm đã chuyển sang '<b>Khác</b>'."
            )
        else:
            confirm = QMessageBox.question(
                self, "Xác nhận xóa",
                f"Xóa phân loại '<b>{name}</b>'? (Không có sản phẩm nào dùng loại này)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
            QMessageBox.information(self, "Đã xóa", f"✅ Đã xóa phân loại '<b>{name}</b>'.")

        self.tbl_sp.setRowCount(0)
        self.lbl_sp_title.setText("Chọn phân loại để xem sản phẩm")
        self.lbl_stat.setText("")
        self._load_cats()

    # ──────────────────────────────────────────────────────────────
    # Lưu phân loại mới vào file JSON (fallback khi không có bảng DB)
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _save_extra_category(name: str):
        import json, os
        path = "data/extra_categories.json"
        os.makedirs("data", exist_ok=True)
        try:
            with open(path, "r", encoding="utf-8") as f:
                cats: list = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cats = []
        if name not in cats:
            cats.append(name)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cats, f, ensure_ascii=False, indent=2)