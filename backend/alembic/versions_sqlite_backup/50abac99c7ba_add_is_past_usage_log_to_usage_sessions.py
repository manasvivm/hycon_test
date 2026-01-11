"""add_is_past_usage_log_to_usage_sessions

Revision ID: 50abac99c7ba
Revises: 21d28830d439
Create Date: 2025-12-06 11:25:34.855075

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '50abac99c7ba'
down_revision = '21d28830d439'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new column only - indexes already exist from previous migration
    with op.batch_alter_table('usage_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_past_usage_log', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.create_index('ix_usage_sessions_is_past_usage_log', ['is_past_usage_log'], unique=False)


def downgrade() -> None:
    # Remove the column
    with op.batch_alter_table('usage_sessions', schema=None) as batch_op:
        batch_op.drop_index('ix_usage_sessions_is_past_usage_log')
        batch_op.drop_column('is_past_usage_log')