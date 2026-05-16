from database.db_config import get_session
from database.models import NguyenLieu
from datetime import date

def get_inventory_status():
    """Lấy danh sách tồn kho và TỰ ĐỘNG RESET đồ dùng trong ngày"""
    session = get_session()
    today = date.today()
    try:
        ingredients = session.query(NguyenLieu).all()
        
        data = []
        for item in ingredients:
            # LOGIC ĂN TIỀN LÀ Ở ĐÂY: Reset đồ tươi sống khi qua ngày mới
            if item.loai_nl == "Trong ngày" and item.ngay_cap_nhat != today:
                item.so_luong_ton = 0.0
                item.ngay_cap_nhat = today
                session.add(item)
            
            data.append({
                'id': item.id,
                'name': item.ten_nl,
                'stock': item.so_luong_ton,
                'unit': item.don_vi_tinh,
                'type': item.loai_nl
            })
            
        session.commit() # Lưu lại việc reset (nếu có)
        return data
    except Exception as e:
        print(f"Lỗi truy xuất kho: {e}")
        return []
    finally:
        session.close()