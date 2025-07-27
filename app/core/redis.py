"""
Redis connection and utilities for caching and rate limiting
"""
import json
import redis.asyncio as redis
from typing import Any, Optional, Union
from datetime import timedelta

from app.core.config import settings


class RedisManager:
    """Redis connection and operations manager"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True
        )
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.redis_client:
            await self.connect()
        return await self.redis_client.get(key)
    
    async def set(
        self, 
        key: str, 
        value: Union[str, dict, list], 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional TTL"""
        if not self.redis_client:
            await self.connect()
        
        # Serialize complex objects to JSON
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        if ttl:
            return await self.redis_client.setex(key, ttl, value)
        else:
            return await self.redis_client.set(key, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.redis_client:
            await self.connect()
        return bool(await self.redis_client.delete(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis_client:
            await self.connect()
        return bool(await self.redis_client.exists(key))
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in Redis"""
        if not self.redis_client:
            await self.connect()
        return await self.redis_client.incrby(key, amount)
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self.redis_client:
            await self.connect()
        return await self.redis_client.expire(key, ttl)
    
    async def hset(self, key: str, mapping: dict) -> int:
        """Set hash fields in Redis"""
        if not self.redis_client:
            await self.connect()
        return await self.redis_client.hset(key, mapping=mapping)
    
    async def hgetall(self, key: str) -> dict:
        """Get all hash fields from Redis"""
        if not self.redis_client:
            await self.connect()
        return await self.redis_client.hgetall(key)
    
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            if not self.redis_client:
                await self.connect()
            await self.redis_client.ping()
            return True
        except Exception:
            return False


# Global Redis manager instance
redis_manager = RedisManager()


def get_redis_client():
    """Get Redis client instance"""
    return redis_manager


class CacheService:
    """High-level caching service"""
    
    @staticmethod
    async def get_certificate(tenant_id: str) -> Optional[dict]:
        """Get cached certificate for tenant"""
        key = f"cert:{tenant_id}"
        cached = await redis_manager.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    @staticmethod
    async def cache_certificate(tenant_id: str, certificate_data: dict):
        """Cache certificate for tenant"""
        key = f"cert:{tenant_id}"
        await redis_manager.set(key, certificate_data, settings.CERTIFICATE_CACHE_TTL)
    
    @staticmethod
    async def get_cabys_code(code: str) -> Optional[dict]:
        """Get cached CABYS code"""
        key = f"cabys:{code}"
        cached = await redis_manager.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    @staticmethod
    async def cache_cabys_code(code: str, code_data: dict):
        """Cache CABYS code"""
        key = f"cabys:{code}"
        await redis_manager.set(key, code_data, settings.CABYS_CACHE_TTL)
    
    @staticmethod
    async def invalidate_tenant_cache(tenant_id: str):
        """Invalidate all cache entries for a tenant"""
        await redis_manager.delete(f"cert:{tenant_id}")


class RateLimitService:
    """Rate limiting service using Redis"""
    
    @staticmethod
    async def check_rate_limit(tenant_id: str, plan: str) -> tuple[bool, int, int]:
        """
        Check if tenant has exceeded rate limit
        Returns: (is_allowed, current_count, limit)
        """
        # Get rate limit based on plan
        limits = {
            "basico": settings.RATE_LIMIT_BASIC,
            "pro": settings.RATE_LIMIT_PRO,
            "empresa": settings.RATE_LIMIT_ENTERPRISE
        }
        limit = limits.get(plan, settings.RATE_LIMIT_BASIC)
        
        # Redis key for rate limiting (per hour)
        key = f"rate_limit:{tenant_id}:{plan}"
        
        # Get current count
        current = await redis_manager.get(key)
        current_count = int(current) if current else 0
        
        if current_count >= limit:
            return False, current_count, limit
        
        # Increment counter
        new_count = await redis_manager.increment(key)
        
        # Set expiration if this is the first request in the window
        if new_count == 1:
            await redis_manager.expire(key, 3600)  # 1 hour window
        
        return True, new_count, limit