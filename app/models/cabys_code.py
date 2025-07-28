"""
CABYS Code model for Costa Rican product and service classification system

This model handles the official CABYS (Central American Tariff System) codes
used for product and service classification in Costa Rica's electronic invoicing system.
Includes full-text search capabilities for efficient code lookup.

Requirements: 11.2, 11.3
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Numeric, Integer,
    CheckConstraint, Index, func, text
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base


class CabysCode(Base):
    """
    CABYS Code model for product and service classification
    
    Stores the official Costa Rican CABYS codes with full-text search support
    for efficient product classification during invoice creation.
    
    CABYS codes are exactly 13 digits and are used to classify all products
    and services for tax purposes in Costa Rica's electronic invoicing system.
    
    Requirements:
    - 11.2: CABYS code validation (exactly 13-digit format and database verification)
    - 11.3: Full-text search across descriptions for product classification
    """
    __tablename__ = "codigos_cabys"
    
    # Primary key - CABYS code (exactly 13 digits)
    codigo = Column(String(13), primary_key=True, 
                   comment="CABYS code - exactly 13 digits")
    
    # Product/service information
    descripcion = Column(Text, nullable=False, 
                        comment="Product or service description in Spanish")
    
    # Classification hierarchy (4 levels as per migration)
    categoria_nivel_1 = Column(String(255), nullable=True,
                              comment="Level 1 category (broadest classification)")
    categoria_nivel_2 = Column(String(255), nullable=True,
                              comment="Level 2 category (sub-classification)")
    categoria_nivel_3 = Column(String(255), nullable=True,
                              comment="Level 3 category (detailed classification)")
    categoria_nivel_4 = Column(String(255), nullable=True,
                              comment="Level 4 category")
    
    # Tax information
    impuesto_iva = Column(Numeric(4, 2), nullable=False, default=Decimal('13.00'),
                         comment="Default IVA tax rate percentage for this product/service")
    exento_iva = Column(Boolean, nullable=False, default=False,
                       comment="Whether this product/service is IVA exempt")
    
    # Status and versioning
    activo = Column(Boolean, nullable=False, default=True,
                   comment="Whether this CABYS code is currently active")
    version_cabys = Column(String(10), nullable=True,
                          comment="CABYS catalog version (e.g., '4.4')")
    fecha_vigencia_desde = Column(DateTime(timezone=True), nullable=True,
                                 comment="Date when this code became effective")
    fecha_vigencia_hasta = Column(DateTime(timezone=True), nullable=True,
                                comment="Date when this code expires (if applicable)")
    
    # Usage statistics
    veces_usado = Column(Integer, nullable=False, default=0,
                        comment="Number of times this code has been used in documents")
    ultimo_uso = Column(DateTime(timezone=True), nullable=True,
                       comment="Last time this code was used in a document")
    
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
            "char_length(codigo) = 13",
            name="ck_cabys_codigo_length"
        ),
        CheckConstraint(
            "codigo ~ '^[0-9]{13}$'",
            name="ck_cabys_codigo_format"
        ),
        CheckConstraint(
            "char_length(descripcion) >= 3",
            name="ck_cabys_descripcion_min_length"
        ),
        CheckConstraint(
            "impuesto_iva >= 0 AND impuesto_iva <= 100",
            name="ck_cabys_impuesto_iva_range"
        ),
        CheckConstraint(
            "veces_usado >= 0",
            name="ck_cabys_veces_usado_positive"
        ),
        CheckConstraint(
            "fecha_vigencia_hasta IS NULL OR fecha_vigencia_hasta > fecha_vigencia_desde",
            name="ck_cabys_fechas_vigencia_valid"
        ),
        
        # Performance indexes
        Index("idx_cabys_codigo", "codigo"),  # Primary key index (automatic)
        Index("idx_cabys_activo", "activo"),
        Index("idx_cabys_descripcion_gin", "descripcion", postgresql_using="gin",
              postgresql_ops={"descripcion": "gin_trgm_ops"}),

        Index("idx_cabys_categoria_1", "categoria_nivel_1"),
        Index("idx_cabys_categoria_2", "categoria_nivel_2"),
        Index("idx_cabys_categoria_3", "categoria_nivel_3"),
        Index("idx_cabys_categoria_4", "categoria_nivel_4"),

        Index("idx_cabys_impuesto_iva", "impuesto_iva"),
        Index("idx_cabys_exento_iva", "exento_iva"),
        Index("idx_cabys_veces_usado", "veces_usado"),
        Index("idx_cabys_ultimo_uso", "ultimo_uso"),
        Index("idx_cabys_version", "version_cabys"),
        Index("idx_cabys_vigencia", "fecha_vigencia_desde", "fecha_vigencia_hasta"),
        
        # Composite indexes for common queries
        Index("idx_cabys_activo_categoria", "activo", "categoria_nivel_1"),
        Index("idx_cabys_activo_impuesto", "activo", "impuesto_iva"),
        Index("idx_cabys_activo_exento", "activo", "exento_iva"),
        Index("idx_cabys_popular", "activo", "veces_usado"),
        
        # Full-text search indexes
        Index("idx_cabys_descripcion_tsvector", 
              text("to_tsvector('spanish', descripcion)"),
              postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<CabysCode(codigo='{self.codigo}', descripcion='{self.descripcion[:50]}...')>"
    
    def __str__(self) -> str:
        return f"{self.codigo} - {self.descripcion}"
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if the CABYS code is currently active and valid"""
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
    def categoria_completa(self) -> str:
        """Get complete category hierarchy as a formatted string"""
        categorias = [
            self.categoria_nivel_1,
            self.categoria_nivel_2,
            self.categoria_nivel_3,
            self.categoria_nivel_4
        ]
        return " > ".join(filter(None, categorias))
    
    @property
    def impuesto_iva_decimal(self) -> Decimal:
        """Get IVA tax rate as decimal (e.g., 0.13 for 13%)"""
        return self.impuesto_iva / Decimal('100')
    
    def increment_usage(self) -> None:
        """Increment usage counter and update last used timestamp"""
        self.veces_usado += 1
        self.ultimo_uso = datetime.now(timezone.utc)
    
    def is_valid_for_date(self, fecha: datetime) -> bool:
        """Check if CABYS code is valid for a specific date"""
        if not self.activo:
            return False
        
        if self.fecha_vigencia_desde and fecha < self.fecha_vigencia_desde:
            return False
        
        if self.fecha_vigencia_hasta and fecha > self.fecha_vigencia_hasta:
            return False
        
        return True
    
    def get_tax_info(self) -> dict:
        """Get comprehensive tax information for this CABYS code"""
        return {
            'codigo_cabys': self.codigo,
            'impuesto_iva_porcentaje': float(self.impuesto_iva),
            'impuesto_iva_decimal': float(self.impuesto_iva_decimal),
            'exento_iva': self.exento_iva,
            'descripcion': self.descripcion,
            'categoria': self.categoria_completa
        }
    
    @classmethod
    def search_by_text(cls, session, query: str, limit: int = 20, 
                      only_active: bool = True) -> List['CabysCode']:
        """
        Full-text search for CABYS codes by description
        
        Args:
            session: SQLAlchemy session
            query: Search query string
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of matching CabysCode objects ordered by relevance
        """
        # Prepare search query for PostgreSQL full-text search
        search_query = query.strip()
        if not search_query:
            return []
        
        # Convert to tsquery format (handle Spanish characters and spaces)
        tsquery = " & ".join(search_query.split())
        
        base_query = session.query(cls)
        
        if only_active:
            base_query = base_query.filter(cls.activo == True)
        
        # Full-text search using PostgreSQL's to_tsvector and to_tsquery
        results = base_query.filter(
            text("to_tsvector('spanish', descripcion) @@ to_tsquery('spanish', :query)")
        ).params(query=tsquery).order_by(
            # Order by relevance (ts_rank) and usage frequency
            text("ts_rank(to_tsvector('spanish', descripcion), to_tsquery('spanish', :query)) DESC, veces_usado DESC")
        ).params(query=tsquery).limit(limit).all()
        
        return results
    
    @classmethod
    def search_by_code_prefix(cls, session, prefix: str, limit: int = 20,
                             only_active: bool = True) -> List['CabysCode']:
        """
        Search CABYS codes by code prefix
        
        Args:
            session: SQLAlchemy session
            prefix: Code prefix to search for
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of matching CabysCode objects ordered by code
        """
        if not prefix or not prefix.isdigit():
            return []
        
        base_query = session.query(cls)
        
        if only_active:
            base_query = base_query.filter(cls.activo == True)
        
        results = base_query.filter(
            cls.codigo.like(f"{prefix}%")
        ).order_by(
            cls.codigo, cls.veces_usado.desc()
        ).limit(limit).all()
        
        return results
    
    @classmethod
    def search_by_category(cls, session, categoria: str, nivel: int = 1,
                          limit: int = 50, only_active: bool = True) -> List['CabysCode']:
        """
        Search CABYS codes by category
        
        Args:
            session: SQLAlchemy session
            categoria: Category name to search for
            nivel: Category level (1-8)
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of matching CabysCode objects ordered by usage
        """
        base_query = session.query(cls)
        
        if only_active:
            base_query = base_query.filter(cls.activo == True)
        
        # Select appropriate category level (1-4)
        category_field = {
            1: cls.categoria_nivel_1,
            2: cls.categoria_nivel_2,
            3: cls.categoria_nivel_3,
            4: cls.categoria_nivel_4
        }.get(nivel, cls.categoria_nivel_1)
        
        results = base_query.filter(
            category_field.ilike(f"%{categoria}%")
        ).order_by(
            cls.veces_usado.desc(), cls.codigo
        ).limit(limit).all()
        
        return results
    
    @classmethod
    def get_most_used(cls, session, limit: int = 100, 
                     only_active: bool = True) -> List['CabysCode']:
        """
        Get most frequently used CABYS codes
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of results
            only_active: Whether to include only active codes
            
        Returns:
            List of CabysCode objects ordered by usage frequency
        """
        base_query = session.query(cls)
        
        if only_active:
            base_query = base_query.filter(cls.activo == True)
        
        results = base_query.filter(
            cls.veces_usado > 0
        ).order_by(
            cls.veces_usado.desc(), cls.ultimo_uso.desc()
        ).limit(limit).all()
        
        return results
    
    @classmethod
    def validate_code_format(cls, codigo: str) -> bool:
        """
        Validate CABYS code format (exactly 13 digits)
        
        Args:
            codigo: CABYS code to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not codigo:
            return False
        
        return len(codigo) == 13 and codigo.isdigit()
    
    @classmethod
    def get_by_code(cls, session, codigo: str) -> Optional['CabysCode']:
        """
        Get CABYS code by exact code match
        
        Args:
            session: SQLAlchemy session
            codigo: Exact CABYS code to find
            
        Returns:
            CabysCode object if found, None otherwise
        """
        if not cls.validate_code_format(codigo):
            return None
        
        return session.query(cls).filter(cls.codigo == codigo).first()