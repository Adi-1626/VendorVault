"""
Database migration utilities.
Handles schema updates while preserving existing data.
"""
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
import config

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handles database migrations."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def run_migrations(self):
        """Run all necessary database migrations."""
        logger.info("Starting database migrations...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check and create invoice_sequence table
            self._create_invoice_sequence_table(cursor)
            
            # Check and create tax_settings table
            self._create_tax_settings_table(cursor)
            
            # Add new columns to bill table if they don't exist
            self._update_bill_table(cursor)
            
            # Add timestamps to tables if they don't exist
            self._add_timestamps(cursor)
            
            # Create indexes for better performance
            self._create_indexes(cursor)
            
            # Create analytics SQL views (2026 Enterprise Analytics)
            self._create_analytics_views(cursor)
            
            conn.commit()
            logger.info("Database migrations completed successfully.")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def _create_invoice_sequence_table(self, cursor):
        """Create invoice sequence table for auto-incrementing invoice numbers."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_sequence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                last_sequence INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date)
            )
        """)
        logger.info("Invoice sequence table created/verified.")
    
    def _create_tax_settings_table(self, cursor):
        """Create tax settings table for configurable tax rates."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tax_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tax_name TEXT NOT NULL UNIQUE,
                tax_rate REAL NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default tax settings if table is empty
        cursor.execute("SELECT COUNT(*) FROM tax_settings")
        if cursor.fetchone()[0] == 0:
            default_taxes = [
                ('GST_18', 18.0, 1),
                ('GST_12', 12.0, 0),
                ('GST_5', 5.0, 0),
                ('NO_TAX', 0.0, 0)
            ]
            cursor.executemany(
                "INSERT INTO tax_settings (tax_name, tax_rate, is_active) VALUES (?, ?, ?)",
                default_taxes
            )
            logger.info("Default tax settings inserted.")
    
    def _update_bill_table(self, cursor):
        """Add new columns to bill table if they don't exist."""
        # Get existing columns
        cursor.execute(f"PRAGMA table_info({config.TABLE_BILL})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add discount column if it doesn't exist
        if 'discount' not in existing_columns:
            cursor.execute(f"""
                ALTER TABLE {config.TABLE_BILL} 
                ADD COLUMN discount REAL DEFAULT 0.0
            """)
            logger.info("Added 'discount' column to bill table.")
        
        # Add tax_amount column if it doesn't exist
        if 'tax_amount' not in existing_columns:
            cursor.execute(f"""
                ALTER TABLE {config.TABLE_BILL} 
                ADD COLUMN tax_amount REAL DEFAULT 0.0
            """)
            logger.info("Added 'tax_amount' column to bill table.")
        
        # Add tax_rate column if it doesn't exist
        if 'tax_rate' not in existing_columns:
            cursor.execute(f"""
                ALTER TABLE {config.TABLE_BILL} 
                ADD COLUMN tax_rate REAL DEFAULT 18.0
            """)
            logger.info("Added 'tax_rate' column to bill table.")
        
        # Add subtotal column if it doesn't exist
        if 'subtotal' not in existing_columns:
            cursor.execute(f"""
                ALTER TABLE {config.TABLE_BILL} 
                ADD COLUMN subtotal REAL DEFAULT 0.0
            """)
            logger.info("Added 'subtotal' column to bill table.")
        
        # Add total column if it doesn't exist
        if 'total' not in existing_columns:
            cursor.execute(f"""
                ALTER TABLE {config.TABLE_BILL} 
                ADD COLUMN total REAL DEFAULT 0.0
            """)
            logger.info("Added 'total' column to bill table.")
    
    def _add_timestamps(self, cursor):
        """Add timestamp columns to tables if they don't exist."""
        tables = [config.TABLE_EMPLOYEE, config.TABLE_BILL, config.TABLE_RAW_INVENTORY]
        
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            if 'created_at' not in existing_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    """)
                    logger.info(f"Added 'created_at' to {table}.")
                except sqlite3.OperationalError:
                    pass  # Column might already exist
            
            if 'updated_at' not in existing_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    """)
                    logger.info(f"Added 'updated_at' to {table}.")
                except sqlite3.OperationalError:
                    pass
    
    def _create_indexes(self, cursor):
        """Create indexes for frequently queried columns - 2026 speed optimization."""
        indexes = [
            # Original indexes
            ("idx_bill_date", config.TABLE_BILL, "date"),
            ("idx_bill_customer", config.TABLE_BILL, "customer_name"),
            ("idx_product_name", config.TABLE_RAW_INVENTORY, "product_name"),
            ("idx_product_cat", config.TABLE_RAW_INVENTORY, "product_cat"),
        ]
        
        # 2026 Speed optimization indexes
        speed_indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_product_active ON products(is_active, product_name)",
            "CREATE INDEX IF NOT EXISTS idx_product_search ON products(product_name, product_code)",
            "CREATE INDEX IF NOT EXISTS idx_variant_sku ON product_variants(sku)",
            "CREATE INDEX IF NOT EXISTS idx_variant_default ON product_variants(product_id, is_default)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON inventory(variant_id, stock_quantity)",
            "CREATE INDEX IF NOT EXISTS idx_bill_employee ON bills(employee_id, bill_date)",
            "CREATE INDEX IF NOT EXISTS idx_brand_name ON brands(brand_name)",
        ]
        
        for index_name, table, column in indexes:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {table} ({column})
                """)
                logger.info(f"Index {index_name} created.")
            except sqlite3.OperationalError:
                pass  # Index might already exist
        
        # Create speed optimization indexes
        for sql in speed_indexes_sql:
            try:
                cursor.execute(sql)
                logger.info(f"Speed index created: {sql[:50]}...")
            except sqlite3.OperationalError as e:
                if "no such table" not in str(e).lower():
                    logger.warning(f"Could not create index: {e}")
    
    def _create_analytics_views(self, cursor):
        """Create analytics SQL views for enterprise reporting (2026)."""
        logger.info("Creating analytics SQL views...")
        
        # Read the SQL file
        sql_file = Path(__file__).parent / 'analytics_views.sql'
        
        if not sql_file.exists():
            logger.warning(f"Analytics views SQL file not found: {sql_file}")
            return
        
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            
            for statement in statements:
                # Skip comments-only statements
                if statement.startswith('--') and '\n' not in statement:
                    continue
                if not statement or statement.isspace():
                    continue
                    
                try:
                    cursor.execute(statement)
                except sqlite3.OperationalError as e:
                    # Views might already exist or table doesn't exist
                    if "already exists" not in str(e).lower():
                        logger.debug(f"View statement skipped: {e}")
            
            logger.info("Analytics SQL views created successfully.")
            
        except Exception as e:
            logger.warning(f"Could not create analytics views: {e}")


def run_migrations():
    """Run database migrations."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    migration = DatabaseMigration(config.get_database_path())
    migration.run_migrations()


if __name__ == "__main__":
    run_migrations()
