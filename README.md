# Bill Generation System

A modern, professional Python desktop application for retail bill generation and inventory management.

## Features

### 🛒 Billing & POS
- Real-time shopping cart with item management
- Automatic invoice number generation (INV-YYYYMMDD-XXXX format)
- GST/tax calculation support (configurable rates)
- Discount support (fixed amount)
- Professional PDF invoice generation
- Search and view previous bills

### 📦 Inventory Management
- Product CRUD operations with categories and subcategories
- Real-time stock tracking
- Low stock alerts
- Search and filter products
- Stock level color coding

### 👥 Employee Management
- Role-based access control (Admin/Employee)
- Secure password authentication
- Employee CRUD operations
- Auto-generated employee IDs

### 📊 Analytics & Reports
- Best-selling products (Day/Month/Year)
- Profit analysis by product
- Revenue tracking
- Interactive matplotlib charts

## Technology Stack

- **Framework**: PySide6 (Qt for Python)
- **Database**: SQLite
- **PDF Generation**: ReportLab
- **Analytics**: Matplotlib, Pandas
- **Architecture**: MVC pattern with clean separation of concerns

## Project Structure

```
BILL_GENERATION_SYSTEM/
├── main.py                    # Application entry point
├── config.py                  # Configuration and constants
├── requirements.txt           # Python dependencies
│
├── src/
│   ├──models/                 # Data models
│   ├── database/              # Database layer
│   ├── logic/                 # Business logic
│   ├── ui/                    # PySide6 UI components
│   └── utils/                 # Utility functions
│
├── data/                      # Database storage
└── generated_bills/           # Generated PDF invoices
```

## Installation

### Prerequisites
- Python 3.9 or higher
- Windows operating system

### Steps

1. **Clone or extract the project**:
   ```bash
   cd C:\Users\adity\Downloads\BILL_GENERATION_SYSTEM
   ```

2. **Create and activate virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migration** (first time only):
   ```bash
   python -m src.database.migrations
   ```

## Running the Application

1. **Activate virtual environment** (if using):
   ```bash
   venv\Scripts\activate
   ```

2. **Run the application**:
   ```bash
   python main.py
   ```

## Default Credentials

The application uses the existing employee data from your database. Login with any valid employee credentials:

- **Admin users**:
  Id - ADM001
  Password -admin123
  Will see the Admin Dashboard
- **Regular employees**:
  Id - EMP001
  Password -emp123
  Will see the Billing System

To view existing users, check the `employee` table in `data/store.db`.

## Usage Guide

### For Employees (Billing)

1. **Login** with your employee credentials
2. **Enter customer information** (name and phone number)
3. **Select products**:
   - Choose Category → Subcategory → Product
   - Set quantity
   - Click "Add to Cart"
4. **Apply discounts and tax** (if needed)
5. **Generate bill**:
   - Click "Generate Bill" to save and create PDF
   - PDF is saved in `generated_bills/` folder

### For Administrators

1. **Login** as Admin
2. **Dashboard**: View quick statistics
   - Total products
   - Total employees
   - Today's bills and revenue
3. **Manage Inventory**:
   - Add/Edit/Delete products
   - Monitor stock levels
   - Search products
4. **Manage Employees**:
   - Add/Edit/Delete employees
   - Assign roles
   - Manage credentials
5. **View Invoices**:
   - Search bills by number or customer
   - View bill details
   - Generate PDFs for past bills
6. **Analytics**:
   - View best-selling products
   - Analyze profit by product
   - Track sales trends

## Key Features Explained

### Auto-Generated Invoice Numbers
Format: `INV-20260108-0001`
- Resets daily
- Auto-increments for each bill

### Tax Calculation
- Default: 18% GST
- Configurable in settings
- Applied on (Subtotal - Discount)

### Discount System
- Fixed amount discount
- Applied before tax calculation
- Visible in bill breakdown

### PDF Invoices
- Professional layout with company branding
- Itemized bill with quantities and prices
- Subtotal, discount, tax, and total clearly shown
- Saved in `generated_bills/` directory

## Building Standalone Executable

To create a standalone Windows executable:

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Create executable**:
   ```bash
   pyinstaller --name="BillGenerationSystem" ^
               --onefile ^
               --windowed ^
               --add-data="src;src" ^
               --add-data="data;data" ^
               main.py
   ```

3. **Executable will be in**: `dist/BillGenerationSystem.exe`

## Configuration

Edit `config.py` to customize:
- Company name
- Default tax rates
- Invoice number format
- Validation patterns
- Window sizes

## Database

The application uses SQLite database located at `data/store.db`.

**Tables**:
- `employee` - Employee credentials and information
- `bill` - Generated bills and invoices
- `raw_inventory` - Product inventory
- `invoice_sequence` - Invoice number tracking
- `tax_settings` - Tax configuration

**Backup**: Regularly backup `data/store.db` to prevent data loss.

## Troubleshooting

### Database Errors
- Ensure `data/` directory exists
- Check file permissions
- Run migrations: `python -m src.database.migrations`

### Import Errors
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Use virtual environment to avoid conflicts

### UI Not Loading
- Check stylesheet file exists: `src/ui/styles/default.qss`
- Verify PySide6 is installed correctly

### PDF Generation Fails
- Ensure `generated_bills/` directory is writable
- Check ReportLab is installed

## Support

For issues or questions:
1. Check the logs in `analytics.log` and `failure.log`
2. Verify database integrity
3. Ensure all dependencies are up to date

## Version

**Version**: 2.0.0  
**Release Date**: January 2026  
**Python Version**: 3.9+  
**Platform**: Windows

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

**Built by [Adi-1626](https://github.com/Adi-1626)** | *Originally developed for JAY LAXMI — customize company details in `config.py` for your business*

