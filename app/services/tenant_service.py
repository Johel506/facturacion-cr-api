"""
Comprehensive tenant management service for multi-tenant Costa Rica invoice API.
Handles tenant CRUD operations, plan management, usage tracking, and statistics.
"""
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError

from app.models.tenant import Tenant
from app.schemas.tenants import (
    TenantCreate, TenantUpdate, TenantResponse, TenantDetail, 
    TenantUsage, TenantStats, CertificateStatus
)
from app.schemas.enums import TenantPlan
from app.core.security import (
    generate_tenant_api_key, verify_tenant_api_key,
    encrypt_certificate_data, decrypt_certificate_data
)
from app.core.database import get_db
from app.utils.business_validators_fixed import validate_email_format, validate_cedula_juridica


class TenantService:
    """
    Comprehensive tenant management service
    
    Handles all tenant-related operations including creation, updates,
    plan management, usage tracking, and statistics reporting.
    
    Requirements: 1.1, 1.5
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_tenant(self, tenant_data: TenantCreate) -> Tuple[Tenant, str]:
        """
        Create a new tenant with enhanced validation
        
        Args:
            tenant_data: Tenant creation data
            
        Returns:
            Tuple of (created_tenant, plain_api_key)
            
        Raises:
            ValueError: If validation fails
            IntegrityError: If tenant already exists
            
        Requirements: 1.1 - tenant creation with business information
        """
        # Enhanced validation
        self._validate_tenant_creation_data(tenant_data)
        
        # Generate secure API key
        tenant_id_str = str(uuid4())  # Generate temporary UUID for key generation
        api_key, api_key_hash = generate_tenant_api_key(tenant_id_str)
        
        # Get plan limits
        plan_limits = self._get_plan_limits(tenant_data.plan)
        
        # Create tenant instance
        tenant = Tenant(
            nombre_empresa=tenant_data.nombre_empresa.strip(),
            cedula_juridica=self._normalize_cedula_juridica(tenant_data.cedula_juridica),
            email_contacto=tenant_data.email_contacto.lower(),
            plan=tenant_data.plan,
            limite_facturas_mes=plan_limits['limite_mensual'],
            api_key=api_key_hash,  # Store hashed version
            api_key_created_at=datetime.now(timezone.utc),
            activo=True,
            verificado=False,  # Requires email verification
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        try:
            self.db.add(tenant)
            self.db.commit()
            self.db.refresh(tenant)
            
            # Log tenant creation
            # self._log_tenant_activity(tenant.id, "tenant_created", {
            #     "plan": tenant_data.plan,
            #     "email": tenant_data.email_contacto
            # })
            
            return tenant, api_key  # Return plain API key for client
            
        except IntegrityError as e:
            self.db.rollback()
            if "cedula_juridica" in str(e):
                raise ValueError("A tenant with this legal ID already exists")
            elif "api_key" in str(e):
                # Retry with new API key (very unlikely collision)
                return self.create_tenant(tenant_data)
            else:
                raise ValueError(f"Failed to create tenant: {str(e)}")
    
    def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Retrieve tenant by ID
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Tenant instance or None if not found
        """
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    def get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """
        Retrieve tenant by API key
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Tenant instance or None if not found
        """
        # Get all tenants and verify API key (since we store hashed versions)
        tenants = self.db.query(Tenant).filter(Tenant.activo == True).all()
        
        for tenant in tenants:
            if verify_tenant_api_key(api_key, tenant.api_key):
                # Update last access time
                tenant.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                return tenant
        
        return None
    
    def get_tenant_by_cedula(self, cedula_juridica: str) -> Optional[Tenant]:
        """
        Retrieve tenant by legal ID
        
        Args:
            cedula_juridica: Legal identification number
            
        Returns:
            Tenant instance or None if not found
        """
        normalized_cedula = self._normalize_cedula_juridica(cedula_juridica)
        return self.db.query(Tenant).filter(
            Tenant.cedula_juridica == normalized_cedula
        ).first()
    
    def update_tenant(self, tenant_id: UUID, updates: TenantUpdate) -> Tenant:
        """
        Update tenant information with plan management
        
        Args:
            tenant_id: Tenant UUID
            updates: Update data
            
        Returns:
            Updated tenant instance
            
        Raises:
            ValueError: If tenant not found or validation fails
            
        Requirements: 1.5 - plan management and updates
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Track changes for audit log
        changes = {}
        
        # Update fields if provided
        if updates.nombre_empresa is not None:
            if updates.nombre_empresa != tenant.nombre_empresa:
                changes['nombre_empresa'] = {
                    'old': tenant.nombre_empresa,
                    'new': updates.nombre_empresa
                }
                tenant.nombre_empresa = updates.nombre_empresa.strip()
        
        if updates.email_contacto is not None:
            new_email = updates.email_contacto.lower()
            if new_email != tenant.email_contacto:
                # Validate email format
                if not validate_email_format(new_email):
                    raise ValueError("Invalid email format")
                
                changes['email_contacto'] = {
                    'old': tenant.email_contacto,
                    'new': new_email
                }
                tenant.email_contacto = new_email
                tenant.verificado = False  # Require re-verification
        
        if updates.plan is not None:
            if updates.plan != tenant.plan:
                old_plan = tenant.plan
                new_limits = self._get_plan_limits(updates.plan)
                
                changes['plan'] = {
                    'old': old_plan,
                    'new': updates.plan,
                    'old_limit': tenant.limite_facturas_mes,
                    'new_limit': new_limits['limite_mensual']
                }
                
                tenant.plan = updates.plan
                tenant.limite_facturas_mes = new_limits['limite_mensual']
                
                # Reset monthly counter if upgrading
                if self._is_plan_upgrade(old_plan, updates.plan):
                    tenant.facturas_usadas_mes = 0
                    tenant.ultimo_reset_contador = datetime.now(timezone.utc)
        
        if updates.activo is not None:
            if updates.activo != tenant.activo:
                changes['activo'] = {
                    'old': tenant.activo,
                    'new': updates.activo
                }
                tenant.activo = updates.activo
        
        # Update timestamp
        tenant.updated_at = datetime.now(timezone.utc)
        
        try:
            self.db.commit()
            self.db.refresh(tenant)
            
            # Log changes
            if changes:
                self._log_tenant_activity(tenant_id, "tenant_updated", changes)
            
            return tenant
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Failed to update tenant: {str(e)}")
    
    def activate_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Activate tenant account
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Updated tenant instance
        """
        return self.update_tenant(tenant_id, TenantUpdate(activo=True))
    
    def deactivate_tenant(self, tenant_id: UUID, cascade: bool = True) -> Tenant:
        """
        Deactivate tenant with cascade effects
        
        Args:
            tenant_id: Tenant UUID
            cascade: Whether to cascade deactivation effects
            
        Returns:
            Updated tenant instance
            
        Requirements: 1.5 - activation/deactivation with cascade effects
        """
        tenant = self.update_tenant(tenant_id, TenantUpdate(activo=False))
        
        if cascade:
            # Cascade effects of deactivation
            self._handle_tenant_deactivation_cascade(tenant_id)
        
        return tenant
    
    def get_tenant_usage(self, tenant_id: UUID) -> TenantUsage:
        """
        Get tenant usage statistics and tracking
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Tenant usage statistics
            
        Requirements: 1.5 - usage tracking
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Check if monthly counter should be reset
        if tenant.should_reset_monthly_counter():
            self.reset_monthly_usage(tenant_id)
            tenant = self.get_tenant(tenant_id)  # Refresh data
        
        # Get document statistics by type (would require Document model)
        documentos_por_tipo = self._get_documents_by_type(tenant_id)
        
        return TenantUsage(
            facturas_usadas_mes=tenant.facturas_usadas_mes,
            limite_facturas_mes=tenant.limite_facturas_mes,
            porcentaje_uso=tenant.monthly_limit_percentage,
            documentos_por_tipo=documentos_por_tipo,
            ultimo_documento=tenant.ultimo_documento_creado
        )
    
    def reset_monthly_usage(self, tenant_id: UUID) -> Tenant:
        """
        Reset monthly usage counter
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Updated tenant instance
            
        Requirements: 1.5 - monthly limits reset
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        old_usage = tenant.facturas_usadas_mes
        tenant.reset_monthly_counter()
        
        self.db.commit()
        self.db.refresh(tenant)
        
        # Log reset
        self._log_tenant_activity(tenant_id, "monthly_usage_reset", {
            "old_usage": old_usage,
            "reset_date": datetime.now(timezone.utc).isoformat()
        })
        
        return tenant
    
    def increment_usage(self, tenant_id: UUID) -> bool:
        """
        Increment tenant usage counter
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if increment successful, False if limit reached
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Check if can create document
        if not tenant.can_create_document():
            return False
        
        # Check monthly counter reset
        if tenant.should_reset_monthly_counter():
            tenant.reset_monthly_counter()
        
        # Increment usage
        tenant.increment_usage()
        
        self.db.commit()
        return True
    
    def get_tenant_statistics(self, tenant_id: UUID) -> TenantStats:
        """
        Get comprehensive tenant statistics and reporting
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Tenant statistics summary
            
        Requirements: 1.5 - statistics and reporting functionality
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Calculate statistics (would require Document model for full implementation)
        current_month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Mock statistics - in real implementation, query Document model
        documentos_por_estado = {
            "pendiente": 0,
            "enviado": 0,
            "aceptado": tenant.total_documentos_aceptados,
            "rechazado": 0,
            "error": 0
        }
        
        documentos_por_tipo = self._get_documents_by_type(tenant_id)
        
        # Calculate average documents per day
        days_since_creation = (datetime.now(timezone.utc) - tenant.created_at).days or 1
        promedio_documentos_dia = tenant.total_documentos_creados / days_since_creation
        
        return TenantStats(
            total_documentos=tenant.total_documentos_creados,
            documentos_mes_actual=tenant.facturas_usadas_mes,
            documentos_por_estado=documentos_por_estado,
            documentos_por_tipo=documentos_por_tipo,
            monto_total_facturado=0.0,  # Would calculate from Document model
            promedio_documentos_dia=round(promedio_documentos_dia, 2),
            ultimo_documento=tenant.ultimo_documento_creado
        )
    
    def list_tenants(
        self, 
        skip: int = 0, 
        limit: int = 100,
        plan: Optional[TenantPlan] = None,
        activo: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[Tenant]:
        """
        List tenants with filtering and pagination
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            plan: Filter by plan
            activo: Filter by active status
            search: Search in company name or legal ID
            
        Returns:
            List of tenant instances
        """
        query = self.db.query(Tenant)
        
        # Apply filters
        if plan is not None:
            query = query.filter(Tenant.plan == plan)
        
        if activo is not None:
            query = query.filter(Tenant.activo == activo)
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Tenant.nombre_empresa).like(search_term),
                    Tenant.cedula_juridica.like(search_term)
                )
            )
        
        # Order by creation date (newest first)
        query = query.order_by(Tenant.created_at.desc())
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()
    
    def count_tenants(
        self,
        plan: Optional[TenantPlan] = None,
        activo: Optional[bool] = None,
        search: Optional[str] = None
    ) -> int:
        """
        Count tenants with filtering
        
        Args:
            plan: Filter by plan
            activo: Filter by active status
            search: Search in company name or legal ID
            
        Returns:
            Total count of matching tenants
        """
        query = self.db.query(func.count(Tenant.id))
        
        # Apply same filters as list_tenants
        if plan is not None:
            query = query.filter(Tenant.plan == plan)
        
        if activo is not None:
            query = query.filter(Tenant.activo == activo)
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Tenant.nombre_empresa).like(search_term),
                    Tenant.cedula_juridica.like(search_term)
                )
            )
        
        return query.scalar()
    
    def regenerate_api_key(self, tenant_id: UUID) -> Tuple[Tenant, str]:
        """
        Regenerate API key for tenant
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Tuple of (updated_tenant, new_plain_api_key)
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Generate new API key
        new_api_key, new_api_key_hash = generate_tenant_api_key(str(tenant_id))
        
        # Update tenant
        old_key_created = tenant.api_key_created_at
        tenant.api_key = new_api_key_hash
        tenant.api_key_created_at = datetime.now(timezone.utc)
        tenant.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(tenant)
        
        # Log API key regeneration
        self._log_tenant_activity(tenant_id, "api_key_regenerated", {
            "old_key_created": old_key_created.isoformat() if old_key_created else None,
            "new_key_created": tenant.api_key_created_at.isoformat()
        })
        
        return tenant, new_api_key
    
    # Private helper methods
    
    def _validate_tenant_creation_data(self, tenant_data: TenantCreate) -> None:
        """Validate tenant creation data with enhanced validation"""
        # Validate legal ID format
        is_valid, error_msg = validate_cedula_juridica(tenant_data.cedula_juridica)
        if not is_valid:
            raise ValueError(f"Invalid legal identification format: {error_msg}")
        
        # Check if tenant already exists
        existing_tenant = self.get_tenant_by_cedula(tenant_data.cedula_juridica)
        if existing_tenant:
            raise ValueError("A tenant with this legal ID already exists")
        
        # Validate email format
        if not validate_email_format(tenant_data.email_contacto):
            raise ValueError("Invalid email format")
        
        # Validate company name
        if len(tenant_data.nombre_empresa.strip()) < 5:
            raise ValueError("Company name must be at least 5 characters long")
    
    def _normalize_cedula_juridica(self, cedula: str) -> str:
        """Normalize legal ID format for consistent storage"""
        # Remove any formatting and store as plain digits
        normalized = re.sub(r'[^\d]', '', cedula)
        
        # Validate length
        if len(normalized) != 10:
            raise ValueError("Legal ID must be exactly 10 digits")
        
        return normalized
    
    def _get_plan_limits(self, plan: TenantPlan) -> Dict[str, Any]:
        """Get plan-specific limits and configuration"""
        plan_configs = {
            TenantPlan.BASICO: {
                'limite_mensual': 100,
                'rate_limit_hora': 50,
                'soporte': 'email',
                'features': ['facturacion_basica', 'api_access']
            },
            TenantPlan.PRO: {
                'limite_mensual': 1000,
                'rate_limit_hora': 200,
                'soporte': 'email_prioritario',
                'features': ['facturacion_basica', 'api_access', 'reportes_avanzados', 'webhooks']
            },
            TenantPlan.EMPRESA: {
                'limite_mensual': -1,  # Unlimited
                'rate_limit_hora': 1000,
                'soporte': 'telefono_email',
                'features': ['facturacion_basica', 'api_access', 'reportes_avanzados', 
                           'webhooks', 'integracion_personalizada', 'soporte_dedicado']
            }
        }
        return plan_configs.get(plan, plan_configs[TenantPlan.BASICO])
    
    def _is_plan_upgrade(self, old_plan: str, new_plan: str) -> bool:
        """Check if plan change is an upgrade"""
        plan_hierarchy = {
            TenantPlan.BASICO: 1,
            TenantPlan.PRO: 2,
            TenantPlan.EMPRESA: 3
        }
        
        old_level = plan_hierarchy.get(old_plan, 1)
        new_level = plan_hierarchy.get(new_plan, 1)
        
        return new_level > old_level
    
    def _handle_tenant_deactivation_cascade(self, tenant_id: UUID) -> None:
        """Handle cascade effects of tenant deactivation"""
        # In a full implementation, this would:
        # 1. Cancel pending document submissions
        # 2. Clear cached certificates
        # 3. Disable webhooks
        # 4. Send deactivation notifications
        
        self._log_tenant_activity(tenant_id, "tenant_deactivated_cascade", {
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def _get_documents_by_type(self, tenant_id: UUID) -> Dict[str, int]:
        """Get document count by type for tenant"""
        # Mock implementation - would query Document model in real implementation
        return {
            "01": 0,  # Factura Electrónica
            "02": 0,  # Nota Débito
            "03": 0,  # Nota Crédito
            "04": 0,  # Tiquete Electrónico
            "05": 0,  # Factura Exportación
            "06": 0,  # Factura Compra
            "07": 0   # Recibo Pago
        }
    
    def _log_tenant_activity(self, tenant_id: UUID, activity: str, details: Dict[str, Any]) -> None:
        """Log tenant activity for audit trail"""
        # In a full implementation, this would write to an audit log table
        # For now, we'll just track in application logs
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Tenant activity: {activity}", extra={
            "tenant_id": str(tenant_id),
            "activity": activity,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# Convenience functions for dependency injection

def get_tenant_service(db: Session = None) -> TenantService:
    """Get tenant service instance"""
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()
    return TenantService(db)


def create_tenant_with_validation(tenant_data: TenantCreate, db: Session) -> Tuple[TenantResponse, str]:
    """
    Create tenant and return response model with API key
    
    Args:
        tenant_data: Tenant creation data
        db: Database session
        
    Returns:
        Tuple of (tenant_response, plain_api_key)
    """
    service = TenantService(db)
    tenant, api_key = service.create_tenant(tenant_data)
    
    # Convert to response model with safer property access
    response = TenantResponse(
        id=tenant.id,
        nombre_empresa=tenant.nombre_empresa,
        cedula_juridica=tenant.cedula_juridica,
        email_contacto=tenant.email_contacto,
        plan=tenant.plan,
        activo=tenant.activo,
        limite_facturas_mes=tenant.limite_facturas_mes,
        facturas_usadas_mes=tenant.facturas_usadas_mes,
        tiene_certificado=tenant.certificado_p12 is not None,
        certificado_valido=False,  # Safe default since no certificate is uploaded during creation
        certificado_vence=tenant.certificado_expires_at,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at
    )
    
    return response, api_key