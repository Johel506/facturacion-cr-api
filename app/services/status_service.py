"""
Ministry status management service for Costa Rica Electronic Invoice API
Handles document status polling, updates, and automatic resubmission
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func

from app.core.config import settings
from app.models.document import Document
from app.models.tenant import Tenant
from app.services.ministry_service import ministry_service
from app.services.document_submission_service import (
    document_submission_service,
    DocumentStatus,
    ErrorCategory
)
from app.utils.ministry_response_parser import MinistryResponseParser
from app.utils.error_parser import ErrorParser

logger = logging.getLogger(__name__)


class StatusService:
    """
    Service for managing Ministry document status polling and updates
    Handles automatic status checking, resubmission, and error management
    """
    
    def __init__(self):
        self.response_parser = MinistryResponseParser()
        self.error_parser = ErrorParser()
        
        # Status polling configuration
        self.polling_intervals = {
            DocumentStatus.SENT: 300,      # 5 minutes for sent documents
            DocumentStatus.PROCESSING: 600, # 10 minutes for processing documents
            DocumentStatus.PENDING: 1800,   # 30 minutes for pending documents
            DocumentStatus.ERROR: 3600      # 1 hour for error documents
        }
        
        # Automatic resubmission configuration
        self.resubmission_delays = {
            ErrorCategory.NETWORK: 1800,        # 30 minutes for network errors
            ErrorCategory.RATE_LIMIT: 3600,     # 1 hour for rate limit errors
            ErrorCategory.MINISTRY_ERROR: 7200, # 2 hours for ministry errors
            ErrorCategory.SYSTEM_ERROR: 3600    # 1 hour for system errors
        }
        
        logger.info("Status service initialized")
    
    async def poll_document_status(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Poll Ministry for document status and update local record
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            db: Database session
            force_update: Force status check regardless of polling interval
        
        Returns:
            Status polling result
        """
        try:
            # Get document from database
            document = await self._get_document(document_id, tenant_id, db)
            
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found",
                    "document_id": str(document_id)
                }
            
            # Check if polling is needed
            if not force_update and not self._should_poll_status(document):
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "Polling not needed yet",
                    "document_key": document.clave,
                    "current_status": document.estado,
                    "next_poll_at": self._calculate_next_poll_time(document).isoformat()
                }
            
            # Poll Ministry for status
            status_result = await ministry_service.check_document_status(
                document_id, tenant_id, db
            )
            
            if not status_result["success"]:
                return {
                    "success": False,
                    "error": status_result.get("error", "Status check failed"),
                    "document_key": document.clave,
                    "current_status": document.estado
                }
            
            # Parse and process status response
            parsed_status = self.response_parser.parse_status_response(
                status_result.get("ministry_response", {})
            )
            
            # Update document status if changed
            status_changed = False
            if parsed_status["status"] != document.estado:
                await self._update_document_status(
                    document, parsed_status, db
                )
                status_changed = True
            
            # Handle status-specific actions
            await self._handle_status_change(document, parsed_status, db)
            
            return {
                "success": True,
                "document_key": document.clave,
                "previous_status": document.estado,
                "current_status": parsed_status["status"],
                "status_changed": status_changed,
                "message": parsed_status.get("message"),
                "ministry_response": status_result.get("ministry_response"),
                "polled_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error polling document status: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": str(document_id),
                "polled_at": datetime.utcnow().isoformat()
            }
    
    async def poll_pending_documents(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        batch_size: int = 50,
        max_processing_time: int = 600
    ) -> Dict[str, Any]:
        """
        Poll status for all pending documents
        
        Args:
            db: Database session
            tenant_id: Specific tenant (optional)
            batch_size: Number of documents to process in batch
            max_processing_time: Maximum processing time in seconds
        
        Returns:
            Batch polling results
        """
        start_time = datetime.utcnow()
        processed_count = 0
        updated_count = 0
        error_count = 0
        results = []
        
        try:
            while (datetime.utcnow() - start_time).seconds < max_processing_time:
                # Get documents that need status polling
                documents = await self._get_documents_for_polling(
                    db, tenant_id, batch_size
                )
                
                if not documents:
                    break
                
                # Poll status for each document
                for document in documents:
                    try:
                        result = await self.poll_document_status(
                            document.id, document.tenant_id, db
                        )
                        
                        processed_count += 1
                        if result["success"]:
                            if result.get("status_changed"):
                                updated_count += 1
                        else:
                            error_count += 1
                        
                        results.append({
                            "document_id": str(document.id),
                            "document_key": document.clave,
                            "result": result
                        })
                        
                        # Add delay between polls to avoid rate limiting
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error polling document {document.id}: {e}")
                        error_count += 1
                        results.append({
                            "document_id": str(document.id),
                            "document_key": document.clave,
                            "result": {"success": False, "error": str(e)}
                        })
                
                # Break if we processed fewer documents than batch size
                if len(documents) < batch_size:
                    break
            
            return {
                "success": True,
                "processed_count": processed_count,
                "updated_count": updated_count,
                "error_count": error_count,
                "processing_time": (datetime.utcnow() - start_time).seconds,
                "results": results,
                "polled_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in batch status polling: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": processed_count,
                "updated_count": updated_count,
                "error_count": error_count
            }
    
    async def handle_document_acceptance(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession,
        ministry_xml: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle document acceptance by Ministry
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            db: Database session
            ministry_xml: Ministry-signed XML response
        
        Returns:
            Acceptance handling result
        """
        try:
            document = await self._get_document(document_id, tenant_id, db)
            
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
            
            # Update document status to accepted
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    estado=DocumentStatus.ACCEPTED,
                    fecha_procesamiento=datetime.utcnow(),
                    xml_respuesta_hacienda=ministry_xml,
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Document {document.clave} accepted by Ministry")
            
            return {
                "success": True,
                "document_key": document.clave,
                "status": DocumentStatus.ACCEPTED,
                "accepted_at": datetime.utcnow().isoformat(),
                "ministry_xml_available": bool(ministry_xml)
            }
            
        except Exception as e:
            logger.error(f"Error handling document acceptance: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": str(document_id)
            }
    
    async def handle_document_rejection(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession,
        rejection_reason: str,
        error_details: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Handle document rejection by Ministry
        
        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            db: Database session
            rejection_reason: Reason for rejection
            error_details: Detailed error information
        
        Returns:
            Rejection handling result
        """
        try:
            document = await self._get_document(document_id, tenant_id, db)
            
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
            
            # Parse rejection details
            parsed_errors = self.error_parser.parse_rejection_errors(
                rejection_reason, error_details
            )
            
            # Update document status to rejected
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    estado=DocumentStatus.REJECTED,
                    mensaje_hacienda=rejection_reason,
                    fecha_procesamiento=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.warning(f"Document {document.clave} rejected by Ministry: {rejection_reason}")
            
            return {
                "success": True,
                "document_key": document.clave,
                "status": DocumentStatus.REJECTED,
                "rejection_reason": rejection_reason,
                "error_details": parsed_errors,
                "is_correctable": parsed_errors.get("is_correctable", False),
                "suggestions": parsed_errors.get("suggestions", []),
                "rejected_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling document rejection: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": str(document_id)
            }
    
    async def auto_resubmit_failed_documents(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        max_documents: int = 20
    ) -> Dict[str, Any]:
        """
        Automatically resubmit failed documents based on error category and timing
        
        Args:
            db: Database session
            tenant_id: Specific tenant (optional)
            max_documents: Maximum number of documents to resubmit
        
        Returns:
            Auto-resubmission results
        """
        try:
            # Get documents eligible for auto-resubmission
            eligible_documents = await self._get_documents_for_resubmission(
                db, tenant_id, max_documents
            )
            
            resubmission_results = []
            
            for document in eligible_documents:
                try:
                    # Determine if document should be resubmitted
                    should_resubmit, reason = self._should_auto_resubmit(document)
                    
                    if not should_resubmit:
                        continue
                    
                    logger.info(f"Auto-resubmitting document {document.clave}: {reason}")
                    
                    # Resubmit document
                    result = await document_submission_service.submit_document(
                        document.id, document.tenant_id, db, force_retry=True
                    )
                    
                    resubmission_results.append({
                        "document_id": str(document.id),
                        "document_key": document.clave,
                        "reason": reason,
                        "result": result
                    })
                    
                    # Add delay between resubmissions
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error auto-resubmitting document {document.id}: {e}")
                    resubmission_results.append({
                        "document_id": str(document.id),
                        "document_key": document.clave,
                        "result": {"success": False, "error": str(e)}
                    })
            
            return {
                "success": True,
                "resubmitted_count": len(resubmission_results),
                "results": resubmission_results,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in auto-resubmission: {e}")
            return {
                "success": False,
                "error": str(e),
                "resubmitted_count": 0
            }
    
    async def get_status_summary(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get status summary for monitoring and reporting
        
        Args:
            db: Database session
            tenant_id: Specific tenant (optional)
            hours: Time period to analyze
        
        Returns:
            Status summary information
        """
        try:
            since_date = datetime.utcnow() - timedelta(hours=hours)
            
            # Build base query
            query = select(Document).where(
                Document.updated_at >= since_date
            )
            
            if tenant_id:
                query = query.where(Document.tenant_id == tenant_id)
            
            # Get documents
            result = await db.execute(query)
            documents = result.scalars().all()
            
            # Calculate summary statistics
            summary = {
                "total_documents": len(documents),
                "status_distribution": {},
                "processing_times": {},
                "error_analysis": {},
                "pending_actions": {
                    "needs_polling": 0,
                    "needs_resubmission": 0,
                    "needs_attention": 0
                }
            }
            
            if documents:
                # Status distribution
                for doc in documents:
                    status = doc.estado
                    summary["status_distribution"][status] = summary["status_distribution"].get(status, 0) + 1
                    
                    # Calculate processing times for completed documents
                    if doc.fecha_procesamiento and doc.created_at:
                        processing_time = (doc.fecha_procesamiento - doc.created_at).total_seconds()
                        if status not in summary["processing_times"]:
                            summary["processing_times"][status] = []
                        summary["processing_times"][status].append(processing_time)
                    
                    # Analyze pending actions
                    if self._should_poll_status(doc):
                        summary["pending_actions"]["needs_polling"] += 1
                    
                    if self._should_auto_resubmit(doc)[0]:
                        summary["pending_actions"]["needs_resubmission"] += 1
                    
                    if doc.estado in [DocumentStatus.ERROR, DocumentStatus.REJECTED]:
                        summary["pending_actions"]["needs_attention"] += 1
                
                # Calculate average processing times
                for status, times in summary["processing_times"].items():
                    if times:
                        summary["processing_times"][status] = {
                            "average": sum(times) / len(times),
                            "min": min(times),
                            "max": max(times),
                            "count": len(times)
                        }
            
            return {
                "success": True,
                "period_hours": hours,
                "tenant_id": str(tenant_id) if tenant_id else "all",
                "summary": summary,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating status summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_document(
        self,
        document_id: UUID,
        tenant_id: UUID,
        db: AsyncSession
    ) -> Optional[Document]:
        """Get document from database"""
        query = select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    def _should_poll_status(self, document: Document) -> bool:
        """Check if document status should be polled"""
        # Don't poll final states
        if document.estado in [DocumentStatus.ACCEPTED, DocumentStatus.REJECTED]:
            return False
        
        # Don't poll if no last update time
        if not document.updated_at:
            return True
        
        # Check polling interval
        interval = self.polling_intervals.get(document.estado, 3600)
        time_since_update = datetime.utcnow() - document.updated_at
        
        return time_since_update.seconds >= interval
    
    def _calculate_next_poll_time(self, document: Document) -> datetime:
        """Calculate next polling time for document"""
        if not document.updated_at:
            return datetime.utcnow()
        
        interval = self.polling_intervals.get(document.estado, 3600)
        return document.updated_at + timedelta(seconds=interval)
    
    async def _get_documents_for_polling(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID],
        limit: int
    ) -> List[Document]:
        """Get documents that need status polling"""
        # Calculate cutoff times for each status
        now = datetime.utcnow()
        cutoff_conditions = []
        
        for status, interval in self.polling_intervals.items():
            cutoff_time = now - timedelta(seconds=interval)
            cutoff_conditions.append(
                and_(
                    Document.estado == status,
                    or_(
                        Document.updated_at.is_(None),
                        Document.updated_at <= cutoff_time
                    )
                )
            )
        
        # Build query
        query = select(Document).where(
            or_(*cutoff_conditions)
        ).order_by(Document.updated_at.asc()).limit(limit)
        
        if tenant_id:
            query = query.where(Document.tenant_id == tenant_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _get_documents_for_resubmission(
        self,
        db: AsyncSession,
        tenant_id: Optional[UUID],
        limit: int
    ) -> List[Document]:
        """Get documents eligible for auto-resubmission"""
        query = select(Document).where(
            and_(
                Document.estado.in_([DocumentStatus.ERROR, DocumentStatus.PENDING]),
                Document.intentos_envio < settings.MINISTRY_MAX_RETRIES,
                Document.xml_firmado.isnot(None)
            )
        ).order_by(Document.updated_at.asc()).limit(limit)
        
        if tenant_id:
            query = query.where(Document.tenant_id == tenant_id)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    def _should_auto_resubmit(self, document: Document) -> Tuple[bool, str]:
        """Check if document should be auto-resubmitted"""
        # Don't resubmit final states
        if document.estado in [DocumentStatus.ACCEPTED, DocumentStatus.REJECTED]:
            return False, "Document in final state"
        
        # Don't resubmit if max retries exceeded
        if document.intentos_envio >= settings.MINISTRY_MAX_RETRIES:
            return False, "Max retries exceeded"
        
        # Don't resubmit validation errors
        if (document.mensaje_hacienda and 
            "validation" in document.mensaje_hacienda.lower()):
            return False, "Validation error - manual correction needed"
        
        # Check if enough time has passed
        if not document.updated_at:
            return True, "No previous attempt timestamp"
        
        # Determine error category and delay
        error_category = document_submission_service._categorize_error(
            document.mensaje_hacienda or ""
        )
        
        required_delay = self.resubmission_delays.get(error_category, 3600)
        time_since_update = datetime.utcnow() - document.updated_at
        
        if time_since_update.seconds >= required_delay:
            return True, f"Retry delay ({required_delay}s) elapsed for {error_category}"
        
        return False, f"Retry delay not elapsed ({time_since_update.seconds}/{required_delay}s)"
    
    async def _update_document_status(
        self,
        document: Document,
        parsed_status: Dict[str, Any],
        db: AsyncSession
    ):
        """Update document status based on parsed Ministry response"""
        update_values = {
            "estado": parsed_status["status"],
            "updated_at": datetime.utcnow()
        }
        
        if parsed_status.get("message"):
            update_values["mensaje_hacienda"] = parsed_status["message"]
        
        if parsed_status.get("ministry_xml"):
            update_values["xml_respuesta_hacienda"] = parsed_status["ministry_xml"]
        
        if parsed_status["status"] in [DocumentStatus.ACCEPTED, DocumentStatus.REJECTED]:
            update_values["fecha_procesamiento"] = datetime.utcnow()
        
        await db.execute(
            update(Document)
            .where(Document.id == document.id)
            .values(**update_values)
        )
        await db.commit()
    
    async def _handle_status_change(
        self,
        document: Document,
        parsed_status: Dict[str, Any],
        db: AsyncSession
    ):
        """Handle status-specific actions when document status changes"""
        new_status = parsed_status["status"]
        
        if new_status == DocumentStatus.ACCEPTED:
            await self.handle_document_acceptance(
                document.id, document.tenant_id, db,
                parsed_status.get("ministry_xml")
            )
        elif new_status == DocumentStatus.REJECTED:
            await self.handle_document_rejection(
                document.id, document.tenant_id, db,
                parsed_status.get("rejection_reason", "Document rejected"),
                parsed_status.get("error_details")
            )


# Global service instance
status_service = StatusService()