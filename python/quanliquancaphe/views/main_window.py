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
        self._active_category  = "Tất cả"   # danh mục đang chọn
        self._cached_products  = []          # phải khai báo trước refresh_product_grid()

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

        # ── Hóa đơn dạng Card (InvoiceTable từ pos_screen.py) ───
        from views.pos_screen import InvoiceTable as _InvoiceTable
        self.order_table = _InvoiceTable()
        self.order_table.order_changed.connect(self.update_grand_total)
        self.right_layout.addWidget(self.order_table)

        # ── Hàng nút KM + Điểm TV ────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self.btn_apply_km = QPushButton("🎉 Khuyến mãi")
        self.btn_apply_km.setMinimumHeight(36)
        self.btn_apply_km.setStyleSheet(
            "background-color: #E67E22; color: white; font-weight: bold;"
            " border-radius: 8px; font-size: 13px;"
        )
        self.btn_apply_km.clicked.connect(self._apply_khuyen_mai)
        action_row.addWidget(self.btn_apply_km)

        self.btn_loyalty = QPushButton("⭐ Điểm TV")
        self.btn_loyalty.setMinimumHeight(36)
        self.btn_loyalty.setStyleSheet(
            "background-color: #8E44AD; color: white; font-weight: bold;"
            " border-radius: 8px; font-size: 13px;"
        )
        self.btn_loyalty.clicked.connect(self._open_loyalty)
        action_row.addWidget(self.btn_loyalty)

        self.right_layout.addLayout(action_row)

        # Label hiển thị KM đang áp dụng (ẩn khi chưa có)
        self.lbl_km_applied = QLabel("")
        self.lbl_km_applied.setStyleSheet(
            "background-color: #2D2D3F; border: 1px solid #E67E22;"
            " border-radius: 6px; padding: 6px 10px;"
            " font-size: 12px; color: #E67E22;"
        )
        self.lbl_km_applied.setWordWrap(True)
        self.lbl_km_applied.setVisible(False)
        self.right_layout.addWidget(self.lbl_km_applied)

        # Label hiển thị khách thành viên đang liên kết (ẩn khi chưa có)
        self.lbl_loyalty_info = QLabel("")
        self.lbl_loyalty_info.setStyleSheet(
            "background-color: #2D2D3F; border: 1px solid #8E44AD;"
            " border-radius: 6px; padding: 6px 10px;"
            " font-size: 12px; color: #C39BD3;"
        )
        self.lbl_loyalty_info.setWordWrap(True)
        self.lbl_loyalty_info.setVisible(False)
        self.right_layout.addWidget(self.lbl_loyalty_info)

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
        self._applied_km  = None   # dict: {id, ten, loai, kieu, gia_tri, tran}
        self._km_discount = 0     # số tiền đã giảm thực tế
        self._linked_kh   = None  # dict: {id, ten, sdt, hang, diem}
        

        # ── ÂM THANH ────────────────────────────────────────────────
        self.sound_beep = QSoundEffect()
        if os.path.exists("sounds/beep.wav"):
            self.sound_beep.setSource(QUrl.fromLocalFile("sounds/beep.wav"))
        self.sound_cash = QSoundEffect()
        if os.path.exists("sounds/cash.wav"):
            self.sound_cash.setSource(QUrl.fromLocalFile("sounds/cash.wav"))

        self._history_dialog  = None
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
        grand_total = self.order_table.grand_total()
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

        # Cập nhật label KM đang áp dụng
        if self._applied_km:
            km = self._applied_km
            if km["kieu"] == "PhanTram":
                mo_ta = f"Giảm {int(km['gia_tri'])}%"
                if km.get("tran"):
                    mo_ta += f" (tối đa {int(km['tran']):,}đ)"
            elif km["kieu"] == "TienMat":
                mo_ta = f"Giảm {int(km['gia_tri']):,}đ"
            else:
                mo_ta = km["ten"]
            self.lbl_km_applied.setText(
                f"✓ {km['ten']}\n"
                f"   {mo_ta}  →  -{int(self._km_discount):,}đ"
            )
            self.lbl_km_applied.setVisible(True)
        else:
            self.lbl_km_applied.setVisible(False)

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
        """Thêm món vào hóa đơn card, hoặc tăng SL nếu đã có."""
        self.order_table.add_item(product['name'], product['price'])
        self.sound_beep.play()
        self.highlight_total()
        _log(self.user.id, "Thêm món vào order",
             f"Thêm '{product['name']}' — {int(product['price']):,}đ",
             o_dau="POS - Order")
        if not self._applied_km:
            self._auto_apply_best_km()

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
    def _auto_apply_best_km(self):
        """
        Tự động tìm và áp KM tốt nhất hợp lệ cho đơn hàng hiện tại.
        Chỉ áp dụng khi chưa có KM nào. Không hỏi xác nhận — âm thầm áp.
        """
        try:
            from datetime import datetime, date
            from database.db_config import get_session
            from database.models import KhuyenMai

            # Tính tổng đơn hiện tại
            grand_total = self.order_table.grand_total()
            if grand_total <= 0:
                return

            now = datetime.now()
            today = date.today()

            s = get_session()
            try:
                kms = s.query(KhuyenMai).filter_by(trang_thai="Đang chạy").all()
            finally:
                s.close()

            best_km   = None
            best_giam = 0

            for km in kms:
                # Kiểm tra ngày hợp lệ
                if km.ngay_bat_dau and today < km.ngay_bat_dau:
                    continue
                if km.ngay_ket_thuc and today > km.ngay_ket_thuc:
                    continue

                # Kiểm tra khung giờ
                gio_tu  = getattr(km, 'gio_tu',  None)
                gio_den = getattr(km, 'gio_den', None)
                if gio_tu and gio_den:
                    t = now.time().replace(second=0, microsecond=0)
                    if not (gio_tu <= t <= gio_den):
                        continue

                # Kiểm tra lượt dùng
                if km.so_luot_toi_da and km.so_luot_da_dung and \
                        km.so_luot_da_dung >= km.so_luot_toi_da:
                    continue

                # Kiểm tra điều kiện tối thiểu
                dk = km.dk_tong_tien_tu or 0
                if grand_total < dk:
                    continue

                # Bỏ qua MuaXTangY (phức tạp, không auto-apply)
                if km.loai_km == "MuaXTangY":
                    continue

                # Tính tiền giảm
                if km.kieu_giam == "PhanTram":
                    giam = grand_total * (km.gia_tri_giam or 0) / 100
                    if km.toi_da_giam:
                        giam = min(giam, km.toi_da_giam)
                else:
                    giam = km.gia_tri_giam or 0

                # Ưu tiên: giam nhiều hơn hoặc cùng giam nhưng uu_tien cao hơn
                uu = int(getattr(km, 'uu_tien', 0) or 0)
                if giam > best_giam or (giam == best_giam and uu > getattr(best_km, '_uu', 0)):
                    best_giam = giam
                    best_km   = km
                    km._uu    = uu

            if not best_km or best_giam <= 0:
                return

            # Áp dụng âm thầm
            self._applied_km  = {
                "id":      best_km.id,
                "ten":     best_km.ten_km,
                "loai":    best_km.loai_km,
                "kieu":    best_km.kieu_giam,
                "gia_tri": best_km.gia_tri_giam,
                "tran":    best_km.toi_da_giam,
            }
            self._km_discount = best_giam
            self.update_grand_total()
        except Exception:
            pass  # Lỗi auto-km không làm crash app

    def _apply_khuyen_mai(self):
        """
        Tự động tính KM tốt nhất đang chạy, cho phép xem/xác nhận/bỏ.
        Không cần nhập mã tay.
        """
        if not self.order_table.get_items():
            QMessageBox.warning(self, "Hóa đơn trống", "Hãy thêm món trước!")
            return

        from database.db_config import get_session
        from database.models import KhuyenMai
        from datetime import date

        # Tính tổng đơn hiện tại
        grand_total = self.order_table.grand_total()
        subtotal    = grand_total * 1.10

        # Lấy danh sách KM hợp lệ
        session = get_session()
        try:
            today = date.today()
            kms = session.query(KhuyenMai).filter_by(trang_thai="Đang chạy").all()
            valid_kms = []
            for km in kms:
                if km.ngay_bat_dau and km.ngay_bat_dau > today: continue
                if km.ngay_ket_thuc and km.ngay_ket_thuc < today: continue
                if km.dk_tong_tien_tu and subtotal < km.dk_tong_tien_tu: continue
                # Tính giảm tạm thời để chọn tốt nhất
                if km.kieu_giam == "PhanTram":
                    giam = subtotal * float(km.gia_tri_giam or 0) / 100
                    if km.toi_da_giam:
                        giam = min(giam, float(km.toi_da_giam))
                elif km.kieu_giam == "TienMat":
                    giam = min(float(km.gia_tri_giam or 0), subtotal)
                else:
                    giam = 0
                valid_kms.append({
                    "id":      km.id,
                    "ten":     km.ten_km,
                    "loai":    km.loai_km or "",
                    "kieu":    km.kieu_giam or "",
                    "gia_tri": float(km.gia_tri_giam or 0),
                    "tran":    float(km.toi_da_giam or 0) or None,
                    "dk_min":  float(km.dk_tong_tien_tu or 0),
                    "_giam":   giam,
                })
        finally:
            session.close()

        # Sắp xếp: KM giảm nhiều nhất lên đầu (auto-best)
        valid_kms.sort(key=lambda x: x["_giam"], reverse=True)

        # ── Dialog chọn KM ───────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle("🎉 Khuyến Mãi")
        dlg.resize(500, 420)
        dlg.setStyleSheet(
            "QDialog,QWidget{background:#1E1E2E;color:white;font-family:'Segoe UI';}"
            "QLabel{background:transparent;}"
            f"QListWidget{{background:#2D2D3F;border:none;border-radius:8px;"
            f"color:white;font-size:13px;}}"
            f"QListWidget::item{{padding:10px 14px;border-bottom:1px solid #3E3E55;}}"
            f"QListWidget::item:selected{{background:#E67E22;color:white;}}"
            f"QPushButton{{border-radius:6px;font-weight:bold;font-size:13px;color:white;padding:6px 14px;}}"
        )
        dv = QVBoxLayout(dlg)
        dv.setContentsMargins(18, 16, 18, 16)
        dv.setSpacing(10)

        # Tiêu đề + tổng đơn
        hdr = QHBoxLayout()
        hdr_lbl = QLabel("<b style='color:#E67E22;font-size:15px;'>🎉  Chọn Khuyến Mãi</b>")
        hdr_lbl.setTextFormat(Qt.RichText)
        hdr.addWidget(hdr_lbl)
        hdr.addStretch()
        total_lbl = QLabel(f"<span style='color:#A1A1AA;font-size:12px;'>Đơn: {int(subtotal):,.0f} đ</span>")
        total_lbl.setTextFormat(Qt.RichText)
        hdr.addWidget(total_lbl)
        dv.addLayout(hdr)

        if not valid_kms:
            no_km = QLabel("😔  Không có khuyến mãi nào phù hợp với đơn này.")
            no_km.setStyleSheet("color:#A1A1AA; font-size:13px; padding:20px 0;")
            no_km.setAlignment(Qt.AlignCenter)
            dv.addWidget(no_km)
            btn_close = QPushButton("Đóng")
            btn_close.setMinimumHeight(38)
            btn_close.setStyleSheet("background:#555566;color:white;font-weight:bold;border-radius:6px;")
            btn_close.clicked.connect(dlg.reject)
            dv.addWidget(btn_close)
            dlg.exec()
            return

        # Gợi ý KM tốt nhất
        best = valid_kms[0]
        tip = QLabel(
            f"✨  <b>Tốt nhất:</b>  {best['ten']}  —  giảm <b style='color:#E67E22;'>"
            f"{int(best['_giam']):,}đ</b>"
        )
        tip.setTextFormat(Qt.RichText)
        tip.setStyleSheet(
            "background:#2D3A2D; border:1px solid #27AE60; border-radius:6px;"
            " padding:7px 12px; font-size:12px; color:#A9DFBF;"
        )
        dv.addWidget(tip)

        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        lst = QListWidget()
        for km in valid_kms:
            if km["kieu"] == "PhanTram":
                desc = f"Giảm {int(km['gia_tri'])}%"
                if km["tran"]:
                    desc += f"  (tối đa {int(km['tran']):,}đ)"
            elif km["kieu"] == "TienMat":
                desc = f"Giảm {int(km['gia_tri']):,}đ"
            else:
                desc = km["loai"]
            if km["dk_min"]:
                desc += f"  |  Đơn từ {int(km['dk_min']):,}đ"
            saving_str = f"  →  -{int(km['_giam']):,}đ" if km["_giam"] else ""
            it = QListWidgetItem(f"  🎉  {km['ten']}  —  {desc}{saving_str}")
            it.setData(Qt.UserRole, km)
            lst.addItem(it)
        lst.setCurrentRow(0)   # Tự động chọn KM tốt nhất
        dv.addWidget(lst)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_ok = QPushButton("✅  Áp dụng")
        btn_ok.setMinimumHeight(40)
        btn_ok.setStyleSheet("background:#27AE60;color:white;font-weight:bold;border-radius:6px;")

        btn_remove = QPushButton("🗑  Bỏ KM")
        btn_remove.setMinimumHeight(40)
        btn_remove.setStyleSheet("background:#C0392B;color:white;font-weight:bold;border-radius:6px;")

        btn_cancel = QPushButton("Hủy")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setStyleSheet("background:#555566;color:white;font-weight:bold;border-radius:6px;")

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_cancel)
        dv.addLayout(btn_row)

        def _do_apply():
            sel = lst.currentItem()
            if not sel:
                QMessageBox.warning(dlg, "Chưa chọn", "Hãy chọn một khuyến mãi!"); return
            km_data = sel.data(Qt.UserRole)
            self._applied_km = km_data
            self.update_grand_total()
            _log(self.user.id, "Áp dụng khuyến mãi",
                 f"Áp KM '{km_data['ten']}' — giảm {int(self._km_discount):,}đ",
                 o_dau="POS - Thanh toán")
            dlg.accept()

        def _do_remove():
            old = self._applied_km["ten"] if self._applied_km else "—"
            self._applied_km = None
            self._km_discount = 0
            self.update_grand_total()
            _log(self.user.id, "Bỏ khuyến mãi", f"Gỡ KM '{old}'", o_dau="POS - Thanh toán")
            dlg.accept()

        btn_ok.clicked.connect(_do_apply)
        btn_remove.clicked.connect(_do_remove)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec()

    # ----------------------------------------------------------------
    # ĐIỂM THÀNH VIÊN
    # ----------------------------------------------------------------
    def _update_loyalty_label(self):
        """Cập nhật label hiển thị KH thành viên đang liên kết."""
        kh = self._linked_kh
        if kh:
            hang_color = {
                "Kim cương": "#00BCD4", "Vàng": "#F1C40F",
                "Bạc": "#BDC3C7", "Đồng": "#CD7F32",
            }.get(kh.get("hang", "Đồng"), "#C39BD3")
            self.lbl_loyalty_info.setText(
                f"⭐  {kh['ten']}  ({kh.get('hang','Đồng')})  |  "
                f"SĐT: {kh['sdt']}  |  Điểm: {kh.get('diem', 0):,}"
            )
            self.lbl_loyalty_info.setStyleSheet(
                f"background-color: #2D2D3F; border: 1px solid {hang_color};"
                f" border-radius: 6px; padding: 6px 10px;"
                f" font-size: 12px; color: {hang_color};"
            )
            self.lbl_loyalty_info.setVisible(True)
        else:
            self.lbl_loyalty_info.setVisible(False)

    def _open_loyalty(self):
        """
        Popup nhập SĐT để tìm / tạo khách thành viên và liên kết bill.
        """
        from database.db_config import get_session
        from database.models import KhachHang

        dlg = QDialog(self)
        dlg.setWindowTitle("⭐ Điểm Thành Viên")
        dlg.resize(420, 320)
        dlg.setStyleSheet(
            "QDialog,QWidget{background:#1E1E2E;color:white;font-family:'Segoe UI';}"
            "QLabel{background:transparent;}"
            "QLineEdit{background:#2D2D3F;border:1px solid #3E3E55;border-radius:6px;"
            "  padding:8px 12px;color:white;font-size:14px;}"
            "QLineEdit:focus{border-color:#8E44AD;}"
            "QPushButton{border-radius:6px;font-weight:bold;font-size:13px;"
            "  color:white;padding:8px 14px;}"
        )
        dv = QVBoxLayout(dlg)
        dv.setContentsMargins(20, 18, 20, 18)
        dv.setSpacing(12)

        # Tiêu đề
        dv.addWidget(QLabel(
            "<b style='color:#C39BD3;font-size:15px;'>⭐  Tra cứu Thành Viên</b>"
        ))

        # Ô nhập SĐT
        from PySide6.QtWidgets import QLineEdit as QLE
        txt_sdt = QLE()
        txt_sdt.setPlaceholderText("Nhập số điện thoại khách hàng…")
        txt_sdt.setMaxLength(15)
        dv.addWidget(txt_sdt)

        # Khu vực kết quả
        lbl_result = QLabel("")
        lbl_result.setWordWrap(True)
        lbl_result.setTextFormat(Qt.RichText)
        lbl_result.setStyleSheet(
            "background:#2D2D3F; border-radius:8px; padding:10px 14px;"
            " font-size:13px; color:#ECF0F1; min-height:60px;"
        )
        dv.addWidget(lbl_result)

        # Hàng nút
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_search = QPushButton("🔍  Tìm")
        btn_search.setStyleSheet("background:#8E44AD;color:white;font-weight:bold;border-radius:6px;")
        btn_link   = QPushButton("✅  Liên kết bill")
        btn_link.setStyleSheet("background:#27AE60;color:white;font-weight:bold;border-radius:6px;")
        btn_link.setEnabled(False)
        btn_unlink = QPushButton("🗑  Bỏ liên kết")
        btn_unlink.setStyleSheet("background:#C0392B;color:white;font-weight:bold;border-radius:6px;")
        btn_new    = QPushButton("➕  Thêm TV mới")
        btn_new.setStyleSheet("background:#2980B9;color:white;font-weight:bold;border-radius:6px;")
        btn_new.setVisible(False)
        btn_close  = QPushButton("Đóng")
        btn_close.setStyleSheet("background:#555566;color:white;font-weight:bold;border-radius:6px;")

        btn_row.addWidget(btn_search)
        btn_row.addWidget(btn_link)
        btn_row.addWidget(btn_unlink)
        btn_row.addWidget(btn_close)
        dv.addLayout(btn_row)
        dv.addWidget(btn_new)

        # Nếu đang có KH liên kết → điền sẵn SĐT
        if self._linked_kh:
            txt_sdt.setText(self._linked_kh["sdt"])

        _found_kh: dict | None = None   # KH tìm được tạm thời

        def _do_search():
            nonlocal _found_kh
            sdt = txt_sdt.text().strip()
            if not sdt:
                lbl_result.setText("<span style='color:#E74C3C;'>Vui lòng nhập SĐT!</span>")
                return
            s = get_session()
            try:
                kh = s.query(KhachHang).filter_by(so_dien_thoai=sdt).first()
                if kh:
                    hang_color = {
                        "Kim cương": "#00BCD4", "Vàng": "#F1C40F",
                        "Bạc": "#BDC3C7", "Đồng": "#CD7F32",
                    }.get(kh.hang_thanh_vien or "Đồng", "#C39BD3")
                    _found_kh = {
                        "id":   kh.id,
                        "ten":  kh.ten_kh,
                        "sdt":  kh.so_dien_thoai,
                        "hang": kh.hang_thanh_vien or "Đồng",
                        "diem": kh.diem_tich_luy or 0,
                    }
                    lbl_result.setText(
                        f"<b style='color:{hang_color};'>{kh.ten_kh}</b>"
                        f"  <span style='color:#A1A1AA;'>({kh.hang_thanh_vien or 'Đồng'})</span><br>"
                        f"<span style='color:#BDC3C7;'>SĐT: {kh.so_dien_thoai}"
                        f"  |  Điểm: <b style='color:#F1C40F;'>{kh.diem_tich_luy or 0:,}</b></span>"
                    )
                    btn_link.setEnabled(True)
                    btn_new.setVisible(False)
                else:
                    _found_kh = None
                    lbl_result.setText(
                        f"<span style='color:#E74C3C;'>⚠️  Chưa có thành viên với SĐT <b>{sdt}</b></span>"
                    )
                    btn_link.setEnabled(False)
                    btn_new.setVisible(True)
            finally:
                s.close()

        def _do_link():
            if _found_kh:
                self._linked_kh = _found_kh
                self._update_loyalty_label()
                _log(self.user.id, "Liên kết thành viên",
                     f"Liên kết KH '{_found_kh['ten']}' ({_found_kh['sdt']}) vào bill",
                     o_dau="POS - Thanh toán")
                dlg.accept()

        def _do_unlink():
            old = self._linked_kh["ten"] if self._linked_kh else "—"
            self._linked_kh = None
            self._update_loyalty_label()
            _log(self.user.id, "Bỏ liên kết thành viên",
                 f"Gỡ KH '{old}' khỏi bill", o_dau="POS - Thanh toán")
            dlg.accept()

        def _do_new():
            """Mở CustomerManagerDialog để tạo KH mới, sau đó quay lại."""
            dlg.reject()
            from views.customer_manager import CustomerManagerDialog
            cm = CustomerManagerDialog(self)
            cm.exec()
            # Điền lại SĐT vừa nhập nếu user muốn tìm lại
            dlg2 = QDialog(self)   # không cần mở lại dlg cũ vì đã reject

        txt_sdt.returnPressed.connect(_do_search)
        btn_search.clicked.connect(_do_search)
        btn_link.clicked.connect(_do_link)
        btn_unlink.clicked.connect(_do_unlink)
        btn_new.clicked.connect(_do_new)
        btn_close.clicked.connect(dlg.reject)
        dlg.exec()

    # ----------------------------------------------------------------
    # THANH TOÁN
    # ----------------------------------------------------------------
    def handle_checkout(self):
        import random
        if not self.order_table.get_items():
            QMessageBox.warning(self, "Cảnh báo", "Hóa đơn đang trống!")
            return

        raw_items   = self.order_table.get_items()
        order_items = []
        grand_total = 0
        for it in raw_items:
            parts = []
            if it.get("topping") and it["topping"] != "Không topping":
                parts.append(it["topping"])
            if it.get("da") and it["da"] != "Bình thường":
                parts.append(it["da"])
            if it.get("duong") and it["duong"] != "Vừa":
                parts.append(it["duong"])
            if it.get("note"):
                parts.append(it["note"])
            note = " | ".join(parts)
            grand_total += it["qty"] * it["price"]
            order_items.append({
                'name': it['name'], 'qty': it['qty'],
                'price': it['price'], 'note': note,
            })

        vat_tax      = grand_total * 0.10
        subtotal     = grand_total + vat_tax
        total_to_pay = max(0, subtotal - self._km_discount)

        # ── POPUP THANH TOÁN NÂNG CẤP ───────────────────────────────
        import random as _rnd
        order_code = f"CF{_rnd.randint(1000, 9999)}"

        # Biến lưu phương thức thanh toán được chọn (mặc định QR)
        _pay_method = ["qr"]   # dùng list để closure có thể ghi

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Thanh toán  ·  {order_code}")
        dialog.setFixedSize(440, 600)
        dialog.setStyleSheet("""
            QDialog { background-color: #0F1729; color: #E2E8F0; }
            QLabel  { border: none; background: transparent; }
            * { font-family: 'Segoe UI', 'Inter', sans-serif; }
        """)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(18, 16, 18, 14)
        dlg_layout.setSpacing(10)

        # ── A. Header ───────────────────────────────────────────────────
        hdr = QFrame(dialog)
        hdr.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            " stop:0 #1E293B, stop:1 #0F172A);"
            " border-radius: 14px; border: 1px solid #1E3A5F; }"
        )
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 14, 18, 14)
        hdr_lay.setSpacing(4)

        # Mã đơn nhỏ gọn
        lbl_code = QLabel(f"🧾  {order_code}")
        lbl_code.setAlignment(Qt.AlignCenter)
        lbl_code.setStyleSheet(
            "font-size: 10px; color: #475569; letter-spacing: 2.5px;"
            " font-weight: 600; text-transform: uppercase;"
        )
        hdr_lay.addWidget(lbl_code)

        # Tổng tiền lớn — tăng 15%, màu xanh dịu
        lbl_total = QLabel(f"{int(total_to_pay):,} đ")
        lbl_total.setAlignment(Qt.AlignCenter)
        lbl_total.setStyleSheet(
            "font-size: 36px; font-weight: 700; color: #38BDF8;"
            " letter-spacing: -1px;"
        )
        hdr_lay.addWidget(lbl_total)

        # Chi tiết: Tạm tính · VAT · Giảm giá — icon outline đồng bộ
        detail_parts = [f"○  {int(grand_total):,} đ", "⊕  VAT 10%"]
        if self._applied_km and self._km_discount > 0:
            detail_parts.append(
                f"◎  {self._applied_km['ten']}  −{int(self._km_discount):,} đ"
            )
        lbl_sub = QLabel("   ·   ".join(detail_parts))
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet(
            "font-size: 10px; color: #475569; letter-spacing: 0.3px;"
        )
        hdr_lay.addWidget(lbl_sub)

        dlg_layout.addWidget(hdr)

        # ── B. Tabs phương thức ─────────────────────────────────────────
        tab_frame = QFrame(dialog)
        tab_frame.setStyleSheet(
            "QFrame { background:#1E293B; border-radius: 10px; border: none; }"
        )
        tab_frame.setFixedHeight(40)       # giảm 10% so với 44px cũ
        tab_lay = QHBoxLayout(tab_frame)
        tab_lay.setContentsMargins(3, 3, 3, 3)
        tab_lay.setSpacing(3)

        _STYLE_TAB_ON = (
            "QPushButton { background: #1D4ED8; color: white; font-weight: 600;"
            " border-radius: 8px; font-size: 12px; padding: 5px 0; border: none;"
            " letter-spacing: 0.3px; }"
        )
        _STYLE_TAB_OFF = (
            "QPushButton { background: transparent; color: #64748B; font-weight: 600;"
            " border-radius: 8px; font-size: 12px; padding: 5px 0; border: none; }"
            "QPushButton:hover { background: #0F172A; color: #94A3B8; }"
        )

        btn_tab_qr   = QPushButton("⬡  QR / Chuyển khoản")
        btn_tab_cash = QPushButton("◈  Tiền mặt")
        for b in (btn_tab_qr, btn_tab_cash):
            tab_lay.addWidget(b)
        dlg_layout.addWidget(tab_frame)

        # ── C. Stack ────────────────────────────────────────────────────
        from PySide6.QtWidgets import QStackedWidget
        stack = QStackedWidget(dialog)
        stack.setStyleSheet("QStackedWidget { border: none; background: transparent; }")

        # ── Panel QR ────────────────────────────────────────────────────
        pg_qr = QWidget(); pg_qr.setStyleSheet("background: transparent;")
        qr_vlay = QVBoxLayout(pg_qr)
        qr_vlay.setContentsMargins(0, 4, 0, 0)
        qr_vlay.setSpacing(8)

        # Card nền sáng cho QR — thu nhỏ 18%
        qr_card = QFrame()
        qr_card.setStyleSheet(
            "QFrame { background: #F8FAFC; border-radius: 14px;"
            " border: 2px solid #E2E8F0; }"
        )
        qr_card_lay = QVBoxLayout(qr_card)
        qr_card_lay.setContentsMargins(10, 10, 10, 10)

        qr_label = QLabel("Đang tải mã QR…")
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setStyleSheet("color: #94A3B8; font-size: 12px; background: transparent;")
        qr_label.setFixedSize(222, 222)   # 270 × 0.82 ≈ 222 (thu nhỏ ~18%)
        qr_card_lay.addWidget(qr_label, 0, Qt.AlignCenter)
        qr_vlay.addWidget(qr_card, 0, Qt.AlignCenter)

        try:
            from utils.qr_generator import generate_vietqr_pixmap
            pixmap = generate_vietqr_pixmap(total_to_pay, f"Thanh toan don {order_code}")
            if pixmap:
                qr_label.setPixmap(
                    pixmap.scaled(222, 222, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        except Exception:
            qr_label.setText("(Không tải được mã QR)")

        hint_qr = QLabel("⬡  Dùng App ngân hàng quét mã · Tự động xác nhận khi nhận tiền")
        hint_qr.setAlignment(Qt.AlignCenter)
        hint_qr.setWordWrap(True)
        hint_qr.setStyleSheet("font-size: 10px; color: #475569; letter-spacing: 0.2px;")
        qr_vlay.addWidget(hint_qr)
        qr_vlay.addStretch()
        stack.addWidget(pg_qr)

        # ── Panel Tiền mặt ───────────────────────────────────────────────
        pg_cash = QWidget(); pg_cash.setStyleSheet("background: transparent;")
        cash_vlay = QVBoxLayout(pg_cash)
        cash_vlay.setContentsMargins(0, 4, 0, 0)
        cash_vlay.setSpacing(8)

        lbl_need = QLabel(f"Cần thu:  {int(total_to_pay):,} đ")
        lbl_need.setAlignment(Qt.AlignCenter)
        lbl_need.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #38BDF8;"
            " background: #1E293B; border-radius: 8px; padding: 8px 0;"
        )
        cash_vlay.addWidget(lbl_need)

        # Ô nhập tiền khách
        row_cash = QHBoxLayout()
        lbl_given = QLabel("Khách đưa:")
        lbl_given.setStyleSheet("font-size: 12px; color: #64748B; min-width: 75px;")
        txt_given = QLineEdit()
        txt_given.setPlaceholderText(f"{int(total_to_pay):,}")
        txt_given.setAlignment(Qt.AlignRight)
        txt_given.setStyleSheet(
            "background: #1E293B; border: 1px solid #334155;"
            " border-radius: 8px; padding: 8px 12px;"
            " color: #F1F5F9; font-size: 15px; font-weight: 600;"
        )
        row_cash.addWidget(lbl_given)
        row_cash.addWidget(txt_given)
        cash_vlay.addLayout(row_cash)

        # Card tiền thối nổi bật
        change_card = QFrame()
        change_card.setStyleSheet(
            "QFrame { background: #1E293B; border-radius: 10px;"
            " border: 1px solid #334155; }"
        )
        change_card_lay = QHBoxLayout(change_card)
        change_card_lay.setContentsMargins(14, 10, 14, 10)
        lbl_change_title = QLabel("Tiền thối")
        lbl_change_title.setStyleSheet("font-size: 12px; color: #64748B;")
        lbl_change = QLabel("—")
        lbl_change.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_change.setStyleSheet("font-size: 24px; font-weight: 700; color: #94A3B8;")
        change_card_lay.addWidget(lbl_change_title)
        change_card_lay.addStretch()
        change_card_lay.addWidget(lbl_change)
        cash_vlay.addWidget(change_card)

        # Quick-cash thông minh: gợi ý số tiền gần nhất + các nút tiện
        def _smart_amounts():
            """Tạo danh sách gợi ý: làm tròn gần nhất + cố định + đúng tiền."""
            candidates = set()
            # Làm tròn lên
            for unit in [10_000, 20_000, 50_000, 100_000, 200_000, 500_000]:
                rounded = ((int(total_to_pay) + unit - 1) // unit) * unit
                candidates.add(rounded)
            # Loại bỏ những số bằng tổng tiền chính xác
            final = sorted([a for a in candidates if a >= total_to_pay])[:3]
            return final

        quick_lay = QGridLayout()
        quick_lay.setSpacing(5)

        smart = _smart_amounts()
        all_btns = []

        # Dòng 1: gợi ý thông minh
        for i, amt in enumerate(smart[:3]):
            label = f"{amt//1000}k" if amt < 1_000_000 else f"{amt/1_000_000:.1f}M"
            bq = QPushButton(label)
            bq.setMinimumHeight(32)
            bq.setStyleSheet(
                "QPushButton { background: #1D4ED8; color: #BFDBFE;"
                " border: none; border-radius: 7px;"
                " font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { background: #2563EB; color: white; }"
            )
            bq.clicked.connect(lambda _, a=amt: txt_given.setText(f"{a:,}"))
            quick_lay.addWidget(bq, 0, i)
            all_btns.append(bq)

        # Dòng 2: đúng tiền, +10k, +50k
        btn_exact = QPushButton("◎ Đúng tiền")
        btn_p10   = QPushButton("+10k")
        btn_p50   = QPushButton("+50k")
        for i, b in enumerate([btn_exact, btn_p10, btn_p50]):
            b.setMinimumHeight(32)
            b.setStyleSheet(
                "QPushButton { background: #0F172A; color: #94A3B8;"
                " border: 1px solid #334155; border-radius: 7px;"
                " font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { background: #1E293B; color: #CBD5E1; }"
            )
            quick_lay.addWidget(b, 1, i)

        btn_exact.clicked.connect(lambda: txt_given.setText(f"{int(total_to_pay):,}"))
        btn_p10.clicked.connect(lambda: _add_to_given(10_000))
        btn_p50.clicked.connect(lambda: _add_to_given(50_000))

        def _add_to_given(delta: int):
            try:
                cur = float(txt_given.text().replace(",", "") or 0)
            except ValueError:
                cur = 0
            txt_given.setText(f"{int(cur + delta):,}")

        cash_vlay.addLayout(quick_lay)
        cash_vlay.addStretch()

        def _calc_change():
            try:
                given  = float(txt_given.text().replace(",", "").replace(".", "") or 0)
                change = given - total_to_pay
                if given <= 0:
                    lbl_change.setText("—")
                    lbl_change.setStyleSheet(
                        "font-size: 24px; font-weight: 700; color: #94A3B8;"
                    )
                    change_card.setStyleSheet(
                        "QFrame { background:#1E293B; border-radius:10px;"
                        " border:1px solid #334155; }"
                    )
                    btn_confirm.setEnabled(True)
                elif change < 0:
                    lbl_change.setText(f"⚠ Thiếu  {abs(int(change)):,} đ")
                    lbl_change.setStyleSheet(
                        "font-size: 16px; font-weight: 700; color: #F87171;"
                    )
                    change_card.setStyleSheet(
                        "QFrame { background:#2D1515; border-radius:10px;"
                        " border:1px solid #7F1D1D; }"
                    )
                    btn_confirm.setEnabled(False)
                    btn_confirm.setStyleSheet(
                        "QPushButton { background:#374151; color:#6B7280;"
                        " font-size:14px; font-weight:500;"
                        " border-radius:14px; border:none; }"
                    )
                else:
                    lbl_change.setText(f"{int(change):,} đ")
                    lbl_change.setStyleSheet(
                        "font-size: 24px; font-weight: 700; color: #34D399;"
                    )
                    change_card.setStyleSheet(
                        "QFrame { background:#0D2B1E; border-radius:10px;"
                        " border:1px solid #065F46; }"
                    )
                    btn_confirm.setEnabled(True)
                    _reset_confirm_style()
            except Exception:
                lbl_change.setText("—")

        txt_given.textChanged.connect(_calc_change)
        stack.addWidget(pg_cash)
        dlg_layout.addWidget(stack, 1)

        # ── D. Nút xác nhận ─────────────────────────────────────────────
        btn_confirm = QPushButton("⬡  ĐÃ NHẬN TIỀN  —  CHỐT ĐƠN")
        btn_confirm.setMinimumHeight(48)

        def _reset_confirm_style():
            btn_confirm.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                " stop:0 #059669, stop:1 #0D9488);"
                " color: white; font-weight: 500; font-size: 14px;"
                " border-radius: 14px; border: none; letter-spacing: 0.5px; }"
                "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                " stop:0 #047857, stop:1 #0F766E); }"
                "QPushButton:pressed { background: #065F46; }"
                "QPushButton:disabled { background: #374151; color: #6B7280; }"
            )

        _reset_confirm_style()

        def _on_confirm():
            btn_confirm.setEnabled(False)
            btn_confirm.setText("⟳  Đang xử lý…")
            dialog.accept()

        btn_confirm.clicked.connect(_on_confirm)
        dlg_layout.addWidget(btn_confirm)

        btn_cancel = QPushButton("Hủy")
        btn_cancel.setMinimumHeight(32)
        btn_cancel.setStyleSheet(
            "QPushButton { background: transparent; color: #475569;"
            " font-size: 12px; border: 1px solid #1E293B; border-radius: 10px; }"
            "QPushButton:hover { background: #1E293B; color: #94A3B8; }"
        )
        btn_cancel.clicked.connect(dialog.reject)
        dlg_layout.addWidget(btn_cancel)

        # ── E. Tab switch ────────────────────────────────────────────────
        def _switch(method: str):
            _pay_method[0] = method
            if method == "qr":
                btn_tab_qr.setStyleSheet(_STYLE_TAB_ON)
                btn_tab_cash.setStyleSheet(_STYLE_TAB_OFF)
                stack.setCurrentIndex(0)
                btn_confirm.setText("⬡  ĐÃ NHẬN TIỀN  —  CHỐT ĐƠN")
                btn_confirm.setEnabled(True)
                _reset_confirm_style()
            else:
                btn_tab_qr.setStyleSheet(_STYLE_TAB_OFF)
                btn_tab_cash.setStyleSheet(_STYLE_TAB_ON)
                stack.setCurrentIndex(1)
                btn_confirm.setText("◈  THU TIỀN MẶT  —  CHỐT ĐƠN")
                _calc_change()   # cập nhật trạng thái nút ngay

        btn_tab_qr.clicked.connect(lambda: _switch("qr"))
        btn_tab_cash.clicked.connect(lambda: _switch("cash"))
        _switch("qr")

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

                # ── Reset hóa đơn ───────────────────────────────────
                # FIX: Reset KM TRƯỚC khi gọi update_grand_total
                self._applied_km  = None
                self._km_discount = 0
                self._linked_kh   = None
                self.order_table.clear_items()
                self.update_grand_total()
                self._update_loyalty_label()
                self.refresh_product_grid()

                # ── Cập nhật lịch sử nếu dialog đang mở ──────────────
                # (HistoryDialog là modal nên thường _history_dialog=None
                #  ở đây; đoạn này chỉ là safety-net)
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
        try:
            from views.report_window import ReportDialog
            ReportDialog(self).exec()
        except ImportError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Lỗi mở Báo cáo",
                f"Không thể mở cửa sổ Báo cáo:\n{e}\n\n"
                "Kiểm tra file views/report_window.py có tồn tại không."
            )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Lỗi Báo cáo", str(e))

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
        # KHÔNG set về None ở đây — để handle_checkout vẫn giữ được reference
        # khi cửa sổ lịch sử vừa được đóng sau thanh toán
        self._history_dialog = None

    # ----------------------------------------------------------------
    # CHECK-OUT CA LÀM VIỆC
    # ----------------------------------------------------------------
    def handle_ca_checkout(self):
        """
        Kết thúc ca làm việc: lưu giờ ra, tính công, khoá nghiệp vụ.
        Nếu không có ca trong ngày (ma_phien=None) → bỏ qua hoàn toàn.
        """
        # Không có ca đang mở → không cần check-out
        # Hỏi DB thực tế thay vì chỉ dựa vào ma_phien (có thể stale)
        try:
            from controllers.auth_controller import lay_ca_dang_mo
            _co_ca_mo = bool(lay_ca_dang_mo(self.user.id))
        except Exception:
            _co_ca_mo = bool(self.ma_phien)   # fallback nếu import lỗi

        if not _co_ca_mo:
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
        # checkout_ca(ma_cham_cong: int) — chỉ nhận int ID của ChamCong.
        # Phải dùng lay_ca_dang_mo() để lấy danh sách, rồi loop từng ca.
        checkout_ok  = False
        checkout_msg = ""
        try:
            from controllers.auth_controller import checkout_ca, lay_ca_dang_mo
            cas_dang_mo = lay_ca_dang_mo(self.user.id)

            if not cas_dang_mo:
                # Không còn ca mở nào → coi như đã checkout
                checkout_ok  = True
                checkout_msg = "Không có ca đang mở"
            else:
                ok_list, err_list = [], []
                for ca_info in cas_dang_mo:
                    ok, msg = checkout_ca(ca_info["id"])   # truyền đúng int
                    (ok_list if ok else err_list).append(
                        f"  • {ca_info['ten_ca']}: {msg}"
                    )

                if err_list:
                    QMessageBox.warning(
                        self, "Lỗi Check-out",
                        "Một số ca không thể check-out:\n"
                        + "\n".join(err_list)
                        + "\n\nVui lòng liên hệ Admin hoặc thử lại."
                    )
                    if not ok_list:
                        return   # toàn bộ đều lỗi → dừng lại

                checkout_ok  = True
                checkout_msg = " | ".join(
                    m.strip("  •") for m in ok_list
                ) or "Đã check-out"

        except ImportError as e:
            # Controller chưa triển khai → bypass (backward-compat)
            checkout_ok  = True
            checkout_msg = f"(bỏ qua — {e})"
        except Exception as e:
            QMessageBox.warning(
                self, "Lỗi Check-out",
                f"Lỗi không mong đợi khi check-out:\n{e}\n\n"
                "Vui lòng liên hệ quản trị viên."
            )
            return

        if not checkout_ok:
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

        # ── Safety-net: chưa check-out ──────────────────────────────
        # Luôn kiểm tra thực tế từ DB thay vì tin vào flag _co_ca (có thể stale)
        co_ca_dang_mo = False
        if not self._da_checkout and role != "Admin":
            try:
                from controllers.auth_controller import lay_ca_dang_mo
                co_ca_dang_mo = bool(lay_ca_dang_mo(self.user.id))
            except Exception:
                co_ca_dang_mo = self._co_ca  # fallback

        if co_ca_dang_mo and not self._da_checkout and role != "Admin":
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
                # handle_ca_checkout đã hiện lỗi → chỉ dừng lại
                return
        # Không có ca đang mở → bỏ qua safety-net, cho phép đăng xuất thẳng

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