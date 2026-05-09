# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/terminal.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""WebSocket terminal router for container and host shell access."""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# Thread pool for blocking socket operations
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="terminal_")


class TerminalSession:
    """Manages a terminal session with a container or host."""

    def __init__(self, websocket: WebSocket, target_id: str, target_type: str):
        self.websocket = websocket
        self.target_id = target_id
        self.target_type = target_type
        self.container = None
        self.exec_id = None
        self.socket = None
        self._running = False

    async def start(self):
        """Start the terminal session."""
        try:
            import docker
            client = docker.from_env()

            if self.target_type == "host":
                # For host access, create a privileged alpine container
                # that shares the host's namespaces
                self.container = client.containers.run(
                    "alpine:latest",
                    command="/bin/sh",
                    stdin_open=True,
                    tty=True,
                    detach=True,
                    remove=True,
                    pid_mode="host",
                    network_mode="host",
                    privileged=True,
                    volumes={"/": {"bind": "/host", "mode": "rw"}},
                )
                # Wait for container to be ready
                await asyncio.sleep(0.5)
            else:
                # Find the container by ID or name
                containers = client.containers.list(all=True)
                for c in containers:
                    if c.id.startswith(self.target_id) or c.name == self.target_id:
                        self.container = c
                        break

                if not self.container:
                    await self.websocket.send_text(
                        json.dumps({"type": "error", "message": f"Container not found: {self.target_id}"})
                    )
                    return False

                if self.container.status != "running":
                    await self.websocket.send_text(
                        json.dumps({"type": "error", "message": f"Container is not running: {self.container.status}"})
                    )
                    return False

            # Determine shell to use
            shell = self._detect_shell()

            # Get container's default user and working directory
            container_config = self.container.attrs.get("Config", {})

            # Create exec instance
            exec_instance = client.api.exec_create(
                self.container.id,
                shell,
                stdin=True,
                tty=True,
                stdout=True,
                stderr=True,
            )

            self.exec_id = exec_instance["Id"]

            # Start the exec and get the socket
            self.socket = client.api.exec_start(
                self.exec_id,
                detach=False,
                tty=True,
                stream=True,
                socket=True,
            )

            self._running = True

            # Notify client that terminal is ready
            await self.websocket.send_text(
                json.dumps({"type": "connected", "message": "Terminal connected"})
            )

            # Start reading from exec socket and sending to websocket
            asyncio.create_task(self._read_output())

            return True

        except ImportError:
            await self.websocket.send_text(
                json.dumps({"type": "error", "message": "Docker SDK not installed"})
            )
            return False
        except Exception as e:
            logger.error(f"Failed to start terminal session: {e}")
            await self.websocket.send_text(
                json.dumps({"type": "error", "message": str(e)})
            )
            return False

    def _detect_shell(self) -> str:
        """Detect the best available shell in the container."""
        shells = ["/bin/bash", "/bin/sh", "/bin/ash"]

        for shell in shells:
            try:
                exit_code, _ = self.container.exec_run(
                    f"test -f {shell}",
                    demux=True,
                )
                if exit_code == 0:
                    return shell
            except Exception:
                continue

        return "/bin/sh"

    async def _read_output(self):
        """Read output from exec socket and send to websocket."""
        import base64

        loop = asyncio.get_event_loop()

        def blocking_recv():
            """Blocking socket receive - runs in thread pool."""
            try:
                # Set socket timeout to avoid indefinite blocking
                self.socket._sock.settimeout(1.0)
                return self.socket._sock.recv(4096)
            except Exception:
                return None

        try:
            while self._running:
                try:
                    # Run blocking recv in thread pool to not block event loop
                    data = await asyncio.wait_for(
                        loop.run_in_executor(_executor, blocking_recv),
                        timeout=5.0
                    )

                    if not data:
                        # Timeout or empty - check if still running and continue
                        if self._running:
                            continue
                        break

                    # Send to websocket as base64 to handle binary data
                    encoded = base64.b64encode(data).decode("utf-8")
                    await self.websocket.send_text(
                        json.dumps({"type": "output", "data": encoded})
                    )
                except asyncio.TimeoutError:
                    # Read timeout - check if still running and continue
                    if self._running:
                        continue
                    break
                except Exception as e:
                    if self._running:
                        logger.debug(f"Read error: {e}")
                    break

        except Exception as e:
            logger.error(f"Output read error: {e}")
        finally:
            await self.stop()

    async def write_input(self, data: bytes):
        """Write input to the exec socket."""
        if self.socket and self._running:
            loop = asyncio.get_event_loop()

            def blocking_send():
                """Blocking socket send - runs in thread pool."""
                try:
                    self.socket._sock.send(data)
                    return True
                except Exception as e:
                    logger.error(f"Write error: {e}")
                    return False

            try:
                await asyncio.wait_for(
                    loop.run_in_executor(_executor, blocking_send),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.error("Write timeout")
            except Exception as e:
                logger.error(f"Write error: {e}")

    async def resize(self, rows: int, cols: int):
        """Resize the terminal."""
        if self.exec_id:
            try:
                import docker
                client = docker.from_env()
                client.api.exec_resize(self.exec_id, height=rows, width=cols)
            except Exception as e:
                logger.debug(f"Resize error: {e}")

    async def stop(self):
        """Stop the terminal session."""
        self._running = False

        try:
            if self.socket:
                self.socket._sock.close()
        except Exception:
            pass

        # If this was a host session, stop the temporary container
        if self.target_type == "host" and self.container:
            try:
                self.container.stop(timeout=1)
            except Exception:
                pass

        try:
            await self.websocket.send_text(
                json.dumps({"type": "disconnected", "message": "Terminal disconnected"})
            )
        except Exception:
            pass


@router.websocket("/ws")
async def terminal_websocket(
    websocket: WebSocket,
    target: str = Query(..., description="Container name/ID or 'host'"),
    target_type: str = Query("container", description="'container' or 'host'"),
):
    """
    WebSocket endpoint for terminal access.

    Connect with a target (container name/ID or 'host') to get shell access.
    Messages should be JSON with the following format:
    - Input: {"type": "input", "data": "<base64-encoded-data>"}
    - Resize: {"type": "resize", "rows": 24, "cols": 80}

    Output messages:
    - {"type": "output", "data": "<base64-encoded-data>"}
    - {"type": "connected", "message": "..."}
    - {"type": "disconnected", "message": "..."}
    - {"type": "error", "message": "..."}
    """
    await websocket.accept()

    session = TerminalSession(websocket, target, target_type)

    try:
        if not await session.start():
            await websocket.close()
            return

        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)

                msg_type = data.get("type")

                if msg_type == "input":
                    import base64
                    input_data = base64.b64decode(data.get("data", ""))
                    await session.write_input(input_data)

                elif msg_type == "resize":
                    rows = data.get("rows", 24)
                    cols = data.get("cols", 80)
                    await session.resize(rows, cols)

                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    finally:
        await session.stop()


@router.get("/targets")
async def get_terminal_targets() -> dict:
    """
    Get available terminal targets (containers and host).
    """
    targets = {
        "containers": [],
        "host_available": True,
    }

    try:
        import docker
        client = docker.from_env()

        containers = client.containers.list()
        for c in containers:
            targets["containers"].append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            })

    except ImportError:
        targets["error"] = "Docker SDK not installed"
        targets["host_available"] = False
    except Exception as e:
        targets["error"] = str(e)
        targets["host_available"] = False

    return targets
