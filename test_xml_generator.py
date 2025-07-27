#!/usr/bin/env python3
"""
Simple test script for XML generator to verify functionality.
"""
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from schemas.enums import DocumentType, IdentificationType, SaleCondition, PaymentMethod, TaxCode, IVATariffCode
from schemas.base import EmisorData, ReceptorData, IdentificationData, LocationData, PhoneData
from schemas.documents import DocumentCreate
from schemas.document_items import DocumentLineItem, TaxData
from utils.xml_generator import generate_document_xml

def create_test_document():
    """Create a test document for XML generation."""
    
    # Create emisor data
    emisor = EmisorData(
        nombre="Empresa de Prueba S.A.",
        identificacion=IdentificationData(
            tipo=IdentificationType.CEDULA_JURIDICA,
            numero="3101123456"
        ),
        nombre_comercial="Empresa Prueba",
        ubicacion=LocationData(
            provincia=1,
            canton=1,
            distrito=1,
            barrio="Centro",
            otras_senas="100 metros norte de la iglesia"
        ),
        telefono=PhoneData(
            codigo_pais=506,
            numero=22334455
        ),
        correo_electronico=["contacto@empresa.cr"],
        codigo_actividad="123456"
    )
    
    # Create receptor data
    receptor = ReceptorData(
        nombre="Cliente de Prueba",
        identificacion=IdentificationData(
            tipo=IdentificationType.CEDULA_FISICA,
            numero="123456789"
        ),
        ubicacion=LocationData(
            provincia=1,
            canton=2,
            distrito=3,
            otras_senas="200 metros sur del parque"
        ),
        correo_electronico="cliente@email.com"
    )
    
    # Create line item with tax
    tax_data = TaxData(
        codigo=TaxCode.IVA,
        codigo_tarifa_iva=IVATariffCode.TARIFA_GENERAL_13_PERCENT,
        tarifa=Decimal("13.0"),
        monto=Decimal("13.00")
    )
    
    line_item = DocumentLineItem(
        numero_linea=1,
        codigo_cabys="1234567890123",
        cantidad=Decimal("1.0"),
        unidad_medida="Unid",
        descripcion="Producto de prueba",
        precio_unitario=Decimal("100.00"),
        monto_total=Decimal("100.00"),
        impuestos=[tax_data]
    )
    
    # Create document
    document = DocumentCreate(
        tipo_documento=DocumentType.FACTURA_ELECTRONICA,
        emisor=emisor,
        receptor=receptor,
        condicion_venta=SaleCondition.CONTADO,
        medio_pago=PaymentMethod.EFECTIVO,
        codigo_moneda="CRC",
        tipo_cambio=Decimal("1.0"),
        detalles=[line_item]
    )
    
    return document

def main():
    """Test the XML generator."""
    try:
        print("Creating test document...")
        document = create_test_document()
        
        print("Generating XML...")
        xml_content = generate_document_xml(
            document_data=document,
            tenant_id="test-tenant-123",
            numero_consecutivo="00100001010000000001",
            clave="50612345678901234567890123456789012345678901234567890"
        )
        
        print("XML generated successfully!")
        print("=" * 80)
        print(xml_content)
        print("=" * 80)
        
        # Basic validation
        if "FacturaElectronica" in xml_content:
            print("✓ Root element found")
        else:
            print("✗ Root element not found")
            
        if "Clave" in xml_content:
            print("✓ Document key found")
        else:
            print("✗ Document key not found")
            
        if "Emisor" in xml_content:
            print("✓ Emisor section found")
        else:
            print("✗ Emisor section not found")
            
        if "Receptor" in xml_content:
            print("✓ Receptor section found")
        else:
            print("✗ Receptor section not found")
            
        if "DetalleServicio" in xml_content:
            print("✓ Line items section found")
        else:
            print("✗ Line items section not found")
            
        if "ResumenFactura" in xml_content:
            print("✓ Summary section found")
        else:
            print("✗ Summary section not found")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())