"""
XML service for Costa Rica electronic documents.
Handles XML generation, validation, and processing workflow.

Requirements: 9.1, 11.1, 14.1, 15.1, 17.1
"""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.tenant import Tenant
from app.schemas.documents import DocumentCreate
from app.utils.xml_generator import XMLGenerator, generate_document_xml
from app.utils.validators import validate_consecutive_number, validate_document_key


class XMLService:
    """
    Service for XML generation and processing.
    Handles the complete XML workflow for electronic documents.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_document_xml(
        self,
        tenant: Tenant,
        document_data: DocumentCreate,
        numero_consecutivo: Optional[str] = None,
        clave: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Generate XML for a document with automatic key generation.
        
        Args:
            tenant: Tenant information
            document_data: Document creation data
            numero_consecutivo: Optional consecutive number (auto-generated if not provided)
            clave: Optional document key (auto-generated if not provided)
            
        Returns:
            Tuple of (xml_content, numero_consecutivo, clave)
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If generation fails
        """
        try:
            # Generate consecutive number if not provided
            if not numero_consecutivo:
                numero_consecutivo = self._generate_consecutive_number(
                    tenant, document_data.tipo_documento
                )
            
            # Validate consecutive number format
            if not validate_consecutive_number(numero_consecutivo):
                raise ValueError(f"Invalid consecutive number format: {numero_consecutivo}")
            
            # Generate document key if not provided
            if not clave:
                clave = self._generate_document_key(
                    tenant, document_data, numero_consecutivo
                )
            
            # Validate document key format
            if not validate_document_key(clave):
                raise ValueError(f"Invalid document key format: {clave}")
            
            # Check for duplicate keys
            if self._is_duplicate_key(clave):
                raise ValueError(f"Document key already exists: {clave}")
            
            # Generate XML using the generator
            xml_content = generate_document_xml(
                document_data=document_data,
                tenant_id=str(tenant.id),
                numero_consecutivo=numero_consecutivo,
                clave=clave,
                fecha_emision=datetime.now(timezone.utc),
                proveedor_sistemas=tenant.cedula_juridica
            )
            
            # Validate generated XML structure
            self._validate_xml_structure(xml_content, document_data.tipo_documento)
            
            return xml_content, numero_consecutivo, clave
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate XML: {str(e)}") from e
    
    def create_document_with_xml(
        self,
        tenant: Tenant,
        document_data: DocumentCreate,
        created_by: Optional[str] = None
    ) -> Document:
        """
        Create a complete document with generated XML.
        
        Args:
            tenant: Tenant information
            document_data: Document creation data
            created_by: User who created the document
            
        Returns:
            Created Document instance
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If creation fails
        """
        try:
            # Generate XML and keys
            xml_content, numero_consecutivo, clave = self.generate_document_xml(
                tenant, document_data
            )
            
            # Calculate document hash for integrity
            document_hash = self._calculate_document_hash(xml_content)
            
            # Calculate totals from document data
            totals = self._calculate_document_totals(document_data)
            
            # Create document instance
            document = Document(
                tenant_id=tenant.id,
                tipo_documento=document_data.tipo_documento,
                numero_consecutivo=numero_consecutivo,
                clave=clave,
                fecha_emision=datetime.now(timezone.utc),
                
                # Emisor information
                emisor_nombre=document_data.emisor.nombre,
                emisor_tipo_identificacion=document_data.emisor.identificacion.tipo,
                emisor_numero_identificacion=document_data.emisor.identificacion.numero,
                emisor_nombre_comercial=document_data.emisor.nombre_comercial,
                emisor_codigo_actividad=document_data.emisor.codigo_actividad,
                
                # Emisor location
                emisor_provincia=document_data.emisor.ubicacion.provincia,
                emisor_canton=document_data.emisor.ubicacion.canton,
                emisor_distrito=document_data.emisor.ubicacion.distrito,
                emisor_barrio=document_data.emisor.ubicacion.barrio,
                emisor_otras_senas=document_data.emisor.ubicacion.otras_senas,
                
                # Emisor contact
                emisor_codigo_pais_telefono=document_data.emisor.telefono.codigo_pais if document_data.emisor.telefono else None,
                emisor_numero_telefono=str(document_data.emisor.telefono.numero) if document_data.emisor.telefono else None,
                emisor_correo_electronico=document_data.emisor.correo_electronico[0],
                
                # Receptor information (optional for tickets)
                receptor_nombre=document_data.receptor.nombre if document_data.receptor else None,
                receptor_tipo_identificacion=document_data.receptor.identificacion.tipo if document_data.receptor and document_data.receptor.identificacion else None,
                receptor_numero_identificacion=document_data.receptor.identificacion.numero if document_data.receptor and document_data.receptor.identificacion else None,
                receptor_nombre_comercial=document_data.receptor.nombre_comercial if document_data.receptor else None,
                receptor_codigo_actividad=document_data.receptor.codigo_actividad if document_data.receptor else None,
                
                # Receptor location
                receptor_provincia=document_data.receptor.ubicacion.provincia if document_data.receptor and document_data.receptor.ubicacion else None,
                receptor_canton=document_data.receptor.ubicacion.canton if document_data.receptor and document_data.receptor.ubicacion else None,
                receptor_distrito=document_data.receptor.ubicacion.distrito if document_data.receptor and document_data.receptor.ubicacion else None,
                receptor_barrio=document_data.receptor.ubicacion.barrio if document_data.receptor and document_data.receptor.ubicacion else None,
                receptor_otras_senas=document_data.receptor.ubicacion.otras_senas if document_data.receptor and document_data.receptor.ubicacion else None,
                receptor_otras_senas_extranjero=document_data.receptor.otras_senas_extranjero if document_data.receptor else None,
                
                # Receptor contact
                receptor_codigo_pais_telefono=document_data.receptor.telefono.codigo_pais if document_data.receptor and document_data.receptor.telefono else None,
                receptor_numero_telefono=str(document_data.receptor.telefono.numero) if document_data.receptor and document_data.receptor.telefono else None,
                receptor_correo_electronico=document_data.receptor.correo_electronico if document_data.receptor else None,
                
                # Transaction conditions
                condicion_venta=document_data.condicion_venta,
                condicion_venta_otros=document_data.condicion_venta_otros,
                plazo_credito=document_data.plazo_credito,
                medio_pago=document_data.medio_pago,
                medio_pago_otros=document_data.medio_pago_otros,
                
                # Currency and totals
                codigo_moneda=document_data.codigo_moneda,
                tipo_cambio=document_data.tipo_cambio,
                total_venta_neta=totals['total_venta_neta'],
                total_impuesto=totals['total_impuesto'],
                total_descuento=totals['total_descuentos'],
                total_otros_cargos=totals['total_otros_cargos'],
                total_comprobante=totals['total_comprobante'],
                
                # XML and processing
                xml_original=xml_content,
                hash_documento=document_hash,
                observaciones=document_data.observaciones,
                created_by=created_by
            )
            
            # Save to database
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            return document
            
        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Failed to create document: {str(e)}") from e
    
    def regenerate_xml(self, document: Document) -> str:
        """
        Regenerate XML for an existing document.
        
        Args:
            document: Document instance
            
        Returns:
            Regenerated XML content
            
        Raises:
            RuntimeError: If regeneration fails
        """
        try:
            # Reconstruct document data from database record
            document_data = self._reconstruct_document_data(document)
            
            # Generate XML
            xml_content = generate_document_xml(
                document_data=document_data,
                tenant_id=str(document.tenant_id),
                numero_consecutivo=document.numero_consecutivo,
                clave=document.clave,
                fecha_emision=document.fecha_emision,
                proveedor_sistemas=document.tenant.cedula_juridica
            )
            
            # Update document with new XML
            document.xml_original = xml_content
            document.hash_documento = self._calculate_document_hash(xml_content)
            document.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            return xml_content
            
        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Failed to regenerate XML: {str(e)}") from e
    
    def _generate_consecutive_number(self, tenant: Tenant, document_type: str) -> str:
        """
        Generate consecutive number for document.
        Format: Branch(3) + Terminal(5) + DocType(2) + Sequential(10)
        
        Args:
            tenant: Tenant information
            document_type: Document type code
            
        Returns:
            20-digit consecutive number
        """
        # Get next sequential number for this tenant and document type
        last_document = self.db.query(Document).filter(
            Document.tenant_id == tenant.id,
            Document.tipo_documento == document_type
        ).order_by(Document.numero_consecutivo.desc()).first()
        
        if last_document:
            # Extract sequential part and increment
            last_consecutive = last_document.numero_consecutivo
            sequential_part = int(last_consecutive[-10:])
            next_sequential = sequential_part + 1
        else:
            next_sequential = 1
        
        # Default branch and terminal (can be configured per tenant)
        branch = "001"  # Default branch
        terminal = "00001"  # Default terminal
        
        # Format: Branch(3) + Terminal(5) + DocType(2) + Sequential(10)
        consecutive_number = f"{branch}{terminal}{document_type}{next_sequential:010d}"
        
        return consecutive_number
    
    def _generate_document_key(
        self, 
        tenant: Tenant, 
        document_data: DocumentCreate,
        numero_consecutivo: str
    ) -> str:
        """
        Generate 50-digit document key.
        Format: Country(3) + Day(2) + Month(2) + Year(2) + Issuer(12) + Branch(3) + Terminal(5) + DocType(2) + Sequential(10) + SecurityCode(8)
        
        Args:
            tenant: Tenant information
            document_data: Document data
            numero_consecutivo: Consecutive number
            
        Returns:
            50-digit document key
        """
        now = datetime.now(timezone.utc)
        
        # Country code (Costa Rica)
        country = "506"
        
        # Date components
        day = f"{now.day:02d}"
        month = f"{now.month:02d}"
        year = f"{now.year % 100:02d}"
        
        # Issuer identification (12 digits, padded with zeros)
        issuer_id = document_data.emisor.identificacion.numero.replace("-", "")
        issuer_padded = issuer_id.ljust(12, "0")[:12]
        
        # Extract branch, terminal, doc type, and sequential from consecutive number
        branch = numero_consecutivo[:3]
        terminal = numero_consecutivo[3:8]
        doc_type = numero_consecutivo[8:10]
        sequential = numero_consecutivo[10:20]
        
        # Generate security code (8 random digits)
        security_code = f"{uuid.uuid4().int % 100000000:08d}"
        
        # Combine all parts
        document_key = f"{country}{day}{month}{year}{issuer_padded}{branch}{terminal}{doc_type}{sequential}{security_code}"
        
        return document_key
    
    def _is_duplicate_key(self, clave: str) -> bool:
        """Check if document key already exists."""
        existing = self.db.query(Document).filter(Document.clave == clave).first()
        return existing is not None
    
    def _validate_xml_structure(self, xml_content: str, document_type: str) -> None:
        """
        Validate XML structure (basic validation).
        Full XSD validation will be implemented in task 6.3.
        
        Args:
            xml_content: XML content to validate
            document_type: Document type code
            
        Raises:
            ValueError: If validation fails
        """
        # Basic validation - check if XML is well-formed
        try:
            from xml.etree.ElementTree import fromstring
            fromstring(xml_content)
        except Exception as e:
            raise ValueError(f"Invalid XML structure: {str(e)}")
        
        # Check if root element matches document type
        expected_roots = {
            "01": "FacturaElectronica",
            "02": "NotaDebitoElectronica", 
            "03": "NotaCreditoElectronica",
            "04": "TiqueteElectronico",
            "05": "FacturaElectronicaExportacion",
            "06": "FacturaElectronicaCompra",
            "07": "ReciboElectronicoPago"
        }
        
        expected_root = expected_roots.get(document_type)
        if expected_root and expected_root not in xml_content:
            raise ValueError(f"XML does not contain expected root element: {expected_root}")
    
    def _calculate_document_hash(self, xml_content: str) -> str:
        """Calculate SHA-256 hash of XML content for integrity."""
        return hashlib.sha256(xml_content.encode('utf-8')).hexdigest()
    
    def _calculate_document_totals(self, document_data: DocumentCreate) -> Dict[str, Any]:
        """
        Calculate document totals from line items.
        
        Args:
            document_data: Document creation data
            
        Returns:
            Dictionary with calculated totals
        """
        totals = {
            'total_venta_neta': 0,
            'total_impuesto': 0,
            'total_descuentos': 0,
            'total_otros_cargos': 0,
            'total_comprobante': 0
        }
        
        # Calculate from line items
        for detalle in document_data.detalles:
            line_total = detalle.monto_total
            discount_amount = detalle.descuento.monto_descuento if detalle.descuento else 0
            
            totals['total_venta_neta'] += line_total - discount_amount
            totals['total_descuentos'] += discount_amount
            
            # Calculate taxes
            for impuesto in detalle.impuestos:
                totals['total_impuesto'] += impuesto.monto
        
        # Add other charges
        if document_data.otros_cargos:
            totals['total_otros_cargos'] = sum(cargo.monto_cargo for cargo in document_data.otros_cargos)
        
        # Final total
        totals['total_comprobante'] = (
            totals['total_venta_neta'] + 
            totals['total_impuesto'] + 
            totals['total_otros_cargos']
        )
        
        return totals
    
    def _reconstruct_document_data(self, document: Document) -> DocumentCreate:
        """
        Reconstruct DocumentCreate from database record.
        This is a simplified version - in a full implementation,
        you'd need to reconstruct all line items and related data.
        
        Args:
            document: Document instance
            
        Returns:
            Reconstructed DocumentCreate instance
        """
        # This is a placeholder implementation
        # In a real scenario, you'd need to reconstruct the complete
        # document data including line items, taxes, etc.
        from app.schemas.base import EmisorData, ReceptorData, IdentificationData, LocationData
        
        # Reconstruct emisor data
        emisor = EmisorData(
            nombre=document.emisor_nombre,
            identificacion=IdentificationData(
                tipo=document.emisor_tipo_identificacion,
                numero=document.emisor_numero_identificacion
            ),
            nombre_comercial=document.emisor_nombre_comercial,
            ubicacion=LocationData(
                provincia=document.emisor_provincia,
                canton=document.emisor_canton,
                distrito=document.emisor_distrito,
                barrio=document.emisor_barrio,
                otras_senas=document.emisor_otras_senas
            ),
            correo_electronico=[document.emisor_correo_electronico],
            codigo_actividad=document.emisor_codigo_actividad
        )
        
        # Reconstruct receptor data (if exists)
        receptor = None
        if document.receptor_nombre:
            receptor = ReceptorData(
                nombre=document.receptor_nombre,
                identificacion=IdentificationData(
                    tipo=document.receptor_tipo_identificacion,
                    numero=document.receptor_numero_identificacion
                ) if document.receptor_tipo_identificacion else None,
                nombre_comercial=document.receptor_nombre_comercial,
                ubicacion=LocationData(
                    provincia=document.receptor_provincia,
                    canton=document.receptor_canton,
                    distrito=document.receptor_distrito,
                    barrio=document.receptor_barrio,
                    otras_senas=document.receptor_otras_senas
                ) if document.receptor_provincia else None,
                otras_senas_extranjero=document.receptor_otras_senas_extranjero,
                correo_electronico=document.receptor_correo_electronico,
                codigo_actividad=document.receptor_codigo_actividad
            )
        
        # Create basic document data (line items would need to be reconstructed from related tables)
        document_data = DocumentCreate(
            tipo_documento=document.tipo_documento,
            emisor=emisor,
            receptor=receptor,
            condicion_venta=document.condicion_venta,
            condicion_venta_otros=document.condicion_venta_otros,
            plazo_credito=document.plazo_credito,
            medio_pago=document.medio_pago,
            medio_pago_otros=document.medio_pago_otros,
            codigo_moneda=document.codigo_moneda,
            tipo_cambio=document.tipo_cambio,
            detalles=[],  # Would need to be reconstructed from DocumentDetail table
            observaciones=document.observaciones
        )
        
        return document_data


def get_xml_service(db: Session = None) -> XMLService:
    """Get XML service instance with database session."""
    if db is None:
        db = next(get_db())
    return XMLService(db)