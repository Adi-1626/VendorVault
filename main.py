"""
Main application entry point.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from src.ui.login import LoginWindow
from src.ui.admin.dashboard import AdminDashboard
from src.ui.employee.billing import BillingWindow
from src.database.migrations import run_migrations
import config


def load_stylesheet(app: QApplication):
    """Load and apply the application stylesheet."""
    qss_file = project_root / "src" / "ui" / "styles" / "default.qss"
    
    if qss_file.exists():
        with open(qss_file, 'r') as f:
            app.setStyleSheet(f.read())


def main():
    """Main application entry point."""
    # Create application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName(config.COMPANY_NAME)
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Load stylesheet
    load_stylesheet(app)
    
    # Run database migrations
    try:
        run_migrations()
    except Exception as e:
        QMessageBox.critical(
            None,
            "Database Error",
            f"Failed to initialize database:\n{str(e)}\n\nPlease check database permissions."
        )
        return 1
    
    # Keep reference to main window
    main_window = None
    
    def on_login_successful(employee):
        """Handle successful login."""
        nonlocal main_window
        
        if employee.is_admin():
            # Show admin dashboard
            main_window = AdminDashboard(employee)
            main_window.show()
        else:
            # Show employee billing window
            main_window = BillingWindow(employee)
            main_window.show()
    
    # Create and show login window
    login_window = LoginWindow()
    login_window.login_successful.connect(on_login_successful)
    login_window.show()
    
    # Run application
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
