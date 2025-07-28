"""
Document key generation utilities for Costa Rica electronic documents.
Provides functions for generating and validating document keys and consecutive numbers.
"""
import re
import random
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from app.models.tenant import Tenant
from app.models.document import DocumentType


def generate_consecutive_number(
    branch: str = "001",
    terminal: str = "00001",
    document_type: DocumentType = DocumentType.FACTURA_ELECTRONICA,
    sequential: int = 1
) -> str:
    """
    Generate consecutive number following Costa Rican format
    
    Format: Branch(3) + Terminal(5) + DocType(2) + Sequential(10)
    Total: 20 digits
    
    Args:
        branch: Branch code (3 digits)
        terminal: Terminal/POS code (5 digits)
        document_type: Document type enum
        sequential: Sequential number (1-9999999999)
        
    Returns:
        20-digit consecutive number
        
    Raises:
        ValueError: If parameters are invalid
        
    Requirements: 10.1, 10.2 - consecutive number format
    """
    # Validate inputs
    if not re.match(r'^\d{3}$', branch):
        raise ValueError(f"Branch must be exactly 3 digits: {branch}")
    
    if not re.match(r'^\d{5}$', terminal):
        raise ValueError(f"Terminal must be exactly 5 digits: {terminal}")
    
    if not isinstance(document_type, DocumentType):
        raise ValueError(f"Invalid document type: {document_type}")
    
    if not (1 <= sequential <= 9999999999):
        raise ValueError(f"Sequential must be between 1 and 9999999999: {sequential}")
    
    # Format consecutive number
    consecutive = f"{branch}{terminal}{document_type.value}{sequential:010d}"
    
    # Validate final format
    if len(consecutive) != 20:
        raise ValueError(f"Generated consecutive number must be 20 digits: {consecutive}")
    
    return consecutive


def generate_document_key(
    tenant: Tenant,
    consecutive_number: str,
    emission_date: Optional[datetime] = None,
    security_code: Optional[str] = None
) -> str:
    """
    Generate 50-character document key following official format
    
    Format: Country(3) + Day(2) + Month(2) + Year(2) + Issuer(12) + 
            Branch(3) + Terminal(5) + DocType(2) + Sequential(10) + SecurityCode(8)
    Total: 50 digits
    
    Args:
        tenant: Tenant instance
        consecutive_number: 20-digit consecutive number
        emission_date: Document emission date (default: now)
        security_code: 8-digit security code (default: random)
        
    Returns:
        50-character document key
        
    Raises:
        ValueError: If parameters are invalid
        
    Requirements: 10.3, 10.4 - document key with all components
    """
    # Validate consecutive number
    if not re.match(r'^\d{20}$', consecutive_number):
        raise ValueError(f"Consecutive number must be exactly 20 digits: {consecutive_number}")
    
    # Use current time if not provided
    if not emission_date:
        emission_date = datetime.now(timezone.utc)
    
    # Generate security code if not provided
    if not security_code:
        security_code = generate_security_code()
    
    # Validate security code
    if not re.match(r'^\d{8}$', security_code):
        raise ValueError(f"Security code must be exactly 8 digits: {security_code}")
    
    # Build document key components
    country = "506"  # Costa Rica country code
    day = f"{emission_date.day:02d}"
    month = f"{emission_date.month:02d}"
    year = f"{emission_date.year % 100:02d}"
    
    # Format issuer identification (12 digits, left-padded with zeros)
    issuer_id = format_issuer_identification(tenant.cedula_juridica)
    
    # Assemble document key
    document_key = f"{country}{day}{month}{year}{issuer_id}{consecutive_number}{security_code}"
    
    # Validate final format
    if len(document_key) != 50:
        raise ValueError(f"Generated document key must be 50 digits: {document_key}")
    
    if not re.match(r'^\d{50}$', document_key):
        raise ValueError(f"Document key must contain only digits: {document_key}")
    
    return document_key


def generate_security_code() -> str:
    """
    Generate 8-digit security code for document uniqueness
    
    Returns:
        8-digit random security code
        
    Requirements: 10.4 - security code generation for document uniqueness
    """
    return f"{random.randint(10000000, 99999999)}"


def format_issuer_identification(cedula_juridica: str) -> str:
    """
    Format issuer identification to 12 digits
    
    Args:
        cedula_juridica: Legal identification number
        
    Returns:
        12-digit formatted identification (left-padded with zeros)
        
    Raises:
        ValueError: If identification is invalid
    """
    # Remove any formatting characters
    clean_cedula = re.sub(r'[^\d]', '', cedula_juridica)
    
    # Validate length
    if len(clean_cedula) > 12:
        raise ValueError(f"Identification number too long: {cedula_juridica}")
    
    if len(clean_cedula) < 9:
        raise ValueError(f"Identification number too short: {cedula_juridica}")
    
    # Pad with zeros to 12 digits (left-padded)
    return f"{clean_cedula:0>12}"


def parse_consecutive_number(consecutive_number: str) -> Dict[str, str]:
    """
    Parse consecutive number into its components
    
    Args:
        consecutive_number: 20-digit consecutive number
        
    Returns:
        Dictionary with components: branch, terminal, document_type, sequential
        
    Raises:
        ValueError: If format is invalid
    """
    if not re.match(r'^\d{20}$', consecutive_number):
        raise ValueError(f"Invalid consecutive number format: {consecutive_number}")
    
    return {
        "branch": consecutive_number[0:3],
        "terminal": consecutive_number[3:8],
        "document_type": consecutive_number[8:10],
        "sequential": consecutive_number[10:20]
    }


def parse_document_key(document_key: str) -> Dict[str, str]:
    """
    Parse document key into its components
    
    Args:
        document_key: 50-character document key
        
    Returns:
        Dictionary with all components
        
    Raises:
        ValueError: If format is invalid
    """
    if not re.match(r'^\d{50}$', document_key):
        raise ValueError(f"Invalid document key format: {document_key}")
    
    return {
        "country": document_key[0:3],
        "day": document_key[3:5],
        "month": document_key[5:7],
        "year": document_key[7:9],
        "issuer": document_key[9:21],
        "branch": document_key[21:24],
        "terminal": document_key[24:29],
        "document_type": document_key[29:31],
        "sequential": document_key[31:41],
        "security_code": document_key[41:49]
    }


def validate_consecutive_format(consecutive_number: str) -> bool:
    """
    Validate consecutive number format
    
    Args:
        consecutive_number: Consecutive number to validate
        
    Returns:
        True if format is valid
    """
    return bool(re.match(r'^\d{20}$', consecutive_number))


def validate_document_key_format(document_key: str) -> bool:
    """
    Validate document key format
    
    Args:
        document_key: Document key to validate
        
    Returns:
        True if format is valid
    """
    return bool(re.match(r'^\d{50}$', document_key))


def extract_date_from_key(document_key: str) -> datetime:
    """
    Extract emission date from document key
    
    Args:
        document_key: 50-character document key
        
    Returns:
        Extracted emission date
        
    Raises:
        ValueError: If key format is invalid
    """
    if not validate_document_key_format(document_key):
        raise ValueError(f"Invalid document key format: {document_key}")
    
    components = parse_document_key(document_key)
    
    # Extract date components
    day = int(components["day"])
    month = int(components["month"])
    year = 2000 + int(components["year"])  # Convert 2-digit year to 4-digit
    
    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError as e:
        raise ValueError(f"Invalid date in document key: {e}")


def extract_issuer_from_key(document_key: str) -> str:
    """
    Extract issuer identification from document key
    
    Args:
        document_key: 50-character document key
        
    Returns:
        Issuer identification (12 digits)
        
    Raises:
        ValueError: If key format is invalid
    """
    if not validate_document_key_format(document_key):
        raise ValueError(f"Invalid document key format: {document_key}")
    
    components = parse_document_key(document_key)
    return components["issuer"]


def extract_document_type_from_key(document_key: str) -> str:
    """
    Extract document type from document key
    
    Args:
        document_key: 50-character document key
        
    Returns:
        Document type code (2 digits)
        
    Raises:
        ValueError: If key format is invalid
    """
    if not validate_document_key_format(document_key):
        raise ValueError(f"Invalid document key format: {document_key}")
    
    components = parse_document_key(document_key)
    return components["document_type"]


def generate_qr_code_data(document_key: str, total_amount: float, emission_date: datetime) -> str:
    """
    Generate QR code data for document
    
    Args:
        document_key: 50-character document key
        total_amount: Document total amount
        emission_date: Document emission date
        
    Returns:
        QR code data string
    """
    # Format date as YYYY-MM-DD
    date_str = emission_date.strftime("%Y-%m-%d")
    
    # Format amount with 2 decimal places
    amount_str = f"{total_amount:.2f}"
    
    # Build QR data (simplified format)
    qr_data = f"{document_key}|{date_str}|{amount_str}"
    
    return qr_data


def validate_qr_code_data(qr_data: str) -> Dict[str, str]:
    """
    Validate and parse QR code data
    
    Args:
        qr_data: QR code data string
        
    Returns:
        Dictionary with parsed QR data
        
    Raises:
        ValueError: If QR data format is invalid
    """
    parts = qr_data.split("|")
    
    if len(parts) != 3:
        raise ValueError(f"Invalid QR code data format: {qr_data}")
    
    document_key, date_str, amount_str = parts
    
    # Validate document key
    if not validate_document_key_format(document_key):
        raise ValueError(f"Invalid document key in QR data: {document_key}")
    
    # Validate date format
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format in QR data: {date_str}")
    
    # Validate amount format
    try:
        float(amount_str)
    except ValueError:
        raise ValueError(f"Invalid amount format in QR data: {amount_str}")
    
    return {
        "document_key": document_key,
        "emission_date": date_str,
        "total_amount": amount_str
    }