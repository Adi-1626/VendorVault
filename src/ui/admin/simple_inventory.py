"""
Simple Inventory Management - Dark Mode with proper label alignment.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QFrame, QComboBox, QFormLayout
)
from PySide6.QtCore import Qt, QTimer
from src.database.connection import db

from src.ui.colors import *

# Map specific colors if needed
BG = DARK_BG
CARD = CARD_BG
WHITE = TEXT_PRIMARY
GRAY = TEXT_SECONDARY
BLUE = PRIMARY
GREEN = SUCCESS
ORANGE = WARNING
RED = DANGER



class SimpleInventoryWindow(QMainWindow):
    """Simple barcode-based inventory - Dark Mode."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_product_id = None
        self.setup_ui()
        self.load_products()
        QTimer.singleShot(100, lambda: self.barcode_input.setFocus())
    
    def setup_ui(self):
        """Setup dark mode UI with proper alignment."""
        self.setWindowTitle("Inventory Management")
        self.setMinimumSize(1100, 700)
        
        # Dark stylesheet
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {BG};
                color: {WHITE};
            }}
            QLabel {{
                color: {WHITE};
                font-size: 14px;
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border-color: {BLUE};
            }}
            QPushButton {{
                background-color: {CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {BORDER};
            }}
            QTableWidget {{
                background-color: {CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 8px;
                font-size: 13px;
                gridline-color: {BORDER};
            }}
            QTableWidget::item {{
                padding: 6px;
                color: {WHITE};
            }}
            QHeaderView::section {{
                background-color: {BG};
                color: {GRAY};
                padding: 8px;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }}
            QFrame {{
                background-color: {CARD};
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}
            QStatusBar {{
                background-color: {CARD};
                color: {GRAY};
            }}
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📦 INVENTORY MANAGEMENT")
        title.setStyleSheet(f"color: {BLUE}; font-size: 22px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        
        close_btn = QPushButton("✕ Close")
        close_btn.setStyleSheet(f"background: {RED}; color: white; border: none;")
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)
        
        # Content: 2 columns
        content = QHBoxLayout()
        content.setSpacing(20)
        
        # === LEFT: Form ===
        form_frame = QFrame()
        form_lyt = QVBoxLayout(form_frame)
        form_lyt.setContentsMargins(20, 15, 20, 15)
        form_lyt.setSpacing(12)
        
        form_title = QLabel("📲 SCAN BARCODE TO ADD/EDIT")
        form_title.setStyleSheet(f"color: {BLUE}; font-size: 14px; font-weight: bold; border: none;")
        form_lyt.addWidget(form_title)
        
        # Barcode
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode here...")
        self.barcode_input.setStyleSheet(f"""
            QLineEdit {{
                border: 3px solid {BLUE};
                font-size: 18px;
                padding: 14px;
            }}
        """)
        self.barcode_input.returnPressed.connect(self.lookup_barcode)
        form_lyt.addWidget(self.barcode_input)
        
        # Form fields using QFormLayout for proper alignment
        fields = QFormLayout()
        fields.setSpacing(12)
        fields.setLabelAlignment(Qt.AlignRight)
        
        # Explicit label style
        lbl_style = f"color: {WHITE}; font-size: 14px; font-weight: bold; background: transparent; border: none;"
        
        name_lbl = QLabel("Product Name:")
        name_lbl.setStyleSheet(lbl_style)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Haldiram Aloo Bhujia 400g")
        fields.addRow(name_lbl, self.name_input)
        
        # Price row
        price_lbl = QLabel("Prices:")
        price_lbl.setStyleSheet(lbl_style)
        price_widget = QWidget()
        price_widget.setStyleSheet("background: transparent; border: none;")
        price_lyt = QHBoxLayout(price_widget)
        price_lyt.setContentsMargins(0, 0, 0, 0)
        price_lyt.setSpacing(15)
        
        mrp_lbl = QLabel("MRP ₹:")
        mrp_lbl.setStyleSheet(f"color: {WHITE}; background: transparent; border: none;")
        self.mrp_input = QDoubleSpinBox()
        self.mrp_input.setMaximum(99999)
        self.mrp_input.setDecimals(2)
        self.mrp_input.setMinimumWidth(100)
        price_lyt.addWidget(mrp_lbl)
        price_lyt.addWidget(self.mrp_input)
        
        cost_lbl = QLabel("Cost ₹:")
        cost_lbl.setStyleSheet(f"color: {WHITE}; background: transparent; border: none;")
        self.cost_input = QDoubleSpinBox()
        self.cost_input.setMaximum(99999)
        self.cost_input.setDecimals(2)
        self.cost_input.setMinimumWidth(100)
        price_lyt.addWidget(cost_lbl)
        price_lyt.addWidget(self.cost_input)
        price_lyt.addStretch()
        
        fields.addRow(price_lbl, price_widget)
        
        # Stock row
        stock_lbl = QLabel("Stock:")
        stock_lbl.setStyleSheet(lbl_style)
        stock_widget = QWidget()
        stock_widget.setStyleSheet("background: transparent; border: none;")
        stock_lyt = QHBoxLayout(stock_widget)
        stock_lyt.setContentsMargins(0, 0, 0, 0)
        stock_lyt.setSpacing(15)
        
        self.stock_input = QSpinBox()
        self.stock_input.setMaximum(99999)
        self.stock_input.setMinimumWidth(80)
        stock_lyt.addWidget(self.stock_input)
        
        cat_lbl = QLabel("Category:")
        cat_lbl.setStyleSheet(f"color: {WHITE}; background: transparent; border: none;")
        stock_lyt.addWidget(cat_lbl)
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems(['Namkeen', 'Biscuits', 'Chips', 'Sweets', 'Dry Fruits', 'Beverages', 'Other'])
        self.category_input.setMinimumWidth(150)
        stock_lyt.addWidget(self.category_input)
        stock_lyt.addStretch()
        
        fields.addRow(stock_lbl, stock_widget)
        
        form_lyt.addLayout(fields)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {GREEN}; font-size: 13px; font-weight: bold; border: none;")
        form_lyt.addWidget(self.status_label)
        
        # Buttons - Even widths
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        btn_style = "color: white; border: none; padding: 12px 20px; font-size: 14px; font-weight: bold; min-width: 120px;"
        
        save_btn = QPushButton("💾 SAVE PRODUCT")
        save_btn.setStyleSheet(f"background: {GREEN}; {btn_style}")
        save_btn.clicked.connect(self.save_product)
        btn_row.addWidget(save_btn)
        
        new_btn = QPushButton("🔄 NEW")
        new_btn.setStyleSheet(f"background: {BLUE}; {btn_style}")
        new_btn.clicked.connect(self.clear_form)
        btn_row.addWidget(new_btn)
        
        del_btn = QPushButton("🗑 DELETE")
        del_btn.setStyleSheet(f"background: {RED}; {btn_style}")
        del_btn.clicked.connect(self.delete_product)
        btn_row.addWidget(del_btn)
        
        form_lyt.addLayout(btn_row)
        
        # Quick stock
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        quick_lbl = QLabel("Quick Stock +")
        quick_lbl.setStyleSheet(f"color: {GRAY}; border: none;")
        quick_row.addWidget(quick_lbl)
        
        for qty in [1, 5, 10, 50]:
            btn = QPushButton(f"+{qty}")
            btn.setStyleSheet(f"padding: 6px 12px;")
            btn.clicked.connect(lambda _, q=qty: self.quick_add_stock(q))
            quick_row.addWidget(btn)
        quick_row.addStretch()
        form_lyt.addLayout(quick_row)
        
        form_lyt.addStretch()
        content.addWidget(form_frame, 1)
        
        # === RIGHT: Product List ===
        list_frame = QFrame()
        list_lyt = QVBoxLayout(list_frame)
        list_lyt.setContentsMargins(15, 15, 15, 15)
        list_lyt.setSpacing(10)
        
        list_title = QLabel("📋 ALL PRODUCTS")
        list_title.setStyleSheet(f"color: {BLUE}; font-size: 14px; font-weight: bold; border: none;")
        list_lyt.addWidget(list_title)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products...")
        self.search_input.textChanged.connect(self.search_products)
        list_lyt.addWidget(self.search_input)
        
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(4)
        self.product_table.setHorizontalHeaderLabels(['Barcode', 'Name', 'MRP', 'Stock'])
        self.product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setColumnWidth(0, 100)
        self.product_table.setColumnWidth(2, 80)
        self.product_table.setColumnWidth(3, 60)
        self.product_table.doubleClicked.connect(self.load_selected)
        list_lyt.addWidget(self.product_table)
        
        content.addWidget(list_frame, 1)
        layout.addLayout(content, 1)
        
        self.statusBar().showMessage("Scan barcode to add/edit products")
    
    def lookup_barcode(self):
        """Look up barcode."""
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
        
        query = "SELECT * FROM simple_products WHERE barcode = ?"
        results = db.execute_query(query, (barcode,))
        
        if results:
            p = results[0]
            self.current_product_id = p['id']
            self.name_input.setText(p['name'])
            self.mrp_input.setValue(p['mrp'] or 0)
            self.cost_input.setValue(p['cost_price'] or 0)
            self.stock_input.setValue(p['stock'] or 0)
            
            cat = p.get('category', '')
            idx = self.category_input.findText(cat)
            if idx >= 0:
                self.category_input.setCurrentIndex(idx)
            else:
                self.category_input.setCurrentText(cat)
            
            self.status_label.setText(f"✓ Found: {p['name']}")
            self.status_label.setStyleSheet(f"color: {GREEN}; font-size: 13px; font-weight: bold; border: none;")
            self.name_input.setFocus()
        else:
            self.current_product_id = None
            self.name_input.clear()
            self.mrp_input.setValue(0)
            self.cost_input.setValue(0)
            self.stock_input.setValue(0)
            self.category_input.setCurrentIndex(0)
            
            self.status_label.setText(f"➕ New barcode: {barcode}")
            self.status_label.setStyleSheet(f"color: {BLUE}; font-size: 13px; font-weight: bold; border: none;")
            self.name_input.setFocus()
    
    def save_product(self):
        """Save product."""
        barcode = self.barcode_input.text().strip()
        name = self.name_input.text().strip()
        
        if not barcode:
            QMessageBox.warning(self, "Required", "Scan barcode first")
            return
        
        if not name:
            QMessageBox.warning(self, "Required", "Enter product name")
            return
        
        mrp = self.mrp_input.value()
        cost = self.cost_input.value()
        stock = self.stock_input.value()
        category = self.category_input.currentText()
        
        try:
            if self.current_product_id:
                query = """
                    UPDATE simple_products 
                    SET name = ?, mrp = ?, cost_price = ?, stock = ?, category = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """
                db.execute_update(query, (name, mrp, cost, stock, category, self.current_product_id))
                self.statusBar().showMessage(f"✓ Updated: {name}")
            else:
                query = """
                    INSERT INTO simple_products (barcode, name, mrp, cost_price, stock, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                db.execute_insert(query, (barcode, name, mrp, cost, stock, category))
                self.statusBar().showMessage(f"✓ Added: {name}")
            
            self.load_products()
            self.clear_form()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {e}")
    
    def delete_product(self):
        """Delete product."""
        if not self.current_product_id:
            return
        
        name = self.name_input.text()
        if QMessageBox.question(self, "Delete", f"Delete '{name}'?") == QMessageBox.Yes:
            query = "DELETE FROM simple_products WHERE id = ?"
            db.execute_update(query, (self.current_product_id,))
            self.load_products()
            self.clear_form()
            self.statusBar().showMessage(f"Deleted: {name}")
    
    def quick_add_stock(self, qty):
        """Quick add stock."""
        self.stock_input.setValue(self.stock_input.value() + qty)
    
    def clear_form(self):
        """Clear form."""
        self.current_product_id = None
        self.barcode_input.clear()
        self.name_input.clear()
        self.mrp_input.setValue(0)
        self.cost_input.setValue(0)
        self.stock_input.setValue(0)
        self.category_input.setCurrentIndex(0)
        self.status_label.clear()
        self.barcode_input.setFocus()
    
    def load_products(self, search_text=None):
        """Load products."""
        if search_text:
            query = """
                SELECT * FROM simple_products 
                WHERE barcode LIKE ? OR name LIKE ?
                ORDER BY name
            """
            pattern = f"%{search_text}%"
            results = db.execute_query(query, (pattern, pattern))
        else:
            query = "SELECT * FROM simple_products ORDER BY name"
            results = db.execute_query(query)
        
        self.product_table.setRowCount(len(results))
        for i, p in enumerate(results):
            self.product_table.setItem(i, 0, QTableWidgetItem(p['barcode']))
            self.product_table.setItem(i, 1, QTableWidgetItem(p['name']))
            self.product_table.setItem(i, 2, QTableWidgetItem(f"₹{p['mrp']:.2f}"))
            self.product_table.setItem(i, 3, QTableWidgetItem(str(p['stock'])))
            self.product_table.item(i, 0).setData(Qt.UserRole, p['id'])
        
        self.statusBar().showMessage(f"Loaded {len(results)} products")
    
    def search_products(self, text):
        """Search products."""
        self.load_products(text if text else None)
    
    def load_selected(self):
        """Load selected."""
        row = self.product_table.currentRow()
        if row < 0:
            return
        barcode = self.product_table.item(row, 0).text()
        self.barcode_input.setText(barcode)
        self.lookup_barcode()
