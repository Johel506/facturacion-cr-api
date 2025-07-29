#!/usr/bin/env python3
"""Test document creation with enum workaround"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.document_service import DocumentService
from app.schemas.documents import DocumentCreate
from app.schemas.document_items import DocumentLineItem, TaxData
from app.schemas.enums import DocumentType, TaxCode, IVATariffCode, SaleCondition, PaymentMethod
from app.schemas.base import EmisorData, ReceptorData, IdentificationData, LocationData, PhoneData
from app.core.database import SessionLocal
from decimal import Decimal
from uuid import UUID
import traceback
import json

# Load tenant info
with open('tenant_info.json', 'r') as f:
    tenant_info = json.load(f)

tenant_id = UUID(tenant_info['tenant_id'])

def test_with_old_enum_values():
    """Test document creation using the old enum values that PostgreSQL expects"""
    print("🧪 TESTING - Document Creation with Old Enum Values")
    print("=" * 60)
    
    # Create document using the old enum values that PostgreSQL currently expects
    try:
        with SessionLocal() as db:
            service = DocumentService(db)
            print("📝 Creating document with old enum values...")
            
            # Build document data exactly like the working test
            emisor = EmisorData(
                identificacion=IdentificationData(
                    tipo="02",  # Using fixed enum value
                    numero="3101858030"
                ),
                nombre="Test Company",
                nombre_comercial=None,
                ubicacion=LocationData(
                    provincia=1,
                    canton=1,
                    distrito=1,
                    otras_senas="Test address"
                ),
                telefono=PhoneData(
                    codigo_pais=506,
                    numero="88888888"
                ),
                correo_electronico="test@test.com",
                codigo_actividad="620200"
            )
            
            receptor = ReceptorData(
                identificacion=IdentificationData(
                    tipo="01",  # Using fixed enum value
                    numero="123456789"
                ),
                nombre="Test Client",
                ubicacion=LocationData(
                    provincia=1,
                    canton=1,
                    distrito=1,
                    otras_senas="Client address"
                )
            )
            
            # Create tax data
            tax_data = TaxData(
                codigo=TaxCode.IVA,
                codigo_tarifa=IVATariffCode.TARIFA_GENERAL_13_PERCENT,
                tarifa=Decimal("13.0"),
                monto=Decimal("13000.0")
            )
            
            # Create line item  
            line_item = DocumentLineItem(
                numero_linea=1,
                codigo_cabys="1234567890123",
                descripcion="Test Item",
                unidad_medida="Unid",
                cantidad=Decimal("1"),
                precio_unitario=Decimal("100000.0"),
                monto_total=Decimal("100000.0"),
                subtotal=Decimal("100000.0"),
                monto_descuento=Decimal("0"),
                naturaleza_descuento="Descuento comercial",
                impuestos=[tax_data]
            )
            
            # Now use OLD enum values that PostgreSQL currently accepts
            document_data = DocumentCreate(
                tipo_documento=DocumentType.FACTURA_ELECTRONICA,  # Using enum, should convert to numeric
                emisor=emisor,
                receptor=receptor,
                # These are the key ones - use OLD enum values PostgreSQL expects
                condicion_venta=SaleCondition.CONTADO,    # This should be "CONTADO" string internally
                medio_pago=PaymentMethod.EFECTIVO,        # This should be "EFECTIVO" string internally  
                codigo_moneda="CRC",
                tipo_cambio=Decimal("1.0"),
                detalles=[line_item]
            )
            
            document = service.create_document(
                document_data,
                tenant_id,
                created_by="test"
            )
            
            print("✅ SUCCESS! Document created:")
            print(f"   📄 ID: {document.id}")
            print(f"   🔑 Key: {document.clave}")
            print(f"   📋 Type: {document.tipo_documento}")
            print(f"   👤 Emisor ID Type: {document.emisor_tipo_identificacion}")
            print(f"   👤 Receptor ID Type: {document.receptor_tipo_identificacion}")
            print(f"   💰 Sale Condition: {document.condicion_venta}")
            print(f"   💳 Payment Method: {document.medio_pago}")
            print(f"   📊 Status: {document.estado}")
            print(f"   💵 Total: ₡{document.total_comprobante:,.2f}")
            
            db.commit()
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"Type: {type(e).__name__}")
        print("\n📄 Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_with_old_enum_values()
    if success:
        print("\n🎉 DOCUMENT CREATION IS WORKING!")
        print("The API is ready for use, but salecondition and paymentmethod enums")
        print("still need to be migrated to numeric codes.")
    else:
        print("\n💥 Document creation still has issues to resolve.")
