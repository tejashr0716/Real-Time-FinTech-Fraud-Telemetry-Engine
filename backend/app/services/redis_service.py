import redis.asyncio as aioredis
import time
import json
import logging
from typing import Optional, List, Dict, Any
from app.config import settings

logger = logging.getLogger("redis_fraud_service")

class RedisService:
    def __init__(self):
        self.pool: Optional[aioredis.ConnectionPool] = None
        self.client: Optional[aioredis.Redis] = None

    async def connect(self):
        if not self.client:
            self.pool = aioredis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS
            )
            self.client = aioredis.Redis(connection_pool=self.pool)

    async def close(self):
        if self.client:
            await self.client.close()
            await self.pool.disconnect()
            self.client = None
            self.pool = None

    def get_client(self) -> aioredis.Redis:
        if not self.client:
            raise RuntimeError("Redis client is not connected.")
        return self.client

    async def record_and_get_velocity(
        self,
        account_id: str,
        tx_id: str,
        now_ms: int,
        window_seconds: int = 60
    ) -> int:
        """
        Sliding-Window Velocity Tracking:
        Atomically trims elements older than window_seconds, adds new transaction timestamp,
        and returns the current velocity count within the window.
        """
        client = self.get_client()
        key = f"velocity:account:{account_id}"
        cutoff_ms = now_ms - (window_seconds * 1000)

        pipe = client.pipeline(transaction=True)
        pipe.zremrangebyscore(key, 0, cutoff_ms)
        pipe.zadd(key, {tx_id: now_ms})
        pipe.zcard(key)
        pipe.expire(key, window_seconds * 2)

        results = await pipe.execute()
        return int(results[2]) # ZCARD result

    async def is_ip_blacklisted(self, ip: str) -> bool:
        client = self.get_client()
        return bool(await client.sismember("blacklist:ips", ip))

    async def add_blacklisted_ip(self, ip: str):
        client = self.get_client()
        await client.sadd("blacklist:ips", ip)

    async def publish_telemetry_event(self, event_data: Dict[str, Any]):
        client = self.get_client()
        await client.publish("channel:fraud:telemetry", json.dumps(event_data))

redis_service = RedisService()
