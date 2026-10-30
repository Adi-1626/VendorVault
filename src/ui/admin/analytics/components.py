"""Layout and presentation components for the Analytics page."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QBoxLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from src.ui import theme as T
from src.ui.admin.analytics.charts import Sparkline
from src.ui.widgets import Card, Divider, make_label, overline

TONE_COLORS = {"success": T.SUCCESS, "danger": T.DANGER, "warning": T.WARNING, "neutral": T.MUTED,
               "accent": T.ACCENT}


def clear_layout(lay) -> None:
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.hide()
            w.deleteLater()
        elif it.layout() is not None:
            clear_layout(it.layout())


class ElidedLabel(QLabel):
    """QLabel that ends with … when it is narrower than its text."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(20)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full = text
        self._elide()

    def full_text(self) -> str:
        return self._full

    def _elide(self) -> None:
        fm = self.fontMetrics()
        shown = fm.elidedText(self._full, Qt.ElideRight, max(10, self.width()))
        super().setText(shown)
        self.setToolTip(self._full if shown != self._full else "")

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._elide()


def elided_label(text: str, size: int = 13, weight: int = 500, role: Optional[str] = None,
                 tone: Optional[str] = None) -> ElidedLabel:
    """Label that shrinks gracefully with an ellipsis (tooltip carries the full text)."""
    lbl = ElidedLabel(text)
    if role:
        lbl.setProperty("role", role)
    color = TONE_COLORS.get(tone) if tone else None
    css = f"font-size: {size}px; font-weight: {weight};" + (f" color: {color};" if color else "")
    lbl.setStyleSheet(css)
    f = lbl.font()
    f.setPixelSize(size)
    f.setWeight(QFont.Weight(weight))
    lbl.setFont(f)
    return lbl


# ---------------------------------------------------------------------------
class DeltaPill(QLabel):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(22)
        self.set_delta("", "neutral")

    def set_delta(self, text: str, tone: str) -> None:
        color = TONE_COLORS.get(tone, T.MUTED)
        arrow = ""
        if text.startswith("+"):
            arrow, text = "▲ ", text[1:]
        elif text.startswith("-"):
            arrow, text = "▼ ", text[1:]
        self.setText(arrow + text)
        self.setVisible(bool(text))
        self.setStyleSheet(
            f"QLabel {{ color: {color}; background: {T.rgba(color, 0.12)}; border-radius: 6px;"
            f" padding: 0 7px; font-size: 12px; font-weight: 600; }}")


class InfoDot(QWidget):
    """Small painted (i) marker that shows a tooltip."""

    def __init__(self, tip: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setToolTip(tip)
        self.setFixedSize(14, 14)
        self.setCursor(Qt.WhatsThisCursor)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(T.FAINT), 1.1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(1, 1, 12, 12))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.FAINT))
        p.drawEllipse(QRectF(6.3, 3.6, 1.6, 1.6))
        p.drawRoundedRect(QRectF(6.4, 6.0, 1.4, 4.6), 0.7, 0.7)


# ---------------------------------------------------------------------------
class KpiCard(Card):
    def __init__(self, key: str, title: str, info: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent, padding=(20, 18, 20, 14), spacing=0)
        self.key = key
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        head = QHBoxLayout()
        head.setSpacing(6)
        self.title = make_label(title, role="muted", size=13, weight=500)
        head.addWidget(self.title)
        if info:
            head.addWidget(InfoDot(info))
        head.addStretch(1)
        self.pill = DeltaPill()
        head.addWidget(self.pill)
        self.body.addLayout(head)
        self.body.addSpacing(8)
        self.value = make_label("—", size=26, weight=600)
        f = self.value.font()
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.6)
        self.value.setFont(f)
        self.body.addWidget(self.value)
        self.caption = make_label("", role="faint", size=12)
        self.caption.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.body.addWidget(self.caption)
        self.body.addStretch(1)
        self.spark = Sparkline()
        self.body.addWidget(self.spark)

    def set_data(self, value: str, caption: str = "", delta: Tuple[str, str] = ("", "neutral"),
                 tooltip: str = "", spark: Sequence[float] = (), muted: bool = False) -> None:
        self.value.setText(value)
        self.value.setStyleSheet(f"font-size: 26px; font-weight: 600; color: {T.FAINT if muted else T.TEXT};")
        self.caption.setText(caption)
        self.pill.set_delta(*delta)
        self.pill.setToolTip(tooltip)
        self.setToolTip(tooltip)
        tone = delta[1]
        self.spark.set_values(spark, T.DANGER if tone == "danger" else T.ACCENT)


# ---------------------------------------------------------------------------
class SectionCard(Card):
    """Card with a title row (title, subtitle, optional right-side widgets)."""

    def __init__(self, title: str, subtitle: str = "", parent: Optional[QWidget] = None,
                 padding: Tuple[int, int, int, int] = (22, 20, 22, 20)):
        super().__init__(parent, padding=padding, spacing=0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        head = QHBoxLayout()
        head.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.title = make_label(title, size=15, weight=600)
        self.subtitle = make_label(subtitle, role="faint", size=12)
        self.subtitle.setVisible(bool(subtitle))
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        head.addLayout(titles, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        head.addLayout(self.actions)
        self.body.addLayout(head)
        self.body.addSpacing(16)
        self.content = QVBoxLayout()
        self.content.setSpacing(0)
        self.body.addLayout(self.content)
        self.body.addStretch(1)

    def set_subtitle(self, text: str) -> None:
        self.subtitle.setText(text)
        self.subtitle.setVisible(bool(text))


# ---------------------------------------------------------------------------
class _EmptyIcon(QWidget):
    def __init__(self, tone: str = "accent"):
        super().__init__()
        self.setFixedSize(40, 40)
        self.color = TONE_COLORS.get(tone, T.ACCENT)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(T.qcolor(self.color, 0.12))
        p.drawRoundedRect(QRectF(0, 0, 40, 40), 12, 12)
        p.setPen(QPen(QColor(self.color), 2, Qt.SolidLine, Qt.RoundCap))
        # three ascending bars
        for i, h in enumerate((8, 13, 18)):
            x = 13 + i * 7
            p.drawLine(x, 29, x, 29 - h)


class EmptyState(QWidget):
    def __init__(self, title: str, hint: str = "", tone: str = "accent", height: int = 160,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumHeight(height)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)
        lay.addStretch(1)
        icon = _EmptyIcon(tone)
        lay.addWidget(icon, 0, Qt.AlignHCenter)
        lay.addSpacing(4)
        t = make_label(title, size=14, weight=600, align=Qt.AlignHCenter)
        lay.addWidget(t)
        if hint:
            h = make_label(hint, role="muted", size=12, align=Qt.AlignHCenter)
            h.setWordWrap(True)
            lay.addWidget(h)
        lay.addStretch(1)


# ---------------------------------------------------------------------------
@dataclass
class Column:
    title: str
    stretch: int = 1
    align: Qt.AlignmentFlag = Qt.AlignLeft
    min_width: int = 0


Cell = Union[str, QWidget, Tuple[str, str]]   # text | widget | (text, tone/role)


class _Row(QFrame):
    def __init__(self, hover: bool = True):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_Hover, hover)
        self.setObjectName("AnRow")
        self.setStyleSheet(
            "QFrame#AnRow { background: transparent; border: none; border-radius: 8px; }"
            + (f"QFrame#AnRow:hover {{ background: {T.SURFACE_2}; }}" if hover else ""))


class GridTable(QWidget):
    """Scroll-free table made of label rows (never steals wheel events)."""

    def __init__(self, columns: Sequence[Column], row_height: int = 44, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.columns = list(columns)
        self.row_height = row_height
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.rows: List[_Row] = []

    def _row_layout(self, row: QWidget) -> QHBoxLayout:
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 0, 10, 0)
        rl.setSpacing(14)
        return rl

    def _place(self, rl: QHBoxLayout, col: Column, w: QWidget) -> None:
        if col.min_width:
            w.setMinimumWidth(col.min_width)
        if type(w) in (QLabel, ElidedLabel):
            w.setAlignment(col.align | Qt.AlignVCenter)
            if col.stretch == 0 and col.min_width:
                w.setFixedWidth(col.min_width)       # fixed column (e.g. rank)
                w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            else:
                w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            rl.addWidget(w, col.stretch)
        else:
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            expanding = w.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding
            right = bool(col.align & Qt.AlignRight)
            if not expanding and right:
                hl.addStretch(1)
            hl.addWidget(w, 1 if expanding else 0, Qt.AlignVCenter)
            if not expanding and not right:
                hl.addStretch(1)
            holder.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            if col.min_width:
                holder.setMinimumWidth(col.min_width)
            rl.addWidget(holder, col.stretch)

    def set_rows(self, rows: Sequence[Sequence[Cell]]) -> None:
        clear_layout(self.lay)
        self.rows = []
        head = _Row(hover=False)
        head.setFixedHeight(30)
        hl = self._row_layout(head)
        for col in self.columns:
            self._place(hl, col, overline(col.title))
        self.lay.addWidget(head)
        self.lay.addWidget(Divider())
        for cells in rows:
            r = _Row()
            r.setFixedHeight(self.row_height)
            rl = self._row_layout(r)
            for col, cell in zip(self.columns, cells):
                self._place(rl, col, self._make_cell(cell))
            self.lay.addWidget(r)
            self.rows.append(r)

    @staticmethod
    def _make_cell(cell: Cell) -> QWidget:
        if isinstance(cell, QWidget):
            return cell
        if isinstance(cell, tuple):
            text, style = cell
            if style in ("muted", "faint"):
                return elided_label(text, 13, 400, role=style)
            if style == "strong":
                return elided_label(text, 13, 600)
            return elided_label(text, 13, 600, tone=style)
        return elided_label(str(cell), 13, 500)


# ---------------------------------------------------------------------------
class ResponsiveGrid(QWidget):
    """Lays out equal-width tiles in 2-4 columns depending on available width,
    preferring a column count that divides the number of tiles evenly."""

    def __init__(self, min_tile: int = 250, max_cols: int = 4, min_cols: int = 2, spacing: int = 16,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.min_tile, self.max_cols, self.min_cols = min_tile, max_cols, min_cols
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(spacing)
        self.tiles: List[QWidget] = []
        self.cols = 0

    def set_tiles(self, tiles: Sequence[QWidget]) -> None:
        self.tiles = list(tiles)
        self.cols = 0
        self._relayout(self.width() or 1200)

    def columns_for(self, width: int) -> int:
        n = len(self.tiles) or 1
        fit = max(self.min_cols, min(self.max_cols, (width + self.grid.spacing()) // (self.min_tile + self.grid.spacing())))
        for c in range(int(fit), self.min_cols - 1, -1):
            if n % c == 0:
                return c
        return int(fit)

    def _relayout(self, width: int) -> None:
        cols = self.columns_for(width)
        if cols == self.cols:
            return
        self.cols = cols
        for t in self.tiles:
            self.grid.removeWidget(t)
        for i, t in enumerate(self.tiles):
            self.grid.addWidget(t, i // cols, i % cols)
        for c in range(self.max_cols):
            self.grid.setColumnStretch(c, 1 if c < cols else 0)

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._relayout(e.size().width())


class ResponsiveRow(QWidget):
    """Side-by-side children that stack vertically below ``breakpoint`` px."""

    def __init__(self, breakpoint: int = 980, spacing: int = 16, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.breakpoint = breakpoint
        self.box = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(spacing)
        self.items: List[Tuple[QWidget, int]] = []

    def add(self, w: QWidget, stretch: int = 1) -> None:
        self.items.append((w, stretch))
        self.box.addWidget(w, stretch)

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        want = QBoxLayout.TopToBottom if e.size().width() < self.breakpoint else QBoxLayout.LeftToRight
        if self.box.direction() != want:
            self.box.setDirection(want)


# ---------------------------------------------------------------------------
class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, text: str, checked: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checked = checked
        self._text = text
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(34)
        f = T.font(13, 500)
        from PySide6.QtGui import QFontMetrics
        self.setFixedWidth(QFontMetrics(f).horizontalAdvance(text) + 52)
        self.setFocusPolicy(Qt.StrongFocus)

    def isChecked(self) -> bool:  # noqa: N802
        return self._checked

    def setChecked(self, on: bool) -> None:  # noqa: N802
        if on != self._checked:
            self._checked = on
            self.update()
            self.toggled.emit(on)

    def mouseReleaseEvent(self, _e) -> None:  # noqa: N802
        self.setChecked(not self._checked)

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.setChecked(not self._checked)
        else:
            super().keyPressEvent(e)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.width(), 34)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        tr = QRectF(0, (self.height() - 18) / 2, 32, 18)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.ACCENT) if self._checked else QColor(T.SURFACE_3))
        p.drawRoundedRect(tr, 9, 9)
        kx = tr.right() - 16 if self._checked else tr.left() + 2
        p.setBrush(QColor("#FFFFFF") if self._checked else QColor(T.MUTED))
        p.drawEllipse(QRectF(kx, tr.top() + 2, 14, 14))
        p.setPen(QColor(T.TEXT if self._checked else T.MUTED))
        p.setFont(T.font(13, 500))
        p.drawText(QRectF(42, 0, self.width() - 42, self.height()), Qt.AlignLeft | Qt.AlignVCenter, self._text)
