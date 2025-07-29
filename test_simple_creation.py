#!/usr/bin/env python3
"""
Simple test to capture the exact exception in document creation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import traceback
from app.core.database import SessionLocal
from app.services.document_service import DocumentService
from app.schemas.documents import DocumentCreate
from app.schemas.document_items import DocumentLineItem, TaxData
from app.schemas.enums import DocumentType, TaxCode, IVATariffCode
from app.schemas.base import EmisorData, ReceptorData, IdentificationData, LocationData, PhoneData
from decimal import Decimal
from uuid import UUID
import json

# Load tenant info
with open('tenant_info.json', 'r') as f:
    tenant_info = json.load(f)

tenant_id = UUID(tenant_info['tenant_id'])

def test_simple_creation():
    """Test with properly structured data"""
    print("🧪 TESTING - Simple Document Creation")
    print("="*50)
    
    db = SessionLocal()
    try:
        service = DocumentService(db)
        
        # Create minimal document
        document_data = DocumentCreate(
            tipo_documento=DocumentType.FACTURA_ELECTRONICA,
            condicion_venta="01",  # Contado
            medio_pago="01",       # Efectivo  
            codigo_moneda="CRC",
            tipo_cambio=Decimal("1.0"),
            emisor=EmisorData(
                nombre="Test Company",
                identificacion=IdentificationData(
                    tipo="02",
                    numero="3101858030"
                ),
                codigo_actividad="620200",
                ubicacion=LocationData(
                    provincia=1,
                    canton=1,
                    distrito=1,
                    otras_senas="Test address"
                ),
                telefono=PhoneData(
                    codigo_pais=506,
                    numero=88888888
                ),
                correo_electronico=["test@test.com"]
            ),
            receptor=ReceptorData(
                nombre="Test Client",
                identificacion=IdentificationData(
                    tipo="01",
                    numero="123456789"
                ),
                ubicacion=LocationData(
                    provincia=1,
                    canton=1,
                    distrito=1,
                    otras_senas="Client address"
                )
            ),
            detalles=[
                DocumentLineItem(
                    numero_linea=1,
                    codigo_cabys="8111200100000",
                    descripcion="Test service",
                    unidad_medida="Sp",
                    cantidad=Decimal("1.0"),
                    precio_unitario=Decimal("100000.0"),
                    monto_total=Decimal("100000.0"),
                    impuestos=[
                        TaxData(
                            codigo=TaxCode.IVA,
                            codigo_tarifa_iva=IVATariffCode.TARIFA_GENERAL_13_PERCENT,
                            tarifa=Decimal("13.0"),
                            monto=Decimal("13000.0")
                        )
                    ]
                )
            ]
        )
        
        print("📝 Creating document...")
        document = service.create_document(
            tenant_id=tenant_id,
            document_data=document_data,
            created_by="test"
        )
        
        print("✅ SUCCESS!")
        print(f"Document ID: {document.id}")
        print(f"Document Key: {document.clave}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"Type: {type(e).__name__}")
        print("\n📄 Full traceback:")
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    test_simple_creation()
