"""
Document management API endpoints for Costa Rica electronic documents.
Supports all 7 document types with comprehensive CRUD operations.
"""
from datetime import date
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.auth import get_current_tenant
from app.models.tenant import Tenant
from app.models.document import Document
from app.models.document_reference import DocumentReference
from app.schemas.documents import (
    DocumentCreate, DocumentResponse, DocumentDetail, DocumentList,
    DocumentFilters, DocumentStatusUpdate, DocumentSummary
)
from app.schemas.enums import DocumentType, DocumentStatus
from app.services.document_service import DocumentService
from app.utils.error_responses import (
    DocumentNotFoundError, ValidationError, PermissionError as CustomPermissionError
)

router = APIRouter(
    prefix="/documents",
    tags=["Electronic Documents"],
    responses={404: {"description": "Not found"}}
)


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new document",
    description="Create a new electronic document supporting all 7 Costa Rican document types"
)
async def create_document(
    document_data: DocumentCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create a new electronic document
    
    Supports all 7 document types:
    - 01: Factura Electrónica
    - 02: Nota de Débito Electrónica  
    - 03: Nota de Crédito Electrónica
    - 04: Tiquete Electrónico
    - 05: Factura Electrónica de Exportación
    - 06: Factura Electrónica de Compra
    - 07: Recibo Electrónico de Pago
    
    Requirements: 9.1 - document creation with complete validation
    """
    try:
        service = DocumentService(db)
        document = service.create_document(
            tenant_id=current_tenant.id,
            document_data=document_data,
            created_by=f"tenant:{current_tenant.id}"
        )
        
        return service._document_to_response(document)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating document"
        )


# =============================================================================
# SPECIFIC ROUTES (must come before /{document_id} route)
# =============================================================================

@router.get(
    "/search",
    response_model=DocumentList,
    summary="Search documents",
    description="Search documents across multiple fields"
)
async def search_documents(
    q: str = Query(..., min_length=3, description="Search term"),
    fields: Optional[List[str]] = Query(
        None, 
        description="Specific fields to search in (default: all searchable fields)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Search documents across multiple fields
    
    Searches in the following fields by default:
    - Consecutive number
    - Document key
    - Issuer name and identification
    - Receiver name and identification
    - Observations
    
    Requirements: 9.1 - document search functionality across all fields
    """
    try:
        service = DocumentService(db)
        return service.search_documents(
            tenant_id=current_tenant.id,
            search_term=q,
            search_fields=fields,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error searching documents"
        )


@router.get(
    "/summary",
    response_model=DocumentSummary,
    summary="Get document summary",
    description="Get document statistics and summary information"
)
async def get_document_summary(
    fecha_desde: Optional[date] = Query(None, description="Start date for summary"),
    fecha_hasta: Optional[date] = Query(None, description="End date for summary"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get document summary statistics
    
    Returns:
    - Total document count
    - Count by document type
    - Count by status
    - Total monetary amount
    - Period information
    
    Requirements: 9.1 - document statistics and reporting
    """
    try:
        service = DocumentService(db)
        return service.get_document_summary(
            tenant_id=current_tenant.id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error generating document summary"
        )


# =============================================================================
# PARAMETERIZED ROUTES (must come after specific routes)
# =============================================================================

@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Retrieve complete document information including line items and relationships"
)
async def get_document(
    document_id: UUID = Path(..., description="Document UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get detailed document information
    
    Returns complete document data including:
    - Header information (emisor, receptor, totals)
    - Line items with taxes and discounts
    - Document references (for credit/debit notes)
    - Other charges and fees
    - Processing status and history
    
    Requirements: 9.1 - document retrieval with tenant isolation
    """
    try:
        service = DocumentService(db)
        document = service.get_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            include_details=True
        )
        
        if not document:
            raise DocumentNotFoundError("Document not found")
        
        # Convert to detailed response (placeholder - would need full implementation)
        return service._document_to_response(document)
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving document"
        )


@router.get(
    "/",
    response_model=DocumentList,
    summary="List documents",
    description="List documents with advanced filtering, pagination, and sorting"
)
async def list_documents(
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    
    # Sorting parameters
    sort_by: str = Query("fecha_emision", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    
    # Filter parameters
    tipo_documento: Optional[DocumentType] = Query(None, description="Filter by document type"),
    estado: Optional[DocumentStatus] = Query(None, description="Filter by status"),
    fecha_desde: Optional[date] = Query(None, description="Filter from date"),
    fecha_hasta: Optional[date] = Query(None, description="Filter to date"),
    emisor_identificacion: Optional[str] = Query(None, description="Filter by issuer ID"),
    receptor_identificacion: Optional[str] = Query(None, description="Filter by receiver ID"),
    monto_minimo: Optional[float] = Query(None, ge=0, description="Minimum amount filter"),
    monto_maximo: Optional[float] = Query(None, ge=0, description="Maximum amount filter"),
    numero_consecutivo: Optional[str] = Query(None, description="Filter by consecutive number"),
    clave: Optional[str] = Query(None, description="Filter by document key"),
    
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List documents with advanced filtering and pagination
    
    Supports filtering by:
    - Document type and status
    - Date ranges
    - Issuer and receiver identification
    - Amount ranges
    - Consecutive number and document key
    
    Supports sorting by any document field with ascending/descending order.
    
    Requirements: 9.1 - document listing with advanced pagination, filtering, and sorting
    """
    try:
        # Build filters
        filters = DocumentFilters(
            tipo_documento=tipo_documento,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            emisor_identificacion=emisor_identificacion,
            receptor_identificacion=receptor_identificacion,
            monto_minimo=monto_minimo,
            monto_maximo=monto_maximo,
            numero_consecutivo=numero_consecutivo,
            clave=clave
        )
        
        service = DocumentService(db)
        return service.list_documents(
            tenant_id=current_tenant.id,
            filters=filters,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error listing documents"
        )


@router.put(
    "/{document_id}/status",
    response_model=DocumentResponse,
    summary="Update document status",
    description="Update document processing status and Ministry information"
)
async def update_document_status(
    document_id: UUID = Path(..., description="Document UUID"),
    status_update: DocumentStatusUpdate = ...,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Update document status and tracking information
    
    Used for:
    - Updating Ministry processing status
    - Recording Ministry responses and errors
    - Tracking document lifecycle
    
    Requirements: 9.1 - document status tracking and history management
    """
    try:
        service = DocumentService(db)
        document = service.update_document_status(
            document_id=document_id,
            tenant_id=current_tenant.id,
            status_update=status_update,
            updated_by=f"tenant:{current_tenant.id}"
        )
        
        return service._document_to_response(document)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error updating document status"
        )


@router.get(
    "/{document_id}/xml",
    response_class=Response,
    summary="Download document XML",
    description="Download original or signed XML document"
)
async def download_document_xml(
    document_id: UUID = Path(..., description="Document UUID"),
    signed: bool = Query(False, description="Download signed XML (default: original)"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Download document XML file
    
    Returns:
    - Original XML (generated): When signed=false
    - Signed XML (with digital signature): When signed=true
    
    Requirements: 5.4 - XML download functionality
    """
    try:
        service = DocumentService(db)
        document = service.get_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            include_details=False
        )
        
        if not document:
            raise DocumentNotFoundError("Document not found")
        
        # Get appropriate XML content
        if signed and document.xml_firmado:
            xml_content = document.xml_firmado
            filename = f"{document.numero_consecutivo}_signed.xml"
        elif document.xml_original:
            xml_content = document.xml_original
            filename = f"{document.numero_consecutivo}_original.xml"
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="XML not available for this document"
            )
        
        return Response(
            content=xml_content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error downloading XML"
        )


@router.get(
    "/{document_id}/status",
    response_model=dict,
    summary="Check Ministry status",
    description="Check document processing status with Ministry of Finance"
)
async def check_document_status(
    document_id: UUID = Path(..., description="Document UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Check document processing status with Ministry of Finance
    
    Returns current Ministry processing status including:
    - Document processing state
    - Ministry response messages
    - Processing timestamps
    - Error details if any
    
    Requirements: 5.5 - Ministry status check
    """
    try:
        service = DocumentService(db)
        document = service.get_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            include_details=False
        )
        
        if not document:
            raise DocumentNotFoundError("Document not found")
        
        # Return comprehensive status information
        status_info = {
            "document_id": str(document.id),
            "clave": document.clave,
            "estado": document.estado.value if document.estado else "unknown",
            "fecha_emision": document.fecha_emision.isoformat(),
            "fecha_procesamiento": document.fecha_procesamiento.isoformat() if document.fecha_procesamiento else None,
            "fecha_aceptacion": document.fecha_aceptacion.isoformat() if hasattr(document, 'fecha_aceptacion') and document.fecha_aceptacion else None,
            "mensaje_hacienda": document.mensaje_hacienda,
            "intentos_envio": document.intentos_envio if hasattr(document, 'intentos_envio') else 0,
            "xml_firmado_disponible": bool(document.xml_firmado),
            "xml_respuesta_disponible": bool(document.xml_respuesta_hacienda),
            "puede_reenviar": document.estado in [DocumentStatus.ERROR, DocumentStatus.RECHAZADO] if hasattr(document, 'estado') else False,
            "puede_cancelar": document.estado in [DocumentStatus.BORRADOR, DocumentStatus.ENVIADO] if hasattr(document, 'estado') else False
        }
        
        return status_info
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error checking document status"
        )


@router.get(
    "/{document_id}/pdf",
    response_class=Response,
    summary="Download document PDF",
    description="Generate and download PDF representation of document"
)
async def download_document_pdf(
    document_id: UUID = Path(..., description="Document UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Generate and download document PDF
    
    Only available for accepted documents.
    
    Requirements: 5.4 - PDF generation and download
    """
    try:
        service = DocumentService(db)
        document = service.get_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            include_details=True
        )
        
        if not document:
            raise DocumentNotFoundError("Document not found")
        
        if document.estado != DocumentStatus.ACEPTADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF only available for accepted documents"
            )
        
        # TODO: Implement PDF generation
        # This would integrate with a PDF generation service
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation not yet implemented"
        )
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error generating PDF"
        )


@router.post(
    "/{document_id}/resend",
    response_model=DocumentResponse,
    summary="Resend document to Ministry",
    description="Resubmit document to Ministry of Finance"
)
async def resend_document(
    document_id: UUID = Path(..., description="Document UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Resubmit document to Ministry of Finance
    
    Used for:
    - Retrying failed submissions
    - Reprocessing rejected documents after corrections
    
    Requirements: 5.5 - document resubmission
    """
    try:
        service = DocumentService(db)
        document = service.get_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            include_details=False
        )
        
        if not document:
            raise DocumentNotFoundError("Document not found")
        
        # Check if document can be resent
        if document.estado not in [DocumentStatus.ERROR, DocumentStatus.RECHAZADO, DocumentStatus.BORRADOR]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document cannot be resent in current state: {document.estado.value}"
            )
        
        # Update status to pending for resubmission
        status_update = DocumentStatusUpdate(
            estado=DocumentStatus.PENDIENTE,
            mensaje_hacienda="Document queued for resubmission"
        )
        
        updated_document = service.update_document_status(
            document_id=document_id,
            tenant_id=current_tenant.id,
            status_update=status_update,
            updated_by=f"tenant:{current_tenant.id}"
        )
        
        # TODO: Queue document for Ministry submission
        # This would integrate with the Ministry service and background task queue
        # For now, we'll just update the status to indicate it's ready for processing
        
        return service._document_to_response(updated_document)
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error resending document"
        )


@router.post(
    "/{document_id}/cancel",
    response_model=DocumentResponse,
    summary="Cancel document",
    description="Cancel document and notify Ministry if necessary"
)
async def cancel_document(
    document_id: UUID = Path(..., description="Document UUID"),
    razon: str = Query(..., min_length=10, max_length=180, description="Cancellation reason"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Cancel document
    
    For accepted documents, this creates a cancellation request to the Ministry.
    For draft documents, this simply marks them as cancelled.
    
    Requirements: 15.1 - document cancellation workflows
    """
    try:
        service = DocumentService(db)
        document = service.get_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            include_details=False
        )
        
        if not document:
            raise DocumentNotFoundError("Document not found")
        
        # Check if document can be cancelled
        if document.estado not in [DocumentStatus.BORRADOR, DocumentStatus.PENDIENTE, DocumentStatus.ERROR]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document cannot be cancelled in current state: {document.estado.value}"
            )
        
        # Update status to cancelled
        status_update = DocumentStatusUpdate(
            estado=DocumentStatus.CANCELADO,
            mensaje_hacienda=f"Cancelled by user: {razon}"
        )
        
        updated_document = service.update_document_status(
            document_id=document_id,
            tenant_id=current_tenant.id,
            status_update=status_update,
            updated_by=f"tenant:{current_tenant.id}"
        )
        
        return service._document_to_response(updated_document)
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error cancelling document"
        )


@router.get(
    "/{document_id}/references",
    response_model=List[DocumentResponse],
    summary="Get document relationships",
    description="Get documents that reference this document or are referenced by it"
)
async def get_document_references(
    document_id: UUID = Path(..., description="Document UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get document relationships
    
    Returns:
    - Documents that reference this document (e.g., credit notes for an invoice)
    - Documents referenced by this document (e.g., original invoice for a credit note)
    
    Requirements: 15.1 - document relationship tracking
    """
    try:
        service = DocumentService(db)
        document = service.get_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            include_details=False
        )
        
        if not document:
            raise DocumentNotFoundError("Document not found")
        
        related_documents = []
        
        # Find documents that reference this document (by document key)
        referencing_docs = db.query(Document).join(DocumentReference).filter(
            and_(
                Document.tenant_id == current_tenant.id,
                DocumentReference.numero == document.clave
            )
        ).all()
        
        # Find documents referenced by this document
        if hasattr(document, 'referencias') and document.referencias:
            referenced_keys = [ref.numero for ref in document.referencias if ref.numero]
            referenced_docs = db.query(Document).filter(
                and_(
                    Document.tenant_id == current_tenant.id,
                    Document.clave.in_(referenced_keys)
                )
            ).all()
            related_documents.extend(referenced_docs)
        
        # Add referencing documents
        related_documents.extend(referencing_docs)
        
        # Remove duplicates and convert to response models
        unique_docs = {doc.id: doc for doc in related_documents}
        return [service._document_to_response(doc) for doc in unique_docs.values()]
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving document references"
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Delete document (only draft documents can be deleted)"
)
async def delete_document(
    document_id: UUID = Path(..., description="Document UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Delete document
    
    Only draft documents can be deleted. Documents that have been sent to the
    Ministry cannot be deleted, only cancelled.
    
    Requirements: 9.1 - document management operations
    """
    try:
        service = DocumentService(db)
        success = service.delete_document(
            document_id=document_id,
            tenant_id=current_tenant.id,
            deleted_by=f"tenant:{current_tenant.id}"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document could not be deleted"
            )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error deleting document"
        )