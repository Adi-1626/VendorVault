"""
Employee data model.
"""
from dataclasses import dataclass
from typing import Optional
import hashlib


@dataclass
class Employee:
    """Employee model representing an employee in the system."""
    
    emp_id: str
    first_name: str
    last_name: str
    password: str
    role: str  # 'Admin' or 'Employee'
    contact_number: str
    email: Optional[str] = None
    address: Optional[str] = None
    designation: Optional[str] = None
    aadhar_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def get_full_name(self) -> str:
        """Get employee's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def is_admin(self) -> bool:
        """Check if employee has admin role."""
        return self.role.lower() == 'admin'
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password for storage.
        
        Args:
            password: Plain text password
        
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
        
        Returns:
            bool: True if password matches
        """
        # For backward compatibility, check both hashed and plain text
        hashed = self.hash_password(password)
        return self.password == hashed or self.password == password
    
    @classmethod
    def from_db_row(cls, row) -> 'Employee':
        """Create Employee instance from database row."""
        # Handle both old schema (name, contact_num) and new schema (first_name, last_name, contact_number)
        
        # Get name - try new schema first, fallback to old
        if 'first_name' in row.keys():
            first_name = row['first_name'] or ''
            last_name = row['last_name'] or ''
        elif 'name' in row.keys():
            # Old schema - split name into first and last
            full_name = row['name'] or ''
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
        else:
            first_name = ''
            last_name = ''
        
        # Get contact - try new schema first, fallback to old
        contact_number = ''
        if 'contact_number' in row.keys():
            contact_number = row['contact_number'] or ''
        elif 'contact_num' in row.keys():
            contact_number = row['contact_num'] or ''
        
        # Get aadhar - handle different column names
        aadhar_number = None
        if 'aadhar_number' in row.keys():
            aadhar_number = row['aadhar_number']
        elif 'aadhar_num' in row.keys():
            aadhar_number = row['aadhar_num']
        
        return cls(
            emp_id=row['emp_id'],
            first_name=first_name,
            last_name=last_name,
            password=row['password'],
            role=row['role'] if 'role' in row.keys() else 'Employee',
            contact_number=contact_number,
            email=row['email'] if 'email' in row.keys() else None,
            address=row['address'] if 'address' in row.keys() else None,
            designation=row['designation'] if 'designation' in row.keys() else None,
            aadhar_number=aadhar_number,
            created_at=row['created_at'] if 'created_at' in row.keys() else None,
            updated_at=row['updated_at'] if 'updated_at' in row.keys() else None
        )
    
    def to_dict(self) -> dict:
        """Convert employee to dictionary."""
        return {
            'emp_id': self.emp_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'password': self.password,
            'role': self.role,
            'contact_number': self.contact_number,
            'email': self.email,
            'address': self.address,
            'designation': self.designation,
            'aadhar_number': self.aadhar_number,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
