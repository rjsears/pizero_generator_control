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

    async def _get_slave_client(self):
        """Get a SlaveClient instance with current config."""
        from app.models import Config
        from app.services.slave_client import SlaveClient

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Config).where(Config.id == 1))
            config = result.scalar_one_or_none()

        if config:
            if config.genslave_ip:
                base_url = f"http://{config.genslave_ip}:8001"
            else:
                base_url = config.slave_api_url
            return SlaveClient(base_url=base_url, secret=config.slave_api_secret)
        else:
            from app.config import settings
            return SlaveClient(base_url=settings.slave_api_url, secret=settings.slave_api_secret)

    async def initialize(self) -> None:
        """
        Initialize state machine from database.

        On boot, we reset certain states for safety:
        - slave_relay_armed = False (require operator to re-arm)
        - slave_connection_status = "unknown" (will be updated by heartbeat)
        - If generator_running was True, mark it as needing reconciliation
        """
        async with AsyncSessionLocal() as db:
            # Ensure system_state row exists
            state = await SystemState.get_instance(db)

            # Log pre-boot state for debugging
            logger.info(
                f"Pre-boot state - "
                f"generator_running: {state.generator_running}, "
                f"relay_armed: {state.slave_relay_armed}, "
                f"slave_status: {state.slave_connection_status}"
            )

            # Check if we had a running generator before crash/reboot
            was_running = state.generator_running

            # Preserve armed state across reboots - GenSlave maintains actual state
            if state.slave_relay_armed:
                logger.info("Relay was armed before reboot - preserving armed state")

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
                    if run and not run.end_time:
                        run.end_time = int(time.time())
                        run.stop_reason = "power_loss"
                        run.notes = (run.notes or "") + " [Ended due to power loss/reboot]"
                        logger.info(f"Closed orphaned run {run.id} due to power loss")
                state.current_run_id = None

            await db.commit()

            logger.info(
                f"State machine initialized - "
                f"generator_running: {state.generator_running}, "
                f"relay_armed: {state.slave_relay_armed}, "
                f"override: {state.override_enabled}"
            )

            # Log event for reboot
            await self.log_event(
                "SYSTEM_BOOT_RESET",
                {
                    "was_running": was_running,
                    "relay_disarmed": True,
                    "reason": "Safety reset on boot",
                },
                severity="WARNING" if was_running else "INFO",
            )

            self._initialized = True

    async def reconcile_with_slave(self, slave_client) -> dict:
        """
        Reconcile GenMaster state with GenSlave's actual state.

        Called during startup to ensure state consistency after reboot.
        This queries GenSlave for its actual relay state and updates
        our records accordingly.

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

                # Update our record of slave's relay state and armed state
                state.slave_relay_state = result["relay_state"]
                state.slave_relay_armed = result["slave_armed"]

                # If slave's relay is ON but we think generator is stopped,
                # we have a mismatch - log it but don't auto-start
                if result["relay_state"] and not state.generator_running:
                    logger.warning(
                        "Reconciliation: GenSlave relay is ON but GenMaster "
                        "shows generator stopped - relay may have been left on"
                    )
                    result["message"] = (
                        "WARNING: GenSlave relay is ON but no active run in GenMaster. "
                        "Manual intervention may be required."
                    )
                    await self.log_event(
                        "RECONCILIATION_MISMATCH",
                        {
                            "slave_relay": result["relay_state"],
                            "master_generator_running": state.generator_running,
                        },
                        severity="WARNING",
                    )
                else:
                    result["message"] = "State reconciliation complete"

                # Update connection status since we successfully reached slave
                state.slave_connection_status = "connected"
                state.missed_heartbeat_count = 0

                await db.commit()

            result["success"] = True
            logger.info(
                f"Reconciliation complete - slave relay: {result['relay_state']}, "
                f"slave armed: {result['slave_armed']}"
            )

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
                if not state.can_start_generator():
                    if state.generator_running:
                        raise ValueError("Generator is already running")
                    if state.override_enabled and state.override_type == "force_stop":
                        raise ValueError("Cannot start - force_stop override is active")
                    if state.slave_connection_status == "disconnected":
                        raise ValueError("Cannot start - GenSlave is disconnected")
                    if state.runtime_lockout_active:
                        raise ValueError(
                            "Cannot start - runtime lockout is active. "
                            "Clear the lockout first."
                        )
                    raise ValueError("Generator cannot be started in current state")

                # Turn on the relay via GenSlave
                # GenSlave will reject if relay is not armed
                slave_client = await self._get_slave_client()
                try:
                    relay_response = await slave_client.relay_on()
                finally:
                    await slave_client.close()
                if not relay_response.success:
                    error_msg = relay_response.error or "Unknown error"
                    # Provide helpful message if GenSlave rejected due to not being armed
                    if "not armed" in error_msg.lower():
                        raise ValueError("Cannot start - GenSlave relay is not armed. Arm the relay first.")
                    raise ValueError(f"Failed to turn on relay: {error_msg}")

                logger.info("GenSlave relay turned ON")

                # Update the slave status cache immediately
                slave_status_service = get_slave_status_service()
                await slave_status_service.update_relay_state(relay_on=True)

                # Fetch generator info for fuel tracking
                gen_info = await GeneratorInfo.get_instance(db)
                fuel_type = gen_info.fuel_type
                load_expected = gen_info.load_expected
                consumption_rate = gen_info.get_consumption_rate()

                # Create run record with fuel tracking data
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

                # Update system state
                state.generator_running = True
                state.generator_start_time = start_time
                state.current_run_id = run.id
                state.run_trigger = trigger

                await db.commit()
                await db.refresh(run)

                logger.info(f"Generator started - trigger: {trigger}, run_id: {run.id}")

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

                # Turn off the relay via GenSlave
                slave_client = await self._get_slave_client()
                try:
                    relay_response = await slave_client.relay_off()
                    if not relay_response.success:
                        logger.error(f"Failed to turn off relay: {relay_response.error}")
                        # Continue anyway to update state - relay may already be off
                finally:
                    await slave_client.close()

                logger.info("GenSlave relay turned OFF")

                # Update the slave status cache immediately
                slave_status_service = get_slave_status_service()
                await slave_status_service.update_relay_state(relay_on=False)

                stop_time = int(time.time())
                run_id = state.current_run_id

                # Update run record if exists
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

                # Update system state
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
                from datetime import datetime
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

    async def _auto_arm_relay(self) -> bool:
        """
        Automatically arm the relay on connection restore.

        This is called when auto-arm is enabled and the connection is restored.
        It sends the arm command to GenSlave and updates local state.

        Returns:
            True if auto-arm succeeded, False otherwise
        """
        try:
            slave_client = await self._get_slave_client()
            try:
                response = await slave_client.arm_relay()
            finally:
                await slave_client.close()

            if response.success:
                # Update local state (not a manual action)
                await self.set_armed_state(armed=True, manual=False)
                logger.info("Auto-armed relay on connection restore")
                await self.log_event(
                    "RELAY_AUTO_ARMED",
                    {"reason": "connection_restored"},
                )
                await self._send_webhook("relay.auto_armed", {"reason": "connection_restored"})
                return True
            else:
                logger.warning(f"Auto-arm failed: {response.error}")
                await self.log_event(
                    "RELAY_AUTO_ARM_FAILED",
                    {"error": response.error},
                    severity="WARNING",
                )
                return False
        except Exception as e:
            logger.error(f"Auto-arm error: {e}")
            await self.log_event(
                "RELAY_AUTO_ARM_ERROR",
                {"error": str(e)},
                severity="ERROR",
            )
            return False

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

                    # Handle armed state carefully - GenMaster is authoritative
                    if "armed" in slave_status:
                        master_armed = state.slave_relay_armed or False
                        slave_armed = slave_status["armed"]

                        if master_armed and not slave_armed:
                            # GenMaster expects armed but GenSlave reports disarmed
                            # This is a sync issue - keep GenMaster's state, next heartbeat will re-push
                            logger.warning(
                                "Armed state mismatch: GenMaster=True, GenSlave=False. "
                                "Keeping GenMaster state - next heartbeat will re-sync GenSlave."
                            )
                            # Don't update - keep master's armed state
                        elif not master_armed and slave_armed:
                            # GenSlave armed by external means - adopt that state
                            logger.info(
                                "GenSlave armed externally, updating GenMaster to match"
                            )
                            state.slave_relay_armed = True
                        # else: states match, no update needed

                # Check if connection was restored
                if state.slave_connection_status == "disconnected":
                    state.slave_connection_status = "connected"
                    logger.info("GenSlave connection restored")
                    await self.log_event("COMMUNICATION_RESTORED", {"latency_ms": latency_ms})
                    await self._send_webhook("communication.restored", {})

                    # Check if auto-arm should trigger
                    if config.auto_arm_relay_on_connect and not state.manual_disarm_active:
                        logger.info("Auto-arm enabled and no manual disarm - triggering auto-arm")
                        # Commit current state before auto-arm (connection status update)
                        await db.commit()
                        # Auto-arm is async and may take time, do it outside the db session
                        asyncio.create_task(self._auto_arm_relay())
                    elif config.auto_arm_relay_on_connect and state.manual_disarm_active:
                        logger.info(
                            "Auto-arm enabled but manual_disarm_active is set - "
                            "skipping auto-arm (respecting user's manual disarm)"
                        )

                    relay_status = "ENABLED" if state.slave_relay_armed else "DISABLED"
                    relay_warning = "" if state.slave_relay_armed else "WARNING: Generator relay is currently disabled."
                    await self._trigger_system_notification(
                        "genslave_comm_restored",
                        {
                            "latency_ms": latency_ms,
                            "relay_status": relay_status,
                            "relay_warning": relay_warning,
                        },
                    )
                elif state.slave_connection_status == "unknown":
                    state.slave_connection_status = "connected"

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
