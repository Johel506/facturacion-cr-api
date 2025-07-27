"""
Tenant management API endpoints for Costa Rica invoice API.
Handles tenant CRUD operations, certificate management, and usage tracking.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.tenant_service import TenantService, create_tenant_with_validation
from app.services.certificate_service import (
    CertificateService, upload_tenant_certificate, get_tenant_certificate_status
)
from app.schemas.tenants import (
    TenantCreate, TenantUpdate, TenantResponse, TenantDetail,
    TenantUsage, TenantStats, ApiKeyResponse, CertificateUpload, CertificateStatus
)
from app.schemas.enums import TenantPlan
from app.schemas.base import BaseResponse, PaginationData
from app.models.tenant import Tenant


router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new tenant with enhanced validation.
    
    Returns the tenant information along with the generated API key.
    The API key is only returned once during creation.
    
    Requirements: 1.1 - tenant creation with business information
    """
    try:
        tenant_response, api_key = create_tenant_with_validation(tenant_data, db)
        
        return {
            "success": True,
            "message": "Tenant created successfully",
            "data": {
                "tenant": tenant_response.dict(),
                "api_key": api_key
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve tenant information by ID.
    
    Returns basic tenant information without sensitive data.
    """
    service = TenantService(db)
    tenant = service.get_tenant(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponse(
        id=tenant.id,
        nombre_empresa=tenant.nombre_empresa,
        cedula_juridica=tenant.cedula_juridica,
        email_contacto=tenant.email_contacto,
        plan=tenant.plan,
        activo=tenant.activo,
        limite_facturas_mes=tenant.limite_facturas_mes,
        facturas_usadas_mes=tenant.facturas_usadas_mes,
        tiene_certificado=tenant.has_certificate,
        certificado_valido=tenant.has_certificate and not tenant.certificate_expired,
        certificado_vence=tenant.certificado_expires_at,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at
    )


@router.get("/{tenant_id}/detail", response_model=TenantDetail)
def get_tenant_detail(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed tenant information including usage statistics.
    
    Requirements: 1.5 - statistics and reporting functionality
    """
    service = TenantService(db)
    tenant = service.get_tenant(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get usage statistics
    usage = service.get_tenant_usage(tenant_id)
    
    # Get certificate status
    from app.schemas.tenants import CertificateStatus
    cert_status = CertificateStatus(
        tiene_certificado=tenant.has_certificate,
        fecha_vencimiento=tenant.certificado_expires_at,
        valido=tenant.has_certificate and not tenant.certificate_expired,
        emisor=tenant.certificado_issuer,
        sujeto=tenant.certificado_subject
    )
    
    return TenantDetail(
        id=tenant.id,
        nombre_empresa=tenant.nombre_empresa,
        cedula_juridica=tenant.cedula_juridica,
        email_contacto=tenant.email_contacto,
        plan=tenant.plan,
        activo=tenant.activo,
        limite_facturas_mes=tenant.limite_facturas_mes,
        facturas_usadas_mes=tenant.facturas_usadas_mes,
        certificado_status=cert_status,
        usage=usage,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at
    )


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: UUID,
    updates: TenantUpdate,
    db: Session = Depends(get_db)
):
    """
    Update tenant information with plan management.
    
    Requirements: 1.5 - plan management and updates
    """
    try:
        service = TenantService(db)
        tenant = service.update_tenant(tenant_id, updates)
        
        return TenantResponse(
            id=tenant.id,
            nombre_empresa=tenant.nombre_empresa,
            cedula_juridica=tenant.cedula_juridica,
            email_contacto=tenant.email_contacto,
            plan=tenant.plan,
            activo=tenant.activo,
            limite_facturas_mes=tenant.limite_facturas_mes,
            facturas_usadas_mes=tenant.facturas_usadas_mes,
            tiene_certificado=tenant.has_certificate,
            certificado_valido=tenant.has_certificate and not tenant.certificate_expired,
            certificado_vence=tenant.certificado_expires_at,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
        )


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
def activate_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Activate tenant account.
    """
    try:
        service = TenantService(db)
        tenant = service.activate_tenant(tenant_id)
        
        return TenantResponse(
            id=tenant.id,
            nombre_empresa=tenant.nombre_empresa,
            cedula_juridica=tenant.cedula_juridica,
            email_contacto=tenant.email_contacto,
            plan=tenant.plan,
            activo=tenant.activo,
            limite_facturas_mes=tenant.limite_facturas_mes,
            facturas_usadas_mes=tenant.facturas_usadas_mes,
            tiene_certificado=tenant.has_certificate,
            certificado_valido=tenant.has_certificate and not tenant.certificate_expired,
            certificado_vence=tenant.certificado_expires_at,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{tenant_id}/deactivate", response_model=TenantResponse)
def deactivate_tenant(
    tenant_id: UUID,
    cascade: bool = Query(True, description="Apply cascade effects"),
    db: Session = Depends(get_db)
):
    """
    Deactivate tenant with cascade effects.
    
    Requirements: 1.5 - activation/deactivation with cascade effects
    """
    try:
        service = TenantService(db)
        tenant = service.deactivate_tenant(tenant_id, cascade=cascade)
        
        return TenantResponse(
            id=tenant.id,
            nombre_empresa=tenant.nombre_empresa,
            cedula_juridica=tenant.cedula_juridica,
            email_contacto=tenant.email_contacto,
            plan=tenant.plan,
            activo=tenant.activo,
            limite_facturas_mes=tenant.limite_facturas_mes,
            facturas_usadas_mes=tenant.facturas_usadas_mes,
            tiene_certificado=tenant.has_certificate,
            certificado_valido=tenant.has_certificate and not tenant.certificate_expired,
            certificado_vence=tenant.certificado_expires_at,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{tenant_id}/usage", response_model=TenantUsage)
def get_tenant_usage(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get tenant usage statistics and tracking.
    
    Requirements: 1.5 - usage tracking
    """
    try:
        service = TenantService(db)
        usage = service.get_tenant_usage(tenant_id)
        return usage
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{tenant_id}/usage/reset", response_model=TenantResponse)
def reset_monthly_usage(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Reset monthly usage counter.
    
    Requirements: 1.5 - monthly limits reset
    """
    try:
        service = TenantService(db)
        tenant = service.reset_monthly_usage(tenant_id)
        
        return TenantResponse(
            id=tenant.id,
            nombre_empresa=tenant.nombre_empresa,
            cedula_juridica=tenant.cedula_juridica,
            email_contacto=tenant.email_contacto,
            plan=tenant.plan,
            activo=tenant.activo,
            limite_facturas_mes=tenant.limite_facturas_mes,
            facturas_usadas_mes=tenant.facturas_usadas_mes,
            tiene_certificado=tenant.has_certificate,
            certificado_valido=tenant.has_certificate and not tenant.certificate_expired,
            certificado_vence=tenant.certificado_expires_at,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{tenant_id}/stats", response_model=TenantStats)
def get_tenant_statistics(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive tenant statistics and reporting.
    
    Requirements: 1.5 - statistics and reporting functionality
    """
    try:
        service = TenantService(db)
        stats = service.get_tenant_statistics(tenant_id)
        return stats
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{tenant_id}/api-key/regenerate", response_model=dict)
def regenerate_api_key(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Regenerate API key for tenant.
    
    Returns the new API key. This is the only time the plain API key is returned.
    """
    try:
        service = TenantService(db)
        tenant, new_api_key = service.regenerate_api_key(tenant_id)
        
        return {
            "success": True,
            "message": "API key regenerated successfully",
            "data": {
                "api_key": new_api_key,
                "created_at": tenant.api_key_created_at.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=dict)
def list_tenants(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    plan: Optional[TenantPlan] = Query(None, description="Filter by plan"),
    activo: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in company name or legal ID"),
    db: Session = Depends(get_db)
):
    """
    List tenants with filtering and pagination.
    """
    service = TenantService(db)
    
    # Get tenants
    tenants = service.list_tenants(
        skip=skip,
        limit=limit,
        plan=plan,
        activo=activo,
        search=search
    )
    
    # Get total count
    total = service.count_tenants(
        plan=plan,
        activo=activo,
        search=search
    )
    
    # Convert to response models
    tenant_responses = []
    for tenant in tenants:
        tenant_responses.append(TenantResponse(
            id=tenant.id,
            nombre_empresa=tenant.nombre_empresa,
            cedula_juridica=tenant.cedula_juridica,
            email_contacto=tenant.email_contacto,
            plan=tenant.plan,
            activo=tenant.activo,
            limite_facturas_mes=tenant.limite_facturas_mes,
            facturas_usadas_mes=tenant.facturas_usadas_mes,
            tiene_certificado=tenant.has_certificate,
            certificado_valido=tenant.has_certificate and not tenant.certificate_expired,
            certificado_vence=tenant.certificado_expires_at,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        ))
    
    # Calculate pagination
    pages = (total + limit - 1) // limit if limit > 0 else 0
    current_page = (skip // limit) + 1 if limit > 0 else 1
    
    return {
        "success": True,
        "data": {
            "items": [tenant.dict() for tenant in tenant_responses],
            "pagination": {
                "total": total,
                "page": current_page,
                "size": limit,
                "pages": pages
            }
        }
    }


@router.get("/search/by-cedula/{cedula_juridica}", response_model=TenantResponse)
def get_tenant_by_cedula(
    cedula_juridica: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve tenant by legal identification number.
    """
    service = TenantService(db)
    tenant = service.get_tenant_by_cedula(cedula_juridica)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponse(
        id=tenant.id,
        nombre_empresa=tenant.nombre_empresa,
        cedula_juridica=tenant.cedula_juridica,
        email_contacto=tenant.email_contacto,
        plan=tenant.plan,
        activo=tenant.activo,
        limite_facturas_mes=tenant.limite_facturas_mes,
        facturas_usadas_mes=tenant.facturas_usadas_mes,
        tiene_certificado=tenant.has_certificate,
        certificado_valido=tenant.has_certificate and not tenant.certificate_expired,
        certificado_vence=tenant.certificado_expires_at,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at
    )


@router.get("/plans/limits", response_model=dict)
def get_plan_limits():
    """
    Get plan limits and features configuration.
    """
    from app.schemas.tenants import TenantPlanLimits
    
    plans = [
        TenantPlanLimits(
            plan=TenantPlan.BASICO,
            limite_facturas_mes=100,
            precio_mensual=29.99,
            caracteristicas=[
                "100 documentos por mes",
                "Acceso API básico",
                "Soporte por email",
                "Facturación electrónica"
            ]
        ),
        TenantPlanLimits(
            plan=TenantPlan.PRO,
            limite_facturas_mes=1000,
            precio_mensual=99.99,
            caracteristicas=[
                "1,000 documentos por mes",
                "Acceso API completo",
                "Soporte prioritario",
                "Reportes avanzados",
                "Webhooks",
                "Facturación electrónica"
            ]
        ),
        TenantPlanLimits(
            plan=TenantPlan.EMPRESA,
            limite_facturas_mes=-1,  # Unlimited
            precio_mensual=299.99,
            caracteristicas=[
                "Documentos ilimitados",
                "Acceso API completo",
                "Soporte dedicado",
                "Reportes avanzados",
                "Webhooks",
                "Integración personalizada",
                "Facturación electrónica"
            ]
        )
    ]
    
    return {
        "success": True,
        "data": {
            "plans": [plan.dict() for plan in plans]
        }
    }


# Certificate management endpoints

@router.post("/{tenant_id}/certificate", response_model=dict)
async def upload_certificate(
    tenant_id: UUID,
    certificate_upload: CertificateUpload,
    db: Session = Depends(get_db)
):
    """
    Upload P12 certificate with validation and secure storage.
    
    Requirements: 1.2 - P12 certificate upload with validation and secure storage
    """
    try:
        success, cert_status, errors = await upload_tenant_certificate(
            tenant_id, certificate_upload, db
        )
        
        if success:
            return {
                "success": True,
                "message": "Certificate uploaded successfully",
                "data": {
                    "certificate_status": cert_status.dict() if cert_status else None,
                    "warnings": errors  # These are actually warnings when success=True
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Certificate upload failed",
                    "errors": errors
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload certificate: {str(e)}"
        )


@router.get("/{tenant_id}/certificate/status", response_model=dict)
async def get_certificate_status(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get certificate status and expiration information.
    
    Requirements: 3.6 - Certificate expiration checking
    """
    try:
        cert_status = await get_tenant_certificate_status(tenant_id, db)
        
        if cert_status:
            return {
                "success": True,
                "data": {
                    "certificate_status": cert_status.dict()
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "certificate_status": {
                        "tiene_certificado": False,
                        "valido": False,
                        "message": "No certificate found"
                    }
                }
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get certificate status: {str(e)}"
        )


@router.post("/{tenant_id}/certificate/validate", response_model=dict)
async def validate_certificate(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Validate tenant's certificate and return detailed results.
    
    Requirements: 1.2 - Certificate parsing, validation, and expiration checking
    """
    try:
        service = CertificateService(db)
        is_valid, errors, warnings = await service.validate_certificate(tenant_id)
        
        return {
            "success": True,
            "data": {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate certificate: {str(e)}"
        )


@router.get("/{tenant_id}/certificate/chain", response_model=dict)
async def get_certificate_chain_validation(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Validate certificate chain and issuer verification.
    
    Requirements: 1.2 - Certificate chain validation and issuer verification
    """
    try:
        service = CertificateService(db)
        chain_info = await service.get_certificate_chain_validation(tenant_id)
        
        return {
            "success": True,
            "data": chain_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate certificate chain: {str(e)}"
        )


@router.delete("/{tenant_id}/certificate", response_model=dict)
async def remove_certificate(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Remove certificate from tenant.
    """
    try:
        service = CertificateService(db)
        success = await service.remove_certificate(tenant_id)
        
        if success:
            return {
                "success": True,
                "message": "Certificate removed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove certificate"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove certificate: {str(e)}"
        )


@router.get("/certificates/expiration-check", response_model=dict)
async def check_certificate_expirations(db: Session = Depends(get_db)):
    """
    Check all certificates for expiration notifications.
    
    Requirements: 3.6 - Automated certificate expiration notification system (30, 15, 7 days)
    """
    try:
        service = CertificateService(db)
        notifications = await service.check_expiration_notifications()
        
        return {
            "success": True,
            "data": {
                "notifications": notifications,
                "count": len(notifications)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check certificate expirations: {str(e)}"
        )


# Health check endpoint for tenant service
@router.get("/health", response_model=dict)
def tenant_service_health(db: Session = Depends(get_db)):
    """
    Health check for tenant service.
    """
    try:
        # Test database connection
        service = TenantService(db)
        db.execute("SELECT 1")
        
        return {
            "success": True,
            "message": "Tenant service is healthy",
            "data": {
                "database": "connected",
                "service": "operational"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Tenant service health check failed: {str(e)}"
        )