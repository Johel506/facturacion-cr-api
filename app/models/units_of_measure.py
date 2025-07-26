"""
Units of Measure model for Costa Rican electronic invoicing system

This model handles the official units of measure as defined in the
RTC 443:2010 standard used in Costa Rica's electronic invoicing system.
Supports metric, commercial, and service-specific units.

Requirements: 17.1
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Numeric, Integer,
    CheckConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UnitsOfMeasure(Base):
    """
    Units of Measure model for official Costa Rican units
    
    Stores the official units of measure as defined in RTC 443:2010 standard
    used for product quantities in electronic invoicing. Includes metric units,
    commercial units, and service-specific units.
    
    The system supports over 100 different units including:
    - Metric units (kg, L, m, m², m³, etc.)
    - Commercial units (Unid, dozen, pack, etc.)
    - Time units (h, day, month, etc.)
    - Service units (Sp, St, etc.)
    
    Requirements:
    - 17.1: Support all official units of measure from RTC 443:2010 standard
    """
    __tablename__ = "unidades_medida"
    
    # Primary key - Unit code
    codigo = Column(String(10), primary_key=True,
                   comment="Official unit code (max 10 characters)")
    
    # Unit information
    descripcion = Column(String(200), nullable=False,
                        comment="Unit description in Spanish")
    descripcion_ingles = Column(String(200), nullable=True,
                               comment="Unit description in English")
    simbolo = Column(String(10), nullable=True,
                    comment="Unit symbol (e.g., 'kg', 'L', 'm')")
    
    # Classification
    categoria = Column(String(50), nullable=False,
                      comment="Unit category (metric, commercial, time, service, etc.)")
    tipo_medida = Column(String(50), nullable=True,
                        comment="Type of measurement (weight, volume, length, area, etc.)")
    
    # Conversion information
    unidad_base = Column(String(10), nullable=True,
                        comment="Base unit for conversion (if applicable)")
    factor_conversion = Column(Numeric(18, 8), nullable=True,
                              comment="Conversion factor to base unit")
    
    # Usage information
    uso_comun = Column(Boolean, nullable=False, default=False,
                      comment="Whether this is a commonly used unit")
    uso_productos = Column(Boolean, nullable=False, default=True,
                          comment="Whether this unit can be used for products")
    uso_servicios = Column(Boolean, nullable=False, default=True,
                          comment="Whether this unit can be used for services")
    
    # Validation rules
    permite_decimales = Column(Boolean, nullable=False, default=True,
                              comment="Whether decimal quantities are allowed")
    cantidad_minima = Column(Numeric(16, 3), nullable=True,
                            comment="Minimum allowed quantity")
    cantidad_maxima = Column(Numeric(16, 3), nullable=True,
                            comment="Maximum allowed quantity")
    
    # Status and versioning
    activo = Column(Boolean, nullable=False, default=True,
                   comment="Whether this unit is currently active")
    version_rtc = Column(String(10), nullable=True,
                        comment="RTC standard version (e.g., '443:2010')")
    fecha_vigencia_desde = Column(DateTime(timezone=True), nullable=True,
                                 comment="Date when this unit became effective")
    fecha_vigencia_hasta = Column(DateTime(timezone=True), nullable=True,
                                comment="Date when this unit expires (if applicable)")
    
    # Usage statistics
    veces_usado = Column(Integer, nullable=False, default=0,
                        comment="Number of times this unit has been used")
    ultimo_uso = Column(DateTime(timezone=True), nullable=True,
                       comment="Last time this unit was used")
    
    # Additional metadata
    notas = Column(Text, nullable=True,
                  comment="Additional notes or usage guidelines")
    ejemplos_uso = Column(Text, nullable=True,
                         comment="Examples of when to use this unit")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now(),
                       comment="Record last update timestamp")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "char_length(codigo) >= 1 AND char_length(codigo) <= 10",
            name="ck_unidad_codigo_length"
        ),
        CheckConstraint(
            "char_length(descripcion) >= 2",
            name="ck_unidad_descripcion_length"
        ),
        CheckConstraint(
            "categoria IN ('metric', 'commercial', 'time', 'service', 'area', 'volume', 'weight', 'length', 'other')",
            name="ck_unidad_categoria_valid"
        ),
        CheckConstraint(
            "factor_conversion IS NULL OR factor_conversion > 0",
            name="ck_unidad_factor_conversion_positive"
        ),
        CheckConstraint(
            "cantidad_minima IS NULL OR cantidad_minima >= 0",
            name="ck_unidad_cantidad_minima_positive"
        ),
        CheckConstraint(
            "cantidad_maxima IS NULL OR cantidad_maxima > 0",
            name="ck_unidad_cantidad_maxima_positive"
        ),
        CheckConstraint(
            "cantidad_minima IS NULL OR cantidad_maxima IS NULL OR cantidad_maxima > cantidad_minima",
            name="ck_unidad_cantidad_range_valid"
        ),
        CheckConstraint(
            "veces_usado >= 0",
            name="ck_unidad_veces_usado_positive"
        ),
        CheckConstraint(
            "fecha_vigencia_hasta IS NULL OR fecha_vigencia_hasta > fecha_vigencia_desde",
            name="ck_unidad_fechas_vigencia_valid"
        ),
        
        # Performance indexes
        Index("idx_unidad_codigo", "codigo"),  # Primary key index (automatic)
        Index("idx_unidad_activo", "activo"),
        Index("idx_unidad_categoria", "categoria"),
        Index("idx_unidad_tipo_medida", "tipo_medida"),
        Index("idx_unidad_uso_comun", "uso_comun"),
        Index("idx_unidad_uso_productos", "uso_productos"),
        Index("idx_unidad_uso_servicios", "uso_servicios"),
        Index("idx_unidad_veces_usado", "veces_usado"),
        Index("idx_unidad_ultimo_uso", "ultimo_uso"),
        Index("idx_unidad_descripcion", "descripcion"),
        Index("idx_unidad_simbolo", "simbolo"),
        Index("idx_unidad_version", "version_rtc"),
        Index("idx_unidad_vigencia", "fecha_vigencia_desde", "fecha_vigencia_hasta"),
        
        # Composite indexes for common queries
        Index("idx_unidad_activo_categoria", "activo", "categoria"),
        Index("idx_unidad_activo_uso_comun", "activo", "uso_comun"),
        Index("idx_unidad_activo_productos", "activo", "uso_productos"),
        Index("idx_unidad_activo_servicios", "activo", "uso_servicios"),
        Index("idx_unidad_categoria_uso", "categoria", "uso_comun"),
        Index("idx_unidad_popular", "activo", "veces_usado"),
        
        # Full-text search indexes
        Index("idx_unidad_descripcion_gin", "descripcion", postgresql_using="gin",
              postgresql_ops={"descripcion": "gin_trgm_ops"}),
        Index("idx_unidad_search_tsvector",
              func.to_tsvector('spanish', 
                              func.concat(
                                  func.coalesce("descripcion", ''), ' ',
                                  func.coalesce("descripcion_ingles", ''), ' ',
                                  func.coalesce("simbolo", ''), ' ',
                                  func.coalesce("codigo", '')
                              )),
              postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<UnitsOfMeasure(codigo='{self.codigo}', descripcion='{self.descripcion}')>"
    
    def __str__(self) -> str:
        if self.simbolo:
            return f"{self.codigo} ({self.simbolo}) - {self.descripcion}"
        return f"{self.codigo} - {self.descripcion}"
    
    @property
    def is_active(self) -> bool:
        """Check if the unit is currently active and valid"""
        if not self.activo:
            return False
        
        now = datetime.now(timezone.utc)
        
        # Check validity period
        if self.fecha_vigencia_desde and now < self.fecha_vigencia_desde:
            return False
        
        if self.fecha_vigencia_hasta and now > self.fecha_vigencia_hasta:
            return False
        
        return True
    
    @property
    def display_name(self) -> str:
        """Get display name with symbol if available"""
        if self.simbolo and self.simbolo != self.codigo:
            return f"{self.descripcion} ({self.simbolo})"
        return self.descripcion
    
    def validate_quantity(self, cantidad: Decimal) -> tuple[bool, Optional[str]]:
        """
        Validate a quantity against this unit's rules
        
        Args:
            cantidad: Quantity to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if cantidad <= 0:
            return False, "Quantity must be greater than zero"
        
        # Check decimal places
        if not self.permite_decimales and cantidad % 1 != 0:
            return False, f"Unit '{self.codigo}' does not allow decimal quantities"
        
        # Check minimum quantity
        if self.cantidad_minima is not None and cantidad < self.cantidad_minima:
            return False, f"Quantity must be at least {self.cantidad_minima} {self.codigo}"
        
        # Check maximum quantity
        if self.cantidad_maxima is not None and cantidad > self.cantidad_maxima:
            return False, f"Quantity cannot exceed {self.cantidad_maxima} {self.codigo}"
        
        return True, None
    
    def convert_to_base_unit(self, cantidad: Decimal) -> Optional[Decimal]:
        """
        Convert quantity to base unit if conversion factor is available
        
        Args:
            cantidad: Quantity in this unit
            
        Returns:
            Converted quantity in base unit, or None if no conversion available
        """
        if not self.factor_conversion or not self.unidad_base:
            return None
        
        return cantidad * self.factor_conversion
    
    def increment_usage(self) -> None:
        """Increment usage counter and update last used timestamp"""
        self.veces_usado += 1
        self.ultimo_uso = datetime.now(timezone.utc)
    
    def is_valid_for_date(self, fecha: datetime) -> bool:
        """Check if unit is valid for a specific date"""
        if not self.activo:
            return False
        
        if self.fecha_vigencia_desde and fecha < self.fecha_vigencia_desde:
            return False
        
        if self.fecha_vigencia_hasta and fecha > self.fecha_vigencia_hasta:
            return False
        
        return True
    
    def get_unit_info(self) -> dict:
        """Get comprehensive unit information"""
        return {
            'codigo': self.codigo,
            'descripcion': self.descripcion,
            'descripcion_ingles': self.descripcion_ingles,
            'simbolo': self.simbolo,
            'categoria': self.categoria,
            'tipo_medida': self.tipo_medida,
            'uso_comun': self.uso_comun,
            'uso_productos': self.uso_productos,
            'uso_servicios': self.uso_servicios,
            'permite_decimales': self.permite_decimales,
            'cantidad_minima': float(self.cantidad_minima) if self.cantidad_minima else None,
            'cantidad_maxima': float(self.cantidad_maxima) if self.cantidad_maxima else None,
            'unidad_base': self.unidad_base,
            'factor_conversion': float(self.factor_conversion) if self.factor_conversion else None,
            'display_name': self.display_name,
            'activo': self.activo,
            'veces_usado': self.veces_usado
        }
    
    @classmethod
    def get_by_code(cls, session, codigo: str) -> Optional['UnitsOfMeasure']:
        """
        Get unit by exact code match
        
        Args:
            session: SQLAlchemy session
            codigo: Unit code to find
            
        Returns:
            UnitsOfMeasure object if found, None otherwise
        """
        return session.query(cls).filter(
            cls.codigo == codigo,
            cls.activo == True
        ).first()
    
    @classmethod
    def search_by_text(cls, session, query: str, limit: int = 20,
                      only_active: bool = True, category: str = None) -> List['UnitsOfMeasure']:
        """
        Full-text search for units by description, symbol, or code
        
        Args:
            session: SQLAlchemy session
            query: Search query string
            limit: Maximum number of results
            only_active: Whether to include only active units
            category: Filter by category (optional)
            
        Returns:
            List of matching UnitsOfMeasure objects ordered by relevance
        """
        if not query or len(query.strip()) < 1:
            return []
        
        search_query = query.strip()
        base_query = session.query(cls)
        
        if only_active:
            base_query = base_query.filter(cls.activo == True)
        
        if category:
            base_query = base_query.filter(cls.categoria == category)
        
        # Search by code first (exact match)
        exact_match = base_query.filter(cls.codigo.ilike(search_query)).first()
        results = [exact_match] if exact_match else []
        
        # Then search by description and symbol
        text_results = base_query.filter(
            func.to_tsvector('spanish',
                           func.concat(
                               func.coalesce(cls.descripcion, ''), ' ',
                               func.coalesce(cls.descripcion_ingles, ''), ' ',
                               func.coalesce(cls.simbolo, ''), ' ',
                               func.coalesce(cls.codigo, '')
                           )).op('@@')(
                               func.to_tsquery('spanish', search_query)
                           )
        ).order_by(
            cls.uso_comun.desc(),
            cls.veces_usado.desc(),
            cls.codigo
        ).limit(limit - len(results)).all()
        
        # Remove duplicates and combine results
        seen_codes = {r.codigo for r in results}
        for result in text_results:
            if result.codigo not in seen_codes:
                results.append(result)
                seen_codes.add(result.codigo)
        
        return results[:limit]
    
    @classmethod
    def get_by_category(cls, session, categoria: str, only_active: bool = True,
                       only_common: bool = False) -> List['UnitsOfMeasure']:
        """
        Get units by category
        
        Args:
            session: SQLAlchemy session
            categoria: Category name
            only_active: Whether to include only active units
            only_common: Whether to include only commonly used units
            
        Returns:
            List of UnitsOfMeasure objects ordered by usage
        """
        base_query = session.query(cls).filter(cls.categoria == categoria)
        
        if only_active:
            base_query = base_query.filter(cls.activo == True)
        
        if only_common:
            base_query = base_query.filter(cls.uso_comun == True)
        
        return base_query.order_by(
            cls.uso_comun.desc(),
            cls.veces_usado.desc(),
            cls.codigo
        ).all()
    
    @classmethod
    def get_common_units(cls, session, for_products: bool = True,
                        for_services: bool = True) -> List['UnitsOfMeasure']:
        """
        Get commonly used units
        
        Args:
            session: SQLAlchemy session
            for_products: Include units suitable for products
            for_services: Include units suitable for services
            
        Returns:
            List of commonly used UnitsOfMeasure objects
        """
        base_query = session.query(cls).filter(
            cls.activo == True,
            cls.uso_comun == True
        )
        
        if for_products and not for_services:
            base_query = base_query.filter(cls.uso_productos == True)
        elif for_services and not for_products:
            base_query = base_query.filter(cls.uso_servicios == True)
        elif for_products and for_services:
            base_query = base_query.filter(
                (cls.uso_productos == True) | (cls.uso_servicios == True)
            )
        
        return base_query.order_by(
            cls.veces_usado.desc(),
            cls.codigo
        ).all()
    
    @classmethod
    def get_most_used(cls, session, limit: int = 50, only_active: bool = True) -> List['UnitsOfMeasure']:
        """
        Get most frequently used units
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of results
            only_active: Whether to include only active units
            
        Returns:
            List of UnitsOfMeasure objects ordered by usage frequency
        """
        base_query = session.query(cls)
        
        if only_active:
            base_query = base_query.filter(cls.activo == True)
        
        return base_query.filter(
            cls.veces_usado > 0
        ).order_by(
            cls.veces_usado.desc(),
            cls.ultimo_uso.desc()
        ).limit(limit).all()
    
    @classmethod
    def validate_unit_code(cls, codigo: str) -> bool:
        """
        Validate unit code format
        
        Args:
            codigo: Unit code to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not codigo:
            return False
        
        return 1 <= len(codigo) <= 10 and codigo.replace(' ', '').replace('.', '').replace('²', '').replace('³', '').isalnum()
    
    @classmethod
    def get_categories(cls, session) -> List[str]:
        """
        Get all available categories
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            List of category names
        """
        return [row[0] for row in session.query(cls.categoria).filter(
            cls.activo == True
        ).distinct().order_by(cls.categoria).all()]
    
    @classmethod
    def seed_default_units(cls, session) -> int:
        """
        Seed database with default RTC 443:2010 units
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            Number of units created
        """
        default_units = [
            # Metric units
            {'codigo': 'Unid', 'descripcion': 'Unidad', 'categoria': 'commercial', 'uso_comun': True, 'permite_decimales': False},
            {'codigo': 'kg', 'descripcion': 'Kilogramo', 'simbolo': 'kg', 'categoria': 'metric', 'tipo_medida': 'weight', 'uso_comun': True},
            {'codigo': 'g', 'descripcion': 'Gramo', 'simbolo': 'g', 'categoria': 'metric', 'tipo_medida': 'weight', 'unidad_base': 'kg', 'factor_conversion': Decimal('0.001')},
            {'codigo': 'L', 'descripcion': 'Litro', 'simbolo': 'L', 'categoria': 'metric', 'tipo_medida': 'volume', 'uso_comun': True},
            {'codigo': 'mL', 'descripcion': 'Mililitro', 'simbolo': 'mL', 'categoria': 'metric', 'tipo_medida': 'volume', 'unidad_base': 'L', 'factor_conversion': Decimal('0.001')},
            {'codigo': 'm', 'descripcion': 'Metro', 'simbolo': 'm', 'categoria': 'metric', 'tipo_medida': 'length', 'uso_comun': True},
            {'codigo': 'cm', 'descripcion': 'Centímetro', 'simbolo': 'cm', 'categoria': 'metric', 'tipo_medida': 'length', 'unidad_base': 'm', 'factor_conversion': Decimal('0.01')},
            {'codigo': 'mm', 'descripcion': 'Milímetro', 'simbolo': 'mm', 'categoria': 'metric', 'tipo_medida': 'length', 'unidad_base': 'm', 'factor_conversion': Decimal('0.001')},
            {'codigo': 'm²', 'descripcion': 'Metro cuadrado', 'simbolo': 'm²', 'categoria': 'metric', 'tipo_medida': 'area', 'uso_comun': True},
            {'codigo': 'm³', 'descripcion': 'Metro cúbico', 'simbolo': 'm³', 'categoria': 'metric', 'tipo_medida': 'volume', 'uso_comun': True},
            
            # Time units
            {'codigo': 'h', 'descripcion': 'Hora', 'simbolo': 'h', 'categoria': 'time', 'uso_comun': True, 'uso_servicios': True},
            {'codigo': 'min', 'descripcion': 'Minuto', 'simbolo': 'min', 'categoria': 'time', 'unidad_base': 'h', 'factor_conversion': Decimal('0.0166667')},
            {'codigo': 'día', 'descripcion': 'Día', 'categoria': 'time', 'uso_comun': True, 'uso_servicios': True, 'permite_decimales': False},
            {'codigo': 'mes', 'descripcion': 'Mes', 'categoria': 'time', 'uso_servicios': True, 'permite_decimales': False},
            {'codigo': 'año', 'descripcion': 'Año', 'categoria': 'time', 'uso_servicios': True, 'permite_decimales': False},
            
            # Service units
            {'codigo': 'Sp', 'descripcion': 'Servicios Profesionales', 'categoria': 'service', 'uso_comun': True, 'uso_productos': False, 'uso_servicios': True},
            {'codigo': 'St', 'descripcion': 'Servicios técnicos', 'categoria': 'service', 'uso_productos': False, 'uso_servicios': True},
            {'codigo': 'Sv', 'descripcion': 'Servicios varios', 'categoria': 'service', 'uso_productos': False, 'uso_servicios': True},
            
            # Commercial units
            {'codigo': 'docena', 'descripcion': 'Docena', 'categoria': 'commercial', 'uso_comun': True, 'permite_decimales': False, 'unidad_base': 'Unid', 'factor_conversion': Decimal('12')},
            {'codigo': 'par', 'descripcion': 'Par', 'categoria': 'commercial', 'permite_decimales': False, 'unidad_base': 'Unid', 'factor_conversion': Decimal('2')},
            {'codigo': 'paquete', 'descripcion': 'Paquete', 'categoria': 'commercial', 'uso_comun': True, 'permite_decimales': False},
            {'codigo': 'caja', 'descripcion': 'Caja', 'categoria': 'commercial', 'uso_comun': True, 'permite_decimales': False},
            {'codigo': 'bolsa', 'descripcion': 'Bolsa', 'categoria': 'commercial', 'permite_decimales': False},
            {'codigo': 'rollo', 'descripcion': 'Rollo', 'categoria': 'commercial', 'permite_decimales': False},
            
            # Additional metric units
            {'codigo': 'ton', 'descripcion': 'Tonelada métrica', 'simbolo': 't', 'categoria': 'metric', 'tipo_medida': 'weight', 'unidad_base': 'kg', 'factor_conversion': Decimal('1000')},
            {'codigo': 'lb', 'descripcion': 'Libra', 'simbolo': 'lb', 'categoria': 'commercial', 'tipo_medida': 'weight', 'unidad_base': 'kg', 'factor_conversion': Decimal('0.453592')},
            {'codigo': 'oz', 'descripcion': 'Onza', 'simbolo': 'oz', 'categoria': 'commercial', 'tipo_medida': 'weight', 'unidad_base': 'kg', 'factor_conversion': Decimal('0.0283495')},
            {'codigo': 'gal', 'descripcion': 'Galón', 'simbolo': 'gal', 'categoria': 'commercial', 'tipo_medida': 'volume', 'unidad_base': 'L', 'factor_conversion': Decimal('3.78541')},
        ]
        
        created_count = 0
        for unit_data in default_units:
            existing = session.query(cls).filter(cls.codigo == unit_data['codigo']).first()
            if not existing:
                unit = cls(**unit_data, version_rtc='443:2010', activo=True)
                session.add(unit)
                created_count += 1
        
        session.commit()
        return created_count