"""
Smart Search Module for simple barcode-based products.
Provides fast product search with caching.
"""
from typing import List, Dict
from src.database.connection import DatabaseConnection
import time
from difflib import SequenceMatcher


class SmartSearch:
    """Fast product search using simple_products table."""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self._cache: List[Dict] = []
        self._cache_time: float = 0
        self._cache_ttl: int = 60  # 1 minute cache
    
    def _load_cache(self, force: bool = False):
        """Load products into cache."""
        now = time.time()
        if not force and self._cache and (now - self._cache_time) < self._cache_ttl:
            return
        
        query = """
            SELECT id, barcode, name as product_name, mrp, cost_price, stock, category
            FROM simple_products
            WHERE is_active = 1
            ORDER BY name
        """
        
        results = self.db.execute_query(query)
        
        self._cache = []
        for row in results:
            self._cache.append({
                'product_id': row['id'],
                'barcode': row['barcode'] or '',
                'product_name': row['product_name'],
                'mrp': row['mrp'] or 0.0,
                'cost_price': row.get('cost_price', 0.0) or 0.0,
                'stock': row['stock'] or 0,
                'category': row.get('category', ''),
                'search_text': f"{row['product_name']} {row['barcode']} {row.get('category', '')}".lower()
            })
        
        self._cache_time = now
    
    def _match_score(self, query: str, text: str) -> float:
        """Calculate match score."""
        query = query.lower()
        text = text.lower()
        
        if query == text:
            return 1.0
        if text.startswith(query):
            return 0.95
        if query in text:
            return 0.8
        
        return SequenceMatcher(None, query, text).ratio()
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search products with fuzzy matching."""
        if not query or not query.strip():
            return []
        
        query = query.strip().lower()
        self._load_cache()
        
        results = []
        for product in self._cache:
            score = max(
                self._match_score(query, product['product_name']),
                self._match_score(query, product['barcode']),
                self._match_score(query, product.get('category', '')) * 0.5
            )
            
            if score >= 0.3:
                # Boost in-stock items
                if product['stock'] > 0:
                    score *= 1.1
                else:
                    score *= 0.5
                
                results.append({**product, 'score': score})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def search_instant(self, query: str, limit: int = 5) -> List[Dict]:
        """Fast search for autocomplete."""
        if not query:
            return []
        
        query = query.strip().lower()
        self._load_cache()
        
        results = []
        
        # First: exact barcode match
        for p in self._cache:
            if p['barcode'].lower() == query:
                return [p]  # Exact barcode match, return immediately
        
        # Second: prefix matches
        for p in self._cache:
            if (p['product_name'].lower().startswith(query) or
                p['barcode'].lower().startswith(query)):
                results.append(p)
                if len(results) >= limit:
                    break
        
        # Third: contains matches
        if len(results) < limit:
            for p in self._cache:
                if p not in results and query in p['search_text']:
                    results.append(p)
                    if len(results) >= limit:
                        break
        
        # Sort: in-stock first, then by name
        results.sort(key=lambda x: (0 if x['stock'] > 0 else 1, x['product_name']))
        
        return results[:limit]
    
    def search_by_barcode(self, barcode: str) -> Dict:
        """Find product by exact barcode."""
        self._load_cache()
        
        for p in self._cache:
            if p['barcode'] == barcode:
                return p
        
        # Fallback to DB if not in cache
        query = "SELECT * FROM simple_products WHERE barcode = ? AND is_active = 1"
        results = self.db.execute_query(query, (barcode,))
        
        if results:
            row = results[0]
            return {
                'product_id': row['id'],
                'barcode': row['barcode'],
                'product_name': row['name'],
                'mrp': row['mrp'] or 0.0,
                'cost_price': row.get('cost_price', 0.0) or 0.0,
                'stock': row['stock'] or 0,
                'category': row.get('category', '')
            }
        
        return None
    
    def refresh_cache(self):
        """Force refresh cache."""
        self._load_cache(force=True)
    
    def get_all_products(self) -> List[Dict]:
        """Get all products."""
        self._load_cache()
        return self._cache.copy()


class QuickAccessManager:
    """Manages quick access/popular products."""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def get_top_products(self, limit: int = 20) -> List[Dict]:
        """Get all products sorted by stock."""
        query = """
            SELECT id as product_id, barcode, name as product_name, mrp, stock, category
            FROM simple_products
            WHERE is_active = 1 AND stock > 0
            ORDER BY stock DESC, name
            LIMIT ?
        """
        
        try:
            results = self.db.execute_query(query, (limit,))
            return [{
                'product_id': r['product_id'],
                'barcode': r['barcode'],
                'product_name': r['product_name'],
                'mrp': r['mrp'] or 0.0,
                'stock': r['stock'] or 0,
                'category': r.get('category', '')
            } for r in results]
        except Exception as e:
            print(f"Error loading top products: {e}")
            return []
    
    def get_quick_access_products(self, employee_id: int = None, limit: int = 12) -> List[Dict]:
        """Get quick access products."""
        return self.get_top_products(limit)
