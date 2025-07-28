# Testing Guide - Costa Rica Electronic Invoice API

## 📋 Current State Overview

### ✅ Implemented Components
- **Database Models**: Document, DocumentDetail, Tenant, DocumentReference, etc.
- **Services**: DocumentService, TenantService, ConsecutiveService
- **Pydantic Schemas**: Complete validations for all document types
- **Endpoints**: Documents, tenants, CABYS, reference data
- **Authentication**: API key system
- **Configuration**: Environment variables configured

### ⚠️ Identified Pending Corrections
1. ~~Documents router not included in main API~~ ✅ **FIXED**
2. ~~Verify database migrations status~~ ✅ **VERIFIED**
3. ~~Configure local Redis (optional for basic tests)~~ ⚠️ **NOT INSTALLED** (Optional for basic tests)
4. ~~Verify import dependencies~~ ✅ **FIXED** (Added missing `validate_cabys_code` function, commented out missing business validators temporarily)

---

## 🎯 Testing Objectives

1. **Validate base architecture** before continuing with XML and digital signature
2. **Detect integration errors** early
3. **Confirm validations** work correctly
4. **Verify error handling** before adding complexity
5. **Gain confidence** to continue with advanced features

---

## 📅 Testing Plan by Phases

### **PHASE 1: Environment Setup (15-20 min)**

#### 1.1 Verify and Fix Configuration
```bash
# Verify all dependencies are installed
pip install -r requirements.txt

# Verify environment variables
cat .env
```

**Environment Variables Checklist:**
- [x] `DATABASE_URL` - Configured with Supabase
- [x] `SECRET_KEY` - Configured
- [x] `ENCRYPTION_KEY` - Configured  
- [x] `MINISTRY_USERNAME` - Configured for development
- [x] `MINISTRY_PASSWORD` - Configured for development
- [ ] `REDIS_URL` - Check if Redis is running locally

#### 1.2 Verify Database Status
```bash
# Verify database connection
python -c "from app.core.database import engine; print('DB connection:', engine.url)"

# Check migrations
alembic current
alembic history
```

#### 1.3 Fix Main Router
- Include documents router in `/app/api/v1/api.py`
- Verify imports

#### 1.4 Verify Application Starts
```bash
# Start server
python -m uvicorn app.main:app --reload --port 8000

# Test in another terminal
curl http://localhost:8000/api/v1/
```

**Expected Result:**
```json
{
  "message": "Costa Rica Electronic Invoice API v1",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### **PHASE 2: Basic API Tests (30-45 min)**

#### 2.1 Verify Documentation and Basic Endpoints

**Test 1: Access documentation**
```bash
# Open in browser
http://localhost:8000/docs
```
**Verify:** Swagger UI loads correctly with all endpoints

**Test 2: Root endpoint**
```bash
curl http://localhost:8000/api/v1/
```

**Test 3: Reference endpoints (no authentication)**
```bash
# Provinces
curl http://localhost:8000/api/v1/ubicaciones/provincias

# CABYS (first 10)
curl "http://localhost:8000/api/v1/cabys/search?query=computadora&limit=10"

# Units of measure
curl http://localhost:8000/api/v1/unidades-medida
```

#### 2.2 Authentication Tests

**Test 4: Access without authentication (should fail)**
```bash
curl http://localhost:8000/api/v1/tenants/
# Expected: HTTP 401 Unauthorized
```

**Test 5: Create test tenant**
```bash
curl -X POST "http://localhost:8000/api/v1/tenants/" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_comercial": "Test Company S.A.",
    "cedula_juridica": "3101234567",
    "email": "test@company.com",
    "telefono": "22345678",
    "plan": "basico"
  }'
```

**Expected Result:**
```json
{
  "id": "uuid-here",
  "nombre_comercial": "Test Company S.A.",
  "cedula_juridica": "3101234567",
  "api_key": "generated-api-key-here",
  "plan": "basico",
  "activo": true
}
```

#### 2.3 Authenticated Tests

**Configure obtained API Key:**
```bash
export API_KEY="generated-api-key-from-previous-step"
```

**Test 6: List documents (empty initially)**
```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/documentos/
```

**Expected Result:**
```json
{
  "items": [],
  "pagination": {
    "current_page": 1,
    "per_page": 20,
    "total_items": 0,
    "total_pages": 0
  }
}
```

---

### **PHASE 3: Document Creation Tests (45-60 min)**

#### 3.1 Create Simple Electronic Invoice (Type 01)

**Test 7: Basic invoice**
```bash
curl -X POST "http://localhost:8000/api/v1/documentos/" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_documento": "01",
    "condicion_venta": "01",
    "plazo_credito": null,
    "medio_pago": "01",
    "emisor": {
      "tipo_identificacion": "02",
      "numero_identificacion": "3101234567",
      "nombre": "Issuer Company S.A.",
      "provincia": "1",
      "canton": "01",
      "distrito": "01",
      "otras_senas": "100m north of central park",
      "telefono": "22345678",
      "email": "issuer@company.com"
    },
    "receptor": {
      "tipo_identificacion": "01",
      "numero_identificacion": "123456789",
      "nombre": "Juan Pérez Gómez",
      "provincia": "1",
      "canton": "02",
      "distrito": "01",
      "otras_senas": "Blue house",
      "telefono": "87654321",
      "email": "juan@email.com"
    },
    "detalles": [
      {
        "numero_linea": 1,
        "codigo_cabys": "1010100010000",
        "descripcion": "Consulting service",
        "unidad_medida": "Sp",
        "cantidad": 1,
        "precio_unitario": 100000,
        "descuento": 0,
        "impuestos": [
          {
            "codigo": "01",
            "codigo_tarifa": "08",
            "tarifa": 13,
            "monto": 13000
          }
        ]
      }
    ]
  }'
```

**Verifications:**
- Document is created correctly
- `clave_numerica` is generated automatically
- `numero_consecutivo` is generated automatically
- Totals are calculated correctly
- Initial status is "draft"

#### 3.2 Verify Created Document

**Test 8: Get document by ID**
```bash
# Use the ID obtained in the previous response
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/documentos/{document_id}
```

**Test 9: List documents**
```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/documentos/
```

#### 3.3 Test Other Document Types

**Test 10: Electronic Ticket (Type 04)**
```bash
curl -X POST "http://localhost:8000/api/v1/documentos/" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_documento": "04",
    "condicion_venta": "01",
    "medio_pago": "01",
    "emisor": {
      "tipo_identificacion": "02",
      "numero_identificacion": "3101234567",
      "nombre": "Issuer Company S.A.",
      "provincia": "1",
      "canton": "01",
      "distrito": "01",
      "otras_senas": "100m north of central park",
      "telefono": "22345678",
      "email": "issuer@company.com"
    },
    "detalles": [
      {
        "numero_linea": 1,
        "codigo_cabys": "1010100010000",
        "descripcion": "American coffee",
        "unidad_medida": "Unid",
        "cantidad": 2,
        "precio_unitario": 1500,
        "descuento": 0,
        "impuestos": [
          {
            "codigo": "01",
            "codigo_tarifa": "08",
            "tarifa": 13,
            "monto": 390
          }
        ]
      }
    ]
  }'
```

**Note:** For electronic tickets, the receptor is optional

---

### **PHASE 4: Validation Tests (30-45 min)**

#### 4.1 Identification Validation Tests

**Test 11: Invalid physical ID**
```bash
curl -X POST "http://localhost:8000/api/v1/documentos/" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_documento": "01",
    "condicion_venta": "01",
    "medio_pago": "01",
    "emisor": {
      "tipo_identificacion": "01",
      "numero_identificacion": "123456789000",
      "nombre": "Name",
      ...other_fields...
    }
  }'
```

**Expected Result:** HTTP 422 with validation error

#### 4.2 CABYS Validation Tests

**Test 12: Invalid CABYS code**
```bash
# Use non-existent CABYS code
curl -X POST "http://localhost:8000/api/v1/documentos/" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    ...
    "detalles": [
      {
        "numero_linea": 1,
        "codigo_cabys": "9999999999999",
        ...
      }
    ]
  }'
```

#### 4.3 Business Rule Validation Tests

**Test 13: Credit sale without term**
```bash
curl -X POST "http://localhost:8000/api/v1/documentos/" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_documento": "01",
    "condicion_venta": "02",
    "plazo_credito": null,
    ...
  }'
```

**Expected Result:** Error indicating that plazo_credito is required for credit sales

---

### **PHASE 5: Document Relationship Tests (30-45 min)**

#### 5.1 Create Credit Note

**Test 14: Credit note referencing invoice**
```bash
curl -X POST "http://localhost:8000/api/v1/documentos/" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_documento": "03",
    "condicion_venta": "01",
    "medio_pago": "01",
    "documentos_referencia": [
      {
        "tipo_documento": "01",
        "numero": "previous_invoice_consecutive_number",
        "fecha_emision": "2024-01-15",
        "codigo": "01",
        "razon": "Frequent customer discount"
      }
    ],
    ...other_fields...
  }'
```

#### 5.2 Verify Filters and Searches

**Test 15: Filter by document type**
```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/documentos/?tipo_documento=01"
```

**Test 16: Filter by date**
```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/documentos/?fecha_desde=2024-01-01&fecha_hasta=2024-12-31"
```

**Test 17: Search by receptor**
```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/documentos/?receptor_nombre=Juan"
```

---

### **PHASE 6: Performance and Limits Tests (15-30 min)**

#### 6.1 Rate Limiting Tests

**Test 18: Verify basic tenant limits**
```bash
# Make multiple rapid requests to test rate limiting
for i in {1..10}; do
  curl -H "Authorization: Bearer $API_KEY" \
    http://localhost:8000/api/v1/documentos/ &
done
wait
```

#### 6.2 Pagination Tests

**Test 19: Pagination with multiple documents**
```bash
# Create multiple documents first, then test pagination
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/documentos/?page=1&per_page=5"
```

---

## 🐛 Found Errors Log

### Critical Errors
- [ ] **Error 1**: Error description
  - **Symptom**: 
  - **Solution**: 
  - **Status**: Pending/Resolved

### Minor Errors
- [ ] **Error 2**: Error description
  - **Symptom**: 
  - **Solution**: 
  - **Status**: Pending/Resolved

### Identified Improvements
- [ ] **Improvement 1**: Improvement description
  - **Justification**: 
  - **Priority**: High/Medium/Low

---

## ✅ Final Validation Checklist

### Basic Functionality
- [ ] Application starts without errors
- [ ] Swagger documentation accessible
- [ ] Reference endpoints work
- [ ] Authentication works correctly
- [ ] Tenants can be created

### Document Management
- [ ] Type 01 document creation (Invoice)
- [ ] Type 04 document creation (Ticket)
- [ ] Automatic consecutive generation
- [ ] Automatic numeric key generation
- [ ] Correct total calculations
- [ ] Business validations work

### Validations
- [ ] Physical/juridical ID validation
- [ ] CABYS code validation
- [ ] Business rule validation
- [ ] Proper validation error handling

### Relationships and Filters
- [ ] Credit/debit note creation
- [ ] Document references
- [ ] Document type filters
- [ ] Date filters
- [ ] Text field searches

---

## 🎯 Success Criteria

### ✅ Successful Tests (Can continue with Point 10)
- All basic endpoints work
- Documents of at least 2 different types can be created
- Main validations work
- Total calculations are correct
- Authentication works
- No critical architecture errors

### ⚠️ Needs Corrections (Fix before continuing)
- Critical errors in document creation
- Authentication or database problems
- Important validations not working
- Import or configuration errors

### ❌ Serious Problems (Architecture review needed)
- Application doesn't start
- Massive database errors
- Fundamental design problems

---

## 📝 Development Notes

### Redis Configuration
- **Optional for basic tests**: If Redis is not available, temporarily comment out rate limiting middleware
- **For complete tests**: Install Redis locally or use Docker

### Database
- **Use configured Supabase**: Credentials are already in `.env`
- **Migrations**: Verify they are applied correctly

### Authentication
- **API Keys**: Generated automatically when creating tenant
- **For development**: Create a test tenant and use its API key

### Next Steps After Testing
1. **If successful**: Continue with Point 10 (XML and Digital Signature)
2. **If minor errors**: Fix and test again
3. **If serious errors**: Review architecture and replan

---

**Ready to start? 🚀**

Let's go step by step executing each phase and documenting the results!
