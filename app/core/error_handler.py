"""
Comprehensive error handling system for Costa Rica Electronic Invoice API
Provides structured error responses, categorization, and recovery suggestions
"""
import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from redis.exceptions import RedisError

from app.utils.error_parser import ErrorParser, ErrorType, ErrorSeverity
from app.utils.error_responses import (
    DocumentNotFoundError,
    NotFoundError,
    ValidationError as CustomValidationError,
    PermissionError as CustomPermissionError,
    BusinessRuleError,
    MinistryError,
    CertificateError
)
from app.core.error_monitoring import error_monitor

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for monitoring and alerting"""
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    CACHE = "cache"
    SYSTEM = "system"
    NETWORK = "network"
    CERTIFICATE = "certificate"
    SIGNATURE = "signature"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


class ErrorHandler:
    """
    Comprehensive error handler with structured responses,
    categorization, and recovery suggestions
    """
    
    def __init__(self):
        self.error_parser = ErrorParser()
        self.error_counts = {}  # For error rate monitoring
        
        # Error code mappings
        self.error_codes = {
            # Validation errors (4000-4099)
            "VALIDATION_ERROR": 4000,
            "FIELD_VALIDATION_ERROR": 4001,
            "SCHEMA_VALIDATION_ERROR": 4002,
            "BUSINESS_RULE_VALIDATION": 4003,
            "CABYS_CODE_INVALID": 4004,
            "IDENTIFICATION_INVALID": 4005,
            "TAX_CALCULATION_ERROR": 4006,
            "DATE_FORMAT_ERROR": 4007,
            "CURRENCY_FORMAT_ERROR": 4008,
            "DOCUMENT_KEY_INVALID": 4009,
            "CONSECUTIVE_NUMBER_INVALID": 4010,
            
            # Authentication/Authorization errors (4100-4199)
            "AUTHENTICATION_FAILED": 4100,
            "INVALID_API_KEY": 4101,
            "EXPIRED_TOKEN": 4102,
            "INSUFFICIENT_PERMISSIONS": 4103,
            "TENANT_NOT_FOUND": 4104,
            "TENANT_INACTIVE": 4105,
            "RATE_LIMIT_EXCEEDED": 4106,
            "MONTHLY_LIMIT_EXCEEDED": 4107,
            
            # Resource errors (4200-4299)
            "RESOURCE_NOT_FOUND": 4200,
            "DOCUMENT_NOT_FOUND": 4201,
            "CABYS_CODE_NOT_FOUND": 4202,
            "CERTIFICATE_NOT_FOUND": 4203,
            "TENANT_NOT_FOUND": 4204,
            
            # Certificate errors (4300-4399)
            "CERTIFICATE_ERROR": 4300,
            "CERTIFICATE_EXPIRED": 4301,
            "CERTIFICATE_INVALID": 4302,
            "CERTIFICATE_UPLOAD_FAILED": 4303,
            "CERTIFICATE_PARSING_ERROR": 4304,
            "SIGNATURE_VERIFICATION_FAILED": 4305,
            
            # Ministry API errors (4400-4499)
            "MINISTRY_API_ERROR": 4400,
            "MINISTRY_VALIDATION_ERROR": 4401,
            "MINISTRY_REJECTION": 4402,
            "MINISTRY_TIMEOUT": 4403,
            "MINISTRY_AUTHENTICATION_ERROR": 4404,
            "MINISTRY_RATE_LIMIT": 4405,
            "MINISTRY_SERVICE_UNAVAILABLE": 4406,
            
            # Database errors (5000-5099)
            "DATABASE_ERROR": 5000,
            "DATABASE_CONNECTION_ERROR": 5001,
            "DATABASE_CONSTRAINT_ERROR": 5002,
            "DATABASE_TIMEOUT": 5003,
            "DATABASE_INTEGRITY_ERROR": 5004,
            
            # Cache errors (5100-5199)
            "CACHE_ERROR": 5100,
            "REDIS_CONNECTION_ERROR": 5101,
            "CACHE_TIMEOUT": 5102,
            
            # System errors (5200-5299)
            "INTERNAL_SERVER_ERROR": 5200,
            "SERVICE_UNAVAILABLE": 5201,
            "CONFIGURATION_ERROR": 5202,
            "FILE_SYSTEM_ERROR": 5203,
            "MEMORY_ERROR": 5204,
            "TIMEOUT_ERROR": 5205,
            
            # Network errors (5300-5399)
            "NETWORK_ERROR": 5300,
            "CONNECTION_TIMEOUT": 5301,
            "DNS_RESOLUTION_ERROR": 5302,
            "SSL_ERROR": 5303,
        }
        
        # HTTP status code mappings
        self.status_mappings = {
            ErrorCategory.VALIDATION: status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCategory.AUTHENTICATION: status.HTTP_401_UNAUTHORIZED,
            ErrorCategory.AUTHORIZATION: status.HTTP_403_FORBIDDEN,
            ErrorCategory.BUSINESS_LOGIC: status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCategory.EXTERNAL_SERVICE: status.HTTP_502_BAD_GATEWAY,
            ErrorCategory.DATABASE: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCategory.CACHE: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCategory.SYSTEM: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCategory.NETWORK: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCategory.CERTIFICATE: status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCategory.SIGNATURE: status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCategory.RATE_LIMIT: status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCategory.UNKNOWN: status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        
        logger.info("Error handler initialized")
    
    async def handle_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        Main exception handler that routes to specific handlers
        
        Args:
            request: FastAPI request object
            exc: Exception to handle
        
        Returns:
            JSONResponse with structured error information
        """
        error_id = str(uuid.uuid4())
        
        try:
            # Log the exception with context
            self._log_exception(exc, request, error_id)
            
            # Route to specific handlers
            if isinstance(exc, RequestValidationError):
                return await self._handle_validation_error(request, exc, error_id)
            elif isinstance(exc, ValidationError):
                return await self._handle_pydantic_validation_error(request, exc, error_id)
            elif isinstance(exc, HTTPException):
                return await self._handle_http_exception(request, exc, error_id)
            elif isinstance(exc, CustomValidationError):
                return await self._handle_custom_validation_error(request, exc, error_id)
            elif isinstance(exc, BusinessRuleError):
                return await self._handle_business_rule_error(request, exc, error_id)
            elif isinstance(exc, MinistryError):
                return await self._handle_ministry_error(request, exc, error_id)
            elif isinstance(exc, CertificateError):
                return await self._handle_certificate_error(request, exc, error_id)
            elif isinstance(exc, (DocumentNotFoundError, NotFoundError)):
                return await self._handle_not_found_error(request, exc, error_id)
            elif isinstance(exc, CustomPermissionError):
                return await self._handle_permission_error(request, exc, error_id)
            elif isinstance(exc, SQLAlchemyError):
                return await self._handle_database_error(request, exc, error_id)
            elif isinstance(exc, RedisError):
                return await self._handle_cache_error(request, exc, error_id)
            else:
                return await self._handle_generic_error(request, exc, error_id)
                
        except Exception as handler_exc:
            # Fallback error handling
            logger.error(f"Error in exception handler: {handler_exc}")
            return self._create_fallback_response(error_id)
    
    async def _handle_validation_error(
        self,
        request: Request,
        exc: RequestValidationError,
        error_id: str
    ) -> JSONResponse:
        """Handle FastAPI validation errors"""
        field_errors = {}
        suggestions = []
        
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            field_errors[field_path] = {
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            }
            
            # Add field-specific suggestions
            field_suggestions = self._get_field_suggestions(field_path, error["type"])
            suggestions.extend(field_suggestions)
        
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="FIELD_VALIDATION_ERROR",
            message="Request validation failed",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            field_errors=field_errors,
            suggestions=list(set(suggestions)),
            is_retryable=False
        )
        
        self._track_error("FIELD_VALIDATION_ERROR", ErrorCategory.VALIDATION, "Request validation failed", is_retryable=False)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    async def _handle_pydantic_validation_error(
        self,
        request: Request,
        exc: ValidationError,
        error_id: str
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
        field_errors = {}
        suggestions = []
        
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            field_errors[field_path] = {
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            }
            
            # Add field-specific suggestions
            field_suggestions = self._get_field_suggestions(field_path, error["type"])
            suggestions.extend(field_suggestions)
        
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="SCHEMA_VALIDATION_ERROR",
            message="Data validation failed",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            field_errors=field_errors,
            suggestions=list(set(suggestions)),
            is_retryable=False
        )
        
        self._track_error("SCHEMA_VALIDATION_ERROR", ErrorCategory.VALIDATION, "Data validation failed", is_retryable=False)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    async def _handle_http_exception(
        self,
        request: Request,
        exc: HTTPException,
        error_id: str
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        category = self._categorize_http_exception(exc.status_code)
        
        error_response = self._create_error_response(
            error_id=error_id,
            error_code=self._get_error_code_from_status(exc.status_code),
            message=exc.detail,
            category=category,
            severity=self._get_severity_from_status(exc.status_code),
            suggestions=self._get_suggestions_for_status(exc.status_code),
            is_retryable=self._is_retryable_status(exc.status_code)
        )
        
        self._track_error(error_response["error"]["error_code"], category, exc.detail, is_retryable=self._is_retryable_status(exc.status_code))
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=getattr(exc, "headers", None)
        )
    
    async def _handle_custom_validation_error(
        self,
        request: Request,
        exc: CustomValidationError,
        error_id: str
    ) -> JSONResponse:
        """Handle custom validation errors"""
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="VALIDATION_ERROR",
            message=str(exc),
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            suggestions=[
                "Review the provided data for correctness",
                "Check field formats and requirements",
                "Ensure all required fields are provided"
            ],
            is_retryable=False
        )
        
        self._track_error("VALIDATION_ERROR", ErrorCategory.VALIDATION, str(exc), is_retryable=False)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    async def _handle_business_rule_error(
        self,
        request: Request,
        exc: BusinessRuleError,
        error_id: str
    ) -> JSONResponse:
        """Handle business rule validation errors"""
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="BUSINESS_RULE_VALIDATION",
            message=str(exc),
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.HIGH,
            suggestions=[
                "Review business logic requirements",
                "Check tax calculations and rates",
                "Verify CABYS codes and product information",
                "Ensure document relationships are correct"
            ],
            is_retryable=False
        )
        
        self._track_error("BUSINESS_RULE_VALIDATION", ErrorCategory.BUSINESS_LOGIC, str(exc), is_retryable=False)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    async def _handle_ministry_error(
        self,
        request: Request,
        exc: MinistryError,
        error_id: str
    ) -> JSONResponse:
        """Handle Ministry API errors"""
        # Parse Ministry error if it contains structured data
        ministry_error_info = None
        if hasattr(exc, 'error_data') and exc.error_data:
            ministry_error_info = self.error_parser.parse_ministry_error(exc.error_data)
        
        suggestions = [
            "Check document format and content",
            "Verify digital signature is valid",
            "Ensure certificate is not expired",
            "Review Ministry API documentation"
        ]
        
        if ministry_error_info:
            suggestions.extend(ministry_error_info.get("suggestions", []))
        
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="MINISTRY_API_ERROR",
            message=str(exc),
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            suggestions=list(set(suggestions)),
            is_retryable=ministry_error_info.get("is_retryable", False) if ministry_error_info else False,
            retry_after=ministry_error_info.get("retry_after") if ministry_error_info else None,
            external_error=ministry_error_info
        )
        
        self._track_error("MINISTRY_API_ERROR", ErrorCategory.EXTERNAL_SERVICE, str(exc), is_retryable=ministry_error_info.get("is_retryable", False) if ministry_error_info else False)
        
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=error_response
        )
    
    async def _handle_certificate_error(
        self,
        request: Request,
        exc: CertificateError,
        error_id: str
    ) -> JSONResponse:
        """Handle certificate-related errors"""
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="CERTIFICATE_ERROR",
            message=str(exc),
            category=ErrorCategory.CERTIFICATE,
            severity=ErrorSeverity.CRITICAL,
            suggestions=[
                "Check certificate expiration date",
                "Verify certificate is valid for electronic invoicing",
                "Ensure certificate chain is complete",
                "Re-upload certificate if necessary",
                "Contact certificate authority if issues persist"
            ],
            is_retryable=False
        )
        
        self._track_error("CERTIFICATE_ERROR", ErrorCategory.CERTIFICATE, str(exc), is_retryable=False)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    async def _handle_not_found_error(
        self,
        request: Request,
        exc: Union[DocumentNotFoundError, NotFoundError],
        error_id: str
    ) -> JSONResponse:
        """Handle resource not found errors"""
        error_code = "DOCUMENT_NOT_FOUND" if isinstance(exc, DocumentNotFoundError) else "RESOURCE_NOT_FOUND"
        
        error_response = self._create_error_response(
            error_id=error_id,
            error_code=error_code,
            message=str(exc),
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            suggestions=[
                "Verify the resource ID is correct",
                "Check if the resource exists",
                "Ensure you have access to the resource"
            ],
            is_retryable=False
        )
        
        self._track_error(error_code, ErrorCategory.VALIDATION, str(exc), is_retryable=False)
        
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response
        )
    
    async def _handle_permission_error(
        self,
        request: Request,
        exc: CustomPermissionError,
        error_id: str
    ) -> JSONResponse:
        """Handle permission/authorization errors"""
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="INSUFFICIENT_PERMISSIONS",
            message=str(exc),
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            suggestions=[
                "Check your API key permissions",
                "Verify you have access to this resource",
                "Contact administrator for access rights"
            ],
            is_retryable=False
        )
        
        self._track_error("INSUFFICIENT_PERMISSIONS", ErrorCategory.AUTHORIZATION, str(exc), is_retryable=False)
        
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error_response
        )
    
    async def _handle_database_error(
        self,
        request: Request,
        exc: SQLAlchemyError,
        error_id: str
    ) -> JSONResponse:
        """Handle database errors"""
        if isinstance(exc, IntegrityError):
            error_code = "DATABASE_INTEGRITY_ERROR"
            message = "Data integrity constraint violation"
            suggestions = [
                "Check for duplicate values in unique fields",
                "Verify foreign key relationships",
                "Ensure data meets database constraints"
            ]
        else:
            error_code = "DATABASE_ERROR"
            message = "Database operation failed"
            suggestions = [
                "Retry the operation",
                "Check database connectivity",
                "Contact support if problem persists"
            ]
        
        error_response = self._create_error_response(
            error_id=error_id,
            error_code=error_code,
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            suggestions=suggestions,
            is_retryable=True
        )
        
        self._track_error(error_code, ErrorCategory.DATABASE, message, is_retryable=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )
    
    async def _handle_cache_error(
        self,
        request: Request,
        exc: RedisError,
        error_id: str
    ) -> JSONResponse:
        """Handle cache/Redis errors"""
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="CACHE_ERROR",
            message="Cache operation failed",
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.MEDIUM,
            suggestions=[
                "Operation will continue without cache",
                "Check Redis connectivity",
                "Contact support if problem persists"
            ],
            is_retryable=True
        )
        
        self._track_error("CACHE_ERROR", ErrorCategory.CACHE, "Cache operation failed", is_retryable=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )
    
    async def _handle_generic_error(
        self,
        request: Request,
        exc: Exception,
        error_id: str
    ) -> JSONResponse:
        """Handle generic/unknown errors"""
        error_response = self._create_error_response(
            error_id=error_id,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            suggestions=[
                "Retry the operation",
                "Contact support with error ID if problem persists"
            ],
            is_retryable=True
        )
        
        self._track_error("INTERNAL_SERVER_ERROR", ErrorCategory.SYSTEM, "An unexpected error occurred", is_retryable=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )
    
    def _create_error_response(
        self,
        error_id: str,
        error_code: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        suggestions: Optional[List[str]] = None,
        is_retryable: bool = False,
        retry_after: Optional[int] = None,
        field_errors: Optional[Dict[str, Any]] = None,
        external_error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create structured error response"""
        response = {
            "error": {
                "id": error_id,
                "code": self.error_codes.get(error_code, 5000),
                "error_code": error_code,
                "message": message,
                "category": category.value,
                "severity": severity.value,
                "timestamp": datetime.utcnow().isoformat(),
                "is_retryable": is_retryable
            }
        }
        
        if suggestions:
            response["error"]["suggestions"] = suggestions
        
        if retry_after:
            response["error"]["retry_after"] = retry_after
        
        if field_errors:
            response["error"]["field_errors"] = field_errors
        
        if external_error:
            response["error"]["external_error"] = external_error
        
        # Add recovery actions
        response["error"]["recovery_actions"] = self._get_recovery_actions(
            category, error_code, is_retryable
        )
        
        return response
    
    def _get_field_suggestions(self, field_path: str, error_type: str) -> List[str]:
        """Get field-specific suggestions"""
        suggestions = []
        
        field_lower = field_path.lower()
        
        if "cabys" in field_lower:
            suggestions.extend([
                "Ensure CABYS code has exactly 13 digits",
                "Verify code exists in official CABYS catalog"
            ])
        elif "identificacion" in field_lower:
            suggestions.extend([
                "Check identification type matches number format",
                "Verify identification type is valid (01-06)"
            ])
        elif "fecha" in field_lower:
            suggestions.extend([
                "Use ISO 8601 format: YYYY-MM-DDTHH:MM:SS",
                "Ensure date is not in the future"
            ])
        elif "email" in field_lower:
            suggestions.append("Provide a valid email address")
        elif "telefono" in field_lower:
            suggestions.append("Check phone number format and country code")
        
        return suggestions
    
    def _get_recovery_actions(
        self,
        category: ErrorCategory,
        error_code: str,
        is_retryable: bool
    ) -> List[str]:
        """Get recovery actions based on error category"""
        actions = []
        
        if is_retryable:
            actions.append("Retry the operation after a short delay")
        
        if category == ErrorCategory.VALIDATION:
            actions.extend([
                "Review and correct the highlighted fields",
                "Validate data against API documentation"
            ])
        elif category == ErrorCategory.AUTHENTICATION:
            actions.extend([
                "Check API key is valid and active",
                "Verify authentication headers"
            ])
        elif category == ErrorCategory.EXTERNAL_SERVICE:
            actions.extend([
                "Check service status",
                "Verify network connectivity"
            ])
        elif category == ErrorCategory.DATABASE:
            actions.extend([
                "Check data constraints",
                "Verify database connectivity"
            ])
        
        actions.append("Contact support if problem persists")
        
        return actions
    
    def _categorize_http_exception(self, status_code: int) -> ErrorCategory:
        """Categorize HTTP exception by status code"""
        if status_code == 401:
            return ErrorCategory.AUTHENTICATION
        elif status_code == 403:
            return ErrorCategory.AUTHORIZATION
        elif status_code == 404:
            return ErrorCategory.VALIDATION
        elif status_code == 422:
            return ErrorCategory.VALIDATION
        elif status_code == 429:
            return ErrorCategory.RATE_LIMIT
        elif 500 <= status_code < 600:
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.UNKNOWN
    
    def _get_error_code_from_status(self, status_code: int) -> str:
        """Get error code from HTTP status"""
        status_to_code = {
            401: "AUTHENTICATION_FAILED",
            403: "INSUFFICIENT_PERMISSIONS",
            404: "RESOURCE_NOT_FOUND",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
            502: "EXTERNAL_SERVICE_ERROR",
            503: "SERVICE_UNAVAILABLE"
        }
        return status_to_code.get(status_code, "UNKNOWN_ERROR")
    
    def _get_severity_from_status(self, status_code: int) -> ErrorSeverity:
        """Get error severity from HTTP status"""
        if status_code < 400:
            return ErrorSeverity.LOW
        elif status_code < 500:
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.CRITICAL
    
    def _get_suggestions_for_status(self, status_code: int) -> List[str]:
        """Get suggestions based on HTTP status code"""
        suggestions_map = {
            401: ["Check API key", "Verify authentication headers"],
            403: ["Check permissions", "Contact administrator"],
            404: ["Verify resource ID", "Check resource exists"],
            422: ["Review request data", "Check field formats"],
            429: ["Reduce request rate", "Wait before retrying"],
            500: ["Retry operation", "Contact support"],
            502: ["Check external service", "Retry later"],
            503: ["Service temporarily unavailable", "Retry later"]
        }
        return suggestions_map.get(status_code, ["Contact support"])
    
    def _is_retryable_status(self, status_code: int) -> bool:
        """Check if HTTP status indicates retryable error"""
        retryable_statuses = {429, 500, 502, 503, 504}
        return status_code in retryable_statuses
    
    def _log_exception(self, exc: Exception, request: Request, error_id: str):
        """Log exception with context"""
        logger.error(
            f"Exception occurred: {type(exc).__name__}: {str(exc)}",
            extra={
                "error_id": error_id,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "request_method": request.method,
                "request_url": str(request.url),
                "request_headers": dict(request.headers),
                "traceback": traceback.format_exc()
            }
        )
    
    def _track_error(self, error_code: str, category: ErrorCategory, message: str = "", tenant_id: Optional[str] = None, is_retryable: bool = False, context: Optional[Dict[str, Any]] = None):
        """Track error for monitoring and alerting"""
        key = f"{category.value}:{error_code}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Record error in monitoring system
        error_monitor.record_error(
            error_code=error_code,
            category=category.value,
            severity=self._get_severity_for_category(category).value,
            message=message or f"Error occurred: {error_code}",
            tenant_id=tenant_id,
            is_retryable=is_retryable,
            context=context
        )
        
        # Log error metrics
        logger.info(
            f"Error tracked: {error_code}",
            extra={
                "error_code": error_code,
                "category": category.value,
                "count": self.error_counts[key],
                "tenant_id": tenant_id
            }
        )
    
    def _get_severity_for_category(self, category: ErrorCategory) -> ErrorSeverity:
        """Get default severity for error category"""
        severity_map = {
            ErrorCategory.VALIDATION: ErrorSeverity.HIGH,
            ErrorCategory.BUSINESS_LOGIC: ErrorSeverity.HIGH,
            ErrorCategory.AUTHENTICATION: ErrorSeverity.HIGH,
            ErrorCategory.AUTHORIZATION: ErrorSeverity.HIGH,
            ErrorCategory.EXTERNAL_SERVICE: ErrorSeverity.HIGH,
            ErrorCategory.DATABASE: ErrorSeverity.HIGH,
            ErrorCategory.CACHE: ErrorSeverity.MEDIUM,
            ErrorCategory.SYSTEM: ErrorSeverity.CRITICAL,
            ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
            ErrorCategory.CERTIFICATE: ErrorSeverity.CRITICAL,
            ErrorCategory.SIGNATURE: ErrorSeverity.CRITICAL,
            ErrorCategory.RATE_LIMIT: ErrorSeverity.MEDIUM,
            ErrorCategory.UNKNOWN: ErrorSeverity.MEDIUM,
        }
        return severity_map.get(category, ErrorSeverity.MEDIUM)
    
    def _create_fallback_response(self, error_id: str) -> JSONResponse:
        """Create fallback response when error handler fails"""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "id": error_id,
                    "code": 5200,
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "category": "system",
                    "severity": "critical",
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_retryable": True,
                    "suggestions": ["Contact support with error ID"],
                    "recovery_actions": ["Retry operation", "Contact support"]
                }
            }
        )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            "error_counts": self.error_counts.copy(),
            "total_errors": sum(self.error_counts.values()),
            "categories": self._get_category_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_category_stats(self) -> Dict[str, int]:
        """Get error statistics by category"""
        category_stats = {}
        for key, count in self.error_counts.items():
            category = key.split(":")[0]
            category_stats[category] = category_stats.get(category, 0) + count
        return category_stats
    
    def reset_error_statistics(self):
        """Reset error statistics"""
        self.error_counts.clear()
        logger.info("Error statistics reset")


# Global error handler instance
error_handler = ErrorHandler()