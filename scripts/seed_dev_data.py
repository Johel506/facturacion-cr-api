#!/usr/bin/env python3
"""
Development Sample Data Seeding Script

This script creates comprehensive sample data for development and testing
purposes, including sample tenants, documents, and related data to facilitate
development and testing of the Costa Rica electronic invoicing API.

Requirements: 18.3
"""
import os
import sys
import logging
import secrets
from pathlib import Path
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import uuid

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base
from app.models.tenant import Tenant
from app.models.document import Document
from app.models.document_detail import DocumentDetail
from app.models.cabys_code import CabysCode
from app.models.geographic_location import GeographicLocation
from app.models.units_of_measure import UnitsOfMeasure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DevDataSeeder:
    """Development sample data seeding utility"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize the dev data seeder
        
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
    
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)
    
    def generate_document_key(self, tenant_cedula: str, doc_type: str, consecutive: int) -> str:
        """
        Generate a 50-character document key
        
        Format: [Country(3)][Day(2)][Month(2)][Year(2)][Issuer(12)][Branch(3)][Terminal(5)][DocType(2)][Sequential(10)][SecurityCode(8)]
        """
        now = datetime.now()
        country = "506"  # Costa Rica
        day = f"{now.day:02d}"
        month = f"{now.month:02d}"
        year = f"{now.year % 100:02d}"
        issuer = f"{tenant_cedula:0>12}"[:12]  # Pad or truncate to 12 digits
        branch = "001"
        terminal = "00001"
        doc_type_code = doc_type
        sequential = f"{consecutive:010d}"
        security_code = f"{secrets.randbelow(100000000):08d}"
        
        return f"{country}{day}{month}{year}{issuer}{branch}{terminal}{doc_type_code}{sequential}{security_code}"
    
    def generate_consecutive_number(self, doc_type: str, consecutive: int) -> str:
        """
        Generate a 20-digit consecutive number
        
        Format: [Branch(3)][Terminal(5)][DocType(2)][Sequential(10)]
        """
        branch = "001"
        terminal = "00001"
        sequential = f"{consecutive:010d}"
        
        return f"{branch}{terminal}{doc_type}{sequential}"
    
    def seed_sample_tenants(self) -> int:
        """
        Seed database with sample tenants for development
        
        Returns:
            Number of tenants created
        """
        logger.info("Starting sample tenants seeding...")
        
        sample_tenants = [
            {
                'nombre_empresa': 'Tecnología Avanzada S.A.',
                'cedula_juridica': '3101234567',
                'email_contacto': 'admin@tecavanzada.cr',
                'plan': 'empresa',
                'limite_facturas_mes': 0,  # Unlimited
                'activo': True
            },
            {
                'nombre_empresa': 'Comercial El Buen Precio Ltda.',
                'cedula_juridica': '3102345678',
                'email_contacto': 'facturacion@buenprecio.cr',
                'plan': 'pro',
                'limite_facturas_mes': 1000,
                'activo': True
            },
            {
                'nombre_empresa': 'Servicios Profesionales Integrales',
                'cedula_juridica': '3103456789',
                'email_contacto': 'info@spi.cr',
                'plan': 'basico',
                'limite_facturas_mes': 100,
                'activo': True
            },
            {
                'nombre_empresa': 'Restaurante La Cocina Tica',
                'cedula_juridica': '3104567890',
                'email_contacto': 'gerencia@cocinatica.cr',
                'plan': 'pro',
                'limite_facturas_mes': 1000,
                'activo': True
            },
            {
                'nombre_empresa': 'Ferretería y Construcción Central',
                'cedula_juridica': '3105678901',
                'email_contacto': 'ventas@ferrecentral.cr',
                'plan': 'pro',
                'limite_facturas_mes': 1000,
                'activo': True
            },
            {
                'nombre_empresa': 'Clínica Médica San Rafael',
                'cedula_juridica': '3106789012',
                'email_contacto': 'administracion@clinicasanrafael.cr',
                'plan': 'basico',
                'limite_facturas_mes': 100,
                'activo': True
            },
            {
                'nombre_empresa': 'Transporte y Logística Express',
                'cedula_juridica': '3107890123',
                'email_contacto': 'operaciones@logisticaexpress.cr',
                'plan': 'pro',
                'limite_facturas_mes': 1000,
                'activo': True
            },
            {
                'nombre_empresa': 'Supermercado Familiar',
                'cedula_juridica': '3108901234',
                'email_contacto': 'gerencia@superfamiliar.cr',
                'plan': 'empresa',
                'limite_facturas_mes': 0,  # Unlimited
                'activo': True
            },
            {
                'nombre_empresa': 'Consultoría Empresarial Moderna',
                'cedula_juridica': '3109012345',
                'email_contacto': 'contacto@consultoriamoderna.cr',
                'plan': 'basico',
                'limite_facturas_mes': 100,
                'activo': True
            },
            {
                'nombre_empresa': 'Taller Automotriz El Mecánico',
                'cedula_juridica': '3100123456',
                'email_contacto': 'taller@elmecanico.cr',
                'plan': 'basico',
                'limite_facturas_mes': 100,
                'activo': True
            }
        ]
        
        session = self.SessionLocal()
        created_count = 0
        
        try:
            for tenant_data in sample_tenants:
                # Check if tenant already exists
                existing = session.query(Tenant).filter(
                    Tenant.cedula_juridica == tenant_data['cedula_juridica']
                ).first()
                
                if not existing:
                    # Create new tenant
                    tenant = Tenant(
                        id=uuid.uuid4(),
                        nombre_empresa=tenant_data['nombre_empresa'],
                        cedula_juridica=tenant_data['cedula_juridica'],
                        api_key=self.generate_api_key(),
                        email_contacto=tenant_data['email_contacto'],
                        plan=tenant_data['plan'],
                        limite_facturas_mes=tenant_data['limite_facturas_mes'],
                        facturas_usadas_mes=0,
                        activo=tenant_data['activo']
                    )
                    
                    session.add(tenant)
                    created_count += 1
                    logger.info(f"Created tenant: {tenant_data['nombre_empresa']} (API Key: {tenant.api_key})")
                else:
                    logger.info(f"Tenant already exists: {tenant_data['nombre_empresa']}")
            
            session.commit()
            logger.info(f"Successfully created {created_count} sample tenants")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding sample tenants: {str(e)}")
            raise
        finally:
            session.close()
        
        return created_count
    
    def seed_sample_documents(self) -> int:
        """
        Seed database with sample documents for development
        
        Returns:
            Number of documents created
        """
        logger.info("Starting sample documents seeding...")
        
        session = self.SessionLocal()
        created_count = 0
        
        try:
            # Get sample tenants
            tenants = session.query(Tenant).filter(Tenant.activo == True).limit(5).all()
            if not tenants:
                logger.warning("No active tenants found. Please seed tenants first.")
                return 0
            
            # Get sample CABYS codes
            cabys_codes = session.query(CabysCode).filter(CabysCode.activo == True).limit(20).all()
            if not cabys_codes:
                logger.warning("No CABYS codes found. Please seed CABYS codes first.")
                return 0
            
            # Get sample units
            units = session.query(UnitsOfMeasure).filter(UnitsOfMeasure.activo == True).limit(10).all()
            if not units:
                logger.warning("No units of measure found. Please seed units first.")
                return 0
            
            # Document types to create
            doc_types = [
                ('01', 'Factura Electrónica'),
                ('02', 'Nota de Débito Electrónica'),
                ('03', 'Nota de Crédito Electrónica'),
                ('04', 'Tiquete Electrónico'),
                ('05', 'Factura Electrónica de Exportación'),
                ('06', 'Factura Electrónica de Compra'),
                ('07', 'Recibo Electrónico de Pago')
            ]
            
            consecutive_counter = 1
            
            for tenant in tenants:
                for doc_type_code, doc_type_name in doc_types:
                    # Create 2-3 documents per type per tenant
                    for doc_num in range(1, 4):
                        try:
                            # Generate document identifiers
                            consecutive = self.generate_consecutive_number(doc_type_code, consecutive_counter)
                            clave = self.generate_document_key(tenant.cedula_juridica, doc_type_code, consecutive_counter)
                            
                            # Create sample document
                            document = Document(
                                id=uuid.uuid4(),
                                tenant_id=tenant.id,
                                tipo_documento=doc_type_code,
                                numero_consecutivo=consecutive,
                                clave=clave,
                                fecha_emision=datetime.now(timezone.utc) - timedelta(days=secrets.randbelow(30)),
                                
                                # Emisor (tenant) information
                                emisor_nombre=tenant.nombre_empresa,
                                emisor_tipo_identificacion='02',  # Cédula jurídica
                                emisor_numero_identificacion=tenant.cedula_juridica,
                                emisor_codigo_actividad='620900',  # Software development
                                
                                # Receptor information (sample customers)
                                receptor_nombre=f"Cliente Ejemplo {doc_num}",
                                receptor_tipo_identificacion='01',  # Cédula física
                                receptor_numero_identificacion=f"{secrets.randbelow(9)+1}-{secrets.randbelow(9000)+1000:04d}-{secrets.randbelow(9000)+1000:04d}",
                                receptor_email=f"cliente{doc_num}@example.com",
                                
                                # Transaction details
                                condicion_venta='01',  # Contado
                                medio_pago='01',  # Efectivo
                                
                                # Currency and totals (will be calculated from details)
                                codigo_moneda='CRC',
                                tipo_cambio=Decimal('1.0'),
                                total_venta_neta=Decimal('0'),
                                total_impuesto=Decimal('0'),
                                total_comprobante=Decimal('0'),
                                
                                # XML and status
                                xml_original='<xml>Sample XML content</xml>',
                                estado='pendiente'
                            )
                            
                            session.add(document)
                            session.flush()  # Get the document ID
                            
                            # Create document details (line items)
                            total_neto = Decimal('0')
                            total_impuesto = Decimal('0')
                            
                            num_items = secrets.randbelow(3) + 1  # 1-3 items per document
                            for item_num in range(1, num_items + 1):
                                cabys_code = secrets.choice(cabys_codes)
                                unit = secrets.choice(units)
                                
                                cantidad = Decimal(str(secrets.randbelow(10) + 1))
                                precio_unitario = Decimal(str(secrets.randbelow(50000) + 1000))  # 1000-51000
                                monto_total = cantidad * precio_unitario
                                
                                # Calculate tax (13% IVA by default)
                                impuesto_monto = monto_total * (cabys_code.impuesto_iva / Decimal('100'))
                                
                                detail = DocumentDetail(
                                    id=uuid.uuid4(),
                                    documento_id=document.id,
                                    numero_linea=item_num,
                                    codigo_cabys=cabys_code.codigo,
                                    descripcion=cabys_code.descripcion,
                                    cantidad=cantidad,
                                    unidad_medida=unit.codigo,
                                    precio_unitario=precio_unitario,
                                    monto_total=monto_total,
                                    monto_descuento=Decimal('0'),
                                    impuesto_codigo='01',  # IVA
                                    impuesto_codigo_tarifa='08',  # 13%
                                    impuesto_tarifa=cabys_code.impuesto_iva,
                                    impuesto_monto=impuesto_monto
                                )
                                
                                session.add(detail)
                                total_neto += monto_total
                                total_impuesto += impuesto_monto
                            
                            # Update document totals
                            document.total_venta_neta = total_neto
                            document.total_impuesto = total_impuesto
                            document.total_comprobante = total_neto + total_impuesto
                            
                            consecutive_counter += 1
                            created_count += 1
                            
                            logger.info(f"Created document: {doc_type_name} {consecutive} for {tenant.nombre_empresa}")
                            
                        except Exception as e:
                            logger.error(f"Error creating document for tenant {tenant.nombre_empresa}: {str(e)}")
                            continue
            
            session.commit()
            logger.info(f"Successfully created {created_count} sample documents")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding sample documents: {str(e)}")
            raise
        finally:
            session.close()
        
        return created_count
    
    def seed_all_sample_data(self) -> Dict[str, int]:
        """
        Seed all sample data for development
        
        Returns:
            Dictionary with counts of created items
        """
        logger.info("Starting comprehensive sample data seeding...")
        
        results = {}
        
        try:
            # Create tables first
            self.create_tables()
            
            # Seed tenants
            results['tenants'] = self.seed_sample_tenants()
            
            # Seed documents (requires tenants, CABYS codes, and units)
            results['documents'] = self.seed_sample_documents()
            
            logger.info("Sample data seeding completed successfully")
            logger.info(f"Results: {results}")
            
        except Exception as e:
            logger.error(f"Error in comprehensive sample data seeding: {str(e)}")
            raise
        
        return results
    
    def clear_all_sample_data(self) -> Dict[str, int]:
        """
        Clear all sample data from database
        
        Returns:
            Dictionary with counts of deleted items
        """
        logger.info("Clearing all sample data...")
        
        session = self.SessionLocal()
        results = {}
        
        try:
            # Clear in reverse dependency order
            results['document_details'] = session.query(DocumentDetail).count()
            session.query(DocumentDetail).delete()
            
            results['documents'] = session.query(Document).count()
            session.query(Document).delete()
            
            results['tenants'] = session.query(Tenant).count()
            session.query(Tenant).delete()
            
            session.commit()
            logger.info(f"Cleared sample data: {results}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing sample data: {str(e)}")
            raise
        finally:
            session.close()
        
        return results
    
    def print_sample_api_keys(self):
        """Print API keys for sample tenants for development use"""
        logger.info("Sample tenant API keys for development:")
        
        session = self.SessionLocal()
        try:
            tenants = session.query(Tenant).filter(Tenant.activo == True).all()
            
            print("\n" + "="*80)
            print("SAMPLE TENANT API KEYS FOR DEVELOPMENT")
            print("="*80)
            
            for tenant in tenants:
                print(f"Company: {tenant.nombre_empresa}")
                print(f"Legal ID: {tenant.cedula_juridica}")
                print(f"API Key: {tenant.api_key}")
                print(f"Plan: {tenant.plan}")
                print(f"Email: {tenant.email_contacto}")
                print("-" * 80)
            
            print("\nUse these API keys in the X-API-Key header for testing")
            print("Example: curl -H 'X-API-Key: <api_key>' http://localhost:8000/v1/documentos")
            print("="*80 + "\n")
            
        except Exception as e:
            logger.error(f"Error retrieving API keys: {str(e)}")
        finally:
            session.close()


def main():
    """Main function to run development data seeding"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed development sample data')
    parser.add_argument('--tenants', action='store_true', help='Seed sample tenants only')
    parser.add_argument('--documents', action='store_true', help='Seed sample documents only')
    parser.add_argument('--all', action='store_true', help='Seed all sample data (default)')
    parser.add_argument('--clear', action='store_true', help='Clear all sample data')
    parser.add_argument('--show-keys', action='store_true', help='Show API keys for sample tenants')
    parser.add_argument('--database-url', type=str, help='Database URL (optional)')
    
    args = parser.parse_args()
    
    # Initialize seeder
    seeder = DevDataSeeder(database_url=args.database_url)
    
    try:
        if args.clear:
            results = seeder.clear_all_sample_data()
            logger.info(f"Sample data clearing completed: {results}")
        elif args.show_keys:
            seeder.print_sample_api_keys()
        elif args.tenants:
            count = seeder.seed_sample_tenants()
            logger.info(f"Sample tenants seeding completed. Created {count} tenants.")
        elif args.documents:
            count = seeder.seed_sample_documents()
            logger.info(f"Sample documents seeding completed. Created {count} documents.")
        else:
            # Default: seed all
            results = seeder.seed_all_sample_data()
            logger.info(f"Development data seeding completed successfully: {results}")
            
            # Show API keys for convenience
            seeder.print_sample_api_keys()
        
    except Exception as e:
        logger.error(f"Development data seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()