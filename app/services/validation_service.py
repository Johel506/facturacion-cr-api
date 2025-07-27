"""
Validation service for Costa Rica electronic documents.
Integrates XSD validation with document processing workflow.

Requirements: 3.2, 9.1, 11.1
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.schemas.enums import DocumentType
from app.utils.xsd_validator import XMLValidator, XSDValidationError, get_xml_validator


logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service for document validation and schema management.
    Handles the complete validation workflow for electronic documents.
    """
    
    def __init__(self, db: Session, schema_directory: str = None):
        self.db = db
        self.xml_validator = get_xml_validator(schema_directory)
    
    def validate_document_xml(
        self,
        document: Document,
        update_status: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a document's XML against XSD schema.
        
        Args:
            document: Document to validate
            update_status: Whether to update document status based on validation
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Check if document has XML content
            if not document.xml_original:
                return {
                    'is_valid': False,
                    'document_id': str(document.id),
                    'errors': ['Document has no XML content to validate'],
                    'validation_time': None
                }
            
            # Validate XML
            result = self.xml_validator.validate_document_xml(
                xml_content=document.xml_original,
                document_type=document.tipo_documento,
                detailed_errors=True
            )
            
            # Add document context
            result['document_id'] = str(document.id)
            result['document_key'] = document.clave
            result['consecutive_number'] = document.numero_consecutivo
            
            # Update document status if requested
            if update_status:
                self._update_document_validation_status(document, result)
            
            # Log validation result
            if result['is_valid']:
                logger.info(f"Document {document.id} XML validation successful")
            else:
                logger.warning(
                    f"Document {document.id} XML validation failed: "
                    f"{len(result['errors'])} errors found"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating document {document.id}: {str(e)}")
            return {
                'is_valid': False,
                'document_id': str(document.id),
                'errors': [f'Validation error: {str(e)}'],
                'validation_time': None
            }
    
    def validate_xml_content(
        self,
        xml_content: str,
        document_type: DocumentType
    ) -> Dict[str, Any]:
        """
        Validate XML content without a document record.
        
        Args:
            xml_content: XML content to validate
            document_type: Document type for schema selection
            
        Returns:
            Dictionary with validation results
        """
        try:
            result = self.xml_validator.validate_document_xml(
                xml_content=xml_content,
                document_type=document_type,
                detailed_errors=True
            )
            
            logger.debug(f"XML content validation for {document_type.value}: {'passed' if result['is_valid'] else 'failed'}")
            return result
            
        except Exception as e:
            logger.error(f"Error validating XML content for {document_type.value}: {str(e)}")
            return {
                'is_valid': False,
                'document_type': document_type.value,
                'errors': [f'Validation error: {str(e)}'],
                'validation_time': None
            }
    
    def validate_multiple_documents(
        self,
        document_ids: List[str],
        tenant_id: Optional[str] = None,
        update_status: bool = True
    ) -> Dict[str, Any]:
        """
        Validate multiple documents in batch.
        
        Args:
            document_ids: List of document IDs to validate
            tenant_id: Optional tenant ID for filtering
            update_status: Whether to update document statuses
            
        Returns:
            Dictionary with batch validation results
        """
        results = {
            'total': len(document_ids),
            'valid': 0,
            'invalid': 0,
            'errors': 0,
            'results': [],
            'summary_by_type': {}
        }
        
        try:
            # Get documents
            query = self.db.query(Document).filter(Document.id.in_(document_ids))
            if tenant_id:
                query = query.filter(Document.tenant_id == tenant_id)
            
            documents = query.all()
            
            if len(documents) != len(document_ids):
                found_ids = [str(doc.id) for doc in documents]
                missing_ids = [doc_id for doc_id in document_ids if doc_id not in found_ids]
                logger.warning(f"Some documents not found: {missing_ids}")
            
            # Validate each document
            for document in documents:
                try:
                    result = self.validate_document_xml(document, update_status)
                    
                    if result['is_valid']:
                        results['valid'] += 1
                    else:
                        results['invalid'] += 1
                    
                    results['results'].append({
                        'document_id': str(document.id),
                        'document_type': document.tipo_documento.value,
                        'clave': document.clave,
                        'is_valid': result['is_valid'],
                        'error_count': len(result.get('errors', [])),
                        'validation_time': result.get('validation_time')
                    })
                    
                    # Update summary by type
                    doc_type = document.tipo_documento.value
                    if doc_type not in results['summary_by_type']:
                        results['summary_by_type'][doc_type] = {'valid': 0, 'invalid': 0}
                    
                    if result['is_valid']:
                        results['summary_by_type'][doc_type]['valid'] += 1
                    else:
                        results['summary_by_type'][doc_type]['invalid'] += 1
                    
                except Exception as e:
                    results['errors'] += 1
                    results['results'].append({
                        'document_id': str(document.id),
                        'document_type': document.tipo_documento.value,
                        'clave': document.clave,
                        'is_valid': False,
                        'error': str(e)
                    })
            
            logger.info(
                f"Batch validation completed. "
                f"Valid: {results['valid']}, Invalid: {results['invalid']}, Errors: {results['errors']}"
            )
            
        except Exception as e:
            logger.error(f"Error in batch validation: {str(e)}")
            results['errors'] = len(document_ids)
            results['batch_error'] = str(e)
        
        return results
    
    def get_schema_information(self) -> Dict[str, Any]:
        """
        Get information about available schemas.
        
        Returns:
            Dictionary with schema information
        """
        try:
            schema_info = {
                'schema_version': self.xml_validator.schema_manager.SCHEMA_VERSION,
                'schema_directory': str(self.xml_validator.schema_manager.schema_directory),
                'available_schemas': {},
                'cache_stats': self.xml_validator.schema_manager.get_cache_stats()
            }
            
            # Get info for each document type
            for document_type in DocumentType:
                schema_info['available_schemas'][document_type.value] = \
                    self.xml_validator.schema_manager.get_schema_info(document_type)
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Error getting schema information: {str(e)}")
            return {
                'error': str(e),
                'schema_version': None,
                'available_schemas': {}
            }
    
    def preload_schemas(self) -> Dict[str, Any]:
        """
        Preload all schemas for better performance.
        
        Returns:
            Dictionary with preloading results
        """
        try:
            results = self.xml_validator.schema_manager.preload_all_schemas()
            logger.info(f"Schema preloading: {results['loaded']} loaded, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error preloading schemas: {str(e)}")
            return {
                'loaded': 0,
                'failed': 0,
                'errors': [str(e)]
            }
    
    def validate_document_before_signing(
        self,
        document: Document
    ) -> Tuple[bool, List[str]]:
        """
        Validate document before signing (pre-signing validation).
        
        Args:
            document: Document to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            if not document.xml_original:
                return False, ["Document has no XML content"]
            
            # Validate XML structure
            is_valid, errors = self.xml_validator.schema_manager.validate_xml(
                document.xml_original,
                document.tipo_documento,
                use_cache=False  # Don't use cache for pre-signing validation
            )
            
            if is_valid:
                logger.info(f"Pre-signing validation passed for document {document.id}")
            else:
                logger.warning(f"Pre-signing validation failed for document {document.id}: {errors}")
            
            return is_valid, errors
            
        except Exception as e:
            error_msg = f"Pre-signing validation error: {str(e)}"
            logger.error(f"Document {document.id}: {error_msg}")
            return False, [error_msg]
    
    def validate_signed_document(
        self,
        document: Document
    ) -> Dict[str, Any]:
        """
        Validate signed document (post-signing validation).
        
        Args:
            document: Document with signed XML
            
        Returns:
            Dictionary with validation results
        """
        try:
            if not document.xml_firmado:
                return {
                    'is_valid': False,
                    'errors': ['Document has no signed XML content'],
                    'document_id': str(document.id)
                }
            
            # Validate signed XML structure
            # Note: This validates the XML structure, not the signature itself
            result = self.xml_validator.validate_document_xml(
                xml_content=document.xml_firmado,
                document_type=document.tipo_documento,
                detailed_errors=True
            )
            
            result['document_id'] = str(document.id)
            result['validation_type'] = 'post_signing'
            
            if result['is_valid']:
                logger.info(f"Post-signing validation passed for document {document.id}")
            else:
                logger.warning(f"Post-signing validation failed for document {document.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Post-signing validation error for document {document.id}: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f'Post-signing validation error: {str(e)}'],
                'document_id': str(document.id),
                'validation_type': 'post_signing'
            }
    
    def get_validation_statistics(
        self,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get validation statistics for documents.
        
        Args:
            tenant_id: Optional tenant ID for filtering
            days: Number of days to look back
            
        Returns:
            Dictionary with validation statistics
        """
        try:
            from datetime import timedelta
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Build query
            query = self.db.query(Document).filter(
                Document.created_at >= start_date,
                Document.created_at <= end_date
            )
            
            if tenant_id:
                query = query.filter(Document.tenant_id == tenant_id)
            
            documents = query.all()
            
            # Calculate statistics
            stats = {
                'total_documents': len(documents),
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'by_type': {},
                'validation_summary': {
                    'with_xml': 0,
                    'without_xml': 0,
                    'signed': 0,
                    'unsigned': 0
                }
            }
            
            # Analyze documents
            for document in documents:
                doc_type = document.tipo_documento.value
                
                if doc_type not in stats['by_type']:
                    stats['by_type'][doc_type] = {
                        'count': 0,
                        'with_xml': 0,
                        'signed': 0
                    }
                
                stats['by_type'][doc_type]['count'] += 1
                
                if document.xml_original:
                    stats['validation_summary']['with_xml'] += 1
                    stats['by_type'][doc_type]['with_xml'] += 1
                else:
                    stats['validation_summary']['without_xml'] += 1
                
                if document.xml_firmado:
                    stats['validation_summary']['signed'] += 1
                    stats['by_type'][doc_type]['signed'] += 1
                else:
                    stats['validation_summary']['unsigned'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting validation statistics: {str(e)}")
            return {
                'error': str(e),
                'total_documents': 0
            }
    
    def _update_document_validation_status(
        self,
        document: Document,
        validation_result: Dict[str, Any]
    ) -> None:
        """
        Update document status based on validation result.
        
        Args:
            document: Document to update
            validation_result: Validation result dictionary
        """
        try:
            # Only update if validation failed
            if not validation_result['is_valid']:
                # You might want to add a validation status field to the Document model
                # For now, we'll just log the validation failure
                logger.info(f"Document {document.id} validation failed, status not updated")
            
            # In a full implementation, you might:
            # - Add a validation_status field to Document model
            # - Store validation errors in a separate table
            # - Update document workflow status
            
        except Exception as e:
            logger.error(f"Error updating document validation status: {str(e)}")


def get_validation_service(db: Session = None, schema_directory: str = None) -> ValidationService:
    """Get validation service instance with database session."""
    if db is None:
        db = next(get_db())
    return ValidationService(db, schema_directory)