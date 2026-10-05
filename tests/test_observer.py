import pytest
import asyncio
from guru import observer


@pytest.fixture(autouse=True)
def clear_events():
    """Clear observer events before and after each test."""
    observer.events = {}
    yield
    observer.events = {}


@pytest.mark.asyncio
async def test_emit_with_sync_callback():
    """Test that emit works with synchronous callbacks."""
    called = []

    def sync_callback(value):
        called.append(value)

    observer.subscribe("test_event", sync_callback)
    await observer.emit("test_event", "test_value")

    assert called == ["test_value"]


@pytest.mark.asyncio
async def test_emit_with_async_callback():
    """Test that emit works with asynchronous callbacks."""
    called = []

    async def async_callback(value):
        await asyncio.sleep(0.01)
        called.append(value)

    observer.subscribe("test_event", async_callback)
    await observer.emit("test_event", "test_value")

    assert called == ["test_value"]


@pytest.mark.asyncio
async def test_emit_with_mixed_callbacks():
    """Test that emit works with both sync and async callbacks."""
    called = []

    def sync_callback(value):
        called.append(f"sync_{value}")

    async def async_callback(value):
        await asyncio.sleep(0.01)
        called.append(f"async_{value}")

    observer.subscribe("test_event", sync_callback)
    observer.subscribe("test_event", async_callback)
    await observer.emit("test_event", "test")

    assert "sync_test" in called
    assert "async_test" in called


@pytest.mark.asyncio
async def test_emit_with_no_subscribers():
    """Test that emit does nothing when no subscribers exist."""
    await observer.emit("nonexistent_event", "value")
    # Should not raise any errors


@pytest.mark.asyncio
async def test_emit_with_exception_in_sync_callback():
    """Test that exceptions in sync callbacks are logged but don't stop other callbacks."""
    called = []

    def failing_callback(value):
        raise ValueError("Test error")

    def success_callback(value):
        called.append(value)

    observer.subscribe("test_event", failing_callback)
    observer.subscribe("test_event", success_callback)
    await observer.emit("test_event", "test")

    # Second callback should still execute
    assert called == ["test"]


@pytest.mark.asyncio
async def test_emit_with_exception_in_async_callback():
    """Test that exceptions in async callbacks are logged but don't stop other callbacks."""
    called = []

    async def failing_callback(value):
        raise ValueError("Test error")

    def success_callback(value):
        called.append(value)

    observer.subscribe("test_event", failing_callback)
    observer.subscribe("test_event", success_callback)
    await observer.emit("test_event", "test")

    # Second callback should still execute
    assert called == ["test"]


@pytest.mark.asyncio
async def test_emit_with_kwargs():
    """Test that emit properly passes keyword arguments."""
    called = []

    def callback(a, b=None):
        called.append((a, b))

    observer.subscribe("test_event", callback)
    await observer.emit("test_event", "val1", b="val2")

    assert called == [("val1", "val2")]


@pytest.mark.asyncio
async def test_multiple_events():
    """Test subscribing to multiple different events."""
    event1_called = []
    event2_called = []

    observer.subscribe("event1", lambda x: event1_called.append(x))
    observer.subscribe("event2", lambda x: event2_called.append(x))

    await observer.emit("event1", "a")
    await observer.emit("event2", "b")

    assert event1_called == ["a"]
    assert event2_called == ["b"]
