"""
Tenant model for multi-tenant architecture with certificate storage and plan limits
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, LargeBinary,
    CheckConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    """
    Tenant model for multi-tenant SaaS architecture
    
    Supports multiple clients with isolated data and configurations,
    encrypted certificate storage, and usage tracking with plan limits.
    
    Requirements: 1.1, 1.2, 1.4, 1.5
    """
    __tablename__ = "tenants"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Business information (Requirement 1.1)
    nombre_empresa = Column(String(255), nullable=False, comment="Company legal name")
    cedula_juridica = Column(String(20), nullable=False, unique=True, index=True, 
                           comment="Costa Rican legal identification number")
    nombre_comercial = Column(String(255), nullable=True, comment="Commercial/trade name")
    email_contacto = Column(String(255), nullable=False, comment="Primary contact email")
    telefono_contacto = Column(String(20), nullable=True, comment="Primary contact phone")
    
    # Address information
    direccion = Column(Text, nullable=True, comment="Complete business address")
    provincia = Column(Integer, nullable=True, comment="Province code (1-7)")
    canton = Column(Integer, nullable=True, comment="Canton code")
    distrito = Column(Integer, nullable=True, comment="District code")
    
    # Authentication (Requirement 1.3)
    api_key = Column(String(64), nullable=False, unique=True, index=True,
                    comment="Cryptographically secure API key (min 32 chars)")
    api_key_created_at = Column(DateTime(timezone=True), nullable=False, 
                               default=lambda: datetime.now(timezone.utc),
                               comment="API key creation timestamp")
    
    # Certificate storage (Requirement 1.2) - Encrypted
    certificado_p12 = Column(LargeBinary, nullable=True, 
                           comment="Encrypted P12 certificate binary data")
    password_certificado = Column(Text, nullable=True, 
                                comment="Encrypted certificate password")
    certificado_uploaded_at = Column(DateTime(timezone=True), nullable=True,
                                   comment="Certificate upload timestamp")
    certificado_expires_at = Column(DateTime(timezone=True), nullable=True,
                                  comment="Certificate expiration date")
    certificado_subject = Column(String(500), nullable=True,
                               comment="Certificate subject information")
    certificado_issuer = Column(String(500), nullable=True,
                              comment="Certificate issuer information")
    
    # Plan and limits (Requirements 1.4, 1.5)
    plan = Column(String(20), nullable=False, default='basico',
                 comment="Subscription plan: basico, pro, empresa")
    limite_facturas_mes = Column(Integer, nullable=False, default=100,
                               comment="Monthly document limit based on plan")
    facturas_usadas_mes = Column(Integer, nullable=False, default=0,
                               comment="Documents used in current month")
    ultimo_reset_contador = Column(DateTime(timezone=True), nullable=False,
                                 default=lambda: datetime.now(timezone.utc),
                                 comment="Last monthly counter reset")
    
    # Usage tracking and statistics
    total_documentos_creados = Column(Integer, nullable=False, default=0,
                                    comment="Total documents created (all time)")
    total_documentos_enviados = Column(Integer, nullable=False, default=0,
                                     comment="Total documents sent to Ministry")
    total_documentos_aceptados = Column(Integer, nullable=False, default=0,
                                      comment="Total documents accepted by Ministry")
    ultimo_documento_creado = Column(DateTime(timezone=True), nullable=True,
                                   comment="Timestamp of last document creation")
    
    # Account status and configuration
    activo = Column(Boolean, nullable=False, default=True,
                   comment="Account active status")
    verificado = Column(Boolean, nullable=False, default=False,
                       comment="Account verification status")
    fecha_verificacion = Column(DateTime(timezone=True), nullable=True,
                              comment="Account verification timestamp")
    
    # Notification preferences
    notificar_vencimiento_certificado = Column(Boolean, nullable=False, default=True,
                                             comment="Enable certificate expiration notifications")
    notificar_limite_mensual = Column(Boolean, nullable=False, default=True,
                                    comment="Enable monthly limit notifications")
    dias_notificacion_certificado = Column(String(20), nullable=False, default="30,15,7",
                                         comment="Days before expiration to notify (comma-separated)")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, 
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    created_by = Column(String(255), nullable=True, comment="User who created the tenant")
    updated_by = Column(String(255), nullable=True, comment="User who last updated the tenant")
    
    # Relationships (will be defined when other models are created)
    # documentos = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    
    # Table constraints
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "plan IN ('basico', 'pro', 'empresa')",
            name="ck_tenant_plan_valid"
        ),
        CheckConstraint(
            "limite_facturas_mes >= 0",
            name="ck_tenant_limite_facturas_positive"
        ),
        CheckConstraint(
            "facturas_usadas_mes >= 0",
            name="ck_tenant_facturas_usadas_positive"
        ),
        CheckConstraint(
            "facturas_usadas_mes <= limite_facturas_mes",
            name="ck_tenant_facturas_within_limit"
        ),
        CheckConstraint(
            "provincia IS NULL OR (provincia >= 1 AND provincia <= 7)",
            name="ck_tenant_provincia_valid"
        ),
        CheckConstraint(
            "canton IS NULL OR (canton >= 1 AND canton <= 99)",
            name="ck_tenant_canton_valid"
        ),
        CheckConstraint(
            "distrito IS NULL OR (distrito >= 1 AND distrito <= 99)",
            name="ck_tenant_distrito_valid"
        ),
        CheckConstraint(
            "char_length(api_key) >= 32",
            name="ck_tenant_api_key_length"
        ),
        CheckConstraint(
            "char_length(cedula_juridica) >= 9",
            name="ck_tenant_cedula_length"
        ),
        CheckConstraint(
            "email_contacto ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="ck_tenant_email_format"
        ),
        
        # Performance indexes
        Index("idx_tenants_api_key", "api_key"),
        Index("idx_tenants_cedula_juridica", "cedula_juridica"),
        Index("idx_tenants_activo", "activo"),
        Index("idx_tenants_plan", "plan"),
        Index("idx_tenants_created_at", "created_at"),
        Index("idx_tenants_certificado_expires", "certificado_expires_at"),
        Index("idx_tenants_ultimo_reset", "ultimo_reset_contador"),
        
        # Composite indexes for common queries
        Index("idx_tenants_activo_plan", "activo", "plan"),
        Index("idx_tenants_plan_limite", "plan", "limite_facturas_mes"),
    )
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, nombre_empresa='{self.nombre_empresa}', plan='{self.plan}')>"
    
    def __str__(self) -> str:
        return f"{self.nombre_empresa} ({self.cedula_juridica})"
    
    @property
    def has_certificate(self) -> bool:
        """Check if tenant has uploaded a certificate"""
        return self.certificado_p12 is not None
    
    @property
    def certificate_expired(self) -> bool:
        """Check if certificate is expired"""
        if not self.certificado_expires_at:
            return False
        return datetime.now(timezone.utc) > self.certificado_expires_at
    
    @property
    def certificate_expires_soon(self, days: int = 30) -> bool:
        """Check if certificate expires within specified days"""
        if not self.certificado_expires_at:
            return False
        from datetime import timedelta
        warning_date = datetime.now(timezone.utc) + timedelta(days=days)
        return self.certificado_expires_at <= warning_date
    
    @property
    def monthly_limit_reached(self) -> bool:
        """Check if monthly document limit has been reached"""
        return self.facturas_usadas_mes >= self.limite_facturas_mes
    
    @property
    def monthly_limit_percentage(self) -> float:
        """Get percentage of monthly limit used"""
        if self.limite_facturas_mes == 0:
            return 0.0
        return (self.facturas_usadas_mes / self.limite_facturas_mes) * 100
    
    def can_create_document(self) -> bool:
        """Check if tenant can create a new document"""
        return (
            self.activo and 
            self.verificado and 
            not self.monthly_limit_reached and
            self.has_certificate and
            not self.certificate_expired
        )
    
    def increment_usage(self) -> None:
        """Increment monthly usage counter"""
        self.facturas_usadas_mes += 1
        self.total_documentos_creados += 1
        self.ultimo_documento_creado = datetime.now(timezone.utc)
    
    def reset_monthly_counter(self) -> None:
        """Reset monthly usage counter"""
        self.facturas_usadas_mes = 0
        self.ultimo_reset_contador = datetime.now(timezone.utc)
    
    def should_reset_monthly_counter(self) -> bool:
        """Check if monthly counter should be reset"""
        if not self.ultimo_reset_contador:
            return True
        
        now = datetime.now(timezone.utc)
        last_reset = self.ultimo_reset_contador
        
        # Reset if it's a new month
        return (
            now.year > last_reset.year or
            (now.year == last_reset.year and now.month > last_reset.month)
        )
    
    def get_plan_limits(self) -> dict:
        """Get plan-specific limits and features"""
        plan_configs = {
            'basico': {
                'limite_mensual': 100,
                'rate_limit_hora': 50,
                'soporte': 'email',
                'features': ['facturacion_basica', 'api_access']
            },
            'pro': {
                'limite_mensual': 1000,
                'rate_limit_hora': 200,
                'soporte': 'email_prioritario',
                'features': ['facturacion_basica', 'api_access', 'reportes_avanzados', 'webhooks']
            },
            'empresa': {
                'limite_mensual': -1,  # Unlimited
                'rate_limit_hora': 1000,
                'soporte': 'telefono_email',
                'features': ['facturacion_basica', 'api_access', 'reportes_avanzados', 
                           'webhooks', 'integracion_personalizada', 'soporte_dedicado']
            }
        }
        return plan_configs.get(self.plan, plan_configs['basico'])