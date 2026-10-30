"""
Employee billing window (Point of Sale).

Redesigned on the shared VendorVault design system (``src/ui/theme.py``).
Business logic is unchanged: every bill, hold/recall, stock and PDF action
still goes through ``BillingService``, ``PendingBillsManager``,
``BarcodeScanner``, ``SmartSearch`` and ``PDFGenerator`` exactly as before.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy,
    QStackedWidget, QStatusBar, QTableWidget, QToolButton, QVBoxLayout, QWidget,
)

import config
from src.logic.analytics import AnalyticsService
from src.logic.barcode_scanner import BarcodeScanner
from src.logic.billing import BillingService
from src.logic.inventory import InventoryService
from src.logic.pending_bills import PendingBillsManager
from src.logic.smart_search import QuickAccessManager, SmartSearch
from src.database.connection import db
from src.models.bill import BillItem
from src.models.employee import Employee
from src.ui import theme as T
from src.ui.widgets import (
    Avatar, Card, ChipRow, Divider, HintButton, InlineNotice, KbdHint, LogoMark, Pill, RemoveButton,
    SearchIcon, SegmentedControl, Stepper, Toast, make_button, make_label, overline,
)
from src.utils.pdf_generator import PDFGenerator

# Legacy module-level colour names (kept for anything importing them).
BG_DARK = T.BG
BG_CARD = T.SURFACE
BORDER = T.BORDER
WHITE = T.TEXT
GRAY = T.MUTED
BLUE = T.ACCENT
GREEN = T.SUCCESS
ORANGE = T.WARNING
RED = T.DANGER
PURPLE = T.ACCENT

LOW_STOCK_THRESHOLD = 10       # same threshold InventoryService uses
QUICK_ADD_SLOTS = 8
PAYMENT_MODES = ["Cash", "UPI", "Card"]   # the modes the billing flow supports


def open_file(path: str) -> None:
    """Open a file with the OS default app (Windows, macOS, Linux)."""
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def cash_suggestions(total: float) -> List[float]:
    """Quick cash chips: exact rounded up to ₹10, next ₹100, next ₹500, next ₹2,000
    (gaps filled with the next ₹50/₹200 step), smallest four distinct amounts."""
    if total <= 0:
        return []
    t = round(total, 2)
    cands = {float(math.ceil(t / s) * s) for s in (10, 100, 500, 2000, 50, 200)}
    out = sorted(cands)
    while len(out) < 4:
        out.append(float((math.floor(out[-1] / 2000) + 1) * 2000))
    return out[:4]


def short_name(employee: Employee) -> str:
    first = (employee.first_name or "").strip()
    last = (employee.last_name or "").strip()
    if first and last:
        return f"{first} {last[0]}."
    return first or last or employee.emp_id


class SearchLineEdit(QLineEdit):
    """Search field that forwards arrow keys to the results list and lets
    Ctrl+Z undo the last cart add while the field is empty."""

    navigate = Signal(int)
    undoRequested = Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Down, Qt.Key_Up):
            self.navigate.emit(1 if event.key() == Qt.Key_Down else -1)
            return
        if event.matches(QKeySequence.Undo) and not self.text():
            self.undoRequested.emit()
            return
        super().keyPressEvent(event)


class PosStatusBar(QStatusBar):
    """Status strip: scanner state, last action message, shortcut legend.

    ``showMessage`` is overridden so existing ``statusBar().showMessage()``
    calls update the 'last action' label instead of hiding the strip.
    """

    LEGEND = [("F1", "Search"), ("F2", "Qty"), ("F4", "Customer"), ("F8", "Hold"),
              ("F10", "Held bills"), ("F12", "Charge")]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSizeGripEnabled(False)
        self.setFixedHeight(48)
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(10)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {T.SUCCESS}; font-size: 10px;")
        lay.addWidget(dot)
        self.scanner_label = make_label("Scanner ready", role="muted", size=12, weight=500)
        self.scanner_label.setToolTip("Keyboard-wedge barcode scanners type into the search field")
        lay.addWidget(self.scanner_label)
        lay.addWidget(make_label("·", role="faint", size=12))
        self.message_label = make_label("Ready", role="muted", size=12, weight=500)
        self.message_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.message_label.setMinimumWidth(120)
        lay.addWidget(self.message_label, 1)
        for key, text in self.LEGEND:
            lay.addSpacing(8)
            lay.addWidget(KbdHint(key))
            lay.addWidget(make_label(text, role="muted", size=12))
        self.addPermanentWidget(box, 1)
        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(lambda: self.message_label.setText("Ready"))

    def showMessage(self, message: str, timeout: int = 0) -> None:  # noqa: N802
        self.message_label.setText(message.replace("✓ ", "").replace("⚠ ", ""))
        self.message_label.setToolTip(message)
        if timeout:
            self._clear_timer.start(timeout)

    def currentMessage(self) -> str:  # noqa: N802
        return self.message_label.text()


class BillingWindow(QMainWindow):
    """Point-of-sale window: scan/search, cart, checkout."""

    def __init__(self, employee: Employee):
        super().__init__()
        self.employee = employee

        # Services (unchanged)
        self.inventory_service = InventoryService()
        self.billing_service = BillingService()
        self.pdf_generator = PDFGenerator()
        self.smart_search = SmartSearch()
        self.barcode_scanner = BarcodeScanner()
        self.pending_bills_mgr = PendingBillsManager()

        # State
        self.cart_items: List[BillItem] = []
        self._cart_meta: List[Dict] = []          # product info per cart line (barcode, stock, category)
        self._search_results: List[Dict] = []
        self._current_product: Optional[Dict] = None
        self._undo_stack: List[Dict] = []
        self._quick_products: List[Dict] = []
        self._selected_row: int = -1

        self.setup_ui()
        self.setup_shortcuts()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        self.update_pending_count()
        self.refresh_invoice_preview()
        self.load_quick_add()
        self.update_totals()
        QTimer.singleShot(100, self.focus_search)

    # ------------------------------------------------------------------ UI
    def setup_ui(self) -> None:
        self.setWindowTitle(config.APP_NAME)
        self.setMinimumSize(1200, 720)
        self.showMaximized()

        central = QWidget()
        central.setObjectName("qt_central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._create_header())
        root.addWidget(Divider())

        content = QHBoxLayout()
        content.setContentsMargins(24, 20, 24, 20)
        content.setSpacing(20)
        content.addWidget(self._create_left_panel(), 900)
        content.addWidget(self._create_right_panel(), 472)
        root.addLayout(content, 1)

        self.setStatusBar(PosStatusBar(self))
        self.statusBar().showMessage("Ready")

        # Overlays (children of the central widget, positioned manually)
        self.search_results = QListWidget(central)
        self.search_results.setObjectName("SearchResults")
        self.search_results.setStyleSheet(
            f"QListWidget#SearchResults {{ background: {T.SURFACE_2}; border: 1px solid {T.BORDER_2};"
            f" border-radius: 10px; padding: 6px; }}"
            f"QListWidget#SearchResults::item {{ border: none; border-radius: 8px; padding: 0; margin: 1px 0; }}"
            f"QListWidget#SearchResults::item:selected {{ background: {T.SURFACE_3}; }}"
        )
        self.search_results.setFocusPolicy(Qt.StrongFocus)
        self.search_results.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.search_results.hide()
        self.search_results.itemClicked.connect(self.on_result_clicked)
        self.search_results.itemDoubleClicked.connect(self.on_result_double_clicked)
        self.search_results.itemActivated.connect(self.on_result_clicked)
        self.search_results.installEventFilter(self)

        self.customer_popover = self._create_customer_popover(central)
        self.toast = Toast(central)
        central.installEventFilter(self)
        self._ui_ready = True

    def _create_header(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(66)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(0)

        left = QHBoxLayout()
        left.setSpacing(10)
        left.addWidget(LogoMark(26))
        left.addWidget(make_label(config.APP_NAME, size=15, weight=600))
        left.addSpacing(6)
        sep = QFrame()
        sep.setFixedSize(1, 16)
        sep.setStyleSheet(f"background: {T.BORDER};")
        left.addWidget(sep)
        left.addSpacing(6)
        self.counter_label = make_label(getattr(config, "COUNTER_NAME", "Counter 1"), role="muted", size=13, weight=500)
        left.addWidget(self.counter_label)
        left_w = QWidget()
        left_w.setLayout(left)
        left.setContentsMargins(0, 0, 0, 0)

        # Search field with icon and F1 hint
        search_box = QFrame()
        search_box.setObjectName("SearchBox")
        search_box.setFixedHeight(38)
        search_box.setMinimumWidth(380)
        search_box.setMaximumWidth(560)
        search_box.setAttribute(Qt.WA_StyledBackground, True)
        self._search_box = search_box
        self._set_search_box_focus(False)
        sl = QHBoxLayout(search_box)
        sl.setContentsMargins(14, 0, 10, 0)
        sl.setSpacing(10)
        sl.addWidget(SearchIcon())
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("Scan barcode or search products")
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; padding: 0; font-size: 14px; color: {T.TEXT}; }}")
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.on_search_enter)
        self.search_input.navigate.connect(self._navigate_results)
        self.search_input.undoRequested.connect(self.undo_last_add)
        self.search_input.installEventFilter(self)
        sl.addWidget(self.search_input, 1)
        sl.addWidget(KbdHint("F1"))

        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        self.pending_btn = Pill("0 on hold", tone="neutral")
        self.pending_btn.setToolTip("Held bills (F10)")
        self.pending_btn.clicked.connect(self.show_pending_bills)
        right.addWidget(self.pending_btn)
        right.addSpacing(8)
        self.time_label = make_label("", role="muted", size=13, weight=500)
        right.addWidget(self.time_label)

        # Cashier block opens a menu (switch to admin, log out)
        self.user_btn = QToolButton()
        self.user_btn.setCursor(Qt.PointingHandCursor)
        self.user_btn.setPopupMode(QToolButton.InstantPopup)
        self.user_btn.setStyleSheet(
            "QToolButton { background: transparent; border: 1px solid transparent; border-radius: 10px; padding: 2px 6px; }"
            f"QToolButton:hover {{ background: {T.SURFACE_2}; border-color: {T.BORDER}; }}"
            "QToolButton::menu-indicator { image: none; width: 0; }")
        ul = QHBoxLayout(self.user_btn)
        ul.setContentsMargins(6, 4, 10, 4)
        ul.setSpacing(10)
        av = Avatar(self.employee.get_full_name(), 30)
        av.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        ul.addWidget(av)
        names = QVBoxLayout()
        names.setSpacing(0)
        n1 = make_label(short_name(self.employee), size=13, weight=500)
        role_text = self.employee.designation or self.employee.role or "Cashier"
        n2 = make_label(role_text, role="faint", size=11)
        for w in (n1, n2):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            names.addWidget(w)
        ul.addLayout(names)
        self.user_btn.setMinimumSize(ul.sizeHint())
        menu = QMenu(self.user_btn)
        if self.employee.role and self.employee.role.lower() == "admin":
            menu.addAction("Switch to admin dashboard", self.switch_to_admin)
            menu.addSeparator()
        menu.addAction("Log out", self.handle_logout)
        self.user_menu = menu
        self.user_btn.setMenu(menu)
        right.addWidget(self.user_btn)
        right_w = QWidget()
        right_w.setLayout(right)

        lay.addWidget(left_w, 1)
        lay.addWidget(search_box, 3)
        lay.addWidget(right_w, 1, Qt.AlignRight)
        return bar

    def _set_search_box_focus(self, focused: bool) -> None:
        self._search_box.setStyleSheet(
            f"QFrame#SearchBox {{ background: {T.SURFACE_2}; border: 1px solid {T.ACCENT if focused else T.BORDER};"
            f" border-radius: 10px; }}")

    def _create_left_panel(self) -> QWidget:
        card = Card(padding=(24, 22, 24, 22), spacing=0)
        self.sale_card = card

        # Header row
        head = QHBoxLayout()
        head.setSpacing(14)
        head.addWidget(make_label("Current sale", size=17, weight=600))
        self.invoice_label = make_label("", role="mono")
        head.addWidget(self.invoice_label)
        head.addStretch(1)
        self.customer_btn = HintButton("+  Add customer", "F4", center=False)
        self.customer_btn.setFixedHeight(32)
        self.customer_btn.setMinimumWidth(172)
        self.customer_btn.set_text_style(f"color: {T.MUTED}; font-size: 13px; font-weight: 500;")
        self.customer_btn.clicked.connect(self.toggle_customer_popover)
        head.addWidget(self.customer_btn)
        card.body.addLayout(head)
        card.body.addSpacing(18)

        # Cart table
        self.cart_title = QLabel()   # legacy attribute; item count also shown in checkout
        self.cart_title.hide()
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(["ITEM", "", "QTY", "PRICE", "TOTAL", ""])
        hh = self.cart_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        for c, w in ((1, 90), (2, 132), (3, 110), (4, 130), (5, 64)):
            hh.setSectionResizeMode(c, QHeaderView.Fixed)
            self.cart_table.setColumnWidth(c, w)
        hh.setHighlightSections(False)
        hh.setDefaultAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        for c, align in ((2, Qt.AlignCenter), (3, Qt.AlignRight | Qt.AlignVCenter), (4, Qt.AlignRight | Qt.AlignVCenter)):
            it = self.cart_table.horizontalHeaderItem(c)
            it.setTextAlignment(align)
        hf = hh.font()
        hf.setPixelSize(11)
        hf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        hh.setFont(hf)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.verticalHeader().setDefaultSectionSize(66)
        self.cart_table.setShowGrid(False)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cart_table.setFocusPolicy(Qt.StrongFocus)
        self.cart_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cart_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.cart_table.setStyleSheet(
            f"QTableWidget {{ background: transparent; border: none; selection-background-color: transparent; }}"
            f"QTableWidget::item {{ border: none; border-bottom: 1px solid {T.SURFACE_3}; padding: 0; }}"
            f"QTableWidget::item:selected {{ background: {T.rgba(T.ACCENT, 0.065)}; border-bottom: 1px solid transparent; }}"  # drawn twice by Qt (row + item) ≈ 12%
            f"QHeaderView::section {{ background: transparent; color: {T.FAINT}; border: none;"
            f" border-bottom: 1px solid {T.BORDER}; padding: 0 0 10px 0; font-size: 11px; font-weight: 600; }}")
        self.cart_table.itemSelectionChanged.connect(self._on_cart_selection)
        card.body.addWidget(self.cart_table, 1)

        # Empty state
        self.empty_state = QWidget()
        es = QVBoxLayout(self.empty_state)
        es.setContentsMargins(0, 24, 0, 24)
        es.addStretch(1)
        es.addWidget(make_label("No items yet", size=15, weight=600, align=Qt.AlignCenter))
        es.addWidget(make_label("Scan a barcode, search above (F1) or tap a quick-add product.",
                                role="muted", align=Qt.AlignCenter))
        es.addStretch(1)
        card.body.addWidget(self.empty_state, 1)

        # Last-action notice (Added N × item · Undo)
        card.body.addSpacing(10)
        self.notice = InlineNotice()
        self.notice.actionClicked.connect(self.undo_last_add)
        card.body.addWidget(self.notice)

        # Quick add grid
        card.body.addSpacing(16)
        card.body.addWidget(Divider())
        card.body.addSpacing(14)
        qa_head = QHBoxLayout()
        qa_head.addWidget(make_label("Quick add", role="muted", size=13, weight=600))
        qa_head.addStretch(1)
        self.quick_caption = make_label("Your best sellers today", role="faint", size=12)
        qa_head.addWidget(self.quick_caption)
        card.body.addLayout(qa_head)
        card.body.addSpacing(12)
        self.quick_grid = QGridLayout()
        self.quick_grid.setHorizontalSpacing(12)
        self.quick_grid.setVerticalSpacing(12)
        card.body.addLayout(self.quick_grid)
        return card

    def _create_right_panel(self) -> QWidget:
        card = Card(padding=(24, 22, 24, 24), spacing=0)
        card.setMinimumWidth(420)
        card.setMaximumWidth(520)

        head = QHBoxLayout()
        head.addWidget(make_label("Checkout", size=17, weight=600))
        head.addStretch(1)
        self.items_count_label = make_label("0 items", role="faint", size=12, weight=500)
        head.addWidget(self.items_count_label)
        card.body.addLayout(head)
        card.body.addSpacing(22)

        # Subtotal
        self.subtotal_label = make_label("₹0.00", size=14, weight=500, align=Qt.AlignRight | Qt.AlignVCenter)
        card.body.addLayout(self._summary_row("Subtotal", self.subtotal_label))
        card.body.addSpacing(10)

        # Discount (link → editable amount)
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setMaximum(99999)
        self.discount_input.setDecimals(2)
        self.discount_input.setPrefix("₹ ")
        self.discount_input.setProperty("noButtons", True)
        self.discount_input.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.discount_input.setFixedSize(120, 30)
        self.discount_input.setStyleSheet(
            "QDoubleSpinBox { padding: 2px 8px; font-size: 13px; }"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; margin: 0px; border: none; }"
            "QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow { image: none; width: 0px; height: 0px; }")
        self.discount_input.valueChanged.connect(self.update_totals)
        self.discount_input.installEventFilter(self)
        self.discount_add_btn = make_button("Add", variant="link")
        self.discount_add_btn.setToolTip("Add a discount amount (₹)")
        self.discount_add_btn.clicked.connect(self._edit_discount)
        self.discount_stack = QStackedWidget()
        self.discount_stack.setFixedHeight(30)
        self.discount_stack.setStyleSheet("QStackedWidget { background: transparent; }")
        for w in (self.discount_add_btn, self.discount_input):
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addStretch(1)
            hl.addWidget(w)
            self.discount_stack.addWidget(holder)
        self.discount_label = self.discount_stack   # legacy attribute name
        card.body.addLayout(self._summary_row("Discount", self.discount_stack))
        card.body.addSpacing(10)

        # Tax (editable rate)
        self.tax_spin = QDoubleSpinBox()
        self.tax_spin.setMaximum(100)
        self.tax_spin.setDecimals(1)
        self.tax_spin.setValue(config.DEFAULT_GST_RATE)
        self.tax_spin.setSuffix("%")
        self.tax_spin.setProperty("noButtons", True)
        self.tax_spin.setFixedSize(66, 30)
        self.tax_spin.setToolTip("Tax rate (%)")
        self.tax_spin.setStyleSheet(
            f"QDoubleSpinBox {{ background: transparent; border: 1px solid transparent; padding: 0 4px; margin: 0;"
            f" color: {T.MUTED}; font-size: 14px; }}"
            f"QDoubleSpinBox:hover {{ border-color: {T.BORDER}; background: {T.SURFACE_2}; }}"
            f"QDoubleSpinBox:focus {{ border-color: {T.ACCENT}; background: {T.SURFACE_2}; color: {T.TEXT}; }}"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; margin: 0px; border: none; }"
            "QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow { image: none; width: 0px; height: 0px; }")
        self.tax_spin.valueChanged.connect(self.update_totals)
        self.tax_label = make_label("₹0.00", size=14, weight=500, align=Qt.AlignRight | Qt.AlignVCenter)
        tax_row = QHBoxLayout()
        tax_row.setSpacing(0)
        tax_row.addWidget(make_label("GST", role="muted", size=14))
        tax_row.addSpacing(2)
        tax_row.addWidget(self.tax_spin)
        tax_row.addStretch(1)
        tax_row.addWidget(self.tax_label)
        card.body.addLayout(tax_row)
        card.body.addSpacing(14)
        card.body.addWidget(Divider())
        card.body.addSpacing(14)

        # Total
        total_row = QHBoxLayout()
        total_row.addWidget(make_label("Total", role="muted", size=14, weight=500), 0, Qt.AlignTop)
        total_row.addStretch(1)
        self.total_label = make_label("₹0.00", size=40, weight=700, align=Qt.AlignRight | Qt.AlignVCenter)
        f = self.total_label.font()
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -1.2)
        self.total_label.setFont(f)
        total_row.addWidget(self.total_label)
        card.body.addLayout(total_row)
        card.body.addSpacing(22)

        # Payment mode
        card.body.addWidget(overline("Payment"))
        card.body.addSpacing(10)
        self.payment_mode = SegmentedControl(PAYMENT_MODES)
        self.payment_mode.currentChanged.connect(self.on_mode_changed)
        card.body.addWidget(self.payment_mode)
        card.body.addSpacing(18)

        # Cash received + chips + change
        self.cash_container = QWidget()
        cl = QVBoxLayout(self.cash_container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(10)
        cl.addWidget(make_label("Cash received", role="muted", size=13, weight=500))
        cash_box = QFrame()
        cash_box.setObjectName("CashBox")
        cash_box.setAttribute(Qt.WA_StyledBackground, True)
        cash_box.setFixedHeight(50)
        self._cash_box = cash_box
        self._set_cash_box_focus(False)
        cbl = QHBoxLayout(cash_box)
        cbl.setContentsMargins(16, 0, 14, 0)
        cbl.setSpacing(8)
        cbl.addWidget(make_label("₹", role="faint", size=17, weight=500))
        self.cash_input = QLineEdit()
        self.cash_input.setPlaceholderText("0")
        self.cash_input.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: none; padding: 0; font-size: 19px; font-weight: 600; color: {T.TEXT}; }}")
        self.cash_input.textChanged.connect(self.calculate_change)
        self.cash_input.returnPressed.connect(lambda: self.finalize_bill(print_pdf=True))
        self.cash_input.installEventFilter(self)
        cbl.addWidget(self.cash_input, 1)
        cl.addWidget(cash_box)
        self.cash_chips = ChipRow()
        self.cash_chips.chipClicked.connect(self._apply_cash_chip)
        cl.addWidget(self.cash_chips)
        cl.addSpacing(4)
        self.change_panel = QFrame()
        self.change_panel.setObjectName("ChangePanel")
        self.change_panel.setAttribute(Qt.WA_StyledBackground, True)
        self.change_panel.setFixedHeight(46)
        chl = QHBoxLayout(self.change_panel)
        chl.setContentsMargins(18, 0, 18, 0)
        self.change_caption = QLabel("Change due")
        self.change_label = QLabel("₹0.00")
        chl.addWidget(self.change_caption)
        chl.addStretch(1)
        chl.addWidget(self.change_label)
        cl.addWidget(self.change_panel)
        card.body.addWidget(self.cash_container)
        self._set_change_state("idle")

        # Non-cash note
        self.noncash_note = make_label("", role="muted", size=13)
        self.noncash_note.setWordWrap(True)
        self.noncash_note.hide()
        card.body.addWidget(self.noncash_note)

        card.body.addStretch(1)
        card.body.addSpacing(16)

        # Primary action
        self.print_btn = HintButton("Charge ₹0.00", "F12", variant="primary", on_accent=True)
        self.print_btn.setFixedHeight(56)
        self.print_btn.setStyleSheet("QPushButton { border-radius: 12px; }")
        self.print_btn.set_text_style("color: #FFFFFF; font-size: 16px; font-weight: 600;")
        self.print_btn.setToolTip("Save the bill, generate the PDF invoice and open it (F12)")
        self.print_btn.clicked.connect(lambda: self.finalize_bill(print_pdf=True))
        card.body.addWidget(self.print_btn)
        card.body.addSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.hold_btn = HintButton("Hold", "F8")
        self.hold_btn.clicked.connect(self.save_pending)
        self.save_btn = HintButton("Save only", "F9")
        self.save_btn.setToolTip("Save the bill without generating a PDF (F9)")
        self.save_btn.clicked.connect(lambda: self.finalize_bill(print_pdf=False))
        self.clear_btn = HintButton("Clear", "Esc")
        self.clear_btn.set_text_style(f"color: {T.DANGER}; font-weight: 500;")
        self.clear_btn.clicked.connect(self.clear_cart)
        for b in (self.hold_btn, self.save_btn, self.clear_btn):
            b.setFixedHeight(44)
            b.setStyleSheet("QPushButton { border-radius: 10px; }")
            row.addWidget(b, 1)
        card.body.addLayout(row)
        return card

    def _summary_row(self, caption: str, value_widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(make_label(caption, role="muted", size=14))
        row.addStretch(1)
        row.addWidget(value_widget)
        return row

    def _set_cash_box_focus(self, focused: bool) -> None:
        self._cash_box.setStyleSheet(
            f"QFrame#CashBox {{ background: {T.SURFACE_2}; border: {'1.5px' if focused else '1px'} solid"
            f" {T.ACCENT if focused else T.BORDER}; border-radius: 10px; }}")

    def _set_change_state(self, state: str, amount: float = 0.0) -> None:
        if state == "change":
            fg, bg, cap = T.SUCCESS, T.SUCCESS_SOFT, "Change due"
        elif state == "due":
            fg, bg, cap = T.WARNING, T.WARNING_SOFT, "Still due"
        else:
            fg, bg, cap = T.MUTED, T.SURFACE_2, "Change due"
        self.change_panel.setStyleSheet(f"QFrame#ChangePanel {{ background: {bg}; border: none; border-radius: 10px; }}")
        self.change_caption.setText(cap)
        self.change_caption.setStyleSheet(f"color: {fg}; font-size: 14px; font-weight: 500;")
        self.change_label.setText(T.money(amount))
        self.change_label.setStyleSheet(f"color: {fg}; font-size: 18px; font-weight: 700;")

    def _create_customer_popover(self, parent: QWidget) -> QFrame:
        pop = QFrame(parent)
        pop.setObjectName("CustomerPopover")
        pop.setAttribute(Qt.WA_StyledBackground, True)
        pop.setStyleSheet(f"QFrame#CustomerPopover {{ background: {T.SURFACE_2}; border: 1px solid {T.BORDER_2}; border-radius: 12px; }}")
        pop.setFixedWidth(320)
        lay = QVBoxLayout(pop)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(8)
        lay.addWidget(make_label("Customer", size=14, weight=600))
        lay.addWidget(make_label("Optional. Printed on the invoice.", role="faint", size=12))
        lay.addSpacing(4)
        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("Customer name")
        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("Phone")
        self.customer_phone.setMaxLength(15)
        for w in (self.customer_name, self.customer_phone):
            w.setStyleSheet(f"QLineEdit {{ background: {T.SURFACE}; }}")
            w.returnPressed.connect(self.close_customer_popover)
            lay.addWidget(w)
        self.customer_name.textChanged.connect(self._update_customer_button)
        self.customer_phone.textChanged.connect(self._update_customer_button)
        btns = QHBoxLayout()
        clear = make_button("Remove", variant="ghost", size="sm")
        clear.clicked.connect(lambda: (self.customer_name.clear(), self.customer_phone.clear()))
        done = make_button("Done", size="sm")
        done.clicked.connect(self.close_customer_popover)
        btns.addWidget(clear)
        btns.addStretch(1)
        btns.addWidget(done)
        lay.addSpacing(4)
        lay.addLayout(btns)
        pop.adjustSize()
        pop.hide()
        return pop

    # ---------------------------------------------------------- geometry
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        et = event.type()
        if not getattr(self, "_ui_ready", False):   # still building the UI
            return super().eventFilter(obj, event)
        if obj is self.centralWidget() and et == QEvent.Resize:
            self._position_overlays()
        elif obj is self.search_input and et in (QEvent.FocusIn, QEvent.FocusOut):
            self._set_search_box_focus(et == QEvent.FocusIn)
        elif obj is self.cash_input and et in (QEvent.FocusIn, QEvent.FocusOut):
            self._set_cash_box_focus(et == QEvent.FocusIn)
        elif obj is self.discount_input and et == QEvent.FocusOut:
            if self.discount_input.value() <= 0:
                self.discount_stack.setCurrentIndex(0)
        elif obj is self.search_results and et == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                item = self.search_results.currentItem()
                if item:
                    self.on_result_clicked(item)
                return True
            if event.key() == Qt.Key_Escape:
                self.clear_selection()
                self.focus_search()
                return True
            if event.key() == Qt.Key_Up and self.search_results.currentRow() <= 0:
                self.focus_search()
                return True
            if event.text() and event.text().isprintable() and event.key() not in (Qt.Key_Up, Qt.Key_Down):
                self.search_input.setFocus()
                self.search_input.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)

    def _position_overlays(self) -> None:
        central = self.centralWidget()
        if central is None:
            return
        box = self._search_box
        top_left = box.mapTo(central, QPoint(0, box.height() + 6))
        self.search_results.setGeometry(top_left.x(), top_left.y(), box.width(), self.search_results.height())
        btn = self.customer_btn
        p = btn.mapTo(central, QPoint(btn.width() - self.customer_popover.width(), btn.height() + 6))
        self.customer_popover.move(p)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        QTimer.singleShot(0, self._position_overlays)

    # ---------------------------------------------------------- shortcuts
    def setup_shortcuts(self) -> None:
        """Keyboard shortcuts.

        Legacy keys kept: F2 (focus qty / search), F5 & F7 (print bill),
        F10 (held bills), Esc (clear search; clears the sale when the search
        is empty). New: F1 search, F4 customer, F8 hold, F9 save only,
        F12 charge, Ctrl+Z undo, Del remove line, +/- qty, 1-8 quick add.
        """
        self._shortcuts: List[QShortcut] = []
        shortcuts = {
            'F1': self.focus_search,
            'F2': self.focus_quantity,
            'F4': self.toggle_customer_popover,
            'F5': lambda: self.finalize_bill(print_pdf=True),
            'F7': lambda: self.finalize_bill(print_pdf=True),
            'F8': self.save_pending,
            'F9': lambda: self.finalize_bill(print_pdf=False),
            'F10': self.show_pending_bills,
            'F12': lambda: self.finalize_bill(print_pdf=True),
            'Escape': self.handle_escape,
            'Ctrl+Z': self.undo_last_add,
            'Delete': self.remove_selected_item,
            '+': lambda: self.change_selected_qty(1),
            '-': lambda: self.change_selected_qty(-1),
        }
        for i in range(1, QUICK_ADD_SLOTS + 1):
            shortcuts[str(i)] = (lambda idx=i - 1: self.quick_add(idx))
        for key, func in shortcuts.items():
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(func)
            self._shortcuts.append(sc)

    def focus_search(self) -> None:
        self.close_customer_popover()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def focus_quantity(self) -> None:
        """F2: focus the quantity of the selected (or last) cart line."""
        if not self.cart_items:
            self.focus_search()
            return
        row = self._selected_row if 0 <= self._selected_row < len(self.cart_items) else len(self.cart_items) - 1
        self.cart_table.selectRow(row)
        stepper = self._stepper(row)
        if stepper:
            stepper.edit.setFocus()
            stepper.edit.selectAll()

    def handle_escape(self) -> None:
        if self.customer_popover.isVisible():
            self.close_customer_popover()
            return
        if self.search_input.text() or self.search_results.isVisible() or self._current_product:
            self.clear_selection()
            self.focus_search()
            return
        if self.cart_items:
            self.clear_cart()

    # ---------------------------------------------------------- search
    def on_search_changed(self, text: str) -> None:
        if len(text) < 1:
            self.search_results.hide()
            self._search_results = []
            return

        # Complete barcode (8-13 digits) → direct lookup, add straight to the cart
        if text.isdigit() and 8 <= len(text) <= 13:
            result = self.barcode_scanner.process_scan(text)
            if result['success']:
                product = result['product']
                self.search_input.blockSignals(True)
                self.search_input.clear()
                self.search_input.blockSignals(False)
                self.search_results.hide()
                self._search_results = []
                self.add_product(product, 1, source="Scanned")
                return

        results = self.smart_search.search_instant(text, limit=6)
        self._search_results = results
        self._populate_results(results)

    def _populate_results(self, results: List[Dict]) -> None:
        self.search_results.clear()
        for p in results:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 48))
            self.search_results.addItem(item)
            self.search_results.setItemWidget(item, self._result_row(p))
        if results:
            self.search_results.setCurrentRow(0)
            h = min(len(results), 6) * 50 + 14
            self.search_results.resize(self._search_box.width(), h)
            self._position_overlays()
            self.search_results.raise_()
            self.search_results.show()
        else:
            self.search_results.hide()

    def _result_row(self, p: Dict) -> QWidget:
        w = QWidget()
        w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 4, 12, 4)
        lay.setSpacing(12)
        col = QVBoxLayout()
        col.setSpacing(1)
        out = p.get('stock', 0) <= 0
        name = make_label(p['product_name'], size=13, weight=500)
        if out:
            name.setStyleSheet(f"color: {T.FAINT}; font-size: 13px; font-weight: 500;")
        col.addWidget(name)
        sub = " · ".join(x for x in (p.get('category') or '', p.get('barcode') or '') if x)
        col.addWidget(make_label(sub, role="faint", size=11))
        lay.addLayout(col, 1)
        stock = p.get('stock', 0)
        if stock <= 0:
            st = make_label("Out of stock", tone="danger", size=12, weight=500)
        elif stock <= LOW_STOCK_THRESHOLD:
            st = make_label(f"{stock} left", tone="warning", size=12, weight=500)
        else:
            st = make_label(f"{stock} in stock", role="faint", size=12)
        lay.addWidget(st)
        lay.addSpacing(8)
        lay.addWidget(make_label(T.money(p.get('mrp') or 0), size=13, weight=600))
        return w

    def _navigate_results(self, step: int) -> None:
        if not self.search_results.isVisible() or self.search_results.count() == 0:
            if step > 0 and self.cart_items:
                self.cart_table.setFocus()
            return
        row = max(0, min(self.search_results.count() - 1, self.search_results.currentRow() + step))
        self.search_results.setCurrentRow(row)
        self.search_results.setFocus()

    def on_search_enter(self) -> None:
        """Enter in search: add the highlighted (or first) result to the cart."""
        if self._search_results:
            row = self.search_results.currentRow() if self.search_results.isVisible() else 0
            row = row if 0 <= row < len(self._search_results) else 0
            self._select_product(self._search_results[row])
            self.add_to_cart()
        elif self._current_product:
            self.add_to_cart()

    def on_result_clicked(self, item: QListWidgetItem) -> None:
        idx = self.search_results.row(item)
        if 0 <= idx < len(self._search_results):
            self._select_product(self._search_results[idx])
            self.add_to_cart()

    def on_result_double_clicked(self, item: QListWidgetItem) -> None:
        # Single click already adds; ignore the second click of a double-click.
        pass

    def _select_product(self, product: Dict) -> None:
        self._current_product = product
        self.search_results.hide()
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self._search_results = []

    # ---------------------------------------------------------- cart
    def add_to_cart(self) -> None:
        """Add the currently selected product (qty 1) to the cart."""
        if not self._current_product:
            self.statusBar().showMessage("⚠ Select a product first")
            self.focus_search()
            return
        product = self._current_product
        self._current_product = None
        self.add_product(product, 1)

    def add_product(self, product: Dict, qty: int = 1, source: str = "Added") -> bool:
        """Add ``qty`` of ``product`` to the cart, merging with an existing line."""
        name = product['product_name']
        stock = int(product.get('stock', 0) or 0)
        idx = next((i for i, it in enumerate(self.cart_items) if it.product_name == name), -1)
        in_cart = self.cart_items[idx].quantity if idx >= 0 else 0
        if in_cart + qty > stock:
            msg = f"Only {stock} of {name} in stock" if stock > 0 else f"{name} is out of stock"
            self.notice.show_message(msg, tone="warning")
            self.statusBar().showMessage(f"⚠ {msg}")
            self.focus_search()
            return False
        if idx >= 0:
            self.cart_items[idx].quantity += qty
            self._cart_meta[idx].update({k: product.get(k) for k in ('barcode', 'category', 'stock') if product.get(k) is not None})
            created = False
        else:
            self.cart_items.append(BillItem(name, qty, product['mrp']))
            self._cart_meta.append({'barcode': product.get('barcode', ''), 'category': product.get('category', ''),
                                    'stock': stock})
            idx = len(self.cart_items) - 1
            created = True
        self._undo_stack.append({'name': name, 'qty': qty, 'created': created})
        del self._undo_stack[:-30]
        self.update_cart_display(select=idx)
        self.update_totals()
        self.focus_search()
        self.notice.show_message(f"{source} {qty} × {name}", action="Undo  Ctrl+Z")
        self.statusBar().showMessage(f"✓ {source} {qty} x {name}")
        return True

    def undo_last_add(self) -> None:
        if not self._undo_stack:
            self.statusBar().showMessage("Nothing to undo")
            return
        last = self._undo_stack.pop()
        idx = next((i for i, it in enumerate(self.cart_items) if it.product_name == last['name']), -1)
        if idx < 0:
            return
        item = self.cart_items[idx]
        if last['created'] or item.quantity <= last['qty']:
            self.cart_items.pop(idx)
            self._cart_meta.pop(idx)
        else:
            item.quantity -= last['qty']
        self.update_cart_display(select=min(idx, len(self.cart_items) - 1))
        self.update_totals()
        self.notice.show_message(f"Undid {last['qty']} × {last['name']}", tone="warning", timeout_ms=3000)
        self.statusBar().showMessage(f"Undid {last['qty']} x {last['name']}")

    def _stepper(self, row: int) -> Optional[Stepper]:
        w = self.cart_table.cellWidget(row, 2)
        return w.findChild(Stepper) if w else None

    def update_cart_display(self, select: Optional[int] = None) -> None:
        if select is None:
            select = self._selected_row
        self.cart_table.blockSignals(True)
        self.cart_table.clearContents()
        self.cart_table.setRowCount(len(self.cart_items))
        self.cart_title.setText(f"CART ({len(self.cart_items)} items)")
        for i, item in enumerate(self.cart_items):
            meta = self._cart_meta[i] if i < len(self._cart_meta) else {}
            self.cart_table.setCellWidget(i, 0, self._item_cell(item, meta))
            self.cart_table.setCellWidget(i, 1, self._stock_cell(item, meta))
            self.cart_table.setCellWidget(i, 2, self._qty_cell(i, item, meta))
            self.cart_table.setCellWidget(i, 3, self._text_cell(T.money(item.unit_price), T.MUTED, 14, 400))
            self.cart_table.setCellWidget(i, 4, self._text_cell(T.money(item.get_total()), T.TEXT, 15, 600))
            rm_holder = QWidget()
            rl = QHBoxLayout(rm_holder)
            rl.setContentsMargins(0, 0, 8, 0)
            rl.addStretch(1)
            rm = RemoveButton()
            rm.clicked.connect(lambda _=False, idx=i: self.remove_item(idx))
            rl.addWidget(rm)
            rm.setVisible(False)
            self.cart_table.setCellWidget(i, 5, rm_holder)
        self.cart_table.blockSignals(False)
        has = bool(self.cart_items)
        self.cart_table.setVisible(has)
        self.empty_state.setVisible(not has)
        if has:
            sel = select if select is not None and 0 <= select < len(self.cart_items) else len(self.cart_items) - 1
            self.cart_table.selectRow(sel)
            self._apply_row_selection(sel)
            self.cart_table.scrollTo(self.cart_table.model().index(sel, 0))
        else:
            self._selected_row = -1

    def _item_cell(self, item: BillItem, meta: Dict) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(14)
        ini = QLabel((item.product_name.strip()[:1] or "?").upper())
        ini.setFixedSize(38, 38)
        ini.setAlignment(Qt.AlignCenter)
        ini.setStyleSheet(f"background: {T.SURFACE_3}; border: 1px solid {T.BORDER}; border-radius: 9px;"
                          f" color: {T.MUTED}; font-size: 14px; font-weight: 600;")
        lay.addWidget(ini)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)
        name = make_label(item.product_name, size=15, weight=500)
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        name.setToolTip(item.product_name)
        col.addStretch(1)
        col.addWidget(name)
        sub = " · ".join(x for x in (meta.get('category') or '', meta.get('barcode') or '') if x)
        sl = make_label(sub or "—", role="faint", size=12)
        sl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(sl)
        col.addStretch(1)
        lay.addLayout(col, 1)
        return w

    def _stock_cell(self, item: BillItem, meta: Dict) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        stock = meta.get('stock')
        if stock is not None and stock <= LOW_STOCK_THRESHOLD:
            lbl = make_label(f"{stock} left", tone="warning" if stock > 0 else "danger", size=12, weight=500)
            lbl.setToolTip(f"Low stock: {stock} in inventory")
            lay.addWidget(lbl)
        lay.addStretch(1)
        return w

    def _qty_cell(self, row: int, item: BillItem, meta: Dict) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        stock = meta.get('stock')
        st = Stepper(item.quantity, 1, max(item.quantity, int(stock)) if stock else 9999)
        st.valueChanged.connect(lambda v, r=row: self.set_item_quantity(r, v))
        st.edit.installEventFilter(self)
        lay.addStretch(1)
        lay.addWidget(st)
        lay.addStretch(1)
        return w

    def _text_cell(self, text: str, color: str, size: int, weight: int) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 4, 0)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight};")
        lay.addWidget(lbl)
        return w

    def _on_cart_selection(self) -> None:
        rows = self.cart_table.selectionModel().selectedRows()
        self._apply_row_selection(rows[0].row() if rows else -1)

    def _apply_row_selection(self, row: int) -> None:
        self._selected_row = row
        for r in range(self.cart_table.rowCount()):
            holder = self.cart_table.cellWidget(r, 5)
            if holder:
                btn = holder.findChild(RemoveButton)
                if btn:
                    btn.setVisible(r == row)
            st = self._stepper(r)
            if st:
                st.set_selected(r == row)

    def set_item_quantity(self, row: int, qty: int) -> None:
        if not (0 <= row < len(self.cart_items)):
            return
        meta = self._cart_meta[row]
        stock = meta.get('stock')
        if stock is not None and qty > stock:
            qty = int(stock)
            self.notice.show_message(f"Only {stock} of {self.cart_items[row].product_name} in stock", tone="warning")
        self.cart_items[row].quantity = max(1, qty)
        # Update the line total in place (avoid rebuilding the row under the cursor)
        self.cart_table.setCellWidget(row, 4, self._text_cell(T.money(self.cart_items[row].get_total()), T.TEXT, 15, 600))
        self.cart_table.selectRow(row)
        self.update_totals()

    def change_selected_qty(self, delta: int) -> None:
        if not (0 <= self._selected_row < len(self.cart_items)):
            return
        st = self._stepper(self._selected_row)
        if st:
            st.setValue(st.value() + delta)

    def remove_selected_item(self) -> None:
        if 0 <= self._selected_row < len(self.cart_items):
            self.remove_item(self._selected_row)

    def remove_item(self, idx: int) -> None:
        if 0 <= idx < len(self.cart_items):
            removed = self.cart_items.pop(idx)
            if idx < len(self._cart_meta):
                self._cart_meta.pop(idx)
            self._undo_stack = [u for u in self._undo_stack if u['name'] != removed.product_name]
            self.update_cart_display(select=min(idx, len(self.cart_items) - 1))
            self.update_totals()
            self.statusBar().showMessage(f"Removed {removed.product_name}")

    # ---------------------------------------------------------- totals
    def _compute(self):
        subtotal = sum(i.get_total() for i in self.cart_items)
        discount = self.discount_input.value()
        tax_rate = self.tax_spin.value()
        taxable = max(0, subtotal - discount)
        tax = taxable * (tax_rate / 100)
        total = subtotal - discount + tax
        return subtotal, discount, tax_rate, tax, total

    def update_totals(self) -> None:
        qty = sum(i.quantity for i in self.cart_items)
        self.items_count_label.setText(f"{qty} item{'s' if qty != 1 else ''}")
        if not self.cart_items:
            self.subtotal_label.setText("₹0.00")
            self.tax_label.setText("₹0.00")
            self.total_label.setText("₹0.00")
            self.print_btn.setText("Charge")
            self.cash_chips.set_amounts([])
            self.calculate_change(self.cash_input.text())
            return
        subtotal, discount, tax_rate, tax, total = self._compute()
        self.subtotal_label.setText(T.money(subtotal))
        if discount > 0 and self.discount_stack.currentIndex() == 0:
            self.discount_stack.setCurrentIndex(1)
        self.tax_label.setText(T.money(tax))
        self.total_label.setText(T.money(total))
        self.print_btn.setText(f"Charge {T.money(total)}")
        self.cash_chips.set_amounts(cash_suggestions(total))
        self.calculate_change(self.cash_input.text())

    def get_total(self) -> float:
        if not self.cart_items:
            return 0
        return self._compute()[4]

    def _edit_discount(self) -> None:
        self.discount_stack.setCurrentIndex(1)
        self.discount_input.setFocus()
        self.discount_input.selectAll()

    # ---------------------------------------------------------- customer
    def toggle_customer_popover(self) -> None:
        if self.customer_popover.isVisible():
            self.close_customer_popover()
            return
        self._position_overlays()
        self.customer_popover.raise_()
        self.customer_popover.show()
        self.customer_name.setFocus()

    def close_customer_popover(self) -> None:
        if self.customer_popover.isVisible():
            self.customer_popover.hide()
            self.search_input.setFocus()

    def _update_customer_button(self) -> None:
        name = self.customer_name.text().strip()
        phone = self.customer_phone.text().strip()
        if name or phone:
            label = name or phone
            fm = self.customer_btn.text_label.fontMetrics()
            self.customer_btn.setText(fm.elidedText(label, Qt.ElideRight, 120))
            self.customer_btn.setToolTip(" · ".join(x for x in (name, phone) if x) + " (F4)")
            self.customer_btn.set_text_style(f"color: {T.TEXT}; font-size: 13px; font-weight: 500;")
        else:
            self.customer_btn.setText("+  Add customer")
            self.customer_btn.set_text_style(f"color: {T.MUTED}; font-size: 13px; font-weight: 500;")

    # ---------------------------------------------------------- reset
    def clear_selection(self) -> None:
        self._current_product = None
        self.search_input.clear()
        self.search_results.hide()
        self._search_results = []

    def clear_cart(self) -> None:
        if not self.cart_items:
            return
        if QMessageBox.question(self, "Clear sale", "Clear all items from this sale?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.cart_items.clear()
            self._cart_meta.clear()
            self._undo_stack.clear()
            self.update_cart_display()
            self.customer_name.clear()
            self.customer_phone.clear()
            self.discount_input.setValue(0)
            self.discount_stack.setCurrentIndex(0)
            self.update_totals()
            self.notice.hide()
            self.statusBar().showMessage("Sale cleared")

    def new_transaction(self) -> None:
        self.cart_items.clear()
        self._cart_meta.clear()
        self._undo_stack.clear()
        self.update_cart_display()
        self.customer_name.clear()
        self.customer_phone.clear()
        self.discount_input.setValue(0)
        self.discount_stack.setCurrentIndex(0)
        self.cash_input.clear()
        self.update_totals()
        self.clear_selection()
        self.notice.hide()
        self.refresh_invoice_preview()
        self.focus_search()

    # ---------------------------------------------------------- payment
    def calculate_change(self, text: str) -> None:
        """Calculate and display change as the cashier types the amount."""
        total = self.get_total()
        try:
            cash = float(text) if text else 0
        except ValueError:
            cash = 0
        self.cash_chips.set_active(cash if cash else None)
        if total <= 0:
            self._set_change_state("idle", 0)
        elif cash >= total:
            self._set_change_state("change", cash - total)
        elif cash > 0:
            self._set_change_state("due", total - cash)
        else:
            self._set_change_state("idle", 0)

    def _apply_cash_chip(self, amount: float) -> None:
        self.cash_input.setText(f"{amount:.0f}")

    def on_mode_changed(self, mode: str) -> None:
        """Show cash fields only for cash payments."""
        is_cash = mode == "Cash"
        self.cash_container.setVisible(is_cash)
        self.noncash_note.setVisible(not is_cash)
        if not is_cash:
            self.noncash_note.setText(f"Collect the total by {mode}, then press Charge (F12) or Save only (F9).")

    def finalize_bill(self, print_pdf: bool = True) -> None:
        """Finalize the bill with the selected payment mode (unchanged logic)."""
        if not self.cart_items:
            self.statusBar().showMessage("⚠ Cart empty")
            QMessageBox.warning(self, "Empty", "Cart is empty")
            return

        total = self.get_total()
        mode = self.payment_mode.currentText()

        if mode == "Cash":
            cash_text = self.cash_input.text().strip()
            try:
                cash = float(cash_text) if cash_text else 0
            except ValueError:
                cash = 0
            if cash < total:
                QMessageBox.warning(self, "Insufficient Cash",
                                    f"Cash Received (₹{cash:.2f}) is less than Total (₹{total:.2f})")
                self.cash_input.setFocus()
                return

        name = self.customer_name.text().strip() or "Walk-in"
        phone = self.customer_phone.text().strip() or "0000000000"

        bill = self.billing_service.create_bill(
            name, phone, self.cart_items.copy(),
            self.discount_input.value(), self.tax_spin.value()
        )

        if self.billing_service.save_bill(bill):
            msg = f"✓ Bill Saved: {bill.bill_no} (₹{bill.total:.2f})"
            if print_pdf:
                try:
                    pdf_path = self.pdf_generator.generate_invoice(bill)
                    open_file(pdf_path)
                    msg += " | PDF Generated"
                except Exception as e:  # noqa: BLE001
                    QMessageBox.warning(self, "PDF Error", f"Could not generate PDF: {str(e)}")
            self.statusBar().showMessage(msg)
            self.smart_search.refresh_cache()   # stock changed
            self.new_transaction()
            self.toast.show_message(f"Bill {bill.bill_no} saved · {T.money(bill.total)} ({mode})")
            self.load_quick_add()
        else:
            QMessageBox.critical(self, "Error", "Failed to save bill")

    # ---------------------------------------------------------- hold / recall
    def save_pending(self) -> None:
        if not self.cart_items:
            return
        cart_data = [{'product_name': i.product_name, 'quantity': i.quantity, 'unit_price': i.unit_price}
                     for i in self.cart_items]
        pid = self.pending_bills_mgr.save_pending_bill(
            getattr(self.employee, 'employee_id', 1), cart_data,
            self.customer_name.text().strip(), self.customer_phone.text().strip(),
            sum(i.get_total() for i in self.cart_items),
            self.discount_input.value(), self.tax_spin.value()
        )
        # NOTE: PendingBillsManager.save_pending_bill() returns 0 (not None) on a
        # successful insert because it reads last_insert_rowid() on a fresh
        # connection; None means it failed. The old `if pid:` check therefore
        # never cleared the cart even though the sale was held.
        if pid is not None:
            ref = f" #{pid}" if pid else ""
            self.update_pending_count()
            self.new_transaction()
            self.statusBar().showMessage(f"✓ Saved pending{ref}")
            self.toast.show_message(f"Sale held{ref}. Recall it from “on hold” (F10).")
        else:
            self.notice.show_message("Could not hold this sale (too many held bills?)", tone="warning")

    def show_pending_bills(self) -> None:
        pending = self.pending_bills_mgr.get_pending_bills(getattr(self.employee, 'employee_id', 1))
        if not pending:
            QMessageBox.information(self, "Pending", "No pending bills")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Held bills")
        dialog.setMinimumSize(480, 380)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(make_label("Held bills", size=17, weight=600))
        layout.addWidget(make_label("Select a sale to bring it back to the counter.", role="muted"))
        list_w = QListWidget()
        for b in pending:
            list_w.addItem(b.get_display_text())
        list_w.setCurrentRow(0)
        layout.addWidget(list_w, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = make_button("Close")
        close_btn.clicked.connect(dialog.close)
        recall_btn = make_button("Recall", variant="primary")
        recall_btn.setDefault(True)
        recall = lambda: self._recall_pending(pending[list_w.currentRow()] if list_w.currentRow() >= 0 else None, dialog)  # noqa: E731
        recall_btn.clicked.connect(recall)
        list_w.itemDoubleClicked.connect(lambda _i: recall())
        btn_row.addWidget(close_btn)
        btn_row.addWidget(recall_btn)
        layout.addLayout(btn_row)
        self._pending_dialog = dialog
        dialog.exec()

    def _recall_pending(self, bill, dialog) -> None:
        if not bill:
            return
        if self.cart_items:
            reply = QMessageBox.question(
                self, "Current sale", "Hold the current sale before recalling?\n\n"
                "Yes: hold it · No: discard it · Cancel: keep working on it",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                self.save_pending()
        bill = self.pending_bills_mgr.recall_pending_bill(bill.pending_id)
        if bill:
            self.cart_items = [BillItem(i['product_name'], i['quantity'], i['unit_price']) for i in bill.cart_items]
            self._cart_meta = [self._lookup_meta(i.product_name) for i in self.cart_items]
            self._undo_stack.clear()
            self.customer_name.setText(bill.customer_name or "")
            self.customer_phone.setText(bill.customer_phone or "")
            self.discount_input.setValue(bill.discount)
            self.tax_spin.setValue(bill.tax_rate)
            self.update_cart_display(select=0)
            self.update_totals()
            self.update_pending_count()
            dialog.close()
            self.toast.show_message(f"Recalled held sale #{bill.pending_id}")

    def _lookup_meta(self, name: str) -> Dict:
        for p in self.smart_search.get_all_products():
            if p['product_name'] == name:
                return {'barcode': p.get('barcode', ''), 'category': p.get('category', ''), 'stock': p.get('stock')}
        return {'barcode': '', 'category': '', 'stock': None}

    def update_pending_count(self) -> None:
        count = self.pending_bills_mgr.get_pending_count(getattr(self.employee, 'employee_id', 1))
        self.pending_btn.setText(f"{count} on hold")
        self.pending_btn.set_tone("warning" if count else "neutral")

    # ---------------------------------------------------------- quick add
    def load_quick_add(self) -> None:
        """Best sellers today, topped up from the last 30 days, then by stock."""
        catalog = {p['product_name']: p for p in self.smart_search.get_all_products()}
        chosen: List[Dict] = []
        caption = "Your best sellers today"
        try:
            analytics = AnalyticsService()
            today = analytics.get_best_selling_today(limit=QUICK_ADD_SLOTS * 2)
            names = [r['product_name'] for r in today]
            if len([n for n in names if n in catalog]) < QUICK_ADD_SLOTS:
                start = (datetime.now().date().toordinal() - 30)
                start_s = datetime.fromordinal(start).strftime("%Y-%m-%d")
                recent = analytics.get_best_selling_products(start_s, None, limit=QUICK_ADD_SLOTS * 2)
                if not [n for n in names if n in catalog]:
                    caption = "Best sellers · last 30 days"
                names += [r['product_name'] for r in recent]
            for n in names:
                if n in catalog and catalog[n] not in chosen and catalog[n].get('stock', 0) > 0:
                    chosen.append(catalog[n])
        except Exception as e:  # noqa: BLE001
            print(f"Quick add: analytics unavailable: {e}")
        if len(chosen) < QUICK_ADD_SLOTS:
            for p in QuickAccessManager().get_top_products(QUICK_ADD_SLOTS * 2):
                full = catalog.get(p['product_name'], p)
                if full not in chosen:
                    chosen.append(full)
            if not chosen:
                caption = "No products yet"
            elif caption == "Your best sellers today" and len(chosen) and not self._has_sales_today():
                caption = "Popular products"
        self._quick_products = chosen[:QUICK_ADD_SLOTS]
        self.quick_caption.setText(caption)
        while self.quick_grid.count():
            it = self.quick_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for k, p in enumerate(self._quick_products):
            self.quick_grid.addWidget(self._quick_tile(k, p), k // 4, k % 4)
        for c in range(4):
            self.quick_grid.setColumnStretch(c, 1)

    def _has_sales_today(self) -> bool:
        try:
            return bool(self.billing_service.get_todays_bills())
        except Exception:  # noqa: BLE001
            return False

    def _quick_tile(self, k: int, p: Dict) -> QPushButton:
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFixedHeight(74)
        btn.setMinimumWidth(120)
        btn.setToolTip(f"{p['product_name']} · {T.money(p.get('mrp') or 0)} · press {k + 1}")
        btn.setStyleSheet(f"QPushButton {{ background: {T.SURFACE_2}; border: 1px solid {T.BORDER}; border-radius: 11px; padding: 0; }}"
                          f"QPushButton:hover {{ border-color: {T.BORDER_2}; background: {T.SURFACE_3}; }}"
                          f"QPushButton:pressed {{ border-color: {T.ACCENT}; }}")
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(16, 12, 14, 12)
        lay.setSpacing(4)
        name = make_label(p['product_name'], size=13, weight=500)
        name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(name)
        row = QHBoxLayout()
        price = make_label(T.money(p.get('mrp') or 0, 0 if float(p.get('mrp') or 0).is_integer() else 2),
                           role="muted", size=13, weight=500)
        key = QLabel(str(k + 1))
        key.setStyleSheet(f"color: {T.FAINT}; font-size: 11px; font-weight: 500; font-family: {T.mono_font_stack()};")
        for w in (price, key):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        row.addWidget(price)
        row.addStretch(1)
        row.addWidget(key)
        lay.addLayout(row)
        btn.clicked.connect(lambda _=False, idx=k: self.quick_add(idx))
        return btn

    def quick_add(self, idx: int) -> None:
        if 0 <= idx < len(self._quick_products):
            name = self._quick_products[idx]['product_name']
            fresh = next((p for p in self.smart_search.get_all_products() if p['product_name'] == name),
                         self._quick_products[idx])
            self.add_product(fresh, 1)

    # ---------------------------------------------------------- misc
    def refresh_invoice_preview(self) -> None:
        """Show the next invoice number without consuming the sequence."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            rows = db.execute_query("SELECT last_sequence FROM invoice_sequence WHERE date = ?", (today,))
            seq = (rows[0]['last_sequence'] if rows else 0) + 1
            self.invoice_label.setText(config.INVOICE_NUMBER_FORMAT.format(
                prefix=config.INVOICE_PREFIX, date=today.replace("-", ""), sequence=seq))
            self.invoice_label.setToolTip("Next invoice number")
        except Exception:  # noqa: BLE001
            self.invoice_label.setText("")

    def update_time(self) -> None:
        self.time_label.setText(datetime.now().strftime("%I:%M %p").lstrip("0"))
        self.time_label.setToolTip(datetime.now().strftime("%A, %d %B %Y"))

    def switch_to_admin(self) -> None:
        if self.employee.role and self.employee.role.lower() == "admin":
            self.close()
            from src.ui.admin.dashboard import AdminDashboard
            self.admin_window = AdminDashboard(self.employee)
            self.admin_window.show()

    def handle_logout(self) -> None:
        if self.cart_items:
            reply = QMessageBox.question(self, "Cart", "Save as pending?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_pending()
            elif reply == QMessageBox.Cancel:
                return
        self.close()
        from src.ui.login import LoginWindow
        self.login_window = LoginWindow()

        def on_login(employee):
            if employee.is_admin():
                from src.ui.admin.dashboard import AdminDashboard
                self.next_window = AdminDashboard(employee)
            else:
                self.next_window = BillingWindow(employee)
            self.next_window.show()

        self.login_window.login_successful.connect(on_login)
        self.login_window.show()

    def closeEvent(self, event) -> None:  # noqa: N802
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        event.accept()
