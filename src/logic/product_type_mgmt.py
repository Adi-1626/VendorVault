"""
Product Type management business logic.
"""
from typing import List, Dict, Optional
from src.database.connection import DatabaseConnection


class ProductTypeService:
    """Service class for product type operations."""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def get_all_product_types(self) -> List[Dict]:
        """Get all product types ordered by display order."""
        query = "SELECT * FROM product_types ORDER BY display_order, type_name"
        return self.db.execute_query(query)
    
    def get_product_type_by_id(self, type_id: int) -> Optional[Dict]:
        """Get product type by ID."""
        query = "SELECT * FROM product_types WHERE product_type_id = ?"
        results = self.db.execute_query(query, (type_id,))
        return results[0] if results else None
    
    def search_product_types(self, search_term: str) -> List[Dict]:
        """Search product types by name or HSN code."""
        query = """
            SELECT * FROM product_types 
            WHERE type_name LIKE ? OR hsn_code LIKE ?
            ORDER BY display_order, type_name
        """
        search_pattern = f"%{search_term}%"
        return self.db.execute_query(query, (search_pattern, search_pattern))
    
    def add_product_type(self, type_data: Dict) -> bool:
        """Add a new product type."""
        try:
            query = """
                INSERT INTO product_types (type_name, hsn_code, display_order, is_active)
                VALUES (?, ?, ?, ?)
            """
            self.db.execute_insert(
                query,
                (
                    type_data['type_name'],
                    type_data.get('hsn_code', ''),
                    type_data.get('display_order', 0),
                    type_data.get('is_active', 1)
                )
            )
            return True
        except Exception as e:
            print(f"Error adding product type: {str(e)}")
            return False
    
    def update_product_type(self, type_id: int, type_data: Dict) -> bool:
        """Update an existing product type."""
        try:
            query = """
                UPDATE product_types
                SET type_name = ?, hsn_code = ?, display_order = ?, is_active = ?
                WHERE product_type_id = ?
            """
            self.db.execute_update(
                query,
                (
                    type_data['type_name'],
                    type_data.get('hsn_code', ''),
                    type_data.get('display_order', 0),
                    type_data.get('is_active', 1),
                    type_id
                )
            )
            return True
        except Exception as e:
            print(f"Error updating product type: {str(e)}")
            return False
    
    def delete_product_type(self, type_id: int) -> bool:
        """
        Delete a product type (soft delete).
        Only allows deletion if no products use this type.
        """
        try:
            # Check if products use this type
            check_query = "SELECT COUNT(*) as count FROM products WHERE product_type_id = ?"
            result = self.db.execute_query(check_query, (type_id,))
            
            if result and result[0]['count'] > 0:
                print(f"Cannot delete: {result[0]['count']} products use this type")
                return False
            
            # Soft delete
            query = "UPDATE product_types SET is_active = 0 WHERE product_type_id = ?"
            self.db.execute_update(query, (type_id,))
            return True
        except Exception as e:
            print(f"Error deleting product type: {str(e)}")
            return False
    
    def get_active_product_types(self) -> List[Dict]:
        """Get only active product types."""
        query = "SELECT * FROM product_types WHERE is_active = 1 ORDER BY display_order, type_name"
        return self.db.execute_query(query)
