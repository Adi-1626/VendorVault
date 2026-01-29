"""
Brand management window - Dark Mode.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QMessageBox, QHeaderView, QDialog, QFormLayout, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from src.ui.dark_theme import get_dark_stylesheet, PRIMARY, SUCCESS, DANGER, TEXT_WHITE, TEXT_GRAY


class BrandManagementWindow(QMainWindow):
    """Brand management window with dark theme."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_brands()
    
    def setup_ui(self):
        """Set up dark mode UI."""
        self.setWindowTitle("Brand Management")
        self.setGeometry(150, 150, 900, 600)
        self.setStyleSheet(get_dark_stylesheet())
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Brand Management")
        header.setStyleSheet(f"color: {PRIMARY}; font-size: 28px; font-weight: bold;")
        layout.addWidget(header)
        
        # Search and actions
        search_layout = QHBoxLayout()
        search_layout.setSpacing(15)
        
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 16px; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search brands...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.search_brands)
        search_layout.addWidget(self.search_input)
        
        search_layout.addStretch()
        
        add_btn = QPushButton("➕ Add Brand")
        add_btn.setStyleSheet(f"background: {SUCCESS}; color: white; border: none;")
        add_btn.clicked.connect(self.add_brand)
        search_layout.addWidget(add_btn)
        
        layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Brand Name", "Description", "Status", "Actions"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 180)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(60)
        
        layout.addWidget(self.table)
        central.setLayout(layout)
    
    def load_brands(self, brands=None):
        """Load brands into table."""
        from src.logic.brand_mgmt import BrandService
        
        if brands is None:
            brand_service = BrandService()
            brands = brand_service.get_all_brands()
        
        self.table.setRowCount(len(brands))
        for idx, brand in enumerate(brands):
            self.table.setItem(idx, 0, QTableWidgetItem(str(brand['brand_id'])))
            self.table.setItem(idx, 1, QTableWidgetItem(brand['brand_name']))
            self.table.setItem(idx, 2, QTableWidgetItem(brand.get('description', '')))
            
            # Status
            status = "Active" if brand.get('is_active', 1) else "Inactive"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(SUCCESS if brand.get('is_active', 1) else DANGER))
            self.table.setItem(idx, 3, status_item)
            
            # Actions
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(8)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(f"background: {PRIMARY}; color: white; border: none; padding: 4px 10px; border-radius: 4px;")
            edit_btn.clicked.connect(lambda checked, b=brand: self.edit_brand(b))
            action_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet(f"background: {DANGER}; color: white; border: none; padding: 4px 10px; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, b=brand: self.delete_brand(b))
            action_layout.addWidget(delete_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(idx, 4, action_widget)
    
    def search_brands(self, text: str):
        """Search brands."""
        from src.logic.brand_mgmt import BrandService
        brand_service = BrandService()
        
        if text:
            brands = brand_service.search_brands(text)
        else:
            brands = brand_service.get_all_brands()
        self.load_brands(brands)
    
    def add_brand(self):
        """Add new brand."""
        dialog = BrandDialog(self)
        if dialog.exec():
            brand_data = dialog.get_brand_data()
            from src.logic.brand_mgmt import BrandService
            brand_service = BrandService()
            
            if brand_service.add_brand(brand_data):
                QMessageBox.information(self, "Success", "Brand added!")
                self.load_brands()
            else:
                QMessageBox.critical(self, "Error", "Failed to add brand")
    
    def edit_brand(self, brand):
        """Edit existing brand."""
        dialog = BrandDialog(self, brand)
        if dialog.exec():
            brand_data = dialog.get_brand_data()
            from src.logic.brand_mgmt import BrandService
            brand_service = BrandService()
            
            if brand_service.update_brand(brand['brand_id'], brand_data):
                QMessageBox.information(self, "Success", "Brand updated!")
                self.load_brands()
            else:
                QMessageBox.critical(self, "Error", "Failed to update brand")
    
    def delete_brand(self, brand):
        """Delete brand."""
        reply = QMessageBox.question(self, "Delete", f"Delete '{brand['brand_name']}'?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            from src.logic.brand_mgmt import BrandService
            brand_service = BrandService()
            
            if brand_service.delete_brand(brand['brand_id']):
                QMessageBox.information(self, "Success", "Brand deleted!")
                self.load_brands()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete brand")


class BrandDialog(QDialog):
    """Brand add/edit dialog with dark theme."""
    
    def __init__(self, parent=None, brand=None):
        super().__init__(parent)
        self.brand = brand
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dark UI."""
        self.setWindowTitle("Add Brand" if not self.brand else "Edit Brand")
        self.setMinimumWidth(500)
        self.setStyleSheet(get_dark_stylesheet())
        
        layout = QFormLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        self.name_input = QLineEdit(self.brand['brand_name'] if self.brand else "")
        self.name_input.setPlaceholderText("e.g., Jaylaxmi, Haldiram's")
        layout.addRow("Brand Name*:", self.name_input)
        
        self.description_input = QTextEdit(self.brand.get('description', '') if self.brand else "")
        self.description_input.setPlaceholderText("Optional description")
        self.description_input.setMaximumHeight(100)
        layout.addRow("Description:", self.description_input)
        
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(self.brand.get('is_active', 1) if self.brand else True)
        layout.addRow("Status:", self.active_checkbox)
        
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
            QMessageBox.warning(self, "Error", "Brand name required!")
            return
        self.accept()
    
    def get_brand_data(self):
        """Get brand data from form."""
        return {
            'brand_name': self.name_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'is_active': 1 if self.active_checkbox.isChecked() else 0
        }
