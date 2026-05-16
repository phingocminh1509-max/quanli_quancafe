"""
views/ingredient_manager.py
NguyenLieu đã bị loại khỏi models (thay bằng gia_nhap trực tiếp trên SanPham).
Module này hiển thị thông báo thay thế.
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class InventoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản Lý Kho")
        self.resize(450, 200)
        self.setStyleSheet("background-color: #1E1E2E; color: white;")

        layout = QVBoxLayout(self)

        lbl = QLabel(
            "📦 <b>Tính năng Quản lý Nguyên liệu đã được tích hợp vào từng Sản phẩm.</b><br><br>"
            "Giá vốn của mỗi món được quản lý trực tiếp trong<br>"
            "<b>⚙️ MENU → Sửa Món → Giá vốn (đ)</b>.<br><br>"
            "<span style='color:#A1A1AA; font-size:12px;'>"
            "Nếu cần module kho nguyên liệu riêng, vui lòng liên hệ kỹ thuật viên.</span>"
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 14px; line-height: 1.6;")
        layout.addWidget(lbl)

        btn = QPushButton("Đóng")
        btn.setMinimumHeight(40)
        btn.setStyleSheet(
            "background-color: #34495E; color: white; font-weight: bold;"
            " border-radius: 8px; font-size: 14px;"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)