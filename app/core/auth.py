"""
Simple authentication module for testing CABYS API
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


class MockTenant:
    """Mock tenant for testing"""
    def __init__(self):
        self.id = "test-tenant-id"
        self.nombre_empresa = "Test Company"
        self.cedula_juridica = "123456789"
        self.plan = "pro"


async def get_current_tenant(credentials: HTTPAuthorizationCredentials = Depends(security)) -> MockTenant:
    """
    Simple mock authentication for testing CABYS API
    
    In production, this would validate the API key and return the actual tenant
    """
    # For testing, just return a mock tenant
    return MockTenant()