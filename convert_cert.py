#!/usr/bin/env python3
"""
Script para convertir certificado P12 legacy a formato moderno
Esto NO altera la validez del certificado, solo actualiza el algoritmo de cifrado del contenedor
"""

import subprocess
import os
import sys

# Configuración
ORIGINAL_CERT = "011858030301.p12"
CONVERTED_CERT = "011858030301_modern.p12"
PASSWORD = "9285"

def convert_p12_to_modern():
    """
    Convierte P12 con algoritmos legacy a formato moderno
    Esto mantiene la misma clave privada y certificado, solo cambia el cifrado del contenedor
    """
    print("🔄 Convirtiendo certificado P12 a formato moderno...")
    print(f"Original: {ORIGINAL_CERT}")
    print(f"Convertido: {CONVERTED_CERT}")
    print("-" * 50)
    
    # Verificar que el archivo original existe
    if not os.path.exists(ORIGINAL_CERT):
        print(f"❌ Error: Archivo {ORIGINAL_CERT} no encontrado")
        return False
    
    # Paso 1: Extraer certificado y clave privada
    print("📤 Paso 1: Extrayendo certificado y clave privada...")
    
    try:
        # Extraer certificado
        cmd_cert = [
            "openssl", "pkcs12", "-in", ORIGINAL_CERT, 
            "-out", "temp_cert.pem", "-clcerts", "-nokeys",
            "-passin", f"pass:{PASSWORD}", "-legacy"
        ]
        result = subprocess.run(cmd_cert, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error extrayendo certificado: {result.stderr}")
            return False
        print("✅ Certificado extraído")
        
        # Extraer clave privada
        cmd_key = [
            "openssl", "pkcs12", "-in", ORIGINAL_CERT,
            "-out", "temp_key.pem", "-nocerts", "-nodes",
            "-passin", f"pass:{PASSWORD}", "-legacy"
        ]
        result = subprocess.run(cmd_key, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error extrayendo clave privada: {result.stderr}")
            return False
        print("✅ Clave privada extraída")
        
        # Extraer cadena de certificados (CA)
        cmd_ca = [
            "openssl", "pkcs12", "-in", ORIGINAL_CERT,
            "-out", "temp_ca.pem", "-cacerts", "-nokeys",
            "-passin", f"pass:{PASSWORD}", "-legacy"
        ]
        result = subprocess.run(cmd_ca, capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️ Advertencia: No se pudo extraer cadena CA (normal en algunos certificados)")
        else:
            print("✅ Cadena CA extraída")
        
    except Exception as e:
        print(f"❌ Error en extracción: {e}")
        return False
    
    # Paso 2: Crear nuevo P12 con algoritmos modernos
    print("\n📥 Paso 2: Creando P12 con algoritmos modernos...")
    
    try:
        # Comando para crear P12 moderno
        cmd_create = [
            "openssl", "pkcs12", "-export",
            "-in", "temp_cert.pem",
            "-inkey", "temp_key.pem",
            "-out", CONVERTED_CERT,
            "-passout", f"pass:{PASSWORD}",
            "-name", "factura_electronica"
        ]
        
        # Agregar CA si existe
        if os.path.exists("temp_ca.pem") and os.path.getsize("temp_ca.pem") > 0:
            cmd_create.extend(["-certfile", "temp_ca.pem"])
        
        result = subprocess.run(cmd_create, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error creando P12 moderno: {result.stderr}")
            return False
        
        print("✅ P12 moderno creado exitosamente")
        
    except Exception as e:
        print(f"❌ Error creando P12: {e}")
        return False
    
    # Paso 3: Limpiar archivos temporales
    print("\n🧹 Paso 3: Limpiando archivos temporales...")
    temp_files = ["temp_cert.pem", "temp_key.pem", "temp_ca.pem"]
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"🗑️ Eliminado: {temp_file}")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar {temp_file}: {e}")
    
    # Paso 4: Verificar el nuevo certificado
    print("\n🔍 Paso 4: Verificando certificado convertido...")
    
    try:
        cmd_verify = [
            "openssl", "pkcs12", "-info", "-in", CONVERTED_CERT,
            "-noout", "-passin", f"pass:{PASSWORD}"
        ]
        result = subprocess.run(cmd_verify, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Certificado convertido es válido")
            print(f"📁 Archivo creado: {CONVERTED_CERT}")
            print(f"📏 Tamaño: {os.path.getsize(CONVERTED_CERT)} bytes")
            return True
        else:
            print(f"❌ Certificado convertido no es válido: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando certificado: {e}")
        return False

def main():
    print("🔐 Conversión de Certificado P12 Legacy")
    print("Este proceso convierte algoritmos obsoletos a modernos")
    print("SIN alterar la validez del certificado de Hacienda")
    print("=" * 60)
    
    if convert_p12_to_modern():
        print("\n🎉 ¡Conversión exitosa!")
        print(f"\n📋 Próximos pasos:")
        print(f"1. Usar el archivo convertido: {CONVERTED_CERT}")
        print(f"2. Actualizar upload_cert.py para usar el nuevo archivo")
        print(f"3. Ejecutar la subida del certificado")
        
        # Mostrar comando para actualizar upload_cert.py
        print(f"\n💡 Para actualizar el script de subida:")
        print(f"   Cambiar CERT_FILE = '{ORIGINAL_CERT}'")
        print(f"   Por:    CERT_FILE = '{CONVERTED_CERT}'")
        
        return True
    else:
        print("\n❌ Conversión fallida")
        print("\n🔧 Posibles causas:")
        print("1. OpenSSL no instalado o versión incorrecta")
        print("2. Contraseña incorrecta del certificado")
        print("3. Archivo P12 original corrupto")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
