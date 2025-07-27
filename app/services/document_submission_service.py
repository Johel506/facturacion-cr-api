"""
Document submission workflow service for Costa Rica Electronic Invoice API
Handles complete document processing pipeline with intelligent retry logic
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Any, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from app.core.config import settings
from app.models.document import Document
from app.models.tenant import Tenant
from app.services.ministry_service import ministry_service
from app.utils.ministry_response_parser import MinistryResponseParser
from app.utils.ministry_client import (
    MinistryAPIError,
    MinistryAuthenticationError,
    MinistryRateLimitError,
    MinistryValidationError,
    MinistryNetworkError
)

logger = logging.getLogger(__name__)


class DocumentStatus(str, Enum):
    """Document processing status"""
    DRAFT = "borrador"
    PENDING = "pendiente"
    SENDING = "enviando"
    SENT = "enviado"
    PROCESSING = "procesando"
    ACCEPTED = "aceptado"
    REJECTED = "rechazado"
    ERROR = "error"


class SubmissionPriority(str, Enum):
    """Submission priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ErrorCategory(str, Enum):
    """Error categorization for better handling"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    MINISTRY_ERROR = "ministry_error"
    SYSTEM_ERROR = "system_error"


class DocumentSubmissionService:
    """
    Service for managing document submission workflow
    Handles queuing, retry logic, and status tracking
    """
    
    def __init__(self):
        self.max_retries = settings.MINISTRY_MAX_RETRIES
        self.base_retry_delay = settings.MINISTRY_RETRY_DELAY
        self.response_parser = MinistryResponseParser()
        
        # Retry delays by error category (in seconds)
        self.retry_delays = {
            ErrorCategory.VALIDATION: 0,  # Don't retry validation errors
            ErrorCategory.AUTHENTICATION: 60,  # Retry auth errors after 1 minute
            ErrorCategory.RATE_LIMIT: 300,  # Retry rate limit after 5 minutes
            ErrorCategory.NETWORK: 30,  # Retry network errors after 30 seconds
            ErrorCategory.MINISTRY_ERROR: 120,  # Retry ministry errors after 2 minutes
            ErrorCategory.SYSTEM_ERROR: 60  # Retry system errors after 1 minute
        }
        
        logger.info("Document submission service initialized")
    
    async def submit_document(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession,
        priority: SubmissionPriority = SubmissionPriority.NORMAL,
        force_retry: bool = False
    ) -> Dict[str, Any]:
        """
        Submit document through complete processing pipeline
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            db: Database session
            priority: Submission priority
            force_retry: Force retry even if max attempts reached
        
        Returns:
            Submission result with detailed status
        """
        try:
            # Get document and validate
            document = await self._get_and_validate_document(
                document_id, tenant_id, db
            )
            
            # Check if document can be submitted
            if not force_retry and not self._can_submit_document(document):
                return {
                    "success": False,
                    "error": "Document cannot be submitted",
                    "status": document.estado,
                    "reason": self._get_submission_block_reason(document)
                }
            
            # Update document status to indicate submission attempt
            await self._update_document_status(
                document_id, DocumentStatus.SENDING, db,
                increment_attempts=True
            )
            
            # Submit to Ministry
            submission_result = await self._submit_to_ministry(document, db)
            
            # Process Ministry response
            if submission_result["success"]:
                await self._handle_successful_submission(
                    document, submission_result, db
                )
            else:
                await self._handle_failed_submission(
                    document, submission_result, db
                )
            
            return submission_result
            
        except Exception as e:
            logger.error(f"Unexpected error in document submission: {e}")
            await self._handle_system_error(document_id, str(e), db)
            return {
                "success": False,
                "error_category": ErrorCategory.SYSTEM_ERROR,
                "error": str(e),
                "status": DocumentStatus.ERROR
            }
    
    async def process_submission_queue(
        self,
        db: AsyncSession,
        batch_size: int = 10,
        max_processing_time: int = 300
    ) -> Dict[str, Any]:
        """
        Process pending document submissions in queue
        
        Args:
            db: Database session
            batch_size: Number of documents to process in batch
            max_processing_time: Maximum processing time in seconds
        
        Returns:
            Processing results summary
        """
        start_time = datetime.utcnow()
        processed_count = 0
        success_count = 0
        error_count = 0
        results = []
        
        try:
            while (datetime.utcnow() - start_time).seconds < max_processing_time:
                # Get next batch of pending documents
                pending_documents = await self._get_pending_documents(
                    db, batch_size
                )
                
                if not pending_documents:
                    break
                
                # Process each document
                for document in pending_documents:
                    try:
                        result = await self.submit_document(
                            document.id, document.tenant_id, db
                        )
                        
                        processed_count += 1
                        if result["success"]:
                            success_count += 1
                        else:
                            error_count += 1
                        
                        results.append({
                            "document_id": str(document.id),
                            "document_key": document.clave,
                            "result": result
                        })
                        
                        # Add delay between submissions to avoid rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing document {document.id}: {e}")
                        error_count += 1
                        results.append({
                            "document_id": str(document.id),
                            "document_key": document.clave,
                            "result": {"success": False, "error": str(e)}
                        })
                
                # Break if we processed fewer documents than batch size
                if len(pending_documents) < batch_size:
                    break
            
            return {
                "success": True,
                "processed_count": processed_count,
                "success_count": success_count,
                "error_count": error_count,
                "processing_time": (datetime.utcnow() - start_time).seconds,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error processing submission queue: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": processed_count,
                "success_count": success_count,
                "error_count": error_count
            }
    
    async def retry_failed_submissions(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        error_categories: Optional[List[ErrorCategory]] = None,
        max_age_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Retry failed document submissions with intelligent filtering
        
        Args:
            db: Database session
            tenant_id: Specific tenant to retry (optional)
            error_categories: Specific error categories to retry
            max_age_hours: Maximum age of documents to retry
        
        Returns:
            Retry operation results
        """
        try:
            # Get failed documents for retry
            failed_documents = await self._get_failed_documents_for_retry(
                db, tenant_id, error_categories, max_age_hours
            )
            
            retry_results = []
            
            for document in failed_documents:
                # Check if enough time has passed since last attempt
                if not self._should_retry_now(document):
                    continue
                
                logger.info(f"Retrying failed document {document.clave}")
                
                result = await self.submit_document(
                    document.id, document.tenant_id, db, force_retry=True
                )
                
                retry_results.append({
                    "document_id": str(document.id),
                    "document_key": document.clave,
                    "previous_error": document.mensaje_hacienda,
                    "retry_result": result
                })
                
                # Add delay between retries
                await asyncio.sleep(2)
            
            return {
                "success": True,
                "retried_count": len(retry_results),
                "results": retry_results,
                "retried_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error retrying failed submissions: {e}")
            return {
                "success": False,
                "error": str(e),
                "retried_count": 0
            }
    
    async def get_submission_statistics(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get submission statistics for monitoring
        
        Args:
            db: Database session
            tenant_id: Specific tenant (optional)
            days: Number of days to analyze
        
        Returns:
            Submission statistics
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Build base query
            query = select(Document).where(
                Document.created_at >= since_date
            )
            
            if tenant_id:
                query = query.where(Document.tenant_id == tenant_id)
            
            # Get documents
            result = await db.execute(query)
            documents = result.scalars().all()
            
            # Calculate statistics
            stats = {
                "total_documents": len(documents),
                "by_status": {},
                "by_document_type": {},
                "success_rate": 0,
                "average_attempts": 0,
                "error_categories": {}
            }
            
            if documents:
                # Status distribution
                for doc in documents:
                    status = doc.estado
                    stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                    
                    # Document type distribution
                    doc_type = doc.tipo_documento
                    stats["by_document_type"][doc_type] = stats["by_document_type"].get(doc_type, 0) + 1
                
                # Success rate
                successful = stats["by_status"].get(DocumentStatus.ACCEPTED, 0)
                stats["success_rate"] = (successful / len(documents)) * 100
                
                # Average attempts
                total_attempts = sum(doc.intentos_envio for doc in documents)
                stats["average_attempts"] = total_attempts / len(documents)
                
                # Error categorization (simplified)
                failed_docs = [doc for doc in documents if doc.estado in [DocumentStatus.ERROR, DocumentStatus.REJECTED]]
                for doc in failed_docs:
                    category = self._categorize_error(doc.mensaje_hacienda or "")
                    stats["error_categories"][category] = stats["error_categories"].get(category, 0) + 1
            
            return {
                "success": True,
                "period_days": days,
                "tenant_id": str(tenant_id) if tenant_id else "all",
                "statistics": stats,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating submission statistics: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_and_validate_document(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession
    ) -> Document:
        """Get and validate document for submission"""
        query = select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        )
        result = await db.execute(query)
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Document {document_id} not found for tenant {tenant_id}")
        
        if not document.xml_firmado:
            raise ValueError(f"Document {document_id} is not signed")
        
        return document
    
    def _can_submit_document(self, document: Document) -> bool:
        """Check if document can be submitted"""
        # Don't submit if already accepted
        if document.estado == DocumentStatus.ACCEPTED:
            return False
        
        # Don't submit if max retries exceeded (unless forced)
        if document.intentos_envio >= self.max_retries:
            return False
        
        # Don't submit validation errors
        if (document.estado == DocumentStatus.REJECTED and 
            "validation" in (document.mensaje_hacienda or "").lower()):
            return False
        
        return True
    
    def _get_submission_block_reason(self, document: Document) -> str:
        """Get reason why document cannot be submitted"""
        if document.estado == DocumentStatus.ACCEPTED:
            return "Document already accepted"
        
        if document.intentos_envio >= self.max_retries:
            return f"Maximum retry attempts ({self.max_retries}) exceeded"
        
        if (document.estado == DocumentStatus.REJECTED and 
            "validation" in (document.mensaje_hacienda or "").lower()):
            return "Document has validation errors"
        
        return "Unknown reason"
    
    async def _submit_to_ministry(
        self,
        document: Document,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Submit document to Ministry and handle response"""
        try:
            result = await ministry_service.submit_document(
                document.id, document.tenant_id, db
            )
            return result
            
        except Exception as e:
            logger.error(f"Ministry submission error: {e}")
            return {
                "success": False,
                "error_category": self._categorize_exception(e),
                "error": str(e),
                "status": DocumentStatus.ERROR
            }
    
    async def _handle_successful_submission(
        self,
        document: Document,
        result: Dict[str, Any],
        db: AsyncSession
    ):
        """Handle successful document submission"""
        try:
            # Parse Ministry response
            ministry_response = result.get("ministry_response", {})
            parsed_response = self.response_parser.parse_submission_response(
                ministry_response
            )
            
            # Update document with parsed response
            await self._update_document_with_response(
                document.id, parsed_response, db
            )
            
            logger.info(f"Document {document.clave} submitted successfully")
            
        except Exception as e:
            logger.error(f"Error handling successful submission: {e}")
    
    async def _handle_failed_submission(
        self,
        document: Document,
        result: Dict[str, Any],
        db: AsyncSession
    ):
        """Handle failed document submission"""
        try:
            error_category = result.get("error_category", ErrorCategory.SYSTEM_ERROR)
            error_message = result.get("error", "Unknown error")
            
            # Determine next status based on error category
            if error_category == ErrorCategory.VALIDATION:
                status = DocumentStatus.REJECTED
            elif error_category in [ErrorCategory.RATE_LIMIT, ErrorCategory.NETWORK]:
                status = DocumentStatus.PENDING  # Can be retried
            else:
                status = DocumentStatus.ERROR
            
            # Update document status
            await self._update_document_status(
                document.id, status, db, error_message=error_message
            )
            
            logger.warning(f"Document {document.clave} submission failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling failed submission: {e}")
    
    async def _update_document_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        db: AsyncSession,
        error_message: Optional[str] = None,
        ministry_response: Optional[str] = None,
        increment_attempts: bool = False
    ):
        """Update document status in database"""
        try:
            update_values = {
                "estado": status,
                "updated_at": datetime.utcnow()
            }
            
            if error_message:
                update_values["mensaje_hacienda"] = error_message
            
            if ministry_response:
                update_values["xml_respuesta_hacienda"] = ministry_response
            
            if increment_attempts:
                update_values["intentos_envio"] = Document.intentos_envio + 1
            
            if status in [DocumentStatus.SENT, DocumentStatus.ACCEPTED, DocumentStatus.REJECTED]:
                update_values["fecha_procesamiento"] = datetime.utcnow()
            
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(**update_values)
            )
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error updating document status: {e}")
            await db.rollback()
    
    async def _update_document_with_response(
        self,
        document_id: UUID,
        parsed_response: Dict[str, Any],
        db: AsyncSession
    ):
        """Update document with parsed Ministry response"""
        await self._update_document_status(
            document_id=document_id,
            status=parsed_response.get("status", DocumentStatus.SENT),
            db=db,
            error_message=parsed_response.get("message"),
            ministry_response=json.dumps(parsed_response.get("raw_response", {}))
        )
    
    async def _get_pending_documents(
        self,
        db: AsyncSession,
        limit: int
    ) -> List[Document]:
        """Get pending documents for processing"""
        query = select(Document).where(
            and_(
                Document.estado == DocumentStatus.PENDING,
                Document.intentos_envio < self.max_retries,
                Document.xml_firmado.isnot(None)
            )
        ).order_by(Document.created_at).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _get_failed_documents_for_retry(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID],
        error_categories: Optional[List[ErrorCategory]],
        max_age_hours: int
    ) -> List[Document]:
        """Get failed documents eligible for retry"""
        since_date = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        query = select(Document).where(
            and_(
                Document.estado.in_([DocumentStatus.ERROR, DocumentStatus.PENDING]),
                Document.intentos_envio < self.max_retries,
                Document.created_at >= since_date,
                Document.xml_firmado.isnot(None)
            )
        )
        
        if tenant_id:
            query = query.where(Document.tenant_id == tenant_id)
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        # Filter by error categories if specified
        if error_categories:
            filtered_docs = []
            for doc in documents:
                doc_category = self._categorize_error(doc.mensaje_hacienda or "")
                if doc_category in error_categories:
                    filtered_docs.append(doc)
            return filtered_docs
        
        return documents
    
    def _should_retry_now(self, document: Document) -> bool:
        """Check if enough time has passed to retry document"""
        if not document.updated_at:
            return True
        
        # Determine retry delay based on error category
        error_category = self._categorize_error(document.mensaje_hacienda or "")
        retry_delay = self.retry_delays.get(error_category, 60)
        
        # Don't retry validation errors
        if error_category == ErrorCategory.VALIDATION:
            return False
        
        # Check if enough time has passed
        time_since_last_attempt = datetime.utcnow() - document.updated_at
        return time_since_last_attempt.seconds >= retry_delay
    
    def _categorize_exception(self, exception: Exception) -> ErrorCategory:
        """Categorize exception for retry logic"""
        if isinstance(exception, MinistryValidationError):
            return ErrorCategory.VALIDATION
        elif isinstance(exception, MinistryAuthenticationError):
            return ErrorCategory.AUTHENTICATION
        elif isinstance(exception, MinistryRateLimitError):
            return ErrorCategory.RATE_LIMIT
        elif isinstance(exception, MinistryNetworkError):
            return ErrorCategory.NETWORK
        elif isinstance(exception, MinistryAPIError):
            return ErrorCategory.MINISTRY_ERROR
        else:
            return ErrorCategory.SYSTEM_ERROR
    
    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """Categorize error message for retry logic"""
        error_lower = error_message.lower()
        
        # Check authentication first (more specific)
        if any(keyword in error_lower for keyword in ["authentication", "unauthorized", "token"]):
            return ErrorCategory.AUTHENTICATION
        elif any(keyword in error_lower for keyword in ["validation", "invalid", "formato"]):
            return ErrorCategory.VALIDATION
        elif any(keyword in error_lower for keyword in ["rate limit", "too many requests", "429"]):
            return ErrorCategory.RATE_LIMIT
        elif any(keyword in error_lower for keyword in ["network", "connection", "timeout"]):
            return ErrorCategory.NETWORK
        elif any(keyword in error_lower for keyword in ["ministry", "hacienda", "server error"]):
            return ErrorCategory.MINISTRY_ERROR
        else:
            return ErrorCategory.SYSTEM_ERROR
    
    async def _handle_system_error(
        self,
        document_id: UUID,
        error_message: str,
        db: AsyncSession
    ):
        """Handle system errors during submission"""
        try:
            await self._update_document_status(
                document_id, DocumentStatus.ERROR, db, error_message
            )
        except Exception as e:
            logger.error(f"Failed to update document after system error: {e}")


# Global service instance
document_submission_service = DocumentSubmissionService()