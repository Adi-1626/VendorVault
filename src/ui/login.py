"""
Login window with dark theme.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QRadioButton, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from src.logic.employee_mgmt import EmployeeService
from src.models.employee import Employee
from src.ui import theme as T
from src.ui.widgets import LogoMark, make_label
import config


class LoginWindow(QWidget):
    """Dark mode login window."""
    
    login_successful = Signal(Employee)
    
    def __init__(self):
        super().__init__()
        self.employee_service = EmployeeService()
        self.setup_ui()
    
    def setup_ui(self):
        """Centered sign-in card on the shared theme."""
        self.setWindowTitle("Login - VendorVault")
        self.setObjectName("LoginWindow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.showMaximized()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        center_widget = QFrame()
        center_widget.setProperty("card", "true")
        center_widget.setFixedWidth(420)

        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(36, 36, 36, 32)
        center_layout.setSpacing(0)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(LogoMark(30))
        title = make_label(config.APP_NAME, size=18, weight=600)
        brand.addWidget(title)
        brand.addStretch()
        center_layout.addLayout(brand)
        center_layout.addSpacing(28)

        center_layout.addWidget(make_label("Sign in", size=22, weight=600))
        center_layout.addSpacing(6)
        subtitle = make_label("Use your employee ID and password.", role="muted", size=13)
        center_layout.addWidget(subtitle)
        center_layout.addSpacing(24)

        # Role selection (styled as a segmented control)
        role_box = QFrame()
        role_box.setObjectName("RoleBox")
        role_box.setFixedHeight(40)
        role_box.setStyleSheet(
            f"QFrame#RoleBox {{ background: {T.SURFACE_2}; border: 1px solid {T.BORDER}; border-radius: 10px; }}"
            f"QRadioButton {{ color: {T.MUTED}; font-size: 13px; font-weight: 500; padding: 0 12px;"
            f" border: 1px solid transparent; border-radius: 8px; }}"
            f"QRadioButton:hover {{ color: {T.TEXT}; }}"
            f"QRadioButton:checked {{ background: {T.SURFACE_3}; border-color: {T.BORDER_2}; color: {T.TEXT}; font-weight: 600; }}"
            f"QRadioButton::indicator {{ width: 0px; height: 0px; border: none; background: transparent; }}")
        role_layout = QHBoxLayout(role_box)
        role_layout.setContentsMargins(3, 3, 3, 3)
        role_layout.setSpacing(2)

        self.employee_radio = QRadioButton("Employee")
        self.admin_radio = QRadioButton("Admin")
        self.employee_radio.setChecked(True)
        for rb in (self.employee_radio, self.admin_radio):
            rb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            rb.setCursor(Qt.PointingHandCursor)
            role_layout.addWidget(rb)

        self.role_group = QButtonGroup(self)
        self.role_group.addButton(self.admin_radio)
        self.role_group.addButton(self.employee_radio)
        center_layout.addWidget(role_box)
        center_layout.addSpacing(18)

        center_layout.addWidget(make_label("Employee ID", role="muted", size=12, weight=500))
        center_layout.addSpacing(6)
        self.emp_id_input = QLineEdit()
        self.emp_id_input.setPlaceholderText("e.g. ADM001")
        self.emp_id_input.setMinimumHeight(42)
        self.emp_id_input.returnPressed.connect(self.handle_login)
        center_layout.addWidget(self.emp_id_input)
        center_layout.addSpacing(14)

        center_layout.addWidget(make_label("Password", role="muted", size=12, weight=500))
        center_layout.addSpacing(6)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(42)
        self.password_input.returnPressed.connect(self.handle_login)
        center_layout.addWidget(self.password_input)
        center_layout.addSpacing(24)

        self.login_btn = QPushButton("Sign in")
        self.login_btn.setProperty("variant", "primary")
        self.login_btn.setMinimumHeight(46)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("QPushButton { border-radius: 10px; font-size: 14px; }")
        self.login_btn.clicked.connect(self.handle_login)
        center_layout.addWidget(self.login_btn)
        center_layout.addSpacing(16)

        hint = make_label("Test: ADM001/admin123 or EMP001/emp123", role="faint", size=12, align=Qt.AlignCenter)
        center_layout.addWidget(hint)

        outer = QVBoxLayout()
        outer.addStretch()
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(center_widget)
        h_layout.addStretch()
        outer.addLayout(h_layout)
        outer.addStretch()

        footer = make_label(f"© 2026 {config.COMPANY_NAME}. All rights reserved.", role="faint", size=12,
                            align=Qt.AlignCenter)
        footer.setContentsMargins(0, 0, 0, 18)
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
