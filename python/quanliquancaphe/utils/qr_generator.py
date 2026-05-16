import urllib.request
import urllib.parse
from PySide6.QtGui import QPixmap

def generate_vietqr_pixmap(amount, description):
    """
    Sử dụng API miễn phí của VietQR để tạo mã QR chuyển khoản.
    """
    # ================= CHỦ QUÁN ĐIỀN THÔNG TIN Ở ĐÂY =================
    # Xem danh sách mã BIN ngân hàng tại: https://api.vietqr.io/v2/banks
    BANK_BIN = "970422"       # Ví dụ: 970422 là MBBank, 970436 là Vietcombank
    ACCOUNT_NO = "031206007631" # Số tài khoản
    ACCOUNT_NAME = "VU LENH HUYNH" # Tên chủ tài khoản (Viết không dấu)
    # =================================================================

    # Xử lý chuỗi (bỏ dấu cách, ký tự đặc biệt để đưa lên Link URL an toàn)
    safe_desc = urllib.parse.quote(description)
    safe_name = urllib.parse.quote(ACCOUNT_NAME)

    # Cấu trúc link API chuẩn của VietQR
    url = f"https://img.vietqr.io/image/{BANK_BIN}-{ACCOUNT_NO}-compact2.png?amount={int(amount)}&addInfo={safe_desc}&accountName={safe_name}"

    try:
        # Tải ảnh trực tiếp từ API về thành dữ liệu nhị phân
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        image_data = response.read()

        # Chuyển dữ liệu nhị phân thành QPixmap để hiển thị lên Giao diện PySide6
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        return pixmap
    except Exception as e:
        print(f"Lỗi tải mã QR từ mạng: {e}")
        return None