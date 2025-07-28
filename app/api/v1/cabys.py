"""
CABYS Code API Endpoints

This module provides REST API endpoints for CABYS code management including
search, validation, and retrieval functionality for Costa Rica's electronic
invoicing system.

Requirements: 11.2, 11.3, 17.1
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field, validator

from app.services.cabys_service import cabys_service
from app.core.auth import get_current_tenant

router = APIRouter(prefix="/cabys", tags=["CABYS Codes"])


class CabysCodeResponse(BaseModel):
    """CABYS code response model"""
    codigo: str = Field(..., description="13-digit CABYS code")
    descripcion: str = Field(..., description="Product/service description")
    categoria_nivel_1: Optional[str] = Field(None, description="Level 1 category")
    categoria_nivel_2: Optional[str] = Field(None, description="Level 2 category")
    categoria_nivel_3: Optional[str] = Field(None, description="Level 3 category")
    categoria_nivel_4: Optional[str] = Field(None, description="Level 4 category")
    categoria_completa: str = Field(..., description="Complete category hierarchy")
    impuesto_iva: float = Field(..., description="IVA tax rate percentage")
    impuesto_iva_decimal: float = Field(..., description="IVA tax rate as decimal")
    exento_iva: bool = Field(..., description="Whether IVA exempt")
    activo: bool = Field(..., description="Whether code is active")
    version_cabys: Optional[str] = Field(None, description="CABYS version")
    fecha_vigencia_desde: Optional[str] = Field(None, description="Validity start date")
    fecha_vigencia_hasta: Optional[str] = Field(None, description="Validity end date")
    veces_usado: int = Field(..., description="Usage count")
    ultimo_uso: Optional[str] = Field(None, description="Last usage timestamp")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    tax_info: Dict[str, Any] = Field(..., description="Tax information")


class CabysSearchResponse(BaseModel):
    """CABYS search response model"""
    results: List[CabysCodeResponse] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")
    query: str = Field(..., description="Search query")


class CabysValidationResponse(BaseModel):
    """CABYS validation response model"""
    codigo: str = Field(..., description="CABYS code being validated")
    is_valid: bool = Field(..., description="Whether code is valid")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    code_data: Optional[CabysCodeResponse] = Field(None, description="Code data if valid")


class CabysStatisticsResponse(BaseModel):
    """CABYS statistics response model"""
    total_codes: int = Field(..., description="Total number of codes")
    active_codes: int = Field(..., description="Number of active codes")
    inactive_codes: int = Field(..., description="Number of inactive codes")
    used_codes: int = Field(..., description="Number of codes that have been used")
    unused_codes: int = Field(..., description="Number of codes never used")
    most_used_code: Dict[str, Any] = Field(..., description="Most frequently used code")
    category_counts: Dict[str, int] = Field(..., description="Category counts by level")
    last_updated: str = Field(..., description="Statistics last update timestamp")


@router.get("/search", response_model=CabysSearchResponse)
async def search_cabys_codes(
    q: str = Query(..., description="Search query", min_length=2),
    limit: int = Query(20, description="Maximum results per page", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    category_filter: Optional[str] = Query(None, description="Category filter"),
    category_level: int = Query(1, description="Category level for filtering", ge=1, le=4),
    only_active: bool = Query(True, description="Include only active codes"),
    tenant = Depends(get_current_tenant)
):
    """
    Search CABYS codes with full-text search and filtering
    
    Performs comprehensive search across CABYS codes using PostgreSQL full-text
    search with Spanish language support. Supports category filtering and pagination.
    """
    try:
        results = await cabys_service.search_codes(
            query=q,
            limit=limit,
            offset=offset,
            category_filter=category_filter,
            category_level=category_level,
            only_active=only_active,
            use_cache=True
        )
        
        return CabysSearchResponse(**results)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching CABYS codes: {str(e)}"
        )


@router.get("/code/{codigo}", response_model=CabysCodeResponse)
async def get_cabys_code(
    codigo: str = Field(..., description="13-digit CABYS code"),
    tenant = Depends(get_current_tenant)
):
    """
    Get CABYS code by exact code match
    
    Retrieves detailed information for a specific CABYS code including
    tax information, category hierarchy, and usage statistics.
    """
    try:
        code_data = await cabys_service.get_code(codigo, use_cache=True)
        
        if not code_data:
            raise HTTPException(
                status_code=404,
                detail=f"CABYS code not found: {codigo}"
            )
        
        return CabysCodeResponse(**code_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving CABYS code: {str(e)}"
        )


@router.get("/validate/{codigo}", response_model=CabysValidationResponse)
async def validate_cabys_code(
    codigo: str = Field(..., description="13-digit CABYS code to validate"),
    tenant = Depends(get_current_tenant)
):
    """
    Validate CABYS code format and existence
    
    Validates that a CABYS code has the correct format (13 digits) and
    exists in the database as an active code.
    """
    try:
        is_valid, error_message = await cabys_service.validate_code(codigo)
        
        code_data = None
        if is_valid:
            code_data = await cabys_service.get_code(codigo, use_cache=True)
        
        return CabysValidationResponse(
            codigo=codigo,
            is_valid=is_valid,
            error_message=error_message,
            code_data=CabysCodeResponse(**code_data) if code_data else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating CABYS code: {str(e)}"
        )


@router.get("/prefix/{prefix}", response_model=List[CabysCodeResponse])
async def search_by_prefix(
    prefix: str = Field(..., description="Code prefix to search for"),
    limit: int = Query(20, description="Maximum number of results", ge=1, le=100),
    only_active: bool = Query(True, description="Include only active codes"),
    tenant = Depends(get_current_tenant)
):
    """
    Search CABYS codes by code prefix
    
    Finds CABYS codes that start with the specified prefix. Useful for
    hierarchical browsing of codes by category structure.
    """
    try:
        results = await cabys_service.search_by_code_prefix(
            prefix=prefix,
            limit=limit,
            only_active=only_active
        )
        
        return [CabysCodeResponse(**code) for code in results]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching CABYS codes by prefix: {str(e)}"
        )


@router.get("/category/{categoria}", response_model=List[CabysCodeResponse])
async def search_by_category(
    categoria: str = Field(..., description="Category name to search for"),
    nivel: int = Query(1, description="Category level", ge=1, le=4),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    only_active: bool = Query(True, description="Include only active codes"),
    tenant = Depends(get_current_tenant)
):
    """
    Search CABYS codes by category
    
    Finds CABYS codes that belong to a specific category at the specified level.
    Useful for browsing codes by product/service categories.
    """
    try:
        results = await cabys_service.search_by_category(
            categoria=categoria,
            nivel=nivel,
            limit=limit,
            only_active=only_active
        )
        
        return [CabysCodeResponse(**code) for code in results]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching CABYS codes by category: {str(e)}"
        )


@router.get("/most-used", response_model=List[CabysCodeResponse])
async def get_most_used_codes(
    limit: int = Query(100, description="Maximum number of results", ge=1, le=500),
    only_active: bool = Query(True, description="Include only active codes"),
    tenant = Depends(get_current_tenant)
):
    """
    Get most frequently used CABYS codes
    
    Returns CABYS codes ordered by usage frequency. Useful for showing
    popular codes to users for quick selection.
    """
    try:
        results = await cabys_service.get_most_used(
            limit=limit,
            only_active=only_active
        )
        
        return [CabysCodeResponse(**code) for code in results]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving most used CABYS codes: {str(e)}"
        )


@router.get("/categories", response_model=List[str])
async def get_categories(
    nivel: int = Query(1, description="Category level", ge=1, le=4),
    tenant = Depends(get_current_tenant)
):
    """
    Get all unique categories at specified level
    
    Returns a list of all unique category names at the specified level.
    Useful for building category filters and navigation.
    """
    try:
        categories = await cabys_service.get_categories(nivel=nivel)
        return categories
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving categories: {str(e)}"
        )


@router.get("/statistics", response_model=CabysStatisticsResponse)
async def get_statistics(
    tenant = Depends(get_current_tenant)
):
    """
    Get CABYS database statistics
    
    Returns comprehensive statistics about the CABYS database including
    counts, usage information, and category breakdowns.
    """
    try:
        stats = await cabys_service.get_statistics()
        return CabysStatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving CABYS statistics: {str(e)}"
        )


@router.post("/clear-cache")
async def clear_cache(
    codigo: Optional[str] = Query(None, description="Specific code to clear, or all if not provided"),
    tenant = Depends(get_current_tenant)
):
    """
    Clear CABYS cache entries
    
    Clears cached CABYS data. Can clear cache for a specific code or all CABYS cache.
    Useful for cache management and testing.
    """
    try:
        await cabys_service.clear_cache(codigo=codigo)
        
        return {
            "message": f"Cache cleared for {'code ' + codigo if codigo else 'all CABYS entries'}",
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing cache: {str(e)}"
        )