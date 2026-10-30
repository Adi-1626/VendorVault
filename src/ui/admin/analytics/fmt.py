"""Number formatting for the Analytics page (Qt-free, unit-testable)."""
from __future__ import annotations

from datetime import date
from typing import Optional


def indian_group(n: int) -> str:
    """1234567 -> '12,34,567' (Indian digit grouping)."""
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + s


def inr(value: float, decimals: int = 0) -> str:
    """₹1,23,456 / ₹1,23,456.50 (Indian grouping)."""
    neg = value < 0
    value = abs(value)
    whole = int(value)
    frac = ""
    if decimals > 0:
        q = round(value, decimals)
        whole = int(q)
        frac = "." + f"{q - whole:.{decimals}f}"[2:]
    return ("-" if neg else "") + "₹" + indian_group(whole) + frac


def inr_smart(value: float) -> str:
    """Whole rupees from ₹1,000 up (and for exactly zero), paise below that."""
    return inr(value, 0 if abs(value) >= 1000 or value == 0 else 2)


def inr_compact(value: float) -> str:
    """Axis-friendly: ₹950, ₹12.5K, ₹3.4L, ₹1.2Cr."""
    v = abs(value)
    sign = "-" if value < 0 else ""
    if v >= 1e7:
        s = f"{v / 1e7:.1f}Cr"
    elif v >= 1e5:
        s = f"{v / 1e5:.1f}L"
    elif v >= 1e3:
        s = f"{v / 1e3:.1f}K"
    else:
        return f"{sign}₹{v:.0f}"
    return sign + "₹" + s.replace(".0", "")


def number(value: float, decimals: int = 0) -> str:
    if decimals:
        whole = int(abs(value))
        frac = f"{abs(value) - whole:.{decimals}f}"[1:]
        return ("-" if value < 0 else "") + indian_group(whole) + frac
    return indian_group(int(round(value)))


def pct(value: Optional[float], decimals: int = 1) -> str:
    return "—" if value is None else f"{value * 100:.{decimals}f}%"


def date_range_label(start: date, end: date) -> str:
    if start == end:
        return start.strftime("%a, %d %b %Y").replace(" 0", " ")
    if start.year == end.year:
        return f"{start.strftime('%d %b').lstrip('0')} – {end.strftime('%d %b %Y').lstrip('0')}"
    return f"{start.strftime('%d %b %Y').lstrip('0')} – {end.strftime('%d %b %Y').lstrip('0')}"


def nice_ceiling(value: float) -> float:
    """Round ``value`` up to a 'nice' axis maximum (1, 2, 4, 6, 8 × 10^n; divides evenly into 4 grid steps)."""
    import math
    if value <= 0:
        return 1.0
    exp = math.floor(math.log10(value))
    base = 10 ** exp
    for m in (1, 2, 4, 6, 8, 10):
        if value <= m * base:
            return m * base
    return 10 * base
