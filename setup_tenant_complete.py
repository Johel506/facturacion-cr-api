#!/usr/bin/env python3
"""
Script completo para crear tenant y subir certificado P12
"""

import requests
import base64
import os
import sys
import json
import uuid

# Configuración API
API_BASE = "http://localhost:8001/api/v1"

# Datos del tenant a crear
TENANT_DATA = {
    "nombre_empresa": "Johel Venegas Dev",
    "cedula_juridica": "3-101-858030",  # Formato correcto: 3-101-xxxxxx
    "email_contacto": "joheldev@test.com",
    "telefono": "70226553",
    "plan": "pro",
    "direccion": "San José, Costa Rica",
    # Ubicación: San José (1), San José (01), Carmen (01)
    "provincia": 1,
    "canton": 1,
    "distrito": 1,
    "otras_senas": "Desarrollo de software"
}

# Datos del certificado
CERT_FILE = "011858030301.p12"
CERT_PASSWORD = "9285"

def create_tenant():
    """Crear nuevo tenant"""
    print("👤 Creando nuevo tenant...")
    print(f"Empresa: {TENANT_DATA['nombre_empresa']}")
    print(f"Email: {TENANT_DATA['email_contacto']}")
    print(f"Cédula Jurídica: {TENANT_DATA['cedula_juridica']}")
    
    try:
        response = requests.post(
            f"{API_BASE}/tenants/",
            json=TENANT_DATA,
            timeout=30
        )
        
        print(f"📥 Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print("✅ ¡Tenant creado exitosamente!")
            
            # Parse the nested response structure
            tenant_data = data.get('data', {})
            tenant_info = tenant_data.get('tenant', {})
            tenant_id = tenant_info.get('id')
            api_key = tenant_data.get('api_key')
            
            if tenant_id and api_key:
                print(f"🆔 Tenant ID: {tenant_id}")
                print(f"🔑 API Key: {api_key}")
                
                # Guardar en archivo para referencia
                tenant_info_save = {
                    "tenant_id": tenant_id,
                    "api_key": api_key,
                    "empresa": TENANT_DATA['nombre_empresa'],
                    "email": TENANT_DATA['email_contacto'],
                    "cedula": tenant_info.get('cedula_juridica', TENANT_DATA['cedula_juridica'])
                }
                
                with open("tenant_info.json", "w") as f:
                    json.dump(tenant_info_save, f, indent=2)
                print("💾 Información guardada en tenant_info.json")
                
                return tenant_id, api_key
            else:
                print("❌ No se pudo obtener tenant_id o api_key de la respuesta")
                print(f"Respuesta: {response.text}")
                return None, None
        else:
            print(f"❌ Error creando tenant: HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ Error en la petición: {e}")
        return None, None

def upload_certificate(tenant_id, api_key):
    """Subir certificado P12 al tenant"""
    print(f"\n📤 Subiendo certificado {CERT_FILE} al tenant {tenant_id}...")
    
    # Verificar que el archivo existe
    if not os.path.exists(CERT_FILE):
        print(f"❌ Error: Archivo {CERT_FILE} no encontrado")
        print(f"   Asegúrate de que esté en: {os.path.abspath(CERT_FILE)}")
        return False
    
    # Leer el archivo P12
    try:
        with open(CERT_FILE, 'rb') as f:
            cert_bytes = f.read()
        print(f"✅ Archivo leído exitosamente ({len(cert_bytes)} bytes)")
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return False
    
    # Convertir a base64
    cert_base64 = base64.b64encode(cert_bytes).decode('utf-8')
    print(f"✅ Certificado convertido a base64 ({len(cert_base64)} caracteres)")
    
    # Preparar headers
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Preparar payload
    payload = {
        "certificado_p12": cert_base64,
        "password_certificado": CERT_PASSWORD
    }
    
    # Hacer la petición
    try:
        print(f"🚀 Enviando certificado al API...")
        response = requests.post(
            f"{API_BASE}/tenants/{tenant_id}/certificate",
            headers=headers,
            json=payload,
            timeout=60  # Mayor timeout para certificados grandes
        )
        
        print(f"📥 Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("✅ ¡Certificado subido exitosamente!")
            print("📄 Respuesta del servidor:")
            print(response.text)
            return True
        else:
            print(f"❌ Error subiendo certificado: HTTP {response.status_code}")
            print(f"📄 Respuesta del servidor:")
            print(response.text)
            
            # Si es error 400, probablemente sea la contraseña
            if response.status_code == 400:
                print("\n💡 Posibles causas:")
                print("   - Contraseña incorrecta (PIN)")
                print("   - Archivo P12 corrupto")
                print("   - Formato del certificado no válido")
            
            return False
            
    except Exception as e:
        print(f"❌ Error en la petición: {e}")
        return False

def verify_certificate_status(tenant_id, api_key):
    """Verificar el estado del certificado después de subir"""
    print(f"\n🔍 Verificando estado del certificado...")
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{API_BASE}/tenants/{tenant_id}/certificate/status",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Estado del certificado:")
            cert_status = data.get('data', {}).get('certificate_status', {})
            print(f"   - Tiene certificado: {cert_status.get('tiene_certificado', 'unknown')}")
            print(f"   - Válido: {cert_status.get('valido', 'unknown')}")
            print(f"   - Fecha vencimiento: {cert_status.get('fecha_vencimiento', 'unknown')}")
            print(f"   - Días para vencer: {cert_status.get('dias_para_vencer', 'unknown')}")
            print(f"   - Emisor: {cert_status.get('emisor', 'unknown')}")
            print(f"   - Sujeto: {cert_status.get('sujeto', 'unknown')}")
            return True
        else:
            print(f"⚠️ No se pudo obtener estado: HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error verificando estado: {e}")
        return False

def verify_tenant_status(tenant_id, api_key):
    """Verificar estado del tenant y activarlo si es necesario"""
    print(f"\n🔍 Verificando estado del tenant...")
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{API_BASE}/tenants/{tenant_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Estado del tenant:")
            print(f"   - Activo: {data.get('activo', 'unknown')}")
            print(f"   - Verificado: {data.get('verificado', 'unknown')}")
            print(f"   - Plan: {data.get('plan', 'unknown')}")
            print(f"   - Límite mensual: {data.get('limite_facturas_mes', 'unknown')}")
            print(f"   - Facturas usadas: {data.get('facturas_usadas_mes', 'unknown')}")
            return True
        else:
            print(f"⚠️ No se pudo obtener estado del tenant: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error verificando tenant: {e}")
        return False

def main():
    print("🏗️ Setup Completo de Tenant y Certificado")
    print("=" * 50)
    
    # Paso 1: Crear tenant
    tenant_id, api_key = create_tenant()
    if not tenant_id or not api_key:
        print("\n❌ No se pudo crear el tenant. Abortando.")
        return False
    
    print(f"\n✅ Tenant creado exitosamente!")
    print(f"🆔 ID: {tenant_id}")
    print(f"🔑 API Key: {api_key}")
    
    # Paso 2: Subir certificado
    print("\n" + "="*50)
    if upload_certificate(tenant_id, api_key):
        # Paso 3: Verificar certificado
        verify_certificate_status(tenant_id, api_key)
        
        # Paso 4: Verificar tenant
        verify_tenant_status(tenant_id, api_key)
        
        print("\n🎉 ¡Setup completado exitosamente!")
        print("\n📋 Próximos pasos:")
        print("1. El tenant ya está creado y el certificado subido")
        print("2. Puedes usar el API Key para crear documentos")
        print("3. La información está guardada en tenant_info.json")
        print(f"\n🔑 Tu API Key: {api_key}")
        print(f"🆔 Tu Tenant ID: {tenant_id}")
        
        return True
    else:
        print("\n❌ No se pudo subir el certificado")
        print("\n🔧 Posibles soluciones:")
        print("1. Verificar que el PIN sea correcto")
        print("2. Verificar que el archivo P12 no esté corrupto")
        print("3. Revisar los logs del servidor")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
