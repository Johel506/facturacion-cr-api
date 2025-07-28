"""
Reference Data API Endpoints

This module provides REST API endpoints for Costa Rican reference data including
geographic locations, units of measure, and currency information for electronic
invoicing system.

Requirements: 12.1, 12.2, 12.3, 13.1, 17.1
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, Path
from pydantic import BaseModel, Field, validator
from decimal import Decimal

from app.core.auth import get_current_tenant
from app.core.database import get_db
from app.models.geographic_location import GeographicLocation
from app.models.units_of_measure import UnitsOfMeasure

router = APIRouter(prefix="/reference", tags=["Reference Data"])


# Response Models
class GeographicLocationResponse(BaseModel):
    """Geographic location response model"""
    id: int = Field(..., description="Location ID")
    provincia: int = Field(..., description="Province code (1-7)")
    canton: int = Field(..., description="Canton code (1-99)")
    distrito: int = Field(..., description="District code (1-99)")
    nombre_provincia: str = Field(..., description="Province name")
    nombre_canton: str = Field(..., description="Canton name")
    nombre_distrito: str = Field(..., description="District name")
    codigo_completo: str = Field(..., description="Complete location code (P-CC-DD)")
    codigo_numerico: str = Field(..., description="Numeric code (PCCDD)")
    nombre_completo: str = Field(..., description="Complete location name")
    codigo_postal: Optional[str] = Field(None, description="Postal code")
    cabecera_canton: bool = Field(..., description="Whether this is canton's administrative center")
    cabecera_provincia: bool = Field(..., description="Whether this is province's administrative center")
    activo: bool = Field(..., description="Whether location is active")


class ProvinceResponse(BaseModel):
    """Province response model"""
    codigo: int = Field(..., description="Province code (1-7)")
    nombre: str = Field(..., description="Province name")
    cantons: Optional[List[Dict[str, Any]]] = Field(None, description="Cantons in province")


class CantonResponse(BaseModel):
    """Canton response model"""
    codigo: int = Field(..., description="Canton code")
    nombre: str = Field(..., description="Canton name")
    provincia_codigo: int = Field(..., description="Province code")
    provincia_nombre: str = Field(..., description="Province name")
    distritos: Optional[List[Dict[str, Any]]] = Field(None, description="Districts in canton")


class DistrictResponse(BaseModel):
    """District response model"""
    codigo: int = Field(..., description="District code")
    nombre: str = Field(..., description="District name")
    canton_codigo: int = Field(..., description="Canton code")
    canton_nombre: str = Field(..., description="Canton name")
    provincia_codigo: int = Field(..., description="Province code")
    provincia_nombre: str = Field(..., description="Province name")
    codigo_completo: str = Field(..., description="Complete location code")
    nombre_completo: str = Field(..., description="Complete location name")


class UnitsOfMeasureResponse(BaseModel):
    """Units of measure response model"""
    codigo: str = Field(..., description="Unit code")
    descripcion: str = Field(..., description="Unit description")
    descripcion_ingles: Optional[str] = Field(None, description="English description")
    simbolo: Optional[str] = Field(None, description="Unit symbol")
    categoria: str = Field(..., description="Unit category")
    tipo_medida: Optional[str] = Field(None, description="Type of measurement")
    uso_comun: bool = Field(..., description="Whether commonly used")
    uso_productos: bool = Field(..., description="Can be used for products")
    uso_servicios: bool = Field(..., description="Can be used for services")
    permite_decimales: bool = Field(..., description="Allows decimal quantities")
    cantidad_minima: Optional[float] = Field(None, description="Minimum allowed quantity")
    cantidad_maxima: Optional[float] = Field(None, description="Maximum allowed quantity")
    unidad_base: Optional[str] = Field(None, description="Base unit for conversion")
    factor_conversion: Optional[float] = Field(None, description="Conversion factor to base unit")
    display_name: str = Field(..., description="Display name with symbol")
    activo: bool = Field(..., description="Whether unit is active")
    veces_usado: int = Field(..., description="Usage count")


class CurrencyResponse(BaseModel):
    """Currency response model"""
    codigo: str = Field(..., description="ISO 4217 currency code")
    nombre: str = Field(..., description="Currency name")
    simbolo: str = Field(..., description="Currency symbol")
    pais: str = Field(..., description="Country")
    activo: bool = Field(..., description="Whether currency is supported")


class LocationValidationResponse(BaseModel):
    """Location validation response model"""
    provincia: int = Field(..., description="Province code")
    canton: int = Field(..., description="Canton code")
    distrito: int = Field(..., description="District code")
    is_valid: bool = Field(..., description="Whether location is valid")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    location_data: Optional[GeographicLocationResponse] = Field(None, description="Location data if valid")


# Geographic Location Endpoints
@router.get("/ubicaciones/provincias", response_model=List[ProvinceResponse])
async def get_provinces(
    include_cantons: bool = Query(False, description="Include cantons in response"),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Get all Costa Rican provinces
    
    Returns list of all 7 provinces with optional canton information.
    """
    try:
        provinces_data = []
        
        for provincia_code in range(1, 8):
            provincia_name = GeographicLocation.get_province_name(provincia_code)
            if not provincia_name:
                continue
            
            province_data = {
                "codigo": provincia_code,
                "nombre": provincia_name,
                "cantons": None
            }
            
            if include_cantons:
                cantons = GeographicLocation.get_cantons_by_province(db, provincia_code)
                province_data["cantons"] = [
                    {
                        "codigo": canton.canton,
                        "nombre": canton.nombre_canton
                    }
                    for canton in cantons
                ]
            
            provinces_data.append(province_data)
        
        return [ProvinceResponse(**province) for province in provinces_data]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving provinces: {str(e)}"
        )


@router.get("/ubicaciones/provincias/{provincia_id}/cantones", response_model=List[CantonResponse])
async def get_cantons_by_province(
    provincia_id: int = Path(..., description="Province code (1-7)", ge=1, le=7),
    include_districts: bool = Query(False, description="Include districts in response"),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Get all cantons in a province
    
    Returns list of cantons for the specified province with optional district information.
    """
    try:
        cantons = GeographicLocation.get_cantons_by_province(db, provincia_id)
        
        if not cantons:
            raise HTTPException(
                status_code=404,
                detail=f"No cantons found for province {provincia_id}"
            )
        
        cantons_data = []
        seen_cantons = set()
        
        for canton in cantons:
            if canton.canton in seen_cantons:
                continue
            seen_cantons.add(canton.canton)
            
            canton_data = {
                "codigo": canton.canton,
                "nombre": canton.nombre_canton,
                "provincia_codigo": canton.provincia,
                "provincia_nombre": canton.nombre_provincia,
                "distritos": None
            }
            
            if include_districts:
                districts = GeographicLocation.get_districts_by_canton(db, provincia_id, canton.canton)
                canton_data["distritos"] = [
                    {
                        "codigo": district.distrito,
                        "nombre": district.nombre_distrito
                    }
                    for district in districts
                ]
            
            cantons_data.append(canton_data)
        
        return [CantonResponse(**canton) for canton in cantons_data]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cantons: {str(e)}"
        )


@router.get("/ubicaciones/provincias/{provincia_id}/cantones/{canton_id}/distritos", response_model=List[DistrictResponse])
async def get_districts_by_canton(
    provincia_id: int = Path(..., description="Province code (1-7)", ge=1, le=7),
    canton_id: int = Path(..., description="Canton code (1-99)", ge=1, le=99),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Get all districts in a canton
    
    Returns list of districts for the specified canton.
    """
    try:
        districts = GeographicLocation.get_districts_by_canton(db, provincia_id, canton_id)
        
        if not districts:
            raise HTTPException(
                status_code=404,
                detail=f"No districts found for canton {canton_id} in province {provincia_id}"
            )
        
        districts_data = []
        for district in districts:
            district_data = {
                "codigo": district.distrito,
                "nombre": district.nombre_distrito,
                "canton_codigo": district.canton,
                "canton_nombre": district.nombre_canton,
                "provincia_codigo": district.provincia,
                "provincia_nombre": district.nombre_provincia,
                "codigo_completo": district.codigo_completo,
                "nombre_completo": district.nombre_completo
            }
            districts_data.append(district_data)
        
        return [DistrictResponse(**district) for district in districts_data]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving districts: {str(e)}"
        )


@router.get("/ubicaciones/search", response_model=List[GeographicLocationResponse])
async def search_locations(
    q: str = Query(..., description="Search query", min_length=2),
    limit: int = Query(20, description="Maximum results", ge=1, le=100),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Search geographic locations by name
    
    Performs full-text search across province, canton, and district names.
    """
    try:
        locations = GeographicLocation.search_by_name(db, q, limit)
        
        locations_data = []
        for location in locations:
            location_data = {
                "id": location.id,
                "provincia": location.provincia,
                "canton": location.canton,
                "distrito": location.distrito,
                "nombre_provincia": location.nombre_provincia,
                "nombre_canton": location.nombre_canton,
                "nombre_distrito": location.nombre_distrito,
                "codigo_completo": location.codigo_completo,
                "codigo_numerico": location.codigo_numerico,
                "nombre_completo": location.nombre_completo,
                "codigo_postal": location.codigo_postal,
                "cabecera_canton": location.cabecera_canton,
                "cabecera_provincia": location.cabecera_provincia,
                "activo": location.activo
            }
            locations_data.append(location_data)
        
        return [GeographicLocationResponse(**location) for location in locations_data]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching locations: {str(e)}"
        )


@router.get("/ubicaciones/validate/{provincia_id}/{canton_id}/{distrito_id}", response_model=LocationValidationResponse)
async def validate_location(
    provincia_id: int = Path(..., description="Province code (1-7)", ge=1, le=7),
    canton_id: int = Path(..., description="Canton code (1-99)", ge=1, le=99),
    distrito_id: int = Path(..., description="District code (1-99)", ge=1, le=99),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Validate geographic location codes
    
    Validates that the specified province, canton, and district combination exists
    and is active in the database.
    """
    try:
        is_valid, error_message = GeographicLocation.validate_address_data(
            db, provincia_id, canton_id, distrito_id
        )
        
        location_data = None
        if is_valid:
            location = GeographicLocation.get_by_codes(db, provincia_id, canton_id, distrito_id)
            if location:
                location_data = GeographicLocationResponse(
                    id=location.id,
                    provincia=location.provincia,
                    canton=location.canton,
                    distrito=location.distrito,
                    nombre_provincia=location.nombre_provincia,
                    nombre_canton=location.nombre_canton,
                    nombre_distrito=location.nombre_distrito,
                    codigo_completo=location.codigo_completo,
                    codigo_numerico=location.codigo_numerico,
                    nombre_completo=location.nombre_completo,
                    codigo_postal=location.codigo_postal,
                    cabecera_canton=location.cabecera_canton,
                    cabecera_provincia=location.cabecera_provincia,
                    activo=location.activo
                )
        
        return LocationValidationResponse(
            provincia=provincia_id,
            canton=canton_id,
            distrito=distrito_id,
            is_valid=is_valid,
            error_message=error_message,
            location_data=location_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating location: {str(e)}"
        )


# Units of Measure Endpoints
@router.get("/unidades-medida", response_model=List[UnitsOfMeasureResponse])
async def get_units_of_measure(
    category: Optional[str] = Query(None, description="Filter by category"),
    only_common: bool = Query(False, description="Include only commonly used units"),
    for_products: bool = Query(True, description="Include units suitable for products"),
    for_services: bool = Query(True, description="Include units suitable for services"),
    limit: int = Query(100, description="Maximum results", ge=1, le=500),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Get units of measure
    
    Returns list of official units of measure from RTC 443:2010 standard
    with optional filtering by category and usage type.
    """
    try:
        if category:
            units = UnitsOfMeasure.get_by_category(
                db, category, only_active=True, only_common=only_common
            )
        elif only_common:
            units = UnitsOfMeasure.get_common_units(
                db, for_products=for_products, for_services=for_services
            )
        else:
            # Get all units with filtering
            query = db.query(UnitsOfMeasure).filter(UnitsOfMeasure.activo == True)
            
            if for_products and not for_services:
                query = query.filter(UnitsOfMeasure.uso_productos == True)
            elif for_services and not for_products:
                query = query.filter(UnitsOfMeasure.uso_servicios == True)
            elif for_products and for_services:
                query = query.filter(
                    (UnitsOfMeasure.uso_productos == True) | 
                    (UnitsOfMeasure.uso_servicios == True)
                )
            
            units = query.order_by(
                UnitsOfMeasure.uso_comun.desc(),
                UnitsOfMeasure.veces_usado.desc(),
                UnitsOfMeasure.codigo
            ).limit(limit).all()
        
        units_data = []
        for unit in units:
            unit_info = unit.get_unit_info()
            units_data.append(unit_info)
        
        return [UnitsOfMeasureResponse(**unit) for unit in units_data]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving units of measure: {str(e)}"
        )


@router.get("/unidades-medida/search", response_model=List[UnitsOfMeasureResponse])
async def search_units_of_measure(
    q: str = Query(..., description="Search query", min_length=1),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, description="Maximum results", ge=1, le=100),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Search units of measure
    
    Performs full-text search across unit codes, descriptions, and symbols.
    """
    try:
        units = UnitsOfMeasure.search_by_text(
            db, q, limit=limit, only_active=True, category=category
        )
        
        units_data = []
        for unit in units:
            unit_info = unit.get_unit_info()
            units_data.append(unit_info)
        
        return [UnitsOfMeasureResponse(**unit) for unit in units_data]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching units of measure: {str(e)}"
        )


@router.get("/unidades-medida/{codigo}", response_model=UnitsOfMeasureResponse)
async def get_unit_of_measure(
    codigo: str = Path(..., description="Unit code"),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Get unit of measure by code
    
    Returns detailed information for a specific unit of measure.
    """
    try:
        unit = UnitsOfMeasure.get_by_code(db, codigo)
        
        if not unit:
            raise HTTPException(
                status_code=404,
                detail=f"Unit of measure not found: {codigo}"
            )
        
        unit_info = unit.get_unit_info()
        return UnitsOfMeasureResponse(**unit_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving unit of measure: {str(e)}"
        )


@router.get("/unidades-medida/categories", response_model=List[str])
async def get_unit_categories(
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Get all unit categories
    
    Returns list of all available unit categories.
    """
    try:
        categories = UnitsOfMeasure.get_categories(db)
        return categories
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving unit categories: {str(e)}"
        )


@router.get("/unidades-medida/most-used", response_model=List[UnitsOfMeasureResponse])
async def get_most_used_units(
    limit: int = Query(50, description="Maximum results", ge=1, le=200),
    tenant = Depends(get_current_tenant),
    db = Depends(get_db)
):
    """
    Get most frequently used units of measure
    
    Returns units ordered by usage frequency.
    """
    try:
        units = UnitsOfMeasure.get_most_used(db, limit=limit, only_active=True)
        
        units_data = []
        for unit in units:
            unit_info = unit.get_unit_info()
            units_data.append(unit_info)
        
        return [UnitsOfMeasureResponse(**unit) for unit in units_data]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving most used units: {str(e)}"
        )


# Currency Endpoints
@router.get("/monedas", response_model=List[CurrencyResponse])
async def get_supported_currencies(
    tenant = Depends(get_current_tenant)
):
    """
    Get supported currencies
    
    Returns list of currencies supported by the electronic invoicing system
    based on ISO 4217 standard and Costa Rican regulations.
    """
    try:
        # Static list of supported currencies based on Costa Rican regulations
        # This would typically come from a database table, but for now we'll use static data
        supported_currencies = [
            {
                "codigo": "CRC",
                "nombre": "Colón Costarricense",
                "simbolo": "₡",
                "pais": "Costa Rica",
                "activo": True
            },
            {
                "codigo": "USD",
                "nombre": "Dólar Estadounidense",
                "simbolo": "$",
                "pais": "Estados Unidos",
                "activo": True
            },
            {
                "codigo": "EUR",
                "nombre": "Euro",
                "simbolo": "€",
                "pais": "Unión Europea",
                "activo": True
            },
            {
                "codigo": "CAD",
                "nombre": "Dólar Canadiense",
                "simbolo": "C$",
                "pais": "Canadá",
                "activo": True
            },
            {
                "codigo": "GBP",
                "nombre": "Libra Esterlina",
                "simbolo": "£",
                "pais": "Reino Unido",
                "activo": True
            },
            {
                "codigo": "JPY",
                "nombre": "Yen Japonés",
                "simbolo": "¥",
                "pais": "Japón",
                "activo": True
            },
            {
                "codigo": "CHF",
                "nombre": "Franco Suizo",
                "simbolo": "CHF",
                "pais": "Suiza",
                "activo": True
            },
            {
                "codigo": "AUD",
                "nombre": "Dólar Australiano",
                "simbolo": "A$",
                "pais": "Australia",
                "activo": True
            },
            {
                "codigo": "NZD",
                "nombre": "Dólar Neozelandés",
                "simbolo": "NZ$",
                "pais": "Nueva Zelanda",
                "activo": True
            },
            {
                "codigo": "MXN",
                "nombre": "Peso Mexicano",
                "simbolo": "MX$",
                "pais": "México",
                "activo": True
            },
            {
                "codigo": "BRL",
                "nombre": "Real Brasileño",
                "simbolo": "R$",
                "pais": "Brasil",
                "activo": True
            },
            {
                "codigo": "ARS",
                "nombre": "Peso Argentino",
                "simbolo": "AR$",
                "pais": "Argentina",
                "activo": True
            },
            {
                "codigo": "CLP",
                "nombre": "Peso Chileno",
                "simbolo": "CL$",
                "pais": "Chile",
                "activo": True
            },
            {
                "codigo": "COP",
                "nombre": "Peso Colombiano",
                "simbolo": "CO$",
                "pais": "Colombia",
                "activo": True
            },
            {
                "codigo": "PEN",
                "nombre": "Sol Peruano",
                "simbolo": "S/",
                "pais": "Perú",
                "activo": True
            },
            {
                "codigo": "GTQ",
                "nombre": "Quetzal Guatemalteco",
                "simbolo": "Q",
                "pais": "Guatemala",
                "activo": True
            },
            {
                "codigo": "HNL",
                "nombre": "Lempira Hondureño",
                "simbolo": "L",
                "pais": "Honduras",
                "activo": True
            },
            {
                "codigo": "NIO",
                "nombre": "Córdoba Nicaragüense",
                "simbolo": "C$",
                "pais": "Nicaragua",
                "activo": True
            },
            {
                "codigo": "PAB",
                "nombre": "Balboa Panameño",
                "simbolo": "B/.",
                "pais": "Panamá",
                "activo": True
            },
            {
                "codigo": "SVC",
                "nombre": "Colón Salvadoreño",
                "simbolo": "₡",
                "pais": "El Salvador",
                "activo": False  # El Salvador uses USD now
            }
        ]
        
        return [CurrencyResponse(**currency) for currency in supported_currencies if currency["activo"]]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving supported currencies: {str(e)}"
        )


@router.get("/monedas/{codigo}", response_model=CurrencyResponse)
async def get_currency(
    codigo: str = Path(..., description="ISO 4217 currency code", min_length=3, max_length=3),
    tenant = Depends(get_current_tenant)
):
    """
    Get currency information by code
    
    Returns detailed information for a specific currency.
    """
    try:
        # Get all supported currencies and find the requested one
        currencies_response = await get_supported_currencies(tenant)
        
        for currency in currencies_response:
            if currency.codigo.upper() == codigo.upper():
                return currency
        
        raise HTTPException(
            status_code=404,
            detail=f"Currency not supported: {codigo}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving currency: {str(e)}"
        )


# Utility Endpoints
@router.get("/validate-identification/{tipo}/{numero}")
async def validate_identification(
    tipo: str = Path(..., description="Identification type (01-06)"),
    numero: str = Path(..., description="Identification number"),
    tenant = Depends(get_current_tenant)
):
    """
    Validate Costa Rican identification numbers
    
    Validates format for all supported identification types:
    - 01: Cédula Física (physical ID)
    - 02: Cédula Jurídica (legal entity ID)
    - 03: DIMEX (foreign resident ID)
    - 04: NITE (tax ID for non-residents)
    - 05: Extranjero No Domiciliado (non-resident foreigner)
    - 06: No Contribuyente (non-taxpayer)
    """
    try:
        from app.utils.validators import validate_identification_number
        
        is_valid, error_message = validate_identification_number(tipo, numero)
        
        return {
            "tipo": tipo,
            "numero": numero,
            "is_valid": is_valid,
            "error_message": error_message,
            "tipo_descripcion": {
                "01": "Cédula Física",
                "02": "Cédula Jurídica", 
                "03": "DIMEX",
                "04": "NITE",
                "05": "Extranjero No Domiciliado",
                "06": "No Contribuyente"
            }.get(tipo, "Tipo desconocido")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating identification: {str(e)}"
        )