#!/usr/bin/env python3
"""
Script de prueba para las APIs de Costa Rica Invoice API
"""
import requests
import json

# Configuración
BASE_URL = "http://localhost:8000/v1"
TOKEN = "dev-token"  # Cambia por el token que prefieras

# Headers con autenticación
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_endpoint(method, endpoint, description):
    """Prueba un endpoint y muestra el resultado"""
    print(f"\n🧪 {description}")
    print(f"   {method} {endpoint}")
    print("-" * 50)
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"✅ Éxito: {len(data)} resultados")
                if data:
                    print(f"   Primer resultado: {json.dumps(data[0], indent=2, ensure_ascii=False)[:200]}...")
            else:
                print(f"✅ Éxito: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

def main():
    print("🚀 Probando APIs de Costa Rica Invoice API")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Token: {TOKEN}")
    
    # Pruebas de CABYS
    test_endpoint("GET", "/cabys/statistics", "Estadísticas de CABYS")
    test_endpoint("GET", "/cabys/search?q=computadora&limit=3", "Búsqueda de códigos CABYS")
    test_endpoint("GET", "/cabys/most-used?limit=5", "Códigos CABYS más usados")
    test_endpoint("GET", "/cabys/categories?nivel=1", "Categorías CABYS nivel 1")
    
    # Pruebas de Reference Data
    test_endpoint("GET", "/reference/ubicaciones/provincias", "Provincias de Costa Rica")
    test_endpoint("GET", "/reference/unidades-medida?only_common=true&limit=5", "Unidades de medida comunes")
    test_endpoint("GET", "/reference/monedas", "Monedas soportadas")
    
    # Pruebas de validación
    test_endpoint("GET", "/reference/validate-identification/01/123456789", "Validar cédula física")
    test_endpoint("GET", "/reference/ubicaciones/validate/1/1/1", "Validar ubicación San José")

if __name__ == "__main__":
    main()