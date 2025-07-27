"""
Document line item and tax models for Costa Rica electronic documents.
Supports all product fields, commercial codes, taxes, and exemptions.
"""
import re
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from .enums import (
    TaxCode, IVATariffCode, ExemptionType, DiscountType, 
    CommercialCodeType, TransactionType, InstitutionType
)
from .base import CABYSCodeData


class CommercialCode(BaseModel):
    """Commercial code for product identification."""
    tipo: CommercialCodeType
    codigo: str = Field(..., max_length=20, description="Commercial code value")

    class Config:
        use_enum_values = True


class PackageComponent(BaseModel):
    """Component of a package/combo product (DetalleSurtido)."""
    codigo_cabys: str = Field(..., regex=r'^\d{13}$', description="13-digit CABYS code")
    cantidad: Decimal = Field(..., gt=0, max_digits=16, decimal_places=3, description="Quantity")
    unidad_medida: str = Field(..., max_length=10, description="Unit of measure")
    descripcion: str = Field(..., min_length=3, max_length=200, description="Product description")

    @validator('codigo_cabys')
    def validate_cabys_format(cls, v):
        """Validate CABYS code format."""
        if not v.isdigit() or len(v) != 13:
            raise ValueError('CABYS code must be exactly 13 digits')
        return v


class ExemptionData(BaseModel):
    """Tax exemption data with document reference."""
    tipo_documento: ExemptionType
    tipo_documento_otro: Optional[str] = Field(None, min_length=5, max_length=100)
    numero_documento: str = Field(..., min_length=3, max_length=40, description="Exemption document number")
    articulo: Optional[int] = Field(None, le=999999, description="Article number")
    inciso: Optional[int] = Field(None, le=999999, description="Subsection number")
    nombre_institucion: InstitutionType
    nombre_institucion_otros: Optional[str] = Field(None, min_length=5, max_length=160)
    fecha_emision: datetime = Field(..., description="Exemption document emission date")
    tarifa_exonerada: Decimal = Field(..., max_digits=4, decimal_places=2, description="Exempted rate")
    monto_exoneracion: Decimal = Field(..., max_digits=18, decimal_places=5, description="Exemption amount")

    @validator('tipo_documento_otro')
    def validate_other_document_type(cls, v, values):
        """Validate other document type when tipo_documento is OTHERS."""
        tipo = values.get('tipo_documento')
        if tipo == ExemptionType.OTHERS and not v:
            raise ValueError('tipo_documento_otro is required when tipo_documento is OTHERS')
        return v

    @validator('nombre_institucion_otros')
    def validate_other_institution(cls, v, values):
        """Validate other institution when nombre_institucion is OTHERS."""
        institucion = values.get('nombre_institucion')
        if institucion == InstitutionType.OTHERS and not v:
            raise ValueError('nombre_institucion_otros is required when nombre_institucion is OTHERS')
        return v

    @validator('tarifa_exonerada')
    def validate_exempted_rate(cls, v):
        """Validate exempted rate is between 0 and 100."""
        if v < 0 or v > 100:
            raise ValueError('Exempted rate must be between 0 and 100')
        return v

    @validator('monto_exoneracion')
    def validate_exemption_amount(cls, v):
        """Validate exemption amount is positive."""
        if v < 0:
            raise ValueError('Exemption amount cannot be negative')
        return v

    class Config:
        use_enum_values = True


class TaxData(BaseModel):
    """Tax information for line items supporting all Costa Rican tax types."""
    codigo: TaxCode
    codigo_impuesto_otro: Optional[str] = Field(None, min_length=5, max_length=100)
    codigo_tarifa_iva: Optional[IVATariffCode] = None
    tarifa: Optional[Decimal] = Field(None, max_digits=4, decimal_places=2, description="Tax rate percentage")
    factor_calculo_iva: Optional[Decimal] = Field(
        None, 
        max_digits=5, 
        decimal_places=4, 
        description="IVA calculation factor for used goods"
    )
    monto: Decimal = Field(..., max_digits=18, decimal_places=5, description="Tax amount")
    
    # Specific tax data for non-tariff taxes (fuel, alcohol, beverages, tobacco)
    cantidad_unidad_medida: Optional[Decimal] = Field(
        None, 
        max_digits=7, 
        decimal_places=2,
        description="Quantity in unit of measure for specific taxes"
    )
    porcentaje: Optional[Decimal] = Field(
        None, 
        max_digits=4, 
        decimal_places=2,
        description="Percentage for alcohol tax"
    )
    proporcion: Optional[Decimal] = Field(
        None, 
        max_digits=5, 
        decimal_places=2,
        description="Proportion for alcohol tax calculation"
    )
    volumen_unidad_consumo: Optional[Decimal] = Field(
        None, 
        max_digits=7, 
        decimal_places=2,
        description="Volume per consumption unit for beverage tax"
    )
    impuesto_unidad: Optional[Decimal] = Field(
        None, 
        max_digits=18, 
        decimal_places=5,
        description="Tax per unit for specific taxes"
    )
    
    # Exemptions
    exoneraciones: Optional[List[ExemptionData]] = Field(None, max_items=5)

    @validator('codigo_impuesto_otro')
    def validate_other_tax_code(cls, v, values):
        """Validate other tax code when codigo is OTHERS."""
        codigo = values.get('codigo')
        if codigo == TaxCode.OTROS and not v:
            raise ValueError('codigo_impuesto_otro is required when codigo is OTHERS')
        return v

    @validator('codigo_tarifa_iva')
    def validate_iva_tariff_code(cls, v, values):
        """Validate IVA tariff code is required for IVA taxes."""
        codigo = values.get('codigo')
        if codigo == TaxCode.IVA and not v:
            raise ValueError('codigo_tarifa_iva is required for IVA taxes')
        return v

    @validator('tarifa')
    def validate_tax_rate(cls, v, values):
        """Validate tax rate based on tax type."""
        if v is not None:
            if v < 0 or v > 100:
                raise ValueError('Tax rate must be between 0 and 100')
        return v

    @validator('factor_calculo_iva')
    def validate_iva_factor(cls, v, values):
        """Validate IVA calculation factor for used goods regime."""
        codigo = values.get('codigo')
        if codigo == TaxCode.IVA_BIENES_USADOS and v is None:
            raise ValueError('factor_calculo_iva is required for used goods IVA')
        if v is not None and (v < 0 or v > 1):
            raise ValueError('IVA calculation factor must be between 0 and 1')
        return v

    @validator('monto')
    def validate_tax_amount(cls, v):
        """Validate tax amount is not negative."""
        if v < 0:
            raise ValueError('Tax amount cannot be negative')
        return v

    class Config:
        use_enum_values = True


class DiscountData(BaseModel):
    """Discount information for line items."""
    monto_descuento: Decimal = Field(..., max_digits=18, decimal_places=5, description="Discount amount")
    codigo_descuento: DiscountType
    codigo_descuento_otro: Optional[str] = Field(None, min_length=5, max_length=100)
    naturaleza_descuento: Optional[str] = Field(None, min_length=3, max_length=80, description="Discount nature")

    @validator('monto_descuento')
    def validate_discount_amount(cls, v):
        """Validate discount amount is not negative."""
        if v < 0:
            raise ValueError('Discount amount cannot be negative')
        return v

    @validator('codigo_descuento_otro')
    def validate_other_discount_code(cls, v, values):
        """Validate other discount code when codigo_descuento is OTHERS."""
        codigo = values.get('codigo_descuento')
        if codigo == DiscountType.OTHERS and not v:
            raise ValueError('codigo_descuento_otro is required when codigo_descuento is OTHERS')
        return v

    class Config:
        use_enum_values = True


class DocumentLineItem(BaseModel):
    """Comprehensive document line item with all product fields and tax support."""
    numero_linea: int = Field(..., ge=1, le=1000, description="Line number (1-1000)")
    codigo_cabys: str = Field(..., regex=r'^\d{13}$', description="13-digit CABYS code")
    codigos_comerciales: Optional[List[CommercialCode]] = Field(None, max_items=5)
    cantidad: Decimal = Field(..., gt=0, max_digits=16, decimal_places=3, description="Quantity")
    unidad_medida: str = Field(..., max_length=10, description="Unit of measure")
    unidad_medida_comercial: Optional[str] = Field(None, max_length=20, description="Commercial unit")
    descripcion: str = Field(..., min_length=3, max_length=200, description="Product/service description")
    precio_unitario: Decimal = Field(..., ge=0, max_digits=18, decimal_places=5, description="Unit price")
    monto_total: Decimal = Field(..., max_digits=18, decimal_places=5, description="Total amount")
    
    # Special product fields
    tipo_transaccion: Optional[TransactionType] = None
    numero_vin_serie: Optional[str] = Field(None, max_length=17, description="VIN/serial number for vehicles")
    registro_medicamento: Optional[str] = Field(None, max_length=100, description="Medicine registration")
    forma_farmaceutica: Optional[str] = Field(None, max_length=3, description="Pharmaceutical form code")
    
    # Package/combo components
    detalle_surtido: Optional[List[PackageComponent]] = Field(None, max_items=20)
    
    # Discounts and taxes
    descuento: Optional[DiscountData] = None
    impuestos: List[TaxData] = Field(..., min_items=1, description="Tax information (at least one)")

    @validator('codigo_cabys')
    def validate_cabys_format(cls, v):
        """Validate CABYS code format."""
        if not v.isdigit() or len(v) != 13:
            raise ValueError('CABYS code must be exactly 13 digits')
        return v

    @validator('numero_vin_serie')
    def validate_vin_format(cls, v):
        """Validate VIN format when provided."""
        if v and not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', v):
            raise ValueError('VIN must be 17 alphanumeric characters (excluding I, O, Q)')
        return v

    @validator('forma_farmaceutica')
    def validate_pharmaceutical_form(cls, v):
        """Validate pharmaceutical form code format."""
        if v and not re.match(r'^\d{3}$', v):
            raise ValueError('Pharmaceutical form code must be exactly 3 digits')
        return v

    @validator('monto_total')
    def validate_total_amount(cls, v, values):
        """Validate total amount calculation."""
        cantidad = values.get('cantidad')
        precio_unitario = values.get('precio_unitario')
        descuento = values.get('descuento')
        
        if cantidad and precio_unitario:
            expected_subtotal = cantidad * precio_unitario
            discount_amount = descuento.monto_descuento if descuento else Decimal('0')
            expected_total = expected_subtotal - discount_amount
            
            # Allow small rounding differences
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError(f'Total amount {v} does not match calculated total {expected_total}')
        
        return v

    @validator('impuestos')
    def validate_taxes_not_empty(cls, v):
        """Validate at least one tax is provided."""
        if not v:
            raise ValueError('At least one tax must be specified')
        return v

    @validator('detalle_surtido')
    def validate_package_components(cls, v, values):
        """Validate package components when provided."""
        if v:
            # Ensure unique CABYS codes within package
            cabys_codes = [comp.codigo_cabys for comp in v]
            if len(cabys_codes) != len(set(cabys_codes)):
                raise ValueError('Package components must have unique CABYS codes')
        return v

    class Config:
        use_enum_values = True


class LineItemSummary(BaseModel):
    """Summary information for line items in responses."""
    numero_linea: int
    codigo_cabys: str
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    monto_total: Decimal
    total_impuestos: Decimal

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }