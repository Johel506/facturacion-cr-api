"""
Authentication and security API endpoints for Costa Rica invoice API.
Handles API key validation, JWT token generation, and rate limit status.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_tenant
from app.core.security import (
    create_jwt_token, verify_jwt_token, verify_tenant_api_key
)
from app.core.rate_limiting import get_rate_limit_status
from app.models.tenant import Tenant
from app.services.tenant_service import TenantService
from app.schemas.base import BaseResponse
from app.schemas.tenants import TenantResponse


router = APIRouter(tags=["Authentication"])


@router.post("/validate-key", response_model=Dict[str, Any])
async def validate_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Validate API key and return tenant information.
    
    Supports multiple authentication methods:
    - X-API-Key header (preferred)
    - Authorization: Bearer <key>
    - Authorization: ApiKey <key>
    
    Requirements: 4.1 - API key validation with proper error responses
    """
    # Extract API key from headers
    api_key = None
    
    if x_api_key:
        api_key = x_api_key.strip()
    elif authorization:
        auth_parts = authorization.split()
        if len(auth_parts) == 2 and auth_parts[0].lower() in ["bearer", "apikey"]:
            api_key = auth_parts[1].strip()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "MISSING_API_KEY",
                "message": "API key is required",
                "supported_headers": [
                    "X-API-Key: <your_api_key>",
                    "Authorization: Bearer <your_api_key>",
                    "Authorization: ApiKey <your_api_key>"
                ]
            }
        )
    
    # Validate API key format
    if len(api_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_API_KEY_FORMAT",
                "message": "API key must be at least 32 characters long",
                "provided_length": len(api_key)
            }
        )
    
    try:
        # Find tenant by API key
        service = TenantService(db)
        tenants = service.list_tenants(limit=1000)  # Get all active tenants
        
        tenant = None
        for t in tenants:
            if verify_tenant_api_key(api_key, t.api_key):
                tenant = t
                break
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_API_KEY",
                    "message": "API key is not valid or has been revoked",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Check if tenant is active
        if not tenant.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ACCOUNT_DEACTIVATED",
                    "message": "Account has been deactivated",
                    "tenant_id": str(tenant.id)
                }
            )
        
        # Get rate limit status
        rate_limit_info = await get_rate_limit_status(tenant.id)
        
        return {
            "success": True,
            "message": "API key is valid",
            "data": {
                "tenant": {
                    "id": str(tenant.id),
                    "nombre_empresa": tenant.nombre_empresa,
                    "cedula_juridica": tenant.cedula_juridica,
                    "plan": tenant.plan,
                    "activo": tenant.activo,
                    "verificado": tenant.verificado,
                    "tiene_certificado": tenant.has_certificate,
                    "certificado_valido": tenant.has_certificate and not tenant.certificate_expired
                },
                "rate_limits": rate_limit_info,
                "validated_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "VALIDATION_ERROR",
                "message": "Error validating API key",
                "details": str(e)
            }
        )


@router.post("/token", response_model=Dict[str, Any])
async def generate_jwt_token(
    expires_minutes: Optional[int] = 60,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Generate JWT token for authenticated tenant (optional feature).
    
    This provides an alternative authentication method using JWT tokens
    instead of API keys for certain use cases.
    
    Requirements: 4.2 - JWT token generation
    """
    try:
        # Validate expiration time
        if expires_minutes < 1 or expires_minutes > 1440:  # Max 24 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_EXPIRATION",
                    "message": "Token expiration must be between 1 and 1440 minutes (24 hours)",
                    "provided": expires_minutes
                }
            )
        
        # Create JWT token
        token_data = {
            "tenant_id": str(current_tenant.id),
            "tenant_name": current_tenant.nombre_empresa,
            "plan": current_tenant.plan,
            "issued_at": datetime.utcnow().isoformat()
        }
        
        token = create_jwt_token(
            data=token_data,
            expires_delta=timedelta(minutes=expires_minutes)
        )
        
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        
        return {
            "success": True,
            "message": "JWT token generated successfully",
            "data": {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": expires_minutes * 60,  # seconds
                "expires_at": expires_at.isoformat(),
                "tenant_id": str(current_tenant.id),
                "scope": "api_access"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "TOKEN_GENERATION_ERROR",
                "message": "Error generating JWT token",
                "details": str(e)
            }
        )


@router.get("/token/validate", response_model=Dict[str, Any])
async def validate_jwt_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate JWT token and return token information.
    
    Requirements: 4.2 - JWT token validation
    """
    try:
        # Verify and decode token
        payload = verify_jwt_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Token is invalid or has expired"
                }
            )
        
        # Get tenant information
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN_PAYLOAD",
                    "message": "Token does not contain valid tenant information"
                }
            )
        
        # Verify tenant still exists and is active
        service = TenantService(db)
        tenant = service.get_tenant(tenant_id)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "TENANT_NOT_FOUND",
                    "message": "Tenant associated with token no longer exists"
                }
            )
        
        if not tenant.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "TENANT_DEACTIVATED",
                    "message": "Tenant account has been deactivated"
                }
            )
        
        return {
            "success": True,
            "message": "Token is valid",
            "data": {
                "token_payload": payload,
                "tenant": {
                    "id": str(tenant.id),
                    "nombre_empresa": tenant.nombre_empresa,
                    "plan": tenant.plan,
                    "activo": tenant.activo
                },
                "validated_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "TOKEN_VALIDATION_ERROR",
                "message": "Error validating JWT token",
                "details": str(e)
            }
        )


@router.get("/limits", response_model=Dict[str, Any])
async def get_current_rate_limits(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get current rate limit status for authenticated tenant.
    
    Returns information about:
    - Current usage counts
    - Rate limit thresholds
    - Reset times
    - Remaining capacity
    
    Requirements: 4.3 - Rate limit status endpoint
    """
    try:
        # Get rate limit information
        rate_limit_info = await get_rate_limit_status(current_tenant.id)
        
        # Get tenant usage statistics
        service = TenantService(db)
        usage = service.get_tenant_usage(current_tenant.id)
        
        # Calculate additional metrics
        monthly_usage_percent = 0
        if current_tenant.limite_facturas_mes > 0:
            monthly_usage_percent = (
                current_tenant.facturas_usadas_mes / current_tenant.limite_facturas_mes
            ) * 100
        
        return {
            "success": True,
            "message": "Rate limit status retrieved successfully",
            "data": {
                "tenant_id": str(current_tenant.id),
                "plan": current_tenant.plan,
                
                # Monthly document limits
                "monthly_limits": {
                    "limit": current_tenant.limite_facturas_mes,
                    "used": current_tenant.facturas_usadas_mes,
                    "remaining": max(0, current_tenant.limite_facturas_mes - current_tenant.facturas_usadas_mes),
                    "usage_percent": round(monthly_usage_percent, 2),
                    "unlimited": current_tenant.limite_facturas_mes == -1
                },
                
                # API rate limits
                "api_rate_limits": rate_limit_info,
                
                # Usage statistics
                "usage_statistics": usage.dict() if usage else None,
                
                # Status flags
                "status": {
                    "can_create_documents": current_tenant.can_create_document(),
                    "monthly_limit_reached": current_tenant.monthly_limit_reached,
                    "certificate_valid": current_tenant.has_certificate and not current_tenant.certificate_expired,
                    "account_active": current_tenant.activo
                },
                
                "retrieved_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "RATE_LIMIT_STATUS_ERROR",
                "message": "Error retrieving rate limit status",
                "details": str(e)
            }
        )


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated tenant information.
    
    Returns comprehensive information about the authenticated tenant
    including permissions, limits, and current status.
    """
    try:
        service = TenantService(db)
        
        # Get detailed tenant information
        usage = service.get_tenant_usage(current_tenant.id)
        
        # Get certificate status
        cert_status = {
            "tiene_certificado": current_tenant.has_certificate,
            "valido": current_tenant.has_certificate and not current_tenant.certificate_expired,
            "fecha_vencimiento": current_tenant.certificado_expires_at.isoformat() if current_tenant.certificado_expires_at else None,
            "dias_para_vencer": current_tenant.days_until_certificate_expires if current_tenant.has_certificate else None
        }
        
        return {
            "success": True,
            "message": "User information retrieved successfully",
            "data": {
                "tenant": {
                    "id": str(current_tenant.id),
                    "nombre_empresa": current_tenant.nombre_empresa,
                    "cedula_juridica": current_tenant.cedula_juridica,
                    "email_contacto": current_tenant.email_contacto,
                    "plan": current_tenant.plan,
                    "activo": current_tenant.activo,
                    "verificado": current_tenant.verificado,
                    "created_at": current_tenant.created_at.isoformat(),
                    "updated_at": current_tenant.updated_at.isoformat() if current_tenant.updated_at else None
                },
                
                "certificate": cert_status,
                
                "usage": usage.dict() if usage else None,
                
                "permissions": {
                    "can_create_documents": current_tenant.can_create_document(),
                    "can_upload_certificate": True,
                    "can_view_documents": True,
                    "can_download_xml": True,
                    "can_regenerate_api_key": True
                },
                
                "plan_features": current_tenant.get_plan_features(),
                
                "retrieved_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "USER_INFO_ERROR",
                "message": "Error retrieving user information",
                "details": str(e)
            }
        )


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_tenant_data(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Refresh tenant data and clear any cached information.
    
    Useful for updating tenant information after external changes
    or clearing cached certificate data.
    """
    try:
        service = TenantService(db)
        
        # Refresh tenant from database
        refreshed_tenant = service.get_tenant(current_tenant.id)
        
        if not refreshed_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Clear any cached data (if using Redis cache)
        # This would be implemented when caching is added
        
        return {
            "success": True,
            "message": "Tenant data refreshed successfully",
            "data": {
                "tenant_id": str(refreshed_tenant.id),
                "refreshed_at": datetime.utcnow().isoformat(),
                "changes_detected": refreshed_tenant.updated_at != current_tenant.updated_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "REFRESH_ERROR",
                "message": "Error refreshing tenant data",
                "details": str(e)
            }
        )


# Health check endpoint for auth service
@router.get("/health", response_model=Dict[str, Any])
def auth_service_health():
    """
    Health check for authentication service.
    """
    return {
        "success": True,
        "message": "Authentication service is healthy",
        "data": {
            "service": "authentication",
            "status": "operational",
            "features": [
                "api_key_validation",
                "jwt_token_generation",
                "rate_limit_status",
                "tenant_information"
            ],
            "checked_at": datetime.utcnow().isoformat()
        }
    }