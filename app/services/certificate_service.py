"""
Advanced certificate management service for Costa Rica invoice API.
Handles P12 certificate upload, validation, caching, and expiration notifications.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend

from app.models.tenant import Tenant
from app.schemas.tenants import CertificateUpload, CertificateStatus
from app.utils.certificate_utils import (
    P12CertificateManager, CertificateExpirationNotifier,
    validate_p12_certificate_file, check_certificate_expiration,
    get_certificate_info, CertificateValidationResult, CertificateInfo
)
from app.utils.crypto_utils import (
    encrypt_certificate_for_storage, decrypt_certificate_from_storage,
    encrypt_password_for_storage, decrypt_password_from_storage,
    create_data_integrity_hash
)
from app.core.redis import get_redis_client
from app.core.config import settings


class CertificateService:
    """
    Advanced certificate management service
    
    Handles P12 certificate upload, validation, secure storage, caching,
    and automated expiration notifications.
    
    Requirements: 1.2, 3.6, 8.3
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.redis_client = get_redis_client()
        self.cache_ttl = settings.CERTIFICATE_CACHE_TTL
    
    async def upload_certificate(
        self, 
        tenant_id: UUID, 
        certificate_upload: CertificateUpload
    ) -> Tuple[bool, CertificateStatus, List[str]]:
        """
        Upload and validate P12 certificate with secure storage
        
        Args:
            tenant_id: Tenant UUID
            certificate_upload: Certificate upload data
            
        Returns:
            Tuple of (success, certificate_status, validation_errors)
            
        Requirements: 1.2 - P12 certificate upload with validation and secure storage
        """
        try:
            # Get tenant
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                return False, None, ["Tenant not found"]
            
            # Validate certificate size
            if len(certificate_upload.certificado_p12) > settings.MAX_CERTIFICATE_SIZE:
                return False, None, [f"Certificate size exceeds maximum allowed ({settings.MAX_CERTIFICATE_SIZE} bytes)"]
            
            # Validate P12 certificate
            validation_result = validate_p12_certificate_file(
                certificate_upload.certificado_p12,
                certificate_upload.password_certificado
            )
            
            if not validation_result.is_valid:
                return False, None, validation_result.errors
            
            # Extract certificate information
            cert_info = validation_result.certificate_info
            
            # Check certificate compatibility
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    certificate_upload.certificado_p12,
                    certificate_upload.password_certificado.encode('utf-8'),
                    backend=default_backend()
                )
                
                is_compatible, compatibility_issues = P12CertificateManager.check_certificate_compatibility(certificate)
                if not is_compatible:
                    return False, None, compatibility_issues
                
            except Exception as e:
                return False, None, [f"Failed to parse certificate: {e}"]
            
            # Encrypt certificate and password for storage
            encrypted_cert = encrypt_certificate_for_storage(certificate_upload.certificado_p12)
            encrypted_password = encrypt_password_for_storage(certificate_upload.password_certificado)
            
            # Create certificate fingerprint for integrity verification
            fingerprint = create_data_integrity_hash(certificate_upload.certificado_p12)
            
            # Update tenant with certificate information
            tenant.certificado_p12 = encrypted_cert.encode('utf-8')  # Store as bytes in DB
            tenant.password_certificado = encrypted_password
            tenant.certificado_uploaded_at = datetime.now(timezone.utc)
            tenant.certificado_expires_at = cert_info.not_valid_after
            tenant.certificado_subject = cert_info.subject
            tenant.certificado_issuer = cert_info.issuer
            tenant.updated_at = datetime.now(timezone.utc)
            
            # Commit to database
            self.db.commit()
            self.db.refresh(tenant)
            
            # Cache certificate in Redis for performance
            await self._cache_certificate(tenant_id, certificate_upload.certificado_p12, certificate_upload.password_certificado)
            
            # Schedule expiration notifications
            await self._schedule_expiration_notifications(tenant_id, cert_info.not_valid_after)
            
            # Create certificate status
            cert_status = CertificateStatus(
                tiene_certificado=True,
                fecha_vencimiento=cert_info.not_valid_after,
                valido=True,
                emisor=cert_info.issuer,
                sujeto=cert_info.subject,
                numero_serie=cert_info.serial_number
            )
            
            # Log certificate upload
            self._log_certificate_activity(tenant_id, "certificate_uploaded", {
                "subject": cert_info.subject,
                "issuer": cert_info.issuer,
                "expires_at": cert_info.not_valid_after.isoformat(),
                "fingerprint": fingerprint
            })
            
            return True, cert_status, validation_result.warnings
            
        except Exception as e:
            self.db.rollback()
            return False, None, [f"Failed to upload certificate: {str(e)}"]
    
    async def get_certificate_status(self, tenant_id: UUID) -> Optional[CertificateStatus]:
        """
        Get certificate status and expiration information
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Certificate status or None if no certificate
            
        Requirements: 3.6 - Certificate expiration checking
        """
        try:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant or not tenant.has_certificate:
                return CertificateStatus(
                    tiene_certificado=False,
                    valido=False
                )
            
            # Check if certificate is cached
            cached_status = await self._get_cached_certificate_status(tenant_id)
            if cached_status:
                return cached_status
            
            # Decrypt certificate and get detailed status
            try:
                encrypted_cert = tenant.certificado_p12.decode('utf-8') if isinstance(tenant.certificado_p12, bytes) else tenant.certificado_p12
                cert_data = decrypt_certificate_from_storage(encrypted_cert)
                password = decrypt_password_from_storage(tenant.password_certificado)
                
                # Get certificate info
                cert_info = get_certificate_info(cert_data, password)
                
                cert_status = CertificateStatus(
                    tiene_certificado=True,
                    fecha_vencimiento=cert_info.not_valid_after,
                    valido=cert_info.is_valid,
                    emisor=cert_info.issuer,
                    sujeto=cert_info.subject,
                    numero_serie=cert_info.serial_number
                )
                
                # Cache the status
                await self._cache_certificate_status(tenant_id, cert_status)
                
                return cert_status
                
            except Exception as e:
                # Return basic status if decryption fails
                return CertificateStatus(
                    tiene_certificado=True,
                    fecha_vencimiento=tenant.certificado_expires_at,
                    valido=not tenant.certificate_expired,
                    emisor=tenant.certificado_issuer,
                    sujeto=tenant.certificado_subject
                )
                
        except Exception as e:
            return None
    
    async def validate_certificate(self, tenant_id: UUID) -> Tuple[bool, List[str], List[str]]:
        """
        Validate tenant's certificate and return detailed results
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Tuple of (is_valid, errors, warnings)
            
        Requirements: 1.2 - Certificate parsing, validation, and expiration checking
        """
        try:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant or not tenant.has_certificate:
                return False, ["No certificate found"], []
            
            # Decrypt certificate
            encrypted_cert = tenant.certificado_p12.decode('utf-8') if isinstance(tenant.certificado_p12, bytes) else tenant.certificado_p12
            cert_data = decrypt_certificate_from_storage(encrypted_cert)
            password = decrypt_password_from_storage(tenant.password_certificado)
            
            # Validate certificate
            validation_result = validate_p12_certificate_file(cert_data, password)
            
            return validation_result.is_valid, validation_result.errors, validation_result.warnings
            
        except Exception as e:
            return False, [f"Certificate validation failed: {str(e)}"], []
    
    async def get_certificate_for_signing(self, tenant_id: UUID) -> Optional[Tuple[bytes, str]]:
        """
        Get certificate data for digital signing
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Tuple of (certificate_data, password) or None if not available
            
        Requirements: 8.3 - Certificate caching in Redis with TTL management
        """
        try:
            # Try to get from cache first
            cached_cert = await self._get_cached_certificate(tenant_id)
            if cached_cert:
                return cached_cert
            
            # Get from database
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant or not tenant.has_certificate:
                return None
            
            # Decrypt certificate
            encrypted_cert = tenant.certificado_p12.decode('utf-8') if isinstance(tenant.certificado_p12, bytes) else tenant.certificado_p12
            cert_data = decrypt_certificate_from_storage(encrypted_cert)
            password = decrypt_password_from_storage(tenant.password_certificado)
            
            # Cache for future use
            await self._cache_certificate(tenant_id, cert_data, password)
            
            return cert_data, password
            
        except Exception as e:
            return None
    
    async def remove_certificate(self, tenant_id: UUID) -> bool:
        """
        Remove certificate from tenant
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                return False
            
            # Clear certificate data
            tenant.certificado_p12 = None
            tenant.password_certificado = None
            tenant.certificado_uploaded_at = None
            tenant.certificado_expires_at = None
            tenant.certificado_subject = None
            tenant.certificado_issuer = None
            tenant.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            # Clear cache
            await self._clear_certificate_cache(tenant_id)
            
            # Log certificate removal
            self._log_certificate_activity(tenant_id, "certificate_removed", {
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    async def check_expiration_notifications(self) -> List[Dict[str, Any]]:
        """
        Check all certificates for expiration notifications
        
        Returns:
            List of notification data for certificates that need notifications
            
        Requirements: 3.6 - Automated certificate expiration notification system (30, 15, 7 days)
        """
        notifications = []
        
        try:
            # Get all tenants with certificates
            tenants_with_certs = self.db.query(Tenant).filter(
                Tenant.certificado_p12.isnot(None),
                Tenant.activo == True
            ).all()
            
            for tenant in tenants_with_certs:
                try:
                    # Get certificate
                    encrypted_cert = tenant.certificado_p12.decode('utf-8') if isinstance(tenant.certificado_p12, bytes) else tenant.certificado_p12
                    cert_data = decrypt_certificate_from_storage(encrypted_cert)
                    password = decrypt_password_from_storage(tenant.password_certificado)
                    
                    # Parse certificate
                    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                        cert_data, password.encode('utf-8'), backend=default_backend()
                    )
                    
                    if certificate:
                        # Check if notification should be sent
                        notification_days = [int(d) for d in tenant.dias_notificacion_certificado.split(',')]
                        should_notify, level, days_until = CertificateExpirationNotifier.should_notify_expiration(
                            certificate, notification_days
                        )
                        
                        if should_notify and tenant.notificar_vencimiento_certificado:
                            # Check if we've already sent this notification recently
                            if not await self._was_notification_sent_recently(tenant.id, level, days_until):
                                notification_message = CertificateExpirationNotifier.get_notification_message(
                                    days_until, tenant.certificado_subject or "Unknown Certificate"
                                )
                                
                                notifications.append({
                                    "tenant_id": tenant.id,
                                    "tenant_name": tenant.nombre_empresa,
                                    "email": tenant.email_contacto,
                                    "certificate_subject": tenant.certificado_subject,
                                    "days_until_expiration": days_until,
                                    "level": level,
                                    "notification": notification_message
                                })
                                
                                # Mark notification as sent
                                await self._mark_notification_sent(tenant.id, level, days_until)
                
                except Exception as e:
                    # Log error but continue with other certificates
                    self._log_certificate_activity(tenant.id, "notification_check_error", {
                        "error": str(e)
                    })
                    continue
            
            return notifications
            
        except Exception as e:
            return []
    
    async def get_certificate_chain_validation(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Validate certificate chain and issuer verification
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Dictionary with chain validation results
            
        Requirements: 1.2 - Certificate chain validation and issuer verification
        """
        try:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant or not tenant.has_certificate:
                return {"valid": False, "error": "No certificate found"}
            
            # Decrypt certificate
            encrypted_cert = tenant.certificado_p12.decode('utf-8') if isinstance(tenant.certificado_p12, bytes) else tenant.certificado_p12
            cert_data = decrypt_certificate_from_storage(encrypted_cert)
            password = decrypt_password_from_storage(tenant.password_certificado)
            
            # Parse certificate
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                cert_data, password.encode('utf-8'), backend=default_backend()
            )
            
            if not certificate:
                return {"valid": False, "error": "Could not parse certificate"}
            
            # Validate certificate chain
            chain_info = {
                "certificate_subject": certificate.subject.rfc4514_string(),
                "certificate_issuer": certificate.issuer.rfc4514_string(),
                "additional_certificates": len(additional_certificates) if additional_certificates else 0,
                "chain_valid": True,
                "chain_warnings": []
            }
            
            # Basic chain validation
            if additional_certificates:
                chain_warnings = P12CertificateManager._validate_certificate_chain(
                    certificate, additional_certificates
                )
                chain_info["chain_warnings"] = chain_warnings
                chain_info["chain_valid"] = len(chain_warnings) == 0
            
            # Check if certificate is self-signed
            if certificate.subject == certificate.issuer:
                chain_info["self_signed"] = True
                chain_info["chain_warnings"].append("Certificate is self-signed")
            else:
                chain_info["self_signed"] = False
            
            return chain_info
            
        except Exception as e:
            return {"valid": False, "error": f"Chain validation failed: {str(e)}"}
    
    # Private helper methods
    
    async def _cache_certificate(self, tenant_id: UUID, cert_data: bytes, password: str) -> None:
        """Cache certificate in Redis with TTL"""
        try:
            if self.redis_client:
                cache_key = f"cert:{tenant_id}"
                cache_data = {
                    "cert_data": cert_data.hex(),  # Store as hex string
                    "password": password,
                    "cached_at": datetime.now(timezone.utc).isoformat()
                }
                
                await self.redis_client.hset(cache_key, mapping=cache_data)
                await self.redis_client.expire(cache_key, self.cache_ttl)
        except Exception:
            # Cache failure shouldn't break the operation
            pass
    
    async def _get_cached_certificate(self, tenant_id: UUID) -> Optional[Tuple[bytes, str]]:
        """Get certificate from Redis cache"""
        try:
            if self.redis_client:
                cache_key = f"cert:{tenant_id}"
                cache_data = await self.redis_client.hgetall(cache_key)
                
                if cache_data and "cert_data" in cache_data and "password" in cache_data:
                    cert_data = bytes.fromhex(cache_data["cert_data"])
                    password = cache_data["password"]
                    return cert_data, password
        except Exception:
            pass
        
        return None
    
    async def _cache_certificate_status(self, tenant_id: UUID, status: CertificateStatus) -> None:
        """Cache certificate status in Redis"""
        try:
            if self.redis_client:
                cache_key = f"cert_status:{tenant_id}"
                cache_data = status.dict()
                
                # Convert datetime to ISO string for JSON serialization
                if cache_data.get("fecha_vencimiento"):
                    cache_data["fecha_vencimiento"] = cache_data["fecha_vencimiento"].isoformat()
                
                await self.redis_client.hset(cache_key, mapping=cache_data)
                await self.redis_client.expire(cache_key, self.cache_ttl // 2)  # Shorter TTL for status
        except Exception:
            pass
    
    async def _get_cached_certificate_status(self, tenant_id: UUID) -> Optional[CertificateStatus]:
        """Get certificate status from Redis cache"""
        try:
            if self.redis_client:
                cache_key = f"cert_status:{tenant_id}"
                cache_data = await self.redis_client.hgetall(cache_key)
                
                if cache_data:
                    # Convert ISO string back to datetime
                    if cache_data.get("fecha_vencimiento"):
                        cache_data["fecha_vencimiento"] = datetime.fromisoformat(cache_data["fecha_vencimiento"])
                    
                    return CertificateStatus(**cache_data)
        except Exception:
            pass
        
        return None
    
    async def _clear_certificate_cache(self, tenant_id: UUID) -> None:
        """Clear certificate cache for tenant"""
        try:
            if self.redis_client:
                cache_keys = [f"cert:{tenant_id}", f"cert_status:{tenant_id}"]
                for key in cache_keys:
                    await self.redis_client.delete(key)
        except Exception:
            pass
    
    async def _schedule_expiration_notifications(self, tenant_id: UUID, expires_at: datetime) -> None:
        """Schedule expiration notifications for certificate"""
        try:
            if self.redis_client:
                # Store expiration date for background notification checking
                notification_key = f"cert_expiration:{tenant_id}"
                await self.redis_client.set(
                    notification_key,
                    expires_at.isoformat(),
                    ex=int((expires_at - datetime.now(timezone.utc)).total_seconds()) + 86400  # Expire 1 day after cert expires
                )
        except Exception:
            pass
    
    async def _was_notification_sent_recently(self, tenant_id: UUID, level: str, days_until: int) -> bool:
        """Check if notification was sent recently to avoid spam"""
        try:
            if self.redis_client:
                notification_key = f"notification_sent:{tenant_id}:{level}:{days_until}"
                exists = await self.redis_client.exists(notification_key)
                return bool(exists)
        except Exception:
            pass
        
        return False
    
    async def _mark_notification_sent(self, tenant_id: UUID, level: str, days_until: int) -> None:
        """Mark notification as sent to avoid duplicate notifications"""
        try:
            if self.redis_client:
                notification_key = f"notification_sent:{tenant_id}:{level}:{days_until}"
                # Mark as sent for 24 hours
                await self.redis_client.set(notification_key, "1", ex=86400)
        except Exception:
            pass
    
    def _log_certificate_activity(self, tenant_id: UUID, activity: str, details: Dict[str, Any]) -> None:
        """Log certificate activity for audit trail"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Certificate activity: {activity}", extra={
            "tenant_id": str(tenant_id),
            "activity": activity,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# Background task for certificate expiration notifications
class CertificateExpirationChecker:
    """
    Background service for checking certificate expirations
    
    Requirements: 3.6 - Automated certificate expiration notification system
    """
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
    
    async def run_expiration_check(self) -> List[Dict[str, Any]]:
        """
        Run certificate expiration check for all tenants
        
        Returns:
            List of notifications that need to be sent
        """
        db = self.db_session_factory()
        try:
            service = CertificateService(db)
            notifications = await service.check_expiration_notifications()
            return notifications
        finally:
            db.close()
    
    async def send_expiration_notifications(self, notifications: List[Dict[str, Any]]) -> None:
        """
        Send expiration notifications (placeholder for email service integration)
        
        Args:
            notifications: List of notification data
        """
        # This would integrate with an email service
        # For now, just log the notifications
        import logging
        logger = logging.getLogger(__name__)
        
        for notification in notifications:
            logger.info(f"Certificate expiration notification", extra={
                "tenant_id": str(notification["tenant_id"]),
                "tenant_name": notification["tenant_name"],
                "email": notification["email"],
                "days_until_expiration": notification["days_until_expiration"],
                "level": notification["level"],
                "message": notification["notification"]["message"]
            })


# Convenience functions for dependency injection

def get_certificate_service(db: Session) -> CertificateService:
    """Get certificate service instance"""
    return CertificateService(db)


async def upload_tenant_certificate(
    tenant_id: UUID,
    certificate_upload: CertificateUpload,
    db: Session
) -> Tuple[bool, Optional[CertificateStatus], List[str]]:
    """
    Upload certificate for tenant
    
    Args:
        tenant_id: Tenant UUID
        certificate_upload: Certificate upload data
        db: Database session
        
    Returns:
        Tuple of (success, certificate_status, errors)
    """
    service = CertificateService(db)
    return await service.upload_certificate(tenant_id, certificate_upload)


async def get_tenant_certificate_status(tenant_id: UUID, db: Session) -> Optional[CertificateStatus]:
    """
    Get certificate status for tenant
    
    Args:
        tenant_id: Tenant UUID
        db: Database session
        
    Returns:
        Certificate status or None
    """
    service = CertificateService(db)
    return await service.get_certificate_status(tenant_id)