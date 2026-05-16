"""
views/admin_settings.py
Quản lý Nhân Sự đầy đủ:
  • CRUD nhân viên (tên, SDT, email, ngày vào làm, lương cơ bản)
  • 5 chức vụ: Admin / Quản lý / Thu ngân / Pha chế / Phục vụ
  • Avatar nhân viên (chọn file ảnh)
  • Khóa / Mở tài khoản
  • Đổi mật khẩu riêng
  • Nhật ký hoạt động theo nhân viên
  • Các tab còn lại của AdminSettingsDialog giữ nguyên
"""

import os
import shutil
from datetime import date, datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget,
    QWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFormLayout, QLineEdit, QComboBox,
    QFrame, QFileDialog, QDateEdit, QSizePolicy, QAbstractItemView,
    QScrollArea,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QPixmap, QPainter, QPainterPath, QFont, QIcon

from database.db_config import get_session
from database.models import NhanVien, NhatKyHoatDong

# ── Màu sắc theo chức vụ ────────────────────────────────────────────────────
ROLE_COLOR = {
    "Admin":    "#E74C3C",
    "Quản lý":  "#E67E22",
    "Thu ngân": "#3498DB",
    "Pha chế":  "#9B59B6",
    "Phục vụ":  "#27AE60",
}
ROLES = list(ROLE_COLOR.keys())

STATUS_COLOR = {
    "Đang làm việc": "#2ECC71",
    "Tạm khóa":      "#F1C40F",
    "Đã nghỉ việc":  "#E74C3C",
}

AVATAR_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)
DEFAULT_AVATAR = os.path.join(os.path.dirname(__file__), "..", "assets", "default_avatar.png")

STYLE_BASE = """
    QDialog  { background-color: #1E1E2E; color: white; }
    QWidget  { background-color: #1E1E2E; color: white; }
    QLabel   { color: white; }
    QLineEdit, QComboBox, QDateEdit {
        background-color: #2D2D3F; border: 1px solid #3E3E55;
        border-radius: 6px; padding: 6px 10px; color: white; font-size: 13px;
    }
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
        border: 1px solid #3498DB;
    }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView { background-color: #2D2D3F; color: white; selection-background-color: #3498DB; }
    QTableWidget {
        background-color: #2D2D3F; border: none; border-radius: 10px;
        gridline-color: #3E3E55; color: white; font-size: 13px;
    }
    QTableWidget::item { padding: 8px; border-bottom: 1px solid #3E3E55; }
    QTableWidget::item:selected { background-color: #3498DB; color: white; }
    QHeaderView::section {
        background-color: #1A1A24; color: #A1A1AA;
        padding: 10px; border: none; font-weight: bold; font-size: 13px;
    }
    QScrollBar:vertical { background: #1A1A24; width: 8px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #3E3E55; border-radius: 4px; }
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: ghi nhật ký
# ═══════════════════════════════════════════════════════════════════════════════
def ghi_nhat_ky(ma_nv: int, hanh_dong: str, mo_ta: str = ""):
    session = get_session()
    try:
        log = NhatKyHoatDong(ma_nv=ma_nv, hanh_dong=hanh_dong, mo_ta=mo_ta)
        session.add(log)
        session.commit()
    except Exception:
        pass
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# WIDGET: Avatar tròn
# ═══════════════════════════════════════════════════════════════════════════════
class AvatarLabel(QLabel):
    """Hiển thị ảnh avatar dạng tròn, kích thước cố định."""
    def __init__(self, size=80, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.set_avatar(None)

    def set_avatar(self, path: str | None):
        pixmap = None
        if path and os.path.isfile(path):
            pixmap = QPixmap(path)
        elif os.path.isfile(DEFAULT_AVATAR):
            pixmap = QPixmap(DEFAULT_AVATAR)

        if pixmap:
            pixmap = pixmap.scaled(self._size, self._size,
                                   Qt.KeepAspectRatioByExpanding,
                                   Qt.SmoothTransformation)
            # Cắt tròn
            rounded = QPixmap(self._size, self._size)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path_clip = QPainterPath()
            path_clip.addEllipse(0, 0, self._size, self._size)
            painter.setClipPath(path_clip)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            self.setPixmap(rounded)
        else:
            # Fallback: vẽ vòng tròn màu xám với chữ "?"
            placeholder = QPixmap(self._size, self._size)
            placeholder.fill(Qt.transparent)
            painter = QPainter(placeholder)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#3E3E55"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, self._size, self._size)
            painter.setPen(QColor("white"))
            font = QFont("Arial", self._size // 3, QFont.Bold)
            painter.setFont(font)
            painter.drawText(0, 0, self._size, self._size, Qt.AlignCenter, "?")
            painter.end()
            self.setPixmap(placeholder)


# ═══════════════════════════════════════════════════════════════════════════════
# FORM: THÊM / SỬA NHÂN VIÊN (đầy đủ)
# ═══════════════════════════════════════════════════════════════════════════════
class EmployeeForm(QDialog):
    """
    Form thêm mới hoặc chỉnh sửa thông tin nhân viên.
    Truyền actor_id để ghi nhật ký (id của admin đang thao tác).
    """
    def __init__(self, parent=None, emp_id=None, actor_id=None):
        super().__init__(parent)
        self.emp_id   = emp_id
        self.actor_id = actor_id
        self._avatar_path = None   # đường dẫn ảnh chọn mới

        self.setWindowTitle("Thêm Nhân Viên" if not emp_id else "Sửa Thông Tin Nhân Viên")
        self.resize(480, 600)
        self.setStyleSheet(STYLE_BASE)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(24, 24, 24, 24)

        # ── Avatar ──────────────────────────────────────────────
        av_row = QHBoxLayout()
        av_row.setAlignment(Qt.AlignCenter)
        self.avatar_lbl = AvatarLabel(90)
        av_row.addWidget(self.avatar_lbl)

        btn_pick_av = QPushButton("🖼 Chọn Ảnh")
        btn_pick_av.setFixedWidth(110)
        btn_pick_av.setStyleSheet(
            "background-color: #2D2D3F; border: 1px solid #3E3E55;"
            " border-radius: 6px; padding: 6px; color: #A1A1AA; font-size: 12px;"
        )
        btn_pick_av.clicked.connect(self._pick_avatar)
        av_col = QVBoxLayout()
        av_col.setAlignment(Qt.AlignCenter)
        av_col.addWidget(self.avatar_lbl, alignment=Qt.AlignCenter)
        av_col.addWidget(btn_pick_av, alignment=Qt.AlignCenter)
        av_row.addLayout(av_col)
        root.addLayout(av_row)

        # ── Form fields ─────────────────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        def _lbl(text):
            l = QLabel(text)
            l.setStyleSheet("color: #A1A1AA; font-size: 13px;")
            return l

        self.txt_name  = QLineEdit();  self.txt_name.setPlaceholderText("Nguyễn Văn A")
        self.txt_user  = QLineEdit();  self.txt_user.setPlaceholderText("nhanvien01")
        self.txt_sdt   = QLineEdit();  self.txt_sdt.setPlaceholderText("0901234567")
        self.txt_email = QLineEdit();  self.txt_email.setPlaceholderText("nv@quancafe.vn")
        self.txt_luong = QLineEdit();  self.txt_luong.setPlaceholderText("5000000")

        self.cb_role = QComboBox()
        self.cb_role.addItems(ROLES)

        self.cb_status = QComboBox()
        self.cb_status.addItems(list(STATUS_COLOR.keys()))

        self.de_ngay = QDateEdit()
        self.de_ngay.setCalendarPopup(True)
        self.de_ngay.setDate(QDate.currentDate())
        self.de_ngay.setDisplayFormat("dd/MM/yyyy")

        form.addRow(_lbl("Họ tên *:"),        self.txt_name)
        form.addRow(_lbl("Tên đăng nhập *:"), self.txt_user)
        form.addRow(_lbl("Số điện thoại:"),   self.txt_sdt)
        form.addRow(_lbl("Email:"),            self.txt_email)
        form.addRow(_lbl("Chức vụ:"),          self.cb_role)
        form.addRow(_lbl("Lương cơ bản (đ):"), self.txt_luong)
        form.addRow(_lbl("Ngày vào làm:"),     self.de_ngay)
        form.addRow(_lbl("Trạng thái:"),       self.cb_status)
        root.addLayout(form)

        # ── Nút lưu ─────────────────────────────────────────────
        btn_save = QPushButton("💾  Lưu Thông Tin")
        btn_save.setMinimumHeight(44)
        btn_save.setStyleSheet(
            "background-color: #27AE60; color: white; font-weight: bold;"
            " font-size: 14px; border-radius: 8px;"
        )
        btn_save.clicked.connect(self._save)
        root.addWidget(btn_save)

        if self.emp_id:
            self._load()

    # ── Chọn avatar ─────────────────────────────────────────────
    def _pick_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh đại diện", "",
            "Ảnh (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._avatar_path = path
            self.avatar_lbl.set_avatar(path)

    # ── Load dữ liệu khi sửa ────────────────────────────────────
    def _load(self):
        session = get_session()
        emp = session.query(NhanVien).get(self.emp_id)
        if emp:
            self.txt_name.setText(emp.ten_nv or "")
            self.txt_user.setText(emp.ten_dang_nhap or "")
            self.txt_sdt.setText(emp.sdt or "")
            self.txt_email.setText(emp.email or "")
            self.txt_luong.setText(str(int(emp.luong_co_ban or 0)))
            self.cb_role.setCurrentText(emp.chuc_vu or "Thu ngân")
            self.cb_status.setCurrentText(emp.trang_thai or "Đang làm việc")
            if emp.ngay_vao_lam:
                self.de_ngay.setDate(
                    QDate(emp.ngay_vao_lam.year,
                          emp.ngay_vao_lam.month,
                          emp.ngay_vao_lam.day)
                )
            self.avatar_lbl.set_avatar(emp.avatar_path)
        session.close()

    # ── Lưu ─────────────────────────────────────────────────────
    def _save(self):
        name  = self.txt_name.text().strip()
        user  = self.txt_user.text().strip()
        sdt   = self.txt_sdt.text().strip()
        email = self.txt_email.text().strip()
        role  = self.cb_role.currentText()
        status = self.cb_status.currentText()
        luong_txt = self.txt_luong.text().strip().replace(",", "").replace(".", "")

        if not name or not user:
            QMessageBox.warning(self, "Thiếu thông tin", "Họ tên và tên đăng nhập là bắt buộc!")
            return

        luong = 0.0
        try:
            luong = float(luong_txt) if luong_txt else 0.0
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Lương cơ bản phải là số!")
            return

        qd = self.de_ngay.date()
        ngay_vao = date(qd.year(), qd.month(), qd.day())

        session = get_session()
        try:
            is_new = (self.emp_id is None)
            if is_new:
                if session.query(NhanVien).filter_by(ten_dang_nhap=user).first():
                    QMessageBox.warning(self, "Trùng tên", "Tên đăng nhập đã tồn tại!")
                    return
                emp = NhanVien(mat_khau="123456")
                session.add(emp)
            else:
                emp = session.query(NhanVien).get(self.emp_id)
                if not emp:
                    QMessageBox.critical(self, "Lỗi", "Không tìm thấy nhân viên!")
                    return

            emp.ten_nv        = name
            emp.ten_dang_nhap = user
            emp.sdt           = sdt or None
            emp.email         = email or None
            emp.chuc_vu       = role
            emp.luong_co_ban  = luong
            emp.ngay_vao_lam  = ngay_vao
            emp.trang_thai    = status

            # Copy avatar vào thư mục assets
            if self._avatar_path:
                ext  = os.path.splitext(self._avatar_path)[1]
                dest = os.path.join(AVATAR_DIR, f"nv_{user}{ext}")
                shutil.copy2(self._avatar_path, dest)
                emp.avatar_path = dest

            session.commit()
            session.refresh(emp)
            if is_new:
                            QMessageBox.information(
                                self, "Tài khoản đã tạo",
                                f"✅ Đã tạo tài khoản {user}\n\n"
                                f"Mật khẩu mặc định: 123456\n"
                                f"Nhân viên nên đổi mật khẩu sau khi đăng nhập lần đầu."
                            )
            # Ghi nhật ký
            if self.actor_id:
                action = f"{'Thêm' if is_new else 'Sửa'} nhân viên"
                ghi_nhat_ky(self.actor_id, action,
                            f"Tài khoản: {user} | Chức vụ: {role}")

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
        finally:
            session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG: ĐỔI MẬT KHẨU
# ═══════════════════════════════════════════════════════════════════════════════
class ChangePasswordDialog(QDialog):
    """
    Đổi mật khẩu nhân viên.
    - Admin đổi cho người khác: không cần nhập MK cũ.
    - Nhân viên tự đổi (actor_id == emp_id): phải nhập MK cũ để xác thực.
    - Sau khi đổi thành công: gửi email xác nhận nếu nhân viên có email.
    """
    def __init__(self, emp_id: int, actor_id: int = None, parent=None):
        super().__init__(parent)
        self.emp_id    = emp_id
        self.actor_id  = actor_id
        self._is_self  = (actor_id is not None and actor_id == emp_id)

        self.setWindowTitle("Đổi Mật Khẩu")
        self.resize(380, self._is_self and 280 or 240)
        self.setStyleSheet(STYLE_BASE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Tiêu đề
        title = QLabel("🔑 ĐỔI MẬT KHẨU")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #E67E22;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet("color: #A1A1AA;")
            return l

        # Ô mật khẩu cũ — chỉ hiện khi tự đổi
        self.txt_old = None
        if self._is_self:
            self.txt_old = QLineEdit()
            self.txt_old.setEchoMode(QLineEdit.Password)
            self.txt_old.setPlaceholderText("Nhập mật khẩu hiện tại")
            form.addRow(_lbl("Mật khẩu cũ:"), self.txt_old)

        self.txt_new  = QLineEdit()
        self.txt_new.setEchoMode(QLineEdit.Password)
        self.txt_new.setPlaceholderText("Mật khẩu mới (tối thiểu 4 ký tự)")

        self.txt_conf = QLineEdit()
        self.txt_conf.setEchoMode(QLineEdit.Password)
        self.txt_conf.setPlaceholderText("Nhập lại mật khẩu mới")

        form.addRow(_lbl("Mật khẩu mới:"), self.txt_new)
        form.addRow(_lbl("Xác nhận lại:"), self.txt_conf)
        layout.addLayout(form)

        # Checkbox gửi email xác nhận
        from PySide6.QtWidgets import QCheckBox
        self.chk_email = QCheckBox("📧 Gửi email xác nhận cho nhân viên")
        self.chk_email.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        self.chk_email.setChecked(True)
        layout.addWidget(self.chk_email)

        btn = QPushButton("🔑  Cập Nhật Mật Khẩu")
        btn.setMinimumHeight(44)
        btn.setStyleSheet(
            "background-color: #E67E22; color: white; font-weight: bold;"
            " border-radius: 8px; font-size: 14px;"
        )
        btn.clicked.connect(self._save)
        layout.addWidget(btn)

        # Enter trong ô cuối cũng submit
        self.txt_conf.returnPressed.connect(self._save)

    def _save(self):
        new  = self.txt_new.text().strip()
        conf = self.txt_conf.text().strip()

        if not new:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu không được trống!")
            return
        if new != conf:
            QMessageBox.warning(self, "Không khớp", "Hai mật khẩu không giống nhau!")
            return
        if len(new) < 4:
            QMessageBox.warning(self, "Quá ngắn", "Mật khẩu tối thiểu 4 ký tự!")
            return

        session = get_session()
        try:
            emp = session.query(NhanVien).get(self.emp_id)
            if not emp:
                QMessageBox.critical(self, "Lỗi", "Không tìm thấy nhân viên!")
                return

            # Xác thực MK cũ khi nhân viên tự đổi
            if self._is_self and self.txt_old:
                old = self.txt_old.text().strip()
                if emp.mat_khau != old:
                    QMessageBox.warning(self, "Sai mật khẩu",
                                        "Mật khẩu cũ không đúng!")
                    self.txt_old.clear()
                    self.txt_old.setFocus()
                    return

            old_user  = emp.ten_dang_nhap
            ten_nv    = emp.ten_nv
            email_nv  = emp.email
            emp.mat_khau = new
            session.commit()

            if self.actor_id:
                ghi_nhat_ky(self.actor_id, "Đổi mật khẩu",
                            f"Tài khoản: {old_user}")

            # Gửi email xác nhận nếu được chọn và có email
            if self.chk_email.isChecked() and email_nv:
                try:
                    from utils.email_helper import send_change_password_confirm
                    ok_send, err = send_change_password_confirm(email_nv, ten_nv)
                    if not ok_send:
                        QMessageBox.warning(
                            self, "⚠️ Đổi MK thành công nhưng gửi email thất bại",
                            f"Mật khẩu đã được cập nhật.\n\n"
                            f"Không gửi được email xác nhận:\n{err}"
                        )
                        self.accept()
                        return
                except Exception as e:
                    pass  # lỗi email không làm hỏng chức năng chính

            QMessageBox.information(
                self, "✅ Thành công",
                f"Đã cập nhật mật khẩu cho {ten_nv}!"
                + (f"\n📧 Email xác nhận đã gửi đến {email_nv}"
                   if self.chk_email.isChecked() and email_nv else "")
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi DB", str(e))
        finally:
            session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG: NHẬT KÝ HOẠT ĐỘNG CỦA 1 NHÂN VIÊN
# ═══════════════════════════════════════════════════════════════════════════════
class ActivityLogDialog(QDialog):
    def __init__(self, emp_id: int, ten_nv: str, parent=None):
        super().__init__(parent)
        self.emp_id = emp_id
        self.setWindowTitle(f"Nhật Ký Hoạt Động — {ten_nv}")
        self.resize(680, 460)
        self.setStyleSheet(STYLE_BASE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"<b>📋 NHẬT KÝ: {ten_nv.upper()}</b>")
        title.setStyleSheet("font-size: 16px; color: #F1C40F; margin-bottom: 8px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Thời Gian", "Hành Động", "Mô Tả"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        btn = QPushButton("Đóng")
        btn.setMinimumHeight(38)
        btn.setStyleSheet(
            "background-color: #34495E; border-radius: 8px; font-weight: bold;"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self._load()

    def _load(self):
        self.table.setRowCount(0)
        session = get_session()
        try:
            logs = (session.query(NhatKyHoatDong)
                    .filter_by(ma_nv=self.emp_id)
                    .order_by(NhatKyHoatDong.thoi_gian.desc())
                    .limit(200).all())
            for i, log in enumerate(logs):
                self.table.insertRow(i)
                tg = log.thoi_gian.strftime("%H:%M  %d/%m/%Y") if log.thoi_gian else ""
                self.table.setItem(i, 0, QTableWidgetItem(tg))
                item_hd = QTableWidgetItem(log.hanh_dong)
                item_hd.setForeground(QColor("#3498DB"))
                self.table.setItem(i, 1, item_hd)
                self.table.setItem(i, 2, QTableWidgetItem(log.mo_ta or ""))
        finally:
            session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PANEL: DANH SÁCH NHÂN VIÊN (tab chính trong AdminSettingsDialog)
# ═══════════════════════════════════════════════════════════════════════════════
class EmployeePanel(QWidget):
    """
    Toàn bộ UI quản lý nhân viên, dùng bên trong AdminSettingsDialog.
    actor_id: id của admin/quản lý đang đăng nhập (để ghi nhật ký).
    """
    def __init__(self, actor_id: int = None, parent=None):
        super().__init__(parent)
        self.actor_id = actor_id
        self.setStyleSheet(STYLE_BASE)

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Tiêu đề + toolbar ───────────────────────────────────
        toolbar = QHBoxLayout()
        title = QLabel("DANH SÁCH NHÂN VIÊN")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #3498DB;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        def _btn(text, color):
            b = QPushButton(text)
            b.setStyleSheet(
                f"background-color: {color}; color: white; font-weight: bold;"
                f" padding: 7px 14px; border-radius: 6px; font-size: 13px;"
            )
            return b

        self.btn_add    = _btn("➕ Thêm mới",      "#27AE60")
        self.btn_edit   = _btn("✏️ Sửa",           "#2980B9")
        self.btn_pwd    = _btn("🔑 Đổi MK",        "#E67E22")
        self.btn_toggle = _btn("🔒 Khóa / Mở",    "#8E44AD")
        self.btn_log    = _btn("📋 Nhật ký",       "#16A085")
        self.btn_del    = _btn("🗑 Xóa",           "#C0392B")

        for b in [self.btn_add, self.btn_edit, self.btn_pwd,
                  self.btn_toggle, self.btn_log, self.btn_del]:
            toolbar.addWidget(b)
        root.addLayout(toolbar)

        # ── Bảng ────────────────────────────────────────────────
        # Cột: Avatar | ID | Tên | ĐN | SDT | Email | Chức vụ | Lương | Vào làm | TT
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "", "ID", "Họ Tên", "Đăng Nhập",
            "SĐT", "Email", "Chức Vụ",
            "Lương Cơ Bản", "Ngày Vào Làm", "Trạng Thái"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed);          self.table.setColumnWidth(0, 52)
        hh.setSectionResizeMode(1, QHeaderView.Fixed);          self.table.setColumnWidth(1, 40)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setRowHeight(0, 56)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)

        # ── Kết nối ─────────────────────────────────────────────
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_pwd.clicked.connect(self._change_pwd)
        self.btn_toggle.clicked.connect(self._toggle_lock)
        self.btn_log.clicked.connect(self._show_log)
        self.btn_del.clicked.connect(self._delete)
        self.table.itemDoubleClicked.connect(self._edit)

        self.load()

    # ── Load bảng ───────────────────────────────────────────────
    def load(self):
        self.table.setRowCount(0)
        session = get_session()
        try:
            emps = session.query(NhanVien).order_by(NhanVien.id).all()
            for i, emp in enumerate(emps):
                self.table.insertRow(i)
                self.table.setRowHeight(i, 56)

                # Cột 0: Avatar
                av_lbl = AvatarLabel(44)
                av_lbl.set_avatar(emp.avatar_path)
                av_lbl.setStyleSheet("background: transparent;")
                cell = QWidget()
                cl = QHBoxLayout(cell)
                cl.setContentsMargins(4, 4, 4, 4)
                cl.addWidget(av_lbl, alignment=Qt.AlignCenter)
                self.table.setCellWidget(i, 0, cell)

                # Cột 1: ID (ẩn, dùng UserRole)
                id_item = QTableWidgetItem(str(emp.id))
                id_item.setData(Qt.UserRole, emp.id)
                id_item.setForeground(QColor("#A1A1AA"))
                self.table.setItem(i, 1, id_item)

                # Cột 2: Họ tên
                name_item = QTableWidgetItem(emp.ten_nv)
                f = name_item.font(); f.setBold(True); name_item.setFont(f)
                self.table.setItem(i, 2, name_item)

                # Cột 3: Đăng nhập
                self.table.setItem(i, 3, QTableWidgetItem(emp.ten_dang_nhap or ""))

                # Cột 4: SĐT
                self.table.setItem(i, 4, QTableWidgetItem(emp.sdt or "—"))

                # Cột 5: Email
                self.table.setItem(i, 5, QTableWidgetItem(emp.email or "—"))

                # Cột 6: Chức vụ (màu theo role)
                role_item = QTableWidgetItem(emp.chuc_vu or "")
                role_item.setForeground(
                    QColor(ROLE_COLOR.get(emp.chuc_vu, "#A1A1AA"))
                )
                f2 = role_item.font(); f2.setBold(True); role_item.setFont(f2)
                self.table.setItem(i, 6, role_item)

                # Cột 7: Lương
                luong_str = f"{int(emp.luong_co_ban or 0):,} đ".replace(",", ".")
                luong_item = QTableWidgetItem(luong_str)
                luong_item.setForeground(QColor("#2ECC71"))
                self.table.setItem(i, 7, luong_item)

                # Cột 8: Ngày vào làm
                nvl = emp.ngay_vao_lam.strftime("%d/%m/%Y") if emp.ngay_vao_lam else "—"
                self.table.setItem(i, 8, QTableWidgetItem(nvl))

                # Cột 9: Trạng thái
                tt = emp.trang_thai or "Đang làm việc"
                tt_item = QTableWidgetItem(tt)
                tt_item.setForeground(QColor(STATUS_COLOR.get(tt, "#A1A1AA")))
                self.table.setItem(i, 9, tt_item)

        finally:
            session.close()

    # ── Lấy emp_id dòng đang chọn ───────────────────────────────
    def _selected_emp_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn", "Vui lòng chọn một nhân viên!")
            return None
        item = self.table.item(row, 1)
        return item.data(Qt.UserRole) if item else None

    def _selected_ten(self) -> str:
        row = self.table.currentRow()
        if row < 0: return ""
        item = self.table.item(row, 2)
        return item.text() if item else ""

    # ── CRUD ────────────────────────────────────────────────────
    def _add(self):
        if EmployeeForm(self, actor_id=self.actor_id).exec():
            self.load()

    def _edit(self, *_):
        emp_id = self._selected_emp_id()
        if emp_id is None: return
        if EmployeeForm(self, emp_id=emp_id, actor_id=self.actor_id).exec():
            self.load()

    def _change_pwd(self):
        emp_id = self._selected_emp_id()
        if emp_id is None: return
        ChangePasswordDialog(emp_id, self.actor_id, self).exec()

    def _toggle_lock(self):
        emp_id = self._selected_emp_id()
        if emp_id is None: return
        session = get_session()
        try:
            emp = session.query(NhanVien).get(emp_id)
            if not emp: return
            if emp.chuc_vu == "Admin":
                QMessageBox.warning(self, "Không thể", "Không thể khóa tài khoản Admin!")
                return
            if emp.trang_thai == "Đang làm việc":
                emp.trang_thai = "Tạm khóa"
                action = "Khóa tài khoản"
            elif emp.trang_thai == "Tạm khóa":
                emp.trang_thai = "Đang làm việc"
                action = "Mở tài khoản"
            else:
                QMessageBox.information(self, "Chú ý",
                    f"Nhân viên đang ở trạng thái '{emp.trang_thai}'.\n"
                    "Hãy sửa thủ công nếu cần.")
                return
            session.commit()
            if self.actor_id:
                ghi_nhat_ky(self.actor_id, action,
                            f"Tài khoản: {emp.ten_dang_nhap}")
        finally:
            session.close()
        self.load()

    def _show_log(self):
        emp_id = self._selected_emp_id()
        if emp_id is None: return
        ActivityLogDialog(emp_id, self._selected_ten(), self).exec()

    def _delete(self):
        emp_id = self._selected_emp_id()
        if emp_id is None: return
        ten = self._selected_ten()
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn XÓA VĨNH VIỄN nhân viên <b>{ten}</b>?<br>"
            "<span style='color:#E74C3C;'>Hành động này không thể hoàn tác!</span>",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes: return
        session = get_session()
        try:
            emp = session.query(NhanVien).get(emp_id)
            if emp:
                if emp.chuc_vu == "Admin":
                    QMessageBox.warning(self, "Không thể", "Không được xóa tài khoản Admin!"); return
                session.delete(emp)
                session.commit()
                if self.actor_id:
                    ghi_nhat_ky(self.actor_id, "Xóa nhân viên",
                                f"Đã xóa: {emp.ten_dang_nhap}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            session.close()
        self.load()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH: CÀI ĐẶT HỆ THỐNG
# ═══════════════════════════════════════════════════════════════════════════════
class AdminSettingsDialog(QDialog):
    def __init__(self, parent=None, actor_id: int = None):
        super().__init__(parent)
        self.actor_id = actor_id
        self.setWindowTitle("Cài Đặt Hệ Thống Nâng Cao")
        self.resize(1100, 640)
        self.setStyleSheet(STYLE_BASE + """
            QListWidget {
                background-color: #2D2D3F; border: none; border-radius: 10px;
                color: #A1A1AA; font-size: 14px; font-weight: bold;
            }
            QListWidget::item { padding: 16px 12px; border-bottom: 1px solid #1E1E2E; }
            QListWidget::item:selected { background-color: #3498DB; color: white; border-radius: 8px; }
        """)

        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Menu trái ───────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(220)
        left.setStyleSheet("background-color: #2D2D3F; border-right: 1px solid #3E3E55;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(10, 16, 10, 16)
        lv.setSpacing(0)

        menu_title = QLabel("⚙️ CÀI ĐẶT")
        menu_title.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #A1A1AA;"
            " padding: 0 8px 12px 8px; letter-spacing: 1px;"
        )
        lv.addWidget(menu_title)

        self.menu_list = QListWidget()
        self.menu_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { padding: 14px 10px; border-radius: 8px; margin-bottom: 2px; }
            QListWidget::item:selected { background-color: #3498DB; color: white; }
            QListWidget::item:hover { background-color: #3E3E55; }
        """)
        self.menu_list.addItems([
            "👥  Quản lý Nhân Sự",
            "🕐  Phân Ca Làm Việc",
            "💰  Bảng Lương",
            "⚙️  Cấu hình Quán",
        ])
        lv.addWidget(self.menu_list)
        lv.addStretch()
        root.addWidget(left)

        # ── Stack phải ──────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setContentsMargins(16, 16, 16, 16)
        root.addWidget(self.stack)

        # Tab 0: Nhân sự
        self.stack.addWidget(EmployeePanel(actor_id=self.actor_id))

        # Tab 1: Phân ca
        self.stack.addWidget(self._make_shift_tab())

        # Tab 2: Lương (demo)
        self.stack.addWidget(self._make_payroll_tab())

        # Tab 3: Cấu hình (placeholder)
        ph = QLabel("🔧 Tính năng Cấu hình Quán đang được phát triển...")
        ph.setAlignment(Qt.AlignCenter)
        ph.setStyleSheet("font-size: 15px; color: #A1A1AA;")
        self.stack.addWidget(ph)

        self.menu_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.menu_list.setCurrentRow(0)

    # ── Tab phân ca ─────────────────────────────────────────────
    def _make_shift_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignCenter)
        lbl = QLabel(
            "🕐 <b>Quản lý Ca Làm Việc & Phân Công</b><br><br>"
            "Tạo ca, phân công nhiều nhân viên theo ngày,<br>"
            "điểm danh và xem lịch tuần trực quan."
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 15px; color: #BDC3C7; line-height: 1.8;")
        lay.addWidget(lbl)
        btn = QPushButton("📅  Mở Màn Hình Phân Ca")
        btn.setMinimumHeight(55); btn.setMinimumWidth(280)
        btn.setStyleSheet(
            "background-color: #2980B9; color: white; font-size: 16px;"
            " font-weight: bold; border-radius: 10px;"
        )
        btn.clicked.connect(self._open_shift_manager)
        lay.addWidget(btn, alignment=Qt.AlignCenter)
        return w

    def _open_shift_manager(self):
        try:
            from views.shift_manager import ShiftManagerDialog
            ShiftManagerDialog(self).exec()
        except ImportError:
            QMessageBox.information(self, "Chưa sẵn sàng",
                                    "Module phân ca chưa được cài đặt.")

    # ── Tab lương ───────────────────────────────────────────────
    def _make_payroll_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        title = QLabel("TÍNH TOÁN LƯƠNG NHÂN VIÊN THÁNG NÀY")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #F1C40F;")
        lay.addWidget(title)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            ["Tên Nhân Viên", "Chức Vụ", "Số Ca Làm", "Lương Cơ Bản", "Tổng Ước Tính"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Load thực từ DB
        session = get_session()
        try:
            emps = session.query(NhanVien).filter(
                NhanVien.trang_thai == "Đang làm việc"
            ).all()
            for i, emp in enumerate(emps):
                table.insertRow(i)
                table.setItem(i, 0, QTableWidgetItem(emp.ten_nv))
                role_item = QTableWidgetItem(emp.chuc_vu or "")
                role_item.setForeground(QColor(ROLE_COLOR.get(emp.chuc_vu, "#A1A1AA")))
                table.setItem(i, 1, role_item)
                table.setItem(i, 2, QTableWidgetItem("— ca"))
                luong = int(emp.luong_co_ban or 0)
                table.setItem(i, 3, QTableWidgetItem(f"{luong:,} đ".replace(",", ".")))
                table.setItem(i, 4, QTableWidgetItem("Đang tính..."))
        finally:
            session.close()

        lay.addWidget(table)
        lay.addWidget(QLabel(
            "<i style='color:#A1A1AA;'>* Module chấm công & tính lương đang hoàn thiện liên kết Database.</i>"
        ))
        return w