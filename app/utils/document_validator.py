"""
Document validation utilities for Costa Rica electronic documents.
Provides comprehensive validation for document integrity, relationships, and business rules.
"""
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from app.models.document import Document, DocumentType, DocumentStatus
from app.models.document_reference import DocumentReference
from app.schemas.documents import DocumentCreate, DocumentReference as DocumentReferenceSchema
from app.schemas.enums import DocumentReferenceType, ReferenceCode
from app.utils.validators import (
    validate_identification_number, validate_cabys_code,
    validate_consecutive_number, validate_document_key
)


class DocumentValidationError(Exception):
    """Custom exception for document validation errors"""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class DocumentValidator:
    """
    Comprehensive document validator
    
    Provides validation for document integrity, relationships,
    and Costa Rican business rules.
    """
    
    @staticmethod
    def validate_document_integrity(document: Document) -> Dict[str, Any]:
        """
        Validate document integrity and consistency
        
        Args:
            document: Document instance to validate
            
        Returns:
            Validation result dictionary
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate consecutive number format
        if not validate_consecutive_number(document.numero_consecutivo):
            result["is_valid"] = False
            result["errors"].append({
                "field": "numero_consecutivo",
                "message": "Invalid consecutive number format",
                "code": "INVALID_CONSECUTIVE_FORMAT"
            })
        
        # Validate document key format
        if not validate_document_key(document.clave):
            result["is_valid"] = False
            result["errors"].append({
                "field": "clave",
                "message": "Invalid document key format",
                "code": "INVALID_KEY_FORMAT"
            })
        
        # Validate document key components match consecutive number
        if document.numero_consecutivo and document.clave:
            key_validation = DocumentValidator._validate_key_consecutive_consistency(
                document.clave, document.numero_consecutivo
            )
            if not key_validation["is_valid"]:
                result["is_valid"] = False
                result["errors"].extend(key_validation["errors"])
        
        # Validate totals consistency
        totals_validation = DocumentValidator._validate_document_totals(document)
        if not totals_validation["is_valid"]:
            result["is_valid"] = False
            result["errors"].extend(totals_validation["errors"])
        
        # Validate identification numbers
        id_validation = DocumentValidator._validate_identification_numbers(document)
        if not id_validation["is_valid"]:
            result["is_valid"] = False
            result["errors"].extend(id_validation["errors"])
        
        # Validate business rules for document type
        business_validation = DocumentValidator._validate_document_type_business_rules(document)
        if not business_validation["is_valid"]:
            result["is_valid"] = False
            result["errors"].extend(business_validation["errors"])
        
        return result
    
    @staticmethod
    def validate_document_references(
        document: Document,
        references: List[DocumentReference]
    ) -> Dict[str, Any]:
        """
        Validate document references and relationships
        
        Args:
            document: Document that contains the references
            references: List of document references
            
        Returns:
            Validation result dictionary
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate references are required for certain document types
        if document.tipo_documento in [DocumentType.NOTA_CREDITO_ELECTRONICA, DocumentType.NOTA_DEBITO_ELECTRONICA]:
            if not references or len(references) == 0:
                result["is_valid"] = False
                result["errors"].append({
                    "field": "referencias",
                    "message": f"{document.get_document_type_name()} must have at least one reference",
                    "code": "REFERENCES_REQUIRED"
                })
        
        # Validate each reference
        for i, reference in enumerate(references):
            ref_validation = DocumentValidator._validate_single_reference(reference, document.tipo_documento)
            if not ref_validation["is_valid"]:
                result["is_valid"] = False
                for error in ref_validation["errors"]:
                    error["field"] = f"referencias[{i}].{error.get('field', 'unknown')}"
                    result["errors"].append(error)
        
        # Validate reference uniqueness
        if len(references) > 1:
            unique_validation = DocumentValidator._validate_reference_uniqueness(references)
            if not unique_validation["is_valid"]:
                result["is_valid"] = False
                result["errors"].extend(unique_validation["errors"])
        
        return result
    
    @staticmethod
    def validate_document_chain_integrity(
        document: Document,
        referenced_documents: Dict[str, Document]
    ) -> Dict[str, Any]:
        """
        Validate document chain integrity
        
        Args:
            document: Document to validate
            referenced_documents: Dictionary of referenced documents by key
            
        Returns:
            Validation result dictionary
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "chain_info": {
                "depth": 0,
                "circular_references": [],
                "broken_references": []
            }
        }
        
        # Check for circular references
        circular_check = DocumentValidator._check_circular_references(
            document, referenced_documents
        )
        if circular_check["has_circular"]:
            result["is_valid"] = False
            result["errors"].append({
                "field": "chain",
                "message": "Circular reference detected in document chain",
                "code": "CIRCULAR_REFERENCE"
            })
            result["chain_info"]["circular_references"] = circular_check["circular_path"]
        
        # Check for broken references
        if document.referencias:
            for reference in document.referencias:
                if reference.numero_referencia and validate_document_key(reference.numero_referencia):
                    if reference.numero_referencia not in referenced_documents:
                        result["warnings"].append({
                            "field": "referencias",
                            "message": f"Referenced document not found: {reference.numero_referencia}",
                            "code": "BROKEN_REFERENCE"
                        })
                        result["chain_info"]["broken_references"].append(reference.numero_referencia)
        
        # Calculate chain depth
        result["chain_info"]["depth"] = DocumentValidator._calculate_chain_depth(
            document, referenced_documents
        )
        
        return result
    
    @staticmethod
    def validate_document_status_transition(
        current_status: DocumentStatus,
        new_status: DocumentStatus,
        document_type: DocumentType
    ) -> Dict[str, Any]:
        """
        Validate document status transition is allowed
        
        Args:
            current_status: Current document status
            new_status: Desired new status
            document_type: Document type
            
        Returns:
            Validation result dictionary
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Define allowed transitions
        allowed_transitions = {
            DocumentStatus.BORRADOR: [
                DocumentStatus.PENDIENTE,
                DocumentStatus.ENVIADO,
                DocumentStatus.CANCELADO
            ],
            DocumentStatus.PENDIENTE: [
                DocumentStatus.ENVIADO,
                DocumentStatus.ERROR,
                DocumentStatus.CANCELADO
            ],
            DocumentStatus.ENVIADO: [
                DocumentStatus.PROCESANDO,
                DocumentStatus.ACEPTADO,
                DocumentStatus.RECHAZADO,
                DocumentStatus.ERROR
            ],
            DocumentStatus.PROCESANDO: [
                DocumentStatus.ACEPTADO,
                DocumentStatus.RECHAZADO,
                DocumentStatus.ERROR
            ],
            DocumentStatus.RECHAZADO: [
                DocumentStatus.BORRADOR,
                DocumentStatus.PENDIENTE,
                DocumentStatus.CANCELADO
            ],
            DocumentStatus.ERROR: [
                DocumentStatus.PENDIENTE,
                DocumentStatus.ENVIADO,
                DocumentStatus.CANCELADO
            ],
            DocumentStatus.ACEPTADO: [
                # Accepted documents generally cannot change status
                # except for special cases handled by Ministry
            ],
            DocumentStatus.CANCELADO: [
                # Cancelled documents generally cannot change status
            ]
        }
        
        # Check if transition is allowed
        if new_status not in allowed_transitions.get(current_status, []):
            result["is_valid"] = False
            result["errors"].append({
                "field": "estado",
                "message": f"Status transition from {current_status.value} to {new_status.value} is not allowed",
                "code": "INVALID_STATUS_TRANSITION"
            })
        
        return result
    
    @staticmethod
    def validate_document_business_rules(document_data: DocumentCreate) -> Dict[str, Any]:
        """
        Validate document against Costa Rican business rules
        
        Args:
            document_data: Document creation data
            
        Returns:
            Validation result dictionary
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate receptor requirements
        receptor_validation = DocumentValidator._validate_receptor_requirements(document_data)
        if not receptor_validation["is_valid"]:
            result["is_valid"] = False
            result["errors"].extend(receptor_validation["errors"])
        
        # Validate credit sale requirements
        credit_validation = DocumentValidator._validate_credit_sale_requirements(document_data)
        if not credit_validation["is_valid"]:
            result["is_valid"] = False
            result["errors"].extend(credit_validation["errors"])
        
        # Validate line items
        for i, detalle in enumerate(document_data.detalles):
            item_validation = DocumentValidator._validate_line_item_business_rules(detalle)
            if not item_validation["is_valid"]:
                result["is_valid"] = False
                for error in item_validation["errors"]:
                    error["field"] = f"detalles[{i}].{error.get('field', 'unknown')}"
                    result["errors"].append(error)
        
        # Validate references for credit/debit notes
        if document_data.tipo_documento in [DocumentType.NOTA_CREDITO_ELECTRONICA, DocumentType.NOTA_DEBITO_ELECTRONICA]:
            if not document_data.referencias or len(document_data.referencias) == 0:
                result["is_valid"] = False
                result["errors"].append({
                    "field": "referencias",
                    "message": "Credit and debit notes must have at least one reference",
                    "code": "REFERENCES_REQUIRED"
                })
        
        return result
    
    # Private helper methods
    
    @staticmethod
    def _validate_key_consecutive_consistency(document_key: str, consecutive_number: str) -> Dict[str, Any]:
        """Validate document key and consecutive number consistency"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        if len(document_key) == 50 and len(consecutive_number) == 20:
            # Extract consecutive part from document key (positions 21-41)
            key_consecutive = document_key[21:41]
            
            if key_consecutive != consecutive_number:
                result["is_valid"] = False
                result["errors"].append({
                    "field": "clave",
                    "message": "Document key consecutive part does not match consecutive number",
                    "code": "KEY_CONSECUTIVE_MISMATCH"
                })
        
        return result
    
    @staticmethod
    def _validate_document_totals(document: Document) -> Dict[str, Any]:
        """Validate document totals consistency"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Basic total validation
        if document.total_venta_neta < 0:
            result["is_valid"] = False
            result["errors"].append({
                "field": "total_venta_neta",
                "message": "Net sale total cannot be negative",
                "code": "NEGATIVE_NET_TOTAL"
            })
        
        if document.total_impuesto < 0:
            result["is_valid"] = False
            result["errors"].append({
                "field": "total_impuesto",
                "message": "Tax total cannot be negative",
                "code": "NEGATIVE_TAX_TOTAL"
            })
        
        if document.total_comprobante < 0:
            result["is_valid"] = False
            result["errors"].append({
                "field": "total_comprobante",
                "message": "Document total cannot be negative",
                "code": "NEGATIVE_DOCUMENT_TOTAL"
            })
        
        # Validate total calculation
        expected_total = (
            document.total_venta_neta + 
            document.total_impuesto - 
            document.total_descuento + 
            document.total_otros_cargos
        )
        
        if abs(document.total_comprobante - expected_total) > Decimal('0.01'):
            result["is_valid"] = False
            result["errors"].append({
                "field": "total_comprobante",
                "message": f"Document total calculation error. Expected: {expected_total}, Got: {document.total_comprobante}",
                "code": "TOTAL_CALCULATION_ERROR"
            })
        
        return result
    
    @staticmethod
    def _validate_identification_numbers(document: Document) -> Dict[str, Any]:
        """Validate identification numbers in document"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Validate emisor identification
        if not validate_identification_number(
            document.emisor_numero_identificacion,
            document.emisor_tipo_identificacion.value
        ):
            result["is_valid"] = False
            result["errors"].append({
                "field": "emisor_numero_identificacion",
                "message": "Invalid issuer identification number format",
                "code": "INVALID_EMISOR_ID"
            })
        
        # Validate receptor identification if present
        if (document.receptor_numero_identificacion and 
            document.receptor_tipo_identificacion and
            not validate_identification_number(
                document.receptor_numero_identificacion,
                document.receptor_tipo_identificacion.value
            )):
            result["is_valid"] = False
            result["errors"].append({
                "field": "receptor_numero_identificacion",
                "message": "Invalid receiver identification number format",
                "code": "INVALID_RECEPTOR_ID"
            })
        
        return result
    
    @staticmethod
    def _validate_document_type_business_rules(document: Document) -> Dict[str, Any]:
        """Validate document type specific business rules"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Tickets don't require receptor
        if document.tipo_documento == DocumentType.TIQUETE_ELECTRONICO:
            # Tickets are valid without receptor
            pass
        else:
            # Other document types require receptor
            if not document.receptor_nombre:
                result["is_valid"] = False
                result["errors"].append({
                    "field": "receptor_nombre",
                    "message": f"{document.get_document_type_name()} requires receiver information",
                    "code": "RECEPTOR_REQUIRED"
                })
        
        # Export invoices have special requirements
        if document.tipo_documento == DocumentType.FACTURA_EXPORTACION:
            if document.codigo_moneda == "CRC":
                result["warnings"] = result.get("warnings", [])
                result["warnings"].append({
                    "field": "codigo_moneda",
                    "message": "Export invoices typically use foreign currency",
                    "code": "EXPORT_CURRENCY_WARNING"
                })
        
        return result
    
    @staticmethod
    def _validate_single_reference(reference: DocumentReference, document_type: DocumentType) -> Dict[str, Any]:
        """Validate a single document reference"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Validate required fields
        if reference.tipo_documento_referencia == DocumentReferenceType.OTHERS and not reference.tipo_documento_otro:
            result["is_valid"] = False
            result["errors"].append({
                "field": "tipo_documento_otro",
                "message": "tipo_documento_otro is required when tipo_documento is OTHERS",
                "code": "OTHER_TYPE_REQUIRED"
            })
        
        if reference.codigo_referencia == ReferenceCode.OTHERS and not reference.codigo_referencia_otro:
            result["is_valid"] = False
            result["errors"].append({
                "field": "codigo_referencia_otro",
                "message": "codigo_referencia_otro is required when codigo is OTHERS",
                "code": "OTHER_CODE_REQUIRED"
            })
        
        # Validate date
        if reference.fecha_emision_referencia and reference.fecha_emision_referencia > datetime.now(timezone.utc):
            result["is_valid"] = False
            result["errors"].append({
                "field": "fecha_emision_referencia",
                "message": "Reference emission date cannot be in the future",
                "code": "FUTURE_REFERENCE_DATE"
            })
        
        # Validate document key format if provided
        if reference.numero_referencia and not validate_document_key(reference.numero_referencia):
            # Check if it's a consecutive number instead
            if not validate_consecutive_number(reference.numero_referencia):
                result["is_valid"] = False
                result["errors"].append({
                    "field": "numero_referencia",
                    "message": "Invalid reference number format",
                    "code": "INVALID_REFERENCE_FORMAT"
                })
        
        return result
    
    @staticmethod
    def _validate_reference_uniqueness(references: List[DocumentReference]) -> Dict[str, Any]:
        """Validate reference uniqueness"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        seen_references = set()
        for reference in references:
            if reference.numero_referencia:
                if reference.numero_referencia in seen_references:
                    result["is_valid"] = False
                    result["errors"].append({
                        "field": "referencias",
                        "message": f"Duplicate reference number: {reference.numero_referencia}",
                        "code": "DUPLICATE_REFERENCE"
                    })
                seen_references.add(reference.numero_referencia)
        
        return result
    
    @staticmethod
    def _check_circular_references(
        document: Document,
        referenced_documents: Dict[str, Document],
        visited: Optional[set] = None
    ) -> Dict[str, Any]:
        """Check for circular references in document chain"""
        if visited is None:
            visited = set()
        
        result = {
            "has_circular": False,
            "circular_path": []
        }
        
        if document.clave in visited:
            result["has_circular"] = True
            result["circular_path"] = list(visited) + [document.clave]
            return result
        
        visited.add(document.clave)
        
        if document.referencias:
            for reference in document.referencias:
                if reference.numero_referencia in referenced_documents:
                    ref_doc = referenced_documents[reference.numero_referencia]
                    circular_check = DocumentValidator._check_circular_references(
                        ref_doc, referenced_documents, visited.copy()
                    )
                    if circular_check["has_circular"]:
                        return circular_check
        
        return result
    
    @staticmethod
    def _calculate_chain_depth(
        document: Document,
        referenced_documents: Dict[str, Document],
        visited: Optional[set] = None
    ) -> int:
        """Calculate document chain depth"""
        if visited is None:
            visited = set()
        
        if document.clave in visited:
            return 0  # Circular reference protection
        
        visited.add(document.clave)
        max_depth = 0
        
        if document.referencias:
            for reference in document.referencias:
                if reference.numero_referencia in referenced_documents:
                    ref_doc = referenced_documents[reference.numero_referencia]
                    depth = 1 + DocumentValidator._calculate_chain_depth(
                        ref_doc, referenced_documents, visited.copy()
                    )
                    max_depth = max(max_depth, depth)
        
        return max_depth
    
    @staticmethod
    def _validate_receptor_requirements(document_data: DocumentCreate) -> Dict[str, Any]:
        """Validate receptor requirements based on document type"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Tickets don't require receptor
        if document_data.tipo_documento == DocumentType.TIQUETE_ELECTRONICO:
            return result
        
        # Other document types require receptor
        if not document_data.receptor:
            result["is_valid"] = False
            result["errors"].append({
                "field": "receptor",
                "message": f"Receptor is required for {document_data.tipo_documento.value}",
                "code": "RECEPTOR_REQUIRED"
            })
        
        return result
    
    @staticmethod
    def _validate_credit_sale_requirements(document_data: DocumentCreate) -> Dict[str, Any]:
        """Validate credit sale requirements"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        if document_data.condicion_venta.value == "02":  # CREDITO
            if not document_data.plazo_credito:
                result["is_valid"] = False
                result["errors"].append({
                    "field": "plazo_credito",
                    "message": "Credit term is required for credit sales",
                    "code": "CREDIT_TERM_REQUIRED"
                })
        
        return result
    
    @staticmethod
    def _validate_line_item_business_rules(detalle) -> Dict[str, Any]:
        """Validate line item business rules"""
        result = {
            "is_valid": True,
            "errors": []
        }
        
        # Validate CABYS code
        if not validate_cabys_code(detalle.codigo_cabys):
            result["is_valid"] = False
            result["errors"].append({
                "field": "codigo_cabys",
                "message": f"Invalid CABYS code: {detalle.codigo_cabys}",
                "code": "INVALID_CABYS_CODE"
            })
        
        # Validate quantities and amounts
        if detalle.cantidad <= 0:
            result["is_valid"] = False
            result["errors"].append({
                "field": "cantidad",
                "message": "Quantity must be positive",
                "code": "INVALID_QUANTITY"
            })
        
        if detalle.precio_unitario < 0:
            result["is_valid"] = False
            result["errors"].append({
                "field": "precio_unitario",
                "message": "Unit price cannot be negative",
                "code": "NEGATIVE_UNIT_PRICE"
            })
        
        return result


# Convenience functions

def validate_document_create(document_data: DocumentCreate) -> Dict[str, Any]:
    """
    Validate document creation data
    
    Args:
        document_data: Document creation data
        
    Returns:
        Validation result dictionary
    """
    return DocumentValidator.validate_document_business_rules(document_data)


def validate_document_model(document: Document) -> Dict[str, Any]:
    """
    Validate document model instance
    
    Args:
        document: Document instance
        
    Returns:
        Validation result dictionary
    """
    return DocumentValidator.validate_document_integrity(document)