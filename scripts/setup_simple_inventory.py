"""
Database fix and setup script for simplified inventory system.
Creates simple_products table for barcode-based inventory.
"""
import sqlite3
import config

def setup_simple_inventory():
    """Create simple_products table and fix any database issues."""
    db_path = config.get_database_path()
    print(f"Setting up database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Create simple_products table
        print("\n1. Creating simple_products table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simple_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                mrp REAL NOT NULL DEFAULT 0,
                cost_price REAL DEFAULT 0,
                stock INTEGER DEFAULT 0,
                category TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✓ simple_products table created")
        
        # 2. Create indexes
        print("\n2. Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simple_barcode ON simple_products(barcode)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simple_name ON simple_products(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_simple_active ON simple_products(is_active)")
        print("   ✓ Indexes created")
        
        # 3. Fix invoice_sequence table
        print("\n3. Checking invoice_sequence table...")
        cursor.execute("PRAGMA table_info(invoice_sequence)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'last_sequence' not in columns:
            print("   Recreating invoice_sequence table...")
            cursor.execute("DROP TABLE IF EXISTS invoice_sequence")
            cursor.execute("""
                CREATE TABLE invoice_sequence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    last_sequence INTEGER NOT NULL DEFAULT 0
                )
            """)
            print("   ✓ invoice_sequence fixed")
        else:
            print("   ✓ invoice_sequence OK")
        
        # 4. Create required tables
        print("\n4. Creating supporting tables...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bill_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total REAL NOT NULL
            )
        """)
        print("   ✓ bill_items table OK")
        
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✓ pending_bills table OK")
        
        # 5. Add sample products for testing
        print("\n5. Checking for sample products...")
        cursor.execute("SELECT COUNT(*) FROM simple_products")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("   Adding sample products...")
            sample_products = [
                ('8901234567890', 'Haldiram Aloo Bhujia 400g', 99.00, 75.00, 50, 'Namkeen'),
                ('8901234567891', 'Haldiram Sev 200g', 45.00, 35.00, 100, 'Namkeen'),
                ('8901234567892', 'Jaylaxmi Special Mix 500g', 120.00, 85.00, 75, 'Namkeen'),
                ('8901234567893', 'Parle-G Biscuit 800g', 55.00, 45.00, 200, 'Biscuits'),
                ('8901234567894', 'Britannia Good Day 250g', 40.00, 32.00, 150, 'Biscuits'),
            ]
            
            cursor.executemany("""
                INSERT INTO simple_products (barcode, name, mrp, cost_price, stock, category)
                VALUES (?, ?, ?, ?, ?, ?)
            """, sample_products)
            print(f"   ✓ Added {len(sample_products)} sample products")
        else:
            print(f"   ✓ {count} products already exist")
        
        conn.commit()
        print("\n✅ Database setup completed successfully!")
        print("\nYou can now:")
        print("  1. Run 'python main.py'")
        print("  2. Login as admin")
        print("  3. Go to 'Inventory' to add products by barcode")
        print("  4. Switch to employee mode to scan and sell products")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_simple_inventory()
