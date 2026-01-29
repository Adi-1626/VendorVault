"""
Create fresh professional database schema V2
Creates clean database with all new tables and sample data.
"""
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_fresh_database():
    """Create fresh professional database."""
    db_path = Path(__file__).parent / 'data' / 'store.db'
    
    # Ensure data directory exists
    db_path.parent.mkdir(exist_ok=True)
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    logger.info("🆕 Creating fresh professional database...")
    
    # 1. Brands
    logger.info("Creating brands table...")
    cursor.execute("""
        CREATE TABLE brands (
            brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Product Types
    logger.info("Creating product_types table...")
    cursor.execute("""
        CREATE TABLE product_types (
            product_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT NOT NULL UNIQUE,
            description TEXT,
            hsn_code TEXT,
            display_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX idx_product_type_name ON product_types(type_name)")
    
    # 3. Products
    logger.info("Creating products table...")
    cursor.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            description TEXT,
            brand_id INTEGER NOT NULL,
            product_type_id INTEGER NOT NULL,
            base_unit TEXT NOT NULL DEFAULT 'Kg',
            hsn_code TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
            FOREIGN KEY (product_type_id) REFERENCES product_types(product_type_id)
        )
    """)
    cursor.execute("CREATE INDEX idx_product_code ON products(product_code)")
    cursor.execute("CREATE INDEX idx_product_name ON products(product_name)")
    
    # 4. Product Variants
    logger.info("Creating product_variants table...")
    cursor.execute("""
        CREATE TABLE product_variants (
            variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            variant_name TEXT NOT NULL,
            sku TEXT NOT NULL UNIQUE,
            barcode TEXT UNIQUE,
            unit_size REAL NOT NULL,
            mrp REAL NOT NULL,
            cost_price REAL,
            is_default INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)
    cursor.execute("CREATE INDEX idx_variant_sku ON product_variants(sku)")
    cursor.execute("CREATE INDEX idx_variant_product ON product_variants(product_id)")
    
    # 5. Inventory
    logger.info("Creating inventory table...")
    cursor.execute("""
        CREATE TABLE inventory (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id INTEGER NOT NULL,
            warehouse_location TEXT DEFAULT 'MAIN',
            stock_quantity REAL NOT NULL DEFAULT 0,
            reorder_level REAL DEFAULT 10,
            max_stock_level REAL,
            batch_number TEXT,
            manufacturing_date TEXT,
            expiry_date TEXT,
            last_restocked_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (variant_id) REFERENCES product_variants(variant_id)
        )
    """)
    cursor.execute("CREATE INDEX idx_inventory_variant ON inventory(variant_id)")
    cursor.execute("CREATE INDEX idx_inventory_stock ON inventory(stock_quantity)")
    
    # 6. Suppliers
    logger.info("Creating suppliers table...")
    cursor.execute("""
        CREATE TABLE suppliers (
            supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            gst_number TEXT UNIQUE,
            pan_number TEXT,
            bank_details TEXT,
            is_active INTEGER DEFAULT 1,
            rating REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 7. Product-Supplier Mapping
    logger.info("Creating product_suppliers table...")
    cursor.execute("""
        CREATE TABLE product_suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            is_preferred INTEGER DEFAULT 0,
            unit_cost REAL,
            lead_time_days INTEGER,
            minimum_order_qty REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
            UNIQUE(product_id, supplier_id)
        )
    """)
    
    # 8. Employee table (preserve structure)
    logger.info("Creating employee table...")
    cursor.execute("""
        CREATE TABLE employee (
            emp_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            contact_num TEXT,
            role TEXT DEFAULT 'Employee',
            address TEXT,
            designation TEXT,
            aadhar_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 9. Bill table with new GST columns
    logger.info("Creating bill table...")
    cursor.execute("""
        CREATE TABLE bill (
            bill_no TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            customer_name TEXT,
            customer_no TEXT,
            subtotal REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            tax_rate REAL DEFAULT 18.0,
            tax_amount REAL DEFAULT 0,
            total REAL NOT NULL,
            bill_details TEXT,
            bill_variants_json TEXT,
            hsn_details_json TEXT,
            cgst_amount REAL DEFAULT 0,
            sgst_amount REAL DEFAULT 0,
            igst_amount REAL DEFAULT 0,
            bill_type TEXT DEFAULT 'B2C',
            customer_gstin TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX idx_bill_date ON bill(date)")
    cursor.execute("CREATE INDEX idx_bill_customer ON bill(customer_name)")
    
    # 10. Invoice sequence table
    logger.info("Creating invoice_sequence table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_sequence (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_invoice_number INTEGER DEFAULT 0,
            last_reset_date TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO invoice_sequence (id, last_invoice_number) VALUES (1, 0)")
    
    conn.commit()
    logger.info("✅ All tables created successfully!")
    
    # Insert default data
    logger.info("\n📝 Inserting default data...")
    
    # Brands
    cursor.executemany("""
        INSERT INTO brands (brand_name, description) VALUES (?, ?)
    """, [
        ('Jaylaxmi', 'Jaylaxmi Food Processing Pvt. Ltd.'),
        ('Third Party', 'Third party brands')
    ])
    
    # Product Types
    cursor.executemany("""
        INSERT INTO product_types (type_name, description, hsn_code, display_order)
        VALUES (?, ?, ?, ?)
    """, [
        ('Namkeen', 'Traditional Indian savory snacks', '2106', 1),
        ('Farsan', 'Gujarati snacks', '1905', 2),
        ('Chips', 'Potato and banana chips', '2005', 3),
        ('Dry Fruits', 'Nuts and dried fruits', '0801', 4),
        ('Sweets', 'Indian sweets', '1704', 5),
        ('Spices', 'Whole and ground spices', '0904', 6)
    ])
    
    # Test Employees
    import hashlib
    admin_pwd = hashlib.sha256('admin123'.encode()).hexdigest()
    emp_pwd = hashlib.sha256('emp123'.encode()).hexdigest()
    
    cursor.executemany("""
        INSERT INTO employee (emp_id, name, password, contact_num, role, designation)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        ('ADM001', 'Admin User', admin_pwd, '9876543210', 'Admin', 'Administrator'),
        ('EMP001', 'Employee User', emp_pwd, '9876543211', 'Employee', 'Cashier')
    ])
    
    # Sample Products with Variants
    logger.info("Adding sample products...")
    
    # Product 1: Shev with 3 variants
    cursor.execute("""
        INSERT INTO products (product_code, product_name, brand_id, product_type_id, base_unit, hsn_code)
        VALUES ('JL-NAM-001', 'Shev', 1, 1, 'Kg', '2106')
    """)
    shev_id = cursor.lastrowid
    
    variants_shev = [
        (shev_id, '250g Pack', 'JL-NAM-001-250G', 0.25, 50.00, 35.00, 0),
        (shev_id, '500g Pack', 'JL-NAM-001-500G', 0.50, 95.00, 65.00, 1),  # default
        (shev_id, '1kg Pack', 'JL-NAM-001-1KG', 1.00, 180.00, 125.00, 0)
    ]
    
    for v in variants_shev:
        cursor.execute("""
            INSERT INTO product_variants 
            (product_id, variant_name, sku, unit_size, mrp, cost_price, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, v)
        variant_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO inventory (variant_id, stock_quantity, reorder_level)
            VALUES (?, ?, 10)
        """, (variant_id, 50))  # Initial stock
    
    # Product 2: Aloo Bhujia
    cursor.execute("""
        INSERT INTO products (product_code, product_name, brand_id, product_type_id, base_unit, hsn_code)
        VALUES ('JL-NAM-002', 'Aloo Bhujia', 1, 1, 'Kg', '2106')
   """)
    bhujia_id = cursor.lastrowid
    
    variants_bhujia = [
        (bhujia_id, '500g Pack', 'JL-NAM-002-500G', 0.50, 90.00, 60.00, 1),
        (bhujia_id, '1kg Pack', 'JL-NAM-002-1KG', 1.00, 170.00, 115.00, 0)
    ]
    
    for v in variants_bhujia:
        cursor.execute("""
            INSERT INTO product_variants 
            (product_id, variant_name, sku, unit_size, mrp, cost_price, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, v)
        variant_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO inventory (variant_id, stock_quantity, reorder_level)
            VALUES (?, ?, 10)
        """, (variant_id, 40))
    
    # Product 3: Banana Chips
    cursor.execute("""
        INSERT INTO products (product_code, product_name, brand_id, product_type_id, base_unit, hsn_code)
        VALUES ('JL-CHI-001', 'Banana Chips', 1, 3, 'Kg', '2005')
    """)
    chips_id = cursor.lastrowid
    
    variants_chips = [
        (chips_id, '250g Pack', 'JL-CHI-001-250G', 0.25, 40.00, 28.00, 1),
        (chips_id, '500g Pack', 'JL-CHI-001-500G', 0.50, 75.00, 52.00, 0)
    ]
    
    for v in variants_chips:
        cursor.execute("""
            INSERT INTO product_variants 
            (product_id, variant_name, sku, unit_size, mrp, cost_price, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, v)
        variant_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO inventory (variant_id, stock_quantity, reorder_level)
            VALUES (?, ?, 10)
        """, (variant_id, 60))
    
    conn.commit()
    logger.info("✅ Sample data added!")
    
    conn.close()
    
    logger.info("\n" + "="*60)
    logger.info("✅ FRESH DATABASE CREATED SUCCESSFULLY!")
    logger.info("="*60)
    logger.info("\n📊 Summary:")
    logger.info("  • 2 Brands")
    logger.info("  • 6 Product Types")
    logger.info("  • 3 Sample Products")
    logger.info("  • 7 Product Variants")
    logger.info("  • 2 Test Employees (ADM001, EMP001)")
    logger.info("\n🎯 Ready to use!")
    logger.info("\n💾 Old database backed up as: data/store_old_backup.db")


if __name__ == '__main__':
    create_fresh_database()
