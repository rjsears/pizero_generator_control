"""Add slave_relay_armed column

Revision ID: 004
Revises: 003
Create Date: 2026-01-19

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add slave_relay_armed column to system_state table
    op.add_column(
        "system_state",
        sa.Column("slave_relay_armed", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("system_state", "slave_relay_armed")
