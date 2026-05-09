# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/alembic/versions/20260118_0003_003_add_genslave_config.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 18th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Add genslave_ip and genslave_hostname to config table.

Revision ID: 003
Revises: 002
Create Date: 2026-01-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add genslave_ip column (nullable, for IP address resolution)
    op.add_column(
        "config",
        sa.Column("genslave_ip", sa.String(length=45), nullable=True),
    )

    # Add genslave_hostname column (not nullable, default 'genslave')
    op.add_column(
        "config",
        sa.Column(
            "genslave_hostname",
            sa.String(length=50),
            nullable=False,
            server_default="genslave",
        ),
    )

    # Note: The model default for slave_api_url is now :8001
    # Existing URLs can be updated via the UI if needed


def downgrade() -> None:
    # Remove the columns
    op.drop_column("config", "genslave_hostname")
    op.drop_column("config", "genslave_ip")
