"""fix_document_type_enum_values

Revision ID: 0675c7abc776
Revises: dca971476666
Create Date: 2025-07-28 18:38:38.960418

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0675c7abc776'
down_revision = 'dca971476666'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing enum and recreate with numeric codes
    op.execute("ALTER TABLE documentos ALTER COLUMN tipo_documento TYPE VARCHAR(10)")
    op.execute("DROP TYPE IF EXISTS documenttype")
    
    # Create new enum with numeric codes
    op.execute("""
        CREATE TYPE documenttype AS ENUM (
            '01',  -- FACTURA_ELECTRONICA
            '02',  -- NOTA_DEBITO_ELECTRONICA  
            '03',  -- NOTA_CREDITO_ELECTRONICA
            '04',  -- TIQUETE_ELECTRONICO
            '05',  -- FACTURA_EXPORTACION
            '06',  -- FACTURA_COMPRA
            '07'   -- RECIBO_PAGO
        )
    """)
    
    # Convert existing data from name to code
    op.execute("""
        UPDATE documentos SET tipo_documento = CASE
            WHEN tipo_documento = 'FACTURA_ELECTRONICA' THEN '01'
            WHEN tipo_documento = 'NOTA_DEBITO_ELECTRONICA' THEN '02'
            WHEN tipo_documento = 'NOTA_CREDITO_ELECTRONICA' THEN '03'
            WHEN tipo_documento = 'TIQUETE_ELECTRONICO' THEN '04'
            WHEN tipo_documento = 'FACTURA_EXPORTACION' THEN '05'
            WHEN tipo_documento = 'FACTURA_COMPRA' THEN '06'
            WHEN tipo_documento = 'RECIBO_PAGO' THEN '07'
            ELSE tipo_documento
        END
    """)
    
    # Change column back to enum type
    op.execute("ALTER TABLE documentos ALTER COLUMN tipo_documento TYPE documenttype USING tipo_documento::documenttype")


def downgrade() -> None:
    # Revert back to original enum values
    op.execute("ALTER TABLE documentos ALTER COLUMN tipo_documento TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS documenttype")
    
    # Recreate original enum
    op.execute("""
        CREATE TYPE documenttype AS ENUM (
            'FACTURA_ELECTRONICA',
            'NOTA_DEBITO_ELECTRONICA', 
            'NOTA_CREDITO_ELECTRONICA',
            'TIQUETE_ELECTRONICO',
            'FACTURA_EXPORTACION',
            'FACTURA_COMPRA',
            'RECIBO_PAGO'
        )
    """)
    
    # Convert data back to original names
    op.execute("""
        UPDATE documentos SET tipo_documento = CASE
            WHEN tipo_documento = '01' THEN 'FACTURA_ELECTRONICA'
            WHEN tipo_documento = '02' THEN 'NOTA_DEBITO_ELECTRONICA'
            WHEN tipo_documento = '03' THEN 'NOTA_CREDITO_ELECTRONICA'
            WHEN tipo_documento = '04' THEN 'TIQUETE_ELECTRONICO'
            WHEN tipo_documento = '05' THEN 'FACTURA_EXPORTACION'
            WHEN tipo_documento = '06' THEN 'FACTURA_COMPRA'
            WHEN tipo_documento = '07' THEN 'RECIBO_PAGO'
            ELSE tipo_documento
        END
    """)
    
    # Change column back to enum type
    op.execute("ALTER TABLE documentos ALTER COLUMN tipo_documento TYPE documenttype USING tipo_documento::documenttype")