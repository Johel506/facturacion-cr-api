"""
Receptor Message model for document acceptance/rejection responses

This model handles receptor messages that are sent in response to received
electronic documents to indicate acceptance, partial acceptance, or rejection
as defined in Costa Rica's electronic invoicing system.

Requirements: 16.1, 16.2
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, Numeric,
    CheckConstraint, Index, func, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ReceptorMessage(Base):
    """
    Receptor Message model for document acceptance/rejection responses
    
    Handles receptor messages sent in response to received electronic documents.
    These messages indicate whether a document is accepted, partially accepted,
    or rejected by the receiver, along with optional details and validation information.
    
    Message types:
    - 1: Accepted (Aceptado)
    - 2: Partially accepted (Aceptado parcialmente)
    - 3: Rejected (Rechazado)
    
    Requirements:
    - 16.1: Support receptor message generation with message types 1, 2, 3
    - 16.2: Include original document key, issuer identification, and emission date
    """
    __tablename__ = "mensajes_receptor"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Reference to original document (optional foreign key)
    documento_id = Column(UUID(as_uuid=True), ForeignKey('documentos.id', ondelete='SET NULL'),
                         nullable=True, index=True,
                         comment="Reference to original document if available in system")
    
    # Original document information (required fields)
    clave_documento = Column(String(50), nullable=False, index=True,
                            comment="Original document key (50 characters)")
    cedula_emisor = Column(String(12), nullable=False, index=True,
                          comment="Issuer identification number (9-12 digits)")
    fecha_emision = Column(DateTime(timezone=True), nullable=False,
                          comment="Original document emission date")
    
    # Receptor message details
    mensaje = Column(Integer, nullable=False,
                    comment="Message type: 1=Accepted, 2=Partially accepted, 3=Rejected")
    detalle_mensaje = Column(String(160), nullable=True,
                            comment="Optional message details (max 160 characters)")
    
    # Validation information (optional)
    monto_total_impuesto = Column(Numeric(18, 5), nullable=True,
                                 comment="Total tax amount for validation")
    codigo_actividad = Column(String(6), nullable=True,
                             comment="Economic activity code")
    condicion_impuesto = Column(String(2), nullable=True,
                               comment="IVA condition: 01-05")
    
    # Receptor information
    receptor_identificacion_tipo = Column(String(2), nullable=False,
                                         comment="Receptor identification type (01-06)")
    receptor_identificacion_numero = Column(String(20), nullable=False,
                                           comment="Receptor identification number")
    receptor_nombre = Column(String(100), nullable=False,
                            comment="Receptor name")
    
    # XML generation and processing
    xml_mensaje = Column(Text, nullable=True,
                        comment="Generated XML message")
    xml_firmado = Column(Text, nullable=True,
                        comment="Digitally signed XML message")
    
    # Processing status
    estado = Column(String(20), nullable=False, default='pendiente',
                   comment="Message status: pendiente, generado, firmado, enviado, error")
    enviado = Column(Boolean, nullable=False, default=False,
                    comment="Whether message has been sent to Ministry")
    fecha_envio = Column(DateTime(timezone=True), nullable=True,
                        comment="Date when message was sent")
    
    # Ministry response
    respuesta_hacienda = Column(Text, nullable=True,
                               comment="Ministry response to the message")
    estado_hacienda = Column(String(20), nullable=True,
                            comment="Ministry processing status")
    fecha_respuesta_hacienda = Column(DateTime(timezone=True), nullable=True,
                                     comment="Date of Ministry response")
    
    # Error handling
    intentos_envio = Column(Integer, nullable=False, default=0,
                           comment="Number of send attempts")
    ultimo_error = Column(Text, nullable=True,
                         comment="Last error message if any")
    fecha_ultimo_error = Column(DateTime(timezone=True), nullable=True,
                               comment="Date of last error")
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       server_default=func.now(),
                       comment="Record last update timestamp")
    created_by = Column(String(255), nullable=True,
                       comment="User who created the message")
    
    # Relationships
    documento = relationship("Document", back_populates="mensajes_receptor")
    
    # Table constraints and indexes
    __table_args__ = (
        # Check constraints for data validation
        CheckConstraint(
            "mensaje IN (1, 2, 3)",
            name="ck_receptor_mensaje_type_valid"
        ),
        CheckConstraint(
            "char_length(clave_documento) = 50",
            name="ck_receptor_clave_documento_length"
        ),
        CheckConstraint(
            "clave_documento ~ '^[0-9]{50}$'",
            name="ck_receptor_clave_documento_format"
        ),
        CheckConstraint(
            "char_length(cedula_emisor) >= 9 AND char_length(cedula_emisor) <= 12",
            name="ck_receptor_cedula_emisor_length"
        ),
        CheckConstraint(
            "cedula_emisor ~ '^[0-9]+$'",
            name="ck_receptor_cedula_emisor_format"
        ),
        CheckConstraint(
            "receptor_identificacion_tipo IN ('01', '02', '03', '04', '05', '06')",
            name="ck_receptor_identificacion_tipo_valid"
        ),
        CheckConstraint(
            "char_length(receptor_identificacion_numero) >= 9",
            name="ck_receptor_identificacion_numero_length"
        ),
        CheckConstraint(
            "char_length(receptor_nombre) >= 3",
            name="ck_receptor_nombre_length"
        ),
        CheckConstraint(
            "detalle_mensaje IS NULL OR char_length(detalle_mensaje) <= 160",
            name="ck_receptor_detalle_mensaje_length"
        ),
        CheckConstraint(
            "codigo_actividad IS NULL OR char_length(codigo_actividad) = 6",
            name="ck_receptor_codigo_actividad_length"
        ),
        CheckConstraint(
            "condicion_impuesto IS NULL OR condicion_impuesto IN ('01', '02', '03', '04', '05')",
            name="ck_receptor_condicion_impuesto_valid"
        ),
        CheckConstraint(
            "monto_total_impuesto IS NULL OR monto_total_impuesto >= 0",
            name="ck_receptor_monto_impuesto_positive"
        ),
        CheckConstraint(
            "estado IN ('pendiente', 'generado', 'firmado', 'enviado', 'aceptado', 'rechazado', 'error')",
            name="ck_receptor_estado_valid"
        ),
        CheckConstraint(
            "intentos_envio >= 0",
            name="ck_receptor_intentos_envio_positive"
        ),
        CheckConstraint(
            "fecha_envio IS NULL OR enviado = true",
            name="ck_receptor_fecha_envio_consistency"
        ),
        
        # Performance indexes
        Index("idx_receptor_mensaje_id", "id"),  # Primary key index (automatic)
        Index("idx_receptor_documento_id", "documento_id"),
        Index("idx_receptor_clave_documento", "clave_documento"),
        Index("idx_receptor_cedula_emisor", "cedula_emisor"),
        Index("idx_receptor_mensaje_tipo", "mensaje"),
        Index("idx_receptor_estado", "estado"),
        Index("idx_receptor_enviado", "enviado"),
        Index("idx_receptor_fecha_emision", "fecha_emision"),
        Index("idx_receptor_fecha_envio", "fecha_envio"),
        Index("idx_receptor_created_at", "created_at"),
        Index("idx_receptor_receptor_identificacion", "receptor_identificacion_numero"),
        Index("idx_receptor_codigo_actividad", "codigo_actividad"),
        Index("idx_receptor_estado_hacienda", "estado_hacienda"),
        Index("idx_receptor_intentos_envio", "intentos_envio"),
        
        # Composite indexes for common queries
        Index("idx_receptor_estado_enviado", "estado", "enviado"),
        Index("idx_receptor_mensaje_estado", "mensaje", "estado"),
        Index("idx_receptor_cedula_fecha", "cedula_emisor", "fecha_emision"),
        Index("idx_receptor_documento_mensaje", "documento_id", "mensaje"),
        Index("idx_receptor_pendientes", "estado", "enviado", "intentos_envio"),
        Index("idx_receptor_errores", "estado", "ultimo_error", "fecha_ultimo_error"),
        
        # Search indexes
        Index("idx_receptor_receptor_nombre", "receptor_nombre"),
        Index("idx_receptor_detalle_mensaje", "detalle_mensaje"),
    )
    
    def __repr__(self) -> str:
        return (f"<ReceptorMessage(id={self.id}, clave_documento='{self.clave_documento}', "
                f"mensaje={self.mensaje}, estado='{self.estado}')>")
    
    def __str__(self) -> str:
        mensaje_text = {1: "Aceptado", 2: "Aceptado parcialmente", 3: "Rechazado"}
        return f"Mensaje {mensaje_text.get(self.mensaje, 'Desconocido')} - {self.clave_documento}"
    
    @property
    def mensaje_texto(self) -> str:
        """Get message type as text"""
        mensaje_types = {
            1: "Aceptado",
            2: "Aceptado parcialmente", 
            3: "Rechazado"
        }
        return mensaje_types.get(self.mensaje, "Desconocido")
    
    @property
    def is_accepted(self) -> bool:
        """Check if message indicates acceptance"""
        return self.mensaje == 1
    
    @property
    def is_partially_accepted(self) -> bool:
        """Check if message indicates partial acceptance"""
        return self.mensaje == 2
    
    @property
    def is_rejected(self) -> bool:
        """Check if message indicates rejection"""
        return self.mensaje == 3
    
    @property
    def requires_details(self) -> bool:
        """Check if message type requires detail message"""
        # Rejection messages typically require details
        return self.mensaje == 3
    
    @property
    def can_be_sent(self) -> bool:
        """Check if message can be sent to Ministry"""
        return (
            self.estado in ['generado', 'firmado'] and
            not self.enviado and
            self.xml_firmado is not None
        )
    
    @property
    def needs_retry(self) -> bool:
        """Check if message needs to be retried"""
        return (
            self.estado == 'error' and
            self.intentos_envio < 3 and
            not self.enviado
        )
    
    def validate_message_data(self) -> tuple[bool, Optional[str]]:
        """
        Validate message data completeness and consistency
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not self.clave_documento or len(self.clave_documento) != 50:
            return False, "Document key must be exactly 50 characters"
        
        if not self.cedula_emisor or not (9 <= len(self.cedula_emisor) <= 12):
            return False, "Issuer identification must be 9-12 digits"
        
        if not self.fecha_emision:
            return False, "Emission date is required"
        
        if self.mensaje not in [1, 2, 3]:
            return False, "Message type must be 1, 2, or 3"
        
        # Check rejection details
        if self.mensaje == 3 and not self.detalle_mensaje:
            return False, "Rejection messages require detail message"
        
        # Check detail message length
        if self.detalle_mensaje and len(self.detalle_mensaje) > 160:
            return False, "Detail message cannot exceed 160 characters"
        
        # Check IVA condition if provided
        if self.condicion_impuesto and self.condicion_impuesto not in ['01', '02', '03', '04', '05']:
            return False, "Invalid IVA condition code"
        
        # Check activity code format
        if self.codigo_actividad and len(self.codigo_actividad) != 6:
            return False, "Activity code must be exactly 6 characters"
        
        return True, None
    
    def mark_as_sent(self) -> None:
        """Mark message as sent to Ministry"""
        self.enviado = True
        self.fecha_envio = datetime.now(timezone.utc)
        self.estado = 'enviado'
    
    def mark_as_error(self, error_message: str) -> None:
        """Mark message as error and record error details"""
        self.estado = 'error'
        self.ultimo_error = error_message
        self.fecha_ultimo_error = datetime.now(timezone.utc)
        self.intentos_envio += 1
    
    def mark_as_accepted_by_ministry(self, respuesta: str = None) -> None:
        """Mark message as accepted by Ministry"""
        self.estado_hacienda = 'aceptado'
        self.fecha_respuesta_hacienda = datetime.now(timezone.utc)
        if respuesta:
            self.respuesta_hacienda = respuesta
    
    def mark_as_rejected_by_ministry(self, respuesta: str = None) -> None:
        """Mark message as rejected by Ministry"""
        self.estado_hacienda = 'rechazado'
        self.fecha_respuesta_hacienda = datetime.now(timezone.utc)
        if respuesta:
            self.respuesta_hacienda = respuesta
    
    def get_message_info(self) -> dict:
        """Get comprehensive message information"""
        return {
            'id': str(self.id),
            'clave_documento': self.clave_documento,
            'cedula_emisor': self.cedula_emisor,
            'fecha_emision': self.fecha_emision.isoformat(),
            'mensaje': self.mensaje,
            'mensaje_texto': self.mensaje_texto,
            'detalle_mensaje': self.detalle_mensaje,
            'receptor_identificacion_tipo': self.receptor_identificacion_tipo,
            'receptor_identificacion_numero': self.receptor_identificacion_numero,
            'receptor_nombre': self.receptor_nombre,
            'estado': self.estado,
            'enviado': self.enviado,
            'fecha_envio': self.fecha_envio.isoformat() if self.fecha_envio else None,
            'estado_hacienda': self.estado_hacienda,
            'fecha_respuesta_hacienda': self.fecha_respuesta_hacienda.isoformat() if self.fecha_respuesta_hacienda else None,
            'intentos_envio': self.intentos_envio,
            'ultimo_error': self.ultimo_error,
            'monto_total_impuesto': float(self.monto_total_impuesto) if self.monto_total_impuesto else None,
            'codigo_actividad': self.codigo_actividad,
            'condicion_impuesto': self.condicion_impuesto,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def get_by_document_key(cls, session, clave_documento: str) -> List['ReceptorMessage']:
        """
        Get all messages for a specific document key
        
        Args:
            session: SQLAlchemy session
            clave_documento: Document key to search for
            
        Returns:
            List of ReceptorMessage objects
        """
        return session.query(cls).filter(
            cls.clave_documento == clave_documento
        ).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_by_issuer(cls, session, cedula_emisor: str, limit: int = 50) -> List['ReceptorMessage']:
        """
        Get messages by issuer identification
        
        Args:
            session: SQLAlchemy session
            cedula_emisor: Issuer identification number
            limit: Maximum number of results
            
        Returns:
            List of ReceptorMessage objects
        """
        return session.query(cls).filter(
            cls.cedula_emisor == cedula_emisor
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_pending_messages(cls, session, limit: int = 100) -> List['ReceptorMessage']:
        """
        Get messages pending to be sent
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of results
            
        Returns:
            List of ReceptorMessage objects ready to be sent
        """
        return session.query(cls).filter(
            cls.estado.in_(['generado', 'firmado']),
            cls.enviado == False,
            cls.xml_firmado.isnot(None)
        ).order_by(cls.created_at).limit(limit).all()
    
    @classmethod
    def get_failed_messages(cls, session, max_attempts: int = 3) -> List['ReceptorMessage']:
        """
        Get messages that failed and need retry
        
        Args:
            session: SQLAlchemy session
            max_attempts: Maximum retry attempts
            
        Returns:
            List of ReceptorMessage objects that need retry
        """
        return session.query(cls).filter(
            cls.estado == 'error',
            cls.enviado == False,
            cls.intentos_envio < max_attempts
        ).order_by(cls.fecha_ultimo_error).all()
    
    @classmethod
    def get_by_receptor(cls, session, receptor_identificacion: str, 
                       limit: int = 50) -> List['ReceptorMessage']:
        """
        Get messages by receptor identification
        
        Args:
            session: SQLAlchemy session
            receptor_identificacion: Receptor identification number
            limit: Maximum number of results
            
        Returns:
            List of ReceptorMessage objects
        """
        return session.query(cls).filter(
            cls.receptor_identificacion_numero == receptor_identificacion
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_statistics(cls, session, fecha_desde: datetime = None, 
                      fecha_hasta: datetime = None) -> dict:
        """
        Get message statistics
        
        Args:
            session: SQLAlchemy session
            fecha_desde: Start date for statistics
            fecha_hasta: End date for statistics
            
        Returns:
            Dictionary with message statistics
        """
        base_query = session.query(cls)
        
        if fecha_desde:
            base_query = base_query.filter(cls.created_at >= fecha_desde)
        
        if fecha_hasta:
            base_query = base_query.filter(cls.created_at <= fecha_hasta)
        
        total = base_query.count()
        
        # Count by message type
        aceptados = base_query.filter(cls.mensaje == 1).count()
        parciales = base_query.filter(cls.mensaje == 2).count()
        rechazados = base_query.filter(cls.mensaje == 3).count()
        
        # Count by status
        enviados = base_query.filter(cls.enviado == True).count()
        pendientes = base_query.filter(cls.enviado == False, cls.estado != 'error').count()
        errores = base_query.filter(cls.estado == 'error').count()
        
        return {
            'total': total,
            'por_tipo': {
                'aceptados': aceptados,
                'parciales': parciales,
                'rechazados': rechazados
            },
            'por_estado': {
                'enviados': enviados,
                'pendientes': pendientes,
                'errores': errores
            },
            'porcentajes': {
                'aceptacion': (aceptados / total * 100) if total > 0 else 0,
                'rechazo': (rechazados / total * 100) if total > 0 else 0,
                'envio_exitoso': (enviados / total * 100) if total > 0 else 0
            }
        }
    
    @classmethod
    def validate_document_key_format(cls, clave_documento: str) -> bool:
        """
        Validate document key format
        
        Args:
            clave_documento: Document key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not clave_documento:
            return False
        
        return len(clave_documento) == 50 and clave_documento.isdigit()
    
    @classmethod
    def validate_issuer_id_format(cls, cedula_emisor: str) -> bool:
        """
        Validate issuer identification format
        
        Args:
            cedula_emisor: Issuer identification to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not cedula_emisor:
            return False
        
        return 9 <= len(cedula_emisor) <= 12 and cedula_emisor.isdigit()