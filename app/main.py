"""
FastAPI application entry point for Costa Rica Electronic Invoice API
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db
from app.core.error_handler import error_handler
from app.api.v1.api import api_router
from app.middleware.auth import APIKeyAuthMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="API for generating and sending electronic invoices compliant with Costa Rica's Ministry of Finance regulations",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Configure OpenAPI security schemes for Swagger UI
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        from fastapi.openapi.utils import get_openapi
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API Key authentication. Use format: X-API-Key: your_api_key_here"
            },
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": "Bearer token authentication. Use format: Authorization: Bearer your_api_key_here"
            }
        }
        
        # Apply security globally to all endpoints except exempt ones
        exempt_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
        
        for path, path_item in openapi_schema["paths"].items():
            # Skip exempt paths
            if any(path.startswith(exempt) for exempt in exempt_paths):
                continue
                
            # Add security requirement to all operations in this path
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation["security"] = [
                        {"ApiKeyAuth": []},
                        {"BearerAuth": []}
                    ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi

    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add authentication middleware
    app.add_middleware(APIKeyAuthMiddleware)

    # Add global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for all unhandled exceptions"""
        return await error_handler.handle_exception(request, exc)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "costa-rica-invoice-api"}


@app.get("/health/errors")
async def error_health_check():
    """Error monitoring health check endpoint"""
    from app.core.error_monitoring import error_monitor
    
    try:
        health_metrics = error_monitor.get_health_metrics()
        error_rates = error_monitor.get_error_rates("1h")
        active_alerts = error_monitor.get_active_alerts()
        
        # Determine overall health status
        status = "healthy"
        if len(active_alerts) > 0:
            critical_alerts = [a for a in active_alerts if a["level"] == "critical"]
            if critical_alerts:
                status = "critical"
            else:
                status = "warning"
        elif error_rates["error_rate_per_minute"] > 10:  # More than 10 errors per minute
            status = "warning"
        
        return {
            "status": status,
            "service": "costa-rica-invoice-api",
            "error_monitoring": {
                "health_metrics": health_metrics,
                "error_rates": error_rates,
                "active_alerts": active_alerts,
                "alerts_count": len(active_alerts)
            }
        }
    except Exception as e:
        logger.error(f"Error in error health check: {e}")
        return {
            "status": "error",
            "service": "costa-rica-invoice-api",
            "error": str(e)
        }


@app.get("/admin/errors/statistics")
async def get_error_statistics():
    """Get comprehensive error statistics (admin endpoint)"""
    from app.core.error_monitoring import error_monitor
    
    try:
        return {
            "health_metrics": error_monitor.get_health_metrics(),
            "error_rates_1h": error_monitor.get_error_rates("1h"),
            "error_rates_24h": error_monitor.get_error_rates("24h"),
            "active_alerts": error_monitor.get_active_alerts(),
            "handler_statistics": error_handler.get_error_statistics()
        }
    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        return {"error": str(e)}