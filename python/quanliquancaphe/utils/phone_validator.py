"""
utils/phone_validator.py
─────────────────────────────────────────────────────────────
Widget QLineEdit có validate SĐT Việt Nam real-time:
  • Viền đỏ + thông báo nhỏ khi sai
  • Viền xanh khi đúng
  • Trống = hợp lệ (không bắt buộc nhập)

Dùng:
    from utils.phone_validator import PhoneLineEdit
    self.txt_sdt = PhoneLineEdit()
    # Lấy giá trị + kiểm tra:
    if self.txt_sdt.is_valid():
        sdt = self.txt_sdt.text().strip()
"""

import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QLabel
from PySide6.QtCore import Qt, Signal


# ─── Đầu số hợp lệ tại Việt Nam ───────────────────────────────
_VALID_PREFIXES = (
    '032','033','034','035','036','037','038','039',  # Viettel
    '086','096','097','098',
    '070','076','077','078','079',                    # Mobifone
    '089','090','093',
    '056','058',                                      # Vietnamobile
    '052','058',
    '055','056','058',                                # Gmobile
    '059',
    '081','082','083','084','085',                    # Vinaphone
    '088','091','094',
)
_VALID_PREFIX_2 = ('03','05','07','08','09')          # Kiểm tra nhanh 2 ký tự


def validate_sdt(sdt: str) -> tuple[bool, str]:
    """
    Trả về (True, "") nếu hợp lệ hoặc trống.
    Trả về (False, thông báo lỗi) nếu sai.
    """
    sdt = sdt.strip()
    if not sdt:
        return True, ""   # Trống = không bắt buộc → hợp lệ

    digits = re.sub(r'\D', '', sdt)

    if len(digits) < 10:
        return False, f"Thiếu số — cần đủ 10 chữ số (hiện có {len(digits)})"
    if len(digits) > 10:
        return False, f"Thừa số — chỉ được 10 chữ số (hiện có {len(digits)})"
    if not digits.startswith('0'):
        return False, "Phải bắt đầu bằng số 0"
    if not any(digits.startswith(p) for p in _VALID_PREFIX_2):
        return False, "Đầu số không hợp lệ (03x, 05x, 07x, 08x, 09x)"

    return True, ""


# ─── Widget tích hợp validate real-time ───────────────────────
class PhoneLineEdit(QWidget):
    """
    Thay thế QLineEdit thông thường cho ô nhập SĐT.
    Có label lỗi nhỏ bên dưới, viền đổi màu real-time.
    """
    textChanged = Signal(str)

    _STYLE_NORMAL = (
        "QLineEdit { background:#252540; border:1px solid #333355;"
        " border-radius:6px; padding:6px 10px; color:#E8E8F0; font-size:13px; }"
        "QLineEdit:focus { border-color:#3498DB; }"
    )
    _STYLE_OK = (
        "QLineEdit { background:#252540; border:2px solid #27AE60;"
        " border-radius:6px; padding:6px 10px; color:#E8E8F0; font-size:13px; }"
    )
    _STYLE_ERR = (
        "QLineEdit { background:#2A1A1A; border:2px solid #E74C3C;"
        " border-radius:6px; padding:6px 10px; color:#E8E8F0; font-size:13px; }"
    )

    def __init__(self, placeholder="0901234567", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.setMaxLength(11)   # cho phép gõ tối đa 11 để báo lỗi "thừa"
        self._edit.setStyleSheet(self._STYLE_NORMAL)
        layout.addWidget(self._edit)

        self._lbl_err = QLabel("")
        self._lbl_err.setStyleSheet(
            "color:#E74C3C; font-size:11px; background:transparent; border:none;"
        )
        self._lbl_err.setWordWrap(True)
        self._lbl_err.hide()
        layout.addWidget(self._lbl_err)

        self._edit.textChanged.connect(self._on_changed)

    # ── Public API (giống QLineEdit) ──────────────────────────
    def text(self) -> str:
        return self._edit.text()

    def setText(self, txt: str):
        self._edit.setText(txt)

    def setPlaceholderText(self, txt: str):
        self._edit.setPlaceholderText(txt)

    def setMaxLength(self, n: int):
        self._edit.setMaxLength(n)

    def setReadOnly(self, v: bool):
        self._edit.setReadOnly(v)

    def clear(self):
        self._edit.clear()

    def setFocus(self):
        self._edit.setFocus()

    def is_valid(self) -> bool:
        ok, _ = validate_sdt(self._edit.text())
        return ok

    def returnPressed(self):
        return self._edit.returnPressed

    # ── Internal ──────────────────────────────────────────────
    def _on_changed(self, text: str):
        self.textChanged.emit(text)
        sdt = text.strip()
        if not sdt:
            self._edit.setStyleSheet(self._STYLE_NORMAL)
            self._lbl_err.hide()
            return

        ok, msg = validate_sdt(sdt)
        if ok:
            self._edit.setStyleSheet(self._STYLE_OK)
            self._lbl_err.hide()
        else:
            self._edit.setStyleSheet(self._STYLE_ERR)
            self._lbl_err.setText(f"⚠ {msg}")
            self._lbl_err.show()