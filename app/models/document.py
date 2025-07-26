"""
Unified Document model supporting all 7 Costa Rican electronic document types
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, Numeric,
    ForeignKey, CheckConstraint, Index, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class DocumentType(enum.Enum):
    """Official Costa Rican electronic document types"""
    FACTURA_ELECTRONICA = "01"
    NOTA_DEBITO_ELECTRONICA = "02"
    NOTA_CREDITO_ELECTRONICA = "03"
    TIQUETE_ELECTRONICO = "04"
    FACTURA_EXPORTACION = "05"
    FACTURA_COMPRA = "06"
    RECIBO_PAGO = "07"


class DocumentStatus(enum.Enum):
    """Document processing status"""
    BORRADOR = "borrador"
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    PROCESANDO = "procesando"
    ACEPTADO = "aceptado"
    RECHAZADO = "rechazado"
    ERROR = "error"
    CANCELADO = "cancelado"


class IdentificationType(enum.Enum):
    """Costa Rican identification types"""
    CEDULA_FISICA = "01"
    CEDULA_JURIDICA = "02"
    DIMEX = "03"
    NITE = "04"
    EXTRANJERO_NO_DOMICILIADO = "05"
    NO_CONTRIBUYENTE = "06"


class SaleCondition(enum.Enum):
    """Sale condition types"""
    CONTADO = "01"
    CREDITO = "02"
    CONSIGNACION = "03"
    APARTADO = "04"
    ARRENDAMIENTO_OPCION_COMPRA = "05"
    ARRENDAMIENTO_FUNCION_FINANCIERA = "06"
    COBRO_TERCERO = "07"
    SERVICIOS_ESTADO_CREDITO = "08"
    VENTA_CREDITO_90_DIAS = "10"
    VENTA_MERCANCIA_NO_NACIONALIZADA = "12"
    VENTA_BIENES_USADOS_NO_CONTRIBUYENTE = "13"
    ARRENDAMIENTO_OPERATIVO = "14"
    ARRENDAMIENTO_FINANCIERO = "15"
    OTROS = "99"


class PaymentMethod(enum.Enum):
    """Payment method types"""
    EFECTIVO = "01"
    TARJETA = "02"
    CHEQUE = "03"
    TRANSFERENCIA = "04"
    RECAUDADO_TERCERO = "05"
    OTROS = "99"


class Document(Base):
    """
    Unified Document model supporting all 7 Costa Rican electronic document types
    
    Supports: FacturaElectronica (01), NotaDebitoElectronica (02), NotaCreditoElectronica (03),
    TiqueteElectronico (04), FacturaElectronicaExportacion (05), FacturaElectronicaCompra (06),
    ReciboElectronicoPago (07)
    
    Requirements: 9.1, 11.1, 11.3, 11.4, 13.1, 13.4, 3.4, 3.5
    """
    __tablename__ = "documentos"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Tenant relationship (multi-tenant isolation)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), 
                      nullable=False, index=True, comment="Tenant owner of the document")
    
    # Document identification (Requirements 9.1, 10.1, 10.2, 10.3)
    tipo_documento = Column(SQLEnum(DocumentType), nullable=False, index=True,
                          comment="Document type: 01-07")
    numero_consecutivo = Column(String(20), nullable=False, index=True,
                              comment="20-digit consecutive number: Branch(3)+Terminal(5)+DocType(2)+Sequential(10)")
    clave = Column(String(50), nullable=False, unique=True, index=True,
                  comment="50-character document key following official format")
    fecha_emision = Column(DateTime(timezone=True), nullable=False, index=True,
                         comment="Document emission date and time")
    
    # Emisor information (Requirements 11.1, 11.3)
    emisor_nombre = Column(String(100), nullable=False, comment="Issuer legal name")
    emisor_tipo_identificacion = Column(SQLEnum(IdentificationType), nullable=False,
                                      comment="Issuer identification type")
    emisor_numero_identificacion = Column(String(20), nullable=False, index=True,
                                        comment="Issuer identification number")
    emisor_nombre_comercial = Column(String(80), nullable=True, comment="Issuer commercial name")
    emisor_codigo_actividad = Column(String(6), nullable=True, comment="Issuer economic activity code")
    
    # Emisor location
    emisor_provincia = Column(Integer, nullable=True, comment="Issuer province (1-7)")
    emisor_canton = Column(Integer, nullable=True, comment="Issuer canton")
    emisor_distrito = Column(Integer, nullable=True, comment="Issuer district")
    emisor_barrio = Column(String(50), nullable=True, comment="Issuer neighborhood")
    emisor_otras_senas = Column(String(250), nullable=True, comment="Issuer detailed address")
    
    # Emisor contact
    emisor_codigo_pais_telefono = Column(Integer, nullable=True, comment="Issuer phone country code")
    emisor_numero_telefono = Column(String(20), nullable=True, comment="Issuer phone number")
    emisor_correo_electronico = Column(String(160), nullable=True, comment="Issuer email")
    
    # Receptor information (Optional for some document types like tickets)
    receptor_nombre = Column(String(100), nullable=True, comment="Receiver legal name")
    receptor_tipo_identificacion = Column(SQLEnum(IdentificationType), nullable=True,
                                        comment="Receiver identification type")
    receptor_numero_identificacion = Column(String(20), nullable=True, index=True,
                                          comment="Receiver identification number")
    receptor_nombre_comercial = Column(String(80), nullable=True, comment="Receiver commercial name")
    receptor_codigo_actividad = Column(String(6), nullable=True, comment="Receiver economic activity code")
    
    # Receptor location
    receptor_provincia = Column(Integer, nullable=True, comment="Receiver province (1-7)")
    receptor_canton = Column(Integer, nullable=True, comment="Receiver canton")
    receptor_distrito = Column(Integer, nullable=True, comment="Receiver district")
    receptor_barrio = Column(String(50), nullable=True, comment="Receiver neighborhood")
    receptor_otras_senas = Column(String(250), nullable=True, comment="Receiver detailed address")
    receptor_otras_senas_extranjero = Column(String(300), nullable=True, 
                                           comment="Foreign receiver address")
    
    # Receptor contact
    receptor_codigo_pais_telefono = Column(Integer, nullable=True, comment="Receiver phone country code")
    receptor_numero_telefono = Column(String(20), nullable=True, comment="Receiver phone number")
    receptor_correo_electronico = Column(String(160), nullable=True, comment="Receiver email")
    
    # Transaction conditions (Requirements 11.3, 11.4)
    condicion_venta = Column(SQLEnum(SaleCondition), nullable=False,
                           comment="Sale condition: 01-15, 99")
    condicion_venta_otros = Column(String(100), nullable=True,
                                 comment="Other sale condition description (required when 99)")
    plazo_credito = Column(Integer, nullable=True,
                         comment="Credit term in days (required for credit sales)")
    medio_pago = Column(SQLEnum(PaymentMethod), nullable=False,
                       comment="Payment method: 01-05, 99")
    medio_pago_otros = Column(String(100), nullable=True,
                            comment="Other payment method description (required when 99)")
    
    # Currency and exchange (Requirements 13.1, 13.4)
    codigo_moneda = Column(String(3), nullable=False, default='CRC',
                         comment="ISO 4217 currency code")
    tipo_cambio = Column(Numeric(18, 5), nullable=False, default=Decimal('1.0'),
                       comment="Exchange rate to CRC")
    
    # Document totals (calculated from line items)
    total_venta_neta = Column(Numeric(18, 5), nullable=False,
                            comment="Net sale total (before taxes)")
    total_impuesto = Column(Numeric(18, 5), nullable=False, default=Decimal('0'),
                          comment="Total tax amount")
    total_descuento = Column(Numeric(18, 5), nullable=False, default=Decimal('0'),
                           comment="Total discount amount")
    total_otros_cargos = Column(Numeric(18, 5), nullable=False, default=Decimal('0'),
                              comment="Total other charges")
    total_comprobante = Column(Numeric(18, 5), nullable=False,
                             comment="Final document total")
    
    # XML storage and processing (Requirements 3.4, 3.5)
    xml_original = Column(Text, nullable=True, comment="Original generated XML")
    xml_firmado = Column(Text, nullable=True, comment="Digitally signed XML")
    xml_respuesta_hacienda = Column(Text, nullable=True, comment="Ministry response XML")
    
    # Ministry status tracking (Requirements 3.4, 3.5)
    estado = Column(SQLEnum(DocumentStatus), nullable=False, default=DocumentStatus.BORRADOR,
                   index=True, comment="Document processing status")
    mensaje_hacienda = Column(Text, nullable=True, comment="Ministry response message")
    codigo_error_hacienda = Column(String(10), nullable=True, comment="Ministry error code")
    fecha_procesamiento = Column(DateTime(timezone=True), nullable=True,
                               comment="Ministry processing timestamp")
    fecha_aceptacion = Column(DateTime(timezone=True), nullable=True,
                            comment="Ministry acceptance timestamp")
    
    # Processing workflow
    intentos_envio = Column(Integer, nullable=False, default=0,
                          comment="Number of submission attempts")
    proximo_intento = Column(DateTime(timezone=True), nullable=True,
                           comment="Next retry attempt timestamp")
    enviado_por = Column(String(255), nullable=True, comment="User who sent the document")
    
    # Document metadata
    observaciones = Column(String(500), nullable=True, comment="Additional observations")
    referencia_interna = Column(String(100), nullable=True, comment="Internal reference number")
    numero_orden_compra = Column(String(100), nullable=True, comment="Purchase order number")
    
    # Security and validation
    hash_documento = Column(String(64), nullable=True, comment="Document content hash for integrity")
    version_esquema = Column(String(10), nullable=False, default="4.4",
                           comment="XSD schema version used")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    created_by = Column(String(255), nullable=True, comment="User who created the document")
    updated_by = Column(String(255), nullable=True, comment="User who last updated the document")
    
    # Relationships
    tenant = relationship("Tenant", back_populates="documentos")
    # detalles = relationship("DocumentDetail", back_populates="documento", cascade="all, delete-orphan")
    # referencias = relationship("DocumentReference", back_populates="documento", cascade="all, delete-orphan")
    # otros_cargos = relationship("DocumentOtherCharge", back_populates="documento", cascade="all, delete-orphan")
    # mensajes_receptor = relationship("ReceptorMessage", back_populates="documento")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "char_length(numero_consecutivo) = 20",
            name="ck_document_consecutivo_length"
        ),
        CheckConstraint(
            "char_length(clave) = 50",
            name="ck_document_clave_length"
        ),
        CheckConstraint(
            "numero_consecutivo ~ '^\\d{20}$'",
            name="ck_document_consecutivo_format"
        ),
        CheckConstraint(
            "clave ~ '^\\d{50}$'",
            name="ck_document_clave_format"
        ),
        CheckConstraint(
            "total_venta_neta >= 0",
            name="ck_document_venta_neta_positive"
        ),
        CheckConstraint(
            "total_impuesto >= 0",
            name="ck_document_impuesto_positive"
        ),
        CheckConstraint(
            "total_descuento >= 0",
            name="ck_document_descuento_positive"
        ),
        CheckConstraint(
            "total_otros_cargos >= 0",
            name="ck_document_otros_cargos_positive"
        ),
        CheckConstraint(
            "total_comprobante >= 0",
            name="ck_document_total_positive"
        ),
        CheckConstraint(
            "intentos_envio >= 0",
            name="ck_document_intentos_positive"
        ),
        CheckConstraint(
            "tipo_cambio > 0",
            name="ck_document_tipo_cambio_positive"
        ),
        CheckConstraint(
            "plazo_credito IS NULL OR plazo_credito > 0",
            name="ck_document_plazo_credito_positive"
        ),
        CheckConstraint(
            "emisor_provincia IS NULL OR (emisor_provincia >= 1 AND emisor_provincia <= 7)",
            name="ck_document_emisor_provincia_valid"
        ),
        CheckConstraint(
            "receptor_provincia IS NULL OR (receptor_provincia >= 1 AND receptor_provincia <= 7)",
            name="ck_document_receptor_provincia_valid"
        ),
        CheckConstraint(
            "(condicion_venta != 'OTROS') OR (condicion_venta_otros IS NOT NULL)",
            name="ck_document_condicion_venta_otros_required"
        ),
        CheckConstraint(
            "(medio_pago != 'OTROS') OR (medio_pago_otros IS NOT NULL)",
            name="ck_document_medio_pago_otros_required"
        ),
        CheckConstraint(
            "(condicion_venta != 'CREDITO') OR (plazo_credito IS NOT NULL)",
            name="ck_document_credito_plazo_required"
        ),
        
        # Performance indexes
        Index("idx_documentos_tenant_id", "tenant_id"),
        Index("idx_documentos_clave", "clave"),
        Index("idx_documentos_tipo", "tipo_documento"),
        Index("idx_documentos_estado", "estado"),
        Index("idx_documentos_fecha_emision", "fecha_emision"),
        Index("idx_documentos_consecutivo", "numero_consecutivo"),
        Index("idx_documentos_emisor_id", "emisor_numero_identificacion"),
        Index("idx_documentos_receptor_id", "receptor_numero_identificacion"),
        Index("idx_documentos_created_at", "created_at"),
        Index("idx_documentos_fecha_procesamiento", "fecha_procesamiento"),
        
        # Composite indexes for common queries
        Index("idx_documentos_tenant_tipo", "tenant_id", "tipo_documento"),
        Index("idx_documentos_tenant_estado", "tenant_id", "estado"),
        Index("idx_documentos_tenant_fecha", "tenant_id", "fecha_emision"),
        Index("idx_documentos_estado_fecha", "estado", "fecha_emision"),
        Index("idx_documentos_tipo_fecha", "tipo_documento", "fecha_emision"),
        Index("idx_documentos_emisor_fecha", "emisor_numero_identificacion", "fecha_emision"),
        Index("idx_documentos_receptor_fecha", "receptor_numero_identificacion", "fecha_emision"),
        
        # Indexes for Ministry processing
        Index("idx_documentos_pendiente_envio", "estado", "proximo_intento"),
        Index("idx_documentos_intentos", "intentos_envio", "estado"),
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, tipo={self.tipo_documento.value}, clave='{self.clave}')>"
    
    def __str__(self) -> str:
        return f"{self.tipo_documento.value} - {self.numero_consecutivo}"
    
    @property
    def is_credit_sale(self) -> bool:
        """Check if this is a credit sale"""
        return self.condicion_venta == SaleCondition.CREDITO
    
    @property
    def is_export_invoice(self) -> bool:
        """Check if this is an export invoice"""
        return self.tipo_documento == DocumentType.FACTURA_EXPORTACION
    
    @property
    def is_ticket(self) -> bool:
        """Check if this is a ticket (receptor optional)"""
        return self.tipo_documento == DocumentType.TIQUETE_ELECTRONICO
    
    @property
    def requires_receptor(self) -> bool:
        """Check if document type requires receptor information"""
        return not self.is_ticket
    
    @property
    def is_reference_document(self) -> bool:
        """Check if this document references another (credit/debit notes)"""
        return self.tipo_documento in [
            DocumentType.NOTA_CREDITO_ELECTRONICA,
            DocumentType.NOTA_DEBITO_ELECTRONICA
        ]
    
    @property
    def can_be_sent(self) -> bool:
        """Check if document can be sent to Ministry"""
        return (
            self.estado in [DocumentStatus.BORRADOR, DocumentStatus.ERROR] and
            self.xml_firmado is not None and
            self.tenant.activo and
            self.tenant.has_certificate and
            not self.tenant.certificate_expired
        )
    
    @property
    def is_final(self) -> bool:
        """Check if document is in final state"""
        return self.estado in [
            DocumentStatus.ACEPTADO,
            DocumentStatus.CANCELADO
        ]
    
    @property
    def needs_retry(self) -> bool:
        """Check if document needs retry"""
        return (
            self.estado == DocumentStatus.ERROR and
            self.intentos_envio < 3 and
            (self.proximo_intento is None or 
             datetime.now(timezone.utc) >= self.proximo_intento)
        )
    
    def calculate_totals(self) -> None:
        """Calculate document totals from line items (to be implemented with details)"""
        # This will be implemented when DocumentDetail model is created
        pass
    
    def increment_retry_count(self) -> None:
        """Increment retry count and set next retry time"""
        from datetime import timedelta
        
        self.intentos_envio += 1
        
        # Exponential backoff: 5min, 15min, 1hour
        retry_delays = [5, 15, 60]
        if self.intentos_envio <= len(retry_delays):
            delay_minutes = retry_delays[self.intentos_envio - 1]
            self.proximo_intento = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        else:
            self.proximo_intento = None  # No more retries
    
    def mark_as_sent(self) -> None:
        """Mark document as sent to Ministry"""
        self.estado = DocumentStatus.ENVIADO
        self.fecha_procesamiento = datetime.now(timezone.utc)
    
    def mark_as_accepted(self, ministry_response: str = None) -> None:
        """Mark document as accepted by Ministry"""
        self.estado = DocumentStatus.ACEPTADO
        self.fecha_aceptacion = datetime.now(timezone.utc)
        if ministry_response:
            self.xml_respuesta_hacienda = ministry_response
        
        # Update tenant statistics
        if self.tenant:
            self.tenant.total_documentos_aceptados += 1
    
    def mark_as_rejected(self, error_message: str, error_code: str = None) -> None:
        """Mark document as rejected by Ministry"""
        self.estado = DocumentStatus.RECHAZADO
        self.mensaje_hacienda = error_message
        self.codigo_error_hacienda = error_code
        self.fecha_procesamiento = datetime.now(timezone.utc)
    
    def mark_as_error(self, error_message: str) -> None:
        """Mark document as having processing error"""
        self.estado = DocumentStatus.ERROR
        self.mensaje_hacienda = error_message
        self.increment_retry_count()
    
    def get_document_type_name(self) -> str:
        """Get human-readable document type name"""
        type_names = {
            DocumentType.FACTURA_ELECTRONICA: "Factura Electrónica",
            DocumentType.NOTA_DEBITO_ELECTRONICA: "Nota de Débito Electrónica",
            DocumentType.NOTA_CREDITO_ELECTRONICA: "Nota de Crédito Electrónica",
            DocumentType.TIQUETE_ELECTRONICO: "Tiquete Electrónico",
            DocumentType.FACTURA_EXPORTACION: "Factura Electrónica de Exportación",
            DocumentType.FACTURA_COMPRA: "Factura Electrónica de Compra",
            DocumentType.RECIBO_PAGO: "Recibo Electrónico de Pago"
        }
        return type_names.get(self.tipo_documento, "Documento Desconocido")
    
    def to_dict(self) -> dict:
        """Convert document to dictionary for API responses"""
        return {
            "id": str(self.id),
            "tipo_documento": self.tipo_documento.value,
            "tipo_documento_nombre": self.get_document_type_name(),
            "numero_consecutivo": self.numero_consecutivo,
            "clave": self.clave,
            "fecha_emision": self.fecha_emision.isoformat(),
            "emisor_nombre": self.emisor_nombre,
            "emisor_identificacion": self.emisor_numero_identificacion,
            "receptor_nombre": self.receptor_nombre,
            "receptor_identificacion": self.receptor_numero_identificacion,
            "estado": self.estado.value,
            "total_venta_neta": float(self.total_venta_neta),
            "total_impuesto": float(self.total_impuesto),
            "total_comprobante": float(self.total_comprobante),
            "codigo_moneda": self.codigo_moneda,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }