"""
Fixed business validators with proper email validation function
"""
import re
from typing import Tuple, List


def validate_email_format(email: str) -> bool:
    """
    Validate email format using regex pattern.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email format is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(email_pattern, email.strip()))


def validate_phone_format(phone: str, country_code: str = "506") -> bool:
    """
    Validate Costa Rican phone number format.
    
    Args:
        phone: Phone number to validate
        country_code: Country code (default: 506 for Costa Rica)
    
    Returns:
        True if phone format is valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove spaces, dashes, and parentheses
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Costa Rican phone patterns
    if country_code == "506":
        # 8-digit format: NNNN-NNNN
        if re.match(r'^\d{8}$', clean_phone):
            return True
        # With country code: +506-NNNN-NNNN or 506-NNNN-NNNN
        if re.match(r'^(\+?506)?\d{8}$', clean_phone):
            return True
    
    return False


def validate_cedula_juridica(cedula: str) -> Tuple[bool, str]:
    """
    Validate Costa Rican legal identification number (cédula jurídica).
    
    Args:
        cedula: Legal ID to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not cedula or not isinstance(cedula, str):
        return False, "Cédula jurídica is required"
    
    # Remove spaces and dashes
    clean_cedula = re.sub(r'[\s\-]', '', cedula)
    
    # Must be exactly 10 digits
    if not re.match(r'^\d{10}$', clean_cedula):
        return False, "Cédula jurídica must be exactly 10 digits"
    
    # First digit must be 3 for legal entities
    if not clean_cedula.startswith('3'):
        return False, "Cédula jurídica must start with 3"
    
    return True, ""


# Simple validation functions for immediate use
def validate_simple_business_rules(data: dict) -> Tuple[bool, List[str]]:
    """Simple validation for basic business rules"""
    errors = []
    
    # Basic required field validation
    if not data.get('nombre_empresa'):
        errors.append("Company name is required")
    
    if not data.get('cedula_juridica'):
        errors.append("Legal ID is required")
    else:
        is_valid, error = validate_cedula_juridica(data['cedula_juridica'])
        if not is_valid:
            errors.append(error)
    
    if not data.get('email_contacto'):
        errors.append("Contact email is required")
    else:
        if not validate_email_format(data['email_contacto']):
            errors.append("Invalid email format")
    
    return len(errors) == 0, errors