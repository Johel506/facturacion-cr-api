"""
Authentication middleware for API key validation and tenant identification
"""
import time
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import get_db
from app.core.security import verify_tenant_api_key
from app.models.tenant import Tenant


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication with tenant identification
    
    Requirements: 4.1, 4.2, 1.3
    """
    
    # Paths that don't require authentication
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico"
    }
    
    # Paths that require authentication (API endpoints)
    API_PATHS_PREFIX = "/api/"
    
    def __init__(self, app, exempt_paths: Optional[set] = None):
        super().__init__(app)
        if exempt_paths:
            self.EXEMPT_PATHS.update(exempt_paths)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate API key if required
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next handler or error response
        """
        start_time = time.time()
        
        # Skip authentication for exempt paths
        if self._is_exempt_path(request.url.path):
            response = await call_next(request)
            return response
        
        # Skip authentication for non-API paths
        if not request.url.path.startswith(self.API_PATHS_PREFIX):
            response = await call_next(request)
            return response
        
        # Validate API key for API endpoints
        try:
            tenant = await self._authenticate_request(request)
            if not tenant:
                return self._create_auth_error_response(
                    "Invalid or missing API key",
                    status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if tenant is active
            if not tenant.activo:
                return self._create_auth_error_response(
                    "Account is deactivated",
                    status.HTTP_403_FORBIDDEN
                )
            
            # Add tenant to request state for use in endpoints
            request.state.tenant = tenant
            request.state.tenant_id = tenant.id
            
            # Process request
            response = await call_next(request)
            
            # Add authentication headers to response
            response.headers["X-Tenant-ID"] = str(tenant.id)
            response.headers["X-API-Version"] = "v1"
            
            # Add timing header
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except HTTPException as e:
            return self._create_auth_error_response(e.detail, e.status_code)
        except Exception as e:
            return self._create_auth_error_response(
                "Authentication error",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        return path in self.EXEMPT_PATHS or path.startswith("/static/")
    
    async def _authenticate_request(self, request: Request) -> Optional[Tenant]:
        """
        Authenticate request using API key
        
        Args:
            request: FastAPI request object
            
        Returns:
            Authenticated tenant or None if invalid
        """
        # Extract API key from headers
        api_key = self._extract_api_key(request)
        if not api_key:
            return None
        
        # Validate API key format
        if not self._is_valid_api_key_format(api_key):
            return None
        
        # Look up tenant by API key
        tenant = await self._get_tenant_by_api_key(api_key)
        if not tenant:
            return None
        
        # Verify API key against stored hash
        if not verify_tenant_api_key(api_key, tenant.api_key):
            return None
        
        return tenant
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers
        
        Supports multiple header formats:
        - X-API-Key: <key>
        - Authorization: Bearer <key>
        - Authorization: ApiKey <key>
        
        Args:
            request: FastAPI request object
            
        Returns:
            API key string or None if not found
        """
        # Check X-API-Key header (preferred)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key.strip()
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            auth_parts = auth_header.split()
            if len(auth_parts) == 2:
                auth_type, token = auth_parts
                if auth_type.lower() in ["bearer", "apikey"]:
                    return token.strip()
        
        return None
    
    def _is_valid_api_key_format(self, api_key: str) -> bool:
        """
        Validate API key format
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not api_key or len(api_key) < 32:
            return False
        
        # Check for valid characters (URL-safe base64)
        import string
        allowed_chars = string.ascii_letters + string.digits + '-_'
        return all(c in allowed_chars for c in api_key)
    
    async def _get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """
        Get tenant by API key from database
        
        Args:
            api_key: API key to look up
            
        Returns:
            Tenant object or None if not found
        """
        try:
            # Get database session
            db: Session = next(get_db())
            
            # Query tenant by API key hash
            # Note: We need to check against all tenants since we hash the key
            tenants = db.query(Tenant).filter(Tenant.activo == True).all()
            
            for tenant in tenants:
                if verify_tenant_api_key(api_key, tenant.api_key):
                    return tenant
            
            return None
            
        except Exception:
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    def _create_auth_error_response(self, message: str, status_code: int) -> JSONResponse:
        """
        Create standardized authentication error response
        
        Args:
            message: Error message
            status_code: HTTP status code
            
        Returns:
            JSON error response
        """
        error_response = {
            "error": {
                "code": "AUTHENTICATION_ERROR",
                "message": message,
                "status_code": status_code,
                "timestamp": time.time(),
                "type": "authentication"
            }
        }
        
        # Add specific error codes for different scenarios
        if status_code == status.HTTP_401_UNAUTHORIZED:
            error_response["error"]["code"] = "INVALID_API_KEY"
            error_response["error"]["details"] = {
                "required_header": "X-API-Key",
                "alternative_headers": ["Authorization: Bearer <key>", "Authorization: ApiKey <key>"],
                "key_requirements": "Minimum 32 characters, URL-safe base64 format"
            }
        elif status_code == status.HTTP_403_FORBIDDEN:
            error_response["error"]["code"] = "ACCESS_FORBIDDEN"
        
        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={
                "WWW-Authenticate": "ApiKey",
                "X-Error-Code": error_response["error"]["code"]
            }
        )


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add tenant context to requests
    
    This middleware should run after authentication middleware
    to ensure tenant information is available throughout the request lifecycle.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Add tenant context to request
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with tenant context
        """
        # Check if tenant was set by auth middleware
        tenant = getattr(request.state, 'tenant', None)
        
        if tenant:
            # Add additional tenant context
            request.state.tenant_plan = tenant.plan
            request.state.tenant_limits = tenant.get_plan_limits()
            request.state.can_create_documents = tenant.can_create_document()
            
            # Check if monthly counter needs reset
            if tenant.should_reset_monthly_counter():
                try:
                    db: Session = next(get_db())
                    tenant.reset_monthly_counter()
                    db.commit()
                except Exception:
                    pass  # Log error but don't fail request
                finally:
                    if 'db' in locals():
                        db.close()
        
        response = await call_next(request)
        return response


# Dependency functions for use in FastAPI endpoints
def get_current_tenant(request: Request) -> Tenant:
    """
    Get current authenticated tenant from request
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current tenant object
        
    Raises:
        HTTPException: If no tenant in request (should not happen with middleware)
    """
    tenant = getattr(request.state, 'tenant', None)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authenticated tenant found"
        )
    return tenant


def get_tenant_id(request: Request) -> str:
    """
    Get current tenant ID from request
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tenant ID string
        
    Raises:
        HTTPException: If no tenant in request
    """
    tenant_id = getattr(request.state, 'tenant_id', None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authenticated tenant found"
        )
    return str(tenant_id)


def require_active_tenant(request: Request) -> Tenant:
    """
    Get current tenant and ensure it's active and can create documents
    
    Args:
        request: FastAPI request object
        
    Returns:
        Active tenant object
        
    Raises:
        HTTPException: If tenant is inactive or cannot create documents
    """
    tenant = get_current_tenant(request)
    
    if not tenant.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    if not tenant.verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not verified"
        )
    
    return tenant


def require_document_creation_capability(request: Request) -> Tenant:
    """
    Get current tenant and ensure it can create documents
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tenant that can create documents
        
    Raises:
        HTTPException: If tenant cannot create documents
    """
    tenant = require_active_tenant(request)
    
    if not tenant.can_create_document():
        reasons = []
        
        if tenant.monthly_limit_reached:
            reasons.append(f"Monthly limit of {tenant.limite_facturas_mes} documents reached")
        
        if not tenant.has_certificate:
            reasons.append("No certificate uploaded")
        
        if tenant.certificate_expired:
            reasons.append("Certificate has expired")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Cannot create documents",
                "reasons": reasons,
                "current_usage": tenant.facturas_usadas_mes,
                "monthly_limit": tenant.limite_facturas_mes,
                "has_certificate": tenant.has_certificate,
                "certificate_expired": tenant.certificate_expired
            }
        )
    
    return tenant