"""
Tenant management models for multi-tenant Costa Rica invoice API.
Includes certificate management and subscription plans.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator, EmailStr
from .enums import TenantPlan, IdentificationType
from .base import IdentificationData


class TenantCreate(BaseModel):
    """Model for creating a new tenant."""
    nombre_empresa: str = Field(..., min_length=5, max_length=255, description="Company name")
    cedula_juridica: str = Field(..., description="Legal identification number")
    email_contacto: EmailStr = Field(..., description="Contact email address")
    plan: TenantPlan = Field(default=TenantPlan.BASICO, description="Subscription plan")

    @validator('cedula_juridica')
    def validate_legal_id(cls, v):
        """Validate legal identification format."""
        import re
        # Legal ID format: 3-101-123456 or 3101123456
        if not re.match(r'^\d-\d{3}-\d{6}$|^\d{10}$', v):
            raise ValueError('Invalid legal ID format. Use format: 3-101-123456 or 3101123456')
        return v

    class Config:
        use_enum_values = True


class TenantUpdate(BaseModel):
    """Model for updating tenant information."""
    nombre_empresa: Optional[str] = Field(None, min_length=5, max_length=255)
    email_contacto: Optional[EmailStr] = None
    plan: Optional[TenantPlan] = None
    activo: Optional[bool] = None

    class Config:
        use_enum_values = True


class CertificateUpload(BaseModel):
    """Model for uploading P12 certificate."""
    certificado_p12: bytes = Field(..., description="P12 certificate file content")
    password_certificado: str = Field(..., min_length=1, max_length=255, description="Certificate password")

    @validator('certificado_p12')
    def validate_certificate_content(cls, v):
        """Validate certificate content is not empty."""
        if not v or len(v) == 0:
            raise ValueError('Certificate content cannot be empty')
        return v


class CertificateStatus(BaseModel):
    """Certificate status information."""
    tiene_certificado: bool = Field(..., description="Whether tenant has a certificate")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Certificate expiration date")
    dias_para_vencer: Optional[int] = Field(None, description="Days until expiration")
    valido: bool = Field(default=False, description="Whether certificate is valid")
    emisor: Optional[str] = Field(None, description="Certificate issuer")
    sujeto: Optional[str] = Field(None, description="Certificate subject")
    numero_serie: Optional[str] = Field(None, description="Certificate serial number")

    @validator('dias_para_vencer', always=True)
    def calculate_days_to_expire(cls, v, values):
        """Calculate days until expiration."""
        fecha_vencimiento = values.get('fecha_vencimiento')
        if fecha_vencimiento:
            delta = fecha_vencimiento - datetime.now(fecha_vencimiento.tzinfo)
            return delta.days
        return None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TenantUsage(BaseModel):
    """Tenant usage statistics."""
    facturas_usadas_mes: int = Field(..., description="Documents used this month")
    limite_facturas_mes: int = Field(..., description="Monthly document limit")
    porcentaje_uso: float = Field(..., description="Usage percentage")
    documentos_por_tipo: dict = Field(default_factory=dict, description="Documents by type")
    ultimo_documento: Optional[datetime] = Field(None, description="Last document creation date")

    @validator('porcentaje_uso', always=True)
    def calculate_usage_percentage(cls, v, values):
        """Calculate usage percentage."""
        usado = values.get('facturas_usadas_mes', 0)
        limite = values.get('limite_facturas_mes', 1)
        if limite > 0:
            return round((usado / limite) * 100, 2)
        return 0.0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TenantResponse(BaseModel):
    """Tenant information response."""
    id: UUID
    nombre_empresa: str
    cedula_juridica: str
    email_contacto: EmailStr
    plan: TenantPlan
    activo: bool
    limite_facturas_mes: int
    facturas_usadas_mes: int
    tiene_certificado: bool
    certificado_valido: bool
    certificado_vence: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TenantDetail(BaseModel):
    """Detailed tenant information including usage statistics."""
    id: UUID
    nombre_empresa: str
    cedula_juridica: str
    email_contacto: EmailStr
    plan: TenantPlan
    activo: bool
    limite_facturas_mes: int
    facturas_usadas_mes: int
    
    # Certificate information
    certificado_status: CertificateStatus
    
    # Usage statistics
    usage: TenantUsage
    
    # Audit fields
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ApiKeyResponse(BaseModel):
    """API key information response."""
    api_key: str = Field(..., description="Generated API key")
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TenantPlanLimits(BaseModel):
    """Plan limits configuration."""
    plan: TenantPlan
    limite_facturas_mes: int
    precio_mensual: Optional[float] = None
    caracteristicas: list = Field(default_factory=list)

    class Config:
        use_enum_values = True


class TenantStats(BaseModel):
    """Tenant statistics summary."""
    total_documentos: int
    documentos_mes_actual: int
    documentos_por_estado: dict
    documentos_por_tipo: dict
    monto_total_facturado: float
    promedio_documentos_dia: float
    ultimo_documento: Optional[datetime]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }