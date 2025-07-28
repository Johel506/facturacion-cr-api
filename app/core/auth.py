"""
Development authentication module for testing APIs

This module provides a simple authentication system for development and testing.
In production, this would be replaced with proper JWT or API key validation.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Development tokens for testing
VALID_DEV_TOKENS = {
    "dev-token": {
        "id": "dev-tenant-001",
        "nombre_empresa": "Empresa de Desarrollo",
        "cedula_juridica": "123456789",
        "plan": "enterprise"
    },
    "test-token": {
        "id": "test-tenant-002", 
        "nombre_empresa": "Empresa de Pruebas",
        "cedula_juridica": "987654321",
        "plan": "pro"
    },
    "demo-token": {
        "id": "demo-tenant-003",
        "nombre_empresa": "Empresa Demo",
        "cedula_juridica": "456789123",
        "plan": "basic"
    }
}


class MockTenant:
    """Mock tenant for testing"""
    def __init__(self, tenant_data: dict):
        self.id = tenant_data["id"]
        self.nombre_empresa = tenant_data["nombre_empresa"]
        self.cedula_juridica = tenant_data["cedula_juridica"]
        self.plan = tenant_data["plan"]


async def get_current_tenant(credentials: HTTPAuthorizationCredentials = Depends(security)) -> MockTenant:
    """
    Development authentication for testing APIs
    
    Valid tokens for testing:
    - dev-token: Enterprise plan tenant
    - test-token: Pro plan tenant  
    - demo-token: Basic plan tenant
    
    In production, this would validate actual API keys or JWT tokens.
    """
    token = credentials.credentials
    
    # Check if it's a valid development token
    if token in VALID_DEV_TOKENS:
        return MockTenant(VALID_DEV_TOKENS[token])
    
    # For development, also accept any token that starts with "dev-", "test-", or "demo-"
    if token.startswith(("dev-", "test-", "demo-")):
        return MockTenant({
            "id": f"tenant-{token}",
            "nombre_empresa": f"Empresa {token.title()}",
            "cedula_juridica": "123456789",
            "plan": "pro"
        })
    
    # Reject invalid tokens
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token. Use one of: dev-token, test-token, demo-token",
        headers={"WWW-Authenticate": "Bearer"},
    )