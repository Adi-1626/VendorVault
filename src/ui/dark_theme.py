"""
Legacy dark-theme helpers.

The real stylesheet now lives in :mod:`src.ui.theme` and is installed once on
the QApplication (see ``main.py``). These names are kept so existing imports
keep working: ``get_dark_stylesheet()`` returns an empty string, so windows
that still call ``setStyleSheet(get_dark_stylesheet())`` simply inherit the
global theme instead of overriding it.
"""
from src.ui.colors import *  # noqa: F401,F403
from src.ui import theme as _T

# Legacy mappings
TEXT_WHITE = _T.TEXT
TEXT_GRAY = _T.MUTED
BLUE = _T.ACCENT
RED = _T.DANGER
GREEN = _T.SUCCESS


def get_dark_stylesheet() -> str:
    """Kept for backward compatibility; the global theme already applies."""
    return ""


def get_full_stylesheet() -> str:
    """The complete application stylesheet (same one ``main.py`` installs)."""
    return _T.build_stylesheet()


def get_button_style(color, hover_color=None) -> str:
    """Quiet button tinted with ``color`` text (legacy helper)."""
    return (
        f"QPushButton {{ background-color: {_T.SURFACE_2}; color: {color}; border: 1px solid {_T.BORDER};"
        f" border-radius: 8px; padding: 7px 14px; font-weight: 500; }}"
        f"QPushButton:hover {{ background-color: {_T.SURFACE_3}; }}"
    )
