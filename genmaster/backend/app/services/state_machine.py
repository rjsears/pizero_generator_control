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

import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import AsyncSessionLocal
from app.models import Config, EventLog, GeneratorRun, SystemState
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

logger = logging.getLogger(__name__)


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
        - automation_armed = False (require operator to re-arm)
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
                f"automation_armed: {state.automation_armed}, "
                f"slave_status: {state.slave_connection_status}"
            )

            # Check if we had a running generator before crash/reboot
            was_running = state.generator_running

            # SAFETY: Always disarm on boot - require operator to re-arm
            if state.automation_armed:
                logger.warning(
                    "Automation was armed before reboot - disarming for safety"
                )
                state.automation_armed = False
                state.automation_armed_at = None
                state.automation_armed_by = None

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
                f"automation_armed: {state.automation_armed}, "
                f"override: {state.override_enabled}"
            )

            # Log event for reboot
            await self.log_event(
                "SYSTEM_BOOT_RESET",
                {
                    "was_running": was_running,
                    "automation_disarmed": True,
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
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            # Validate state transition
            if not state.can_start_generator():
                if not state.slave_relay_armed:
                    raise ValueError("Cannot start - GenSlave relay is not armed")
                if state.generator_running:
                    raise ValueError("Generator is already running")
                if state.override_enabled and state.override_type == "force_stop":
                    raise ValueError("Cannot start - force_stop override is active")
                if state.slave_connection_status == "disconnected":
                    raise ValueError("Cannot start - GenSlave is disconnected")
                raise ValueError("Generator cannot be started in current state")

            # Turn on the relay via GenSlave
            slave_client = await self._get_slave_client()
            relay_response = await slave_client.relay_on()
            if not relay_response.success:
                raise ValueError(f"Failed to turn on relay: {relay_response.error}")

            logger.info("GenSlave relay turned ON")

            # Create run record
            start_time = int(time.time())
            run = GeneratorRun(
                start_time=start_time,
                trigger_type=trigger,
                scheduled_run_id=scheduled_run_id,
                notes=notes,
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
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            if not state.generator_running:
                logger.warning("Attempted to stop generator that isn't running")
                return None

            # Turn off the relay via GenSlave
            slave_client = await self._get_slave_client()
            relay_response = await slave_client.relay_off()
            if not relay_response.success:
                logger.error(f"Failed to turn off relay: {relay_response.error}")
                # Continue anyway to update state - relay may already be off

            logger.info("GenSlave relay turned OFF")

            stop_time = int(time.time())
            run_id = state.current_run_id

            # Update run record if exists
            run = None
            if run_id:
                from sqlalchemy.future import select

                result = await db.execute(
                    select(GeneratorRun).where(GeneratorRun.id == run_id)
                )
                run = result.scalar_one_or_none()
                if run:
                    run.complete(stop_time, reason)

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

            return run

    async def handle_victron_signal_change(self, signal_active: bool) -> None:
        """
        Handle Victron relay signal change.

        Args:
            signal_active: True if generator is wanted, False otherwise
        """
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

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
    # Automation Arming Operations
    # =========================================================================

    async def arm_automation(self, source: str = "api") -> dict:
        """
        Arm the automation system, enabling all automated actions.

        Args:
            source: What initiated the arm request ('api', 'ui', 'startup')

        Returns:
            Dict with armed status, warnings, and any messages
        """
        warnings = []

        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            # Check if already armed
            if state.automation_armed:
                return {
                    "success": True,
                    "armed": True,
                    "message": "Automation already armed",
                    "armed_at": state.automation_armed_at,
                    "warnings": [],
                }

            # Check GenSlave connection status
            if state.slave_connection_status == "disconnected":
                warnings.append(
                    "GenSlave is disconnected - automation may not function correctly"
                )
            elif state.slave_connection_status == "unknown":
                warnings.append(
                    "GenSlave connection status unknown - recommend verifying connection first"
                )

            # Arm the system
            now = int(time.time())
            state.automation_armed = True
            state.automation_armed_at = now
            state.automation_armed_by = source
            await db.commit()

            logger.info(f"Automation armed by {source}")

            await self.log_event(
                "AUTOMATION_ARMED",
                {
                    "source": source,
                    "slave_status": state.slave_connection_status,
                    "warnings": warnings,
                },
            )
            await self._send_webhook(
                "automation.armed",
                {"source": source, "armed_at": now},
            )

            return {
                "success": True,
                "armed": True,
                "message": "Automation armed successfully",
                "armed_at": now,
                "warnings": warnings,
            }

    async def disarm_automation(self, source: str = "api") -> dict:
        """
        Disarm the automation system, blocking all automated actions.

        If the generator is running, it will NOT be stopped automatically.
        The operator should manually stop it if needed.

        Args:
            source: What initiated the disarm request

        Returns:
            Dict with armed status and any messages
        """
        warnings = []

        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)

            # Check if already disarmed
            if not state.automation_armed:
                return {
                    "success": True,
                    "armed": False,
                    "message": "Automation already disarmed",
                    "armed_at": None,
                    "warnings": [],
                }

            # Warn if generator is running
            if state.generator_running:
                warnings.append(
                    "Generator is currently running - it will NOT be stopped automatically. "
                    "Use manual stop if needed."
                )

            # Disarm the system
            state.automation_armed = False
            previous_armed_at = state.automation_armed_at
            state.automation_armed_at = None
            state.automation_armed_by = None
            await db.commit()

            logger.info(f"Automation disarmed by {source}")

            await self.log_event(
                "AUTOMATION_DISARMED",
                {
                    "source": source,
                    "generator_was_running": state.generator_running,
                    "was_armed_since": previous_armed_at,
                },
            )
            await self._send_webhook(
                "automation.disarmed",
                {"source": source, "generator_running": state.generator_running},
            )

            return {
                "success": True,
                "armed": False,
                "message": "Automation disarmed",
                "armed_at": None,
                "warnings": warnings,
            }

    async def get_arm_status(self) -> dict:
        """Get current automation arm status."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return {
                "armed": state.automation_armed,
                "armed_at": state.automation_armed_at,
                "armed_by": state.automation_armed_by,
                "slave_connection": state.slave_connection_status,
            }

    async def is_armed(self) -> bool:
        """Check if automation is armed."""
        async with AsyncSessionLocal() as db:
            state = await self._get_state(db)
            return state.automation_armed

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

                # Update slave relay state and armed state if provided
                if slave_status:
                    if "relay_state" in slave_status:
                        state.slave_relay_state = slave_status["relay_state"]
                    if "armed" in slave_status:
                        state.slave_relay_armed = slave_status["armed"]

                # Check if connection was restored
                if state.slave_connection_status == "disconnected":
                    state.slave_connection_status = "connected"
                    logger.info("GenSlave connection restored")
                    await self.log_event("COMMUNICATION_RESTORED", {"latency_ms": latency_ms})
                    await self._send_webhook("communication.restored", {})
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
            automation_armed=await self.is_armed(),
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
