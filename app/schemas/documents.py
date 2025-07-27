"""
Document and reference models for Costa Rica electronic documents.
Supports all 7 document types with comprehensive validation.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator
from .enums import (
    DocumentType, SaleCondition, PaymentMethod, DocumentReferenceType, 
    ReferenceCode, OtherChargeType, DocumentStatus
)
from .base import EmisorData, ReceptorData, CurrencyData, IdentificationData, PaginationData
from .document_items import DocumentLineItem, LineItemSummary


class DocumentReference(BaseModel):
    """Document reference for credit/debit note relationships."""
    tipo_documento: DocumentReferenceType
    tipo_documento_otro: Optional[str] = Field(None, min_length=5, max_length=100)
    numero: Optional[str] = Field(None, max_length=50, description="Referenced document key or consecutive")
    fecha_emision: datetime = Field(..., description="Referenced document emission date")
    codigo: Optional[ReferenceCode] = None
    codigo_referencia_otro: Optional[str] = Field(None, min_length=5, max_length=100)
    razon: Optional[str] = Field(None, max_length=180, description="Reference reason")

    @validator('tipo_documento_otro')
    def validate_other_document_type(cls, v, values):
        """Validate other document type when tipo_documento is OTHERS."""
        tipo = values.get('tipo_documento')
        if tipo == DocumentReferenceType.OTHERS and not v:
            raise ValueError('tipo_documento_otro is required when tipo_documento is OTHERS')
        return v

    @validator('codigo_referencia_otro')
    def validate_other_reference_code(cls, v, values):
        """Validate other reference code when codigo is OTHERS."""
        codigo = values.get('codigo')
        if codigo == ReferenceCode.OTHERS and not v:
            raise ValueError('codigo_referencia_otro is required when codigo is OTHERS')
        return v

    @validator('fecha_emision')
    def validate_reference_date(cls, v):
        """Validate reference date is not in the future."""
        if v > datetime.now(v.tzinfo):
            raise ValueError('Reference emission date cannot be in the future')
        return v

    class Config:
        use_enum_values = True


class OtherCharge(BaseModel):
    """Other charges for stamps and additional fees."""
    tipo_documento: OtherChargeType
    tipo_documento_otros: Optional[str] = Field(None, min_length=5, max_length=100)
    
    # Third party information (optional)
    tercero_identificacion: Optional[IdentificationData] = None
    tercero_nombre: Optional[str] = Field(None, min_length=5, max_length=100)
    
    detalle: str = Field(..., max_length=160, description="Charge description")
    porcentaje: Optional[Decimal] = Field(
        None, 
        max_digits=9, 
        decimal_places=5, 
        ge=0,
        description="Percentage for calculation"
    )
    monto_cargo: Decimal = Field(..., max_digits=18, decimal_places=5, description="Charge amount")

    @validator('tipo_documento_otros')
    def validate_other_document_type(cls, v, values):
        """Validate other document type when tipo_documento is OTHERS."""
        tipo = values.get('tipo_documento')
        if tipo == OtherChargeType.OTHERS and not v:
            raise ValueError('tipo_documento_otros is required when tipo_documento is OTHERS')
        return v

    @validator('monto_cargo')
    def validate_charge_amount(cls, v):
        """Validate charge amount is not negative."""
        if v < 0:
            raise ValueError('Charge amount cannot be negative')
        return v

    @validator('porcentaje')
    def validate_percentage(cls, v):
        """Validate percentage is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Percentage must be between 0 and 100')
        return v

    class Config:
        use_enum_values = True


class DocumentCreate(BaseModel):
    """Main document creation model supporting all 7 document types."""
    tipo_documento: DocumentType
    emisor: EmisorData
    receptor: Optional[ReceptorData] = None  # Optional for some document types like tickets
    condicion_venta: SaleCondition
    condicion_venta_otros: Optional[str] = Field(None, min_length=5, max_length=100)
    plazo_credito: Optional[int] = Field(None, le=99999, description="Credit term in days")
    medio_pago: PaymentMethod
    medio_pago_otros: Optional[str] = Field(None, min_length=3, max_length=100)
    
    # Currency information
    codigo_moneda: str = Field(default="CRC", max_length=3, description="Currency code")
    tipo_cambio: Decimal = Field(
        default=Decimal("1.0"), 
        max_digits=18, 
        decimal_places=5,
        description="Exchange rate"
    )
    
    # Line items
    detalles: List[DocumentLineItem] = Field(..., min_items=1, max_items=1000)
    
    # References (required for credit/debit notes)
    referencias: Optional[List[DocumentReference]] = Field(None, max_items=10)
    
    # Other charges
    otros_cargos: Optional[List[OtherCharge]] = None
    
    # Additional fields
    observaciones: Optional[str] = Field(None, max_length=500, description="Additional observations")

    @validator('condicion_venta_otros')
    def validate_other_sale_condition(cls, v, values):
        """Validate other sale condition when condicion_venta is OTHERS."""
        condicion = values.get('condicion_venta')
        if condicion == SaleCondition.OTROS and not v:
            raise ValueError('condicion_venta_otros is required when condicion_venta is OTHERS')
        return v

    @validator('plazo_credito')
    def validate_credit_term(cls, v, values):
        """Validate credit term is required for credit sales."""
        condicion = values.get('condicion_venta')
        if condicion == SaleCondition.CREDITO and not v:
            raise ValueError('plazo_credito is required for credit sales')
        if v is not None and v <= 0:
            raise ValueError('Credit term must be positive')
        return v

    @validator('medio_pago_otros')
    def validate_other_payment_method(cls, v, values):
        """Validate other payment method when medio_pago is OTHERS."""
        medio = values.get('medio_pago')
        if medio == PaymentMethod.OTROS and not v:
            raise ValueError('medio_pago_otros is required when medio_pago is OTHERS')
        return v

    @validator('receptor')
    def validate_receptor_required(cls, v, values):
        """Validate receptor is required for certain document types."""
        tipo_documento = values.get('tipo_documento')
        
        # Receptor is optional only for tickets (TiqueteElectronico)
        if tipo_documento != DocumentType.TIQUETE_ELECTRONICO and not v:
            raise ValueError(f'Receptor is required for document type {tipo_documento}')
        
        return v

    @validator('referencias')
    def validate_references_required(cls, v, values):
        """Validate references are required for credit/debit notes."""
        tipo_documento = values.get('tipo_documento')
        
        if tipo_documento in [DocumentType.NOTA_CREDITO_ELECTRONICA, DocumentType.NOTA_DEBITO_ELECTRONICA]:
            if not v or len(v) == 0:
                raise ValueError('References are required for credit and debit notes')
        
        return v

    @validator('detalles')
    def validate_line_numbers_unique(cls, v):
        """Validate line numbers are unique and sequential."""
        if not v:
            raise ValueError('At least one line item is required')
        
        line_numbers = [item.numero_linea for item in v]
        if len(line_numbers) != len(set(line_numbers)):
            raise ValueError('Line numbers must be unique')
        
        # Check if line numbers are sequential starting from 1
        expected_numbers = list(range(1, len(v) + 1))
        if sorted(line_numbers) != expected_numbers:
            raise ValueError('Line numbers must be sequential starting from 1')
        
        return v

    @validator('codigo_moneda')
    def validate_currency_code(cls, v):
        """Validate currency code format."""
        import re
        if not re.match(r'^[A-Z]{3}$', v):
            raise ValueError('Currency code must be 3 uppercase letters (ISO 4217)')
        return v

    @validator('tipo_cambio')
    def validate_exchange_rate(cls, v):
        """Validate exchange rate is positive."""
        if v <= 0:
            raise ValueError('Exchange rate must be positive')
        return v

    class Config:
        use_enum_values = True


class DocumentResponse(BaseModel):
    """Document response model with essential information."""
    id: UUID
    tipo_documento: DocumentType
    numero_consecutivo: str = Field(..., description="20-digit consecutive number")
    clave: str = Field(..., description="50-digit document key")
    fecha_emision: datetime
    emisor_nombre: str
    emisor_identificacion: str
    receptor_nombre: Optional[str]
    receptor_identificacion: Optional[str]
    estado: DocumentStatus
    total_venta_neta: Decimal = Field(..., description="Net sale total")
    total_impuesto: Decimal = Field(..., description="Total tax amount")
    total_comprobante: Decimal = Field(..., description="Total document amount")
    codigo_moneda: str
    tipo_cambio: Decimal
    xml_url: Optional[str] = Field(None, description="URL to download XML")
    pdf_url: Optional[str] = Field(None, description="URL to download PDF")
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


class DocumentDetail(BaseModel):
    """Detailed document information including line items."""
    id: UUID
    tipo_documento: DocumentType
    numero_consecutivo: str
    clave: str
    fecha_emision: datetime
    
    # Emisor information
    emisor: EmisorData
    
    # Receptor information
    receptor: Optional[ReceptorData]
    
    # Transaction details
    condicion_venta: SaleCondition
    condicion_venta_otros: Optional[str]
    plazo_credito: Optional[int]
    medio_pago: PaymentMethod
    medio_pago_otros: Optional[str]
    
    # Currency and totals
    codigo_moneda: str
    tipo_cambio: Decimal
    total_venta_neta: Decimal
    total_impuesto: Decimal
    total_comprobante: Decimal
    
    # Line items
    detalles: List[LineItemSummary]
    
    # References and charges
    referencias: Optional[List[DocumentReference]]
    otros_cargos: Optional[List[OtherCharge]]
    
    # Processing information
    estado: DocumentStatus
    mensaje_hacienda: Optional[str]
    fecha_procesamiento: Optional[datetime]
    intentos_envio: int
    
    # Additional fields
    observaciones: Optional[str]
    xml_url: Optional[str]
    pdf_url: Optional[str]
    
    # Audit fields
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


class DocumentList(BaseModel):
    """Paginated list of documents."""
    items: List[DocumentResponse]
    pagination: PaginationData

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


class DocumentFilters(BaseModel):
    """Filters for document listing and search."""
    tipo_documento: Optional[DocumentType] = None
    estado: Optional[DocumentStatus] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    emisor_identificacion: Optional[str] = None
    receptor_identificacion: Optional[str] = None
    monto_minimo: Optional[Decimal] = None
    monto_maximo: Optional[Decimal] = None
    numero_consecutivo: Optional[str] = None
    clave: Optional[str] = None

    @validator('fecha_hasta')
    def validate_date_range(cls, v, values):
        """Validate date range is logical."""
        fecha_desde = values.get('fecha_desde')
        if fecha_desde and v and v < fecha_desde:
            raise ValueError('fecha_hasta must be greater than or equal to fecha_desde')
        return v

    @validator('monto_maximo')
    def validate_amount_range(cls, v, values):
        """Validate amount range is logical."""
        monto_minimo = values.get('monto_minimo')
        if monto_minimo and v and v < monto_minimo:
            raise ValueError('monto_maximo must be greater than or equal to monto_minimo')
        return v

    @validator('numero_consecutivo')
    def validate_consecutive_format(cls, v):
        """Validate consecutive number format if provided."""
        if v:
            import re
            if not re.match(r'^\d{20}$', v):
                raise ValueError('Consecutive number must be exactly 20 digits')
        return v

    @validator('clave')
    def validate_key_format(cls, v):
        """Validate document key format if provided."""
        if v:
            import re
            if not re.match(r'^\d{50}$', v):
                raise ValueError('Document key must be exactly 50 digits')
        return v

    class Config:
        use_enum_values = True


class DocumentStatusUpdate(BaseModel):
    """Model for updating document status."""
    estado: DocumentStatus
    mensaje_hacienda: Optional[str] = None
    xml_respuesta_hacienda: Optional[str] = None

    class Config:
        use_enum_values = True


class DocumentSummary(BaseModel):
    """Summary statistics for documents."""
    total_documentos: int
    por_tipo: dict
    por_estado: dict
    total_monto: Decimal
    periodo: str

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }