"""
Receptor message API endpoints for Costa Rica electronic documents.
Handles acceptance, partial acceptance, and rejection messages.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.messages import (
    ReceptorMessageCreate, ReceptorMessageResponse, ReceptorMessageList,
    ReceptorMessageFilters, ReceptorMessageStatus, ReceptorMessageSummary
)
from app.schemas.enums import ReceptorMessageType
from app.services.receptor_message_service import ReceptorMessageService
from app.utils.error_responses import ValidationError, NotFoundError

router = APIRouter(
    prefix="/mensajes-receptor",
    tags=["Receptor Messages"],
    responses={404: {"description": "Not found"}}
)


@router.post(
    "/",
    response_model=ReceptorMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create receptor message",
    description="Create acceptance/rejection message for received electronic document"
)
async def create_receptor_message(
    message_data: ReceptorMessageCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create a new receptor message for document acceptance/rejection.
    
    Supports three message types:
    - 1: Accepted (Aceptado)
    - 2: Partially accepted (Aceptado parcialmente)  
    - 3: Rejected (Rechazado)
    
    For rejection messages, detalle_mensaje is required to specify the reason.
    
    Requirements: 16.1 - Support receptor message generation with message types 1, 2, 3
    """
    try:
        service = ReceptorMessageService(db)
        message = service.create_message(
            tenant=current_tenant,
            message_data=message_data,
            created_by=f"tenant:{current_tenant.id}"
        )
        
        return service._message_to_response(message)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating receptor message"
        )


@router.get(
    "/{message_id}",
    response_model=ReceptorMessageResponse,
    summary="Get receptor message",
    description="Retrieve receptor message details by ID"
)
async def get_receptor_message(
    message_id: UUID = Path(..., description="Message UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get detailed receptor message information.
    
    Returns complete message data including:
    - Original document information
    - Message type and details
    - Processing status and timestamps
    - XML content if generated
    
    Requirements: 16.2 - Message retrieval with original document key, issuer identification, and emission date
    """
    try:
        service = ReceptorMessageService(db)
        message = service.get_message(message_id, current_tenant)
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receptor message not found"
            )
        
        return service._message_to_response(message)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving receptor message"
        )


@router.get(
    "/",
    response_model=ReceptorMessageList,
    summary="List receptor messages",
    description="List receptor messages with filtering and pagination"
)
async def list_receptor_messages(
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    
    # Sorting parameters
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    
    # Filter parameters
    clave_documento: Optional[str] = Query(None, description="Filter by document key"),
    cedula_emisor: Optional[str] = Query(None, description="Filter by issuer ID"),
    mensaje: Optional[ReceptorMessageType] = Query(None, description="Filter by message type"),
    enviado: Optional[bool] = Query(None, description="Filter by sent status"),
    fecha_desde: Optional[datetime] = Query(None, description="Filter from date"),
    fecha_hasta: Optional[datetime] = Query(None, description="Filter to date"),
    
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List receptor messages with advanced filtering and pagination.
    
    Supports filtering by:
    - Document key and issuer identification
    - Message type (accepted, partially accepted, rejected)
    - Send status and date ranges
    
    Supports sorting by any message field with ascending/descending order.
    
    Requirements: 16.2 - Message listing and retrieval functionality
    """
    try:
        # Build filters
        filters = ReceptorMessageFilters(
            clave_documento=clave_documento,
            cedula_emisor=cedula_emisor,
            mensaje=mensaje,
            enviado=enviado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
        service = ReceptorMessageService(db)
        return service.list_messages(
            tenant=current_tenant,
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
            detail="Internal server error listing receptor messages"
        )


@router.post(
    "/{message_id}/enviar",
    response_model=ReceptorMessageResponse,
    summary="Send receptor message",
    description="Send receptor message to Ministry of Finance"
)
async def send_receptor_message(
    message_id: UUID = Path(..., description="Message UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Send receptor message to Ministry of Finance.
    
    This endpoint:
    1. Generates XML message if not already generated
    2. Digitally signs the XML with tenant certificate
    3. Submits the message to Ministry API
    4. Updates message status based on response
    
    Requirements: 16.3 - Message submission to Ministry
    """
    try:
        service = ReceptorMessageService(db)
        message = service.send_message(message_id, current_tenant)
        
        return service._message_to_response(message)
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receptor message not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error sending receptor message"
        )


@router.get(
    "/{message_id}/status",
    response_model=ReceptorMessageStatus,
    summary="Get message status",
    description="Get receptor message processing status"
)
async def get_message_status(
    message_id: UUID = Path(..., description="Message UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get receptor message processing status.
    
    Returns current processing status including:
    - Send status and timestamps
    - Ministry response information
    - Error details if any
    - Retry information
    
    Requirements: 16.4 - Message status tracking
    """
    try:
        service = ReceptorMessageService(db)
        return service.get_message_status(message_id, current_tenant)
        
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receptor message not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting message status"
        )


@router.get(
    "/summary",
    response_model=ReceptorMessageSummary,
    summary="Get messages summary",
    description="Get receptor message statistics and summary"
)
async def get_messages_summary(
    fecha_desde: Optional[datetime] = Query(None, description="Start date for summary"),
    fecha_hasta: Optional[datetime] = Query(None, description="End date for summary"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get receptor message summary statistics.
    
    Returns:
    - Total message count
    - Count by message type (accepted, partial, rejected)
    - Count by processing status
    - Send success rates
    - Period information
    
    Requirements: 16.5 - Message analytics and reporting
    """
    try:
        service = ReceptorMessageService(db)
        return service.get_messages_summary(
            tenant=current_tenant,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error generating messages summary"
        )


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete receptor message",
    description="Delete receptor message (only unsent messages can be deleted)"
)
async def delete_receptor_message(
    message_id: UUID = Path(..., description="Message UUID"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Delete receptor message.
    
    Only messages that haven't been sent to the Ministry can be deleted.
    Sent messages cannot be deleted to maintain audit trail.
    
    Requirements: 16.6 - Message management operations
    """
    try:
        service = ReceptorMessageService(db)
        message = service.get_message(message_id, current_tenant)
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receptor message not found"
            )
        
        if message.enviado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete sent messages"
            )
        
        db.delete(message)
        db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error deleting receptor message"
        )