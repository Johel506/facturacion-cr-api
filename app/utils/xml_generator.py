"""
Comprehensive UBL 2.1 XML generator for Costa Rica electronic documents.
Supports all 7 document types with proper namespaces and structure.

Requirements: 9.1, 11.1, 14.1, 15.1, 17.1
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from app.schemas.enums import DocumentType, IdentificationType, SaleCondition, PaymentMethod
from app.schemas.documents import DocumentCreate, DocumentReference, OtherCharge
from app.schemas.document_items import DocumentLineItem, TaxData, ExemptionData, DiscountData
from app.schemas.base import EmisorData, ReceptorData, IdentificationData, LocationData, PhoneData


class XMLGenerator:
    """
    Comprehensive XML generator for Costa Rican electronic documents.
    Generates UBL 2.1 compliant XML for all 7 document types.
    """
    
    # Document type to namespace mapping
    NAMESPACES = {
        DocumentType.FACTURA_ELECTRONICA: "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica",
        DocumentType.NOTA_DEBITO_ELECTRONICA: "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/notaDebitoElectronica",
        DocumentType.NOTA_CREDITO_ELECTRONICA: "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/notaCreditoElectronica",
        DocumentType.TIQUETE_ELECTRONICO: "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/tiqueteElectronico",
        DocumentType.FACTURA_EXPORTACION: "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronicaExportacion",
        DocumentType.FACTURA_COMPRA: "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronicaCompra",
        DocumentType.RECIBO_PAGO: "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/reciboElectronicoPago"
    }
    
    # Document type to root element mapping
    ROOT_ELEMENTS = {
        DocumentType.FACTURA_ELECTRONICA: "FacturaElectronica",
        DocumentType.NOTA_DEBITO_ELECTRONICA: "NotaDebitoElectronica",
        DocumentType.NOTA_CREDITO_ELECTRONICA: "NotaCreditoElectronica",
        DocumentType.TIQUETE_ELECTRONICO: "TiqueteElectronico",
        DocumentType.FACTURA_EXPORTACION: "FacturaElectronicaExportacion",
        DocumentType.FACTURA_COMPRA: "FacturaElectronicaCompra",
        DocumentType.RECIBO_PAGO: "ReciboElectronicoPago"
    }
    
    def __init__(self, tenant_id: str, proveedor_sistemas: str = None):
        """
        Initialize XML generator.
        
        Args:
            tenant_id: Tenant identification for system provider
            proveedor_sistemas: System provider identification (defaults to tenant_id)
        """
        self.tenant_id = tenant_id
        self.proveedor_sistemas = proveedor_sistemas or tenant_id
    
    def generate_xml(
        self, 
        document_data: DocumentCreate, 
        numero_consecutivo: str,
        clave: str,
        fecha_emision: datetime = None
    ) -> str:
        """
        Generate complete XML for any document type.
        
        Args:
            document_data: Document creation data
            numero_consecutivo: 20-digit consecutive number
            clave: 50-digit document key
            fecha_emision: Emission date (defaults to now)
            
        Returns:
            Formatted XML string
        """
        if fecha_emision is None:
            fecha_emision = datetime.now(timezone.utc)
        
        # Get namespace and root element for document type
        namespace = self.NAMESPACES[document_data.tipo_documento]
        root_element_name = self.ROOT_ELEMENTS[document_data.tipo_documento]
        
        # Create root element with namespace
        root = Element(root_element_name)
        root.set("xmlns", namespace)
        root.set("xmlns:ds", "http://www.w3.org/2000/09/xmldsig#")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        
        # Generate document header
        self._add_document_header(root, clave, numero_consecutivo, fecha_emision, document_data)
        
        # Add emisor data
        self._add_emisor_data(root, document_data.emisor)
        
        # Add receptor data (optional for tickets)
        if document_data.receptor or document_data.tipo_documento != DocumentType.TIQUETE_ELECTRONICO:
            self._add_receptor_data(root, document_data.receptor)
        
        # Add transaction conditions
        self._add_transaction_conditions(root, document_data)
        
        # Add line items (DetalleServicio)
        if document_data.detalles:
            self._add_line_items(root, document_data.detalles)
        
        # Add document references (for credit/debit notes)
        if document_data.referencias:
            self._add_document_references(root, document_data.referencias)
        
        # Add other charges
        if document_data.otros_cargos:
            self._add_other_charges(root, document_data.otros_cargos)
        
        # Add document summary (ResumenFactura)
        self._add_document_summary(root, document_data)
        
        # Add additional observations
        if document_data.observaciones:
            observaciones_elem = SubElement(root, "Observaciones")
            observaciones_elem.text = document_data.observaciones
        
        # Format and return XML
        return self._format_xml(root)
    
    def _add_document_header(
        self, 
        root: Element, 
        clave: str, 
        numero_consecutivo: str,
        fecha_emision: datetime,
        document_data: DocumentCreate
    ) -> None:
        """Add document header elements."""
        # Document key (50 digits)
        clave_elem = SubElement(root, "Clave")
        clave_elem.text = clave
        
        # System provider identification
        proveedor_elem = SubElement(root, "ProveedorSistemas")
        proveedor_elem.text = self.proveedor_sistemas
        
        # Emisor economic activity code
        codigo_actividad_emisor = SubElement(root, "CodigoActividadEmisor")
        codigo_actividad_emisor.text = document_data.emisor.codigo_actividad
        
        # Receptor economic activity code (optional)
        if document_data.receptor and document_data.receptor.codigo_actividad:
            codigo_actividad_receptor = SubElement(root, "CodigoActividadReceptor")
            codigo_actividad_receptor.text = document_data.receptor.codigo_actividad
        
        # Consecutive number (20 digits)
        numero_consecutivo_elem = SubElement(root, "NumeroConsecutivo")
        numero_consecutivo_elem.text = numero_consecutivo
        
        # Emission date
        fecha_emision_elem = SubElement(root, "FechaEmision")
        fecha_emision_elem.text = fecha_emision.isoformat()
    
    def _add_emisor_data(self, root: Element, emisor: EmisorData) -> None:
        """Add emisor (issuer) data."""
        emisor_elem = SubElement(root, "Emisor")
        
        # Company name
        nombre_elem = SubElement(emisor_elem, "Nombre")
        nombre_elem.text = emisor.nombre
        
        # Identification
        identificacion_elem = SubElement(emisor_elem, "Identificacion")
        self._add_identification_data(identificacion_elem, emisor.identificacion)
        
        # Commercial name (optional)
        if emisor.nombre_comercial:
            nombre_comercial_elem = SubElement(emisor_elem, "NombreComercial")
            nombre_comercial_elem.text = emisor.nombre_comercial
        
        # Location
        ubicacion_elem = SubElement(emisor_elem, "Ubicacion")
        self._add_location_data(ubicacion_elem, emisor.ubicacion)
        
        # Phone (optional)
        if emisor.telefono:
            telefono_elem = SubElement(emisor_elem, "Telefono")
            self._add_phone_data(telefono_elem, emisor.telefono)
        
        # Email addresses
        correo_electronico_elem = SubElement(emisor_elem, "CorreoElectronico")
        correo_electronico_elem.text = emisor.correo_electronico[0]  # Primary email
    
    def _add_receptor_data(self, root: Element, receptor: Optional[ReceptorData]) -> None:
        """Add receptor (receiver) data."""
        receptor_elem = SubElement(root, "Receptor")
        
        if receptor:
            # Company/person name
            nombre_elem = SubElement(receptor_elem, "Nombre")
            nombre_elem.text = receptor.nombre
            
            # Identification (optional for tickets)
            if receptor.identificacion:
                identificacion_elem = SubElement(receptor_elem, "Identificacion")
                self._add_identification_data(identificacion_elem, receptor.identificacion)
            
            # Commercial name (optional)
            if receptor.nombre_comercial:
                nombre_comercial_elem = SubElement(receptor_elem, "NombreComercial")
                nombre_comercial_elem.text = receptor.nombre_comercial
            
            # Location (Costa Rican or foreign)
            if receptor.ubicacion:
                ubicacion_elem = SubElement(receptor_elem, "Ubicacion")
                self._add_location_data(ubicacion_elem, receptor.ubicacion)
            elif receptor.otras_senas_extranjero:
                ubicacion_elem = SubElement(receptor_elem, "Ubicacion")
                otras_senas_elem = SubElement(ubicacion_elem, "OtrasSenasExtranjero")
                otras_senas_elem.text = receptor.otras_senas_extranjero
            
            # Phone (optional)
            if receptor.telefono:
                telefono_elem = SubElement(receptor_elem, "Telefono")
                self._add_phone_data(telefono_elem, receptor.telefono)
            
            # Email (optional)
            if receptor.correo_electronico:
                correo_electronico_elem = SubElement(receptor_elem, "CorreoElectronico")
                correo_electronico_elem.text = receptor.correo_electronico
    
    def _add_identification_data(self, parent: Element, identificacion: IdentificationData) -> None:
        """Add identification data."""
        tipo_elem = SubElement(parent, "Tipo")
        # Handle both enum objects and string values
        tipo_elem.text = identificacion.tipo.value if hasattr(identificacion.tipo, 'value') else str(identificacion.tipo)
        
        numero_elem = SubElement(parent, "Numero")
        numero_elem.text = identificacion.numero
    
    def _add_location_data(self, parent: Element, ubicacion: LocationData) -> None:
        """Add location data."""
        provincia_elem = SubElement(parent, "Provincia")
        provincia_elem.text = str(ubicacion.provincia)
        
        canton_elem = SubElement(parent, "Canton")
        canton_elem.text = str(ubicacion.canton).zfill(2)  # Zero-pad to 2 digits
        
        distrito_elem = SubElement(parent, "Distrito")
        distrito_elem.text = str(ubicacion.distrito).zfill(2)  # Zero-pad to 2 digits
        
        if ubicacion.barrio:
            barrio_elem = SubElement(parent, "Barrio")
            barrio_elem.text = ubicacion.barrio
        
        otras_senas_elem = SubElement(parent, "OtrasSenas")
        otras_senas_elem.text = ubicacion.otras_senas
    
    def _add_phone_data(self, parent: Element, telefono: PhoneData) -> None:
        """Add phone data."""
        codigo_pais_elem = SubElement(parent, "CodigoPais")
        codigo_pais_elem.text = str(telefono.codigo_pais)
        
        numero_elem = SubElement(parent, "NumTelefono")
        numero_elem.text = str(telefono.numero)
    
    def _add_transaction_conditions(self, root: Element, document_data: DocumentCreate) -> None:
        """Add transaction conditions."""
        # Sale condition
        condicion_venta_elem = SubElement(root, "CondicionVenta")
        condicion_venta_elem.text = document_data.condicion_venta.value if hasattr(document_data.condicion_venta, 'value') else str(document_data.condicion_venta)
        
        # Other sale condition description (required when 99)
        if document_data.condicion_venta_otros:
            condicion_venta_otros_elem = SubElement(root, "CondicionVentaOtros")
            condicion_venta_otros_elem.text = document_data.condicion_venta_otros
        
        # Credit term (required for credit sales)
        if document_data.plazo_credito:
            plazo_credito_elem = SubElement(root, "PlazoCredito")
            plazo_credito_elem.text = str(document_data.plazo_credito)
        
        # Payment method
        medio_pago_elem = SubElement(root, "MedioPago")
        medio_pago_elem.text = document_data.medio_pago.value if hasattr(document_data.medio_pago, 'value') else str(document_data.medio_pago)
        
        # Other payment method description (required when 99)
        if document_data.medio_pago_otros:
            medio_pago_otros_elem = SubElement(root, "MedioPagoOtros")
            medio_pago_otros_elem.text = document_data.medio_pago_otros
    
    def _add_line_items(self, root: Element, detalles: List[DocumentLineItem]) -> None:
        """Add line items (DetalleServicio)."""
        detalle_servicio_elem = SubElement(root, "DetalleServicio")
        
        for detalle in detalles:
            linea_detalle_elem = SubElement(detalle_servicio_elem, "LineaDetalle")
            
            # Line number
            numero_linea_elem = SubElement(linea_detalle_elem, "NumeroLinea")
            numero_linea_elem.text = str(detalle.numero_linea)
            
            # CABYS code
            codigo_cabys_elem = SubElement(linea_detalle_elem, "CodigoCABYS")
            codigo_cabys_elem.text = detalle.codigo_cabys
            
            # Commercial codes (up to 5)
            if detalle.codigos_comerciales:
                for codigo_comercial in detalle.codigos_comerciales:
                    codigo_comercial_elem = SubElement(linea_detalle_elem, "CodigoComercial")
                    
                    tipo_elem = SubElement(codigo_comercial_elem, "Tipo")
                    tipo_elem.text = codigo_comercial.tipo.value if hasattr(codigo_comercial.tipo, 'value') else str(codigo_comercial.tipo)
                    
                    codigo_elem = SubElement(codigo_comercial_elem, "Codigo")
                    codigo_elem.text = codigo_comercial.codigo
            
            # Quantity
            cantidad_elem = SubElement(linea_detalle_elem, "Cantidad")
            cantidad_elem.text = str(detalle.cantidad)
            
            # Unit of measure
            unidad_medida_elem = SubElement(linea_detalle_elem, "UnidadMedida")
            unidad_medida_elem.text = detalle.unidad_medida
            
            # Commercial unit (optional)
            if detalle.unidad_medida_comercial:
                unidad_medida_comercial_elem = SubElement(linea_detalle_elem, "UnidadMedidaComercial")
                unidad_medida_comercial_elem.text = detalle.unidad_medida_comercial
            
            # Description
            descripcion_elem = SubElement(linea_detalle_elem, "Detalle")
            descripcion_elem.text = detalle.descripcion
            
            # Unit price
            precio_unitario_elem = SubElement(linea_detalle_elem, "PrecioUnitario")
            precio_unitario_elem.text = str(detalle.precio_unitario)
            
            # Total amount
            monto_total_elem = SubElement(linea_detalle_elem, "MontoTotal")
            monto_total_elem.text = str(detalle.monto_total)
            
            # Special fields
            if detalle.tipo_transaccion:
                tipo_transaccion_elem = SubElement(linea_detalle_elem, "TipoTransaccion")
                tipo_transaccion_elem.text = detalle.tipo_transaccion.value if hasattr(detalle.tipo_transaccion, 'value') else str(detalle.tipo_transaccion)
            
            if detalle.numero_vin_serie:
                numero_vin_elem = SubElement(linea_detalle_elem, "NumeroVINSerie")
                numero_vin_elem.text = detalle.numero_vin_serie
            
            if detalle.registro_medicamento:
                registro_medicamento_elem = SubElement(linea_detalle_elem, "RegistroMedicamento")
                registro_medicamento_elem.text = detalle.registro_medicamento
            
            if detalle.forma_farmaceutica:
                forma_farmaceutica_elem = SubElement(linea_detalle_elem, "FormaFarmaceutica")
                forma_farmaceutica_elem.text = detalle.forma_farmaceutica
            
            # Package components (DetalleSurtido)
            if detalle.detalle_surtido:
                detalle_surtido_elem = SubElement(linea_detalle_elem, "DetalleSurtido")
                for componente in detalle.detalle_surtido:
                    componente_elem = SubElement(detalle_surtido_elem, "ComponenteSurtido")
                    
                    codigo_cabys_comp_elem = SubElement(componente_elem, "CodigoCABYS")
                    codigo_cabys_comp_elem.text = componente.codigo_cabys
                    
                    cantidad_comp_elem = SubElement(componente_elem, "Cantidad")
                    cantidad_comp_elem.text = str(componente.cantidad)
                    
                    unidad_medida_comp_elem = SubElement(componente_elem, "UnidadMedida")
                    unidad_medida_comp_elem.text = componente.unidad_medida
                    
                    descripcion_comp_elem = SubElement(componente_elem, "Detalle")
                    descripcion_comp_elem.text = componente.descripcion
            
            # Discount (optional)
            if detalle.descuento:
                self._add_discount_data(linea_detalle_elem, detalle.descuento)
            
            # Taxes (required - at least one)
            self._add_tax_data(linea_detalle_elem, detalle.impuestos)
    
    def _add_discount_data(self, parent: Element, descuento: DiscountData) -> None:
        """Add discount data."""
        descuento_elem = SubElement(parent, "Descuento")
        
        monto_descuento_elem = SubElement(descuento_elem, "MontoDescuento")
        monto_descuento_elem.text = str(descuento.monto_descuento)
        
        codigo_descuento_elem = SubElement(descuento_elem, "CodigoDescuento")
        codigo_descuento_elem.text = descuento.codigo_descuento.value if hasattr(descuento.codigo_descuento, 'value') else str(descuento.codigo_descuento)
        
        if descuento.codigo_descuento_otro:
            codigo_descuento_otro_elem = SubElement(descuento_elem, "CodigoDescuentoOtro")
            codigo_descuento_otro_elem.text = descuento.codigo_descuento_otro
        
        if descuento.naturaleza_descuento:
            naturaleza_descuento_elem = SubElement(descuento_elem, "NaturalezaDescuento")
            naturaleza_descuento_elem.text = descuento.naturaleza_descuento
    
    def _add_tax_data(self, parent: Element, impuestos: List[TaxData]) -> None:
        """Add tax data for line items."""
        impuesto_elem = SubElement(parent, "Impuesto")
        
        for impuesto in impuestos:
            impuesto_item_elem = SubElement(impuesto_elem, "ImpuestoItem")
            
            # Tax code
            codigo_elem = SubElement(impuesto_item_elem, "Codigo")
            codigo_elem.text = impuesto.codigo.value if hasattr(impuesto.codigo, 'value') else str(impuesto.codigo)
            
            # Other tax code description (required when 99)
            if impuesto.codigo_impuesto_otro:
                codigo_otro_elem = SubElement(impuesto_item_elem, "CodigoImpuestoOtro")
                codigo_otro_elem.text = impuesto.codigo_impuesto_otro
            
            # IVA tariff code (required for IVA)
            if impuesto.codigo_tarifa_iva:
                codigo_tarifa_elem = SubElement(impuesto_item_elem, "CodigoTarifa")
                codigo_tarifa_elem.text = impuesto.codigo_tarifa_iva.value if hasattr(impuesto.codigo_tarifa_iva, 'value') else str(impuesto.codigo_tarifa_iva)
            
            # Tax rate
            if impuesto.tarifa is not None:
                tarifa_elem = SubElement(impuesto_item_elem, "Tarifa")
                tarifa_elem.text = str(impuesto.tarifa)
            
            # IVA calculation factor (for used goods)
            if impuesto.factor_calculo_iva is not None:
                factor_elem = SubElement(impuesto_item_elem, "FactorCalculoIVA")
                factor_elem.text = str(impuesto.factor_calculo_iva)
            
            # Tax amount
            monto_elem = SubElement(impuesto_item_elem, "Monto")
            monto_elem.text = str(impuesto.monto)
            
            # Specific tax fields for non-tariff taxes
            if impuesto.cantidad_unidad_medida is not None:
                cantidad_unidad_elem = SubElement(impuesto_item_elem, "CantidadUnidadMedida")
                cantidad_unidad_elem.text = str(impuesto.cantidad_unidad_medida)
            
            if impuesto.porcentaje is not None:
                porcentaje_elem = SubElement(impuesto_item_elem, "Porcentaje")
                porcentaje_elem.text = str(impuesto.porcentaje)
            
            if impuesto.proporcion is not None:
                proporcion_elem = SubElement(impuesto_item_elem, "Proporcion")
                proporcion_elem.text = str(impuesto.proporcion)
            
            if impuesto.volumen_unidad_consumo is not None:
                volumen_elem = SubElement(impuesto_item_elem, "VolumenUnidadConsumo")
                volumen_elem.text = str(impuesto.volumen_unidad_consumo)
            
            if impuesto.impuesto_unidad is not None:
                impuesto_unidad_elem = SubElement(impuesto_item_elem, "ImpuestoUnidad")
                impuesto_unidad_elem.text = str(impuesto.impuesto_unidad)
            
            # Exemptions (optional)
            if impuesto.exoneraciones:
                self._add_exemption_data(impuesto_item_elem, impuesto.exoneraciones)
    
    def _add_exemption_data(self, parent: Element, exoneraciones: List[ExemptionData]) -> None:
        """Add exemption data."""
        for exoneracion in exoneraciones:
            exoneracion_elem = SubElement(parent, "Exoneracion")
            
            # Document type
            tipo_documento_elem = SubElement(exoneracion_elem, "TipoDocumento")
            tipo_documento_elem.text = exoneracion.tipo_documento.value if hasattr(exoneracion.tipo_documento, 'value') else str(exoneracion.tipo_documento)
            
            # Other document type (required when 99)
            if exoneracion.tipo_documento_otro:
                tipo_documento_otro_elem = SubElement(exoneracion_elem, "TipoDocumentoOtro")
                tipo_documento_otro_elem.text = exoneracion.tipo_documento_otro
            
            # Document number
            numero_documento_elem = SubElement(exoneracion_elem, "NumeroDocumento")
            numero_documento_elem.text = exoneracion.numero_documento
            
            # Article and subsection (optional)
            if exoneracion.articulo:
                articulo_elem = SubElement(exoneracion_elem, "Articulo")
                articulo_elem.text = str(exoneracion.articulo)
            
            if exoneracion.inciso:
                inciso_elem = SubElement(exoneracion_elem, "Inciso")
                inciso_elem.text = str(exoneracion.inciso)
            
            # Institution
            nombre_institucion_elem = SubElement(exoneracion_elem, "NombreInstitucion")
            nombre_institucion_elem.text = exoneracion.nombre_institucion.value if hasattr(exoneracion.nombre_institucion, 'value') else str(exoneracion.nombre_institucion)
            
            # Other institution (required when 99)
            if exoneracion.nombre_institucion_otros:
                nombre_institucion_otros_elem = SubElement(exoneracion_elem, "NombreInstitucionOtros")
                nombre_institucion_otros_elem.text = exoneracion.nombre_institucion_otros
            
            # Emission date
            fecha_emision_elem = SubElement(exoneracion_elem, "FechaEmision")
            fecha_emision_elem.text = exoneracion.fecha_emision.isoformat()
            
            # Exempted rate
            tarifa_exonerada_elem = SubElement(exoneracion_elem, "TarifaExonerada")
            tarifa_exonerada_elem.text = str(exoneracion.tarifa_exonerada)
            
            # Exemption amount
            monto_exoneracion_elem = SubElement(exoneracion_elem, "MontoExoneracion")
            monto_exoneracion_elem.text = str(exoneracion.monto_exoneracion)
    
    def _add_document_references(self, root: Element, referencias: List[DocumentReference]) -> None:
        """Add document references for credit/debit notes."""
        for referencia in referencias:
            referencia_elem = SubElement(root, "InformacionReferencia")
            
            # Document type
            tipo_documento_elem = SubElement(referencia_elem, "TipoDoc")
            tipo_documento_elem.text = referencia.tipo_documento.value if hasattr(referencia.tipo_documento, 'value') else str(referencia.tipo_documento)
            
            # Other document type (required when 99)
            if referencia.tipo_documento_otro:
                tipo_documento_otro_elem = SubElement(referencia_elem, "TipoDocOtro")
                tipo_documento_otro_elem.text = referencia.tipo_documento_otro
            
            # Reference number (document key or consecutive)
            if referencia.numero:
                numero_elem = SubElement(referencia_elem, "Numero")
                numero_elem.text = referencia.numero
            
            # Emission date
            fecha_emision_elem = SubElement(referencia_elem, "FechaEmision")
            fecha_emision_elem.text = referencia.fecha_emision.isoformat()
            
            # Reference code
            if referencia.codigo:
                codigo_elem = SubElement(referencia_elem, "Codigo")
                codigo_elem.text = referencia.codigo.value if hasattr(referencia.codigo, 'value') else str(referencia.codigo)
            
            # Other reference code (required when 99)
            if referencia.codigo_referencia_otro:
                codigo_otro_elem = SubElement(referencia_elem, "CodigoReferenciaOtro")
                codigo_otro_elem.text = referencia.codigo_referencia_otro
            
            # Reason
            if referencia.razon:
                razon_elem = SubElement(referencia_elem, "Razon")
                razon_elem.text = referencia.razon
    
    def _add_other_charges(self, root: Element, otros_cargos: List[OtherCharge]) -> None:
        """Add other charges for stamps and additional fees."""
        otros_cargos_elem = SubElement(root, "OtrosCargos")
        
        for cargo in otros_cargos:
            cargo_elem = SubElement(otros_cargos_elem, "TipoDocumento")
            cargo_elem.text = cargo.tipo_documento.value if hasattr(cargo.tipo_documento, 'value') else str(cargo.tipo_documento)
            
            # Other document type (required when 99)
            if cargo.tipo_documento_otros:
                tipo_otros_elem = SubElement(otros_cargos_elem, "TipoDocumentoOtros")
                tipo_otros_elem.text = cargo.tipo_documento_otros
            
            # Third party information (optional)
            if cargo.tercero_identificacion:
                tercero_elem = SubElement(otros_cargos_elem, "TerceroIdentificacion")
                self._add_identification_data(tercero_elem, cargo.tercero_identificacion)
            
            if cargo.tercero_nombre:
                tercero_nombre_elem = SubElement(otros_cargos_elem, "TerceroNombre")
                tercero_nombre_elem.text = cargo.tercero_nombre
            
            # Charge details
            detalle_elem = SubElement(otros_cargos_elem, "Detalle")
            detalle_elem.text = cargo.detalle
            
            # Percentage (optional)
            if cargo.porcentaje is not None:
                porcentaje_elem = SubElement(otros_cargos_elem, "Porcentaje")
                porcentaje_elem.text = str(cargo.porcentaje)
            
            # Charge amount
            monto_cargo_elem = SubElement(otros_cargos_elem, "MontoCargo")
            monto_cargo_elem.text = str(cargo.monto_cargo)
    
    def _add_document_summary(self, root: Element, document_data: DocumentCreate) -> None:
        """Add document summary (ResumenFactura) with totals."""
        resumen_elem = SubElement(root, "ResumenFactura")
        
        # Currency code
        codigo_moneda_elem = SubElement(resumen_elem, "CodigoMoneda")
        codigo_moneda_elem.text = document_data.codigo_moneda
        
        # Exchange rate
        tipo_cambio_elem = SubElement(resumen_elem, "TipoCambio")
        tipo_cambio_elem.text = str(document_data.tipo_cambio)
        
        # Calculate totals from line items
        totals = self._calculate_totals(document_data)
        
        # Total services/goods
        total_servicios_elem = SubElement(resumen_elem, "TotalServGravados")
        total_servicios_elem.text = str(totals['total_servicios_gravados'])
        
        total_servicios_exentos_elem = SubElement(resumen_elem, "TotalServExentos")
        total_servicios_exentos_elem.text = str(totals['total_servicios_exentos'])
        
        total_servicios_exonerados_elem = SubElement(resumen_elem, "TotalServExonerados")
        total_servicios_exonerados_elem.text = str(totals['total_servicios_exonerados'])
        
        total_mercancias_elem = SubElement(resumen_elem, "TotalMercanciasGravadas")
        total_mercancias_elem.text = str(totals['total_mercancias_gravadas'])
        
        total_mercancias_exentas_elem = SubElement(resumen_elem, "TotalMercanciasExentas")
        total_mercancias_exentas_elem.text = str(totals['total_mercancias_exentas'])
        
        total_mercancias_exoneradas_elem = SubElement(resumen_elem, "TotalMercanciasExoneradas")
        total_mercancias_exoneradas_elem.text = str(totals['total_mercancias_exoneradas'])
        
        # Total gross amount
        total_gravado_elem = SubElement(resumen_elem, "TotalGravado")
        total_gravado_elem.text = str(totals['total_gravado'])
        
        # Total exempt amount
        total_exento_elem = SubElement(resumen_elem, "TotalExento")
        total_exento_elem.text = str(totals['total_exento'])
        
        # Total exempted amount
        total_exonerado_elem = SubElement(resumen_elem, "TotalExonerado")
        total_exonerado_elem.text = str(totals['total_exonerado'])
        
        # Net sale total
        total_venta_elem = SubElement(resumen_elem, "TotalVenta")
        total_venta_elem.text = str(totals['total_venta'])
        
        # Total discounts
        total_descuentos_elem = SubElement(resumen_elem, "TotalDescuentos")
        total_descuentos_elem.text = str(totals['total_descuentos'])
        
        # Net sale after discounts
        total_venta_neta_elem = SubElement(resumen_elem, "TotalVentaNeta")
        total_venta_neta_elem.text = str(totals['total_venta_neta'])
        
        # Total taxes
        total_impuesto_elem = SubElement(resumen_elem, "TotalImpuesto")
        total_impuesto_elem.text = str(totals['total_impuesto'])
        
        # IVA return (for used goods regime)
        if totals['iva_devuelto'] > 0:
            iva_devuelto_elem = SubElement(resumen_elem, "TotalIVADevuelto")
            iva_devuelto_elem.text = str(totals['iva_devuelto'])
        
        # Other charges total
        if document_data.otros_cargos:
            total_otros_cargos = sum(cargo.monto_cargo for cargo in document_data.otros_cargos)
            total_otros_cargos_elem = SubElement(resumen_elem, "TotalOtrosCargos")
            total_otros_cargos_elem.text = str(total_otros_cargos)
        else:
            total_otros_cargos_elem = SubElement(resumen_elem, "TotalOtrosCargos")
            total_otros_cargos_elem.text = "0.00000"
        
        # Final document total
        total_comprobante_elem = SubElement(resumen_elem, "TotalComprobante")
        total_comprobante_elem.text = str(totals['total_comprobante'])
    
    def _calculate_totals(self, document_data: DocumentCreate) -> Dict[str, Decimal]:
        """Calculate document totals from line items."""
        totals = {
            'total_servicios_gravados': Decimal('0'),
            'total_servicios_exentos': Decimal('0'),
            'total_servicios_exonerados': Decimal('0'),
            'total_mercancias_gravadas': Decimal('0'),
            'total_mercancias_exentas': Decimal('0'),
            'total_mercancias_exoneradas': Decimal('0'),
            'total_gravado': Decimal('0'),
            'total_exento': Decimal('0'),
            'total_exonerado': Decimal('0'),
            'total_venta': Decimal('0'),
            'total_descuentos': Decimal('0'),
            'total_venta_neta': Decimal('0'),
            'total_impuesto': Decimal('0'),
            'iva_devuelto': Decimal('0'),
            'total_comprobante': Decimal('0')
        }
        
        for detalle in document_data.detalles:
            # Determine if it's a service or merchandise based on CABYS code
            # This is a simplified logic - in reality, you'd check against CABYS database
            is_service = detalle.codigo_cabys.startswith('9')  # Services typically start with 9
            
            # Calculate line total after discount
            line_total = detalle.monto_total
            discount_amount = detalle.descuento.monto_descuento if detalle.descuento else Decimal('0')
            line_net_total = line_total - discount_amount
            
            # Determine tax status (gravado, exento, exonerado)
            has_tax = any(impuesto.monto > 0 for impuesto in detalle.impuestos)
            has_exemption = any(impuesto.exoneraciones for impuesto in detalle.impuestos if impuesto.exoneraciones)
            
            if has_exemption:
                # Exempted (exonerado)
                if is_service:
                    totals['total_servicios_exonerados'] += line_net_total
                else:
                    totals['total_mercancias_exoneradas'] += line_net_total
                totals['total_exonerado'] += line_net_total
            elif has_tax:
                # Taxed (gravado)
                if is_service:
                    totals['total_servicios_gravados'] += line_net_total
                else:
                    totals['total_mercancias_gravadas'] += line_net_total
                totals['total_gravado'] += line_net_total
            else:
                # Exempt (exento)
                if is_service:
                    totals['total_servicios_exentos'] += line_net_total
                else:
                    totals['total_mercancias_exentas'] += line_net_total
                totals['total_exento'] += line_net_total
            
            # Accumulate totals
            totals['total_venta'] += line_total
            totals['total_descuentos'] += discount_amount
            totals['total_venta_neta'] += line_net_total
            
            # Calculate taxes
            for impuesto in detalle.impuestos:
                totals['total_impuesto'] += impuesto.monto
        
        # Add other charges to final total
        otros_cargos_total = Decimal('0')
        if document_data.otros_cargos:
            otros_cargos_total = sum(cargo.monto_cargo for cargo in document_data.otros_cargos)
        
        # Final document total
        totals['total_comprobante'] = totals['total_venta_neta'] + totals['total_impuesto'] + otros_cargos_total - totals['iva_devuelto']
        
        return totals
    
    def _format_xml(self, root: Element) -> str:
        """Format XML with proper indentation."""
        # Convert to string
        rough_string = tostring(root, encoding='unicode')
        
        # Parse and format with minidom
        reparsed = minidom.parseString(rough_string)
        formatted = reparsed.toprettyxml(indent="  ", encoding=None)
        
        # Remove empty lines and fix formatting
        lines = [line for line in formatted.split('\n') if line.strip()]
        
        # Remove XML declaration added by minidom (we'll add our own)
        if lines[0].startswith('<?xml'):
            lines = lines[1:]
        
        # Add proper XML declaration
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>'
        formatted_xml = xml_declaration + '\n' + '\n'.join(lines)
        
        return formatted_xml


def generate_document_xml(
    document_data: DocumentCreate,
    tenant_id: str,
    numero_consecutivo: str,
    clave: str,
    fecha_emision: datetime = None,
    proveedor_sistemas: str = None
) -> str:
    """
    Convenience function to generate XML for any document type.
    
    Args:
        document_data: Document creation data
        tenant_id: Tenant identification
        numero_consecutivo: 20-digit consecutive number
        clave: 50-digit document key
        fecha_emision: Emission date (defaults to now)
        proveedor_sistemas: System provider identification
        
    Returns:
        Formatted XML string
    """
    generator = XMLGenerator(tenant_id, proveedor_sistemas)
    return generator.generate_xml(document_data, numero_consecutivo, clave, fecha_emision)