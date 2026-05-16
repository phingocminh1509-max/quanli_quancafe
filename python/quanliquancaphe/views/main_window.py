import sys
import os
from PySide6.QtWidgets import (QApplication, QLineEdit, QMainWindow, QWidget, QHBoxLayout,
                               QVBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLabel, QMessageBox,
                               QGridLayout, QScrollArea, QFrame, QDialog, QListWidget,
                               QListWidgetItem, QAbstractItemView, QSizePolicy, QCheckBox)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QCursor, QFont, QColor, QPixmap
from PySide6.QtMultimedia import QSoundEffect


from utils.permissions import co_quyen, yeu_cau_quyen
from database.db_config import ghi_nhat_ky_hoat_dong as _log

# Thư mục lưu ảnh sản phẩm
PRODUCT_IMAGE_DIR = "product_images"


def get_product_image_path(product_id: int) -> str | None:
    """Trả về đường dẫn ảnh nếu tồn tại, None nếu chưa có."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = os.path.join(PRODUCT_IMAGE_DIR, f"{product_id}.{ext}")
        if os.path.exists(path):
            return path
    return None


# ================= CLASS TẠO THẺ SẢN PHẨM =================
class ProductCard(QFrame):
    def __init__(self, product, available_qty, click_callback):
        super().__init__()
        self.product = product
        self.setFixedSize(185, 105)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.click_callback = click_callback

        self.setStyleSheet("""
            ProductCard { background-color: #2D2D3F; border-radius: 12px; border: 1px solid #3E3E55; }
            ProductCard:hover { border: 2px solid #3498DB; background-color: #35354A; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── Ảnh sản phẩm hoặc icon emoji fallback ──────────────────
        img_label = QLabel()
        img_label.setFixedSize(65, 65)
        img_label.setAlignment(Qt.AlignCenter)

        img_path = get_product_image_path(product.id)
        if img_path:
            pixmap = QPixmap(img_path).scaled(
                65, 65, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            # Crop ở giữa nếu ảnh không vuông
            if pixmap.width() > 65 or pixmap.height() > 65:
                x = (pixmap.width() - 65) // 2
                y = (pixmap.height() - 65) // 2
                pixmap = pixmap.copy(x, y, 65, 65)
            img_label.setPixmap(pixmap)
            img_label.setStyleSheet(
                "background-color: #1E1E2E; border-radius: 12px; border: none;"
            )
        else:
            # Fallback icon tự động theo tên món
            name_lower = product.ten_sp.lower()
            icon = "📦"
            if any(x in name_lower for x in ["cà phê", "cafe", "bạc xỉu", "espresso", "đen"]):
                icon = "☕"
            elif any(x in name_lower for x in ["trà", "tea", "matcha", "đào"]):
                icon = "🍵"
            elif any(x in name_lower for x in ["sinh tố", "nước ép", "vải", "cam", "chanh"]):
                icon = "🍹"
            elif any(x in name_lower for x in ["bánh", "cake", "mì", "sandwich", "croissant"]):
                icon = "🍰"
            elif any(x in name_lower for x in ["cơm", "phở", "bún", "mì xào", "lẩu"]):
                icon = "🍲"
            elif any(x in name_lower for x in ["khoai tây", "hướng dương", "khô bò", "snack"]):
                icon = "🍟"
            img_label.setText(icon)
            img_label.setStyleSheet(
                "background-color: #1E1E2E; border-radius: 12px; font-size: 35px; border: none;"
            )

        layout.addWidget(img_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_lbl = QLabel(product.ten_sp)
        name_lbl.setStyleSheet(
            "color: white; font-weight: bold; font-size: 14px; border: none;"
        )
        name_lbl.setWordWrap(True)

        price_lbl = QLabel(f"{product.gia_ban:,.0f} đ")
        price_lbl.setStyleSheet(
            "color: #F1C40F; font-size: 13px; font-weight: bold; border: none;"
        )

        stock_lbl = QLabel()
        stock_lbl.setStyleSheet("border: none;")
        if available_qty == 0:
            stock_lbl.setText("HẾT HÀNG")
            stock_lbl.setStyleSheet(
                "color: #E74C3C; font-size: 11px; font-weight: bold; border: none;"
            )
            self.setEnabled(False)
            self.setStyleSheet(
                "ProductCard { background-color: #1A1A24; border-radius: 12px;"
                " border: 1px solid #E74C3C; }"
            )
        elif available_qty == -1:
            stock_lbl.setText("")
        else:
            stock_lbl.setText(f"Còn: {int(available_qty)} ly")
            stock_lbl.setStyleSheet(
                "color: #2ECC71; font-size: 11px; font-weight: bold; border: none;"
            )

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(price_lbl)
        info_layout.addWidget(stock_lbl)
        layout.addLayout(info_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.click_callback()


# ─── Helper: parse ghi chú cũ → điền lại vào các control dialog ───────────
def _restore_note(note: str, da_btns, da_sel, da_opts,
                  duong_btns, duong_sel, duong_opts,
                  tp_checks, topping_opts, txt_note):
    """Phân tích chuỗi ghi chú đã lưu và khôi phục về các widget."""
    if not note:
        return
    parts = [p.strip() for p in note.split("|")]
    free_parts = []
    for part in parts:
        matched = False
        for opt in da_opts:
            if opt in part:
                # Kích hoạt nút đá tương ứng
                da_btns[opt].click()
                matched = True
                break
        if matched:
            continue
        for opt in duong_opts:
            if opt in part:
                duong_btns[opt].click()
                matched = True
                break
        if matched:
            continue
        if part.startswith("Topping:"):
            tp_text = part[len("Topping:"):].strip()
            tp_names = [t.strip() for t in tp_text.split(",")]
            for cb in tp_checks:
                if cb.text() in tp_names:
                    cb.setChecked(True)
            matched = True
        if not matched:
            free_parts.append(part)
    txt_note.setText(" | ".join(free_parts))


# ================= CLASS CỬA SỔ CHÍNH =================
class POSWindow(QMainWindow):
    
    def show_customer_manager(self):
        if not yeu_cau_quyen(self.user.chuc_vu, "quan_ly_khach_hang", self):
            return
        _log(self.user.id, "Mở Quản lý Khách hàng", o_dau="Khách hàng")
        from views.customer_manager import CustomerManagerDialog
        CustomerManagerDialog(self).exec()

    def show_system_log(self):
        if not yeu_cau_quyen(self.user.chuc_vu, "xem_nhat_ky", self):
            return
        _log(self.user.id, "Mở Nhật ký hệ thống", o_dau="Nhật ký")
        from views.system_log import SystemLogDialog
        SystemLogDialog(self, chuc_vu=self.user.chuc_vu).exec()

    def show_admin_settings(self):
        if not yeu_cau_quyen(self.user.chuc_vu, "cai_dat_he_thong", self):
            return
        _log(self.user.id, "Mở Cài đặt hệ thống", o_dau="Hệ thống")
        from views.admin_settings import AdminSettingsDialog
        AdminSettingsDialog(self, actor_id=self.user.id).exec()
        self.apply_permissions()

    def __init__(self, current_user, ma_phien: int = None):
        super().__init__()
        self.user        = current_user
        self.ma_phien    = ma_phien   # ID PhienLamViec để check-out khi logout
        self._da_checkout = False     # True sau khi nhân viên đã hoàn tất check-out ca

        # Kiểm tra có ca được phân công hôm nay không (độc lập với ma_phien)
        self._co_ca = self._kiem_tra_co_ca()
        self.setWindowTitle("Hệ Thống Quản Lý Quán Cà Phê")
        self.resize(1200, 750)
        self.setStyleSheet("background-color: #1E1E2E; color: white;")

        # Ghi nhật ký đăng nhập vào POS
        _log(self.user.id, "Đăng nhập POS",
             f"{self.user.ten_nv} ({self.user.chuc_vu}) mở màn hình bán hàng",
             o_dau="POS")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ── NỬA TRÁI: MENU ──────────────────────────────────────────
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #1A1A24; border-radius: 15px;")
        left_layout = QVBoxLayout(left_panel)

        header_layout = QHBoxLayout()
        title_lbl = QLabel("📋 DANH MỤC MÓN")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3498DB;")
        header_layout.addWidget(title_lbl)

        # Nút CHECK-OUT CA (kết thúc ca làm, tính công)
        self.btn_ca_checkout = QPushButton("⏱️ Check-out Ca")
        self.btn_ca_checkout.setStyleSheet(
            "background-color: #E67E22; color: white; font-weight: bold;"
            " padding: 8px; border-radius: 6px;"
        )
        self.btn_ca_checkout.setToolTip("Kết thúc ca làm việc — tính giờ & chốt số liệu")
        self.btn_ca_checkout.clicked.connect(self.handle_ca_checkout)
        header_layout.addWidget(self.btn_ca_checkout, alignment=Qt.AlignRight)

        # Nút ĐĂNG XUẤT (thoát phiên ứng dụng)
        self.btn_logout = QPushButton(f"🚪 Đăng xuất ({self.user.ten_dang_nhap})")
        self.btn_logout.setStyleSheet(
            "background-color: #C0392B; color: white; font-weight: bold;"
            " padding: 8px; border-radius: 6px;"
        )
        self.btn_logout.clicked.connect(self.logout)
        header_layout.addWidget(self.btn_logout, alignment=Qt.AlignRight)
        left_layout.addLayout(header_layout)

        # Thanh tìm kiếm
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Nhập tên món để tìm kiếm nhanh...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D3F; border: 1px solid #3E3E55;
                border-radius: 20px; padding: 10px 15px; color: white; font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #3498DB; background-color: #35354A; }
        """)
        self.search_bar.textChanged.connect(self.filter_products)
        left_layout.addWidget(self.search_bar)

        # ── Thanh lọc phân loại nằm ngang ───────────────────────
        self._active_category = "Tất cả"   # danh mục đang chọn

        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(46)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._cat_bar_widget = QWidget()
        self._cat_bar_widget.setStyleSheet("background: transparent;")
        self._cat_bar_layout = QHBoxLayout(self._cat_bar_widget)
        self._cat_bar_layout.setContentsMargins(0, 0, 0, 0)
        self._cat_bar_layout.setSpacing(8)
        self._cat_bar_layout.setAlignment(Qt.AlignLeft)

        cat_scroll.setWidget(self._cat_bar_widget)
        left_layout.addWidget(cat_scroll)
        self._cat_scroll = cat_scroll

        # Grid sản phẩm
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop)

        self.refresh_product_grid()
        scroll_area.setWidget(self.grid_widget)
        left_layout.addWidget(scroll_area)

        # Nút chức năng dưới cùng
        func_layout = QHBoxLayout()
        func_layout.setSpacing(8)

        self.history_btn = QPushButton("📜 LỊCH SỬ")
        self.report_btn  = QPushButton("📊 BÁO CÁO")
        self.menu_btn    = QPushButton("⚙️ MENU")
        self.func_btn    = QPushButton("☰ CHỨC NĂNG ▾")   # popup menu

        for btn in [self.history_btn, self.report_btn, self.menu_btn, self.func_btn]:
            btn.setMinimumHeight(45)
            btn.setStyleSheet(
                "background-color: #34495E; color: white; font-weight: bold; border-radius: 8px;"
            )
            func_layout.addWidget(btn)

        self.func_btn.setStyleSheet(
            "background-color: #2C3E50; color: white; font-weight: bold; border-radius: 8px;"
        )

        self.history_btn.clicked.connect(self.show_history_dialog)
        self.report_btn.clicked.connect(self.show_report)
        self.menu_btn.clicked.connect(self.show_product_manager)
        self.func_btn.clicked.connect(self._show_func_menu)

        left_layout.addLayout(func_layout)
        main_layout.addWidget(left_panel, stretch=6)

        # ── NỬA PHẢI: HÓA ĐƠN ──────────────────────────────────────
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #1A1A24; border-radius: 15px;")
        self.right_layout = QVBoxLayout(right_panel)

        inv_title = QLabel("🧾 HÓA ĐƠN")
        inv_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2ECC71;")
        inv_title.setAlignment(Qt.AlignCenter)
        self.right_layout.addWidget(inv_title)

        self.order_table = QTableWidget(0, 4)
        self.order_table.setHorizontalHeaderLabels(["Tên Món", "Đơn Giá", "T.Tiền", "SL"])
        self.order_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.order_table.setColumnWidth(1, 80)   # Đơn giá
        self.order_table.setColumnWidth(2, 80)   # Thành tiền
        self.order_table.setColumnWidth(3, 100)  # SL + -/+
        self.order_table.setStyleSheet("""
            QTableWidget {
                background-color: #2D2D3F; border: none; border-radius: 10px;
                gridline-color: #3E3E55; color: white; font-size: 13px;
            }
            QTableWidget::item { padding: 5px; border-bottom: 1px solid #3E3E55; }
            QHeaderView::section {
                background-color: #2C3E50; color: #A1A1AA; padding: 8px;
                border: none; font-weight: bold; font-size: 13px;
            }
        """)
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.order_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Double-click để thêm/sửa ghi chú inline
        self.order_table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self.right_layout.addWidget(self.order_table)

        # Nút áp dụng khuyến mãi
        self.btn_apply_km = QPushButton("🎉 Áp dụng Khuyến Mãi")
        self.btn_apply_km.setMinimumHeight(36)
        self.btn_apply_km.setStyleSheet(
            "background-color: #E67E22; color: white; font-weight: bold;"
            " border-radius: 8px; font-size: 13px;"
        )
        self.btn_apply_km.clicked.connect(self._apply_khuyen_mai)
        self.right_layout.addWidget(self.btn_apply_km)

        self.total_label = QLabel("Tổng cộng: 0 Đ")
        self.total_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #E74C3C; background-color: transparent;"
        )
        self.right_layout.addWidget(self.total_label)

        self.checkout_btn = QPushButton("XUẤT HÓA ĐƠN")
        self.checkout_btn.setMinimumHeight(60)
        self.checkout_btn.setStyleSheet(
            "background-color: #27AE60; color: white; font-size: 18px;"
            " font-weight: bold; border-radius: 10px;"
        )
        self.checkout_btn.clicked.connect(self.handle_checkout)
        self.right_layout.addWidget(self.checkout_btn)

        main_layout.addWidget(right_panel, stretch=4)

        # Biến lưu khuyến mãi đang áp dụng
        self._applied_km = None   # dict: {id, ten, giam}
        self._km_discount = 0     # số tiền đã giảm thực tế
        

        # ── ÂM THANH ────────────────────────────────────────────────
        self.sound_beep = QSoundEffect()
        if os.path.exists("sounds/beep.wav"):
            self.sound_beep.setSource(QUrl.fromLocalFile("sounds/beep.wav"))
        self.sound_cash = QSoundEffect()
        if os.path.exists("sounds/cash.wav"):
            self.sound_cash.setSource(QUrl.fromLocalFile("sounds/cash.wav"))

        self._history_dialog  = None
        self._cached_products = []   # cache SanPham cho _draw_product_grid
        self.apply_permissions()


    # ================================================================
    # CÁC HÀM XỬ LÝ
    # ================================================================

    
    def apply_permissions(self):
        role = getattr(self.user, 'chuc_vu', 'Phục vụ') or 'Phục vụ'

        # Nút luôn hiện với mọi role
        self.history_btn.setVisible(co_quyen(role, "xem_lich_su"))
        self.report_btn.setVisible(co_quyen(role, "xem_bao_cao"))
        self.menu_btn.setVisible(co_quyen(role, "quan_ly_menu"))

        # Nút Check-out Ca: chỉ hiện khi có ca hôm nay và không phải Admin
        self.btn_ca_checkout.setVisible(role != "Admin" and self._co_ca)

        # Nút CHỨC NĂNG: hiện nếu có ít nhất 1 quyền trong menu
        func_quyen = [
            "quan_ly_khach_hang", "xem_nhat_ky", "quan_ly_ca_lam",
            "quan_ly_khuyen_mai", "quan_ly_nhan_su", "cai_dat_he_thong",
            "quan_ly_phan_loai",
        ]
        self.func_btn.setVisible(any(co_quyen(role, q) for q in func_quyen))

        self.setWindowTitle(f"☕ POS Cafe — {role}: {self.user.ten_nv}")

    def _kiem_tra_co_ca(self) -> bool:
        """Trả True nếu nhân viên có ca được phân công hôm nay."""
        try:
            from datetime import date
            from database.db_config import get_session
            from database.models import PhanCongCaLam
            s = get_session()
            try:
                count = (s.query(PhanCongCaLam)
                         .filter_by(ma_nv=self.user.id, ngay_lam=date.today())
                         .count())
                return count > 0
            finally:
                s.close()
        except Exception:
            return False  # lỗi → ẩn nút cho an toàn

    def show_change_password(self):
        """Nhân viên tự đổi mật khẩu của chính mình."""
        from views.admin_settings import ChangePasswordDialog
        dlg = ChangePasswordDialog(
            emp_id=self.user.id,
            actor_id=self.user.id,   # tự đổi → bắt buộc nhập MK cũ
            parent=self
        )
        dlg.exec()

    def _show_func_menu(self):
        """Hiện popup menu CHỨC NĂNG theo quyền của user."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        role = getattr(self.user, 'chuc_vu', 'Phục vụ') or 'Phục vụ'

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D3F; color: white;
                border: 1px solid #3E3E55; border-radius: 8px;
                padding: 6px 0;
            }
            QMenu::item { padding: 10px 24px; font-size: 13px; font-weight: bold; }
            QMenu::item:selected { background-color: #3498DB; border-radius: 4px; }
            QMenu::separator { height: 1px; background: #3E3E55; margin: 4px 12px; }
        """)

        def _add(icon, label, slot, quyen):
            if co_quyen(role, quyen):
                act = QAction(f"{icon}  {label}", self)
                act.triggered.connect(slot)
                menu.addAction(act)

        _add("👥", "Quản lý Khách hàng",  self.show_customer_manager,  "quan_ly_khach_hang")
        _add("🎉", "Khuyến mãi",           self.show_khuyen_mai,         "quan_ly_khuyen_mai")
        _add("🏷️", "Quản lý Phân Loại",   self.show_category_manager,   "quan_ly_phan_loai")

        if co_quyen(role, "quan_ly_ca_lam") or co_quyen(role, "xem_nhat_ky") or co_quyen(role, "quan_ly_nhan_su") or co_quyen(role, "quan_ly_phan_loai"):
            menu.addSeparator()

        _add("📅", "Phân công Ca làm",     self.show_shift_manager,     "quan_ly_ca_lam")
        _add("✅", "Điểm danh",             self.show_attendance,         "quan_ly_ca_lam")
        _add("📋", "Nhật ký hệ thống",     self.show_system_log,         "xem_nhat_ky")

        if co_quyen(role, "cai_dat_he_thong") or co_quyen(role, "quan_ly_nhan_su"):
            menu.addSeparator()

        _add("👤", "Quản lý Nhân sự",      self.show_admin_settings,     "quan_ly_nhan_su")
        _add("🛡️", "Cài đặt Hệ thống",    self.show_admin_settings,     "cai_dat_he_thong")

        # Đổi mật khẩu — mọi nhân viên đều có quyền tự đổi MK của mình
        menu.addSeparator()
        act_pw = QAction("🔑  Đổi Mật Khẩu", self)
        act_pw.triggered.connect(self.show_change_password)
        menu.addAction(act_pw)

        if not menu.actions():
            return

        # Hiện menu ngay dưới nút func_btn
        pos = self.func_btn.mapToGlobal(self.func_btn.rect().bottomLeft())
        menu.exec(pos)


    def filter_products(self, text):
        search_text = text.lower().strip()
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if not hasattr(widget, 'product'):
                    widget.setVisible(True)
                    continue
                visible = (not search_text) or (search_text in widget.product.ten_sp.lower())
                widget.setVisible(visible)

    def _rebuild_category_bar(self, categories: list):
        """Xóa và vẽ lại thanh nút phân loại nằm ngang."""
        while self._cat_bar_layout.count():
            item = self._cat_bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_cats = ["Tất cả"] + categories

        for cat in all_cats:
            btn = QPushButton(cat)
            btn.setFixedHeight(34)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            is_active = (cat == self._active_category)
            self._style_cat_btn(btn, is_active)
            btn.clicked.connect(lambda checked=False, c=cat: self._select_category(c))
            self._cat_bar_layout.addWidget(btn)

        self._cat_bar_layout.addStretch()

    def _style_cat_btn(self, btn: QPushButton, active: bool):
        if active:
            btn.setStyleSheet(
                "QPushButton {"
                " background-color: #3498DB; color: white; font-weight: bold;"
                " border-radius: 17px; font-size: 12px; padding: 0 16px;"
                " border: none;"
                "}"
            )
        else:
            btn.setStyleSheet(
                "QPushButton {"
                " background-color: #2D2D3F; color: #A1A1AA; font-weight: bold;"
                " border-radius: 17px; font-size: 12px; padding: 0 16px;"
                " border: 1px solid #3E3E55;"
                "}"
                "QPushButton:hover {"
                " background-color: #35354A; color: white; border: 1px solid #3498DB;"
                "}"
            )

    def _select_category(self, cat: str):
        """Chọn tab phân loại -> cập nhật style nút + vẽ lại grid."""
        self._active_category = cat
        for i in range(self._cat_bar_layout.count()):
            item = self._cat_bar_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QPushButton):
                b = item.widget()
                self._style_cat_btn(b, b.text() == cat)
        self._draw_product_grid(self._cached_products)

    def refresh_product_grid(self):
        """Xóa và vẽ lại toàn bộ grid sản phẩm từ DB."""
        from database.db_config import get_session
        from database.models import SanPham
        session = get_session()
        try:
            self._cached_products = (
                session.query(SanPham)
                .filter(SanPham.trang_thai == 'Đang bán')
                .order_by(SanPham.danh_muc, SanPham.ten_sp)
                .all()
            )
        finally:
            session.close()

        seen = []
        for sp in self._cached_products:
            cat = (sp.danh_muc or "Khác").strip()
            if cat not in seen:
                seen.append(cat)

        self._rebuild_category_bar(seen)
        self._draw_product_grid(self._cached_products)

    def _draw_product_grid(self, products):
        """Vẽ lại grid theo _active_category, có header separator mỗi nhóm."""
        from collections import OrderedDict
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._active_category == "Tất cả":
            filtered = products
        else:
            filtered = [p for p in products
                        if (p.danh_muc or "Khác").strip() == self._active_category]

        groups: OrderedDict = OrderedDict()
        for sp in filtered:
            cat = (sp.danh_muc or "Khác").strip()
            groups.setdefault(cat, []).append(sp)

        grid_row = 0
        COLS = 3

        for cat_name, sp_list in groups.items():
            if self._active_category == "Tất cả":
                header_widget = QWidget()
                header_widget.setStyleSheet("background: transparent;")
                h_layout = QHBoxLayout(header_widget)
                h_layout.setContentsMargins(4, 8, 4, 4)
                h_layout.setSpacing(8)

                lbl = QLabel(f"  {cat_name}")
                lbl.setStyleSheet(
                    "color: #3498DB; font-size: 13px; font-weight: bold;"
                    " background: transparent; border: none;"
                )
                h_layout.addWidget(lbl)

                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setStyleSheet("color: #3E3E55; background-color: #3E3E55; border: none;")
                line.setFixedHeight(1)
                h_layout.addWidget(line, stretch=1)

                self.grid_layout.addWidget(header_widget, grid_row, 0, 1, COLS)
                grid_row += 1

            col = 0
            for product in sp_list:
                p_data = {
                    'id':    product.id,
                    'name':  product.ten_sp,
                    'price': product.gia_ban,
                }
                card = ProductCard(
                    product, -1,
                    lambda p=p_data: self.add_to_order(p)
                )
                self.grid_layout.addWidget(card, grid_row, col)
                col += 1
                if col >= COLS:
                    col = 0
                    grid_row += 1

            if col != 0:
                grid_row += 1

    def highlight_total(self):
        original_style = self.total_label.styleSheet()
        highlight = original_style + " background-color: rgba(39,174,96,0.4); border-radius: 8px;"
        self.total_label.setStyleSheet(highlight)
        QTimer.singleShot(200, lambda: self.total_label.setStyleSheet(original_style))

    def update_grand_total(self):
        grand_total = 0
        for row in range(self.order_table.rowCount()):
            item = self.order_table.item(row, 2)
            # Bỏ qua row ghi chú (col 2 trống hoặc item là None)
            if item and item.text().strip() and item.data(Qt.UserRole) != "note_row":
                try:
                    grand_total += float(item.text().replace(",", ""))
                except ValueError:
                    pass
        tax = grand_total * 0.10
        subtotal = grand_total + tax

        # Tính giảm KM
        self._km_discount = 0
        km_line = ""
        if self._applied_km:
            km = self._applied_km
            if km["kieu"] == "PhanTram":
                giam = subtotal * km["gia_tri"] / 100
                if km.get("tran") and giam > km["tran"]:
                    giam = km["tran"]
                self._km_discount = giam
            elif km["kieu"] == "TienMat":
                self._km_discount = min(km["gia_tri"], subtotal)
            km_line = (
                f"<span style='font-size:13px; color:#E67E22;'>"
                f"🎉 KM [{km['ten']}]: -{int(self._km_discount):,.0f} đ"
                f"</span><br>"
            )

        total_to_pay = max(0, subtotal - self._km_discount)
        self.total_label.setText(
            f"<div style='text-align:right; background-color:transparent;'>"
            f"<span style='font-size:14px; color:#BDC3C7;'>Tổng tiền món: {int(grand_total):,.0f} đ</span><br>"
            f"<span style='font-size:14px; color:#E74C3C;'>Thuế VAT (10%): +{int(tax):,.0f} đ</span><br>"
            f"{km_line}"
            f"<b style='font-size:24px; color:#27AE60;'>CẦN THANH TOÁN: {int(total_to_pay):,.0f} Đ</b>"
            f"</div>"
        )

    # ----------------------------------------------------------------
    # FIX: Lưu dữ liệu giá vào UserRole thay vì dùng closure để tránh
    #      lỗi row index bị lệch sau khi xóa dòng.
    # ----------------------------------------------------------------
    def _rebuild_action_buttons(self):
        """Vẽ lại toàn bộ widget SL+-  theo row index hiện tại. Bỏ qua row ghi chú."""
        for row in range(self.order_table.rowCount()):
            # Col 3 là widget SL+-; dùng col 1 (đơn giá) để tính price
            don_gia_item   = self.order_table.item(row, 1)
            thanh_tien_item = self.order_table.item(row, 2)
            # Row ghi chú: col 1 có UserRole "note_row"
            col1 = self.order_table.item(row, 1)
            if col1 and col1.data(Qt.UserRole) == "note_row":
                self.order_table.setCellWidget(row, 3, None)
                continue
            if not don_gia_item or not thanh_tien_item:
                continue
            try:
                price = float(don_gia_item.text().replace(",", ""))
                total = float(thanh_tien_item.text().replace(",", ""))
                qty   = round(total / price) if price else 1
            except (ValueError, ZeroDivisionError):
                continue
            self.order_table.setCellWidget(row, 3, self._make_btn_widget(row, price))

    def _make_btn_widget(self, row: int, price: float) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(2, 2, 2, 2)
        h.setSpacing(2)

        btn_minus = QPushButton("−")
        btn_plus  = QPushButton("+")
        style = (
            "font-weight: bold; min-width: 24px; max-width: 24px;"
            " min-height: 24px; max-height: 24px;"
            " background-color: #34495E; color: white; border-radius: 4px;"
        )
        btn_minus.setStyleSheet(style)
        btn_plus.setStyleSheet(style)

        # Label số lượng ở giữa
        thanh_tien_item = self.order_table.item(row, 2)
        don_gia_item    = self.order_table.item(row, 1)
        try:
            total = float(thanh_tien_item.text().replace(",", "")) if thanh_tien_item else 0
            qty   = round(total / price) if price else 1
        except (ValueError, ZeroDivisionError):
            qty = 1
        qty_lbl = QLabel(str(qty))
        qty_lbl.setAlignment(Qt.AlignCenter)
        qty_lbl.setMinimumWidth(24)
        qty_lbl.setStyleSheet(
            "color: white; font-weight: bold; font-size: 13px; background: transparent;"
        )
        qty_lbl.setObjectName(f"qty_lbl_{row}")

        btn_minus.clicked.connect(lambda checked=False, r=row, p=price: self._change_qty(r, -1, p))
        btn_plus.clicked.connect(lambda checked=False, r=row, p=price: self._change_qty(r, 1, p))

        h.addWidget(btn_minus)
        h.addWidget(qty_lbl)
        h.addWidget(btn_plus)
        return container

    def _change_qty(self, row: int, delta: int, price: float):
        """Thay đổi số lượng. Nếu về 0 thì xóa cả dòng món lẫn dòng ghi chú liền dưới."""
        if row >= self.order_table.rowCount():
            return
        thanh_tien_item = self.order_table.item(row, 2)
        if not thanh_tien_item:
            return
        try:
            total   = float(thanh_tien_item.text().replace(",", ""))
            cur_qty = round(total / price) if price else 1
        except (ValueError, ZeroDivisionError):
            return
        new_qty = cur_qty + delta

        name_item = self.order_table.item(row, 0)
        mon_ten   = name_item.text() if name_item else "?"

        if new_qty <= 0:
            _log(self.user.id, "Hủy món khỏi order",
                 f"Xóa '{mon_ten}' ({int(price):,}đ) khỏi hóa đơn",
                 o_dau="POS - Order")
            note_row = row + 1
            if (note_row < self.order_table.rowCount() and
                    self.order_table.item(note_row, 1) and
                    self.order_table.item(note_row, 1).data(Qt.UserRole) == "note_row"):
                self.order_table.removeRow(note_row)
            self.order_table.removeRow(row)
        else:
            # Cập nhật thành tiền (đơn giá giữ nguyên ở col 1)
            self.order_table.setItem(row, 2, QTableWidgetItem(f"{int(new_qty * price):,}"))
        self._rebuild_action_buttons()
        self.update_grand_total()
        self.sound_beep.play()
        self.highlight_total()

    # Giữ tên cũ để các nơi khác vẫn gọi được (compat)
    def change_qty(self, row, delta, price):
        self._change_qty(row, delta, price)

    def add_to_order(self, product):
        """Thêm món vào bảng order, hoặc tăng SL nếu đã có."""
        for row in range(self.order_table.rowCount()):
            item = self.order_table.item(row, 0)
            if item and item.text() == product['name']:
                self._change_qty(row, 1, product['price'])
                _log(self.user.id, "Tăng số lượng món",
                     f"Tăng SL '{product['name']}' ({int(product['price']):,}đ)",
                     o_dau="POS - Order")
                return

        from PySide6.QtGui import QColor
        row_idx = self.order_table.rowCount()
        self.order_table.insertRow(row_idx)

        name_item = QTableWidgetItem(product['name'])
        name_item.setData(Qt.UserRole, product['price'])
        self.order_table.setItem(row_idx, 0, name_item)

        # Col 1: Đơn giá
        don_gia_item = QTableWidgetItem(f"{int(product['price']):,}")
        don_gia_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.order_table.setItem(row_idx, 1, don_gia_item)

        # Col 2: Thành tiền (= đơn giá × 1)
        thanh_tien_item = QTableWidgetItem(f"{int(product['price']):,}")
        thanh_tien_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.order_table.setItem(row_idx, 2, thanh_tien_item)

        # Col 3: Widget SL + -/+
        self._rebuild_action_buttons()
        self.update_grand_total()
        self.sound_beep.play()
        self.highlight_total()
        _log(self.user.id, "Thêm món vào order",
             f"Thêm '{product['name']}' — {int(product['price']):,}đ",
             o_dau="POS - Order")

    def _find_product_row(self, row: int) -> int:
        """Trả về row chứa món (không phải row ghi chú). -1 nếu không hợp lệ."""
        if row < 0 or row >= self.order_table.rowCount():
            return -1
        item = self.order_table.item(row, 1)
        if item and item.data(Qt.UserRole) == "note_row":
            return -1   # đây là row ghi chú
        if item and item.text().strip():
            return row  # đây là row món
        return -1

    def _on_row_double_clicked(self, row: int, col: int):
        """Double-click vào cột SL → sửa số lượng trực tiếp trên ô.
        Double-click các cột khác → mở dialog topping/đá/đường."""
        if col == 3:
            self._edit_qty_inline(row)
            return

        # Nếu click vào row ghi chú → mở lại dialog của món cha
        item_check = self.order_table.item(row, 1)
        if item_check and item_check.data(Qt.UserRole) == "note_row":
            parent_col2 = self.order_table.item(row, 2)
            product_row = parent_col2.data(Qt.UserRole) if parent_col2 else -1
            if product_row >= 0:
                self._open_customize_dialog(product_row)
            return

        product_row = self._find_product_row(row)
        if product_row < 0:
            return
        self._open_customize_dialog(product_row)

    def _edit_qty_inline(self, row: int):
        """Thay widget SL bằng QLineEdit để nhập trực tiếp, Enter/blur để xác nhận."""
        don_gia_item    = self.order_table.item(row, 1)
        thanh_tien_item = self.order_table.item(row, 2)
        name_item       = self.order_table.item(row, 0)
        if not don_gia_item or not thanh_tien_item or not name_item:
            return
        if don_gia_item.data(Qt.UserRole) == "note_row":
            return
        try:
            price   = float(don_gia_item.text().replace(",", ""))
            total   = float(thanh_tien_item.text().replace(",", ""))
            cur_qty = round(total / price) if price else 1
        except (ValueError, ZeroDivisionError):
            return

        # Tạo QLineEdit thay thế widget -/+ tạm thời
        editor = QLineEdit(str(cur_qty))
        editor.setAlignment(Qt.AlignCenter)
        editor.setStyleSheet(
            "background:#3498DB; color:white; font-weight:bold; font-size:14px;"
            " border:2px solid #5DADE2; border-radius:4px; padding:2px;"
        )
        editor.selectAll()
        self.order_table.setCellWidget(row, 3, editor)
        editor.setFocus()

        def _confirm():
            txt = editor.text().strip()
            try:
                new_qty = int(txt)
            except ValueError:
                # Nhập không hợp lệ → khôi phục widget cũ
                self._rebuild_action_buttons()
                return
            if new_qty == cur_qty:
                self._rebuild_action_buttons()
                return
            if new_qty <= 0:
                self._change_qty(row, -cur_qty, price)
            else:
                self._change_qty(row, new_qty - cur_qty, price)

        editor.returnPressed.connect(_confirm)
        editor.editingFinished.connect(_confirm)

    def _open_customize_dialog(self, product_row: int):
        """Dialog tùy chỉnh món: đá, đường, topping, ghi chú tự do."""
        name_item = self.order_table.item(product_row, 0)
        if not name_item:
            return
        mon_name = name_item.text()

        # Lấy ghi chú hiện tại (nếu đã có)
        current_note = self._get_note_for_product_row(product_row)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"⚙️  Tùy chỉnh: {mon_name}")
        dlg.setFixedWidth(440)
        dlg.setStyleSheet("""
            QDialog { background-color: #1E1E2E; color: white; }
            QLabel  { color: white; font-size: 13px; }
            QLineEdit {
                background: #2D2D3F; border: 1px solid #3E3E55;
                border-radius: 6px; padding: 7px 10px;
                color: white; font-size: 13px;
            }
            QLineEdit:focus { border-color: #3498DB; }
            QPushButton {
                border-radius: 6px; font-size: 12px;
                font-weight: bold; padding: 6px 10px;
            }
        """)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        # Tiêu đề món
        lbl_title = QLabel(f"🍹  <b>{mon_name}</b>")
        lbl_title.setStyleSheet("font-size:15px; color:#3498DB;")
        root.addWidget(lbl_title)

        # ── helper: tạo group nút bấm toggle ──────────────────────
        def _make_toggle_group(options: list[str], default: str, colors: dict) -> tuple[QHBoxLayout, dict]:
            """Trả về layout + dict {text: btn} để lấy giá trị đang chọn."""
            layout = QHBoxLayout()
            layout.setSpacing(6)
            btns: dict[str, QPushButton] = {}
            selected = [default]

            def _select(txt):
                selected[0] = txt
                for t, b in btns.items():
                    active = (t == txt)
                    bg = colors.get(t, "#3498DB") if active else "#2D2D3F"
                    border = colors.get(t, "#3498DB") if active else "#3E3E55"
                    b.setStyleSheet(
                        f"background:{bg}; color:white; border:2px solid {border};"
                        f" border-radius:6px; font-size:12px; font-weight:bold; padding:6px 10px;"
                    )

            for opt in options:
                b = QPushButton(opt)
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _, t=opt: _select(t))
                btns[opt] = b
                layout.addWidget(b)

            _select(default)  # khởi tạo style
            return layout, btns, selected

        # ── Mức đá ────────────────────────────────────────────────
        da_opts    = ["❄️ Bình thường", "🧊 Nhiều đá", "🔹 Ít đá", "🚫 Không đá"]
        da_colors  = {
            "❄️ Bình thường": "#2980B9",
            "🧊 Nhiều đá":    "#1ABC9C",
            "🔹 Ít đá":       "#16A085",
            "🚫 Không đá":    "#7F8C8D",
        }
        root.addWidget(QLabel("🧊  Mức đá:"))
        da_layout, da_btns, da_sel = _make_toggle_group(da_opts, da_opts[0], da_colors)
        root.addLayout(da_layout)

        # ── Mức đường ─────────────────────────────────────────────
        duong_opts   = ["🍬 Bình thường", "🍭 Nhiều đường", "🔸 Ít đường", "🚫 Không đường"]
        duong_colors = {
            "🍬 Bình thường":  "#E67E22",
            "🍭 Nhiều đường":  "#E74C3C",
            "🔸 Ít đường":     "#F39C12",
            "🚫 Không đường":  "#7F8C8D",
        }
        root.addWidget(QLabel("🍬  Mức đường:"))
        duong_layout, duong_btns, duong_sel = _make_toggle_group(duong_opts, duong_opts[0], duong_colors)
        root.addLayout(duong_layout)

        # ── Topping ───────────────────────────────────────────────
        root.addWidget(QLabel("🧆  Topping thêm:"))
        topping_opts = [
            ("🧋 Trân châu",    False),
            ("🍮 Pudding",      False),
            ("🥛 Kem tươi",     False),
            ("🌱 Thạch dừa",    False),
            ("🫙 Sữa đặc thêm", False),
        ]
        topping_frame = QWidget()
        topping_frame.setStyleSheet("background:transparent;")
        tp_grid = QGridLayout(topping_frame)
        tp_grid.setContentsMargins(0, 0, 0, 0)
        tp_grid.setSpacing(6)
        tp_checks: list[QCheckBox] = []
        for i, (tp_name, _) in enumerate(topping_opts):
            cb = QCheckBox(tp_name)
            cb.setStyleSheet("""
                QCheckBox { color:white; font-size:12px; spacing:6px; }
                QCheckBox::indicator { width:16px; height:16px; border-radius:4px;
                    border:2px solid #3E3E55; background:#1E1E2E; }
                QCheckBox::indicator:checked { background:#27AE60; border-color:#27AE60; }
                QCheckBox::indicator:hover   { border-color:#3498DB; }
            """)
            tp_grid.addWidget(cb, i // 3, i % 3)
            tp_checks.append(cb)
        root.addWidget(topping_frame)

        # ── Ghi chú tự do ─────────────────────────────────────────
        root.addWidget(QLabel("✏️  Ghi chú thêm:"))
        txt_note = QLineEdit()
        txt_note.setPlaceholderText("VD: không sữa, thêm muối, đóng gói riêng...")

        # Parse lại ghi chú cũ để điền sẵn vào các control
        _restore_note(current_note, da_btns, da_sel, da_opts,
                      duong_btns, duong_sel, duong_opts,
                      tp_checks, topping_opts, txt_note)

        root.addWidget(txt_note)

        # ── Nút OK / Hủy ──────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_ok  = QPushButton("✅  Xác nhận")
        btn_ok.setMinimumHeight(40)
        btn_ok.setStyleSheet(
            "background:#27AE60;color:white;font-weight:bold;"
            "border-radius:8px;font-size:14px;"
        )
        btn_clear = QPushButton("🗑  Xóa tùy chỉnh")
        btn_clear.setMinimumHeight(40)
        btn_clear.setStyleSheet(
            "background:#7F8C8D;color:white;font-weight:bold;"
            "border-radius:8px;font-size:13px;"
        )
        btn_cancel = QPushButton("✖  Đóng")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setStyleSheet(
            "background:#C0392B;color:white;font-weight:bold;"
            "border-radius:8px;font-size:13px;"
        )
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_clear)
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

        def _build_note_text() -> str:
            parts = []
            da_val = da_sel[0]
            if da_val != da_opts[0]:   # khác bình thường mới ghi
                parts.append(da_val)
            duong_val = duong_sel[0]
            if duong_val != duong_opts[0]:
                parts.append(duong_val)
            toppings = [cb.text() for cb in tp_checks if cb.isChecked()]
            if toppings:
                parts.append("Topping: " + ", ".join(toppings))
            free = txt_note.text().strip()
            if free:
                parts.append(free)
            return " | ".join(parts)

        def _confirm():
            note_text = _build_note_text()
            self._set_note_for_product_row(product_row, note_text)
            dlg.accept()

        def _clear():
            self._set_note_for_product_row(product_row, "")
            dlg.accept()

        btn_ok.clicked.connect(_confirm)
        btn_clear.clicked.connect(_clear)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec()

    def _set_note_for_product_row(self, product_row: int, note_text: str):
        """Ghi / cập nhật / xóa dòng ghi chú ngay dưới dòng món."""
        note_row = product_row + 1
        has_note_row = (
            note_row < self.order_table.rowCount()
            and self.order_table.item(note_row, 1) is not None
            and self.order_table.item(note_row, 1).data(Qt.UserRole) == "note_row"
        )

        if not note_text:
            # Xóa dòng ghi chú nếu có
            if has_note_row:
                self.order_table.removeRow(note_row)
                self._rebuild_action_buttons()
            return

        if not has_note_row:
            # Chèn dòng mới
            self.order_table.insertRow(note_row)
            marker = QTableWidgetItem("")
            marker.setData(Qt.UserRole, "note_row")
            marker.setFlags(Qt.NoItemFlags)
            self.order_table.setItem(note_row, 1, marker)
            parent_item = QTableWidgetItem("")
            parent_item.setData(Qt.UserRole, product_row)
            parent_item.setFlags(Qt.NoItemFlags)
            self.order_table.setItem(note_row, 2, parent_item)
            self.order_table.setRowHeight(note_row, 28)

        # Đặt widget hiển thị (read-only label style)
        note_lbl = QLabel(f"  📝 {note_text}")
        note_lbl.setStyleSheet(
            "background:#1A1A24; color:#F1C40F;"
            " font-size:12px; font-style:italic; padding:4px 8px;"
        )
        note_lbl.setWordWrap(True)
        self.order_table.setCellWidget(note_row, 0, note_lbl)
        self._rebuild_action_buttons()

    def _get_note_for_product_row(self, product_row: int) -> str:
        """Lấy nội dung ghi chú của dòng món (từ row ghi chú ngay dưới)."""
        note_row = product_row + 1
        if note_row >= self.order_table.rowCount():
            return ""
        marker = self.order_table.item(note_row, 1)
        if not marker or marker.data(Qt.UserRole) != "note_row":
            return ""
        widget = self.order_table.cellWidget(note_row, 0)
        if widget and isinstance(widget, QLabel):
            # Bỏ prefix "  📝 "
            t = widget.text().strip()
            return t[2:].strip() if t.startswith("📝") else t
        if widget and hasattr(widget, 'text'):
            return widget.text().strip()
        item = self.order_table.item(note_row, 0)
        return item.text().strip() if item else ""

    # ── Áp dụng khuyến mãi ─────────────────────────────────────
    def _apply_khuyen_mai(self):
        """Mở dialog chọn KM đang chạy, tính giảm và cập nhật tổng."""
        if self.order_table.rowCount() == 0:
            QMessageBox.warning(self, "Hóa đơn trống", "Hãy thêm món trước khi áp dụng KM!"); return

        from database.db_config import get_session
        from database.models import KhuyenMai, SanPham

        # Tính tổng đơn hiện tại (trước VAT)
        grand_total = 0
        for row in range(self.order_table.rowCount()):
            item = self.order_table.item(row, 2)
            if item and item.text().strip() and item.data(Qt.UserRole) != "note_row":
                try:
                    grand_total += float(item.text().replace(",", ""))
                except ValueError:
                    pass
        subtotal = grand_total * 1.10  # có VAT

        session = get_session()
        try:
            kms = session.query(KhuyenMai).filter_by(trang_thai="Đang chạy").all()
            # Lọc KM thỏa điều kiện đơn tối thiểu
            valid_kms = []
            from datetime import date
            today = date.today()
            for km in kms:
                if km.ngay_bat_dau and km.ngay_bat_dau > today: continue
                if km.ngay_ket_thuc and km.ngay_ket_thuc < today: continue
                if km.dk_tong_tien_tu and subtotal < km.dk_tong_tien_tu: continue
                valid_kms.append(km)
        finally:
            session.close()

        if not valid_kms:
            QMessageBox.information(self, "Không có KM", "Không có khuyến mãi nào phù hợp với đơn này."); return

        # Dialog chọn KM
        dlg = QDialog(self)
        dlg.setWindowTitle("🎉 Chọn Khuyến Mãi")
        dlg.resize(480, 360)
        dlg.setStyleSheet("background-color:#1E1E2E; color:white;")
        dv = QVBoxLayout(dlg)
        dv.setContentsMargins(16, 16, 16, 16); dv.setSpacing(10)

        dv.addWidget(QLabel(f"<b style='color:#E67E22; font-size:15px;'>Chọn khuyến mãi áp dụng</b>"))
        dv.addWidget(QLabel(f"<span style='color:#A1A1AA;'>Tổng đơn: {int(subtotal):,.0f} đ</span>"))

        lst = QListWidget()
        lst.setStyleSheet(
            "QListWidget{background:#2D2D3F;border:none;border-radius:8px;color:white;font-size:13px;}"
            "QListWidget::item{padding:10px 12px;border-bottom:1px solid #3E3E55;}"
            "QListWidget::item:selected{background:#E67E22;}"
        )
        for km in valid_kms:
            if km.loai_km == "MuaXTangY":
                desc = f"Mua {km.so_luong_mua or 1} tặng {km.so_luong_tang or 1}"
            elif km.kieu_giam == "PhanTram":
                desc = f"Giảm {int(km.gia_tri_giam or 0)}%"
                if km.toi_da_giam: desc += f" (tối đa {int(km.toi_da_giam):,}đ)"
            else:
                desc = f"Giảm {int(km.gia_tri_giam or 0):,}đ"
            if km.dk_tong_tien_tu:
                desc += f" | Đơn từ {int(km.dk_tong_tien_tu):,}đ"
            item = QListWidgetItem(f"  🎉 {km.ten_km}  —  {desc}")
            item.setData(Qt.UserRole, km.id)
            lst.addItem(item)

        dv.addWidget(lst)

        btn_row = QHBoxLayout()
        btn_ok  = QPushButton("✅ Áp dụng")
        btn_ok.setMinimumHeight(40)
        btn_ok.setStyleSheet("background:#27AE60;color:white;font-weight:bold;border-radius:6px;")
        btn_huy = QPushButton("❌ Bỏ KM")
        btn_huy.setMinimumHeight(40)
        btn_huy.setStyleSheet("background:#C0392B;color:white;font-weight:bold;border-radius:6px;")
        btn_row.addWidget(btn_ok); btn_row.addWidget(btn_huy)
        dv.addLayout(btn_row)

        def _do_apply():
            sel = lst.currentItem()
            if not sel:
                QMessageBox.warning(dlg, "Chưa chọn", "Hãy chọn một khuyến mãi!"); return
            km_id = sel.data(Qt.UserRole)
            s2 = get_session()
            try:
                km2 = s2.query(KhuyenMai).get(km_id)
                self._applied_km = {
                    "id":      km2.id,
                    "ten":     km2.ten_km,
                    "loai":    km2.loai_km,
                    "kieu":    km2.kieu_giam or "",
                    "gia_tri": float(km2.gia_tri_giam or 0),
                    "tran":    float(km2.toi_da_giam or 0) or None,
                }
            finally:
                s2.close()
            self.update_grand_total()
            _log(self.user.id, "Áp dụng khuyến mãi",
                 f"Áp KM '{self._applied_km['ten']}' — giảm {int(self._km_discount):,}đ",
                 o_dau="POS - Thanh toán")
            dlg.accept()

        def _do_remove():
            old_name = self._applied_km["ten"] if self._applied_km else "—"
            self._applied_km = None
            self._km_discount = 0
            self.update_grand_total()
            _log(self.user.id, "Bỏ khuyến mãi",
                 f"Gỡ KM '{old_name}' khỏi hóa đơn",
                 o_dau="POS - Thanh toán")
            dlg.accept()

        btn_ok.clicked.connect(_do_apply)
        btn_huy.clicked.connect(_do_remove)
        dlg.exec()

    # ----------------------------------------------------------------
    # THANH TOÁN
    # ----------------------------------------------------------------
    def handle_checkout(self):
        import random
        if self.order_table.rowCount() == 0:
            QMessageBox.warning(self, "Cảnh báo", "Hóa đơn đang trống!")
            return

        order_items = []
        grand_total = 0
        row = 0
        while row < self.order_table.rowCount():
            don_gia_item    = self.order_table.item(row, 1)
            thanh_tien_item = self.order_table.item(row, 2)
            # Bỏ qua row ghi chú
            if not don_gia_item or don_gia_item.data(Qt.UserRole) == "note_row":
                row += 1
                continue
            if not thanh_tien_item or not thanh_tien_item.text().strip():
                row += 1
                continue
            name       = self.order_table.item(row, 0).text()
            unit_price = float(don_gia_item.text().replace(",", ""))
            line_total = float(thanh_tien_item.text().replace(",", ""))
            qty        = round(line_total / unit_price) if unit_price else 1
            grand_total += line_total
            note = self._get_note_for_product_row(row)
            order_items.append({'name': name, 'qty': qty, 'price': unit_price, 'note': note})
            row += 1

        vat_tax      = grand_total * 0.10
        subtotal     = grand_total + vat_tax
        total_to_pay = max(0, subtotal - self._km_discount)

        # Dialog QR thanh toán
        dialog = QDialog(self)
        dialog.setWindowTitle("Quét mã thanh toán")
        dialog.setFixedSize(400, 580)
        dialog.setStyleSheet("background-color: #1E1E2E; color: white;")
        dlg_layout = QVBoxLayout(dialog)

        lines = [f"<b>CẦN THANH TOÁN (+10% VAT): {int(total_to_pay):,.0f} Đ</b>"]
        if self._applied_km:
            lines.append(
                f"<span style='color:#E67E22; font-size:13px;'>"
                f"🎉 KM [{self._applied_km['ten']}]: -{int(self._km_discount):,.0f} đ</span>"
            )
        title_lbl = QLabel("<br>".join(lines))
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("font-size: 16px; color: #2ECC71; margin-top: 10px;")
        title_lbl.setTextFormat(Qt.RichText)
        dlg_layout.addWidget(title_lbl)

        qr_label = QLabel("Đang tải mã QR...")
        qr_label.setAlignment(Qt.AlignCenter)
        dlg_layout.addWidget(qr_label)

        try:
            from utils.qr_generator import generate_vietqr_pixmap
            order_code = f"CF{random.randint(1000, 9999)}"
            pixmap = generate_vietqr_pixmap(total_to_pay, f"Thanh toan don {order_code}")
            if pixmap:
                qr_label.setPixmap(
                    pixmap.scaled(330, 330, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        except Exception:
            qr_label.setText("(Không tải được mã QR)")

        confirm_btn = QPushButton("ĐÃ NHẬN TIỀN (CHỐT ĐƠN)")
        confirm_btn.setMinimumHeight(60)
        confirm_btn.setStyleSheet(
            "background-color: #27AE60; color: white; font-weight: bold;"
            " font-size: 16px; border-radius: 8px;"
        )
        confirm_btn.clicked.connect(dialog.accept)
        dlg_layout.addWidget(confirm_btn)

        cancel_btn = QPushButton("Khách chưa chuyển (Hủy)")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setStyleSheet("background-color: #E74C3C; color: white; border-radius: 8px;")
        cancel_btn.clicked.connect(dialog.reject)
        dlg_layout.addWidget(cancel_btn)

        if dialog.exec() == QDialog.Accepted:
            from controllers.pos_controller import process_checkout
            success, message = process_checkout(
                order_items, self.user.id,
                km_id=self._applied_km["id"] if self._applied_km else None,
                km_discount=int(self._km_discount),
            )
            if success:
                self.sound_cash.play()

                # Tóm tắt đơn để ghi log
                mon_list = ", ".join(
                    f"{it['name']} x{it['qty']}" for it in order_items
                )
                km_info = f" | KM: {self._applied_km['ten']}" if self._applied_km else ""
                _log(self.user.id, "Chốt đơn hàng",
                     f"{message}{km_info} | Món: {mon_list}",
                     o_dau="POS - Thanh toán")

                # ── Reset bảng order: xóa widget con trước, rồi xóa rows ──
                for r in range(self.order_table.rowCount() - 1, -1, -1):
                    for c in range(self.order_table.columnCount()):
                        w = self.order_table.cellWidget(r, c)
                        if w:
                            w.setParent(None)
                            self.order_table.setCellWidget(r, c, None)
                self.order_table.clearContents()
                self.order_table.setRowCount(0)

                self._applied_km = None
                self._km_discount = 0
                self.update_grand_total()
                self.refresh_product_grid()

                # ── Cập nhật lịch sử TRƯỚC khi hiện thông báo ───────
                if self._history_dialog is not None:
                    try:
                        self._history_dialog.load_data()
                    except Exception:
                        pass

                QMessageBox.information(
                    self, "✅ Thành công",
                    f"ĐÃ CHỐT ĐƠN HÀNG!\n\n{message}\n\n"
                    "(Xem Lịch sử giao dịch để lấy mã hóa đơn nếu cần)"
                )
            else:
                _log(self.user.id, "Lỗi chốt đơn", message,
                     o_dau="POS - Thanh toán", ket_qua="Thất bại")
                QMessageBox.warning(self, "Lỗi Database", message)

    def show_shift_manager(self):
        if not yeu_cau_quyen(self.user.chuc_vu, "quan_ly_ca_lam", self):
            return
        _log(self.user.id, "Mở Phân công ca làm", o_dau="Phân công")
        from views.shift_manager import ShiftManagerDialog
        ShiftManagerDialog(self).exec()

    def show_attendance(self):
        if not yeu_cau_quyen(self.user.chuc_vu, "quan_ly_ca_lam", self):
            return
        _log(self.user.id, "Mở Điểm danh", o_dau="Điểm danh")
        from views.attendance_manager import AttendanceDialog
        AttendanceDialog(self).exec()

    def show_khuyen_mai(self):
        _log(self.user.id, "Mở Quản lý KM", o_dau="Khuyến mãi")
        from views.khuyen_mai_manager import KhuyenMaiManagerDialog
        KhuyenMaiManagerDialog(self).exec()

    def show_report(self):
        _log(self.user.id, "Mở Báo cáo", o_dau="Báo cáo")
        from views.report_window import ReportDialog
        ReportDialog(self).exec()

    def show_product_manager(self):
        _log(self.user.id, "Mở Quản lý Menu", o_dau="Menu")
        from views.product_manager import ProductManager
        ProductManager(self).exec()
        self.refresh_product_grid()

    def show_category_manager(self):
        _log(self.user.id, "Mở Quản lý Phân Loại", o_dau="Phân Loại")
        from views.category_manager import CategoryManagerDialog
        CategoryManagerDialog(self).exec()
        self.refresh_product_grid()

    def show_history_dialog(self):
        _log(self.user.id, "Mở Lịch sử giao dịch", o_dau="Lịch sử")
        from views.history_window import HistoryDialog
        self._history_dialog = HistoryDialog(self)
        self._history_dialog.exec()
        self._history_dialog = None

    # ----------------------------------------------------------------
    # CHECK-OUT CA LÀM VIỆC
    # ----------------------------------------------------------------
    def handle_ca_checkout(self):
        """
        Kết thúc ca làm việc: lưu giờ ra, tính công, khoá nghiệp vụ.
        Nếu không có ca trong ngày (ma_phien=None) → bỏ qua hoàn toàn.
        """
        # Không có ca → không cần check-out
        if not self.ma_phien:
            self._da_checkout = True
            return

        if self._da_checkout:
            QMessageBox.information(
                self, "Đã check-out",
                "Bạn đã hoàn tất check-out rồi.\nHãy bấm Đăng xuất để thoát."
            )
            return

        confirm = QMessageBox.question(
            self, "Xác nhận Check-out Ca",
            f"Bạn có muốn kết thúc ca làm việc không?\n\n"
            f"Hệ thống sẽ:\n"
            f"  ✅ Ghi nhận giờ ra\n"
            f"  ✅ Tính tổng giờ làm & tăng ca\n"
            f"  ✅ Khoá các thao tác bán hàng\n"
            f"  ✅ Chuyển trạng thái sang 'Nghỉ ca'",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        # ── Thực hiện check-out qua auth_controller ──────────────
        checkout_ok = False
        checkout_msg = ""
        try:
            from controllers.auth_controller import checkout_ca
            checkout_ok, checkout_msg = checkout_ca(self.user, ma_phien=self.ma_phien)
        except Exception as e:
            checkout_ok = False
            checkout_msg = str(e)

        if not checkout_ok:
            # Nếu controller chưa có hàm checkout_ca, coi như thành công
            # (backward-compat) — chỉ ghi log và tiếp tục
            if "cannot import" in checkout_msg.lower() or "has no attribute" in checkout_msg.lower():
                checkout_ok = True
                checkout_msg = "(checkout_ca chưa triển khai — bỏ qua)"
            else:
                QMessageBox.warning(
                    self, "Lỗi Check-out",
                    f"Không thể hoàn tất check-out:\n{checkout_msg}"
                )
                return

        # ── Cập nhật trạng thái UI ───────────────────────────────
        self._da_checkout = True

        _log(self.user.id, "Check-out ca làm",
             f"{self.user.ten_nv} kết thúc ca | phiên #{self.ma_phien} | {checkout_msg}",
             o_dau="Ca làm việc")

        # Khoá nút bán hàng
        self.checkout_btn.setEnabled(False)
        self.checkout_btn.setStyleSheet(
            "background-color: #555; color: #999; font-size: 18px;"
            " font-weight: bold; border-radius: 10px;"
        )
        self.checkout_btn.setText("🔒 ĐÃ KHOÁ (Ca đã kết thúc)")

        # Khoá luôn nút check-out và đổi màu
        self.btn_ca_checkout.setEnabled(False)
        self.btn_ca_checkout.setStyleSheet(
            "background-color: #27AE60; color: white; font-weight: bold;"
            " padding: 8px; border-radius: 6px;"
        )
        self.btn_ca_checkout.setText("✅ Đã Check-out")

        # Làm nổi bật nút Đăng xuất để hướng dẫn bước tiếp theo
        self.btn_logout.setStyleSheet(
            "background-color: #E74C3C; color: white; font-weight: bold;"
            " padding: 8px; border-radius: 6px;"
            " border: 2px solid #FF6B6B;"
        )
        self.btn_logout.setText(f"🚪 Đăng xuất ngay ←")

        QMessageBox.information(
            self, "✅ Check-out Thành Công",
            f"Ca làm việc đã được kết thúc!\n\n"
            f"Bạn có thể bấm 'Đăng xuất' để thoát khỏi hệ thống."
        )

    # ----------------------------------------------------------------
    # ĐĂNG XUẤT (thoát phiên ứng dụng)
    # ----------------------------------------------------------------
    def logout(self):
        """
        Thoát phiên đăng nhập.
        Safety-net: nếu chưa check-out, cảnh báo và cho phép
        thực hiện check-out + đăng xuất gộp hoặc huỷ.
        """
        from utils.session_manager import clear_session

        role = getattr(self.user, 'chuc_vu', '') or ''

        # ── Safety-net: chưa check-out (chỉ áp dụng khi có ca và không phải Admin) ──────
        if not self._da_checkout and self._co_ca and role != "Admin":
            reply = QMessageBox.warning(
                self, "Chưa Check-out Ca",
                "⚠️ Bạn chưa check-out ca làm việc!\n\n"
                "Xác nhận check-out và đăng xuất ngay bây giờ?",
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return
            self.handle_ca_checkout()
            if not self._da_checkout:
                return
        # Không có ca → bỏ qua safety-net, cho phép đăng xuất thẳng

        # ── Xác nhận đăng xuất thông thường ─────────────────────
        confirm = QMessageBox.question(
            self, "Đăng xuất",
            "Bạn có chắc chắn muốn đăng xuất?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        _log(self.user.id, "Đăng xuất POS",
             f"{self.user.ten_nv} đăng xuất khỏi màn hình bán hàng",
             o_dau="POS")

        # Gọi logout_user để đóng phiên trên server (nếu chưa checkout riêng)
        try:
            from controllers.auth_controller import logout_user
            logout_user(self.user, ma_phien=self.ma_phien)
        except Exception:
            pass

        clear_session()
        self.is_logged_out = True
        self.close()