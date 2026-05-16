"""
views/report_window.py
Báo cáo kinh doanh có bộ lọc ngày và biểu đồ doanh thu 7 ngày.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDateEdit, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import QSizePolicy

from controllers.report_controller import get_revenue_summary, get_daily_revenue


# ── Widget vẽ biểu đồ cột đơn giản (không cần thư viện ngoài) ──────────────
class BarChartWidget(QFrame):
    def __init__(self, data: list[dict], parent=None):
        """data: list of {'ngay': str, 'doanh_thu': float}"""
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(160)
        self.setStyleSheet("background-color: #1A1A24; border-radius: 10px;")

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 10, 10, 20, 40
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        max_val = max(d['doanh_thu'] for d in self.data) or 1
        n       = len(self.data)
        bar_w   = max(8, chart_w // n - 8)

        for i, d in enumerate(self.data):
            bar_h  = int(chart_h * d['doanh_thu'] / max_val)
            x      = pad_l + i * (chart_w // n) + (chart_w // n - bar_w) // 2
            y      = pad_t + chart_h - bar_h

            # Thanh cột
            color = QColor("#3498DB") if d['doanh_thu'] > 0 else QColor("#3E3E55")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, 4, 4)

            # Nhãn ngày
            painter.setPen(QPen(QColor("#A1A1AA")))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(x - 2, h - pad_b + 15, bar_w + 4, 20, Qt.AlignCenter, d['ngay'])

            # Giá trị trên đầu cột
            if d['doanh_thu'] > 0:
                val_str = f"{int(d['doanh_thu'] / 1000)}k"
                painter.setPen(QPen(QColor("#2ECC71")))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(x - 4, y - 14, bar_w + 8, 14, Qt.AlignCenter, val_str)

        painter.end()


# ── Dialog Báo cáo ──────────────────────────────────────────────────────────
class ReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Báo Cáo Hoạt Động Kinh Doanh")
        self.resize(560, 680)
        self.setStyleSheet("background-color: #1E1E2E; color: white;")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Tiêu đề ─────────────────────────────────────────────
        title = QLabel("<b>📊 KẾT QUẢ KINH DOANH</b>")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; color: #F1C40F; margin-bottom: 5px;")
        layout.addWidget(title)

        # ── Bộ lọc ngày ─────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame { background-color: #2D2D3F; border-radius: 10px; border: 1px solid #3E3E55; }"
        )
        filter_lay = QHBoxLayout(filter_frame)
        filter_lay.setContentsMargins(15, 10, 15, 10)

        lbl_from = QLabel("Từ ngày:")
        lbl_from.setStyleSheet("border: none; color: #A1A1AA; font-size: 13px;")
        self.de_from = QDateEdit()
        self.de_from.setCalendarPopup(True)
        self.de_from.setDate(QDate.currentDate().addDays(-30))
        self.de_from.setDisplayFormat("dd/MM/yyyy")
        self.de_from.setStyleSheet(
            "background-color: #1A1A24; border: 1px solid #3E3E55; border-radius: 6px;"
            " padding: 5px; color: white;"
        )

        lbl_to = QLabel("Đến ngày:")
        lbl_to.setStyleSheet("border: none; color: #A1A1AA; font-size: 13px;")
        self.de_to = QDateEdit()
        self.de_to.setCalendarPopup(True)
        self.de_to.setDate(QDate.currentDate())
        self.de_to.setDisplayFormat("dd/MM/yyyy")
        self.de_to.setStyleSheet(
            "background-color: #1A1A24; border: 1px solid #3E3E55; border-radius: 6px;"
            " padding: 5px; color: white;"
        )

        btn_filter = QPushButton("🔍 Xem báo cáo")
        btn_filter.setStyleSheet(
            "background-color: #2980B9; color: white; font-weight: bold;"
            " padding: 7px 14px; border-radius: 6px; border: none;"
        )
        btn_filter.clicked.connect(self._refresh)

        btn_today = QPushButton("Hôm nay")
        btn_today.setStyleSheet(
            "background-color: #27AE60; color: white; font-weight: bold;"
            " padding: 7px 12px; border-radius: 6px; border: none;"
        )
        btn_today.clicked.connect(self._set_today)

        btn_month = QPushButton("Tháng này")
        btn_month.setStyleSheet(
            "background-color: #8E44AD; color: white; font-weight: bold;"
            " padding: 7px 12px; border-radius: 6px; border: none;"
        )
        btn_month.clicked.connect(self._set_month)

        filter_lay.addWidget(lbl_from)
        filter_lay.addWidget(self.de_from)
        filter_lay.addWidget(lbl_to)
        filter_lay.addWidget(self.de_to)
        filter_lay.addWidget(btn_today)
        filter_lay.addWidget(btn_month)
        filter_lay.addWidget(btn_filter)
        layout.addWidget(filter_frame)

        # ── Khu vực số liệu (có thể scroll) ─────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.content_lay = QVBoxLayout(self.content)
        self.content_lay.setSpacing(10)
        scroll.setWidget(self.content)
        layout.addWidget(scroll)

        # ── Nút đóng ─────────────────────────────────────────────
        close_btn = QPushButton("Đóng Báo Cáo")
        close_btn.setMinimumHeight(42)
        close_btn.setStyleSheet(
            "background-color: #34495E; font-weight: bold; font-size: 15px; border-radius: 10px;"
        )
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._refresh()

    # ── Helpers bộ lọc nhanh ────────────────────────────────────
    def _set_today(self):
        today = QDate.currentDate()
        self.de_from.setDate(today)
        self.de_to.setDate(today)
        self._refresh()

    def _set_month(self):
        today = QDate.currentDate()
        self.de_from.setDate(QDate(today.year(), today.month(), 1))
        self.de_to.setDate(today)
        self._refresh()

    # ── Vẽ lại nội dung ─────────────────────────────────────────
    def _refresh(self):
        from datetime import datetime

        # Xóa nội dung cũ
        while self.content_lay.count():
            item = self.content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Lấy khoảng ngày
        qd_from = self.de_from.date()
        qd_to   = self.de_to.date()
        dt_from = datetime(qd_from.year(), qd_from.month(), qd_from.day(), 0,  0,  0)
        dt_to   = datetime(qd_to.year(),   qd_to.month(),   qd_to.day(),   23, 59, 59)

        data = get_revenue_summary(dt_from, dt_to)

        def _block(label_text, value_text, color, is_main=False):
            frame = QFrame()
            frame.setStyleSheet(
                "QFrame { background-color: #2D2D3F; border-radius: 12px;"
                " border: 1px solid #3E3E55; }"
            )
            vb = QVBoxLayout(frame)
            vb.setSpacing(6)
            vb.setContentsMargins(15, 18, 15, 18)
            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size: 13px; color: #A1A1AA; font-weight: bold; border: none;")
            val = QLabel(value_text)
            val.setAlignment(Qt.AlignCenter)
            fs = "34px" if is_main else "22px"
            val.setStyleSheet(f"font-size: {fs}; font-weight: 900; color: {color}; border: none;")
            vb.addWidget(lbl)
            vb.addWidget(val)
            return frame

        # Dòng 1
        row1 = QHBoxLayout()
        row1.addWidget(_block("TỔNG SỐ ĐƠN",
                               f"{data['total_orders']} đơn", "#3498DB"))
        row1.addWidget(_block("DOANH THU",
                               f"{data['total_revenue']:,.0f} đ", "#2ECC71"))
        self.content_lay.addLayout(row1)

        # Dòng 2
        row2 = QHBoxLayout()
        row2.addWidget(_block("CHI PHÍ VỐN",
                               f"-{data['total_cost']:,.0f} đ", "#E67E22"))
        row2.addWidget(_block("THUẾ (10%)",
                               f"-{data['total_tax']:,.0f} đ", "#E74C3C"))
        self.content_lay.addLayout(row2)

        # Lợi nhuận
        self.content_lay.addWidget(
            _block("LỢI NHUẬN RÒNG (BỎ TÚI)",
                   f"{data['net_profit']:,.0f} VNĐ", "#1ABC9C", is_main=True)
        )

        # ── Biểu đồ 7 ngày ──────────────────────────────────────
        chart_title = QLabel("📈 DOANH THU 7 NGÀY GẦN NHẤT")
        chart_title.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #A1A1AA; margin-top: 6px;"
        )
        self.content_lay.addWidget(chart_title)

        chart_data = get_daily_revenue(7)
        chart = BarChartWidget(chart_data)
        chart.setMinimumHeight(160)
        self.content_lay.addWidget(chart)

        self.content_lay.addStretch()