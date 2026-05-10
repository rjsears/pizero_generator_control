"""Remove auto_arm_relay_on_connect — redundant with heartbeat sync.

Revision ID: 014
Revises: 013
Create Date: 2026-05-10

The auto-arm-on-connect feature pre-dated the GenSlave heartbeat-driven
state sync and the explicit boot arming policy. With both of those in
place, this setting no longer has any meaningful effect:

- Runtime reconnects: GenSlave reads `armed` from every heartbeat and
  matches GenMaster's DB. If GenMaster's DB still says armed=True after
  a comm blip, the slave re-arms automatically via "genmaster_sync"
  without auto_arm_relay_on_connect being involved.
- Boot reconciliation under `fail_safe` policy: explicitly suppressed
  via `manual_disarm_active=True` so the operator must re-arm manually.
- Boot reconciliation under `preserve_state` policy: state is preserved
  by the policy itself; auto-arm would be a no-op.

Removing the setting simplifies the model: GenMaster's DB is the source
of truth; GenSlave follows the heartbeat.
"""

from alembic import op


# revision identifiers
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("config", "auto_arm_relay_on_connect")


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column(
        "config",
        sa.Column(
            "auto_arm_relay_on_connect",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
