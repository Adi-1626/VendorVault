"""
Configuration module for Bill Generation System.
Manages all paths relative to project root and application constants.
"""
import os
from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).parent.absolute()

# Database configuration
DATABASE_DIR = ROOT_DIR / "data"
DATABASE_PATH = DATABASE_DIR / "store.db"

# Resources
RESOURCES_DIR = ROOT_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"

# Generated files
GENERATED_BILLS_DIR = ROOT_DIR / "generated_bills"

# Ensure directories exist
DATABASE_DIR.mkdir(exist_ok=True)
GENERATED_BILLS_DIR.mkdir(exist_ok=True)

# Application constants
APP_NAME = "Bill Generation System"
APP_VERSION = "2.0.0"
COMPANY_NAME = "JAY LAXMI"

# Tax configuration
DEFAULT_GST_RATE = 18.0  # 18% GST
TAX_RATES = {
    "GST_18": 18.0,
    "GST_12": 12.0,
    "GST_5": 5.0,
    "NO_TAX": 0.0
}

# Invoice configuration
INVOICE_PREFIX = "INV"
INVOICE_NUMBER_FORMAT = "{prefix}-{date}-{sequence:04d}"  # Example: INV-20260108-0001

# Validation patterns
PHONE_PATTERN = r"[789]\d{9}$"
AADHAR_PATTERN = r"^\d{12}$"
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# UI Configuration
WINDOW_TITLE_ADMIN = f"{APP_NAME} - Admin"
WINDOW_TITLE_EMPLOYEE = f"{APP_NAME} - Employee"
WINDOW_SIZE_DEFAULT = (1920, 1080)
WINDOW_FULLSCREEN = True  # Enable fullscreen by default

# Database tables
TABLE_EMPLOYEE = "employee"
TABLE_BILL = "bill"
TABLE_RAW_INVENTORY = "raw_inventory"
TABLE_INVOICE_SEQUENCE = "invoice_sequence"
TABLE_TAX_SETTINGS = "tax_settings"

def get_database_path():
    """Get the absolute path to the database file."""
    return str(DATABASE_PATH)

def get_generated_bills_dir():
    """Get the absolute path to generated bills directory."""
    return str(GENERATED_BILLS_DIR)
