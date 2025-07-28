"""
Custom error classes for structured error handling.
"""


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""
    pass


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class PermissionError(Exception):
    """Raised when permission is denied."""
    pass


class BusinessRuleError(Exception):
    """Raised when business rule validation fails."""
    pass


class MinistryError(Exception):
    """Raised when Ministry API returns an error."""
    pass


class CertificateError(Exception):
    """Raised when certificate validation fails."""
    pass