# 🧪 Guía Completa de Pruebas de Endpoints

Esta guía contiene todos los scripts de prueba para validar el funcionamiento completo de la API de facturación electrónica de Costa Rica.

## 📋 Scripts de Prueba Disponibles

### 🔐 Autenticación
- **`test_auth_endpoints_complete.py`** - Prueba todos los endpoints de autenticación
  - Validación de API keys
  - Generación y validación de JWT tokens
  - Información de límites y rate limiting
  - Health checks del servicio de auth

### 🏢 Tenants
- **`test_tenant_endpoints_complete.py`** - Prueba todos los endpoints de tenants
  - Gestión de tenants (CRUD)
  - Certificados digitales
  - Estadísticas y uso
  - Planes y límites

### 🏷️ CABYS
- **`test_cabys_endpoints_complete.py`** - Prueba todos los endpoints de códigos CABYS
  - Búsqueda de códigos
  - Validación de códigos
  - Categorías y estadísticas
  - Códigos más usados

### 📄 Documentos
- **`test_documents_endpoints_complete.py`** - Prueba todos los endpoints de documentos
  - Creación de documentos electrónicos
  - Consulta y filtrado
  - Gestión de estados
  - Descarga de XML y PDF

### 💬 Mensajes Receptor
- **`test_messages_endpoints_complete.py`** - Prueba todos los endpoints de mensajes
  - Creación de mensajes de aceptación/rechazo
  - Envío al Ministerio de Hacienda
  - Consulta y filtrado
  - Estadísticas

### 🗺️ Datos de Referencia
- **`test_reference_data_endpoints_complete.py`** - Prueba todos los endpoints de datos de referencia
  - Ubicaciones geográficas (provincias, cantones, distritos)
  - Unidades de medida
  - Monedas soportadas
  - Números consecutivos

### 🛠️ Utilidades
- **`test_utils_endpoints_complete.py`** - Prueba todos los endpoints de utilidades
  - Health checks del sistema
  - Información de versión
  - Estadísticas del sistema
  - Endpoints de monitoreo

### 🚀 Script Maestro
- **`test_all_endpoints_complete.py`** - Ejecuta todas las pruebas de forma secuencial
  - Reporte completo de resultados
  - Estadísticas de éxito/fallo
  - Recomendaciones basadas en resultados

## 🔧 Configuración

### Credenciales
Todos los scripts están configurados con las siguientes credenciales por defecto:

```python
API_KEY = "cr_02640646_0PorxOcoJjTYG9pc8QPYfTRV-RRlEQqkcGHJNtppNr76uK8aXqApokkvrI4NzybZDEp0wg"
TENANT_ID = "02640646-3f6a-4ca9-b912-19e1cc72e64d"
BASE_URL = "http://localhost:8000"
```

### Personalización
Para usar diferentes credenciales, modifica las variables al inicio de cada script:

```python
# Cambiar estas variables según tu configuración
API_KEY = "tu_api_key_aqui"
TENANT_ID = "tu_tenant_id_aqui"
BASE_URL = "https://tu-servidor.com"  # Para servidor remoto
```

## 🚀 Ejecución

### Ejecutar Todas las Pruebas
```bash
python test_all_endpoints_complete.py
```

### Ejecutar Pruebas Individuales
```bash
# Autenticación
python test_auth_endpoints_complete.py

# Tenants
python test_tenant_endpoints_complete.py

# CABYS
python test_cabys_endpoints_complete.py

# Documentos
python test_documents_endpoints_complete.py

# Mensajes
python test_messages_endpoints_complete.py

# Datos de Referencia
python test_reference_data_endpoints_complete.py

# Utilidades
python test_utils_endpoints_complete.py
```

## 📊 Interpretación de Resultados

### Códigos de Color
- 🟢 **Verde**: Operación exitosa
- 🟡 **Amarillo**: Advertencia o problema menor
- 🔴 **Rojo**: Error o fallo
- 🔵 **Azul**: Información general
- 🟣 **Púrpura**: Detalles técnicos

### Códigos de Salida
- **0**: Todas las pruebas exitosas
- **1**: Algunas pruebas fallaron

### Porcentajes de Éxito
- **100%**: Perfecto - Todos los endpoints funcionan
- **80-99%**: Excelente - Problemas menores
- **60-79%**: Bueno - Algunos problemas que requieren atención
- **<60%**: Crítico - Problemas serios que requieren revisión

## 🔍 Diagnóstico de Problemas

### Problemas Comunes

#### 1. Error de Conexión
```
❌ Exception: Connection refused
```
**Solución**: Verificar que el servidor esté ejecutándose en `http://localhost:8000`

#### 2. Error de Autenticación
```
❌ FAILED - Status 401
Detail: Invalid API key
```
**Solución**: Verificar que el API_KEY sea válido y esté activo

#### 3. Error de Tenant
```
❌ FAILED - Status 403
Detail: Tenant not found or inactive
```
**Solución**: Verificar que el TENANT_ID exista y esté activo

#### 4. Timeout
```
❌ TIMEOUT - El script tardó más de 5 minutos
```
**Solución**: Verificar la conectividad y rendimiento del servidor

### Logs Detallados
Cada script proporciona información detallada sobre:
- URL del endpoint probado
- Método HTTP utilizado
- Headers de autenticación
- Código de respuesta HTTP
- Tiempo de respuesta
- Datos devueltos (resumen)

## 📈 Reportes

### Reporte Automático
El script maestro genera automáticamente un archivo de reporte:
```
test_report_YYYYMMDD_HHMMSS.txt
```

### Contenido del Reporte
- Resumen ejecutivo
- Detalles por módulo
- Estadísticas de tiempo
- Recomendaciones
- Información técnica

## 🛡️ Consideraciones de Seguridad

### Datos de Prueba
- Los scripts crean datos de prueba que se eliminan automáticamente
- No afectan datos de producción si se usan las credenciales correctas
- Los documentos creados son claramente marcados como "de prueba"

### API Keys
- Nunca hardcodees API keys en código de producción
- Usa variables de entorno para credenciales sensibles
- Rota las API keys regularmente

### Rate Limiting
- Los scripts incluyen pausas para evitar saturar el servidor
- Respetan los límites de rate limiting de la API
- Incluyen manejo de errores por límites excedidos

## 🔄 Mantenimiento

### Actualización de Scripts
Para mantener los scripts actualizados:

1. **Nuevos Endpoints**: Agregar pruebas a los scripts correspondientes
2. **Cambios en API**: Actualizar las estructuras de datos esperadas
3. **Nuevas Validaciones**: Agregar casos de prueba adicionales

### Versionado
Los scripts están diseñados para la versión actual de la API. Si la API cambia:
- Actualizar las URLs de endpoints
- Modificar las estructuras de datos
- Ajustar las validaciones esperadas

## 📞 Soporte

### Problemas con los Scripts
Si encuentras problemas con los scripts de prueba:
1. Verificar la configuración de credenciales
2. Confirmar que el servidor esté ejecutándose
3. Revisar los logs del servidor para errores específicos
4. Ejecutar pruebas individuales para aislar problemas

### Contribuciones
Para mejorar los scripts:
1. Agregar nuevos casos de prueba
2. Mejorar el manejo de errores
3. Optimizar el rendimiento
4. Agregar más validaciones

## 📚 Recursos Adicionales

### Documentación de la API
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

### Herramientas Recomendadas
- **Postman**: Para pruebas manuales de endpoints
- **curl**: Para pruebas rápidas desde línea de comandos
- **HTTPie**: Alternativa amigable a curl
- **Insomnia**: Cliente REST alternativo

---

## 🎯 Resumen de Uso Rápido

```bash
# 1. Ejecutar todas las pruebas
python test_all_endpoints_complete.py

# 2. Si hay problemas, ejecutar pruebas individuales
python test_auth_endpoints_complete.py
python test_tenant_endpoints_complete.py
# ... etc

# 3. Revisar el reporte generado
cat test_report_*.txt

# 4. Corregir problemas identificados

# 5. Re-ejecutar pruebas para verificar correcciones
python test_all_endpoints_complete.py
```

¡Los scripts están listos para usar con las credenciales proporcionadas! 🚀