# Implementation Plan

- [x] 1. Set up project structure and core configuration
  - Create FastAPI project structure with proper directory organization
  - Configure environment variables and settings management
  - Set up Supabase connection and SQLAlchemy configuration
  - Configure Redis connection for caching and rate limiting
  - Execute: `git add . && git commit -m "feat: set up project structure and core configuration"`
  - _Requirements: 18.3, 18.5_

- [-] 2. Implement database models and migrations
  - [x] 2.1 Create core SQLAlchemy models
    - [x] 2.1.1 Implement complete Tenant model
      - Create Tenant model with basic fields, encrypted certificate storage, and plan limits
      - Add usage tracking and monthly limits functionality
      - Execute: `git add app/models/tenant.py && git commit -m "feat(models): implement Tenant model with certificate storage and plan limits"`
      - _Requirements: 1.1, 1.2, 1.4, 1.5_
    
    - [x] 2.1.2 Implement unified Document model
      - Create Document model supporting all 7 document types with header fields
      - Add emisor/receptor data, transaction conditions, and payment methods
      - Include currency support, totals calculation, and XML storage
      - Add Ministry status tracking and processing workflow
      - Execute: `git add app/models/document.py && git commit -m "feat(models): implement unified Document model for all 7 document types"`
      - _Requirements: 9.1, 11.1, 11.3, 11.4, 13.1, 13.4, 3.4, 3.5_

  - [x] 2.2 Create document detail and relationship models
    - [x] 2.2.1 Implement complete DocumentDetail model
      - Create DocumentDetail model with line item fields, product identification (CABYS, commercial codes)
      - Add quantity, pricing, discount fields, and special product fields (VIN, medicine, pharmacy)
      - Execute: `git add app/models/document_detail.py && git commit -m "feat(models): implement DocumentDetail model with product and pricing fields"`
      - _Requirements: 17.1, 11.2, 17.2, 14.3, 17.4, 17.5_
    
    - [x] 2.2.2 Create document relationship models
      - Create DocumentReference model for credit/debit note relationships
      - Add DocumentTax model supporting all Costa Rican tax types
      - Implement DocumentExemption model for tax exemption handling
      - Create DocumentOtherCharge model for stamps and additional fees
      - Execute: `git add app/models/document_reference.py app/models/document_tax.py app/models/document_exemption.py app/models/document_other_charge.py && git commit -m "feat(models): implement document relationship and tax models"`
      - _Requirements: 15.1, 15.2, 14.1, 14.2, 14.4_

  - [x] 2.3 Create reference data models
    - [x] 2.3.1 Create CabysCode model with search capabilities
      - Execute: `git add app/models/cabys_code.py && git commit -m "feat(models): create CabysCode model with full-text search support"`
      - _Requirements: 11.2, 11.3_
    
    - [x] 2.3.2 Create GeographicLocation model for Costa Rican addresses
      - Execute: `git add app/models/geographic_location.py && git commit -m "feat(models): create GeographicLocation model for CR provinces/cantons/districts"`
      - _Requirements: 12.1, 12.2, 12.3_
    
    - [x] 2.3.3 Create UnitsOfMeasure model for official units
      - Execute: `git add app/models/units_of_measure.py && git commit -m "feat(models): create UnitsOfMeasure model with RTC 443:2010 standard"`
      - _Requirements: 17.1_
    
    - [x] 2.3.4 Create ReceptorMessage model for document responses
      - Execute: `git add app/models/receptor_message.py && git commit -m "feat(models): create ReceptorMessage model for document acceptance/rejection"`
      - _Requirements: 16.1, 16.2_

  - [x] 2.4 Set up Alembic migrations
    - [x] 2.4.1 Configure Alembic and create initial migration
      - Configure Alembic with proper settings for database migrations
      - Create initial migration for tenant and core tables with all relationships
      - Execute: `git add alembic.ini alembic/env.py alembic/versions/001_initial_tables.py && git commit -m "migration: configure Alembic and create initial database schema"`
      - _Requirements: 8.5, 1.1, 9.1_
    
    - [x] 2.4.2 Add performance indexes and database constraints
      - Add comprehensive performance indexes for document keys and tenant isolation
      - Implement foreign key constraints with proper cascade rules
      - Add check constraints for document types and identification validation
      - Execute: `git add alembic/versions/002_add_indexes_constraints.py && git commit -m "migration: add performance indexes and database constraints"`
      - _Requirements: 8.5, 10.1, 1.5, 15.5, 11.1, 11.6_

  - [x] 2.5 Create and execute reference data seeding
    - [x] 2.5.1 Create comprehensive reference data seeding scripts
      - Create CABYS codes seeding script from official Excel file
      - Add Costa Rican geographic data seeding (provinces, cantons, districts)
      - Implement units of measure seeding script with RTC 443:2010 standard
      - Create development sample data for testing
      - Execute: `git add scripts/seed_cabys.py scripts/seed_locations.py scripts/seed_units.py scripts/seed_dev_data.py && git commit -m "feat(data): create comprehensive reference data seeding scripts"`
      - _Requirements: 11.2, 12.1, 17.1, 18.3_

- [x] 3. Implement Pydantic schemas and validation
  - [x] 3.1 Create core enums and base data models
    - Create all document type enums (DocumentType, IdentificationType, SaleCondition, PaymentMethod, TaxCode, IVATariffCode)
    - Implement base data models (IdentificationData, LocationData, PhoneData, EmisorData, ReceptorData)
    - Add comprehensive validation for Costa Rican business rules
    - Execute: `git add app/schemas/enums.py app/schemas/base.py && git commit -m "feat(schemas): implement core enums and base data models with CR validation"`
    - _Requirements: 9.1, 11.1, 11.3, 11.4, 12.1, 12.2, 12.3, 13.1, 14.1, 14.2_

  - [x] 3.2 Create document line item and tax models
    - Create comprehensive DocumentLineItem with product fields, commercial codes, and identification
    - Implement TaxData, ExemptionData, and DiscountData models supporting all Costa Rican tax types
    - Add PackageComponent model for product combos and surtidos
    - Execute: `git add app/schemas/document_items.py && git commit -m "feat(schemas): implement document line item models with tax and product support"`
    - _Requirements: 17.1, 17.2, 14.1, 14.2, 14.3, 17.6_

  - [x] 3.3 Create document and reference models
    - Create DocumentReference model for credit/debit note relationships
    - Implement OtherCharge model for stamps and additional fees
    - Create main DocumentCreate model supporting all 7 document types
    - Add DocumentResponse and DocumentList models for API responses
    - Execute: `git add app/schemas/documents.py && git commit -m "feat(schemas): implement document and reference models for all document types"`
    - _Requirements: 15.1, 15.2, 14.4, 9.1, 5.1, 5.2_

  - [x] 3.4 Create tenant and message models
    - Create tenant management models (TenantCreate, TenantUpdate, TenantResponse)
    - Implement certificate management models (CertificateUpload, CertificateStatus)
    - Add receptor message models (ReceptorMessageCreate, ReceptorMessageResponse)
    - Execute: `git add app/schemas/tenants.py app/schemas/messages.py && git commit -m "feat(schemas): implement tenant and receptor message models"`
    - _Requirements: 1.1, 1.2, 16.1, 16.2_

  - [x] 3.5 Implement comprehensive validators
    - Create identification number validators for all 6 types (física, jurídica, DIMEX, NITE, extranjero, no contribuyente)
    - Implement CABYS code format validation with database lookup
    - Add consecutive number and document key validators (20 and 50 character formats)
    - Create address, currency, and tax calculation validators
    - Execute: `git add app/utils/validators.py && git commit -m "feat(validators): implement comprehensive Costa Rican validation rules"`
    - _Requirements: 11.1, 11.2, 11.3, 10.1, 10.2, 10.3, 10.4, 12.1, 12.4, 13.1, 14.1, 14.5_

  - [x] 3.6 Add advanced business validation rules
    - Create document type specific validators and cross-field validation rules
    - Implement conditional field validation for "Others" codes requiring descriptions
    - Add business logic validation (credit sales require plazo_credito, exemptions require documents)
    - Execute: `git add app/utils/business_validators.py && git commit -m "feat(validators): implement advanced business validation rules"`
    - _Requirements: 9.1, 11.3, 11.6, 14.1_

- [x] 4. Implement authentication and security layer
  - [x] 4.1 Create API key authentication system
    - Implement cryptographically secure API key generation (minimum 32 characters)
    - Create middleware for API key authentication with tenant identification
    - Add API key validation with proper error responses (HTTP 401)
    - Implement API key rotation and management functionality
    - Execute: `git add app/core/security.py app/middleware/auth.py && git commit -m "feat(auth): implement secure API key authentication system"`
    - _Requirements: 4.1, 4.2, 1.3_

  - [x] 4.2 Implement comprehensive rate limiting
    - Create Redis-based rate limiting system with sliding window algorithm
    - Implement different limits per tenant plan (básico: 100/month, pro: 1000/month, empresa: unlimited)
    - Add rate limit headers to responses and per-endpoint/tenant limiting
    - Implement monthly document count limits with reset functionality
    - Execute: `git add app/core/rate_limiting.py app/middleware/rate_limit.py && git commit -m "feat(auth): implement Redis-based rate limiting with tenant plans"`
    - _Requirements: 4.3, 1.4, 1.5_

  - [x] 4.3 Add encryption and certificate security utilities
    - Implement AES-256 encryption for P12 certificates and passwords
    - Create secure certificate storage with encrypted fields in database
    - Add P12 certificate validation, parsing, and expiration checking
    - Implement certificate chain validation and expiration notification system (30, 15, 7 days)
    - Execute: `git add app/utils/crypto_utils.py app/utils/certificate_utils.py && git commit -m "feat(security): implement encryption and certificate management utilities"`
    - _Requirements: 4.5, 3.6, 1.2_

- [x] 5. Implement tenant management service
  - [x] 5.1 Create comprehensive tenant CRUD operations
    - Implement tenant creation with enhanced validation (cedula jurídica format, email verification)
    - Add tenant retrieval and update functionality with plan management
    - Create tenant activation/deactivation with cascade effects
    - Implement tenant usage tracking and monthly limits reset
    - Add tenant statistics and reporting functionality
    - Execute: `git add app/services/tenant_service.py app/api/v1/endpoints/tenants.py && git commit -m "feat(tenants): implement comprehensive tenant CRUD operations"`
    - _Requirements: 1.1, 1.5_

  - [x] 5.2 Implement advanced certificate management
    - Create P12 certificate upload with validation and secure storage
    - Add certificate parsing, validation, and expiration checking
    - Implement certificate caching in Redis with TTL management
    - Create automated certificate expiration notification system (30, 15, 7 days)
    - Add certificate chain validation and issuer verification
    - Execute: `git add app/services/certificate_service.py app/utils/certificate_utils.py && git commit -m "feat(certificates): implement advanced certificate management system"`
    - _Requirements: 1.2, 3.6, 8.3_

- [x] 6. Implement XML generation and validation
  - [x] 6.1 Create comprehensive UBL 2.1 XML generator for all document types
    - Implement XML structure generation for all 7 document types with proper namespaces
    - Create document header generation (Clave, ProveedorSistemas, CodigoActividad, NumeroConsecutivo, FechaEmision)
    - Implement Emisor and Receptor data generation with all address and contact fields
    - Create comprehensive line items (DetalleServicio) generation with all product, tax, discount, and exemption fields
    - Add complex tax calculations supporting all tax types (IVA, Selectivo, Específicos) and exemptions
    - Implement ResumenFactura generation with totals, other charges, and payment methods
    - Create document references generation for credit/debit notes and corrections
    - Add support for package/combo (DetalleSurtido) components
    - Execute: `git add app/utils/xml_generator.py app/services/xml_service.py && git commit -m "feat(xml): implement comprehensive UBL 2.1 XML generator for all document types"`
    - _Requirements: 9.1, 11.1, 14.1, 15.1, 17.1_

  - [x] 6.2 Implement XML digital signature with XAdES-EPES
    - Create P12 certificate loading, parsing, and validation using `cryptography` library
    - Implement XML digital signature using XAdES-EPES standard as required by Ministry (use `xmlsec` or `signxml`)
    - Add signature verification functionality for both tenant and Ministry signatures
    - Create signature timestamp and certificate chain validation
    - Implement signature canonicalization and digest calculation (SHA-256)
    - Execute: `git add app/utils/xml_signature.py app/services/signature_service.py && git commit -m "feat(xml): implement XML digital signature with XAdES-EPES using xmlsec"`
    - _Requirements: 3.1, 3.2_

  - [x] 6.3 Add comprehensive XSD schema validation
    - Load and cache all official Ministry XSD schemas (v4.4) for all document types
    - Implement XML validation against document-type-specific schemas
    - Create detailed validation error reporting with line numbers and field paths
    - Add schema version validation and compatibility checking
    - Implement validation caching for performance optimization
    - Execute: `git add app/utils/xsd_validator.py app/services/validation_service.py && git commit -m "feat(xml): add comprehensive XSD schema validation"`
    - _Requirements: 3.2, 9.1, 11.1_

- [x] 7. Implement Ministry of Finance integration
  - [x] 7.1 Create comprehensive Ministry API client
    - Implement HTTP client for Ministry API communication with proper authentication (OIDC/OAuth 2.0 using `authlib` or `python-jose`)
    - Add environment-specific URL configuration (development: api.comprobanteselectronicos.go.cr, production)
    - Create request/response handling for document submission with proper JSON structure
    - Implement rate limiting compliance with Ministry API limits (X-Ratelimit headers) using `aiohttp` with retry logic
    - Add timeout handling and connection pooling for reliability with `httpx` async client
    - Create callback URL handling for asynchronous Ministry responses
    - Execute: `git add app/services/ministry_service.py app/utils/ministry_client.py && git commit -m "feat(ministry): create comprehensive Ministry API client with OIDC using authlib"`
    - _Requirements: 3.3, 3.4_

  - [x] 7.2 Implement comprehensive document submission workflow
    - Create complete document processing pipeline for all 7 document types
    - Add intelligent retry logic for failed submissions with exponential backoff
    - Implement response parsing for all Ministry response states (recibido, procesando, aceptado, rechazado, error)
    - Store Ministry-signed XML responses with XAdES-XL signatures
    - Create document status tracking and update mechanisms
    - Add submission queue management for high-volume processing
    - Implement error categorization and handling (validation, network, Ministry errors)
    - Execute: `git add app/services/document_submission_service.py app/utils/ministry_response_parser.py && git commit -m "feat(ministry): implement comprehensive document submission workflow"`
    - _Requirements: 3.4, 3.5, 5.5_

  - [x] 7.3 Add Ministry response and status management
    - Implement document status polling and updates
    - Create Ministry response XML parsing and validation
    - Add automatic resubmission for transient failures
    - Implement document acceptance/rejection handling
    - Create Ministry error message parsing and user-friendly error reporting
    - Execute: `git add app/services/status_service.py app/utils/error_parser.py && git commit -m "feat(ministry): add Ministry response and status management"`
    - _Requirements: 3.4, 3.5_

- [-] 8. Implement CABYS code management and reference data services
  - [x] 8.1 Create comprehensive CABYS database and search
    - Implement CABYS code database seeding with official catalog (13-digit codes, descriptions, categories, tax rates)
    - Create full-text search functionality using PostgreSQL with Spanish language support (`gin` indexes with `to_tsvector`)
    - Add CABYS code validation for document line items with database lookup using `asyncpg` for performance
    - Implement CABYS code caching in Redis for performance using `aioredis` with TTL management
    - Create CABYS code update and synchronization mechanisms with `pandas` for Excel processing
    - Execute: `git add app/services/cabys_service.py app/utils/cabys_search.py && git commit -m "feat(cabys): create comprehensive CABYS database and search with PostgreSQL gin indexes"`
    - _Requirements: 11.2, 11.3, 17.1_

  - [x] 8.2 Add comprehensive CABYS and reference data API endpoints
    - Create GET /v1/cabys/search endpoint with pagination and filtering
    - Implement GET /v1/cabys/{codigo} for exact code lookup
    - Add category-based filtering and hierarchical browsing
    - Create GET /v1/ubicaciones endpoints for Costa Rican geographic data
    - Implement GET /v1/unidades-medida for official units of measure
    - Add GET /v1/monedas for supported currencies
    - Execute: `git add app/api/v1/endpoints/cabys.py app/api/v1/endpoints/reference_data.py && git commit -m "feat(api): add comprehensive CABYS and reference data API endpoints"`
    - _Requirements: 11.2, 12.1, 13.1, 17.1_

- [x] 9. Implement comprehensive document management service
  - [x] 9.1 Create document CRUD operations for all types
    - Implement document creation with complete validation for all 7 document types
    - Add document retrieval with tenant isolation and type-specific formatting
    - Create document listing with advanced pagination, filtering, and sorting
    - Implement document search functionality across all fields
    - Add document status tracking and history management
    - Execute: `git add app/services/document_service.py app/api/v1/endpoints/documents.py && git commit -m "feat(documents): create comprehensive document CRUD operations"`
    - _Requirements: 9.1, 5.1, 5.2, 5.3, 1.5_

  - [x] 9.2 Add consecutive number and document key management
    - Implement automatic consecutive number generation with proper format (20 digits)
    - Create branch and point-of-sale configuration per tenant
    - Add consecutive number validation and uniqueness per document type
    - Create 50-character document key following official format with all components
    - Add security code generation (8 random digits) for document uniqueness
    - Implement key uniqueness validation across all tenants and document types
    - Execute: `git add app/services/consecutive_service.py app/utils/key_generator.py && git commit -m "feat(documents): implement consecutive number and document key management"`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 9.3 Add document relationship management
    - Implement document reference creation and validation
    - Create document correction and cancellation workflows
    - Add credit/debit note relationship tracking
    - Implement document substitution and replacement functionality
    - Create document chain validation and integrity checking
    - Execute: `git add app/services/document_relationship_service.py app/utils/document_validator.py && git commit -m "feat(documents): add document relationship management"`
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [-] 10. Create comprehensive API endpoints
  - [x] 10.1 Implement authentication and security endpoints
    - Create POST /v1/auth/validate-key for API key validation
    - Add POST /v1/auth/token for optional JWT token generation
    - Implement GET /v1/auth/token/validate for token validation
    - Create GET /v1/auth/limits for current rate limit status
    - Execute: `git add app/api/v1/endpoints/auth.py && git commit -m "feat(api): implement authentication and security endpoints"`
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 10.2 Create comprehensive tenant management endpoints
    - Implement POST /v1/tenants for tenant creation with full validation
    - Add GET /v1/tenants/{id} for tenant retrieval with usage statistics
    - Create PUT /v1/tenants/{id} for tenant updates and plan changes
    - Implement POST /v1/tenants/{id}/certificado for P12 certificate upload
    - Add GET /v1/tenants/{id}/certificado/status for certificate status and expiration
    - Create DELETE /v1/tenants/{id}/certificado for certificate removal
    - Implement GET /v1/tenants/{id}/usage for usage statistics and limits
    - Execute: `git add app/api/v1/endpoints/tenants.py && git commit -m "feat(api): create comprehensive tenant management endpoints"`
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [ ] 10.3 Implement comprehensive document endpoints for all types
    - Create POST /v1/documentos for document creation supporting all 7 types
    - Add GET /v1/documentos/{id} for document retrieval with full details
    - Implement GET /v1/documentos for document listing with advanced filters
    - Create GET /v1/documentos/{id}/xml for original and signed XML download
    - Add GET /v1/documentos/{id}/pdf for PDF generation and download
    - Implement GET /v1/documentos/{id}/status for Ministry status check
    - Create POST /v1/documentos/{id}/reenviar for document resubmission
    - Add POST /v1/documentos/{id}/cancelar for document cancellation
    - Implement GET /v1/documentos/{id}/referencias for document relationships
    - Execute: `git add app/api/v1/endpoints/documents.py && git commit -m "feat(api): implement comprehensive document endpoints for all types"`
    - _Requirements: 9.1, 5.1, 5.2, 5.3, 5.4, 5.5, 15.1_

  - [ ] 10.4 Create receptor message and utility endpoints
    - Implement POST /v1/mensajes-receptor for acceptance/rejection messages
    - Add GET /v1/mensajes-receptor/{id} for message retrieval and listing
    - Implement POST /v1/mensajes-receptor/{id}/enviar for message submission
    - Create GET /v1/health for comprehensive health checks
    - Add GET /v1/stats for detailed usage statistics and analytics
    - Execute: `git add app/api/v1/endpoints/messages.py app/api/v1/endpoints/utils.py && git commit -m "feat(api): create receptor message and utility endpoints"`
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

  - [ ] 10.5 Create reference data endpoints
    - Implement GET /v1/cabys/search for CABYS code search with pagination
    - Add GET /v1/cabys/{codigo} for exact CABYS code lookup
    - Create GET /v1/ubicaciones endpoints for provinces, cantons, and districts
    - Create GET /v1/unidades-medida for units of measure catalog
    - Add GET /v1/monedas for supported currencies
    - Implement GET /v1/consecutivo/next/{tipo} for next consecutive number by document type
    - Execute: `git add app/api/v1/endpoints/cabys.py app/api/v1/endpoints/reference_data.py && git commit -m "feat(api): create comprehensive reference data endpoints"`
    - _Requirements: 11.2, 12.1, 12.2, 12.3, 12.4, 13.1, 17.1, 10.4_

- [ ] 11. Implement comprehensive error handling and logging
  - [ ] 11.1 Create comprehensive error handling system
    - Implement structured error responses with specific error codes for all scenarios
    - Add detailed validation error handling with field-level messages and suggestions
    - Create Ministry error response parsing and user-friendly error translation
    - Implement error categorization (validation, business logic, external service, system errors)
    - Add error recovery suggestions and corrective action guidance
    - Create error rate monitoring and alerting system
    - Execute: `git add app/core/error_handler.py app/utils/error_responses.py && git commit -m "feat(errors): create comprehensive error handling system"`
    - _Requirements: 7.1, 7.2, 3.5_

  - [ ] 11.2 Add comprehensive audit logging and monitoring system
    - Implement structured logging for all API requests with correlation IDs
    - Create detailed audit trails for authentication attempts and security events
    - Add comprehensive logging for Ministry interactions, responses, and status changes
    - Implement certificate modification and security event logging
    - Create document lifecycle logging (creation, modification, submission, acceptance/rejection)
    - Add performance monitoring and slow query logging
    - Implement log aggregation and search capabilities
    - Execute: `git add app/core/logging.py app/utils/audit_logger.py app/middleware/logging.py && git commit -m "feat(logging): add comprehensive audit logging and monitoring system"`
    - _Requirements: 7.2, 7.3, 7.4, 7.5_

- [ ] 12. Implement comprehensive caching and performance optimization
  - [ ] 12.1 Add comprehensive Redis caching layer
    - Implement certificate caching with TTL management for performance using `aioredis` with connection pooling
    - Create XSD schema caching in memory with version control using `cachetools` for LRU eviction
    - Add CABYS code caching for frequent searches with invalidation strategies using Redis hash structures
    - Implement geographic location caching for address validation with `redis-py` clustering support
    - Create units of measure caching for product line items with automatic refresh mechanisms
    - Add currency and exchange rate caching with refresh mechanisms using background tasks
    - Implement document template caching for XML generation with `jinja2` template caching
    - Execute: `git add app/core/cache.py app/utils/redis_cache.py && git commit -m "feat(cache): add comprehensive Redis caching layer with aioredis and cachetools"`
    - _Requirements: 8.1, 8.3, 8.4_

  - [ ] 12.2 Optimize database queries and performance
    - Add comprehensive database indexes for all query patterns (document keys, tenant isolation, date ranges, status filtering)
    - Implement advanced connection pooling with Supabase with proper sizing
    - Create query optimization for document listing with complex filters
    - Add database query monitoring and slow query identification
    - Implement read replicas for reporting and analytics queries
    - Create database partitioning strategies for large document volumes
    - Execute: `git add app/core/database.py app/utils/query_optimizer.py && git commit -m "feat(db): optimize database queries and performance"`
    - _Requirements: 8.5, 5.1_

  - [ ] 12.3 Add application-level performance optimizations
    - Implement async processing for Ministry submissions with queue management
    - Create background tasks for certificate expiration notifications
    - Add response compression and caching headers for API endpoints
    - Implement request/response size optimization and pagination
    - Create memory usage optimization for large XML processing
    - Execute: `git add app/core/background_tasks.py app/utils/performance.py && git commit -m "feat(perf): add application-level performance optimizations"`
    - _Requirements: 8.1, 8.2_

- [ ] 13. Create comprehensive test suite
  - [ ] 13.1 Implement complete unit and integration test suite
    - Create comprehensive unit tests for all Pydantic models, validators, and service layer business logic
    - Implement tests for XML generation, validation, and cryptographic utilities (P12, digital signatures)
    - Add database integration tests with real PostgreSQL for all models and relationships
    - Create Redis integration tests for caching, rate limiting, and session management
    - Implement API endpoint integration tests for all endpoints with authentication
    - Add Ministry API integration tests using development environment and certificate management tests
    - Execute: `git add tests/unit/ tests/integration/ && git commit -m "feat(tests): implement comprehensive unit and integration test suite"`
    - _Requirements: 18.4_

  - [ ] 13.2 Implement end-to-end and performance testing
    - Create complete document flow tests from creation to Ministry submission for all 7 document types
    - Add multi-tenant isolation tests ensuring complete data separation
    - Implement error scenario testing (validation failures, Ministry rejections, network errors)
    - Create performance and load testing for high-volume document processing using `pytest-benchmark`
    - Add security testing for authentication, authorization, and data encryption
    - Implement document relationship testing (credit/debit notes, references, corrections)
    - Execute: `git add tests/e2e/ tests/performance/ tests/security/ && git commit -m "feat(tests): implement end-to-end and performance testing with pytest-benchmark"`
    - _Requirements: 18.4_

- [ ] 14. Add comprehensive API documentation and development tools
  - [ ] 14.1 Configure comprehensive FastAPI documentation and development environment
    - Set up enhanced Swagger UI at /docs endpoint with custom styling and branding using `fastapi` OpenAPI customization
    - Add comprehensive request/response examples for all 7 document types with `pydantic` model examples
    - Create detailed endpoint descriptions with business context and use cases
    - Implement complete error code documentation with resolution guidance
    - Set up Docker Compose for local development with all services (PostgreSQL, Redis, Ministry mock using `wiremock`)
    - Create development utilities (data generators, test certificate creation, Ministry simulator)
    - Add development debugging tools and logging configuration with `structlog`
    - Execute: `git add app/core/docs.py app/api/v1/docs/ docker-compose.yml docker-compose.dev.yml scripts/dev/ && git commit -m "feat(docs): configure FastAPI documentation and development environment with Docker"`
    - _Requirements: 18.1, 18.2, 18.3, 18.6_

  - [ ] 14.2 Add developer experience enhancements and tooling
    - Create CLI tools for common development tasks using `typer` (tenant creation, certificate upload, document generation)
    - Implement code generation tools for new document types and validators
    - Add development dashboard for monitoring API usage and testing with `streamlit` or `dash`
    - Create automated code quality checks and pre-commit hooks using `black`, `isort`, `flake8`, `mypy`
    - Implement development metrics and performance monitoring with `prometheus` client
    - Add API versioning documentation and migration guides
    - Execute: `git add scripts/cli/ tools/ .pre-commit-config.yaml pyproject.toml && git commit -m "feat(dev): add developer experience enhancements with typer CLI and code quality tools"`
    - _Requirements: 18.1, 18.3_

- [ ] 15. Final integration and deployment preparation
  - [ ] 15.1 Complete comprehensive system integration testing
    - Test complete document workflow with real Ministry development API for all 7 document types
    - Validate multi-tenant data isolation with comprehensive security testing
    - Perform extensive security testing for authentication, authorization, and data encryption
    - Test certificate management lifecycle including expiration and renewal
    - Validate all tax calculations and exemption scenarios with real-world data
    - Test document relationship workflows (credit/debit notes, corrections, cancellations)
    - Perform load testing with realistic document volumes and concurrent users
    - Execute: `git add tests/integration_system/ tests/security/ && git commit -m "feat(testing): complete comprehensive system integration testing"`
    - _Requirements: 3.3, 1.5, 4.5, 9.1, 14.1, 15.1, 16.1_

  - [ ] 15.2 Prepare comprehensive production deployment
    - Create production configuration templates with security best practices
    - Set up comprehensive environment variable documentation with validation
    - Implement advanced health checks and monitoring endpoints with detailed metrics
    - Create automated deployment scripts with rollback capabilities
    - Add production logging and monitoring configuration (structured logs, metrics, alerts)
    - Implement database backup and disaster recovery procedures
    - Create production security hardening checklist and implementation
    - Add production performance monitoring and optimization guidelines
    - Execute: `git add deploy/ config/production/ scripts/deploy/ && git commit -m "feat(deploy): prepare comprehensive production deployment"`
    - _Requirements: 8.1, 18.5, 18.6_

  - [ ] 15.3 Create operational documentation and maintenance procedures
    - Create comprehensive operational runbooks for common scenarios
    - Implement monitoring and alerting setup for production environments
    - Add troubleshooting guides for common issues and error scenarios
    - Create maintenance procedures for certificate renewals and updates
    - Implement backup and recovery procedures with testing protocols
    - Add performance tuning guides and capacity planning documentation
    - Create incident response procedures and escalation protocols
    - Execute: `git add docs/operations/ docs/troubleshooting/ docs/maintenance/ && git commit -m "feat(docs): create operational documentation and maintenance procedures"`
    - _Requirements: 7.1, 7.2, 8.1_