"""
Employee management window - Dark Mode.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QMessageBox, QHeaderView, QDialog, QFormLayout, QComboBox
)
from PySide6.QtCore import Qt
from src.logic.employee_mgmt import EmployeeService
from src.models.employee import Employee
from src.ui.dark_theme import get_dark_stylesheet, PRIMARY, SUCCESS, DANGER, TEXT_WHITE, TEXT_GRAY


class EmployeeWindow(QMainWindow):
    """Employee management window with dark theme."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.employee_service = EmployeeService()
        self.setup_ui()
        self.load_employees()
    
    def setup_ui(self):
        """Set up dark mode UI."""
        self.setWindowTitle("Employee Management")
        self.setGeometry(150, 150, 900, 600)
        self.setStyleSheet(get_dark_stylesheet())
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Employee Management")
        header.setStyleSheet(f"color: {PRIMARY}; font-size: 28px; font-weight: bold;")
        layout.addWidget(header)
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.setSpacing(15)
        
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 16px; font-weight: bold;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search employees...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.search_employees)
        search_layout.addWidget(self.search_input)
        
        search_layout.addStretch()
        
        add_btn = QPushButton("Add Employee")
        add_btn.setStyleSheet(f"background: {SUCCESS}; color: white; border: none;")
        add_btn.clicked.connect(self.add_employee)
        search_layout.addWidget(add_btn)
        
        layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Employee ID", "Name", "Role", "Contact", "Email", "Actions"])
        self.table.setColumnWidth(5, 180)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(60)
        layout.addWidget(self.table)
        
        central.setLayout(layout)
    
    def load_employees(self, employees=None):
        """Load employees into table."""
        if employees is None:
            employees = self.employee_service.get_all_employees()
        
        self.table.setRowCount(len(employees))
        for idx, emp in enumerate(employees):
            self.table.setItem(idx, 0, QTableWidgetItem(emp.emp_id))
            self.table.setItem(idx, 1, QTableWidgetItem(emp.get_full_name()))
            self.table.setItem(idx, 2, QTableWidgetItem(emp.role))
            self.table.setItem(idx, 3, QTableWidgetItem(emp.contact_number))
            self.table.setItem(idx, 4, QTableWidgetItem(emp.email or ""))
            
            # Actions
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(8)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(f"background: {PRIMARY}; color: white; border: none; padding: 4px 10px; border-radius: 4px;")
            edit_btn.clicked.connect(lambda checked, e=emp: self.edit_employee(e))
            action_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet(f"background: {DANGER}; color: white; border: none; padding: 4px 10px; border-radius: 4px;")
            delete_btn.clicked.connect(lambda checked, e=emp: self.delete_employee(e))
            action_layout.addWidget(delete_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(idx, 5, action_widget)
    
    def search_employees(self, text: str):
        """Search employees."""
        if text:
            employees = self.employee_service.search_employees(text)
        else:
            employees = self.employee_service.get_all_employees()
        self.load_employees(employees)
    
    def add_employee(self):
        """Add new employee."""
        dialog = EmployeeDialog(self)
        if dialog.exec():
            employee = dialog.get_employee()
            if self.employee_service.add_employee(employee):
                QMessageBox.information(self, "Success", "Employee added")
                self.load_employees()
    
    def edit_employee(self, employee: Employee):
        """Edit employee."""
        dialog = EmployeeDialog(self, employee)
        if dialog.exec():
            updated = dialog.get_employee()
            if self.employee_service.update_employee(updated):
                QMessageBox.information(self, "Success", "Employee updated")
                self.load_employees()
    
    def delete_employee(self, employee: Employee):
        """Delete employee."""
        reply = QMessageBox.question(self, "Delete", f"Delete '{employee.get_full_name()}'?",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.employee_service.delete_employee(employee.emp_id):
                QMessageBox.information(self, "Success", "Employee deleted")
                self.load_employees()


class EmployeeDialog(QDialog):
    """Employee add/edit dialog with dark theme."""
    
    def __init__(self, parent=None, employee: Employee = None):
        super().__init__(parent)
        self.employee = employee
        self.employee_service = EmployeeService()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dark UI."""
        self.setWindowTitle("Add Employee" if not self.employee else "Edit Employee")
        self.setMinimumWidth(450)
        self.setStyleSheet(get_dark_stylesheet())
        
        layout = QFormLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        if self.employee is None:
            emp_id = self.employee_service.generate_employee_id()
            self.id_input = QLineEdit(emp_id)
            self.id_input.setReadOnly(True)
        else:
            self.id_input = QLineEdit(self.employee.emp_id)
            self.id_input.setReadOnly(True)
        layout.addRow("Employee ID:", self.id_input)
        
        self.first_name_input = QLineEdit(self.employee.first_name if self.employee else "")
        layout.addRow("First Name:", self.first_name_input)
        
        self.last_name_input = QLineEdit(self.employee.last_name if self.employee else "")
        layout.addRow("Last Name:", self.last_name_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Leave blank to keep current" if self.employee else "Password")
        layout.addRow("Password:", self.password_input)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Employee", "Admin"])
        if self.employee:
            self.role_combo.setCurrentText(self.employee.role)
        layout.addRow("Role:", self.role_combo)
        
        self.contact_input = QLineEdit(self.employee.contact_number if self.employee else "")
        self.contact_input.setPlaceholderText("10-digit phone")
        layout.addRow("Contact:", self.contact_input)
        
        self.email_input = QLineEdit(self.employee.email if self.employee and self.employee.email else "")
        self.email_input.setPlaceholderText("Optional")
        layout.addRow("Email:", self.email_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"background: {SUCCESS}; color: white; border: none;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"background: {DANGER}; color: white; border: none;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow("", btn_layout)
        self.setLayout(layout)
    
    def get_employee(self) -> Employee:
        """Get employee from form."""
        password = self.password_input.text()
        if self.employee and not password:
            password = self.employee.password
        elif password:
            password = Employee.hash_password(password)
        
        return Employee(
            emp_id=self.id_input.text(),
            first_name=self.first_name_input.text(),
            last_name=self.last_name_input.text(),
            password=password,
            role=self.role_combo.currentText(),
            contact_number=self.contact_input.text(),
            email=self.email_input.text() if self.email_input.text() else None
        )
