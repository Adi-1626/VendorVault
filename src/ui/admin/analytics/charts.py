"""
QPainter charts for the Analytics page.

All charts have a fixed height and never accept wheel events, so the page's
single outer QScrollArea always receives scrolling. Hover feedback uses
mouse tracking only.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from src.ui import theme as T
from src.ui.admin.analytics.fmt import inr, inr_compact, nice_ceiling

# Categorical palette: accent first, then muted companions that sit well on #111317.
PALETTE = ["#7C6CF6", "#34D399", "#60A5FA", "#FBBF24", "#F472B6", "#5B616B"]


def smooth_path(pts: Sequence[QPointF]) -> QPainterPath:
    """Monotone cubic (Fritsch–Carlson) path: smooth, never overshoots the data."""
    path = QPainterPath(pts[0])
    n = len(pts)
    if n < 3:
        for p in pts[1:]:
            path.lineTo(p)
        return path
    xs = [p.x() for p in pts]
    ys = [p.y() for p in pts]
    d = [(ys[i + 1] - ys[i]) / ((xs[i + 1] - xs[i]) or 1e-9) for i in range(n - 1)]
    m = [d[0]] + [0.0] * (n - 2) + [d[-1]]
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        s = a * a + b * b
        if s > 9:
            t = 3 / s ** 0.5
            m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    for i in range(n - 1):
        h = xs[i + 1] - xs[i]
        path.cubicTo(QPointF(xs[i] + h / 3, ys[i] + m[i] * h / 3),
                     QPointF(xs[i + 1] - h / 3, ys[i + 1] - m[i + 1] * h / 3), pts[i + 1])
    return path


def hour_range(h: int) -> str:
    def f(x: int) -> str:
        return f"{x % 12 or 12} {'AM' if x % 24 < 12 else 'PM'}"
    return f"{f(h)} – {f(h + 1)}"


class _NoWheel(QWidget):
    def wheelEvent(self, event) -> None:  # noqa: N802 - let the page scroll
        event.ignore()


# ---------------------------------------------------------------------------
class Sparkline(_NoWheel):
    def __init__(self, color: str = T.ACCENT, height: int = 36, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._values: List[float] = []
        self._color = color
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_values(self, values: Sequence[float], color: Optional[str] = None) -> None:
        self._values = [float(v) for v in values]
        if color:
            self._color = color
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        vals = self._values
        if len(vals) < 2 or max(vals) == min(vals) == 0:
            pen = QPen(T.qcolor(T.FAINT, 0.6), 1.2, Qt.CustomDashLine)
            pen.setDashPattern([2, 4])
            p.setPen(pen)
            p.drawLine(QPointF(2, h - 4), QPointF(w - 2, h - 4))
            return
        lo, hi = min(vals), max(vals)
        rng = (hi - lo) or 1.0
        step = (w - 4) / (len(vals) - 1)
        pts = [QPointF(2 + i * step, 3 + (h - 7) * (1 - (v - lo) / rng)) for i, v in enumerate(vals)]
        line = smooth_path(pts)
        area = QPainterPath(line)
        area.lineTo(pts[-1].x(), h)
        area.lineTo(pts[0].x(), h)
        area.closeSubpath()
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, T.qcolor(self._color, 0.22))
        g.setColorAt(1, T.qcolor(self._color, 0.0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawPath(area)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(self._color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(line)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self._color))
        p.drawEllipse(pts[-1], 2.4, 2.4)


# ---------------------------------------------------------------------------
class TrendChart(_NoWheel):
    """Revenue over time: smooth area line, optional dashed previous period,
    nice y-axis, collision-free x labels and a hover crosshair + tooltip."""

    LEFT_PAD, RIGHT_PAD, TOP_PAD, BOTTOM_PAD = 56, 12, 16, 34

    def __init__(self, height: int = 300, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.values: List[float] = []
        self.prev: List[float] = []
        self.labels: List[str] = []
        self.long_labels: List[str] = []
        self.prev_long_labels: List[str] = []
        self.show_prev = True
        self.empty_text = "No sales in this period"
        self._hover: Optional[int] = None
        self.formatter: Callable[[float], str] = lambda v: inr(v)

    def set_data(self, values: Sequence[float], labels: Sequence[str], long_labels: Sequence[str],
                 prev: Sequence[float] = (), prev_long_labels: Sequence[str] = (),
                 show_prev: bool = True, empty_text: str = "No sales in this period") -> None:
        self.values = [float(v) for v in values]
        self.labels = list(labels)
        self.long_labels = list(long_labels)
        self.prev = [float(v) for v in prev]
        self.prev_long_labels = list(prev_long_labels)
        self.show_prev = show_prev and bool(self.prev) and any(self.prev)
        self.empty_text = empty_text
        self._hover = None
        self.update()

    # geometry helpers
    def _plot(self) -> QRectF:
        return QRectF(self.LEFT_PAD, self.TOP_PAD, max(1, self.width() - self.LEFT_PAD - self.RIGHT_PAD),
                      max(1, self.height() - self.TOP_PAD - self.BOTTOM_PAD))

    def _x(self, i: int, n: int, plot: QRectF) -> float:
        if n <= 1:
            return plot.center().x()
        return plot.left() + i * plot.width() / (n - 1)

    def _ymax(self) -> float:
        vals = self.values + (self.prev if self.show_prev else [])
        return nice_ceiling(max(vals) * 1.08) if vals and max(vals) > 0 else 1.0

    def leaveEvent(self, _e) -> None:  # noqa: N802
        self._hover = None
        self.update()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        n = len(self.values)
        if n == 0 or not any(self.values + self.prev):
            return
        plot = self._plot()
        x = e.position().x()
        i = 0 if n == 1 else round((x - plot.left()) / (plot.width() / (n - 1)))
        i = max(0, min(n - 1, i))
        if i != self._hover:
            self._hover = i
            self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        plot = self._plot()
        n = len(self.values)
        ymax = self._ymax()
        # grid + y labels
        p.setFont(T.font(11))
        fm = QFontMetrics(p.font())
        has_data = n > 0 and any(self.values + (self.prev if self.show_prev else []))
        for g in range(5):
            y = plot.bottom() - g * plot.height() / 4
            pen = QPen(QColor(T.SURFACE_3) if g else QColor(T.BORDER), 1)
            if g:
                pen.setStyle(Qt.CustomDashLine)
                pen.setDashPattern([3, 4])
            p.setPen(pen)
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            if has_data:
                p.setPen(QColor(T.FAINT))
                p.drawText(QRectF(0, y - 8, self.LEFT_PAD - 10, 16), Qt.AlignRight | Qt.AlignVCenter,
                           inr_compact(ymax * g / 4))
        self._draw_x_labels(p, fm, plot, n)
        if n == 0 or not any(self.values + (self.prev if self.show_prev else [])):
            p.setFont(T.font(13, 500))
            p.setPen(QColor(T.MUTED))
            p.drawText(plot.adjusted(0, -10, 0, -10), Qt.AlignCenter, self.empty_text)
            return

        def pts_of(vals: Sequence[float]) -> List[QPointF]:
            return [QPointF(self._x(i, len(vals), plot), plot.bottom() - (v / ymax) * plot.height())
                    for i, v in enumerate(vals)]

        if self.show_prev:
            pp = pts_of(self.prev[:max(n, 1)])
            pen = QPen(T.qcolor(T.MUTED, 0.75), 1.4, Qt.CustomDashLine)
            pen.setDashPattern([4, 4])
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            if len(pp) == 1:
                p.drawEllipse(pp[0], 3, 3)
            else:
                p.drawPath(smooth_path(pp))

        pts = pts_of(self.values)
        if n == 1:
            # a single bucket: draw a soft column + dot so it doesn't look broken
            x = pts[0].x()
            bar = QRectF(x - 18, pts[0].y(), 36, plot.bottom() - pts[0].y())
            g = QLinearGradient(0, bar.top(), 0, bar.bottom())
            g.setColorAt(0, T.qcolor(T.ACCENT, 0.45))
            g.setColorAt(1, T.qcolor(T.ACCENT, 0.05))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(bar, 6, 6)
        else:
            line = smooth_path(pts)
            area = QPainterPath(line)
            area.lineTo(pts[-1].x(), plot.bottom())
            area.lineTo(pts[0].x(), plot.bottom())
            area.closeSubpath()
            g = QLinearGradient(0, plot.top(), 0, plot.bottom())
            g.setColorAt(0, T.qcolor(T.ACCENT, 0.30))
            g.setColorAt(1, T.qcolor(T.ACCENT, 0.0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawPath(area)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(T.ACCENT), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(line)

        hv = self._hover
        if hv is None and n == 1:
            hv = 0
        if hv is not None and hv < n:
            self._draw_hover(p, plot, pts, hv, ymax)

    def _draw_x_labels(self, p: QPainter, fm: QFontMetrics, plot: QRectF, n: int) -> None:
        if n == 0:
            return
        p.setPen(QColor(T.FAINT))
        widest = max((fm.horizontalAdvance(lab) for lab in self.labels), default=0) + 18
        slot = plot.width() / max(1, n - 1) if n > 1 else plot.width()
        every = max(1, int(-(-widest // max(slot, 1))))
        last_right = -1e9
        idxs = list(range(0, n, every))
        if n - 1 not in idxs and n > 1:
            idxs.append(n - 1)
        for i in idxs:
            lab = self.labels[i] if i < len(self.labels) else ""
            if not lab:
                continue
            x = self._x(i, n, plot)
            w = fm.horizontalAdvance(lab)
            left = min(max(x - w / 2, plot.left() - 6), plot.right() + self.RIGHT_PAD - w)
            if left < last_right + 10:
                continue
            p.drawText(QRectF(left, plot.bottom() + 10, w + 2, 16), Qt.AlignLeft | Qt.AlignVCenter, lab)
            last_right = left + w

    def _draw_hover(self, p: QPainter, plot: QRectF, pts: List[QPointF], i: int, ymax: float) -> None:
        pt = pts[i]
        pen = QPen(T.qcolor(T.TEXT, 0.18), 1)
        p.setPen(pen)
        p.drawLine(QPointF(pt.x(), plot.top()), QPointF(pt.x(), plot.bottom()))
        if self.show_prev and i < len(self.prev):
            py = plot.bottom() - (self.prev[i] / ymax) * plot.height()
            p.setPen(QPen(QColor(T.MUTED), 1.4))
            p.setBrush(QColor(T.SURFACE))
            p.drawEllipse(QPointF(pt.x(), py), 3.5, 3.5)
        p.setPen(QPen(QColor(T.ACCENT), 2.4))
        p.setBrush(QColor(T.BG))
        p.drawEllipse(pt, 5, 5)
        # tooltip
        lines: List[Tuple[str, str, str]] = [
            (self.long_labels[i] if i < len(self.long_labels) else "", "", T.MUTED),
            ("Revenue", self.formatter(self.values[i]), T.ACCENT)]
        if self.show_prev and i < len(self.prev):
            lines.append(("Previous", self.formatter(self.prev[i]), T.MUTED))
        p.setFont(T.font(12, 500))
        fm = QFontMetrics(p.font())
        width = max(fm.horizontalAdvance(a) + (fm.horizontalAdvance(b) + 40 if b else 0) for a, b, _c in lines) + 28
        width = max(width, 170)
        height = 14 + len(lines) * 20
        tx = pt.x() + 14
        if tx + width > self.width() - 4:
            tx = pt.x() - 14 - width
        ty = min(max(plot.top(), pt.y() - height / 2), plot.bottom() - height)
        box = QRectF(tx, ty, width, height)
        p.setPen(QPen(QColor(T.BORDER_2), 1))
        p.setBrush(QColor(T.SURFACE_3))
        p.drawRoundedRect(box, 8, 8)
        y = ty + 8
        for k, (a, b, c) in enumerate(lines):
            r = QRectF(tx + 12, y, width - 24, 18)
            if k == 0:
                p.setFont(T.font(11, 500))
                p.setPen(QColor(T.FAINT))
                p.drawText(r, Qt.AlignLeft | Qt.AlignVCenter, a)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(c))
                p.drawRoundedRect(QRectF(r.left(), r.center().y() - 4, 8, 8), 2, 2)
                p.setFont(T.font(12, 500))
                p.setPen(QColor(T.MUTED))
                p.drawText(r.adjusted(14, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, a)
                p.setFont(T.font(12, 600))
                p.setPen(QColor(T.TEXT))
                p.drawText(r, Qt.AlignRight | Qt.AlignVCenter, b)
            y += 20


# ---------------------------------------------------------------------------
class Heatmap(_NoWheel):
    """Weekday × hour-of-day revenue heatmap."""

    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    LEFT, TOP, CELL_H, GAP = 40, 4, 26, 4

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(self.TOP + 7 * (self.CELL_H + self.GAP) + 22)
        self.rev: List[List[float]] = [[0.0] * 24 for _ in range(7)]
        self.cnt: List[List[int]] = [[0] * 24 for _ in range(7)]
        self.hours: Tuple[int, int] = (9, 21)
        self._hover: Optional[Tuple[int, int]] = None

    def set_data(self, rev: List[List[float]], cnt: List[List[int]], hours: Tuple[int, int]) -> None:
        self.rev, self.cnt, self.hours = rev, cnt, hours
        self._hover = None
        self.update()

    def _cols(self) -> List[int]:
        return list(range(self.hours[0], self.hours[1] + 1))

    def _cell(self, r: int, c: int, ncols: int) -> QRectF:
        cw = (self.width() - self.LEFT) / max(1, ncols)
        return QRectF(self.LEFT + c * cw + self.GAP / 2, self.TOP + r * (self.CELL_H + self.GAP),
                      cw - self.GAP, self.CELL_H)

    def leaveEvent(self, _e) -> None:  # noqa: N802
        self._hover = None
        self.update()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        cols = self._cols()
        pos = e.position()
        hit = None
        for r in range(7):
            for c in range(len(cols)):
                if self._cell(r, c, len(cols)).contains(pos):
                    hit = (r, c)
        if hit != self._hover:
            self._hover = hit
            if hit:
                r, c = hit
                h = cols[c]
                n = self.cnt[r][h]
                self.setToolTip(f"{self.DAYS[r]} {hour_range(h)}\n{inr(self.rev[r][h])} · {n} bill{'s' if n != 1 else ''}")
            else:
                self.setToolTip("")
            self.update()

    def peak(self) -> Optional[Tuple[int, int, float]]:
        best = None
        for r in range(7):
            for h in range(24):
                v = self.rev[r][h]
                if v > 0 and (best is None or v > best[2]):
                    best = (r, h, v)
        return best

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cols = self._cols()
        mx = max((self.rev[r][h] for r in range(7) for h in cols), default=0) or 1.0
        p.setFont(T.font(11, 500))
        fm = QFontMetrics(p.font())
        for r in range(7):
            cr = self._cell(r, 0, len(cols))
            p.setPen(QColor(T.FAINT))
            p.drawText(QRectF(0, cr.top(), self.LEFT - 8, cr.height()), Qt.AlignLeft | Qt.AlignVCenter, self.DAYS[r])
            for c, h in enumerate(cols):
                rect = self._cell(r, c, len(cols))
                v = self.rev[r][h]
                p.setPen(Qt.NoPen)
                if v <= 0:
                    p.setBrush(QColor(T.SURFACE_2))
                else:
                    t = (v / mx) ** 0.75
                    p.setBrush(T.qcolor(T.ACCENT, 0.14 + 0.86 * t))
                p.drawRoundedRect(rect, 5, 5)
                if self._hover == (r, c):
                    p.setPen(QPen(QColor(T.TEXT), 1.2))
                    p.setBrush(Qt.NoBrush)
                    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 5, 5)
        # hour labels (skip to avoid overlap)
        cw = (self.width() - self.LEFT) / max(1, len(cols))
        need = fm.horizontalAdvance("12p") + 10
        every = max(1, int(-(-need // max(cw, 1))))
        y = self.TOP + 7 * (self.CELL_H + self.GAP) + 2
        p.setPen(QColor(T.FAINT))
        for c, h in enumerate(cols):
            if (h - cols[0]) % every:
                continue
            rect = self._cell(0, c, len(cols))
            p.drawText(QRectF(rect.left() - 10, y, rect.width() + 20, 16), Qt.AlignCenter, f"{h % 12 or 12}{'a' if h < 12 else 'p'}")


# ---------------------------------------------------------------------------
class Donut(_NoWheel):
    def __init__(self, size: int = 176, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.values: List[float] = []
        self.colors: List[str] = []
        self.center_value = ""
        self.center_caption = ""

    def set_data(self, values: Sequence[float], colors: Sequence[str], center_value: str, center_caption: str) -> None:
        self.values = [max(0.0, float(v)) for v in values]
        self.colors = list(colors)
        self.center_value, self.center_caption = center_value, center_caption
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.size()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height())
        thick = 18
        r = QRectF(thick / 2 + 2, thick / 2 + 2, s - thick - 4, s - thick - 4)
        p.setPen(QPen(QColor(T.SURFACE_3), thick, Qt.SolidLine, Qt.FlatCap))
        p.drawArc(r, 0, 360 * 16)
        total = sum(self.values)
        if total > 0:
            start = 90 * 16
            gap = 2.5 * 16 if len([v for v in self.values if v > 0]) > 1 else 0
            for v, c in zip(self.values, self.colors):
                if v <= 0:
                    continue
                span = -v / total * 360 * 16
                draw = span + gap if abs(span) > gap else span
                p.setPen(QPen(QColor(c), thick, Qt.SolidLine, Qt.FlatCap))
                p.drawArc(r, int(start - gap / 2), int(draw))
                start += span
        p.setPen(QColor(T.TEXT))
        p.setFont(T.font(18, 600))
        p.drawText(QRectF(0, s / 2 - 22, s, 26), Qt.AlignCenter, self.center_value)
        p.setPen(QColor(T.FAINT))
        p.setFont(T.font(11, 500))
        p.drawText(QRectF(0, s / 2 + 4, s, 18), Qt.AlignCenter, self.center_caption)


class MiniBar(_NoWheel):
    """Thin horizontal share bar (used in tables)."""

    def __init__(self, fraction: float = 0.0, color: str = T.ACCENT, height: int = 6,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.fraction = max(0.0, min(1.0, fraction))
        self.color = color
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        h = self.height()
        p.setBrush(QColor(T.SURFACE_3))
        p.drawRoundedRect(QRectF(0, 0, self.width(), h), h / 2, h / 2)
        if self.fraction > 0:
            p.setBrush(QColor(self.color))
            p.drawRoundedRect(QRectF(0, 0, max(h, self.width() * self.fraction), h), h / 2, h / 2)
