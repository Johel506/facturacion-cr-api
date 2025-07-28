#!/usr/bin/env python3
"""
Phase 3: Document Creation Tests for Costa Rica Electronic Invoice API

This script tests document creation functionality including:
- Test 6: List documents (empty state)
- Test 7: Create simple electronic invoice
- Test 8: Get document by ID

Requirements:
- API server running on localhost:8000
- Valid tenant with API key
- Tenant must be verified and have certificate for document creation
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000/api/v1"
TENANT_ID = "78785c89-453a-4c9b-bafb-687f63360f33"
API_KEY = "cr_78785c89_1XrlyCQqcGP33Twwe46d7IdzsDvx64UvevaDdjwwd3ZnURt9z2gOyB01C5ClvVP7JlEl-g"

# Request headers for tenant management (X-API-Key)
tenant_headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Request headers for document operations (Bearer token)
document_headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Global variable to store created document ID
created_document_id = None


def test_list_documents_empty():
    """Test 6: List documents (should be empty initially)"""
    print("\n=== Test 6: List documents (empty initially) ===")
    
    try:
        response = requests.get(f"{API_BASE}/documentos/", headers=document_headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            total = data.get('pagination', {}).get('total', 0)
            
            print(f"Total documents: {total}")
            print(f"Items in response: {len(items)}")
            
            if total == 0:
                print("✅ Test 6 PASSED: No documents found (expected)")
                return True
            else:
                print(f"⚠️ Test 6 WARNING: Found {total} existing documents")
                return True
        else:
            print(f"❌ Test 6 FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test 6 FAILED: {str(e)}")
        return False


def reset_tenant_usage():
    """Reset tenant usage counter to 0"""
    print("\n=== Resetting tenant usage counter ===")
    
    try:
        response = requests.post(
            f"{API_BASE}/tenants/{TENANT_ID}/usage/reset",
            headers=tenant_headers
        )
        
        print(f"Reset response status: {response.status_code}")
        print(f"Reset response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Usage counter reset successfully")
            return True
        else:
            print(f"❌ Failed to reset usage counter: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error resetting usage: {e}")
        return False


def enable_tenant_for_testing():
    """Enable tenant for document creation (set verificado=True and handle certificate)"""
    print("\n=== Enabling tenant for document creation ===")
    
    # For testing purposes, we need to directly update the database
    # since there's no API endpoint to set verificado=True
    print("⚠️  Note: Tenant verification typically requires email verification")
    print("⚠️  For testing, we need to manually enable the tenant in the database")
    print(f"⚠️  Run this SQL command in your database:")
    print(f"     UPDATE tenants SET verificado = true, fecha_verificacion = NOW() WHERE id = '{TENANT_ID}';")
    
    # Check current tenant status
    response = requests.get(f"{API_BASE}/tenants/{TENANT_ID}", headers=tenant_headers)
    if response.status_code == 200:
        tenant_data = response.json()
        print(f"\nCurrent tenant status:")
        print(f"  - Active: {tenant_data.get('activo', 'unknown')}")
        print(f"  - Has Certificate: {tenant_data.get('tiene_certificado', 'unknown')}")
        print(f"  - Certificate Valid: {tenant_data.get('certificado_valido', 'unknown')}")
        print(f"  - Usage: {tenant_data.get('facturas_usadas_mes', 0)}/{tenant_data.get('limite_facturas_mes', 0)}")
        
        # For testing, we can try creating a simple test certificate
        if not tenant_data.get('tiene_certificado', False):
            print("\n⚠️  No certificate found. For production use, upload a valid P12 certificate.")
            print("⚠️  For testing, you may need to create or use a test certificate.")
    
    return False  # Return False since manual intervention is needed


def test_create_invoice():
    """Test 7: Create Simple Electronic Invoice (Type 01)"""
    print("\n=== Test 7: Create Simple Electronic Invoice (Type 01) ===")
    
    invoice_data = {
        "tipo_documento": "01",
        "condicion_venta": "01",
        "medio_pago": "01",
        "emisor": {
            "nombre": "Issuer Company S.A.",
            "identificacion": {
                "tipo": "02",
                "numero": "3101234567"
            },
            "ubicacion": {
                "provincia": 1,
                "canton": 1,
                "distrito": 1,
                "otras_senas": "100m north of central park"
            },
            "telefono": {
                "codigo_pais": 506,
                "numero": 22345678
            },
            "correo_electronico": ["issuer@company.com"],
            "codigo_actividad": "123456"
        },
        "receptor": {
            "nombre": "Juan Pérez Gómez",
            "identificacion": {
                "tipo": "01",
                "numero": "123456789"
            },
            "ubicacion": {
                "provincia": 1,
                "canton": 2,
                "distrito": 1,
                "otras_senas": "Blue house"
            },
            "telefono": {
                "codigo_pais": 506,
                "numero": 87654321
            },
            "correo_electronico": "juan@email.com"
        },
        "detalles": [
            {
                "numero_linea": 1,
                "codigo_cabys": "1010100010000",
                "descripcion": "Consulting service",
                "cantidad": 1,
                "unidad_medida": "unidad",
                "precio_unitario": 100.00,
                "monto_total": 100.00,
                "impuestos": [
                    {
                        "codigo": "01",
                        "codigo_tarifa_iva": "08",
                        "tarifa": 13.0,
                        "monto": 13.0
                    }
                ]
            }
        ],
        "resumen": {
            "codigo_tipo_moneda": "CRC",
            "total_servicio_gravado": 100.0,
            "total_iva": 13.0,
            "total_comprobante": 113.0
        }
    }
    
    try:
        response = requests.post(f"{API_BASE}/documentos/", 
                               headers=document_headers, 
                               json=invoice_data, 
                               timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            global created_document_id
            created_document_id = data.get("id")
            print(f"✅ Test 7 PASSED: Invoice created with ID: {created_document_id}")
            print(f"Document key: {data.get('clave_documento', 'N/A')}")
            return True, created_document_id
        else:
            print(f"❌ Test 7 FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Test 7 FAILED: {str(e)}")
        return False, None


def test_get_document(document_id):
    """Test 8: Get document by ID"""
    if not document_id:
        print("\n=== Test 8: SKIPPED (no document ID) ===")
        return False
        
    print(f"\n=== Test 8: Get document by ID ({document_id}) ===")
    try:
        response = requests.get(f"{API_BASE}/documentos/{document_id}", 
                               headers=document_headers, 
                               timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response:", json.dumps(data, indent=2))
            print("✅ Test 8 PASSED: Document retrieved successfully")
            return True
        else:
            print(f"❌ Test 8 FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test 8 FAILED: {str(e)}")
        return False


def main():
    """Run Phase 3 tests"""
    print("🚀 Starting Phase 3: Document Creation Tests")
    print(f"API Base: {API_BASE}")
    print(f"API Key: {API_KEY[:20]}...")
    
    # Check tenant status and requirements first
    enable_tenant_for_testing()
    
    tests_passed = 0
    total_tests = 3
    
    # Test 6: List documents (empty)
    if test_list_documents_empty():
        tests_passed += 1
    
    # Reset usage counter first
    if not reset_tenant_usage():
        print("⚠️ Could not reset usage counter, attempting document creation anyway...")
    
    # Test 7: Create invoice
    success, document_id = test_create_invoice()
    if success:
        tests_passed += 1
    
    # Test 8: Get document
    if test_get_document(document_id):
        tests_passed += 1
    
    print(f"\n📊 Phase 3 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 Phase 3 COMPLETED SUCCESSFULLY!")
        return True
    else:
        print("⚠️ Phase 3 completed with some failures")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
