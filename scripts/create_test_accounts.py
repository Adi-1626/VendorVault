"""
Create test admin and employee accounts for easy testing.
Run this once to add test credentials to the database.
"""
import sqlite3
from pathlib import Path

# Database path
db_path = Path(__file__).parent / "data" / "store.db"

# Connect to database
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# First, add the role column if it doesn't exist
try:
    cursor.execute("ALTER TABLE employee ADD COLUMN role TEXT")
    print("✓ Added 'role' column to employee table")
    conn.commit()
except sqlite3.OperationalError:
    print("✓ 'role' column already exists")

# Also add other missing columns that the new system expects
missing_columns = [
    ('first_name', 'TEXT'),
    ('last_name', 'TEXT'),
    ('email', 'TEXT'),
    ('designation', 'TEXT'),
    ('aadhar_number', 'TEXT'),
]

for col_name, col_type in missing_columns:
    try:
        cursor.execute(f"ALTER TABLE employee ADD COLUMN {col_name} {col_type}")
        print(f"✓ Added '{col_name}' column to employee table")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

# Test accounts - using existing schema columns
test_accounts = [
    ('ADM001', 'Admin User', 'admin123', '9876543210', 'Admin'),
    ('EMP001', 'Employee User', 'emp123', '9876543211', 'Employee'),
]

print("\nCreating test accounts...")

for account in test_accounts:
    emp_id, name, password, contact, role = account
    
    # Check if employee already exists
    cursor.execute("SELECT emp_id FROM employee WHERE emp_id = ?", (emp_id,))
    if cursor.fetchone():
        print(f"  ⚠️  {emp_id} already exists, skipping...")
        continue
    
    # Insert employee
    cursor.execute("""
        INSERT INTO employee (emp_id, name, password, contact_num, role, address)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (emp_id, name, password, contact, role, 'Test Address'))
    
    print(f"  ✓ Created {role}: {emp_id} (password: {password})")

conn.commit()
conn.close()

print("\n" + "="*70)
print("✅ TEST ACCOUNTS CREATED SUCCESSFULLY!")
print("="*70)
print("\n📝 LOGIN CREDENTIALS:")
print("-" * 70)
print()
print("🔐 ADMIN LOGIN:")
print("   Employee ID: ADM001")
print("   Password   : admin123")
print("   Role       : Admin")
print()
print("-" * 70)
print()
print("👤 EMPLOYEE LOGIN:")
print("   Employee ID: EMP001")
print("   Password   : emp123")
print("   Role       : Employee")
print()
print("-" * 70)
print("\n💡 TIP: Use these credentials in the login screen")
print("   Select the appropriate role (Admin/Employee) before logging in")
print("="*70)
