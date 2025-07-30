"""
Error handling helpers and utilities for Costa Rica Electronic Invoice API
Provides convenient functions for common error scenarios and recovery suggestions
"""
from typing import Dict, Any, List, Optional, Union
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.utils.error_responses import (
    APIError,
    ValidationError as CustomValidationError,
    BusinessRuleError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    DocumentNotFoundError,
    NotFoundError,
    CertificateError,
    MinistryError,
    DatabaseError,
    CacheError,
    NetworkError,
    CABYSError,
    TaxCalculationError,
    ConsecutiveNumberError,
    DocumentKeyError,
    create_error_response,
    create_validation_error_response,
    create_ministry_error_response
)


def raise_validation_error(
    message: str,
    field_errors: Optional[Dict[str, str]] = None,
    suggestions: Optional[List[str]] = None
):
    """
    Raise a validation error with structured information
    
    Args:
        message: Main error message
        field_errors: Field-specific error messages
        suggestions: Recovery suggestions
    
    Raises:
        CustomValidationError: Structured validation error
    """
    raise CustomValidationError(
        message=message,
        field_errors=field_errors,
        suggestions=suggestions
    )


def raise_business_rule_error(
    message: str,
    rule_code: Optional[str] = None,
    affected_fields: Optional[List[str]] = None,
    suggestions: Optional[List[str]] = None
):
    """
    Raise a business rule validation error
    
    Args:
        message: Error message
        rule_code: Business rule code that failed
        affected_fields: Fields affected by the rule
        suggestions: Recovery suggestions
    
    Raises:
        BusinessRuleError: Structured business rule error
    """
    raise BusinessRuleError(
        message=message,
        rule_code=rule_code,
        affected_fields=affected_fields,
        suggestions=suggestions
    )


def raise_cabys_error(
    message: str,
    cabys_code: Optional[str] = None,
    suggestions: Optional[List[str]] = None
):
    """
    Raise a CABYS code validation error
    
    Args:
        message: Error message
        cabys_code: Invalid CABYS code
        suggestions: Recovery suggestions
    
    Raises:
        CABYSError: Structured CABYS error
    """
    raise CABYSError(
        message=message,
        cabys_code=cabys_code,
        suggestions=suggestions
    )


def raise_tax_calculation_error(
    message: str,
    tax_type: Optional[str] = None,
    line_number: Optional[int] = None,
    suggestions: Optional[List[str]] = None
):
    """
    Raise a tax calculation error
    
    Args:
        message: Error message
        tax_type: Type of tax that failed calculation
        line_number: Line number where error occurred
        suggestions: Recovery suggestions
    
    Raises:
        TaxCalculationError: Structured tax calculation error
    """
    raise TaxCalculationError(
        message=message,
        tax_type=tax_type,
        line_number=line_number,
        suggestions=suggestions
    )


def raise_certificate_error(
    message: str,
    certificate_issue: Optional[str] = None,
    expiry_date: Optional[str] = None,
    suggestions: Optional[List[str]] = None
):
    """
    Raise a certificate error
    
    Args:
        message: Error message
        certificate_issue: Specific certificate issue
        expiry_date: Certificate expiry date if relevant
        suggestions: Recovery suggestions
    
    Raises:
        CertificateError: Structured certificate error
    """
    raise CertificateError(
        message=message,
        certificate_issue=certificate_issue,
        expiry_date=expiry_date,
        suggestions=suggestions
    )


def raise_ministry_error(
    message: str,
    ministry_code: Optional[str] = None,
    ministry_response: Optional[Dict[str, Any]] = None,
    is_retryable: bool = False,
    suggestions: Optional[List[str]] = None
):
    """
    Raise a Ministry API error
    
    Args:
        message: Error message
        ministry_code: Ministry error code
        ministry_response: Raw Ministry response
        is_retryable: Whether error is retryable
        suggestions: Recovery suggestions
    
    Raises:
        MinistryError: Structured Ministry error
    """
    raise MinistryError(
        message=message,
        ministry_code=ministry_code,
        ministry_response=ministry_response,
        is_retryable=is_retryable,
        suggestions=suggestions
    )


def raise_document_not_found(
    document_id: str,
    message: Optional[str] = None
):
    """
    Raise a document not found error
    
    Args:
        document_id: ID of the document that wasn't found
        message: Optional custom message
    
    Raises:
        DocumentNotFoundError: Structured document not found error
    """
    raise DocumentNotFoundError(
        message=message or f"Document not found: {document_id}",
        document_id=document_id
    )


def raise_resource_not_found(
    resource_type: str,
    resource_id: str,
    message: Optional[str] = None
):
    """
    Raise a resource not found error
    
    Args:
        resource_type: Type of resource
        resource_id: ID of the resource that wasn't found
        message: Optional custom message
    
    Raises:
        NotFoundError: Structured resource not found error
    """
    raise NotFoundError(
        message=message or f"{resource_type} not found: {resource_id}",
        resource_type=resource_type,
        resource_id=resource_id
    )


def raise_authentication_error(
    message: Optional[str] = None,
    suggestions: Optional[List[str]] = None
):
    """
    Raise an authentication error
    
    Args:
        message: Optional custom message
        suggestions: Recovery suggestions
    
    Raises:
        AuthenticationError: Structured authentication error
    """
    raise AuthenticationError(
        message=message or "Authentication failed",
        suggestions=suggestions
    )


def raise_authorization_error(
    message: Optional[str] = None,
    required_permission: Optional[str] = None,
    suggestions: Optional[List[str]] = None
):
    """
    Raise an authorization error
    
    Args:
        message: Optional custom message
        required_permission: Required permission that was missing
        suggestions: Recovery suggestions
    
    Raises:
        AuthorizationError: Structured authorization error
    """
    raise AuthorizationError(
        message=message or "Insufficient permissions",
        required_permission=required_permission,
        suggestions=suggestions
    )


def raise_rate_limit_error(
    limit: int,
    reset_time: Optional[int] = None,
    message: Optional[str] = None
):
    """
    Raise a rate limit error
    
    Args:
        limit: Rate limit that was exceeded
        reset_time: Time when limit resets
        message: Optional custom message
    
    Raises:
        RateLimitError: Structured rate limit error
    """
    raise RateLimitError(
        message=message or f"Rate limit of {limit} requests exceeded",
        limit=limit,
        reset_time=reset_time
    )


def handle_pydantic_validation_error(
    validation_error: ValidationError,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert Pydantic validation error to structured error response
    
    Args:
        validation_error: Pydantic ValidationError
        context: Optional context for the error
    
    Returns:
        Structured error response dictionary
    """
    field_errors = {}
    for error in validation_error.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = error["msg"]
    
    message = f"Validation failed{f' for {context}' if context else ''}"
    
    return create_validation_error_response(
        message=message,
        field_errors=field_errors
    )


def get_error_suggestions_for_field(field_name: str, error_type: str) -> List[str]:
    """
    Get field-specific error suggestions
    
    Args:
        field_name: Name of the field with error
        error_type: Type of validation error
    
    Returns:
        List of suggestions for fixing the error
    """
    field_lower = field_name.lower()
    suggestions = []
    
    if "cabys" in field_lower:
        suggestions.extend([
            "Ensure CABYS code has exactly 13 digits",
            "Verify code exists in official CABYS catalog",
            "Check for typos in the code",
            "Use the CABYS search endpoint to find valid codes"
        ])
    elif "identificacion" in field_lower:
        suggestions.extend([
            "Check identification type matches number format",
            "Verify identification type is valid (01-06)",
            "For physical ID: use format 1-2345-6789",
            "For legal ID: use format 3-101-123456"
        ])
    elif "fecha" in field_lower:
        suggestions.extend([
            "Use ISO 8601 format: YYYY-MM-DDTHH:MM:SS",
            "Ensure date is not in the future",
            "Include timezone information if required",
            "Check date is within valid business range"
        ])
    elif "email" in field_lower:
        suggestions.extend([
            "Provide a valid email address",
            "Check email format includes @ and domain",
            "Ensure email length is within limits"
        ])
    elif "telefono" in field_lower:
        suggestions.extend([
            "Check phone number format",
            "Include valid country code (1-999)",
            "Ensure phone number has correct digit count"
        ])
    elif "moneda" in field_lower or "currency" in field_lower:
        suggestions.extend([
            "Use 3-letter ISO 4217 currency code",
            "Common codes: CRC, USD, EUR",
            "Ensure currency code is uppercase"
        ])
    elif "impuesto" in field_lower or "tax" in field_lower:
        suggestions.extend([
            "Verify tax rates are correct",
            "Check tax calculations match line totals",
            "Ensure all required taxes are included",
            "Use valid tax codes (01-12, 99)"
        ])
    elif "precio" in field_lower or "monto" in field_lower:
        suggestions.extend([
            "Ensure amounts are positive",
            "Check decimal precision (max 5 decimal places)",
            "Verify amounts don't exceed maximum limits",
            "Use proper decimal format"
        ])
    
    # Add general suggestions based on error type
    if error_type == "value_error":
        suggestions.append("Check the value format and constraints")
    elif error_type == "type_error":
        suggestions.append("Ensure the value is of the correct data type")
    elif error_type == "missing":
        suggestions.append("This field is required and cannot be empty")
    
    return suggestions


def create_field_error_map(
    validation_errors: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Create a comprehensive field error map from validation errors
    
    Args:
        validation_errors: List of validation error dictionaries
    
    Returns:
        Dictionary mapping field paths to error information
    """
    field_errors = {}
    
    for error in validation_errors:
        field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "unknown")
        message = error.get("msg", "Validation failed")
        
        field_errors[field_path] = {
            "message": message,
            "type": error_type,
            "input": error.get("input"),
            "suggestions": get_error_suggestions_for_field(field_path, error_type)
        }
    
    return field_errors


def format_ministry_error(
    ministry_response: Dict[str, Any],
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format Ministry API error response into structured format
    
    Args:
        ministry_response: Raw Ministry error response
        context: Optional context for the error
    
    Returns:
        Formatted error response
    """
    error_code = ministry_response.get("codigo", ministry_response.get("code"))
    error_message = ministry_response.get("mensaje", ministry_response.get("message"))
    
    if context:
        error_message = f"{context}: {error_message}"
    
    # Determine if error is retryable based on code/message
    is_retryable = False
    if error_code:
        retryable_codes = ["TIMEOUT", "NETWORK", "SERVICE_UNAVAILABLE", "RATE_LIMIT"]
        is_retryable = any(code in str(error_code).upper() for code in retryable_codes)
    
    return create_ministry_error_response(
        message=error_message or "Ministry API error occurred",
        ministry_code=error_code,
        ministry_response=ministry_response,
        is_retryable=is_retryable
    )


def get_recovery_actions_for_error(error_code: str, category: str) -> List[str]:
    """
    Get recovery actions for specific error codes and categories
    
    Args:
        error_code: Error code
        category: Error category
    
    Returns:
        List of recovery actions
    """
    actions = []
    
    # Specific error code actions
    error_actions = {
        "CABYS_CODE_INVALID": [
            "Search for valid CABYS codes using the search endpoint",
            "Verify the code format (exactly 13 digits)",
            "Check the official CABYS catalog"
        ],
        "CERTIFICATE_EXPIRED": [
            "Renew your digital certificate",
            "Upload the new certificate through the API",
            "Contact your certificate authority"
        ],
        "MINISTRY_AUTHENTICATION_ERROR": [
            "Check Ministry API credentials",
            "Verify authentication token is valid",
            "Contact Ministry support if credentials are correct"
        ],
        "RATE_LIMIT_EXCEEDED": [
            "Wait for the rate limit to reset",
            "Reduce request frequency",
            "Consider upgrading your plan for higher limits"
        ],
        "VALIDATION_ERROR": [
            "Review the field errors and correct the data",
            "Check the API documentation for field requirements",
            "Validate data before sending requests"
        ]
    }
    
    if error_code in error_actions:
        actions.extend(error_actions[error_code])
    
    # Category-based actions
    category_actions = {
        "validation": [
            "Review and correct the highlighted fields",
            "Validate data against API documentation"
        ],
        "authentication": [
            "Check API key is valid and active",
            "Verify authentication headers"
        ],
        "external_service": [
            "Check service status",
            "Verify network connectivity",
            "Retry after a short delay"
        ],
        "database": [
            "Check data constraints",
            "Verify database connectivity",
            "Retry the operation"
        ],
        "certificate": [
            "Check certificate expiration",
            "Verify certificate is valid for electronic invoicing",
            "Re-upload certificate if necessary"
        ]
    }
    
    if category in category_actions:
        actions.extend(category_actions[category])
    
    # Always add general recovery action
    actions.append("Contact support if problem persists")
    
    return list(set(actions))  # Remove duplicates


def is_retryable_error(error: Union[Exception, Dict[str, Any]]) -> bool:
    """
    Determine if an error is retryable
    
    Args:
        error: Error instance or error dictionary
    
    Returns:
        True if error is retryable, False otherwise
    """
    if isinstance(error, APIError):
        return error.is_retryable
    
    if isinstance(error, dict):
        return error.get("is_retryable", False)
    
    # Check error type for retryability
    retryable_types = [
        NetworkError,
        DatabaseError,
        CacheError,
        MinistryError  # Some Ministry errors are retryable
    ]
    
    return any(isinstance(error, error_type) for error_type in retryable_types)


def get_retry_delay(error: Union[Exception, Dict[str, Any]], attempt: int = 1) -> int:
    """
    Get retry delay for an error based on attempt number
    
    Args:
        error: Error instance or error dictionary
        attempt: Retry attempt number (1-based)
    
    Returns:
        Delay in seconds before retry
    """
    if isinstance(error, APIError) and error.retry_after:
        return error.retry_after
    
    if isinstance(error, dict) and error.get("retry_after"):
        return error["retry_after"]
    
    # Exponential backoff with jitter
    base_delay = 2 ** min(attempt - 1, 6)  # Cap at 64 seconds base
    jitter = base_delay * 0.1  # 10% jitter
    
    import random
    return int(base_delay + random.uniform(-jitter, jitter))


# Convenience functions for common error scenarios
def validate_cabys_code(code: str) -> None:
    """Validate CABYS code format"""
    if not code or len(code) != 13 or not code.isdigit():
        raise_cabys_error(
            message=f"Invalid CABYS code format: {code}",
            cabys_code=code
        )


def validate_identification(tipo: str, numero: str) -> None:
    """Validate identification number format"""
    import re
    
    if tipo == "01":  # Physical ID
        if not re.match(r'^\d-\d{4}-\d{4}$', numero):
            raise_validation_error(
                message="Invalid physical ID format",
                field_errors={"identificacion.numero": "Must follow format: 1-2345-6789"},
                suggestions=["Use format: 1-2345-6789 for physical ID"]
            )
    elif tipo == "02":  # Legal ID
        if not re.match(r'^\d-\d{3}-\d{6}$', numero):
            raise_validation_error(
                message="Invalid legal ID format",
                field_errors={"identificacion.numero": "Must follow format: 3-101-123456"},
                suggestions=["Use format: 3-101-123456 for legal ID"]
            )


def validate_document_key(key: str) -> None:
    """Validate document key format"""
    if not key or len(key) != 50 or not key.isdigit():
        raise DocumentKeyError(
            message=f"Invalid document key format: {key}",
            document_key=key
        )


def validate_consecutive_number(number: str) -> None:
    """Validate consecutive number format"""
    if not number or len(number) != 20 or not number.isdigit():
        raise ConsecutiveNumberError(
            message=f"Invalid consecutive number format: {number}"
        )