"""
Small reusable widgets for the VendorVault design system.

Everything here is presentation-only: no database or business logic.
Colours come from :mod:`src.ui.theme`.
"""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QIntValidator, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from src.ui import theme as T


# ---------------------------------------------------------------------------
# Basic building blocks
# ---------------------------------------------------------------------------
def make_label(text: str = "", role: Optional[str] = None, tone: Optional[str] = None,
               size: Optional[int] = None, weight: Optional[int] = None,
               align: Optional[Qt.AlignmentFlag] = None, spacing: float = 0.0,
               parent: Optional[QWidget] = None) -> QLabel:
    """Create a themed QLabel. ``size``/``weight`` override the role font."""
    lbl = QLabel(text, parent)
    if role:
        lbl.setProperty("role", role)
    if tone:
        lbl.setProperty("tone", tone)
    if size is not None or weight is not None or spacing:
        f = lbl.font()
        if size is not None:
            f.setPixelSize(size)
        if weight is not None:
            f.setWeight(QFont.Weight(weight))
        if spacing:
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        lbl.setFont(f)
        # A role-based QSS font-size would override setFont; pin it inline.
        css = []
        if size is not None:
            css.append(f"font-size: {size}px;")
        if weight is not None:
            css.append(f"font-weight: {weight};")
        if css:
            lbl.setStyleSheet(" ".join(css))
    if align is not None:
        lbl.setAlignment(align)
    return lbl


def overline(text: str) -> QLabel:
    """Small uppercase section label (``ITEM``, ``PAYMENT``)."""
    lbl = make_label(text.upper(), role="overline")
    f = lbl.font()
    f.setPixelSize(11)
    f.setWeight(QFont.Weight(600))
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
    lbl.setFont(f)
    return lbl


def make_button(text: str, variant: Optional[str] = None, size: Optional[str] = None,
                shortcut_hint: Optional[str] = None, parent: Optional[QWidget] = None) -> QPushButton:
    btn = QPushButton(text, parent)
    if variant:
        btn.setProperty("variant", variant)
    if size:
        btn.setProperty("size", size)
    btn.setCursor(Qt.PointingHandCursor)
    if shortcut_hint:
        btn.setToolTip(f"{text} ({shortcut_hint})")
    return btn


class Card(QFrame):
    """Rounded surface with a 1px border. ``inset=True`` uses surface-2."""

    def __init__(self, parent: Optional[QWidget] = None, inset: bool = False,
                 padding: Tuple[int, int, int, int] = (24, 22, 24, 22), spacing: int = 12):
        super().__init__(parent)
        self.setProperty("card", "inset" if inset else "true")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(*padding)
        self.body.setSpacing(spacing)


class Divider(QFrame):
    def __init__(self, soft: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("divider", "soft" if soft else "true")
        self.setFixedHeight(1)


class KbdHint(QLabel):
    """Keyboard key-cap hint (``F1``, ``Esc``)."""

    def __init__(self, key: str, on_accent: bool = False, parent: Optional[QWidget] = None):
        super().__init__(key, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if on_accent:
            css = ("background: rgba(255,255,255,46); color: #FFFFFF; border: none; border-radius: 5px;"
                   " padding: 1px 7px; font-size: 11px; font-weight: 600;")
        else:
            css = (f"background: {T.SURFACE_3}; color: {T.MUTED}; border: 1px solid {T.BORDER_2};"
                   f" border-radius: 5px; padding: 1px 6px; font-size: 11px; font-weight: 500;")
        self.setStyleSheet(css)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


class HintButton(QPushButton):
    """A button whose label sits left/centre and a key hint sits on the right."""

    def __init__(self, text: str, key: str = "", variant: Optional[str] = None,
                 on_accent: bool = False, parent: Optional[QWidget] = None, center: bool = True):
        super().__init__(parent)
        if variant:
            self.setProperty("variant", variant)
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(8)
        self.text_label = QLabel(text)
        self.text_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if center:
            lay.addStretch(1)
        lay.addWidget(self.text_label)
        lay.addStretch(1)
        self.kbd: Optional[QLabel] = None
        if key:
            if on_accent:
                self.kbd = KbdHint(key, on_accent=True)
            else:
                self.kbd = QLabel(key)
                self.kbd.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                self.kbd.setStyleSheet(f"color: {T.FAINT}; font-size: 11px; font-weight: 500;")
            lay.addWidget(self.kbd)
        self.setToolTip(f"{text} ({key})" if key else text)

    def setText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        self.text_label.setText(text)

    def text(self) -> str:  # noqa: D401
        return self.text_label.text()

    def set_text_style(self, css: str) -> None:
        self.text_label.setStyleSheet(css)


class Pill(QPushButton):
    """Rounded status pill with a leading dot (e.g. ``● 2 on hold``)."""

    TONES = {
        "warning": (T.WARNING, T.WARNING_SOFT),
        "success": (T.SUCCESS, T.SUCCESS_SOFT),
        "danger": (T.DANGER, T.DANGER_SOFT),
        "neutral": (T.MUTED, T.SURFACE_2),
        "accent": (T.ACCENT, T.ACCENT_SOFT),
    }

    def __init__(self, text: str = "", tone: str = "warning", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._text = text
        self.set_tone(tone)
        self.setText(text)

    def set_tone(self, tone: str) -> None:
        fg, bg = self.TONES.get(tone, self.TONES["neutral"])
        self.setStyleSheet(
            f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid transparent; border-radius: 16px;"
            f" padding: 6px 14px 6px 12px; font-size: 12px; font-weight: 500; }}"
            f"QPushButton:hover {{ border-color: {T.rgba(fg, 0.35)}; }}"
        )

    def setText(self, text: str) -> None:  # noqa: N802
        self._text = text
        super().setText(f"●  {text}")


class StatusBadge(QLabel):
    """Small rounded badge (``Low``, ``Critical``)."""

    def __init__(self, text: str, tone: str = "warning", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        fg, bg = Pill.TONES.get(tone, Pill.TONES["neutral"])
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 11px; padding: 0 10px;"
                           f" font-size: 12px; font-weight: 600;")
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


class Avatar(QLabel):
    """Circular initials avatar."""

    def __init__(self, name: str, size: int = 30, parent: Optional[QWidget] = None):
        super().__init__(T.initials(name), parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"background: {T.SURFACE_3}; color: {T.TEXT}; border: 1px solid {T.BORDER_2};"
                           f" border-radius: {size // 2}px; font-size: {max(10, size // 3)}px; font-weight: 600;")


class LogoMark(QWidget):
    """Accent rounded square with a 'V' stroke."""

    def __init__(self, size: int = 26, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.ACCENT))
        p.drawRoundedRect(QRectF(0, 0, s, s), s * 0.27, s * 0.27)
        pen = QPen(QColor("#FFFFFF"), max(1.6, s * 0.085), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        path = QPainterPath(QPointF(s * 0.27, s * 0.35))
        path.lineTo(QPointF(s * 0.5, s * 0.69))
        path.lineTo(QPointF(s * 0.73, s * 0.35))
        p.drawPath(path)


class CheckBadge(QWidget):
    """Filled circle with a check mark (used in success notices)."""

    def __init__(self, color: str = T.SUCCESS, size: int = 16, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self._color))
        p.drawEllipse(QRectF(0, 0, s, s))
        p.setPen(QPen(QColor(T.BG), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        path = QPainterPath(QPointF(s * 0.28, s * 0.52))
        path.lineTo(QPointF(s * 0.45, s * 0.68))
        path.lineTo(QPointF(s * 0.74, s * 0.34))
        p.drawPath(path)


class SearchIcon(QWidget):
    def __init__(self, color: str = T.MUTED, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(18, 18)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(self._color), 1.6, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(QRectF(2, 2, 11, 11))
        p.drawLine(QPointF(11.3, 11.3), QPointF(16, 16))


class RemoveButton(QPushButton):
    """Round red ✕ button used on the selected cart row."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Remove item (Del)")
        self.setStyleSheet(f"QPushButton {{ background: {T.DANGER_SOFT}; border: none; border-radius: 14px; padding: 0; }}"
                           f"QPushButton:hover {{ background: {T.rgba(T.DANGER, 0.22)}; }}")

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(T.DANGER), 1.6, Qt.SolidLine, Qt.RoundCap))
        c = self.width() / 2
        d = 5
        p.drawLine(QPointF(c - d, c - d), QPointF(c + d, c + d))
        p.drawLine(QPointF(c + d, c - d), QPointF(c - d, c + d))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
class Stepper(QFrame):
    """Compact − value + quantity control."""

    valueChanged = Signal(int)

    def __init__(self, value: int = 1, minimum: int = 1, maximum: int = 9999,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._min, self._max = minimum, maximum
        self._value = max(minimum, min(maximum, value))
        self.setFixedSize(100, 34)
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(0)
        self.minus = QPushButton("−")
        self.plus = QPushButton("+")
        for b in (self.minus, self.plus):
            b.setFixedSize(30, 28)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {T.MUTED};"
                            f" font-size: 16px; font-weight: 500; padding: 0; border-radius: 6px; }}"
                            f"QPushButton:hover {{ color: {T.TEXT}; background: {T.SURFACE_3}; }}")
        self.edit = QLineEdit(str(self._value))
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setValidator(QIntValidator(minimum, maximum, self))
        self.edit.setStyleSheet(f"QLineEdit {{ background: transparent; border: none; padding: 0;"
                                f" font-size: 14px; font-weight: 600; color: {T.TEXT}; }}")
        lay.addWidget(self.minus)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.plus)
        self.minus.clicked.connect(lambda: self.setValue(self._value - 1))
        self.plus.clicked.connect(lambda: self.setValue(self._value + 1))
        self.edit.editingFinished.connect(self._commit_edit)
        self.set_selected(False)

    def _commit_edit(self) -> None:
        txt = self.edit.text().strip()
        if txt.isdigit():
            self.setValue(int(txt))
        else:
            self.edit.setText(str(self._value))

    def set_selected(self, selected: bool) -> None:
        border = T.ACCENT if selected else T.BORDER
        self.setStyleSheet(f"Stepper {{ background: {T.SURFACE_2}; border: 1px solid {border}; border-radius: 9px; }}")

    def setMaximum(self, maximum: int) -> None:  # noqa: N802
        self._max = max(self._min, maximum)
        self.edit.setValidator(QIntValidator(self._min, self._max, self))

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:  # noqa: N802
        value = max(self._min, min(self._max, int(value)))
        changed = value != self._value
        self._value = value
        self.edit.setText(str(value))
        if changed:
            self.valueChanged.emit(value)


class SegmentedControl(QFrame):
    """Exclusive set of options rendered as a segmented pill bar."""

    currentChanged = Signal(str)

    def __init__(self, options: Sequence[str], parent: Optional[QWidget] = None, height: int = 42):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(height)
        self.setStyleSheet(f"SegmentedControl {{ background: {T.SURFACE_2}; border: 1px solid {T.BORDER}; border-radius: 10px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: List[QPushButton] = []
        for opt in options:
            b = QPushButton(opt)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; border: 1px solid transparent; border-radius: 8px;"
                f" color: {T.MUTED}; font-size: 13px; font-weight: 500; padding: 0; }}"
                f"QPushButton:hover {{ color: {T.TEXT}; }}"
                f"QPushButton:checked {{ background: {T.SURFACE_3}; border-color: {T.BORDER_2}; color: {T.TEXT}; font-weight: 600; }}"
            )
            self._group.addButton(b)
            self._buttons.append(b)
            lay.addWidget(b)
            b.toggled.connect(lambda on, o=opt: on and self.currentChanged.emit(o))
        if self._buttons:
            self._buttons[0].setChecked(True)

    def currentText(self) -> str:  # noqa: N802
        b = self._group.checkedButton()
        return b.text() if b else ""

    def setCurrentText(self, text: str) -> None:  # noqa: N802
        for b in self._buttons:
            if b.text() == text:
                b.setChecked(True)
                return

    def options(self) -> List[str]:
        return [b.text() for b in self._buttons]


class ChipRow(QWidget):
    """Row of quick-amount chips; ``chipClicked`` emits the chip value."""

    chipClicked = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(8)
        self._buttons: List[Tuple[QPushButton, float]] = []
        self._active: Optional[float] = None

    def set_amounts(self, amounts: Iterable[float]) -> None:
        for b, _ in self._buttons:
            b.deleteLater()
        self._buttons = []
        for amt in amounts:
            b = QPushButton(T.money(amt, 0))
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(32)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, a=amt: self.chipClicked.emit(a))
            self._lay.addWidget(b, 1)
            self._buttons.append((b, amt))
        self.set_active(self._active)

    def set_active(self, amount: Optional[float]) -> None:
        self._active = amount
        for b, amt in self._buttons:
            on = amount is not None and abs(amt - amount) < 0.005
            bg, bd, fg = (T.ACCENT_SOFT, T.ACCENT, T.TEXT) if on else (T.SURFACE_2, T.BORDER, T.MUTED)
            b.setStyleSheet(f"QPushButton {{ background: {bg}; border: 1px solid {bd}; border-radius: 8px;"
                            f" color: {fg}; font-size: 12px; font-weight: 500; padding: 0 6px; }}"
                            f"QPushButton:hover {{ color: {T.TEXT}; border-color: {T.BORDER_2 if not on else T.ACCENT}; }}")


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
class InlineNotice(QFrame):
    """Soft success/warning strip with a message and an optional action link."""

    actionClicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 16, 0)
        lay.setSpacing(10)
        self.icon = CheckBadge(T.SUCCESS)
        self.message = QLabel()
        self.action = QPushButton()
        self.action.setCursor(Qt.PointingHandCursor)
        self.action.setFocusPolicy(Qt.NoFocus)
        self.action.clicked.connect(self.actionClicked)
        lay.addWidget(self.icon)
        lay.addWidget(self.message, 1)
        lay.addWidget(self.action)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.set_tone("success")
        self.hide()

    def set_tone(self, tone: str) -> None:
        fg, bg = {"success": (T.SUCCESS, T.SUCCESS_SOFT), "warning": (T.WARNING, T.WARNING_SOFT),
                  "danger": (T.DANGER, T.DANGER_SOFT)}.get(tone, (T.SUCCESS, T.SUCCESS_SOFT))
        self.setStyleSheet(f"InlineNotice {{ background: {bg}; border: none; border-radius: 10px; }}")
        self.message.setStyleSheet(f"color: {fg}; font-size: 13px; font-weight: 500;")
        self.action.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {fg};"
                                  f" font-size: 12px; font-weight: 500; padding: 0; }}"
                                  f"QPushButton:hover {{ text-decoration: underline; }}")
        self.icon._color = fg
        self.icon.update()

    def show_message(self, text: str, action: str = "", tone: str = "success", timeout_ms: int = 6000) -> None:
        self.set_tone(tone)
        self.message.setText(text)
        self.action.setText(action)
        self.action.setVisible(bool(action))
        self.show()
        if timeout_ms:
            self._timer.start(timeout_ms)


class Toast(QFrame):
    """Floating notification anchored to the bottom-centre of its parent."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 16, 10)
        lay.setSpacing(10)
        self.icon = CheckBadge(T.SUCCESS)
        self.label = QLabel()
        self.label.setStyleSheet(f"color: {T.TEXT}; font-size: 13px; font-weight: 500;")
        lay.addWidget(self.icon)
        lay.addWidget(self.label)
        self.setStyleSheet(f"Toast {{ background: {T.SURFACE_3}; border: 1px solid {T.BORDER_2}; border-radius: 10px; }}")
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, text: str, tone: str = "success", timeout_ms: int = 2600, bottom: int = 72) -> None:
        self.icon._color = {"success": T.SUCCESS, "warning": T.WARNING, "danger": T.DANGER}.get(tone, T.ACCENT)
        self.icon.update()
        self.label.setText(text)
        self.adjustSize()
        par = self.parentWidget()
        if par is not None:
            self.move((par.width() - self.width()) // 2, par.height() - self.height() - bottom)
        self.raise_()
        self.show()
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(timeout_ms)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._hide_once)
        self._anim.start()

    def _hide_once(self) -> None:
        try:
            self._anim.finished.disconnect(self._hide_once)
        except (RuntimeError, TypeError):
            pass
        if self._effect.opacity() < 0.05:
            self.hide()


# ---------------------------------------------------------------------------
# Dashboard pieces
# ---------------------------------------------------------------------------
class StatCard(Card):
    """KPI card: caption, big value, coloured delta line."""

    def __init__(self, title: str, value: str = "—", delta: str = "", tone: str = "success",
                 parent: Optional[QWidget] = None):
        super().__init__(parent, padding=(20, 18, 20, 18), spacing=6)
        self.setMinimumHeight(112)
        self.title = make_label(title, role="muted", size=13, weight=500)
        self.value = make_label(value, size=28, weight=600)
        f = self.value.font()
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.8)
        self.value.setFont(f)
        self.delta = make_label(delta, size=12, weight=500)
        self.body.addWidget(self.title)
        self.body.addWidget(self.value)
        self.body.addWidget(self.delta)
        self.body.addStretch(1)
        self.set_delta(delta, tone)

    def set_value(self, value: str) -> None:
        self.value.setText(value)

    def set_delta(self, text: str, tone: str = "success") -> None:
        color = {"success": T.SUCCESS, "warning": T.WARNING, "danger": T.DANGER}.get(tone, T.MUTED)
        self.delta.setText(text)
        self.delta.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500;")


class BarRow(QWidget):
    """Label + value on one line with a thin progress bar beneath."""

    def __init__(self, label: str, value: str, fraction: float, parent: Optional[QWidget] = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        top = QHBoxLayout()
        top.setSpacing(8)
        name = make_label(label, size=13, weight=500)
        name.setMinimumWidth(10)
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        name.setToolTip(label)
        val = make_label(value, role="muted", size=12, weight=500)
        top.addWidget(name, 1)
        top.addWidget(val)
        lay.addLayout(top)
        self.bar = _Bar(fraction)
        lay.addWidget(self.bar)


class _Bar(QWidget):
    def __init__(self, fraction: float):
        super().__init__()
        self.fraction = max(0.0, min(1.0, fraction))
        self.setFixedHeight(5)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        r = QRectF(0, 0, self.width(), self.height())
        p.setBrush(QColor(T.SURFACE_3))
        p.drawRoundedRect(r, 2.5, 2.5)
        if self.fraction > 0:
            p.setBrush(QColor(T.ACCENT))
            p.drawRoundedRect(QRectF(0, 0, max(5.0, self.width() * self.fraction), self.height()), 2.5, 2.5)


class AreaChart(QWidget):
    """Lightweight QPainter area chart (no matplotlib) for hourly sales.

    ``set_data(points, labels)`` where ``points`` are numeric values and
    ``labels`` the x-axis captions (empty string to skip a tick). The
    highest point is highlighted with a tooltip bubble.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._values: List[float] = []
        self._labels: List[str] = []
        self._tips: List[str] = []
        self._empty_text = "No sales yet today"
        self.setMinimumHeight(200)

    def set_data(self, values: Sequence[float], labels: Sequence[str], tips: Optional[Sequence[str]] = None,
                 empty_text: str = "No sales yet today") -> None:
        self._values = [float(v) for v in values]
        self._labels = list(labels)
        self._tips = list(tips) if tips else [""] * len(self._values)
        self._empty_text = empty_text
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        left, right, top, bottom = 10, 10, 54, 30
        base = h - bottom
        plot_w = max(1, w - left - right)
        # grid
        grid_pen = QPen(QColor(T.SURFACE_3), 1, Qt.CustomDashLine)
        grid_pen.setDashPattern([3, 5])
        p.setPen(grid_pen)
        for g in range(5):
            gy = base - g * (base - top) / 4
            p.drawLine(QPointF(left, gy), QPointF(w - right, gy))
        n = len(self._values)
        p.setFont(T.font(11))
        if n < 2 or max(self._values or [0]) <= 0:
            p.setPen(QColor(T.FAINT))
            p.drawText(QRectF(0, top, w, base - top), Qt.AlignCenter, self._empty_text)
            self._draw_labels(p, n, left, plot_w, base)
            return
        mx = max(self._values) * 1.1
        step = plot_w / (n - 1)
        pts = [QPointF(left + i * step, base - (v / mx) * (base - top)) for i, v in enumerate(self._values)]
        line = QPainterPath(pts[0])
        for pt in pts[1:]:
            line.lineTo(pt)
        area = QPainterPath(line)
        area.lineTo(QPointF(pts[-1].x(), base))
        area.lineTo(QPointF(pts[0].x(), base))
        area.closeSubpath()
        grad = QLinearGradient(0, top, 0, base)
        grad.setColorAt(0, T.qcolor(T.ACCENT, 0.35))
        grad.setColorAt(1, T.qcolor(T.ACCENT, 0.0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(area)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(T.ACCENT), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(line)
        # highlight peak
        peak = max(range(n), key=lambda i: self._values[i])
        pk = pts[peak]
        p.setPen(QPen(QColor(T.ACCENT), 2.2))
        p.setBrush(QColor(T.BG))
        p.drawEllipse(pk, 5, 5)
        tip_w, tip_h = 116, 36
        tx = min(max(pk.x() - tip_w / 2, 0), w - tip_w)
        ty = max(pk.y() - tip_h - 14, 0)
        p.setPen(QPen(QColor(T.BORDER_2), 1))
        p.setBrush(QColor(T.SURFACE_3))
        p.drawRoundedRect(QRectF(tx, ty, tip_w, tip_h), 8, 8)
        tip = self._tips[peak] if peak < len(self._tips) else ""
        cap, _, val = tip.partition("|")
        p.setFont(T.font(11, 500))
        p.setPen(QColor(T.FAINT))
        p.drawText(QRectF(tx, ty + 3, tip_w, 15), Qt.AlignCenter, cap)
        p.setFont(T.font(12, 600))
        p.setPen(QColor(T.TEXT))
        p.drawText(QRectF(tx, ty + 17, tip_w, 16), Qt.AlignCenter, val)
        self._draw_labels(p, n, left, plot_w, base)

    def _draw_labels(self, p: QPainter, n: int, left: float, plot_w: float, base: float) -> None:
        if n < 2:
            return
        step = plot_w / (n - 1)
        p.setFont(T.font(11))
        p.setPen(QColor(T.FAINT))
        for i, lab in enumerate(self._labels):
            if not lab:
                continue
            x = left + i * step
            p.drawText(QRectF(x - 30, base + 10, 60, 16), Qt.AlignCenter, lab)
