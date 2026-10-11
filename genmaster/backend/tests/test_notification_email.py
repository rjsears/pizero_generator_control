"""Tests for NotificationService email sending (SMTP transport selection and timeouts)."""

import asyncio
import socket
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services import notification_service as ns
from app.services.notification_service import NotificationService, SMTP_TIMEOUT_SECONDS


def _channel(port, use_tls=True, host="smtp.example.com"):
    return SimpleNamespace(
        id=1,
        name="test-email",
        config={
            "smtp_host": host,
            "smtp_port": port,
            "use_tls": use_tls,
            "username": "user",
            "password": "pass",
            "from_address": "from@example.com",
            "to_addresses": ["to@example.com"],
        },
    )


@pytest.mark.asyncio
async def test_port_465_uses_implicit_tls():
    with patch("app.services.notification_service.smtplib") as mock_smtplib:
        server = mock_smtplib.SMTP_SSL.return_value.__enter__.return_value

        result = await NotificationService()._send_email(_channel("465"), "Title", "Body")

        assert result.success is True, result.error
        mock_smtplib.SMTP_SSL.assert_called_once_with(
            "smtp.example.com", 465, timeout=SMTP_TIMEOUT_SECONDS
        )
        mock_smtplib.SMTP.assert_not_called()
        server.starttls.assert_not_called()
        mock_smtplib.SMTP_SSL.return_value.starttls.assert_not_called()
        server.login.assert_called_once_with("user", "pass")
        server.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_port_587_uses_starttls():
    with patch("app.services.notification_service.smtplib") as mock_smtplib:
        server = mock_smtplib.SMTP.return_value.__enter__.return_value

        result = await NotificationService()._send_email(_channel(587), "Title", "Body")

        assert result.success is True, result.error
        mock_smtplib.SMTP.assert_called_once_with(
            "smtp.example.com", 587, timeout=SMTP_TIMEOUT_SECONDS
        )
        mock_smtplib.SMTP_SSL.assert_not_called()
        server.starttls.assert_called_once_with()
        server.login.assert_called_once_with("user", "pass")
        server.sendmail.assert_called_once()
        call_names = [c[0] for c in server.method_calls]
        assert call_names.index("starttls") < call_names.index("login") < call_names.index("sendmail")


@pytest.mark.asyncio
async def test_hung_server_does_not_block_event_loop():
    # A server that accepts the connection but never sends the SMTP greeting.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    stop = threading.Event()
    accepted = []

    def serve():
        listener.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
                accepted.append(conn)
            except socket.timeout:
                continue
            except OSError:
                break

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    counter = 0

    async def ticker():
        nonlocal counter
        while True:
            await asyncio.sleep(0.1)
            counter += 1

    tick_task = asyncio.create_task(ticker())
    try:
        with patch("app.services.notification_service.SMTP_TIMEOUT_SECONDS", 1):
            start = time.monotonic()
            result = await asyncio.wait_for(
                NotificationService()._send_email(
                    _channel(port, use_tls=True, host="127.0.0.1"), "Title", "Body"
                ),
                timeout=5,
            )
            elapsed = time.monotonic() - start
    finally:
        tick_task.cancel()
        stop.set()
        for conn in accepted:
            conn.close()
        listener.close()
        thread.join(timeout=2)

    assert elapsed < 3, f"send took {elapsed:.2f}s"
    assert result.success is False
    assert result.error and "timed out" in result.error.lower()
    assert counter >= 5, f"event loop ticker only advanced {counter} times"
    assert ns.SMTP_TIMEOUT_SECONDS == 30
