"""
views/product_manager.py
Quản lý danh mục sản phẩm — có thêm chức năng chọn ảnh cho món.
"""
import os
import shutil

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QMessageBox, QFormLayout, QComboBox, QLabel,
    QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

from database.db_config import get_session
from database.models import SanPham

# Thư mục lưu ảnh sản phẩm (tự tạo nếu chưa có)
PRODUCT_IMAGE_DIR = "product_images"
os.makedirs(PRODUCT_IMAGE_DIR, exist_ok=True)


def get_product_image_path(product_id: int) -> str | None:
    """Trả về đường dẫn ảnh đầu tiên tìm thấy, None nếu chưa có."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = os.path.join(PRODUCT_IMAGE_DIR, f"{product_id}.{ext}")
        if os.path.exists(path):
            return path
    return None


def save_product_image(product_id: int, src_path: str) -> str:
    """
    Copy ảnh vào thư mục product_images với tên <id>.<ext>.
    Xóa ảnh cũ cùng id (nếu có) trước khi lưu mới.
    Trả về đường dẫn đích.
    """
    # Xóa ảnh cũ
    for ext in ("jpg", "jpeg", "png", "webp"):
        old = os.path.join(PRODUCT_IMAGE_DIR, f"{product_id}.{ext}")
        if os.path.exists(old):
            os.remove(old)

    ext = os.path.splitext(src_path)[1].lower().lstrip(".")
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    dst = os.path.join(PRODUCT_IMAGE_DIR, f"{product_id}.{ext}")
    shutil.copy2(src_path, dst)
    return dst


# ─────────────────────────────────────────────
# FORM THÊM / SỬA SẢN PHẨM (có chọn ảnh)
# ─────────────────────────────────────────────
class ProductForm(QDialog):
    def __init__(self, parent=None, product: SanPham = None):
        super().__init__(parent)
        self.product = product          # None = thêm mới
        self._pending_image_path = None # Đường dẫn ảnh người dùng vừa chọn (chưa lưu)

        self.setWindowTitle("Thêm Món Mới" if not product else f"Sửa: {product.ten_sp}")
        self.resize(460, 400)
        self.setStyleSheet("""
            QDialog { background-color: #1E1E2E; color: white; }
            QLabel  { color: #E2E8F0; font-weight: bold; }
            QLineEdit, QComboBox {
                background-color: #2D2D3F; border: 1px solid #475569;
                border-radius: 6px; padding: 8px; color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3498DB; background-color: #35354A;
            }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)

        self.txt_name  = QLineEdit()
        self.txt_price = QLineEdit()
        self.txt_cost  = QLineEdit()
        self.txt_cost.setPlaceholderText("Giá vốn ước tính (tùy chọn)")

        self.cb_danhmuc = QComboBox()
        self.cb_danhmuc.addItems(["Cà phê", "Trà", "Sinh tố", "Bánh", "Đồ ăn", "Khác"])
        self.cb_danhmuc.setEditable(True)

        self.cb_trangthai = QComboBox()
        self.cb_trangthai.addItems(["Đang bán", "Ngừng bán", "Hết hàng"])

        form.addRow("Tên món *:", self.txt_name)
        form.addRow("Giá bán (đ) *:", self.txt_price)
        form.addRow("Giá vốn (đ):", self.txt_cost)
        form.addRow("Danh mục:", self.cb_danhmuc)
        form.addRow("Trạng thái:", self.cb_trangthai)
        layout.addLayout(form)

        # ── KHU VỰC CHỌN ẢNH ────────────────────────────────────
        img_row = QHBoxLayout()

        self.img_preview = QLabel()
        self.img_preview.setFixedSize(80, 80)
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setStyleSheet(
            "background-color: #2D2D3F; border: 2px dashed #475569;"
            " border-radius: 10px; color: #A1A1AA; font-size: 28px;"
        )
        self.img_preview.setText("🖼️")
        img_row.addWidget(self.img_preview)

        img_btn_col = QVBoxLayout()
        btn_pick = QPushButton("📂 Chọn ảnh")
        btn_pick.setStyleSheet(
            "background-color: #2980B9; color: white; font-weight: bold;"
            " padding: 8px; border-radius: 6px;"
        )
        btn_pick.clicked.connect(self._pick_image)

        btn_clear = QPushButton("🗑️ Xóa ảnh")
        btn_clear.setStyleSheet(
            "background-color: #7F8C8D; color: white; font-weight: bold;"
            " padding: 8px; border-radius: 6px;"
        )
        btn_clear.clicked.connect(self._clear_image)

        img_btn_col.addWidget(btn_pick)
        img_btn_col.addWidget(btn_clear)

        hint = QLabel("JPG / PNG / WEBP\nNên dùng ảnh vuông")
        hint.setStyleSheet("color: #64748B; font-size: 11px; font-weight: normal;")
        img_btn_col.addWidget(hint)

        img_row.addLayout(img_btn_col)
        img_row.addStretch()
        layout.addLayout(img_row)

        # Điền sẵn dữ liệu nếu đang sửa
        if product:
            self.txt_name.setText(product.ten_sp)
            self.txt_price.setText(str(int(product.gia_ban)))
            self.txt_cost.setText(str(int(product.gia_nhap or 0)))
            idx = self.cb_danhmuc.findText(product.danh_muc or "")
            if idx >= 0:
                self.cb_danhmuc.setCurrentIndex(idx)
            else:
                self.cb_danhmuc.setCurrentText(product.danh_muc or "Khác")
            idx2 = self.cb_trangthai.findText(product.trang_thai or "Đang bán")
            if idx2 >= 0:
                self.cb_trangthai.setCurrentIndex(idx2)
            # Load ảnh hiện tại
            existing = get_product_image_path(product.id)
            if existing:
                self._load_preview(existing)

        btn_save = QPushButton("💾 Lưu")
        btn_save.setMinimumHeight(42)
        btn_save.setStyleSheet(
            "background-color: #27AE60; color: white; font-weight: bold; border-radius: 8px;"
        )
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

    # ── Helpers ảnh ────────────────────────────────────────────────
    def _load_preview(self, path: str):
        px = QPixmap(path).scaled(80, 80, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        if px.width() > 80 or px.height() > 80:
            x = (px.width() - 80) // 2
            y = (px.height() - 80) // 2
            px = px.copy(x, y, 80, 80)
        self.img_preview.setPixmap(px)
        self.img_preview.setStyleSheet(
            "background-color: #2D2D3F; border: 2px solid #27AE60; border-radius: 10px;"
        )

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh sản phẩm", "",
            "Ảnh (*.jpg *.jpeg *.png *.webp)"
        )
        if path:
            self._pending_image_path = path
            self._load_preview(path)

    def _clear_image(self):
        """Đánh dấu xóa ảnh — sẽ xóa file thật khi nhấn Lưu."""
        self._pending_image_path = "__DELETE__"
        self.img_preview.setPixmap(QPixmap())
        self.img_preview.setText("🖼️")
        self.img_preview.setStyleSheet(
            "background-color: #2D2D3F; border: 2px dashed #475569;"
            " border-radius: 10px; color: #A1A1AA; font-size: 28px;"
        )

    # ── Lưu DB + ảnh ───────────────────────────────────────────────
    def save(self):
        name  = self.txt_name.text().strip()
        price = self.txt_price.text().strip()
        cost  = self.txt_cost.text().strip()

        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên món!")
            return
        try:
            gia_ban  = float(price)
            gia_nhap = float(cost) if cost else 0.0
            if gia_ban <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Giá bán phải là số dương!")
            return

        session = get_session()
        try:
            if self.product:
                sp = session.get(SanPham, self.product.id)
            else:
                sp = SanPham()
                session.add(sp)

            sp.ten_sp     = name
            sp.gia_ban    = gia_ban
            sp.gia_nhap   = gia_nhap
            sp.danh_muc   = self.cb_danhmuc.currentText()
            sp.trang_thai = self.cb_trangthai.currentText()

            session.commit()
            session.refresh(sp)

            # ── Xử lý ảnh sau khi có ID ────────────────────────
            if self._pending_image_path == "__DELETE__":
                # Xóa tất cả ảnh của sản phẩm này
                for ext in ("jpg", "jpeg", "png", "webp"):
                    p = os.path.join(PRODUCT_IMAGE_DIR, f"{sp.id}.{ext}")
                    if os.path.exists(p):
                        os.remove(p)
            elif self._pending_image_path:
                try:
                    save_product_image(sp.id, self._pending_image_path)
                except Exception as e:
                    QMessageBox.warning(self, "Lưu ảnh thất bại", str(e))

            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Lỗi Database", str(e))
        finally:
            session.close()


# ─────────────────────────────────────────────
# MÀN HÌNH QUẢN LÝ DANH SÁCH SẢN PHẨM
# ─────────────────────────────────────────────
class ProductManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản Lý Danh Mục Món")
        self.resize(750, 520)
        self.setStyleSheet("background-color: #1E1E2E; color: white;")

        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_add = QPushButton("➕ Thêm Món Mới")
        btn_add.setStyleSheet(
            "background-color: #2980B9; color: white; font-weight: bold;"
            " padding: 8px 16px; border-radius: 6px;"
        )
        btn_add.clicked.connect(self.add_product)

        btn_edit = QPushButton("✏️ Sửa Món")
        btn_edit.setStyleSheet(
            "background-color: #E67E22; color: white; font-weight: bold;"
            " padding: 8px 16px; border-radius: 6px;"
        )
        btn_edit.clicked.connect(self.edit_product)

        btn_delete = QPushButton("🗑️ Ngừng Bán")
        btn_delete.setStyleSheet(
            "background-color: #C0392B; color: white; font-weight: bold;"
            " padding: 8px 16px; border-radius: 6px;"
        )
        btn_delete.clicked.connect(self.toggle_status)

        btn_xoa = QPushButton("❌ Xóa Món")
        btn_xoa.setStyleSheet(
            "background-color: #7F0000; color: white; font-weight: bold;"
            " padding: 8px 16px; border-radius: 6px;"
        )
        btn_xoa.clicked.connect(self.delete_product)

        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_edit)
        toolbar.addWidget(btn_delete)
        toolbar.addWidget(btn_xoa)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Bảng danh sách — thêm cột Ảnh ở đầu
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Ảnh", "Tên Món", "Danh Mục", "Giá Vốn", "Giá Bán", "Trạng Thái"]
        )
        self.table.setColumnWidth(0, 60)   # cột ảnh
        self.table.setRowHeight(0, 55)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2D2D3F; border: none;
                border-radius: 10px; color: white; font-size: 13px;
            }
            QTableWidget::item { padding: 6px; border-bottom: 1px solid #3E3E55; }
            QTableWidget::item:selected { background-color: #2980B9; }
            QHeaderView::section {
                background-color: #1A1A24; color: #A1A1AA;
                padding: 8px; border: none; font-weight: bold;
            }
        """)
        self.table.itemDoubleClicked.connect(self.edit_product)
        layout.addWidget(self.table)

        self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        session = get_session()
        try:
            products = session.query(SanPham).order_by(SanPham.danh_muc, SanPham.ten_sp).all()
            self._product_ids = []
            for p in products:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setRowHeight(row, 55)
                self._product_ids.append(p.id)

                # Cột 0: Ảnh thumbnail
                img_lbl = QLabel()
                img_lbl.setFixedSize(50, 50)
                img_lbl.setAlignment(Qt.AlignCenter)
                img_path = get_product_image_path(p.id)
                if img_path:
                    px = QPixmap(img_path).scaled(
                        50, 50, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                    )
                    if px.width() > 50 or px.height() > 50:
                        x = (px.width() - 50) // 2
                        y = (px.height() - 50) // 2
                        px = px.copy(x, y, 50, 50)
                    img_lbl.setPixmap(px)
                    img_lbl.setStyleSheet("border-radius: 6px;")
                else:
                    img_lbl.setText("📦")
                    img_lbl.setStyleSheet("font-size: 22px; color: #64748B;")
                self.table.setCellWidget(row, 0, img_lbl)

                self.table.setItem(row, 1, QTableWidgetItem(p.ten_sp))
                self.table.setItem(row, 2, QTableWidgetItem(p.danh_muc or "—"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{int(p.gia_nhap or 0):,} đ"))

                item_gia = QTableWidgetItem(f"{int(p.gia_ban):,} đ")
                item_gia.setForeground(QColor("#F1C40F"))
                self.table.setItem(row, 4, item_gia)

                item_tt = QTableWidgetItem(p.trang_thai or "Đang bán")
                if p.trang_thai == "Đang bán":
                    item_tt.setForeground(QColor("#2ECC71"))
                elif p.trang_thai == "Hết hàng":
                    item_tt.setForeground(QColor("#E74C3C"))
                else:
                    item_tt.setForeground(QColor("#95A5A6"))
                self.table.setItem(row, 5, item_tt)
        finally:
            session.close()

    def _selected_product_id(self) -> int | None:
        rows = self.table.selectedItems()
        if not rows:
            QMessageBox.information(self, "Chưa chọn", "Vui lòng chọn một món trước!")
            return None
        row = self.table.currentRow()
        return self._product_ids[row]

    def add_product(self):
        dlg = ProductForm(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def edit_product(self):
        pid = self._selected_product_id()
        if pid is None:
            return
        session = get_session()
        try:
            sp = session.get(SanPham, pid)

            class SPProxy:
                pass
            proxy = SPProxy()
            proxy.id         = sp.id
            proxy.ten_sp     = sp.ten_sp
            proxy.gia_ban    = sp.gia_ban
            proxy.gia_nhap   = sp.gia_nhap
            proxy.danh_muc   = sp.danh_muc
            proxy.trang_thai = sp.trang_thai
        finally:
            session.close()

        dlg = ProductForm(self, product=proxy)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def toggle_status(self):
        pid = self._selected_product_id()
        if pid is None:
            return
        session = get_session()
        try:
            sp = session.get(SanPham, pid)
            if sp.trang_thai == "Đang bán":
                sp.trang_thai = "Ngừng bán"
                msg = f"'{sp.ten_sp}' đã được chuyển sang Ngừng bán."
            else:
                sp.trang_thai = "Đang bán"
                msg = f"'{sp.ten_sp}' đã được kích hoạt lại."
            session.commit()
            QMessageBox.information(self, "Cập nhật", msg)
            self.load_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            session.close()

    def delete_product(self):
        pid = self._selected_product_id()
        if pid is None:
            return

        # Lấy tên để hiển thị xác nhận
        session = get_session()
        try:
            sp = session.get(SanPham, pid)
            ten = sp.ten_sp if sp else "?"
        finally:
            session.close()

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Xác nhận xóa")
        confirm.setIcon(QMessageBox.Warning)
        confirm.setText(
            f"<b>Xóa vĩnh viễn '{ten}'?</b><br><br>"
            "<span style='color:#E74C3C;'>"
            "Thao tác này không thể hoàn tác.<br>"
            "Toàn bộ dữ liệu liên quan sẽ bị xóa."
            "</span>"
        )
        confirm.setTextFormat(Qt.RichText)
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.No)
        confirm.button(QMessageBox.Yes).setText("Xóa vĩnh viễn")
        confirm.button(QMessageBox.No).setText("Hủy")
        confirm.setStyleSheet(
            "QMessageBox { background-color: #1E1E2E; color: white; }"
            "QLabel { color: white; }"
            "QPushButton { background-color: #2D2D3F; color: white;"
            " border-radius: 6px; padding: 6px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #3E3E55; }"
        )

        if confirm.exec() != QMessageBox.Yes:
            return

        session = get_session()
        try:
            sp = session.get(SanPham, pid)
            if not sp:
                QMessageBox.warning(self, "Lỗi", "Không tìm thấy sản phẩm!"); return

            # Xóa ảnh liên quan
            for ext in ("jpg", "jpeg", "png", "webp"):
                img_path = os.path.join(PRODUCT_IMAGE_DIR, f"{pid}.{ext}")
                if os.path.exists(img_path):
                    os.remove(img_path)

            session.delete(sp)
            session.commit()
            QMessageBox.information(self, "Đã xóa", f"Đã xóa món '<b>{ten}</b>'.")
            self.load_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Lỗi Database", str(e))
        finally:
            session.close()