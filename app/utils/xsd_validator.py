"""
XSD schema validation for Costa Rica electronic documents.
Validates XML against official Ministry XSD schemas (v4.4).

Requirements: 3.2, 9.1, 11.1
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from xml.etree.ElementTree import fromstring, ParseError
import xmlschema
from xmlschema import XMLSchema
from xmlschema.exceptions import XMLSchemaException

from app.schemas.enums import DocumentType


logger = logging.getLogger(__name__)


class XSDValidationError(Exception):
    """Custom exception for XSD validation errors."""
    pass


class XSDSchemaManager:
    """
    Manager for XSD schemas with caching and validation.
    Handles loading and caching of official Ministry XSD schemas.
    """
    
    # Document type to XSD file mapping
    SCHEMA_FILES = {
        DocumentType.FACTURA_ELECTRONICA: "FacturaElectronica_V4.4.xsd",
        DocumentType.NOTA_DEBITO_ELECTRONICA: "NotaDebitoElectronica_V4.4.xsd",
        DocumentType.NOTA_CREDITO_ELECTRONICA: "NotaCreditoElectronica_V4.4.xsd",
        DocumentType.TIQUETE_ELECTRONICO: "TiqueteElectronico_V4.4.xsd",
        DocumentType.FACTURA_EXPORTACION: "FacturaElectronicaExportacion_V4.4.xsd",
        DocumentType.FACTURA_COMPRA: "FacturaElectronicaCompra_V4.4.xsd",
        DocumentType.RECIBO_PAGO: "ReciboElectronicoPago_V4.4.xsd"
    }
    
    # Schema version
    SCHEMA_VERSION = "4.4"
    
    def __init__(self, schema_directory: str = None):
        """
        Initialize schema manager.
        
        Args:
            schema_directory: Directory containing XSD files (defaults to project directory)
        """
        if schema_directory is None:
            # Default to the project's schema directory
            project_root = Path(__file__).parent.parent.parent
            schema_directory = project_root / "Estructuras XML y Anexos Version 4.4"
        
        self.schema_directory = Path(schema_directory)
        self._schema_cache: Dict[DocumentType, XMLSchema] = {}
        self._validation_cache: Dict[str, bool] = {}
        
        # Verify schema directory exists
        if not self.schema_directory.exists():
            raise XSDValidationError(f"Schema directory not found: {self.schema_directory}")
        
        logger.info(f"XSD Schema Manager initialized with directory: {self.schema_directory}")
    
    def get_schema(self, document_type: DocumentType) -> XMLSchema:
        """
        Get XSD schema for document type with caching.
        
        Args:
            document_type: Document type enum
            
        Returns:
            XMLSchema instance
            
        Raises:
            XSDValidationError: If schema loading fails
        """
        # Check cache first
        if document_type in self._schema_cache:
            return self._schema_cache[document_type]
        
        # Get schema file name
        schema_file = self.SCHEMA_FILES.get(document_type)
        if not schema_file:
            raise XSDValidationError(f"No schema file defined for document type: {document_type}")
        
        # Build full path
        schema_path = self.schema_directory / schema_file
        
        if not schema_path.exists():
            raise XSDValidationError(f"Schema file not found: {schema_path}")
        
        try:
            # Load schema
            logger.info(f"Loading XSD schema: {schema_path}")
            schema = XMLSchema(str(schema_path))
            
            # Cache schema
            self._schema_cache[document_type] = schema
            
            logger.info(f"Successfully loaded schema for {document_type.value}")
            return schema
            
        except XMLSchemaException as e:
            raise XSDValidationError(f"Failed to load schema {schema_file}: {str(e)}") from e
        except Exception as e:
            raise XSDValidationError(f"Unexpected error loading schema {schema_file}: {str(e)}") from e
    
    def validate_xml(
        self, 
        xml_content: str, 
        document_type: DocumentType,
        use_cache: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate XML against XSD schema.
        
        Args:
            xml_content: XML content to validate
            document_type: Document type for schema selection
            use_cache: Whether to use validation cache
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            # Generate cache key
            cache_key = None
            if use_cache:
                import hashlib
                cache_key = f"{document_type.value}:{hashlib.md5(xml_content.encode()).hexdigest()}"
                
                # Check cache
                if cache_key in self._validation_cache:
                    cached_result = self._validation_cache[cache_key]
                    return cached_result, [] if cached_result else ["Cached validation failure"]
            
            # Get schema
            schema = self.get_schema(document_type)
            
            # Parse XML
            try:
                xml_doc = fromstring(xml_content)
            except ParseError as e:
                error_msg = f"XML parsing error: {str(e)}"
                logger.warning(error_msg)
                return False, [error_msg]
            
            # Validate against schema
            try:
                schema.validate(xml_doc)
                
                # Cache successful validation
                if cache_key:
                    self._validation_cache[cache_key] = True
                
                logger.debug(f"XML validation successful for document type {document_type.value}")
                return True, []
                
            except XMLSchemaException as e:
                error_messages = self._parse_validation_errors(e)
                
                # Cache failed validation
                if cache_key:
                    self._validation_cache[cache_key] = False
                
                logger.warning(f"XML validation failed for document type {document_type.value}: {error_messages}")
                return False, error_messages
            
        except XSDValidationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]
    
    def _parse_validation_errors(self, exception: XMLSchemaException) -> List[str]:
        """
        Parse validation errors from XMLSchemaException.
        
        Args:
            exception: XMLSchemaException with validation errors
            
        Returns:
            List of formatted error messages
        """
        error_messages = []
        
        # Handle single error
        if hasattr(exception, 'message') and exception.message:
            error_messages.append(exception.message)
        elif str(exception):
            error_messages.append(str(exception))
        
        # Handle multiple errors if available
        if hasattr(exception, 'errors') and exception.errors:
            for error in exception.errors:
                if hasattr(error, 'message') and error.message:
                    error_messages.append(error.message)
                else:
                    error_messages.append(str(error))
        
        # If no specific errors found, use the exception string
        if not error_messages:
            error_messages.append(str(exception))
        
        return error_messages
    
    def get_schema_info(self, document_type: DocumentType) -> Dict[str, Any]:
        """
        Get information about a schema.
        
        Args:
            document_type: Document type
            
        Returns:
            Dictionary with schema information
        """
        try:
            schema = self.get_schema(document_type)
            schema_file = self.SCHEMA_FILES.get(document_type)
            schema_path = self.schema_directory / schema_file
            
            return {
                'document_type': document_type.value,
                'schema_file': schema_file,
                'schema_path': str(schema_path),
                'schema_version': self.SCHEMA_VERSION,
                'target_namespace': schema.target_namespace,
                'is_loaded': True,
                'file_exists': schema_path.exists(),
                'file_size': schema_path.stat().st_size if schema_path.exists() else 0
            }
            
        except Exception as e:
            return {
                'document_type': document_type.value,
                'schema_file': self.SCHEMA_FILES.get(document_type),
                'error': str(e),
                'is_loaded': False,
                'file_exists': False
            }
    
    def preload_all_schemas(self) -> Dict[str, Any]:
        """
        Preload all schemas for performance.
        
        Returns:
            Dictionary with loading results
        """
        results = {
            'loaded': 0,
            'failed': 0,
            'errors': [],
            'schemas': {}
        }
        
        for document_type in DocumentType:
            try:
                schema_info = self.get_schema_info(document_type)
                if schema_info.get('is_loaded'):
                    results['loaded'] += 1
                    results['schemas'][document_type.value] = schema_info
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{document_type.value}: {schema_info.get('error', 'Unknown error')}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{document_type.value}: {str(e)}")
        
        logger.info(f"Schema preloading completed. Loaded: {results['loaded']}, Failed: {results['failed']}")
        return results
    
    def clear_cache(self) -> None:
        """Clear schema and validation caches."""
        self._schema_cache.clear()
        self._validation_cache.clear()
        logger.info("Schema caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'schema_cache_size': len(self._schema_cache),
            'validation_cache_size': len(self._validation_cache),
            'cached_document_types': [dt.value for dt in self._schema_cache.keys()]
        }


class XMLValidator:
    """
    High-level XML validator with detailed error reporting.
    Provides convenient methods for validating XML documents.
    """
    
    def __init__(self, schema_directory: str = None):
        """
        Initialize XML validator.
        
        Args:
            schema_directory: Directory containing XSD files
        """
        self.schema_manager = XSDSchemaManager(schema_directory)
    
    def validate_document_xml(
        self,
        xml_content: str,
        document_type: DocumentType,
        detailed_errors: bool = True
    ) -> Dict[str, Any]:
        """
        Validate document XML with detailed results.
        
        Args:
            xml_content: XML content to validate
            document_type: Document type for schema selection
            detailed_errors: Whether to include detailed error information
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'is_valid': False,
            'document_type': document_type.value,
            'schema_version': XSDSchemaManager.SCHEMA_VERSION,
            'errors': [],
            'warnings': [],
            'validation_time': None,
            'xml_size': len(xml_content.encode('utf-8'))
        }
        
        try:
            import time
            start_time = time.time()
            
            # Validate XML
            is_valid, error_messages = self.schema_manager.validate_xml(
                xml_content, document_type
            )
            
            result['validation_time'] = time.time() - start_time
            result['is_valid'] = is_valid
            result['errors'] = error_messages
            
            # Add detailed error information if requested
            if detailed_errors and error_messages:
                result['error_details'] = self._analyze_errors(error_messages, xml_content)
            
            # Add warnings for common issues
            warnings = self._check_common_issues(xml_content, document_type)
            result['warnings'] = warnings
            
        except XSDValidationError as e:
            result['errors'] = [f"Schema validation error: {str(e)}"]
        except Exception as e:
            result['errors'] = [f"Unexpected validation error: {str(e)}"]
        
        return result
    
    def _analyze_errors(self, error_messages: List[str], xml_content: str) -> List[Dict[str, Any]]:
        """
        Analyze validation errors to provide more context.
        
        Args:
            error_messages: List of error messages
            xml_content: Original XML content
            
        Returns:
            List of detailed error information
        """
        detailed_errors = []
        
        for error_msg in error_messages:
            error_detail = {
                'message': error_msg,
                'type': 'validation_error',
                'suggestions': []
            }
            
            # Analyze common error patterns and provide suggestions
            if 'required' in error_msg.lower():
                error_detail['type'] = 'missing_required_field'
                error_detail['suggestions'].append("Check that all required fields are present")
            
            elif 'invalid' in error_msg.lower() or 'not valid' in error_msg.lower():
                error_detail['type'] = 'invalid_value'
                error_detail['suggestions'].append("Verify the field value format and constraints")
            
            elif 'namespace' in error_msg.lower():
                error_detail['type'] = 'namespace_error'
                error_detail['suggestions'].append("Check XML namespace declarations")
            
            elif 'element' in error_msg.lower():
                error_detail['type'] = 'element_error'
                error_detail['suggestions'].append("Verify element structure and ordering")
            
            detailed_errors.append(error_detail)
        
        return detailed_errors
    
    def _check_common_issues(self, xml_content: str, document_type: DocumentType) -> List[str]:
        """
        Check for common issues that might not be schema violations.
        
        Args:
            xml_content: XML content
            document_type: Document type
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        try:
            # Check for common formatting issues
            if '\t' in xml_content:
                warnings.append("XML contains tab characters, consider using spaces for indentation")
            
            # Check for very large XML
            if len(xml_content) > 1024 * 1024:  # 1MB
                warnings.append("XML is very large (>1MB), consider optimizing")
            
            # Check for missing encoding declaration
            if '<?xml' not in xml_content[:100]:
                warnings.append("XML declaration is missing or not at the beginning")
            
            # Check for potential character encoding issues
            try:
                xml_content.encode('utf-8')
            except UnicodeEncodeError:
                warnings.append("XML contains characters that cannot be encoded as UTF-8")
            
        except Exception:
            # Don't fail validation due to warning checks
            pass
        
        return warnings
    
    def validate_multiple_documents(
        self,
        documents: List[Tuple[str, DocumentType]]
    ) -> Dict[str, Any]:
        """
        Validate multiple documents in batch.
        
        Args:
            documents: List of (xml_content, document_type) tuples
            
        Returns:
            Dictionary with batch validation results
        """
        results = {
            'total': len(documents),
            'valid': 0,
            'invalid': 0,
            'errors': 0,
            'results': [],
            'summary': {}
        }
        
        for i, (xml_content, document_type) in enumerate(documents):
            try:
                result = self.validate_document_xml(xml_content, document_type, detailed_errors=False)
                
                if result['is_valid']:
                    results['valid'] += 1
                else:
                    results['invalid'] += 1
                
                results['results'].append({
                    'index': i,
                    'document_type': document_type.value,
                    'is_valid': result['is_valid'],
                    'error_count': len(result['errors']),
                    'validation_time': result['validation_time']
                })
                
            except Exception as e:
                results['errors'] += 1
                results['results'].append({
                    'index': i,
                    'document_type': document_type.value if document_type else 'unknown',
                    'is_valid': False,
                    'error': str(e)
                })
        
        # Generate summary by document type
        for result in results['results']:
            doc_type = result['document_type']
            if doc_type not in results['summary']:
                results['summary'][doc_type] = {'valid': 0, 'invalid': 0, 'errors': 0}
            
            if result.get('error'):
                results['summary'][doc_type]['errors'] += 1
            elif result['is_valid']:
                results['summary'][doc_type]['valid'] += 1
            else:
                results['summary'][doc_type]['invalid'] += 1
        
        return results


# Global validator instance
_global_validator: Optional[XMLValidator] = None


def get_xml_validator(schema_directory: str = None) -> XMLValidator:
    """
    Get global XML validator instance.
    
    Args:
        schema_directory: Directory containing XSD files
        
    Returns:
        XMLValidator instance
    """
    global _global_validator
    
    if _global_validator is None:
        _global_validator = XMLValidator(schema_directory)
    
    return _global_validator


# Convenience functions
def validate_xml(xml_content: str, document_type: DocumentType) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate XML.
    
    Args:
        xml_content: XML content to validate
        document_type: Document type for schema selection
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = get_xml_validator()
    return validator.schema_manager.validate_xml(xml_content, document_type)


def validate_xml_detailed(xml_content: str, document_type: DocumentType) -> Dict[str, Any]:
    """
    Convenience function to validate XML with detailed results.
    
    Args:
        xml_content: XML content to validate
        document_type: Document type for schema selection
        
    Returns:
        Dictionary with detailed validation results
    """
    validator = get_xml_validator()
    return validator.validate_document_xml(xml_content, document_type)