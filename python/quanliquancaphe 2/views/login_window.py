from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Qt

from controllers.auth_controller import authenticate_user

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Đăng Nhập Hệ Thống")
        self.setFixedSize(350, 250)
        self.user_data  = None   # NhanVien object
        self.ma_phien   = None   # ID PhienLamViec vừa tạo (dùng để check-out khi logout)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>TÊN ĐĂNG NHẬP</b>"))
        self.txt_username = QLineEdit()
        layout.addWidget(self.txt_username)

        layout.addWidget(QLabel("<b>MẬT KHẨU</b>"))
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.txt_password)

        self.btn_login = QPushButton("ĐĂNG NHẬP")
        self.btn_login.setFixedHeight(45)
        self.btn_login.setStyleSheet("background-color: #2980B9; color: white; font-weight: bold;")
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)

        self.btn_forgot = QPushButton("❓ Quên mật khẩu")
        self.btn_forgot.setStyleSheet("background: none; color: #3498DB; border: none; text-decoration: underline;")
        self.btn_forgot.clicked.connect(self.forgot_password)
        layout.addWidget(self.btn_forgot)

        # Enter trong ô mật khẩu cũng kích hoạt đăng nhập
        self.txt_password.returnPressed.connect(self.handle_login)

    def handle_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        result = authenticate_user(username, password)
        if result:
            self.user_data = result["user"]
            self.ma_phien  = result["ma_phien"]
            self.accept()
        else:
            QMessageBox.warning(self, "Thất bại", "Sai tài khoản hoặc mật khẩu!")

    def forgot_password(self):
        from PySide6.QtWidgets import QInputDialog
        username, ok = QInputDialog.getText(
            self, "Quên Mật Khẩu",
            "Nhập tên đăng nhập của bạn:",
            QLineEdit.Normal, ""
        )
        if not ok or not username.strip():
            return

        username = username.strip()

        from database.db_config import get_session
        from database.models import NhanVien
        session = get_session()
        try:
            emp = session.query(NhanVien).filter_by(ten_dang_nhap=username).first()
            if not emp:
                QMessageBox.warning(self, "Không tìm thấy",
                                    f"Tên đăng nhập '{username}' không tồn tại.")
                return
            if not emp.email:
                QMessageBox.warning(
                    self, "Chưa có email",
                    f"Tài khoản '{username}' chưa được đăng ký email.\n\n"
                    "Vui lòng liên hệ Admin để được cấp lại mật khẩu."
                )
                return

            from utils.email_helper import gen_password, send_reset_password
            new_pw = gen_password(8)

            # Che bớt email để bảo mật hiển thị: ab***@gmail.com
            email = emp.email
            at    = email.index("@")
            shown = email[:2] + "***" + email[at:]

            confirm = QMessageBox.question(
                self, "Xác nhận",
                f"Hệ thống sẽ gửi mật khẩu mới đến:\n📧 {shown}\n\nTiếp tục?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

            ok_send, err = send_reset_password(
                emp.email, emp.ten_nv, emp.ten_dang_nhap, new_pw
            )
            if not ok_send:
                QMessageBox.critical(self, "Gửi email thất bại", err)
                return

            # Chỉ lưu MK mới khi gửi email thành công
            emp.mat_khau = new_pw
            session.commit()

            QMessageBox.information(
                self, "✅ Đã gửi",
                f"Mật khẩu mới đã được gửi đến {shown}\n\n"
                "Vui lòng kiểm tra hộp thư và đăng nhập bằng mật khẩu mới."
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            session.close()