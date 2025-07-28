# 🧪 API Testing Guide

## 🔑 Development Authentication

### Available Tokens:
- **`dev-token`** - Development Company (enterprise plan)
- **`test-token`** - Test Company (pro plan)  
- **`demo-token`** - Demo Company (basic plan)

### Dynamic Tokens:
You can also use any token that starts with:
- **`dev-`** (example: `dev-my-test`)
- **`test-`** (example: `test-123`)
- **`demo-`** (example: `demo-local`)

## 🌐 Using Swagger UI

1. **Start the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Open Swagger UI**: http://localhost:8000/docs

3. **Authenticate**:
   - Click the "Authorize" button (🔒)
   - Enter one of the tokens (example: `dev-token`)
   - Click "Authorize" and then "Close"

4. **Test the endpoints!**

## 🐍 Using Python Script

```bash
python test_api.py
```

## 📡 Using cURL

```bash
# Example: Search CABYS codes
curl -X GET "http://localhost:8000/v1/cabys/search?q=computadora&limit=5" \
  -H "Authorization: Bearer dev-token"

# Example: Get provinces
curl -X GET "http://localhost:8000/v1/reference/ubicaciones/provincias" \
  -H "Authorization: Bearer dev-token"

# Example: Validate ID
curl -X GET "http://localhost:8000/v1/reference/validate-identification/01/123456789" \
  -H "Authorization: Bearer dev-token"
```

## 🧪 Main Endpoints to Test

### CABYS Codes:
- `GET /v1/cabys/search?q=computadora&limit=5` - Search codes
- `GET /v1/cabys/statistics` - Statistics
- `GET /v1/cabys/most-used?limit=10` - Most used
- `GET /v1/cabys/categories?nivel=1` - Categories

### Reference Data:
- `GET /v1/reference/ubicaciones/provincias` - Provinces
- `GET /v1/reference/unidades-medida?only_common=true` - Common units
- `GET /v1/reference/monedas` - Supported currencies

### Validation:
- `GET /v1/reference/validate-identification/01/123456789` - Validate ID
- `GET /v1/reference/ubicaciones/validate/1/1/1` - Validate location

## 🔧 Troubleshooting

### Error 401 Unauthorized:
- Verify that you're using a valid token
- Make sure to include "Bearer " before the token in cURL
- In Swagger UI, only enter the token without "Bearer "

### Error 422 Validation Error:
- Check the required parameters
- Verify the format of the data sent

### Connection Error:
- Make sure the server is running
- Verify that port 8000 is available