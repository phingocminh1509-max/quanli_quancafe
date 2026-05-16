"""
utils/permissions.py
══════════════════════════════════════════════════════════════
Phân quyền tập trung — mọi chỗ trong app đều import từ đây.

Thứ tự quyền (cao → thấp):
  Admin > Quản lý > Thu ngân > Pha chế > Phục vụ
══════════════════════════════════════════════════════════════
"""

# Các chức vụ hợp lệ
ROLES = ["Admin", "Quản lý", "Thu ngân", "Pha chế", "Phục vụ"]

# Màu hiển thị theo chức vụ
ROLE_COLOR = {
    "Admin":    "#E74C3C",
    "Quản lý":  "#E67E22",
    "Thu ngân": "#3498DB",
    "Pha chế":  "#9B59B6",
    "Phục vụ":  "#27AE60",
}

# ── Bảng quyền ──────────────────────────────────────────────────────────────
# Mỗi quyền là set các chức vụ được phép
_PERMS: dict[str, set[str]] = {
    # Bán hàng (ai cũng làm được)
    "ban_hang":          {"Admin", "Quản lý", "Thu ngân", "Pha chế", "Phục vụ"},

    # Xem lịch sử hóa đơn
    "xem_lich_su":       {"Admin", "Quản lý", "Thu ngân"},

    # Xem / in báo cáo doanh thu
    "xem_bao_cao":       {"Admin", "Quản lý"},

    # Quản lý menu sản phẩm
    "quan_ly_menu":      {"Admin", "Quản lý"},

    # Quản lý kho (nếu có)
    "quan_ly_kho":       {"Admin", "Quản lý"},

    # Quản lý nhân viên & cài đặt hệ thống
    "quan_ly_nhan_su":   {"Admin"},
    "cai_dat_he_thong":  {"Admin"},

    # Xem phân ca (mọi người xem được ca của mình; Admin/QL sửa được)
    "xem_phan_ca":       {"Admin", "Quản lý", "Thu ngân", "Pha chế", "Phục vụ"},
    "sua_phan_ca":       {"Admin", "Quản lý"},

    # Phân công & điểm danh (chỉ Admin và Quản lý)
    "quan_ly_ca_lam":    {"Admin", "Quản lý"},

    # Khuyến mãi
    "xem_khuyen_mai":    {"Admin", "Quản lý", "Thu ngân"},
    "quan_ly_khuyen_mai":{"Admin", "Quản lý"},

    # Khách hàng thành viên
    "quan_ly_khach_hang":{"Admin", "Quản lý", "Thu ngân"},

    # Nhật ký hệ thống
    "xem_nhat_ky":       {"Admin"},
}


def co_quyen(chuc_vu: str, quyen: str) -> bool:
    """
    Kiểm tra chức vụ có quyền thực hiện hành động không.

    Ví dụ:
        co_quyen("Thu ngân", "ban_hang")    → True
        co_quyen("Phục vụ",  "xem_bao_cao") → False
    """
    return chuc_vu in _PERMS.get(quyen, set())


def yeu_cau_quyen(chuc_vu: str, quyen: str, parent=None) -> bool:
    """
    Kiểm tra và hiện thông báo nếu không đủ quyền.
    Trả về True nếu được phép, False kèm popup nếu không.
    """
    if co_quyen(chuc_vu, quyen):
        return True
    # Hiện cảnh báo nếu có parent widget
    if parent is not None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(
            parent,
            "Không đủ quyền",
            f"Chức vụ <b>{chuc_vu}</b> không được phép thực hiện thao tác này.<br>"
            f"Vui lòng liên hệ Admin."
        )
    return False