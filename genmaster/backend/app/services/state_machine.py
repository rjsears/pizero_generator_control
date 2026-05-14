# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/state_machine.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""State machine service for generator state management."""

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Config, EventLog, GeneratorInfo, GeneratorRun, SystemState
from app.schemas import (
    FullSystemStatus,
    GeneratorStatus,
    HOAStatus,
    OverrideStatus,
    SlaveHealth,
    SystemHealth,
    VictronStatus,
)

if TYPE_CHECKING:
    from app.services.webhook import WebhookService

from app.services.slave_status_service import get_slave_status_service
from app.services.system_notification_engine import SystemNotificationEngine

logger = logging.getLogger(__name__)

# Global notification engine instance
_notification_engine: Optional[SystemNotificationEngine] = None


def get_notification_engine() -> SystemNotificationEngine:
    """Get or create the notification engine singleton."""
    global _notification_engine
    if _notification_engine is None:
        _notification_engine = SystemNotificationEngine()
    return _notification_engine


class StateMachine:
    """
    Manages generator state transitions and coordinates system operations.

    This is the central controller that:
    - Tracks generator running state
    - Handles Victron signal changes
    - Manages manual overrides
    - Coordinates with GenSlave
    - Logs events
    - Sends webhooks
    """

    def __init__(self):
        """Initialize state machine."""
        self._webhook_service: Optional["WebhookService"] = None
        self._initialized = False
        self._operation_lock = asyncio.Lock()

    def set_webhook_service(self, webhook_service: "WebhookService") -> None:
        """Set the webhook service for notifications."""
        self._webhook_service = webhook_service

    async def _get_slave_client(self, timeout: float = 3.0):
        """Get a SlaveClient instance with current config from Redis cache.

        Args:
            timeout: Request timeout in seconds. Use longer timeouts for critical
                     operations like relay control (default 3.0, use 10.0 for relay).
        """
        from app.services.slave_status_service import create_slave_client

        return await create_slave_client(timeout=timeout)

    async def initialize(self) -> None:
        """
        Initialize state machine from database.

        Boot behavior is governed by the operator-configurable
        ``config.boot_arming_policy`` setting:

        - ``"fail_safe"`` (default, safer): force ``slave_relay_armed = False``
          on every GenMaster boot. The operator must explicitly re-arm via the
          UI. A `boot_disarmed_failsafe` notification is fired so the operator
          knows the generator will not start automatically until they act.
        - ``"preserve_state"``: keep the prior ``slave_relay_armed`` value
          across the reboot. The system can resume operation automatically
          after a power outage.

        Regardless of policy, ``generator_running`` is reset to ``False`` on
        boot — actual run state is reconciled from GenSlave via the first
        heartbeat.
        """
        async with AsyncSessionLocal() as db:
            # Ensure system_state row exists
            state = await SystemState.get_instance(db)

            # Read the policy from config
            config = await Config.get_instance(db)
            boot_policy = config.boot_arming_policy or "fail_safe"

            # Log pre-boot state for debugging
            logger.info(
                f"Pre-boot state - "
                f"generator_running: {state.generator_running}, "
                f"relay_armed: {state.slave_relay_armed}, "
                f"slave_status: {state.slave_connection_status}, "
                f"boot_arming_policy: {boot_policy}"
            )

            # Check if we had a running generator before crash/reboot
            was_running = state.generator_running

            # Apply the boot-arming policy
            was_armed_pre_boot = state.slave_relay_armed
            policy_disarmed = False
            if boot_policy == "fail_safe":
                if was_armed_pre_boot:
                    logger.warning(
                        "Boot arming policy is 'fail_safe' — disarming relay "
                        "(was armed pre-boot). Operator must re-arm to enable "
                        "automatic generator operations."
                    )
                    state.slave_relay_armed = False
                    # Set manual_disarm_active so the operator's "this is
                    # disarmed and stays disarmed" intent is recorded. The
                    # flag is cleared automatically when the operator re-arms
                    # manually via the UI. (Originally this also suppressed
                    # the auto-arm-on-connect feature, which was removed in
                    # migration 014.)
                    state.manual_disarm_active = True
                    policy_disarmed = True
                else:
                    logger.info("Boot arming policy is 'fail_safe' — relay was already disarmed")
            else:  # preserve_state
                if was_armed_pre_boot:
                    logger.info(
                        "Boot arming policy is 'preserve_state' — keeping armed "
                        "state across reboot"
                    )

            # Reset slave connection status - will be updated by heartbeat
            state.slave_connection_status = "unknown"
            state.missed_heartbeat_count = 0

            # If generator was marked as running, we need to reconcile
            # For now, mark as not running - reconciliation will verify actual state
            if was_running:
                logger.warning(
                    "Generator was marked as running before reboot - "
                    "marking as stopped until reconciliation with GenSlave"
                )
                state.generator_running = False
                state.run_trigger = "idle"
                state.generator_start_time = None
                # Keep current_run_id to close the run record properly
                if state.current_run_id:
                    # Mark the run as ended due to power loss
                    result = await db.execute(
                        select(GeneratorRun).where(
                            GeneratorRun.id == state.current_run_id
                        )
                    )
                    run = result.scalar_one_or_none()
                    if run and not run.stop_time:
                        run.stop_time = int(time.time())
                        run.duration_seconds = run.stop_time - run.start_time
                        run.stop_reason = "error"
                        run.notes = (run.notes or "") + " [Ended due to power loss/reboot]"
                        logger.info(f"Closed orphaned run {run.id} due to power loss/reboot")
                state.current_run_id = None

            await db.commit()

            logger.info(
                f"State machine initialized - "
                f"generator_running: {state.generator_running}, "
                f"relay_armed: {state.slave_relay_armed}, "
                f"override: {state.override_enabled}, "
                f"boot_arming_policy: {boot_policy}"
            )

            # Log internal event for reboot — accurately reflects whether the
            # policy actually disarmed the relay this time.
            await self.log_event(
                "SYSTEM_BOOT_RESET",
                {
                    "was_running": was_running,
                    "was_armed_pre_boot": was_armed_pre_boot,
                    "boot_arming_policy": boot_policy,
                    "relay_disarmed_by_policy": policy_disarmed,
                },
                severity="WARNING" if (was_running or policy_disarmed) else "INFO",
            )

            # Fire the operator-facing notification ONLY when fail_safe
            # actually disarmed the relay (i.e. it was armed before boot).
            # This is what tells the user "the generator will not start until
            # you re-arm it." We dispatch it as a background task so a slow
            # or hung notification target (SMTP, Twilio, etc.) cannot block
            # GenMaster startup — startup must complete promptly so the
            # health check passes and the rest of the stack comes up.
            if policy_disarmed:
                async def _fire_boot_disarmed_notification():
                    try:
                        from app.services.system_notification_engine import (
                            system_notification_engine,
                        )
                        async with AsyncSessionLocal() as notify_db:
                            await system_notification_engine.trigger_notification(
                                db=notify_db,
                                event_type="boot_disarmed_failsafe",
                                event_data={
                                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "was_running": str(was_running),
                                },
                                skip_rate_limiting=True,
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to fire boot_disarmed_failsafe notification: {e}"
                        )

                asyncio.create_task(_fire_boot_disarmed_notification())

            self._initialized = True

    async def reconcile_with_slave(self, slave_client) -> dict:
        """
        Reconcile GenMaster state with GenSlave's actual state.

        Called during startup to ensure state consistency after reboot.
        This queries GenSlave for its actual relay state and updates
        GenMaster's records to match REALITY (what GenSlave reports).

        IMPORTANT: This method does NOT send relay commands. GenSlave's
        physical relay state is the truth after a reboot. GenMaster
        updates its database to match.

        Args:
            slave_client: SlaveClient instance

        Returns:
            Dict with reconciliation results
        """
        result = {
            "success": False,
            "slave_reachable": False,
            "relay_state": None,
            "slave_armed": None,
            "message": "",
        }

        try:
            # Try to get GenSlave status
            response = await slave_client.get_relay_state()

            if not response.success:
                result["message"] = f"Could not reach GenSlave: {response.error}"
                logger.warning(f"Reconciliation failed: {result['message']}")
                return result

            result["slave_reachable"] = True
            result["relay_state"] = response.data.get("relay_state", False)
            result["slave_armed"] = response.data.get("armed", False)

            async with AsyncSessionLocal() as db:
                state = await self._get_state(db)

                # GenSlave's PHYSICAL relay state is the truth on startup —
                # update our record to reflect what's actually on the wire.
                state.slave_relay_state = result["relay_state"]

                # NOTE: We deliberately do NOT overwrite state.slave_relay_armed
                # from result["slave_armed"]. The armed flag is GenMaster's
                # policy decision (set by initialize() per boot_arming_policy
                # or by explicit operator action via the UI) — GenSlave is the
                # follower. If GenSlave is currently in a different armed state
                # than GenMaster's DB says, the next heartbeat will push the
                # correct value down to GenSlave via failsafe.record_heartbeat.
                # Overwriting here would silently undo a fail_safe boot disarm.

                # On startup, GenSlave's PHYSICAL state is the truth.
                # Update GenMaster to match reality - do NOT send relay commands.
                if result["relay_state"] and not state.generator_running:
                    # GenSlave relay is ON - generator is actually running
                    # Update GenMaster to reflect this reality
                    logger.warning(
                        "Reconciliation: GenSlave relay is ON but GenMaster "
                        "shows stopped - updating GenMaster to match reality"
                    )
                    state.generator_running = True
                    state.run_trigger = "manual"  # Unknown trigger, mark as manual
                    state.generator_start_time = int(time.time())  # Approximate
                    result["message"] = "Updated GenMaster: generator is running"

                    await self.log_event(
                        "RECONCILIATION_STATE_UPDATED",
                        {
                            "slave_relay": True,
                            "master_was_running": False,
                            "action": "set_genmaster_running_true",
                        },
                        severity="WARNING",
                    )

                elif not result["relay_state"] and state.generator_running:
                    # GenSlave relay is OFF - generator is actually stopped
                    # Update GenMaster to reflect this reality
                    logger.warning(
                        "Reconciliation: GenSlave relay is OFF but GenMaster "
                        "shows running - updating GenMaster to match reality"
                    )
                    state.generator_running = False
                    state.run_trigger = "idle"
                    state.generator_start_time = None
                    state.current_run_id = None
                    result["message"] = "Updated GenMaster: generator is stopped"

                    await self.log_event(
                        "RECONCILIATION_STATE_UPDATED",
                        {
                            "slave_relay": False,
                            "master_was_running": True,
                            "action": "set_genmaster_running_false",
                        },
                        severity="WARNING",
                    )
                else:
                    result["message"] = "State reconciliation complete - states match"

                # Update connection status since we successfully reached slave
                state.slave_connection_status = "connected"
                state.missed_heartbeat_count = 0

                await db.commit()

            result["success"] = True
            logger.info(
                f"Reconciliation complete - slave relay: {result['relay_state']}, "
                f"slave armed: {result['slave_armed']}"
            )

            # Note: auto-arm-on-connect was removed in migration 014. The
            # heartbeat-driven sync from GenMaster to GenSlave handles all
            # reconnect/recovery cases — slave reads `armed` from each
            # heartbeat and matches GenMaster's DB without any extra wiring.

        except Exception as e:
            result["message"] = f"Reconciliation error: {e}"
            logger.error(f"Reconciliation failed: {e}")

        return result

    async def _get_state(self, db: AsyncSession) -> SystemState:
        """Get current system state from database."""
        return await SystemState.get_instance(db)

    async def _get_config(self, db: AsyncSession) -> Config:
        """Get current config from database."""
        return await Config.get_instance(db)

    # =========================================================================
    # Generator State Operations
    # =========================================================================

    async def start_generator(
        self,
        trigger: str,
        duration_minutes: Optional[int] = None,
        notes: Optional[str] = None,
        scheduled_run_id: Optional[int] = None,
    ) -> GeneratorRun:
        """
        Start the generator.

        Args:
            trigger: What triggered the start ('victron', 'manual', 'scheduled')
            duration_minutes: Optional duration before auto-stop
            notes: Optional notes for this run
            scheduled_run_id: Optional ID of scheduled run that triggered this

        Returns:
            The created GeneratorRun record

        Raises:
            ValueError: If generator cannot be started
        """
        async with self._operation_lock:
            async with AsyncSessionLocal() as db:
                state = await self._get_state(db)

                # For manual starts, check and clear cooldown (but not lockout)
                if trigger == "manual":
                    if state.runtime_lockout_active:
                        raise ValueError(
                            "Cannot start - runtime lockout is active. "
                            "Clear the lockout first by acknowledging the max runtime event."
                        )
                    # Clear cooldown on manual start
                    if state.cooldown_active:
                        state.cooldown_active = False
                        state.cooldown_end_time = None
                        logger.info("Cooldown cleared due to manual start")
                        await db.commit()
                        await self.log_event("COOLDOWN_CLEARED_MANUAL_START", {})

                # Validate state transition
                # Note: force_stop override only blocks victron-triggered auto-starts,
                # not manual/scheduled/exercise starts
                is_auto_start = trigger == "victron"

                # Check each condition individually for clearer error messages.
                # EPO is the absolute top of the precedence stack — block every
                # trigger (manual, victron, scheduled, exercise) while the
                # GenSlave hardware E-stop is engaged. The physical NC contact
                # at the generator already breaks the relay output wire, so
                # this guard's job is to keep software state consistent and
                # surface a clear "blocked by EPO" event to the audit log.
                if state.slave_physical_safety_engaged:
                    await self.log_event(
                        "RUN_BLOCKED_EPO_ENGAGED",
                        {"trigger": trigger, "scheduled_run_id": scheduled_run_id},
                        severity="WARNING",
                    )
                    await self._trigger_system_notification(
                        "manual_run_blocked_by_safety", {"trigger": trigger}
                    )
                    raise ValueError(
                        "Cannot start - GenSlave hardware safety interlock "
                        "(EPO) is engaged. Release the E-stop at the generator "
                        "to allow operation."
                    )

                # HOA Quiet guard. Sits below EPO in the precedence stack:
                # while the HOA selector is in the Quiet position, automation
                # triggers (Victron, scheduled, exercise) are suppressed —
                # UNLESS the operator has an active web override (Phase 4c).
                # Quiet is an operator-preference filter, not a safety
                # lockout; manual starts always bypass it.
                if trigger in ("victron", "scheduled", "exercise"):
                    from app.main import hoa_monitor
                    if (
                        hoa_monitor is not None
                        and hoa_monitor.current_state == "quiet"
                        and not self._is_quiet_override_active(state)
                    ):
                        await self.log_event(
                            "AUTO_RUN_SUPPRESSED_BY_QUIET",
                            {
                                "trigger": trigger,
                                "scheduled_run_id": scheduled_run_id,
                                "hoa_state": "quiet",
                            },
                            severity="WARNING",
                        )
                        await self._trigger_system_notification(
                            "auto_run_suppressed_by_quiet", {"trigger": trigger}
                        )
                        raise ValueError(
                            f"Cannot start - HOA selector is in the Quiet "
                            f"position; automation triggers ({trigger}) are "
                            f"suppressed. Use the web UI's manual start or "
                            f"the Quiet override, or turn the HOA selector "
                            f"to Auto."
                        )

                if state.generator_running:
                    raise ValueError("Generator is already running")
                if state.slave_connection_status == "disconnected":
                    raise ValueError("Cannot start - GenSlave is disconnected")
                if state.runtime_lockout_active:
                    raise ValueError(
                        "Cannot start - runtime lockout is active. "
                        "Clear the lockout first."
                    )
                # force_stop override only blocks automatic victron-triggered starts
                if state.override_enabled and state.override_type == "force_stop":
                    if is_auto_start:
                        raise ValueError("Cannot start - force_stop override is active")
                    # Allow manual/scheduled/exercise starts even with force_stop
                    logger.info(f"Allowing {trigger} start despite force_stop override")

                # Fetch generator info for fuel tracking
                gen_info = await GeneratorInfo.get_instance(db)
                fuel_type = gen_info.fuel_type
                load_expected = gen_info.load_expected
                consumption_rate = gen_info.get_consumption_rate()

                # Create run record with fuel tracking data
                # DB FIRST - this is the source of truth
                start_time = int(time.time())
                run = GeneratorRun(
                    start_time=start_time,
                    trigger_type=trigger,
                    scheduled_run_id=scheduled_run_id,
                    notes=notes,
                    fuel_type_at_run=fuel_type,
                    load_at_run=load_expected,
                    fuel_consumption_rate=consumption_rate,
                )
                db.add(run)
                await db.flush()

                # Update system state - this sets generator_running=True
                # which is the source of truth that heartbeat sends to GenSlave
                state.generator_running = True
                state.generator_start_time = start_time
                state.current_run_id = run.id
                state.run_trigger = trigger

                await db.commit()
                await db.refresh(run)

                logger.info(f"Generator started - trigger: {trigger}, run_id: {run.id}")

                # NOW send relay command to GenSlave
                # Even if this fails/times out, the next heartbeat will sync GenSlave
                # because generator_running=True is already committed to DB
                slave_client = await self._get_slave_client(timeout=10.0)
                try:
                    relay_response = await slave_client.relay_on()
                    if relay_response.success:
                        logger.info("GenSlave relay turned ON")
                    else:
                        # Log warning but don't fail - heartbeat will fix it
                        logger.warning(
                            f"relay_on command failed: {relay_response.error}. "
                            "Heartbeat will sync GenSlave to match."
                        )
                except Exception as e:
                    # Log warning but don't fail - heartbeat will fix it
                    logger.warning(
                        f"relay_on command error: {e}. "
                        "Heartbeat will sync GenSlave to match."
                    )
                finally:
                    await slave_client.close()

                # Update the slave status cache
                slave_status_service = get_slave_status_service()
                await slave_status_service.update_relay_state(relay_on=True)

                # Log event
                await self.log_event(
                    f"GENERATOR_STARTED_{trigger.upper()}",
                    {"run_id": run.id, "trigger": trigger, "notes": notes},
                )

                # Send webhook
                await self._send_webhook(
                    f"generator.started.{trigger}",
                    {"run_id": run.id, "trigger": trigger},
                )

                # Trigger system notification
                from datetime import datetime
                reason_map = {
                    "victron": "Victron signal",
                    "manual": "Manual start",
                    "scheduled": "Scheduled run",
                    "exercise": "Exercise run",
                    "local_switch_genmaster": "Hardware switch (HOA Run)",
                }
                await self._trigger_system_notification(
                    "generator_started",
                    {
                        "run_id": run.id,
                        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "reason": reason_map.get(trigger, trigger),
                    },
                )

                return run

    async def stop_generator(
        self,
        reason: str,
        notes: Optional[str] = None,
    ) -> Optional[GeneratorRun]:
        """
        Stop the generator.

        Args:
            reason: Why stopped ('victron', 'manual', 'scheduled_end', 'comm_loss', 'override', 'error')
            notes: Optional notes

        Returns:
            The completed GeneratorRun record, or None if not running
        """
        async with self._operation_lock:
            async with AsyncSessionLocal() as db:
                state = await self._get_state(db)

                if not state.generator_running:
                    logger.warning("Attempted to stop generator that isn't running")
                    return None

                stop_time = int(time.time())
                run_id = state.current_run_id

                # Update run record if exists
                # DB FIRST - this is the source of truth
                run = None
                if run_id:
                    result = await db.execute(
                        select(GeneratorRun).where(GeneratorRun.id == run_id)
                    )
                    run = result.scalar_one_or_none()
                    if run:
                        run.complete(stop_time, reason)
                        # Calculate estimated fuel used if we have consumption rate
                        if run.fuel_consumption_rate and run.duration_seconds:
                            # Formula: (runtime_seconds / 3600) * fuel_consumption_rate
                            run.estimated_fuel_used = round(
                                (run.duration_seconds / 3600) * run.fuel_consumption_rate,
                                3
                            )

                # Update system state - this sets generator_running=False
                # which is the source of truth that heartbeat sends to GenSlave
                state.generator_running = False
                state.generator_start_time = None
                state.current_run_id = None
                state.run_trigger = "idle"

                await db.commit()

                if run:
                    await db.refresh(run)
                    duration = run.duration_seconds or 0
                    logger.info(
                        f"Generator stopped - reason: {reason}, "
                        f"duration: {duration}s, run_id: {run_id}"
                    )
                else:
                    logger.info(f"Generator stopped - reason: {reason}")

                # NOW send relay command to GenSlave
                # Even if this fails/times out, the next heartbeat will sync GenSlave
                # because generator_running=False is already committed to DB
                slave_client = await self._get_slave_client(timeout=10.0)
                try:
                    relay_response = await slave_client.relay_off()
                    if relay_response.success:
                        logger.info("GenSlave relay turned OFF")
                    else:
                        logger.warning(
                            f"relay_off command failed: {relay_response.error}. "
                            "Heartbeat will sync GenSlave to match."
                        )
                except Exception as e:
                    logger.warning(
                        f"relay_off command error: {e}. "
                        "Heartbeat will sync GenSlave to match."
                    )
                finally:
                    await slave_client.close()

                # Update the slave status cache
                slave_status_service = get_slave_status_service()
                await slave_status_service.update_relay_state(relay_on=False)

                # Log event
                await self.log_event(
                    f"GENERATOR_STOPPED_{reason.upper()}",
                    {"run_id": run_id, "reason": reason, "notes": notes},
                )

                # Send webhook
                await self._send_webhook(
                    f"generator.stopped.{reason}",
                    {"run_id": run_id, "reason": reason},
                )

                # Trigger system notification
                reason_map = {
                    "victron": "Victron signal off",
                    "manual": "Manual stop",
                    "scheduled_end": "Scheduled run ended",
                    "exercise_end": "Exercise run ended",
                    "comm_loss": "Communication loss",
                    "override": "Override activated",
                    "error": "Error occurred",
                    "max_runtime": "Max runtime exceeded",
                    "local_switch_genmaster_end": "HOA selector returned to Auto",
                    "hoa_quiet": "HOA selector flipped to Quiet during run",
                }
                duration_seconds = run.duration_seconds if run else 0
                # Format runtime as human-readable
                hours, remainder = divmod(duration_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                if hours > 0:
                    runtime = f"{int(hours)}h {int(minutes)}m"
                elif minutes > 0:
                    runtime = f"{int(minutes)}m {int(seconds)}s"
                else:
                    runtime = f"{int(seconds)}s"
                # Use actual fuel consumed from run record (calculated from consumption rate)
                fuel_gallons = run.estimated_fuel_used if run and run.estimated_fuel_used else 0
                # Use fuel type stored when run started
                fuel_type = run.fuel_type_at_run if run and run.fuel_type_at_run else "Unknown"
                # Format fuel type for display (lpg -> Propane, natural_gas -> Natural Gas, diesel -> Diesel)
                fuel_type_display = {
                    "lpg": "Propane",
                    "natural_gas": "Natural Gas",
                    "diesel": "Diesel",
                }.get(fuel_type, fuel_type.title() if fuel_type else "Unknown")

                await self._trigger_system_notification(
                    "generator_stopped",
                    {
                        "run_id": run_id,
                        "reason": reason_map.get(reason, reason),
                        "runtime": runtime,
                        "fuel_gallons": fuel_gallons,
                        "fuel_type": fuel_type_display,
                    },
                )

                return run

    async def handle_victron_signal_change(self, signal_active: bool) -> None:
        """
        Handle Victron relay signal change.

        Args:
            signal_active: True if generator is wanted, False otherwise
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            config = await self._get_config(db)

            # Update signal state
            state.victron_signal_state = signal_active
            state.victron_last_change = int(time.time())
            await db.commit()

            # Check if override blocks action
            if state.override_enabled:
                logger.info(
                    f"Victron signal changed to {signal_active}, "
                    f"but override ({state.override_type}) is active - ignoring"
                )
                return

            # Check if relay is armed
            if not state.slave_relay_armed:
                logger.info(
                    f"Victron signal changed to {signal_active}, "
                    f"but GenSlave relay is not armed - ignoring"
                )
                return

            # Take action based on signal
            if signal_active and not state.generator_running:
                # Check EPO. start_generator() would refuse anyway, but
                # we pre-check here so the log message is "Victron request
                # suppressed by EPO" rather than a generic ValueError trace.
                # Same pattern as the lockout/cooldown checks below.
                if state.slave_physical_safety_engaged:
                    logger.warning(
                        "Victron signal active but GenSlave EPO is engaged - "
                        "suppressing run request until E-stop is released"
                    )
                    await self.log_event(
                        "VICTRON_START_BLOCKED_EPO",
                        {},
                        severity="WARNING",
                    )
                    return

                # Check HOA Quiet. Same pre-check pattern as EPO so the log
                # is informative ("suppressed by Quiet") rather than a generic
                # ValueError trace from start_generator(). Quiet is an
                # operator-preference filter that suppresses automation
                # triggers; manual web starts still work, and an active
                # Quiet override (Phase 4c) lets automation through.
                from app.main import hoa_monitor
                if (
                    hoa_monitor is not None
                    and hoa_monitor.current_state == "quiet"
                    and not self._is_quiet_override_active(state)
                ):
                    logger.info(
                        "Victron signal active but HOA selector is in Quiet "
                        "position - suppressing automation run. Operator can "
                        "manually start via web UI, or use the Quiet "
                        "override, if needed."
                    )
                    await self.log_event(
                        "AUTO_RUN_SUPPRESSED_BY_QUIET",
                        {"trigger": "victron", "hoa_state": "quiet"},
                        severity="WARNING",
                    )
                    await self._trigger_system_notification(
                        "auto_run_suppressed_by_quiet", {"trigger": "victron"}
                    )
                    return

                # Check runtime lockout
                if state.runtime_lockout_active:
                    logger.warning(
                        "Victron signal active but runtime lockout is active - "
                        "cannot start generator until lockout is cleared"
                    )
                    await self.log_event(
                        "VICTRON_START_BLOCKED_LOCKOUT",
                        {"lockout_reason": state.runtime_lockout_reason},
                        severity="WARNING",
                    )
                    return

                # Check cooldown
                if state.cooldown_active and not state.is_cooldown_expired():
                    remaining = state.cooldown_end_time - int(time.time()) if state.cooldown_end_time else 0
                    logger.info(
                        f"Victron signal active but cooldown is active - "
                        f"{remaining}s remaining before restart allowed"
                    )
                    await self.log_event(
                        "VICTRON_START_BLOCKED_COOLDOWN",
                        {"cooldown_remaining_seconds": remaining},
                    )
                    return

                logger.info("Victron signal active - starting generator")
                await self.start_generator("victron")
            elif not signal_active and state.generator_running:
                if state.run_trigger == "victron":
                    logger.info("Victron signal inactive - stopping generator")
                    await self.stop_generator("victron")
                else:
                    logger.info(
                        f"Victron signal inactive, but run was triggered by "
                        f"{state.run_trigger} - not stopping"
                    )

    async def handle_hoa_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """React to a debounced HOA selector position change (Phase 4d).

        Implements the mid-run transition matrix from
        ``.claude/failsafe.md`` §6 / decisions #4-6:

          * Run -> anything: if the generator is running with the
            ``local_switch_genmaster`` trigger, stop it. (Operator
            chose to leave Run, so the manual run is over.)
          * anything -> Run: start a manual run via
            ``local_switch_genmaster`` if no run is active. If a run
            is already in progress (e.g. Victron-triggered), keep it
            running but reclassify the trigger so it persists past
            Victron's release. (Decision #5.)
          * anything -> Quiet during an automation-triggered run
            (victron / scheduled / exercise): stop the run.
            (Decision #6.) Manual + local-switch runs are not
            interrupted by Quiet — Quiet is an operator-preference
            filter for automation, not a stop command.

        Boot delay is handled in ``HOAMonitor`` — by the time we get
        here, the operator has actually moved the switch since boot.

        Fault state ("both contacts closed") is treated identically to
        Auto for state-machine purposes — no transition action fires.
        The yellow banner in the UI alerts the operator to fix wiring.
        """
        logger.info(
            f"State machine handling HOA transition: {old_state} -> {new_state}"
        )

        # Quiet engaged/released notifications track the selector position
        # itself, independent of any run-state transition below. Fire them
        # first so they go out even when one of the CASE branches returns
        # early.
        if new_state == "quiet" and old_state != "quiet":
            await self._trigger_system_notification(
                "quiet_mode_engaged_genmaster", {}
            )
        elif old_state == "quiet" and new_state != "quiet":
            await self._trigger_system_notification(
                "quiet_mode_released_genmaster", {}
            )
            # A Quiet override only makes sense while Quiet is active.
            # Once the operator turns the selector out of Quiet, any
            # active override is moot — clear it so it doesn't dangle
            # (and so the UI doesn't show a stale countdown). Idempotent,
            # so calling it when no override is active is harmless.
            await self.clear_quiet_override("hoa_left_quiet")

        # Snapshot the current run state without holding the session
        # across calls to start/stop_generator (which open their own
        # sessions and acquire the state-machine lock).
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            was_running = state.generator_running
            current_trigger = state.run_trigger

        # CASE 1: operator left the Run position. If the active run
        # was started by the local switch, stop it now.
        if old_state == "run" and was_running and current_trigger == "local_switch_genmaster":
            logger.info(
                "HOA left Run position; stopping local-switch manual run"
            )
            try:
                await self.stop_generator("local_switch_genmaster_end")
                await self._trigger_system_notification(
                    "manual_run_ended_genmaster_switch", {}
                )
            except Exception as e:
                logger.error(f"Failed to stop local-switch run on HOA leave-Run: {e}")
            return

        # CASE 2: operator moved the switch TO the Run position.
        if new_state == "run":
            if was_running:
                # Reclassify an existing automation-triggered run so it
                # continues past the auto trigger's release. We update
                # the system_state row directly; the run_history row's
                # trigger_type is the original value (manual reclassify
                # would lose the audit trail of who started it).
                logger.info(
                    f"HOA flipped to Run while generator running with "
                    f"trigger={current_trigger}; reclassifying current "
                    f"run trigger to local_switch_genmaster"
                )
                async with AsyncSessionLocal() as db:
                    state = await self._get_state(db)
                    state.run_trigger = "local_switch_genmaster"
                    await db.commit()
                await self.log_event(
                    "MANUAL_RUN_RECLASSIFIED_BY_HOA",
                    {
                        "old_trigger": current_trigger,
                        "new_trigger": "local_switch_genmaster",
                    },
                )
            else:
                # No active run — start one via the local switch trigger.
                # start_generator() enforces all guards (EPO, lockout, etc.)
                # and raises ValueError on policy refusals; broader excs
                # (DB integrity errors from a stale migration, network
                # failures, etc.) get caught + logged separately so they
                # don't get silently swallowed by the gpiozero-thread
                # dispatch path.
                logger.info(
                    "HOA flipped to Run; starting generator via local switch"
                )
                try:
                    await self.start_generator("local_switch_genmaster")
                    await self._trigger_system_notification(
                        "manual_run_started_genmaster_switch", {}
                    )
                except ValueError as e:
                    logger.warning(
                        f"HOA Run requested but start refused: {e}"
                    )
                    await self.log_event(
                        "HOA_RUN_START_REFUSED",
                        {"reason": str(e)},
                        severity="WARNING",
                    )
                except Exception:
                    logger.exception(
                        "HOA Run start raised an unexpected exception; "
                        "the generator did NOT start. This is usually a DB "
                        "constraint mismatch (migration not applied?) or a "
                        "network failure to GenSlave."
                    )
            return

        # CASE 3: operator moved the switch TO Quiet during an
        # automation-triggered run. Stop the run; Phase 4b's Quiet
        # guard will then block any new auto triggers until the
        # selector leaves Quiet.
        if (
            new_state == "quiet"
            and was_running
            and current_trigger in ("victron", "scheduled", "exercise")
        ):
            logger.info(
                f"HOA flipped to Quiet during {current_trigger}-triggered run; "
                f"stopping the auto-run"
            )
            try:
                await self.stop_generator("hoa_quiet")
            except Exception as e:
                logger.error(
                    f"Failed to stop auto-run on HOA -> Quiet: {e}"
                )

    async def fire_boot_hardware_state_notification(self) -> None:
        """One-shot startup notification describing the EPO + HOA state
        the system came up in (Phase 5b).

        Only fires when something is non-normal — EPO engaged or HOA not
        in Auto. A fully-normal boot (EPO released, HOA Auto) produces no
        notification.

        Called from main.py's lifespan via a short delayed task so the
        first GenSlave poll/heartbeat has had time to populate the EPO
        state. Uses the HOA monitor's *raw* state (the actual physical
        switch position) rather than its boot-delay-suppressed reported
        state — the boot delay governs whether we ACT on the switch, but
        this notification is purely informational.
        """
        from app.main import hoa_monitor

        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            epo_engaged = bool(state.slave_physical_safety_engaged)

        hoa_state = "auto"
        if hoa_monitor is not None:
            hoa_state = hoa_monitor.raw_state

        # Fully-normal boot — no news is good news.
        if not epo_engaged and hoa_state == "auto":
            logger.info(
                "Boot hardware state normal (EPO released, HOA Auto) — "
                "no boot-state notification"
            )
            return

        if epo_engaged and hoa_state == "run":
            msg = (
                "GenMaster is back online. The HOA selector is in RUN, but "
                "the GenSlave EPO is engaged — the generator will NOT start. "
                "Release the E-stop at the generator to allow it to run."
            )
        elif epo_engaged and hoa_state == "quiet":
            msg = (
                "GenMaster is back online. The HOA selector is in QUIET and "
                "the GenSlave EPO is engaged — the generator cannot run from "
                "any source until the E-stop is released."
            )
        elif epo_engaged:
            msg = (
                "GenMaster is back online. The GenSlave EPO is engaged — no "
                "generator runs (automatic or manual) will occur until the "
                "E-stop at the generator is released."
            )
        elif hoa_state == "run":
            msg = (
                "GenMaster is back online. The HOA selector is in RUN — the "
                "generator will start shortly, after the boot-delay window. "
                "Turn the selector to Auto if this is not intended."
            )
        elif hoa_state == "quiet":
            msg = (
                "GenMaster is back online. The HOA selector is in QUIET — "
                "automatic generator runs are suppressed. Turn the selector "
                "to Auto to resume normal automation."
            )
        else:  # hoa_state == "fault"
            msg = (
                "GenMaster is back online. The HOA selector is reporting a "
                "FAULT (both contacts closed) — check the switch wiring. "
                "The system is treating it as Auto until resolved."
            )

        await self._trigger_system_notification(
            "genmaster_boot_hardware_state", {"state_message": msg}
        )
        logger.info(f"Boot hardware-state notification fired: {msg}")

    # =========================================================================
    # HOA Quiet Override (Phase 4c)
    # =========================================================================

    def _is_quiet_override_active(self, state: SystemState) -> bool:
        """Pure check — is the operator's Quiet override currently in effect?

        True only if the flag is set AND the expiry timestamp is in the
        future. Does NOT mutate state; the lazy clear of an expired flag
        happens in get_quiet_override_status() (polled by the UI).

        Used by the HOA Quiet guards in start_generator() and
        handle_victron_signal_change() to let automation through while
        an override window is open.
        """
        if not state.quiet_override_active:
            return False
        if state.quiet_override_expires_at is None:
            return False
        return int(time.time()) < state.quiet_override_expires_at

    async def enable_quiet_override(self, duration_seconds: int) -> dict:
        """Enable the Quiet override for an operator-selected duration.

        Per failsafe.md decision #2 the duration is chosen by the
        operator every time — there is no default and no "continuous"
        option. The caller (the API endpoint) validates that
        duration_seconds is positive and within a sane bound.
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            now = int(time.time())
            expires_at = now + duration_seconds
            state.quiet_override_active = True
            state.quiet_override_expires_at = expires_at
            await db.commit()

        await self.log_event(
            "QUIET_OVERRIDE_ENABLED",
            {"duration_seconds": duration_seconds, "expires_at": expires_at},
        )
        await self._trigger_system_notification(
            "quiet_override_enabled",
            {"duration_minutes": duration_seconds // 60},
        )
        logger.info(
            f"Quiet override enabled for {duration_seconds}s "
            f"(expires at unix {expires_at})"
        )
        return {
            "active": True,
            "expires_at": expires_at,
            "seconds_remaining": duration_seconds,
        }

    async def get_quiet_override_status(self) -> dict:
        """Return the current Quiet override status.

        Lazily clears the flag when the window has passed — this method
        is polled by the UI every few seconds, so it doubles as the
        cleanup path. Quiet re-engages automatically once cleared.
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            now = int(time.time())
            active = bool(
                state.quiet_override_active
                and state.quiet_override_expires_at is not None
                and now < state.quiet_override_expires_at
            )

            # Lazy cleanup: flag set but window expired -> clear it so the
            # DB and UI reflect that Quiet has re-engaged.
            if state.quiet_override_active and not active:
                state.quiet_override_active = False
                state.quiet_override_expires_at = None
                await db.commit()
                logger.info(
                    "Quiet override window expired — Quiet mode re-engaged"
                )
                await self.log_event("QUIET_OVERRIDE_EXPIRED", {})

            seconds_remaining = (
                max(0, state.quiet_override_expires_at - now)
                if active and state.quiet_override_expires_at is not None
                else 0
            )
            return {
                "active": active,
                "expires_at": state.quiet_override_expires_at if active else None,
                "seconds_remaining": seconds_remaining,
            }

    async def clear_quiet_override(self, reason: str = "operator_cancel") -> dict:
        """Explicitly clear an active Quiet override.

        Two callers:
          * the operator clicking "Cancel Override" in the web UI
            (reason="operator_cancel")
          * the state machine when the HOA selector leaves Quiet — the
            override is moot once Quiet itself is gone, so it shouldn't
            dangle (reason="hoa_left_quiet")

        Idempotent — safe to call when no override is active; only logs
        an event when it actually cleared something.
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            was_active = state.quiet_override_active
            state.quiet_override_active = False
            state.quiet_override_expires_at = None
            await db.commit()

        if was_active:
            await self.log_event("QUIET_OVERRIDE_CANCELLED", {"reason": reason})
            logger.info(f"Quiet override cleared (reason: {reason})")

        return {"active": False, "expires_at": None, "seconds_remaining": 0}

    # =========================================================================
    # Override Operations
    # =========================================================================

    async def enable_override(self, override_type: str) -> None:
        """
        Enable manual override.

        Args:
            override_type: 'force_run' or 'force_stop'
        """
        if override_type not in ("force_run", "force_stop"):
            raise ValueError(f"Invalid override type: {override_type}")

        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            state.override_enabled = True
            state.override_type = override_type
            await db.commit()

            logger.info(f"Override enabled: {override_type}")

            # Take action based on override type
            if override_type == "force_run" and not state.generator_running:
                await self.start_generator("manual")
            elif override_type == "force_stop" and state.generator_running:
                await self.stop_generator("override")

            await self.log_event("OVERRIDE_ENABLED", {"type": override_type})
            await self._send_webhook("override.enabled", {"type": override_type})
            await self._trigger_system_notification("override_enabled", {"type": override_type})

    async def disable_override(self) -> str:
        """
        Disable manual override.

        Returns:
            The previous override type
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            previous_type = state.override_type
            state.override_enabled = False
            state.override_type = "none"
            await db.commit()

            logger.info(f"Override disabled (was: {previous_type})")

            await self.log_event("OVERRIDE_DISABLED", {"previous_type": previous_type})
            await self._send_webhook("override.disabled", {"previous_type": previous_type})
            await self._trigger_system_notification("override_disabled", {"previous_type": previous_type})

            return previous_type

    # =========================================================================
    # Arm Status (cached from heartbeat - GenSlave is source of truth)
    # =========================================================================

    async def get_arm_status(self) -> dict:
        """Get current relay arm status."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return {
                "armed": state.slave_relay_armed or False,
                "slave_connection": state.slave_connection_status,
            }

    async def is_armed(self) -> bool:
        """Check if relay is armed."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return state.slave_relay_armed or False

    async def update_slave_physical_safety_from_poll(self, new_value: bool) -> None:
        """Update the cached EPO state from a fast-poll response.

        Called by slave_status_service after each successful relay-state
        poll (every few seconds). Lets the UI react to EPO transitions
        within sub-heartbeat-interval latency rather than waiting up to
        ~60s for the next push-heartbeat to land.

        Short-circuits when the value is unchanged so the steady-state
        (no EPO transitions) imposes zero DB write traffic.
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            if state.slave_physical_safety_engaged == new_value:
                return  # no transition, skip the write
            old_value = state.slave_physical_safety_engaged
            state.slave_physical_safety_engaged = new_value
            await db.commit()
            logger.info(
                f"GenSlave EPO state synced from fast-poll: "
                f"{old_value} -> {new_value}"
            )

        # Fire the operator notification on the EPO transition. Done after
        # the session closes so a slow notification target can't hold a DB
        # connection open. _trigger_system_notification is exception-safe.
        await self._trigger_system_notification(
            "hardware_safety_engaged_genslave"
            if new_value
            else "hardware_safety_released_genslave",
            {},
        )

    async def set_armed_state(self, armed: bool, manual: bool = True) -> None:
        """
        Set the relay armed state in the database.

        This is called when the user explicitly arms/disarms via the UI,
        ensuring GenMaster's database tracks the intended armed state.
        The heartbeat will then sync this to GenSlave.

        Args:
            armed: True to arm, False to disarm
            manual: True if this is a manual action from the user (default)
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            state.slave_relay_armed = armed

            # Track manual disarm/arm for auto-arm feature
            if manual:
                if armed:
                    # Manual arm clears the manual_disarm_active flag
                    state.manual_disarm_active = False
                    logger.info("Manual arm - clearing manual_disarm_active flag")
                else:
                    # Manual disarm sets the flag to prevent auto-arm
                    state.manual_disarm_active = True
                    logger.info("Manual disarm - setting manual_disarm_active flag")

            await db.commit()
            logger.info(f"Relay armed state set to {armed} in GenMaster database (manual={manual})")

    # =========================================================================
    # Heartbeat/Communication Operations
    # =========================================================================

    async def update_heartbeat_status(
        self,
        success: bool,
        slave_status: Optional[dict] = None,
        latency_ms: Optional[float] = None,
    ) -> None:
        """
        Update heartbeat/communication status.

        Args:
            success: Whether heartbeat was successful
            slave_status: Status returned by GenSlave
            latency_ms: Round-trip latency
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            config = await self._get_config(db)

            now = int(time.time())
            state.last_heartbeat_sent = now

            if success:
                state.last_heartbeat_received = now
                previous_missed = state.missed_heartbeat_count
                state.missed_heartbeat_count = 0

                # Update slave relay state if provided
                if slave_status:
                    if "relay_state" in slave_status:
                        state.slave_relay_state = slave_status["relay_state"]

                    # GenSlave hardware E-stop state. Added in Phase 2; older
                    # GenSlave builds (pre-physical_safety_engaged) will omit
                    # this key and we leave the cached value alone, so a
                    # version skew during a rolling deploy degrades gracefully.
                    if "physical_safety_engaged" in slave_status:
                        state.slave_physical_safety_engaged = slave_status[
                            "physical_safety_engaged"
                        ]

                    # Handle armed state carefully — GenMaster is authoritative
                    # for the armed flag. The heartbeat reply from GenSlave can
                    # carry a stale `armed` value (the reply is composed before
                    # GenSlave processes the in-bound heartbeat that would tell
                    # it to disarm), so we must NEVER adopt GenSlave's value.
                    # Just log the mismatch — the next heartbeat we send carries
                    # the correct value and GenSlave's failsafe.record_heartbeat
                    # will sync the slave to match GenMaster.
                    if "armed" in slave_status:
                        master_armed = state.slave_relay_armed or False
                        slave_armed = slave_status["armed"]

                        if master_armed and not slave_armed:
                            logger.warning(
                                "Armed state mismatch: GenMaster=True, GenSlave=False. "
                                "Keeping GenMaster state — next heartbeat will re-sync GenSlave."
                            )
                        elif not master_armed and slave_armed:
                            logger.warning(
                                "Armed state mismatch: GenMaster=False, GenSlave=True. "
                                "Keeping GenMaster state (e.g. fail_safe boot disarm) — "
                                "next heartbeat will tell GenSlave to disarm."
                            )
                        # else: states match, no update needed

                # Check if connection was restored or established for the first time
                if state.slave_connection_status in ("disconnected", "unknown"):
                    was_disconnected = state.slave_connection_status == "disconnected"
                    state.slave_connection_status = "connected"

                    if was_disconnected:
                        logger.info("GenSlave connection restored")
                        await self.log_event("COMMUNICATION_RESTORED", {"latency_ms": latency_ms})
                        await self._send_webhook("communication.restored", {})
                    else:
                        logger.info("GenSlave connection established (first connect)")
                        await self.log_event("COMMUNICATION_ESTABLISHED", {"latency_ms": latency_ms})

                    # No explicit auto-arm step needed: GenMaster's DB still
                    # holds the operator's intended armed state (user only
                    # changes it via the UI). The next heartbeat to GenSlave
                    # carries that value, and GenSlave's failsafe.record_heartbeat
                    # syncs the local _armed flag accordingly.

                    if was_disconnected:
                        # Determine relay status for notification based on
                        # GenMaster's DB armed state (the source of truth).
                        if state.slave_relay_armed:
                            relay_status = "ENABLED"
                            relay_warning = ""
                        else:
                            relay_status = "DISABLED"
                            relay_warning = "WARNING: Generator relay is currently disabled."
                        await self._trigger_system_notification(
                            "genslave_comm_restored",
                            {
                                "latency_ms": latency_ms,
                                "relay_status": relay_status,
                                "relay_warning": relay_warning,
                            },
                        )

            else:
                state.missed_heartbeat_count += 1

                # Check if threshold exceeded
                if (
                    state.missed_heartbeat_count >= config.heartbeat_failure_threshold
                    and state.slave_connection_status != "disconnected"
                ):
                    state.slave_connection_status = "disconnected"
                    logger.warning(
                        f"GenSlave connection lost after {state.missed_heartbeat_count} "
                        f"missed heartbeats"
                    )
                    await self.log_event(
                        "COMMUNICATION_LOST",
                        {"missed_count": state.missed_heartbeat_count},
                        severity="WARNING",
                    )
                    await self._send_webhook(
                        "communication.lost",
                        {"missed_count": state.missed_heartbeat_count},
                    )
                    from datetime import datetime
                    await self._trigger_system_notification(
                        "genslave_comm_lost",
                        {
                            "missed_count": state.missed_heartbeat_count,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        },
                    )

            await db.commit()

    # =========================================================================
    # Status Getters
    # =========================================================================

    async def get_generator_status(self) -> GeneratorStatus:
        """Get current generator status."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            runtime = None
            if state.generator_running and state.generator_start_time:
                runtime = int(time.time()) - state.generator_start_time

            return GeneratorStatus(
                running=state.generator_running,
                start_time=state.generator_start_time,
                runtime_seconds=runtime,
                trigger=state.run_trigger,
                current_run_id=state.current_run_id,
            )

    async def get_override_status(self) -> OverrideStatus:
        """Get current override status."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return OverrideStatus(
                enabled=state.override_enabled,
                override_type=state.override_type,
            )

    async def get_slave_health(self) -> SlaveHealth:
        """Get GenSlave health status."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return SlaveHealth(
                connection_status=state.slave_connection_status,
                last_heartbeat_sent=state.last_heartbeat_sent,
                last_heartbeat_received=state.last_heartbeat_received,
                missed_heartbeat_count=state.missed_heartbeat_count,
                relay_state=state.slave_relay_state,
                physical_safety_engaged=state.slave_physical_safety_engaged,
            )

    async def get_victron_status(self, mock_mode: bool = False) -> VictronStatus:
        """Get Victron relay input status."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return VictronStatus(
                signal_state=state.victron_signal_state,
                last_change=state.victron_last_change,
                gpio_pin=17,
                mock_mode=mock_mode,
            )

    async def get_hoa_status(self) -> HOAStatus:
        """Get HOA selector status from the running HOA monitor.

        Imported lazily to avoid a top-level circular dependency between
        state_machine and main.py (where the singleton is created).
        Returns a synthesized 'auto/disabled' snapshot if the monitor
        hasn't been started yet — keeps /api/system/status responsive
        during the brief startup window before lifespan finishes.
        """
        from app.main import hoa_monitor

        if hoa_monitor is None:
            return HOAStatus(
                state="auto",
                raw_state="auto",
                hoa_monitor_running=False,
                enabled=settings.hoa_switch_enabled,
                mock_mode=settings.is_mock_gpio,
                boot_delay_active=False,
                boot_delay_seconds=settings.hoa_boot_delay_seconds,
                boot_complete_at=None,
                raw_quiet_pressed=False,
                raw_run_pressed=False,
                gpio_quiet=settings.hoa_gpio_quiet,
                gpio_run=settings.hoa_gpio_run,
                state_change_count=0,
                last_state_change_at=None,
            )
        return HOAStatus(**hoa_monitor.get_status())

    async def get_full_status(self, system_health: SystemHealth) -> FullSystemStatus:
        """Get complete system status."""
        return FullSystemStatus(
            generator=await self.get_generator_status(),
            victron=await self.get_victron_status(),
            hoa=await self.get_hoa_status(),
            slave_health=await self.get_slave_health(),
            override=await self.get_override_status(),
            system_health=system_health,
            relay_armed=await self.is_armed(),
            timestamp=int(time.time()),
        )

    # =========================================================================
    # Event Logging
    # =========================================================================

    async def log_event(
        self,
        event_type: str,
        data: Optional[dict[str, Any]] = None,
        severity: str = "INFO",
    ) -> None:
        """Log an event to the database."""
        async with AsyncSessionLocal() as db:
            await EventLog.log(db, event_type, data, severity)

    # =========================================================================
    # Webhook Sending
    # =========================================================================

    async def _send_webhook(self, event: str, data: dict[str, Any]) -> None:
        """Send a webhook notification."""
        if self._webhook_service:
            try:
                await self._webhook_service.send(event, data)
            except Exception as e:
                logger.error(f"Failed to send webhook: {e}")

    async def _trigger_system_notification(
        self,
        event_type: str,
        event_data: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Trigger a system notification for the given event type.

        Args:
            event_type: The event type (e.g., "generator_started")
            event_data: Data to use for template variable substitution
        """
        try:
            engine = get_notification_engine()
            async with AsyncSessionLocal() as db:
                result = await engine.trigger_notification(
                    db=db,
                    event_type=event_type,
                    event_data=event_data or {},
                )
                if result.success:
                    logger.debug(f"System notification sent for {event_type}")
                elif result.status == "suppressed":
                    logger.debug(f"System notification suppressed for {event_type}: {result.suppression_reason}")
                else:
                    logger.warning(f"System notification failed for {event_type}: {result.error_message}")
        except Exception as e:
            logger.error(f"Failed to trigger system notification: {e}")

    # =========================================================================
    # Runtime Lockout/Cooldown Operations
    # =========================================================================

    async def check_runtime_lockout(self) -> bool:
        """
        Check if runtime lockout blocks starting the generator.

        Returns:
            True if lockout is active and blocks start
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return state.runtime_lockout_active

    async def check_cooldown_active(self) -> bool:
        """
        Check if cooldown is active and not yet expired.

        Returns:
            True if cooldown is active and not expired
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            if not state.cooldown_active:
                return False
            return not state.is_cooldown_expired()

    async def activate_runtime_lockout(self, reason: str) -> None:
        """
        Activate runtime lockout requiring manual acknowledgment.

        Args:
            reason: Reason for the lockout (e.g., "max_runtime_reached")
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            state.runtime_lockout_active = True
            state.runtime_lockout_started = int(time.time())
            state.runtime_lockout_reason = reason

            await db.commit()

            logger.warning(f"Runtime lockout activated: {reason}")
            await self.log_event(
                "RUNTIME_LOCKOUT_ACTIVATED",
                {"reason": reason},
                severity="WARNING",
            )
            await self._send_webhook(
                "runtime.lockout.activated",
                {"reason": reason},
            )

    async def activate_cooldown(self, duration_minutes: int) -> None:
        """
        Activate cooldown period before generator can be restarted.

        Args:
            duration_minutes: Duration of cooldown in minutes
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            end_time = int(time.time()) + (duration_minutes * 60)
            state.cooldown_active = True
            state.cooldown_end_time = end_time

            await db.commit()

            logger.info(f"Cooldown activated for {duration_minutes} minutes")
            await self.log_event(
                "COOLDOWN_ACTIVATED",
                {"duration_minutes": duration_minutes, "end_time": end_time},
            )
            await self._send_webhook(
                "runtime.cooldown.activated",
                {"duration_minutes": duration_minutes, "end_time": end_time},
            )

    async def clear_runtime_lockout(self) -> bool:
        """
        Clear runtime lockout after user acknowledgment.

        Returns:
            True if lockout was cleared, False if wasn't active
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            if not state.runtime_lockout_active:
                return False

            state.runtime_lockout_active = False
            state.runtime_lockout_started = None
            state.runtime_lockout_reason = None

            await db.commit()

            logger.info("Runtime lockout cleared by user acknowledgment")
            await self.log_event("RUNTIME_LOCKOUT_CLEARED", {})
            await self._send_webhook("runtime.lockout.cleared", {})

            return True

    async def clear_cooldown(self) -> bool:
        """
        Clear cooldown period.

        Returns:
            True if cooldown was cleared, False if wasn't active
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            if not state.cooldown_active:
                return False

            state.cooldown_active = False
            state.cooldown_end_time = None

            await db.commit()

            logger.info("Cooldown cleared")
            await self.log_event("COOLDOWN_CLEARED", {})
            await self._send_webhook("runtime.cooldown.cleared", {})

            return True

    async def get_runtime_limits_status(self) -> dict:
        """
        Get current runtime limits status.

        Returns:
            Dict with configuration and lockout/cooldown state
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            config = await self._get_config(db)

            cooldown_remaining = None
            if state.cooldown_active and state.cooldown_end_time:
                remaining = state.cooldown_end_time - int(time.time())
                cooldown_remaining = max(0, remaining)

            return {
                "enabled": config.runtime_limits_enabled,
                "min_run_minutes": config.min_run_minutes,
                "max_run_minutes": config.max_run_minutes,
                "max_runtime_action": config.max_runtime_action,
                "cooldown_duration_minutes": config.cooldown_duration_minutes,
                "lockout_active": state.runtime_lockout_active,
                "lockout_started": state.runtime_lockout_started,
                "lockout_reason": state.runtime_lockout_reason,
                "cooldown_active": state.cooldown_active,
                "cooldown_end_time": state.cooldown_end_time,
                "cooldown_remaining_seconds": cooldown_remaining,
            }

    async def handle_cooldown_expiry(self) -> None:
        """
        Handle cooldown expiry - clear cooldown and check if Victron signal
        should restart the generator.
        """
        await self.clear_cooldown()

        # Check if Victron signal is still active and should restart
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            config = await self._get_config(db)

            if (
                state.victron_signal_state
                and state.slave_relay_armed
                and not state.override_enabled
                and config.runtime_limits_enabled
            ):
                logger.info(
                    "Cooldown expired with Victron signal active - "
                    "checking if generator should restart"
                )
                # Don't auto-restart here, let the normal Victron signal handler
                # take care of it on next check
