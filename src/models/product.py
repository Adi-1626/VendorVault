"""
Product/Inventory data model for Namkeen Business.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    """Product model for namkeen (snacks) inventory."""
    
    product_id: int
    product_name: str
    product_cat: str  # Category (e.g., "Namkeen", "Farsan", "Dry Fruits", "Sweets")
    stock: int  # Quantity in stock
    mrp: float  # Selling price per unit
    unit: str = "Kg"  # Unit of measurement (Kg, Gram, Piece, Packet)
    cost_price: Optional[float] = None  # Purchase/cost price
    supplier_name: Optional[str] = None  # Supplier/vendor name
    supplier_phone: Optional[str] = None  # Supplier contact
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def is_in_stock(self, quantity: int = 1) -> bool:
        """
        Check if product has sufficient stock.
        
        Args:
            quantity: Required quantity
        
        Returns:
            bool: True if sufficient stock available
        """
        return self.stock >= quantity
    
    def calculate_profit(self, quantity: int = 1) -> float:
        """
        Calculate profit for given quantity.
        
        Args:
            quantity: Quantity sold
        
        Returns:
            float: Profit amount
        """
        if self.cost_price is None:
            return 0.0
        return (self.mrp - self.cost_price) * quantity
    
    def update_stock(self, quantity_sold: int) -> int:
        """
        Update stock after sale.
        
        Args:
            quantity_sold: Quantity to subtract from stock
        
        Returns:
            int: New stock quantity
        """
        self.stock -= quantity_sold
        return self.stock
    
    def is_low_stock(self, threshold: int = 10) -> bool:
        """
        Check if product is low on stock.
        
        Args:
            threshold: Stock threshold for low stock warning
        
        Returns:
            bool: True if stock is below threshold
        """
        return self.stock < threshold
    
    @classmethod
    def from_db_row(cls, row) -> 'Product':
        """Create Product instance from database row."""
        # Handle product_subcat for backward compatibility - ignore it
        # Map vendor_phn to supplier fields
        
        supplier_phone = None
        if 'supplier_phone' in row.keys():
            supplier_phone = row['supplier_phone']
        elif 'vendor_phn' in row.keys():
            supplier_phone = row['vendor_phn']
        
        return cls(
            product_id=row['product_id'],
            product_name=row['product_name'],
            product_cat=row['product_cat'],
            stock=row['stock'],
            mrp=row['mrp'],
            unit=row['unit'] if 'unit' in row.keys() else "Kg",
            cost_price=row['cost_price'] if 'cost_price' in row.keys() else None,
            supplier_name=row['supplier_name'] if 'supplier_name' in row.keys() else None,
            supplier_phone=supplier_phone,
            created_at=row['created_at'] if 'created_at' in row.keys() else None,
            updated_at=row['updated_at'] if 'updated_at' in row.keys() else None
        )
    
    def to_dict(self) -> dict:
        """Convert product to dictionary."""
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_cat': self.product_cat,
            'product_subcat': self.product_subcat,
            'stock': self.stock,
            'mrp': self.mrp,
            'cost_price': self.cost_price,
            'vendor_phn': self.vendor_phn,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
