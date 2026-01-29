"""
Database migration script - Professional Food Manufacturing Schema V2
Migrates from simple schema to professional normalized schema with variants.
"""
import sqlite3
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection."""
    db_path = Path(__file__).parent / 'data' / 'store.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def backup_database():
    """Create backup of current database."""
    import shutil
    db_path = Path(__file__).parent / 'data' / 'store.db'
    backup_path = Path(__file__).parent / 'data' / f'store_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    
    if db_path.exists():
        shutil.copy(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    return None


def create_new_tables(conn):
    """Create new professional schema tables."""
    cursor = conn.cursor()
    
    # Disable foreign keys during migration
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    # 1. Brands table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✓ Created brands table")
    
    # 2. Product Types table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_types (
            product_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT NOT NULL UNIQUE,
            description TEXT,
            hsn_code TEXT,
            display_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_type_name ON product_types(type_name)")
    logger.info("✓ Created product_types table")
    
    # 3. Products (Master Catalog)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_code ON products(product_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_name_search ON products(product_name)")
    logger.info("✓ Created products table")
    
    # 4. Product Variants
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_variants (
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_variant_sku ON product_variants(sku)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_variant_barcode ON product_variants(barcode)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_variant_product ON product_variants(product_id)")
    logger.info("✓ Created product_variants table")
    
    # 5. Inventory (by variant)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_variant ON inventory(variant_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_expiry ON inventory(expiry_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_stock ON inventory(stock_quantity)")
    logger.info("✓ Created inventory table")
    
    # 6. Suppliers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_name ON suppliers(supplier_name)")
    logger.info("✓ Created suppliers table")
    
    # 7. Product-Supplier Mapping
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_suppliers (
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
    logger.info("✓ Created product_suppliers table")
    
    conn.commit()
    logger.info("✅ All new tables created successfully!")


def populate_default_data(conn):
    """Populate default brands and product types."""
    cursor = conn.cursor()
    
    # Default brands
    brands = [
        ('Jaylaxmi', 'Jaylaxmi Food Processing Pvt. Ltd. house brand'),
        ('Third Party', 'Third party brands we distribute')
    ]
    
    for brand_name, description in brands:
        cursor.execute("""
            INSERT OR IGNORE INTO brands (brand_name, description)
            VALUES (?, ?)
        """, (brand_name, description))
    
    logger.info("✓ Inserted default brands")
    
    # Default product types for namkeen business
    product_types = [
        ('Namkeen', 'Traditional Indian savory snacks', '2106', 1),
        ('Farsan', 'Gujarati snacks and farsan varieties', '1905', 2),
        ('Chips', 'Potato and banana chips', '2005', 3),
        ('Dry Fruits', 'Nuts and dried fruits', '0801', 4),
        ('Sweets', 'Indian sweets and mithai', '1704', 5),
        ('Spices', 'Whole and ground spices', '0904', 6),
        ('Other', 'Miscellaneous food products', '2106', 99)
    ]
    
    for type_name, description, hsn_code, display_order in product_types:
        cursor.execute("""
            INSERT OR IGNORE INTO product_types (type_name, description, hsn_code, display_order)
            VALUES (?, ?, ?, ?)
        """, (type_name, description, hsn_code, display_order))
    
    logger.info("✓ Inserted default product types")
    
    conn.commit()
    logger.info("✅ Default data populated!")


def migrate_existing_products(conn):
    """Migrate existing raw_inventory data to new schema."""
    cursor = conn.cursor()
    
    # Check if old table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_inventory'")
    if not cursor.fetchone():
        logger.info("No raw_inventory table found, skipping migration")
        return
    
    # Get column names from raw_inventory
    cursor.execute("PRAGMA table_info(raw_inventory)")
    columns_info = cursor.fetchall()
    column_names = [col[1] for col in columns_info]
    logger.info(f"Raw inventory columns: {', '.join(column_names)}")
    
    # Get all existing products
    cursor.execute("SELECT * FROM raw_inventory")
    old_products = cursor.fetchall()
    
    if not old_products:
        logger.info("No existing products to migrate")
        return
    
    logger.info(f"Found {len(old_products)} products to migrate")
    
    # Get default brand ID
    cursor.execute("SELECT brand_id FROM brands WHERE brand_name = 'Jaylaxmi'")
    default_brand_id = cursor.fetchone()[0]
    
    migrated_count = 0
    
    for old_product in old_products:
        try:
            # Build dict from row using column names
            product_dict = {column_names[i]: old_product[i] for i in range(len(column_names))}
            
            # Get or create product type
            product_cat = product_dict.get('product_cat', 'Other')
            
            cursor.execute("SELECT product_type_id FROM product_types WHERE type_name = ?", (product_cat,))
            result = cursor.fetchone()
            
            if result:
                product_type_id = result[0]
            else:
                # Create new type if not found
                cursor.execute("""
                    INSERT INTO product_types (type_name, description, display_order)
                   VALUES (?, ?, 99)
                """, (product_cat, f'Migrated category: {product_cat}'))
                product_type_id = cursor.lastrowid
            
            # Generate product code
            product_id_value = product_dict.get('product_id', migrated_count + 1)
            product_code = f"JL-MIG-{product_id_value:04d}"
            
            # Create product
            cursor.execute("""
                INSERT INTO products (product_code, product_name, brand_id, product_type_id, base_unit, hsn_code)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                product_code,
                product_dict.get('product_name', 'Unknown Product'),
                default_brand_id,
                product_type_id,
                'Kg',  # Default unit
                '2106'  # Default HSN
            ))
            product_id = cursor.lastrowid
            
            # Create default variant
            sku = f"{product_code}-1KG"
            mrp_value = product_dict.get('mrp', 0.0)
            cost_price_value = product_dict.get('cost_price', None)
            
            cursor.execute("""
                INSERT INTO product_variants (
                    product_id, variant_name, sku, unit_size, mrp, cost_price, is_default
                )
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                product_id,
                '1kg Pack',
                sku,
                1.0,
                mrp_value,
                cost_price_value
            ))
            variant_id = cursor.lastrowid
            
            # Create inventory entry
            stock_value = product_dict.get('stock', 0)
            cursor.execute("""
                INSERT INTO inventory (variant_id, stock_quantity, reorder_level)
                VALUES (?, ?, 10)
            """, (variant_id, stock_value))
            
            migrated_count += 1
            logger.info(f"  ✓ Migrated: {product_dict.get('product_name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error migrating product: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    conn.commit()
    logger.info(f"✅ Migrated {migrated_count}/{len(old_products)} products successfully!")


def update_bill_table(conn):
    """Add new columns to bill table for GST and variants."""
    cursor = conn.cursor()
    
    # Check which columns already exist
    cursor.execute("PRAGMA table_info(bill)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    new_columns = {
        'bill_variants_json': 'TEXT',
        'hsn_details_json': 'TEXT',
        'cgst_amount': 'REAL DEFAULT 0',
        'sgst_amount': 'REAL DEFAULT 0',
        'igst_amount': 'REAL DEFAULT 0',
        'bill_type': "TEXT DEFAULT 'B2C'",
        'customer_gstin': 'TEXT'
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE bill ADD COLUMN {col_name} {col_type}")
                logger.info(f"✓ Added column {col_name} to bill table")
            except sqlite3.OperationalError as e:
                logger.warning(f"Column {col_name} might already exist: {e}")
    
    conn.commit()
    logger.info("✅ Bill table updated!")


def rename_old_table(conn):
    """Rename old raw_inventory table as backup."""
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_inventory'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE raw_inventory RENAME TO raw_inventory_backup")
            logger.info("✓ Renamed raw_inventory to raw_inventory_backup")
        else:
            logger.info("No raw_inventory table to rename")
    except sqlite3.OperationalError as e:
        logger.warning(f"Could not rename table: {e}")
    
    conn.commit()


def run_migration():
    """Run complete migration."""
    logger.info("=" * 60)
    logger.info("STARTING DATABASE MIGRATION TO PROFESSIONAL SCHEMA V2")
    logger.info("=" * 60)
    
    try:
        # Step 1: Backup
        logger.info("\n📦 Step 1: Creating backup...")
        backup_path = backup_database()
        
        # Step 2: Connect
        logger.info("\n🔌 Step 2: Connecting to database...")
        conn = get_db_connection()
        
        # Step 3: Create new tables
        logger.info("\n🏗️  Step 3: Creating new tables...")
        create_new_tables(conn)
        
        # Step 4: Populate defaults
        logger.info("\n📝 Step 4: Populating default data...")
        populate_default_data(conn)
        
        # Step 5: Migrate existing data
        logger.info("\n🔄 Step 5: Migrating existing products...")
        migrate_existing_products(conn)
        
        # Step 6: Update bill table
        logger.info("\n📊 Step 6: Updating bill table...")
        update_bill_table(conn)
        
        # Step 7: Rename old table
        logger.info("\n🗄️  Step 7: Archiving old table...")
        rename_old_table(conn)
        
        # Re-enable foreign keys
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        
        # Close connection
        conn.close()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"\n📁 Backup saved at: {backup_path}")
        logger.info("🎉 Your database is now using professional schema V2!")
        logger.info("\nNew tables:")
        logger.info("  • brands")
        logger.info("  • product_types")
        logger.info("  • products")
        logger.info("  • product_variants")
        logger.info("  • inventory")
        logger.info("  • suppliers")
        logger.info("  • product_suppliers")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        logger.error("Your original database is backed up and safe!")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_migration()
    if success:
        print("\n✅ You can now run the application with the new schema!")
    else:
        print("\n❌ Please check the errors above and try again")
