"""
Enterprise Analytics Engine for POS Bill Generation System.
Provides KPI calculations, data aggregation, and analytics using Pandas.
Version: 2.0.0 | Created: January 2026
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache
from collections import defaultdict
import json
import logging

from src.database.connection import db

logger = logging.getLogger(__name__)


# =============================================================================
# DATE RANGE UTILITIES
# =============================================================================

class DateRange:
    """Date range helper for analytics filtering."""
    
    PRESET_7D = "7D"
    PRESET_30D = "30D"
    PRESET_90D = "90D"
    PRESET_365D = "365D"
    PRESET_MTD = "MTD"  # Month to date
    PRESET_YTD = "YTD"  # Year to date
    PRESET_CUSTOM = "CUSTOM"
    
    @staticmethod
    def get_date_bounds(preset: str, custom_start: str = None, custom_end: str = None) -> Tuple[str, str]:
        """
        Get start and end dates for a preset or custom range.
        
        Args:
            preset: One of 7D, 30D, 90D, 365D, MTD, YTD, CUSTOM
            custom_start: Start date for CUSTOM (YYYY-MM-DD)
            custom_end: End date for CUSTOM (YYYY-MM-DD)
            
        Returns:
            Tuple of (start_date, end_date) as strings
        """
        today = datetime.now().date()
        end_date = today.strftime("%Y-%m-%d")
        
        if preset == DateRange.PRESET_7D:
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        elif preset == DateRange.PRESET_30D:
            start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        elif preset == DateRange.PRESET_90D:
            start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        elif preset == DateRange.PRESET_365D:
            start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        elif preset == DateRange.PRESET_MTD:
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
        elif preset == DateRange.PRESET_YTD:
            start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        elif preset == DateRange.PRESET_CUSTOM and custom_start and custom_end:
            start_date = custom_start
            end_date = custom_end
        else:
            # Default to 30 days
            start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        
        return start_date, end_date
    
    @staticmethod
    def get_previous_period(start_date: str, end_date: str) -> Tuple[str, str]:
        """Get the equivalent previous period for comparison."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        period_days = (end - start).days
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days)
        
        return prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d")


# =============================================================================
# KPI UTILITIES
# =============================================================================

class KPICalculator:
    """Utility class for KPI calculations."""
    
    @staticmethod
    def calculate_growth_percent(current: float, previous: float) -> float:
        """Calculate growth percentage between two values."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)
    
    @staticmethod
    def format_currency(value: float) -> str:
        """Format value as Indian currency."""
        return f"₹{value:,.2f}"
    
    @staticmethod
    def format_percent(value: float) -> str:
        """Format value as percentage."""
        return f"{value:+.1f}%" if value != 0 else "0%"


# =============================================================================
# SALES ANALYTICS
# =============================================================================

class SalesAnalytics:
    """Sales analytics with KPIs and trend analysis."""
    
    def __init__(self):
        self.db = db
    
    def get_sales_kpis(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get sales KPIs for date range with comparison to previous period.
        
        Returns:
            Dict with revenue, aov, bill_count, units_sold and their changes
        """
        # Current period
        current = self._get_sales_summary(start_date, end_date)
        
        # Previous period for comparison
        prev_start, prev_end = DateRange.get_previous_period(start_date, end_date)
        previous = self._get_sales_summary(prev_start, prev_end)
        
        return {
            'total_revenue': current['total_revenue'],
            'revenue_change': KPICalculator.calculate_growth_percent(
                current['total_revenue'], previous['total_revenue']
            ),
            'avg_order_value': current['avg_order_value'],
            'aov_change': KPICalculator.calculate_growth_percent(
                current['avg_order_value'], previous['avg_order_value']
            ),
            'bill_count': current['bill_count'],
            'bill_change': KPICalculator.calculate_growth_percent(
                current['bill_count'], previous['bill_count']
            ),
            'total_units': current['total_units'],
            'units_change': KPICalculator.calculate_growth_percent(
                current['total_units'], previous['total_units']
            ),
            'total_tax': current['total_tax'],
            'total_discount': current['total_discount'],
            'period': f"{start_date} to {end_date}"
        }
    
    def _get_sales_summary(self, start_date: str, end_date: str) -> Dict:
        """Get sales summary for a date range."""
        query = """
            SELECT 
                COUNT(*) as bill_count,
                COALESCE(SUM(total), 0) as total_revenue,
                COALESCE(AVG(total), 0) as avg_order_value,
                COALESCE(SUM(tax_amount), 0) as total_tax,
                COALESCE(SUM(discount), 0) as total_discount
            FROM bill
            WHERE date(date) >= ? AND date(date) <= ?
        """
        result = self.db.execute_query(query, (start_date, end_date))
        
        if result:
            row = result[0]
            # Parse bill details to get unit count
            total_units = self._count_units_sold(start_date, end_date)
            return {
                'bill_count': row['bill_count'] or 0,
                'total_revenue': row['total_revenue'] or 0,
                'avg_order_value': row['avg_order_value'] or 0,
                'total_tax': row['total_tax'] or 0,
                'total_discount': row['total_discount'] or 0,
                'total_units': total_units
            }
        
        return {
            'bill_count': 0, 'total_revenue': 0, 'avg_order_value': 0,
            'total_tax': 0, 'total_discount': 0, 'total_units': 0
        }
    
    def _count_units_sold(self, start_date: str, end_date: str) -> int:
        """Count total units sold from bill details."""
        query = """
            SELECT bill_details, bill_variants_json 
            FROM bill 
            WHERE date(date) >= ? AND date(date) <= ?
        """
        bills = self.db.execute_query(query, (start_date, end_date))
        
        total_units = 0
        for bill in bills:
            # Try JSON format first
            if bill.get('bill_variants_json'):
                try:
                    items = json.loads(bill['bill_variants_json'])
                    total_units += sum(item.get('quantity', 0) for item in items)
                    continue
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Fall back to text format
            if bill.get('bill_details'):
                for line in bill['bill_details'].split('\n'):
                    parts = [p.strip() for p in line.split('\t') if p.strip()]
                    if len(parts) >= 2:
                        try:
                            total_units += int(parts[1])
                        except ValueError:
                            pass
        
        return total_units
    
    def get_daily_revenue_trend(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get daily revenue trend as DataFrame."""
        query = """
            SELECT 
                date(date) as sale_date,
                COUNT(*) as bill_count,
                COALESCE(SUM(total), 0) as total_revenue,
                COALESCE(AVG(total), 0) as avg_order_value
            FROM bill
            WHERE date(date) >= ? AND date(date) <= ?
            GROUP BY date(date)
            ORDER BY sale_date
        """
        results = self.db.execute_query(query, (start_date, end_date))
        
        if not results:
            return pd.DataFrame(columns=['sale_date', 'bill_count', 'total_revenue', 'avg_order_value'])
        
        df = pd.DataFrame(results)
        df['sale_date'] = pd.to_datetime(df['sale_date'])
        return df
    
    def get_top_products(self, start_date: str, end_date: str, limit: int = 10) -> List[Dict]:
        """Get top selling products by quantity."""
        query = """
            SELECT bill_details, bill_variants_json 
            FROM bill 
            WHERE date(date) >= ? AND date(date) <= ?
        """
        bills = self.db.execute_query(query, (start_date, end_date))
        
        product_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0})
        
        for bill in bills:
            # Try JSON format
            if bill.get('bill_variants_json'):
                try:
                    items = json.loads(bill['bill_variants_json'])
                    for item in items:
                        name = item.get('product_name', 'Unknown')
                        qty = item.get('quantity', 0)
                        price = item.get('unit_price', 0) * qty
                        product_sales[name]['quantity'] += qty
                        product_sales[name]['revenue'] += price
                    continue
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Fall back to text format
            if bill.get('bill_details'):
                for line in bill['bill_details'].split('\n'):
                    parts = [p.strip() for p in line.split('\t') if p.strip()]
                    if len(parts) >= 3:
                        try:
                            name = parts[0]
                            qty = int(parts[1])
                            price = float(parts[2]) * qty
                            product_sales[name]['quantity'] += qty
                            product_sales[name]['revenue'] += price
                        except (ValueError, IndexError):
                            pass
        
        # Sort by quantity and limit
        sorted_products = sorted(
            product_sales.items(),
            key=lambda x: x[1]['quantity'],
            reverse=True
        )[:limit]
        
        return [
            {'product_name': name, 'quantity': data['quantity'], 'revenue': data['revenue']}
            for name, data in sorted_products
        ]
    
    def get_bottom_products(self, start_date: str, end_date: str, limit: int = 10) -> List[Dict]:
        """Get lowest selling products."""
        query = """
            SELECT bill_details, bill_variants_json 
            FROM bill 
            WHERE date(date) >= ? AND date(date) <= ?
        """
        bills = self.db.execute_query(query, (start_date, end_date))
        
        product_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0})
        
        for bill in bills:
            if bill.get('bill_variants_json'):
                try:
                    items = json.loads(bill['bill_variants_json'])
                    for item in items:
                        name = item.get('product_name', 'Unknown')
                        qty = item.get('quantity', 0)
                        price = item.get('unit_price', 0) * qty
                        product_sales[name]['quantity'] += qty
                        product_sales[name]['revenue'] += price
                    continue
                except (json.JSONDecodeError, TypeError):
                    pass
            
            if bill.get('bill_details'):
                for line in bill['bill_details'].split('\n'):
                    parts = [p.strip() for p in line.split('\t') if p.strip()]
                    if len(parts) >= 3:
                        try:
                            name = parts[0]
                            qty = int(parts[1])
                            price = float(parts[2]) * qty
                            product_sales[name]['quantity'] += qty
                            product_sales[name]['revenue'] += price
                        except (ValueError, IndexError):
                            pass
        
        # Sort by quantity ascending
        sorted_products = sorted(
            product_sales.items(),
            key=lambda x: x[1]['quantity']
        )[:limit]
        
        return [
            {'product_name': name, 'quantity': data['quantity'], 'revenue': data['revenue']}
            for name, data in sorted_products
        ]
    
    def get_sales_by_product_type(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get sales aggregated by product type."""
        # Get product type mapping
        product_types = self.db.execute_query("""
            SELECT p.product_name, pt.type_name
            FROM products p
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
        """)
        
        type_map = {row['product_name']: row['type_name'] for row in product_types}
        
        # Get sales
        top_products = self.get_top_products(start_date, end_date, limit=1000)
        
        type_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0})
        for product in top_products:
            ptype = type_map.get(product['product_name'], 'Other')
            type_sales[ptype]['quantity'] += product['quantity']
            type_sales[ptype]['revenue'] += product['revenue']
        
        return pd.DataFrame([
            {'product_type': ptype, 'quantity': data['quantity'], 'revenue': data['revenue']}
            for ptype, data in type_sales.items()
        ])
    
    def get_sales_by_brand(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get sales aggregated by brand."""
        # Get brand mapping
        brands = self.db.execute_query("""
            SELECT p.product_name, b.brand_name
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
        """)
        
        brand_map = {row['product_name']: row['brand_name'] for row in brands}
        
        # Get sales
        top_products = self.get_top_products(start_date, end_date, limit=1000)
        
        brand_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0})
        for product in top_products:
            brand = brand_map.get(product['product_name'], 'Other')
            brand_sales[brand]['quantity'] += product['quantity']
            brand_sales[brand]['revenue'] += product['revenue']
        
        return pd.DataFrame([
            {'brand_name': brand, 'quantity': data['quantity'], 'revenue': data['revenue']}
            for brand, data in brand_sales.items()
        ])


# =============================================================================
# INVENTORY ANALYTICS
# =============================================================================

class InventoryAnalytics:
    """Inventory analytics with stock health and turnover metrics."""
    
    def __init__(self):
        self.db = db
    
    def get_inventory_kpis(self) -> Dict[str, Any]:
        """Get inventory KPIs."""
        query = """
            SELECT 
                COUNT(*) as total_variants,
                COALESCE(SUM(stock_quantity), 0) as total_stock,
                COALESCE(SUM(stock_quantity * cost_price), 0) as stock_value,
                COALESCE(SUM(stock_quantity * mrp), 0) as stock_mrp_value,
                COUNT(CASE WHEN stock_status = 'LOW' THEN 1 END) as low_stock_count,
                COUNT(CASE WHEN stock_status = 'OUT_OF_STOCK' THEN 1 END) as out_of_stock_count,
                COUNT(CASE WHEN stock_status = 'EXPIRED' THEN 1 END) as expired_count,
                COUNT(CASE WHEN stock_status = 'OVERSTOCK' THEN 1 END) as overstock_count,
                COUNT(CASE WHEN expiring_soon = 1 THEN 1 END) as expiring_soon_count
            FROM views_inventory_health
        """
        
        try:
            result = self.db.execute_query(query)
            if result:
                row = result[0]
                return {
                    'total_variants': row['total_variants'] or 0,
                    'total_stock': row['total_stock'] or 0,
                    'stock_value': row['stock_value'] or 0,
                    'stock_mrp_value': row['stock_mrp_value'] or 0,
                    'low_stock_count': row['low_stock_count'] or 0,
                    'out_of_stock_count': row['out_of_stock_count'] or 0,
                    'expired_count': row['expired_count'] or 0,
                    'overstock_count': row['overstock_count'] or 0,
                    'expiring_soon_count': row['expiring_soon_count'] or 0
                }
        except Exception as e:
            logger.warning(f"Could not get inventory KPIs from view: {e}")
            # Fallback to direct query
            return self._get_inventory_kpis_fallback()
        
        return self._empty_inventory_kpis()
    
    def _get_inventory_kpis_fallback(self) -> Dict[str, Any]:
        """Fallback inventory KPIs without views."""
        query = """
            SELECT 
                COUNT(*) as total_variants,
                COALESCE(SUM(i.stock_quantity), 0) as total_stock,
                COALESCE(SUM(i.stock_quantity * pv.cost_price), 0) as stock_value
            FROM inventory i
            JOIN product_variants pv ON i.variant_id = pv.variant_id
            JOIN products p ON pv.product_id = p.product_id
            WHERE p.is_active = 1
        """
        result = self.db.execute_query(query)
        
        if result:
            row = result[0]
            return {
                'total_variants': row['total_variants'] or 0,
                'total_stock': row['total_stock'] or 0,
                'stock_value': row['stock_value'] or 0,
                'stock_mrp_value': 0,
                'low_stock_count': 0,
                'out_of_stock_count': 0,
                'expired_count': 0,
                'overstock_count': 0,
                'expiring_soon_count': 0
            }
        
        return self._empty_inventory_kpis()
    
    def _empty_inventory_kpis(self) -> Dict[str, Any]:
        """Return empty KPIs structure."""
        return {
            'total_variants': 0, 'total_stock': 0, 'stock_value': 0,
            'stock_mrp_value': 0, 'low_stock_count': 0, 'out_of_stock_count': 0,
            'expired_count': 0, 'overstock_count': 0, 'expiring_soon_count': 0
        }
    
    def get_low_stock_items(self, limit: int = 20) -> List[Dict]:
        """Get low stock items."""
        try:
            query = """
                SELECT product_name, variant_name, stock_quantity, reorder_level, 
                       product_type, brand_name, sku, stock_status
                FROM views_inventory_health
                WHERE stock_status IN ('LOW', 'OUT_OF_STOCK')
                ORDER BY stock_quantity ASC
                LIMIT ?
            """
            return self.db.execute_query(query, (limit,))
        except Exception as e:
            logger.warning(f"Could not get low stock from view: {e}")
            return self._get_low_stock_fallback(limit)
    
    def _get_low_stock_fallback(self, limit: int) -> List[Dict]:
        """Fallback low stock query."""
        query = """
            SELECT p.product_name, pv.variant_name, i.stock_quantity, i.reorder_level
            FROM inventory i
            JOIN product_variants pv ON i.variant_id = pv.variant_id
            JOIN products p ON pv.product_id = p.product_id
            WHERE i.stock_quantity <= i.reorder_level AND p.is_active = 1
            ORDER BY i.stock_quantity ASC
            LIMIT ?
        """
        return self.db.execute_query(query, (limit,))
    
    def get_stock_by_product_type(self) -> pd.DataFrame:
        """Get stock distribution by product type."""
        try:
            query = """
                SELECT product_type, 
                       COUNT(*) as variant_count,
                       COALESCE(SUM(stock_quantity), 0) as total_stock,
                       COALESCE(SUM(stock_value), 0) as stock_value
                FROM views_inventory_health
                GROUP BY product_type
                ORDER BY stock_value DESC
            """
            results = self.db.execute_query(query)
        except Exception:
            query = """
                SELECT pt.type_name as product_type,
                       COUNT(*) as variant_count,
                       COALESCE(SUM(i.stock_quantity), 0) as total_stock,
                       COALESCE(SUM(i.stock_quantity * pv.cost_price), 0) as stock_value
                FROM product_types pt
                LEFT JOIN products p ON pt.product_type_id = p.product_type_id
                LEFT JOIN product_variants pv ON p.product_id = pv.product_id
                LEFT JOIN inventory i ON pv.variant_id = i.variant_id
                WHERE pt.is_active = 1
                GROUP BY pt.type_name
                ORDER BY stock_value DESC
            """
            results = self.db.execute_query(query)
        
        if not results:
            return pd.DataFrame(columns=['product_type', 'variant_count', 'total_stock', 'stock_value'])
        
        return pd.DataFrame(results)
    
    def get_stock_by_brand(self) -> pd.DataFrame:
        """Get stock distribution by brand."""
        try:
            query = """
                SELECT brand_name,
                       COUNT(*) as variant_count,
                       COALESCE(SUM(stock_quantity), 0) as total_stock,
                       COALESCE(SUM(stock_value), 0) as stock_value
                FROM views_inventory_health
                GROUP BY brand_name
                ORDER BY stock_value DESC
            """
            results = self.db.execute_query(query)
        except Exception:
            query = """
                SELECT b.brand_name,
                       COUNT(*) as variant_count,
                       COALESCE(SUM(i.stock_quantity), 0) as total_stock,
                       COALESCE(SUM(i.stock_quantity * pv.cost_price), 0) as stock_value
                FROM brands b
                LEFT JOIN products p ON b.brand_id = p.brand_id
                LEFT JOIN product_variants pv ON p.product_id = pv.product_id
                LEFT JOIN inventory i ON pv.variant_id = i.variant_id
                WHERE b.is_active = 1
                GROUP BY b.brand_name
                ORDER BY stock_value DESC
            """
            results = self.db.execute_query(query)
        
        if not results:
            return pd.DataFrame(columns=['brand_name', 'variant_count', 'total_stock', 'stock_value'])
        
        return pd.DataFrame(results)


# =============================================================================
# PROFITABILITY ANALYTICS
# =============================================================================

class ProfitabilityAnalytics:
    """Profitability analytics with margin analysis."""
    
    def __init__(self):
        self.db = db
        self.sales = SalesAnalytics()
    
    def get_profitability_kpis(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get profitability KPIs."""
        # Get product cost mapping
        cost_map = self._get_cost_map()
        
        # Get sales with revenue
        top_products = self.sales.get_top_products(start_date, end_date, limit=1000)
        
        total_revenue = 0
        total_cost = 0
        
        for product in top_products:
            qty = product['quantity']
            revenue = product['revenue']
            cost = cost_map.get(product['product_name'], {}).get('cost', 0) * qty
            
            total_revenue += revenue
            total_cost += cost
        
        gross_profit = total_revenue - total_cost
        margin_percent = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'gross_profit': gross_profit,
            'margin_percent': round(margin_percent, 2),
            'period': f"{start_date} to {end_date}"
        }
    
    def _get_cost_map(self) -> Dict[str, Dict]:
        """Get product name to cost/mrp mapping."""
        query = """
            SELECT p.product_name, pv.cost_price, pv.mrp
            FROM products p
            JOIN product_variants pv ON p.product_id = pv.product_id AND pv.is_default = 1
        """
        results = self.db.execute_query(query)
        
        return {
            row['product_name']: {
                'cost': row['cost_price'] or 0,
                'mrp': row['mrp'] or 0
            }
            for row in results
        }
    
    def get_profit_by_product(self, start_date: str, end_date: str, limit: int = 10) -> List[Dict]:
        """Get profit analysis by product."""
        cost_map = self._get_cost_map()
        top_products = self.sales.get_top_products(start_date, end_date, limit=100)
        
        profit_list = []
        for product in top_products:
            name = product['product_name']
            qty = product['quantity']
            revenue = product['revenue']
            unit_cost = cost_map.get(name, {}).get('cost', 0)
            total_cost = unit_cost * qty
            profit = revenue - total_cost
            margin = (profit / revenue * 100) if revenue > 0 else 0
            
            profit_list.append({
                'product_name': name,
                'quantity': qty,
                'revenue': revenue,
                'cost': total_cost,
                'profit': profit,
                'margin_percent': round(margin, 2)
            })
        
        # Sort by profit
        profit_list.sort(key=lambda x: x['profit'], reverse=True)
        return profit_list[:limit]
    
    def get_loss_making_products(self, start_date: str, end_date: str, limit: int = 10) -> List[Dict]:
        """Get products with negative margins."""
        all_products = self.get_profit_by_product(start_date, end_date, limit=1000)
        
        loss_products = [p for p in all_products if p['profit'] < 0]
        loss_products.sort(key=lambda x: x['profit'])  # Most negative first
        
        return loss_products[:limit]
    
    def get_profit_by_category(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get profit aggregated by product type."""
        cost_map = self._get_cost_map()
        
        # Get type mapping
        type_map = {}
        types = self.db.execute_query("""
            SELECT p.product_name, pt.type_name
            FROM products p
            JOIN product_types pt ON p.product_type_id = pt.product_type_id
        """)
        for row in types:
            type_map[row['product_name']] = row['type_name']
        
        # Get sales
        top_products = self.sales.get_top_products(start_date, end_date, limit=1000)
        
        category_profit = defaultdict(lambda: {'revenue': 0, 'cost': 0, 'profit': 0})
        for product in top_products:
            name = product['product_name']
            ptype = type_map.get(name, 'Other')
            qty = product['quantity']
            revenue = product['revenue']
            cost = cost_map.get(name, {}).get('cost', 0) * qty
            profit = revenue - cost
            
            category_profit[ptype]['revenue'] += revenue
            category_profit[ptype]['cost'] += cost
            category_profit[ptype]['profit'] += profit
        
        result = []
        for ptype, data in category_profit.items():
            margin = (data['profit'] / data['revenue'] * 100) if data['revenue'] > 0 else 0
            result.append({
                'product_type': ptype,
                'revenue': data['revenue'],
                'cost': data['cost'],
                'profit': data['profit'],
                'margin_percent': round(margin, 2)
            })
        
        df = pd.DataFrame(result) if result else pd.DataFrame(
            columns=['product_type', 'revenue', 'cost', 'profit', 'margin_percent']
        )
        return df.sort_values('profit', ascending=False) if not df.empty else df


# =============================================================================
# SUPPLIER ANALYTICS
# =============================================================================

class SupplierAnalytics:
    """Supplier performance analytics."""
    
    def __init__(self):
        self.db = db
    
    def get_supplier_kpis(self) -> Dict[str, Any]:
        """Get supplier KPIs."""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_suppliers,
                    COALESCE(AVG(avg_lead_time), 0) as avg_lead_time,
                    COALESCE(AVG(avg_unit_cost), 0) as avg_unit_cost,
                    COALESCE(SUM(product_count), 0) as total_products_supplied
                FROM views_supplier_performance
            """
            result = self.db.execute_query(query)
            
            if result:
                row = result[0]
                return {
                    'total_suppliers': row['total_suppliers'] or 0,
                    'avg_lead_time': round(row['avg_lead_time'] or 0, 1),
                    'avg_unit_cost': round(row['avg_unit_cost'] or 0, 2),
                    'total_products_supplied': row['total_products_supplied'] or 0
                }
        except Exception as e:
            logger.warning(f"Could not get supplier KPIs from view: {e}")
            return self._get_supplier_kpis_fallback()
        
        return {'total_suppliers': 0, 'avg_lead_time': 0, 'avg_unit_cost': 0, 'total_products_supplied': 0}
    
    def _get_supplier_kpis_fallback(self) -> Dict[str, Any]:
        """Fallback supplier KPIs."""
        query = "SELECT COUNT(*) as total FROM suppliers WHERE is_active = 1"
        result = self.db.execute_query(query)
        return {
            'total_suppliers': result[0]['total'] if result else 0,
            'avg_lead_time': 0,
            'avg_unit_cost': 0,
            'total_products_supplied': 0
        }
    
    def get_supplier_performance(self, limit: int = 20) -> List[Dict]:
        """Get supplier performance list."""
        try:
            query = """
                SELECT supplier_name, product_count, avg_unit_cost, avg_lead_time, rating
                FROM views_supplier_performance
                ORDER BY product_count DESC, rating DESC
                LIMIT ?
            """
            return self.db.execute_query(query, (limit,))
        except Exception:
            query = """
                SELECT s.supplier_name, COUNT(ps.product_id) as product_count,
                       COALESCE(AVG(ps.unit_cost), 0) as avg_unit_cost,
                       COALESCE(AVG(ps.lead_time_days), 0) as avg_lead_time,
                       s.rating
                FROM suppliers s
                LEFT JOIN product_suppliers ps ON s.supplier_id = ps.supplier_id
                WHERE s.is_active = 1
                GROUP BY s.supplier_id
                ORDER BY product_count DESC
                LIMIT ?
            """
            return self.db.execute_query(query, (limit,))


# =============================================================================
# MAIN ANALYTICS ENGINE
# =============================================================================

class AnalyticsEngine:
    """
    Main analytics engine that aggregates all analytics modules.
    Provides a unified interface for dashboard components.
    """
    
    def __init__(self):
        self.sales = SalesAnalytics()
        self.inventory = InventoryAnalytics()
        self.profitability = ProfitabilityAnalytics()
        self.suppliers = SupplierAnalytics()
        self._cache = {}
        self._cache_ttl = 60  # seconds
    
    def get_dashboard_kpis(self, date_range: str = "30D", 
                           custom_start: str = None, 
                           custom_end: str = None) -> Dict[str, Any]:
        """
        Get all dashboard KPIs in one call.
        
        Args:
            date_range: One of 7D, 30D, 90D, 365D, MTD, YTD, CUSTOM
            custom_start: Start date for CUSTOM
            custom_end: End date for CUSTOM
            
        Returns:
            Dict with sales, inventory, profitability, and supplier KPIs
        """
        start, end = DateRange.get_date_bounds(date_range, custom_start, custom_end)
        
        return {
            'sales': self.sales.get_sales_kpis(start, end),
            'inventory': self.inventory.get_inventory_kpis(),
            'profitability': self.profitability.get_profitability_kpis(start, end),
            'suppliers': self.suppliers.get_supplier_kpis(),
            'date_range': {'start': start, 'end': end, 'preset': date_range}
        }
    
    def get_sales_analytics(self, date_range: str = "30D",
                            custom_start: str = None,
                            custom_end: str = None) -> Dict[str, Any]:
        """Get complete sales analytics data."""
        start, end = DateRange.get_date_bounds(date_range, custom_start, custom_end)
        
        return {
            'kpis': self.sales.get_sales_kpis(start, end),
            'trend': self.sales.get_daily_revenue_trend(start, end).to_dict('records'),
            'top_products': self.sales.get_top_products(start, end),
            'bottom_products': self.sales.get_bottom_products(start, end),
            'by_type': self.sales.get_sales_by_product_type(start, end).to_dict('records'),
            'by_brand': self.sales.get_sales_by_brand(start, end).to_dict('records'),
            'date_range': {'start': start, 'end': end}
        }
    
    def get_inventory_analytics(self) -> Dict[str, Any]:
        """Get complete inventory analytics data."""
        return {
            'kpis': self.inventory.get_inventory_kpis(),
            'low_stock': self.inventory.get_low_stock_items(),
            'by_type': self.inventory.get_stock_by_product_type().to_dict('records'),
            'by_brand': self.inventory.get_stock_by_brand().to_dict('records')
        }
    
    def get_profitability_analytics(self, date_range: str = "30D",
                                     custom_start: str = None,
                                     custom_end: str = None) -> Dict[str, Any]:
        """Get complete profitability analytics data."""
        start, end = DateRange.get_date_bounds(date_range, custom_start, custom_end)
        
        return {
            'kpis': self.profitability.get_profitability_kpis(start, end),
            'by_product': self.profitability.get_profit_by_product(start, end),
            'loss_making': self.profitability.get_loss_making_products(start, end),
            'by_category': self.profitability.get_profit_by_category(start, end).to_dict('records'),
            'date_range': {'start': start, 'end': end}
        }
    
    def get_supplier_analytics(self) -> Dict[str, Any]:
        """Get complete supplier analytics data."""
        return {
            'kpis': self.suppliers.get_supplier_kpis(),
            'performance': self.suppliers.get_supplier_performance()
        }
    
    # Employee dashboard quick stats
    def get_today_stats(self) -> Dict[str, Any]:
        """Get quick stats for employee dashboard."""
        today = datetime.now().strftime("%Y-%m-%d")
        sales_kpis = self.sales.get_sales_kpis(today, today)
        low_stock = self.inventory.get_low_stock_items(limit=5)
        top_products = self.sales.get_top_products(today, today, limit=5)
        
        return {
            'today_revenue': sales_kpis['total_revenue'],
            'today_bills': sales_kpis['bill_count'],
            'today_units': sales_kpis['total_units'],
            'low_stock_count': len(low_stock),
            'low_stock_items': low_stock,
            'top_products': top_products
        }
