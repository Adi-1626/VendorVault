"""
Login window with dark theme.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from src.logic.employee_mgmt import EmployeeService
from src.models.employee import Employee
from src.ui.dark_theme import get_dark_stylesheet, PRIMARY, TEXT_WHITE, CARD_BG, BORDER, TEXT_GRAY


class LoginWindow(QWidget):
    """Dark mode login window."""
    
    login_successful = Signal(Employee)
    
    def __init__(self):
        super().__init__()
        self.employee_service = EmployeeService()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up dark mode UI."""
        self.setWindowTitle("Login - Bill Generation System")
        self.showMaximized()
        
        # Apply dark theme
        self.setStyleSheet(get_dark_stylesheet())
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Center card
        center_widget = QFrame()
        center_widget.setMaximumWidth(600)
        center_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_BG};
                border: 2px solid {BORDER};
                border-radius: 20px;
            }}
        """)
        
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(60, 50, 60, 50)
        center_layout.setSpacing(25)
        
        # Title
        title = QLabel("⚡ Lightning POS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {PRIMARY}; font-size: 36px; font-weight: bold; border: none;")
        center_layout.addWidget(title)
        
        subtitle = QLabel("Please login to continue")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 18px; border: none;")
        center_layout.addWidget(subtitle)
        
        center_layout.addSpacing(20)
        
        # Role selection
        role_label = QLabel("Select Role:")
        role_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {TEXT_WHITE}; border: none;")
        center_layout.addWidget(role_label)
        
        role_layout = QHBoxLayout()
        role_layout.setSpacing(30)
        
        self.admin_radio = QRadioButton("Admin")
        self.admin_radio.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 16px;")
        self.employee_radio = QRadioButton("Employee")
        self.employee_radio.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 16px;")
        self.employee_radio.setChecked(True)
        
        self.role_group = QButtonGroup()
        self.role_group.addButton(self.admin_radio)
        self.role_group.addButton(self.employee_radio)
        
        role_layout.addWidget(self.admin_radio)
        role_layout.addWidget(self.employee_radio)
        role_layout.addStretch()
        center_layout.addLayout(role_layout)
        
        center_layout.addSpacing(10)
        
        # Employee ID
        emp_label = QLabel("Employee ID:")
        emp_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {TEXT_WHITE}; border: none;")
        center_layout.addWidget(emp_label)
        
        self.emp_id_input = QLineEdit()
        self.emp_id_input.setPlaceholderText("Enter your employee ID (e.g., ADM001)")
        self.emp_id_input.setMinimumHeight(55)
        self.emp_id_input.returnPressed.connect(self.handle_login)
        center_layout.addWidget(self.emp_id_input)
        
        # Password
        pass_label = QLabel("Password:")
        pass_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {TEXT_WHITE}; border: none;")
        center_layout.addWidget(pass_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(55)
        self.password_input.returnPressed.connect(self.handle_login)
        center_layout.addWidget(self.password_input)
        
        center_layout.addSpacing(15)
        
        # Login button
        self.login_btn = QPushButton("Login")
        self.login_btn.setMinimumHeight(60)
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563EB;
            }}
        """)
        self.login_btn.clicked.connect(self.handle_login)
        center_layout.addWidget(self.login_btn)
        
        center_layout.addSpacing(15)
        
        # Hint
        hint = QLabel("Test: ADM001/admin123 or EMP001/emp123")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 14px; border: none;")
        center_layout.addWidget(hint)
        
        # Center the card
        outer = QVBoxLayout()
        outer.addStretch()
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(center_widget)
        h_layout.addStretch()
        outer.addLayout(h_layout)
        outer.addStretch()
        
        # Footer
        footer = QLabel("© 2026 JAY LAXMI. All rights reserved.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 13px; border: none;")
        outer.addWidget(footer)
        
        main_layout.addLayout(outer)
        self.setLayout(main_layout)
        self.emp_id_input.setFocus()
    
    def handle_login(self):
        """Handle login."""
        emp_id = self.emp_id_input.text().strip()
        password = self.password_input.text()
        
        if not emp_id:
            QMessageBox.warning(self, "Error", "Enter employee ID")
            self.emp_id_input.setFocus()
            return
        
        if not password:
            QMessageBox.warning(self, "Error", "Enter password")
            self.password_input.setFocus()
            return
        
        employee = self.employee_service.authenticate(emp_id, password)
        
        if employee:
            is_admin_role = employee.is_admin()
            is_admin_selected = self.admin_radio.isChecked()
            
            if is_admin_role and not is_admin_selected:
                QMessageBox.warning(self, "Role Mismatch", "You are an Admin. Select 'Admin' role.")
                return
            
            if not is_admin_role and is_admin_selected:
                QMessageBox.warning(self, "Role Mismatch", "You are not an Admin. Select 'Employee' role.")
                return
            
            self.login_successful.emit(employee)
            self.close()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid ID or password")
            self.password_input.clear()
            self.password_input.setFocus()
