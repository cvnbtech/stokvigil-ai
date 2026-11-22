import pytest
from app.market_cache import market_cache
from app.engine.tick_broadcaster import tick_broadcaster
from app.engine.ticker_stream import ticker_manager
from app.routers.stocks import stream_stock_ticks


@pytest.fixture(autouse=True)
def clean_state():
    market_cache.clear()
    tick_broadcaster.clear()
    yield
    market_cache.clear()
    tick_broadcaster.clear()


@pytest.mark.asyncio
async def test_ticker_stream_broadcasts_to_broadcaster():
    """Verifies that ticker_stream.on_tick_received pushes ticks to tick_broadcaster."""
    sub_id, q = tick_broadcaster.register({"INFY"})

    tick_packet = {
        "stock_code": "INFY",
        "last": 1700.0,
        "high": 1715.0,
        "low": 1690.0,
        "volume": 500000
    }

    ticker_manager.on_tick_received(tick_packet)

    assert not q.empty()
    item = q.get_nowait()
    assert item["symbol"] == "INFY"
    assert item["price"] == 1700.0
    assert item["day_high"] == 1715.0
    assert item["day_low"] == 1690.0

    tick_broadcaster.unregister(sub_id)


@pytest.mark.asyncio
async def test_stocks_stream_initial_snapshot_and_tick_event():
    """
    Verifies that stream_stock_ticks:
    1. Immediately yields the initial snapshot for requested symbols.
    2. Yields incoming tick events when broadcaster pushes.
    3. Unregisters the subscriber queue cleanly when the stream closes.
    """
    market_cache.set_stock("RELIANCE", {
        "symbol": "RELIANCE",
        "current_price": 2550.0,
        "day_high": 2570.0,
        "day_low": 2530.0,
        "live_volume": 1200000,
        "technicals": {
            "change_pct": 1.25,
            "current_price": 2550.0
        }
    })

    # Call route handler directly
    response = await stream_stock_ticks(symbols="RELIANCE")
    assert response.status_code == 200
    assert response.media_type == "text/event-stream"
    assert tick_broadcaster.get_stats()["active_subscribers"] == 1

    iterator = response.body_iterator

    # 1. First event must be snapshot
    first_event = await anext(iterator)
    assert "event: snapshot" in first_event
    assert "RELIANCE" in first_event
    assert "2550" in first_event

    # 2. Broadcast a live tick
    tick_broadcaster.broadcast_tick("RELIANCE", {"price": 2565.0, "change_pct": 1.84})
    second_event = await anext(iterator)
    assert "event: tick" in second_event
    assert "2565" in second_event

    # 3. Close the stream and verify zero active subscribers left (memory cleanup)
    await iterator.aclose()
    assert tick_broadcaster.get_stats()["active_subscribers"] == 0
