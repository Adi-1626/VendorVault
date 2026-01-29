"""
Admin dashboard window - Dark Mode with proper alignment.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from datetime import datetime
from src.models.employee import Employee
from src.logic.inventory import InventoryService
from src.logic.employee_mgmt import EmployeeService
from src.logic.billing import BillingService

from src.ui.colors import *

# Map dashboard specific colors
BG = DARK_BG
CARD = CARD_BG
WHITE = TEXT_PRIMARY
GRAY = TEXT_SECONDARY
BLUE = PRIMARY
GREEN = SUCCESS
ORANGE = WARNING
RED = DANGER
PURPLE = "#8B5CF6" # Keep purple for stats if needed



class AdminDashboard(QMainWindow):
    """Admin dashboard with full dark mode."""
    
    def __init__(self, admin: Employee):
        super().__init__()
        self.admin = admin
        self.inventory_service = InventoryService()
        self.employee_service = EmployeeService()
        self.billing_service = BillingService()
        
        self.setup_ui()
        self.load_statistics()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def setup_ui(self):
        """Set up dark mode UI."""
        self.setWindowTitle("Admin Dashboard - Bill Generation System")
        self.showMaximized()
        
        # Dark stylesheet
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {BG};
                color: {WHITE};
            }}
            QLabel {{
                color: {WHITE};
                font-size: 15px;
            }}
            QPushButton {{
                background-color: {CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {BORDER};
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
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(25)
        
        # === HEADER ===
        header = QHBoxLayout()
        header.setSpacing(15)
        
        title = QLabel("Admin Dashboard")
        title.setStyleSheet(f"color: {WHITE}; font-size: 28px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Switch to POS
        switch_btn = QPushButton("👤 Switch to POS Mode")
        switch_btn.setStyleSheet(f"background: {PURPLE}; color: white; border: none; padding: 10px 16px;")
        switch_btn.clicked.connect(self.switch_to_employee_mode)
        header.addWidget(switch_btn)
        
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {GRAY}; font-size: 14px;")
        header.addWidget(self.time_label)
        
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet(f"background: {CARD}; color: {WHITE}; padding: 10px 16px;")
        logout_btn.clicked.connect(self.handle_logout)
        header.addWidget(logout_btn)
        
        layout.addLayout(header)
        
        # Welcome
        welcome = QLabel(f"Welcome back, {self.admin.get_full_name()}")
        welcome.setStyleSheet(f"color: {GRAY}; font-size: 16px;")
        layout.addWidget(welcome)
        
        # === STATS CARDS ===
        stats = QHBoxLayout()
        stats.setSpacing(20)
        
        self.products_card = self._stat_card("Total Products", "0", BLUE)
        self.employees_card = self._stat_card("Total Employees", "0", GREEN)
        self.bills_card = self._stat_card("Bills Today", "0", ORANGE)
        self.revenue_card = self._stat_card("Today's Revenue", "₹0.00", PURPLE)
        
        stats.addWidget(self.products_card)
        stats.addWidget(self.employees_card)
        stats.addWidget(self.bills_card)
        stats.addWidget(self.revenue_card)
        
        layout.addLayout(stats)
        
        # === MANAGEMENT SECTION ===
        mgmt_label = QLabel("Management")
        mgmt_label.setStyleSheet(f"color: {WHITE}; font-size: 20px; font-weight: bold;")
        layout.addWidget(mgmt_label)
        
        nav = QGridLayout()
        nav.setSpacing(20)
        
        inv_btn = self._nav_btn("📦 Inventory Management", "Manage products, stock, and categories", BLUE)
        inv_btn.clicked.connect(self.open_inventory)
        
        brand_btn = self._nav_btn("🏷️ Brand Management", "Manage product brands and suppliers", "#EC4899")
        brand_btn.clicked.connect(self.open_brands)
        
        type_btn = self._nav_btn("📂 Product Types", "Manage categories & HSN codes", ORANGE)
        type_btn.clicked.connect(self.open_product_types)
        
        emp_btn = self._nav_btn("👥 Employee Management", "Add, edit, and manage employees", GREEN)
        emp_btn.clicked.connect(self.open_employees)
        
        inv_bill_btn = self._nav_btn("📄 Invoices & Bills", "Search and view all invoices", ORANGE)
        inv_bill_btn.clicked.connect(self.open_invoices)
        
        analytics_btn = self._nav_btn("📊 Analytics & Reports", "View sales analytics and reports", PURPLE)
        analytics_btn.clicked.connect(self.open_analytics)
        
        nav.addWidget(inv_btn, 0, 0)
        nav.addWidget(brand_btn, 0, 1)
        nav.addWidget(type_btn, 0, 2)
        nav.addWidget(emp_btn, 1, 0)
        nav.addWidget(inv_bill_btn, 1, 1)
        nav.addWidget(analytics_btn, 1, 2)
        
        layout.addLayout(nav)
        layout.addStretch()
        
        self.statusBar().showMessage("Ready")
    
    def _stat_card(self, title: str, value: str, color: str) -> QFrame:
        """Create stat card with dark background."""
        card = QFrame()
        card.setMinimumHeight(120)
        card.setMaximumHeight(140)
        
        lyt = QVBoxLayout(card)
        lyt.setContentsMargins(20, 15, 20, 15)
        lyt.setSpacing(8)
        
        t = QLabel(title)
        t.setStyleSheet(f"color: {GRAY}; font-size: 14px; border: none;")
        lyt.addWidget(t)
        
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold; border: none;")
        v.setObjectName("value")
        lyt.addWidget(v)
        
        lyt.addStretch()
        return card
    
    def _nav_btn(self, title: str, desc: str, color: str) -> QPushButton:
        """Create nav button with dark theme."""
        btn = QPushButton(f"{title}\n{desc}")
        btn.setMinimumHeight(100)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CARD};
                color: {WHITE};
                border: 2px solid {BORDER};
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 16px;
                text-align: left;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {BORDER};
            }}
        """)
        return btn
    
    def update_time(self):
        t = datetime.now().strftime("%B %d, %Y | %I:%M:%S %p")
        self.time_label.setText(t)
    
    def load_statistics(self):
        try:
            products = self.inventory_service.get_total_product_count()
            self.products_card.findChild(QLabel, "value").setText(str(products))
        except:
            pass
        
        try:
            employees = len(self.employee_service.get_all_employees())
            self.employees_card.findChild(QLabel, "value").setText(str(employees))
        except:
            pass
        
        try:
            bills = len(self.billing_service.get_todays_bills())
            self.bills_card.findChild(QLabel, "value").setText(str(bills))
        except:
            pass
        
        try:
            revenue = self.billing_service.calculate_daily_revenue(datetime.now().strftime("%Y-%m-%d"))
            self.revenue_card.findChild(QLabel, "value").setText(f"₹{revenue:,.2f}")
        except:
            pass
    
    def open_inventory(self):
        from src.ui.admin.simple_inventory import SimpleInventoryWindow
        self.inv_window = SimpleInventoryWindow(self)
        self.inv_window.show()
    
    def open_brands(self):
        from src.ui.admin.brands import BrandManagementWindow
        self.brands_window = BrandManagementWindow(self)
        self.brands_window.show()
    
    def open_product_types(self):
        from src.ui.admin.product_types import ProductTypeManagementWindow
        self.types_window = ProductTypeManagementWindow(self)
        self.types_window.show()
    
    def open_employees(self):
        from src.ui.admin.employees import EmployeeWindow
        self.emp_window = EmployeeWindow(self)
        self.emp_window.show()
    
    def open_invoices(self):
        from src.ui.admin.invoices import InvoicesWindow
        self.invoices_window = InvoicesWindow(self)
        self.invoices_window.show()
    
    def open_analytics(self):
        from src.ui.admin.analytics_dashboard import EnterpriseDashboard
        self.analytics_window = EnterpriseDashboard(self)
        self.analytics_window.show()
    
    def switch_to_employee_mode(self):
        self.close()
        from src.ui.employee.billing import BillingWindow
        self.billing_window = BillingWindow(self.admin)
        self.billing_window.show()
    
    def handle_logout(self):
        self.close()
        from src.ui.login import LoginWindow
        self.login_window = LoginWindow()
        
        # Connect login signal
        def on_login(employee):
            if employee.is_admin():
                from src.ui.admin.dashboard import AdminDashboard
                self.next_window = AdminDashboard(employee)
            else:
                from src.ui.employee.billing import BillingWindow
                self.next_window = BillingWindow(employee)
            self.next_window.show()
            
        self.login_window.login_successful.connect(on_login)
        self.login_window.show()
    
    def closeEvent(self, event):
        self.timer.stop()
        event.accept()
