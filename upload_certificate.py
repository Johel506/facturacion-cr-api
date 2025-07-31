#!/usr/bin/env python3
"""
Script para subir certificado P12 al tenant
"""

import requests
import base64
import os
import sys

# Configuración
API_BASE = "http://localhost:8000/api/v1"
TENANT_ID = "02640646-3f6a-4ca9-b912-19e1cc72e64d"
API_KEY = "cr_02640646_0PorxOcoJjTYG9pc8QPYfTRV-RRlEQqkcGHJNtppNr76uK8aXqApokkvrI4NzybZDEp0wg"


# Tu certificado (usando el original que funciona con OpenSSL legacy)
CERT_FILE = "011858030301.p12"
CERT_PASSWORD = "9285"

def upload_certificate():
    """Subir certificado P12 al tenant"""
    print(f"📤 Subiendo certificado {CERT_FILE}...")
    
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
        "X-API-Key": API_KEY,
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
            f"{API_BASE}/tenants/{TENANT_ID}/certificate",
            headers=headers,
            json=payload,
            timeout=30
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

def verify_certificate_status():
    """Verificar el estado del certificado después de subir"""
    print(f"\n🔍 Verificando estado del certificado...")
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{API_BASE}/tenants/{TENANT_ID}/certificate/status",
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
        else:
            print(f"⚠️ No se pudo obtener estado: HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except Exception as e:
        print(f"⚠️ Error verificando estado: {e}")

def main():
    print("🔐 Subida de certificado P12")
    print(f"Certificado: {CERT_FILE}")
    print(f"Tenant ID: {TENANT_ID}")
    print(f"API: {API_BASE}")
    print("-" * 50)
    
    # Subir certificado
    if upload_certificate():
        # Verificar estado
        verify_certificate_status()
        
        print("\n🎉 ¡Proceso completado!")
        print("\n📋 Próximos pasos:")
        print("1. Ejecutar el SQL para verificar el tenant:")
        print(f"   UPDATE tenants SET verificado = true, fecha_verificacion = NOW() WHERE id = '{TENANT_ID}';")
        print("2. Ejecutar test_phase3.py para probar la creación de facturas")
        
        return True
    else:
        print("\n❌ Proceso fallido")
        print("\n🔧 Posibles soluciones:")
        print("1. Verificar que el PIN sea correcto")
        print("2. Probar con contraseña vacía: ''")
        print("3. Verificar que el archivo no esté corrupto")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
