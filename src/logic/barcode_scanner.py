"""
Barcode Scanner Module for simple barcode-based products.
"""
from typing import Dict, Optional
from src.database.connection import DatabaseConnection


class BarcodeScanner:
    """Handle barcode scanning and lookup."""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def process_scan(self, barcode: str) -> Dict:
        """
        Process scanned barcode and return product info.
        Checks both simple_products and products/product_variants tables.
        
        Returns:
            Dict with 'success' and 'product' keys
        """
        barcode = barcode.strip()
        
        if not barcode:
            return {'success': False, 'error': 'Empty barcode'}
        
        # First, try simple_products table
        query1 = """
            SELECT id, barcode, name as product_name, mrp, cost_price, stock, category
            FROM simple_products
            WHERE barcode = ? AND is_active = 1
        """
        results = self.db.execute_query(query1, (barcode,))
        
        if results:
            row = results[0]
            return {
                'success': True,
                'product': {
                    'product_id': row['id'],
                    'barcode': row['barcode'],
                    'product_name': row['product_name'],
                    'mrp': row['mrp'] or 0.0,
                    'cost_price': row.get('cost_price', 0.0) or 0.0,
                    'stock': row['stock'] or 0,
                    'category': row.get('category', '')
                }
            }
        
        # Second, try products + product_variants tables (Admin-added products)
        query2 = """
            SELECT 
                p.product_id,
                pv.sku as barcode,
                p.product_name,
                pv.mrp,
                pv.cost_price
            FROM products p
            JOIN product_variants pv ON pv.product_id = p.product_id
            WHERE pv.sku = ? AND p.is_active = 1
        """
        results = self.db.execute_query(query2, (barcode,))
        
        if results:
            row = results[0]
            return {
                'success': True,
                'product': {
                    'product_id': row['product_id'],
                    'barcode': row['barcode'],
                    'product_name': row['product_name'],
                    'mrp': row['mrp'] or 0.0,
                    'cost_price': row.get('cost_price', 0.0) or 0.0,
                    'stock': row.get('stock', 100),  # Default stock
                    'category': row.get('category', '')
                }
            }
        
        return {'success': False, 'error': f'Product not found: {barcode}'}
    
    def lookup_barcode(self, barcode: str) -> Optional[Dict]:
        """Look up barcode and return product or None."""
        result = self.process_scan(barcode)
        return result.get('product') if result['success'] else None
    
    def is_valid_barcode(self, barcode: str) -> bool:
        """Check if barcode format is valid."""
        barcode = barcode.strip()
        # Most retail barcodes are 8-13 digits
        return barcode.isdigit() and 8 <= len(barcode) <= 13
