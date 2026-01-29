"""
Input validation utilities.
"""
import re
from typing import Tuple
import config


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    Validate Indian phone number.
    
    Args:
        phone: Phone number string
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    phone = phone.strip()
    if not re.match(config.PHONE_PATTERN, phone):
        return False, "Phone number must be 10 digits starting with 7, 8, or 9"
    
    return True, ""


def validate_aadhar(aadhar: str) -> Tuple[bool, str]:
    """
    Validate Aadhar number.
    
    Args:
        aadhar: Aadhar number string
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not aadhar:
        return False, "Aadhar number is required"
    
    aadhar = aadhar.strip()
    if not re.match(config.AADHAR_PATTERN, aadhar):
        return False, "Aadhar number must be exactly 12 digits"
    
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address.
    
    Args:
        email: Email address string
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return True, ""  # Email is optional
    
    email = email.strip()
    if not re.match(config.EMAIL_PATTERN, email):
        return False, "Invalid email address format"
    
    return True, ""


def validate_required(value: str, field_name: str) -> Tuple[bool, str]:
    """
    Validate that a field is not empty.
    
    Args:
        value: Field value
        field_name: Name of the field for error message
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, f"{field_name} is required"
    
    return True, ""


def validate_numeric(value: str, field_name: str, min_val: float = None, max_val: float = None) -> Tuple[bool, str]:
    """
    Validate numeric input.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error message
        min_val: Minimum allowed value (optional)
        max_val: Maximum allowed value (optional)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return False, f"{field_name} is required"
    
    try:
        num = float(value)
        
        if min_val is not None and num < min_val:
            return False, f"{field_name} must be at least {min_val}"
        
        if max_val is not None and num > max_val:
            return False, f"{field_name} must not exceed {max_val}"
        
        return True, ""
    except ValueError:
        return False, f"{field_name} must be a valid number"


def validate_integer(value: str, field_name: str, min_val: int = None, max_val: int = None) -> Tuple[bool, str]:
    """
    Validate integer input.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error message
        min_val: Minimum allowed value (optional)
        max_val: Maximum allowed value (optional)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return False, f"{field_name} is required"
    
    try:
        num = int(value)
        
        if min_val is not None and num < min_val:
            return False, f"{field_name} must be at least {min_val}"
        
        if max_val is not None and num > max_val:
            return False, f"{field_name} must not exceed {max_val}"
        
        return True, ""
    except ValueError:
        return False, f"{field_name} must be a valid integer"
