"""initial_tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema for Costa Rica Electronic Invoice API"""
    
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('nombre_empresa', sa.String(length=255), nullable=False, comment='Company legal name'),
        sa.Column('cedula_juridica', sa.String(length=20), nullable=False, comment='Costa Rican legal identification number'),
        sa.Column('nombre_comercial', sa.String(length=255), nullable=True, comment='Commercial/trade name'),
        sa.Column('email_contacto', sa.String(length=255), nullable=False, comment='Primary contact email'),
        sa.Column('telefono_contacto', sa.String(length=20), nullable=True, comment='Primary contact phone'),
        sa.Column('direccion', sa.Text(), nullable=True, comment='Complete business address'),
        sa.Column('provincia', sa.Integer(), nullable=True, comment='Province code (1-7)'),
        sa.Column('canton', sa.Integer(), nullable=True, comment='Canton code'),
        sa.Column('distrito', sa.Integer(), nullable=True, comment='District code'),
        sa.Column('api_key', sa.String(length=64), nullable=False, comment='Cryptographically secure API key (min 32 chars)'),
        sa.Column('api_key_created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='API key creation timestamp'),
        sa.Column('certificado_p12', sa.LargeBinary(), nullable=True, comment='Encrypted P12 certificate binary data'),
        sa.Column('password_certificado', sa.Text(), nullable=True, comment='Encrypted certificate password'),
        sa.Column('certificado_uploaded_at', sa.DateTime(timezone=True), nullable=True, comment='Certificate upload timestamp'),
        sa.Column('certificado_expires_at', sa.DateTime(timezone=True), nullable=True, comment='Certificate expiration date'),
        sa.Column('certificado_subject', sa.String(length=500), nullable=True, comment='Certificate subject information'),
        sa.Column('certificado_issuer', sa.String(length=500), nullable=True, comment='Certificate issuer information'),
        sa.Column('plan', sa.String(length=20), nullable=False, server_default='basico', comment='Subscription plan: basico, pro, empresa'),
        sa.Column('limite_facturas_mes', sa.Integer(), nullable=False, server_default='100', comment='Monthly document limit based on plan'),
        sa.Column('facturas_usadas_mes', sa.Integer(), nullable=False, server_default='0', comment='Documents used in current month'),
        sa.Column('ultimo_reset_contador', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Last monthly counter reset'),
        sa.Column('total_documentos_creados', sa.Integer(), nullable=False, server_default='0', comment='Total documents created (all time)'),
        sa.Column('total_documentos_enviados', sa.Integer(), nullable=False, server_default='0', comment='Total documents sent to Ministry'),
        sa.Column('total_documentos_aceptados', sa.Integer(), nullable=False, server_default='0', comment='Total documents accepted by Ministry'),
        sa.Column('ultimo_documento_creado', sa.DateTime(timezone=True), nullable=True, comment='Timestamp of last document creation'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true', comment='Account active status'),
        sa.Column('verificado', sa.Boolean(), nullable=False, server_default='false', comment='Account verification status'),
        sa.Column('fecha_verificacion', sa.DateTime(timezone=True), nullable=True, comment='Account verification timestamp'),
        sa.Column('notificar_vencimiento_certificado', sa.Boolean(), nullable=False, server_default='true', comment='Enable certificate expiration notifications'),
        sa.Column('notificar_limite_mensual', sa.Boolean(), nullable=False, server_default='true', comment='Enable monthly limit notifications'),
        sa.Column('dias_notificacion_certificado', sa.String(length=20), nullable=False, server_default='30,15,7', comment='Days before expiration to notify (comma-separated)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(length=255), nullable=True, comment='User who created the tenant'),
        sa.Column('updated_by', sa.String(length=255), nullable=True, comment='User who last updated the tenant'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cedula_juridica'),
        sa.UniqueConstraint('api_key'),
        sa.CheckConstraint("plan IN ('basico', 'pro', 'empresa')", name='ck_tenant_plan_valid'),
        sa.CheckConstraint('limite_facturas_mes >= 0', name='ck_tenant_limite_facturas_positive'),
        sa.CheckConstraint('facturas_usadas_mes >= 0', name='ck_tenant_facturas_usadas_positive'),
        sa.CheckConstraint('facturas_usadas_mes <= limite_facturas_mes', name='ck_tenant_facturas_within_limit'),
        sa.CheckConstraint('provincia IS NULL OR (provincia >= 1 AND provincia <= 7)', name='ck_tenant_provincia_valid'),
        sa.CheckConstraint('canton IS NULL OR (canton >= 1 AND canton <= 99)', name='ck_tenant_canton_valid'),
        sa.CheckConstraint('distrito IS NULL OR (distrito >= 1 AND distrito <= 99)', name='ck_tenant_distrito_valid'),
        sa.CheckConstraint('char_length(api_key) >= 32', name='ck_tenant_api_key_length'),
        sa.CheckConstraint('char_length(cedula_juridica) >= 9', name='ck_tenant_cedula_length'),
        sa.CheckConstraint("email_contacto ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", name='ck_tenant_email_format')
    )
    
    # Create CABYS codes table
    op.create_table('codigos_cabys',
        sa.Column('codigo', sa.String(length=13), nullable=False, comment='13-digit CABYS code'),
        sa.Column('descripcion', sa.Text(), nullable=False, comment='Product/service description'),
        sa.Column('categoria_nivel_1', sa.String(length=255), nullable=True, comment='Level 1 category'),
        sa.Column('categoria_nivel_2', sa.String(length=255), nullable=True, comment='Level 2 category'),
        sa.Column('categoria_nivel_3', sa.String(length=255), nullable=True, comment='Level 3 category'),
        sa.Column('categoria_nivel_4', sa.String(length=255), nullable=True, comment='Level 4 category'),
        sa.Column('impuesto_iva', sa.Numeric(precision=4, scale=2), nullable=False, server_default='13.00', comment='Default IVA rate'),
        sa.Column('exento_iva', sa.Boolean(), nullable=False, server_default='false', comment='IVA exempt flag'),
        sa.Column('version_cabys', sa.String(length=10), nullable=False, server_default='4.4', comment='CABYS version'),
        sa.Column('fecha_vigencia_desde', sa.Date(), nullable=True, comment='Validity start date'),
        sa.Column('fecha_vigencia_hasta', sa.Date(), nullable=True, comment='Validity end date'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true', comment='Active status'),
        sa.Column('veces_usado', sa.Integer(), nullable=False, server_default='0', comment='Usage count for popularity'),
        sa.Column('ultimo_uso', sa.DateTime(timezone=True), nullable=True, comment='Last usage timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('codigo'),
        sa.CheckConstraint("codigo ~ '^\\d{13}$'", name='ck_cabys_codigo_format'),
        sa.CheckConstraint('char_length(descripcion) >= 3', name='ck_cabys_descripcion_length'),
        sa.CheckConstraint('impuesto_iva >= 0 AND impuesto_iva <= 99.99', name='ck_cabys_impuesto_range'),
        sa.CheckConstraint('veces_usado >= 0', name='ck_cabys_veces_usado_positive')
    )
    
    # Create geographic locations table
    op.create_table('ubicaciones_cr',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provincia', sa.Integer(), nullable=False, comment='Province code (1-7)'),
        sa.Column('canton', sa.Integer(), nullable=False, comment='Canton code'),
        sa.Column('distrito', sa.Integer(), nullable=False, comment='District code'),
        sa.Column('nombre_provincia', sa.String(length=50), nullable=False, comment='Province name'),
        sa.Column('nombre_canton', sa.String(length=100), nullable=False, comment='Canton name'),
        sa.Column('nombre_distrito', sa.String(length=100), nullable=False, comment='District name'),
        sa.Column('codigo_inec', sa.String(length=10), nullable=True, comment='INEC statistical code'),
        sa.Column('codigo_postal', sa.String(length=10), nullable=True, comment='Postal code'),
        sa.Column('cabecera_provincia', sa.Boolean(), nullable=False, server_default='false', comment='Province capital flag'),
        sa.Column('cabecera_canton', sa.Boolean(), nullable=False, server_default='false', comment='Canton capital flag'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true', comment='Active status'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provincia', 'canton', 'distrito'),
        sa.CheckConstraint('provincia >= 1 AND provincia <= 7', name='ck_ubicacion_provincia_valid'),
        sa.CheckConstraint('canton >= 1 AND canton <= 99', name='ck_ubicacion_canton_valid'),
        sa.CheckConstraint('distrito >= 1 AND distrito <= 99', name='ck_ubicacion_distrito_valid')
    )
    
    # Create units of measure table
    op.create_table('unidades_medida',
        sa.Column('codigo', sa.String(length=10), nullable=False, comment='Unit code'),
        sa.Column('descripcion', sa.String(length=200), nullable=False, comment='Unit description'),
        sa.Column('simbolo', sa.String(length=20), nullable=True, comment='Unit symbol'),
        sa.Column('categoria', sa.String(length=50), nullable=True, comment='Unit category'),
        sa.Column('tipo_medida', sa.String(length=50), nullable=True, comment='Measurement type'),
        sa.Column('uso_comun', sa.Boolean(), nullable=False, server_default='true', comment='Common usage flag'),
        sa.Column('uso_productos', sa.Boolean(), nullable=False, server_default='true', comment='Product usage flag'),
        sa.Column('uso_servicios', sa.Boolean(), nullable=False, server_default='false', comment='Service usage flag'),
        sa.Column('version_rtc', sa.String(length=10), nullable=False, server_default='443:2010', comment='RTC standard version'),
        sa.Column('fecha_vigencia_desde', sa.Date(), nullable=True, comment='Validity start date'),
        sa.Column('fecha_vigencia_hasta', sa.Date(), nullable=True, comment='Validity end date'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true', comment='Active status'),
        sa.Column('veces_usado', sa.Integer(), nullable=False, server_default='0', comment='Usage count for popularity'),
        sa.Column('ultimo_uso', sa.DateTime(timezone=True), nullable=True, comment='Last usage timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('codigo'),
        sa.CheckConstraint('char_length(descripcion) >= 2', name='ck_unidad_descripcion_length'),
        sa.CheckConstraint('veces_usado >= 0', name='ck_unidad_veces_usado_positive')
    )
    
    # Create documents table
    op.create_table('documentos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Tenant owner of the document'),
        sa.Column('tipo_documento', sa.Enum('FACTURA_ELECTRONICA', 'NOTA_DEBITO_ELECTRONICA', 'NOTA_CREDITO_ELECTRONICA', 'TIQUETE_ELECTRONICO', 'FACTURA_EXPORTACION', 'FACTURA_COMPRA', 'RECIBO_PAGO', name='documenttype'), nullable=False, comment='Document type: 01-07'),
        sa.Column('numero_consecutivo', sa.String(length=20), nullable=False, comment='20-digit consecutive number: Branch(3)+Terminal(5)+DocType(2)+Sequential(10)'),
        sa.Column('clave', sa.String(length=50), nullable=False, comment='50-character document key following official format'),
        sa.Column('fecha_emision', sa.DateTime(timezone=True), nullable=False, comment='Document emission date and time'),
        sa.Column('emisor_nombre', sa.String(length=100), nullable=False, comment='Issuer legal name'),
        sa.Column('emisor_tipo_identificacion', sa.Enum('CEDULA_FISICA', 'CEDULA_JURIDICA', 'DIMEX', 'NITE', 'EXTRANJERO_NO_DOMICILIADO', 'NO_CONTRIBUYENTE', name='identificationtype'), nullable=False, comment='Issuer identification type'),
        sa.Column('emisor_numero_identificacion', sa.String(length=20), nullable=False, comment='Issuer identification number'),
        sa.Column('emisor_nombre_comercial', sa.String(length=80), nullable=True, comment='Issuer commercial name'),
        sa.Column('emisor_codigo_actividad', sa.String(length=6), nullable=True, comment='Issuer economic activity code'),
        sa.Column('emisor_provincia', sa.Integer(), nullable=True, comment='Issuer province (1-7)'),
        sa.Column('emisor_canton', sa.Integer(), nullable=True, comment='Issuer canton'),
        sa.Column('emisor_distrito', sa.Integer(), nullable=True, comment='Issuer district'),
        sa.Column('emisor_barrio', sa.String(length=50), nullable=True, comment='Issuer neighborhood'),
        sa.Column('emisor_otras_senas', sa.String(length=250), nullable=True, comment='Issuer detailed address'),
        sa.Column('emisor_codigo_pais_telefono', sa.Integer(), nullable=True, comment='Issuer phone country code'),
        sa.Column('emisor_numero_telefono', sa.String(length=20), nullable=True, comment='Issuer phone number'),
        sa.Column('emisor_correo_electronico', sa.String(length=160), nullable=True, comment='Issuer email'),
        sa.Column('receptor_nombre', sa.String(length=100), nullable=True, comment='Receiver legal name'),
        sa.Column('receptor_tipo_identificacion', sa.Enum('CEDULA_FISICA', 'CEDULA_JURIDICA', 'DIMEX', 'NITE', 'EXTRANJERO_NO_DOMICILIADO', 'NO_CONTRIBUYENTE', name='identificationtype'), nullable=True, comment='Receiver identification type'),
        sa.Column('receptor_numero_identificacion', sa.String(length=20), nullable=True, comment='Receiver identification number'),
        sa.Column('receptor_nombre_comercial', sa.String(length=80), nullable=True, comment='Receiver commercial name'),
        sa.Column('receptor_codigo_actividad', sa.String(length=6), nullable=True, comment='Receiver economic activity code'),
        sa.Column('receptor_provincia', sa.Integer(), nullable=True, comment='Receiver province (1-7)'),
        sa.Column('receptor_canton', sa.Integer(), nullable=True, comment='Receiver canton'),
        sa.Column('receptor_distrito', sa.Integer(), nullable=True, comment='Receiver district'),
        sa.Column('receptor_barrio', sa.String(length=50), nullable=True, comment='Receiver neighborhood'),
        sa.Column('receptor_otras_senas', sa.String(length=250), nullable=True, comment='Receiver detailed address'),
        sa.Column('receptor_otras_senas_extranjero', sa.String(length=300), nullable=True, comment='Foreign receiver address'),
        sa.Column('receptor_codigo_pais_telefono', sa.Integer(), nullable=True, comment='Receiver phone country code'),
        sa.Column('receptor_numero_telefono', sa.String(length=20), nullable=True, comment='Receiver phone number'),
        sa.Column('receptor_correo_electronico', sa.String(length=160), nullable=True, comment='Receiver email'),
        sa.Column('condicion_venta', sa.Enum('CONTADO', 'CREDITO', 'CONSIGNACION', 'APARTADO', 'ARRENDAMIENTO_OPCION_COMPRA', 'ARRENDAMIENTO_FUNCION_FINANCIERA', 'COBRO_TERCERO', 'SERVICIOS_ESTADO_CREDITO', 'VENTA_CREDITO_90_DIAS', 'VENTA_MERCANCIA_NO_NACIONALIZADA', 'VENTA_BIENES_USADOS_NO_CONTRIBUYENTE', 'ARRENDAMIENTO_OPERATIVO', 'ARRENDAMIENTO_FINANCIERO', 'OTROS', name='salecondition'), nullable=False, comment='Sale condition: 01-15, 99'),
        sa.Column('condicion_venta_otros', sa.String(length=100), nullable=True, comment='Other sale condition description (required when 99)'),
        sa.Column('plazo_credito', sa.Integer(), nullable=True, comment='Credit term in days (required for credit sales)'),
        sa.Column('medio_pago', sa.Enum('EFECTIVO', 'TARJETA', 'CHEQUE', 'TRANSFERENCIA', 'RECAUDADO_TERCERO', 'OTROS', name='paymentmethod'), nullable=False, comment='Payment method: 01-05, 99'),
        sa.Column('medio_pago_otros', sa.String(length=100), nullable=True, comment='Other payment method description (required when 99)'),
        sa.Column('codigo_moneda', sa.String(length=3), nullable=False, server_default='CRC', comment='ISO 4217 currency code'),
        sa.Column('tipo_cambio', sa.Numeric(precision=18, scale=5), nullable=False, server_default='1.0', comment='Exchange rate to CRC'),
        sa.Column('total_venta_neta', sa.Numeric(precision=18, scale=5), nullable=False, comment='Net sale total (before taxes)'),
        sa.Column('total_impuesto', sa.Numeric(precision=18, scale=5), nullable=False, server_default='0', comment='Total tax amount'),
        sa.Column('total_descuento', sa.Numeric(precision=18, scale=5), nullable=False, server_default='0', comment='Total discount amount'),
        sa.Column('total_otros_cargos', sa.Numeric(precision=18, scale=5), nullable=False, server_default='0', comment='Total other charges'),
        sa.Column('total_comprobante', sa.Numeric(precision=18, scale=5), nullable=False, comment='Final document total'),
        sa.Column('xml_original', sa.Text(), nullable=True, comment='Original generated XML'),
        sa.Column('xml_firmado', sa.Text(), nullable=True, comment='Digitally signed XML'),
        sa.Column('xml_respuesta_hacienda', sa.Text(), nullable=True, comment='Ministry response XML'),
        sa.Column('estado', sa.Enum('BORRADOR', 'PENDIENTE', 'ENVIADO', 'PROCESANDO', 'ACEPTADO', 'RECHAZADO', 'ERROR', 'CANCELADO', name='documentstatus'), nullable=False, server_default='BORRADOR', comment='Document processing status'),
        sa.Column('mensaje_hacienda', sa.Text(), nullable=True, comment='Ministry response message'),
        sa.Column('codigo_error_hacienda', sa.String(length=10), nullable=True, comment='Ministry error code'),
        sa.Column('fecha_procesamiento', sa.DateTime(timezone=True), nullable=True, comment='Ministry processing timestamp'),
        sa.Column('fecha_aceptacion', sa.DateTime(timezone=True), nullable=True, comment='Ministry acceptance timestamp'),
        sa.Column('intentos_envio', sa.Integer(), nullable=False, server_default='0', comment='Number of submission attempts'),
        sa.Column('proximo_intento', sa.DateTime(timezone=True), nullable=True, comment='Next retry attempt timestamp'),
        sa.Column('enviado_por', sa.String(length=255), nullable=True, comment='User who sent the document'),
        sa.Column('observaciones', sa.String(length=500), nullable=True, comment='Additional observations'),
        sa.Column('referencia_interna', sa.String(length=100), nullable=True, comment='Internal reference number'),
        sa.Column('numero_orden_compra', sa.String(length=100), nullable=True, comment='Purchase order number'),
        sa.Column('hash_documento', sa.String(length=64), nullable=True, comment='Document content hash for integrity'),
        sa.Column('version_esquema', sa.String(length=10), nullable=False, server_default='4.4', comment='XSD schema version used'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(length=255), nullable=True, comment='User who created the document'),
        sa.Column('updated_by', sa.String(length=255), nullable=True, comment='User who last updated the document'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('clave'),
        sa.CheckConstraint('char_length(numero_consecutivo) = 20', name='ck_document_consecutivo_length'),
        sa.CheckConstraint('char_length(clave) = 50', name='ck_document_clave_length'),
        sa.CheckConstraint("numero_consecutivo ~ '^\\d{20}$'", name='ck_document_consecutivo_format'),
        sa.CheckConstraint("clave ~ '^\\d{50}$'", name='ck_document_clave_format'),
        sa.CheckConstraint('total_venta_neta >= 0', name='ck_document_venta_neta_positive'),
        sa.CheckConstraint('total_impuesto >= 0', name='ck_document_impuesto_positive'),
        sa.CheckConstraint('total_descuento >= 0', name='ck_document_descuento_positive'),
        sa.CheckConstraint('total_otros_cargos >= 0', name='ck_document_otros_cargos_positive'),
        sa.CheckConstraint('total_comprobante >= 0', name='ck_document_total_positive'),
        sa.CheckConstraint('intentos_envio >= 0', name='ck_document_intentos_positive'),
        sa.CheckConstraint('tipo_cambio > 0', name='ck_document_tipo_cambio_positive'),
        sa.CheckConstraint('plazo_credito IS NULL OR plazo_credito > 0', name='ck_document_plazo_credito_positive'),
        sa.CheckConstraint('emisor_provincia IS NULL OR (emisor_provincia >= 1 AND emisor_provincia <= 7)', name='ck_document_emisor_provincia_valid'),
        sa.CheckConstraint('receptor_provincia IS NULL OR (receptor_provincia >= 1 AND receptor_provincia <= 7)', name='ck_document_receptor_provincia_valid'),
        sa.CheckConstraint("(condicion_venta != 'OTROS') OR (condicion_venta_otros IS NOT NULL)", name='ck_document_condicion_venta_otros_required'),
        sa.CheckConstraint("(medio_pago != 'OTROS') OR (medio_pago_otros IS NOT NULL)", name='ck_document_medio_pago_otros_required'),
        sa.CheckConstraint("(condicion_venta != 'CREDITO') OR (plazo_credito IS NOT NULL)", name='ck_document_credito_plazo_required')
    )
    
    # Create document details table
    op.create_table('detalle_documentos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('documento_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Parent document ID'),
        sa.Column('numero_linea', sa.Integer(), nullable=False, comment='Line number (1-1000)'),
        sa.Column('codigo_cabys', sa.String(length=13), nullable=False, comment='13-digit CABYS code for product/service classification'),
        sa.Column('descripcion', sa.Text(), nullable=False, comment='Product/service description (3-200 chars)'),
        sa.Column('codigos_comerciales', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Array of commercial codes: [{tipo, codigo}, ...]'),
        sa.Column('cantidad', sa.Numeric(precision=16, scale=3), nullable=False, comment='Quantity (must be positive)'),
        sa.Column('unidad_medida', sa.String(length=10), nullable=False, comment='Official unit of measure code'),
        sa.Column('unidad_medida_comercial', sa.String(length=20), nullable=True, comment='Commercial unit description'),
        sa.Column('precio_unitario', sa.Numeric(precision=18, scale=5), nullable=False, comment='Unit price (can be 0 for free items)'),
        sa.Column('monto_total', sa.Numeric(precision=18, scale=5), nullable=False, comment='Line total (cantidad * precio_unitario)'),
        sa.Column('monto_descuento', sa.Numeric(precision=18, scale=5), nullable=False, server_default='0', comment='Discount amount'),
        sa.Column('naturaleza_descuento', sa.String(length=80), nullable=True, comment='Discount description/reason'),
        sa.Column('tipo_transaccion', sa.Enum('VENTA_NORMAL', 'AUTOCONSUMO_EXENTO', 'AUTOCONSUMO_GRAVADO', 'AUTOCONSUMO_SERVICIOS_EXENTO', 'AUTOCONSUMO_SERVICIOS_GRAVADO', 'CUOTA_MEMBRESIA', 'CUOTA_MEMBRESIA_EXENTA', 'BIENES_CAPITAL_EMISOR', 'BIENES_CAPITAL_RECEPTOR', 'BIENES_CAPITAL_AMBOS', 'AUTOCONSUMO_BIENES_CAPITAL_EXENTO', 'BIENES_CAPITAL_TERCEROS_EXENTO', 'SIN_CONTRAPRESTACION_TERCEROS', name='transactiontype'), nullable=True, comment='Special transaction type for tax treatment'),
        sa.Column('numero_vin_serie', sa.String(length=17), nullable=True, comment='VIN or serial number for vehicles (max 17 chars)'),
        sa.Column('registro_medicamento', sa.String(length=100), nullable=True, comment='Medicine registration number'),
        sa.Column('forma_farmaceutica', sa.String(length=3), nullable=True, comment='Pharmaceutical form code'),
        sa.Column('detalle_surtido', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Package components: [{codigo_cabys, cantidad, unidad_medida, descripcion}, ...]'),
        sa.Column('codigo_producto_interno', sa.String(length=50), nullable=True, comment='Internal product code'),
        sa.Column('marca', sa.String(length=100), nullable=True, comment='Product brand'),
        sa.Column('modelo', sa.String(length=100), nullable=True, comment='Product model'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['documento_id'], ['documentos.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('documento_id', 'numero_linea'),
        sa.CheckConstraint('numero_linea >= 1 AND numero_linea <= 1000', name='ck_detail_numero_linea_range'),
        sa.CheckConstraint('char_length(codigo_cabys) = 13', name='ck_detail_cabys_length'),
        sa.CheckConstraint("codigo_cabys ~ '^\\d{13}$'", name='ck_detail_cabys_format'),
        sa.CheckConstraint('char_length(descripcion) >= 3 AND char_length(descripcion) <= 200', name='ck_detail_descripcion_length'),
        sa.CheckConstraint('cantidad > 0', name='ck_detail_cantidad_positive'),
        sa.CheckConstraint('precio_unitario >= 0', name='ck_detail_precio_positive'),
        sa.CheckConstraint('monto_total >= 0', name='ck_detail_monto_total_positive'),
        sa.CheckConstraint('monto_descuento >= 0', name='ck_detail_descuento_positive'),
        sa.CheckConstraint('monto_descuento <= monto_total', name='ck_detail_descuento_not_exceed_total'),
        sa.CheckConstraint('numero_vin_serie IS NULL OR char_length(numero_vin_serie) <= 17', name='ck_detail_vin_length'),
        sa.CheckConstraint('registro_medicamento IS NULL OR char_length(registro_medicamento) <= 100', name='ck_detail_medicina_length'),
        sa.CheckConstraint('forma_farmaceutica IS NULL OR char_length(forma_farmaceutica) <= 3', name='ck_detail_forma_farmaceutica_length'),
        sa.CheckConstraint('numero_linea > 0', name='ck_detail_numero_linea_positive')
    )
    
    # Create document references table
    op.create_table('referencias_documentos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('documento_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Document that contains this reference'),
        sa.Column('tipo_documento_referencia', sa.Enum('FACTURA_ELECTRONICA', 'NOTA_DEBITO_ELECTRONICA', 'NOTA_CREDITO_ELECTRONICA', 'TIQUETE_ELECTRONICO', 'NOTA_DESPACHO', 'CONTRATO', 'PROCEDIMIENTO', 'COMPROBANTE_CONTINGENCIA', 'DEVOLUCION_MERCANCIA', 'RECHAZADO_MINISTERIO', 'RECHAZADO_RECEPTOR_SUSTITUTO', 'SUSTITUTO_FACTURA_EXPORTACION', 'FACTURACION_MES_ANTERIOR', 'COMPROBANTE_REGIMEN_ESPECIAL', 'SUSTITUTO_FACTURA_COMPRA', 'PROVEEDOR_NO_DOMICILIADO', 'NOTA_CREDITO_FACTURA_COMPRA', 'NOTA_DEBITO_FACTURA_COMPRA', 'OTROS', name='referencedocumenttype'), nullable=False, comment='Type of referenced document'),
        sa.Column('tipo_documento_otro', sa.String(length=100), nullable=True, comment='Other document type description (required when tipo = 99)'),
        sa.Column('numero_referencia', sa.String(length=50), nullable=True, comment='Document key or consecutive number of referenced document'),
        sa.Column('fecha_emision_referencia', sa.DateTime(timezone=True), nullable=False, comment='Emission date of referenced document'),
        sa.Column('codigo_referencia', sa.Enum('ANULA_DOCUMENTO_REFERENCIA', 'CORRIGE_TEXTO_DOCUMENTO_REFERENCIA', 'REFERENCIA_OTRO_DOCUMENTO', 'SUSTITUYE_COMPROBANTE_CONTINGENCIA', 'DEVOLUCION_MERCANCIA', 'SUSTITUYE_COMPROBANTE_ELECTRONICO', 'FACTURA_ENDOSADA', 'NOTA_CREDITO_FINANCIERA', 'NOTA_DEBITO_FINANCIERA', 'PROVEEDOR_NO_DOMICILIADO', 'NOTA_CREDITO_EXONERACION_POSTERIOR', 'OTROS', name='referencecode'), nullable=True, comment='Type of reference relationship'),
        sa.Column('codigo_referencia_otro', sa.String(length=100), nullable=True, comment='Other reference code description (required when codigo = 99)'),
        sa.Column('razon', sa.String(length=180), nullable=True, comment='Reason for the reference (corrections, cancellations, etc.)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['documento_id'], ['documentos.id'], ondelete='CASCADE'),
        sa.CheckConstraint("(tipo_documento_referencia != 'OTROS') OR (tipo_documento_otro IS NOT NULL)", name='ck_reference_tipo_otro_required'),
        sa.CheckConstraint("(codigo_referencia != 'OTROS') OR (codigo_referencia_otro IS NOT NULL)", name='ck_reference_codigo_otro_required'),
        sa.CheckConstraint('numero_referencia IS NULL OR char_length(numero_referencia) <= 50', name='ck_reference_numero_length'),
        sa.CheckConstraint('tipo_documento_otro IS NULL OR char_length(tipo_documento_otro) <= 100', name='ck_reference_tipo_otro_length'),
        sa.CheckConstraint('codigo_referencia_otro IS NULL OR char_length(codigo_referencia_otro) <= 100', name='ck_reference_codigo_otro_length'),
        sa.CheckConstraint('razon IS NULL OR char_length(razon) <= 180', name='ck_reference_razon_length')
    )
    
    # Create document taxes table
    op.create_table('impuestos_documentos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('detalle_documento_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Document detail line item'),
        sa.Column('codigo_impuesto', sa.Enum('IVA', 'SELECTIVO_CONSUMO', 'UNICO_COMBUSTIBLES', 'ESPECIFICO_BEBIDAS_ALCOHOLICAS', 'ESPECIFICO_BEBIDAS_SIN_ALCOHOL', 'PRODUCTOS_TABACO', 'IVA_CALCULO_ESPECIAL', 'IVA_BIENES_USADOS', 'ESPECIFICO_CEMENTO', 'OTROS', name='taxcode'), nullable=False, comment='Tax code: 01=IVA, 02=Selectivo, etc.'),
        sa.Column('codigo_impuesto_otro', sa.String(length=100), nullable=True, comment='Other tax code description (required when codigo = 99)'),
        sa.Column('codigo_tarifa_iva', sa.Enum('TARIFA_0_PERCENT', 'TARIFA_REDUCIDA_1_PERCENT', 'TARIFA_REDUCIDA_2_PERCENT', 'TARIFA_REDUCIDA_4_PERCENT', 'TRANSITORIO_0_PERCENT', 'TRANSITORIO_4_PERCENT', 'TRANSITORIO_8_PERCENT', 'TARIFA_GENERAL_13_PERCENT', 'TARIFA_REDUCIDA_0_5_PERCENT', 'TARIFA_EXENTA', 'TARIFA_0_SIN_CREDITO', name='ivatariffcode'), nullable=True, comment='IVA tariff code (01-11) - required for IVA taxes'),
        sa.Column('tarifa', sa.Numeric(precision=4, scale=2), nullable=True, comment='Tax rate percentage (0.00-99.99)'),
        sa.Column('factor_calculo_iva', sa.Numeric(precision=5, scale=4), nullable=True, comment='IVA calculation factor for used goods regime'),
        sa.Column('monto', sa.Numeric(precision=18, scale=5), nullable=False, comment='Tax amount'),
        sa.Column('cantidad_unidad_medida', sa.Numeric(precision=7, scale=2), nullable=True, comment='Quantity in unit of measure for specific taxes'),
        sa.Column('porcentaje', sa.Numeric(precision=4, scale=2), nullable=True, comment='Percentage for alcohol tax calculation'),
        sa.Column('proporcion', sa.Numeric(precision=5, scale=2), nullable=True, comment='Proportion for alcohol tax calculation'),
        sa.Column('volumen_unidad_consumo', sa.Numeric(precision=7, scale=2), nullable=True, comment='Volume per consumption unit for beverage tax'),
        sa.Column('impuesto_unidad', sa.Numeric(precision=18, scale=5), nullable=True, comment='Tax amount per unit for specific taxes'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['detalle_documento_id'], ['detalle_documentos.id'], ondelete='CASCADE'),
        sa.CheckConstraint("(codigo_impuesto != 'OTROS') OR (codigo_impuesto_otro IS NOT NULL)", name='ck_tax_codigo_otro_required'),
        sa.CheckConstraint("(codigo_impuesto != 'IVA') OR (codigo_tarifa_iva IS NOT NULL)", name='ck_tax_iva_tarifa_required'),
        sa.CheckConstraint('monto >= 0', name='ck_tax_monto_positive'),
        sa.CheckConstraint('tarifa IS NULL OR (tarifa >= 0 AND tarifa <= 99.99)', name='ck_tax_tarifa_range'),
        sa.CheckConstraint('factor_calculo_iva IS NULL OR (factor_calculo_iva >= 0 AND factor_calculo_iva <= 1)', name='ck_tax_factor_iva_range'),
        sa.CheckConstraint('cantidad_unidad_medida IS NULL OR cantidad_unidad_medida >= 0', name='ck_tax_cantidad_positive'),
        sa.CheckConstraint('porcentaje IS NULL OR (porcentaje >= 0 AND porcentaje <= 100)', name='ck_tax_porcentaje_range'),
        sa.CheckConstraint('proporcion IS NULL OR proporcion >= 0', name='ck_tax_proporcion_positive'),
        sa.CheckConstraint('volumen_unidad_consumo IS NULL OR volumen_unidad_consumo >= 0', name='ck_tax_volumen_positive'),
        sa.CheckConstraint('impuesto_unidad IS NULL OR impuesto_unidad >= 0', name='ck_tax_impuesto_unidad_positive'),
        sa.CheckConstraint('codigo_impuesto_otro IS NULL OR char_length(codigo_impuesto_otro) <= 100', name='ck_tax_codigo_otro_length')
    )
    
    # Create document exemptions table
    op.create_table('exoneraciones_documentos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('impuesto_documento_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Tax that is being exempted'),
        sa.Column('tipo_documento_exoneracion', sa.Enum('AUTORIZACION_DGT_COMPRAS', 'VENTAS_DIPLOMATICAS', 'AUTORIZACION_LEY_ESPECIAL', 'AUTORIZACION_GENERAL_LOCAL', 'SERVICIOS_INGENIERIA_TRANSITORIO', 'SERVICIOS_TURISTICOS_ICT', 'RECICLAJE_TRANSITORIO', 'ZONA_FRANCA', 'SERVICIOS_COMPLEMENTARIOS_EXPORTACION', 'CORPORACIONES_MUNICIPALES', 'AUTORIZACION_ESPECIFICA_LOCAL', 'OTROS', name='exemptiondocumenttype'), nullable=False, comment='Type of exemption document'),
        sa.Column('tipo_documento_otro', sa.String(length=100), nullable=True, comment='Other document type description (required when tipo = 99)'),
        sa.Column('numero_documento', sa.String(length=40), nullable=False, comment='Exemption document number'),
        sa.Column('articulo', sa.Integer(), nullable=True, comment='Article number in exemption document'),
        sa.Column('inciso', sa.Integer(), nullable=True, comment='Subsection number in exemption document'),
        sa.Column('nombre_institucion', sa.Enum('DIRECCION_GENERAL_TRIBUTACION', 'MINISTERIO_RELACIONES_EXTERIORES', 'TRIBUNAL_SUPREMO_ELECCIONES', 'CONTRALORIA_GENERAL_REPUBLICA', 'INSTITUTO_COSTARRICENSE_TURISMO', 'COMISION_NACIONAL_EMERGENCIAS', 'INSTITUTO_MIXTO_AYUDA_SOCIAL', 'CONSEJO_NACIONAL_REHABILITACION', 'PATRONATO_NACIONAL_INFANCIA', 'CRUZ_ROJA_COSTARRICENSE', 'JUNTA_PROTECCION_SOCIAL', 'CUALQUIER_INSTITUCION_PUBLICA', 'OTROS', name='exemptioninstitution'), nullable=False, comment='Institution that granted the exemption'),
        sa.Column('nombre_institucion_otros', sa.String(length=160), nullable=True, comment='Other institution name (required when institucion = 99)'),
        sa.Column('fecha_emision', sa.DateTime(timezone=True), nullable=False, comment='Exemption document emission date'),
        sa.Column('tarifa_exonerada', sa.Numeric(precision=4, scale=2), nullable=False, comment='Exempted tax rate percentage'),
        sa.Column('monto_exoneracion', sa.Numeric(precision=18, scale=5), nullable=False, comment='Exemption amount'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['impuesto_documento_id'], ['impuestos_documentos.id'], ondelete='CASCADE'),
        sa.CheckConstraint("(tipo_documento_exoneracion != 'OTROS') OR (tipo_documento_otro IS NOT NULL)", name='ck_exemption_tipo_otro_required'),
        sa.CheckConstraint("(nombre_institucion != 'OTROS') OR (nombre_institucion_otros IS NOT NULL)", name='ck_exemption_institucion_otros_required'),
        sa.CheckConstraint('char_length(numero_documento) >= 3 AND char_length(numero_documento) <= 40', name='ck_exemption_numero_length'),
        sa.CheckConstraint('articulo IS NULL OR (articulo > 0 AND articulo <= 999999)', name='ck_exemption_articulo_range'),
        sa.CheckConstraint('inciso IS NULL OR (inciso > 0 AND inciso <= 999999)', name='ck_exemption_inciso_range'),
        sa.CheckConstraint('tarifa_exonerada >= 0 AND tarifa_exonerada <= 99.99', name='ck_exemption_tarifa_range'),
        sa.CheckConstraint('monto_exoneracion >= 0', name='ck_exemption_monto_positive'),
        sa.CheckConstraint('tipo_documento_otro IS NULL OR char_length(tipo_documento_otro) <= 100', name='ck_exemption_tipo_otro_length'),
        sa.CheckConstraint('nombre_institucion_otros IS NULL OR char_length(nombre_institucion_otros) <= 160', name='ck_exemption_institucion_otros_length')
    )
    
    # Create document other charges table
    op.create_table('otros_cargos_documentos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('documento_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Document that contains this charge'),
        sa.Column('tipo_documento', sa.Enum('CONTRIBUCION_PARAFISCAL', 'TIMBRE_CRUZ_ROJA', 'TIMBRE_BOMBEROS', 'COBRO_TERCERO', 'GASTOS_EXPORTACION', 'IMPUESTO_SERVICIO_10_PERCENT', 'TIMBRES_COLEGIOS_PROFESIONALES', 'DEPOSITOS_GARANTIA', 'MULTAS_SANCIONES', 'INTERESES_MORATORIOS', 'OTROS', name='otherchargetype'), nullable=False, comment='Type of other charge'),
        sa.Column('tipo_documento_otros', sa.String(length=100), nullable=True, comment='Other charge type description (required when tipo = 99)'),
        sa.Column('tercero_tipo_identificacion', sa.Enum('CEDULA_FISICA', 'CEDULA_JURIDICA', 'DIMEX', 'NITE', 'EXTRANJERO_NO_DOMICILIADO', 'NO_CONTRIBUYENTE', name='identificationtype'), nullable=True, comment='Third party identification type'),
        sa.Column('tercero_numero_identificacion', sa.String(length=20), nullable=True, comment='Third party identification number'),
        sa.Column('tercero_nombre', sa.String(length=100), nullable=True, comment='Third party name'),
        sa.Column('detalle', sa.String(length=160), nullable=False, comment='Charge description/details'),
        sa.Column('porcentaje', sa.Numeric(precision=9, scale=5), nullable=True, comment='Percentage for calculation (when applicable)'),
        sa.Column('monto_cargo', sa.Numeric(precision=18, scale=5), nullable=False, comment='Charge amount'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['documento_id'], ['documentos.id'], ondelete='CASCADE'),
        sa.CheckConstraint("(tipo_documento != 'OTROS') OR (tipo_documento_otros IS NOT NULL)", name='ck_other_charge_tipo_otros_required'),
        sa.CheckConstraint('char_length(detalle) >= 1 AND char_length(detalle) <= 160', name='ck_other_charge_detalle_length'),
        sa.CheckConstraint('monto_cargo >= 0', name='ck_other_charge_monto_positive'),
        sa.CheckConstraint('porcentaje IS NULL OR (porcentaje >= 0 AND porcentaje <= 100)', name='ck_other_charge_porcentaje_range'),
        sa.CheckConstraint('tipo_documento_otros IS NULL OR char_length(tipo_documento_otros) <= 100', name='ck_other_charge_tipo_otros_length'),
        sa.CheckConstraint('tercero_nombre IS NULL OR char_length(tercero_nombre) <= 100', name='ck_other_charge_tercero_nombre_length'),
        sa.CheckConstraint('tercero_numero_identificacion IS NULL OR char_length(tercero_numero_identificacion) <= 20', name='ck_other_charge_tercero_id_length'),
        sa.CheckConstraint('(tercero_tipo_identificacion IS NULL AND tercero_numero_identificacion IS NULL AND tercero_nombre IS NULL) OR (tercero_tipo_identificacion IS NOT NULL AND tercero_numero_identificacion IS NOT NULL)', name='ck_other_charge_tercero_consistency')
    )
    
    # Create receptor messages table
    op.create_table('mensajes_receptor',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('documento_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Related document (optional)'),
        sa.Column('clave_documento', sa.String(length=50), nullable=False, comment='Original document key'),
        sa.Column('cedula_emisor', sa.String(length=12), nullable=False, comment='Issuer identification'),
        sa.Column('fecha_emision', sa.DateTime(timezone=True), nullable=False, comment='Original document emission date'),
        sa.Column('mensaje', sa.Integer(), nullable=False, comment='Message type: 1=Accepted, 2=Partial, 3=Rejected'),
        sa.Column('detalle_mensaje', sa.String(length=160), nullable=True, comment='Optional rejection details'),
        sa.Column('monto_total_impuesto', sa.Numeric(precision=18, scale=5), nullable=True, comment='Total tax amount for validation'),
        sa.Column('codigo_actividad', sa.String(length=6), nullable=True, comment='Economic activity code'),
        sa.Column('condicion_impuesto', sa.String(length=2), nullable=True, comment='IVA condition (01-05)'),
        sa.Column('receptor_identificacion_tipo', sa.Enum('CEDULA_FISICA', 'CEDULA_JURIDICA', 'DIMEX', 'NITE', 'EXTRANJERO_NO_DOMICILIADO', 'NO_CONTRIBUYENTE', name='identificationtype'), nullable=False, comment='Receptor identification type'),
        sa.Column('receptor_identificacion_numero', sa.String(length=20), nullable=False, comment='Receptor identification number'),
        sa.Column('receptor_nombre', sa.String(length=100), nullable=False, comment='Receptor name'),
        sa.Column('xml_mensaje', sa.Text(), nullable=True, comment='Generated XML message'),
        sa.Column('xml_firmado', sa.Text(), nullable=True, comment='Signed XML message'),
        sa.Column('estado', sa.String(length=20), nullable=False, server_default='borrador', comment='Message status'),
        sa.Column('enviado', sa.Boolean(), nullable=False, server_default='false', comment='Sent to Ministry flag'),
        sa.Column('fecha_envio', sa.DateTime(timezone=True), nullable=True, comment='Send timestamp'),
        sa.Column('intentos_envio', sa.Integer(), nullable=False, server_default='0', comment='Send attempts count'),
        sa.Column('estado_hacienda', sa.String(length=20), nullable=True, comment='Ministry response status'),
        sa.Column('ultimo_error', sa.Text(), nullable=True, comment='Last error message'),
        sa.Column('fecha_ultimo_error', sa.DateTime(timezone=True), nullable=True, comment='Last error timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['documento_id'], ['documentos.id'], ondelete='SET NULL'),
        sa.CheckConstraint('mensaje >= 1 AND mensaje <= 3', name='ck_receptor_mensaje_range'),
        sa.CheckConstraint("clave_documento ~ '^\\d{50}$'", name='ck_receptor_clave_format'),
        sa.CheckConstraint("cedula_emisor ~ '^\\d{9,12}$'", name='ck_receptor_cedula_format'),
        sa.CheckConstraint('detalle_mensaje IS NULL OR char_length(detalle_mensaje) <= 160', name='ck_receptor_detalle_length'),
        sa.CheckConstraint('monto_total_impuesto IS NULL OR monto_total_impuesto >= 0', name='ck_receptor_monto_positive'),
        sa.CheckConstraint('intentos_envio >= 0', name='ck_receptor_intentos_positive')
    )


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('mensajes_receptor')
    op.drop_table('otros_cargos_documentos')
    op.drop_table('exoneraciones_documentos')
    op.drop_table('impuestos_documentos')
    op.drop_table('referencias_documentos')
    op.drop_table('detalle_documentos')
    op.drop_table('documentos')
    op.drop_table('unidades_medida')
    op.drop_table('ubicaciones_cr')
    op.drop_table('codigos_cabys')
    op.drop_table('tenants')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS otherchargetype')
    op.execute('DROP TYPE IF EXISTS exemptioninstitution')
    op.execute('DROP TYPE IF EXISTS exemptiondocumenttype')
    op.execute('DROP TYPE IF EXISTS ivatariffcode')
    op.execute('DROP TYPE IF EXISTS taxcode')
    op.execute('DROP TYPE IF EXISTS referencecode')
    op.execute('DROP TYPE IF EXISTS referencedocumenttype')
    op.execute('DROP TYPE IF EXISTS transactiontype')
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS paymentmethod')
    op.execute('DROP TYPE IF EXISTS salecondition')
    op.execute('DROP TYPE IF EXISTS identificationtype')
    op.execute('DROP TYPE IF EXISTS documenttype')