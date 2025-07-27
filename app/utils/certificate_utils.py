"""
P12 certificate validation, parsing, and expiration checking utilities
"""
import io
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID, ExtensionOID

from app.utils.crypto_utils import create_data_integrity_hash


class CertificateInfo(NamedTuple):
    """Certificate information structure"""
    subject: str
    issuer: str
    serial_number: str
    not_valid_before: datetime
    not_valid_after: datetime
    fingerprint: str
    key_usage: List[str]
    extended_key_usage: List[str]
    is_valid: bool
    validation_errors: List[str]


class CertificateValidationResult(NamedTuple):
    """Certificate validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    certificate_info: Optional[CertificateInfo]


class CertificateExpirationInfo(NamedTuple):
    """Certificate expiration information"""
    expires_at: datetime
    days_until_expiration: int
    is_expired: bool
    expires_soon: bool
    warning_level: str  # 'none', 'info', 'warning', 'critical', 'expired'


class P12CertificateManager:
    """
    P12 certificate validation, parsing, and management utilities
    
    Requirements: 4.5, 3.6, 1.2 - P12 certificate validation, parsing, and expiration checking
    """
    
    # Certificate validation thresholds
    EXPIRATION_WARNING_DAYS = [30, 15, 7]  # Days before expiration to warn
    
    @staticmethod
    def validate_p12_certificate(
        certificate_data: bytes, 
        password: str
    ) -> CertificateValidationResult:
        """
        Validate P12 certificate format and contents
        
        Args:
            certificate_data: P12 certificate binary data
            password: Certificate password
            
        Returns:
            CertificateValidationResult with validation details
        """
        errors = []
        warnings = []
        certificate_info = None
        
        try:
            # Validate input
            if not certificate_data:
                errors.append("Certificate data is empty")
                return CertificateValidationResult(False, errors, warnings, None)
            
            if len(certificate_data) < 100:  # Minimum reasonable size
                errors.append("Certificate data is too small to be valid")
                return CertificateValidationResult(False, errors, warnings, None)
            
            # Try to parse P12 certificate
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    certificate_data, password.encode('utf-8'), backend=default_backend()
                )
            except ValueError as e:
                if "invalid" in str(e).lower() or "bad decrypt" in str(e).lower():
                    errors.append("Invalid certificate password")
                else:
                    errors.append(f"Invalid P12 certificate format: {e}")
                return CertificateValidationResult(False, errors, warnings, None)
            except Exception as e:
                errors.append(f"Failed to parse P12 certificate: {e}")
                return CertificateValidationResult(False, errors, warnings, None)
            
            # Validate certificate exists
            if not certificate:
                errors.append("No certificate found in P12 file")
                return CertificateValidationResult(False, errors, warnings, None)
            
            # Validate private key exists
            if not private_key:
                errors.append("No private key found in P12 file")
                return CertificateValidationResult(False, errors, warnings, None)
            
            # Extract certificate information
            certificate_info = P12CertificateManager._extract_certificate_info(
                certificate, certificate_data
            )
            
            # Validate certificate dates
            now = datetime.now(timezone.utc)
            if certificate.not_valid_after < now:
                errors.append("Certificate has expired")
            elif certificate.not_valid_before > now:
                errors.append("Certificate is not yet valid")
            
            # Check expiration warnings
            expiration_info = P12CertificateManager.get_expiration_info(certificate)
            if expiration_info.expires_soon:
                warnings.append(
                    f"Certificate expires in {expiration_info.days_until_expiration} days"
                )
            
            # Validate key usage for digital signatures
            key_usage_errors = P12CertificateManager._validate_key_usage(certificate)
            errors.extend(key_usage_errors)
            
            # Validate certificate chain if additional certificates present
            if additional_certificates:
                chain_warnings = P12CertificateManager._validate_certificate_chain(
                    certificate, additional_certificates
                )
                warnings.extend(chain_warnings)
            
            # Check for Costa Rican specific requirements
            cr_validation_errors = P12CertificateManager._validate_costa_rica_requirements(
                certificate
            )
            errors.extend(cr_validation_errors)
            
            is_valid = len(errors) == 0
            
            return CertificateValidationResult(
                is_valid, errors, warnings, certificate_info
            )
            
        except Exception as e:
            errors.append(f"Unexpected error during certificate validation: {e}")
            return CertificateValidationResult(False, errors, warnings, None)
    
    @staticmethod
    def _extract_certificate_info(
        certificate: x509.Certificate, 
        certificate_data: bytes
    ) -> CertificateInfo:
        """Extract detailed information from certificate"""
        
        # Extract subject information
        subject_parts = []
        for attribute in certificate.subject:
            subject_parts.append(f"{attribute.oid._name}={attribute.value}")
        subject = ", ".join(subject_parts)
        
        # Extract issuer information
        issuer_parts = []
        for attribute in certificate.issuer:
            issuer_parts.append(f"{attribute.oid._name}={attribute.value}")
        issuer = ", ".join(issuer_parts)
        
        # Get serial number
        serial_number = str(certificate.serial_number)
        
        # Get validity dates
        not_valid_before = certificate.not_valid_before.replace(tzinfo=timezone.utc)
        not_valid_after = certificate.not_valid_after.replace(tzinfo=timezone.utc)
        
        # Create fingerprint
        fingerprint = create_data_integrity_hash(certificate_data)
        
        # Extract key usage
        key_usage = []
        try:
            ku_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            ku = ku_ext.value
            if ku.digital_signature:
                key_usage.append("digital_signature")
            if ku.key_encipherment:
                key_usage.append("key_encipherment")
            if ku.data_encipherment:
                key_usage.append("data_encipherment")
            if ku.key_agreement:
                key_usage.append("key_agreement")
            if ku.key_cert_sign:
                key_usage.append("key_cert_sign")
            if ku.crl_sign:
                key_usage.append("crl_sign")
        except x509.ExtensionNotFound:
            pass
        
        # Extract extended key usage
        extended_key_usage = []
        try:
            eku_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            eku = eku_ext.value
            for usage in eku:
                extended_key_usage.append(usage.dotted_string)
        except x509.ExtensionNotFound:
            pass
        
        # Basic validation
        now = datetime.now(timezone.utc)
        is_valid = (
            not_valid_before <= now <= not_valid_after and
            len(key_usage) > 0
        )
        
        validation_errors = []
        if not_valid_before > now:
            validation_errors.append("Certificate not yet valid")
        if not_valid_after < now:
            validation_errors.append("Certificate expired")
        if not key_usage:
            validation_errors.append("No key usage specified")
        
        return CertificateInfo(
            subject=subject,
            issuer=issuer,
            serial_number=serial_number,
            not_valid_before=not_valid_before,
            not_valid_after=not_valid_after,
            fingerprint=fingerprint,
            key_usage=key_usage,
            extended_key_usage=extended_key_usage,
            is_valid=is_valid,
            validation_errors=validation_errors
        )
    
    @staticmethod
    def _validate_key_usage(certificate: x509.Certificate) -> List[str]:
        """Validate certificate has required key usage for digital signatures"""
        errors = []
        
        try:
            ku_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            ku = ku_ext.value
            
            # For Costa Rican electronic invoicing, we need digital signature capability
            if not ku.digital_signature:
                errors.append("Certificate does not have digital signature capability")
            
            # Non-repudiation is also typically required
            if hasattr(ku, 'content_commitment') and not ku.content_commitment:
                # Note: content_commitment is the new name for non_repudiation
                pass  # This is optional for some certificates
                
        except x509.ExtensionNotFound:
            errors.append("Certificate does not specify key usage")
        
        return errors
    
    @staticmethod
    def _validate_certificate_chain(
        certificate: x509.Certificate, 
        additional_certificates: List[x509.Certificate]
    ) -> List[str]:
        """Validate certificate chain if present"""
        warnings = []
        
        # Basic chain validation - check if certificate is signed by any of the additional certs
        try:
            # This is a simplified check - full chain validation would be more complex
            issuer_found = False
            for additional_cert in additional_certificates:
                if certificate.issuer == additional_cert.subject:
                    issuer_found = True
                    break
            
            if not issuer_found and len(additional_certificates) > 0:
                warnings.append("Certificate chain may be incomplete")
                
        except Exception:
            warnings.append("Could not validate certificate chain")
        
        return warnings
    
    @staticmethod
    def _validate_costa_rica_requirements(certificate: x509.Certificate) -> List[str]:
        """Validate Costa Rica specific certificate requirements"""
        errors = []
        
        # Check if certificate has required extensions for Costa Rican digital signatures
        # This is a basic check - actual requirements may be more specific
        
        try:
            # Check for basic constraints
            bc_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
            bc = bc_ext.value
            if bc.ca:
                errors.append("Certificate appears to be a CA certificate, not an end-entity certificate")
        except x509.ExtensionNotFound:
            # Basic constraints extension is optional for end-entity certificates
            pass
        
        # Check subject alternative name for email (often required)
        try:
            san_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san = san_ext.value
            has_email = any(isinstance(name, x509.RFC822Name) for name in san)
            if not has_email:
                # This is just a warning as email in SAN is not always required
                pass
        except x509.ExtensionNotFound:
            pass
        
        return errors
    
    @staticmethod
    def get_expiration_info(certificate: x509.Certificate) -> CertificateExpirationInfo:
        """
        Get detailed expiration information for certificate
        
        Args:
            certificate: X.509 certificate object
            
        Returns:
            CertificateExpirationInfo with expiration details
        """
        expires_at = certificate.not_valid_after.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        days_until_expiration = (expires_at - now).days
        is_expired = expires_at < now
        
        # Determine warning level
        if is_expired:
            warning_level = "expired"
            expires_soon = False
        elif days_until_expiration <= 7:
            warning_level = "critical"
            expires_soon = True
        elif days_until_expiration <= 15:
            warning_level = "warning"
            expires_soon = True
        elif days_until_expiration <= 30:
            warning_level = "info"
            expires_soon = True
        else:
            warning_level = "none"
            expires_soon = False
        
        return CertificateExpirationInfo(
            expires_at=expires_at,
            days_until_expiration=days_until_expiration,
            is_expired=is_expired,
            expires_soon=expires_soon,
            warning_level=warning_level
        )
    
    @staticmethod
    def extract_certificate_subject_info(certificate: x509.Certificate) -> Dict[str, str]:
        """
        Extract structured subject information from certificate
        
        Args:
            certificate: X.509 certificate object
            
        Returns:
            Dictionary with subject information
        """
        subject_info = {}
        
        for attribute in certificate.subject:
            oid_name = attribute.oid._name
            if oid_name == "commonName":
                subject_info["common_name"] = attribute.value
            elif oid_name == "organizationName":
                subject_info["organization"] = attribute.value
            elif oid_name == "organizationalUnitName":
                subject_info["organizational_unit"] = attribute.value
            elif oid_name == "countryName":
                subject_info["country"] = attribute.value
            elif oid_name == "stateOrProvinceName":
                subject_info["state"] = attribute.value
            elif oid_name == "localityName":
                subject_info["locality"] = attribute.value
            elif oid_name == "emailAddress":
                subject_info["email"] = attribute.value
            else:
                subject_info[oid_name] = attribute.value
        
        return subject_info
    
    @staticmethod
    def get_certificate_fingerprint(certificate_data: bytes) -> str:
        """
        Get SHA-256 fingerprint of certificate
        
        Args:
            certificate_data: P12 certificate binary data
            
        Returns:
            SHA-256 fingerprint hex string
        """
        return create_data_integrity_hash(certificate_data)
    
    @staticmethod
    def check_certificate_compatibility(certificate: x509.Certificate) -> Tuple[bool, List[str]]:
        """
        Check if certificate is compatible with Costa Rican electronic invoicing
        
        Args:
            certificate: X.509 certificate object
            
        Returns:
            Tuple of (is_compatible, compatibility_issues)
        """
        issues = []
        
        # Check key algorithm
        public_key = certificate.public_key()
        if hasattr(public_key, 'key_size'):
            if public_key.key_size < 2048:
                issues.append("Key size is less than 2048 bits (not recommended)")
        
        # Check signature algorithm
        signature_algorithm = certificate.signature_algorithm_oid._name
        if 'sha1' in signature_algorithm.lower():
            issues.append("Certificate uses SHA-1 signature (deprecated)")
        
        # Check validity period
        validity_period = certificate.not_valid_after - certificate.not_valid_before
        if validity_period.days > 365 * 3:  # More than 3 years
            issues.append("Certificate validity period is longer than recommended (3 years)")
        
        is_compatible = len(issues) == 0
        return is_compatible, issues


class CertificateExpirationNotifier:
    """
    Certificate expiration notification system
    
    Requirements: 3.6, 1.2 - Certificate expiration notification system (30, 15, 7 days)
    """
    
    @staticmethod
    def should_notify_expiration(
        certificate: x509.Certificate, 
        notification_days: List[int] = None
    ) -> Tuple[bool, str, int]:
        """
        Check if certificate expiration notification should be sent
        
        Args:
            certificate: X.509 certificate object
            notification_days: Days before expiration to notify (default: [30, 15, 7])
            
        Returns:
            Tuple of (should_notify, notification_level, days_until_expiration)
        """
        if notification_days is None:
            notification_days = [30, 15, 7]
        
        expiration_info = P12CertificateManager.get_expiration_info(certificate)
        
        if expiration_info.is_expired:
            return True, "expired", expiration_info.days_until_expiration
        
        for days in sorted(notification_days):
            if expiration_info.days_until_expiration <= days:
                if days <= 7:
                    level = "critical"
                elif days <= 15:
                    level = "warning"
                else:
                    level = "info"
                return True, level, expiration_info.days_until_expiration
        
        return False, "none", expiration_info.days_until_expiration
    
    @staticmethod
    def get_notification_message(
        days_until_expiration: int, 
        certificate_subject: str
    ) -> Dict[str, str]:
        """
        Generate notification message for certificate expiration
        
        Args:
            days_until_expiration: Days until certificate expires
            certificate_subject: Certificate subject name
            
        Returns:
            Dictionary with notification message details
        """
        if days_until_expiration < 0:
            return {
                "title": "Certificate Expired",
                "message": f"Your certificate '{certificate_subject}' has expired {abs(days_until_expiration)} days ago. Please renew immediately.",
                "urgency": "critical",
                "action_required": "Renew certificate immediately"
            }
        elif days_until_expiration == 0:
            return {
                "title": "Certificate Expires Today",
                "message": f"Your certificate '{certificate_subject}' expires today. Please renew immediately.",
                "urgency": "critical",
                "action_required": "Renew certificate today"
            }
        elif days_until_expiration <= 7:
            return {
                "title": "Certificate Expires Soon",
                "message": f"Your certificate '{certificate_subject}' expires in {days_until_expiration} days. Please renew as soon as possible.",
                "urgency": "critical",
                "action_required": "Renew certificate within 7 days"
            }
        elif days_until_expiration <= 15:
            return {
                "title": "Certificate Expiration Warning",
                "message": f"Your certificate '{certificate_subject}' expires in {days_until_expiration} days. Please plan for renewal.",
                "urgency": "warning",
                "action_required": "Plan certificate renewal"
            }
        elif days_until_expiration <= 30:
            return {
                "title": "Certificate Expiration Notice",
                "message": f"Your certificate '{certificate_subject}' expires in {days_until_expiration} days. Please prepare for renewal.",
                "urgency": "info",
                "action_required": "Prepare for certificate renewal"
            }
        else:
            return {
                "title": "Certificate Status",
                "message": f"Your certificate '{certificate_subject}' is valid for {days_until_expiration} more days.",
                "urgency": "none",
                "action_required": "No action required"
            }


# Convenience functions for common operations
def validate_p12_certificate_file(
    certificate_data: bytes, 
    password: str
) -> CertificateValidationResult:
    """
    Validate P12 certificate file
    
    Args:
        certificate_data: P12 certificate binary data
        password: Certificate password
        
    Returns:
        CertificateValidationResult with validation details
    """
    return P12CertificateManager.validate_p12_certificate(certificate_data, password)


def check_certificate_expiration(certificate_data: bytes, password: str) -> CertificateExpirationInfo:
    """
    Check certificate expiration status
    
    Args:
        certificate_data: P12 certificate binary data
        password: Certificate password
        
    Returns:
        CertificateExpirationInfo with expiration details
        
    Raises:
        ValueError: If certificate cannot be parsed
    """
    try:
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            certificate_data, password.encode('utf-8'), backend=default_backend()
        )
        
        if not certificate:
            raise ValueError("No certificate found in P12 file")
        
        return P12CertificateManager.get_expiration_info(certificate)
        
    except Exception as e:
        raise ValueError(f"Failed to check certificate expiration: {e}")


def get_certificate_info(certificate_data: bytes, password: str) -> CertificateInfo:
    """
    Get detailed certificate information
    
    Args:
        certificate_data: P12 certificate binary data
        password: Certificate password
        
    Returns:
        CertificateInfo with certificate details
        
    Raises:
        ValueError: If certificate cannot be parsed
    """
    validation_result = P12CertificateManager.validate_p12_certificate(
        certificate_data, password
    )
    
    if not validation_result.certificate_info:
        raise ValueError(f"Failed to extract certificate info: {validation_result.errors}")
    
    return validation_result.certificate_info