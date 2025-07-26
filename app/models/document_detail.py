"""
DocumentDetail model for invoice line items with product identification and pricing
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Numeric, JSON,
    ForeignKey, CheckConstraint, Index, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class TransactionType(enum.Enum):
    """Transaction types for special tax treatments"""
    VENTA_NORMAL = "01"
    AUTOCONSUMO_EXENTO = "02"
    AUTOCONSUMO_GRAVADO = "03"
    AUTOCONSUMO_SERVICIOS_EXENTO = "04"
    AUTOCONSUMO_SERVICIOS_GRAVADO = "05"
    CUOTA_MEMBRESIA = "06"
    CUOTA_MEMBRESIA_EXENTA = "07"
    BIENES_CAPITAL_EMISOR = "08"
    BIENES_CAPITAL_RECEPTOR = "09"
    BIENES_CAPITAL_AMBOS = "10"
    AUTOCONSUMO_BIENES_CAPITAL_EXENTO = "11"
    BIENES_CAPITAL_TERCEROS_EXENTO = "12"
    SIN_CONTRAPRESTACION_TERCEROS = "13"


class CommercialCodeType(enum.Enum):
    """Commercial code types"""
    CODIGO_VENDEDOR = "01"
    CODIGO_COMPRADOR = "02"
    CODIGO_ASIGNADO_INDUSTRIA = "03"
    CODIGO_USO_INTERNO = "04"
    OTROS = "99"


class DocumentDetail(Base):
    """
    Document line items with product identification, pricing, and special fields
    
    Supports all product types including pharmaceuticals, vehicles, and package components.
    Includes CABYS codes, commercial codes, quantities, pricing, and discounts.
    
    Requirements: 17.1, 11.2, 17.2, 14.3, 17.4, 17.5
    """
    __tablename__ = "detalle_documentos"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Document relationship
    documento_id = Column(UUID(as_uuid=True), ForeignKey("documentos.id", ondelete="CASCADE"),
                         nullable=False, index=True, comment="Parent document ID")
    
    # Line identification (Requirements 17.1)
    numero_linea = Column(Integer, nullable=False, comment="Line number (1-1000)")
    
    # Product identification (Requirements 11.2, 17.1)
    codigo_cabys = Column(String(13), nullable=False, index=True,
                         comment="13-digit CABYS code for product/service classification")
    descripcion = Column(Text, nullable=False, comment="Product/service description (3-200 chars)")
    
    # Commercial codes (up to 5 per line item) (Requirement 17.2)
    codigos_comerciales = Column(JSON, nullable=True,
                               comment="Array of commercial codes: [{tipo, codigo}, ...]")
    
    # Quantities and measures (Requirements 17.1)
    cantidad = Column(Numeric(16, 3), nullable=False, comment="Quantity (must be positive)")
    unidad_medida = Column(String(10), nullable=False, comment="Official unit of measure code")
    unidad_medida_comercial = Column(String(20), nullable=True,
                                   comment="Commercial unit description")
    
    # Pricing (Requirements 17.1, 17.2)
    precio_unitario = Column(Numeric(18, 5), nullable=False,
                           comment="Unit price (can be 0 for free items)")
    monto_total = Column(Numeric(18, 5), nullable=False,
                        comment="Line total (cantidad * precio_unitario)")
    
    # Discount information (Requirement 14.3)
    monto_descuento = Column(Numeric(18, 5), nullable=False, default=Decimal('0'),
                           comment="Discount amount")
    naturaleza_descuento = Column(String(80), nullable=True,
                                comment="Discount description/reason")
    
    # Special transaction type (Requirements 17.4)
    tipo_transaccion = Column(SQLEnum(TransactionType), nullable=True,
                            comment="Special transaction type for tax treatment")
    
    # Vehicle identification (Requirement 17.5)
    numero_vin_serie = Column(String(17), nullable=True,
                            comment="VIN or serial number for vehicles (max 17 chars)")
    
    # Pharmaceutical information (Requirement 17.5)
    registro_medicamento = Column(String(100), nullable=True,
                                comment="Medicine registration number")
    forma_farmaceutica = Column(String(3), nullable=True,
                              comment="Pharmaceutical form code")
    
    # Package/combo components (DetalleSurtido) (Requirement 17.6)
    detalle_surtido = Column(JSON, nullable=True,
                           comment="Package components: [{codigo_cabys, cantidad, unidad_medida, descripcion}, ...]")
    
    # Additional product information
    codigo_producto_interno = Column(String(50), nullable=True,
                                   comment="Internal product code")
    marca = Column(String(100), nullable=True, comment="Product brand")
    modelo = Column(String(100), nullable=True, comment="Product model")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now())
    
    # Relationships
    documento = relationship("Document", back_populates="detalles")
    # impuestos = relationship("DocumentTax", back_populates="detalle", cascade="all, delete-orphan")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "numero_linea >= 1 AND numero_linea <= 1000",
            name="ck_detail_numero_linea_range"
        ),
        CheckConstraint(
            "char_length(codigo_cabys) = 13",
            name="ck_detail_cabys_length"
        ),
        CheckConstraint(
            "codigo_cabys ~ '^\\d{13}$'",
            name="ck_detail_cabys_format"
        ),
        CheckConstraint(
            "char_length(descripcion) >= 3 AND char_length(descripcion) <= 200",
            name="ck_detail_descripcion_length"
        ),
        CheckConstraint(
            "cantidad > 0",
            name="ck_detail_cantidad_positive"
        ),
        CheckConstraint(
            "precio_unitario >= 0",
            name="ck_detail_precio_positive"
        ),
        CheckConstraint(
            "monto_total >= 0",
            name="ck_detail_monto_total_positive"
        ),
        CheckConstraint(
            "monto_descuento >= 0",
            name="ck_detail_descuento_positive"
        ),
        CheckConstraint(
            "monto_descuento <= monto_total",
            name="ck_detail_descuento_not_exceed_total"
        ),
        CheckConstraint(
            "numero_vin_serie IS NULL OR char_length(numero_vin_serie) <= 17",
            name="ck_detail_vin_length"
        ),
        CheckConstraint(
            "registro_medicamento IS NULL OR char_length(registro_medicamento) <= 100",
            name="ck_detail_medicina_length"
        ),
        CheckConstraint(
            "forma_farmaceutica IS NULL OR char_length(forma_farmaceutica) <= 3",
            name="ck_detail_forma_farmaceutica_length"
        ),
        
        # Unique constraint for line numbers within a document
        CheckConstraint(
            "numero_linea > 0",
            name="ck_detail_numero_linea_positive"
        ),
        
        # Performance indexes
        Index("idx_detalle_documento_id", "documento_id"),
        Index("idx_detalle_cabys", "codigo_cabys"),
        Index("idx_detalle_numero_linea", "documento_id", "numero_linea", unique=True),
        Index("idx_detalle_descripcion_gin", "descripcion", postgresql_using="gin",
              postgresql_ops={"descripcion": "gin_trgm_ops"}),
        Index("idx_detalle_created_at", "created_at"),
        
        # Indexes for special fields
        Index("idx_detalle_vin", "numero_vin_serie"),
        Index("idx_detalle_medicina", "registro_medicamento"),
        Index("idx_detalle_producto_interno", "codigo_producto_interno"),
        
        # Composite indexes for common queries
        Index("idx_detalle_documento_linea", "documento_id", "numero_linea"),
        Index("idx_detalle_cabys_descripcion", "codigo_cabys", "descripcion"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentDetail(id={self.id}, documento_id={self.documento_id}, linea={self.numero_linea})>"
    
    def __str__(self) -> str:
        return f"Línea {self.numero_linea}: {self.descripcion[:50]}..."
    
    @property
    def has_discount(self) -> bool:
        """Check if line item has discount"""
        return self.monto_descuento > 0
    
    @property
    def is_vehicle(self) -> bool:
        """Check if line item is a vehicle"""
        return self.numero_vin_serie is not None
    
    @property
    def is_medicine(self) -> bool:
        """Check if line item is a pharmaceutical product"""
        return self.registro_medicamento is not None
    
    @property
    def is_package(self) -> bool:
        """Check if line item is a package/combo"""
        return self.detalle_surtido is not None
    
    @property
    def has_commercial_codes(self) -> bool:
        """Check if line item has commercial codes"""
        return self.codigos_comerciales is not None and len(self.codigos_comerciales) > 0
    
    @property
    def net_amount(self) -> Decimal:
        """Get net amount after discount"""
        return self.monto_total - self.monto_descuento
    
    @property
    def discount_percentage(self) -> float:
        """Calculate discount percentage"""
        if self.monto_total == 0:
            return 0.0
        return float((self.monto_descuento / self.monto_total) * 100)
    
    def validate_cabys_code(self) -> bool:
        """Validate CABYS code format"""
        import re
        return bool(re.match(r'^\d{13}$', self.codigo_cabys))
    
    def validate_commercial_codes(self) -> bool:
        """Validate commercial codes structure"""
        if not self.codigos_comerciales:
            return True
        
        if not isinstance(self.codigos_comerciales, list):
            return False
        
        if len(self.codigos_comerciales) > 5:
            return False
        
        for code in self.codigos_comerciales:
            if not isinstance(code, dict):
                return False
            if 'tipo' not in code or 'codigo' not in code:
                return False
            if code['tipo'] not in ['01', '02', '03', '04', '99']:
                return False
            if not isinstance(code['codigo'], str) or len(code['codigo']) > 20:
                return False
        
        return True
    
    def validate_package_components(self) -> bool:
        """Validate package components structure"""
        if not self.detalle_surtido:
            return True
        
        if not isinstance(self.detalle_surtido, list):
            return False
        
        if len(self.detalle_surtido) > 20:
            return False
        
        for component in self.detalle_surtido:
            if not isinstance(component, dict):
                return False
            
            required_fields = ['codigo_cabys', 'cantidad', 'unidad_medida', 'descripcion']
            for field in required_fields:
                if field not in component:
                    return False
            
            # Validate CABYS code format
            import re
            if not re.match(r'^\d{13}$', component['codigo_cabys']):
                return False
            
            # Validate quantity is positive
            try:
                cantidad = float(component['cantidad'])
                if cantidad <= 0:
                    return False
            except (ValueError, TypeError):
                return False
            
            # Validate description length
            descripcion = component['descripcion']
            if not isinstance(descripcion, str) or len(descripcion) < 3 or len(descripcion) > 200:
                return False
        
        return True
    
    def add_commercial_code(self, tipo: str, codigo: str) -> bool:
        """Add a commercial code to the line item"""
        if not self.codigos_comerciales:
            self.codigos_comerciales = []
        
        if len(self.codigos_comerciales) >= 5:
            return False
        
        if tipo not in ['01', '02', '03', '04', '99']:
            return False
        
        if len(codigo) > 20:
            return False
        
        # Check if code type already exists
        for existing_code in self.codigos_comerciales:
            if existing_code['tipo'] == tipo:
                return False
        
        self.codigos_comerciales.append({
            'tipo': tipo,
            'codigo': codigo
        })
        return True
    
    def add_package_component(self, codigo_cabys: str, cantidad: float, 
                            unidad_medida: str, descripcion: str) -> bool:
        """Add a component to package details"""
        if not self.detalle_surtido:
            self.detalle_surtido = []
        
        if len(self.detalle_surtido) >= 20:
            return False
        
        # Validate inputs
        import re
        if not re.match(r'^\d{13}$', codigo_cabys):
            return False
        
        if cantidad <= 0:
            return False
        
        if len(descripcion) < 3 or len(descripcion) > 200:
            return False
        
        self.detalle_surtido.append({
            'codigo_cabys': codigo_cabys,
            'cantidad': cantidad,
            'unidad_medida': unidad_medida,
            'descripcion': descripcion
        })
        return True
    
    def calculate_line_total(self) -> Decimal:
        """Calculate line total from quantity and unit price"""
        return self.cantidad * self.precio_unitario
    
    def apply_discount(self, discount_amount: Decimal, reason: str = None) -> bool:
        """Apply discount to line item"""
        if discount_amount < 0 or discount_amount > self.monto_total:
            return False
        
        self.monto_descuento = discount_amount
        if reason:
            self.naturaleza_descuento = reason
        
        return True
    
    def get_commercial_code_by_type(self, tipo: str) -> Optional[str]:
        """Get commercial code by type"""
        if not self.codigos_comerciales:
            return None
        
        for code in self.codigos_comerciales:
            if code['tipo'] == tipo:
                return code['codigo']
        
        return None
    
    def to_dict(self) -> dict:
        """Convert line item to dictionary for API responses"""
        return {
            "id": str(self.id),
            "numero_linea": self.numero_linea,
            "codigo_cabys": self.codigo_cabys,
            "descripcion": self.descripcion,
            "cantidad": float(self.cantidad),
            "unidad_medida": self.unidad_medida,
            "unidad_medida_comercial": self.unidad_medida_comercial,
            "precio_unitario": float(self.precio_unitario),
            "monto_total": float(self.monto_total),
            "monto_descuento": float(self.monto_descuento),
            "naturaleza_descuento": self.naturaleza_descuento,
            "tipo_transaccion": self.tipo_transaccion.value if self.tipo_transaccion else None,
            "numero_vin_serie": self.numero_vin_serie,
            "registro_medicamento": self.registro_medicamento,
            "forma_farmaceutica": self.forma_farmaceutica,
            "codigos_comerciales": self.codigos_comerciales,
            "detalle_surtido": self.detalle_surtido,
            "net_amount": float(self.net_amount),
            "discount_percentage": self.discount_percentage,
            "is_vehicle": self.is_vehicle,
            "is_medicine": self.is_medicine,
            "is_package": self.is_package
        }