"""
Brand management business logic.
"""
from typing import List, Dict, Optional
from src.database.connection import DatabaseConnection


class BrandService:
    """Service class for brand operations."""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def get_all_brands(self) -> List[Dict]:
        """Get all brands."""
        query = "SELECT * FROM brands ORDER BY brand_name"
        return self.db.execute_query(query)
    
    def get_brand_by_id(self, brand_id: int) -> Optional[Dict]:
        """Get brand by ID."""
        query = "SELECT * FROM brands WHERE brand_id = ?"
        results = self.db.execute_query(query, (brand_id,))
        return results[0] if results else None
    
    def search_brands(self, search_term: str) -> List[Dict]:
        """Search brands by name."""
        query = "SELECT * FROM brands WHERE brand_name LIKE ? ORDER BY brand_name"
        search_pattern = f"%{search_term}%"
        return self.db.execute_query(query, (search_pattern,))
    
    def add_brand(self, brand_data: Dict) -> bool:
        """Add a new brand."""
        try:
            query = """
                INSERT INTO brands (brand_name, description, is_active)
                VALUES (?, ?, ?)
            """
            self.db.execute_insert(
                query,
                (
                    brand_data['brand_name'],
                    brand_data.get('description', ''),
                    brand_data.get('is_active', 1)
                )
            )
            return True
        except Exception as e:
            print(f"Error adding brand: {str(e)}")
            return False
    
    def update_brand(self, brand_id: int, brand_data: Dict) -> bool:
        """Update an existing brand."""
        try:
            query = """
                UPDATE brands
                SET brand_name = ?, description = ?, is_active = ?
                WHERE brand_id = ?
            """
            self.db.execute_update(
                query,
                (
                    brand_data['brand_name'],
                    brand_data.get('description', ''),
                    brand_data.get('is_active', 1),
                    brand_id
                )
            )
            return True
        except Exception as e:
            print(f"Error updating brand: {str(e)}")
            return False
    
    def delete_brand(self, brand_id: int) -> bool:
        """
        Delete a brand (soft delete by setting is_active = 0).
        Only allows deletion if no products are using this brand.
        """
        try:
            # Check if any products use this brand
            check_query = "SELECT COUNT(*) as count FROM products WHERE brand_id = ?"
            result = self.db.execute_query(check_query, (brand_id,))
            
            if result and result[0]['count'] > 0:
                print(f"Cannot delete brand: {result[0]['count']} products are using it")
                return False
            
            # Soft delete
            query = "UPDATE brands SET is_active = 0 WHERE brand_id = ?"
            self.db.execute_update(query, (brand_id,))
            return True
        except Exception as e:
            print(f"Error deleting brand: {str(e)}")
            return False
    
    def get_active_brands(self) -> List[Dict]:
        """Get only active brands."""
        query = "SELECT * FROM brands WHERE is_active = 1 ORDER BY brand_name"
        return self.db.execute_query(query)
