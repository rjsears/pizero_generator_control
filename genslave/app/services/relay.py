# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/services/relay.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Relay control service for Automation Hat Mini."""

import logging
import time
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import automationhat, fall back to mock if not available
automationhat = None
HAT_AVAILABLE = False

if settings.MOCK_HAT_MODE:
    logger.info("Mock HAT mode enabled via configuration")
else:
    try:
        import automationhat as _automationhat

        # Test that we can actually use the relay by reading its state
        # The automationhat library auto-initializes on import
        # We verify it works by attempting to access the relay
        try:
            # Give the HAT a moment to initialize
            import time
            time.sleep(0.1)

            # Try to read relay state - this will fail if HAT not present
            _ = _automationhat.relay.one.is_on()

            automationhat = _automationhat
            HAT_AVAILABLE = True
            logger.info("Automation Hat Mini detected and ready")

        except Exception as e:
            logger.warning(
                f"automationhat library loaded but HAT not responding: {e}"
            )

    except ImportError as e:
        logger.warning(f"automationhat library not installed: {e}")


class RelayService:
    """
    Controls the Automation Hat Mini relay for generator start/stop.

    The relay is used to trigger the generator's remote start terminal.
    - Relay ON = Generator should run
    - Relay OFF = Generator should stop
    """

    def __init__(self):
        """Initialize relay service."""
        self._mock_state: bool = False
        self._last_change: Optional[int] = None
        self._change_count: int = 0
        self._armed: bool = False
        self._armed_at: Optional[int] = None
        self._armed_by: Optional[str] = None

        # Initialize relay to OFF state on startup
        if HAT_AVAILABLE:
            try:
                automationhat.relay.one.off()
                logger.info("Relay initialized to OFF state")
            except Exception as e:
                logger.error(f"Failed to initialize relay: {e}")

    @property
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return not HAT_AVAILABLE

    @property
    def is_armed(self) -> bool:
        """Check if automation is armed."""
        return self._armed

    def arm(self, source: str = "api") -> dict:
        """
        Arm the automation system.

        When armed, relay commands from GenMaster are executed.
        When disarmed, relay commands are logged but ignored.
        """
        if self._armed:
            return {
                "success": True,
                "armed": True,
                "message": "Already armed",
                "armed_at": self._armed_at,
            }

        self._armed = True
        self._armed_at = int(time.time())
        self._armed_by = source
        logger.info(f"Automation armed by {source}")

        return {
            "success": True,
            "armed": True,
            "message": "Automation armed",
            "armed_at": self._armed_at,
        }

    def disarm(self, source: str = "api") -> dict:
        """
        Disarm the automation system.

        Does NOT automatically turn off the relay - use relay_off() if needed.
        """
        if not self._armed:
            return {
                "success": True,
                "armed": False,
                "message": "Already disarmed",
            }

        was_armed_at = self._armed_at
        self._armed = False
        self._armed_at = None
        self._armed_by = None
        relay_state = self.get_state()

        logger.info(f"Automation disarmed by {source}, relay_state={relay_state}")

        return {
            "success": True,
            "armed": False,
            "message": "Automation disarmed",
            "relay_state": relay_state,
            "warning": "Relay state unchanged - use explicit off command if needed" if relay_state else None,
        }

    def get_arm_status(self) -> dict:
        """Get current arm status."""
        return {
            "armed": self._armed,
            "armed_at": self._armed_at,
            "armed_by": self._armed_by,
        }

    def relay_on(self, force: bool = False) -> bool:
        """
        Turn relay ON (start generator).

        Args:
            force: If True, bypass armed check (for failsafe recovery)

        Returns:
            True if successful, False otherwise
        """
        if not force and not self._armed:
            logger.warning("Relay ON requested but automation not armed - ignoring")
            return False

        try:
            if HAT_AVAILABLE:
                automationhat.relay.one.on()
            self._mock_state = True  # Track state internally

            self._last_change = int(time.time())
            self._change_count += 1
            logger.info(f"Relay turned ON (count: {self._change_count})")
            return True

        except Exception as e:
            logger.error(f"Failed to turn relay ON: {e}")
            return False

    def relay_off(self, force: bool = False) -> bool:
        """
        Turn relay OFF (stop generator).

        Args:
            force: If True, bypass armed check (for failsafe)

        Returns:
            True if successful, False otherwise
        """
        # Always allow OFF for safety, but log if not armed
        if not force and not self._armed:
            logger.info("Relay OFF requested while not armed - executing for safety")

        try:
            if HAT_AVAILABLE:
                automationhat.relay.one.off()
            self._mock_state = False  # Track state internally

            self._last_change = int(time.time())
            self._change_count += 1
            logger.info(f"Relay turned OFF (count: {self._change_count})")
            return True

        except Exception as e:
            logger.error(f"Failed to turn relay OFF: {e}")
            return False

    def get_state(self) -> bool:
        """
        Get current relay state.

        Returns:
            True if relay is ON, False if OFF

        Note: The Automation Hat Mini relay doesn't have state readback,
        so we track state internally based on our commands.
        """
        return self._mock_state  # We use _mock_state to track actual state too

    def get_status(self) -> dict:
        """Get full relay status."""
        return {
            "relay_state": self.get_state(),
            "last_change": self._last_change,
            "change_count": self._change_count,
            "mock_mode": self.is_mock_mode,
            "armed": self._armed,
            "armed_at": self._armed_at,
        }


# Global relay service instance
relay_service = RelayService()
