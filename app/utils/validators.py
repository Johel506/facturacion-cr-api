"""
Comprehensive validators for Costa Rican business rules and formats.
Includes identification numbers, CABYS codes, document keys, and more.
"""
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from app.schemas.enums import IdentificationType


class ValidationError(Exception):
    """Custom validation error with detailed information."""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class IdentificationValidator:
    """Validator for Costa Rican identification numbers."""
    
    @staticmethod
    def validate_cedula_fisica(numero: str) -> bool:
        """Validate physical ID (cédula física) format and check digit."""
        # Remove hyphens if present
        clean_numero = numero.replace('-', '')
        
        # Must be exactly 9 digits
        if not re.match(r'^\d{9}$', clean_numero):
            return False
        
        # Check digit validation using Costa Rican algorithm
        digits = [int(d) for d in clean_numero]
        multipliers = [2, 3, 4, 5, 6, 7, 8, 9]
        
        total = sum(digit * mult for digit, mult in zip(digits[:8], multipliers))
        remainder = total % 11
        
        if remainder < 2:
            check_digit = remainder
        else:
            check_digit = 11 - remainder
        
        return digits[8] == check_digit
    
    @staticmethod
    def validate_cedula_juridica(numero: str) -> bool:
        """Validate legal ID (cédula jurídica) format and check digit."""
        # Remove hyphens if present
        clean_numero = numero.replace('-', '')
        
        # Must be exactly 10 digits
        if not re.match(r'^\d{10}$', clean_numero):
            return False
        
        # Check digit validation
        digits = [int(d) for d in clean_numero]
        multipliers = [2, 3, 4, 5, 6, 7, 8, 9]
        
        total = sum(digit * mult for digit, mult in zip(digits[:8], multipliers))
        remainder = total % 11
        
        if remainder < 2:
            check_digit = remainder
        else:
            check_digit = 11 - remainder
        
        return digits[9] == check_digit
    
    @staticmethod
    def validate_dimex(numero: str) -> bool:
        """Validate DIMEX format (11-12 digits)."""
        return re.match(r'^\d{11,12}$', numero) is not None
    
    @staticmethod
    def validate_nite(numero: str) -> bool:
        """Validate NITE format (10 digits)."""
        return re.match(r'^\d{10}$', numero) is not None
    
    @staticmethod
    def validate_extranjero_no_domiciliado(numero: str) -> bool:
        """Validate foreign non-resident ID format (11-12 digits)."""
        return re.match(r'^\d{11,12}$', numero) is not None
    
    @staticmethod
    def validate_no_contribuyente(numero: str) -> bool:
        """Validate non-taxpayer ID format (9-12 digits)."""
        return re.match(r'^\d{9,12}$', numero) is not None
    
    @classmethod
    def validate_identification(cls, tipo: IdentificationType, numero: str) -> Tuple[bool, str]:
        """
        Validate identification number based on type.
        Returns (is_valid, error_message).
        """
        if not numero:
            return False, "Identification number is required"
        
        validators = {
            IdentificationType.CEDULA_FISICA: cls.validate_cedula_fisica,
            IdentificationType.CEDULA_JURIDICA: cls.validate_cedula_juridica,
            IdentificationType.DIMEX: cls.validate_dimex,
            IdentificationType.NITE: cls.validate_nite,
            IdentificationType.EXTRANJERO_NO_DOMICILIADO: cls.validate_extranjero_no_domiciliado,
            IdentificationType.NO_CONTRIBUYENTE: cls.validate_no_contribuyente,
        }
        
        validator = validators.get(tipo)
        if not validator:
            return False, f"Unknown identification type: {tipo}"
        
        if validator(numero):
            return True, ""
        else:
            return False, f"Invalid {tipo.value} format: {numero}"


class CABYSValidator:
    """Validator for CABYS codes."""
    
    @staticmethod
    def validate_format(codigo: str) -> bool:
        """Validate CABYS code format (exactly 13 digits)."""
        return re.match(r'^\d{13}$', codigo) is not None
    
    @staticmethod
    def validate_structure(codigo: str) -> Tuple[bool, str]:
        """
        Validate CABYS code structure and hierarchy.
        Returns (is_valid, error_message).
        """
        if not CABYSValidator.validate_format(codigo):
            return False, "CABYS code must be exactly 13 digits"
        
        # Extract hierarchy levels
        seccion = codigo[:2]
        division = codigo[:3]
        grupo = codigo[:4]
        clase = codigo[:6]
        subclase = codigo[:8]
        categoria = codigo[:10]
        subcategoria = codigo[:13]
        
        # Basic structure validation
        if seccion == "00":
            return False, "Invalid section code (cannot be 00)"
        
        if division[2] == "0" and grupo[3] != "0":
            return False, "Invalid hierarchy: group cannot be specified without division"
        
        return True, ""
    
    @staticmethod
    async def validate_exists_in_database(codigo: str, db_session) -> Tuple[bool, str]:
        """
        Validate CABYS code exists in database.
        This would be implemented with actual database lookup.
        """
        # Placeholder for database validation
        # In real implementation, this would query the CABYS database
        return True, ""


class ConsecutiveNumberValidator:
    """Validator for consecutive numbers (20 digits)."""
    
    @staticmethod
    def validate_format(numero: str) -> bool:
        """Validate consecutive number format (exactly 20 digits)."""
        return re.match(r'^\d{20}$', numero) is not None
    
    @staticmethod
    def validate_structure(numero: str) -> Tuple[bool, str]:
        """
        Validate consecutive number structure.
        Format: Branch(3) + Terminal(5) + DocType(2) + Sequential(10)
        """
        if not ConsecutiveNumberValidator.validate_format(numero):
            return False, "Consecutive number must be exactly 20 digits"
        
        branch = numero[:3]
        terminal = numero[3:8]
        doc_type = numero[8:10]
        sequential = numero[10:20]
        
        # Validate components
        if branch == "000":
            return False, "Branch code cannot be 000"
        
        if terminal == "00000":
            return False, "Terminal code cannot be 00000"
        
        if doc_type not in ["01", "02", "03", "04", "05", "06", "07"]:
            return False, f"Invalid document type code: {doc_type}"
        
        if sequential == "0000000000":
            return False, "Sequential number cannot be all zeros"
        
        return True, ""


class DocumentKeyValidator:
    """Validator for document keys (50 digits)."""
    
    @staticmethod
    def validate_format(clave: str) -> bool:
        """Validate document key format (exactly 50 digits)."""
        return re.match(r'^\d{50}$', clave) is not None
    
    @staticmethod
    def validate_structure(clave: str) -> Tuple[bool, str]:
        """
        Validate document key structure.
        Format: Country(3) + Day(2) + Month(2) + Year(2) + Issuer(12) + Branch(3) + Terminal(5) + DocType(2) + Sequential(10) + SecurityCode(8)
        """
        if not DocumentKeyValidator.validate_format(clave):
            return False, "Document key must be exactly 50 digits"
        
        country = clave[:3]
        day = clave[3:5]
        month = clave[5:7]
        year = clave[7:9]
        issuer = clave[9:21]
        branch = clave[21:24]
        terminal = clave[24:29]
        doc_type = clave[29:31]
        sequential = clave[31:41]
        security_code = clave[41:50]
        
        # Validate components
        if country != "506":  # Costa Rica country code
            return False, f"Invalid country code: {country} (must be 506)"
        
        if not (1 <= int(day) <= 31):
            return False, f"Invalid day: {day}"
        
        if not (1 <= int(month) <= 12):
            return False, f"Invalid month: {month}"
        
        if issuer == "000000000000":
            return False, "Issuer identification cannot be all zeros"
        
        if branch == "000":
            return False, "Branch code cannot be 000"
        
        if terminal == "00000":
            return False, "Terminal code cannot be 00000"
        
        if doc_type not in ["01", "02", "03", "04", "05", "06", "07"]:
            return False, f"Invalid document type: {doc_type}"
        
        if sequential == "0000000000":
            return False, "Sequential number cannot be all zeros"
        
        if security_code == "00000000":
            return False, "Security code cannot be all zeros"
        
        return True, ""
    
    @staticmethod
    def generate_security_code() -> str:
        """Generate 8-digit random security code."""
        import random
        return f"{random.randint(10000000, 99999999)}"


class AddressValidator:
    """Validator for Costa Rican addresses."""
    
    # Valid province codes
    VALID_PROVINCES = {1, 2, 3, 4, 5, 6, 7}
    
    # Province names for reference
    PROVINCE_NAMES = {
        1: "San José",
        2: "Alajuela", 
        3: "Cartago",
        4: "Heredia",
        5: "Guanacaste",
        6: "Puntarenas",
        7: "Limón"
    }
    
    @staticmethod
    def validate_provincia(provincia: int) -> Tuple[bool, str]:
        """Validate province code."""
        if provincia not in AddressValidator.VALID_PROVINCES:
            return False, f"Invalid province code: {provincia}. Valid codes: {sorted(AddressValidator.VALID_PROVINCES)}"
        return True, ""
    
    @staticmethod
    def validate_canton(provincia: int, canton: int) -> Tuple[bool, str]:
        """Validate canton code for given province."""
        if not (1 <= canton <= 99):
            return False, f"Canton code must be between 1 and 99, got: {canton}"
        
        # In a real implementation, this would check against the actual
        # canton database for each province
        return True, ""
    
    @staticmethod
    def validate_distrito(provincia: int, canton: int, distrito: int) -> Tuple[bool, str]:
        """Validate district code for given province and canton."""
        if not (1 <= distrito <= 99):
            return False, f"District code must be between 1 and 99, got: {distrito}"
        
        # In a real implementation, this would check against the actual
        # district database for each province/canton combination
        return True, ""


class CurrencyValidator:
    """Validator for currency codes and exchange rates."""
    
    # Common currency codes (ISO 4217)
    VALID_CURRENCIES = {
        "CRC", "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "MXN"
    }
    
    @staticmethod
    def validate_currency_code(codigo: str) -> Tuple[bool, str]:
        """Validate currency code format and common codes."""
        if not re.match(r'^[A-Z]{3}$', codigo):
            return False, "Currency code must be 3 uppercase letters"
        
        # For now, just validate format. In production, you might want to
        # validate against a comprehensive list or external service
        return True, ""
    
    @staticmethod
    def validate_exchange_rate(rate: Decimal, currency: str) -> Tuple[bool, str]:
        """Validate exchange rate value."""
        if rate <= 0:
            return False, "Exchange rate must be positive"
        
        if currency == "CRC" and rate != Decimal("1.0"):
            return False, "Exchange rate for CRC must be 1.0"
        
        # Reasonable bounds check
        if rate > Decimal("10000"):
            return False, "Exchange rate seems unreasonably high"
        
        return True, ""


class TaxCalculationValidator:
    """Validator for tax calculations."""
    
    # Standard IVA rate in Costa Rica
    STANDARD_IVA_RATE = Decimal("13.0")
    
    @staticmethod
    def validate_iva_calculation(
        base_amount: Decimal, 
        tax_rate: Decimal, 
        calculated_tax: Decimal,
        tolerance: Decimal = Decimal("0.01")
    ) -> Tuple[bool, str]:
        """Validate IVA tax calculation."""
        expected_tax = (base_amount * tax_rate / 100).quantize(Decimal('0.01'))
        
        if abs(calculated_tax - expected_tax) > tolerance:
            return False, f"Tax calculation error. Expected: {expected_tax}, got: {calculated_tax}"
        
        return True, ""
    
    @staticmethod
    def validate_tax_rate(rate: Decimal, tax_code: str) -> Tuple[bool, str]:
        """Validate tax rate for given tax code."""
        if rate < 0 or rate > 100:
            return False, f"Tax rate must be between 0 and 100, got: {rate}"
        
        # Specific validations for different tax types
        if tax_code == "01":  # IVA
            valid_iva_rates = {0, 1, 2, 4, 8, 13}
            if float(rate) not in valid_iva_rates:
                return False, f"Invalid IVA rate: {rate}. Valid rates: {valid_iva_rates}"
        
        return True, ""


class BusinessRuleValidator:
    """Validator for Costa Rican business rules."""
    
    @staticmethod
    def validate_credit_sale_requirements(
        condicion_venta: str, 
        plazo_credito: Optional[int]
    ) -> Tuple[bool, str]:
        """Validate credit sale requirements."""
        if condicion_venta == "02":  # Credit sale
            if not plazo_credito:
                return False, "Credit term (plazo_credito) is required for credit sales"
            if plazo_credito <= 0:
                return False, "Credit term must be positive"
            if plazo_credito > 365:
                return False, "Credit term cannot exceed 365 days"
        
        return True, ""
    
    @staticmethod
    def validate_exemption_requirements(
        has_exemption: bool,
        exemption_document: Optional[str],
        exemption_institution: Optional[str]
    ) -> Tuple[bool, str]:
        """Validate tax exemption requirements."""
        if has_exemption:
            if not exemption_document:
                return False, "Exemption document number is required for tax exemptions"
            if not exemption_institution:
                return False, "Exemption institution is required for tax exemptions"
        
        return True, ""
    
    @staticmethod
    def validate_document_totals(
        line_items_total: Decimal,
        tax_total: Decimal,
        discount_total: Decimal,
        other_charges_total: Decimal,
        document_total: Decimal,
        tolerance: Decimal = Decimal("0.01")
    ) -> Tuple[bool, str]:
        """Validate document total calculations."""
        expected_total = line_items_total + tax_total - discount_total + other_charges_total
        
        if abs(document_total - expected_total) > tolerance:
            return False, f"Document total mismatch. Expected: {expected_total}, got: {document_total}"
        
        return True, ""


def validate_all_business_rules(document_data: Dict[str, Any]) -> Tuple[bool, list]:
    """
    Comprehensive validation of all business rules for a document.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    
    try:
        # Validate identification numbers
        if 'emisor' in document_data and 'identificacion' in document_data['emisor']:
            emisor_id = document_data['emisor']['identificacion']
            is_valid, error = IdentificationValidator.validate_identification(
                emisor_id.get('tipo'), emisor_id.get('numero')
            )
            if not is_valid:
                errors.append(f"Emisor identification: {error}")
        
        # Validate receptor identification if present
        if 'receptor' in document_data and document_data['receptor'] and 'identificacion' in document_data['receptor']:
            receptor_id = document_data['receptor']['identificacion']
            if receptor_id:
                is_valid, error = IdentificationValidator.validate_identification(
                    receptor_id.get('tipo'), receptor_id.get('numero')
                )
                if not is_valid:
                    errors.append(f"Receptor identification: {error}")
        
        # Validate CABYS codes in line items
        if 'detalles' in document_data:
            for i, detalle in enumerate(document_data['detalles']):
                if 'codigo_cabys' in detalle:
                    is_valid, error = CABYSValidator.validate_structure(detalle['codigo_cabys'])
                    if not is_valid:
                        errors.append(f"Line {i+1} CABYS code: {error}")
        
        # Validate credit sale requirements
        is_valid, error = BusinessRuleValidator.validate_credit_sale_requirements(
            document_data.get('condicion_venta'),
            document_data.get('plazo_credito')
        )
        if not is_valid:
            errors.append(error)
        
        # Validate currency and exchange rate
        if 'codigo_moneda' in document_data:
            is_valid, error = CurrencyValidator.validate_currency_code(document_data['codigo_moneda'])
            if not is_valid:
                errors.append(f"Currency code: {error}")
        
        if 'tipo_cambio' in document_data and 'codigo_moneda' in document_data:
            is_valid, error = CurrencyValidator.validate_exchange_rate(
                Decimal(str(document_data['tipo_cambio'])),
                document_data['codigo_moneda']
            )
            if not is_valid:
                errors.append(f"Exchange rate: {error}")
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
    
    return len(errors) == 0, errors


# Convenience functions for XML service and other modules
def validate_consecutive_number(numero: str) -> bool:
    """Validate consecutive number format for XML service."""
    return ConsecutiveNumberValidator.validate_format(numero)


def validate_document_key(clave: str) -> bool:
    """Validate document key format for XML service."""
    return DocumentKeyValidator.validate_format(clave)


def validate_cedula_juridica(cedula: str) -> bool:
    """Validate legal ID format for tenant service."""
    return IdentificationValidator.validate_cedula_juridica(cedula)


def validate_email_format(email: str) -> bool:
    """Validate email format."""
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None