"""
Rate limiting middleware with Redis-based sliding window algorithm
"""
import time
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.rate_limiting import rate_limiter, TenantPlan
from app.models.tenant import Tenant


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with comprehensive limits per tenant plan
    
    Requirements: 4.3, 1.4, 1.5
    """
    
    # Endpoints that require document creation limits
    DOCUMENT_CREATION_ENDPOINTS = {
        "/api/v1/documents",
        "/api/v1/documents/",
    }
    
    # Endpoints exempt from rate limiting
    EXEMPT_ENDPOINTS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico"
    }
    
    def __init__(self, app, enable_rate_limiting: bool = True):
        super().__init__(app)
        self.enable_rate_limiting = enable_rate_limiting
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and apply rate limiting
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with rate limit headers or error response
        """
        start_time = time.time()
        
        # Skip rate limiting if disabled or for exempt endpoints
        if not self.enable_rate_limiting or self._is_exempt_endpoint(request.url.path):
            response = await call_next(request)
            return response
        
        # Skip rate limiting for non-API endpoints
        if not request.url.path.startswith("/api/"):
            response = await call_next(request)
            return response
        
        # Get tenant from request state (set by auth middleware)
        tenant = getattr(request.state, 'tenant', None)
        if not tenant:
            # No tenant means no authentication - let auth middleware handle it
            response = await call_next(request)
            return response
        
        try:
            # Check rate limits
            allowed, limit_results, headers = await self._check_rate_limits(
                request, tenant
            )
            
            if not allowed:
                return self._create_rate_limit_error_response(
                    limit_results, headers
                )
            
            # Process request
            response = await call_next(request)
            
            # Increment counters after successful request
            await self._increment_counters(request, tenant)
            
            # Add rate limit headers to response
            for header_name, header_value in headers.items():
                response.headers[header_name] = header_value
            
            # Add timing header
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log error but don't fail the request
            print(f"Rate limiting error: {e}")
            response = await call_next(request)
            return response
    
    def _is_exempt_endpoint(self, path: str) -> bool:
        """Check if endpoint is exempt from rate limiting"""
        return path in self.EXEMPT_ENDPOINTS or path.startswith("/static/")
    
    def _is_document_creation_endpoint(self, path: str, method: str) -> bool:
        """Check if this is a document creation endpoint"""
        return (
            method.upper() == "POST" and
            any(path.startswith(endpoint) for endpoint in self.DOCUMENT_CREATION_ENDPOINTS)
        )
    
    async def _check_rate_limits(
        self, 
        request: Request, 
        tenant: Tenant
    ) -> tuple[bool, list, Dict[str, str]]:
        """
        Check all applicable rate limits for the request
        
        Args:
            request: FastAPI request object
            tenant: Authenticated tenant
            
        Returns:
            Tuple of (allowed, limit_results, headers)
        """
        tenant_plan = TenantPlan(tenant.plan)
        endpoint = self._normalize_endpoint(request.url.path)
        is_document_creation = self._is_document_creation_endpoint(
            request.url.path, request.method
        )
        
        return await rate_limiter.check_all_limits(
            str(tenant.id),
            tenant_plan,
            endpoint,
            is_document_creation
        )
    
    async def _increment_counters(self, request: Request, tenant: Tenant) -> None:
        """
        Increment rate limit counters after successful request
        
        Args:
            request: FastAPI request object
            tenant: Authenticated tenant
        """
        tenant_plan = TenantPlan(tenant.plan)
        endpoint = self._normalize_endpoint(request.url.path)
        is_document_creation = self._is_document_creation_endpoint(
            request.url.path, request.method
        )
        
        await rate_limiter.increment_counters(
            str(tenant.id),
            tenant_plan,
            endpoint,
            is_document_creation
        )
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for rate limiting
        
        Args:
            path: Request path
            
        Returns:
            Normalized endpoint path
        """
        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]
        
        # Remove trailing slash
        if path.endswith('/') and path != '/':
            path = path[:-1]
        
        # Replace UUID patterns with placeholder
        import re
        uuid_pattern = r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        path = re.sub(uuid_pattern, '/{id}', path, flags=re.IGNORECASE)
        
        return path
    
    def _create_rate_limit_error_response(
        self, 
        limit_results: list, 
        headers: Dict[str, str]
    ) -> JSONResponse:
        """
        Create rate limit exceeded error response
        
        Args:
            limit_results: List of rate limit check results
            headers: Rate limit headers
            
        Returns:
            JSON error response with rate limit information
        """
        # Find the first exceeded limit
        exceeded_limit = next(
            (result for result in limit_results if not result.allowed), 
            None
        )
        
        if not exceeded_limit:
            # Fallback error
            error_response = {
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded",
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                    "timestamp": time.time(),
                    "type": "rate_limit"
                }
            }
        else:
            # Determine limit type for user-friendly message
            limit_type = self._determine_limit_type(headers, exceeded_limit)
            
            error_response = {
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"{limit_type} rate limit exceeded",
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                    "timestamp": time.time(),
                    "type": "rate_limit",
                    "details": {
                        "limit_type": limit_type.lower(),
                        "current_usage": exceeded_limit.current_count,
                        "limit": exceeded_limit.limit,
                        "reset_time": exceeded_limit.reset_time,
                        "retry_after": exceeded_limit.retry_after
                    }
                }
            }
        
        # Add retry-after header if available
        if exceeded_limit and exceeded_limit.retry_after:
            headers["Retry-After"] = str(exceeded_limit.retry_after)
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_response,
            headers=headers
        )
    
    def _determine_limit_type(self, headers: Dict[str, str], exceeded_limit) -> str:
        """
        Determine which type of limit was exceeded for user-friendly messaging
        
        Args:
            headers: Rate limit headers
            exceeded_limit: The exceeded limit result
            
        Returns:
            Human-readable limit type
        """
        # Check headers to determine limit type
        if "X-RateLimit-Remaining-Month" in headers:
            remaining_month = headers["X-RateLimit-Remaining-Month"]
            if remaining_month == "0":
                return "Monthly document"
        
        if "X-RateLimit-Remaining-Hour" in headers:
            remaining_hour = int(headers.get("X-RateLimit-Remaining-Hour", "1"))
            if remaining_hour == 0:
                return "Hourly API"
        
        if "X-RateLimit-Remaining-Day" in headers:
            remaining_day = int(headers.get("X-RateLimit-Remaining-Day", "1"))
            if remaining_day == 0:
                return "Daily API"
        
        return "API"


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limit headers to all API responses
    
    This middleware runs after the main rate limit middleware to add
    current usage information to responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Add rate limit headers to response
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with additional rate limit headers
        """
        response = await call_next(request)
        
        # Only add headers to API endpoints
        if not request.url.path.startswith("/api/"):
            return response
        
        # Get tenant from request state
        tenant = getattr(request.state, 'tenant', None)
        if not tenant:
            return response
        
        try:
            # Get current usage statistics
            tenant_plan = TenantPlan(tenant.plan)
            usage_stats = await rate_limiter.get_usage_stats(
                str(tenant.id), tenant_plan
            )
            
            # Add usage statistics headers
            response.headers["X-Usage-Monthly-Documents"] = str(
                usage_stats.get("monthly", {}).get("documents_used", 0)
            )
            response.headers["X-Usage-Hourly-Requests"] = str(
                usage_stats.get("hourly", {}).get("requests_used", 0)
            )
            response.headers["X-Usage-Daily-Requests"] = str(
                usage_stats.get("daily", {}).get("requests_used", 0)
            )
            
        except Exception:
            # Don't fail the response if we can't add usage headers
            pass
        
        return response


# Dependency functions for use in FastAPI endpoints
async def check_rate_limit_dependency(request: Request) -> None:
    """
    FastAPI dependency to check rate limits
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    tenant = getattr(request.state, 'tenant', None)
    if not tenant:
        return  # No tenant, skip rate limiting
    
    tenant_plan = TenantPlan(tenant.plan)
    endpoint = request.url.path
    is_document_creation = (
        request.method.upper() == "POST" and
        endpoint.startswith("/api/v1/documents")
    )
    
    allowed, limit_results, headers = await rate_limiter.check_all_limits(
        str(tenant.id),
        tenant_plan,
        endpoint,
        is_document_creation
    )
    
    if not allowed:
        exceeded_limit = next(
            (result for result in limit_results if not result.allowed), 
            None
        )
        
        detail = {
            "message": "Rate limit exceeded",
            "current_usage": exceeded_limit.current_count if exceeded_limit else 0,
            "limit": exceeded_limit.limit if exceeded_limit else 0,
            "reset_time": exceeded_limit.reset_time if exceeded_limit else 0
        }
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers
        )


async def get_rate_limit_status(request: Request) -> Dict:
    """
    Get current rate limit status for tenant
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with current rate limit status
    """
    tenant = getattr(request.state, 'tenant', None)
    if not tenant:
        return {}
    
    tenant_plan = TenantPlan(tenant.plan)
    return await rate_limiter.get_usage_stats(str(tenant.id), tenant_plan)