"""
Invoices viewing window - Dark Mode.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QMessageBox, QHeaderView, QTextEdit, QDialog
)
from PySide6.QtCore import Qt
from src.logic.billing import BillingService
from src.utils.pdf_generator import PDFGenerator
from src.ui.dark_theme import PRIMARY, SUCCESS, TEXT_WHITE, TEXT_GRAY, CARD_BG, BORDER


class InvoicesWindow(QMainWindow):
    """Invoices window with dark theme."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.billing_service = BillingService()
        self.pdf_generator = PDFGenerator()
        self.setup_ui()
        self.load_bills()
    
    def setup_ui(self):
        """Set up dark mode UI."""
        self.setWindowTitle("Invoices & Bills")
        self.setGeometry(150, 150, 1000, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Invoices & Bills")
        header.setProperty("role", "h1")
        layout.addWidget(header)
        
        # Search filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(15)
        
        search_label = QLabel("Search:")
        search_label.setProperty("role", "muted")
        filter_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Bill number or customer name...")
        self.search_input.setMinimumWidth(400)
        filter_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.setProperty("variant", "secondary")
        search_btn.clicked.connect(self.search_bills)
        filter_layout.addWidget(search_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_search)
        filter_layout.addWidget(clear_btn)
        
        filter_layout.addStretch()

        # Bill-level CSV export (moved here from the Overview page)
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setToolTip("Export the bills listed below to CSV")
        self.export_btn.clicked.connect(self.export_csv)
        filter_layout.addWidget(self.export_btn)
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Bill No", "Date", "Customer", "Phone", "Total", "Actions"])
        self.table.setColumnWidth(5, 180)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(60)
        layout.addWidget(self.table)
        
        central.setLayout(layout)
    
    def load_bills(self, bills=None):
        """Load bills into table."""
        if bills is None:
            bills = self.billing_service.search_bills()
        self._shown_bills = list(bills)
        
        self.table.setRowCount(len(bills))
        for idx, bill in enumerate(bills):
            self.table.setItem(idx, 0, QTableWidgetItem(bill.bill_no))
            self.table.setItem(idx, 1, QTableWidgetItem(bill.date))
            self.table.setItem(idx, 2, QTableWidgetItem(bill.customer_name))
            self.table.setItem(idx, 3, QTableWidgetItem(bill.customer_no))
            self.table.setItem(idx, 4, QTableWidgetItem(f"₹{bill.total:.2f}"))
            
            # Actions
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(8)
            
            view_btn = QPushButton("View")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setProperty("size", "sm")
            view_btn.clicked.connect(lambda checked, b=bill: self.view_bill(b))
            action_layout.addWidget(view_btn)
            
            pdf_btn = QPushButton("PDF")
            pdf_btn.setCursor(Qt.PointingHandCursor)
            pdf_btn.setProperty("size", "sm")
            pdf_btn.clicked.connect(lambda checked, b=bill: self.generate_pdf(b))
            action_layout.addWidget(pdf_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(idx, 5, action_widget)
    
    def export_csv(self, path=None):
        """Export the bills currently listed to a CSV file."""
        import csv
        from PySide6.QtWidgets import QFileDialog
        bills = getattr(self, "_shown_bills", [])
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export bills", "vendorvault-bills.csv", "CSV files (*.csv)")
            if not path:
                return None
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["Bill No", "Date", "Customer", "Phone", "Subtotal", "Discount", "Tax rate", "Tax", "Total"])
                for b in bills:
                    w.writerow([b.bill_no, b.date, b.customer_name, b.customer_no, f"{b.subtotal:.2f}",
                                f"{b.discount:.2f}", b.tax_rate, f"{b.tax_amount:.2f}", f"{b.total:.2f}"])
        except OSError as e:
            QMessageBox.critical(self, "Export failed", str(e))
            return None
        QMessageBox.information(self, "Export", f"Exported {len(bills)} bills to\n{path}")
        return path

    def search_bills(self):
        """Search bills."""
        search_term = self.search_input.text().strip()
        bills = self.billing_service.search_bills(search_term)
        self.load_bills(bills)
    
    def clear_search(self):
        """Clear search."""
        self.search_input.clear()
        self.load_bills()
    
    def view_bill(self, bill):
        """View bill details."""
        dialog = BillViewDialog(self, bill)
        dialog.exec()
    
    def generate_pdf(self, bill):
        """Generate PDF for bill and open it."""
        import os
        import subprocess
        import sys
        
        try:
            # Generate PDF using PDFGenerator
            pdf_path = self.pdf_generator.generate_invoice(bill)
            
            # Open PDF in default viewer
            if sys.platform == 'win32':
                os.startfile(pdf_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', pdf_path])
            else:  # Linux
                subprocess.run(['xdg-open', pdf_path])
                
            QMessageBox.information(self, "PDF Generated", f"PDF saved and opened:\n{pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {e}")


class BillViewDialog(QDialog):
    """Bill view dialog - dark mode."""
    
    def __init__(self, parent, bill):
        super().__init__(parent)
        self.bill = bill
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dark UI."""
        self.setWindowTitle(f"Bill Details - {self.bill.bill_no}")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Bill info
        info = [
            f"Bill No: {self.bill.bill_no}",
            f"Date: {self.bill.date}",
            f"Customer: {self.bill.customer_name}",
            f"Phone: {self.bill.customer_no}"
        ]
        for text in info:
            label = QLabel(text)
            label.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 14px;")
            layout.addWidget(label)
        
        # Details
        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(self.bill.bill_details or "No details")
        layout.addWidget(details)
        
        # Totals
        total_label = QLabel(f"TOTAL: ₹{self.bill.total:.2f}")
        total_label.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 22px; font-weight: 700;")
        layout.addWidget(total_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        open_pdf_btn = QPushButton("Open PDF")
        open_pdf_btn.setProperty("variant", "primary")
        open_pdf_btn.clicked.connect(self.open_pdf)
        btn_layout.addWidget(open_pdf_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setProperty("variant", "secondary")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def open_pdf(self):
        """Generate and open PDF for this bill."""
        import os
        import subprocess
        import sys
        
        try:
            pdf_generator = PDFGenerator()
            pdf_path = pdf_generator.generate_invoice(self.bill)
            
            # Open PDF in default viewer
            if sys.platform == 'win32':
                os.startfile(pdf_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', pdf_path])
            else:
                subprocess.run(['xdg-open', pdf_path])
                
            QMessageBox.information(self, "PDF Opened", f"PDF saved:\n{pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {e}")
