"""
VendorVault design system.

One place for every colour, radius, spacing step and font used by the UI,
plus the global Qt stylesheet built from them. ``apply_theme(app)`` is
called once from ``main.py``; individual windows should not set their own
full-window stylesheets any more. Widgets opt into variants through
dynamic properties instead of inline styles, e.g.::

    btn.setProperty("variant", "primary")     # accent filled
    btn.setProperty("variant", "danger")      # red text, quiet
    label.setProperty("role", "muted")        # secondary text

Legacy modules (``src.ui.colors`` and ``src.ui.dark_theme``) re-export
names from here so existing imports keep working.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QWidget

# ---------------------------------------------------------------------------
# Colour tokens
# ---------------------------------------------------------------------------
BG = "#0A0B0D"
SURFACE = "#111317"
SURFACE_2 = "#16191E"
SURFACE_3 = "#1C2026"
BORDER = "#24282F"
BORDER_2 = "#2E333B"

TEXT = "#EDEEF0"
MUTED = "#8B909A"
FAINT = "#5B616B"

ACCENT = "#7C6CF6"
ACCENT_HOVER = "#8B7DF7"
ACCENT_PRESSED = "#6E5EEA"

SUCCESS = "#34D399"
WARNING = "#FBBF24"
DANGER = "#F87171"


def rgba(hex_color: str, alpha: float) -> str:
    """Return a QSS ``rgba()`` string for ``hex_color`` at ``alpha`` (0-1)."""
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {int(round(alpha * 255))})"


def qcolor(hex_color: str, alpha: float = 1.0) -> QColor:
    """QColor helper used by custom-painted widgets."""
    c = QColor(hex_color)
    c.setAlphaF(alpha)
    return c


ACCENT_SOFT = rgba(ACCENT, 0.12)
ACCENT_SOFTER = rgba(ACCENT, 0.07)
SUCCESS_SOFT = rgba(SUCCESS, 0.10)
WARNING_SOFT = rgba(WARNING, 0.10)
DANGER_SOFT = rgba(DANGER, 0.12)

# ---------------------------------------------------------------------------
# Geometry tokens (8px grid)
# ---------------------------------------------------------------------------
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32

RADIUS_SM = 8
RADIUS_MD = 10
RADIUS_LG = 14

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONT_FALLBACK = "Segoe UI"
FONT_FAMILY = "Inter"
MONO_FAMILY = "JetBrains Mono"

_FONT_FILES = ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")
_fonts_loaded = False


def asset(name: str) -> str:
    """Absolute, forward-slash path to a bundled UI asset (for QSS url())."""
    return (Path(__file__).resolve().parent / "assets" / name).as_posix()


def fonts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "fonts"


def load_fonts() -> str:
    """Register the bundled Inter font files; return the family to use."""
    global _fonts_loaded, FONT_FAMILY
    if _fonts_loaded:
        return FONT_FAMILY
    loaded = False
    for name in _FONT_FILES:
        path = fonts_dir() / name
        if path.exists() and QFontDatabase.addApplicationFont(str(path)) != -1:
            loaded = True
    FONT_FAMILY = "Inter" if loaded or "Inter" in QFontDatabase.families() else FONT_FALLBACK
    _fonts_loaded = True
    return FONT_FAMILY


def font(size: float = 13, weight: int = 400) -> QFont:
    """Return a QFont in the app family at a pixel size and CSS-like weight."""
    f = QFont(FONT_FAMILY)
    f.setPixelSize(int(round(size)))
    f.setWeight(QFont.Weight(weight))
    return f


def mono_font_stack() -> str:
    return f"'{MONO_FAMILY}', 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', monospace"


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------
def build_stylesheet() -> str:
    """Build the single global QSS for the application."""
    fam = f"'{FONT_FAMILY}', '{FONT_FALLBACK}', 'Segoe UI', Arial, sans-serif"
    return f"""
/* ---------- base ---------- */
* {{
    font-family: {fam};
    outline: none;
}}
QWidget {{
    color: {TEXT};
    font-size: 13px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
}}
QMainWindow, QDialog, #LoginWindow, QMainWindow > QWidget#qt_central, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: {BG};
}}
QMainWindow::separator {{ background: {BORDER}; width: 1px; height: 1px; }}
QToolTip {{
    background: {SURFACE_3}; color: {TEXT}; border: 1px solid {BORDER_2};
    border-radius: 6px; padding: 6px 8px;
}}
QLabel {{ background: transparent; border: none; }}
QLabel[role="h1"]      {{ font-size: 24px; font-weight: 600; }}
QLabel[role="h2"]      {{ font-size: 17px; font-weight: 600; }}
QLabel[role="h3"]      {{ font-size: 15px; font-weight: 600; }}
QLabel[role="muted"]   {{ color: {MUTED}; }}
QLabel[role="faint"]   {{ color: {FAINT}; }}
QLabel[role="overline"]{{ color: {FAINT}; font-size: 11px; font-weight: 600; }}
QLabel[role="mono"]    {{ color: {FAINT}; font-family: {mono_font_stack()}; font-size: 12px; font-weight: 500; }}
QLabel[tone="success"] {{ color: {SUCCESS}; }}
QLabel[tone="warning"] {{ color: {WARNING}; }}
QLabel[tone="danger"]  {{ color: {DANGER}; }}
QLabel[tone="accent"]  {{ color: {ACCENT}; }}

/* ---------- surfaces ---------- */
QFrame[card="true"] {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_LG}px;
}}
QFrame[card="inset"] {{
    background-color: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
}}
QFrame[divider="true"] {{ background-color: {BORDER}; border: none; max-height: 1px; min-height: 1px; }}
QFrame[divider="soft"] {{ background-color: {SURFACE_3}; border: none; max-height: 1px; min-height: 1px; }}
QFrame#TopBar, QFrame#StatusStrip {{ background-color: {BG}; border: none; }}
QFrame#Sidebar {{ background-color: {SURFACE}; border: none; border-right: 1px solid {BORDER}; }}

/* ---------- buttons ---------- */
QPushButton, QToolButton {{
    background-color: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover, QToolButton:hover {{ background-color: {SURFACE_3}; border-color: {BORDER_2}; }}
QPushButton:pressed, QToolButton:pressed {{ background-color: {BORDER}; }}
QPushButton:disabled {{ color: {FAINT}; background-color: {SURFACE}; border-color: {BORDER}; }}
QPushButton:focus {{ border-color: {ACCENT}; }}
QPushButton[variant="primary"] {{
    background-color: {ACCENT}; color: #FFFFFF; border: 1px solid {ACCENT}; font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background-color: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton[variant="primary"]:pressed {{ background-color: {ACCENT_PRESSED}; }}
QPushButton[variant="primary"]:disabled {{ background-color: {rgba(ACCENT, 0.35)}; border-color: transparent; color: {rgba('#FFFFFF', 0.6)}; }}
QPushButton[variant="light"] {{ background-color: {TEXT}; color: {BG}; border: 1px solid {TEXT}; font-weight: 600; }}
QPushButton[variant="light"]:hover {{ background-color: #FFFFFF; }}
QPushButton[variant="danger"] {{ color: {DANGER}; }}
QPushButton[variant="danger"]:hover {{ background-color: {DANGER_SOFT}; border-color: {rgba(DANGER, 0.35)}; }}
QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid transparent; color: {MUTED}; }}
QPushButton[variant="ghost"]:hover {{ background: {SURFACE_3}; color: {TEXT}; }}
QPushButton[variant="link"] {{ background: transparent; border: none; color: {ACCENT}; padding: 0px; font-weight: 600; }}
QPushButton[variant="link"]:hover {{ color: {ACCENT_HOVER}; }}
QPushButton[size="sm"] {{ padding: 4px 10px; font-size: 12px; }}
QPushButton[size="lg"] {{ padding: 12px 18px; font-size: 14px; }}
QPushButton::menu-indicator {{ image: none; width: 0px; }}

/* ---------- inputs ---------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
    background-color: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}px;
    padding: 7px 10px;
    font-size: 13px;
    selection-background-color: {rgba(ACCENT, 0.45)};
}}
QLineEdit:hover, QTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QDateEdit:hover {{ border-color: {BORDER_2}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{ color: {FAINT}; background: {SURFACE}; }}
QLineEdit[size="lg"] {{ font-size: 19px; font-weight: 600; padding: 10px 14px; border-width: 1px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button,
QTimeEdit::up-button, QDateTimeEdit::up-button {{
    subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none; background: transparent;
    margin: 2px 2px 0 0;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button,
QTimeEdit::down-button, QDateTimeEdit::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none; background: transparent;
    margin: 0 2px 2px 0;
}}
QSpinBox[noButtons="true"]::up-button, QSpinBox[noButtons="true"]::down-button,
QDoubleSpinBox[noButtons="true"]::up-button, QDoubleSpinBox[noButtons="true"]::down-button {{
    width: 0px; margin: 0px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {SURFACE_3}; border-radius: 4px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow, QTimeEdit::up-arrow, QDateTimeEdit::up-arrow {{
    image: url("{asset('chevron-up.svg')}"); width: 10px; height: 10px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow {{
    image: url("{asset('chevron-down.svg')}"); width: 10px; height: 10px;
}}
QComboBox::drop-down, QDateEdit::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow, QDateEdit::down-arrow {{
    image: url("{asset('chevron-down.svg')}"); width: 12px; height: 12px; margin-right: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER_2};
    border-radius: {RADIUS_SM}px; padding: 4px; selection-background-color: {SURFACE_3}; outline: none;
}}
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; color: {TEXT}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; background: {SURFACE_2}; border: 1px solid {BORDER_2};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; image: url("{asset('check.svg')}"); }}
QRadioButton::indicator:checked {{ background: {ACCENT}; border: 4px solid {SURFACE_2}; }}

/* ---------- tables & lists ---------- */
QTableWidget, QTableView, QTreeView, QListWidget, QListView {{
    background-color: {SURFACE};
    alternate-background-color: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_MD}px;
    gridline-color: {SURFACE_3};
    font-size: 13px;
    outline: none;
    selection-background-color: transparent;
}}
QTableWidget::item, QTableView::item {{ padding: 6px 8px; border: none; border-bottom: 1px solid {SURFACE_3}; }}
QTableWidget::item:selected, QTableView::item:selected, QListWidget::item:selected, QListView::item:selected {{
    background-color: {ACCENT_SOFT}; color: {TEXT};
}}
QListWidget::item {{ padding: 8px 10px; border-radius: 6px; }}
QListWidget::item:hover {{ background-color: {SURFACE_3}; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background-color: {SURFACE};
    color: {FAINT};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 8px;
    font-size: 11px;
    font-weight: 600;
   
}}
QTableCornerButton::section {{ background: {SURFACE}; border: none; }}
QTableWidget[flat="true"], QListWidget[flat="true"] {{ border: none; background: transparent; }}

/* ---------- tabs ---------- */
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px; background: {SURFACE}; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; border: none; padding: 8px 16px; margin-right: 4px;
    border-radius: {RADIUS_SM}px; font-weight: 500;
}}
QTabBar::tab:hover {{ color: {TEXT}; background: {SURFACE_2}; }}
QTabBar::tab:selected {{ color: {TEXT}; background: {SURFACE_3}; }}

/* ---------- scrollbars ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {BORDER_2}; border-radius: 3px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- menus, status, message boxes ---------- */
QMenu {{ background: {SURFACE_2}; border: 1px solid {BORDER_2}; border-radius: {RADIUS_MD}px; padding: 6px; }}
QMenu::item {{ padding: 8px 14px; border-radius: 6px; color: {TEXT}; }}
QMenu::item:selected {{ background: {SURFACE_3}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 6px; }}
QStatusBar {{ background: {BG}; color: {MUTED}; border-top: 1px solid {BORDER}; font-size: 12px; }}
QStatusBar::item {{ border: none; }}
QMessageBox {{ background-color: {SURFACE}; }}
QMessageBox QLabel {{ color: {TEXT}; font-size: 13px; }}
QMessageBox QPushButton {{ min-width: 84px; }}
QGroupBox {{ border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px; margin-top: 18px; padding: 12px; color: {MUTED}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {MUTED}; font-weight: 600; }}
QProgressBar {{ background: {SURFACE_3}; border: none; border-radius: 3px; text-align: center; color: transparent; max-height: 6px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QCalendarWidget QWidget {{ background: {SURFACE_2}; color: {TEXT}; }}
"""


def apply_theme(app: Optional[QApplication] = None) -> None:
    """Load fonts and install the global stylesheet + default font."""
    app = app or QApplication.instance()
    if app is None:
        return
    family = load_fonts()
    base = QFont(family)
    base.setPixelSize(13)
    base.setHintingPreference(QFont.PreferNoHinting)
    app.setFont(base)
    app.setPalette(build_palette())
    app.setStyleSheet(build_stylesheet())


def build_palette() -> QPalette:
    """Dark palette so native/unstyled surfaces match the theme."""
    pal = QPalette()
    roles = {
        QPalette.Window: BG, QPalette.WindowText: TEXT, QPalette.Base: SURFACE_2,
        QPalette.AlternateBase: SURFACE, QPalette.Text: TEXT, QPalette.Button: SURFACE_2,
        QPalette.ButtonText: TEXT, QPalette.ToolTipBase: SURFACE_3, QPalette.ToolTipText: TEXT,
        QPalette.Highlight: ACCENT, QPalette.HighlightedText: "#FFFFFF", QPalette.PlaceholderText: FAINT,
        QPalette.Link: ACCENT, QPalette.Mid: BORDER, QPalette.Dark: BG, QPalette.Light: SURFACE_3,
    }
    for role, col in roles.items():
        pal.setColor(role, QColor(col))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(FAINT))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(FAINT))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(FAINT))
    return pal


def repolish(widget: QWidget) -> None:
    """Re-apply the stylesheet after a dynamic property change."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_prop(widget: QWidget, name: str, value) -> None:
    """Set a dynamic style property and repolish if it changed."""
    if widget.property(name) != value:
        widget.setProperty(name, value)
        repolish(widget)


def initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def money(value: float, decimals: int = 2) -> str:
    """Indian-rupee formatted amount, e.g. ₹1,234.50."""
    return f"₹{value:,.{decimals}f}"
