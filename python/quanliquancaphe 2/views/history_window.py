from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QLabel, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from database.db_config import get_session
from database.models import HoaDon

# ========================================================
# 1. TAB CHI TIẾT HÓA ĐƠN (Popup hiện ra khi nhấp đúp)
# ========================================================
class BillDetailDialog(QDialog):
    def __init__(self, order_id, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.setWindowTitle(f"Chi Tiết Hóa Đơn - HD{order_id:04d}")
        self.resize(500, 550)
        self.setStyleSheet("background-color: #1E1E2E; color: white;")

        layout = QVBoxLayout(self)

        self.lbl_title = QLabel(f"<b>🧾 CHI TIẾT HÓA ĐƠN HD{order_id:04d}</b>")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 20px; color: #F1C40F; margin-bottom: 5px;")
        layout.addWidget(self.lbl_title)

        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet("font-size: 14px; color: #BDC3C7; margin-bottom: 15px;")
        layout.addWidget(self.lbl_info)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tên Món", "SL", "Đơn Giá", "Thành Tiền"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #2D2D3F; border: none; border-radius: 8px; color: white; font-size: 13px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #3E3E55; }
            QHeaderView::section { background-color: #1A1A24; color: #A1A1AA; padding: 8px; border: none; font-weight: bold; }
        """)
        self.table.setColumnWidth(1, 40)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 90)
        layout.addWidget(self.table)

        self.lbl_total = QLabel()
        self.lbl_total.setAlignment(Qt.AlignRight)
        self.lbl_total.setStyleSheet("font-size: 22px; font-weight: bold; color: #2ECC71; margin-top: 10px;")
        layout.addWidget(self.lbl_total)

        btn_close = QPushButton("Đóng Chi Tiết")
        btn_close.setMinimumHeight(45)
        btn_close.setStyleSheet("background-color: #E74C3C; font-weight: bold; border-radius: 8px; font-size: 14px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.load_detail()

    def load_detail(self):
        session = get_session()
        try:
            order = session.query(HoaDon).filter(HoaDon.id == self.order_id).first()
            if not order:
                return

            thoi_gian = (
                order.thoi_gian.strftime("%H:%M - %d/%m/%Y")
                if order.thoi_gian else "Không rõ"
            )

            # ── FIX: Lấy tên nhân viên qua PhienLamViec → NhanVien ──
            thu_ngan = "Hệ thống"
            try:
                if order.phien_lam_viec and order.phien_lam_viec.nhan_vien:
                    thu_ngan = order.phien_lam_viec.nhan_vien.ten_nv
            except Exception:
                pass

            self.lbl_info.setText(
                f"🕒 Thời gian: {thoi_gian}<br>👤 Thu ngân: {thu_ngan}"
            )
            self.lbl_total.setText(f"TỔNG CỘNG: {order.thanh_tien:,.0f} Đ")

            if order.chi_tiet:
                self.table.setRowCount(len(order.chi_tiet))
                for i, ct in enumerate(order.chi_tiet):
                    ten = (
                        ct.san_pham.ten_sp
                        if ct.san_pham else getattr(ct, 'ten_sp', "Món ăn")
                    )
                    sl        = getattr(ct, 'so_luong', 1)
                    gia       = getattr(ct, 'don_gia', 0)
                    thanh_tien = getattr(ct, 'thanh_tien', sl * gia)

                    self.table.setItem(i, 0, QTableWidgetItem(ten))
                    self.table.setItem(i, 1, QTableWidgetItem(str(sl)))
                    self.table.setItem(i, 2, QTableWidgetItem(f"{gia:,.0f}"))
                    self.table.setItem(i, 3, QTableWidgetItem(f"{thanh_tien:,.0f}"))
            else:
                self.table.setRowCount(1)
                item = QTableWidgetItem("Hóa đơn này chỉ có tổng tiền (Không lưu chi tiết món)")
                item.setForeground(QColor("#E74C3C"))
                self.table.setItem(0, 0, item)

        except Exception as e:
            print(f"Lỗi tải chi tiết: {e}")
        finally:
            session.close()


# ========================================================
# 2. CỬA SỔ LỊCH SỬ TỔNG QUÁT
# ========================================================
class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lịch Sử Giao Dịch Gần Đây")
        self.resize(780, 520)
        self.setStyleSheet("background-color: #1E1E2E; color: white;")

        layout = QVBoxLayout(self)

        title = QLabel(
            "<b>📜 LỊCH SỬ 50 GIAO DỊCH GẦN NHẤT</b><br>"
            "<span style='font-size: 13px; color: #BDC3C7;'>"
            "(💡 Mẹo: Nhấp đúp chuột vào một hóa đơn bất kỳ để xem chi tiết các món)"
            "</span>"
        )
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; color: #3498DB; margin-bottom: 10px;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Mã Hóa Đơn", "Thời Gian", "Thu Ngân", "Tổng Tiền", "Trạng Thái"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #2D2D3F; border: none; border-radius: 10px; color: white; font-size: 13px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #3E3E55; }
            QTableWidget::item:selected { background-color: #3498DB; color: white; }
            QHeaderView::section { background-color: #1A1A24; color: #A1A1AA; padding: 10px; border: none; font-weight: bold; font-size: 13px; }
        """)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Làm mới")
        btn_refresh.setMinimumHeight(40)
        btn_refresh.setStyleSheet(
            "background-color: #2980B9; font-weight: bold; border-radius: 8px; font-size: 14px;"
        )
        btn_refresh.clicked.connect(self.load_data)

        close_btn = QPushButton("Đóng")
        close_btn.setMinimumHeight(40)
        close_btn.setStyleSheet(
            "background-color: #34495E; font-weight: bold; border-radius: 8px; font-size: 14px;"
        )
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.table.itemDoubleClicked.connect(self.show_bill_detail)
        self.load_data()

    def load_data(self):
        """Load lại 50 hóa đơn mới nhất — gọi được bất cứ lúc nào."""
        self.table.setRowCount(0)
        session = get_session()
        try:
            orders = (
                session.query(HoaDon)
                .order_by(HoaDon.id.desc())
                .limit(50)
                .all()
            )
            for i, order in enumerate(orders):
                self.table.insertRow(i)

                # Cột 0: Mã hóa đơn
                ma_hd_str = f"HD{order.id:04d}"
                item_ma = QTableWidgetItem(ma_hd_str)
                item_ma.setData(Qt.UserRole, order.id)
                item_ma.setForeground(QColor("#F1C40F"))
                font = item_ma.font(); font.setBold(True); item_ma.setFont(font)
                self.table.setItem(i, 0, item_ma)

                # Cột 1: Thời gian
                thoi_gian = (
                    order.thoi_gian.strftime("%H:%M - %d/%m/%Y")
                    if order.thoi_gian else "Không rõ"
                )
                self.table.setItem(i, 1, QTableWidgetItem(thoi_gian))

                # Cột 2: Thu ngân
                thu_ngan = "Hệ thống"
                try:
                    if order.phien_lam_viec and order.phien_lam_viec.nhan_vien:
                        thu_ngan = order.phien_lam_viec.nhan_vien.ten_nv
                except Exception:
                    pass
                self.table.setItem(i, 2, QTableWidgetItem(thu_ngan))

                # Cột 3: Tổng tiền
                tong_tien = f"{order.thanh_tien:,.0f} đ" if order.thanh_tien else "0 đ"
                item_tien = QTableWidgetItem(tong_tien)
                item_tien.setForeground(QColor("#2ECC71"))
                self.table.setItem(i, 3, item_tien)

                # Cột 4: Trạng thái
                tt = getattr(order, 'trang_thai', 'Đã thanh toán') or 'Đã thanh toán'
                item_tt = QTableWidgetItem(tt)
                if "Đã" in tt:
                    item_tt.setForeground(QColor("#2ECC71"))
                elif "Hủy" in tt:
                    item_tt.setForeground(QColor("#E74C3C"))
                else:
                    item_tt.setForeground(QColor("#F1C40F"))
                self.table.setItem(i, 4, item_tt)

        except Exception as e:
            import traceback; traceback.print_exc()
            # Hiện lỗi ngay trong bảng để dễ debug
            self.table.setRowCount(1)
            err_item = QTableWidgetItem(f"❌ Lỗi tải dữ liệu: {e}")
            err_item.setForeground(QColor("#E74C3C"))
            self.table.setItem(0, 0, err_item)
        finally:
            session.close()

    def show_bill_detail(self, item):
        row = item.row()
        order_id = self.table.item(row, 0).data(Qt.UserRole)
        if order_id:
            dialog = BillDetailDialog(order_id, self)
            dialog.exec()