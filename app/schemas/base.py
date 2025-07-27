"""
Base Pydantic models for Costa Rica electronic document system.
Includes comprehensive validation for Costa Rican business rules.
"""
import re
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, validator, EmailStr
from .enums import IdentificationType


class IdentificationData(BaseModel):
    """Identification data with Costa Rican validation rules."""
    tipo: IdentificationType
    numero: str = Field(..., max_length=20, description="Identification number")

    @validator('numero')
    def validate_identification_number(cls, v, values):
        """Validate identification number format based on type."""
        tipo = values.get('tipo')
        
        if tipo == IdentificationType.CEDULA_FISICA:
            # Physical ID format: 1-2345-6789 or 123456789
            if not re.match(r'^\d-\d{4}-\d{4}$|^\d{9}$', v):
                raise ValueError('Invalid physical ID format. Use format: 1-2345-6789 or 123456789')
        
        elif tipo == IdentificationType.CEDULA_JURIDICA:
            # Legal ID format: 3-101-123456 or 3101123456
            if not re.match(r'^\d-\d{3}-\d{6}$|^\d{10}$', v):
                raise ValueError('Invalid legal ID format. Use format: 3-101-123456 or 3101123456')
        
        elif tipo == IdentificationType.DIMEX:
            # DIMEX format: 11-12 digits
            if not re.match(r'^\d{11,12}$', v):
                raise ValueError('Invalid DIMEX format. Must be 11-12 digits')
        
        elif tipo == IdentificationType.NITE:
            # NITE format: 10 digits
            if not re.match(r'^\d{10}$', v):
                raise ValueError('Invalid NITE format. Must be 10 digits')
        
        elif tipo == IdentificationType.EXTRANJERO_NO_DOMICILIADO:
            # Foreign non-resident: 11-12 digits
            if not re.match(r'^\d{11,12}$', v):
                raise ValueError('Invalid foreign non-resident ID format. Must be 11-12 digits')
        
        elif tipo == IdentificationType.NO_CONTRIBUYENTE:
            # Non-taxpayer: 9-12 digits
            if not re.match(r'^\d{9,12}$', v):
                raise ValueError('Invalid non-taxpayer ID format. Must be 9-12 digits')
        
        return v

    class Config:
        use_enum_values = True


class LocationData(BaseModel):
    """Costa Rican location data with geographic validation."""
    provincia: int = Field(..., ge=1, le=7, description="Province code (1-7)")
    canton: int = Field(..., ge=1, le=99, description="Canton code (1-99)")
    distrito: int = Field(..., ge=1, le=99, description="District code (1-99)")
    barrio: Optional[str] = Field(None, min_length=5, max_length=50, description="Neighborhood")
    otras_senas: str = Field(..., min_length=5, max_length=250, description="Additional address details")

    @validator('provincia')
    def validate_provincia(cls, v):
        """Validate Costa Rican province codes."""
        valid_provinces = {1, 2, 3, 4, 5, 6, 7}
        if v not in valid_provinces:
            raise ValueError(f'Invalid province code. Must be one of: {valid_provinces}')
        return v

    @validator('canton')
    def validate_canton(cls, v, values):
        """Validate canton codes based on province."""
        # Basic validation - in a real implementation, you'd check against
        # the actual canton database for each province
        if v < 1 or v > 99:
            raise ValueError('Canton code must be between 1 and 99')
        return v

    @validator('distrito')
    def validate_distrito(cls, v, values):
        """Validate district codes based on province and canton."""
        # Basic validation - in a real implementation, you'd check against
        # the actual district database for each province/canton combination
        if v < 1 or v > 99:
            raise ValueError('District code must be between 1 and 99')
        return v


class PhoneData(BaseModel):
    """Phone number data with international format."""
    codigo_pais: int = Field(..., ge=1, le=999, description="Country code (1-999)")
    numero: int = Field(..., ge=10000000, le=99999999999999999999, description="Phone number")

    @validator('numero')
    def validate_phone_number(cls, v):
        """Validate phone number length."""
        phone_str = str(v)
        if len(phone_str) < 8 or len(phone_str) > 20:
            raise ValueError('Phone number must be between 8 and 20 digits')
        return v


class EmisorData(BaseModel):
    """Issuer data with comprehensive validation."""
    nombre: str = Field(..., min_length=5, max_length=100, description="Company name")
    identificacion: IdentificationData
    nombre_comercial: Optional[str] = Field(None, min_length=3, max_length=80, description="Commercial name")
    ubicacion: LocationData
    telefono: Optional[PhoneData] = None
    correo_electronico: List[EmailStr] = Field(..., min_items=1, max_items=4, description="Email addresses")
    codigo_actividad: str = Field(..., min_length=6, max_length=6, description="Economic activity code")

    @validator('codigo_actividad')
    def validate_activity_code(cls, v):
        """Validate economic activity code format."""
        if not re.match(r'^\d{6}$', v):
            raise ValueError('Activity code must be exactly 6 digits')
        return v

    @validator('correo_electronico')
    def validate_emails(cls, v):
        """Validate email list is not empty."""
        if not v:
            raise ValueError('At least one email address is required')
        return v


class ReceptorData(BaseModel):
    """Receptor data with optional fields for different document types."""
    nombre: str = Field(..., min_length=3, max_length=100, description="Customer name")
    identificacion: Optional[IdentificationData] = None  # Optional for tickets
    nombre_comercial: Optional[str] = Field(None, min_length=3, max_length=80, description="Commercial name")
    ubicacion: Optional[LocationData] = None
    otras_senas_extranjero: Optional[str] = Field(
        None, 
        min_length=5, 
        max_length=300, 
        description="Foreign address details"
    )
    telefono: Optional[PhoneData] = None
    correo_electronico: Optional[EmailStr] = None
    codigo_actividad: Optional[str] = Field(None, min_length=6, max_length=6, description="Economic activity code")

    @validator('codigo_actividad')
    def validate_activity_code(cls, v):
        """Validate economic activity code format."""
        if v and not re.match(r'^\d{6}$', v):
            raise ValueError('Activity code must be exactly 6 digits')
        return v

    @validator('otras_senas_extranjero')
    def validate_foreign_address(cls, v, values):
        """Validate foreign address when no Costa Rican location is provided."""
        ubicacion = values.get('ubicacion')
        if not ubicacion and not v:
            # If no Costa Rican location, foreign address might be required
            # This depends on the document type and business rules
            pass
        return v


class MoneyData(BaseModel):
    """Money amount with decimal validation."""
    monto: Decimal = Field(..., max_digits=18, decimal_places=5, description="Amount")
    
    @validator('monto')
    def validate_amount(cls, v):
        """Validate amount is not negative."""
        if v < 0:
            raise ValueError('Amount cannot be negative')
        return v


class CurrencyData(BaseModel):
    """Currency information with exchange rate."""
    codigo_moneda: str = Field(default="CRC", max_length=3, description="Currency code")
    tipo_cambio: Decimal = Field(
        default=Decimal("1.0"), 
        max_digits=18, 
        decimal_places=5,
        description="Exchange rate"
    )

    @validator('codigo_moneda')
    def validate_currency_code(cls, v):
        """Validate currency code format."""
        if not re.match(r'^[A-Z]{3}$', v):
            raise ValueError('Currency code must be 3 uppercase letters (ISO 4217)')
        return v

    @validator('tipo_cambio')
    def validate_exchange_rate(cls, v):
        """Validate exchange rate is positive."""
        if v <= 0:
            raise ValueError('Exchange rate must be positive')
        return v


class ConsecutiveNumberData(BaseModel):
    """Consecutive number with format validation."""
    numero_consecutivo: str = Field(..., description="20-digit consecutive number")

    @validator('numero_consecutivo')
    def validate_consecutive_format(cls, v):
        """Validate consecutive number format (20 digits)."""
        if not re.match(r'^\d{20}$', v):
            raise ValueError('Consecutive number must be exactly 20 digits')
        return v


class DocumentKeyData(BaseModel):
    """Document key with format validation."""
    clave: str = Field(..., description="50-digit document key")

    @validator('clave')
    def validate_key_format(cls, v):
        """Validate document key format (50 digits)."""
        if not re.match(r'^\d{50}$', v):
            raise ValueError('Document key must be exactly 50 digits')
        return v


class CABYSCodeData(BaseModel):
    """CABYS code with format validation."""
    codigo_cabys: str = Field(..., description="13-digit CABYS code")

    @validator('codigo_cabys')
    def validate_cabys_format(cls, v):
        """Validate CABYS code format (13 digits)."""
        if not re.match(r'^\d{13}$', v):
            raise ValueError('CABYS code must be exactly 13 digits')
        return v


class DateTimeData(BaseModel):
    """DateTime with timezone validation."""
    fecha_emision: datetime = Field(..., description="Emission date with timezone")

    @validator('fecha_emision')
    def validate_emission_date(cls, v):
        """Validate emission date is not in the future."""
        if v > datetime.now(v.tzinfo):
            raise ValueError('Emission date cannot be in the future')
        return v


class BaseResponse(BaseModel):
    """Base response model with common fields."""
    success: bool = Field(default=True, description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


class PaginationData(BaseModel):
    """Pagination information."""
    page: int = Field(default=1, ge=1, description="Current page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")
    total: int = Field(default=0, ge=0, description="Total items")
    pages: int = Field(default=0, ge=0, description="Total pages")

    @validator('pages', always=True)
    def calculate_pages(cls, v, values):
        """Calculate total pages based on total and size."""
        total = values.get('total', 0)
        size = values.get('size', 20)
        if size > 0:
            return (total + size - 1) // size
        return 0