"""
Ministry response parser for Costa Rica Electronic Invoice API
Handles parsing and interpretation of Ministry API responses
"""
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Optional, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class MinistryResponseStatus(str, Enum):
    """Ministry response status codes"""
    RECEIVED = "recibido"
    PROCESSING = "procesando"
    ACCEPTED = "aceptado"
    REJECTED = "rechazado"
    ERROR = "error"


class MinistryResponseParser:
    """
    Parser for Ministry of Finance API responses
    Handles both JSON and XML response formats
    """
    
    def __init__(self):
        # Status mapping from Ministry codes to internal status
        self.status_mapping = {
            "recibido": "enviado",
            "procesando": "procesando",
            "aceptado": "aceptado",
            "rechazado": "rechazado",
            "error": "error",
            "received": "enviado",
            "processing": "procesando",
            "accepted": "aceptado",
            "rejected": "rechazado"
        }
        
        # Common error codes and their meanings
        self.error_codes = {
            "XSD-01": "XML structure validation error",
            "XSD-02": "Required field missing",
            "XSD-03": "Invalid field format",
            "BUS-01": "Business rule validation error",
            "BUS-02": "Invalid CABYS code",
            "BUS-03": "Invalid tax calculation",
            "BUS-04": "Invalid identification number",
            "SIG-01": "Digital signature validation error",
            "SIG-02": "Certificate validation error",
            "SIG-03": "Certificate expired",
            "AUTH-01": "Authentication error",
            "AUTH-02": "Authorization error",
            "SYS-01": "System error",
            "SYS-02": "Service unavailable"
        }
        
        logger.info("Ministry response parser initialized")
    
    def parse_submission_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Ministry submission response
        
        Args:
            response_data: Raw Ministry API response
        
        Returns:
            Parsed response with standardized format
        """
        try:
            parsed = {
                "success": True,
                "status": "enviado",
                "message": None,
                "error_code": None,
                "error_details": [],
                "ministry_reference": None,
                "processed_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
            
            # Handle different response formats
            if isinstance(response_data, dict):
                parsed.update(self._parse_json_response(response_data))
            elif isinstance(response_data, str):
                # Try to parse as JSON first, then XML
                try:
                    json_data = json.loads(response_data)
                    parsed.update(self._parse_json_response(json_data))
                except json.JSONDecodeError:
                    parsed.update(self._parse_xml_response(response_data))
            
            # Standardize status
            if "status" in parsed:
                parsed["status"] = self.status_mapping.get(
                    parsed["status"].lower(), parsed["status"]
                )
            
            # Determine success based on status
            parsed["success"] = parsed["status"] not in ["rechazado", "error"]
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing submission response: {e}")
            return {
                "success": False,
                "status": "error",
                "message": f"Response parsing error: {e}",
                "error_code": "PARSE-01",
                "error_details": [],
                "ministry_reference": None,
                "processed_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
    
    def parse_status_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Ministry status check response
        
        Args:
            response_data: Raw Ministry status response
        
        Returns:
            Parsed status information
        """
        try:
            parsed = {
                "document_key": None,
                "status": "unknown",
                "message": None,
                "acceptance_date": None,
                "rejection_reason": None,
                "ministry_xml": None,
                "checked_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
            
            if isinstance(response_data, dict):
                # Extract document key
                parsed["document_key"] = response_data.get("clave")
                
                # Extract status
                status = response_data.get("estado", response_data.get("status"))
                if status:
                    parsed["status"] = self.status_mapping.get(
                        status.lower(), status
                    )
                
                # Extract message
                parsed["message"] = response_data.get(
                    "mensaje", response_data.get("message")
                )
                
                # Extract dates
                if "fechaAceptacion" in response_data:
                    parsed["acceptance_date"] = response_data["fechaAceptacion"]
                elif "acceptance_date" in response_data:
                    parsed["acceptance_date"] = response_data["acceptance_date"]
                
                # Extract rejection details
                if parsed["status"] == "rechazado":
                    parsed["rejection_reason"] = self._extract_rejection_reason(
                        response_data
                    )
                
                # Extract Ministry-signed XML if available
                if "xmlRespuesta" in response_data:
                    parsed["ministry_xml"] = response_data["xmlRespuesta"]
                elif "response_xml" in response_data:
                    parsed["ministry_xml"] = response_data["response_xml"]
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing status response: {e}")
            return {
                "document_key": None,
                "status": "error",
                "message": f"Status parsing error: {e}",
                "checked_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
    
    def parse_error_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Ministry error response
        
        Args:
            response_data: Raw Ministry error response
        
        Returns:
            Parsed error information
        """
        try:
            parsed = {
                "error_code": None,
                "error_message": None,
                "error_details": [],
                "field_errors": {},
                "suggestions": [],
                "is_retryable": False,
                "parsed_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
            
            if isinstance(response_data, dict):
                # Extract main error information
                parsed["error_code"] = response_data.get("codigo", response_data.get("code"))
                parsed["error_message"] = response_data.get("mensaje", response_data.get("message"))
                
                # Extract detailed errors
                if "errores" in response_data:
                    parsed["error_details"] = self._parse_error_details(
                        response_data["errores"]
                    )
                elif "errors" in response_data:
                    parsed["error_details"] = self._parse_error_details(
                        response_data["errors"]
                    )
                
                # Extract field-specific errors
                if "camposError" in response_data:
                    parsed["field_errors"] = self._parse_field_errors(
                        response_data["camposError"]
                    )
                elif "field_errors" in response_data:
                    parsed["field_errors"] = self._parse_field_errors(
                        response_data["field_errors"]
                    )
                
                # Determine if error is retryable
                parsed["is_retryable"] = self._is_error_retryable(
                    parsed["error_code"], parsed["error_message"]
                )
                
                # Generate suggestions
                parsed["suggestions"] = self._generate_error_suggestions(
                    parsed["error_code"], parsed["error_details"]
                )
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing error response: {e}")
            return {
                "error_code": "PARSE-02",
                "error_message": f"Error response parsing failed: {e}",
                "error_details": [],
                "field_errors": {},
                "suggestions": ["Check response format and try again"],
                "is_retryable": True,
                "parsed_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
    
    def parse_receptor_message_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse receptor message submission response
        
        Args:
            response_data: Raw Ministry receptor message response
        
        Returns:
            Parsed receptor message response
        """
        try:
            parsed = {
                "success": True,
                "message_id": None,
                "document_key": None,
                "message_type": None,
                "status": "enviado",
                "message": None,
                "processed_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
            
            if isinstance(response_data, dict):
                parsed["message_id"] = response_data.get("idMensaje", response_data.get("message_id"))
                parsed["document_key"] = response_data.get("clave", response_data.get("document_key"))
                parsed["message_type"] = response_data.get("tipoMensaje", response_data.get("message_type"))
                parsed["message"] = response_data.get("mensaje", response_data.get("message"))
                
                # Check for errors
                if "error" in response_data or "codigo" in response_data:
                    parsed["success"] = False
                    parsed["status"] = "error"
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing receptor message response: {e}")
            return {
                "success": False,
                "message": f"Receptor message parsing error: {e}",
                "status": "error",
                "processed_at": datetime.utcnow().isoformat(),
                "raw_response": response_data
            }
    
    def _parse_json_response(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON response format"""
        parsed = {}
        
        # Extract status
        if "estado" in json_data:
            parsed["status"] = json_data["estado"]
        elif "status" in json_data:
            parsed["status"] = json_data["status"]
        
        # Extract message
        if "mensaje" in json_data:
            parsed["message"] = json_data["mensaje"]
        elif "message" in json_data:
            parsed["message"] = json_data["message"]
        
        # Extract Ministry reference
        if "referencia" in json_data:
            parsed["ministry_reference"] = json_data["referencia"]
        elif "reference" in json_data:
            parsed["ministry_reference"] = json_data["reference"]
        
        # Extract error information
        if "codigo" in json_data:
            parsed["error_code"] = json_data["codigo"]
        elif "code" in json_data:
            parsed["error_code"] = json_data["code"]
        
        return parsed
    
    def _parse_xml_response(self, xml_data: str) -> Dict[str, Any]:
        """Parse XML response format"""
        try:
            root = ET.fromstring(xml_data)
            parsed = {}
            
            # Extract status from XML
            status_elem = root.find(".//estado") or root.find(".//status")
            if status_elem is not None:
                parsed["status"] = status_elem.text
            
            # Extract message from XML
            message_elem = root.find(".//mensaje") or root.find(".//message")
            if message_elem is not None:
                parsed["message"] = message_elem.text
            
            # Extract error code from XML
            code_elem = root.find(".//codigo") or root.find(".//code")
            if code_elem is not None:
                parsed["error_code"] = code_elem.text
            
            return parsed
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return {"status": "error", "message": f"XML parsing error: {e}"}
    
    def _parse_error_details(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse detailed error information"""
        parsed_errors = []
        
        for error in errors:
            if isinstance(error, dict):
                parsed_error = {
                    "code": error.get("codigo", error.get("code")),
                    "message": error.get("mensaje", error.get("message")),
                    "field": error.get("campo", error.get("field")),
                    "value": error.get("valor", error.get("value")),
                    "line": error.get("linea", error.get("line"))
                }
                parsed_errors.append(parsed_error)
            elif isinstance(error, str):
                parsed_errors.append({"message": error})
        
        return parsed_errors
    
    def _parse_field_errors(self, field_errors: Dict[str, Any]) -> Dict[str, str]:
        """Parse field-specific errors"""
        parsed_fields = {}
        
        for field, error in field_errors.items():
            if isinstance(error, dict):
                parsed_fields[field] = error.get("mensaje", error.get("message", str(error)))
            else:
                parsed_fields[field] = str(error)
        
        return parsed_fields
    
    def _extract_rejection_reason(self, response_data: Dict[str, Any]) -> Optional[str]:
        """Extract rejection reason from response"""
        # Try different possible fields for rejection reason
        reason_fields = [
            "motivoRechazo", "rejection_reason", "razon", "reason",
            "detalleRechazo", "rejection_details"
        ]
        
        for field in reason_fields:
            if field in response_data and response_data[field]:
                return response_data[field]
        
        # If no specific rejection reason, use general message
        return response_data.get("mensaje", response_data.get("message"))
    
    def _is_error_retryable(self, error_code: Optional[str], error_message: Optional[str]) -> bool:
        """Determine if error is retryable"""
        if not error_code and not error_message:
            return False
        
        # Non-retryable error codes (validation, business rules)
        non_retryable_codes = ["XSD-", "BUS-", "SIG-01", "SIG-02"]
        
        if error_code:
            for code_prefix in non_retryable_codes:
                if error_code.startswith(code_prefix):
                    return False
        
        # Non-retryable error messages
        if error_message:
            error_lower = error_message.lower()
            non_retryable_keywords = [
                "validation", "invalid format", "business rule",
                "signature", "certificate", "expired"
            ]
            
            for keyword in non_retryable_keywords:
                if keyword in error_lower:
                    return False
        
        # Retryable errors (network, system, temporary issues)
        retryable_codes = ["SYS-", "AUTH-", "TEMP-"]
        
        if error_code:
            for code_prefix in retryable_codes:
                if error_code.startswith(code_prefix):
                    return True
        
        # Default to retryable for unknown errors
        return True
    
    def _generate_error_suggestions(
        self,
        error_code: Optional[str],
        error_details: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate helpful suggestions based on error information"""
        suggestions = []
        
        if error_code:
            # Code-specific suggestions
            if error_code.startswith("XSD-"):
                suggestions.append("Check XML structure and required fields")
                suggestions.append("Validate against official XSD schema")
            elif error_code.startswith("BUS-"):
                suggestions.append("Review business rule validations")
                suggestions.append("Check CABYS codes and tax calculations")
            elif error_code.startswith("SIG-"):
                suggestions.append("Verify digital signature and certificate")
                suggestions.append("Check certificate expiration date")
            elif error_code.startswith("AUTH-"):
                suggestions.append("Check authentication credentials")
                suggestions.append("Verify API access permissions")
            elif error_code.startswith("SYS-"):
                suggestions.append("Retry the operation after a short delay")
                suggestions.append("Contact support if problem persists")
        
        # Field-specific suggestions
        for error in error_details:
            field = error.get("field")
            if field:
                if "cabys" in field.lower():
                    suggestions.append(f"Verify CABYS code format for field {field}")
                elif "identificacion" in field.lower():
                    suggestions.append(f"Check identification number format for field {field}")
                elif "fecha" in field.lower():
                    suggestions.append(f"Verify date format for field {field}")
        
        # Remove duplicates and return
        return list(set(suggestions))
    
    def get_error_description(self, error_code: str) -> str:
        """Get human-readable error description"""
        return self.error_codes.get(error_code, f"Unknown error code: {error_code}")
    
    def is_temporary_error(self, error_code: Optional[str], error_message: Optional[str]) -> bool:
        """Check if error is temporary and should be retried"""
        if error_code:
            temporary_codes = ["SYS-02", "AUTH-01", "TEMP-"]
            for code in temporary_codes:
                if error_code.startswith(code):
                    return True
        
        if error_message:
            temporary_keywords = [
                "service unavailable", "timeout", "connection",
                "rate limit", "temporary", "try again"
            ]
            error_lower = error_message.lower()
            for keyword in temporary_keywords:
                if keyword in error_lower:
                    return True
        
        return False