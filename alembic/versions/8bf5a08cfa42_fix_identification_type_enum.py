"""fix_identification_type_enum

Revision ID: 8bf5a08cfa42
Revises: 0675c7abc776
Create Date: 2025-07-28 19:44:01.102369

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8bf5a08cfa42'
down_revision = '0675c7abc776'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert all identificationtype columns to varchar temporarily
    op.execute("ALTER TABLE documentos ALTER COLUMN emisor_tipo_identificacion TYPE VARCHAR(50)")
    op.execute("ALTER TABLE documentos ALTER COLUMN receptor_tipo_identificacion TYPE VARCHAR(50)")
    op.execute("ALTER TABLE otros_cargos_documentos ALTER COLUMN tercero_tipo_identificacion TYPE VARCHAR(50)")
    op.execute("ALTER TABLE mensajes_receptor ALTER COLUMN receptor_identificacion_tipo TYPE VARCHAR(50)")
    
    # Drop and recreate the enum with numeric values
    op.execute("DROP TYPE identificationtype CASCADE")
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
    
    # Convert data values
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
    
    # Convert columns back to enum type
    op.execute("ALTER TABLE documentos ALTER COLUMN emisor_tipo_identificacion TYPE identificationtype USING emisor_tipo_identificacion::identificationtype")
    op.execute("ALTER TABLE documentos ALTER COLUMN receptor_tipo_identificacion TYPE identificationtype USING receptor_tipo_identificacion::identificationtype")
    op.execute("ALTER TABLE otros_cargos_documentos ALTER COLUMN tercero_tipo_identificacion TYPE identificationtype USING tercero_tipo_identificacion::identificationtype")
    op.execute("ALTER TABLE mensajes_receptor ALTER COLUMN receptor_identificacion_tipo TYPE identificationtype USING receptor_identificacion_tipo::identificationtype")


def downgrade() -> None:
    # Revert if needed
    pass