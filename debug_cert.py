#!/usr/bin/env python3
"""
Script para debuggear el proceso de base64 encode/decode del certificado
"""

import base64
import tempfile
import subprocess
import os

CERT_FILE = "011858030301.p12"
PASSWORD = "9285"

def test_base64_roundtrip():
    """Prueba que el certificado sobreviva el proceso base64 encode/decode"""
    print("🔍 Probando proceso base64 encode/decode...")
    
    # Leer archivo original
    with open(CERT_FILE, 'rb') as f:
        original_data = f.read()
    print(f"✅ Archivo original: {len(original_data)} bytes")
    
    # Convertir a base64
    cert_base64 = base64.b64encode(original_data).decode('utf-8')
    print(f"✅ Base64: {len(cert_base64)} caracteres")
    
    # Decodificar de base64
    decoded_data = base64.b64decode(cert_base64)
    print(f"✅ Decodificado: {len(decoded_data)} bytes")
    
    # Verificar que son iguales
    if original_data == decoded_data:
        print("✅ Datos idénticos después de base64 roundtrip")
    else:
        print("❌ Datos diferentes después de base64 roundtrip")
        return False
    
    # Probar con OpenSSL usando datos decodificados
    temp_dir = tempfile.mkdtemp()
    temp_p12 = os.path.join(temp_dir, "test.p12")
    temp_cert = os.path.join(temp_dir, "test.pem")
    
    try:
        # Escribir datos decodificados
        with open(temp_p12, 'wb') as f:
            f.write(decoded_data)
        
        # Probar extracción con OpenSSL
        cmd = [
            "openssl", "pkcs12", "-in", temp_p12,
            "-out", temp_cert, "-clcerts", "-nokeys",
            "-passin", f"pass:{PASSWORD}", "-legacy"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ OpenSSL puede leer el certificado decodificado")
            return True
        else:
            print(f"❌ OpenSSL no puede leer el certificado decodificado: {result.stderr}")
            return False
            
    finally:
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def test_server_validation_logic():
    """Simula exactamente lo que hace el servidor"""
    print("\n🔍 Simulando lógica de validación del servidor...")
    
    # Leer y encodear como hace el cliente
    with open(CERT_FILE, 'rb') as f:
        cert_bytes = f.read()
    
    cert_base64 = base64.b64encode(cert_bytes).decode('utf-8')
    print(f"📤 Cliente envía: {len(cert_base64)} caracteres base64")
    
    # Decodificar como hace el servidor
    try:
        certificate_data = base64.b64decode(cert_base64)
        print(f"📥 Servidor recibe: {len(certificate_data)} bytes")
        
        # Simular validación cryptography
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.backends import default_backend
        
        try:
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                certificate_data, PASSWORD.encode('utf-8'), backend=default_backend()
            )
            print("✅ cryptography puede validar el certificado")
            return True
        except Exception as e:
            print(f"❌ cryptography falla: {e}")
            
            # Probar el fallback subprocess como hace el servidor
            temp_dir = tempfile.mkdtemp()
            p12_path = os.path.join(temp_dir, "cert.p12")
            cert_path = os.path.join(temp_dir, "cert.pem")
            
            try:
                # Escribir datos como hace el servidor
                with open(p12_path, 'wb') as f:
                    f.write(certificate_data)
                
                # Extraer certificado
                cmd = [
                    "openssl", "pkcs12", "-in", p12_path,
                    "-out", cert_path, "-clcerts", "-nokeys",
                    "-passin", f"pass:{PASSWORD}", "-legacy"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ Fallback subprocess funciona")
                    return True
                else:
                    print(f"❌ Fallback subprocess falla: {result.stderr}")
                    return False
                    
            finally:
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    except Exception as e:
        print(f"❌ Error en decodificación base64: {e}")
        return False

def main():
    print("🔐 Debug de certificado P12")
    print(f"Archivo: {CERT_FILE}")
    print("=" * 50)
    
    # Test 1: Base64 roundtrip
    if not test_base64_roundtrip():
        print("\n❌ Falló el test de base64 roundtrip")
        return False
    
    # Test 2: Lógica completa del servidor
    if not test_server_validation_logic():
        print("\n❌ Falló la simulación de validación del servidor")
        return False
    
    print("\n🎉 ¡Todos los tests pasaron!")
    print("El problema debe estar en otro lugar...")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
