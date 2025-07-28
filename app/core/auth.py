"""
Authentication module for Costa Rica invoice API

This module provides API key authentication for tenants.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenant import Tenant
from app.services.tenant_service import TenantService

security = HTTPBearer()


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Authenticate tenant using API key
    
    Args:
        credentials: Bearer token credentials
        db: Database session
        
    Returns:
        Authenticated tenant instance
        
    Raises:
        HTTPException: If authentication fails
    """
    api_key = credentials.credentials
    
    try:
        # Get tenant service
        tenant_service = TenantService(db)
        
        # Authenticate using API key
        tenant = tenant_service.get_tenant_by_api_key(api_key)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not tenant.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return tenant
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error",
            headers={"WWW-Authenticate": "Bearer"},
        )