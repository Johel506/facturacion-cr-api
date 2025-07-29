"""
Security utilities for API key authentication and cryptographic operations
"""
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from passlib.context import CryptContext
from jose import JWTError, jwt
from cryptography.fernet import Fernet
import base64

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption for sensitive data
def get_encryption_key() -> bytes:
    """Get or generate encryption key for sensitive data"""
    # Use the configured encryption key, ensure it's properly formatted for Fernet
    key = settings.ENCRYPTION_KEY.encode()
    # Fernet requires a 32-byte base64-encoded key
    return base64.urlsafe_b64encode(hashlib.sha256(key).digest())

fernet = Fernet(get_encryption_key())


class APIKeyGenerator:
    """Cryptographically secure API key generation and validation"""
    
    @staticmethod
    def generate_api_key(length: int = 64) -> str:
        """
        Generate a cryptographically secure API key
        
        Args:
            length: Key length in characters (minimum 32)
            
        Returns:
            Secure random API key string
            
        Requirements: 4.1 - minimum 32 characters, cryptographically secure
        """
        if length < 32:
            raise ValueError("API key must be at least 32 characters long")
        
        # Generate secure random token
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key_with_prefix(tenant_id: str, length: int = 64) -> str:
        """
        Generate API key with tenant prefix for easier identification
        
        Args:
            tenant_id: Tenant UUID string
            length: Total key length including prefix
            
        Returns:
            API key with format: cr_<short_tenant_id>_<random_token>
        """
        if length < 32:
            raise ValueError("API key must be at least 32 characters long")
        
        # Create short tenant identifier (first 8 chars of UUID)
        short_tenant = tenant_id.replace('-', '')[:8]
        prefix = f"cr_{short_tenant}_"
        
        # Calculate remaining length for random part
        remaining_length = length - len(prefix)
        if remaining_length < 16:
            remaining_length = 16  # Minimum random part
        
        # Generate random token
        random_token = secrets.token_urlsafe(remaining_length)
        
        return f"{prefix}{random_token}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash API key for secure storage comparison
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Hashed API key for database storage
        """
        return pwd_context.hash(api_key)
    
    @staticmethod
    def verify_api_key(plain_key: str, hashed_key: str) -> bool:
        """
        Verify API key against stored hash
        
        Args:
            plain_key: Plain text API key from request
            hashed_key: Hashed key from database
            
        Returns:
            True if key matches, False otherwise
        """
        return pwd_context.verify(plain_key, hashed_key)
    
    @staticmethod
    def is_valid_api_key_format(api_key: str) -> bool:
        """
        Validate API key format and length
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if not api_key or len(api_key) < 32:
            return False
        
        # Check if it's URL-safe base64 characters
        import string
        allowed_chars = string.ascii_letters + string.digits + '-_'
        return all(c in allowed_chars for c in api_key)


class JWTManager:
    """JWT token management for optional token-based authentication"""
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return payload
        except JWTError:
            return None


class DataEncryption:
    """Utilities for encrypting sensitive data like certificates and passwords"""
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        """
        Encrypt sensitive string data
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if not data:
            return ""
        
        encrypted_bytes = fernet.encrypt(data.encode())
        return base64.b64encode(encrypted_bytes).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """
        Decrypt sensitive string data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return ""
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception:
            raise ValueError("Failed to decrypt data - invalid format or key")
    
    @staticmethod
    def encrypt_binary_data(data: bytes) -> bytes:
        """
        Encrypt binary data (like P12 certificates)
        
        Args:
            data: Binary data to encrypt
            
        Returns:
            Encrypted binary data
        """
        if not data:
            return b""
        
        return fernet.encrypt(data)
    
    @staticmethod
    def decrypt_binary_data(encrypted_data: bytes) -> bytes:
        """
        Decrypt binary data
        
        Args:
            encrypted_data: Encrypted binary data
            
        Returns:
            Decrypted binary data
        """
        if not encrypted_data:
            return b""
        
        try:
            return fernet.decrypt(encrypted_data)
        except Exception:
            raise ValueError("Failed to decrypt binary data - invalid format or key")


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_api_key_strength(api_key: str) -> Tuple[bool, str]:
        """
        Validate API key strength and format
        
        Args:
            api_key: API key to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not api_key:
            return False, "API key cannot be empty"
        
        if len(api_key) < 32:
            return False, "API key must be at least 32 characters long"
        
        if len(api_key) > 128:
            return False, "API key cannot exceed 128 characters"
        
        if not APIKeyGenerator.is_valid_api_key_format(api_key):
            return False, "API key contains invalid characters"
        
        # Check for common weak patterns
        if api_key.lower() in ['test', 'demo', 'example']:
            return False, "API key cannot be a common test value"
        
        # Check for repeated characters (more than 50% repetition)
        char_counts = {}
        for char in api_key:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        max_repetition = max(char_counts.values())
        if max_repetition > len(api_key) * 0.5:
            return False, "API key has too many repeated characters"
        
        return True, "API key is valid"
    
    @staticmethod
    def generate_secure_api_key_for_tenant(tenant_id: str) -> str:
        """
        Generate a secure API key for a specific tenant
        
        Args:
            tenant_id: Tenant UUID string
            
        Returns:
            Cryptographically secure API key
        """
        # Generate key with tenant prefix for easier identification
        api_key = APIKeyGenerator.generate_api_key_with_prefix(tenant_id, 64)
        
        # Validate the generated key
        is_valid, error_msg = SecurityValidator.validate_api_key_strength(api_key)
        if not is_valid:
            # Fallback to standard generation if prefix version fails validation
            api_key = APIKeyGenerator.generate_api_key(64)
        
        return api_key
    
    @staticmethod
    def create_api_key_hash(api_key: str) -> str:
        """
        Create a secure hash of the API key for database storage
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Hashed API key for secure storage
        """
        # Use HMAC-SHA256 with secret key for additional security
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            api_key.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine with bcrypt hash for double protection
        bcrypt_hash = pwd_context.hash(api_key)
        
        return f"hmac:{signature}|bcrypt:{bcrypt_hash}"
    
    @staticmethod
    def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
        """
        Verify API key against stored hash
        
        Args:
            api_key: Plain text API key
            stored_hash: Stored hash from database
            
        Returns:
            True if key is valid, False otherwise
        """
        try:
            if '|' in stored_hash and stored_hash.startswith('hmac:'):
                # New format with HMAC + bcrypt
                hmac_part, bcrypt_part = stored_hash.split('|', 1)
                stored_signature = hmac_part.replace('hmac:', '')
                stored_bcrypt = bcrypt_part.replace('bcrypt:', '')
                
                # Verify HMAC signature
                expected_signature = hmac.new(
                    settings.SECRET_KEY.encode(),
                    api_key.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                hmac_valid = hmac.compare_digest(stored_signature, expected_signature)
                bcrypt_valid = pwd_context.verify(api_key, stored_bcrypt)
                
                return hmac_valid and bcrypt_valid
            else:
                # Legacy format - just bcrypt
                return pwd_context.verify(api_key, stored_hash)
        except Exception:
            return False


# Convenience functions for common operations
def generate_tenant_api_key(tenant_id: str) -> Tuple[str, str]:
    """
    Generate API key and hash for a tenant
    
    Args:
        tenant_id: Tenant UUID string
        
    Returns:
        Tuple of (plain_api_key, hashed_api_key)
    """
    api_key = SecurityValidator.generate_secure_api_key_for_tenant(tenant_id)
    api_key_hash = SecurityValidator.create_api_key_hash(api_key)
    return api_key, api_key_hash


def verify_tenant_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify tenant API key
    
    Args:
        api_key: Plain text API key from request
        stored_hash: Stored hash from database
        
    Returns:
        True if valid, False otherwise
    """
    return SecurityValidator.verify_api_key_hash(api_key, stored_hash)


def encrypt_certificate_data(certificate_data: bytes, password: str) -> Tuple[bytes, str]:
    """
    Encrypt certificate and password for secure storage
    
    Args:
        certificate_data: P12 certificate binary data
        password: Certificate password
        
    Returns:
        Tuple of (encrypted_certificate, encrypted_password)
    """
    encrypted_cert = DataEncryption.encrypt_binary_data(certificate_data)
    encrypted_password = DataEncryption.encrypt_data(password)
    return encrypted_cert, encrypted_password


def decrypt_certificate_data(encrypted_cert: bytes, encrypted_password: str) -> Tuple[bytes, str]:
    """
    Decrypt certificate and password from storage
    
    Args:
        encrypted_cert: Encrypted certificate binary data
        encrypted_password: Encrypted password string
        
    Returns:
        Tuple of (certificate_data, password)
    """
    cert_data = DataEncryption.decrypt_binary_data(encrypted_cert)
    password = DataEncryption.decrypt_data(encrypted_password)
    return cert_data, password


def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT token for optional authentication
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    return JWTManager.create_access_token(data, expires_delta)


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload or None if invalid
    """
    return JWTManager.verify_token(token)