"""
Authentication module for Costa Rica invoice API

This module provides API key authentication for tenants.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenant import Tenant
from app.services.tenant_service import TenantService

security = HTTPBearer()


async def get_current_tenant(request: Request) -> Tenant:
    """
    Get current authenticated tenant from request state (set by middleware)
    
    Args:
        request: FastAPI request object
        
    Returns:
        Authenticated tenant instance
        
    Raises:
        HTTPException: If no tenant found in request
    """
    # Get tenant from request state (set by auth middleware)
    tenant = getattr(request.state, 'tenant', None)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authenticated tenant found",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return tenant