"""
Database fix script - Run this to fix schema issues.
"""
import sqlite3
import config

def fix_database():
    """Fix database schema issues."""
    db_path = config.get_database_path()
    print(f"Fixing database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Fix invoice_sequence table
        print("Checking invoice_sequence table...")
        cursor.execute("PRAGMA table_info(invoice_sequence)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        if 'last_sequence' not in columns:
            print("Recreating invoice_sequence table with correct schema...")
            cursor.execute("DROP TABLE IF EXISTS invoice_sequence")
            cursor.execute("""
                CREATE TABLE invoice_sequence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    last_sequence INTEGER NOT NULL DEFAULT 0
                )
            """)
            print("✓ invoice_sequence table fixed")
        else:
            print("✓ invoice_sequence table OK")
        
        # 2. Create bill_items table if missing (for quick access tracking)
        print("\nChecking bill_items table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bill_items'")
        if not cursor.fetchone():
            print("Creating bill_items table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bill_items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id INTEGER,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    total REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ bill_items table created")
        else:
            print("✓ bill_items table OK")
        
        # 3. Create pending_bills table
        print("\nChecking pending_bills table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_bills'")
        if not cursor.fetchone():
            print("Creating pending_bills table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_bills (
                    pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    customer_name TEXT,
                    customer_phone TEXT,
                    cart_items TEXT NOT NULL,
                    subtotal REAL DEFAULT 0,
                    discount REAL DEFAULT 0,
                    tax_rate REAL DEFAULT 18,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME
                )
            """)
            print("✓ pending_bills table created")
        else:
            print("✓ pending_bills table OK")
        
        # 4. Create payment_transactions table
        print("\nChecking payment_transactions table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment_transactions'")
        if not cursor.fetchone():
            print("Creating payment_transactions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id INTEGER NOT NULL,
                    payment_method TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_reference TEXT,
                    payment_status TEXT DEFAULT 'COMPLETED',
                    metadata TEXT,
                    payment_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ payment_transactions table created")
        else:
            print("✓ payment_transactions table OK")
        
        # 5. Add indexes
        print("\nAdding performance indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_product_active ON products(is_active, product_name)",
            "CREATE INDEX IF NOT EXISTS idx_product_search ON products(product_name, product_code)",
            "CREATE INDEX IF NOT EXISTS idx_variant_sku ON product_variants(sku)",
            "CREATE INDEX IF NOT EXISTS idx_variant_default ON product_variants(product_id, is_default)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON inventory(variant_id, stock_quantity)",
            "CREATE INDEX IF NOT EXISTS idx_brand_name ON brands(brand_name)",
        ]
        
        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
            except Exception as e:
                pass  # Ignore if table doesn't exist
        print("✓ Indexes added")
        
        conn.commit()
        print("\n✅ Database fix completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_database()
