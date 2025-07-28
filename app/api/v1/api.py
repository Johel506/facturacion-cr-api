"""
API router aggregation for v1 endpoints
"""
from fastapi import APIRouter

# Import endpoint routers
from app.api.v1.endpoints import tenants, reference_data, documents
from app.api.v1 import cabys

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(tenants.router, prefix="/tenants")
api_router.include_router(documents.router, prefix="/documentos")

# Future endpoints (will be uncommented in later tasks)
# api_router.include_router(auth.router, prefix="/auth")
# api_router.include_router(invoices.router, prefix="/facturas")
api_router.include_router(cabys.router)
api_router.include_router(reference_data.router)
# api_router.include_router(utils.router, prefix="/utils")


@api_router.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Costa Rica Electronic Invoice API v1",
        "version": "1.0.0",
        "docs": "/docs"
    }