"""
Product with Variant management dialog.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTextEdit, QCheckBox,
    QTableWidget, QTableWidgetItem, QWidget, QMessageBox,
    QSpinBox, QDoubleSpinBox, QHeaderView, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class ProductDialog(QDialog):
    """Comprehensive product entry dialog with variant management."""
    
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.product = product
        self.variants = []
        self.setup_ui()
        
        if product:
            self.load_product_data()
    
    def setup_ui(self):
        """Setup UI."""
        self.setWindowTitle("Add Product" if self.product is None else "Edit Product")
        self.setMinimumSize(900, 700)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        
        # Header
        header = QLabel("Product & Variant Management")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #000000;")
        main_layout.addWidget(header)
        
        # Tab widget for organization
        tabs = QTabWidget()
        
        # Tab 1: Product Info
        product_tab = QWidget()
        product_layout = QFormLayout()
        product_layout.setSpacing(12)
        
        # Product Code (auto-generated or display)
        self.code_input = QLineEdit()
        if not self.product:
            # Auto-generate product code preview
            self.code_input.setPlaceholderText("Auto-generated (e.g., JL-NAM-004)")
            self.code_input.setReadOnly(True)
            # Set to empty, will be generated on type selection
        else:
            self.code_input.setText(self.product.get('product_code', ''))
        product_layout.addRow("Product Code:", self.code_input)
        
        # Product Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Masala Peanuts")
        product_layout.addRow("Product Name*:", self.name_input)
        
        # Brand dropdown
        self.brand_combo = QComboBox()
        self.load_brands()
        product_layout.addRow("Brand*:", self.brand_combo)
        
        # Product Type dropdown
        self.type_combo = QComboBox()
        self.load_product_types()
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        product_layout.addRow("Product Type*:", self.type_combo)
        
        # Base Unit
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["Kg", "Liter", "Piece", "Box"])
        product_layout.addRow("Base Unit:", self.unit_combo)
        
        # HSN Code (auto-filled from type, editable)
        self.hsn_input = QLineEdit()
        self.hsn_input.setPlaceholderText("Auto-filled from Product Type")
        product_layout.addRow("HSN Code:", self.hsn_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Optional product description")
        product_layout.addRow("Description:", self.description_input)
        
        # Active status
        self.active_checkbox = QCheckBox("Product Active")
        self.active_checkbox.setChecked(True)
        product_layout.addRow("Status:", self.active_checkbox)
        
        product_tab.setLayout(product_layout)
        tabs.addTab(product_tab, "📦 Product Info")
        
        # Tab 2: Variants
        variant_tab = QWidget()
        variant_layout = QVBoxLayout()
        
        variant_header = QLabel("Product Variants")
        variant_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        variant_layout.addWidget(variant_header)
        
        help_text = QLabel("💡 Add at least one variant (e.g., 250g Pack, 500g Pack). One must be marked as default.")
        help_text.setStyleSheet("color: #6B7280; font-size: 12px;")
        help_text.setWordWrap(True)
        variant_layout.addWidget(help_text)
        
        # Variant table
        self.variant_table = QTableWidget()
        self.variant_table.setColumnCount(8)
        self.variant_table.setHorizontalHeaderLabels([
            "Variant Name", "SKU", "Size", "Unit", "MRP (₹)", "Cost (₹)", "Initial Stock", "Default"
        ])
        
        # Column widths
        self.variant_table.setColumnWidth(0, 150)
        self.variant_table.setColumnWidth(1, 130)
        self.variant_table.setColumnWidth(2, 70)
        self.variant_table.setColumnWidth(3, 60)
        self.variant_table.setColumnWidth(4, 90)
        self.variant_table.setColumnWidth(5, 90)
        self.variant_table.setColumnWidth(6, 100)
        self.variant_table.setColumnWidth(7, 70)
        
        self.variant_table.verticalHeader().setDefaultSectionSize(50)
        variant_layout.addWidget(self.variant_table)
        
        # Variant buttons
        variant_btn_layout = QHBoxLayout()
        add_variant_btn = QPushButton("➕ Add Variant")
        add_variant_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        add_variant_btn.clicked.connect(self.add_variant)
        
        remove_variant_btn = QPushButton("🗑️ Remove Selected")
        remove_variant_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        remove_variant_btn.clicked.connect(self.remove_variant)
        
        variant_btn_layout.addWidget(add_variant_btn)
        variant_btn_layout.addWidget(remove_variant_btn)
        variant_btn_layout.addStretch()
        variant_layout.addLayout(variant_btn_layout)
        
        variant_tab.setLayout(variant_layout)
        tabs.addTab(variant_tab, "📊 Variants")
        
        main_layout.addWidget(tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Save Product")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                padding: 10px 24px;
                font-size: 15px;
                font-weight: 600;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        save_btn.clicked.connect(self.validate_and_save)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def load_brands(self):
        """Load brands into combo box."""
        from src.logic.brand_mgmt import BrandService
        service = BrandService()
        brands = service.get_active_brands()
        
        for brand in brands:
            self.brand_combo.addItem(brand['brand_name'], brand['brand_id'])
    
    def load_product_types(self):
        """Load product types into combo box."""
        from src.logic.product_type_mgmt import ProductTypeService
        service = ProductTypeService()
        types = service.get_active_product_types()
        
        for ptype in types:
            self.type_combo.addItem(ptype['type_name'], ptype['product_type_id'])
    
    def on_type_changed(self, index):
        """Auto-fill HSN code and update product code preview when type changes."""
        if index >= 0:
            from src.logic.product_type_mgmt import ProductTypeService
            from src.logic.inventory import InventoryService
            
            type_service = ProductTypeService()
            type_id = self.type_combo.currentData()
            ptype = type_service.get_product_type_by_id(type_id)
            
            # Auto-fill HSN code
            if ptype and ptype.get('hsn_code'):
                self.hsn_input.setText(ptype['hsn_code'])
            
            # Update product code preview if adding new product
            if not self.product:
                inv_service = InventoryService()
                code_preview = inv_service.get_next_product_code(type_id)
                self.code_input.setText(code_preview)
    
    def add_variant(self):
        """Add new variant row."""
        dialog = VariantDialog(self, self.name_input.text())
        if dialog.exec():
            variant_data = dialog.get_variant_data()
            
            # Auto-generate SKU if not provided
            if not variant_data['sku']:
                # Get product code prefix
                product_code = self.code_input.text() or "NEW"
                size_suffix = f"{int(variant_data['unit_size'])}{variant_data['size_unit']}"
                variant_data['sku'] = f"{product_code}-{size_suffix}".upper()
            
            self.add_variant_to_table(variant_data)
    
    def add_variant_to_table(self, variant_data):
        """Add variant to table."""
        row = self.variant_table.rowCount()
        self.variant_table.insertRow(row)
        
        self.variant_table.setItem(row, 0, QTableWidgetItem(variant_data['variant_name']))
        self.variant_table.setItem(row, 1, QTableWidgetItem(variant_data['sku']))
        self.variant_table.setItem(row, 2, QTableWidgetItem(str(variant_data['unit_size'])))
        self.variant_table.setItem(row, 3, QTableWidgetItem(variant_data['size_unit']))
        self.variant_table.setItem(row, 4, QTableWidgetItem(f"₹{variant_data['mrp']:.2f}"))
        self.variant_table.setItem(row, 5, QTableWidgetItem(f"₹{variant_data['cost_price']:.2f}"))
        self.variant_table.setItem(row, 6, QTableWidgetItem(str(variant_data['initial_stock'])))
        
        # Default checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(variant_data['is_default'])
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.setAlignment(Qt.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.variant_table.setCellWidget(row, 7, checkbox_widget)
    
    def remove_variant(self):
        """Remove selected variant."""
        current_row = self.variant_table.currentRow()
        if current_row >= 0:
            self.variant_table.removeRow(current_row)
    
    def validate_and_save(self):
        """Validate and save product."""
        # Validation
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Product name is required!")
            return
        
        if self.brand_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validation Error", "Please select a brand!")
            return
        
        if self.type_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validation Error", "Please select a product type!")
            return
        
        if self.variant_table.rowCount() == 0:
            QMessageBox.warning(self, "Validation Error", "Please add at least one variant!")
            return
        
        # Check for default variant
        has_default = False
        for row in range(self.variant_table.rowCount()):
            checkbox_widget = self.variant_table.cellWidget(row, 7)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    has_default = True
                    break
        
        if not has_default:
            QMessageBox.warning(self, "Validation Error", "Please mark one variant as default!")
            return
        
        self.accept()
    
    def load_product_data(self):
        """Load existing product data for editing."""
        # This would be implemented to load product and variants from database
        pass
    
    def get_product_data(self):
        """Get product data from form."""
        # Collect variants
        variants = []
        for row in range(self.variant_table.rowCount()):
            checkbox_widget = self.variant_table.cellWidget(row, 7)
            checkbox = checkbox_widget.findChild(QCheckBox) if checkbox_widget else None
            
            variant = {
                'variant_name': self.variant_table.item(row, 0).text(),
                'sku': self.variant_table.item(row, 1).text(),
                'unit_size': float(self.variant_table.item(row, 2).text()),
                'size_unit': self.variant_table.item(row, 3).text(),
                'mrp': float(self.variant_table.item(row, 4).text().replace('₹', '')),
                'cost_price': float(self.variant_table.item(row, 5).text().replace('₹', '')),
                'initial_stock': int(self.variant_table.item(row, 6).text()),
                'is_default': checkbox.isChecked() if checkbox else False
            }
            variants.append(variant)
        
        return {
            'product_code': self.code_input.text(),
            'product_name': self.name_input.text().strip(),
            'brand_id': self.brand_combo.currentData(),
            'product_type_id': self.type_combo.currentData(),
            'base_unit': self.unit_combo.currentText(),
            'hsn_code': self.hsn_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'is_active': 1 if self.active_checkbox.isChecked() else 0,
            'variants': variants
        }


class VariantDialog(QDialog):
    """Dialog for adding/editing a single variant."""
    
    def __init__(self, parent=None, product_name=""):
        super().__init__(parent)
        self.product_name = product_name
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI."""
        self.setWindowTitle("Add Variant")
        self.setMinimumWidth(450)
        
        layout = QFormLayout()
        layout.setSpacing(12)
        
        # Variant Name
        self.variant_name_input = QLineEdit()
        self.variant_name_input.setPlaceholderText("e.g., 250g Pack, 500g Pack, 1kg Pack")
        layout.addRow("Variant Name*:", self.variant_name_input)
        
        # SKU (auto-generated, can edit)
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("Auto-generated (e.g., JL-NAM-001-250G)")
        layout.addRow("SKU:", self.sku_input)
        
        # Unit Size
        size_layout = QHBoxLayout()
        self.size_input = QDoubleSpinBox()
        self.size_input.setRange(0.01, 99999)
        self.size_input.setDecimals(2)
        self.size_input.setValue(250)
        
        self.size_unit_combo = QComboBox()
        self.size_unit_combo.addItems(["g", "kg", "ml", "L"])
        
        size_layout.addWidget(self.size_input)
        size_layout.addWidget(self.size_unit_combo)
        layout.addRow("Package Size*:", size_layout)
        
        # MRP
        self.mrp_input = QDoubleSpinBox()
        self.mrp_input.setRange(0, 999999)
        self.mrp_input.setDecimals(2)
        self.mrp_input.setPrefix("₹")
        layout.addRow("MRP*:", self.mrp_input)
        
        # Cost Price
        self.cost_input = QDoubleSpinBox()
        self.cost_input.setRange(0, 999999)
        self.cost_input.setDecimals(2)
        self.cost_input.setPrefix("₹")
        layout.addRow("Cost Price:", self.cost_input)
        
        # Initial Stock
        self.stock_input = QSpinBox()
        self.stock_input.setRange(0, 999999)
        self.stock_input.setValue(0)
        layout.addRow("Initial Stock:", self.stock_input)
        
        # Is Default
        self.default_checkbox = QCheckBox("Mark as default variant")
        layout.addRow("", self.default_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow("", button_layout)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        """Validate and accept."""
        if not self.variant_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Variant name is required!")
            return
        
        if self.mrp_input.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "MRP must be greater than 0!")
            return
        
        if self.cost_input.value() > self.mrp_input.value():
            reply = QMessageBox.question(
                self,
                "Warning",
                "Cost price is higher than MRP. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        self.accept()
    
    def get_variant_data(self):
        """Get variant data from form."""
        return {
            'variant_name': self.variant_name_input.text().strip(),
            'sku': self.sku_input.text().strip(),
            'unit_size': self.size_input.value(),
            'size_unit': self.size_unit_combo.currentText(),
            'mrp': self.mrp_input.value(),
            'cost_price': self.cost_input.value(),
            'initial_stock': self.stock_input.value(),
            'is_default': self.default_checkbox.isChecked()
        }
