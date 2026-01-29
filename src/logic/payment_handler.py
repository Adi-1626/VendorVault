"""
Payment Integration Module for 2026 Indian Standards.
Supports UPI, Cash, Card, Digital Wallets, and Split Payments.
NPCI compliant with GST invoice support.
"""
from typing import List, Optional, Dict
from src.database.connection import DatabaseConnection
from datetime import datetime
import json
import config


class PaymentMethod:
    """Enum-like class for payment methods."""
    CASH = 'CASH'
    UPI = 'UPI'
    CARD = 'CARD'
    WALLET = 'WALLET'
    CREDIT = 'CREDIT'
    
    @classmethod
    def all_methods(cls) -> List[str]:
        return [cls.CASH, cls.UPI, cls.CARD, cls.WALLET, cls.CREDIT]
    
    @classmethod
    def get_display_name(cls, method: str) -> str:
        names = {
            cls.CASH: 'Cash',
            cls.UPI: 'UPI / QR Code',
            cls.CARD: 'Credit/Debit Card',
            cls.WALLET: 'Digital Wallet',
            cls.CREDIT: 'Credit / Pay Later'
        }
        return names.get(method, method)


class PaymentStatus:
    """Payment status constants."""
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    REFUNDED = 'REFUNDED'


class PaymentTransaction:
    """Represents a single payment transaction."""
    
    def __init__(self, 
                 payment_method: str,
                 amount: float,
                 reference: str = None,
                 status: str = PaymentStatus.COMPLETED,
                 metadata: dict = None):
        self.payment_method = payment_method
        self.amount = amount
        self.reference = reference
        self.status = status
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            'payment_method': self.payment_method,
            'amount': self.amount,
            'reference': self.reference,
            'status': self.status,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class PaymentHandler:
    """
    Handles all payment operations for 2026 Indian retail.
    Supports multiple payment methods and split payments.
    """
    
    # Common cash denominations in India
    CASH_DENOMINATIONS = [10, 20, 50, 100, 200, 500, 2000]
    
    # UPI daily limit (NPCI 2026)
    UPI_DAILY_LIMIT = 100000  # ₹1,00,000
    UPI_MEDICAL_LIMIT = 500000  # ₹5,00,000 for medical/education
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def calculate_change(self, bill_total: float, amount_received: float) -> float:
        """Calculate change to return to customer."""
        change = amount_received - bill_total
        return max(0, round(change, 2))
    
    def get_suggested_amounts(self, bill_total: float) -> List[int]:
        """
        Get suggested cash amounts based on bill total.
        Returns common denominations that are >= bill total.
        """
        suggestions = []
        
        # Add rounded amounts
        rounded_up = int((bill_total // 10 + 1) * 10)
        rounded_100 = int((bill_total // 100 + 1) * 100)
        
        for denom in self.CASH_DENOMINATIONS:
            if denom >= bill_total:
                suggestions.append(denom)
        
        # Add combinations for common scenarios
        if bill_total < 500:
            if rounded_100 not in suggestions:
                suggestions.append(rounded_100)
        
        # Add exact amount option
        if bill_total not in suggestions:
            suggestions.insert(0, int(bill_total))
        
        # Sort and limit
        suggestions = sorted(set(suggestions))[:6]
        
        return suggestions
    
    def generate_upi_payment_string(self, 
                                    amount: float, 
                                    bill_no: str,
                                    merchant_upi: str = None) -> str:
        """
        Generate UPI payment string for QR code.
        Format: upi://pay?pa=<VPA>&pn=<Name>&am=<Amount>&tn=<Note>&cu=INR
        """
        # Use configured UPI or default
        upi_id = merchant_upi or getattr(config, 'MERCHANT_UPI_ID', 'merchant@upi')
        merchant_name = getattr(config, 'COMPANY_NAME', 'Store').replace(' ', '%20')
        
        payment_string = (
            f"upi://pay?"
            f"pa={upi_id}&"
            f"pn={merchant_name}&"
            f"am={amount:.2f}&"
            f"tn=Bill%20{bill_no}&"
            f"cu=INR"
        )
        
        return payment_string
    
    def validate_upi_amount(self, amount: float, is_special_category: bool = False) -> tuple[bool, str]:
        """
        Validate UPI payment amount against NPCI 2026 limits.
        """
        limit = self.UPI_MEDICAL_LIMIT if is_special_category else self.UPI_DAILY_LIMIT
        
        if amount <= 0:
            return False, "Amount must be greater than zero"
        
        if amount > limit:
            return False, f"Amount exceeds UPI limit of ₹{limit:,.2f}"
        
        return True, "Valid"
    
    def process_cash_payment(self, 
                            bill_id: int, 
                            bill_total: float, 
                            amount_received: float) -> Dict:
        """
        Process cash payment.
        Returns payment result with change calculation.
        """
        if amount_received < bill_total:
            return {
                'success': False,
                'error': f'Insufficient amount. Need ₹{bill_total - amount_received:.2f} more.'
            }
        
        change = self.calculate_change(bill_total, amount_received)
        
        transaction = PaymentTransaction(
            payment_method=PaymentMethod.CASH,
            amount=bill_total,
            metadata={
                'received': amount_received,
                'change': change
            }
        )
        
        # Save to database
        self._save_payment_transaction(bill_id, transaction)
        
        return {
            'success': True,
            'method': PaymentMethod.CASH,
            'amount_paid': bill_total,
            'amount_received': amount_received,
            'change': change,
            'transaction': transaction.to_dict()
        }
    
    def process_upi_payment(self,
                           bill_id: int,
                           amount: float,
                           reference: str = None) -> Dict:
        """
        Process UPI payment.
        """
        is_valid, message = self.validate_upi_amount(amount)
        
        if not is_valid:
            return {
                'success': False,
                'error': message
            }
        
        transaction = PaymentTransaction(
            payment_method=PaymentMethod.UPI,
            amount=amount,
            reference=reference,
            metadata={
                'upi_ref': reference
            }
        )
        
        # Save to database
        self._save_payment_transaction(bill_id, transaction)
        
        return {
            'success': True,
            'method': PaymentMethod.UPI,
            'amount_paid': amount,
            'reference': reference,
            'transaction': transaction.to_dict()
        }
    
    def process_card_payment(self,
                            bill_id: int,
                            amount: float,
                            reference: str = None,
                            card_type: str = None) -> Dict:
        """
        Process card (credit/debit) payment.
        """
        transaction = PaymentTransaction(
            payment_method=PaymentMethod.CARD,
            amount=amount,
            reference=reference,
            metadata={
                'card_type': card_type,
                'approval_code': reference
            }
        )
        
        # Save to database
        self._save_payment_transaction(bill_id, transaction)
        
        return {
            'success': True,
            'method': PaymentMethod.CARD,
            'amount_paid': amount,
            'reference': reference,
            'transaction': transaction.to_dict()
        }
    
    def process_split_payment(self,
                             bill_id: int,
                             bill_total: float,
                             payments: List[Dict]) -> Dict:
        """
        Process split payment with multiple methods.
        payments: List of {'method': str, 'amount': float, 'reference': str}
        """
        total_paid = sum(p['amount'] for p in payments)
        
        if total_paid < bill_total:
            return {
                'success': False,
                'error': f'Total payments (₹{total_paid:.2f}) less than bill (₹{bill_total:.2f})'
            }
        
        transactions = []
        
        for payment in payments:
            transaction = PaymentTransaction(
                payment_method=payment['method'],
                amount=payment['amount'],
                reference=payment.get('reference'),
                metadata=payment.get('metadata', {})
            )
            
            self._save_payment_transaction(bill_id, transaction)
            transactions.append(transaction.to_dict())
        
        change = total_paid - bill_total if total_paid > bill_total else 0
        
        return {
            'success': True,
            'method': 'SPLIT',
            'total_paid': total_paid,
            'bill_total': bill_total,
            'change': change,
            'transactions': transactions
        }
    
    def _save_payment_transaction(self, bill_id: int, transaction: PaymentTransaction):
        """Save payment transaction to database."""
        try:
            query = """
                INSERT INTO payment_transactions 
                (bill_id, payment_method, amount, payment_reference, payment_status, metadata, payment_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute_update(query, (
                bill_id,
                transaction.payment_method,
                transaction.amount,
                transaction.reference,
                transaction.status,
                json.dumps(transaction.metadata),
                transaction.timestamp.isoformat()
            ))
        except Exception as e:
            print(f"Error saving payment transaction: {e}")
            # Continue even if save fails - payment was successful
    
    def get_bill_payments(self, bill_id: int) -> List[Dict]:
        """Get all payments for a bill."""
        query = """
            SELECT * FROM payment_transactions 
            WHERE bill_id = ? 
            ORDER BY payment_timestamp
        """
        
        try:
            results = self.db.execute_query(query, (bill_id,))
            return [dict(row) for row in results]
        except Exception as e:
            print(f"Error getting bill payments: {e}")
            return []


def create_payment_tables():
    """Create payment-related database tables if they don't exist."""
    db = DatabaseConnection()
    
    create_sql = """
        CREATE TABLE IF NOT EXISTS payment_transactions (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_reference TEXT,
            payment_status TEXT DEFAULT 'COMPLETED',
            metadata TEXT,
            payment_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bill_id) REFERENCES bill(bill_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_payment_bill ON payment_transactions(bill_id);
        CREATE INDEX IF NOT EXISTS idx_payment_method ON payment_transactions(payment_method);
    """
    
    try:
        db.execute_update(create_sql)
        return True
    except Exception as e:
        print(f"Error creating payment tables: {e}")
        return False
