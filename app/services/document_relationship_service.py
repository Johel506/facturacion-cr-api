"""
Document relationship management service for Costa Rica electronic documents.
Handles document references, corrections, cancellations, and relationship tracking.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import IntegrityError

from app.models.document import Document, DocumentType, DocumentStatus
from app.models.document_reference import DocumentReference
from app.models.tenant import Tenant
from app.schemas.documents import DocumentReference as DocumentReferenceSchema
from app.schemas.enums import DocumentReferenceType, ReferenceCode
from app.services.document_service import DocumentService
from app.utils.validators import validate_document_key


class DocumentRelationshipService:
    """
    Document relationship management service
    
    Handles document references, corrections, cancellations, substitutions,
    and relationship tracking for all document types.
    
    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.document_service = DocumentService(db)
    
    def create_document_reference(
        self,
        document_id: UUID,
        tenant_id: UUID,
        reference_data: DocumentReferenceSchema,
        created_by: Optional[str] = None
    ) -> DocumentReference:
        """
        Create document reference with validation
        
        Args:
            document_id: Document UUID that contains the reference
            tenant_id: Tenant UUID for isolation
            reference_data: Reference data
            created_by: User who created the reference
            
        Returns:
            Created document reference
            
        Raises:
            ValueError: If validation fails
            
        Requirements: 15.1 - document reference creation and validation
        """
        # Validate document exists and belongs to tenant
        document = self.document_service.get_document(document_id, tenant_id, include_details=False)
        if not document:
            raise ValueError("Document not found")
        
        # Validate reference data
        self._validate_reference_data(reference_data, document.tipo_documento)
        
        # Validate referenced document exists if key is provided
        if reference_data.numero and validate_document_key(reference_data.numero):
            referenced_doc = self._get_referenced_document(reference_data.numero, tenant_id)
            if not referenced_doc:
                raise ValueError(f"Referenced document not found: {reference_data.numero}")
        
        # Create reference instance
        reference = DocumentReference(
            documento_id=document_id,
            tipo_documento_referencia=reference_data.tipo_documento,
            tipo_documento_otro=reference_data.tipo_documento_otro,
            numero_referencia=reference_data.numero,
            fecha_emision_referencia=reference_data.fecha_emision,
            codigo_referencia=reference_data.codigo,
            codigo_referencia_otro=reference_data.codigo_referencia_otro,
            razon=reference_data.razon,
            created_at=datetime.now(timezone.utc),
            created_by=created_by
        )
        
        try:
            self.db.add(reference)
            self.db.commit()
            self.db.refresh(reference)
            
            # Log reference creation
            self._log_relationship_activity(document_id, "reference_created", {
                "reference_type": reference_data.tipo_documento,
                "reference_number": reference_data.numero,
                "created_by": created_by
            })
            
            return reference
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Failed to create document reference: {str(e)}")
    
    def create_correction_workflow(
        self,
        original_document_id: UUID,
        tenant_id: UUID,
        correction_reason: str,
        corrected_by: Optional[str] = None
    ) -> Document:
        """
        Create document correction workflow
        
        Args:
            original_document_id: Original document UUID
            tenant_id: Tenant UUID
            correction_reason: Reason for correction
            corrected_by: User who initiated correction
            
        Returns:
            Original document marked for correction
            
        Requirements: 15.2 - document correction workflows
        """
        # Get original document
        original_doc = self.document_service.get_document(
            original_document_id, tenant_id, include_details=False
        )
        if not original_doc:
            raise ValueError("Original document not found")
        
        # Validate document can be corrected
        if not self._can_document_be_corrected(original_doc):
            raise ValueError(f"Document cannot be corrected in current state: {original_doc.estado}")
        
        # Mark original document as requiring correction
        original_doc.estado = DocumentStatus.ERROR
        original_doc.mensaje_hacienda = f"Correction required: {correction_reason}"
        original_doc.updated_at = datetime.now(timezone.utc)
        original_doc.updated_by = corrected_by
        
        self.db.commit()
        self.db.refresh(original_doc)
        
        # Log correction workflow
        self._log_relationship_activity(original_document_id, "correction_initiated", {
            "reason": correction_reason,
            "corrected_by": corrected_by
        })
        
        return original_doc
    
    def create_cancellation_workflow(
        self,
        document_id: UUID,
        tenant_id: UUID,
        cancellation_reason: str,
        cancelled_by: Optional[str] = None
    ) -> Document:
        """
        Create document cancellation workflow
        
        Args:
            document_id: Document UUID to cancel
            tenant_id: Tenant UUID
            cancellation_reason: Reason for cancellation
            cancelled_by: User who initiated cancellation
            
        Returns:
            Cancelled document
            
        Requirements: 15.2 - document cancellation workflows
        """
        # Get document
        document = self.document_service.get_document(document_id, tenant_id, include_details=False)
        if not document:
            raise ValueError("Document not found")
        
        # Validate document can be cancelled
        if not self._can_document_be_cancelled(document):
            raise ValueError(f"Document cannot be cancelled in current state: {document.estado}")
        
        # Cancel document
        document.estado = DocumentStatus.CANCELADO
        document.mensaje_hacienda = f"Cancelled: {cancellation_reason}"
        document.updated_at = datetime.now(timezone.utc)
        document.updated_by = cancelled_by
        
        self.db.commit()
        self.db.refresh(document)
        
        # Log cancellation
        self._log_relationship_activity(document_id, "document_cancelled", {
            "reason": cancellation_reason,
            "cancelled_by": cancelled_by
        })
        
        return document
    
    def track_credit_debit_note_relationship(
        self,
        note_document_id: UUID,
        original_document_key: str,
        tenant_id: UUID,
        relationship_type: str = "reference"
    ) -> bool:
        """
        Track credit/debit note relationship to original document
        
        Args:
            note_document_id: Credit/debit note document UUID
            original_document_key: Original document key
            tenant_id: Tenant UUID
            relationship_type: Type of relationship
            
        Returns:
            True if relationship tracked successfully
            
        Requirements: 15.2 - credit/debit note relationship tracking
        """
        # Get note document
        note_doc = self.document_service.get_document(note_document_id, tenant_id, include_details=False)
        if not note_doc:
            raise ValueError("Note document not found")
        
        # Validate document type
        if note_doc.tipo_documento not in [DocumentType.NOTA_CREDITO_ELECTRONICA, DocumentType.NOTA_DEBITO_ELECTRONICA]:
            raise ValueError("Document must be a credit or debit note")
        
        # Get original document
        original_doc = self._get_referenced_document(original_document_key, tenant_id)
        if not original_doc:
            raise ValueError(f"Original document not found: {original_document_key}")
        
        # Validate original document type
        if original_doc.tipo_documento not in [DocumentType.FACTURA_ELECTRONICA, DocumentType.TIQUETE_ELECTRONICO]:
            raise ValueError("Original document must be an invoice or ticket")
        
        # Create reference
        reference_data = DocumentReferenceSchema(
            tipo_documento=DocumentReferenceType.ELECTRONIC_INVOICE if original_doc.tipo_documento == DocumentType.FACTURA_ELECTRONICA else DocumentReferenceType.ELECTRONIC_TICKET,
            numero=original_document_key,
            fecha_emision=original_doc.fecha_emision,
            codigo=ReferenceCode.REFERENCE_OTHER_DOCUMENT,
            razon=f"{note_doc.get_document_type_name()} for {original_doc.get_document_type_name()}"
        )
        
        self.create_document_reference(
            document_id=note_document_id,
            tenant_id=tenant_id,
            reference_data=reference_data,
            created_by=f"system:relationship_tracking"
        )
        
        return True
    
    def create_substitution_workflow(
        self,
        original_document_id: UUID,
        substitute_document_id: UUID,
        tenant_id: UUID,
        substitution_reason: str,
        substituted_by: Optional[str] = None
    ) -> Tuple[Document, Document]:
        """
        Create document substitution and replacement workflow
        
        Args:
            original_document_id: Original document UUID
            substitute_document_id: Substitute document UUID
            tenant_id: Tenant UUID
            substitution_reason: Reason for substitution
            substituted_by: User who initiated substitution
            
        Returns:
            Tuple of (original_document, substitute_document)
            
        Requirements: 15.3 - document substitution and replacement functionality
        """
        # Get both documents
        original_doc = self.document_service.get_document(
            original_document_id, tenant_id, include_details=False
        )
        substitute_doc = self.document_service.get_document(
            substitute_document_id, tenant_id, include_details=False
        )
        
        if not original_doc:
            raise ValueError("Original document not found")
        if not substitute_doc:
            raise ValueError("Substitute document not found")
        
        # Validate substitution is allowed
        if not self._can_document_be_substituted(original_doc):
            raise ValueError(f"Original document cannot be substituted: {original_doc.estado}")
        
        if substitute_doc.estado != DocumentStatus.BORRADOR:
            raise ValueError("Substitute document must be in draft state")
        
        # Mark original as substituted
        original_doc.estado = DocumentStatus.CANCELADO
        original_doc.mensaje_hacienda = f"Substituted: {substitution_reason}"
        original_doc.updated_at = datetime.now(timezone.utc)
        original_doc.updated_by = substituted_by
        
        # Create reference from substitute to original
        reference_data = DocumentReferenceSchema(
            tipo_documento=self._get_reference_type_for_document(original_doc.tipo_documento),
            numero=original_doc.clave,
            fecha_emision=original_doc.fecha_emision,
            codigo=ReferenceCode.SUBSTITUTE_ELECTRONIC_VOUCHER,
            razon=f"Substitute for {original_doc.numero_consecutivo}: {substitution_reason}"
        )
        
        self.create_document_reference(
            document_id=substitute_document_id,
            tenant_id=tenant_id,
            reference_data=reference_data,
            created_by=substituted_by
        )
        
        self.db.commit()
        self.db.refresh(original_doc)
        self.db.refresh(substitute_doc)
        
        # Log substitution
        self._log_relationship_activity(original_document_id, "document_substituted", {
            "substitute_document_id": str(substitute_document_id),
            "reason": substitution_reason,
            "substituted_by": substituted_by
        })
        
        return original_doc, substitute_doc
    
    def validate_document_chain(
        self,
        document_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate document chain and integrity checking
        
        Args:
            document_id: Document UUID to validate
            tenant_id: Tenant UUID
            
        Returns:
            Validation result with chain information
            
        Requirements: 15.5 - document chain validation and integrity checking
        """
        # Get document with references
        document = self.document_service.get_document(document_id, tenant_id, include_details=True)
        if not document:
            raise ValueError("Document not found")
        
        validation_result = {
            "document_id": str(document_id),
            "document_type": document.tipo_documento.value,
            "status": document.estado.value,
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "chain_info": {
                "references_count": len(document.referencias) if document.referencias else 0,
                "referenced_by_count": 0,
                "chain_depth": 0
            }
        }
        
        # Validate references
        if document.referencias:
            for ref in document.referencias:
                ref_validation = self._validate_single_reference(ref, tenant_id)
                if not ref_validation["is_valid"]:
                    validation_result["errors"].extend(ref_validation["errors"])
                    validation_result["is_valid"] = False
        
        # Check if document is referenced by others
        referencing_docs = self._get_documents_referencing(document.clave, tenant_id)
        validation_result["chain_info"]["referenced_by_count"] = len(referencing_docs)
        
        # Calculate chain depth
        validation_result["chain_info"]["chain_depth"] = self._calculate_chain_depth(document, tenant_id)
        
        # Validate business rules for document type
        type_validation = self._validate_document_type_rules(document)
        if not type_validation["is_valid"]:
            validation_result["errors"].extend(type_validation["errors"])
            validation_result["is_valid"] = False
        
        return validation_result
    
    def get_document_relationships(
        self,
        document_id: UUID,
        tenant_id: UUID,
        include_chain: bool = True
    ) -> Dict[str, Any]:
        """
        Get complete document relationship information
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            include_chain: Whether to include full relationship chain
            
        Returns:
            Complete relationship information
        """
        document = self.document_service.get_document(document_id, tenant_id, include_details=True)
        if not document:
            raise ValueError("Document not found")
        
        relationships = {
            "document": {
                "id": str(document.id),
                "type": document.tipo_documento.value,
                "consecutive": document.numero_consecutivo,
                "key": document.clave,
                "status": document.estado.value
            },
            "references": [],
            "referenced_by": [],
            "chain_summary": {
                "total_references": 0,
                "total_referenced_by": 0,
                "chain_depth": 0
            }
        }
        
        # Get direct references
        if document.referencias:
            for ref in document.referencias:
                ref_info = {
                    "type": ref.tipo_documento_referencia.value if ref.tipo_documento_referencia else None,
                    "number": ref.numero_referencia,
                    "date": ref.fecha_emision_referencia.isoformat() if ref.fecha_emision_referencia else None,
                    "code": ref.codigo_referencia.value if ref.codigo_referencia else None,
                    "reason": ref.razon
                }
                
                # Get referenced document details if available
                if ref.numero_referencia and validate_document_key(ref.numero_referencia):
                    referenced_doc = self._get_referenced_document(ref.numero_referencia, tenant_id)
                    if referenced_doc:
                        ref_info["referenced_document"] = {
                            "id": str(referenced_doc.id),
                            "type": referenced_doc.tipo_documento.value,
                            "consecutive": referenced_doc.numero_consecutivo,
                            "status": referenced_doc.estado.value
                        }
                
                relationships["references"].append(ref_info)
        
        # Get documents that reference this one
        referencing_docs = self._get_documents_referencing(document.clave, tenant_id)
        for ref_doc in referencing_docs:
            relationships["referenced_by"].append({
                "id": str(ref_doc.id),
                "type": ref_doc.tipo_documento.value,
                "consecutive": ref_doc.numero_consecutivo,
                "key": ref_doc.clave,
                "status": ref_doc.estado.value
            })
        
        # Update summary
        relationships["chain_summary"]["total_references"] = len(relationships["references"])
        relationships["chain_summary"]["total_referenced_by"] = len(relationships["referenced_by"])
        
        if include_chain:
            relationships["chain_summary"]["chain_depth"] = self._calculate_chain_depth(document, tenant_id)
        
        return relationships
    
    # Private helper methods
    
    def _validate_reference_data(
        self,
        reference_data: DocumentReferenceSchema,
        document_type: DocumentType
    ) -> None:
        """Validate reference data based on document type and business rules"""
        # Credit and debit notes must have references
        if document_type in [DocumentType.NOTA_CREDITO_ELECTRONICA, DocumentType.NOTA_DEBITO_ELECTRONICA]:
            if not reference_data.numero:
                raise ValueError("Credit and debit notes must reference an original document")
        
        # Validate reference type compatibility
        if reference_data.tipo_documento == DocumentReferenceType.OTHERS and not reference_data.tipo_documento_otro:
            raise ValueError("tipo_documento_otro is required when tipo_documento is OTHERS")
        
        if reference_data.codigo == ReferenceCode.OTHERS and not reference_data.codigo_referencia_otro:
            raise ValueError("codigo_referencia_otro is required when codigo is OTHERS")
        
        # Validate date is not in future
        if reference_data.fecha_emision > datetime.now(timezone.utc):
            raise ValueError("Reference emission date cannot be in the future")
    
    def _get_referenced_document(self, document_key: str, tenant_id: UUID) -> Optional[Document]:
        """Get referenced document by key"""
        return self.db.query(Document).filter(
            and_(
                Document.clave == document_key,
                Document.tenant_id == tenant_id
            )
        ).first()
    
    def _get_documents_referencing(self, document_key: str, tenant_id: UUID) -> List[Document]:
        """Get documents that reference the given document key"""
        return self.db.query(Document).join(DocumentReference).filter(
            and_(
                DocumentReference.numero_referencia == document_key,
                Document.tenant_id == tenant_id
            )
        ).all()
    
    def _can_document_be_corrected(self, document: Document) -> bool:
        """Check if document can be corrected"""
        return document.estado in [
            DocumentStatus.BORRADOR,
            DocumentStatus.RECHAZADO,
            DocumentStatus.ERROR
        ]
    
    def _can_document_be_cancelled(self, document: Document) -> bool:
        """Check if document can be cancelled"""
        return document.estado not in [
            DocumentStatus.CANCELADO
        ]
    
    def _can_document_be_substituted(self, document: Document) -> bool:
        """Check if document can be substituted"""
        return document.estado in [
            DocumentStatus.BORRADOR,
            DocumentStatus.RECHAZADO,
            DocumentStatus.ERROR
        ]
    
    def _get_reference_type_for_document(self, document_type: DocumentType) -> DocumentReferenceType:
        """Get appropriate reference type for document type"""
        type_mapping = {
            DocumentType.FACTURA_ELECTRONICA: DocumentReferenceType.ELECTRONIC_INVOICE,
            DocumentType.NOTA_DEBITO_ELECTRONICA: DocumentReferenceType.ELECTRONIC_DEBIT_NOTE,
            DocumentType.NOTA_CREDITO_ELECTRONICA: DocumentReferenceType.ELECTRONIC_CREDIT_NOTE,
            DocumentType.TIQUETE_ELECTRONICO: DocumentReferenceType.ELECTRONIC_TICKET,
            DocumentType.FACTURA_EXPORTACION: DocumentReferenceType.ELECTRONIC_INVOICE,
            DocumentType.FACTURA_COMPRA: DocumentReferenceType.ELECTRONIC_INVOICE,
            DocumentType.RECIBO_PAGO: DocumentReferenceType.ELECTRONIC_INVOICE
        }
        return type_mapping.get(document_type, DocumentReferenceType.OTHERS)
    
    def _validate_single_reference(self, reference: DocumentReference, tenant_id: UUID) -> Dict[str, Any]:
        """Validate a single document reference"""
        validation = {
            "is_valid": True,
            "errors": []
        }
        
        # Check if referenced document exists
        if reference.numero_referencia and validate_document_key(reference.numero_referencia):
            referenced_doc = self._get_referenced_document(reference.numero_referencia, tenant_id)
            if not referenced_doc:
                validation["is_valid"] = False
                validation["errors"].append(f"Referenced document not found: {reference.numero_referencia}")
        
        return validation
    
    def _calculate_chain_depth(self, document: Document, tenant_id: UUID, visited: Optional[set] = None) -> int:
        """Calculate document chain depth (recursive)"""
        if visited is None:
            visited = set()
        
        if document.clave in visited:
            return 0  # Circular reference protection
        
        visited.add(document.clave)
        max_depth = 0
        
        # Check references
        if document.referencias:
            for ref in document.referencias:
                if ref.numero_referencia and validate_document_key(ref.numero_referencia):
                    referenced_doc = self._get_referenced_document(ref.numero_referencia, tenant_id)
                    if referenced_doc:
                        depth = 1 + self._calculate_chain_depth(referenced_doc, tenant_id, visited.copy())
                        max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _validate_document_type_rules(self, document: Document) -> Dict[str, Any]:
        """Validate document type specific business rules"""
        validation = {
            "is_valid": True,
            "errors": []
        }
        
        # Credit and debit notes must have references
        if document.tipo_documento in [DocumentType.NOTA_CREDITO_ELECTRONICA, DocumentType.NOTA_DEBITO_ELECTRONICA]:
            if not document.referencias or len(document.referencias) == 0:
                validation["is_valid"] = False
                validation["errors"].append(f"{document.get_document_type_name()} must have at least one reference")
        
        return validation
    
    def _log_relationship_activity(self, document_id: UUID, activity: str, details: Dict[str, Any]) -> None:
        """Log relationship activity for audit trail"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Document relationship activity: {activity}", extra={
            "document_id": str(document_id),
            "activity": activity,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# Convenience functions for dependency injection

def get_document_relationship_service(db: Session = None) -> DocumentRelationshipService:
    """Get document relationship service instance"""
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()
    return DocumentRelationshipService(db)