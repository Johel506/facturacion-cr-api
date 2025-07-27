"""
Receptor message models for Costa Rica electronic document system.
Handles acceptance, partial acceptance, and rejection messages.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator
from .enums import ReceptorMessageType, IVACondition


class ReceptorMessageCreate(BaseModel):
    """Model for creating receptor messages (acceptance/rejection)."""
    clave_documento: str = Field(..., regex=r'^\d{50}$', description="50-digit document key")
    cedula_emisor: str = Field(..., regex=r'^\d{9,12}$', description="Issuer identification (9-12 digits)")
    fecha_emision: datetime = Field(..., description="Original document emission date")
    mensaje: ReceptorMessageType = Field(..., description="Message type (1=Accepted, 2=Partial, 3=Rejected)")
    detalle_mensaje: Optional[str] = Field(None, max_length=160, description="Rejection details (required for rejection)")
    monto_total_impuesto: Optional[Decimal] = Field(
        None, 
        max_digits=18, 
        decimal_places=5,
        description="Total tax amount for validation"
    )
    codigo_actividad: Optional[str] = Field(None, max_length=6, description="Economic activity code")
    condicion_impuesto: Optional[IVACondition] = Field(None, description="IVA condition")

    @validator('clave_documento')
    def validate_document_key(cls, v):
        """Validate document key format."""
        if not v.isdigit() or len(v) != 50:
            raise ValueError('Document key must be exactly 50 digits')
        return v

    @validator('cedula_emisor')
    def validate_issuer_id(cls, v):
        """Validate issuer identification format."""
        if not v.isdigit() or len(v) < 9 or len(v) > 12:
            raise ValueError('Issuer identification must be 9-12 digits')
        return v

    @validator('detalle_mensaje')
    def validate_rejection_details(cls, v, values):
        """Validate rejection details are provided for rejection messages."""
        mensaje = values.get('mensaje')
        if mensaje == ReceptorMessageType.REJECTED and not v:
            raise ValueError('detalle_mensaje is required for rejection messages')
        if v and len(v.strip()) == 0:
            raise ValueError('detalle_mensaje cannot be empty when provided')
        return v

    @validator('codigo_actividad')
    def validate_activity_code(cls, v):
        """Validate economic activity code format."""
        if v:
            import re
            if not re.match(r'^\d{6}$', v):
                raise ValueError('Activity code must be exactly 6 digits')
        return v

    @validator('monto_total_impuesto')
    def validate_tax_amount(cls, v):
        """Validate tax amount is not negative."""
        if v is not None and v < 0:
            raise ValueError('Tax amount cannot be negative')
        return v

    @validator('fecha_emision')
    def validate_emission_date(cls, v):
        """Validate emission date is not in the future."""
        if v > datetime.now(v.tzinfo):
            raise ValueError('Emission date cannot be in the future')
        return v

    class Config:
        use_enum_values = True


class ReceptorMessageResponse(BaseModel):
    """Receptor message response information."""
    id: UUID
    clave_documento: str
    cedula_emisor: str
    fecha_emision: datetime
    mensaje: ReceptorMessageType
    detalle_mensaje: Optional[str]
    monto_total_impuesto: Optional[Decimal]
    codigo_actividad: Optional[str]
    condicion_impuesto: Optional[IVACondition]
    xml_mensaje: Optional[str] = Field(None, description="Generated XML message")
    xml_firmado: Optional[str] = Field(None, description="Signed XML message")
    enviado: bool = Field(default=False, description="Whether message was sent to Ministry")
    fecha_envio: Optional[datetime] = Field(None, description="Send date to Ministry")
    respuesta_hacienda: Optional[str] = Field(None, description="Ministry response")
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


class ReceptorMessageList(BaseModel):
    """List of receptor messages with pagination."""
    items: list[ReceptorMessageResponse]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


class ReceptorMessageFilters(BaseModel):
    """Filters for receptor message listing."""
    clave_documento: Optional[str] = Field(None, regex=r'^\d{50}$')
    cedula_emisor: Optional[str] = Field(None, regex=r'^\d{9,12}$')
    mensaje: Optional[ReceptorMessageType] = None
    enviado: Optional[bool] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None

    @validator('fecha_hasta')
    def validate_date_range(cls, v, values):
        """Validate date range is logical."""
        fecha_desde = values.get('fecha_desde')
        if fecha_desde and v and v < fecha_desde:
            raise ValueError('fecha_hasta must be greater than or equal to fecha_desde')
        return v

    class Config:
        use_enum_values = True


class ReceptorMessageStatus(BaseModel):
    """Status information for receptor message."""
    id: UUID
    enviado: bool
    fecha_envio: Optional[datetime]
    respuesta_hacienda: Optional[str]
    estado_procesamiento: str
    intentos_envio: int = Field(default=0)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReceptorMessageSummary(BaseModel):
    """Summary statistics for receptor messages."""
    total_mensajes: int
    por_tipo: dict  # Count by message type
    por_estado: dict  # Count by processing status
    enviados: int
    pendientes: int
    errores: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }