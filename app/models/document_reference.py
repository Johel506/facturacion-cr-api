"""
DocumentReference model for credit/debit note relationships and document corrections
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, CheckConstraint, Index, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ReferenceDocumentType(enum.Enum):
    """Reference document types"""
    FACTURA_ELECTRONICA = "01"
    NOTA_DEBITO_ELECTRONICA = "02"
    NOTA_CREDITO_ELECTRONICA = "03"
    TIQUETE_ELECTRONICO = "04"
    NOTA_DESPACHO = "05"
    CONTRATO = "06"
    PROCEDIMIENTO = "07"
    COMPROBANTE_CONTINGENCIA = "08"
    DEVOLUCION_MERCANCIA = "09"
    RECHAZADO_MINISTERIO = "10"
    RECHAZADO_RECEPTOR_SUSTITUTO = "11"
    SUSTITUTO_FACTURA_EXPORTACION = "12"
    FACTURACION_MES_ANTERIOR = "13"
    COMPROBANTE_REGIMEN_ESPECIAL = "14"
    SUSTITUTO_FACTURA_COMPRA = "15"
    PROVEEDOR_NO_DOMICILIADO = "16"
    NOTA_CREDITO_FACTURA_COMPRA = "17"
    NOTA_DEBITO_FACTURA_COMPRA = "18"
    OTROS = "99"


class ReferenceCode(enum.Enum):
    """Reference codes for document relationships"""
    ANULA_DOCUMENTO_REFERENCIA = "01"
    CORRIGE_TEXTO_DOCUMENTO_REFERENCIA = "02"
    REFERENCIA_OTRO_DOCUMENTO = "04"
    SUSTITUYE_COMPROBANTE_CONTINGENCIA = "05"
    DEVOLUCION_MERCANCIA = "06"
    SUSTITUYE_COMPROBANTE_ELECTRONICO = "07"
    FACTURA_ENDOSADA = "08"
    NOTA_CREDITO_FINANCIERA = "09"
    NOTA_DEBITO_FINANCIERA = "10"
    PROVEEDOR_NO_DOMICILIADO = "11"
    NOTA_CREDITO_EXONERACION_POSTERIOR = "12"
    OTROS = "99"


class DocumentReference(Base):
    """
    Document references for credit/debit notes, corrections, and cancellations
    
    Supports all types of document relationships including corrections,
    cancellations, substitutions, and references to other documents.
    
    Requirements: 15.1, 15.2
    """
    __tablename__ = "referencias_documentos"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Document relationship
    documento_id = Column(UUID(as_uuid=True), ForeignKey("documentos.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="Document that contains this reference")
    
    # Reference document information (Requirements 15.1, 15.2)
    tipo_documento_referencia = Column(SQLEnum(ReferenceDocumentType), nullable=False,
                                     comment="Type of referenced document")
    tipo_documento_otro = Column(String(100), nullable=True,
                               comment="Other document type description (required when tipo = 99)")
    
    # Reference identification
    numero_referencia = Column(String(50), nullable=True, index=True,
                             comment="Document key or consecutive number of referenced document")
    fecha_emision_referencia = Column(DateTime(timezone=True), nullable=False,
                                    comment="Emission date of referenced document")
    
    # Reference relationship
    codigo_referencia = Column(SQLEnum(ReferenceCode), nullable=True,
                             comment="Type of reference relationship")
    codigo_referencia_otro = Column(String(100), nullable=True,
                                  comment="Other reference code description (required when codigo = 99)")
    
    # Reference reason
    razon = Column(String(180), nullable=True,
                  comment="Reason for the reference (corrections, cancellations, etc.)")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    
    # Relationships
    documento = relationship("Document", back_populates="referencias")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "(tipo_documento_referencia != 'OTROS') OR (tipo_documento_otro IS NOT NULL)",
            name="ck_reference_tipo_otro_required"
        ),
        CheckConstraint(
            "(codigo_referencia != 'OTROS') OR (codigo_referencia_otro IS NOT NULL)",
            name="ck_reference_codigo_otro_required"
        ),
        CheckConstraint(
            "numero_referencia IS NULL OR char_length(numero_referencia) <= 50",
            name="ck_reference_numero_length"
        ),
        CheckConstraint(
            "tipo_documento_otro IS NULL OR char_length(tipo_documento_otro) <= 100",
            name="ck_reference_tipo_otro_length"
        ),
        CheckConstraint(
            "codigo_referencia_otro IS NULL OR char_length(codigo_referencia_otro) <= 100",
            name="ck_reference_codigo_otro_length"
        ),
        CheckConstraint(
            "razon IS NULL OR char_length(razon) <= 180",
            name="ck_reference_razon_length"
        ),
        
        # Performance indexes
        Index("idx_referencias_documento_id", "documento_id"),
        Index("idx_referencias_numero", "numero_referencia"),
        Index("idx_referencias_tipo", "tipo_documento_referencia"),
        Index("idx_referencias_codigo", "codigo_referencia"),
        Index("idx_referencias_fecha", "fecha_emision_referencia"),
        Index("idx_referencias_created_at", "created_at"),
        
        # Composite indexes for common queries
        Index("idx_referencias_documento_tipo", "documento_id", "tipo_documento_referencia"),
        Index("idx_referencias_numero_fecha", "numero_referencia", "fecha_emision_referencia"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentReference(id={self.id}, documento_id={self.documento_id}, tipo={self.tipo_documento_referencia.value})>"
    
    def __str__(self) -> str:
        return f"Referencia {self.tipo_documento_referencia.value}: {self.numero_referencia or 'Sin número'}"
    
    @property
    def is_cancellation(self) -> bool:
        """Check if this reference is a cancellation"""
        return self.codigo_referencia == ReferenceCode.ANULA_DOCUMENTO_REFERENCIA
    
    @property
    def is_correction(self) -> bool:
        """Check if this reference is a text correction"""
        return self.codigo_referencia == ReferenceCode.CORRIGE_TEXTO_DOCUMENTO_REFERENCIA
    
    @property
    def is_substitution(self) -> bool:
        """Check if this reference is a substitution"""
        return self.codigo_referencia in [
            ReferenceCode.SUSTITUYE_COMPROBANTE_CONTINGENCIA,
            ReferenceCode.SUSTITUYE_COMPROBANTE_ELECTRONICO
        ]
    
    @property
    def requires_other_description(self) -> bool:
        """Check if 'otros' fields are required"""
        return (
            self.tipo_documento_referencia == ReferenceDocumentType.OTROS or
            self.codigo_referencia == ReferenceCode.OTROS
        )
    
    def get_reference_type_name(self) -> str:
        """Get human-readable reference type name"""
        type_names = {
            ReferenceDocumentType.FACTURA_ELECTRONICA: "Factura Electrónica",
            ReferenceDocumentType.NOTA_DEBITO_ELECTRONICA: "Nota de Débito Electrónica",
            ReferenceDocumentType.NOTA_CREDITO_ELECTRONICA: "Nota de Crédito Electrónica",
            ReferenceDocumentType.TIQUETE_ELECTRONICO: "Tiquete Electrónico",
            ReferenceDocumentType.NOTA_DESPACHO: "Nota de Despacho",
            ReferenceDocumentType.CONTRATO: "Contrato",
            ReferenceDocumentType.PROCEDIMIENTO: "Procedimiento",
            ReferenceDocumentType.COMPROBANTE_CONTINGENCIA: "Comprobante de Contingencia",
            ReferenceDocumentType.DEVOLUCION_MERCANCIA: "Devolución de Mercancía",
            ReferenceDocumentType.RECHAZADO_MINISTERIO: "Rechazado por Ministerio",
            ReferenceDocumentType.RECHAZADO_RECEPTOR_SUSTITUTO: "Rechazado por Receptor - Sustituto",
            ReferenceDocumentType.SUSTITUTO_FACTURA_EXPORTACION: "Sustituto Factura de Exportación",
            ReferenceDocumentType.FACTURACION_MES_ANTERIOR: "Facturación Mes Anterior",
            ReferenceDocumentType.COMPROBANTE_REGIMEN_ESPECIAL: "Comprobante Régimen Especial",
            ReferenceDocumentType.SUSTITUTO_FACTURA_COMPRA: "Sustituto Factura de Compra",
            ReferenceDocumentType.PROVEEDOR_NO_DOMICILIADO: "Proveedor No Domiciliado",
            ReferenceDocumentType.NOTA_CREDITO_FACTURA_COMPRA: "Nota de Crédito a Factura de Compra",
            ReferenceDocumentType.NOTA_DEBITO_FACTURA_COMPRA: "Nota de Débito a Factura de Compra",
            ReferenceDocumentType.OTROS: "Otros"
        }
        return type_names.get(self.tipo_documento_referencia, "Tipo Desconocido")
    
    def get_reference_code_name(self) -> str:
        """Get human-readable reference code name"""
        if not self.codigo_referencia:
            return "Sin código"
        
        code_names = {
            ReferenceCode.ANULA_DOCUMENTO_REFERENCIA: "Anula documento de referencia",
            ReferenceCode.CORRIGE_TEXTO_DOCUMENTO_REFERENCIA: "Corrige texto del documento de referencia",
            ReferenceCode.REFERENCIA_OTRO_DOCUMENTO: "Referencia a otro documento",
            ReferenceCode.SUSTITUYE_COMPROBANTE_CONTINGENCIA: "Sustituye comprobante por contingencia",
            ReferenceCode.DEVOLUCION_MERCANCIA: "Devolución de mercancía",
            ReferenceCode.SUSTITUYE_COMPROBANTE_ELECTRONICO: "Sustituye comprobante electrónico",
            ReferenceCode.FACTURA_ENDOSADA: "Factura endosada",
            ReferenceCode.NOTA_CREDITO_FINANCIERA: "Nota de crédito financiera",
            ReferenceCode.NOTA_DEBITO_FINANCIERA: "Nota de débito financiera",
            ReferenceCode.PROVEEDOR_NO_DOMICILIADO: "Proveedor no domiciliado",
            ReferenceCode.NOTA_CREDITO_EXONERACION_POSTERIOR: "Nota de crédito por exoneración posterior",
            ReferenceCode.OTROS: "Otros"
        }
        return code_names.get(self.codigo_referencia, "Código Desconocido")
    
    def validate_reference(self) -> bool:
        """Validate reference data consistency"""
        # Check if 'otros' descriptions are provided when required
        if self.tipo_documento_referencia == ReferenceDocumentType.OTROS:
            if not self.tipo_documento_otro or len(self.tipo_documento_otro.strip()) == 0:
                return False
        
        if self.codigo_referencia == ReferenceCode.OTROS:
            if not self.codigo_referencia_otro or len(self.codigo_referencia_otro.strip()) == 0:
                return False
        
        # Validate field lengths
        if self.numero_referencia and len(self.numero_referencia) > 50:
            return False
        
        if self.tipo_documento_otro and len(self.tipo_documento_otro) > 100:
            return False
        
        if self.codigo_referencia_otro and len(self.codigo_referencia_otro) > 100:
            return False
        
        if self.razon and len(self.razon) > 180:
            return False
        
        return True
    
    def to_dict(self) -> dict:
        """Convert reference to dictionary for API responses"""
        return {
            "id": str(self.id),
            "tipo_documento_referencia": self.tipo_documento_referencia.value,
            "tipo_documento_referencia_nombre": self.get_reference_type_name(),
            "tipo_documento_otro": self.tipo_documento_otro,
            "numero_referencia": self.numero_referencia,
            "fecha_emision_referencia": self.fecha_emision_referencia.isoformat(),
            "codigo_referencia": self.codigo_referencia.value if self.codigo_referencia else None,
            "codigo_referencia_nombre": self.get_reference_code_name(),
            "codigo_referencia_otro": self.codigo_referencia_otro,
            "razon": self.razon,
            "is_cancellation": self.is_cancellation,
            "is_correction": self.is_correction,
            "is_substitution": self.is_substitution,
            "created_at": self.created_at.isoformat()
        }