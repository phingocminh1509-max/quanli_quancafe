"""
utils/email_helper.py
Gửi email qua Gmail SMTP (App Password).

HƯỚNG DẪN CẤU HÌNH LẦN ĐẦU:
  1. Vào https://myaccount.google.com/security
  2. Bật "Xác minh 2 bước" nếu chưa bật
  3. Vào https://myaccount.google.com/apppasswords
  4. Tạo App Password cho "Mail" → copy 16 ký tự
  5. Điền vào SENDER_EMAIL và SENDER_APP_PASSWORD bên dưới
"""

import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ══════════════════════════════════════════════════════
# ⚙️  CẤU HÌNH — chỉ cần sửa 2 dòng này
# ══════════════════════════════════════════════════════
SENDER_EMAIL        = "tektak1509@gmail.com"   # ← Gmail của quán
SENDER_APP_PASSWORD = "gjjp usup zcle aflh"          # ← App Password 16 ký tự
SHOP_NAME           = "Quán Cà Phê"
# ══════════════════════════════════════════════════════


def _send(to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Gửi 1 email HTML. Trả về (True, "") hoặc (False, lỗi)."""
    if not to_email or "@" not in to_email:
        return False, "Địa chỉ email không hợp lệ."
    if SENDER_APP_PASSWORD.startswith("xxxx"):
        return False, (
            "Chưa cấu hình email gửi đi.\n\n"
            "Mở file utils/email_helper.py và điền\n"
            "SENDER_EMAIL + SENDER_APP_PASSWORD."
        )
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SHOP_NAME} <{SENDER_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Xác thực Gmail thất bại.\n"
            "Kiểm tra lại SENDER_EMAIL và SENDER_APP_PASSWORD\n"
            "trong file utils/email_helper.py."
        )
    except Exception as e:
        return False, str(e)


def gen_password(length: int = 8) -> str:
    """Tạo mật khẩu ngẫu nhiên gồm chữ + số."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def send_reset_password(to_email: str, ten_nv: str,
                        ten_dang_nhap: str, new_password: str) -> tuple[bool, str]:
    """
    Gửi email chứa mật khẩu mới sau khi reset.
    Trả về (True, "") hoặc (False, thông báo lỗi).
    """
    subject = f"[{SHOP_NAME}] Mật khẩu mới của bạn"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;
                border:1px solid #ddd;border-radius:10px;overflow:hidden;">
      <div style="background:#2980B9;padding:24px;text-align:center;">
        <h2 style="color:white;margin:0;">☕ {SHOP_NAME}</h2>
      </div>
      <div style="padding:28px 32px;">
        <p style="font-size:15px;">Xin chào <b>{ten_nv}</b>,</p>
        <p style="font-size:14px;color:#555;">
          Mật khẩu tài khoản của bạn đã được đặt lại.
          Đây là thông tin đăng nhập mới:
        </p>
        <div style="background:#F4F6F8;border-radius:8px;padding:16px 20px;margin:16px 0;">
          <p style="margin:4px 0;font-size:14px;">
            👤 <b>Tên đăng nhập:</b> <code>{ten_dang_nhap}</code>
          </p>
          <p style="margin:4px 0;font-size:14px;">
            🔑 <b>Mật khẩu mới:</b>
            <span style="font-size:20px;font-weight:bold;
                         letter-spacing:3px;color:#E74C3C;">{new_password}</span>
          </p>
        </div>
        <p style="font-size:13px;color:#E67E22;">
          ⚠️ Vui lòng đăng nhập và đổi mật khẩu ngay sau đó!
        </p>
        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
        <p style="font-size:12px;color:#AAA;text-align:center;">
          Email tự động từ hệ thống {SHOP_NAME}. Vui lòng không trả lời email này.
        </p>
      </div>
    </div>
    """
    return _send(to_email, subject, html)


def send_change_password_confirm(to_email: str, ten_nv: str) -> tuple[bool, str]:
    """
    Gửi email xác nhận sau khi nhân viên tự đổi mật khẩu thành công.
    """
    from datetime import datetime
    subject = f"[{SHOP_NAME}] Mật khẩu đã được thay đổi"
    now_str = datetime.now().strftime("%H:%M %d/%m/%Y")
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;
                border:1px solid #ddd;border-radius:10px;overflow:hidden;">
      <div style="background:#27AE60;padding:24px;text-align:center;">
        <h2 style="color:white;margin:0;">☕ {SHOP_NAME}</h2>
      </div>
      <div style="padding:28px 32px;">
        <p style="font-size:15px;">Xin chào <b>{ten_nv}</b>,</p>
        <p style="font-size:14px;color:#555;">
          ✅ Mật khẩu tài khoản của bạn đã được thay đổi thành công lúc
          <b>{now_str}</b>.
        </p>
        <p style="font-size:13px;color:#E74C3C;">
          Nếu bạn không thực hiện thao tác này, hãy liên hệ Admin ngay lập tức!
        </p>
        <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
        <p style="font-size:12px;color:#AAA;text-align:center;">
          Email tự động từ hệ thống {SHOP_NAME}. Vui lòng không trả lời email này.
        </p>
      </div>
    </div>
    """
    return _send(to_email, subject, html)