"""
Custom error classes and structured error responses for Costa Rica Electronic Invoice API
Provides comprehensive error handling with categorization and recovery suggestions
"""
from typing import Dict, Any, Optional, List
from enum import Enum


class ErrorSeverity(str, Enum):
    """Error severity levels for prioritization and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class APIError(Exception):
    """
    Base API error class with structured error information
    """
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        suggestions: Optional[List[str]] = None,
        field_errors: Optional[Dict[str, str]] = None,
        is_retryable: bool = False,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.suggestions = suggestions or []
        self.field_errors = field_errors or {}
        self.is_retryable = is_retryable
        self.retry_after = retry_after
        self.context = context or {}


class ValidationError(APIError):
    """Raised when validation fails"""
    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.HIGH,
            field_errors=field_errors,
            suggestions=suggestions or [
                "Review the provided data for correctness",
                "Check field formats and requirements",
                "Ensure all required fields are provided"
            ],
            is_retryable=False,
            **kwargs
        )


class BusinessRuleError(APIError):
    """Raised when business rule validation fails"""
    def __init__(
        self,
        message: str,
        rule_code: Optional[str] = None,
        affected_fields: Optional[List[str]] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if rule_code:
            context['rule_code'] = rule_code
        if affected_fields:
            context['affected_fields'] = affected_fields
            
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_VALIDATION",
            severity=ErrorSeverity.HIGH,
            suggestions=suggestions or [
                "Review business logic requirements",
                "Check tax calculations and rates",
                "Verify CABYS codes and product information",
                "Ensure document relationships are correct"
            ],
            is_retryable=False,
            context=context,
            **kwargs
        )


class AuthenticationError(APIError):
    """Raised when authentication fails"""
    def __init__(
        self,
        message: str = "Authentication failed",
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            severity=ErrorSeverity.HIGH,
            suggestions=suggestions or [
                "Check API key is valid and active",
                "Verify authentication headers are correct",
                "Ensure API key has not expired"
            ],
            is_retryable=False,
            **kwargs
        )


class AuthorizationError(APIError):
    """Raised when authorization/permission fails"""
    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if required_permission:
            context['required_permission'] = required_permission
            
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_PERMISSIONS",
            severity=ErrorSeverity.HIGH,
            suggestions=suggestions or [
                "Check your API key permissions",
                "Verify you have access to this resource",
                "Contact administrator for access rights"
            ],
            is_retryable=False,
            context=context,
            **kwargs
        )


class RateLimitError(APIError):
    """Raised when rate limit is exceeded"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        reset_time: Optional[int] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if limit:
            context['limit'] = limit
        if reset_time:
            context['reset_time'] = reset_time
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            severity=ErrorSeverity.MEDIUM,
            suggestions=suggestions or [
                "Reduce request rate",
                "Wait before retrying",
                "Consider upgrading your plan for higher limits"
            ],
            is_retryable=True,
            retry_after=reset_time,
            context=context,
            **kwargs
        )


class DocumentNotFoundError(APIError):
    """Raised when a document is not found"""
    def __init__(
        self,
        message: str = "Document not found",
        document_id: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if document_id:
            context['document_id'] = document_id
            
        super().__init__(
            message=message,
            error_code="DOCUMENT_NOT_FOUND",
            severity=ErrorSeverity.MEDIUM,
            suggestions=suggestions or [
                "Verify the document ID is correct",
                "Check if the document exists",
                "Ensure you have access to the document"
            ],
            is_retryable=False,
            context=context,
            **kwargs
        )


class NotFoundError(APIError):
    """Raised when a resource is not found"""
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if resource_type:
            context['resource_type'] = resource_type
        if resource_id:
            context['resource_id'] = resource_id
            
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            severity=ErrorSeverity.MEDIUM,
            suggestions=suggestions or [
                "Verify the resource ID is correct",
                "Check if the resource exists",
                "Ensure you have access to the resource"
            ],
            is_retryable=False,
            context=context,
            **kwargs
        )


class PermissionError(AuthorizationError):
    """Alias for AuthorizationError for backward compatibility"""
    pass


class CertificateError(APIError):
    """Raised when certificate validation fails"""
    def __init__(
        self,
        message: str,
        certificate_issue: Optional[str] = None,
        expiry_date: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if certificate_issue:
            context['certificate_issue'] = certificate_issue
        if expiry_date:
            context['expiry_date'] = expiry_date
            
        super().__init__(
            message=message,
            error_code="CERTIFICATE_ERROR",
            severity=ErrorSeverity.CRITICAL,
            suggestions=suggestions or [
                "Check certificate expiration date",
                "Verify certificate is valid for electronic invoicing",
                "Ensure certificate chain is complete",
                "Re-upload certificate if necessary",
                "Contact certificate authority if issues persist"
            ],
            is_retryable=False,
            context=context,
            **kwargs
        )


class MinistryError(APIError):
    """Raised when Ministry API returns an error"""
    def __init__(
        self,
        message: str,
        ministry_code: Optional[str] = None,
        ministry_response: Optional[Dict[str, Any]] = None,
        is_retryable: bool = False,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if ministry_code:
            context['ministry_code'] = ministry_code
        if ministry_response:
            context['ministry_response'] = ministry_response
            
        super().__init__(
            message=message,
            error_code="MINISTRY_API_ERROR",
            severity=ErrorSeverity.HIGH,
            suggestions=suggestions or [
                "Check document format and content",
                "Verify digital signature is valid",
                "Ensure certificate is not expired",
                "Review Ministry API documentation"
            ],
            is_retryable=is_retryable,
            context=context,
            **kwargs
        )
        
        # Store raw error data for detailed parsing
        self.error_data = ministry_response


class DatabaseError(APIError):
    """Raised when database operations fail"""
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        table: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if operation:
            context['operation'] = operation
        if table:
            context['table'] = table
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            severity=ErrorSeverity.HIGH,
            suggestions=suggestions or [
                "Retry the operation",
                "Check database connectivity",
                "Contact support if problem persists"
            ],
            is_retryable=True,
            context=context,
            **kwargs
        )


class CacheError(APIError):
    """Raised when cache operations fail"""
    def __init__(
        self,
        message: str = "Cache operation failed",
        cache_key: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if cache_key:
            context['cache_key'] = cache_key
            
        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            severity=ErrorSeverity.MEDIUM,
            suggestions=suggestions or [
                "Operation will continue without cache",
                "Check Redis connectivity",
                "Contact support if problem persists"
            ],
            is_retryable=True,
            context=context,
            **kwargs
        )


class NetworkError(APIError):
    """Raised when network operations fail"""
    def __init__(
        self,
        message: str = "Network operation failed",
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if endpoint:
            context['endpoint'] = endpoint
        if timeout:
            context['timeout'] = timeout
            
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            severity=ErrorSeverity.MEDIUM,
            suggestions=suggestions or [
                "Check network connectivity",
                "Retry the operation",
                "Verify endpoint is accessible"
            ],
            is_retryable=True,
            context=context,
            **kwargs
        )


class ConfigurationError(APIError):
    """Raised when configuration is invalid"""
    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            suggestions=suggestions or [
                "Check configuration settings",
                "Verify environment variables",
                "Contact administrator"
            ],
            is_retryable=False,
            context=context,
            **kwargs
        )


class CABYSError(ValidationError):
    """Raised when CABYS code validation fails"""
    def __init__(
        self,
        message: str,
        cabys_code: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if cabys_code:
            context['cabys_code'] = cabys_code
            
        super().__init__(
            message=message,
            suggestions=suggestions or [
                "Ensure CABYS code has exactly 13 digits",
                "Verify code exists in official CABYS catalog",
                "Check for typos in the code"
            ],
            context=context,
            **kwargs
        )
        self.error_code = "CABYS_CODE_INVALID"


class TaxCalculationError(BusinessRuleError):
    """Raised when tax calculation fails"""
    def __init__(
        self,
        message: str,
        tax_type: Optional[str] = None,
        line_number: Optional[int] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if tax_type:
            context['tax_type'] = tax_type
        if line_number:
            context['line_number'] = line_number
            
        super().__init__(
            message=message,
            suggestions=suggestions or [
                "Verify tax rates are correct",
                "Check tax calculations match line totals",
                "Ensure all required taxes are included"
            ],
            context=context,
            **kwargs
        )
        self.error_code = "TAX_CALCULATION_ERROR"


class ConsecutiveNumberError(ValidationError):
    """Raised when consecutive number generation/validation fails"""
    def __init__(
        self,
        message: str,
        document_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if document_type:
            context['document_type'] = document_type
        if tenant_id:
            context['tenant_id'] = tenant_id
            
        super().__init__(
            message=message,
            suggestions=suggestions or [
                "Check document type is valid",
                "Verify tenant configuration",
                "Ensure consecutive number format is correct"
            ],
            context=context,
            **kwargs
        )
        self.error_code = "CONSECUTIVE_NUMBER_INVALID"


class DocumentKeyError(ValidationError):
    """Raised when document key generation/validation fails"""
    def __init__(
        self,
        message: str,
        document_key: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if document_key:
            context['document_key'] = document_key
            
        super().__init__(
            message=message,
            suggestions=suggestions or [
                "Verify document key format (50 digits)",
                "Check key generation parameters",
                "Ensure key uniqueness"
            ],
            context=context,
            **kwargs
        )
        self.error_code = "DOCUMENT_KEY_INVALID"


# Error response helpers
def create_error_response(
    error: APIError,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response from APIError
    
    Args:
        error: APIError instance
        request_id: Optional request ID for tracking
    
    Returns:
        Structured error response dictionary
    """
    from datetime import datetime
    
    response = {
        "error": {
            "code": error.error_code or "UNKNOWN_ERROR",
            "message": error.message,
            "severity": error.severity.value,
            "timestamp": datetime.utcnow().isoformat(),
            "is_retryable": error.is_retryable
        }
    }
    
    if request_id:
        response["error"]["request_id"] = request_id
    
    if error.suggestions:
        response["error"]["suggestions"] = error.suggestions
    
    if error.field_errors:
        response["error"]["field_errors"] = error.field_errors
    
    if error.retry_after:
        response["error"]["retry_after"] = error.retry_after
    
    if error.context:
        response["error"]["context"] = error.context
    
    return response


def create_validation_error_response(
    message: str,
    field_errors: Dict[str, str],
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create validation error response
    
    Args:
        message: Main error message
        field_errors: Field-specific error messages
        request_id: Optional request ID for tracking
    
    Returns:
        Structured validation error response
    """
    error = ValidationError(message=message, field_errors=field_errors)
    return create_error_response(error, request_id)


def create_ministry_error_response(
    message: str,
    ministry_code: Optional[str] = None,
    ministry_response: Optional[Dict[str, Any]] = None,
    is_retryable: bool = False,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create Ministry API error response
    
    Args:
        message: Error message
        ministry_code: Ministry error code
        ministry_response: Raw Ministry response
        is_retryable: Whether error is retryable
        request_id: Optional request ID for tracking
    
    Returns:
        Structured Ministry error response
    """
    error = MinistryError(
        message=message,
        ministry_code=ministry_code,
        ministry_response=ministry_response,
        is_retryable=is_retryable
    )
    return create_error_response(error, request_id)