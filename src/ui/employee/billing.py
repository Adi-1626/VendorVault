"""
Employee billing window (Point of Sale).
Professional Dark Theme - Optimized for 1920x1080.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QFrame, QMessageBox, QHeaderView, QDoubleSpinBox, QComboBox,
    QListWidget, QListWidgetItem, QGridLayout, QDialog, QFormLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QColor
from datetime import datetime
from typing import List
from src.models.employee import Employee
from src.models.bill import Bill, BillItem
from src.logic.inventory import InventoryService
from src.logic.billing import BillingService
from src.logic.smart_search import SmartSearch
from src.logic.barcode_scanner import BarcodeScanner
from src.logic.pending_bills import PendingBillsManager
from src.utils.pdf_generator import PDFGenerator
import config


# Dark mode colors
BG_DARK = "#0F172A"
BG_CARD = "#1E293B"
BORDER = "#334155"
WHITE = "#F8FAFC"
GRAY = "#94A3B8"
BLUE = "#3B82F6"
GREEN = "#22C55E"
ORANGE = "#F59E0B"
RED = "#EF4444"
PURPLE = "#8B5CF6"


class BillingWindow(QMainWindow):
    """Professional Dark Mode POS - 1920x1080 optimized."""
    
    def __init__(self, employee: Employee):
        super().__init__()
        self.employee = employee
        
        # Services
        self.inventory_service = InventoryService()
        self.billing_service = BillingService()
        self.pdf_generator = PDFGenerator()
        self.smart_search = SmartSearch()
        self.barcode_scanner = BarcodeScanner()
        self.pending_bills_mgr = PendingBillsManager()
        
        # State
        self.cart_items: List[BillItem] = []
        self._search_results = []
        self._current_product = None
        
        self.setup_ui()
        self.setup_shortcuts()
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
        
        QTimer.singleShot(100, self.focus_search)
    
    def setup_ui(self):
        """Setup UI optimized for 1920x1080."""
        self.setWindowTitle("Lightning POS")
        self.setMinimumSize(1200, 700)
        self.showMaximized()
        
        # Global dark stylesheet - ALL widgets dark with white text
        self.setStyleSheet(f"""
            * {{
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QMainWindow, QWidget {{
                background-color: {BG_DARK};
                color: {WHITE};
            }}
            QLabel {{
                color: {WHITE};
                font-size: 15px;
                background: transparent;
            }}
            QLineEdit {{
                background-color: {BG_CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 16px;
            }}
            QLineEdit:focus {{
                border-color: {BLUE};
            }}
            QSpinBox, QDoubleSpinBox {{
                background-color: {BG_CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 15px;
                min-width: 80px;
                min-height: 35px;
            }}
            QPushButton {{
                background-color: {BG_CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {BORDER};
            }}
            QTableWidget {{
                background-color: {BG_CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 8px;
                font-size: 14px;
                gridline-color: {BORDER};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {WHITE};
            }}
            QHeaderView::section {{
                background-color: {BG_DARK};
                color: {GRAY};
                padding: 10px;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }}
            QListWidget {{
                background-color: {BG_CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 8px;
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {BORDER};
            }}
            QListWidget::item:selected {{
                background-color: {BLUE};
            }}
            QFrame {{
                background-color: {BG_CARD};
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}
            QStatusBar {{
                background-color: {BG_CARD};
                color: {GRAY};
                font-size: 14px;
            }}
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(15)
        
        # === HEADER ===
        header = self._create_header()
        main_layout.addLayout(header)
        
        # === CONTENT: 2 columns ===
        content = QHBoxLayout()
        content.setSpacing(20)
        
        # LEFT: Search + Cart (60%)
        left = self._create_left_panel()
        content.addLayout(left, 6)
        
        # RIGHT: Summary + Payment + Actions (40%)
        right = self._create_right_panel()
        content.addLayout(right, 4)
        
        main_layout.addLayout(content, 1)
        
        self.statusBar().showMessage("Ready | F2: Search | F7: Quick Checkout | F9: Clear")
    
    def _create_header(self):
        """Create header bar."""
        header = QHBoxLayout()
        header.setSpacing(15)
        
        title = QLabel("⚡ LIGHTNING POS")
        title.setStyleSheet(f"color: {BLUE}; font-size: 24px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Pending
        self.pending_btn = QPushButton("📋 Pending (0)")
        self.pending_btn.setStyleSheet(f"background: {ORANGE}; color: white; border: none;")
        self.pending_btn.clicked.connect(self.show_pending_bills)
        header.addWidget(self.pending_btn)
        
        # Time
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {GRAY}; font-size: 14px;")
        header.addWidget(self.time_label)
        
        # Employee
        emp = QLabel(f"👤 {self.employee.get_full_name()}")
        emp.setStyleSheet(f"color: {GRAY}; font-size: 14px;")
        header.addWidget(emp)
        
        # Admin
        if self.employee.role and self.employee.role.lower() == "admin":
            admin_btn = QPushButton("🔐 Admin")
            admin_btn.setStyleSheet(f"background: {PURPLE}; color: white; border: none;")
            admin_btn.clicked.connect(self.switch_to_admin)
            header.addWidget(admin_btn)
        
        # Logout
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet(f"background: {RED}; color: white; border: none;")
        logout_btn.clicked.connect(self.handle_logout)
        header.addWidget(logout_btn)
        
        return header
    
    def _create_left_panel(self):
        """Left panel - search and cart."""
        left = QVBoxLayout()
        left.setSpacing(15)
        
        # === SEARCH SECTION ===
        search_frame = QFrame()
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(18, 18, 18, 18)
        search_layout.setSpacing(12)
        
        # Title
        search_title = QLabel("🔍 SCAN BARCODE / SEARCH")
        search_title.setStyleSheet(f"color: {BLUE}; font-size: 16px; font-weight: bold; border: none;")
        search_layout.addWidget(search_title)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan barcode or type product name...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: 3px solid {BLUE};
                font-size: 18px;
                padding: 14px 18px;
            }}
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.on_search_enter)
        search_layout.addWidget(self.search_input)
        
        # Search results dropdown
        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(150)
        self.search_results.hide()
        self.search_results.itemClicked.connect(self.on_result_clicked)
        self.search_results.itemDoubleClicked.connect(self.on_result_double_clicked)
        search_layout.addWidget(self.search_results)
        
        # Quantity row
        qty_row = QHBoxLayout()
        qty_row.setSpacing(12)
        
        qty_label = QLabel("QTY:")
        qty_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {WHITE};")
        qty_row.addWidget(qty_label)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(9999)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setFixedWidth(80)
        qty_row.addWidget(self.quantity_spin)
        
        self.product_label = QLabel("No product selected")
        self.product_label.setStyleSheet(f"color: {GRAY}; font-size: 14px;")
        qty_row.addWidget(self.product_label, 1)
        
        self.stock_label = QLabel("")
        self.stock_label.setStyleSheet(f"color: {GREEN}; font-size: 14px; font-weight: bold;")
        qty_row.addWidget(self.stock_label)
        
        add_btn = QPushButton("+ ADD")
        add_btn.setStyleSheet(f"background: {GREEN}; color: white; border: none; padding: 12px 24px; font-size: 16px;")
        add_btn.clicked.connect(self.add_to_cart)
        qty_row.addWidget(add_btn)
        
        search_layout.addLayout(qty_row)
        
        # Customer row
        cust_row = QHBoxLayout()
        cust_row.setSpacing(12)
        
        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("Customer Name (optional)")
        cust_row.addWidget(self.customer_name, 2)
        
        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("Phone")
        self.customer_phone.setMaximumWidth(150)
        cust_row.addWidget(self.customer_phone)
        
        search_layout.addLayout(cust_row)
        left.addWidget(search_frame)
        
        # === CART SECTION ===
        cart_frame = QFrame()
        cart_layout = QVBoxLayout(cart_frame)
        cart_layout.setContentsMargins(18, 18, 18, 18)
        cart_layout.setSpacing(10)
        
        self.cart_title = QLabel("🛒 CART (0 items)")
        self.cart_title.setStyleSheet(f"color: {BLUE}; font-size: 16px; font-weight: bold; border: none;")
        cart_layout.addWidget(self.cart_title)
        
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(5)
        self.cart_table.setHorizontalHeaderLabels(["Product", "Qty", "Price", "Total", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setColumnWidth(1, 60)
        self.cart_table.setColumnWidth(2, 100)
        self.cart_table.setColumnWidth(3, 100)
        self.cart_table.setColumnWidth(4, 60)
        cart_layout.addWidget(self.cart_table)
        
        left.addWidget(cart_frame, 1)
        
        return left
    
    def _create_right_panel(self):
        """Right panel - summary, payment, actions."""
        right = QVBoxLayout()
        right.setSpacing(15)
        
        # === BILL SUMMARY ===
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(15, 15, 15, 15)
        summary_layout.setSpacing(10)
        
        # Inputs Row (Discount & Tax side-by-side)
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(10)
        
        # Input Style
        input_style = f"""
            QDoubleSpinBox {{
                background-color: {BG_DARK}; 
                color: {WHITE};
                border: 2px solid {BORDER}; 
                border-radius: 6px;
                padding: 4px 8px; 
                font-size: 14px;
                min-width: 80px;
                min-height: 30px;
            }}
            QDoubleSpinBox:focus {{ border-color: {BLUE}; }}
        """
        
        # Discount Section
        disc_layout = QVBoxLayout()
        disc_layout.setSpacing(2)
        disc_lbl = QLabel("Discount (₹)")
        disc_lbl.setStyleSheet(f"color: {GRAY}; font-size: 12px; font-weight: bold;")
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setMaximum(99999)
        self.discount_input.setDecimals(2)
        self.discount_input.setStyleSheet(input_style)
        self.discount_input.valueChanged.connect(self.update_totals)
        disc_layout.addWidget(disc_lbl)
        disc_layout.addWidget(self.discount_input)
        inputs_layout.addLayout(disc_layout)
        
        # Tax Section
        tax_layout = QVBoxLayout()
        tax_layout.setSpacing(2)
        tax_lbl = QLabel("Tax (%)")
        tax_lbl.setStyleSheet(f"color: {GRAY}; font-size: 12px; font-weight: bold;")
        self.tax_spin = QDoubleSpinBox()
        self.tax_spin.setMaximum(100)
        self.tax_spin.setValue(config.DEFAULT_GST_RATE)
        self.tax_spin.setStyleSheet(input_style)
        self.tax_spin.valueChanged.connect(self.update_totals)
        tax_layout.addWidget(tax_lbl)
        tax_layout.addWidget(self.tax_spin)
        inputs_layout.addLayout(tax_layout)
        
        summary_layout.addLayout(inputs_layout)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet(f"background-color: {BORDER}; margin-top: 5px; margin-bottom: 5px;")
        line.setFixedHeight(1)
        summary_layout.addWidget(line)
        
        # Totals Grid
        totals_grid = QGridLayout()
        totals_grid.setVerticalSpacing(5)
        
        self.subtotal_label = QLabel("Subtotal: ₹0.00")
        self.subtotal_label.setStyleSheet(f"color: {WHITE}; font-size: 14px;")
        totals_grid.addWidget(self.subtotal_label, 0, 0)
        
        self.discount_label = QLabel("Disc: -₹0.00")
        self.discount_label.setStyleSheet(f"color: {ORANGE}; font-size: 14px;")
        totals_grid.addWidget(self.discount_label, 1, 0)
        
        self.tax_label = QLabel("Tax: ₹0.00")
        self.tax_label.setStyleSheet(f"color: {GRAY}; font-size: 14px;")
        totals_grid.addWidget(self.tax_label, 2, 0)
        
        summary_layout.addLayout(totals_grid)
        
        # Grand Total
        self.total_label = QLabel("₹ 0.00")
        self.total_label.setStyleSheet(f"""
            color: {GREEN};
            font-size: 28px;
            font-weight: bold;
            padding: 10px;
            background: {BG_DARK};
            border-radius: 8px;
            border: none;
            qproperty-alignment: AlignCenter;
        """)
        summary_layout.addWidget(self.total_label)
        
        right.addWidget(summary_frame)
        
        # === CHECKOUT SECTION ===
        checkout_frame = QFrame()
        checkout_layout = QVBoxLayout(checkout_frame)
        checkout_layout.setContentsMargins(15, 15, 15, 15)
        checkout_layout.setSpacing(15)
        
        # Cash Input Area (Create FIRST to avoid AttributeError)
        self.cash_container = QWidget()
        cash_layout = QVBoxLayout(self.cash_container)
        cash_layout.setContentsMargins(0, 0, 0, 0)
        cash_layout.setSpacing(5)
        
        self.cash_input = QLineEdit()
        self.cash_input.setPlaceholderText("Cash Received (₹)")
        self.cash_input.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_DARK}; color: {WHITE};
                border: 2px solid {BORDER}; border-radius: 6px;
                padding: 8px; font-size: 15px;
            }}
            QLineEdit:focus {{ border-color: {GREEN}; }}
        """)
        self.cash_input.textChanged.connect(self.calculate_change)
        
        self.change_label = QLabel("Change: ₹0.00")
        self.change_label.setStyleSheet(f"color: {GRAY}; font-size: 14px; font-weight: bold; margin-left: 5px;")
        
        cash_layout.addWidget(self.cash_input)
        cash_layout.addWidget(self.change_label)
        # Note: Added to layout later
        
        # Payment Mode Selection
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Payment Mode:")
        mode_lbl.setStyleSheet(f"color: {WHITE}; font-size: 14px; font-weight: bold;")
        
        self.payment_mode = QComboBox()
        self.payment_mode.addItems(["Cash", "UPI", "Card"])
        self.payment_mode.setStyleSheet(f"""
            QComboBox {{
                background: {BG_DARK};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 14px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.payment_mode.currentTextChanged.connect(self.on_mode_changed)
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.payment_mode, 1)
        checkout_layout.addLayout(mode_row)
        
        # Add Cash Container (Now safe)
        checkout_layout.addWidget(self.cash_container)
        
        # Main Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.print_btn = QPushButton("🖨️ PRINT & BILL")
        self.print_btn.setStyleSheet(f"""
            QPushButton {{
                background: {GREEN}; color: white; border: none;
                font-size: 16px; font-weight: bold; padding: 15px; border-radius: 8px;
            }}
            QPushButton:hover {{ background: #16A34A; }}
        """)
        self.print_btn.clicked.connect(lambda: self.finalize_bill(print_pdf=True))
        
        self.save_btn = QPushButton("💾 SAVE ONLY")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {BLUE}; color: white; border: none;
                font-size: 14px; font-weight: bold; padding: 15px; border-radius: 8px;
            }}
            QPushButton:hover {{ background: #2563EB; }}
        """)
        self.save_btn.clicked.connect(lambda: self.finalize_bill(print_pdf=False))
        
        btn_layout.addWidget(self.save_btn, 1)
        btn_layout.addWidget(self.print_btn, 2)
        checkout_layout.addLayout(btn_layout)
        
        # Secondary Actions (Hold, Clear)
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(10)
        
        hold_btn = QPushButton("⏸ HOLD")
        hold_btn.setStyleSheet(f"background: {ORANGE}; color: white; border: none; font-size: 12px; padding: 8px; border-radius: 4px;")
        hold_btn.clicked.connect(self.save_pending)
        
        clear_btn = QPushButton("🗑 CLEAR")
        clear_btn.setStyleSheet(f"background: {RED}; color: white; border: none; font-size: 12px; padding: 8px; border-radius: 4px;")
        clear_btn.clicked.connect(self.clear_cart)
        
        secondary_layout.addWidget(hold_btn)
        secondary_layout.addWidget(clear_btn)
        checkout_layout.addLayout(secondary_layout)
        
        right.addWidget(checkout_frame)
        right.addStretch()
        
        return right
    
    # === EVENT HANDLERS ===
    
    def setup_shortcuts(self):
        shortcuts = {
            'F2': self.focus_search, 'F5': lambda: self.finalize_bill(print_pdf=True),
            'F7': lambda: self.finalize_bill(print_pdf=True), 'F9': self.clear_cart,
            'F10': self.show_pending_bills, 'Escape': self.clear_selection,
        }
        for key, func in shortcuts.items():
            if func == self.clear_cart:
                QShortcut(QKeySequence(key), self).activated.connect(func)
            else:
                 QShortcut(QKeySequence(key), self).activated.connect(func)
    
    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()
    
    def on_search_changed(self, text):
        if len(text) < 1:
            self.search_results.hide()
            self._search_results = []
            return
        
        # If it looks like a complete barcode (8-13 digits), try direct lookup
        if text.isdigit() and 8 <= len(text) <= 13:
            result = self.barcode_scanner.process_scan(text)
            if result['success']:
                # Barcode found - auto-select product (no dropdown)
                product = result['product']
                self._select_product(product)
                self.search_input.clear()
                self.search_results.hide()
                self.statusBar().showMessage(f"✓ Scanned: {product['product_name']} - Adjust qty & click ADD")
                return
            # Barcode not found - fall through to regular search
        
        # Regular search - Show dropdown
        results = self.smart_search.search_instant(text, limit=6)
        self._search_results = results
        
        self.search_results.clear()
        for p in results:
            stock = f"Stock: {p['stock']}" if p['stock'] > 0 else "OUT"
            item = QListWidgetItem(f"{p['product_name']} | Rs.{p['mrp']:.2f} | {stock}")
            if p['stock'] <= 0:
                item.setForeground(QColor(GRAY))
            self.search_results.addItem(item)
        
        self.search_results.setVisible(len(results) > 0)
    
    def on_search_enter(self):
        """Handle Enter key in search - select first result or add current product."""
        if self._search_results:
            self._select_product(self._search_results[0])
            self.search_results.hide()
        elif self._current_product:
            self.add_to_cart()
    
    def on_result_clicked(self, item):
        idx = self.search_results.row(item)
        if 0 <= idx < len(self._search_results):
            self._select_product(self._search_results[idx])
    
    def on_result_double_clicked(self, item):
        self.on_result_clicked(item)
        self.add_to_cart()
    
    def _select_product(self, product):
        self._current_product = product
        self.product_label.setText(f"✓ {product['product_name']} | Rs.{product['mrp']:.2f}")
        self.product_label.setStyleSheet(f"color: {GREEN}; font-size: 14px; font-weight: bold;")
        
        stock = product.get('stock', 0)
        self.stock_label.setText(f"Stock: {stock}")
        color = GREEN if stock >= 10 else ORANGE if stock > 0 else RED
        self.stock_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        
        self.quantity_spin.setMaximum(max(1, stock))
        self.quantity_spin.setValue(1)
        self.quantity_spin.setFocus()
        self.search_results.hide()
        self.search_input.clear()
    
    def add_to_cart(self):
        if not self._current_product:
            self.statusBar().showMessage("⚠ Select a product first")
            self.focus_search()
            return
        
        product = self._current_product
        qty = self.quantity_spin.value()
        
        if qty > product.get('stock', 0):
            QMessageBox.warning(self, "Stock", f"Only {product.get('stock', 0)} available")
            return
        
        item = BillItem(product['product_name'], qty, product['mrp'])
        self.cart_items.append(item)
        
        self.update_cart_display()
        self.update_totals()
        self.clear_selection()
        self.focus_search()
        self.statusBar().showMessage(f"✓ Added {qty} x {product['product_name']}")
    
    def update_cart_display(self):
        self.cart_table.setRowCount(len(self.cart_items))
        self.cart_title.setText(f"🛒 CART ({len(self.cart_items)} items)")
        
        for i, item in enumerate(self.cart_items):
            self.cart_table.setItem(i, 0, QTableWidgetItem(item.product_name))
            self.cart_table.setItem(i, 1, QTableWidgetItem(str(item.quantity)))
            self.cart_table.setItem(i, 2, QTableWidgetItem(f"₹{item.unit_price:.2f}"))
            self.cart_table.setItem(i, 3, QTableWidgetItem(f"₹{item.get_total():.2f}"))
            
            rm_btn = QPushButton("✕")
            rm_btn.setStyleSheet(f"background: {RED}; color: white; border: none; padding: 6px 10px;")
            rm_btn.clicked.connect(lambda _, idx=i: self.remove_item(idx))
            self.cart_table.setCellWidget(i, 4, rm_btn)
    
    def remove_item(self, idx):
        if 0 <= idx < len(self.cart_items):
            removed = self.cart_items.pop(idx)
            self.update_cart_display()
            self.update_totals()
            self.statusBar().showMessage(f"Removed {removed.product_name}")
    
    def update_totals(self):
        if not self.cart_items:
            self.subtotal_label.setText("Subtotal: ₹0.00")
            self.discount_label.setText("Discount: -₹0.00")
            self.tax_label.setText("Tax: ₹0.00")
            self.total_label.setText("₹ 0.00")
            return
        
        subtotal = sum(i.get_total() for i in self.cart_items)
        discount = self.discount_input.value()
        tax_rate = self.tax_spin.value()
        taxable = max(0, subtotal - discount)
        tax = taxable * (tax_rate / 100)
        total = subtotal - discount + tax
        
        self.subtotal_label.setText(f"Subtotal: ₹{subtotal:.2f}")
        self.discount_label.setText(f"Discount: -₹{discount:.2f}")
        self.tax_label.setText(f"Tax ({tax_rate}%): ₹{tax:.2f}")
        self.total_label.setText(f"₹ {total:.2f}")
    
    def get_total(self):
        if not self.cart_items:
            return 0
        subtotal = sum(i.get_total() for i in self.cart_items)
        discount = self.discount_input.value()
        tax_rate = self.tax_spin.value()
        taxable = max(0, subtotal - discount)
        tax = taxable * (tax_rate / 100)
        return subtotal - discount + tax
    
    def clear_selection(self):
        self._current_product = None
        self.product_label.setText("No product selected")
        self.product_label.setStyleSheet(f"color: {GRAY}; font-size: 14px;")
        self.stock_label.setText("")
        self.quantity_spin.setValue(1)
        self.search_input.clear()
        self.search_results.hide()
    
    def clear_cart(self):
        if not self.cart_items:
            return
        if QMessageBox.question(self, "Clear", "Clear all items?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.cart_items.clear()
            self.update_cart_display()
            self.update_totals()
            self.customer_name.clear()
            self.customer_phone.clear()
            self.discount_input.setValue(0)
            self.change_label.setText("")
    
    def new_transaction(self):
        self.cart_items.clear()
        self.update_cart_display()
        self.update_totals()
        self.customer_name.clear()
        self.customer_phone.clear()
        self.discount_input.setValue(0)
        self.cash_input.clear()
        self.change_label.setText("Change: ₹0.00")
        self.clear_selection()
        self.focus_search()
    
    def calculate_change(self, text):
        """Calculate and display change as user types cash amount."""
        total = self.get_total()
        try:
            cash = float(text) if text else 0
            if cash >= total and total > 0:
                change = cash - total
                self.change_label.setText(f"Change: ₹{change:.2f}")
                self.change_label.setStyleSheet(f"color: {GREEN}; font-size: 24px; font-weight: bold; padding: 12px; background: {BG_DARK}; border-radius: 8px; border: none;")
            elif total > 0:
                self.change_label.setText(f"Due: ₹{total:.2f}")
                self.change_label.setStyleSheet(f"color: {ORANGE}; font-size: 24px; font-weight: bold; padding: 12px; background: {BG_DARK}; border-radius: 8px; border: none;")
            else:
                self.change_label.setText("Change: ₹0.00")
        except ValueError:
            self.change_label.setText("Change: ₹0.00")
    
    def on_mode_changed(self, mode):
        """Toggle UI elements based on payment mode."""
        self.cash_container.setVisible(mode == "Cash")
        
    def finalize_bill(self, print_pdf=True):
        """Finalize the bill with selected payment mode."""
        if not self.cart_items:
            self.statusBar().showMessage("⚠ Cart empty")
            QMessageBox.warning(self, "Empty", "Cart is empty")
            return
            
        total = self.get_total()
        mode = self.payment_mode.currentText()
        
        # Validation for Cash
        if mode == "Cash":
            cash_text = self.cash_input.text().strip()
            try:
                cash = float(cash_text) if cash_text else 0
            except ValueError:
                cash = 0
            
            if cash < total:
                QMessageBox.warning(self, "Insufficient Cash", f"Cash Received (₹{cash:.2f}) is less than Total (₹{total:.2f})")
                self.cash_input.setFocus()
                return
        
        # Prepare Data
        name = self.customer_name.text().strip() or "Walk-in"
        phone = self.customer_phone.text().strip() or "0000000000"
        
        # Create Bill
        bill = self.billing_service.create_bill(
            name, phone, self.cart_items.copy(),
            self.discount_input.value(), self.tax_spin.value()
        )
        # Store payment mode usage (not in current schema but good for logging)
        # bill.payment_mode = mode 
        
        if self.billing_service.save_bill(bill):
            msg = f"✓ Bill Saved: {bill.bill_no} (₹{bill.total:.2f})"
            
            if print_pdf:
                try:
                    pdf_path = self.pdf_generator.generate_invoice(bill)
                    # Open PDF
                    import os
                    os.startfile(pdf_path)
                    msg += " | PDF Generated"
                except Exception as e:
                    QMessageBox.warning(self, "PDF Error", f"Could not generate PDF: {str(e)}")
            
            self.statusBar().showMessage(msg)
            QMessageBox.information(self, "Success", f"Bill {bill.bill_no} processed successfully!")
            self.new_transaction()
        else:
            QMessageBox.critical(self, "Error", "Failed to save bill")
    
    def save_pending(self):
        if not self.cart_items:
            return
        cart_data = [{'product_name': i.product_name, 'quantity': i.quantity, 'unit_price': i.unit_price} for i in self.cart_items]
        pid = self.pending_bills_mgr.save_pending_bill(
            getattr(self.employee, 'employee_id', 1), cart_data,
            self.customer_name.text().strip(), self.customer_phone.text().strip(),
            sum(i.get_total() for i in self.cart_items),
            self.discount_input.value(), self.tax_spin.value()
        )
        if pid:
            self.update_pending_count()
            self.new_transaction()
            self.statusBar().showMessage(f"✓ Saved pending #{pid}")
    
    def show_pending_bills(self):
        pending = self.pending_bills_mgr.get_pending_bills(getattr(self.employee, 'employee_id', 1))
        if not pending:
            QMessageBox.information(self, "Pending", "No pending bills")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Pending Bills")
        dialog.setMinimumSize(450, 350)
        dialog.setStyleSheet(f"background: {BG_DARK}; color: {WHITE};")
        
        layout = QVBoxLayout(dialog)
        list_w = QListWidget()
        for b in pending:
            list_w.addItem(b.get_display_text())
        layout.addWidget(list_w)
        
        btn_row = QHBoxLayout()
        recall_btn = QPushButton("Recall")
        recall_btn.clicked.connect(lambda: self._recall_pending(pending[list_w.currentRow()] if list_w.currentRow() >= 0 else None, dialog))
        btn_row.addWidget(recall_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        btn_row.addWidget(close_btn)
        
        layout.addLayout(btn_row)
        dialog.exec()
    
    def _recall_pending(self, bill, dialog):
        if not bill:
            return
        bill = self.pending_bills_mgr.recall_pending_bill(bill.pending_id)
        if bill:
            self.cart_items = [BillItem(i['product_name'], i['quantity'], i['unit_price']) for i in bill.cart_items]
            self.customer_name.setText(bill.customer_name or "")
            self.customer_phone.setText(bill.customer_phone or "")
            self.discount_input.setValue(bill.discount)
            self.tax_spin.setValue(bill.tax_rate)
            self.update_cart_display()
            self.update_totals()
            self.update_pending_count()
            dialog.close()
    
    def update_pending_count(self):
        count = self.pending_bills_mgr.get_pending_count(getattr(self.employee, 'employee_id', 1))
        self.pending_btn.setText(f"📋 Pending ({count})")
    
    def update_time(self):
        self.time_label.setText(datetime.now().strftime("%d %b %Y | %I:%M %p"))
    
    def switch_to_admin(self):
        if self.employee.role and self.employee.role.lower() == "admin":
            self.close()
            from src.ui.admin.dashboard import AdminDashboard
            self.admin_window = AdminDashboard(self.employee)
            self.admin_window.show()
    
    def handle_logout(self):
        if self.cart_items:
            reply = QMessageBox.question(self, "Cart", "Save as pending?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_pending()
            elif reply == QMessageBox.Cancel:
                return
        self.close()
        from src.ui.login import LoginWindow
        self.login_window = LoginWindow()
        
        # Connect login signal to open appropriate window
        def on_login(employee):
            if employee.is_admin():
                from src.ui.admin.dashboard import AdminDashboard
                self.next_window = AdminDashboard(employee)
            else:
                self.next_window = BillingWindow(employee)
            self.next_window.show()
        
        self.login_window.login_successful.connect(on_login)
        self.login_window.show()
    
    def closeEvent(self, event):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        event.accept()
