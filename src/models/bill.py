"""
Bill data model.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class BillItem:
    """Represents a single item in a bill."""
    
    product_name: str
    quantity: int
    unit_price: float
    
    def get_total(self) -> float:
        """Calculate total for this item."""
        return self.quantity * self.unit_price
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total': self.get_total()
        }


@dataclass
class Bill:
    """Bill model representing a customer invoice."""
    
    bill_no: str
    date: str
    customer_name: str
    customer_no: str
    items: List[BillItem] = field(default_factory=list)
    subtotal: float = 0.0
    discount: float = 0.0
    tax_rate: float = 18.0
    tax_amount: float = 0.0
    total: float = 0.0
    bill_details: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def add_item(self, item: BillItem):
        """Add an item to the bill."""
        self.items.append(item)
        self._recalculate()
    
    def remove_item(self, index: int):
        """Remove an item from the bill."""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self._recalculate()
    
    def calculate_subtotal(self) -> float:
        """Calculate subtotal from all items."""
        return sum(item.get_total() for item in self.items)
    
    def apply_discount(self, discount: float, is_percentage: bool = False):
        """
        Apply discount to the bill.
        
        Args:
            discount: Discount amount or percentage
            is_percentage: If True, discount is a percentage; otherwise, fixed amount
        """
        if is_percentage:
            self.discount = self.subtotal * (discount / 100)
        else:
            self.discount = discount
        self._recalculate()
    
    def calculate_tax(self) -> float:
        """Calculate tax amount based on tax rate."""
        taxable_amount = self.subtotal - self.discount
        return taxable_amount * (self.tax_rate / 100)
    
    def calculate_total(self) -> float:
        """Calculate final total amount."""
        return self.subtotal - self.discount + self.tax_amount
    
    def _recalculate(self):
        """Recalculate all amounts."""
        self.subtotal = self.calculate_subtotal()
        self.tax_amount = self.calculate_tax()
        self.total = self.calculate_total()
    
    def set_tax_rate(self, tax_rate: float):
        """Set tax rate and recalculate."""
        self.tax_rate = tax_rate
        self._recalculate()
    
    def get_item_count(self) -> int:
        """Get total number of items."""
        return len(self.items)
    
    def get_total_quantity(self) -> int:
        """Get total quantity of all items."""
        return sum(item.quantity for item in self.items)
    
    def generate_bill_details(self) -> str:
        """Generate formatted bill details string."""
        lines = []
        for item in self.items:
            lines.append(f"{item.product_name}\t\t{item.quantity}\t\t{item.get_total():.2f}")
        return "\n".join(lines)
    
    @classmethod
    def from_db_row(cls, row, items: List[BillItem] = None) -> 'Bill':
        """
        Create Bill instance from database row.
        
        Args:
            row: Database row (sqlite3.Row or dict)
            items: List of bill items (optional)
        
        Returns:
            Bill: Bill instance
        """
        return cls(
            bill_no=row['bill_no'],
            date=row['date'],
            customer_name=row['customer_name'],
            customer_no=row['customer_no'] if 'customer_no' in row.keys() else '',
            items=[],  # Items are stored as text, need to be parsed separately
            subtotal=row['subtotal'] if 'subtotal' in row.keys() else 0.0,
            discount=row['discount'] if 'discount' in row.keys() else 0.0,
            tax_rate=row['tax_rate'] if 'tax_rate' in row.keys() else 18.0,
            tax_amount=row['tax_amount'] if 'tax_amount' in row.keys() else 0.0,
            total=row['total'] if 'total' in row.keys() else 0.0,
            bill_details=row['bill_details'] if 'bill_details' in row.keys() else '',
            created_at=row['created_at'] if 'created_at' in row.keys() else None,
            updated_at=row['updated_at'] if 'updated_at' in row.keys() else None
        )
    
    def to_dict(self) -> dict:
        """Convert bill to dictionary."""
        return {
            'bill_no': self.bill_no,
            'date': self.date,
            'customer_name': self.customer_name,
            'customer_no': self.customer_no,
            'items': [item.to_dict() for item in self.items],
            'subtotal': self.subtotal,
            'discount': self.discount,
            'tax_rate': self.tax_rate,
            'tax_amount': self.tax_amount,
            'total': self.total,
            'item_count': self.get_item_count(),
            'total_quantity': self.get_total_quantity()
        }
