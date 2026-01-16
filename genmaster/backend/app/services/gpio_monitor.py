# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/gpio_monitor.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""GPIO monitor service for Victron relay signal on GPIO17."""

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Optional

from app.config import settings

if TYPE_CHECKING:
    from app.services.state_machine import StateMachine

logger = logging.getLogger(__name__)


class GPIOMonitor:
    """
    Monitors GPIO17 for Victron relay signal.

    When running on a Raspberry Pi, uses gpiozero to monitor the actual GPIO pin.
    On other platforms (Mac/Linux dev machines), runs in mock mode for testing.
    """

    def __init__(
        self,
        state_machine: "StateMachine",
        gpio_pin: int = 17,
        mock_mode: Optional[bool] = None,
    ):
        """
        Initialize GPIO monitor.

        Args:
            state_machine: StateMachine instance to notify of signal changes
            gpio_pin: GPIO pin number to monitor (default 17)
            mock_mode: Force mock mode if True, auto-detect if None
        """
        self.state_machine = state_machine
        self.gpio_pin = gpio_pin
        self.mock_mode = mock_mode if mock_mode is not None else settings.is_mock_gpio
        self._running = False
        self._button = None
        self._current_state = False
        self._mock_signal_callback: Optional[Callable[[bool], None]] = None

    def _is_raspberry_pi(self) -> bool:
        """Check if running on a Raspberry Pi."""
        try:
            with open("/proc/cpuinfo", "r") as f:
                return "Raspberry Pi" in f.read()
        except (FileNotFoundError, PermissionError):
            return False

    def start(self) -> None:
        """Start monitoring GPIO."""
        if self._running:
            logger.warning("GPIO monitor already running")
            return

        self._running = True

        if self.mock_mode:
            logger.info(
                f"GPIO monitor starting in MOCK mode (pin {self.gpio_pin} simulated)"
            )
            self._current_state = False
        else:
            try:
                from gpiozero import Button

                # Configure GPIO17 with pull-up resistor
                # Signal is active-low: pressed = relay closed = generator wanted
                self._button = Button(
                    self.gpio_pin,
                    pull_up=True,
                    bounce_time=0.1,  # 100ms debounce
                )
                self._button.when_pressed = self._on_signal_active
                self._button.when_released = self._on_signal_inactive

                # Read initial state
                self._current_state = self._button.is_pressed

                logger.info(
                    f"GPIO monitor started on pin {self.gpio_pin}, "
                    f"initial state: {'ACTIVE' if self._current_state else 'INACTIVE'}"
                )
            except ImportError:
                logger.error("gpiozero not available, falling back to mock mode")
                self.mock_mode = True
                self._current_state = False
            except Exception as e:
                logger.error(f"Failed to initialize GPIO: {e}, falling back to mock mode")
                self.mock_mode = True
                self._current_state = False

    def stop(self) -> None:
        """Stop monitoring GPIO."""
        if not self._running:
            return

        self._running = False

        if self._button is not None:
            self._button.close()
            self._button = None

        logger.info("GPIO monitor stopped")

    def _on_signal_active(self) -> None:
        """Handle relay signal becoming active (generator wanted)."""
        if not self._running:
            return

        self._current_state = True
        logger.info("Victron signal ACTIVE - generator wanted")

        # Notify state machine asynchronously
        asyncio.create_task(self._notify_state_change(True))

    def _on_signal_inactive(self) -> None:
        """Handle relay signal becoming inactive (generator not wanted)."""
        if not self._running:
            return

        self._current_state = False
        logger.info("Victron signal INACTIVE - generator not wanted")

        # Notify state machine asynchronously
        asyncio.create_task(self._notify_state_change(False))

    async def _notify_state_change(self, active: bool) -> None:
        """Notify state machine of signal change."""
        try:
            await self.state_machine.handle_victron_signal_change(active)
        except Exception as e:
            logger.error(f"Error notifying state machine of signal change: {e}")

    @property
    def current_state(self) -> bool:
        """Get current signal state."""
        return self._current_state

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    # Mock mode methods for testing

    def mock_set_signal(self, active: bool) -> None:
        """
        Set mock signal state for testing.

        Args:
            active: True to simulate generator wanted, False for not wanted

        Raises:
            RuntimeError: If not in mock mode
        """
        if not self.mock_mode:
            raise RuntimeError("Cannot set mock signal when not in mock mode")

        if not self._running:
            raise RuntimeError("GPIO monitor not running")

        if active != self._current_state:
            self._current_state = active
            logger.info(f"Mock signal set to {'ACTIVE' if active else 'INACTIVE'}")

            if active:
                self._on_signal_active()
            else:
                self._on_signal_inactive()

    def mock_toggle_signal(self) -> bool:
        """
        Toggle mock signal state for testing.

        Returns:
            New signal state

        Raises:
            RuntimeError: If not in mock mode
        """
        self.mock_set_signal(not self._current_state)
        return self._current_state
