"""
Error parser for Costa Rica Electronic Invoice API
Handles parsing and interpretation of Ministry error messages
"""
import json
import logging
import re
from typing import Dict, Optional, Any, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(str, Enum):
    """Error type categories"""
    VALIDATION = "validation"
    BUSINESS_RULE = "business_rule"
    SIGNATURE = "signature"
    CERTIFICATE = "certificate"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorParser:
    """
    Parser for Ministry error messages and responses
    Provides user-friendly error interpretation and suggestions
    """
    
    def __init__(self):
        # Error code patterns and their interpretations
        self.error_patterns = {
            # XSD Validation Errors
            r"XSD-\d+": {
                "type": ErrorType.VALIDATION,
                "severity": ErrorSeverity.HIGH,
                "category": "XML Structure",
                "is_correctable": True
            },
            
            # Business Rule Errors
            r"BUS-\d+": {
                "type": ErrorType.BUSINESS_RULE,
                "severity": ErrorSeverity.HIGH,
                "category": "Business Logic",
                "is_correctable": True
            },
            
            # Signature Errors
            r"SIG-\d+": {
                "type": ErrorType.SIGNATURE,
                "severity": ErrorSeverity.CRITICAL,
                "category": "Digital Signature",
                "is_correctable": False
            },
            
            # Certificate Errors
            r"CERT-\d+": {
                "type": ErrorType.CERTIFICATE,
                "severity": ErrorSeverity.CRITICAL,
                "category": "Certificate",
                "is_correctable": False
            },
            
            # Authentication Errors
            r"AUTH-\d+": {
                "type": ErrorType.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "category": "Authentication",
                "is_correctable": False
            },
            
            # System Errors
            r"SYS-\d+": {
                "type": ErrorType.SYSTEM,
                "severity": ErrorSeverity.MEDIUM,
                "category": "System",
                "is_correctable": False
            }
        }
        
        # Common error messages and their interpretations
        self.message_patterns = {
            # CABYS code errors
            r"c[óo]digo\s+cabys.*inv[áa]lido": {
                "type": ErrorType.VALIDATION,
                "field": "codigo_cabys",
                "suggestion": "Verify CABYS code format (13 digits) and existence in official catalog"
            },
            
            # Identification errors
            r"identificaci[óo]n.*inv[áa]lida": {
                "type": ErrorType.VALIDATION,
                "field": "identificacion",
                "suggestion": "Check identification number format and type"
            },
            
            # Tax calculation errors
            r"c[áa]lculo.*impuesto.*incorrecto": {
                "type": ErrorType.BUSINESS_RULE,
                "field": "impuestos",
                "suggestion": "Review tax calculations and rates"
            },
            
            # Date format errors
            r"fecha.*formato.*incorrecto": {
                "type": ErrorType.VALIDATION,
                "field": "fecha",
                "suggestion": "Use ISO 8601 date format (YYYY-MM-DDTHH:MM:SS)"
            },
            
            # Certificate expiration
            r"certificado.*expirado": {
                "type": ErrorType.CERTIFICATE,
                "field": "certificado",
                "suggestion": "Renew digital certificate"
            },
            
            # Signature validation
            r"firma.*inv[áa]lida": {
                "type": ErrorType.SIGNATURE,
                "field": "firma",
                "suggestion": "Verify digital signature and certificate"
            },
            
            # Network errors
            r"error.*conexi[óo]n|conexi[óo]n.*error|network.*error": {
                "type": ErrorType.NETWORK,
                "field": "network",
                "suggestion": "Check network connectivity and retry"
            },
            
            # Service availability errors
            r"servicio.*no.*disponible|service.*unavailable|temporarily.*unavailable": {
                "type": ErrorType.SYSTEM,
                "field": "service",
                "suggestion": "Retry after a short delay - service is temporarily unavailable"
            }
        }
        
        # Field-specific error suggestions
        self.field_suggestions = {
            "codigo_cabys": [
                "Ensure CABYS code has exactly 13 digits",
                "Verify code exists in official CABYS catalog",
                "Check for typos in the code"
            ],
            "identificacion": [
                "Verify identification type matches number format",
                "Check for correct number of digits",
                "Ensure identification type is valid (01-06)"
            ],
            "fecha": [
                "Use ISO 8601 format: YYYY-MM-DDTHH:MM:SS",
                "Ensure date is not in the future",
                "Check timezone information"
            ],
            "impuestos": [
                "Verify tax rates are correct",
                "Check tax calculations match line totals",
                "Ensure all required taxes are included"
            ],
            "certificado": [
                "Check certificate expiration date",
                "Verify certificate is valid for electronic invoicing",
                "Ensure certificate chain is complete"
            ],
            "firma": [
                "Verify digital signature is valid",
                "Check certificate used for signing",
                "Ensure XML was not modified after signing"
            ]
        }
        
        logger.info("Error parser initialized")
    
    def parse_rejection_errors(
        self,
        rejection_reason: str,
        error_details: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Parse Ministry rejection errors and provide user-friendly interpretation
        
        Args:
            rejection_reason: Main rejection reason
            error_details: Detailed error information
        
        Returns:
            Parsed error information with suggestions
        """
        try:
            parsed = {
                "main_reason": rejection_reason,
                "error_type": ErrorType.UNKNOWN,
                "severity": ErrorSeverity.MEDIUM,
                "category": "General",
                "is_correctable": True,
                "affected_fields": [],
                "suggestions": [],
                "detailed_errors": [],
                "corrective_actions": [],
                "parsed_at": self._get_timestamp()
            }
            
            # Parse main rejection reason
            main_error = self._parse_single_error(rejection_reason)
            parsed.update(main_error)
            
            # Parse detailed errors if available
            if error_details:
                for error_detail in error_details:
                    detailed_error = self._parse_error_detail(error_detail)
                    parsed["detailed_errors"].append(detailed_error)
                    
                    # Collect affected fields
                    if detailed_error.get("field"):
                        parsed["affected_fields"].append(detailed_error["field"])
                    
                    # Collect suggestions
                    if detailed_error.get("suggestions"):
                        parsed["suggestions"].extend(detailed_error["suggestions"])
            
            # Generate corrective actions
            parsed["corrective_actions"] = self._generate_corrective_actions(
                parsed["error_type"], parsed["affected_fields"]
            )
            
            # Remove duplicates from suggestions
            parsed["suggestions"] = list(set(parsed["suggestions"]))
            parsed["affected_fields"] = list(set(parsed["affected_fields"]))
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing rejection errors: {e}")
            return {
                "main_reason": rejection_reason,
                "error_type": ErrorType.UNKNOWN,
                "severity": ErrorSeverity.MEDIUM,
                "category": "Parsing Error",
                "is_correctable": True,
                "affected_fields": [],
                "suggestions": ["Contact support for assistance with this error"],
                "detailed_errors": [],
                "corrective_actions": ["Review error message manually"],
                "parsing_error": str(e),
                "parsed_at": self._get_timestamp()
            }
    
    def parse_ministry_error(self, error_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Ministry API error response
        
        Args:
            error_response: Raw Ministry error response
        
        Returns:
            Parsed error information
        """
        try:
            parsed = {
                "error_code": None,
                "error_message": None,
                "error_type": ErrorType.UNKNOWN,
                "severity": ErrorSeverity.MEDIUM,
                "is_retryable": False,
                "retry_after": None,
                "field_errors": {},
                "suggestions": [],
                "raw_response": error_response,
                "parsed_at": self._get_timestamp()
            }
            
            # Extract basic error information
            parsed["error_code"] = error_response.get("codigo", error_response.get("code"))
            parsed["error_message"] = error_response.get("mensaje", error_response.get("message"))
            
            # Parse error code if available
            if parsed["error_code"]:
                code_info = self._parse_error_code(parsed["error_code"])
                parsed.update(code_info)
            
            # Parse error message
            if parsed["error_message"]:
                message_info = self._parse_error_message(parsed["error_message"])
                parsed.update(message_info)
            
            # Parse field-specific errors
            if "errores" in error_response:
                parsed["field_errors"] = self._parse_field_errors(error_response["errores"])
            elif "errors" in error_response:
                parsed["field_errors"] = self._parse_field_errors(error_response["errors"])
            
            # Determine if error is retryable
            parsed["is_retryable"] = self._is_retryable_error(
                parsed["error_code"], parsed["error_message"], parsed["error_type"]
            )
            
            # Extract retry-after if available
            if "retry_after" in error_response:
                parsed["retry_after"] = error_response["retry_after"]
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing Ministry error response: {e}")
            return {
                "error_code": "PARSE_ERROR",
                "error_message": f"Failed to parse error response: {e}",
                "error_type": ErrorType.SYSTEM,
                "severity": ErrorSeverity.MEDIUM,
                "is_retryable": True,
                "suggestions": ["Retry the operation", "Contact support if problem persists"],
                "raw_response": error_response,
                "parsed_at": self._get_timestamp()
            }
    
    def categorize_error_for_retry(self, error_info: Dict[str, Any]) -> Tuple[bool, int]:
        """
        Categorize error for retry logic
        
        Args:
            error_info: Parsed error information
        
        Returns:
            Tuple of (should_retry, delay_seconds)
        """
        error_type = error_info.get("error_type", ErrorType.UNKNOWN)
        severity = error_info.get("severity", ErrorSeverity.MEDIUM)
        
        # Don't retry validation and business rule errors
        if error_type in [ErrorType.VALIDATION, ErrorType.BUSINESS_RULE]:
            return False, 0
        
        # Don't retry certificate and signature errors
        if error_type in [ErrorType.CERTIFICATE, ErrorType.SIGNATURE]:
            return False, 0
        
        # Retry delays based on error type and severity
        retry_delays = {
            ErrorType.NETWORK: {
                ErrorSeverity.LOW: 30,
                ErrorSeverity.MEDIUM: 60,
                ErrorSeverity.HIGH: 120,
                ErrorSeverity.CRITICAL: 300
            },
            ErrorType.SYSTEM: {
                ErrorSeverity.LOW: 60,
                ErrorSeverity.MEDIUM: 120,
                ErrorSeverity.HIGH: 300,
                ErrorSeverity.CRITICAL: 600
            },
            ErrorType.AUTHENTICATION: {
                ErrorSeverity.LOW: 60,
                ErrorSeverity.MEDIUM: 120,
                ErrorSeverity.HIGH: 300,
                ErrorSeverity.CRITICAL: 600
            }
        }
        
        delay = retry_delays.get(error_type, {}).get(severity, 300)
        return True, delay
    
    def _parse_single_error(self, error_message: str) -> Dict[str, Any]:
        """Parse a single error message"""
        error_info = {
            "error_type": ErrorType.UNKNOWN,
            "severity": ErrorSeverity.MEDIUM,
            "category": "General",
            "is_correctable": True,
            "suggestions": []
        }
        
        # Check message patterns
        for pattern, info in self.message_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                error_info["error_type"] = info["type"]
                error_info["suggestions"].append(info["suggestion"])
                
                if "field" in info:
                    field_suggestions = self.field_suggestions.get(info["field"], [])
                    error_info["suggestions"].extend(field_suggestions)
                
                break
        
        return error_info
    
    def _parse_error_detail(self, error_detail: Dict[str, Any]) -> Dict[str, Any]:
        """Parse detailed error information"""
        parsed = {
            "code": error_detail.get("codigo", error_detail.get("code")),
            "message": error_detail.get("mensaje", error_detail.get("message")),
            "field": error_detail.get("campo", error_detail.get("field")),
            "value": error_detail.get("valor", error_detail.get("value")),
            "line": error_detail.get("linea", error_detail.get("line")),
            "suggestions": []
        }
        
        # Add field-specific suggestions
        if parsed["field"]:
            field_key = self._normalize_field_name(parsed["field"])
            suggestions = self.field_suggestions.get(field_key, [])
            parsed["suggestions"].extend(suggestions)
        
        # Parse error code if available
        if parsed["code"]:
            code_info = self._parse_error_code(parsed["code"])
            parsed.update(code_info)
        
        return parsed
    
    def _parse_error_code(self, error_code: str) -> Dict[str, Any]:
        """Parse error code and extract information"""
        for pattern, info in self.error_patterns.items():
            if re.match(pattern, error_code):
                return {
                    "error_type": info["type"],
                    "severity": info["severity"],
                    "category": info["category"],
                    "is_correctable": info["is_correctable"]
                }
        
        return {
            "error_type": ErrorType.UNKNOWN,
            "severity": ErrorSeverity.MEDIUM,
            "category": "Unknown",
            "is_correctable": True
        }
    
    def _parse_error_message(self, error_message: str) -> Dict[str, Any]:
        """Parse error message for additional information"""
        info = {"suggestions": []}
        
        # Check for specific patterns in message
        for pattern, pattern_info in self.message_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                info["error_type"] = pattern_info["type"]
                info["suggestions"].append(pattern_info["suggestion"])
        
        return info
    
    def _parse_field_errors(self, field_errors: List[Dict[str, Any]]) -> Dict[str, str]:
        """Parse field-specific errors"""
        parsed_fields = {}
        
        for error in field_errors:
            field = error.get("campo", error.get("field"))
            message = error.get("mensaje", error.get("message"))
            
            if field and message:
                parsed_fields[field] = message
        
        return parsed_fields
    
    def _generate_corrective_actions(
        self,
        error_type: ErrorType,
        affected_fields: List[str]
    ) -> List[str]:
        """Generate corrective actions based on error type and fields"""
        actions = []
        
        if error_type == ErrorType.VALIDATION:
            actions.append("Review and correct the highlighted fields")
            actions.append("Validate document against XSD schema")
            
        elif error_type == ErrorType.BUSINESS_RULE:
            actions.append("Review business logic validations")
            actions.append("Check tax calculations and rates")
            
        elif error_type == ErrorType.SIGNATURE:
            actions.append("Re-sign the document with valid certificate")
            actions.append("Verify certificate is not expired")
            
        elif error_type == ErrorType.CERTIFICATE:
            actions.append("Renew or replace digital certificate")
            actions.append("Verify certificate is valid for electronic invoicing")
            
        elif error_type == ErrorType.AUTHENTICATION:
            actions.append("Check API credentials")
            actions.append("Verify authentication token is valid")
            
        elif error_type == ErrorType.NETWORK:
            actions.append("Retry the operation after a short delay")
            actions.append("Check network connectivity")
            
        elif error_type == ErrorType.SYSTEM:
            actions.append("Retry the operation")
            actions.append("Contact support if problem persists")
        
        # Add field-specific actions
        for field in affected_fields:
            if field in self.field_suggestions:
                actions.extend(self.field_suggestions[field])
        
        return list(set(actions))  # Remove duplicates
    
    def _normalize_field_name(self, field_name: str) -> str:
        """Normalize field name for lookup"""
        field_lower = field_name.lower()
        
        if "cabys" in field_lower:
            return "codigo_cabys"
        elif "identificacion" in field_lower:
            return "identificacion"
        elif "fecha" in field_lower:
            return "fecha"
        elif "impuesto" in field_lower:
            return "impuestos"
        elif "certificado" in field_lower:
            return "certificado"
        elif "firma" in field_lower:
            return "firma"
        
        return field_name
    
    def _is_retryable_error(
        self,
        error_code: Optional[str],
        error_message: Optional[str],
        error_type: ErrorType
    ) -> bool:
        """Determine if error is retryable"""
        # Non-retryable error types
        if error_type in [
            ErrorType.VALIDATION,
            ErrorType.BUSINESS_RULE,
            ErrorType.SIGNATURE,
            ErrorType.CERTIFICATE
        ]:
            return False
        
        # Retryable error types
        if error_type in [
            ErrorType.NETWORK,
            ErrorType.SYSTEM,
            ErrorType.AUTHENTICATION
        ]:
            return True
        
        # Check specific error codes
        if error_code:
            non_retryable_prefixes = ["XSD-", "BUS-", "SIG-", "CERT-"]
            for prefix in non_retryable_prefixes:
                if error_code.startswith(prefix):
                    return False
        
        # Check error message for retryable indicators
        if error_message:
            retryable_keywords = [
                "timeout", "connection", "network", "service unavailable",
                "rate limit", "temporary", "try again"
            ]
            message_lower = error_message.lower()
            for keyword in retryable_keywords:
                if keyword in message_lower:
                    return True
        
        # Default to non-retryable for unknown errors
        return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_error_help(self, error_code: str) -> Dict[str, Any]:
        """Get comprehensive help for specific error code"""
        help_info = {
            "error_code": error_code,
            "description": "Unknown error",
            "category": "Unknown",
            "severity": ErrorSeverity.MEDIUM,
            "is_correctable": True,
            "common_causes": [],
            "solutions": [],
            "prevention_tips": []
        }
        
        # Add specific help based on error code patterns
        if error_code.startswith("XSD-"):
            help_info.update({
                "description": "XML structure validation error",
                "category": "XML Validation",
                "severity": ErrorSeverity.HIGH,
                "common_causes": [
                    "Missing required fields",
                    "Invalid field formats",
                    "Incorrect XML structure"
                ],
                "solutions": [
                    "Validate XML against official XSD schema",
                    "Check all required fields are present",
                    "Verify field formats match specifications"
                ],
                "prevention_tips": [
                    "Use validated XML generation libraries",
                    "Implement comprehensive field validation",
                    "Test with official XSD schemas"
                ]
            })
        
        elif error_code.startswith("BUS-"):
            help_info.update({
                "description": "Business rule validation error",
                "category": "Business Logic",
                "severity": ErrorSeverity.HIGH,
                "common_causes": [
                    "Invalid CABYS codes",
                    "Incorrect tax calculations",
                    "Business rule violations"
                ],
                "solutions": [
                    "Review business logic validations",
                    "Verify CABYS codes in official catalog",
                    "Check tax calculations and rates"
                ],
                "prevention_tips": [
                    "Keep CABYS catalog updated",
                    "Implement automated tax calculations",
                    "Regular business rule validation"
                ]
            })
        
        return help_info