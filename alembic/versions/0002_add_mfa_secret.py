"""add mfa secret column"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('mfa_secret', sa.String(32)))


def downgrade() -> None:
    op.drop_column('users', 'mfa_secret')
