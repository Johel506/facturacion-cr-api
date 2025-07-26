"""
Geographic Location model for Costa Rican administrative divisions

This model handles the official Costa Rican geographic hierarchy:
provinces, cantons, and districts for proper address validation
in electronic invoicing system.

Requirements: 12.1, 12.2, 12.3
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text,
    CheckConstraint, Index, func, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class GeographicLocation(Base):
    """
    Geographic Location model for Costa Rican administrative divisions
    
    Stores the official Costa Rican geographic hierarchy with provinces (1-7),
    cantons (1-99 per province), and districts (1-99 per canton) for proper
    address validation in electronic invoicing.
    
    Costa Rica has 7 provinces, each with multiple cantons, and each canton
    has multiple districts. This model ensures proper address validation
    according to official government divisions.
    
    Requirements:
    - 12.1: Province code validation (1-7 single digit)
    - 12.2: Canton code validation (2-digit codes per province)
    - 12.3: District code validation (2-digit codes per canton)
    """
    __tablename__ = "ubicaciones_cr"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True,
               comment="Auto-incrementing primary key")
    
    # Geographic hierarchy codes
    provincia = Column(Integer, nullable=False,
                      comment="Province code (1-7)")
    canton = Column(Integer, nullable=False,
                   comment="Canton code (1-99 within province)")
    distrito = Column(Integer, nullable=False,
                     comment="District code (1-99 within canton)")
    
    # Geographic names
    nombre_provincia = Column(String(50), nullable=False,
                             comment="Official province name")
    nombre_canton = Column(String(100), nullable=False,
                          comment="Official canton name")
    nombre_distrito = Column(String(100), nullable=False,
                            comment="Official district name")
    
    # Additional geographic information
    codigo_postal = Column(String(10), nullable=True,
                          comment="Postal code if available")
    area_km2 = Column(Integer, nullable=True,
                     comment="Area in square kilometers")
    poblacion = Column(Integer, nullable=True,
                      comment="Population count (from last census)")
    
    # Administrative information
    cabecera_canton = Column(Boolean, nullable=False, default=False,
                            comment="Whether this district is the canton's administrative center")
    cabecera_provincia = Column(Boolean, nullable=False, default=False,
                               comment="Whether this district is the province's administrative center")
    
    # Status and metadata
    activo = Column(Boolean, nullable=False, default=True,
                   comment="Whether this location is currently active")
    fecha_creacion_oficial = Column(DateTime(timezone=True), nullable=True,
                                   comment="Official creation date of the administrative division")
    
    # Alternative names and search
    nombres_alternativos = Column(Text, nullable=True,
                                 comment="Alternative names or common abbreviations (JSON array)")
    codigo_inec = Column(String(10), nullable=True,
                        comment="INEC (National Statistics Institute) code")
    
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
        # Unique constraint for geographic hierarchy
        UniqueConstraint('provincia', 'canton', 'distrito',
                        name='uq_ubicacion_provincia_canton_distrito'),
        
        # Check constraints for data validation
        CheckConstraint(
            "provincia >= 1 AND provincia <= 7",
            name="ck_ubicacion_provincia_range"
        ),
        CheckConstraint(
            "canton >= 1 AND canton <= 99",
            name="ck_ubicacion_canton_range"
        ),
        CheckConstraint(
            "distrito >= 1 AND distrito <= 99",
            name="ck_ubicacion_distrito_range"
        ),
        CheckConstraint(
            "char_length(nombre_provincia) >= 3",
            name="ck_ubicacion_nombre_provincia_length"
        ),
        CheckConstraint(
            "char_length(nombre_canton) >= 3",
            name="ck_ubicacion_nombre_canton_length"
        ),
        CheckConstraint(
            "char_length(nombre_distrito) >= 3",
            name="ck_ubicacion_nombre_distrito_length"
        ),
        CheckConstraint(
            "area_km2 IS NULL OR area_km2 > 0",
            name="ck_ubicacion_area_positive"
        ),
        CheckConstraint(
            "poblacion IS NULL OR poblacion >= 0",
            name="ck_ubicacion_poblacion_positive"
        ),
        
        # Performance indexes
        Index("idx_ubicacion_provincia", "provincia"),
        Index("idx_ubicacion_canton", "provincia", "canton"),
        Index("idx_ubicacion_distrito", "provincia", "canton", "distrito"),
        Index("idx_ubicacion_activo", "activo"),
        Index("idx_ubicacion_nombre_provincia", "nombre_provincia"),
        Index("idx_ubicacion_nombre_canton", "nombre_canton"),
        Index("idx_ubicacion_nombre_distrito", "nombre_distrito"),
        Index("idx_ubicacion_codigo_postal", "codigo_postal"),
        Index("idx_ubicacion_codigo_inec", "codigo_inec"),
        Index("idx_ubicacion_cabecera_canton", "cabecera_canton"),
        Index("idx_ubicacion_cabecera_provincia", "cabecera_provincia"),
        
        # Composite indexes for common queries
        Index("idx_ubicacion_activo_provincia", "activo", "provincia"),
        Index("idx_ubicacion_activo_canton", "activo", "provincia", "canton"),
        Index("idx_ubicacion_provincia_nombre", "provincia", "nombre_provincia"),
        Index("idx_ubicacion_canton_nombre", "provincia", "canton", "nombre_canton"),
        
        # Full-text search indexes for names
        Index("idx_ubicacion_nombres_gin", 
              func.to_tsvector('spanish', 
                              func.concat(
                                  func.coalesce("nombre_provincia", ''), ' ',
                                  func.coalesce("nombre_canton", ''), ' ',
                                  func.coalesce("nombre_distrito", ''), ' ',
                                  func.coalesce("nombres_alternativos", '')
                              )),
              postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return (f"<GeographicLocation(provincia={self.provincia}, canton={self.canton}, "
                f"distrito={self.distrito}, nombre='{self.nombre_completo}')>")
    
    def __str__(self) -> str:
        return self.nombre_completo
    
    @property
    def nombre_completo(self) -> str:
        """Get complete location name as formatted string"""
        return f"{self.nombre_distrito}, {self.nombre_canton}, {self.nombre_provincia}"
    
    @property
    def codigo_completo(self) -> str:
        """Get complete location code as formatted string (P-CC-DD)"""
        return f"{self.provincia}-{self.canton:02d}-{self.distrito:02d}"
    
    @property
    def codigo_numerico(self) -> str:
        """Get numeric code for database storage (PCCDD)"""
        return f"{self.provincia}{self.canton:02d}{self.distrito:02d}"
    
    @property
    def is_capital_district(self) -> bool:
        """Check if this is a capital district (canton or province)"""
        return self.cabecera_canton or self.cabecera_provincia
    
    def get_hierarchy_info(self) -> dict:
        """Get complete hierarchy information"""
        return {
            'provincia': {
                'codigo': self.provincia,
                'nombre': self.nombre_provincia,
                'es_cabecera': self.cabecera_provincia
            },
            'canton': {
                'codigo': self.canton,
                'nombre': self.nombre_canton,
                'es_cabecera': self.cabecera_canton
            },
            'distrito': {
                'codigo': self.distrito,
                'nombre': self.nombre_distrito
            },
            'codigo_completo': self.codigo_completo,
            'codigo_numerico': self.codigo_numerico,
            'nombre_completo': self.nombre_completo
        }
    
    @classmethod
    def validate_codes(cls, provincia: int, canton: int, distrito: int) -> bool:
        """
        Validate geographic codes format
        
        Args:
            provincia: Province code (1-7)
            canton: Canton code (1-99)
            distrito: District code (1-99)
            
        Returns:
            True if all codes are in valid range, False otherwise
        """
        return (
            1 <= provincia <= 7 and
            1 <= canton <= 99 and
            1 <= distrito <= 99
        )
    
    @classmethod
    def get_by_codes(cls, session, provincia: int, canton: int, 
                    distrito: int) -> Optional['GeographicLocation']:
        """
        Get location by exact codes
        
        Args:
            session: SQLAlchemy session
            provincia: Province code
            canton: Canton code
            distrito: District code
            
        Returns:
            GeographicLocation object if found, None otherwise
        """
        if not cls.validate_codes(provincia, canton, distrito):
            return None
        
        return session.query(cls).filter(
            cls.provincia == provincia,
            cls.canton == canton,
            cls.distrito == distrito,
            cls.activo == True
        ).first()
    
    @classmethod
    def get_provinces(cls, session) -> List['GeographicLocation']:
        """
        Get all provinces (unique province entries)
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            List of GeographicLocation objects representing provinces
        """
        return session.query(cls).filter(
            cls.activo == True
        ).distinct(cls.provincia).order_by(cls.provincia).all()
    
    @classmethod
    def get_cantons_by_province(cls, session, provincia: int) -> List['GeographicLocation']:
        """
        Get all cantons in a province
        
        Args:
            session: SQLAlchemy session
            provincia: Province code
            
        Returns:
            List of GeographicLocation objects representing cantons
        """
        if not (1 <= provincia <= 7):
            return []
        
        return session.query(cls).filter(
            cls.provincia == provincia,
            cls.activo == True
        ).distinct(cls.canton).order_by(cls.canton).all()
    
    @classmethod
    def get_districts_by_canton(cls, session, provincia: int, 
                               canton: int) -> List['GeographicLocation']:
        """
        Get all districts in a canton
        
        Args:
            session: SQLAlchemy session
            provincia: Province code
            canton: Canton code
            
        Returns:
            List of GeographicLocation objects representing districts
        """
        if not (1 <= provincia <= 7 and 1 <= canton <= 99):
            return []
        
        return session.query(cls).filter(
            cls.provincia == provincia,
            cls.canton == canton,
            cls.activo == True
        ).order_by(cls.distrito).all()
    
    @classmethod
    def search_by_name(cls, session, query: str, limit: int = 20) -> List['GeographicLocation']:
        """
        Search locations by name (full-text search)
        
        Args:
            session: SQLAlchemy session
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching GeographicLocation objects
        """
        if not query or len(query.strip()) < 2:
            return []
        
        search_query = query.strip()
        
        # Full-text search across all name fields
        results = session.query(cls).filter(
            cls.activo == True
        ).filter(
            func.to_tsvector('spanish', 
                           func.concat(
                               func.coalesce(cls.nombre_provincia, ''), ' ',
                               func.coalesce(cls.nombre_canton, ''), ' ',
                               func.coalesce(cls.nombre_distrito, ''), ' ',
                               func.coalesce(cls.nombres_alternativos, '')
                           )).op('@@')(
                               func.to_tsquery('spanish', search_query)
                           )
        ).order_by(
            cls.provincia, cls.canton, cls.distrito
        ).limit(limit).all()
        
        return results
    
    @classmethod
    def get_province_name(cls, provincia_code: int) -> Optional[str]:
        """
        Get province name by code (static mapping for performance)
        
        Args:
            provincia_code: Province code (1-7)
            
        Returns:
            Province name if valid code, None otherwise
        """
        province_names = {
            1: "San José",
            2: "Alajuela", 
            3: "Cartago",
            4: "Heredia",
            5: "Guanacaste",
            6: "Puntarenas",
            7: "Limón"
        }
        return province_names.get(provincia_code)
    
    @classmethod
    def validate_address_data(cls, session, provincia: int, canton: int, 
                             distrito: int) -> Tuple[bool, Optional[str]]:
        """
        Validate complete address data against database
        
        Args:
            session: SQLAlchemy session
            provincia: Province code
            canton: Canton code
            distrito: District code
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check code format
        if not cls.validate_codes(provincia, canton, distrito):
            return False, "Invalid geographic codes format"
        
        # Check if location exists in database
        location = cls.get_by_codes(session, provincia, canton, distrito)
        if not location:
            return False, f"Geographic location {provincia}-{canton:02d}-{distrito:02d} not found"
        
        if not location.activo:
            return False, f"Geographic location {location.nombre_completo} is not active"
        
        return True, None
    
    @classmethod
    def get_location_hierarchy(cls, session, provincia: int, canton: int = None, 
                              distrito: int = None) -> dict:
        """
        Get hierarchical location data
        
        Args:
            session: SQLAlchemy session
            provincia: Province code
            canton: Canton code (optional)
            distrito: District code (optional, requires canton)
            
        Returns:
            Dictionary with hierarchical location data
        """
        result = {
            'provincia': {
                'codigo': provincia,
                'nombre': cls.get_province_name(provincia),
                'cantons': []
            }
        }
        
        if canton is not None:
            cantons = cls.get_cantons_by_province(session, provincia)
            canton_data = next((c for c in cantons if c.canton == canton), None)
            
            if canton_data:
                result['canton'] = {
                    'codigo': canton,
                    'nombre': canton_data.nombre_canton,
                    'distritos': []
                }
                
                if distrito is not None:
                    districts = cls.get_districts_by_canton(session, provincia, canton)
                    district_data = next((d for d in districts if d.distrito == distrito), None)
                    
                    if district_data:
                        result['distrito'] = {
                            'codigo': distrito,
                            'nombre': district_data.nombre_distrito,
                            'codigo_completo': district_data.codigo_completo,
                            'nombre_completo': district_data.nombre_completo
                        }
                    else:
                        result['distrito'] = None
                else:
                    # Get all districts for this canton
                    districts = cls.get_districts_by_canton(session, provincia, canton)
                    result['canton']['distritos'] = [
                        {
                            'codigo': d.distrito,
                            'nombre': d.nombre_distrito,
                            'codigo_completo': d.codigo_completo
                        }
                        for d in districts
                    ]
            else:
                result['canton'] = None
        else:
            # Get all cantons for this province
            cantons = cls.get_cantons_by_province(session, provincia)
            result['provincia']['cantons'] = [
                {
                    'codigo': c.canton,
                    'nombre': c.nombre_canton
                }
                for c in cantons
            ]
        
        return result