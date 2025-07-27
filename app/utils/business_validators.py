"""
Advanced business validation rules for Costa Rica electronic documents.
Implements document type specific validators and cross-field validation.
"""
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from app.schemas.enums import (
    DocumentType, SaleCondition, PaymentMethod, TaxCode, 
    ExemptionType, DiscountType, OtherChargeType
)


class DocumentTypeValidator:
    """Document type specific validation rules."""
    
    @staticmethod
    def validate_factura_electronica(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate electronic invoice specific rules."""
        errors = []
        
        # Receptor is required for invoices
        if not document_data.get('receptor'):
            errors.append("Receptor is required for electronic invoices")
        
        # Must have at least one line item
        if not document_data.get('detalles') or len(document_data['detalles']) == 0:
            errors.append("At least one line item is required")
        
        # Validate total amounts are positive
        if document_data.get('total_comprobante', 0) <= 0:
            errors.append("Total amount must be positive for invoices")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_nota_credito(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate credit note specific rules."""
        errors = []
        
        # Credit notes must have references to original documents
        if not document_data.get('referencias') or len(document_data['referencias']) == 0:
            errors.append("Credit notes must reference at least one original document")
        
        # Receptor is required
        if not document_data.get('receptor'):
            errors.append("Receptor is required for credit notes")
        
        # Validate reference document types are appropriate
        referencias = document_data.get('referencias', [])
        for ref in referencias:
            if ref.get('tipo_documento') not in ['01', '04', '05']:  # Invoice, Ticket, Export Invoice
                errors.append(f"Credit note cannot reference document type: {ref.get('tipo_documento')}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_nota_debito(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate debit note specific rules."""
        errors = []
        
        # Debit notes must have references to original documents
        if not document_data.get('referencias') or len(document_data['referencias']) == 0:
            errors.append("Debit notes must reference at least one original document")
        
        # Receptor is required
        if not document_data.get('receptor'):
            errors.append("Receptor is required for debit notes")
        
        # Total amount must be positive (adding charges)
        if document_data.get('total_comprobante', 0) <= 0:
            errors.append("Total amount must be positive for debit notes")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_tiquete_electronico(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate electronic ticket specific rules."""
        errors = []
        
        # Tickets can have optional receptor
        # But if receptor is provided, it must be valid
        
        # Tickets typically have simpler requirements
        if not document_data.get('detalles') or len(document_data['detalles']) == 0:
            errors.append("At least one line item is required")
        
        # Payment method is usually cash for tickets
        medio_pago = document_data.get('medio_pago')
        if medio_pago and medio_pago not in ['01', '02']:  # Cash or Card
            # This is a warning, not an error
            pass
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_factura_exportacion(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate export invoice specific rules."""
        errors = []
        
        # Export invoices must have receptor
        if not document_data.get('receptor'):
            errors.append("Receptor is required for export invoices")
        
        # Currency might be different from CRC
        codigo_moneda = document_data.get('codigo_moneda', 'CRC')
        if codigo_moneda != 'CRC':
            # Exchange rate must be provided and valid
            tipo_cambio = document_data.get('tipo_cambio')
            if not tipo_cambio or tipo_cambio <= 0:
                errors.append("Valid exchange rate is required for foreign currency")
        
        # Export invoices typically have zero IVA
        detalles = document_data.get('detalles', [])
        for detalle in detalles:
            impuestos = detalle.get('impuestos', [])
            for impuesto in impuestos:
                if impuesto.get('codigo') == '01' and impuesto.get('tarifa', 0) > 0:
                    errors.append("Export invoices typically should have 0% IVA")
                    break
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_factura_compra(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate purchase invoice specific rules."""
        errors = []
        
        # Purchase invoices have specific requirements
        if not document_data.get('receptor'):
            errors.append("Receptor is required for purchase invoices")
        
        # Validate that this is actually a purchase scenario
        # (This would depend on business logic)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_recibo_pago(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate payment receipt specific rules."""
        errors = []
        
        # Payment receipts must have receptor
        if not document_data.get('receptor'):
            errors.append("Receptor is required for payment receipts")
        
        # Must reference the documents being paid
        if not document_data.get('referencias') or len(document_data['referencias']) == 0:
            errors.append("Payment receipts must reference the documents being paid")
        
        return len(errors) == 0, errors


class ConditionalFieldValidator:
    """Validator for conditional field requirements."""
    
    @staticmethod
    def validate_others_codes(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that 'Others' codes have required descriptions."""
        errors = []
        
        # Sale condition others
        if document_data.get('condicion_venta') == '99':
            if not document_data.get('condicion_venta_otros'):
                errors.append("condicion_venta_otros is required when condicion_venta is '99' (Others)")
        
        # Payment method others
        if document_data.get('medio_pago') == '99':
            if not document_data.get('medio_pago_otros'):
                errors.append("medio_pago_otros is required when medio_pago is '99' (Others)")
        
        # Check line items for others codes
        detalles = document_data.get('detalles', [])
        for i, detalle in enumerate(detalles):
            # Tax code others
            impuestos = detalle.get('impuestos', [])
            for j, impuesto in enumerate(impuestos):
                if impuesto.get('codigo') == '99':
                    if not impuesto.get('codigo_impuesto_otro'):
                        errors.append(f"Line {i+1}, tax {j+1}: codigo_impuesto_otro is required when codigo is '99'")
            
            # Discount code others
            descuento = detalle.get('descuento')
            if descuento and descuento.get('codigo_descuento') == '99':
                if not descuento.get('codigo_descuento_otro'):
                    errors.append(f"Line {i+1}: codigo_descuento_otro is required when codigo_descuento is '99'")
        
        # Other charges others
        otros_cargos = document_data.get('otros_cargos', [])
        for i, cargo in enumerate(otros_cargos):
            if cargo.get('tipo_documento') == '99':
                if not cargo.get('tipo_documento_otros'):
                    errors.append(f"Other charge {i+1}: tipo_documento_otros is required when tipo_documento is '99'")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_exemption_requirements(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate exemption document requirements."""
        errors = []
        
        detalles = document_data.get('detalles', [])
        for i, detalle in enumerate(detalles):
            impuestos = detalle.get('impuestos', [])
            for j, impuesto in enumerate(impuestos):
                exoneraciones = impuesto.get('exoneraciones', [])
                for k, exoneracion in enumerate(exoneraciones):
                    # Validate exemption document number
                    if not exoneracion.get('numero_documento'):
                        errors.append(f"Line {i+1}, tax {j+1}, exemption {k+1}: numero_documento is required")
                    
                    # Validate institution
                    if not exoneracion.get('nombre_institucion'):
                        errors.append(f"Line {i+1}, tax {j+1}, exemption {k+1}: nombre_institucion is required")
                    
                    # Validate others fields
                    if exoneracion.get('tipo_documento') == '99':
                        if not exoneracion.get('tipo_documento_otro'):
                            errors.append(f"Line {i+1}, tax {j+1}, exemption {k+1}: tipo_documento_otro is required")
                    
                    if exoneracion.get('nombre_institucion') == '99':
                        if not exoneracion.get('nombre_institucion_otros'):
                            errors.append(f"Line {i+1}, tax {j+1}, exemption {k+1}: nombre_institucion_otros is required")
        
        return len(errors) == 0, errors


class CrossFieldValidator:
    """Validator for cross-field business logic."""
    
    @staticmethod
    def validate_credit_sale_requirements(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate credit sale specific requirements."""
        errors = []
        
        condicion_venta = document_data.get('condicion_venta')
        if condicion_venta == '02':  # Credit sale
            # Credit term is required
            plazo_credito = document_data.get('plazo_credito')
            if not plazo_credito:
                errors.append("plazo_credito is required for credit sales")
            elif plazo_credito <= 0:
                errors.append("plazo_credito must be positive for credit sales")
            elif plazo_credito > 365:
                errors.append("plazo_credito cannot exceed 365 days")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_foreign_currency_requirements(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate foreign currency requirements."""
        errors = []
        
        codigo_moneda = document_data.get('codigo_moneda', 'CRC')
        tipo_cambio = document_data.get('tipo_cambio', 1.0)
        
        if codigo_moneda != 'CRC':
            # Exchange rate must be different from 1.0
            if abs(float(tipo_cambio) - 1.0) < 0.0001:
                errors.append("Exchange rate must be different from 1.0 for foreign currencies")
            
            # Exchange rate must be reasonable
            if float(tipo_cambio) <= 0:
                errors.append("Exchange rate must be positive")
            elif float(tipo_cambio) > 10000:
                errors.append("Exchange rate seems unreasonably high")
        else:
            # For CRC, exchange rate should be 1.0
            if abs(float(tipo_cambio) - 1.0) > 0.0001:
                errors.append("Exchange rate must be 1.0 for CRC currency")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_tax_consistency(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate tax calculations are consistent."""
        errors = []
        
        detalles = document_data.get('detalles', [])
        for i, detalle in enumerate(detalles):
            cantidad = Decimal(str(detalle.get('cantidad', 0)))
            precio_unitario = Decimal(str(detalle.get('precio_unitario', 0)))
            monto_total = Decimal(str(detalle.get('monto_total', 0)))
            
            # Calculate expected subtotal
            expected_subtotal = cantidad * precio_unitario
            
            # Account for discounts
            descuento = detalle.get('descuento')
            discount_amount = Decimal(str(descuento.get('monto_descuento', 0))) if descuento else Decimal('0')
            
            expected_total = expected_subtotal - discount_amount
            
            # Allow small rounding differences
            if abs(monto_total - expected_total) > Decimal('0.01'):
                errors.append(f"Line {i+1}: Total amount calculation error. Expected: {expected_total}, got: {monto_total}")
            
            # Validate tax calculations
            impuestos = detalle.get('impuestos', [])
            for j, impuesto in enumerate(impuestos):
                codigo = impuesto.get('codigo')
                tarifa = Decimal(str(impuesto.get('tarifa', 0)))
                monto_impuesto = Decimal(str(impuesto.get('monto', 0)))
                
                if codigo == '01':  # IVA
                    # Calculate expected tax
                    base_imponible = expected_total  # After discount
                    expected_tax = (base_imponible * tarifa / 100).quantize(Decimal('0.01'))
                    
                    if abs(monto_impuesto - expected_tax) > Decimal('0.01'):
                        errors.append(f"Line {i+1}, tax {j+1}: IVA calculation error. Expected: {expected_tax}, got: {monto_impuesto}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_document_totals(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate document total calculations."""
        errors = []
        
        # Calculate totals from line items
        total_venta_neta = Decimal('0')
        total_impuesto = Decimal('0')
        
        detalles = document_data.get('detalles', [])
        for detalle in detalles:
            monto_total = Decimal(str(detalle.get('monto_total', 0)))
            total_venta_neta += monto_total
            
            impuestos = detalle.get('impuestos', [])
            for impuesto in impuestos:
                monto_impuesto = Decimal(str(impuesto.get('monto', 0)))
                total_impuesto += monto_impuesto
        
        # Add other charges
        total_otros_cargos = Decimal('0')
        otros_cargos = document_data.get('otros_cargos', [])
        for cargo in otros_cargos:
            monto_cargo = Decimal(str(cargo.get('monto_cargo', 0)))
            total_otros_cargos += monto_cargo
        
        # Calculate expected total
        expected_total = total_venta_neta + total_impuesto + total_otros_cargos
        
        # Compare with provided totals
        provided_venta_neta = Decimal(str(document_data.get('total_venta_neta', 0)))
        provided_impuesto = Decimal(str(document_data.get('total_impuesto', 0)))
        provided_total = Decimal(str(document_data.get('total_comprobante', 0)))
        
        if abs(total_venta_neta - provided_venta_neta) > Decimal('0.01'):
            errors.append(f"Net sale total mismatch. Calculated: {total_venta_neta}, provided: {provided_venta_neta}")
        
        if abs(total_impuesto - provided_impuesto) > Decimal('0.01'):
            errors.append(f"Tax total mismatch. Calculated: {total_impuesto}, provided: {provided_impuesto}")
        
        if abs(expected_total - provided_total) > Decimal('0.01'):
            errors.append(f"Document total mismatch. Calculated: {expected_total}, provided: {provided_total}")
        
        return len(errors) == 0, errors


class BusinessLogicValidator:
    """High-level business logic validator."""
    
    @staticmethod
    def validate_document_business_rules(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Comprehensive business rules validation."""
        all_errors = []
        
        # Get document type
        tipo_documento = document_data.get('tipo_documento')
        if not tipo_documento:
            return False, ["Document type is required"]
        
        # Document type specific validation
        type_validators = {
            DocumentType.FACTURA_ELECTRONICA: DocumentTypeValidator.validate_factura_electronica,
            DocumentType.NOTA_CREDITO_ELECTRONICA: DocumentTypeValidator.validate_nota_credito,
            DocumentType.NOTA_DEBITO_ELECTRONICA: DocumentTypeValidator.validate_nota_debito,
            DocumentType.TIQUETE_ELECTRONICO: DocumentTypeValidator.validate_tiquete_electronico,
            DocumentType.FACTURA_EXPORTACION: DocumentTypeValidator.validate_factura_exportacion,
            DocumentType.FACTURA_COMPRA: DocumentTypeValidator.validate_factura_compra,
            DocumentType.RECIBO_PAGO: DocumentTypeValidator.validate_recibo_pago,
        }
        
        validator = type_validators.get(DocumentType(tipo_documento))
        if validator:
            is_valid, errors = validator(document_data)
            if not is_valid:
                all_errors.extend(errors)
        
        # Conditional field validation
        is_valid, errors = ConditionalFieldValidator.validate_others_codes(document_data)
        if not is_valid:
            all_errors.extend(errors)
        
        is_valid, errors = ConditionalFieldValidator.validate_exemption_requirements(document_data)
        if not is_valid:
            all_errors.extend(errors)
        
        # Cross-field validation
        is_valid, errors = CrossFieldValidator.validate_credit_sale_requirements(document_data)
        if not is_valid:
            all_errors.extend(errors)
        
        is_valid, errors = CrossFieldValidator.validate_foreign_currency_requirements(document_data)
        if not is_valid:
            all_errors.extend(errors)
        
        is_valid, errors = CrossFieldValidator.validate_tax_consistency(document_data)
        if not is_valid:
            all_errors.extend(errors)
        
        is_valid, errors = CrossFieldValidator.validate_document_totals(document_data)
        if not is_valid:
            all_errors.extend(errors)
        
        return len(all_errors) == 0, all_errors
    
    @staticmethod
    def validate_line_item_business_rules(line_item: Dict[str, Any], line_number: int) -> Tuple[bool, List[str]]:
        """Validate business rules for individual line items."""
        errors = []
        
        # Validate required fields
        if not line_item.get('codigo_cabys'):
            errors.append(f"Line {line_number}: CABYS code is required")
        
        if not line_item.get('descripcion'):
            errors.append(f"Line {line_number}: Description is required")
        
        cantidad = line_item.get('cantidad', 0)
        if cantidad <= 0:
            errors.append(f"Line {line_number}: Quantity must be positive")
        
        precio_unitario = line_item.get('precio_unitario', 0)
        if precio_unitario < 0:
            errors.append(f"Line {line_number}: Unit price cannot be negative")
        
        # Validate taxes
        impuestos = line_item.get('impuestos', [])
        if not impuestos:
            errors.append(f"Line {line_number}: At least one tax must be specified")
        
        # Validate special product fields
        numero_vin = line_item.get('numero_vin_serie')
        if numero_vin:
            import re
            if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', numero_vin):$', numero_vin):
                errors.append(f"Line {line_number}: Invalid VIN format")
        
        return len(errors) == 0, errors


def validate_email_format(email: str) -> bool:
    """
    Validate email format using regex pattern.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email format is valid, False otherwise
    """
    import re
    
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(email_pattern, email.strip()))


def validate_phone_format(phone: str, country_code: str = "506") -> bool:
    """
    Validate Costa Rican phone number format.
    
    Args:
        phone: Phone number to validate
        country_code: Country code (default: 506 for Costa Rica)
    
    Returns:
        True if phone format is valid, False otherwise
    """
    import re
    
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove spaces, dashes, and parentheses
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Costa Rican phone patterns
    if country_code == "506":
        # 8-digit format: NNNN-NNNN
        if re.match(r'^\d{8}$', clean_phone):
            return True
        # With country code: +506-NNNN-NNNN or 506-NNNN-NNNN
        if re.match(r'^(\+?506)?\d{8}$', clean_phone):
            return True
    
    return False


def validate_complete_document(document_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Complete document validation including all business rules.
    This is the main entry point for document validation.
    """
    all_errors = []
    
    try:
        # Basic structure validation
        if not isinstance(document_data, dict):
            return False, ["Document data must be a dictionary"]
        
        # Business logic validation
        is_valid, errors = BusinessLogicValidator.validate_document_business_rules(document_data)
        if not is_valid:
            all_errors.extend(errors)
        
        # Line item validation
        detalles = document_data.get('detalles', [])
        for i, detalle in enumerate(detalles):
            is_valid, errors = BusinessLogicValidator.validate_line_item_business_rules(detalle, i + 1)
            if not is_valid:
                all_errors.extend(errors)
        
        return len(all_errors) == 0, all_errors
        
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]