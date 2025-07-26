"""
DocumentTax model supporting all Costa Rican tax types and calculations
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


class TaxCode(enum.Enum):
    """Costa Rican tax codes"""
    IVA = "01"
    SELECTIVO_CONSUMO = "02"
    UNICO_COMBUSTIBLES = "03"
    ESPECIFICO_BEBIDAS_ALCOHOLICAS = "04"
    ESPECIFICO_BEBIDAS_SIN_ALCOHOL = "05"
    PRODUCTOS_TABACO = "06"
    IVA_CALCULO_ESPECIAL = "07"
    IVA_BIENES_USADOS = "08"
    ESPECIFICO_CEMENTO = "12"
    OTROS = "99"


class IVATariffCode(enum.Enum):
    """IVA tariff codes"""
    TARIFA_0_PERCENT = "01"
    TARIFA_REDUCIDA_1_PERCENT = "02"
    TARIFA_REDUCIDA_2_PERCENT = "03"
    TARIFA_REDUCIDA_4_PERCENT = "04"
    TRANSITORIO_0_PERCENT = "05"
    TRANSITORIO_4_PERCENT = "06"
    TRANSITORIO_8_PERCENT = "07"
    TARIFA_GENERAL_13_PERCENT = "08"
    TARIFA_REDUCIDA_0_5_PERCENT = "09"
    TARIFA_EXENTA = "10"
    TARIFA_0_SIN_CREDITO = "11"


class DocumentTax(Base):
    """
    Tax information for document line items supporting all Costa Rican tax types
    
    Supports IVA, selective consumption taxes, specific taxes for fuel, alcohol,
    beverages, tobacco, cement, and special calculation methods.
    
    Requirements: 14.1, 14.2
    """
    __tablename__ = "impuestos_documentos"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Line item relationship
    detalle_documento_id = Column(UUID(as_uuid=True), ForeignKey("detalle_documentos.id", ondelete="CASCADE"),
                                 nullable=False, index=True, comment="Document detail line item")
    
    # Tax identification (Requirements 14.1, 14.2)
    codigo_impuesto = Column(SQLEnum(TaxCode), nullable=False, index=True,
                           comment="Tax code: 01=IVA, 02=Selectivo, etc.")
    codigo_impuesto_otro = Column(String(100), nullable=True,
                                comment="Other tax code description (required when codigo = 99)")
    
    # IVA specific fields
    codigo_tarifa_iva = Column(SQLEnum(IVATariffCode), nullable=True,
                             comment="IVA tariff code (01-11) - required for IVA taxes")
    tarifa = Column(Numeric(4, 2), nullable=True,
                   comment="Tax rate percentage (0.00-99.99)")
    factor_calculo_iva = Column(Numeric(5, 4), nullable=True,
                              comment="IVA calculation factor for used goods regime")
    
    # Tax amount
    monto = Column(Numeric(18, 5), nullable=False, comment="Tax amount")
    
    # Specific tax data for non-tariff taxes (fuel, alcohol, beverages, tobacco, cement)
    cantidad_unidad_medida = Column(Numeric(7, 2), nullable=True,
                                  comment="Quantity in unit of measure for specific taxes")
    porcentaje = Column(Numeric(4, 2), nullable=True,
                       comment="Percentage for alcohol tax calculation")
    proporcion = Column(Numeric(5, 2), nullable=True,
                       comment="Proportion for alcohol tax calculation")
    volumen_unidad_consumo = Column(Numeric(7, 2), nullable=True,
                                  comment="Volume per consumption unit for beverage tax")
    impuesto_unidad = Column(Numeric(18, 5), nullable=True,
                           comment="Tax amount per unit for specific taxes")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    
    # Relationships
    detalle = relationship("DocumentDetail", back_populates="impuestos")
    exoneraciones = relationship("DocumentExemption", back_populates="impuesto", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "(codigo_impuesto != 'OTROS') OR (codigo_impuesto_otro IS NOT NULL)",
            name="ck_tax_codigo_otro_required"
        ),
        CheckConstraint(
            "(codigo_impuesto != 'IVA') OR (codigo_tarifa_iva IS NOT NULL)",
            name="ck_tax_iva_tarifa_required"
        ),
        CheckConstraint(
            "monto >= 0",
            name="ck_tax_monto_positive"
        ),
        CheckConstraint(
            "tarifa IS NULL OR (tarifa >= 0 AND tarifa <= 99.99)",
            name="ck_tax_tarifa_range"
        ),
        CheckConstraint(
            "factor_calculo_iva IS NULL OR (factor_calculo_iva >= 0 AND factor_calculo_iva <= 1)",
            name="ck_tax_factor_iva_range"
        ),
        CheckConstraint(
            "cantidad_unidad_medida IS NULL OR cantidad_unidad_medida >= 0",
            name="ck_tax_cantidad_positive"
        ),
        CheckConstraint(
            "porcentaje IS NULL OR (porcentaje >= 0 AND porcentaje <= 100)",
            name="ck_tax_porcentaje_range"
        ),
        CheckConstraint(
            "proporcion IS NULL OR proporcion >= 0",
            name="ck_tax_proporcion_positive"
        ),
        CheckConstraint(
            "volumen_unidad_consumo IS NULL OR volumen_unidad_consumo >= 0",
            name="ck_tax_volumen_positive"
        ),
        CheckConstraint(
            "impuesto_unidad IS NULL OR impuesto_unidad >= 0",
            name="ck_tax_impuesto_unidad_positive"
        ),
        CheckConstraint(
            "codigo_impuesto_otro IS NULL OR char_length(codigo_impuesto_otro) <= 100",
            name="ck_tax_codigo_otro_length"
        ),
        
        # Performance indexes
        Index("idx_impuestos_detalle_id", "detalle_documento_id"),
        Index("idx_impuestos_codigo", "codigo_impuesto"),
        Index("idx_impuestos_tarifa_iva", "codigo_tarifa_iva"),
        Index("idx_impuestos_monto", "monto"),
        Index("idx_impuestos_created_at", "created_at"),
        
        # Composite indexes for common queries
        Index("idx_impuestos_detalle_codigo", "detalle_documento_id", "codigo_impuesto"),
        Index("idx_impuestos_codigo_tarifa", "codigo_impuesto", "codigo_tarifa_iva"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentTax(id={self.id}, codigo={self.codigo_impuesto.value}, monto={self.monto})>"
    
    def __str__(self) -> str:
        return f"{self.get_tax_name()}: {self.monto}"
    
    @property
    def is_iva(self) -> bool:
        """Check if this is an IVA tax"""
        return self.codigo_impuesto in [TaxCode.IVA, TaxCode.IVA_CALCULO_ESPECIAL, TaxCode.IVA_BIENES_USADOS]
    
    @property
    def is_specific_tax(self) -> bool:
        """Check if this is a specific (unit-based) tax"""
        return self.codigo_impuesto in [
            TaxCode.UNICO_COMBUSTIBLES,
            TaxCode.ESPECIFICO_BEBIDAS_ALCOHOLICAS,
            TaxCode.ESPECIFICO_BEBIDAS_SIN_ALCOHOL,
            TaxCode.PRODUCTOS_TABACO,
            TaxCode.ESPECIFICO_CEMENTO
        ]
    
    @property
    def is_selective_tax(self) -> bool:
        """Check if this is a selective consumption tax"""
        return self.codigo_impuesto == TaxCode.SELECTIVO_CONSUMO
    
    @property
    def requires_tariff_code(self) -> bool:
        """Check if tax requires IVA tariff code"""
        return self.is_iva
    
    @property
    def requires_specific_data(self) -> bool:
        """Check if tax requires specific tax calculation data"""
        return self.is_specific_tax
    
    @property
    def effective_rate(self) -> Optional[Decimal]:
        """Get effective tax rate percentage"""
        if self.tarifa is not None:
            return self.tarifa
        
        # Default rates for IVA tariff codes
        if self.codigo_tarifa_iva:
            default_rates = {
                IVATariffCode.TARIFA_0_PERCENT: Decimal('0.00'),
                IVATariffCode.TARIFA_REDUCIDA_1_PERCENT: Decimal('1.00'),
                IVATariffCode.TARIFA_REDUCIDA_2_PERCENT: Decimal('2.00'),
                IVATariffCode.TARIFA_REDUCIDA_4_PERCENT: Decimal('4.00'),
                IVATariffCode.TRANSITORIO_0_PERCENT: Decimal('0.00'),
                IVATariffCode.TRANSITORIO_4_PERCENT: Decimal('4.00'),
                IVATariffCode.TRANSITORIO_8_PERCENT: Decimal('8.00'),
                IVATariffCode.TARIFA_GENERAL_13_PERCENT: Decimal('13.00'),
                IVATariffCode.TARIFA_REDUCIDA_0_5_PERCENT: Decimal('0.50'),
                IVATariffCode.TARIFA_EXENTA: Decimal('0.00'),
                IVATariffCode.TARIFA_0_SIN_CREDITO: Decimal('0.00')
            }
            return default_rates.get(self.codigo_tarifa_iva)
        
        return None
    
    def get_tax_name(self) -> str:
        """Get human-readable tax name"""
        tax_names = {
            TaxCode.IVA: "Impuesto al Valor Agregado",
            TaxCode.SELECTIVO_CONSUMO: "Impuesto Selectivo de Consumo",
            TaxCode.UNICO_COMBUSTIBLES: "Impuesto Único a los Combustibles",
            TaxCode.ESPECIFICO_BEBIDAS_ALCOHOLICAS: "Impuesto Específico a las Bebidas Alcohólicas",
            TaxCode.ESPECIFICO_BEBIDAS_SIN_ALCOHOL: "Impuesto Específico a las Bebidas sin Alcohol",
            TaxCode.PRODUCTOS_TABACO: "Impuesto a los Productos de Tabaco",
            TaxCode.IVA_CALCULO_ESPECIAL: "IVA Cálculo Especial",
            TaxCode.IVA_BIENES_USADOS: "IVA Régimen de Bienes Usados",
            TaxCode.ESPECIFICO_CEMENTO: "Impuesto Específico al Cemento",
            TaxCode.OTROS: "Otros Impuestos"
        }
        return tax_names.get(self.codigo_impuesto, "Impuesto Desconocido")
    
    def get_tariff_name(self) -> str:
        """Get human-readable IVA tariff name"""
        if not self.codigo_tarifa_iva:
            return "Sin tarifa"
        
        tariff_names = {
            IVATariffCode.TARIFA_0_PERCENT: "Tarifa 0%",
            IVATariffCode.TARIFA_REDUCIDA_1_PERCENT: "Tarifa Reducida 1%",
            IVATariffCode.TARIFA_REDUCIDA_2_PERCENT: "Tarifa Reducida 2%",
            IVATariffCode.TARIFA_REDUCIDA_4_PERCENT: "Tarifa Reducida 4%",
            IVATariffCode.TRANSITORIO_0_PERCENT: "Transitorio 0%",
            IVATariffCode.TRANSITORIO_4_PERCENT: "Transitorio 4%",
            IVATariffCode.TRANSITORIO_8_PERCENT: "Transitorio 8%",
            IVATariffCode.TARIFA_GENERAL_13_PERCENT: "Tarifa General 13%",
            IVATariffCode.TARIFA_REDUCIDA_0_5_PERCENT: "Tarifa Reducida 0.5%",
            IVATariffCode.TARIFA_EXENTA: "Exenta",
            IVATariffCode.TARIFA_0_SIN_CREDITO: "0% sin derecho a crédito"
        }
        return tariff_names.get(self.codigo_tarifa_iva, "Tarifa Desconocida")
    
    def validate_tax_data(self) -> bool:
        """Validate tax data consistency"""
        # Check if 'otros' description is provided when required
        if self.codigo_impuesto == TaxCode.OTROS:
            if not self.codigo_impuesto_otro or len(self.codigo_impuesto_otro.strip()) == 0:
                return False
        
        # Check if IVA tariff code is provided for IVA taxes
        if self.is_iva and not self.codigo_tarifa_iva:
            return False
        
        # Check if specific tax data is provided for specific taxes
        if self.is_specific_tax:
            if self.codigo_impuesto == TaxCode.ESPECIFICO_BEBIDAS_ALCOHOLICAS:
                # Alcohol tax requires percentage and proportion
                if self.porcentaje is None or self.proporcion is None:
                    return False
            elif self.codigo_impuesto == TaxCode.ESPECIFICO_BEBIDAS_SIN_ALCOHOL:
                # Non-alcohol beverage tax requires volume per consumption unit
                if self.volumen_unidad_consumo is None:
                    return False
            
            # All specific taxes should have unit tax amount
            if self.impuesto_unidad is None:
                return False
        
        # Validate numeric ranges
        if self.monto < 0:
            return False
        
        if self.tarifa is not None and (self.tarifa < 0 or self.tarifa > 99.99):
            return False
        
        if self.factor_calculo_iva is not None and (self.factor_calculo_iva < 0 or self.factor_calculo_iva > 1):
            return False
        
        return True
    
    def calculate_tax_amount(self, base_amount: Decimal, quantity: Decimal = None) -> Decimal:
        """Calculate tax amount based on base amount and tax configuration"""
        if self.is_specific_tax and self.impuesto_unidad is not None:
            # Specific taxes are calculated per unit
            if quantity is None:
                return Decimal('0')
            return self.impuesto_unidad * quantity
        
        elif self.is_iva and self.factor_calculo_iva is not None:
            # Used goods regime uses factor calculation
            return base_amount * self.factor_calculo_iva
        
        elif self.effective_rate is not None:
            # Percentage-based calculation
            return base_amount * (self.effective_rate / 100)
        
        else:
            # Return stored amount if no calculation method available
            return self.monto
    
    def to_dict(self) -> dict:
        """Convert tax to dictionary for API responses"""
        return {
            "id": str(self.id),
            "codigo_impuesto": self.codigo_impuesto.value,
            "codigo_impuesto_nombre": self.get_tax_name(),
            "codigo_impuesto_otro": self.codigo_impuesto_otro,
            "codigo_tarifa_iva": self.codigo_tarifa_iva.value if self.codigo_tarifa_iva else None,
            "codigo_tarifa_iva_nombre": self.get_tariff_name(),
            "tarifa": float(self.tarifa) if self.tarifa else None,
            "factor_calculo_iva": float(self.factor_calculo_iva) if self.factor_calculo_iva else None,
            "monto": float(self.monto),
            "cantidad_unidad_medida": float(self.cantidad_unidad_medida) if self.cantidad_unidad_medida else None,
            "porcentaje": float(self.porcentaje) if self.porcentaje else None,
            "proporcion": float(self.proporcion) if self.proporcion else None,
            "volumen_unidad_consumo": float(self.volumen_unidad_consumo) if self.volumen_unidad_consumo else None,
            "impuesto_unidad": float(self.impuesto_unidad) if self.impuesto_unidad else None,
            "effective_rate": float(self.effective_rate) if self.effective_rate else None,
            "is_iva": self.is_iva,
            "is_specific_tax": self.is_specific_tax,
            "is_selective_tax": self.is_selective_tax,
            "created_at": self.created_at.isoformat()
        }