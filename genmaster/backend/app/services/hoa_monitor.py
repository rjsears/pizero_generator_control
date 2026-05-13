# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/hoa_monitor.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - May 13th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""HOA (Hand-Off-Auto, here labeled Quiet/Auto/Run) selector monitor.

Reads a 3-position rotary selector wired to GenMaster's Pi 5 header:

  GPIO22 = Quiet contact (closes to GND when handle is in Quiet position)
  GPIO27 = Run   contact (closes to GND when handle is in Run position)
  Center (Auto) position closes neither.

Both lines use the Pi's internal pull-ups, so an open contact reads HIGH
and a closed contact reads LOW. State is decoded from the pair:

  GPIO22 HIGH, GPIO27 HIGH → auto    (center; also the default if
                                       neither wire is connected)
  GPIO22 LOW,  GPIO27 HIGH → quiet   (Block A closed, position 1)
  GPIO22 HIGH, GPIO27 LOW  → run     (Block B closed, position 3)
  GPIO22 LOW,  GPIO27 LOW  → fault   (mechanically impossible — log
                                       and treat as auto for safety)

Boot delay: when GenMaster starts up, the switch may have been in Run or
Quiet for some time without the system reacting (because the system was
off). Per decision #3 we wait `hoa_boot_delay_seconds` (default 90s)
before honoring the state; during the window the monitor reports
`auto` regardless of the physical reading. This prevents a stale switch
position from triggering an automatic run the instant the system
recovers from a power blip.

No state-machine integration here — this monitor only OBSERVES the
switch and exposes the current decoded state. Phase 4 wires the state
machine to react to changes (blocking runs in Quiet, etc.).
"""

import asyncio
import logging
import time
from typing import Literal, Optional

from app.config import settings

logger = logging.getLogger(__name__)


HOAState = Literal["quiet", "auto", "run", "fault"]


def _decode_state(quiet_pressed: bool, run_pressed: bool) -> HOAState:
    """Decode the two contact states into a single HOA position.

    `*_pressed` here means "contact closed to GND" (gpiozero Button's
    `is_pressed` semantics with pull_up=True).
    """
    if quiet_pressed and run_pressed:
        return "fault"
    if quiet_pressed:
        return "quiet"
    if run_pressed:
        return "run"
    return "auto"


class HOAMonitor:
    """Monitors the HOA selector switch on GenMaster.

    Uses gpiozero's `Button` (event-driven, internal debounce) on each
    pin. State decode happens on every edge so we always report the
    combined (Quiet/Auto/Run) position, not individual contacts.
    """

    def __init__(
        self,
        gpio_quiet: Optional[int] = None,
        gpio_run: Optional[int] = None,
        boot_delay_seconds: Optional[int] = None,
        mock_mode: Optional[bool] = None,
    ):
        self.gpio_quiet = gpio_quiet if gpio_quiet is not None else settings.hoa_gpio_quiet
        self.gpio_run = gpio_run if gpio_run is not None else settings.hoa_gpio_run
        self.boot_delay_seconds = (
            boot_delay_seconds
            if boot_delay_seconds is not None
            else settings.hoa_boot_delay_seconds
        )
        self.mock_mode = (
            mock_mode if mock_mode is not None else settings.is_mock_gpio
        )

        self._running: bool = False
        self._button_quiet = None
        self._button_run = None
        self._current_state: HOAState = "auto"
        self._raw_quiet: bool = False
        self._raw_run: bool = False
        self._boot_complete_at: Optional[float] = None
        # One-shot log: emit a single message the first time we leave the
        # boot-delay window, so operators see when switch state is
        # actually being honored.
        self._boot_delay_announced: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Diagnostics
        self._state_change_count: int = 0
        self._last_state_change_at: Optional[int] = None

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def start(self) -> None:
        """Start monitoring. Idempotent."""
        if self._running:
            logger.warning("HOA monitor already running")
            return
        if not settings.hoa_switch_enabled:
            logger.info(
                "HOA monitor disabled via configuration "
                "(HOA_SWITCH_ENABLED=false)"
            )
            return

        self._running = True
        self._boot_complete_at = time.time() + self.boot_delay_seconds

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()

        if self.mock_mode:
            logger.info(
                f"HOA monitor starting in MOCK mode "
                f"(quiet=GPIO{self.gpio_quiet}, run=GPIO{self.gpio_run}, "
                f"boot_delay={self.boot_delay_seconds}s)"
            )
            self._raw_quiet = False
            self._raw_run = False
            self._current_state = "auto"
            return

        try:
            from gpiozero import Button

            self._button_quiet = Button(
                self.gpio_quiet,
                pull_up=True,
                bounce_time=0.05,  # 50ms — matches GenSlave EPO debounce
            )
            self._button_run = Button(
                self.gpio_run,
                pull_up=True,
                bounce_time=0.05,
            )
            self._button_quiet.when_pressed = self._on_quiet_pressed
            self._button_quiet.when_released = self._on_quiet_released
            self._button_run.when_pressed = self._on_run_pressed
            self._button_run.when_released = self._on_run_released

            # Read initial state
            self._raw_quiet = self._button_quiet.is_pressed
            self._raw_run = self._button_run.is_pressed
            self._current_state = _decode_state(self._raw_quiet, self._raw_run)

            logger.info(
                f"HOA monitor started (quiet=GPIO{self.gpio_quiet}, "
                f"run=GPIO{self.gpio_run}, boot_delay={self.boot_delay_seconds}s, "
                f"initial raw state={self._current_state})"
            )
            if self.boot_delay_seconds > 0:
                logger.info(
                    f"HOA boot delay active — reporting 'auto' for the next "
                    f"{self.boot_delay_seconds}s regardless of switch position."
                )

        except ImportError:
            logger.error("gpiozero not available — falling back to HOA mock mode")
            self.mock_mode = True
            self._raw_quiet = False
            self._raw_run = False
            self._current_state = "auto"
        except Exception as e:
            logger.error(f"Failed to init HOA GPIO: {e} — falling back to mock")
            self.mock_mode = True
            self._raw_quiet = False
            self._raw_run = False
            self._current_state = "auto"

    def stop(self) -> None:
        """Stop monitoring. Idempotent."""
        if not self._running:
            return
        self._running = False

        if self._button_quiet is not None:
            try:
                self._button_quiet.close()
            except Exception:
                pass
            self._button_quiet = None
        if self._button_run is not None:
            try:
                self._button_run.close()
            except Exception:
                pass
            self._button_run = None

        logger.info("HOA monitor stopped")

    # =========================================================================
    # Public state surface
    # =========================================================================

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_boot_delay_active(self) -> bool:
        """True if we're still inside the post-boot grace window."""
        if self._boot_complete_at is None:
            return False
        return time.time() < self._boot_complete_at

    @property
    def current_state(self) -> HOAState:
        """The HOA position that callers (state machine, UI) should act on.

        Returns `auto` during the boot delay regardless of physical state,
        per decision #3.
        """
        if self.is_boot_delay_active:
            # Lazy-log on the FIRST property read AFTER the window closes
            # — but we don't have a "did we just transition?" hook here,
            # so the boot_delay_announced flag handles it.
            return "auto"

        # First read after boot delay ended — emit a one-shot info log so
        # operators know switch state is now live.
        if not self._boot_delay_announced and self._boot_complete_at is not None:
            self._boot_delay_announced = True
            logger.info(
                f"HOA boot delay expired — switch state is now live "
                f"(current position: {self._current_state})"
            )

        return self._current_state

    @property
    def raw_state(self) -> HOAState:
        """Decoded state IGNORING the boot delay. For diagnostics only —
        callers wanting the operational state should use `current_state`.
        """
        return self._current_state

    def get_status(self) -> dict:
        """Diagnostic snapshot for /api/system/hoa and UI consumption."""
        return {
            "hoa_monitor_running": self._running,
            "enabled": settings.hoa_switch_enabled,
            "mock_mode": self.mock_mode,
            "state": self.current_state,
            "raw_state": self._current_state,
            "boot_delay_active": self.is_boot_delay_active,
            "boot_delay_seconds": self.boot_delay_seconds,
            "boot_complete_at": (
                int(self._boot_complete_at)
                if self._boot_complete_at is not None
                else None
            ),
            "raw_quiet_pressed": self._raw_quiet,
            "raw_run_pressed": self._raw_run,
            "gpio_quiet": self.gpio_quiet,
            "gpio_run": self.gpio_run,
            "state_change_count": self._state_change_count,
            "last_state_change_at": self._last_state_change_at,
        }

    # =========================================================================
    # GPIO event handlers (called from gpiozero's internal thread)
    # =========================================================================

    def _on_quiet_pressed(self) -> None:
        self._raw_quiet = True
        self._reevaluate()

    def _on_quiet_released(self) -> None:
        self._raw_quiet = False
        self._reevaluate()

    def _on_run_pressed(self) -> None:
        self._raw_run = True
        self._reevaluate()

    def _on_run_released(self) -> None:
        self._raw_run = False
        self._reevaluate()

    def _reevaluate(self) -> None:
        """Recompute the combined state. Logs transitions."""
        new_state = _decode_state(self._raw_quiet, self._raw_run)
        old_state = self._current_state
        if new_state == old_state:
            return

        self._current_state = new_state
        self._state_change_count += 1
        self._last_state_change_at = int(time.time())

        if new_state == "fault":
            logger.warning(
                "HOA selector reported 'fault' (both contacts closed). "
                "Mechanically impossible — likely a wiring short or stuck "
                "contact. Treating as 'auto' until resolved."
            )
        elif self.is_boot_delay_active:
            logger.info(
                f"HOA raw state change: {old_state} → {new_state} "
                f"(suppressed by boot delay — reporting 'auto')"
            )
        else:
            logger.info(f"HOA state changed: {old_state} → {new_state}")

    # =========================================================================
    # Mock controls (for dev/tests on non-Pi platforms)
    # =========================================================================

    def mock_set_pins(self, quiet_pressed: bool, run_pressed: bool) -> None:
        """Set the raw pin states in mock mode and re-evaluate."""
        if not self.mock_mode:
            raise RuntimeError("Cannot mock pins when not in mock mode")
        if not self._running:
            raise RuntimeError("HOA monitor not running")
        self._raw_quiet = quiet_pressed
        self._raw_run = run_pressed
        self._reevaluate()

    def mock_set_state(self, state: HOAState) -> None:
        """Set the HOA state directly in mock mode (skips pin simulation)."""
        if state == "quiet":
            self.mock_set_pins(True, False)
        elif state == "run":
            self.mock_set_pins(False, True)
        elif state == "auto":
            self.mock_set_pins(False, False)
        elif state == "fault":
            self.mock_set_pins(True, True)
        else:
            raise ValueError(f"Invalid HOA state: {state}")
