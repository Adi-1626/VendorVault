"""
Legacy colour names, kept so older imports (``from src.ui.colors import *``)
keep working. All values now come from :mod:`src.ui.theme`; prefer importing
that module directly in new code.
"""
from src.ui import theme as _T

# Backgrounds
DARK_BG = _T.BG
DARKER_BG = _T.BG
CARD_BG = _T.SURFACE

# Interactive elements
PRIMARY = _T.ACCENT
PRIMARY_HOVER = _T.ACCENT_HOVER
SECONDARY = _T.SURFACE_3

# Status colours
SUCCESS = _T.SUCCESS
SUCCESS_HOVER = _T.SUCCESS
DANGER = _T.DANGER
DANGER_HOVER = _T.DANGER
WARNING = _T.WARNING
INFO = _T.ACCENT

# Text
TEXT_PRIMARY = _T.TEXT
TEXT_SECONDARY = _T.MUTED
TEXT_DISABLED = _T.FAINT

# Borders & dividers
BORDER = _T.BORDER
BORDER_FOCUS = _T.ACCENT

# Specific UI colours
INPUT_BG = _T.SURFACE_2
TABLE_HEADER_BG = _T.SURFACE
TABLE_ALTERNATE_BG = _T.SURFACE_2
