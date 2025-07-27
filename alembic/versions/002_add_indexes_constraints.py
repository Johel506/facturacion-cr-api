"""add_indexes_constraints

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add comprehensive performance indexes and database constraints"""
    
    # ========================================
    # TENANTS TABLE INDEXES
    # ========================================
    
    # Primary performance indexes for tenants
    op.create_index('idx_tenants_api_key_lookup', 'tenants', ['api_key'])
    op.create_index('idx_tenants_cedula_lookup', 'tenants', ['cedula_juridica'])
    op.create_index('idx_tenants_active_status', 'tenants', ['activo'])
    op.create_index('idx_tenants_plan_type', 'tenants', ['plan'])
    op.create_index('idx_tenants_certificate_expiry', 'tenants', ['certificado_expires_at'])
    op.create_index('idx_tenants_monthly_reset', 'tenants', ['ultimo_reset_contador'])
    
    # Composite indexes for common tenant queries
    op.create_index('idx_tenants_active_plan_composite', 'tenants', ['activo', 'plan'])
    op.create_index('idx_tenants_plan_limits_composite', 'tenants', ['plan', 'limite_facturas_mes'])
    op.create_index('idx_tenants_usage_tracking', 'tenants', ['activo', 'facturas_usadas_mes', 'limite_facturas_mes'])
    op.create_index('idx_tenants_certificate_status', 'tenants', ['activo', 'certificado_expires_at'])
    
    # ========================================
    # CABYS CODES TABLE INDEXES
    # ========================================
    
    # Primary CABYS lookup indexes
    op.create_index('idx_cabys_codigo_lookup', 'codigos_cabys', ['codigo'])
    op.create_index('idx_cabys_active_status', 'codigos_cabys', ['activo'])
    op.create_index('idx_cabys_category_level1', 'codigos_cabys', ['categoria_nivel_1'])
    op.create_index('idx_cabys_category_level2', 'codigos_cabys', ['categoria_nivel_2'])
    op.create_index('idx_cabys_iva_rate', 'codigos_cabys', ['impuesto_iva'])
    op.create_index('idx_cabys_iva_exempt', 'codigos_cabys', ['exento_iva'])
    op.create_index('idx_cabys_usage_count', 'codigos_cabys', ['veces_usado'])
    op.create_index('idx_cabys_last_used', 'codigos_cabys', ['ultimo_uso'])
    
    # Full-text search index for CABYS descriptions (PostgreSQL specific)
    op.execute("""
        CREATE INDEX idx_cabys_descripcion_fulltext 
        ON codigos_cabys 
        USING gin(to_tsvector('spanish', descripcion))
    """)
    
    # Composite indexes for CABYS filtering and search
    op.create_index('idx_cabys_active_category', 'codigos_cabys', ['activo', 'categoria_nivel_1'])
    op.create_index('idx_cabys_active_iva', 'codigos_cabys', ['activo', 'impuesto_iva'])
    op.create_index('idx_cabys_active_exempt', 'codigos_cabys', ['activo', 'exento_iva'])
    op.create_index('idx_cabys_popularity', 'codigos_cabys', ['activo', 'veces_usado'])
    op.create_index('idx_cabys_validity_period', 'codigos_cabys', ['fecha_vigencia_desde', 'fecha_vigencia_hasta'])
    
    # ========================================
    # GEOGRAPHIC LOCATIONS TABLE INDEXES
    # ========================================
    
    # Geographic hierarchy indexes
    op.create_index('idx_ubicacion_provincia_lookup', 'ubicaciones_cr', ['provincia'])
    op.create_index('idx_ubicacion_canton_lookup', 'ubicaciones_cr', ['provincia', 'canton'])
    op.create_index('idx_ubicacion_distrito_lookup', 'ubicaciones_cr', ['provincia', 'canton', 'distrito'])
    op.create_index('idx_ubicacion_active_status', 'ubicaciones_cr', ['activo'])
    op.create_index('idx_ubicacion_inec_code', 'ubicaciones_cr', ['codigo_inec'])
    op.create_index('idx_ubicacion_postal_code', 'ubicaciones_cr', ['codigo_postal'])
    
    # Name-based search indexes
    op.create_index('idx_ubicacion_provincia_name', 'ubicaciones_cr', ['nombre_provincia'])
    op.create_index('idx_ubicacion_canton_name', 'ubicaciones_cr', ['nombre_canton'])
    op.create_index('idx_ubicacion_distrito_name', 'ubicaciones_cr', ['nombre_distrito'])
    
    # Full-text search for location names
    op.execute("""
        CREATE INDEX idx_ubicacion_nombres_fulltext 
        ON ubicaciones_cr 
        USING gin(to_tsvector('spanish', nombre_provincia || ' ' || nombre_canton || ' ' || nombre_distrito))
    """)
    
    # Composite indexes for location queries
    op.create_index('idx_ubicacion_active_provincia', 'ubicaciones_cr', ['activo', 'provincia'])
    op.create_index('idx_ubicacion_active_canton', 'ubicaciones_cr', ['activo', 'provincia', 'canton'])
    op.create_index('idx_ubicacion_capitals', 'ubicaciones_cr', ['cabecera_provincia', 'cabecera_canton'])
    
    # ========================================
    # UNITS OF MEASURE TABLE INDEXES
    # ========================================
    
    # Primary unit lookup indexes
    op.create_index('idx_unidad_codigo_lookup', 'unidades_medida', ['codigo'])
    op.create_index('idx_unidad_active_status', 'unidades_medida', ['activo'])
    op.create_index('idx_unidad_category', 'unidades_medida', ['categoria'])
    op.create_index('idx_unidad_measurement_type', 'unidades_medida', ['tipo_medida'])
    op.create_index('idx_unidad_common_usage', 'unidades_medida', ['uso_comun'])
    op.create_index('idx_unidad_product_usage', 'unidades_medida', ['uso_productos'])
    op.create_index('idx_unidad_service_usage', 'unidades_medida', ['uso_servicios'])
    op.create_index('idx_unidad_usage_count', 'unidades_medida', ['veces_usado'])
    op.create_index('idx_unidad_last_used', 'unidades_medida', ['ultimo_uso'])
    
    # Full-text search for unit descriptions
    op.execute("""
        CREATE INDEX idx_unidad_descripcion_fulltext 
        ON unidades_medida 
        USING gin(to_tsvector('spanish', descripcion))
    """)
    
    # Composite indexes for unit filtering
    op.create_index('idx_unidad_active_category', 'unidades_medida', ['activo', 'categoria'])
    op.create_index('idx_unidad_active_products', 'unidades_medida', ['activo', 'uso_productos'])
    op.create_index('idx_unidad_active_services', 'unidades_medida', ['activo', 'uso_servicios'])
    op.create_index('idx_unidad_active_common', 'unidades_medida', ['activo', 'uso_comun'])
    op.create_index('idx_unidad_popularity', 'unidades_medida', ['activo', 'veces_usado'])
    op.create_index('idx_unidad_validity_period', 'unidades_medida', ['fecha_vigencia_desde', 'fecha_vigencia_hasta'])
    
    # ========================================
    # DOCUMENTS TABLE INDEXES
    # ========================================
    
    # Primary document lookup indexes
    op.create_index('idx_documentos_tenant_isolation', 'documentos', ['tenant_id'])
    op.create_index('idx_documentos_clave_lookup', 'documentos', ['clave'])
    op.create_index('idx_documentos_consecutivo_lookup', 'documentos', ['numero_consecutivo'])
    op.create_index('idx_documentos_document_type', 'documentos', ['tipo_documento'])
    op.create_index('idx_documentos_status', 'documentos', ['estado'])
    op.create_index('idx_documentos_emission_date', 'documentos', ['fecha_emision'])
    op.create_index('idx_documentos_processing_date', 'documentos', ['fecha_procesamiento'])
    op.create_index('idx_documentos_acceptance_date', 'documentos', ['fecha_aceptacion'])
    
    # Issuer and receiver indexes
    op.create_index('idx_documentos_emisor_id', 'documentos', ['emisor_numero_identificacion'])
    op.create_index('idx_documentos_receptor_id', 'documentos', ['receptor_numero_identificacion'])
    
    # Ministry processing indexes
    op.create_index('idx_documentos_retry_attempts', 'documentos', ['intentos_envio'])
    op.create_index('idx_documentos_next_retry', 'documentos', ['proximo_intento'])
    op.create_index('idx_documentos_error_code', 'documentos', ['codigo_error_hacienda'])
    
    # Composite indexes for common document queries
    op.create_index('idx_documentos_tenant_type', 'documentos', ['tenant_id', 'tipo_documento'])
    op.create_index('idx_documentos_tenant_status', 'documentos', ['tenant_id', 'estado'])
    op.create_index('idx_documentos_tenant_date', 'documentos', ['tenant_id', 'fecha_emision'])
    op.create_index('idx_documentos_type_status', 'documentos', ['tipo_documento', 'estado'])
    op.create_index('idx_documentos_status_date', 'documentos', ['estado', 'fecha_emision'])
    op.create_index('idx_documentos_emisor_date', 'documentos', ['emisor_numero_identificacion', 'fecha_emision'])
    op.create_index('idx_documentos_receptor_date', 'documentos', ['receptor_numero_identificacion', 'fecha_emision'])
    
    # Ministry processing workflow indexes
    op.create_index('idx_documentos_pending_submission', 'documentos', ['estado', 'proximo_intento'])
    op.create_index('idx_documentos_retry_workflow', 'documentos', ['intentos_envio', 'estado'])
    op.create_index('idx_documentos_processing_workflow', 'documentos', ['estado', 'fecha_procesamiento'])
    
    # Document totals and currency indexes
    op.create_index('idx_documentos_currency', 'documentos', ['codigo_moneda'])
    op.create_index('idx_documentos_total_amount', 'documentos', ['total_comprobante'])
    op.create_index('idx_documentos_tenant_totals', 'documentos', ['tenant_id', 'total_comprobante'])
    
    # ========================================
    # DOCUMENT DETAILS TABLE INDEXES
    # ========================================
    
    # Primary detail lookup indexes
    op.create_index('idx_detalle_documento_relation', 'detalle_documentos', ['documento_id'])
    op.create_index('idx_detalle_line_number', 'detalle_documentos', ['documento_id', 'numero_linea'])
    op.create_index('idx_detalle_cabys_lookup', 'detalle_documentos', ['codigo_cabys'])
    
    # Product identification indexes
    op.create_index('idx_detalle_internal_code', 'detalle_documentos', ['codigo_producto_interno'])
    op.create_index('idx_detalle_vin_number', 'detalle_documentos', ['numero_vin_serie'])
    op.create_index('idx_detalle_medicine_registration', 'detalle_documentos', ['registro_medicamento'])
    op.create_index('idx_detalle_brand', 'detalle_documentos', ['marca'])
    op.create_index('idx_detalle_model', 'detalle_documentos', ['modelo'])
    
    # Full-text search for product descriptions
    op.execute("""
        CREATE INDEX idx_detalle_descripcion_fulltext 
        ON detalle_documentos 
        USING gin(to_tsvector('spanish', descripcion))
    """)
    
    # Composite indexes for detail queries
    op.create_index('idx_detalle_cabys_description', 'detalle_documentos', ['codigo_cabys', 'descripcion'])
    op.create_index('idx_detalle_document_cabys', 'detalle_documentos', ['documento_id', 'codigo_cabys'])
    
    # ========================================
    # DOCUMENT REFERENCES TABLE INDEXES
    # ========================================
    
    # Primary reference lookup indexes
    op.create_index('idx_referencias_documento_relation', 'referencias_documentos', ['documento_id'])
    op.create_index('idx_referencias_reference_number', 'referencias_documentos', ['numero_referencia'])
    op.create_index('idx_referencias_document_type', 'referencias_documentos', ['tipo_documento_referencia'])
    op.create_index('idx_referencias_reference_code', 'referencias_documentos', ['codigo_referencia'])
    op.create_index('idx_referencias_emission_date', 'referencias_documentos', ['fecha_emision_referencia'])
    
    # Composite indexes for reference queries
    op.create_index('idx_referencias_document_type_combo', 'referencias_documentos', ['documento_id', 'tipo_documento_referencia'])
    op.create_index('idx_referencias_number_date', 'referencias_documentos', ['numero_referencia', 'fecha_emision_referencia'])
    op.create_index('idx_referencias_type_code', 'referencias_documentos', ['tipo_documento_referencia', 'codigo_referencia'])
    
    # ========================================
    # DOCUMENT TAXES TABLE INDEXES
    # ========================================
    
    # Primary tax lookup indexes
    op.create_index('idx_impuestos_detail_relation', 'impuestos_documentos', ['detalle_documento_id'])
    op.create_index('idx_impuestos_tax_code', 'impuestos_documentos', ['codigo_impuesto'])
    op.create_index('idx_impuestos_iva_tariff', 'impuestos_documentos', ['codigo_tarifa_iva'])
    op.create_index('idx_impuestos_tax_amount', 'impuestos_documentos', ['monto'])
    
    # Composite indexes for tax queries
    op.create_index('idx_impuestos_detail_tax_code', 'impuestos_documentos', ['detalle_documento_id', 'codigo_impuesto'])
    op.create_index('idx_impuestos_tax_tariff_combo', 'impuestos_documentos', ['codigo_impuesto', 'codigo_tarifa_iva'])
    
    # ========================================
    # DOCUMENT EXEMPTIONS TABLE INDEXES
    # ========================================
    
    # Primary exemption lookup indexes
    op.create_index('idx_exoneraciones_tax_relation', 'exoneraciones_documentos', ['impuesto_documento_id'])
    op.create_index('idx_exoneraciones_document_number', 'exoneraciones_documentos', ['numero_documento'])
    op.create_index('idx_exoneraciones_document_type', 'exoneraciones_documentos', ['tipo_documento_exoneracion'])
    op.create_index('idx_exoneraciones_institution', 'exoneraciones_documentos', ['nombre_institucion'])
    op.create_index('idx_exoneraciones_emission_date', 'exoneraciones_documentos', ['fecha_emision'])
    op.create_index('idx_exoneraciones_exemption_amount', 'exoneraciones_documentos', ['monto_exoneracion'])
    
    # Composite indexes for exemption queries
    op.create_index('idx_exoneraciones_tax_type', 'exoneraciones_documentos', ['impuesto_documento_id', 'tipo_documento_exoneracion'])
    op.create_index('idx_exoneraciones_number_date', 'exoneraciones_documentos', ['numero_documento', 'fecha_emision'])
    op.create_index('idx_exoneraciones_institution_date', 'exoneraciones_documentos', ['nombre_institucion', 'fecha_emision'])
    
    # ========================================
    # DOCUMENT OTHER CHARGES TABLE INDEXES
    # ========================================
    
    # Primary other charges lookup indexes
    op.create_index('idx_otros_cargos_document_relation', 'otros_cargos_documentos', ['documento_id'])
    op.create_index('idx_otros_cargos_charge_type', 'otros_cargos_documentos', ['tipo_documento'])
    op.create_index('idx_otros_cargos_third_party_id', 'otros_cargos_documentos', ['tercero_numero_identificacion'])
    op.create_index('idx_otros_cargos_charge_amount', 'otros_cargos_documentos', ['monto_cargo'])
    
    # Composite indexes for other charges queries
    op.create_index('idx_otros_cargos_document_type', 'otros_cargos_documentos', ['documento_id', 'tipo_documento'])
    op.create_index('idx_otros_cargos_third_party_combo', 'otros_cargos_documentos', ['tercero_tipo_identificacion', 'tercero_numero_identificacion'])
    
    # ========================================
    # RECEPTOR MESSAGES TABLE INDEXES
    # ========================================
    
    # Primary receptor message lookup indexes
    op.create_index('idx_receptor_document_relation', 'mensajes_receptor', ['documento_id'])
    op.create_index('idx_receptor_document_key', 'mensajes_receptor', ['clave_documento'])
    op.create_index('idx_receptor_issuer_id', 'mensajes_receptor', ['cedula_emisor'])
    op.create_index('idx_receptor_message_type', 'mensajes_receptor', ['mensaje'])
    op.create_index('idx_receptor_message_status', 'mensajes_receptor', ['estado'])
    op.create_index('idx_receptor_sent_status', 'mensajes_receptor', ['enviado'])
    op.create_index('idx_receptor_emission_date', 'mensajes_receptor', ['fecha_emision'])
    op.create_index('idx_receptor_send_date', 'mensajes_receptor', ['fecha_envio'])
    op.create_index('idx_receptor_send_attempts', 'mensajes_receptor', ['intentos_envio'])
    op.create_index('idx_receptor_ministry_status', 'mensajes_receptor', ['estado_hacienda'])
    op.create_index('idx_receptor_activity_code', 'mensajes_receptor', ['codigo_actividad'])
    op.create_index('idx_receptor_identification', 'mensajes_receptor', ['receptor_identificacion_numero'])
    op.create_index('idx_receptor_name', 'mensajes_receptor', ['receptor_nombre'])
    
    # Composite indexes for receptor message queries
    op.create_index('idx_receptor_document_message', 'mensajes_receptor', ['documento_id', 'mensaje'])
    op.create_index('idx_receptor_issuer_date', 'mensajes_receptor', ['cedula_emisor', 'fecha_emision'])
    op.create_index('idx_receptor_message_status_combo', 'mensajes_receptor', ['mensaje', 'estado'])
    op.create_index('idx_receptor_status_sent', 'mensajes_receptor', ['estado', 'enviado'])
    op.create_index('idx_receptor_pending_messages', 'mensajes_receptor', ['estado', 'enviado', 'intentos_envio'])
    op.create_index('idx_receptor_error_tracking', 'mensajes_receptor', ['estado', 'ultimo_error', 'fecha_ultimo_error'])
    
    # ========================================
    # ADDITIONAL PERFORMANCE CONSTRAINTS
    # ========================================
    
    # Add partial indexes for common filtered queries
    
    # Active tenants only
    op.execute("""
        CREATE INDEX idx_tenants_active_only 
        ON tenants (id, plan, limite_facturas_mes) 
        WHERE activo = true
    """)
    
    # Active CABYS codes only
    op.execute("""
        CREATE INDEX idx_cabys_active_only 
        ON codigos_cabys (codigo, descripcion, impuesto_iva) 
        WHERE activo = true
    """)
    
    # Active geographic locations only
    op.execute("""
        CREATE INDEX idx_ubicacion_active_only 
        ON ubicaciones_cr (provincia, canton, distrito, nombre_provincia, nombre_canton, nombre_distrito) 
        WHERE activo = true
    """)
    
    # Active units of measure only
    op.execute("""
        CREATE INDEX idx_unidad_active_only 
        ON unidades_medida (codigo, descripcion, categoria) 
        WHERE activo = true
    """)
    
    # Documents pending Ministry submission
    op.execute("""
        CREATE INDEX idx_documentos_pending_ministry 
        ON documentos (tenant_id, fecha_emision, intentos_envio) 
        WHERE estado IN ('BORRADOR', 'ERROR') AND intentos_envio < 3
    """)
    
    # Documents requiring retry
    op.execute("""
        CREATE INDEX idx_documentos_retry_queue 
        ON documentos (proximo_intento, intentos_envio) 
        WHERE estado = 'ERROR' AND proximo_intento IS NOT NULL AND proximo_intento <= NOW()
    """)
    
    # Receptor messages pending send
    op.execute("""
        CREATE INDEX idx_receptor_pending_send 
        ON mensajes_receptor (created_at, intentos_envio) 
        WHERE enviado = false AND intentos_envio < 3
    """)


def downgrade() -> None:
    """Remove performance indexes and constraints"""
    
    # Drop partial indexes
    op.drop_index('idx_receptor_pending_send', 'mensajes_receptor')
    op.drop_index('idx_documentos_retry_queue', 'documentos')
    op.drop_index('idx_documentos_pending_ministry', 'documentos')
    op.drop_index('idx_unidad_active_only', 'unidades_medida')
    op.drop_index('idx_ubicacion_active_only', 'ubicaciones_cr')
    op.drop_index('idx_cabys_active_only', 'codigos_cabys')
    op.drop_index('idx_tenants_active_only', 'tenants')
    
    # Drop receptor messages indexes
    op.drop_index('idx_receptor_error_tracking', 'mensajes_receptor')
    op.drop_index('idx_receptor_pending_messages', 'mensajes_receptor')
    op.drop_index('idx_receptor_status_sent', 'mensajes_receptor')
    op.drop_index('idx_receptor_message_status_combo', 'mensajes_receptor')
    op.drop_index('idx_receptor_issuer_date', 'mensajes_receptor')
    op.drop_index('idx_receptor_document_message', 'mensajes_receptor')
    op.drop_index('idx_receptor_name', 'mensajes_receptor')
    op.drop_index('idx_receptor_identification', 'mensajes_receptor')
    op.drop_index('idx_receptor_activity_code', 'mensajes_receptor')
    op.drop_index('idx_receptor_ministry_status', 'mensajes_receptor')
    op.drop_index('idx_receptor_send_attempts', 'mensajes_receptor')
    op.drop_index('idx_receptor_send_date', 'mensajes_receptor')
    op.drop_index('idx_receptor_emission_date', 'mensajes_receptor')
    op.drop_index('idx_receptor_sent_status', 'mensajes_receptor')
    op.drop_index('idx_receptor_message_status', 'mensajes_receptor')
    op.drop_index('idx_receptor_message_type', 'mensajes_receptor')
    op.drop_index('idx_receptor_issuer_id', 'mensajes_receptor')
    op.drop_index('idx_receptor_document_key', 'mensajes_receptor')
    op.drop_index('idx_receptor_document_relation', 'mensajes_receptor')
    
    # Drop other charges indexes
    op.drop_index('idx_otros_cargos_third_party_combo', 'otros_cargos_documentos')
    op.drop_index('idx_otros_cargos_document_type', 'otros_cargos_documentos')
    op.drop_index('idx_otros_cargos_charge_amount', 'otros_cargos_documentos')
    op.drop_index('idx_otros_cargos_third_party_id', 'otros_cargos_documentos')
    op.drop_index('idx_otros_cargos_charge_type', 'otros_cargos_documentos')
    op.drop_index('idx_otros_cargos_document_relation', 'otros_cargos_documentos')
    
    # Drop exemptions indexes
    op.drop_index('idx_exoneraciones_institution_date', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_number_date', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_tax_type', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_exemption_amount', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_emission_date', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_institution', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_document_type', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_document_number', 'exoneraciones_documentos')
    op.drop_index('idx_exoneraciones_tax_relation', 'exoneraciones_documentos')
    
    # Drop taxes indexes
    op.drop_index('idx_impuestos_tax_tariff_combo', 'impuestos_documentos')
    op.drop_index('idx_impuestos_detail_tax_code', 'impuestos_documentos')
    op.drop_index('idx_impuestos_tax_amount', 'impuestos_documentos')
    op.drop_index('idx_impuestos_iva_tariff', 'impuestos_documentos')
    op.drop_index('idx_impuestos_tax_code', 'impuestos_documentos')
    op.drop_index('idx_impuestos_detail_relation', 'impuestos_documentos')
    
    # Drop references indexes
    op.drop_index('idx_referencias_type_code', 'referencias_documentos')
    op.drop_index('idx_referencias_number_date', 'referencias_documentos')
    op.drop_index('idx_referencias_document_type_combo', 'referencias_documentos')
    op.drop_index('idx_referencias_emission_date', 'referencias_documentos')
    op.drop_index('idx_referencias_reference_code', 'referencias_documentos')
    op.drop_index('idx_referencias_document_type', 'referencias_documentos')
    op.drop_index('idx_referencias_reference_number', 'referencias_documentos')
    op.drop_index('idx_referencias_documento_relation', 'referencias_documentos')
    
    # Drop detail indexes
    op.drop_index('idx_detalle_document_cabys', 'detalle_documentos')
    op.drop_index('idx_detalle_cabys_description', 'detalle_documentos')
    op.drop_index('idx_detalle_descripcion_fulltext', 'detalle_documentos')
    op.drop_index('idx_detalle_model', 'detalle_documentos')
    op.drop_index('idx_detalle_brand', 'detalle_documentos')
    op.drop_index('idx_detalle_medicine_registration', 'detalle_documentos')
    op.drop_index('idx_detalle_vin_number', 'detalle_documentos')
    op.drop_index('idx_detalle_internal_code', 'detalle_documentos')
    op.drop_index('idx_detalle_cabys_lookup', 'detalle_documentos')
    op.drop_index('idx_detalle_line_number', 'detalle_documentos')
    op.drop_index('idx_detalle_documento_relation', 'detalle_documentos')
    
    # Drop documents indexes
    op.drop_index('idx_documentos_tenant_totals', 'documentos')
    op.drop_index('idx_documentos_total_amount', 'documentos')
    op.drop_index('idx_documentos_currency', 'documentos')
    op.drop_index('idx_documentos_processing_workflow', 'documentos')
    op.drop_index('idx_documentos_retry_workflow', 'documentos')
    op.drop_index('idx_documentos_pending_submission', 'documentos')
    op.drop_index('idx_documentos_receptor_date', 'documentos')
    op.drop_index('idx_documentos_emisor_date', 'documentos')
    op.drop_index('idx_documentos_status_date', 'documentos')
    op.drop_index('idx_documentos_type_status', 'documentos')
    op.drop_index('idx_documentos_tenant_date', 'documentos')
    op.drop_index('idx_documentos_tenant_status', 'documentos')
    op.drop_index('idx_documentos_tenant_type', 'documentos')
    op.drop_index('idx_documentos_error_code', 'documentos')
    op.drop_index('idx_documentos_next_retry', 'documentos')
    op.drop_index('idx_documentos_retry_attempts', 'documentos')
    op.drop_index('idx_documentos_receptor_id', 'documentos')
    op.drop_index('idx_documentos_emisor_id', 'documentos')
    op.drop_index('idx_documentos_acceptance_date', 'documentos')
    op.drop_index('idx_documentos_processing_date', 'documentos')
    op.drop_index('idx_documentos_emission_date', 'documentos')
    op.drop_index('idx_documentos_status', 'documentos')
    op.drop_index('idx_documentos_document_type', 'documentos')
    op.drop_index('idx_documentos_consecutivo_lookup', 'documentos')
    op.drop_index('idx_documentos_clave_lookup', 'documentos')
    op.drop_index('idx_documentos_tenant_isolation', 'documentos')
    
    # Drop units indexes
    op.drop_index('idx_unidad_validity_period', 'unidades_medida')
    op.drop_index('idx_unidad_popularity', 'unidades_medida')
    op.drop_index('idx_unidad_active_common', 'unidades_medida')
    op.drop_index('idx_unidad_active_services', 'unidades_medida')
    op.drop_index('idx_unidad_active_products', 'unidades_medida')
    op.drop_index('idx_unidad_active_category', 'unidades_medida')
    op.drop_index('idx_unidad_descripcion_fulltext', 'unidades_medida')
    op.drop_index('idx_unidad_last_used', 'unidades_medida')
    op.drop_index('idx_unidad_usage_count', 'unidades_medida')
    op.drop_index('idx_unidad_service_usage', 'unidades_medida')
    op.drop_index('idx_unidad_product_usage', 'unidades_medida')
    op.drop_index('idx_unidad_common_usage', 'unidades_medida')
    op.drop_index('idx_unidad_measurement_type', 'unidades_medida')
    op.drop_index('idx_unidad_category', 'unidades_medida')
    op.drop_index('idx_unidad_active_status', 'unidades_medida')
    op.drop_index('idx_unidad_codigo_lookup', 'unidades_medida')
    
    # Drop locations indexes
    op.drop_index('idx_ubicacion_capitals', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_active_canton', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_active_provincia', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_nombres_fulltext', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_distrito_name', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_canton_name', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_provincia_name', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_postal_code', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_inec_code', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_active_status', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_distrito_lookup', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_canton_lookup', 'ubicaciones_cr')
    op.drop_index('idx_ubicacion_provincia_lookup', 'ubicaciones_cr')
    
    # Drop CABYS indexes
    op.drop_index('idx_cabys_validity_period', 'codigos_cabys')
    op.drop_index('idx_cabys_popularity', 'codigos_cabys')
    op.drop_index('idx_cabys_active_exempt', 'codigos_cabys')
    op.drop_index('idx_cabys_active_iva', 'codigos_cabys')
    op.drop_index('idx_cabys_active_category', 'codigos_cabys')
    op.drop_index('idx_cabys_descripcion_fulltext', 'codigos_cabys')
    op.drop_index('idx_cabys_last_used', 'codigos_cabys')
    op.drop_index('idx_cabys_usage_count', 'codigos_cabys')
    op.drop_index('idx_cabys_iva_exempt', 'codigos_cabys')
    op.drop_index('idx_cabys_iva_rate', 'codigos_cabys')
    op.drop_index('idx_cabys_category_level2', 'codigos_cabys')
    op.drop_index('idx_cabys_category_level1', 'codigos_cabys')
    op.drop_index('idx_cabys_active_status', 'codigos_cabys')
    op.drop_index('idx_cabys_codigo_lookup', 'codigos_cabys')
    
    # Drop tenants indexes
    op.drop_index('idx_tenants_certificate_status', 'tenants')
    op.drop_index('idx_tenants_usage_tracking', 'tenants')
    op.drop_index('idx_tenants_plan_limits_composite', 'tenants')
    op.drop_index('idx_tenants_active_plan_composite', 'tenants')
    op.drop_index('idx_tenants_monthly_reset', 'tenants')
    op.drop_index('idx_tenants_certificate_expiry', 'tenants')
    op.drop_index('idx_tenants_plan_type', 'tenants')
    op.drop_index('idx_tenants_active_status', 'tenants')
    op.drop_index('idx_tenants_cedula_lookup', 'tenants')
    op.drop_index('idx_tenants_api_key_lookup', 'tenants')