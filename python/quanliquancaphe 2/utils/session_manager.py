import json
import os
from datetime import datetime, timedelta

SESSION_FILE = "session.json"

def save_session(user_id):
    """Lưu ID user và thời gian đóng app vào file ẩn"""
    data = {
        "user_id": user_id,
        "last_active": datetime.now().isoformat()
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)

def get_valid_session(timeout_minutes=60):
    """Kiểm tra xem phiên còn hạn 60 phút không. Nếu còn trả về user_id"""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r") as f:
            data = json.load(f)
        last_active = datetime.fromisoformat(data["last_active"])
        
        # Nếu chưa quá 60 phút thì phiên còn hợp lệ
        if datetime.now() - last_active <= timedelta(minutes=timeout_minutes):
            return data["user_id"]
        else:
            return None
    except Exception:
        return None

def clear_session():
    """Xóa file phiên khi bấm Đăng xuất"""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)