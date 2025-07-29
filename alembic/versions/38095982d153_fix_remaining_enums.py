"""fix_remaining_enums

Revision ID: 38095982d153
Revises: 8bf5a08cfa42
Create Date: 2025-07-28 20:13:20.370737

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38095982d153'
down_revision = '8bf5a08cfa42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix salecondition enum
    op.execute("ALTER TABLE documentos ALTER COLUMN condicion_venta TYPE VARCHAR(10)")
    op.execute("DROP TYPE salecondition CASCADE")
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
    
    # Convert salecondition data
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
    
    op.execute("ALTER TABLE documentos ALTER COLUMN condicion_venta TYPE salecondition USING condicion_venta::salecondition")
    
    # Fix paymentmethod enum
    op.execute("ALTER TABLE documentos ALTER COLUMN medio_pago TYPE VARCHAR(10)")
    op.execute("DROP TYPE paymentmethod CASCADE")
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
    
    # Convert paymentmethod data
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
    
    op.execute("ALTER TABLE documentos ALTER COLUMN medio_pago TYPE paymentmethod USING medio_pago::paymentmethod")


def downgrade() -> None:
    # Revert if needed
    pass