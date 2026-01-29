"""
Pending Bills Management Module.
Allows saving/recalling cart states for multi-customer handling.
"""
from typing import List, Optional, Dict
from src.database.connection import DatabaseConnection
from datetime import datetime, timedelta
import json


class PendingBill:
    """Represents a pending/held transaction."""
    
    def __init__(self,
                 pending_id: int = None,
                 employee_id: int = None,
                 customer_name: str = None,
                 customer_phone: str = None,
                 cart_items: List[Dict] = None,
                 subtotal: float = 0,
                 discount: float = 0,
                 tax_rate: float = 18,
                 created_at: datetime = None):
        self.pending_id = pending_id
        self.employee_id = employee_id
        self.customer_name = customer_name
        self.customer_phone = customer_phone
        self.cart_items = cart_items or []
        self.subtotal = subtotal
        self.discount = discount
        self.tax_rate = tax_rate
        self.created_at = created_at or datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'pending_id': self.pending_id,
            'employee_id': self.employee_id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'cart_items': self.cart_items,
            'subtotal': self.subtotal,
            'discount': self.discount,
            'tax_rate': self.tax_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PendingBill':
        created_at = None
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except:
                created_at = datetime.now()
        
        return cls(
            pending_id=data.get('pending_id'),
            employee_id=data.get('employee_id'),
            customer_name=data.get('customer_name'),
            customer_phone=data.get('customer_phone'),
            cart_items=data.get('cart_items', []),
            subtotal=data.get('subtotal', 0),
            discount=data.get('discount', 0),
            tax_rate=data.get('tax_rate', 18),
            created_at=created_at
        )
    
    def get_age_minutes(self) -> int:
        """Get how many minutes this bill has been pending."""
        if self.created_at:
            delta = datetime.now() - self.created_at
            return int(delta.total_seconds() / 60)
        return 0
    
    def get_display_text(self) -> str:
        """Get display text for the pending bill."""
        items_count = len(self.cart_items)
        name = self.customer_name or self.customer_phone or f"Bill #{self.pending_id}"
        age = self.get_age_minutes()
        return f"{name} - {items_count} items (₹{self.subtotal:.2f}) - {age}m ago"


class PendingBillsManager:
    """
    Manages pending/held transactions.
    Allows employees to hold a transaction and serve another customer.
    """
    
    MAX_PENDING_BILLS = 10
    EXPIRY_HOURS = 4  # Auto-expire after 4 hours
    
    def __init__(self):
        self.db = DatabaseConnection()
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create pending_bills table if it doesn't exist."""
        create_sql = """
            CREATE TABLE IF NOT EXISTS pending_bills (
                pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                cart_items TEXT NOT NULL,
                subtotal REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                tax_rate REAL DEFAULT 18,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
            )
        """
        try:
            self.db.execute_update(create_sql)
        except Exception as e:
            print(f"Note: Could not create pending_bills table: {e}")
    
    def save_pending_bill(self, 
                         employee_id: int,
                         cart_items: List[Dict],
                         customer_name: str = None,
                         customer_phone: str = None,
                         subtotal: float = 0,
                         discount: float = 0,
                         tax_rate: float = 18) -> Optional[int]:
        """
        Save current cart as a pending bill.
        Returns pending_id on success, None on failure.
        """
        if not cart_items:
            return None
        
        # Check limit
        count = self.get_pending_count(employee_id)
        if count >= self.MAX_PENDING_BILLS:
            return None
        
        expires_at = datetime.now() + timedelta(hours=self.EXPIRY_HOURS)
        cart_json = json.dumps(cart_items)
        
        query = """
            INSERT INTO pending_bills 
            (employee_id, customer_name, customer_phone, cart_items, subtotal, discount, tax_rate, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            self.db.execute_update(query, (
                employee_id,
                customer_name,
                customer_phone,
                cart_json,
                subtotal,
                discount,
                tax_rate,
                expires_at.isoformat()
            ))
            
            # Get the inserted ID
            result = self.db.execute_query("SELECT last_insert_rowid() as id")
            if result:
                return result[0]['id']
            return None
        except Exception as e:
            print(f"Error saving pending bill: {e}")
            return None
    
    def get_pending_bills(self, employee_id: int) -> List[PendingBill]:
        """Get all pending bills for an employee."""
        # Clean up expired bills first
        self._cleanup_expired()
        
        query = """
            SELECT * FROM pending_bills 
            WHERE employee_id = ?
            ORDER BY created_at DESC
        """
        
        try:
            results = self.db.execute_query(query, (employee_id,))
            
            pending_bills = []
            for row in results:
                cart_items = json.loads(row['cart_items']) if row['cart_items'] else []
                
                created_at = None
                if row['created_at']:
                    try:
                        created_at = datetime.fromisoformat(row['created_at'])
                    except:
                        created_at = datetime.now()
                
                bill = PendingBill(
                    pending_id=row['pending_id'],
                    employee_id=row['employee_id'],
                    customer_name=row['customer_name'],
                    customer_phone=row['customer_phone'],
                    cart_items=cart_items,
                    subtotal=row['subtotal'] or 0,
                    discount=row['discount'] or 0,
                    tax_rate=row['tax_rate'] or 18,
                    created_at=created_at
                )
                pending_bills.append(bill)
            
            return pending_bills
        except Exception as e:
            print(f"Error getting pending bills: {e}")
            return []
    
    def get_pending_bill(self, pending_id: int) -> Optional[PendingBill]:
        """Get a specific pending bill by ID."""
        query = "SELECT * FROM pending_bills WHERE pending_id = ?"
        
        try:
            results = self.db.execute_query(query, (pending_id,))
            
            if results:
                row = results[0]
                cart_items = json.loads(row['cart_items']) if row['cart_items'] else []
                
                created_at = None
                if row['created_at']:
                    try:
                        created_at = datetime.fromisoformat(row['created_at'])
                    except:
                        created_at = datetime.now()
                
                return PendingBill(
                    pending_id=row['pending_id'],
                    employee_id=row['employee_id'],
                    customer_name=row['customer_name'],
                    customer_phone=row['customer_phone'],
                    cart_items=cart_items,
                    subtotal=row['subtotal'] or 0,
                    discount=row['discount'] or 0,
                    tax_rate=row['tax_rate'] or 18,
                    created_at=created_at
                )
            return None
        except Exception as e:
            print(f"Error getting pending bill: {e}")
            return None
    
    def recall_pending_bill(self, pending_id: int) -> Optional[PendingBill]:
        """
        Recall a pending bill (get and delete).
        Returns the bill data for loading into cart.
        """
        bill = self.get_pending_bill(pending_id)
        
        if bill:
            self.delete_pending_bill(pending_id)
        
        return bill
    
    def delete_pending_bill(self, pending_id: int) -> bool:
        """Delete a pending bill."""
        query = "DELETE FROM pending_bills WHERE pending_id = ?"
        
        try:
            self.db.execute_update(query, (pending_id,))
            return True
        except Exception as e:
            print(f"Error deleting pending bill: {e}")
            return False
    
    def get_pending_count(self, employee_id: int) -> int:
        """Get count of pending bills for an employee."""
        query = "SELECT COUNT(*) as count FROM pending_bills WHERE employee_id = ?"
        
        try:
            results = self.db.execute_query(query, (employee_id,))
            return results[0]['count'] if results else 0
        except:
            return 0
    
    def _cleanup_expired(self):
        """Remove expired pending bills."""
        query = "DELETE FROM pending_bills WHERE expires_at < datetime('now')"
        
        try:
            self.db.execute_update(query)
        except:
            pass
    
    def search_by_phone(self, employee_id: int, phone_digits: str) -> List[PendingBill]:
        """Search pending bills by last digits of phone number."""
        if not phone_digits:
            return []
        
        query = """
            SELECT * FROM pending_bills 
            WHERE employee_id = ? AND customer_phone LIKE ?
            ORDER BY created_at DESC
        """
        
        try:
            results = self.db.execute_query(query, (employee_id, f'%{phone_digits}'))
            
            pending_bills = []
            for row in results:
                cart_items = json.loads(row['cart_items']) if row['cart_items'] else []
                
                bill = PendingBill(
                    pending_id=row['pending_id'],
                    employee_id=row['employee_id'],
                    customer_name=row['customer_name'],
                    customer_phone=row['customer_phone'],
                    cart_items=cart_items,
                    subtotal=row['subtotal'] or 0,
                    discount=row['discount'] or 0,
                    tax_rate=row['tax_rate'] or 18
                )
                pending_bills.append(bill)
            
            return pending_bills
        except Exception as e:
            print(f"Error searching pending bills: {e}")
            return []
