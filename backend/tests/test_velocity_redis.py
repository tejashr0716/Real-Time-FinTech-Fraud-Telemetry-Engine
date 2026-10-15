import pytest
import time
from app.services.redis_service import redis_service

@pytest.mark.asyncio
async def test_redis_sliding_window_velocity():
    account_id = "test_acc_velocity_01"
    now_ms = int(time.time() * 1000)

    # 1st transaction in window
    count1 = await redis_service.record_and_get_velocity(account_id, "tx_01", now_ms, window_seconds=60)
    assert count1 == 1

    # 2nd transaction
    count2 = await redis_service.record_and_get_velocity(account_id, "tx_02", now_ms + 100, window_seconds=60)
    assert count2 == 2

    # 3rd transaction
    count3 = await redis_service.record_and_get_velocity(account_id, "tx_03", now_ms + 200, window_seconds=60)
    assert count3 == 3

    # Clean up test key
    client = redis_service.get_client()
    await client.delete(f"velocity:account:{account_id}")

@pytest.mark.asyncio
async def test_redis_ip_blacklist_management():
    test_ip = "192.0.2.250"
    assert await redis_service.is_ip_blacklisted(test_ip) is False

    await redis_service.add_blacklisted_ip(test_ip)
    assert await redis_service.is_ip_blacklisted(test_ip) is True

    # Clean up
    client = redis_service.get_client()
    await client.srem("blacklist:ips", test_ip)
