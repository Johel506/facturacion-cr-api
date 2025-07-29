"""
Receptor Message Service for Costa Rica electronic document system.
Handles creation, management, and submission of receptor messages.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.models.receptor_message import ReceptorMessage
from app.models.document import Document
from app.models.tenant import Tenant
from app.schemas.messages import (
    ReceptorMessageCreate, ReceptorMessageResponse, ReceptorMessageList,
    ReceptorMessageFilters, ReceptorMessageStatus, ReceptorMessageSummary
)
from app.schemas.enums import ReceptorMessageType, IVACondition
from app.utils.error_responses import ValidationError, NotFoundError


class ReceptorMessageService:
    """Service for managing receptor messages."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_message(
        self,
        tenant: Tenant,
        message_data: ReceptorMessageCreate,
        created_by: str = None
    ) -> ReceptorMessage:
        """
        Create a new receptor message.
        
        Args:
            tenant: Tenant creating the message
            message_data: Message creation data
            created_by: User creating the message
            
        Returns:
            Created ReceptorMessage instance
            
        Raises:
            ValidationError: If message data is invalid
        """
        # Validate document key format
        if not ReceptorMessage.validate_document_key_format(message_data.clave_documento):
            raise ValidationError("Invalid document key format")
        
        # Validate issuer ID format
        if not ReceptorMessage.validate_issuer_id_format(message_data.cedula_emisor):
            raise ValidationError("Invalid issuer identification format")
        
        # Check if message already exists for this document
        existing_message = self.db.query(ReceptorMessage).filter(
            and_(
                ReceptorMessage.clave_documento == message_data.clave_documento,
                ReceptorMessage.receptor_identificacion_numero == tenant.cedula_juridica
            )
        ).first()
        
        if existing_message:
            raise ValidationError("Message already exists for this document")
        
        # Try to find the original document in our system
        original_document = self.db.query(Document).filter(
            Document.clave == message_data.clave_documento
        ).first()
        
        # Create the receptor message
        message = ReceptorMessage(
            documento_id=original_document.id if original_document else None,
            clave_documento=message_data.clave_documento,
            cedula_emisor=message_data.cedula_emisor,
            fecha_emision=message_data.fecha_emision,
            mensaje=message_data.mensaje.value,
            detalle_mensaje=message_data.detalle_mensaje,
            monto_total_impuesto=message_data.monto_total_impuesto,
            codigo_actividad=message_data.codigo_actividad,
            condicion_impuesto=message_data.condicion_impuesto.value if message_data.condicion_impuesto else None,
            receptor_identificacion_tipo="02",  # Default to cedula juridica for companies
            receptor_identificacion_numero=tenant.cedula_juridica,
            receptor_nombre=tenant.nombre_empresa,
            estado='pendiente',
            created_by=created_by or f"tenant:{tenant.id}"
        )
        
        # Validate message data
        is_valid, error_msg = message.validate_message_data()
        if not is_valid:
            raise ValidationError(error_msg)
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_message(self, message_id: UUID, tenant: Tenant) -> Optional[ReceptorMessage]:
        """
        Get a receptor message by ID.
        
        Args:
            message_id: Message UUID
            tenant: Tenant requesting the message
            
        Returns:
            ReceptorMessage instance or None if not found
        """
        return self.db.query(ReceptorMessage).filter(
            and_(
                ReceptorMessage.id == message_id,
                ReceptorMessage.receptor_identificacion_numero == tenant.cedula_juridica
            )
        ).first()
    
    def list_messages(
        self,
        tenant: Tenant,
        filters: ReceptorMessageFilters = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> ReceptorMessageList:
        """
        List receptor messages with filtering and pagination.
        
        Args:
            tenant: Tenant requesting the messages
            filters: Optional filters to apply
            page: Page number (1-based)
            size: Page size
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            ReceptorMessageList with paginated results
        """
        # Base query with tenant isolation
        query = self.db.query(ReceptorMessage).filter(
            ReceptorMessage.receptor_identificacion_numero == tenant.cedula_juridica
        )
        
        # Apply filters
        if filters:
            if filters.clave_documento:
                query = query.filter(ReceptorMessage.clave_documento == filters.clave_documento)
            
            if filters.cedula_emisor:
                query = query.filter(ReceptorMessage.cedula_emisor == filters.cedula_emisor)
            
            if filters.mensaje:
                query = query.filter(ReceptorMessage.mensaje == filters.mensaje.value)
            
            if filters.enviado is not None:
                query = query.filter(ReceptorMessage.enviado == filters.enviado)
            
            if filters.fecha_desde:
                query = query.filter(ReceptorMessage.created_at >= filters.fecha_desde)
            
            if filters.fecha_hasta:
                query = query.filter(ReceptorMessage.created_at <= filters.fecha_hasta)
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(ReceptorMessage, sort_by, ReceptorMessage.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (page - 1) * size
        messages = query.offset(offset).limit(size).all()
        
        # Calculate pagination info
        pages = (total + size - 1) // size
        
        return ReceptorMessageList(
            items=[self._message_to_response(msg) for msg in messages],
            total=total,
            page=page,
            size=size,
            pages=pages
        )
    
    def send_message(self, message_id: UUID, tenant: Tenant) -> ReceptorMessage:
        """
        Send a receptor message to the Ministry.
        
        Args:
            message_id: Message UUID
            tenant: Tenant sending the message
            
        Returns:
            Updated ReceptorMessage instance
            
        Raises:
            NotFoundError: If message not found
            ValidationError: If message cannot be sent
        """
        message = self.get_message(message_id, tenant)
        if not message:
            raise NotFoundError("Message not found")
        
        # Check if message can be sent
        if not message.can_be_sent:
            raise ValidationError(f"Message cannot be sent in current state: {message.estado}")
        
        # TODO: Implement actual Ministry submission
        # For now, we'll simulate the process
        
        try:
            # Generate XML if not already generated
            if not message.xml_mensaje:
                message.xml_mensaje = self._generate_message_xml(message)
                message.estado = 'generado'
            
            # Sign XML if not already signed
            if not message.xml_firmado:
                # TODO: Implement XML signing with tenant certificate
                message.xml_firmado = message.xml_mensaje  # Placeholder
                message.estado = 'firmado'
            
            # Send to Ministry
            # TODO: Implement actual Ministry API call
            message.mark_as_sent()
            
            self.db.commit()
            self.db.refresh(message)
            
            return message
            
        except Exception as e:
            message.mark_as_error(str(e))
            self.db.commit()
            raise ValidationError(f"Failed to send message: {str(e)}")
    
    def get_message_status(self, message_id: UUID, tenant: Tenant) -> ReceptorMessageStatus:
        """
        Get message status information.
        
        Args:
            message_id: Message UUID
            tenant: Tenant requesting the status
            
        Returns:
            ReceptorMessageStatus with current status
            
        Raises:
            NotFoundError: If message not found
        """
        message = self.get_message(message_id, tenant)
        if not message:
            raise NotFoundError("Message not found")
        
        return ReceptorMessageStatus(
            id=message.id,
            enviado=message.enviado,
            fecha_envio=message.fecha_envio,
            respuesta_hacienda=message.respuesta_hacienda,
            estado_procesamiento=message.estado,
            intentos_envio=message.intentos_envio
        )
    
    def get_messages_summary(
        self,
        tenant: Tenant,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> ReceptorMessageSummary:
        """
        Get summary statistics for receptor messages.
        
        Args:
            tenant: Tenant requesting the summary
            fecha_desde: Start date for summary
            fecha_hasta: End date for summary
            
        Returns:
            ReceptorMessageSummary with statistics
        """
        # Base query with tenant isolation
        query = self.db.query(ReceptorMessage).filter(
            ReceptorMessage.receptor_identificacion_numero == tenant.cedula_juridica
        )
        
        # Apply date filters
        if fecha_desde:
            query = query.filter(ReceptorMessage.created_at >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(ReceptorMessage.created_at <= fecha_hasta)
        
        # Get total count
        total_mensajes = query.count()
        
        # Count by message type
        aceptados = query.filter(ReceptorMessage.mensaje == 1).count()
        parciales = query.filter(ReceptorMessage.mensaje == 2).count()
        rechazados = query.filter(ReceptorMessage.mensaje == 3).count()
        
        # Count by status
        enviados = query.filter(ReceptorMessage.enviado == True).count()
        pendientes = query.filter(
            and_(
                ReceptorMessage.enviado == False,
                ReceptorMessage.estado != 'error'
            )
        ).count()
        errores = query.filter(ReceptorMessage.estado == 'error').count()
        
        return ReceptorMessageSummary(
            total_mensajes=total_mensajes,
            por_tipo={
                'aceptados': aceptados,
                'parciales': parciales,
                'rechazados': rechazados
            },
            por_estado={
                'enviados': enviados,
                'pendientes': pendientes,
                'errores': errores
            },
            enviados=enviados,
            pendientes=pendientes,
            errores=errores
        )
    
    def _message_to_response(self, message: ReceptorMessage) -> ReceptorMessageResponse:
        """Convert ReceptorMessage to response model."""
        return ReceptorMessageResponse(
            id=message.id,
            clave_documento=message.clave_documento,
            cedula_emisor=message.cedula_emisor,
            fecha_emision=message.fecha_emision,
            mensaje=ReceptorMessageType(message.mensaje),
            detalle_mensaje=message.detalle_mensaje,
            monto_total_impuesto=message.monto_total_impuesto,
            codigo_actividad=message.codigo_actividad,
            condicion_impuesto=IVACondition(message.condicion_impuesto) if message.condicion_impuesto else None,
            xml_mensaje=message.xml_mensaje,
            xml_firmado=message.xml_firmado,
            enviado=message.enviado,
            fecha_envio=message.fecha_envio,
            respuesta_hacienda=message.respuesta_hacienda,
            created_at=message.created_at,
            updated_at=message.updated_at
        )
    
    def _generate_message_xml(self, message: ReceptorMessage) -> str:
        """
        Generate XML for receptor message.
        
        Args:
            message: ReceptorMessage instance
            
        Returns:
            Generated XML string
        """
        # TODO: Implement actual XML generation based on Ministry specifications
        # This is a placeholder implementation
        
        mensaje_text = {1: "Aceptado", 2: "Aceptado parcialmente", 3: "Rechazado"}
        
        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<MensajeReceptor xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/mensajeReceptor">
    <Clave>{message.clave_documento}</Clave>
    <NumeroCedulaEmisor>{message.cedula_emisor}</NumeroCedulaEmisor>
    <FechaEmisionDoc>{message.fecha_emision.strftime('%Y-%m-%dT%H:%M:%S%z')}</FechaEmisionDoc>
    <Mensaje>{message.mensaje}</Mensaje>
    <DetalleMensaje>{message.detalle_mensaje or ''}</DetalleMensaje>
    <MontoTotalImpuesto>{message.monto_total_impuesto or 0}</MontoTotalImpuesto>
    <CodigoActividad>{message.codigo_actividad or ''}</CodigoActividad>
    <CondicionImpuesto>{message.condicion_impuesto or ''}</CondicionImpuesto>
</MensajeReceptor>"""
        
        return xml_template