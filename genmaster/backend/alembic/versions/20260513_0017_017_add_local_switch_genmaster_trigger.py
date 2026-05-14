"""Add local_switch_genmaster to trigger + stop_reason constraints.

Revision ID: 017
Revises: 015
Create Date: 2026-05-13

The HOA selector at GenMaster's panel can drive a generator run directly:
operator turns the rotary to the Run position and the state machine starts
the generator with `trigger = 'local_switch_genmaster'`. This trigger
source is tracked separately from `manual` so run-history audits can tell
"operator clicked the web Start button" apart from "operator turned the
hardware switch to Run."

Three CHECK constraints need updating:

  * `chk_run_trigger` on `system_state.run_trigger` — adds the value to the
    set of legal current-trigger states.
  * `chk_trigger_type` on `generator_runs.trigger_type` — adds the value to
    the set of legal historical run triggers, so the run record persists.
  * `chk_stop_reason` on `generator_runs.stop_reason` — adds two new
    HOA-specific stop reasons so the run-history audit trail records WHY
    a run ended (operator flipped HOA out of Run vs operator flipped HOA
    to Quiet during an auto-run). Without these the chk_stop_reason
    constraint would reject the row.

There is no migration 016 in this sequence by intent — slot 016 is
reserved for the Quiet override DB columns (Phase 4c) which may land
later. Alembic doesn't require numeric continuity in revisions; the
down_revision pointer below makes the chain explicit.
"""

from alembic import op


# revision identifiers
revision = "017"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update system_state run_trigger constraint
    op.drop_constraint("chk_run_trigger", "system_state", type_="check")
    op.create_check_constraint(
        "chk_run_trigger",
        "system_state",
        "run_trigger IN ('idle', 'victron', 'manual', 'scheduled', 'exercise', 'local_switch_genmaster')",
    )

    # Update generator_runs trigger_type constraint
    op.drop_constraint("chk_trigger_type", "generator_runs", type_="check")
    op.create_check_constraint(
        "chk_trigger_type",
        "generator_runs",
        "trigger_type IN ('victron', 'manual', 'scheduled', 'exercise', 'local_switch_genmaster')",
    )

    # Update generator_runs stop_reason constraint to allow HOA-specific
    # stop reasons. New values:
    #   'local_switch_genmaster_end' — operator turned HOA away from Run
    #   'hoa_quiet'                  — HOA flipped to Quiet during an
    #                                  automation-triggered run
    op.drop_constraint("chk_stop_reason", "generator_runs", type_="check")
    op.create_check_constraint(
        "chk_stop_reason",
        "generator_runs",
        "stop_reason IS NULL OR stop_reason IN ("
        "'victron', 'manual', 'scheduled_end', 'exercise_end', "
        "'comm_loss', 'override', 'error', 'max_runtime', "
        "'local_switch_genmaster_end', 'hoa_quiet')",
    )


def downgrade() -> None:
    # Revert system_state run_trigger constraint
    op.drop_constraint("chk_run_trigger", "system_state", type_="check")
    op.create_check_constraint(
        "chk_run_trigger",
        "system_state",
        "run_trigger IN ('idle', 'victron', 'manual', 'scheduled', 'exercise')",
    )

    # Revert generator_runs trigger_type constraint
    op.drop_constraint("chk_trigger_type", "generator_runs", type_="check")
    op.create_check_constraint(
        "chk_trigger_type",
        "generator_runs",
        "trigger_type IN ('victron', 'manual', 'scheduled', 'exercise')",
    )

    # Revert generator_runs stop_reason constraint
    op.drop_constraint("chk_stop_reason", "generator_runs", type_="check")
    op.create_check_constraint(
        "chk_stop_reason",
        "generator_runs",
        "stop_reason IS NULL OR stop_reason IN ("
        "'victron', 'manual', 'scheduled_end', 'exercise_end', "
        "'comm_loss', 'override', 'error', 'max_runtime')",
    )
