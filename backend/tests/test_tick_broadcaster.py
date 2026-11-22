import asyncio
import pytest
from app.engine.tick_broadcaster import TickBroadcaster, tick_broadcaster


@pytest.fixture(autouse=True)
def clean_broadcaster():
    tick_broadcaster.clear()
    yield
    tick_broadcaster.clear()


@pytest.mark.asyncio
async def test_subscriber_registration_and_tick_fanout():
    """Verifies that ticks are delivered to registered subscribers matching symbol filters."""
    sub_id1, q1 = tick_broadcaster.register({"RELIANCE", "INFY"})
    sub_id2, q2 = tick_broadcaster.register({"TCS"})
    sub_id3, q3 = tick_broadcaster.register()  # Subscribe to all

    assert tick_broadcaster.get_stats()["active_subscribers"] == 3

    # Broadcast tick for RELIANCE
    delivered = tick_broadcaster.broadcast_tick("RELIANCE", {"price": 2550.0, "change_pct": 1.5})
    assert delivered == 2  # Sub1 and Sub3

    tick1 = q1.get_nowait()
    assert tick1["symbol"] == "RELIANCE"
    assert tick1["price"] == 2550.0

    assert q2.empty()

    tick3 = q3.get_nowait()
    assert tick3["symbol"] == "RELIANCE"

    # Broadcast tick for TCS
    delivered = tick_broadcaster.broadcast_tick("TCS.NS", {"price": 3900.0, "change_pct": -0.8})
    assert delivered == 2  # Sub2 and Sub3

    assert q1.empty()
    tick2 = q2.get_nowait()
    assert tick2["symbol"] == "TCS"
    assert tick2["price"] == 3900.0


@pytest.mark.asyncio
async def test_queue_overflow_drop_oldest_eviction():
    """Verifies that slow subscribers drop the oldest ticks rather than leaking memory."""
    sub_id, q = tick_broadcaster.register({"RELIANCE"})

    # Fill the bounded queue (maxsize=100) and overflow it by 10 ticks
    for i in range(110):
        tick_broadcaster.broadcast_tick("RELIANCE", {"price": 2000.0 + i})

    assert q.qsize() == 100
    stats = tick_broadcaster.get_stats()
    assert stats["ticks_dropped_queue_full"] == 10

    # The first item should be price 2010.0 (first 10 were dropped)
    first_item = q.get_nowait()
    assert first_item["price"] == 2010.0

    tick_broadcaster.unregister(sub_id)
    assert tick_broadcaster.get_stats()["active_subscribers"] == 0


@pytest.mark.asyncio
async def test_dynamic_subscription_update():
    """Verifies dynamic subscription update for active client sessions."""
    sub_id, q = tick_broadcaster.register({"INFY"})
    
    # Broadcast TCS -> not received
    tick_broadcaster.broadcast_tick("TCS", {"price": 3950.0})
    assert q.empty()

    # Update subscription to include TCS
    tick_broadcaster.update_subscription(sub_id, {"INFY", "TCS"})
    tick_broadcaster.broadcast_tick("TCS", {"price": 3955.0})
    assert not q.empty()
    item = q.get_nowait()
    assert item["symbol"] == "TCS"
    assert item["price"] == 3955.0

    tick_broadcaster.unregister(sub_id)
