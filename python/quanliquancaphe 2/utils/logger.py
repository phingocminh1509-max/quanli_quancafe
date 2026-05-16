import logging
import os

# Tự động tạo thư mục logs nếu chưa có
if not os.path.exists('logs'):
    os.makedirs('logs')

# Cấu hình chuẩn Form doanh nghiệp
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S %d/%m/%Y'
)

def log_info(message):
    """Ghi lại các hoạt động bình thường (Đăng nhập, chốt đơn)"""
    logging.info(message)
    print(f"[LOG] {message}") # In ra cả màn hình Terminal để bro dễ nhìn

def log_error(message):
    """Ghi lại các lỗi hoặc cảnh báo an ninh (Nhập sai pass, lỗi DB)"""
    logging.error(message)
    print(f"[ERROR] {message}")