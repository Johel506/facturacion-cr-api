"""
Ministry of Finance integration service for Costa Rica Electronic Invoice API
Handles document submission, status tracking, and response processing
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document
from app.models.tenant import Tenant
from app.utils.ministry_client import (
    MinistryClient,
    MinistryAPIError,
    MinistryAuthenticationError,
    MinistryRateLimitError,
    MinistryValidationError,
    MinistryNetworkError
)

logger = logging.getLogger(__name__)


class MinistryService:
    """
    Service for managing Ministry of Finance API interactions
    Handles document submission, status tracking, and error management
    """
    
    def __init__(self):
        self.environment = settings.MINISTRY_ENVIRONMENT
        self.timeout = settings.MINISTRY_TIMEOUT
        self.max_retries = settings.MINISTRY_MAX_RETRIES
        
        # Authentication credentials from settings
        self.default_username = settings.MINISTRY_USERNAME
        self.default_password = settings.MINISTRY_PASSWORD
        self.default_client_id = settings.MINISTRY_CLIENT_ID
        self.default_client_secret = settings.MINISTRY_CLIENT_SECRET
        
        if not self.default_username or not self.default_password or not self.default_client_id:
            logger.warning("Ministry authentication credentials not configured in settings")
        
        logger.info(f"Ministry service initialized for {self.environment} environment")
    
    def _get_ministry_client(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> MinistryClient:
        """
        Create Ministry API client with appropriate credentials
        
        Args:
            username: Ministry username (uses default if not provided)
            password: Ministry password (uses default if not provided)
            client_id: OAuth2 client ID (uses default if not provided)
            client_secret: OAuth2 client secret (uses default if not provided)
        
        Returns:
            Configured MinistryClient instance
        """
        return MinistryClient(
            username=username or self.default_username,
            password=password or self.default_password,
            client_id=client_id or self.default_client_id,
            client_secret=client_secret or self.default_client_secret,
            environment=self.environment,
            timeout=self.timeout
        )
    
    async def submit_document(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Submit document to Ministry of Finance
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            db: Database session
        
        Returns:
            Submission result with status and Ministry response
        """
        try:
            # Get document and tenant from database
            document_query = select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id
            )
            document_result = await db.execute(document_query)
            document = document_result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found for tenant {tenant_id}")
            
            if not document.xml_firmado:
                raise ValueError(f"Document {document_id} is not signed")
            
            # Get tenant for potential custom credentials
            tenant_query = select(Tenant).where(Tenant.id == tenant_id)
            tenant_result = await db.execute(tenant_query)
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant or not tenant.activo:
                raise ValueError(f"Tenant {tenant_id} not found or inactive")
            
            # Update document status to indicate submission attempt
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    estado="enviando",
                    intentos_envio=Document.intentos_envio + 1,
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            # Submit to Ministry
            async with self._get_ministry_client() as client:
                ministry_response = await client.submit_document(
                    document_xml=document.xml_firmado,
                    document_key=document.clave,
                    document_type=document.tipo_documento,
                    callback_url=settings.MINISTRY_CALLBACK_URL
                )
            
            # Update document with Ministry response
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    estado="enviado",
                    xml_respuesta_hacienda=str(ministry_response),
                    fecha_procesamiento=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Document {document.clave} submitted successfully to Ministry")
            
            return {
                "success": True,
                "document_key": document.clave,
                "ministry_response": ministry_response,
                "status": "enviado",
                "submitted_at": datetime.utcnow().isoformat()
            }
            
        except MinistryValidationError as e:
            # Document validation failed
            await self._handle_submission_error(
                document_id, db, "rechazado", f"Validation error: {e}"
            )
            logger.error(f"Document validation failed: {e}")
            return {
                "success": False,
                "error_type": "validation",
                "error": str(e),
                "status": "rechazado"
            }
            
        except MinistryRateLimitError as e:
            # Rate limit exceeded - keep as pending for retry
            await self._handle_submission_error(
                document_id, db, "pendiente", f"Rate limit exceeded: {e}"
            )
            logger.warning(f"Rate limit exceeded: {e}")
            return {
                "success": False,
                "error_type": "rate_limit",
                "error": str(e),
                "status": "pendiente",
                "retry_after": self._extract_retry_after(str(e))
            }
            
        except MinistryAuthenticationError as e:
            # Authentication failed
            await self._handle_submission_error(
                document_id, db, "error", f"Authentication error: {e}"
            )
            logger.error(f"Ministry authentication failed: {e}")
            return {
                "success": False,
                "error_type": "authentication",
                "error": str(e),
                "status": "error"
            }
            
        except MinistryNetworkError as e:
            # Network error - keep as pending for retry
            await self._handle_submission_error(
                document_id, db, "pendiente", f"Network error: {e}"
            )
            logger.error(f"Network error submitting document: {e}")
            return {
                "success": False,
                "error_type": "network",
                "error": str(e),
                "status": "pendiente"
            }
            
        except Exception as e:
            # Unexpected error
            await self._handle_submission_error(
                document_id, db, "error", f"Unexpected error: {e}"
            )
            logger.error(f"Unexpected error submitting document: {e}")
            return {
                "success": False,
                "error_type": "unexpected",
                "error": str(e),
                "status": "error"
            }
    
    async def check_document_status(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Check document status with Ministry
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            db: Database session
        
        Returns:
            Status check result
        """
        try:
            # Get document from database
            document_query = select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id
            )
            document_result = await db.execute(document_query)
            document = document_result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found for tenant {tenant_id}")
            
            # Check status with Ministry
            async with self._get_ministry_client() as client:
                status_response = await client.check_document_status(document.clave)
            
            # Parse Ministry status
            ministry_status = self._parse_ministry_status(status_response)
            
            # Update document if status changed
            if ministry_status["status"] != document.estado:
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(
                        estado=ministry_status["status"],
                        mensaje_hacienda=ministry_status.get("message"),
                        xml_respuesta_hacienda=str(status_response),
                        updated_at=datetime.utcnow()
                    )
                )
                await db.commit()
                
                logger.info(
                    f"Document {document.clave} status updated to {ministry_status['status']}"
                )
            
            return {
                "success": True,
                "document_key": document.clave,
                "status": ministry_status["status"],
                "message": ministry_status.get("message"),
                "ministry_response": status_response,
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check document status: {e}")
            return {
                "success": False,
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
    
    async def submit_receptor_message(
        self,
        message_xml: str,
        document_key: str,
        message_type: int,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Submit receptor message to Ministry
        
        Args:
            message_xml: Signed receptor message XML
            document_key: Original document key
            message_type: 1=Accepted, 2=Partial, 3=Rejected
            tenant_id: Tenant UUID
        
        Returns:
            Submission result
        """
        try:
            async with self._get_ministry_client() as client:
                ministry_response = await client.submit_receptor_message(
                    message_xml=message_xml,
                    document_key=document_key,
                    message_type=message_type
                )
            
            logger.info(f"Receptor message submitted for document {document_key}")
            
            return {
                "success": True,
                "document_key": document_key,
                "message_type": message_type,
                "ministry_response": ministry_response,
                "submitted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to submit receptor message: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_key": document_key,
                "message_type": message_type
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Ministry API
        
        Returns:
            Health status information
        """
        try:
            async with self._get_ministry_client() as client:
                health_status = await client.health_check()
            
            return {
                "ministry_api": health_status,
                "service_status": "healthy",
                "environment": self.environment,
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ministry health check failed: {e}")
            return {
                "ministry_api": {"status": "unhealthy", "error": str(e)},
                "service_status": "degraded",
                "environment": self.environment,
                "checked_at": datetime.utcnow().isoformat()
            }
    
    async def retry_failed_documents(
        self,
        tenant_id: Optional[UUID] = None,
        max_retries: int = 3,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Retry failed document submissions
        
        Args:
            tenant_id: Specific tenant ID (optional, retries all if None)
            max_retries: Maximum retry attempts
            db: Database session
        
        Returns:
            Retry operation results
        """
        try:
            # Build query for failed documents
            query = select(Document).where(
                Document.estado.in_(["pendiente", "error"]),
                Document.intentos_envio < max_retries
            )
            
            if tenant_id:
                query = query.where(Document.tenant_id == tenant_id)
            
            # Get failed documents
            result = await db.execute(query)
            failed_documents = result.scalars().all()
            
            retry_results = []
            
            for document in failed_documents:
                logger.info(f"Retrying document {document.clave}")
                
                result = await self.submit_document(
                    document_id=document.id,
                    tenant_id=document.tenant_id,
                    db=db
                )
                
                retry_results.append({
                    "document_id": str(document.id),
                    "document_key": document.clave,
                    "result": result
                })
                
                # Add delay between retries to avoid rate limiting
                await asyncio.sleep(1)
            
            return {
                "success": True,
                "retried_count": len(retry_results),
                "results": retry_results,
                "retried_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to retry documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "retried_count": 0
            }
    
    async def _handle_submission_error(
        self,
        document_id: UUID,
        db: AsyncSession,
        status: str,
        error_message: str
    ):
        """Handle submission error by updating document status"""
        try:
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    estado=status,
                    mensaje_hacienda=error_message,
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to update document error status: {e}")
    
    def _parse_ministry_status(self, ministry_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Ministry status response into standardized format
        
        Args:
            ministry_response: Raw Ministry API response
        
        Returns:
            Parsed status information
        """
        # This is a simplified parser - actual implementation would depend on
        # the exact format of Ministry responses
        status_map = {
            "recibido": "enviado",
            "procesando": "procesando",
            "aceptado": "aceptado",
            "rechazado": "rechazado",
            "error": "error"
        }
        
        raw_status = ministry_response.get("estado", "unknown")
        mapped_status = status_map.get(raw_status, "error")
        
        return {
            "status": mapped_status,
            "message": ministry_response.get("mensaje"),
            "raw_response": ministry_response
        }
    
    def _extract_retry_after(self, error_message: str) -> Optional[int]:
        """Extract retry-after value from error message"""
        # Simple extraction - could be more sophisticated
        import re
        match = re.search(r"retry_after['\"]?\s*:\s*(\d+)", error_message)
        if match:
            return int(match.group(1))
        return None


# Global service instance
ministry_service = MinistryService()