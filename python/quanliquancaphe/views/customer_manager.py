"""
views/customer_manager.py
Sửa:
  • Lỗi không sửa được KH → dùng session riêng biệt, merge đúng cách
  • Xóa KH không mất → cascade delete đúng + dùng session.delete()
  • Thêm nút "Trừ điểm" riêng biệt
  • Enter trong ô tìm → thêm mới nếu không có kết quả
  • Bỏ ngày sinh
"""
from __future__ import annotations
import random, string
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFormLayout, QLineEdit, QComboBox,
    QAbstractItemView, QSpinBox, QDoubleSpinBox, QDateEdit,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from database.db_config import get_session
from database.models import KhachHang, Voucher, LichSuDiemKH

# ── Hạng thành viên ─────────────────────────────────────────────────────────
HANG_CONFIG = [
    ("Kim cương", 10_000_000, "#00BCD4"),
    ("Vàng",       5_000_000, "#F1C40F"),
    ("Bạc",        2_000_000, "#BDC3C7"),
    ("Đồng",               0, "#CD7F32"),
]

STYLE = """
QDialog,QWidget{background-color:#1E1E2E;color:white;}
QTabWidget::pane{border:none;}
QTabBar::tab{background:#2D2D3F;color:#A1A1AA;padding:10px 18px;
    border-radius:6px 6px 0 0;font-weight:bold;font-size:13px;}
QTabBar::tab:selected{background:#3498DB;color:white;}
QTabBar::tab:hover{background:#3E3E55;color:white;}
QTableWidget{background:#2D2D3F;border:none;border-radius:8px;
    gridline-color:#3E3E55;color:white;font-size:13px;}
QTableWidget::item{padding:7px;border-bottom:1px solid #3E3E55;}
QTableWidget::item:selected{background:#3498DB;}
QHeaderView::section{background:#1A1A24;color:#A1A1AA;
    padding:9px;border:none;font-weight:bold;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QDateEdit{
    background:#2D2D3F;border:1px solid #3E3E55;border-radius:6px;
    padding:6px 10px;color:white;font-size:13px;}
QLineEdit:focus{border-color:#3498DB;}
QComboBox::drop-down{border:none;}
QComboBox QAbstractItemView{background:#2D2D3F;color:white;
    selection-background-color:#3498DB;}
QScrollBar:vertical{background:#1A1A24;width:7px;border-radius:4px;}
QScrollBar::handle:vertical{background:#3E3E55;border-radius:4px;}
"""

def _btn(t, c, h=36):
    b = QPushButton(t); b.setMinimumHeight(h)
    b.setStyleSheet(
        f"background:{c};color:white;font-weight:bold;"
        f"border-radius:6px;font-size:12px;padding:0 10px;"
    )
    return b

def _lbl(t, c="white", s=13, bold=False):
    l = QLabel(t)
    l.setStyleSheet(f"color:{c};font-size:{s}px;" + ("font-weight:bold;" if bold else ""))
    return l

def _fl(t):
    l = QLabel(t); l.setStyleSheet("color:#A1A1AA;"); return l

def tinh_hang(chi_tieu: float) -> str:
    for h, n, _ in HANG_CONFIG:
        if chi_tieu >= n: return h
    return "Đồng"

def mau_hang(hang: str) -> str:
    for h, _, c in HANG_CONFIG:
        if h == hang: return c
    return "#CD7F32"

def gen_code(prefix="VC") -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ═══════════════════════════════════════════════════════════════════════════════
# FORM THÊM / SỬA KHÁCH HÀNG
# ═══════════════════════════════════════════════════════════════════════════════
class CustomerForm(QDialog):
    def __init__(self, kh_id=None, ten_mac_dinh="", parent=None):
        super().__init__(parent)
        self.kh_id = kh_id
        self.setWindowTitle("Thêm Khách Hàng" if not kh_id else "Sửa Thông Tin Khách Hàng")
        self.resize(400, 270)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24); root.setSpacing(12)

        form = QFormLayout(); form.setSpacing(10)
        self.txt_ten  = QLineEdit(); self.txt_ten.setPlaceholderText("Nguyễn Văn A")
        from utils.phone_validator import PhoneLineEdit
        self.txt_sdt  = PhoneLineEdit()
        self.txt_mail = QLineEdit(); self.txt_mail.setPlaceholderText("kh@email.com")
        self.txt_note = QLineEdit(); self.txt_note.setPlaceholderText("Ghi chú…")

        if ten_mac_dinh:
            self.txt_ten.setText(ten_mac_dinh)

        form.addRow(_fl("Họ tên *:"),      self.txt_ten)
        form.addRow(_fl("Số điện thoại:"), self.txt_sdt)
        form.addRow(_fl("Email:"),          self.txt_mail)
        form.addRow(_fl("Ghi chú:"),        self.txt_note)
        root.addLayout(form)

        btn = _btn("💾  Lưu", "#27AE60", 44)
        btn.clicked.connect(self._save)
        root.addWidget(btn)

        if kh_id:
            self._load()

    def _load(self):
        # ── FIX: mở session mới, đọc xong đóng ngay ──────────────
        s = get_session()
        try:
            kh = s.query(KhachHang).filter_by(id=self.kh_id).first()
            if not kh:
                return
            ten  = kh.ten_kh or ""
            sdt  = kh.so_dien_thoai or ""
            mail = kh.email or ""
            note = kh.ghi_chu or ""
        finally:
            s.close()

        self.txt_ten.setText(ten)
        self.txt_sdt.setText(sdt)
        self.txt_mail.setText(mail)
        self.txt_note.setText(note)

    def _save(self):
        ten  = self.txt_ten.text().strip()
        if not ten:
            QMessageBox.warning(self, "Thiếu", "Họ tên là bắt buộc!"); return

        if not self.txt_sdt.is_valid():
            QMessageBox.warning(self, "SĐT không hợp lệ",
                "Số điện thoại không hợp lệ!\n"
                "Phải gồm đúng 10 chữ số và đúng đầu số nhà mạng (03x, 05x, 07x, 08x, 09x).")
            self.txt_sdt.setFocus()
            return

        sdt  = self.txt_sdt.text().strip() or None
        mail = self.txt_mail.text().strip() or None
        note = self.txt_note.text().strip() or None

        # ── FIX: luôn dùng session mới, commit, đóng ─────────────
        s = get_session()
        try:
            if self.kh_id:
                # Fetch lại trong session này
                kh = s.query(KhachHang).filter_by(id=self.kh_id).first()
                if not kh:
                    QMessageBox.critical(self, "Lỗi", "Không tìm thấy khách hàng!"); return
            else:
                if sdt and s.query(KhachHang).filter_by(so_dien_thoai=sdt).first():
                    QMessageBox.warning(self, "Trùng SĐT", "Số điện thoại đã tồn tại!"); return
                kh = KhachHang()
                s.add(kh)

            kh.ten_kh        = ten
            kh.so_dien_thoai = sdt
            kh.email         = mail
            kh.ghi_chu       = note
            s.commit()
            self.accept()
        except Exception as e:
            s.rollback()
            QMessageBox.critical(self, "Lỗi DB", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG ĐIỂM: TÍCH hoặc TRỪ
# ═══════════════════════════════════════════════════════════════════════════════
class PointDialog(QDialog):
    """
    Dùng chung cho cả Tích điểm và Trừ điểm.
    mode = 'add' | 'deduct'
    """
    def __init__(self, kh_id: int, ten_kh: str, diem_hien: int,
                 mode: str = 'add', parent=None):
        super().__init__(parent)
        self.kh_id = kh_id
        self.mode  = mode
        title = "Tích Điểm" if mode == 'add' else "Trừ / Đổi Điểm"
        self.setWindowTitle(f"{title} — {ten_kh}")
        self.resize(360, 230)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24); root.setSpacing(12)

        color = "#2ECC71" if mode == 'add' else "#E67E22"
        icon  = "⭐ Tích điểm" if mode == 'add' else "🔄 Trừ/Đổi điểm"
        root.addWidget(_lbl(f"{icon}  |  Điểm hiện tại: <b>{diem_hien:,}</b>", color, 13, True))

        form = QFormLayout(); form.setSpacing(10)
        self.sp_diem = QSpinBox()
        self.sp_diem.setRange(1, 999_999)
        self.sp_diem.setValue(100)

        if mode == 'add':
            self.cb_loai = QComboBox()
            self.cb_loai.addItems(["Tích điểm", "Điều chỉnh tăng"])
            form.addRow(_fl("Loại:"),    self.cb_loai)
        else:
            self.cb_loai = QComboBox()
            self.cb_loai.addItems(["Đổi điểm lấy quà", "Trừ điểm phạt", "Điều chỉnh giảm"])
            form.addRow(_fl("Lý do:"),   self.cb_loai)

        form.addRow(_fl("Số điểm:"),  self.sp_diem)
        self.txt_ly = QLineEdit(); self.txt_ly.setPlaceholderText("Ghi chú thêm…")
        form.addRow(_fl("Ghi chú:"),  self.txt_ly)
        root.addLayout(form)

        btn_color = "#27AE60" if mode == 'add' else "#E67E22"
        btn_text  = "✅ Cộng điểm" if mode == 'add' else "➖ Trừ điểm"
        btn = _btn(btn_text, btn_color, 44)
        btn.clicked.connect(self._save)
        root.addWidget(btn)

    def _save(self):
        diem = self.sp_diem.value()
        loai = self.cb_loai.currentText()
        ly   = self.txt_ly.text().strip() or loai

        # Tính delta: cộng hay trừ
        if self.mode == 'add':
            delta = diem
            loai_log = "Tích điểm"
        else:
            delta = -diem
            loai_log = "Đổi điểm"

        s = get_session()
        try:
            kh = s.query(KhachHang).filter_by(id=self.kh_id).first()
            if not kh:
                QMessageBox.critical(self, "Lỗi", "Không tìm thấy khách hàng!"); return

            new_diem = max(0, (kh.diem_tich_luy or 0) + delta)

            if self.mode == 'deduct' and new_diem == 0 and diem > (kh.diem_tich_luy or 0):
                QMessageBox.warning(
                    self, "Không đủ điểm",
                    f"Khách chỉ có {kh.diem_tich_luy or 0} điểm, không đủ để trừ {diem}!"
                )
                return

            kh.diem_tich_luy    = new_diem
            kh.hang_thanh_vien  = tinh_hang(kh.tong_chi_tieu or 0)

            s.add(LichSuDiemKH(
                ma_kh=self.kh_id,
                loai=loai_log,
                so_diem=delta,
                mo_ta=f"{loai}: {ly}"
            ))
            s.commit()
            self.accept()
        except Exception as e:
            s.rollback()
            QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG PHÁT VOUCHER
# ═══════════════════════════════════════════════════════════════════════════════
class IssueVoucherDialog(QDialog):
    def __init__(self, kh_id: int, ten_kh: str, parent=None):
        super().__init__(parent)
        self.kh_id = kh_id
        self.setWindowTitle(f"Phát Voucher — {ten_kh}")
        self.resize(400, 340); self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24); root.setSpacing(12)

        form = QFormLayout(); form.setSpacing(10)
        self.txt_ten = QLineEdit("Voucher tri ân")
        self.cb_loai = QComboBox(); self.cb_loai.addItems(["TienMat", "PhanTram"])
        self.sp_gt   = QDoubleSpinBox()
        self.sp_gt.setRange(0, 10_000_000); self.sp_gt.setValue(50_000)
        self.sp_max  = QDoubleSpinBox()
        self.sp_max.setRange(0, 5_000_000); self.sp_max.setSpecialValueText("Không giới hạn")
        self.sp_dk   = QDoubleSpinBox()
        self.sp_dk.setRange(0, 10_000_000); self.sp_dk.setSpecialValueText("Không yêu cầu")
        self.de_het  = QDateEdit(QDate.currentDate().addDays(30))
        self.de_het.setCalendarPopup(True); self.de_het.setDisplayFormat("dd/MM/yyyy")

        form.addRow(_fl("Tên voucher:"),       self.txt_ten)
        form.addRow(_fl("Loại giảm:"),         self.cb_loai)
        form.addRow(_fl("Giá trị giảm:"),      self.sp_gt)
        form.addRow(_fl("Giảm tối đa (đ):"),   self.sp_max)
        form.addRow(_fl("Đơn tối thiểu (đ):"), self.sp_dk)
        form.addRow(_fl("Hết hạn:"),           self.de_het)
        root.addLayout(form)

        btn = _btn("🎁  Phát Voucher", "#8E44AD", 44)
        btn.clicked.connect(self._issue)
        root.addWidget(btn)

    def _issue(self):
        qd  = self.de_het.date()
        het = date(qd.year(), qd.month(), qd.day())
        s = get_session()
        try:
            code = gen_code()
            v = Voucher(
                ma_kh=self.kh_id, ma_code=code,
                ten_voucher=self.txt_ten.text().strip() or "Voucher",
                loai_giam=self.cb_loai.currentText(),
                gia_tri_giam=self.sp_gt.value(),
                toi_da_giam=self.sp_max.value() or None,
                dieu_kien_toi_thieu=self.sp_dk.value(),
                ngay_het_han=het,
            )
            s.add(v); s.commit()
            QMessageBox.information(self, "Thành công", f"✅ Đã phát voucher!\nMã: {code}")
            self.accept()
        except Exception as e:
            s.rollback(); QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG LỊCH SỬ ĐIỂM
# ═══════════════════════════════════════════════════════════════════════════════
class PointHistoryDialog(QDialog):
    def __init__(self, kh_id: int, ten_kh: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Lịch Sử Điểm — {ten_kh}")
        self.resize(600, 400); self.setStyleSheet(STYLE)

        root = QVBoxLayout(self); root.setContentsMargins(16, 16, 16, 16)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Thời Gian", "Loại", "Số Điểm", "Ghi Chú"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table)

        btn = _btn("Đóng", "#34495E", 38); btn.clicked.connect(self.accept)
        root.addWidget(btn)

        self._load(kh_id)

    def _load(self, kh_id):
        s = get_session()
        try:
            logs = (s.query(LichSuDiemKH)
                    .filter_by(ma_kh=kh_id)
                    .order_by(LichSuDiemKH.thoi_gian.desc())
                    .limit(200).all())
            for i, log in enumerate(logs):
                self.table.insertRow(i)
                tg = log.thoi_gian.strftime("%H:%M  %d/%m/%Y") if log.thoi_gian else "—"
                self.table.setItem(i, 0, QTableWidgetItem(tg))
                self.table.setItem(i, 1, QTableWidgetItem(log.loai or ""))

                diem_str = f"+{log.so_diem}" if (log.so_diem or 0) > 0 else str(log.so_diem or 0)
                di = QTableWidgetItem(diem_str)
                di.setForeground(QColor("#2ECC71" if (log.so_diem or 0) > 0 else "#E74C3C"))
                self.table.setItem(i, 2, di)
                self.table.setItem(i, 3, QTableWidgetItem(log.mo_ta or ""))
        finally:
            s.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DIALOG CHÍNH
# ═══════════════════════════════════════════════════════════════════════════════
class CustomerManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("👥 Quản Lý Khách Hàng Thành Viên")
        self.resize(1080, 660); self.setStyleSheet(STYLE)

        root = QVBoxLayout(self); root.setContentsMargins(10, 10, 10, 10)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._make_list_tab(),    "📋  Danh Sách")
        self.tabs.addTab(self._make_voucher_tab(), "🎁  Voucher")
        root.addWidget(self.tabs)

        btn = _btn("Đóng", "#34495E", 40); btn.clicked.connect(self.accept)
        root.addWidget(btn)

        self.tabs.currentChanged.connect(self._on_tab)

    def showEvent(self, e):
        super().showEvent(e); self._load_kh()

    # ── Tab Danh sách ────────────────────────────────────────────
    def _make_list_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setSpacing(8)

        # Toolbar
        bar = QHBoxLayout()
        bar.addWidget(_lbl("THÀNH VIÊN", "#3498DB", 16, True)); bar.addStretch()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍  Tên / SĐT  (Enter = thêm mới nếu chưa có)")
        self.txt_search.setFixedWidth(290)
        self.txt_search.textChanged.connect(lambda t: self._load_kh(t))
        self.txt_search.returnPressed.connect(self._search_or_add)
        bar.addWidget(self.txt_search)

        self.btn_add     = _btn("➕ Thêm",     "#27AE60")
        self.btn_edit    = _btn("✏️ Sửa",      "#2980B9")
        self.btn_add_pt  = _btn("⭐ Cộng điểm","#27AE60")
        self.btn_deduct  = _btn("➖ Trừ điểm", "#E67E22")   # ← MỚI
        self.btn_vc      = _btn("🎁 Voucher",  "#8E44AD")
        self.btn_hist    = _btn("📋 Lịch sử",  "#16A085")
        self.btn_del     = _btn("🗑 Xóa",      "#C0392B")

        for b in [self.btn_add, self.btn_edit, self.btn_add_pt,
                  self.btn_deduct, self.btn_vc, self.btn_hist, self.btn_del]:
            bar.addWidget(b)
        v.addLayout(bar)

        # Bảng
        self.tbl_kh = QTableWidget(0, 7)
        self.tbl_kh.setHorizontalHeaderLabels(
            ["ID", "Họ Tên", "SĐT", "Hạng", "Điểm", "Tổng Chi Tiêu", "Ngày Tham Gia"])
        hh = self.tbl_kh.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed); self.tbl_kh.setColumnWidth(0, 40)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in range(2, 7): hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tbl_kh.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_kh.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_kh.verticalHeader().setVisible(False)
        self.tbl_kh.itemDoubleClicked.connect(lambda _: self._edit_kh())
        v.addWidget(self.tbl_kh)

        # Kết nối
        self.btn_add.clicked.connect(self._add_kh)
        self.btn_edit.clicked.connect(self._edit_kh)
        self.btn_add_pt.clicked.connect(lambda: self._open_points('add'))
        self.btn_deduct.clicked.connect(lambda: self._open_points('deduct'))
        self.btn_vc.clicked.connect(self._issue_voucher)
        self.btn_hist.clicked.connect(self._show_history)
        self.btn_del.clicked.connect(self._del_kh)
        return w

    def _search_or_add(self):
        kw = self.txt_search.text().strip()
        if self.tbl_kh.rowCount() > 0:
            self.tbl_kh.selectRow(0)
        else:
            if CustomerForm(ten_mac_dinh=kw, parent=self).exec():
                self.txt_search.clear()
                self._load_kh()

    def _load_kh(self, keyword=""):
        self.tbl_kh.setRowCount(0)
        s = get_session()
        try:
            q = s.query(KhachHang)
            if keyword:
                q = q.filter(
                    KhachHang.ten_kh.ilike(f"%{keyword}%") |
                    KhachHang.so_dien_thoai.ilike(f"%{keyword}%")
                )
            rows = []
            for kh in q.order_by(KhachHang.id.desc()).all():
                rows.append({
                    "id": kh.id, "ten": kh.ten_kh or "",
                    "sdt": kh.so_dien_thoai or "—",
                    "hang": kh.hang_thanh_vien or "Đồng",
                    "diem": kh.diem_tich_luy or 0,
                    "chi_tieu": kh.tong_chi_tieu or 0,
                    "ngay": kh.ngay_tham_gia.strftime("%d/%m/%Y") if kh.ngay_tham_gia else "—",
                })
        finally:
            s.close()  # đóng session trước khi đổ vào UI

        for i, r in enumerate(rows):
            self.tbl_kh.insertRow(i)
            id_it = QTableWidgetItem(str(r["id"])); id_it.setData(Qt.UserRole, r["id"])
            self.tbl_kh.setItem(i, 0, id_it)
            self.tbl_kh.setItem(i, 1, QTableWidgetItem(r["ten"]))
            self.tbl_kh.setItem(i, 2, QTableWidgetItem(r["sdt"]))

            hi = QTableWidgetItem(f"⭐ {r['hang']}")
            hi.setForeground(QColor(mau_hang(r["hang"])))
            self.tbl_kh.setItem(i, 3, hi)

            di = QTableWidgetItem(f"{r['diem']:,} điểm")
            di.setForeground(QColor("#F1C40F"))
            self.tbl_kh.setItem(i, 4, di)

            ti = QTableWidgetItem(f"{int(r['chi_tieu']):,} đ")
            ti.setForeground(QColor("#2ECC71"))
            self.tbl_kh.setItem(i, 5, ti)

            self.tbl_kh.setItem(i, 6, QTableWidgetItem(r["ngay"]))

    def _sel_id(self):
        r = self.tbl_kh.currentRow()
        if r < 0:
            QMessageBox.information(self, "", "Hãy chọn một khách hàng!"); return None
        return self.tbl_kh.item(r, 0).data(Qt.UserRole)

    def _sel_ten(self):
        r = self.tbl_kh.currentRow()
        return self.tbl_kh.item(r, 1).text() if r >= 0 else ""

    def _sel_diem(self) -> int:
        r = self.tbl_kh.currentRow()
        if r < 0: return 0
        txt = self.tbl_kh.item(r, 4).text().replace(",", "").replace(" điểm", "").strip()
        try: return int(txt)
        except: return 0

    def _add_kh(self):
        if CustomerForm(parent=self).exec(): self._load_kh()

    def _edit_kh(self):
        kid = self._sel_id()
        if kid is None: return
        if CustomerForm(kh_id=kid, parent=self).exec():
            self._load_kh()

    def _open_points(self, mode: str):
        kid = self._sel_id()
        if kid is None: return
        if PointDialog(kid, self._sel_ten(), self._sel_diem(), mode, self).exec():
            self._load_kh()

    def _issue_voucher(self):
        kid = self._sel_id()
        if kid is None: return
        if IssueVoucherDialog(kid, self._sel_ten(), self).exec():
            self._load_vouchers()

    def _show_history(self):
        kid = self._sel_id()
        if kid is None: return
        PointHistoryDialog(kid, self._sel_ten(), self).exec()

    def _del_kh(self):
        kid = self._sel_id()
        if kid is None: return
        ten = self._sel_ten()
        r = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Xóa khách hàng <b>{ten}</b>?<br>"
            f"<span style='color:#E74C3C;font-size:12px;'>"
            f"Voucher và lịch sử điểm của khách sẽ bị xóa theo.</span>",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r != QMessageBox.Yes: return

        s = get_session()
        try:
            kh = s.query(KhachHang).filter_by(id=kid).first()
            if not kh:
                QMessageBox.warning(self, "Lỗi", "Không tìm thấy khách hàng!"); return

            # ── FIX: xóa thủ công các bảng liên quan trước ────────
            s.query(LichSuDiemKH).filter_by(ma_kh=kid).delete()
            s.query(Voucher).filter_by(ma_kh=kid).delete()
            s.delete(kh)
            s.commit()

            QMessageBox.information(self, "Đã xóa", f"Đã xóa khách hàng '{ten}'.")
        except Exception as e:
            s.rollback()
            QMessageBox.critical(self, "Lỗi", str(e))
        finally:
            s.close()

        self._load_kh()

    # ── Tab Voucher ──────────────────────────────────────────────
    def _make_voucher_tab(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setSpacing(8)
        bar = QHBoxLayout()
        bar.addWidget(_lbl("VOUCHER", "#8E44AD", 16, True)); bar.addStretch()
        btn_exp = _btn("❌ Hủy voucher", "#C0392B")
        btn_exp.clicked.connect(self._cancel_voucher)
        bar.addWidget(btn_exp); v.addLayout(bar)

        self.tbl_vc = QTableWidget(0, 7)
        self.tbl_vc.setHorizontalHeaderLabels(
            ["Mã", "Khách Hàng", "Tên Voucher", "Loại", "Giá Trị", "Hết Hạn", "Trạng Thái"])
        hh2 = self.tbl_vc.horizontalHeader()
        hh2.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(1, QHeaderView.Stretch)
        hh2.setSectionResizeMode(2, QHeaderView.Stretch)
        for c in range(3, 7): hh2.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tbl_vc.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_vc.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_vc.verticalHeader().setVisible(False)
        v.addWidget(self.tbl_vc)

        self._load_vouchers()
        return w

    def _load_vouchers(self):
        self.tbl_vc.setRowCount(0)
        s = get_session()
        try:
            rows = []
            for vc in s.query(Voucher).order_by(Voucher.id.desc()).limit(300).all():
                kh = s.query(KhachHang).filter_by(id=vc.ma_kh).first()
                rows.append({
                    "id": vc.id, "code": vc.ma_code,
                    "kh_ten": kh.ten_kh if kh else "?",
                    "ten": vc.ten_voucher or "",
                    "loai": vc.loai_giam or "",
                    "gt": vc.gia_tri_giam or 0,
                    "het": vc.ngay_het_han.strftime("%d/%m/%Y") if vc.ngay_het_han else "—",
                    "tt": vc.trang_thai or "Chưa dùng",
                })
        finally:
            s.close()

        for i, r in enumerate(rows):
            self.tbl_vc.insertRow(i)
            it = QTableWidgetItem(r["code"]); it.setData(Qt.UserRole, r["id"])
            it.setForeground(QColor("#F1C40F")); self.tbl_vc.setItem(i, 0, it)
            self.tbl_vc.setItem(i, 1, QTableWidgetItem(r["kh_ten"]))
            self.tbl_vc.setItem(i, 2, QTableWidgetItem(r["ten"]))
            self.tbl_vc.setItem(i, 3, QTableWidgetItem(r["loai"]))
            gt = f"{int(r['gt'])}%" if r["loai"] == "PhanTram" else f"{int(r['gt']):,}đ"
            self.tbl_vc.setItem(i, 4, QTableWidgetItem(gt))
            self.tbl_vc.setItem(i, 5, QTableWidgetItem(r["het"]))
            tt_it = QTableWidgetItem(r["tt"])
            tt_it.setForeground(QColor(
                {"Chưa dùng": "#2ECC71", "Đã dùng": "#A1A1AA", "Hết hạn": "#E74C3C"}.get(r["tt"], "white")
            ))
            self.tbl_vc.setItem(i, 6, tt_it)

    def _cancel_voucher(self):
        row = self.tbl_vc.currentRow()
        if row < 0:
            QMessageBox.information(self, "", "Hãy chọn voucher!"); return
        vc_id = self.tbl_vc.item(row, 0).data(Qt.UserRole)
        s = get_session()
        try:
            vc = s.query(Voucher).filter_by(id=vc_id).first()
            if vc: vc.trang_thai = "Hết hạn"; s.commit()
        finally: s.close()
        self._load_vouchers()

    def _on_tab(self, idx):
        if idx == 0: self._load_kh()
        elif idx == 1: self._load_vouchers()