"""
Cryptographic utilities for AES-256 encryption and secure data handling
"""
import os
import base64
import hashlib
import secrets
from typing import Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.core.config import settings


class AESEncryption:
    """
    AES-256 encryption utilities for sensitive data
    
    Requirements: 4.5 - AES-256 encryption for P12 certificates and passwords
    """
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new AES-256 key"""
        return secrets.token_bytes(32)  # 256 bits
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """
        Derive AES key from password using PBKDF2
        
        Args:
            password: Password string
            salt: Salt bytes (should be 16 bytes)
            
        Returns:
            Derived 32-byte key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
            backend=default_backend()
        )
        return kdf.derive(password.encode())
    
    @staticmethod
    def encrypt_data(data: bytes, key: bytes) -> Tuple[bytes, bytes]:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Data to encrypt
            key: 32-byte encryption key
            
        Returns:
            Tuple of (encrypted_data, nonce)
        """
        # Generate random nonce
        nonce = secrets.token_bytes(12)  # 96 bits for GCM
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        
        # Encrypt data
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Combine ciphertext and authentication tag
        encrypted_data = ciphertext + encryptor.tag
        
        return encrypted_data, nonce
    
    @staticmethod
    def decrypt_data(encrypted_data: bytes, key: bytes, nonce: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Encrypted data (includes auth tag at end)
            key: 32-byte encryption key
            nonce: 12-byte nonce used for encryption
            
        Returns:
            Decrypted data
            
        Raises:
            ValueError: If decryption fails or authentication fails
        """
        # Split ciphertext and authentication tag
        ciphertext = encrypted_data[:-16]  # All but last 16 bytes
        tag = encrypted_data[-16:]  # Last 16 bytes
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        
        # Decrypt data
        decryptor = cipher.decryptor()
        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    @staticmethod
    def encrypt_with_password(data: bytes, password: str) -> Tuple[bytes, bytes]:
        """
        Encrypt data with password-derived key
        
        Args:
            data: Data to encrypt
            password: Password for key derivation
            
        Returns:
            Tuple of (encrypted_data_with_nonce, salt)
        """
        # Generate salt
        salt = secrets.token_bytes(16)
        
        # Derive key from password
        key = AESEncryption.derive_key_from_password(password, salt)
        
        # Encrypt data
        encrypted_data, nonce = AESEncryption.encrypt_data(data, key)
        
        # Combine nonce and encrypted data
        encrypted_with_nonce = nonce + encrypted_data
        
        return encrypted_with_nonce, salt
    
    @staticmethod
    def decrypt_with_password(
        encrypted_with_nonce: bytes, 
        salt: bytes, 
        password: str
    ) -> bytes:
        """
        Decrypt data with password-derived key
        
        Args:
            encrypted_with_nonce: Nonce + encrypted data
            salt: Salt used for key derivation
            password: Password for key derivation
            
        Returns:
            Decrypted data
        """
        # Extract nonce and encrypted data
        nonce = encrypted_with_nonce[:12]
        encrypted_data = encrypted_with_nonce[12:]
        
        # Derive key from password
        key = AESEncryption.derive_key_from_password(password, salt)
        
        # Decrypt data
        return AESEncryption.decrypt_data(encrypted_data, key, nonce)


class SecureDataManager:
    """
    High-level secure data management using application encryption key
    
    Requirements: 4.5 - Secure certificate storage with encrypted fields
    """
    
    def __init__(self):
        # Use application encryption key from settings
        self.master_key = self._get_master_key()
    
    def _get_master_key(self) -> bytes:
        """Get or derive master encryption key from settings"""
        # Use configured encryption key
        key_material = settings.ENCRYPTION_KEY.encode()
        
        # Derive consistent 32-byte key using SHA-256
        return hashlib.sha256(key_material).digest()
    
    def encrypt_certificate(self, certificate_data: bytes) -> str:
        """
        Encrypt P12 certificate for database storage
        
        Args:
            certificate_data: P12 certificate binary data
            
        Returns:
            Base64-encoded encrypted certificate
        """
        if not certificate_data:
            return ""
        
        encrypted_data, nonce = AESEncryption.encrypt_data(
            certificate_data, self.master_key
        )
        
        # Combine nonce and encrypted data, then base64 encode
        combined = nonce + encrypted_data
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_certificate(self, encrypted_certificate: str) -> bytes:
        """
        Decrypt P12 certificate from database storage
        
        Args:
            encrypted_certificate: Base64-encoded encrypted certificate
            
        Returns:
            P12 certificate binary data
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_certificate:
            return b""
        
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_certificate.encode('utf-8'))
            
            # Extract nonce and encrypted data
            nonce = combined[:12]
            encrypted_data = combined[12:]
            
            # Decrypt
            return AESEncryption.decrypt_data(
                encrypted_data, self.master_key, nonce
            )
        except Exception as e:
            raise ValueError(f"Failed to decrypt certificate: {e}")
    
    def encrypt_password(self, password: str) -> str:
        """
        Encrypt certificate password for database storage
        
        Args:
            password: Plain text password
            
        Returns:
            Base64-encoded encrypted password
        """
        if not password:
            return ""
        
        password_bytes = password.encode('utf-8')
        encrypted_data, nonce = AESEncryption.encrypt_data(
            password_bytes, self.master_key
        )
        
        # Combine nonce and encrypted data, then base64 encode
        combined = nonce + encrypted_data
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt certificate password from database storage
        
        Args:
            encrypted_password: Base64-encoded encrypted password
            
        Returns:
            Plain text password
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_password:
            return ""
        
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_password.encode('utf-8'))
            
            # Extract nonce and encrypted data
            nonce = combined[:12]
            encrypted_data = combined[12:]
            
            # Decrypt
            password_bytes = AESEncryption.decrypt_data(
                encrypted_data, self.master_key, nonce
            )
            
            return password_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decrypt password: {e}")
    
    def encrypt_sensitive_string(self, data: str) -> str:
        """
        Encrypt any sensitive string data
        
        Args:
            data: Sensitive string to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not data:
            return ""
        
        data_bytes = data.encode('utf-8')
        encrypted_data, nonce = AESEncryption.encrypt_data(
            data_bytes, self.master_key
        )
        
        # Combine nonce and encrypted data, then base64 encode
        combined = nonce + encrypted_data
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_sensitive_string(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive string data
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Plain text string
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_data:
            return ""
        
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract nonce and encrypted data
            nonce = combined[:12]
            encrypted_bytes = combined[12:]
            
            # Decrypt
            data_bytes = AESEncryption.decrypt_data(
                encrypted_bytes, self.master_key, nonce
            )
            
            return data_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decrypt string: {e}")


class SecureRandom:
    """Cryptographically secure random number generation"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_hex_token(length: int = 32) -> str:
        """Generate cryptographically secure random hex token"""
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_bytes(length: int = 32) -> bytes:
        """Generate cryptographically secure random bytes"""
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_security_code(length: int = 8) -> str:
        """
        Generate numeric security code for document keys
        
        Args:
            length: Length of security code (default 8 for document keys)
            
        Returns:
            Numeric security code string
        """
        # Generate random digits
        digits = ''.join(secrets.choice('0123456789') for _ in range(length))
        return digits
    
    @staticmethod
    def generate_salt(length: int = 16) -> bytes:
        """Generate cryptographic salt"""
        return secrets.token_bytes(length)


class HashingUtils:
    """Secure hashing utilities"""
    
    @staticmethod
    def sha256_hash(data: bytes) -> str:
        """Generate SHA-256 hash of data"""
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def sha256_hash_string(data: str) -> str:
        """Generate SHA-256 hash of string"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_hash(data: bytes, expected_hash: str) -> bool:
        """Verify data against expected SHA-256 hash"""
        actual_hash = HashingUtils.sha256_hash(data)
        return secrets.compare_digest(actual_hash, expected_hash)
    
    @staticmethod
    def hmac_sha256(data: bytes, key: bytes) -> str:
        """Generate HMAC-SHA256 of data with key"""
        import hmac
        return hmac.new(key, data, hashlib.sha256).hexdigest()
    
    @staticmethod
    def verify_hmac(data: bytes, key: bytes, expected_hmac: str) -> bool:
        """Verify HMAC-SHA256"""
        actual_hmac = HashingUtils.hmac_sha256(data, key)
        return secrets.compare_digest(actual_hmac, expected_hmac)


class DataIntegrityChecker:
    """Data integrity verification utilities"""
    
    @staticmethod
    def create_checksum(data: bytes) -> str:
        """Create integrity checksum for data"""
        return HashingUtils.sha256_hash(data)
    
    @staticmethod
    def verify_checksum(data: bytes, expected_checksum: str) -> bool:
        """Verify data integrity using checksum"""
        return HashingUtils.verify_hash(data, expected_checksum)
    
    @staticmethod
    def create_certificate_fingerprint(certificate_data: bytes) -> str:
        """
        Create fingerprint for certificate identification
        
        Args:
            certificate_data: P12 certificate binary data
            
        Returns:
            SHA-256 fingerprint of certificate
        """
        return HashingUtils.sha256_hash(certificate_data)
    
    @staticmethod
    def verify_certificate_integrity(
        certificate_data: bytes, 
        expected_fingerprint: str
    ) -> bool:
        """
        Verify certificate hasn't been tampered with
        
        Args:
            certificate_data: P12 certificate binary data
            expected_fingerprint: Expected SHA-256 fingerprint
            
        Returns:
            True if certificate is intact, False otherwise
        """
        return HashingUtils.verify_hash(certificate_data, expected_fingerprint)


# Global secure data manager instance
secure_data_manager = SecureDataManager()


# Convenience functions for common operations
def encrypt_certificate_for_storage(certificate_data: bytes) -> str:
    """
    Encrypt P12 certificate for database storage
    
    Args:
        certificate_data: P12 certificate binary data
        
    Returns:
        Encrypted certificate string for database storage
    """
    return secure_data_manager.encrypt_certificate(certificate_data)


def decrypt_certificate_from_storage(encrypted_certificate: str) -> bytes:
    """
    Decrypt P12 certificate from database storage
    
    Args:
        encrypted_certificate: Encrypted certificate from database
        
    Returns:
        P12 certificate binary data
    """
    return secure_data_manager.decrypt_certificate(encrypted_certificate)


def encrypt_password_for_storage(password: str) -> str:
    """
    Encrypt certificate password for database storage
    
    Args:
        password: Plain text password
        
    Returns:
        Encrypted password string for database storage
    """
    return secure_data_manager.encrypt_password(password)


def decrypt_password_from_storage(encrypted_password: str) -> str:
    """
    Decrypt certificate password from database storage
    
    Args:
        encrypted_password: Encrypted password from database
        
    Returns:
        Plain text password
    """
    return secure_data_manager.decrypt_password(encrypted_password)


def generate_document_security_code() -> str:
    """
    Generate 8-digit security code for document keys
    
    Returns:
        8-digit numeric security code
    """
    return SecureRandom.generate_security_code(8)


def create_data_integrity_hash(data: bytes) -> str:
    """
    Create integrity hash for data verification
    
    Args:
        data: Data to hash
        
    Returns:
        SHA-256 hash for integrity verification
    """
    return DataIntegrityChecker.create_checksum(data)