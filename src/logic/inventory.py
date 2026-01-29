"""
Inventory management business logic.
"""
from typing import List, Optional
import sqlite3
from src.database.connection import DatabaseConnection
from src.models.product import Product
import config


class InventoryService:
    """Service for managing inventory operations with professional schema."""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.db_path = config.DATABASE_PATH  # Fixed: was config.DB_PATH
    
    def get_all_products(self):
        """Get all products with their default variants."""
        query = """
            SELECT 
                p.product_id,
                p.product_code,
                p.product_name,
                p.description,
                p.base_unit,
                p.hsn_code,
                b.brand_name,
                pt.type_name as product_cat,
                pv.variant_id,
                pv.variant_name,
                pv.sku,
                pv.unit_size,
                pv.mrp,
                pv.cost_price,
                i.stock_quantity as stock
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_default = 1
            LEFT JOIN inventory i ON pv.variant_id = i.variant_id
            WHERE p.is_active = 1
            ORDER BY p.product_name
        """
        results = self.db.execute_query(query)
        
        products = []
        for row in results:
            product = Product(
                product_id=row['product_id'],
                product_name=row['product_name'],
                product_cat=row['product_cat'],
                stock=row['stock'] if row['stock'] is not None else 0,
                unit=row['base_unit'],
                mrp=row['mrp'] if row['mrp'] is not None else 0.0,
                supplier_name=row['brand_name']
            )
            products.append(product)
        
        return products
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.base_unit,
                b.brand_name,
                pt.type_name as product_cat,
                pv.mrp,
                i.stock_quantity as stock
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_default = 1
            LEFT JOIN inventory i ON pv.variant_id = i.variant_id
            WHERE p.product_id = ? AND p.is_active = 1
        """
        results = self.db.execute_query(query, (product_id,))
        
        if results:
            row = results[0]
            return Product(
                product_id=row['product_id'],
                product_name=row['product_name'],
                product_cat=row['product_cat'],
                stock=row['stock'] if row['stock'] is not None else 0,
                unit=row['base_unit'],
                mrp=row['mrp'] if row['mrp'] is not None else 0.0,
                supplier_name=row['brand_name']
            )
        return None
    
    def get_product_by_name(self, product_name: str) -> Optional[Product]:
        """Get product by name (for billing compatibility)."""
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.base_unit,
                b.brand_name,
                pt.type_name as product_cat,
                pv.mrp,
                i.stock_quantity as stock
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_default = 1
            LEFT JOIN inventory i ON pv.variant_id = i.variant_id
            WHERE p.product_name = ? AND p.is_active = 1
        """
        results = self.db.execute_query(query, (product_name,))
        
        if results:
            row = results[0]
            return Product(
                product_id=row['product_id'],
                product_name=row['product_name'],
                product_cat=row['product_cat'],
                stock=row['stock'] if row['stock'] is not None else 0,
                unit=row['base_unit'],
                mrp=row['mrp'] if row['mrp'] is not None else 0.0,
                supplier_name=row['brand_name']
            )
        return None
    
    def search_products(self, search_term: str) -> List[Product]:
        """Search products by name or code."""
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.base_unit,
                b.brand_name,
                pt.type_name as product_cat,
                pv.mrp,
                i.stock_quantity as stock
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_default = 1
            LEFT JOIN inventory i ON pv.variant_id = i.variant_id
            WHERE (p.product_name LIKE ? OR p.product_code LIKE ? OR pv.sku LIKE ?)
            AND p.is_active = 1
            ORDER BY p.product_name
        """
        search_pattern = f"%{search_term}%"
        results = self.db.execute_query(query, (search_pattern, search_pattern, search_pattern))
        
        products = []
        for row in results:
            product = Product(
                product_id=row['product_id'],
                product_name=row['product_name'],
                product_cat=row['product_cat'],
                stock=row['stock'] if row['stock'] is not None else 0,
                unit=row['base_unit'],
                mrp=row['mrp'] if row['mrp'] is not None else 0.0,
                supplier_name=row['brand_name']
            )
            products.append(product)
        
        return products
    
    def get_categories(self) -> List[str]:
        """Get unique product categories."""
        query = "SELECT DISTINCT type_name FROM product_types WHERE is_active = 1 ORDER BY display_order, type_name"
        results = self.db.execute_query(query)
        return [row['type_name'] for row in results]
    
    def get_products_by_category(self, category: str, subcategory: Optional[str] = None) -> List[Product]:
        """Get products by category."""
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.base_unit,
                b.brand_name,
                pt.type_name as product_cat,
                pv.mrp,
                i.stock_quantity as stock
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_default = 1
            LEFT JOIN inventory i ON pv.variant_id = i.variant_id
            WHERE pt.type_name = ? AND p.is_active = 1
            ORDER BY p.product_name
        """
        results = self.db.execute_query(query, (category,))
        
        products = []
        for row in results:
            product = Product(
                product_id=row['product_id'],
                product_name=row['product_name'],
                product_cat=row['product_cat'],
                stock=row['stock'] if row['stock'] is not None else 0,
                unit=row['base_unit'],
                mrp=row['mrp'] if row['mrp'] is not None else 0.0,
                supplier_name=row['brand_name']
            )
            products.append(product)
        
        return products
    
    def get_total_product_count(self) -> int:
        """Get total number of active products."""
        query = "SELECT COUNT(*) as count FROM products WHERE is_active = 1"
        result = self.db.execute_query(query)
        return result[0]['count'] if result else 0
    
    def get_total_stock_value(self) -> float:
        """Calculate total stock value."""
        query = """
            SELECT SUM(i.stock_quantity * pv.cost_price) as total_value
            FROM inventory i
            JOIN product_variants pv ON i.variant_id = pv.variant_id
            JOIN products p ON pv.product_id = p.product_id
            WHERE p.is_active = 1
        """
        result = self.db.execute_query(query)
        return result[0]['total_value'] if result and result[0]['total_value'] else 0.0
    
    def get_low_stock_products(self, threshold: int = 10) -> List[Product]:
        """Get products with low stock."""
        query = """
            SELECT 
                p.product_id,
                p.product_name,
                p.base_unit,
                b.brand_name,
                pt.type_name as product_cat,
                pv.mrp,
                i.stock_quantity as stock
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_default = 1
            LEFT JOIN inventory i ON pv.variant_id = i.variant_id
            WHERE i.stock_quantity <= ? AND p.is_active = 1
            ORDER BY i.stock_quantity ASC
        """
        results = self.db.execute_query(query, (threshold,))
        
        products = []
        for row in results:
            product = Product(
                product_id=row['product_id'],
                product_name=row['product_name'],
                product_cat=row['product_cat'],
                stock=row['stock'] if row['stock'] is not None else 0,
                unit=row['base_unit'],
                mrp=row['mrp'] if row['mrp'] is not None else 0.0,
                supplier_name=row['brand_name']
            )
            products.append(product)
        
        return products
    
    def update_stock(self, product_id: int, quantity: int) -> bool:
        """Update product stock (for default variant)."""
        try:
            query = """
                UPDATE inventory
                SET stock_quantity = stock_quantity + ?,
                    last_updated = datetime('now')
                WHERE variant_id IN (
                    SELECT variant_id FROM product_variants
                    WHERE product_id = ? AND is_default = 1
                )
            """
            self.db.execute_update(query, (quantity, product_id))
            return True
        except Exception as e:
            print(f"Error updating stock: {str(e)}")
            return False
    
    def add_product_with_variants(self, product_data: dict) -> bool:
        """
        Add a new product with its variants and initial inventory.
        Returns True if successful, False otherwise.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate product code if not provided
            product_code = product_data.get('product_code')
            if not product_code:
                # Get type abbreviation
                type_id = product_data['product_type_id']
                cursor.execute("SELECT type_name FROM product_types WHERE product_type_id = ?", (type_id,))
                type_result = cursor.fetchone()
                type_abbr = type_result[0][:3].upper() if type_result else "PRD"
                
                # Get next product number
                cursor.execute("SELECT COUNT(*) FROM products WHERE product_type_id = ?", (type_id,))
                count = cursor.fetchone()[0]
                product_code = f"JL-{type_abbr}-{count + 1:03d}"
            
            # Insert product
            cursor.execute("""
                INSERT INTO products (
                    product_code, product_name, brand_id, product_type_id,
                    base_unit, hsn_code, description, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                product_code,
                product_data['product_name'],
                product_data['brand_id'],
                product_data['product_type_id'],
                product_data.get('base_unit', 'Kg'),
                product_data.get('hsn_code', ''),
                product_data.get('description', ''),
                product_data.get('is_active', 1)
            ))
            
            product_id = cursor.lastrowid
            
            # Insert variants and inventory
            for variant in product_data['variants']:
                # Insert variant
                cursor.execute("""
                    INSERT INTO product_variants (
                        product_id, variant_name, sku, unit_size, size_unit,
                        mrp, cost_price, is_default, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
                """, (
                    product_id,
                    variant['variant_name'],
                    variant['sku'],
                    variant['unit_size'],
                    variant['size_unit'],
                    variant['mrp'],
                    variant['cost_price'],
                    1 if variant['is_default'] else 0
                ))
                
                variant_id = cursor.lastrowid
                
                # Insert initial inventory
                cursor.execute("""
                    INSERT INTO inventory (
                        variant_id, stock_quantity, reorder_level,
                        last_updated
                    ) VALUES (?, ?, ?, datetime('now'))
                """, (
                    variant_id,
                    variant.get('initial_stock', 0),
                    variant.get('reorder_level', 10)
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error adding product: {str(e)}")
            if conn:
                conn.rollback()
                conn.close()
            return False
    
    def get_next_product_code(self, product_type_id: int) -> str:
        """Generate next product code for a given type."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get type abbreviation
            cursor.execute("SELECT type_name FROM product_types WHERE product_type_id = ?", (product_type_id,))
            type_result = cursor.fetchone()
            type_abbr = type_result[0][:3].upper() if type_result else "PRD"
            
            # Get next number
            cursor.execute("SELECT COUNT(*) FROM products WHERE product_type_id = ?", (product_type_id,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return f"JL-{type_abbr}-{count + 1:03d}"
            
        except Exception as e:
            print(f"Error generating product code: {str(e)}")
            return "JL-NEW-001"
