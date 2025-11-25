import redis.asyncio as redis
from typing import Optional
import logging
from app.models import IdempotencyStatus

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for idempotency tracking"""

    def __init__(self, redis_url: str, idempotency_ttl: int):
        self.redis_url = redis_url
        self.idempotency_ttl = idempotency_ttl
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Establish Redis connection"""
        self.client = redis.from_url(
            self.redis_url, encoding="utf-8", decode_responses=True
        )
        logger.info("Redis connection established")

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

    async def check_idempotency(self, idempotency_key: str) -> IdempotencyStatus:
        """Check if message has been processed"""
        key = f"idempotency:{idempotency_key}"
        value = await self.client.get(key)

        if value is None:
            return IdempotencyStatus.NOT_FOUND
        elif value == "processing":
            return IdempotencyStatus.PROCESSING
        elif value == "sent":
            return IdempotencyStatus.SENT
        elif value == "failed":
            return IdempotencyStatus.FAILED
        else:
            logger.warning(f"Unknown idempotency status: {value}")
            return IdempotencyStatus.NOT_FOUND

    async def mark_as_processing(self, idempotency_key: str):
        """Mark message as currently processing"""
        key = f"idempotency:{idempotency_key}"
        await self.client.setex(key, self.idempotency_ttl, "processing")
        logger.debug(f"Marked {idempotency_key} as processing")

    async def mark_as_sent(self, idempotency_key: str):
        """Mark message as successfully sent"""
        key = f"idempotency:{idempotency_key}"
        await self.client.setex(key, self.idempotency_ttl, "sent")
        logger.debug(f"Marked {idempotency_key} as sent")

    async def mark_as_failed(self, idempotency_key: str):
        """Mark message as failed"""
        key = f"idempotency:{idempotency_key}"
        await self.client.setex(key, self.idempotency_ttl, "failed")
        logger.debug(f"Marked {idempotency_key} as failed")

    async def ping(self) -> bool:
        """Health check for Redis"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
