# 🧪 Guía para Probar las APIs

## 🔑 Autenticación para Desarrollo

### Tokens Disponibles:
- **`dev-token`** - Empresa de Desarrollo (plan enterprise)
- **`test-token`** - Empresa de Pruebas (plan pro)  
- **`demo-token`** - Empresa Demo (plan basic)

### Tokens Dinámicos:
También puedes usar cualquier token que empiece con:
- **`dev-`** (ejemplo: `dev-mi-prueba`)
- **`test-`** (ejemplo: `test-123`)
- **`demo-`** (ejemplo: `demo-local`)

## 🌐 Usando Swagger UI

1. **Inicia el servidor**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Abre Swagger UI**: http://localhost:8000/docs

3. **Autentícate**:
   - Haz clic en el botón "Authorize" (🔒)
   - Ingresa uno de los tokens (ejemplo: `dev-token`)
   - Haz clic en "Authorize" y luego "Close"

4. **¡Prueba los endpoints!**

## 🐍 Usando Python Script

```bash
python test_api.py
```

## 📡 Usando cURL

```bash
# Ejemplo: Buscar códigos CABYS
curl -X GET "http://localhost:8000/v1/cabys/search?q=computadora&limit=5" \
  -H "Authorization: Bearer dev-token"

# Ejemplo: Obtener provincias
curl -X GET "http://localhost:8000/v1/reference/ubicaciones/provincias" \
  -H "Authorization: Bearer dev-token"

# Ejemplo: Validar cédula
curl -X GET "http://localhost:8000/v1/reference/validate-identification/01/123456789" \
  -H "Authorization: Bearer dev-token"
```

## 🧪 Endpoints Principales para Probar

### CABYS Codes:
- `GET /v1/cabys/search?q=computadora&limit=5` - Buscar códigos
- `GET /v1/cabys/statistics` - Estadísticas
- `GET /v1/cabys/most-used?limit=10` - Más usados
- `GET /v1/cabys/categories?nivel=1` - Categorías

### Reference Data:
- `GET /v1/reference/ubicaciones/provincias` - Provincias
- `GET /v1/reference/unidades-medida?only_common=true` - Unidades comunes
- `GET /v1/reference/monedas` - Monedas soportadas

### Validación:
- `GET /v1/reference/validate-identification/01/123456789` - Validar cédula
- `GET /v1/reference/ubicaciones/validate/1/1/1` - Validar ubicación

## 🔧 Troubleshooting

### Error 401 Unauthorized:
- Verifica que estés usando un token válido
- Asegúrate de incluir "Bearer " antes del token en cURL
- En Swagger UI, solo ingresa el token sin "Bearer "

### Error 422 Validation Error:
- Revisa los parámetros requeridos
- Verifica el formato de los datos enviados

### Error de conexión:
- Asegúrate de que el servidor esté corriendo
- Verifica que el puerto 8000 esté disponible