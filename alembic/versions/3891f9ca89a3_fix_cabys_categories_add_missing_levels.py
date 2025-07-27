"""fix_cabys_categories_add_missing_levels

Revision ID: 3891f9ca89a3
Revises: 002
Create Date: 2025-07-26 19:27:32.297683

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3891f9ca89a3'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing CABYS category levels (5-8) to match official 8-level structure"""
    
    # Add the 4 missing category levels to CABYS table
    op.add_column('codigos_cabys', sa.Column('categoria_nivel_5', sa.String(length=255), nullable=True, comment='Level 5 category'))
    op.add_column('codigos_cabys', sa.Column('categoria_nivel_6', sa.String(length=255), nullable=True, comment='Level 6 category'))
    op.add_column('codigos_cabys', sa.Column('categoria_nivel_7', sa.String(length=255), nullable=True, comment='Level 7 category'))
    op.add_column('codigos_cabys', sa.Column('categoria_nivel_8', sa.String(length=255), nullable=True, comment='Level 8 category (most specific)'))
    
    # Add indexes for the new category levels
    op.create_index('idx_cabys_category_level5', 'codigos_cabys', ['categoria_nivel_5'])
    op.create_index('idx_cabys_category_level6', 'codigos_cabys', ['categoria_nivel_6'])
    op.create_index('idx_cabys_category_level7', 'codigos_cabys', ['categoria_nivel_7'])
    op.create_index('idx_cabys_category_level8', 'codigos_cabys', ['categoria_nivel_8'])
    
    # Add composite indexes for filtering by multiple category levels
    op.create_index('idx_cabys_active_category_5', 'codigos_cabys', ['activo', 'categoria_nivel_5'])
    op.create_index('idx_cabys_active_category_6', 'codigos_cabys', ['activo', 'categoria_nivel_6'])
    op.create_index('idx_cabys_active_category_7', 'codigos_cabys', ['activo', 'categoria_nivel_7'])
    op.create_index('idx_cabys_active_category_8', 'codigos_cabys', ['activo', 'categoria_nivel_8'])


def downgrade() -> None:
    """Remove the added CABYS category levels"""
    
    # Drop composite indexes
    op.drop_index('idx_cabys_active_category_8', 'codigos_cabys')
    op.drop_index('idx_cabys_active_category_7', 'codigos_cabys')
    op.drop_index('idx_cabys_active_category_6', 'codigos_cabys')
    op.drop_index('idx_cabys_active_category_5', 'codigos_cabys')
    
    # Drop individual category indexes
    op.drop_index('idx_cabys_category_level8', 'codigos_cabys')
    op.drop_index('idx_cabys_category_level7', 'codigos_cabys')
    op.drop_index('idx_cabys_category_level6', 'codigos_cabys')
    op.drop_index('idx_cabys_category_level5', 'codigos_cabys')
    
    # Drop the columns
    op.drop_column('codigos_cabys', 'categoria_nivel_8')
    op.drop_column('codigos_cabys', 'categoria_nivel_7')
    op.drop_column('codigos_cabys', 'categoria_nivel_6')
    op.drop_column('codigos_cabys', 'categoria_nivel_5')