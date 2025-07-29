"""fix_all_enum_values_to_numeric_codes

Revision ID: 9d13c8cc543d
Revises: 0675c7abc776
Create Date: 2025-07-28 18:40:02.703939

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d13c8cc543d'
down_revision = '0675c7abc776'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix identificationtype enum - Convert all columns to VARCHAR first
    op.execute("ALTER TABLE documentos ALTER COLUMN emisor_tipo_identificacion TYPE VARCHAR(10)")
    op.execute("ALTER TABLE documentos ALTER COLUMN receptor_tipo_identificacion TYPE VARCHAR(10)")
    op.execute("ALTER TABLE otros_cargos_documentos ALTER COLUMN tercero_tipo_identificacion TYPE VARCHAR(10)")
    op.execute("ALTER TABLE mensajes_receptor ALTER COLUMN receptor_identificacion_tipo TYPE VARCHAR(10)")
    op.execute("DROP TYPE IF EXISTS identificationtype CASCADE")
    
    op.execute("""
        CREATE TYPE identificationtype AS ENUM (
            '01',  -- CEDULA_FISICA
            '02',  -- CEDULA_JURIDICA  
            '03',  -- DIMEX
            '04',  -- NITE
            '05',  -- EXTRANJERO_NO_DOMICILIADO
            '06'   -- NO_CONTRIBUYENTE
        )
    """)
    
    # Convert existing identification data
    op.execute("""
        UPDATE documentos SET emisor_tipo_identificacion = CASE
            WHEN emisor_tipo_identificacion = 'CEDULA_FISICA' THEN '01'
            WHEN emisor_tipo_identificacion = 'CEDULA_JURIDICA' THEN '02'
            WHEN emisor_tipo_identificacion = 'DIMEX' THEN '03'
            WHEN emisor_tipo_identificacion = 'NITE' THEN '04'
            WHEN emisor_tipo_identificacion = 'EXTRANJERO_NO_DOMICILIADO' THEN '05'
            WHEN emisor_tipo_identificacion = 'NO_CONTRIBUYENTE' THEN '06'
            ELSE emisor_tipo_identificacion
        END
    """)
    
    op.execute("""
        UPDATE documentos SET receptor_tipo_identificacion = CASE
            WHEN receptor_tipo_identificacion = 'CEDULA_FISICA' THEN '01'
            WHEN receptor_tipo_identificacion = 'CEDULA_JURIDICA' THEN '02'
            WHEN receptor_tipo_identificacion = 'DIMEX' THEN '03'
            WHEN receptor_tipo_identificacion = 'NITE' THEN '04'
            WHEN receptor_tipo_identificacion = 'EXTRANJERO_NO_DOMICILIADO' THEN '05'
            WHEN receptor_tipo_identificacion = 'NO_CONTRIBUYENTE' THEN '06'
            ELSE receptor_tipo_identificacion
        END
        WHERE receptor_tipo_identificacion IS NOT NULL
    """)
    
    op.execute("""
        UPDATE otros_cargos_documentos SET tercero_tipo_identificacion = CASE
            WHEN tercero_tipo_identificacion = 'CEDULA_FISICA' THEN '01'
            WHEN tercero_tipo_identificacion = 'CEDULA_JURIDICA' THEN '02'
            WHEN tercero_tipo_identificacion = 'DIMEX' THEN '03'
            WHEN tercero_tipo_identificacion = 'NITE' THEN '04'
            WHEN tercero_tipo_identificacion = 'EXTRANJERO_NO_DOMICILIADO' THEN '05'
            WHEN tercero_tipo_identificacion = 'NO_CONTRIBUYENTE' THEN '06'
            ELSE tercero_tipo_identificacion
        END
        WHERE tercero_tipo_identificacion IS NOT NULL
    """)
    
    op.execute("""
        UPDATE mensajes_receptor SET receptor_identificacion_tipo = CASE
            WHEN receptor_identificacion_tipo = 'CEDULA_FISICA' THEN '01'
            WHEN receptor_identificacion_tipo = 'CEDULA_JURIDICA' THEN '02'
            WHEN receptor_identificacion_tipo = 'DIMEX' THEN '03'
            WHEN receptor_identificacion_tipo = 'NITE' THEN '04'
            WHEN receptor_identificacion_tipo = 'EXTRANJERO_NO_DOMICILIADO' THEN '05'
            WHEN receptor_identificacion_tipo = 'NO_CONTRIBUYENTE' THEN '06'
            ELSE receptor_identificacion_tipo
        END
        WHERE receptor_identificacion_tipo IS NOT NULL
    """)
    
    # Convert back to enum
    op.execute("ALTER TABLE documentos ALTER COLUMN emisor_tipo_identificacion TYPE identificationtype USING emisor_tipo_identificacion::identificationtype")
    op.execute("ALTER TABLE documentos ALTER COLUMN receptor_tipo_identificacion TYPE identificationtype USING receptor_tipo_identificacion::identificationtype")
    op.execute("ALTER TABLE otros_cargos_documentos ALTER COLUMN tercero_tipo_identificacion TYPE identificationtype USING tercero_tipo_identificacion::identificationtype")
    op.execute("ALTER TABLE mensajes_receptor ALTER COLUMN receptor_identificacion_tipo TYPE identificationtype USING receptor_identificacion_tipo::identificationtype")
    
    # Fix salecondition enum
    op.execute("ALTER TABLE documentos ALTER COLUMN condicion_venta TYPE VARCHAR(10)")
    op.execute("DROP TYPE IF EXISTS salecondition CASCADE")
    
    op.execute("""
        CREATE TYPE salecondition AS ENUM (
            '01',  -- CONTADO
            '02',  -- CREDITO
            '03',  -- CONSIGNACION
            '04',  -- APARTADO
            '05',  -- ARRENDAMIENTO_OPCION_COMPRA
            '06',  -- ARRENDAMIENTO_FUNCION_FINANCIERA
            '07',  -- COBRO_TERCERO
            '08',  -- SERVICIOS_ESTADO_CREDITO
            '09',  -- VENTA_CREDITO_90_DIAS
            '10',  -- VENTA_MERCANCIA_NO_NACIONALIZADA
            '11',  -- VENTA_BIENES_USADOS_NO_CONTRIBUYENTE
            '12',  -- ARRENDAMIENTO_OPERATIVO
            '13',  -- ARRENDAMIENTO_FINANCIERO
            '99'   -- OTROS
        )
    """)
    
    # Convert existing sale condition data
    op.execute("""
        UPDATE documentos SET condicion_venta = CASE
            WHEN condicion_venta = 'CONTADO' THEN '01'
            WHEN condicion_venta = 'CREDITO' THEN '02'
            WHEN condicion_venta = 'CONSIGNACION' THEN '03'
            WHEN condicion_venta = 'APARTADO' THEN '04'
            WHEN condicion_venta = 'ARRENDAMIENTO_OPCION_COMPRA' THEN '05'
            WHEN condicion_venta = 'ARRENDAMIENTO_FUNCION_FINANCIERA' THEN '06'
            WHEN condicion_venta = 'COBRO_TERCERO' THEN '07'
            WHEN condicion_venta = 'SERVICIOS_ESTADO_CREDITO' THEN '08'
            WHEN condicion_venta = 'VENTA_CREDITO_90_DIAS' THEN '09'
            WHEN condicion_venta = 'VENTA_MERCANCIA_NO_NACIONALIZADA' THEN '10'
            WHEN condicion_venta = 'VENTA_BIENES_USADOS_NO_CONTRIBUYENTE' THEN '11'
            WHEN condicion_venta = 'ARRENDAMIENTO_OPERATIVO' THEN '12'
            WHEN condicion_venta = 'ARRENDAMIENTO_FINANCIERO' THEN '13'
            WHEN condicion_venta = 'OTROS' THEN '99'
            ELSE condicion_venta
        END
    """)
    
    # Convert back to enum
    op.execute("ALTER TABLE documentos ALTER COLUMN condicion_venta TYPE salecondition USING condicion_venta::salecondition")
    
    # Fix paymentmethod enum
    op.execute("ALTER TABLE documentos ALTER COLUMN medio_pago TYPE VARCHAR(10)")
    op.execute("DROP TYPE IF EXISTS paymentmethod CASCADE")
    
    op.execute("""
        CREATE TYPE paymentmethod AS ENUM (
            '01',  -- EFECTIVO
            '02',  -- TARJETA
            '03',  -- CHEQUE
            '04',  -- TRANSFERENCIA
            '05',  -- RECAUDADO_TERCERO
            '99'   -- OTROS
        )
    """)
    
    # Convert existing payment method data
    op.execute("""
        UPDATE documentos SET medio_pago = CASE
            WHEN medio_pago = 'EFECTIVO' THEN '01'
            WHEN medio_pago = 'TARJETA' THEN '02'
            WHEN medio_pago = 'CHEQUE' THEN '03'
            WHEN medio_pago = 'TRANSFERENCIA' THEN '04'
            WHEN medio_pago = 'RECAUDADO_TERCERO' THEN '05'
            WHEN medio_pago = 'OTROS' THEN '99'
            ELSE medio_pago
        END
    """)
    
    # Convert back to enum
    op.execute("ALTER TABLE documentos ALTER COLUMN medio_pago TYPE paymentmethod USING medio_pago::paymentmethod")


def downgrade() -> None:
    # Revert back to original enum values - implement if needed
    pass