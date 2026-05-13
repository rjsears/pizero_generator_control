# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/services/hardware_safety.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - May 13th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Hardware safety interlock monitor for GenSlave.

Watches the physical E-stop wired to Auto Hat Mini IN1. The E-stop has a
DPDT-style contact block: one NC contact wired in series with the relay
output (physical, hardware-enforced lockout — independent of this code)
and one NO contact wired through the HAT's 5V terminal to IN1 for software
signaling. When the E-stop is pressed:

  * NC contact opens  → relay output wire is physically broken; the
    generator cannot start regardless of what software does.
  * NO contact closes → 5V appears at IN1 → this monitor reads HIGH →
    we drop the relay command in software so internal state matches
    physical reality.

The hardware NC contact is the actual safety guarantee. This monitor is
the software-side mirror: it keeps internal relay/state consistent with
what the hardware is actually doing, and (Phase 2) reports the engaged
flag to GenMaster via heartbeat so the state machine refuses new runs
until the operator explicitly releases and re-arms.

Polarity reminder: Auto Hat Mini buffered inputs are opto-isolated and
trigger on APPLIED VOLTAGE, not on being grounded. Wiring is therefore
HAT-5V → NO COM → NO terminal → IN1. Reading True from
`automationhat.input.one.read()` means voltage is present, which in our
wiring means the E-stop is pressed.
"""

import asyncio
import logging
import time
from typing import Optional

from app.config import settings
from app.services.relay import HAT_AVAILABLE, automationhat

logger = logging.getLogger(__name__)


class HardwareSafetyMonitor:
    """Polls Auto Hat Mini IN1 for the hardware safety E-stop switch.

    Independent of FailsafeMonitor (which watches GenMaster heartbeat
    timeouts). Both can drop the relay; they do so for different reasons.
    """

    # Poll at 25ms and require two consecutive matching reads to debounce
    # mechanical bounce on the E-stop contacts. Effective worst-case
    # detection latency ≈ 50ms, which is well below human-perceivable for
    # a maintenance-grade safety control. Constants here rather than in
    # config because tuning these is a development concern, not an
    # operator concern; promote to settings only if a real need emerges.
    POLL_INTERVAL_SEC: float = 0.025
    DEBOUNCE_READS: int = 2

    def __init__(self) -> None:
        self._relay_service = None
        self._engaged: bool = False              # debounced public state
        self._raw_last: bool = False             # most recent raw read
        self._stable_count: int = 0              # consecutive matching reads
        self._engaged_at: Optional[int] = None
        self._released_at: Optional[int] = None
        self._engagement_count: int = 0
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    def set_relay_service(self, relay_service) -> None:
        """Inject the relay service so engagement can drop the relay."""
        self._relay_service = relay_service

    @property
    def is_engaged(self) -> bool:
        """Whether the safety interlock is currently engaged (debounced)."""
        return self._engaged

    @property
    def is_available(self) -> bool:
        """Whether the underlying Auto Hat Mini library is usable.

        False in mock mode or if the HAT isn't responding. The monitor
        still runs and reports `engaged = False` in that case, so callers
        don't need to special-case unavailable hardware.
        """
        return HAT_AVAILABLE

    async def start(self) -> None:
        """Start the background polling task."""
        if not settings.HARDWARE_SAFETY_ENABLED:
            logger.info(
                "Hardware safety monitor disabled by configuration "
                "(HARDWARE_SAFETY_ENABLED=false)"
            )
            return
        if self._running:
            logger.warning("Hardware safety monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

        mode = "real HAT" if HAT_AVAILABLE else "mock (HAT unavailable)"
        logger.info(
            f"Hardware safety monitor started ({mode}, "
            f"poll={int(self.POLL_INTERVAL_SEC * 1000)}ms, "
            f"debounce={self.DEBOUNCE_READS} reads)"
        )

    async def stop(self) -> None:
        """Stop the background polling task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Hardware safety monitor stopped")

    def _read_input(self) -> bool:
        """Read the raw state of Auto Hat Mini IN1.

        Returns True when 5V is applied at IN1 (E-stop pressed in our
        wiring). In mock mode or on read error, returns False (not
        engaged) — the parallel NC contact still provides physical safety
        regardless of what software reports.
        """
        if not HAT_AVAILABLE:
            return False
        try:
            return bool(automationhat.input.one.read())
        except Exception as e:
            logger.error(f"Failed to read Auto Hat Mini IN1: {e}")
            return False

    async def _monitor_loop(self) -> None:
        """Main polling loop. Runs until stop() is called."""
        while self._running:
            try:
                await asyncio.sleep(self.POLL_INTERVAL_SEC)
                self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in hardware safety loop: {e}")
                # Avoid tight-looping on a persistent error
                await asyncio.sleep(0.5)

    def _tick(self) -> None:
        """Run one poll cycle: read, debounce, transition, re-assert."""
        raw = self._read_input()

        # Debounce: only flip public state after DEBOUNCE_READS matching
        # reads in a row.
        if raw == self._raw_last:
            self._stable_count += 1
        else:
            self._stable_count = 1
            self._raw_last = raw

        if (
            self._stable_count >= self.DEBOUNCE_READS
            and raw != self._engaged
        ):
            self._engaged = raw
            now = int(time.time())
            if raw:
                self._engaged_at = now
                self._engagement_count += 1
                logger.warning(
                    "HARDWARE SAFETY ENGAGED — E-stop pressed at GenSlave. "
                    "Dropping relay command."
                )
                if self._relay_service:
                    self._relay_service.relay_off(force=True)
            else:
                self._released_at = now
                logger.info(
                    "Hardware safety RELEASED — E-stop returned to normal "
                    "position. The next inbound heartbeat from GenMaster "
                    "will re-assert the desired run state; if a run is "
                    "still being requested (Victron, scheduled, manual), "
                    "the relay will turn back on automatically — up to one "
                    "heartbeat interval of delay."
                )

        # While engaged: continuously re-assert relay-off. GenMaster's
        # heartbeat sync may otherwise turn the relay back on (until
        # Phase 2 wires the engaged flag into the heartbeat schema). The
        # parallel NC contact in the E-stop physically blocks the
        # generator regardless of relay state, but we keep software
        # consistent so logs and UI don't lie about what's happening.
        if (
            self._engaged
            and self._relay_service is not None
            and self._relay_service.get_state()
        ):
            self._relay_service.relay_off(force=True)

    def get_status(self) -> dict:
        """Return a snapshot for diagnostics / future heartbeat payload."""
        return {
            "running": self._running,
            "available": HAT_AVAILABLE,
            "enabled": settings.HARDWARE_SAFETY_ENABLED,
            "engaged": self._engaged,
            "engaged_at": self._engaged_at,
            "released_at": self._released_at,
            "engagement_count": self._engagement_count,
            "raw_input": self._raw_last,
        }


# Global singleton, mirrors the pattern used by other GenSlave services.
hardware_safety_monitor = HardwareSafetyMonitor()
