"""
DocumentExemption model for tax exemption handling
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, DateTime, Numeric, ForeignKey, CheckConstraint, Index, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ExemptionDocumentType(enum.Enum):
    """Exemption document types"""
    AUTORIZACION_DGT_COMPRAS = "01"
    VENTAS_DIPLOMATICAS = "02"
    AUTORIZACION_LEY_ESPECIAL = "03"
    AUTORIZACION_GENERAL_LOCAL = "04"
    SERVICIOS_INGENIERIA_TRANSITORIO = "05"
    SERVICIOS_TURISTICOS_ICT = "06"
    RECICLAJE_TRANSITORIO = "07"
    ZONA_FRANCA = "08"
    SERVICIOS_COMPLEMENTARIOS_EXPORTACION = "09"
    CORPORACIONES_MUNICIPALES = "10"
    AUTORIZACION_ESPECIFICA_LOCAL = "11"
    OTROS = "99"


class ExemptionInstitution(enum.Enum):
    """Institutions that grant exemptions"""
    DIRECCION_GENERAL_TRIBUTACION = "01"
    MINISTERIO_RELACIONES_EXTERIORES = "02"
    TRIBUNAL_SUPREMO_ELECCIONES = "03"
    CONTRALORIA_GENERAL_REPUBLICA = "04"
    INSTITUTO_COSTARRICENSE_TURISMO = "05"
    COMISION_NACIONAL_EMERGENCIAS = "06"
    INSTITUTO_MIXTO_AYUDA_SOCIAL = "07"
    CONSEJO_NACIONAL_REHABILITACION = "08"
    PATRONATO_NACIONAL_INFANCIA = "09"
    CRUZ_ROJA_COSTARRICENSE = "10"
    JUNTA_PROTECCION_SOCIAL = "11"
    CUALQUIER_INSTITUCION_PUBLICA = "12"
    OTROS = "99"


class DocumentExemption(Base):
    """
    Tax exemption information for document line items
    
    Supports all types of tax exemptions including DGT authorizations,
    diplomatic sales, special law authorizations, and institutional exemptions.
    
    Requirements: 14.1, 14.2
    """
    __tablename__ = "exoneraciones_documentos"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Tax relationship
    impuesto_documento_id = Column(UUID(as_uuid=True), ForeignKey("impuestos_documentos.id", ondelete="CASCADE"),
                                  nullable=False, index=True, comment="Tax that is being exempted")
    
    # Exemption document information (Requirements 14.1, 14.2)
    tipo_documento_exoneracion = Column(SQLEnum(ExemptionDocumentType), nullable=False,
                                      comment="Type of exemption document")
    tipo_documento_otro = Column(String(100), nullable=True,
                               comment="Other document type description (required when tipo = 99)")
    
    # Exemption document identification
    numero_documento = Column(String(40), nullable=False, index=True,
                            comment="Exemption document number")
    articulo = Column(Integer, nullable=True, comment="Article number in exemption document")
    inciso = Column(Integer, nullable=True, comment="Subsection number in exemption document")
    
    # Exemption authority
    nombre_institucion = Column(SQLEnum(ExemptionInstitution), nullable=False,
                              comment="Institution that granted the exemption")
    nombre_institucion_otros = Column(String(160), nullable=True,
                                    comment="Other institution name (required when institucion = 99)")
    
    # Exemption details
    fecha_emision = Column(DateTime(timezone=True), nullable=False,
                         comment="Exemption document emission date")
    tarifa_exonerada = Column(Numeric(4, 2), nullable=False,
                            comment="Exempted tax rate percentage")
    monto_exoneracion = Column(Numeric(18, 5), nullable=False,
                             comment="Exemption amount")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    
    # Relationships
    impuesto = relationship("DocumentTax", back_populates="exoneraciones")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "(tipo_documento_exoneracion != 'OTROS') OR (tipo_documento_otro IS NOT NULL)",
            name="ck_exemption_tipo_otro_required"
        ),
        CheckConstraint(
            "(nombre_institucion != 'OTROS') OR (nombre_institucion_otros IS NOT NULL)",
            name="ck_exemption_institucion_otros_required"
        ),
        CheckConstraint(
            "char_length(numero_documento) >= 3 AND char_length(numero_documento) <= 40",
            name="ck_exemption_numero_length"
        ),
        CheckConstraint(
            "articulo IS NULL OR (articulo > 0 AND articulo <= 999999)",
            name="ck_exemption_articulo_range"
        ),
        CheckConstraint(
            "inciso IS NULL OR (inciso > 0 AND inciso <= 999999)",
            name="ck_exemption_inciso_range"
        ),
        CheckConstraint(
            "tarifa_exonerada >= 0 AND tarifa_exonerada <= 99.99",
            name="ck_exemption_tarifa_range"
        ),
        CheckConstraint(
            "monto_exoneracion >= 0",
            name="ck_exemption_monto_positive"
        ),
        CheckConstraint(
            "tipo_documento_otro IS NULL OR char_length(tipo_documento_otro) <= 100",
            name="ck_exemption_tipo_otro_length"
        ),
        CheckConstraint(
            "nombre_institucion_otros IS NULL OR char_length(nombre_institucion_otros) <= 160",
            name="ck_exemption_institucion_otros_length"
        ),
        
        # Performance indexes
        Index("idx_exoneraciones_impuesto_id", "impuesto_documento_id"),
        Index("idx_exoneraciones_numero", "numero_documento"),
        Index("idx_exoneraciones_tipo", "tipo_documento_exoneracion"),
        Index("idx_exoneraciones_institucion", "nombre_institucion"),
        Index("idx_exoneraciones_fecha", "fecha_emision"),
        Index("idx_exoneraciones_monto", "monto_exoneracion"),
        Index("idx_exoneraciones_created_at", "created_at"),
        
        # Composite indexes for common queries
        Index("idx_exoneraciones_impuesto_tipo", "impuesto_documento_id", "tipo_documento_exoneracion"),
        Index("idx_exoneraciones_numero_fecha", "numero_documento", "fecha_emision"),
        Index("idx_exoneraciones_institucion_fecha", "nombre_institucion", "fecha_emision"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentExemption(id={self.id}, numero={self.numero_documento}, monto={self.monto_exoneracion})>"
    
    def __str__(self) -> str:
        return f"Exoneración {self.numero_documento}: {self.monto_exoneracion}"
    
    @property
    def requires_other_descriptions(self) -> bool:
        """Check if 'otros' fields are required"""
        return (
            self.tipo_documento_exoneracion == ExemptionDocumentType.OTROS or
            self.nombre_institucion == ExemptionInstitution.OTROS
        )
    
    @property
    def has_article_reference(self) -> bool:
        """Check if exemption has article/subsection reference"""
        return self.articulo is not None or self.inciso is not None
    
    @property
    def exemption_percentage(self) -> Decimal:
        """Get exemption percentage of the tax"""
        return self.tarifa_exonerada
    
    def get_document_type_name(self) -> str:
        """Get human-readable exemption document type name"""
        type_names = {
            ExemptionDocumentType.AUTORIZACION_DGT_COMPRAS: "Autorización DGT para compras autorizadas",
            ExemptionDocumentType.VENTAS_DIPLOMATICAS: "Ventas diplomáticas",
            ExemptionDocumentType.AUTORIZACION_LEY_ESPECIAL: "Autorización por ley especial",
            ExemptionDocumentType.AUTORIZACION_GENERAL_LOCAL: "Autorización general local",
            ExemptionDocumentType.SERVICIOS_INGENIERIA_TRANSITORIO: "Servicios de ingeniería (transitorio)",
            ExemptionDocumentType.SERVICIOS_TURISTICOS_ICT: "Servicios turísticos ICT",
            ExemptionDocumentType.RECICLAJE_TRANSITORIO: "Reciclaje (transitorio)",
            ExemptionDocumentType.ZONA_FRANCA: "Zona franca",
            ExemptionDocumentType.SERVICIOS_COMPLEMENTARIOS_EXPORTACION: "Servicios complementarios de exportación",
            ExemptionDocumentType.CORPORACIONES_MUNICIPALES: "Corporaciones municipales",
            ExemptionDocumentType.AUTORIZACION_ESPECIFICA_LOCAL: "Autorización específica local",
            ExemptionDocumentType.OTROS: "Otros"
        }
        return type_names.get(self.tipo_documento_exoneracion, "Tipo Desconocido")
    
    def get_institution_name(self) -> str:
        """Get human-readable institution name"""
        institution_names = {
            ExemptionInstitution.DIRECCION_GENERAL_TRIBUTACION: "Dirección General de Tributación",
            ExemptionInstitution.MINISTERIO_RELACIONES_EXTERIORES: "Ministerio de Relaciones Exteriores",
            ExemptionInstitution.TRIBUNAL_SUPREMO_ELECCIONES: "Tribunal Supremo de Elecciones",
            ExemptionInstitution.CONTRALORIA_GENERAL_REPUBLICA: "Contraloría General de la República",
            ExemptionInstitution.INSTITUTO_COSTARRICENSE_TURISMO: "Instituto Costarricense de Turismo",
            ExemptionInstitution.COMISION_NACIONAL_EMERGENCIAS: "Comisión Nacional de Emergencias",
            ExemptionInstitution.INSTITUTO_MIXTO_AYUDA_SOCIAL: "Instituto Mixto de Ayuda Social",
            ExemptionInstitution.CONSEJO_NACIONAL_REHABILITACION: "Consejo Nacional de Rehabilitación",
            ExemptionInstitution.PATRONATO_NACIONAL_INFANCIA: "Patronato Nacional de la Infancia",
            ExemptionInstitution.CRUZ_ROJA_COSTARRICENSE: "Cruz Roja Costarricense",
            ExemptionInstitution.JUNTA_PROTECCION_SOCIAL: "Junta de Protección Social",
            ExemptionInstitution.CUALQUIER_INSTITUCION_PUBLICA: "Cualquier institución pública",
            ExemptionInstitution.OTROS: "Otros"
        }
        return institution_names.get(self.nombre_institucion, "Institución Desconocida")
    
    def get_full_document_reference(self) -> str:
        """Get full document reference including article and subsection"""
        reference = self.numero_documento
        
        if self.articulo:
            reference += f", Art. {self.articulo}"
        
        if self.inciso:
            reference += f", Inc. {self.inciso}"
        
        return reference
    
    def validate_exemption_data(self) -> bool:
        """Validate exemption data consistency"""
        # Check if 'otros' descriptions are provided when required
        if self.tipo_documento_exoneracion == ExemptionDocumentType.OTROS:
            if not self.tipo_documento_otro or len(self.tipo_documento_otro.strip()) == 0:
                return False
        
        if self.nombre_institucion == ExemptionInstitution.OTROS:
            if not self.nombre_institucion_otros or len(self.nombre_institucion_otros.strip()) == 0:
                return False
        
        # Validate document number length
        if len(self.numero_documento) < 3 or len(self.numero_documento) > 40:
            return False
        
        # Validate numeric ranges
        if self.articulo is not None and (self.articulo <= 0 or self.articulo > 999999):
            return False
        
        if self.inciso is not None and (self.inciso <= 0 or self.inciso > 999999):
            return False
        
        if self.tarifa_exonerada < 0 or self.tarifa_exonerada > 99.99:
            return False
        
        if self.monto_exoneracion < 0:
            return False
        
        # Validate field lengths
        if self.tipo_documento_otro and len(self.tipo_documento_otro) > 100:
            return False
        
        if self.nombre_institucion_otros and len(self.nombre_institucion_otros) > 160:
            return False
        
        return True
    
    def calculate_exemption_amount(self, tax_base: Decimal) -> Decimal:
        """Calculate exemption amount based on tax base and exemption rate"""
        return tax_base * (self.tarifa_exonerada / 100)
    
    def is_valid_for_date(self, check_date: datetime = None) -> bool:
        """Check if exemption is valid for a given date"""
        if check_date is None:
            check_date = datetime.now(timezone.utc)
        
        # Basic validation - exemption document should be issued before use
        return self.fecha_emision <= check_date
    
    def to_dict(self) -> dict:
        """Convert exemption to dictionary for API responses"""
        return {
            "id": str(self.id),
            "tipo_documento_exoneracion": self.tipo_documento_exoneracion.value,
            "tipo_documento_exoneracion_nombre": self.get_document_type_name(),
            "tipo_documento_otro": self.tipo_documento_otro,
            "numero_documento": self.numero_documento,
            "articulo": self.articulo,
            "inciso": self.inciso,
            "nombre_institucion": self.nombre_institucion.value,
            "nombre_institucion_nombre": self.get_institution_name(),
            "nombre_institucion_otros": self.nombre_institucion_otros,
            "fecha_emision": self.fecha_emision.isoformat(),
            "tarifa_exonerada": float(self.tarifa_exonerada),
            "monto_exoneracion": float(self.monto_exoneracion),
            "full_document_reference": self.get_full_document_reference(),
            "has_article_reference": self.has_article_reference,
            "created_at": self.created_at.isoformat()
        }