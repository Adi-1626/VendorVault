"""
Analytics and reporting business logic.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
import config
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
    
    def get_best_selling_month(self, limit: int = 5) -> List[Dict]:
        """Get best-selling products for current month."""
        today = datetime.now()
        month_start = today.replace(day=1).strftime("%Y-%m-%d")
        month_end = today.strftime("%Y-%m-%d")
        return self.get_best_selling_products(month_start, month_end, limit)
    
    def get_best_selling_year(self, limit: int = 5) -> List[Dict]:
        """Get best-selling products for current year."""
        today = datetime.now()
        year_start = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        year_end = today.strftime("%Y-%m-%d")
        return self.get_best_selling_products(year_start, year_end, limit)
    
    def calculate_profit_by_product(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Calculate profit by product for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            List of dictionaries with product and profit info
        """
        # Get bills
        bill_query = "SELECT bill_details FROM bill WHERE 1=1"
        params = []
        
        if start_date:
            bill_query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            bill_query += " AND date <= ?"
            params.append(end_date)
        
        bills = self.db.execute_query(bill_query, tuple(params))
        
        # Get product cost prices
        product_query = "SELECT product_name, cost_price, mrp FROM raw_inventory"
        products = self.db.execute_query(product_query)
        
        # Create cost price lookup
        cost_prices = {}
        mrp_prices = {}
        for product in products:
            cost_prices[product['product_name']] = product['cost_price'] or 0
            mrp_prices[product['product_name']] = product['mrp'] or 0
        
        # Calculate profit per product
        product_profits = defaultdict(lambda: {'quantity': 0, 'profit': 0.0})
        
        for bill in bills:
            items = self.parse_bill_details(bill['bill_details'])
            for product_name, quantity, _ in items:
                cost = cost_prices.get(product_name, 0)
                mrp = mrp_prices.get(product_name, 0)
                profit = (mrp - cost) * quantity
                
                product_profits[product_name]['quantity'] += quantity
                product_profits[product_name]['profit'] += profit
        
        # Convert to list and sort by profit
        result = [
            {
                'product_name': name,
                'quantity': data['quantity'],
                'profit': data['profit']
            }
            for name, data in product_profits.items()
        ]
        
        result.sort(key=lambda x: x['profit'], reverse=True)
        return result
    
    def get_profit_today(self) -> List[Dict]:
        """Get profit by product for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.calculate_profit_by_product(today, today)
    
    def get_daily_sales_summary(self, date: str = None) -> Dict:
        """
        Get sales summary for a specific day.
        
        Args:
            date: Date (YYYY-MM-DD), defaults to today
        
        Returns:
            Dictionary with sales metrics
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Get bills for the date
        query = """
            SELECT COUNT(*) as bill_count, 
                   SUM(total) as total_revenue,
                   SUM(subtotal) as subtotal,
                   SUM(tax_amount) as total_tax,
                   SUM(discount) as total_discount
            FROM bill 
            WHERE date = ?
        """
        results = self.db.execute_query(query, (date,))
        
        if results:
            row = results[0]
            return {
                'date': date,
                'bill_count': row['bill_count'] or 0,
                'total_revenue': row['total_revenue'] or 0.0,
                'subtotal': row['subtotal'] or 0.0,
                'total_tax': row['total_tax'] or 0.0,
                'total_discount': row['total_discount'] or 0.0
            }
        
        return {
            'date': date,
            'bill_count': 0,
            'total_revenue': 0.0,
            'subtotal': 0.0,
            'total_tax': 0.0,
            'total_discount': 0.0
        }
    
    def get_monthly_sales_summary(self, year: int = None, month: int = None) -> Dict:
        """Get sales summary for a month."""
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        month_start = f"{year}-{month:02d}-01"
        
        # Calculate last day of month
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        
        query = """
            SELECT COUNT(*) as bill_count, 
                   SUM(total) as total_revenue,
                   SUM(subtotal) as subtotal,
                   SUM(tax_amount) as total_tax,
                   SUM(discount) as total_discount
            FROM bill 
            WHERE date >= ? AND date < ?
        """
        results = self.db.execute_query(query, (month_start, next_month))
        
        if results:
            row = results[0]
            return {
                'year': year,
                'month': month,
                'bill_count': row['bill_count'] or 0,
                'total_revenue': row['total_revenue'] or 0.0,
                'subtotal': row['subtotal'] or 0.0,
                'total_tax': row['total_tax'] or 0.0,
                'total_discount': row['total_discount'] or 0.0
            }
        
        return {
            'year': year,
            'month': month,
            'bill_count': 0,
            'total_revenue': 0.0,
            'subtotal': 0.0,
            'total_tax': 0.0,
            'total_discount': 0.0
        }
