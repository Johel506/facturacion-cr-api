# Quick Testing Guide - Phase 3 Document Creation

## 🚀 **How to Test Document Creation**

### **Prerequisites**
1. Database running (Supabase connected via .env)
2. Valid tenant exists in database
3. Python virtual environment activated

### **1. Quick Test - Document Creation**
```bash
# Test basic document creation functionality
python3 test_files/test_simple_creation.py
```

**Expected Output**:
```
✅ SUCCESS!
Document ID: [UUID]
Document Key: [50-character key]
```

### **2. Verify Database Enums**
```bash
# Check current enum values in database
python3 setup_scripts/check_current_enums.py
```

**Expected**: All enums should show numeric values ('01', '02', etc.)

### **3. Legacy Compatibility Test**
```bash
# Test enum conversion compatibility
python3 test_files/test_with_old_enums.py
```

### **4. API Server Test** (Optional)
```bash
# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Test API endpoint
curl -X POST "http://localhost:8001/api/v1/documentos/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-test-h3k9m2v8x1p4q7r5" \
  -d '{
    "document": {
      "tipo_documento": "01",
      "receptor_nombre": "Test Client",
      "receptor_tipo_identificacion": "01",
      "receptor_numero_identificacion": "123456789",
      "receptor_provincia": 1,
      "receptor_canton": 1,
      "receptor_distrito": 1,
      "receptor_otras_senas": "Test Address",
      "condicion_venta": "01",
      "medio_pago": "01",
      "codigo_moneda": "CRC",
      "tipo_cambio": 1.0
    },
    "line_items": [
      {
        "codigo_cabys": "8111200100000",
        "descripcion": "Test Service",
        "cantidad": 1.0,
        "unidad_medida": "Sp",
        "precio_unitario": 50000.0
      }
    ]
  }'
```

---

## 🔧 **Troubleshooting**

### **Issue: ModuleNotFoundError**
**Solution**: Ensure you're in the virtual environment
```bash
source venv/bin/activate  # or appropriate activation command
```

### **Issue: Database Connection Error**
**Solution**: Check .env file and Supabase connection
```bash
# Verify DATABASE_URL in .env is correct
cat .env | grep DATABASE_URL
```

### **Issue: Enum Validation Error**
**Solution**: Ensure migration 9d13c8cc543d is applied
```bash
alembic current  # Should show: 9d13c8cc543d (head)
alembic upgrade head  # If not at head
```

### **Issue: Tenant Not Found**
**Solution**: Verify tenant_info.json exists and has valid UUID
```bash
cat tenant_info.json
```

---

## 📋 **Success Criteria**

### **✅ Document Creation Working When:**
- test_files/test_simple_creation.py completes without errors
- Document ID and 50-character key are generated
- Database INSERT operations succeed
- All enum values validate correctly (tipo_documento='01', etc.)

### **✅ Migration Status Correct When:**
- `alembic current` shows `9d13c8cc543d (head)`
- setup_scripts/check_current_enums.py shows numeric enum values
- No enum validation errors during document creation

### **✅ Database Integration Working When:**
- Supabase connection established successfully
- Document and detail records created in database
- Tenant counters updated properly

---

## 🎯 **Phase 3 Completion Checklist**

- [x] **Core Functionality**: Document creation service implemented
- [x] **Enum Alignment**: All enums use numeric codes per Ministry standards  
- [x] **Database Migrations**: Applied successfully with data preservation
- [x] **SQLAlchemy Configuration**: Fixed enum value handling
- [x] **Testing Infrastructure**: Comprehensive test suite created
- [x] **Documentation**: Complete implementation guide available
- [x] **Git Commit**: All changes properly committed and documented

**Status**: ✅ **PHASE 3 COMPLETE AND OPERATIONAL**
