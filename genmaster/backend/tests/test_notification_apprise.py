"""Tests for NotificationService Apprise sending (worker-thread offload and error paths)."""

import asyncio
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.notification_service import NotificationService


def _channel(url="json://example.invalid/notify"):
    return SimpleNamespace(
        id=2,
        name="test-apprise",
        config={"url": url},
    )


def _fake_apprise_module(notify_impl):
    """Build a stand-in for the apprise module whose Apprise().notify calls notify_impl."""
    record = {"urls": [], "notify_thread": None, "calls": []}

    class FakeApprise:
        def add(self, url):
            record["urls"].append(url)
            return True

        def notify(self, title, body):
            record["notify_thread"] = threading.current_thread()
            record["calls"].append((title, body))
            return notify_impl()

    return SimpleNamespace(Apprise=FakeApprise), record


@pytest.mark.asyncio
async def test_apprise_notify_runs_off_event_loop():
    def slow_notify():
        time.sleep(0.3)
        return True

    fake_module, record = _fake_apprise_module(slow_notify)

    counter = 0

    async def ticker():
        nonlocal counter
        while True:
            await asyncio.sleep(0.05)
            counter += 1

    tick_task = asyncio.create_task(ticker())
    try:
        with patch.object(NotificationService, "_get_apprise", return_value=fake_module):
            result = await asyncio.wait_for(
                NotificationService()._send_apprise(_channel(), "Title", "Body"),
                timeout=5,
            )
    finally:
        tick_task.cancel()

    assert result.success is True, result.error
    assert record["urls"] == ["json://example.invalid/notify"]
    assert record["calls"] == [("Title", "Body")]
    assert record["notify_thread"] is not None
    assert record["notify_thread"] is not threading.main_thread()
    assert counter >= 3, f"event loop ticker only advanced {counter} times"


@pytest.mark.asyncio
async def test_apprise_failure_and_exception_paths():
    fake_module, _ = _fake_apprise_module(lambda: False)
    with patch.object(NotificationService, "_get_apprise", return_value=fake_module):
        result = await NotificationService()._send_apprise(_channel(), "Title", "Body")

    assert result.success is False
    assert result.error == "Apprise notification failed"

    def boom():
        raise RuntimeError("boom")

    fake_module, _ = _fake_apprise_module(boom)
    with patch.object(NotificationService, "_get_apprise", return_value=fake_module):
        result = await NotificationService()._send_apprise(_channel(), "Title", "Body")

    assert result.success is False
    assert result.error and "boom" in result.error
