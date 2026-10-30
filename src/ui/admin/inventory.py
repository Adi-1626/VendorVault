"""
Inventory management window.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from src.logic.inventory import InventoryService
from src.models.product import Product
from src.ui import theme as T


class InventoryWindow(QMainWindow):
    """Inventory management window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.inventory_service = InventoryService()
        self.setup_ui()
        self.load_products()
    
    def setup_ui(self):
        """Set up UI."""
        self.setWindowTitle("Inventory Management")
        self.setGeometry(150, 150, 1000, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Inventory Management")
        header.setProperty("role", "h1")
        layout.addWidget(header)
        
        # Search and Actions
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products...")
        self.search_input.textChanged.connect(self.search_products)
        search_layout.addWidget(self.search_input)
        search_layout.addStretch()
        
        # Add Product button
        add_btn = QPushButton("Add Product")
        add_btn.setProperty("variant", "primary")
        add_btn.clicked.connect(self.show_add_product_message)
        search_layout.addWidget(add_btn)
        
        layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Product Name", "Category", "Unit", "Stock", "MRP (₹)", "Supplier"
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 60)   # ID
        self.table.setColumnWidth(2, 120)  # Category
        self.table.setColumnWidth(3, 80)   # Unit
        self.table.setColumnWidth(4, 100)  # Stock - wider for visibility
        self.table.setColumnWidth(5, 100)  # MRP
        self.table.setColumnWidth(6, 120)  # Supplier
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Increase row height and font size for better visibility
        self.table.verticalHeader().setDefaultSectionSize(60)  # Increased to 60px for editing
        
        layout.addWidget(self.table)
        
        central.setLayout(layout)
    
    def load_products(self, products=None):
        """Load products into table."""
        if products is None:
            products = self.inventory_service.get_all_products()
        
        self.table.setRowCount(len(products))
        for idx, product in enumerate(products):
            self.table.setItem(idx, 0, QTableWidgetItem(str(product.product_id)))
            self.table.setItem(idx, 1, QTableWidgetItem(product.product_name))
            self.table.setItem(idx, 2, QTableWidgetItem(product.product_cat))
            self.table.setItem(idx, 3, QTableWidgetItem(product.unit))
            
            # Stock with color coding
            stock_item = QTableWidgetItem(str(int(product.stock)))
            if product.stock < 10:
                stock_item.setForeground(QColor(T.DANGER))
            elif product.stock < 50:
                stock_item.setForeground(QColor(T.WARNING))
            else:
                stock_item.setForeground(QColor(T.SUCCESS))
            self.table.setItem(idx, 4, stock_item)
            
            self.table.setItem(idx, 5, QTableWidgetItem(f"₹{product.mrp:.2f}"))
            self.table.setItem(idx, 6, QTableWidgetItem(product.supplier_name if product.supplier_name else "-"))
    
    def search_products(self, text: str):
        """Search products."""
        if text:
            products = self.inventory_service.search_products(text)
        else:
            products = self.inventory_service.get_all_products()
        self.load_products(products)
    
    def show_add_product_message(self):
        """Open product dialog to add new product."""
        from src.ui.admin.product_dialog import ProductDialog
        dialog = ProductDialog(self)
        if dialog.exec():
            product_data = dialog.get_product_data()
            
            # Save to database
            if self.inventory_service.add_product_with_variants(product_data):
                QMessageBox.information(
                    self,
                    "Success",
                    f"Product '{product_data['product_name']}' with {len(product_data['variants'])} variant(s) added successfully!"
                )
                # Reload products
                self.load_products()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to save product. Please check the console for details."
                )
