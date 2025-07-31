"""
Comprehensive audit logging and monitoring system for Costa Rica Electronic Invoice API
Provides structured logging with correlation IDs, audit trails, and performance monitoring
"""
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from contextlib import contextmanager
from functools import wraps

from app.core.config import settings

# Configure structured logging format
class LogLevel(str, Enum):
    """Log levels for structured logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log categories for filtering and analysis"""
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SECURITY = "security"
    CERTIFICATE = "certificate"
    DOCUMENT_LIFECYCLE = "document_lifecycle"
    MINISTRY_INTERACTION = "ministry_interaction"
    DATABASE = "database"
    CACHE = "cache"
    PERFORMANCE = "performance"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    AUDIT = "audit"


class AuditLogger:
    """
    Comprehensive audit logger with structured logging and correlation tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger("costa_rica_invoice_api")
        self._setup_logger()
        self.correlation_id = None
        
    def _setup_logger(self):
        """Setup structured logging configuration"""
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        # Create file handler for audit logs
        file_handler = logging.FileHandler("audit.log")
        file_handler.setLevel(logging.INFO)
        
        # Set formatters based on configuration
        if settings.LOG_FORMAT.lower() == "json":
            formatter = JsonFormatter()
        else:
            formatter = StructuredFormatter()
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)
        
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracking"""
        self.correlation_id = correlation_id
    
    def generate_correlation_id(self) -> str:
        """Generate new correlation ID"""
        correlation_id = str(uuid.uuid4())
        self.set_correlation_id(correlation_id)
        return correlation_id
    
    def log_structured(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        **kwargs
    ):
        """
        Log structured message with metadata
        
        Args:
            level: Log level
            category: Log category
            message: Log message
            **kwargs: Additional metadata
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "category": category.value,
            "message": message,
            "correlation_id": self.correlation_id,
            **kwargs
        }
        
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        # Log at appropriate level
        log_level = getattr(logging, level.value)
        self.logger.log(log_level, json.dumps(log_data))
    
    def log_api_request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body_size: Optional[int] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        tenant_id: Optional[str] = None,
        api_key_id: Optional[str] = None
    ):
        """Log API request details"""
        self.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.API_REQUEST,
            message=f"{method} {path}",
            method=method,
            path=path,
            query_params=query_params,
            headers=self._sanitize_headers(headers) if headers else None,
            body_size=body_size,
            client_ip=client_ip,
            user_agent=user_agent,
            tenant_id=tenant_id,
            api_key_id=api_key_id
        )
    
    def log_api_response(
        self,
        method: str,
        path: str,
        status_code: int,
        response_size: Optional[int] = None,
        duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """Log API response details"""
        level = LogLevel.ERROR if status_code >= 500 else LogLevel.WARNING if status_code >= 400 else LogLevel.INFO
        
        self.log_structured(
            level=level,
            category=LogCategory.API_RESPONSE,
            message=f"{method} {path} -> {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            response_size=response_size,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            error_code=error_code
        )
    
    def log_authentication_attempt(
        self,
        auth_type: str,
        success: bool,
        tenant_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None
    ):
        """Log authentication attempts"""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Authentication {auth_type} {'successful' if success else 'failed'}"
        
        self.log_structured(
            level=level,
            category=LogCategory.AUTHENTICATION,
            message=message,
            auth_type=auth_type,
            success=success,
            tenant_id=tenant_id,
            api_key_id=api_key_id,
            client_ip=client_ip,
            user_agent=user_agent,
            failure_reason=failure_reason
        )
    
    def log_authorization_check(
        self,
        resource: str,
        action: str,
        success: bool,
        tenant_id: Optional[str] = None,
        required_permission: Optional[str] = None,
        failure_reason: Optional[str] = None
    ):
        """Log authorization checks"""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Authorization check for {action} on {resource} {'granted' if success else 'denied'}"
        
        self.log_structured(
            level=level,
            category=LogCategory.AUTHORIZATION,
            message=message,
            resource=resource,
            action=action,
            success=success,
            tenant_id=tenant_id,
            required_permission=required_permission,
            failure_reason=failure_reason
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        tenant_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log security events"""
        level = LogLevel.CRITICAL if severity == "critical" else LogLevel.ERROR if severity == "high" else LogLevel.WARNING
        
        self.log_structured(
            level=level,
            category=LogCategory.SECURITY,
            message=f"Security event: {event_type}",
            event_type=event_type,
            severity=severity,
            description=description,
            tenant_id=tenant_id,
            client_ip=client_ip,
            additional_data=additional_data
        )
    
    def log_certificate_event(
        self,
        event_type: str,
        tenant_id: str,
        certificate_subject: Optional[str] = None,
        certificate_serial: Optional[str] = None,
        expiry_date: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log certificate-related events"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Certificate {event_type} for tenant {tenant_id}"
        
        self.log_structured(
            level=level,
            category=LogCategory.CERTIFICATE,
            message=message,
            event_type=event_type,
            tenant_id=tenant_id,
            certificate_subject=certificate_subject,
            certificate_serial=certificate_serial,
            expiry_date=expiry_date,
            success=success,
            error_message=error_message
        )
    
    def log_document_lifecycle(
        self,
        event_type: str,
        document_id: str,
        document_type: str,
        tenant_id: str,
        document_key: Optional[str] = None,
        status: Optional[str] = None,
        ministry_response: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[float] = None
    ):
        """Log document lifecycle events"""
        level = LogLevel.ERROR if error_message else LogLevel.INFO
        message = f"Document {event_type}: {document_type} {document_id}"
        
        self.log_structured(
            level=level,
            category=LogCategory.DOCUMENT_LIFECYCLE,
            message=message,
            event_type=event_type,
            document_id=document_id,
            document_type=document_type,
            document_key=document_key,
            tenant_id=tenant_id,
            status=status,
            ministry_response=ministry_response,
            error_message=error_message,
            processing_time_ms=processing_time_ms
        )
    
    def log_ministry_interaction(
        self,
        interaction_type: str,
        endpoint: str,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        tenant_id: Optional[str] = None,
        document_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log Ministry API interactions"""
        level = LogLevel.ERROR if not success else LogLevel.INFO
        message = f"Ministry {interaction_type} to {endpoint}"
        
        self.log_structured(
            level=level,
            category=LogCategory.MINISTRY_INTERACTION,
            message=message,
            interaction_type=interaction_type,
            endpoint=endpoint,
            request_data=self._sanitize_sensitive_data(request_data) if request_data else None,
            response_data=self._sanitize_sensitive_data(response_data) if response_data else None,
            status_code=status_code,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            document_id=document_id,
            success=success,
            error_message=error_message
        )
    
    def log_database_operation(
        self,
        operation: str,
        table: str,
        duration_ms: Optional[float] = None,
        affected_rows: Optional[int] = None,
        tenant_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        query_hash: Optional[str] = None
    ):
        """Log database operations"""
        level = LogLevel.ERROR if not success else LogLevel.WARNING if duration_ms and duration_ms > 1000 else LogLevel.DEBUG
        message = f"Database {operation} on {table}"
        
        self.log_structured(
            level=level,
            category=LogCategory.DATABASE,
            message=message,
            operation=operation,
            table=table,
            duration_ms=duration_ms,
            affected_rows=affected_rows,
            tenant_id=tenant_id,
            success=success,
            error_message=error_message,
            query_hash=query_hash,
            slow_query=duration_ms and duration_ms > 1000
        )
    
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
        """Log cache operations"""
        level = LogLevel.ERROR if not success else LogLevel.DEBUG
        message = f"Cache {operation} for key {cache_key[:50]}..."
        
        self.log_structured(
            level=level,
            category=LogCategory.CACHE,
            message=message,
            operation=operation,
            cache_key_hash=hash(cache_key),  # Don't log full key for security
            hit=hit,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            success=success,
            error_message=error_message
        )
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: str,
        tenant_id: Optional[str] = None,
        additional_tags: Optional[Dict[str, str]] = None
    ):
        """Log performance metrics"""
        self.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.PERFORMANCE,
            message=f"Performance metric: {metric_name}",
            metric_name=metric_name,
            value=value,
            unit=unit,
            tenant_id=tenant_id,
            additional_tags=additional_tags
        )
    
    def log_business_event(
        self,
        event_type: str,
        description: str,
        tenant_id: Optional[str] = None,
        document_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log business logic events"""
        self.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.BUSINESS_LOGIC,
            message=f"Business event: {event_type}",
            event_type=event_type,
            description=description,
            tenant_id=tenant_id,
            document_id=document_id,
            additional_data=additional_data
        )
    
    def log_system_event(
        self,
        event_type: str,
        description: str,
        severity: str = "info",
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log system events"""
        level = LogLevel.CRITICAL if severity == "critical" else LogLevel.ERROR if severity == "error" else LogLevel.WARNING if severity == "warning" else LogLevel.INFO
        
        self.log_structured(
            level=level,
            category=LogCategory.SYSTEM,
            message=f"System event: {event_type}",
            event_type=event_type,
            description=description,
            severity=severity,
            additional_data=additional_data
        )
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers to remove sensitive information"""
        sensitive_headers = {"authorization", "x-api-key", "cookie", "x-auth-token"}
        sanitized = {}
        
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data from logs"""
        if not isinstance(data, dict):
            return data
        
        sensitive_keys = {
            "password", "token", "api_key", "secret", "certificate", 
            "private_key", "signature", "auth", "credential"
        }
        
        sanitized = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_sensitive_data(value)
            else:
                sanitized[key] = value
        
        return sanitized


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        try:
            # Try to parse message as JSON first
            message = record.getMessage()
            if message.startswith('{') and message.endswith('}'):
                # Already JSON formatted
                return message
            else:
                # Create structured format
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": message,
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                
                return json.dumps(log_data)
        except Exception:
            # Fallback to basic format
            return f"{datetime.utcnow().isoformat()} | {record.levelname} | {record.getMessage()}"


class StructuredFormatter(logging.Formatter):
    """Structured text formatter for human-readable logs"""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# Performance monitoring decorators
def log_performance(metric_name: str, unit: str = "ms"):
    """Decorator to log performance metrics"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                audit_logger.log_performance_metric(metric_name, duration, unit)
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                audit_logger.log_performance_metric(f"{metric_name}_error", duration, unit)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                audit_logger.log_performance_metric(metric_name, duration, unit)
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                audit_logger.log_performance_metric(f"{metric_name}_error", duration, unit)
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    return decorator


@contextmanager
def log_operation_context(
    operation_name: str,
    category: LogCategory = LogCategory.SYSTEM,
    tenant_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
):
    """Context manager for logging operations with timing"""
    start_time = time.time()
    correlation_id = audit_logger.generate_correlation_id()
    
    audit_logger.log_structured(
        level=LogLevel.INFO,
        category=category,
        message=f"Starting operation: {operation_name}",
        operation=operation_name,
        tenant_id=tenant_id,
        additional_data=additional_data
    )
    
    try:
        yield correlation_id
        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_structured(
            level=LogLevel.INFO,
            category=category,
            message=f"Completed operation: {operation_name}",
            operation=operation_name,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            success=True
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_structured(
            level=LogLevel.ERROR,
            category=category,
            message=f"Failed operation: {operation_name}",
            operation=operation_name,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            success=False,
            error_message=str(e)
        )
        raise


# Global audit logger instance
audit_logger = AuditLogger()