# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/services/display.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Display service for Automation Hat Mini LCD."""

import asyncio
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import display libraries
ST7735 = None
Image = None
ImageDraw = None
ImageFont = None
DISPLAY_AVAILABLE = False

if not settings.MOCK_HAT_MODE:
    try:
        from st7735 import ST7735 as _ST7735
        from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont
        ST7735 = _ST7735
        Image = _Image
        ImageDraw = _ImageDraw
        ImageFont = _ImageFont
        DISPLAY_AVAILABLE = True
        logger.info("Display libraries loaded successfully")
    except ImportError as e:
        logger.warning(f"Display libraries not available: {e}")


class DisplayService:
    """
    Controls the Automation Hat Mini ST7735 LCD display.

    Shows:
    - Link status to GenMaster (heartbeat)
    - CPU temperature in °F
    - Generator status (OFF/RUNNING)
    """

    # Display dimensions for Automation Hat Mini
    WIDTH = 160
    HEIGHT = 80

    # Colors (RGB)
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    YELLOW = (255, 255, 0)
    BLUE = (0, 100, 255)

    def __init__(self):
        """Initialize display service."""
        self._display = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._failsafe_monitor = None
        self._relay_service = None
        self._last_update = None

        if DISPLAY_AVAILABLE:
            try:
                self._display = ST7735(
                    port=0,
                    cs=1,
                    dc=9,
                    backlight=25,
                    rotation=270,
                    spi_speed_hz=10000000
                )
                logger.info("Display initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize display: {e}")
                self._display = None

    def set_services(self, failsafe_monitor, relay_service) -> None:
        """Set references to other services for status display."""
        self._failsafe_monitor = failsafe_monitor
        self._relay_service = relay_service

    def _get_cpu_temp_f(self) -> float:
        """Get CPU temperature in Fahrenheit."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_c = float(f.read().strip()) / 1000.0
                temp_f = (temp_c * 9 / 5) + 32
                return round(temp_f, 1)
        except Exception as e:
            logger.debug(f"Failed to read CPU temp: {e}")
            return 0.0

    def _get_ip_address(self) -> str:
        """Get the primary IP address."""
        import socket
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                # Fallback: get hostname IP
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "Unknown"

    def _get_link_status(self) -> tuple:
        """
        Get link status to GenMaster.

        Returns:
            (status_text, color) tuple
        """
        if not self._failsafe_monitor:
            return ("WAITING", self.YELLOW)

        status = self._failsafe_monitor.get_status()
        last_hb = status.get("last_heartbeat")
        seconds_since = status.get("seconds_since_heartbeat")
        timeout = status.get("timeout_seconds", 30)

        if last_hb is None:
            return ("WAITING", self.YELLOW)

        if seconds_since is None:
            return ("WAITING", self.YELLOW)

        if seconds_since <= timeout:
            return ("ALIVE", self.GREEN)
        else:
            return ("DOWN", self.RED)

    def _get_gen_status(self) -> tuple:
        """
        Get generator status.

        Returns:
            (status_text, color) tuple
        """
        if not self._relay_service:
            return ("???", self.YELLOW)

        relay_state = self._relay_service.get_state()
        is_armed = self._relay_service.is_armed

        if relay_state:
            return ("RUNNING", self.GREEN)
        else:
            if is_armed:
                return ("OFF ARMED", self.WHITE)
            else:
                return ("DISARMED", self.YELLOW)

    def update_display(self) -> None:
        """Update the display with current status."""
        if not self._display:
            return

        try:
            # Create image
            img = Image.new('RGB', (self.WIDTH, self.HEIGHT), color=self.BLACK)
            draw = ImageDraw.Draw(img)

            # Try to use a built-in font, fall back to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
            except Exception:
                font = ImageFont.load_default()

            # Get status info
            link_text, link_color = self._get_link_status()
            gen_text, gen_color = self._get_gen_status()
            cpu_temp = self._get_cpu_temp_f()
            ip_addr = self._get_ip_address()

            # Line spacing for 4 lines on 80px height: ~19px per line
            y_pos = 1

            # Line 1: GenMaster status
            draw.text((2, y_pos), "GenMaster:", font=font, fill=self.WHITE)
            draw.text((90, y_pos), link_text, font=font, fill=link_color)

            # Line 2: Generator status
            y_pos += 19
            draw.text((2, y_pos), "Generator:", font=font, fill=self.WHITE)
            draw.text((90, y_pos), gen_text, font=font, fill=gen_color)

            # Line 3: CPU temp
            y_pos += 19
            # Color based on temp
            if cpu_temp > 170:
                temp_color = self.RED
            elif cpu_temp > 150:
                temp_color = self.YELLOW
            else:
                temp_color = self.BLUE
            draw.text((2, y_pos), f"CPU Temp: {cpu_temp:.1f}F", font=font, fill=temp_color)

            # Line 4: IP address
            y_pos += 19
            draw.text((2, y_pos), f"IP: {ip_addr}", font=font, fill=self.WHITE)

            # Display the image
            self._display.display(img)

        except Exception as e:
            logger.error(f"Failed to update display: {e}")

    async def start(self) -> None:
        """Start the display update loop."""
        if self._running:
            logger.warning("Display service already running")
            return

        if not self._display:
            logger.warning("Display not available - service not starting")
            return

        self._running = True

        # Show initial display
        self.update_display()

        self._task = asyncio.create_task(self._update_loop())
        logger.info("Display service started")

    async def stop(self) -> None:
        """Stop the display service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Clear display on shutdown
        if self._display:
            try:
                img = Image.new('RGB', (self.WIDTH, self.HEIGHT), color=self.BLACK)
                self._display.display(img)
            except Exception:
                pass

        logger.info("Display service stopped")

    async def _update_loop(self) -> None:
        """Main display update loop."""
        update_interval = 2  # Update every 2 seconds

        while self._running:
            try:
                await asyncio.sleep(update_interval)
                self.update_display()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in display update loop: {e}")


# Global display service instance
display_service = DisplayService()
