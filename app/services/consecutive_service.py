"""
Consecutive number and document key management service for Costa Rica electronic documents.
Handles automatic generation, validation, and uniqueness for all document types.
"""
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError

from app.models.document import Document, DocumentType
from app.models.tenant import Tenant
from app.utils.validators import validate_consecutive_number, validate_document_key


class ConsecutiveService:
    """
    Consecutive number and document key management service
    
    Handles automatic generation of consecutive numbers and document keys
    following Costa Rican Ministry of Finance specifications.
    
    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_consecutive_number(
        self, 
        tenant: Tenant, 
        document_type: DocumentType,
        branch: str = "001",
        terminal: str = "00001"
    ) -> str:
        """
        Generate automatic consecutive number with proper format (20 digits)
        
        Format: Branch(3) + Terminal(5) + DocType(2) + Sequential(10)
        Example: 00100001010000076513
        
        Args:
            tenant: Tenant instance
            document_type: Document type
            branch: Branch code (3 digits, default: "001")
            terminal: Terminal/point-of-sale code (5 digits, default: "00001")
            
        Returns:
            20-digit consecutive number
            
        Raises:
            ValueError: If validation fails
            
        Requirements: 10.1, 10.2 - automatic consecutive number generation
        """
        # Validate branch and terminal configuration
        self._validate_branch_terminal_config(branch, terminal)
        
        # Get next sequential number for this tenant, document type, branch, and terminal
        sequential = self._get_next_sequential_number(tenant.id, document_type, branch, terminal)
        
        # Format consecutive number
        consecutive = f"{branch}{terminal}{document_type.value}{sequential:010d}"
        
        # Validate format
        if not validate_consecutive_number(consecutive):
            raise ValueError(f"Generated consecutive number has invalid format: {consecutive}")
        
        return consecutive
    
    def generate_document_key(
        self,
        tenant: Tenant,
        document_type: DocumentType,
        consecutive_number: str,
        emission_date: Optional[datetime] = None
    ) -> str:
        """
        Generate 50-character document key following official format
        
        Format: Country(3) + Day(2) + Month(2) + Year(2) + Issuer(12) + 
                Branch(3) + Terminal(5) + DocType(2) + Sequential(10) + SecurityCode(8)
        
        Args:
            tenant: Tenant instance
            document_type: Document type
            consecutive_number: 20-digit consecutive number
            emission_date: Document emission date (default: now)
            
        Returns:
            50-character document key
            
        Raises:
            ValueError: If validation fails
            
        Requirements: 10.3, 10.4 - document key generation with all components
        """
        if not emission_date:
            emission_date = datetime.now(timezone.utc)
        
        # Validate consecutive number format
        if not validate_consecutive_number(consecutive_number):
            raise ValueError(f"Invalid consecutive number format: {consecutive_number}")
        
        # Extract components from consecutive number
        branch = consecutive_number[0:3]
        terminal = consecutive_number[3:8]
        doc_type = consecutive_number[8:10]
        sequential = consecutive_number[10:20]
        
        # Validate document type matches
        if doc_type != document_type.value:
            raise ValueError(f"Document type mismatch: {doc_type} != {document_type.value}")
        
        # Build document key components
        country = "506"  # Costa Rica country code
        day = f"{emission_date.day:02d}"
        month = f"{emission_date.month:02d}"
        year = f"{emission_date.year % 100:02d}"
        
        # Format issuer identification (12 digits, padded with zeros)
        issuer_id = self._format_issuer_identification(tenant.cedula_juridica)
        
        # Generate security code (8 random digits)
        security_code = self._generate_security_code()
        
        # Assemble document key
        document_key = f"{country}{day}{month}{year}{issuer_id}{branch}{terminal}{doc_type}{sequential}{security_code}"
        
        # Validate final format
        if not validate_document_key(document_key):
            raise ValueError(f"Generated document key has invalid format: {document_key}")
        
        # Ensure uniqueness
        if self._is_document_key_exists(document_key):
            # Regenerate with new security code (very unlikely collision)
            return self.generate_document_key(tenant, document_type, consecutive_number, emission_date)
        
        return document_key
    
    def validate_consecutive_uniqueness(
        self,
        tenant_id: UUID,
        consecutive_number: str,
        document_type: DocumentType,
        exclude_document_id: Optional[UUID] = None
    ) -> bool:
        """
        Validate consecutive number uniqueness per document type
        
        Args:
            tenant_id: Tenant UUID
            consecutive_number: Consecutive number to validate
            document_type: Document type
            exclude_document_id: Document ID to exclude from check (for updates)
            
        Returns:
            True if unique, False if already exists
            
        Requirements: 10.2 - consecutive number validation and uniqueness
        """
        query = self.db.query(Document).filter(
            and_(
                Document.tenant_id == tenant_id,
                Document.numero_consecutivo == consecutive_number,
                Document.tipo_documento == document_type
            )
        )
        
        if exclude_document_id:
            query = query.filter(Document.id != exclude_document_id)
        
        return query.first() is None
    
    def validate_document_key_uniqueness(
        self,
        document_key: str,
        exclude_document_id: Optional[UUID] = None
    ) -> bool:
        """
        Validate document key uniqueness across all tenants and document types
        
        Args:
            document_key: Document key to validate
            exclude_document_id: Document ID to exclude from check (for updates)
            
        Returns:
            True if unique, False if already exists
            
        Requirements: 10.5 - key uniqueness validation across all tenants
        """
        query = self.db.query(Document).filter(Document.clave == document_key)
        
        if exclude_document_id:
            query = query.filter(Document.id != exclude_document_id)
        
        return query.first() is None
    
    def get_branch_terminal_config(self, tenant_id: UUID) -> Dict[str, Dict[str, str]]:
        """
        Get branch and point-of-sale configuration per tenant
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Dictionary with branch and terminal configurations
            
        Requirements: 10.1 - branch and point-of-sale configuration per tenant
        """
        # For now, return default configuration
        # In a full implementation, this would be stored in a separate table
        return {
            "default": {
                "branch": "001",
                "terminal": "00001",
                "name": "Sucursal Principal - Terminal 1"
            }
        }
    
    def get_next_consecutive_preview(
        self,
        tenant_id: UUID,
        document_type: DocumentType,
        branch: str = "001",
        terminal: str = "00001"
    ) -> str:
        """
        Preview the next consecutive number without reserving it
        
        Args:
            tenant_id: Tenant UUID
            document_type: Document type
            branch: Branch code
            terminal: Terminal code
            
        Returns:
            Next consecutive number that would be generated
        """
        # Get next sequential number
        sequential = self._get_next_sequential_number(tenant_id, document_type, branch, terminal)
        
        # Format consecutive number
        return f"{branch}{terminal}{document_type.value}{sequential:010d}"
    
    def parse_consecutive_number(self, consecutive_number: str) -> Dict[str, str]:
        """
        Parse consecutive number into its components
        
        Args:
            consecutive_number: 20-digit consecutive number
            
        Returns:
            Dictionary with parsed components
            
        Raises:
            ValueError: If format is invalid
        """
        if not validate_consecutive_number(consecutive_number):
            raise ValueError(f"Invalid consecutive number format: {consecutive_number}")
        
        return {
            "branch": consecutive_number[0:3],
            "terminal": consecutive_number[3:8],
            "document_type": consecutive_number[8:10],
            "sequential": consecutive_number[10:20]
        }
    
    def parse_document_key(self, document_key: str) -> Dict[str, str]:
        """
        Parse document key into its components
        
        Args:
            document_key: 50-character document key
            
        Returns:
            Dictionary with parsed components
            
        Raises:
            ValueError: If format is invalid
        """
        if not validate_document_key(document_key):
            raise ValueError(f"Invalid document key format: {document_key}")
        
        return {
            "country": document_key[0:3],
            "day": document_key[3:5],
            "month": document_key[5:7],
            "year": document_key[7:9],
            "issuer": document_key[9:21],
            "branch": document_key[21:24],
            "terminal": document_key[24:29],
            "document_type": document_key[29:31],
            "sequential": document_key[31:41],
            "security_code": document_key[41:49]
        }
    
    def get_consecutive_statistics(
        self,
        tenant_id: UUID,
        document_type: Optional[DocumentType] = None
    ) -> Dict[str, any]:
        """
        Get consecutive number usage statistics
        
        Args:
            tenant_id: Tenant UUID
            document_type: Optional document type filter
            
        Returns:
            Statistics dictionary
        """
        query = self.db.query(Document).filter(Document.tenant_id == tenant_id)
        
        if document_type:
            query = query.filter(Document.tipo_documento == document_type)
        
        # Get total count
        total_documents = query.count()
        
        # Get count by document type
        by_type = {}
        for doc_type in DocumentType:
            count = query.filter(Document.tipo_documento == doc_type).count()
            if count > 0:
                by_type[doc_type.value] = count
        
        # Get latest consecutive numbers by type
        latest_consecutives = {}
        for doc_type in DocumentType:
            latest = query.filter(Document.tipo_documento == doc_type)\
                         .order_by(Document.numero_consecutivo.desc())\
                         .first()
            if latest:
                latest_consecutives[doc_type.value] = latest.numero_consecutivo
        
        return {
            "total_documents": total_documents,
            "by_document_type": by_type,
            "latest_consecutives": latest_consecutives
        }
    
    # Private helper methods
    
    def _validate_branch_terminal_config(self, branch: str, terminal: str) -> None:
        """Validate branch and terminal configuration"""
        if not re.match(r'^\d{3}$', branch):
            raise ValueError(f"Branch must be exactly 3 digits: {branch}")
        
        if not re.match(r'^\d{5}$', terminal):
            raise ValueError(f"Terminal must be exactly 5 digits: {terminal}")
    
    def _get_next_sequential_number(
        self,
        tenant_id: UUID,
        document_type: DocumentType,
        branch: str,
        terminal: str
    ) -> int:
        """Get next sequential number for the given parameters"""
        # Build consecutive prefix (branch + terminal + doc_type)
        prefix = f"{branch}{terminal}{document_type.value}"
        
        # Find the highest sequential number for this prefix
        max_consecutive = self.db.query(func.max(Document.numero_consecutivo))\
            .filter(
                and_(
                    Document.tenant_id == tenant_id,
                    Document.numero_consecutivo.like(f"{prefix}%")
                )
            ).scalar()
        
        if max_consecutive:
            # Extract sequential part and increment
            sequential_part = max_consecutive[10:20]  # Last 10 digits
            return int(sequential_part) + 1
        else:
            # First document of this type for this tenant/branch/terminal
            return 1
    
    def _format_issuer_identification(self, cedula_juridica: str) -> str:
        """Format issuer identification to 12 digits"""
        # Remove any formatting and ensure numeric
        clean_cedula = re.sub(r'[^\d]', '', cedula_juridica)
        
        # Pad with zeros to 12 digits (left-padded)
        return f"{clean_cedula:0>12}"[:12]
    
    def _generate_security_code(self) -> str:
        """Generate 8-digit security code for document uniqueness"""
        import random
        return f"{random.randint(10000000, 99999999)}"
    
    def _is_document_key_exists(self, document_key: str) -> bool:
        """Check if document key already exists"""
        return self.db.query(Document).filter(Document.clave == document_key).first() is not None


# Convenience functions for dependency injection

def get_consecutive_service(db: Session = None) -> ConsecutiveService:
    """Get consecutive service instance"""
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()
    return ConsecutiveService(db)