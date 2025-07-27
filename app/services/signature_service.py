"""
Signature service for Costa Rica electronic documents.
Integrates XML signature functionality with document processing.

Requirements: 3.1, 3.2
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.tenant import Tenant
from app.utils.xml_signature import XMLSignatureService, XMLSignatureError
from app.utils.crypto_utils import decrypt_certificate_from_storage, decrypt_password_from_storage


logger = logging.getLogger(__name__)


class SignatureService:
    """
    Service for XML document signing and signature management.
    Handles the complete signature workflow for electronic documents.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def sign_document(
        self,
        document: Document,
        force_resign: bool = False
    ) -> Tuple[bool, str]:
        """
        Sign a document with the tenant's certificate.
        
        Args:
            document: Document to sign
            force_resign: Force re-signing even if already signed
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Check if document is already signed
            if document.xml_firmado and not force_resign:
                return True, "Document is already signed"
            
            # Check if document has original XML
            if not document.xml_original:
                return False, "Document has no XML content to sign"
            
            # Get tenant certificate
            tenant = document.tenant
            if not tenant.certificado_p12 or not tenant.password_certificado:
                return False, "Tenant has no certificate configured"
            
            # Decrypt certificate data
            try:
                p12_data = decrypt_certificate_from_storage(tenant.certificado_p12)
                password = decrypt_password_from_storage(tenant.password_certificado)
            except Exception as e:
                logger.error(f"Failed to decrypt certificate for tenant {tenant.id}: {str(e)}")
                return False, "Failed to decrypt certificate"
            
            # Sign XML
            signed_xml, cert_info = XMLSignatureService.sign_xml_with_p12(
                xml_content=document.xml_original,
                p12_data=p12_data,
                password=password
            )
            
            # Update document with signed XML
            document.xml_firmado = signed_xml
            document.updated_at = datetime.now(timezone.utc)
            
            # Log signing activity
            logger.info(
                f"Document {document.id} signed successfully. "
                f"Certificate: {cert_info.get('subject', 'Unknown')}"
            )
            
            # Save changes
            self.db.commit()
            
            return True, "Document signed successfully"
            
        except XMLSignatureError as e:
            logger.error(f"XML signature error for document {document.id}: {str(e)}")
            return False, f"Signature error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error signing document {document.id}: {str(e)}")
            self.db.rollback()
            return False, f"Failed to sign document: {str(e)}"
    
    def verify_document_signature(
        self,
        document: Document
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify a document's signature.
        
        Args:
            document: Document to verify
            
        Returns:
            Tuple of (is_valid, error_message, certificate_info)
        """
        try:
            if not document.xml_firmado:
                return False, "Document is not signed", None
            
            # Verify signature
            is_valid, error_msg, cert_info = XMLSignatureService.verify_xml_signature(
                document.xml_firmado
            )
            
            if is_valid:
                logger.info(f"Document {document.id} signature verified successfully")
            else:
                logger.warning(f"Document {document.id} signature verification failed: {error_msg}")
            
            return is_valid, error_msg, cert_info
            
        except Exception as e:
            logger.error(f"Error verifying signature for document {document.id}: {str(e)}")
            return False, f"Verification error: {str(e)}", None
    
    def validate_tenant_certificate(
        self,
        tenant: Tenant
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate tenant's certificate.
        
        Args:
            tenant: Tenant to validate certificate for
            
        Returns:
            Tuple of (is_valid, error_message, certificate_info)
        """
        try:
            if not tenant.certificado_p12 or not tenant.password_certificado:
                return False, "No certificate configured", None
            
            # Decrypt certificate data
            try:
                p12_data = decrypt_certificate_from_storage(tenant.certificado_p12)
                password = decrypt_password_from_storage(tenant.password_certificado)
            except Exception as e:
                logger.error(f"Failed to decrypt certificate for tenant {tenant.id}: {str(e)}")
                return False, "Failed to decrypt certificate", None
            
            # Validate certificate
            is_valid, error_msg = XMLSignatureService.validate_p12_certificate(p12_data, password)
            
            # Get certificate info
            cert_info = None
            if is_valid:
                try:
                    cert_info = XMLSignatureService.extract_certificate_info(p12_data, password)
                except Exception as e:
                    logger.warning(f"Failed to extract certificate info for tenant {tenant.id}: {str(e)}")
            
            return is_valid, error_msg, cert_info
            
        except Exception as e:
            logger.error(f"Error validating certificate for tenant {tenant.id}: {str(e)}")
            return False, f"Certificate validation error: {str(e)}", None
    
    def get_certificate_expiration_info(
        self,
        tenant: Tenant
    ) -> Optional[Dict[str, Any]]:
        """
        Get certificate expiration information.
        
        Args:
            tenant: Tenant to check certificate for
            
        Returns:
            Certificate expiration info or None if error
        """
        try:
            is_valid, error_msg, cert_info = self.validate_tenant_certificate(tenant)
            
            if not cert_info:
                return None
            
            # Calculate days until expiration
            now = datetime.now(timezone.utc)
            expiry_date = cert_info['not_valid_after']
            
            if expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
            
            days_until_expiry = (expiry_date - now).days
            
            return {
                'is_valid': is_valid,
                'error_message': error_msg,
                'expiry_date': expiry_date,
                'days_until_expiry': days_until_expiry,
                'is_expired': cert_info['is_expired'],
                'needs_renewal': days_until_expiry <= 30,  # Warn 30 days before expiry
                'subject': cert_info.get('subject'),
                'issuer': cert_info.get('issuer'),
                'serial_number': cert_info.get('serial_number')
            }
            
        except Exception as e:
            logger.error(f"Error getting certificate expiration info for tenant {tenant.id}: {str(e)}")
            return None


def get_signature_service(db: Session = None) -> SignatureService:
    """Get signature service instance with database session."""
    if db is None:
        db = next(get_db())
    return SignatureService(db)