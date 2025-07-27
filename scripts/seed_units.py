#!/usr/bin/env python3
"""
Units of Measure Seeding Script

This script seeds the database with official Costa Rican units of measure
as defined in the RTC 443:2010 standard used in electronic invoicing system.
Supports metric, commercial, and service-specific units.

Requirements: 17.1
"""
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.models.units_of_measure import UnitsOfMeasure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnitsSeeder:
    """Units of measure seeding utility"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize the units seeder
        
        Args:
            database_url: Database connection URL (defaults to settings)
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def seed_rtc_443_units(self) -> int:
        """
        Seed database with official RTC 443:2010 units of measure
        
        Returns:
            Number of units created
        """
        logger.info("Starting RTC 443:2010 units of measure seeding...")
        
        # Official units from RTC 443:2010 standard
        units_data = [
            # BASIC COMMERCIAL UNITS
            {
                'codigo': 'Unid',
                'descripcion': 'Unidad',
                'descripcion_ingles': 'Unit',
                'simbolo': 'Unid',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': True,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Unidad básica para conteo de productos individuales'
            },
            
            # METRIC WEIGHT UNITS
            {
                'codigo': 'kg',
                'descripcion': 'Kilogramo',
                'descripcion_ingles': 'Kilogram',
                'simbolo': 'kg',
                'categoria': 'metric',
                'tipo_medida': 'weight',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.001'),
                'notas': 'Unidad básica de masa en el sistema métrico'
            },
            {
                'codigo': 'g',
                'descripcion': 'Gramo',
                'descripcion_ingles': 'Gram',
                'simbolo': 'g',
                'categoria': 'metric',
                'tipo_medida': 'weight',
                'unidad_base': 'kg',
                'factor_conversion': Decimal('0.001'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Submúltiplo del kilogramo'
            },
            {
                'codigo': 'mg',
                'descripcion': 'Miligramo',
                'descripcion_ingles': 'Milligram',
                'simbolo': 'mg',
                'categoria': 'metric',
                'tipo_medida': 'weight',
                'unidad_base': 'kg',
                'factor_conversion': Decimal('0.000001'),
                'uso_comun': False,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Usado principalmente para medicamentos'
            },
            {
                'codigo': 'ton',
                'descripcion': 'Tonelada métrica',
                'descripcion_ingles': 'Metric ton',
                'simbolo': 't',
                'categoria': 'metric',
                'tipo_medida': 'weight',
                'unidad_base': 'kg',
                'factor_conversion': Decimal('1000'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.001'),
                'notas': 'Múltiplo del kilogramo para grandes cantidades'
            },
            
            # METRIC VOLUME UNITS
            {
                'codigo': 'L',
                'descripcion': 'Litro',
                'descripcion_ingles': 'Liter',
                'simbolo': 'L',
                'categoria': 'metric',
                'tipo_medida': 'volume',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.001'),
                'notas': 'Unidad básica de volumen'
            },
            {
                'codigo': 'mL',
                'descripcion': 'Mililitro',
                'descripcion_ingles': 'Milliliter',
                'simbolo': 'mL',
                'categoria': 'metric',
                'tipo_medida': 'volume',
                'unidad_base': 'L',
                'factor_conversion': Decimal('0.001'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Submúltiplo del litro'
            },
            {
                'codigo': 'cL',
                'descripcion': 'Centilitro',
                'descripcion_ingles': 'Centiliter',
                'simbolo': 'cL',
                'categoria': 'metric',
                'tipo_medida': 'volume',
                'unidad_base': 'L',
                'factor_conversion': Decimal('0.01'),
                'uso_comun': False,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Usado principalmente para bebidas'
            },
            
            # METRIC LENGTH UNITS
            {
                'codigo': 'm',
                'descripcion': 'Metro',
                'descripcion_ingles': 'Meter',
                'simbolo': 'm',
                'categoria': 'metric',
                'tipo_medida': 'length',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.001'),
                'notas': 'Unidad básica de longitud'
            },
            {
                'codigo': 'cm',
                'descripcion': 'Centímetro',
                'descripcion_ingles': 'Centimeter',
                'simbolo': 'cm',
                'categoria': 'metric',
                'tipo_medida': 'length',
                'unidad_base': 'm',
                'factor_conversion': Decimal('0.01'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Submúltiplo del metro'
            },
            {
                'codigo': 'mm',
                'descripcion': 'Milímetro',
                'descripcion_ingles': 'Millimeter',
                'simbolo': 'mm',
                'categoria': 'metric',
                'tipo_medida': 'length',
                'unidad_base': 'm',
                'factor_conversion': Decimal('0.001'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Submúltiplo del metro para medidas precisas'
            },
            {
                'codigo': 'km',
                'descripcion': 'Kilómetro',
                'descripcion_ingles': 'Kilometer',
                'simbolo': 'km',
                'categoria': 'metric',
                'tipo_medida': 'length',
                'unidad_base': 'm',
                'factor_conversion': Decimal('1000'),
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.001'),
                'notas': 'Múltiplo del metro para grandes distancias'
            },
            
            # METRIC AREA UNITS
            {
                'codigo': 'm²',
                'descripcion': 'Metro cuadrado',
                'descripcion_ingles': 'Square meter',
                'simbolo': 'm²',
                'categoria': 'metric',
                'tipo_medida': 'area',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad básica de área'
            },
            {
                'codigo': 'cm²',
                'descripcion': 'Centímetro cuadrado',
                'descripcion_ingles': 'Square centimeter',
                'simbolo': 'cm²',
                'categoria': 'metric',
                'tipo_medida': 'area',
                'unidad_base': 'm²',
                'factor_conversion': Decimal('0.0001'),
                'uso_comun': False,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Submúltiplo del metro cuadrado'
            },
            {
                'codigo': 'ha',
                'descripcion': 'Hectárea',
                'descripcion_ingles': 'Hectare',
                'simbolo': 'ha',
                'categoria': 'metric',
                'tipo_medida': 'area',
                'unidad_base': 'm²',
                'factor_conversion': Decimal('10000'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.0001'),
                'notas': 'Múltiplo del metro cuadrado para terrenos'
            },
            
            # METRIC VOLUME (CUBIC) UNITS
            {
                'codigo': 'm³',
                'descripcion': 'Metro cúbico',
                'descripcion_ingles': 'Cubic meter',
                'simbolo': 'm³',
                'categoria': 'metric',
                'tipo_medida': 'volume',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.001'),
                'notas': 'Unidad básica de volumen cúbico'
            },
            {
                'codigo': 'cm³',
                'descripcion': 'Centímetro cúbico',
                'descripcion_ingles': 'Cubic centimeter',
                'simbolo': 'cm³',
                'categoria': 'metric',
                'tipo_medida': 'volume',
                'unidad_base': 'm³',
                'factor_conversion': Decimal('0.000001'),
                'uso_comun': False,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Submúltiplo del metro cúbico'
            },
            
            # TIME UNITS
            {
                'codigo': 'h',
                'descripcion': 'Hora',
                'descripcion_ingles': 'Hour',
                'simbolo': 'h',
                'categoria': 'time',
                'tipo_medida': 'time',
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad básica de tiempo para servicios'
            },
            {
                'codigo': 'min',
                'descripcion': 'Minuto',
                'descripcion_ingles': 'Minute',
                'simbolo': 'min',
                'categoria': 'time',
                'tipo_medida': 'time',
                'unidad_base': 'h',
                'factor_conversion': Decimal('0.0166667'),
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('1'),
                'notas': 'Submúltiplo de la hora'
            },
            {
                'codigo': 'día',
                'descripcion': 'Día',
                'descripcion_ingles': 'Day',
                'simbolo': 'día',
                'categoria': 'time',
                'tipo_medida': 'time',
                'unidad_base': 'h',
                'factor_conversion': Decimal('24'),
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Múltiplo de la hora para servicios de larga duración'
            },
            {
                'codigo': 'semana',
                'descripcion': 'Semana',
                'descripcion_ingles': 'Week',
                'simbolo': 'sem',
                'categoria': 'time',
                'tipo_medida': 'time',
                'unidad_base': 'día',
                'factor_conversion': Decimal('7'),
                'uso_comun': False,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Múltiplo del día'
            },
            {
                'codigo': 'mes',
                'descripcion': 'Mes',
                'descripcion_ingles': 'Month',
                'simbolo': 'mes',
                'categoria': 'time',
                'tipo_medida': 'time',
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Unidad de tiempo para servicios mensuales'
            },
            {
                'codigo': 'año',
                'descripcion': 'Año',
                'descripcion_ingles': 'Year',
                'simbolo': 'año',
                'categoria': 'time',
                'tipo_medida': 'time',
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Unidad de tiempo para servicios anuales'
            },
            
            # SERVICE UNITS
            {
                'codigo': 'Sp',
                'descripcion': 'Servicios Profesionales',
                'descripcion_ingles': 'Professional Services',
                'simbolo': 'Sp',
                'categoria': 'service',
                'tipo_medida': 'service',
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad para servicios profesionales especializados'
            },
            {
                'codigo': 'St',
                'descripcion': 'Servicios técnicos',
                'descripcion_ingles': 'Technical Services',
                'simbolo': 'St',
                'categoria': 'service',
                'tipo_medida': 'service',
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad para servicios técnicos'
            },
            {
                'codigo': 'Sv',
                'descripcion': 'Servicios varios',
                'descripcion_ingles': 'Various Services',
                'simbolo': 'Sv',
                'categoria': 'service',
                'tipo_medida': 'service',
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad para servicios generales'
            },
            {
                'codigo': 'Sc',
                'descripcion': 'Servicios comerciales',
                'descripcion_ingles': 'Commercial Services',
                'simbolo': 'Sc',
                'categoria': 'service',
                'tipo_medida': 'service',
                'uso_comun': False,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad para servicios comerciales'
            },
            
            # COMMERCIAL UNITS
            {
                'codigo': 'docena',
                'descripcion': 'Docena',
                'descripcion_ingles': 'Dozen',
                'simbolo': 'doc',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'unidad_base': 'Unid',
                'factor_conversion': Decimal('12'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Agrupación de 12 unidades'
            },
            {
                'codigo': 'par',
                'descripcion': 'Par',
                'descripcion_ingles': 'Pair',
                'simbolo': 'par',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'unidad_base': 'Unid',
                'factor_conversion': Decimal('2'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Agrupación de 2 unidades'
            },
            {
                'codigo': 'paquete',
                'descripcion': 'Paquete',
                'descripcion_ingles': 'Package',
                'simbolo': 'paq',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Agrupación comercial de productos'
            },
            {
                'codigo': 'caja',
                'descripcion': 'Caja',
                'descripcion_ingles': 'Box',
                'simbolo': 'caja',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Contenedor comercial'
            },
            {
                'codigo': 'bolsa',
                'descripcion': 'Bolsa',
                'descripcion_ingles': 'Bag',
                'simbolo': 'bolsa',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Contenedor flexible'
            },
            {
                'codigo': 'rollo',
                'descripcion': 'Rollo',
                'descripcion_ingles': 'Roll',
                'simbolo': 'rollo',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Producto enrollado'
            },
            {
                'codigo': 'lata',
                'descripcion': 'Lata',
                'descripcion_ingles': 'Can',
                'simbolo': 'lata',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Contenedor metálico'
            },
            {
                'codigo': 'botella',
                'descripcion': 'Botella',
                'descripcion_ingles': 'Bottle',
                'simbolo': 'bot',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Contenedor de vidrio o plástico'
            },
            {
                'codigo': 'frasco',
                'descripcion': 'Frasco',
                'descripcion_ingles': 'Jar',
                'simbolo': 'frasco',
                'categoria': 'commercial',
                'tipo_medida': 'count',
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': False,
                'cantidad_minima': Decimal('1'),
                'notas': 'Contenedor pequeño'
            },
            
            # IMPERIAL/US UNITS (commonly used)
            {
                'codigo': 'lb',
                'descripcion': 'Libra',
                'descripcion_ingles': 'Pound',
                'simbolo': 'lb',
                'categoria': 'commercial',
                'tipo_medida': 'weight',
                'unidad_base': 'kg',
                'factor_conversion': Decimal('0.453592'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad de peso del sistema imperial'
            },
            {
                'codigo': 'oz',
                'descripcion': 'Onza',
                'descripcion_ingles': 'Ounce',
                'simbolo': 'oz',
                'categoria': 'commercial',
                'tipo_medida': 'weight',
                'unidad_base': 'kg',
                'factor_conversion': Decimal('0.0283495'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Submúltiplo de la libra'
            },
            {
                'codigo': 'gal',
                'descripcion': 'Galón',
                'descripcion_ingles': 'Gallon',
                'simbolo': 'gal',
                'categoria': 'commercial',
                'tipo_medida': 'volume',
                'unidad_base': 'L',
                'factor_conversion': Decimal('3.78541'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad de volumen del sistema imperial'
            },
            {
                'codigo': 'ft',
                'descripcion': 'Pie',
                'descripcion_ingles': 'Foot',
                'simbolo': 'ft',
                'categoria': 'commercial',
                'tipo_medida': 'length',
                'unidad_base': 'm',
                'factor_conversion': Decimal('0.3048'),
                'uso_comun': False,
                'uso_productos': True,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Unidad de longitud del sistema imperial'
            },
            {
                'codigo': 'in',
                'descripcion': 'Pulgada',
                'descripcion_ingles': 'Inch',
                'simbolo': 'in',
                'categoria': 'commercial',
                'tipo_medida': 'length',
                'unidad_base': 'm',
                'factor_conversion': Decimal('0.0254'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.01'),
                'notas': 'Submúltiplo del pie'
            },
            
            # SPECIAL UNITS
            {
                'codigo': 'kWh',
                'descripcion': 'Kilovatio hora',
                'descripcion_ingles': 'Kilowatt hour',
                'simbolo': 'kWh',
                'categoria': 'metric',
                'tipo_medida': 'energy',
                'uso_comun': True,
                'uso_productos': False,
                'uso_servicios': True,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.001'),
                'notas': 'Unidad de energía eléctrica'
            },
            {
                'codigo': 'cal',
                'descripcion': 'Caloría',
                'descripcion_ingles': 'Calorie',
                'simbolo': 'cal',
                'categoria': 'metric',
                'tipo_medida': 'energy',
                'uso_comun': False,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Unidad de energía alimentaria'
            },
            {
                'codigo': 'kcal',
                'descripcion': 'Kilocaloría',
                'descripcion_ingles': 'Kilocalorie',
                'simbolo': 'kcal',
                'categoria': 'metric',
                'tipo_medida': 'energy',
                'unidad_base': 'cal',
                'factor_conversion': Decimal('1000'),
                'uso_comun': True,
                'uso_productos': True,
                'uso_servicios': False,
                'permite_decimales': True,
                'cantidad_minima': Decimal('0.1'),
                'notas': 'Múltiplo de la caloría'
            }
        ]
        
        session = self.SessionLocal()
        created_count = 0
        
        try:
            for unit_data in units_data:
                # Check if unit already exists
                existing = session.query(UnitsOfMeasure).filter(
                    UnitsOfMeasure.codigo == unit_data['codigo']
                ).first()
                
                if not existing:
                    # Create new unit
                    unit = UnitsOfMeasure(
                        codigo=unit_data['codigo'],
                        descripcion=unit_data['descripcion'],
                        descripcion_ingles=unit_data.get('descripcion_ingles'),
                        simbolo=unit_data.get('simbolo'),
                        categoria=unit_data['categoria'],
                        tipo_medida=unit_data.get('tipo_medida'),
                        unidad_base=unit_data.get('unidad_base'),
                        factor_conversion=unit_data.get('factor_conversion'),
                        uso_comun=unit_data.get('uso_comun', False),
                        uso_productos=unit_data.get('uso_productos', True),
                        uso_servicios=unit_data.get('uso_servicios', True),
                        permite_decimales=unit_data.get('permite_decimales', True),
                        cantidad_minima=unit_data.get('cantidad_minima'),
                        cantidad_maxima=unit_data.get('cantidad_maxima'),
                        activo=True,
                        version_rtc='443:2010',
                        fecha_vigencia_desde=datetime.now(timezone.utc),
                        notas=unit_data.get('notas'),
                        ejemplos_uso=unit_data.get('ejemplos_uso')
                    )
                    
                    session.add(unit)
                    created_count += 1
                    logger.info(f"Created unit: {unit_data['codigo']} - {unit_data['descripcion']}")
                else:
                    logger.info(f"Unit already exists: {unit_data['codigo']}")
            
            session.commit()
            logger.info(f"Successfully created {created_count} units of measure")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding units of measure: {str(e)}")
            raise
        finally:
            session.close()
        
        return created_count
    
    def clear_units(self) -> int:
        """
        Clear all units from database
        
        Returns:
            Number of units deleted
        """
        logger.info("Clearing all units of measure...")
        
        session = self.SessionLocal()
        try:
            count = session.query(UnitsOfMeasure).count()
            session.query(UnitsOfMeasure).delete()
            session.commit()
            logger.info(f"Deleted {count} units of measure")
            return count
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing units: {str(e)}")
            raise
        finally:
            session.close()


def main():
    """Main function to run units seeding"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed units of measure database')
    parser.add_argument('--clear', action='store_true', help='Clear existing units')
    parser.add_argument('--database-url', type=str, help='Database URL (optional)')
    
    args = parser.parse_args()
    
    # Initialize seeder
    seeder = UnitsSeeder(database_url=args.database_url)
    
    try:
        # Create tables
        seeder.create_tables()
        
        # Clear existing data if requested
        if args.clear:
            seeder.clear_units()
        
        # Seed data
        count = seeder.seed_rtc_443_units()
        
        logger.info(f"Units seeding completed successfully. Created {count} units.")
        
    except Exception as e:
        logger.error(f"Units seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()