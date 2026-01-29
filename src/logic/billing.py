"""
Billing business logic.
Handles invoice generation, calculations, and bill management.
"""
from datetime import datetime
from typing import List, Optional, Tuple
import config
from src.database.connection import db
from src.models.bill import Bill, BillItem
from src.models.product import Product


class BillingService:
    """Service class for billing operations."""
    
    def __init__(self):
        self.db = db
    
    def generate_invoice_number(self, date: str = None) -> str:
        """
        Generate unique invoice number for the day.
        Format: INV-YYYYMMDD-0001
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to today
        
        Returns:
            str: Generated invoice number
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        date_key = date.replace("-", "")
        
        # Get or create sequence for this date
        with self.db.get_cursor() as cursor:
            # Check if sequence exists for this date
            cursor.execute(
                "SELECT last_sequence FROM invoice_sequence WHERE date = ?",
                (date,)
            )
            result = cursor.fetchone()
            
            if result:
                # Increment sequence
                new_sequence = result[0] + 1
                cursor.execute(
                    "UPDATE invoice_sequence SET last_sequence = ? WHERE date = ?",
                    (new_sequence, date)
                )
            else:
                # Create new sequence for this date
                new_sequence = 1
                cursor.execute(
                    "INSERT INTO invoice_sequence (date, last_sequence) VALUES (?, ?)",
                    (date, new_sequence)
                )
        
        invoice_number = config.INVOICE_NUMBER_FORMAT.format(
            prefix=config.INVOICE_PREFIX,
            date=date_key,
            sequence=new_sequence
        )
        
        return invoice_number
    
    def create_bill(self, customer_name: str, customer_no: str, items: List[BillItem],
                   discount: float = 0.0, tax_rate: float = None) -> Bill:
        """
        Create a new bill.
        
        Args:
            customer_name: Customer name
            customer_no: Customer phone number
            items: List of bill items
            discount: Discount amount (default 0.0)
            tax_rate: Tax rate (default from config)
        
        Returns:
            Bill: Created bill object
        """
        if tax_rate is None:
            tax_rate = config.DEFAULT_GST_RATE
        
        invoice_number = self.generate_invoice_number()
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        bill = Bill(
            bill_no=invoice_number,
            date=current_date,
            customer_name=customer_name,
            customer_no=customer_no,
            items=items,
            discount=discount,
            tax_rate=tax_rate
        )
        
        # Calculations are done automatically in Bill model
        bill._recalculate()
        
        return bill
    
    def save_bill(self, bill: Bill) -> bool:
        """
        Save bill to database and update inventory.
        
        Args:
            bill: Bill object to save
        
        Returns:
            bool: True if successful
        """
        try:
            # Generate bill details string
            bill_details = bill.generate_bill_details()
            
            # Insert bill into database
            insert_query = """
                INSERT INTO bill (
                    bill_no, date, customer_name, customer_no, 
                    bill_details, subtotal, discount, tax_rate, tax_amount, total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute_insert(
                insert_query,
                (
                    bill.bill_no, bill.date, bill.customer_name, bill.customer_no,
                    bill_details, bill.subtotal, bill.discount, bill.tax_rate,
                    bill.tax_amount, bill.total
                )
            )
            
            # Update inventory stock in simple_products
            for item in bill.items:
                update_query = """
                    UPDATE simple_products 
                    SET stock = stock - ? 
                    WHERE name = ?
                """
                self.db.execute_update(update_query, (item.quantity, item.product_name))
            
            return True
            
        except Exception as e:
            print(f"Error saving bill: {str(e)}")
            return False
    
    def get_bill_by_number(self, bill_no: str) -> Optional[Bill]:
        """
        Retrieve a bill by its number.
        
        Args:
            bill_no: Bill number
        
        Returns:
            Bill object or None if not found
        """
        query = "SELECT * FROM bill WHERE bill_no = ?"
        results = self.db.execute_query(query, (bill_no,))
        
        if results:
            row = results[0]
            bill = Bill.from_db_row(row)
            return bill
        return None
    
    def search_bills(self, search_term: str = None, start_date: str = None, 
                    end_date: str = None) -> List[Bill]:
        """
        Search bills by various criteria.
        
        Args:
            search_term: Search in bill number or customer name
            start_date: Start date filter
            end_date: End date filter
        
        Returns:
            List of Bill objects
        """
        query = "SELECT * FROM bill WHERE 1=1"
        params = []
        
        if search_term:
            query += " AND (bill_no LIKE ? OR customer_name LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date DESC, bill_no DESC"
        
        results = self.db.execute_query(query, tuple(params))
        return [Bill.from_db_row(row) for row in results]
    
    def get_bills_by_date(self, date: str) -> List[Bill]:
        """Get all bills for a specific date."""
        query = "SELECT * FROM bill WHERE date = ? ORDER BY bill_no"
        results = self.db.execute_query(query, (date,))
        return [Bill.from_db_row(row) for row in results]
    
    def get_todays_bills(self) -> List[Bill]:
        """Get all bills for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_bills_by_date(today)
    
    def calculate_daily_revenue(self, date: str) -> float:
        """Calculate total revenue for a specific date."""
        query = "SELECT SUM(total) as revenue FROM bill WHERE date = ?"
        results = self.db.execute_query(query, (date,))
        
        if results and results[0]['revenue']:
            return float(results[0]['revenue'])
        return 0.0
    
    def get_bill_count(self, start_date: str = None, end_date: str = None) -> int:
        """Get count of bills within date range."""
        query = "SELECT COUNT(*) as count FROM bill WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        results = self.db.execute_query(query, tuple(params))
        return results[0]['count'] if results else 0
