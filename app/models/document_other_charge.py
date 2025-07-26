"""
DocumentOtherCharge model for stamps and additional fees
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, String, DateTime, Numeric, ForeignKey, CheckConstraint, Index, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.document import IdentificationType


class OtherChargeType(enum.Enum):
    """Other charge types"""
    CONTRIBUCION_PARAFISCAL = "01"
    TIMBRE_CRUZ_ROJA = "02"
    TIMBRE_BOMBEROS = "03"
    COBRO_TERCERO = "04"
    GASTOS_EXPORTACION = "05"
    IMPUESTO_SERVICIO_10_PERCENT = "06"
    TIMBRES_COLEGIOS_PROFESIONALES = "07"
    DEPOSITOS_GARANTIA = "08"
    MULTAS_SANCIONES = "09"
    INTERESES_MORATORIOS = "10"
    OTROS = "99"


class DocumentOtherCharge(Base):
    """
    Other charges for documents including stamps and additional fees
    
    Supports parafiscal contributions, stamps (Cruz Roja, Bomberos, Professional Colleges),
    third-party collections, export costs, service taxes, guarantees, fines, and interest.
    
    Requirements: 14.4
    """
    __tablename__ = "otros_cargos_documentos"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Document relationship
    documento_id = Column(UUID(as_uuid=True), ForeignKey("documentos.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="Document that contains this charge")
    
    # Charge type (Requirement 14.4)
    tipo_documento = Column(SQLEnum(OtherChargeType), nullable=False, index=True,
                          comment="Type of other charge")
    tipo_documento_otros = Column(String(100), nullable=True,
                                comment="Other charge type description (required when tipo = 99)")
    
    # Third party information (optional for some charge types)
    tercero_tipo_identificacion = Column(SQLEnum(IdentificationType), nullable=True,
                                       comment="Third party identification type")
    tercero_numero_identificacion = Column(String(20), nullable=True, index=True,
                                         comment="Third party identification number")
    tercero_nombre = Column(String(100), nullable=True,
                          comment="Third party name")
    
    # Charge details
    detalle = Column(String(160), nullable=False,
                    comment="Charge description/details")
    porcentaje = Column(Numeric(9, 5), nullable=True,
                       comment="Percentage for calculation (when applicable)")
    monto_cargo = Column(Numeric(18, 5), nullable=False,
                        comment="Charge amount")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    
    # Relationships
    documento = relationship("Document", back_populates="otros_cargos")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "(tipo_documento != 'OTROS') OR (tipo_documento_otros IS NOT NULL)",
            name="ck_other_charge_tipo_otros_required"
        ),
        CheckConstraint(
            "char_length(detalle) >= 1 AND char_length(detalle) <= 160",
            name="ck_other_charge_detalle_length"
        ),
        CheckConstraint(
            "monto_cargo >= 0",
            name="ck_other_charge_monto_positive"
        ),
        CheckConstraint(
            "porcentaje IS NULL OR (porcentaje >= 0 AND porcentaje <= 100)",
            name="ck_other_charge_porcentaje_range"
        ),
        CheckConstraint(
            "tipo_documento_otros IS NULL OR char_length(tipo_documento_otros) <= 100",
            name="ck_other_charge_tipo_otros_length"
        ),
        CheckConstraint(
            "tercero_nombre IS NULL OR char_length(tercero_nombre) <= 100",
            name="ck_other_charge_tercero_nombre_length"
        ),
        CheckConstraint(
            "tercero_numero_identificacion IS NULL OR char_length(tercero_numero_identificacion) <= 20",
            name="ck_other_charge_tercero_id_length"
        ),
        CheckConstraint(
            "(tercero_tipo_identificacion IS NULL AND tercero_numero_identificacion IS NULL AND tercero_nombre IS NULL) OR " +
            "(tercero_tipo_identificacion IS NOT NULL AND tercero_numero_identificacion IS NOT NULL)",
            name="ck_other_charge_tercero_consistency"
        ),
        
        # Performance indexes
        Index("idx_otros_cargos_documento_id", "documento_id"),
        Index("idx_otros_cargos_tipo", "tipo_documento"),
        Index("idx_otros_cargos_tercero_id", "tercero_numero_identificacion"),
        Index("idx_otros_cargos_monto", "monto_cargo"),
        Index("idx_otros_cargos_created_at", "created_at"),
        
        # Composite indexes for common queries
        Index("idx_otros_cargos_documento_tipo", "documento_id", "tipo_documento"),
        Index("idx_otros_cargos_tercero_tipo", "tercero_tipo_identificacion", "tercero_numero_identificacion"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentOtherCharge(id={self.id}, tipo={self.tipo_documento.value}, monto={self.monto_cargo})>"
    
    def __str__(self) -> str:
        return f"{self.get_charge_type_name()}: {self.monto_cargo}"
    
    @property
    def has_third_party(self) -> bool:
        """Check if charge involves a third party"""
        return (
            self.tercero_tipo_identificacion is not None and
            self.tercero_numero_identificacion is not None
        )
    
    @property
    def is_percentage_based(self) -> bool:
        """Check if charge is calculated as percentage"""
        return self.porcentaje is not None
    
    @property
    def requires_other_description(self) -> bool:
        """Check if 'otros' description is required"""
        return self.tipo_documento == OtherChargeType.OTROS
    
    @property
    def is_stamp(self) -> bool:
        """Check if charge is a stamp (timbre)"""
        return self.tipo_documento in [
            OtherChargeType.TIMBRE_CRUZ_ROJA,
            OtherChargeType.TIMBRE_BOMBEROS,
            OtherChargeType.TIMBRES_COLEGIOS_PROFESIONALES
        ]
    
    @property
    def is_tax(self) -> bool:
        """Check if charge is a tax"""
        return self.tipo_documento in [
            OtherChargeType.CONTRIBUCION_PARAFISCAL,
            OtherChargeType.IMPUESTO_SERVICIO_10_PERCENT
        ]
    
    def get_charge_type_name(self) -> str:
        """Get human-readable charge type name"""
        type_names = {
            OtherChargeType.CONTRIBUCION_PARAFISCAL: "Contribución Parafiscal",
            OtherChargeType.TIMBRE_CRUZ_ROJA: "Timbre Cruz Roja",
            OtherChargeType.TIMBRE_BOMBEROS: "Timbre Bomberos",
            OtherChargeType.COBRO_TERCERO: "Cobro a Tercero",
            OtherChargeType.GASTOS_EXPORTACION: "Gastos de Exportación",
            OtherChargeType.IMPUESTO_SERVICIO_10_PERCENT: "Impuesto al Servicio 10%",
            OtherChargeType.TIMBRES_COLEGIOS_PROFESIONALES: "Timbres Colegios Profesionales",
            OtherChargeType.DEPOSITOS_GARANTIA: "Depósitos de Garantía",
            OtherChargeType.MULTAS_SANCIONES: "Multas y Sanciones",
            OtherChargeType.INTERESES_MORATORIOS: "Intereses Moratorios",
            OtherChargeType.OTROS: "Otros Cargos"
        }
        return type_names.get(self.tipo_documento, "Cargo Desconocido")
    
    def get_third_party_info(self) -> Optional[dict]:
        """Get third party information as dictionary"""
        if not self.has_third_party:
            return None
        
        return {
            "tipo_identificacion": self.tercero_tipo_identificacion.value,
            "numero_identificacion": self.tercero_numero_identificacion,
            "nombre": self.tercero_nombre
        }
    
    def validate_charge_data(self) -> bool:
        """Validate charge data consistency"""
        # Check if 'otros' description is provided when required
        if self.tipo_documento == OtherChargeType.OTROS:
            if not self.tipo_documento_otros or len(self.tipo_documento_otros.strip()) == 0:
                return False
        
        # Validate charge amount is positive
        if self.monto_cargo < 0:
            return False
        
        # Validate percentage range
        if self.porcentaje is not None and (self.porcentaje < 0 or self.porcentaje > 100):
            return False
        
        # Validate detail length
        if len(self.detalle) == 0 or len(self.detalle) > 160:
            return False
        
        # Validate third party data consistency
        if self.tercero_tipo_identificacion is not None:
            if not self.tercero_numero_identificacion:
                return False
        
        if self.tercero_numero_identificacion is not None:
            if not self.tercero_tipo_identificacion:
                return False
        
        # Validate field lengths
        if self.tipo_documento_otros and len(self.tipo_documento_otros) > 100:
            return False
        
        if self.tercero_nombre and len(self.tercero_nombre) > 100:
            return False
        
        if self.tercero_numero_identificacion and len(self.tercero_numero_identificacion) > 20:
            return False
        
        return True
    
    def calculate_charge_amount(self, base_amount: Decimal) -> Decimal:
        """Calculate charge amount based on percentage if applicable"""
        if self.is_percentage_based and self.porcentaje is not None:
            return base_amount * (self.porcentaje / 100)
        else:
            return self.monto_cargo
    
    def set_third_party(self, tipo_identificacion: IdentificationType, 
                       numero_identificacion: str, nombre: str = None) -> bool:
        """Set third party information"""
        if len(numero_identificacion) > 20:
            return False
        
        if nombre and len(nombre) > 100:
            return False
        
        self.tercero_tipo_identificacion = tipo_identificacion
        self.tercero_numero_identificacion = numero_identificacion
        self.tercero_nombre = nombre
        
        return True
    
    def clear_third_party(self) -> None:
        """Clear third party information"""
        self.tercero_tipo_identificacion = None
        self.tercero_numero_identificacion = None
        self.tercero_nombre = None
    
    def to_dict(self) -> dict:
        """Convert charge to dictionary for API responses"""
        return {
            "id": str(self.id),
            "tipo_documento": self.tipo_documento.value,
            "tipo_documento_nombre": self.get_charge_type_name(),
            "tipo_documento_otros": self.tipo_documento_otros,
            "tercero": self.get_third_party_info(),
            "detalle": self.detalle,
            "porcentaje": float(self.porcentaje) if self.porcentaje else None,
            "monto_cargo": float(self.monto_cargo),
            "has_third_party": self.has_third_party,
            "is_percentage_based": self.is_percentage_based,
            "is_stamp": self.is_stamp,
            "is_tax": self.is_tax,
            "created_at": self.created_at.isoformat()
        }