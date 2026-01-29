"""
Product Type management window - Dark Mode.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QMessageBox, QHeaderView, QDialog, QFormLayout, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from src.ui.dark_theme import get_dark_stylesheet, PRIMARY, SUCCESS, DANGER, TEXT_WHITE, TEXT_GRAY


class ProductTypeManagementWindow(QMainWindow):
    """Product type management window with dark theme."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_product_types()
    
    def setup_ui(self):
        """Set up dark mode UI."""
        self.setWindowTitle("Product Type Management")
        self.setGeometry(150, 150, 1000, 600)
        self.setStyleSheet(get_dark_stylesheet())
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Product Type Management")
        header.setStyleSheet(f"color: {PRIMARY}; font-size: 28px; font-weight: bold;")
        layout.addWidget(header)
        
        # Search and actions
        search_layout = QHBoxLayout()
        search_layout.setSpacing(15)
        
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 16px; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search product types...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.search_types)
        search_layout.addWidget(self.search_input)
        
        search_layout.addStretch()
        
        add_btn = QPushButton("➕ Add Product Type")
        add_btn.setStyleSheet(f"background: {SUCCESS}; color: white; border: none;")
        add_btn.clicked.connect(self.add_type)
        search_layout.addWidget(add_btn)
        
        layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Type Name", "HSN Code", "Display Order", "Status", "Actions"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 180)
        self.table.verticalHeader().setDefaultSectionSize(60)
        
        layout.addWidget(self.table)
        central.setLayout(layout)
    
    def load_product_types(self, types=None):
        """Load product types into table."""
        from src.logic.product_type_mgmt import ProductTypeService
        
        if types is None:
            service = ProductTypeService()
            types = service.get_all_product_types()
        
        self.table.setRowCount(len(types))
        for idx, ptype in enumerate(types):
            self.table.setItem(idx, 0, QTableWidgetItem(str(ptype['product_type_id'])))
            self.table.setItem(idx, 1, QTableWidgetItem(ptype['type_name']))
            self.table.setItem(idx, 2, QTableWidgetItem(ptype.get('hsn_code', '')))
            self.table.setItem(idx, 3, QTableWidgetItem(str(ptype.get('display_order', 0))))
            
            # Status
            status = "Active" if ptype.get('is_active', 1) else "Inactive"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(SUCCESS if ptype.get('is_active', 1) else DANGER))
            self.table.setItem(idx, 4, status_item)
            
            # Actions
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(8)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(f"background: {PRIMARY}; color: white; border: none; padding: 4px 10px; border-radius: 4px;")
            edit_btn.clicked.connect(lambda checked, t=ptype: self.edit_type(t))
            action_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet(f"background: {DANGER}; color: white; border: none; padding: 4px 10px; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, t=ptype: self.delete_type(t))
            action_layout.addWidget(delete_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(idx, 5, action_widget)
    
    def search_types(self, text: str):
        """Search product types."""
        from src.logic.product_type_mgmt import ProductTypeService
        service = ProductTypeService()
        
        if text:
            types = service.search_product_types(text)
        else:
            types = service.get_all_product_types()
        self.load_product_types(types)
    
    def add_type(self):
        """Add new product type."""
        dialog = ProductTypeDialog(self)
        if dialog.exec():
            type_data = dialog.get_type_data()
            from src.logic.product_type_mgmt import ProductTypeService
            service = ProductTypeService()
            
            if service.add_product_type(type_data):
                QMessageBox.information(self, "Success", "Product type added!")
                self.load_product_types()
            else:
                QMessageBox.critical(self, "Error", "Failed to add product type")
    
    def edit_type(self, ptype):
        """Edit existing product type."""
        dialog = ProductTypeDialog(self, ptype)
        if dialog.exec():
            type_data = dialog.get_type_data()
            from src.logic.product_type_mgmt import ProductTypeService
            service = ProductTypeService()
            
            if service.update_product_type(ptype['product_type_id'], type_data):
                QMessageBox.information(self, "Success", "Product type updated!")
                self.load_product_types()
            else:
                QMessageBox.critical(self, "Error", "Failed to update product type")
    
    def delete_type(self, ptype):
        """Delete product type."""
        reply = QMessageBox.question(self, "Delete", f"Delete '{ptype['type_name']}'?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            from src.logic.product_type_mgmt import ProductTypeService
            service = ProductTypeService()
            
            if service.delete_product_type(ptype['product_type_id']):
                QMessageBox.information(self, "Success", "Product type deleted!")
                self.load_product_types()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete. Products may be using this type.")


class ProductTypeDialog(QDialog):
    """Product Type add/edit dialog with dark theme."""
    
    def __init__(self, parent=None, ptype=None):
        super().__init__(parent)
        self.ptype = ptype
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dark UI."""
        self.setWindowTitle("Add Product Type" if not self.ptype else "Edit Product Type")
        self.setMinimumWidth(500)
        self.setStyleSheet(get_dark_stylesheet())
        
        layout = QFormLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        self.name_input = QLineEdit(self.ptype['type_name'] if self.ptype else "")
        self.name_input.setPlaceholderText("e.g., Namkeen, Chips, Dry Fruits")
        layout.addRow("Type Name*:", self.name_input)
        
        self.hsn_input = QLineEdit(self.ptype.get('hsn_code', '') if self.ptype else "")
        self.hsn_input.setPlaceholderText("e.g., 2106 (for Namkeen)")
        self.hsn_input.setMaxLength(8)
        layout.addRow("HSN Code:", self.hsn_input)
        
        self.order_input = QSpinBox()
        self.order_input.setRange(0, 999)
        self.order_input.setValue(self.ptype.get('display_order', 0) if self.ptype else 0)
        layout.addRow("Display Order:", self.order_input)
        
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(self.ptype.get('is_active', 1) if self.ptype else True)
        layout.addRow("Status:", self.active_checkbox)
        
        # Help text
        help_label = QLabel("💡 HSN code is for GST. Display order affects sorting.")
        help_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 13px;")
        layout.addRow("", help_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"background: {SUCCESS}; color: white; border: none;")
        save_btn.clicked.connect(self.validate_and_accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"background: {DANGER}; color: white; border: none;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow("", btn_layout)
        self.setLayout(layout)
    
    def validate_and_accept(self):
        """Validate and accept."""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Error", "Type name required!")
            return
        self.accept()
    
    def get_type_data(self):
        """Get type data from form."""
        return {
            'type_name': self.name_input.text().strip(),
            'hsn_code': self.hsn_input.text().strip(),
            'display_order': self.order_input.value(),
            'is_active': 1 if self.active_checkbox.isChecked() else 0
        }
