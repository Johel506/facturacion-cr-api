# Costa Rica Electronic Invoice API

API for generating and sending electronic invoices compliant with Costa Rica's Ministry of Finance regulations.

## 📋 Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Development](#development)
- [Contributing](#contributing)

## ✨ Features

- **Electronic Invoice Generation** compliant with MH version 4.4
- **Digital Signature** of XML documents
- **Automatic XSD Validation**
- **Ministry of Finance API Integration**
- **Digital Certificate Management**
- **OAuth 2.0 Authentication System**
- **Rate limiting** and security middleware
- **PostgreSQL Database** with Alembic migrations
- **Redis Cache** for optimization
- **REST API** with automatic documentation (Swagger/OpenAPI)

## 🔧 System Requirements

- **Python 3.8+**
- **PostgreSQL 12+**
- **Redis 6+**
- **Git**

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Johel506/facturacion-cr-api.git
cd facturacion-cr-api
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL database

```sql
-- Connect to PostgreSQL and create the database
CREATE DATABASE facturacion_cr;
CREATE USER facturacion_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE facturacion_cr TO facturacion_user;
```

### 5. Configure Redis

Make sure Redis is running on your system:

```bash
# On Ubuntu/Debian
sudo systemctl start redis-server

# On macOS with Homebrew
brew services start redis

# On Windows (WSL or native installation)
redis-server
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://facturacion_user:your_password@localhost/facturacion_cr

# Redis
REDIS_URL=redis://localhost:6379/0

# Application configuration
PROJECT_NAME="Facturación CR API"
VERSION="1.0.0"
API_V1_STR="/api/v1"
SECRET_KEY="your-super-secret-key-here"

# CORS
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Ministry of Finance API
MH_API_BASE_URL="https://api.comprobanteselectronicos.go.cr"
MH_CLIENT_ID="your-client-id"
MH_CLIENT_SECRET="your-client-secret"

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Development configuration
DEBUG=true
TESTING=false
```

### Run migrations

```bash
alembic upgrade head
```

### Seed initial data (optional)

```bash
python -m scripts.seed_all
```

## 🎯 Usage

### Start development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Using Docker (alternative)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run only (if already built)
docker-compose up
```

### Access documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## 📁 Project Structure

```
facturacion-cr-api/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Core configuration
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── utils/           # Utilities
│   └── middleware/      # Custom middleware
├── alembic/             # Database migrations
├── scripts/             # Initialization scripts
├── tests/               # Automated tests
├── Estructuras XML y Anexos Version 4.4/  # MH Documentation
├── requirements.txt     # Python dependencies
├── alembic.ini         # Alembic configuration
├── pytest.ini          # Test configuration
├── docker-compose.yml   # Docker configuration
└── Dockerfile          # Docker image
```

## 🔗 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

### Documents
- `POST /api/v1/documents/` - Create document
- `GET /api/v1/documents/{id}` - Get document
- `PUT /api/v1/documents/{id}` - Update document
- `POST /api/v1/documents/{id}/sign` - Sign document
- `POST /api/v1/documents/{id}/submit` - Submit to MH

### Tenants
- `GET /api/v1/tenants/` - List tenants
- `POST /api/v1/tenants/` - Create tenant
- `GET /api/v1/tenants/{id}` - Get tenant

### Catalogs
- `GET /api/v1/catalogs/cabys` - CABYS codes
- `GET /api/v1/catalogs/locations` - Geographic locations
- `GET /api/v1/catalogs/units` - Units of measure

## 🧪 Testing

### Run all tests

```bash
pytest
```

### Run specific tests

```bash
# Unit tests
pytest -m unit

# Integration tests
pytest -m integration

# Tests with coverage
pytest --cov=app --cov-report=html
```

### XML validation tests

```bash
python test_xml_generator.py
python test_xml_signature.py
python test_xsd_validation.py
```

## 💻 Development

### Code quality tools

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Linting
flake8 app/ tests/

# Type checking
mypy app/
```

### Create new migration

```bash
alembic revision --autogenerate -m "Description of change"
```

### Apply migrations

```bash
alembic upgrade head
```

### Revert migration

```bash
alembic downgrade -1
```

## 📚 Additional Documentation

- [XML Structures MH v4.4](./Estructuras%20XML%20y%20Anexos%20Version%204.4/)
- [Ministry of Finance API](./Estructuras%20XML%20y%20Anexos%20Version%204.4/API%20Ministerio%20de%20Hacienda.md)
- [Endpoints](./Estructuras%20XML%20y%20Anexos%20Version%204.4/Endpoints.md)

## 🤝 Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🆘 Support

For help or to report issues:

1. Check the [documentation](#-additional-documentation)
2. Search [existing issues](https://github.com/Johel506/facturacion-cr-api/issues)
3. Create a [new issue](https://github.com/Johel506/facturacion-cr-api/issues/new) if needed

---

**Developed with ❤️ for Costa Rica's electronic invoicing ecosystem**