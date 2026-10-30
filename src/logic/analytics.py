"""
Lightweight best-seller queries used by the POS quick-add grid and the
admin Overview. The Analytics page uses :mod:`src.logic.analytics_engine`.
"""
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict
from src.database.connection import db


class AnalyticsService:
    """Service class for analytics and reporting."""
    
    def __init__(self):
        self.db = db
    
    def parse_bill_details(self, bill_details: str) -> List[Tuple[str, int, float]]:
        """
        Parse bill details string to extract product information.
        
        Args:
            bill_details: Bill details string
        
        Returns:
            List of tuples (product_name, quantity, price)
        """
        items = []
        lines = bill_details.strip().split('\n')
        
        for line in lines:
            parts = line.split('\t')
            # Filter out empty parts
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 3:
                try:
                    product_name = parts[0]
                    quantity = int(parts[1])
                    price = float(parts[2])
                    items.append((product_name, quantity, price))
                except (ValueError, IndexError):
                    continue
        
        return items
    
    def get_best_selling_products(self, start_date: str = None, end_date: str = None, 
                                  limit: int = 5) -> List[Dict]:
        """
        Get best-selling products for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Number of top products to return
        
        Returns:
            List of dictionaries with product info and quantity sold
        """
        query = "SELECT bill_details FROM bill WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        results = self.db.execute_query(query, tuple(params))
        
        # Aggregate product quantities
        product_quantities = defaultdict(int)
        
        for row in results:
            items = self.parse_bill_details(row['bill_details'])
            for product_name, quantity, _ in items:
                product_quantities[product_name] += quantity
        
        # Sort and get top products
        sorted_products = sorted(
            product_quantities.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:limit]
        
        return [
            {'product_name': name, 'quantity_sold': qty}
            for name, qty in sorted_products
        ]
    
    def get_best_selling_today(self, limit: int = 5) -> List[Dict]:
        """Get best-selling products for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_best_selling_products(today, today, limit)
