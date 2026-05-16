import sys
from PySide6.QtWidgets import QApplication
from views.login_window import LoginDialog
from views.main_window import POSWindow
from database.db_config import init_db_and_seed, get_session
from database.models import NhanVien
from utils.session_manager import get_valid_session, save_session

def main():
    app = QApplication(sys.argv)
    init_db_and_seed()

    # Vòng lặp vô tận để xử lý chu kỳ Đăng nhập -> Bán hàng -> Đăng xuất
    while True:
        db = get_session()
        current_user = None

        # 1. KIỂM TRA PHIÊN LÀM VIỆC (Có bị quá 60 phút chưa?)
        ma_phien = None
        saved_user_id = get_valid_session()
        if saved_user_id:
            current_user = db.get(NhanVien, saved_user_id)
            # Tìm lại PhienLamViec đang hoạt động của user này
            if current_user:
                from database.models import PhienLamViec
                phien_cu = (db.query(PhienLamViec)
                            .filter_by(ma_nv=current_user.id, dang_hoat_dong=True)
                            .order_by(PhienLamViec.thoi_gian_dang_nhap.desc())
                            .first())
                if phien_cu:
                    ma_phien = phien_cu.id

        # 2. NẾU KHÔNG CÓ PHIÊN -> BẮT ĐĂNG NHẬP
        if not current_user:
            login = LoginDialog()
            if login.exec() == LoginDialog.Accepted:
                current_user = login.user_data
                ma_phien     = login.ma_phien   # ← FIX: lấy ma_phien từ login
            else:
                db.close()
                break # Bấm dấu X tắt form login thì tắt luôn tool

        db.close()

        # 3. VÀO MÀN HÌNH CHÍNH
        if current_user:
            window = POSWindow(current_user=current_user, ma_phien=ma_phien)
            window.show()
            app.exec() # Chặn code ở đây, chờ đến khi POSWindow đóng lại

            # 4. KIỂM TRA LÝ DO ĐÓNG CỬA SỔ
            if getattr(window, 'is_logged_out', False):
                # Nếu do bấm Đăng xuất -> Vòng lặp chạy lại -> Hiện Login
                continue 
            else:
                # Nếu do bấm X để tắt tool -> Lưu thời gian hiện tại vào Session -> Tắt app
                save_session(current_user.id)
                break

if __name__ == "__main__":
    main()