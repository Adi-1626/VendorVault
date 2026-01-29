"""
Dark Theme Stylesheet for the entire system.
Apply this to any QMainWindow or QWidget to get dark mode.
"""

from src.ui.colors import *

# Legacy mappings for backward compatibility if needed, but preferred to use colors directly
TEXT_WHITE = TEXT_PRIMARY
TEXT_GRAY = TEXT_SECONDARY
BLUE = PRIMARY
RED = DANGER
GREEN = SUCCESS



def get_dark_stylesheet():
    """Returns the complete dark mode stylesheet."""
    return f"""
        /* Main Window */
        QMainWindow, QWidget {{
            background-color: {DARK_BG};
            color: {TEXT_WHITE};
        }}
        
        /* Labels */
        QLabel {{
            color: {TEXT_WHITE};
            font-size: 16px;
            background: transparent;
        }}
        
        /* Line Edits */
        QLineEdit {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 16px;
        }}
        QLineEdit:focus {{
            border-color: {PRIMARY};
        }}
        QLineEdit::placeholder {{
            color: {TEXT_GRAY};
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 16px;
            font-weight: bold;
            min-height: 40px;
        }}
        QPushButton:hover {{
            background-color: {BORDER};
        }}
        
        /* Tables */
        QTableWidget, QTableView {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            font-size: 15px;
            gridline-color: {BORDER};
            selection-background-color: {PRIMARY};
        }}
        QTableWidget::item, QTableView::item {{
            padding: 10px;
            color: {TEXT_WHITE};
            background-color: {CARD_BG};
        }}
        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {PRIMARY};
            color: {TEXT_WHITE};
        }}
        QHeaderView::section {{
            background-color: {DARK_BG};
            color: {TEXT_GRAY};
            padding: 12px;
            border: none;
            font-size: 14px;
            font-weight: bold;
        }}
        QTableCornerButton::section {{
            background-color: {DARK_BG};
            border: none;
        }}
        
        /* Combo Box */
        QComboBox {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 16px;
            min-width: 120px;
        }}
        QComboBox:hover {{
            border-color: {PRIMARY};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            selection-background-color: {PRIMARY};
        }}
        
        /* Spin Box */
        QSpinBox, QDoubleSpinBox {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 16px;
            min-width: 100px;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {PRIMARY};
        }}
        
        /* List Widget */
        QListWidget {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            font-size: 15px;
        }}
        QListWidget::item {{
            padding: 12px;
            border-bottom: 1px solid {BORDER};
            color: {TEXT_WHITE};
        }}
        QListWidget::item:selected {{
            background-color: {PRIMARY};
            color: {TEXT_WHITE};
        }}
        QListWidget::item:hover {{
            background-color: {BORDER};
        }}
        
        /* Frames */
        QFrame {{
            background-color: {CARD_BG};
            border: 2px solid {BORDER};
            border-radius: 10px;
        }}
        
        /* Group Box */
        QGroupBox {{
            background-color: {CARD_BG};
            border: 2px solid {BORDER};
            border-radius: 10px;
            margin-top: 15px;
            padding-top: 20px;
            color: {TEXT_WHITE};
            font-size: 16px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            color: {TEXT_WHITE};
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px;
        }}
        
        /* Text Edit */
        QTextEdit, QPlainTextEdit {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            padding: 10px;
            font-size: 15px;
        }}
        
        /* Radio Button */
        QRadioButton {{
            color: {TEXT_WHITE};
            font-size: 16px;
            spacing: 8px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
        }}
        
        /* Check Box */
        QCheckBox {{
            color: {TEXT_WHITE};
            font-size: 16px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {DARKER_BG};
            color: {TEXT_GRAY};
            font-size: 14px;
            padding: 8px;
        }}
        
        /* Scroll Bars */
        QScrollBar:vertical {{
            background-color: {DARK_BG};
            width: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {BORDER};
            border-radius: 6px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {TEXT_GRAY};
        }}
        QScrollBar:horizontal {{
            background-color: {DARK_BG};
            height: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {BORDER};
            border-radius: 6px;
            min-width: 30px;
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0px;
            height: 0px;
        }}
        
        /* Dialog */
        QDialog {{
            background-color: {DARK_BG};
            color: {TEXT_WHITE};
        }}
        
        /* Message Box */
        QMessageBox {{
            background-color: {DARK_BG};
            color: {TEXT_WHITE};
        }}
        QMessageBox QLabel {{
            color: {TEXT_WHITE};
        }}
        QMessageBox QPushButton {{
            min-width: 80px;
        }}
        
        /* Menu */
        QMenu {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            padding: 5px;
        }}
        QMenu::item {{
            padding: 10px 20px;
            border-radius: 5px;
        }}
        QMenu::item:selected {{
            background-color: {PRIMARY};
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            background-color: {CARD_BG};
            border: 2px solid {BORDER};
            border-radius: 8px;
        }}
        QTabBar::tab {{
            background-color: {DARK_BG};
            color: {TEXT_GRAY};
            padding: 12px 20px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-size: 14px;
        }}
        QTabBar::tab:selected {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
        }}
        
        /* Calendar */
        QCalendarWidget {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
        }}
        QCalendarWidget QAbstractItemView {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            selection-background-color: {PRIMARY};
        }}
        
        /* Date Edit */
        QDateEdit {{
            background-color: {CARD_BG};
            color: {TEXT_WHITE};
            border: 2px solid {BORDER};
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 16px;
        }}
    """


def get_button_style(color, hover_color=None):
    """Get styled button with specific color."""
    if hover_color is None:
        hover_color = color
    return f"""
        QPushButton {{
            background-color: {color};
            color: {TEXT_WHITE};
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 16px;
            font-weight: bold;
            min-height: 40px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """
