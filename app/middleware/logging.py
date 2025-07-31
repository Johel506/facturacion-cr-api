"""
Logging middleware for Costa Rica Electronic Invoice API
Provides automatic request/response logging with correlation IDs
"""
import time
import json
from typing import Callable, Optional
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.core.logging import audit_logger, LogLevel, LogCategory


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging
    """
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate correlation ID
        correlation_id = str(uuid4())
        audit_logger.set_correlation_id(correlation_id)
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Extract request information
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        tenant_id = getattr(request.state, 'tenant_id', None)
        api_key_id = getattr(request.state, 'api_key_id', None)
        
        # Read request body for logging (if not too large)
        body_size = None
        request_body = None
        
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_size = len(body) if body else 0
                
                # Only log body if it's reasonable size and not binary
                if body_size < 10000:  # 10KB limit
                    try:
                        request_body = json.loads(body) if body else None
                        # Sanitize sensitive data
                        if request_body:
                            request_body = self._sanitize_request_body(request_body)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_body = f"<binary data: {body_size} bytes>"
                
                # Recreate request with body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive
                
            except Exception as e:
                audit_logger.log_structured(
                    level=LogLevel.WARNING,
                    category=LogCategory.SYSTEM,
                    message=f"Failed to read request body: {e}",
                    correlation_id=correlation_id
                )
        
        # Log request
        audit_logger.log_api_request(
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params) if request.query_params else None,
            headers=dict(request.headers),
            body_size=body_size,
            client_ip=client_ip,
            user_agent=user_agent,
            tenant_id=tenant_id,
            api_key_id=api_key_id
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Get response size
            response_size = None
            if hasattr(response, 'body'):
                response_size = len(response.body)
            elif isinstance(response, StreamingResponse):
                response_size = None  # Cannot determine size for streaming responses
            
            # Extract error code if present
            error_code = None
            if response.status_code >= 400:
                try:
                    if hasattr(response, 'body'):
                        response_data = json.loads(response.body.decode())
                        error_code = response_data.get('error', {}).get('error_code')
                except:
                    pass
            
            # Log response
            audit_logger.log_api_response(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_size=response_size,
                duration_ms=duration_ms,
                tenant_id=tenant_id,
                error_code=error_code
            )
            
            # Log performance metrics for slow requests
            if duration_ms > 1000:  # Requests taking more than 1 second
                audit_logger.log_performance_metric(
                    metric_name="slow_request",
                    value=duration_ms,
                    unit="ms",
                    tenant_id=tenant_id,
                    additional_tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": str(response.status_code)
                    }
                )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000
            
            # Log failed request
            audit_logger.log_api_response(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                tenant_id=tenant_id,
                error_code="INTERNAL_SERVER_ERROR"
            )
            
            # Log the exception
            audit_logger.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.SYSTEM,
                message=f"Request processing failed: {str(e)}",
                method=request.method,
                path=request.url.path,
                exception=str(e),
                tenant_id=tenant_id,
                duration_ms=duration_ms
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _sanitize_request_body(self, body: dict) -> dict:
        """Sanitize sensitive data from request body"""
        if not isinstance(body, dict):
            return body
        
        sensitive_keys = {
            "password", "token", "api_key", "secret", "certificate", 
            "private_key", "signature", "auth", "credential", "p12_data",
            "password_certificado"
        }
        
        sanitized = {}
        for key, value in body.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_request_body(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_request_body(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


class DatabaseLoggingMiddleware:
    """
    Middleware for logging database operations
    """
    
    def __init__(self):
        self.slow_query_threshold_ms = 1000  # 1 second
    
    def log_query(
        self,
        operation: str,
        table: str,
        query_hash: str,
        duration_ms: float,
        affected_rows: Optional[int] = None,
        tenant_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log database query execution"""
        audit_logger.log_database_operation(
            operation=operation,
            table=table,
            duration_ms=duration_ms,
            affected_rows=affected_rows,
            tenant_id=tenant_id,
            success=success,
            error_message=error_message,
            query_hash=query_hash
        )
        
        # Log slow queries as performance issues
        if duration_ms > self.slow_query_threshold_ms:
            audit_logger.log_performance_metric(
                metric_name="slow_query",
                value=duration_ms,
                unit="ms",
                tenant_id=tenant_id,
                additional_tags={
                    "operation": operation,
                    "table": table,
                    "query_hash": query_hash
                }
            )


class CacheLoggingMiddleware:
    """
    Middleware for logging cache operations
    """
    
    def log_cache_operation(
        self,
        operation: str,
        cache_key: str,
        hit: Optional[bool] = None,
        duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log cache operation"""
        audit_logger.log_cache_operation(
            operation=operation,
            cache_key=cache_key,
            hit=hit,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            success=success,
            error_message=error_message
        )
        
        # Log cache performance metrics
        if duration_ms is not None:
            audit_logger.log_performance_metric(
                metric_name=f"cache_{operation}",
                value=duration_ms,
                unit="ms",
                tenant_id=tenant_id,
                additional_tags={
                    "operation": operation,
                    "hit": str(hit) if hit is not None else None
                }
            )


# Global middleware instances
database_logger = DatabaseLoggingMiddleware()
cache_logger = CacheLoggingMiddleware()


# Decorator for logging function execution
def log_function_execution(
    category: LogCategory = LogCategory.SYSTEM,
    log_args: bool = False,
    log_result: bool = False
):
    """Decorator to log function execution"""
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = f"{func.__module__}.{func.__name__}"
            
            log_data = {
                "function": function_name,
                "args_count": len(args),
                "kwargs_count": len(kwargs)
            }
            
            if log_args:
                log_data["args"] = str(args)[:500]  # Limit size
                log_data["kwargs"] = str(kwargs)[:500]
            
            audit_logger.log_structured(
                level=LogLevel.DEBUG,
                category=category,
                message=f"Function started: {function_name}",
                **log_data
            )
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                log_data.update({
                    "duration_ms": duration_ms,
                    "success": True
                })
                
                if log_result:
                    log_data["result"] = str(result)[:500]  # Limit size
                
                audit_logger.log_structured(
                    level=LogLevel.DEBUG,
                    category=category,
                    message=f"Function completed: {function_name}",
                    **log_data
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                audit_logger.log_structured(
                    level=LogLevel.ERROR,
                    category=category,
                    message=f"Function failed: {function_name}",
                    function=function_name,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = f"{func.__module__}.{func.__name__}"
            
            log_data = {
                "function": function_name,
                "args_count": len(args),
                "kwargs_count": len(kwargs)
            }
            
            if log_args:
                log_data["args"] = str(args)[:500]
                log_data["kwargs"] = str(kwargs)[:500]
            
            audit_logger.log_structured(
                level=LogLevel.DEBUG,
                category=category,
                message=f"Function started: {function_name}",
                **log_data
            )
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                log_data.update({
                    "duration_ms": duration_ms,
                    "success": True
                })
                
                if log_result:
                    log_data["result"] = str(result)[:500]
                
                audit_logger.log_structured(
                    level=LogLevel.DEBUG,
                    category=category,
                    message=f"Function completed: {function_name}",
                    **log_data
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                audit_logger.log_structured(
                    level=LogLevel.ERROR,
                    category=category,
                    message=f"Function failed: {function_name}",
                    function=function_name,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator