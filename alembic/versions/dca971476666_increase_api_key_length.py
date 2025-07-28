"""increase_api_key_length

Revision ID: dca971476666
Revises: 3891f9ca89a3
Create Date: 2025-07-27 23:44:17.918323

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dca971476666'
down_revision = '3891f9ca89a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Increase api_key field length from 64 to 255 characters
    op.alter_column('tenants', 'api_key',
                    existing_type=sa.String(64),
                    type_=sa.String(255),
                    existing_nullable=False)


def downgrade() -> None:
    # Revert api_key field length back to 64 characters
    op.alter_column('tenants', 'api_key',
                    existing_type=sa.String(255),
                    type_=sa.String(64),
                    existing_nullable=False)