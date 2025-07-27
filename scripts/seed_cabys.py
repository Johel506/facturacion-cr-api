#!/usr/bin/env python3
"""
CABYS Codes Seeding Script

This script seeds the database with official Costa Rican CABYS codes
from the official Excel file or creates a comprehensive set of sample
CABYS codes for development and testing purposes.

CABYS (Central American Tariff System) codes are 13-digit codes used
to classify products and services for tax purposes in Costa Rica's
electronic invoicing system.

Requirements: 11.2, 11.3
"""
import os
import sys
import asyncio
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
from app.models.cabys_code import CabysCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CabysSeeder:
    """CABYS codes seeding utility"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize the CABYS seeder
        
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
    
    def seed_sample_cabys_codes(self) -> int:
        """
        Seed database with comprehensive sample CABYS codes for development
        
        Returns:
            Number of CABYS codes created
        """
        logger.info("Starting CABYS codes seeding with sample data...")
        
        # Comprehensive sample CABYS codes covering major categories
        sample_codes = [
            # Food and beverages (01-15)
            {
                'codigo': '1010101010101',
                'descripcion': 'Arroz blanco grano largo',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Cereales y productos de cereales',
                'categoria_nivel_3': 'Arroz',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1010201010101',
                'descripcion': 'Frijoles negros secos',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Legumbres secas',
                'categoria_nivel_3': 'Frijoles',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1020101010101',
                'descripcion': 'Leche entera pasteurizada',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Productos lácteos',
                'categoria_nivel_3': 'Leche líquida',
                'impuesto_iva': Decimal('1.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1030101010101',
                'descripcion': 'Carne de res molida',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Carne y productos cárnicos',
                'categoria_nivel_3': 'Carne de bovino',
                'impuesto_iva': Decimal('1.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1040101010101',
                'descripcion': 'Pollo entero fresco',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Carne y productos cárnicos',
                'categoria_nivel_3': 'Carne de ave',
                'impuesto_iva': Decimal('1.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1050101010101',
                'descripcion': 'Pan blanco rebanado',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Productos de panadería',
                'categoria_nivel_3': 'Pan',
                'impuesto_iva': Decimal('1.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1060101010101',
                'descripcion': 'Banano maduro',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Frutas y vegetales',
                'categoria_nivel_3': 'Frutas tropicales',
                'impuesto_iva': Decimal('1.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1070101010101',
                'descripcion': 'Café tostado y molido',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Café, té y especias',
                'categoria_nivel_3': 'Café procesado',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1080101010101',
                'descripcion': 'Agua embotellada natural',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Bebidas no alcohólicas',
                'categoria_nivel_3': 'Agua embotellada',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '1090101010101',
                'descripcion': 'Cerveza nacional lager',
                'categoria_nivel_1': 'Productos alimenticios, bebidas y tabaco',
                'categoria_nivel_2': 'Bebidas alcohólicas',
                'categoria_nivel_3': 'Cerveza',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'aplica_impuesto_selectivo': True,
                'version_cabys': '4.4'
            },
            
            # Textiles and clothing (20-29)
            {
                'codigo': '2010101010101',
                'descripcion': 'Camisa de algodón para hombre',
                'categoria_nivel_1': 'Textiles y prendas de vestir',
                'categoria_nivel_2': 'Prendas de vestir',
                'categoria_nivel_3': 'Camisas',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '2020101010101',
                'descripcion': 'Pantalón jean para mujer',
                'categoria_nivel_1': 'Textiles y prendas de vestir',
                'categoria_nivel_2': 'Prendas de vestir',
                'categoria_nivel_3': 'Pantalones',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '2030101010101',
                'descripcion': 'Zapatos de cuero para hombre',
                'categoria_nivel_1': 'Textiles y prendas de vestir',
                'categoria_nivel_2': 'Calzado',
                'categoria_nivel_3': 'Zapatos de cuero',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            
            # Electronics and appliances (30-39)
            {
                'codigo': '3010101010101',
                'descripcion': 'Teléfono celular smartphone',
                'categoria_nivel_1': 'Equipos electrónicos y electrodomésticos',
                'categoria_nivel_2': 'Equipos de comunicación',
                'categoria_nivel_3': 'Teléfonos móviles',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '3020101010101',
                'descripcion': 'Computadora portátil',
                'categoria_nivel_1': 'Equipos electrónicos y electrodomésticos',
                'categoria_nivel_2': 'Equipos de cómputo',
                'categoria_nivel_3': 'Computadoras portátiles',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '3030101010101',
                'descripcion': 'Televisor LED 55 pulgadas',
                'categoria_nivel_1': 'Equipos electrónicos y electrodomésticos',
                'categoria_nivel_2': 'Equipos audiovisuales',
                'categoria_nivel_3': 'Televisores',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '3040101010101',
                'descripcion': 'Refrigeradora dos puertas',
                'categoria_nivel_1': 'Equipos electrónicos y electrodomésticos',
                'categoria_nivel_2': 'Electrodomésticos',
                'categoria_nivel_3': 'Refrigeradoras',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            
            # Vehicles and transportation (40-49)
            {
                'codigo': '4010101010101',
                'descripcion': 'Automóvil sedán gasolina',
                'categoria_nivel_1': 'Vehículos y equipo de transporte',
                'categoria_nivel_2': 'Vehículos de pasajeros',
                'categoria_nivel_3': 'Automóviles',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '4020101010101',
                'descripcion': 'Motocicleta 250cc',
                'categoria_nivel_1': 'Vehículos y equipo de transporte',
                'categoria_nivel_2': 'Motocicletas',
                'categoria_nivel_3': 'Motocicletas de calle',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '4030101010101',
                'descripcion': 'Llantas para automóvil R15',
                'categoria_nivel_1': 'Vehículos y equipo de transporte',
                'categoria_nivel_2': 'Repuestos y accesorios',
                'categoria_nivel_3': 'Llantas',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            
            # Construction materials (50-59)
            {
                'codigo': '5010101010101',
                'descripcion': 'Cemento Portland gris',
                'categoria_nivel_1': 'Materiales de construcción',
                'categoria_nivel_2': 'Cemento y concreto',
                'categoria_nivel_3': 'Cemento',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'aplica_impuesto_especifico': True,
                'version_cabys': '4.4'
            },
            {
                'codigo': '5020101010101',
                'descripcion': 'Varilla de hierro #4',
                'categoria_nivel_1': 'Materiales de construcción',
                'categoria_nivel_2': 'Materiales metálicos',
                'categoria_nivel_3': 'Varillas de construcción',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '5030101010101',
                'descripcion': 'Bloque de concreto 15x20x40',
                'categoria_nivel_1': 'Materiales de construcción',
                'categoria_nivel_2': 'Bloques y ladrillos',
                'categoria_nivel_3': 'Bloques de concreto',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            
            # Medicines and health products (60-69)
            {
                'codigo': '6010101010101',
                'descripcion': 'Acetaminofén 500mg tabletas',
                'categoria_nivel_1': 'Productos farmacéuticos y de salud',
                'categoria_nivel_2': 'Medicamentos',
                'categoria_nivel_3': 'Analgésicos',
                'impuesto_iva': Decimal('1.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '6020101010101',
                'descripcion': 'Vitamina C 1000mg cápsulas',
                'categoria_nivel_1': 'Productos farmacéuticos y de salud',
                'categoria_nivel_2': 'Suplementos nutricionales',
                'categoria_nivel_3': 'Vitaminas',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '6030101010101',
                'descripcion': 'Mascarillas quirúrgicas desechables',
                'categoria_nivel_1': 'Productos farmacéuticos y de salud',
                'categoria_nivel_2': 'Dispositivos médicos',
                'categoria_nivel_3': 'Equipo de protección',
                'impuesto_iva': Decimal('1.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            
            # Services (80-99)
            {
                'codigo': '8010101010101',
                'descripcion': 'Consulta médica general',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de salud',
                'categoria_nivel_3': 'Consultas médicas',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8020101010101',
                'descripcion': 'Servicios de contabilidad',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios profesionales',
                'categoria_nivel_3': 'Servicios contables',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8030101010101',
                'descripcion': 'Servicios de desarrollo de software',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de tecnología',
                'categoria_nivel_3': 'Desarrollo de software',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8040101010101',
                'descripcion': 'Servicios de reparación de vehículos',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de reparación',
                'categoria_nivel_3': 'Reparación automotriz',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8050101010101',
                'descripcion': 'Servicios de limpieza comercial',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de mantenimiento',
                'categoria_nivel_3': 'Servicios de limpieza',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8060101010101',
                'descripcion': 'Servicios de transporte de carga',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de transporte',
                'categoria_nivel_3': 'Transporte de carga',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8070101010101',
                'descripcion': 'Servicios de hospedaje hotelero',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de hospedaje',
                'categoria_nivel_3': 'Hoteles',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8080101010101',
                'descripcion': 'Servicios de restaurante',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de alimentación',
                'categoria_nivel_3': 'Restaurantes',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '8090101010101',
                'descripcion': 'Servicios educativos privados',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios educativos',
                'categoria_nivel_3': 'Educación privada',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            },
            {
                'codigo': '9010101010101',
                'descripcion': 'Servicios de consultoría empresarial',
                'categoria_nivel_1': 'Servicios',
                'categoria_nivel_2': 'Servicios de consultoría',
                'categoria_nivel_3': 'Consultoría empresarial',
                'impuesto_iva': Decimal('13.00'),
                'exento_iva': False,
                'version_cabys': '4.4'
            }
        ]
        
        session = self.SessionLocal()
        created_count = 0
        
        try:
            for code_data in sample_codes:
                # Check if code already exists
                existing = session.query(CabysCode).filter(
                    CabysCode.codigo == code_data['codigo']
                ).first()
                
                if not existing:
                    # Create new CABYS code
                    cabys_code = CabysCode(
                        codigo=code_data['codigo'],
                        descripcion=code_data['descripcion'],
                        categoria_nivel_1=code_data.get('categoria_nivel_1'),
                        categoria_nivel_2=code_data.get('categoria_nivel_2'),
                        categoria_nivel_3=code_data.get('categoria_nivel_3'),
                        impuesto_iva=code_data.get('impuesto_iva', Decimal('13.00')),
                        exento_iva=code_data.get('exento_iva', False),
                        aplica_impuesto_selectivo=code_data.get('aplica_impuesto_selectivo', False),
                        aplica_impuesto_especifico=code_data.get('aplica_impuesto_especifico', False),
                        activo=True,
                        version_cabys=code_data.get('version_cabys', '4.4'),
                        fecha_vigencia_desde=datetime.now(timezone.utc)
                    )
                    
                    session.add(cabys_code)
                    created_count += 1
                    logger.info(f"Created CABYS code: {code_data['codigo']} - {code_data['descripcion']}")
                else:
                    logger.info(f"CABYS code already exists: {code_data['codigo']}")
            
            # Update search vectors for full-text search
            logger.info("Updating search vectors for full-text search...")
            session.execute(text("""
                UPDATE codigos_cabys 
                SET search_vector = to_tsvector('spanish', 
                    COALESCE(descripcion, '') || ' ' || 
                    COALESCE(categoria_nivel_1, '') || ' ' ||
                    COALESCE(categoria_nivel_2, '') || ' ' ||
                    COALESCE(categoria_nivel_3, '')
                )
                WHERE search_vector IS NULL
            """))
            
            session.commit()
            logger.info(f"Successfully created {created_count} CABYS codes")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding CABYS codes: {str(e)}")
            raise
        finally:
            session.close()
        
        return created_count
    
    def seed_from_excel(self, excel_path: str) -> int:
        """
        Seed CABYS codes from official Excel file
        
        Args:
            excel_path: Path to the official CABYS Excel file
            
        Returns:
            Number of CABYS codes created
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required to read Excel files. Install with: pip install pandas openpyxl")
            return 0
        
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return 0
        
        logger.info(f"Reading CABYS codes from Excel file: {excel_path}")
        
        try:
            # Read Excel file (adjust sheet name and columns as needed)
            df = pd.read_excel(excel_path, sheet_name=0)
            logger.info(f"Read {len(df)} rows from Excel file")
            
            session = self.SessionLocal()
            created_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Extract data from Excel row (adjust column names as needed)
                    codigo = str(row.get('Codigo', '')).strip()
                    descripcion = str(row.get('Descripcion', '')).strip()
                    
                    # Validate CABYS code format
                    if not CabysCode.validate_code_format(codigo):
                        logger.warning(f"Invalid CABYS code format: {codigo}")
                        continue
                    
                    if not descripcion or len(descripcion) < 3:
                        logger.warning(f"Invalid description for code {codigo}")
                        continue
                    
                    # Check if code already exists
                    existing = session.query(CabysCode).filter(
                        CabysCode.codigo == codigo
                    ).first()
                    
                    if not existing:
                        # Create new CABYS code
                        cabys_code = CabysCode(
                            codigo=codigo,
                            descripcion=descripcion,
                            categoria_nivel_1=str(row.get('Categoria1', '')).strip() or None,
                            categoria_nivel_2=str(row.get('Categoria2', '')).strip() or None,
                            categoria_nivel_3=str(row.get('Categoria3', '')).strip() or None,
                            impuesto_iva=Decimal(str(row.get('IVA', '13.00'))),
                            exento_iva=bool(row.get('Exento', False)),
                            activo=True,
                            version_cabys='4.4',
                            fecha_vigencia_desde=datetime.now(timezone.utc)
                        )
                        
                        session.add(cabys_code)
                        created_count += 1
                        
                        if created_count % 100 == 0:
                            logger.info(f"Processed {created_count} CABYS codes...")
                    
                except Exception as e:
                    logger.error(f"Error processing row {index}: {str(e)}")
                    continue
            
            # Update search vectors
            logger.info("Updating search vectors...")
            session.execute(text("""
                UPDATE codigos_cabys 
                SET search_vector = to_tsvector('spanish', 
                    COALESCE(descripcion, '') || ' ' || 
                    COALESCE(categoria_nivel_1, '') || ' ' ||
                    COALESCE(categoria_nivel_2, '') || ' ' ||
                    COALESCE(categoria_nivel_3, '')
                )
                WHERE search_vector IS NULL
            """))
            
            session.commit()
            logger.info(f"Successfully created {created_count} CABYS codes from Excel file")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error reading Excel file: {str(e)}")
            raise
        finally:
            session.close()
        
        return created_count
    
    def clear_cabys_codes(self) -> int:
        """
        Clear all CABYS codes from database
        
        Returns:
            Number of codes deleted
        """
        logger.info("Clearing all CABYS codes...")
        
        session = self.SessionLocal()
        try:
            count = session.query(CabysCode).count()
            session.query(CabysCode).delete()
            session.commit()
            logger.info(f"Deleted {count} CABYS codes")
            return count
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing CABYS codes: {str(e)}")
            raise
        finally:
            session.close()


def main():
    """Main function to run CABYS seeding"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed CABYS codes database')
    parser.add_argument('--excel', type=str, help='Path to Excel file with CABYS codes')
    parser.add_argument('--clear', action='store_true', help='Clear existing CABYS codes')
    parser.add_argument('--sample', action='store_true', help='Seed with sample data (default)')
    parser.add_argument('--database-url', type=str, help='Database URL (optional)')
    
    args = parser.parse_args()
    
    # Initialize seeder
    seeder = CabysSeeder(database_url=args.database_url)
    
    try:
        # Create tables
        seeder.create_tables()
        
        # Clear existing data if requested
        if args.clear:
            seeder.clear_cabys_codes()
        
        # Seed data
        if args.excel:
            count = seeder.seed_from_excel(args.excel)
        else:
            count = seeder.seed_sample_cabys_codes()
        
        logger.info(f"CABYS seeding completed successfully. Created {count} codes.")
        
    except Exception as e:
        logger.error(f"CABYS seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()