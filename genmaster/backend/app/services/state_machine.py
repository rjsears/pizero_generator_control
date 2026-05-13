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

from app.database import AsyncSessionLocal
from app.models import Config, EventLog, GeneratorInfo, GeneratorRun, SystemState
from app.schemas import (
    FullSystemStatus,
    GeneratorStatus,
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

                # Check each condition individually for clearer error messages
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
                    "comm_loss": "Communication loss",
                    "override": "Override activated",
                    "error": "Error occurred",
                    "max_runtime": "Max runtime exceeded",
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

    async def get_full_status(self, system_health: SystemHealth) -> FullSystemStatus:
        """Get complete system status."""
        return FullSystemStatus(
            generator=await self.get_generator_status(),
            victron=await self.get_victron_status(),
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
