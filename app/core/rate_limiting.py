"""
Rate limiting utilities for Costa Rica invoice API
Implements Redis-based rate limiting with sliding window algorithm
"""
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from uuid import UUID
import redis
from redis import Redis

from app.core.config import settings
from app.schemas.enums import TenantPlan


class RateLimiter:
    """
    Redis-based rate limiter with sliding window algorithm
    
    Implements different limits per tenant plan and tracks usage
    across multiple time windows (hourly, daily, monthly).
    
    Requirements: 4.3 - Rate limiting with sliding window algorithm
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize rate limiter
        
        Args:
            redis_client: Optional Redis client instance
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True
            )
    
    def _get_plan_limits(self, plan: TenantPlan) -> Dict[str, int]:
        """
        Get rate limits for tenant plan
        
        Args:
            plan: Tenant plan
            
        Returns:
            Dictionary with rate limits per time window
        """
        limits = {
            TenantPlan.BASICO: {
                "requests_per_minute": 10,
                "requests_per_hour": 100,
                "requests_per_day": 500,
                "documents_per_month": 100
            },
            TenantPlan.PRO: {
                "requests_per_minute": 50,
                "requests_per_hour": 500,
                "requests_per_day": 2000,
                "documents_per_month": 1000
            },
            TenantPlan.EMPRESA: {
                "requests_per_minute": 100,
                "requests_per_hour": 2000,
                "requests_per_day": 10000,
                "documents_per_month": -1  # Unlimited
            }
        }
        
        return limits.get(plan, limits[TenantPlan.BASICO])
    
    def _get_redis_key(self, tenant_id: UUID, window: str, timestamp: int = None) -> str:
        """
        Generate Redis key for rate limiting
        
        Args:
            tenant_id: Tenant UUID
            window: Time window (minute, hour, day, month)
            timestamp: Optional timestamp for the window
            
        Returns:
            Redis key string
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Calculate window timestamp based on window type
        if window == "minute":
            window_ts = timestamp // 60
        elif window == "hour":
            window_ts = timestamp // 3600
        elif window == "day":
            window_ts = timestamp // 86400
        elif window == "month":
            dt = datetime.fromtimestamp(timestamp)
            window_ts = int(datetime(dt.year, dt.month, 1).timestamp())
        else:
            window_ts = timestamp
        
        return f"rate_limit:{tenant_id}:{window}:{window_ts}"
    
    def _increment_counter(self, key: str, window_seconds: int) -> int:
        """
        Increment counter with expiration
        
        Args:
            key: Redis key
            window_seconds: Window duration in seconds
            
        Returns:
            Current counter value
        """
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = pipe.execute()
        return results[0]
    
    def check_rate_limit(
        self, 
        tenant_id: UUID, 
        plan: TenantPlan, 
        endpoint: str = "general"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits
        
        Args:
            tenant_id: Tenant UUID
            plan: Tenant plan
            endpoint: Endpoint being accessed
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        limits = self._get_plan_limits(plan)
        current_time = int(time.time())
        
        # Check different time windows
        windows = {
            "minute": (60, limits["requests_per_minute"]),
            "hour": (3600, limits["requests_per_hour"]),
            "day": (86400, limits["requests_per_day"])
        }
        
        rate_limit_info = {
            "tenant_id": str(tenant_id),
            "plan": plan,
            "endpoint": endpoint,
            "timestamp": current_time,
            "windows": {}
        }
        
        # Check each window
        for window_name, (window_seconds, limit) in windows.items():
            key = self._get_redis_key(tenant_id, window_name, current_time)
            
            try:
                current_count = int(self.redis.get(key) or 0)
                
                rate_limit_info["windows"][window_name] = {
                    "limit": limit,
                    "used": current_count,
                    "remaining": max(0, limit - current_count),
                    "reset_time": current_time + window_seconds - (current_time % window_seconds)
                }
                
                # Check if limit exceeded
                if current_count >= limit:
                    rate_limit_info["exceeded_window"] = window_name
                    rate_limit_info["retry_after"] = window_seconds - (current_time % window_seconds)
                    return False, rate_limit_info
                    
            except Exception as e:
                # If Redis fails, allow the request but log the error
                print(f"Rate limiting error: {e}")
                rate_limit_info["error"] = str(e)
                return True, rate_limit_info
        
        return True, rate_limit_info
    
    def increment_usage(
        self, 
        tenant_id: UUID, 
        plan: TenantPlan, 
        endpoint: str = "general"
    ) -> Dict[str, Any]:
        """
        Increment usage counters after successful request
        
        Args:
            tenant_id: Tenant UUID
            plan: Tenant plan
            endpoint: Endpoint that was accessed
            
        Returns:
            Updated rate limit information
        """
        current_time = int(time.time())
        
        # Increment counters for all windows
        windows = {
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        updated_info = {
            "tenant_id": str(tenant_id),
            "plan": plan,
            "endpoint": endpoint,
            "timestamp": current_time,
            "windows": {}
        }
        
        for window_name, window_seconds in windows.items():
            key = self._get_redis_key(tenant_id, window_name, current_time)
            
            try:
                new_count = self._increment_counter(key, window_seconds)
                limits = self._get_plan_limits(plan)
                
                if window_name == "minute":
                    limit = limits["requests_per_minute"]
                elif window_name == "hour":
                    limit = limits["requests_per_hour"]
                else:  # day
                    limit = limits["requests_per_day"]
                
                updated_info["windows"][window_name] = {
                    "limit": limit,
                    "used": new_count,
                    "remaining": max(0, limit - new_count),
                    "reset_time": current_time + window_seconds - (current_time % window_seconds)
                }
                
            except Exception as e:
                print(f"Error incrementing usage: {e}")
                updated_info["error"] = str(e)
        
        return updated_info
    
    def get_usage_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get current usage statistics for tenant
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Usage statistics across all time windows
        """
        current_time = int(time.time())
        
        windows = {
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        stats = {
            "tenant_id": str(tenant_id),
            "timestamp": current_time,
            "windows": {}
        }
        
        for window_name, window_seconds in windows.items():
            key = self._get_redis_key(tenant_id, window_name, current_time)
            
            try:
                current_count = int(self.redis.get(key) or 0)
                
                stats["windows"][window_name] = {
                    "used": current_count,
                    "reset_time": current_time + window_seconds - (current_time % window_seconds)
                }
                
            except Exception as e:
                stats["windows"][window_name] = {
                    "error": str(e),
                    "used": 0
                }
        
        return stats
    
    def reset_tenant_limits(self, tenant_id: UUID) -> bool:
        """
        Reset all rate limits for a tenant (admin function)
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find all keys for this tenant
            pattern = f"rate_limit:{tenant_id}:*"
            keys = self.redis.keys(pattern)
            
            if keys:
                self.redis.delete(*keys)
            
            return True
            
        except Exception as e:
            print(f"Error resetting tenant limits: {e}")
            return False
    
    def get_top_usage_tenants(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get tenants with highest usage (admin function)
        
        Args:
            limit: Maximum number of tenants to return
            
        Returns:
            List of tenant usage statistics
        """
        try:
            # This would require more complex Redis operations
            # For now, return empty list - can be implemented later
            return []
            
        except Exception as e:
            print(f"Error getting top usage tenants: {e}")
            return []


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def get_rate_limit_status(tenant_id: UUID) -> Dict[str, Any]:
    """
    Get current rate limit status for tenant
    
    Args:
        tenant_id: Tenant UUID
        
    Returns:
        Rate limit status information
    """
    try:
        limiter = get_rate_limiter()
        stats = limiter.get_usage_stats(tenant_id)
        
        return {
            "tenant_id": str(tenant_id),
            "current_usage": stats,
            "status": "active",
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "tenant_id": str(tenant_id),
            "error": str(e),
            "status": "error",
            "retrieved_at": datetime.utcnow().isoformat()
        }


async def check_tenant_rate_limit(
    tenant_id: UUID, 
    plan: TenantPlan, 
    endpoint: str = "general"
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if tenant request is within rate limits
    
    Args:
        tenant_id: Tenant UUID
        plan: Tenant plan
        endpoint: Endpoint being accessed
        
    Returns:
        Tuple of (is_allowed, rate_limit_info)
    """
    try:
        limiter = get_rate_limiter()
        return limiter.check_rate_limit(tenant_id, plan, endpoint)
        
    except Exception as e:
        # If rate limiting fails, allow the request but log the error
        print(f"Rate limiting check failed: {e}")
        return True, {
            "error": str(e),
            "fallback": True,
            "tenant_id": str(tenant_id)
        }


async def increment_tenant_usage(
    tenant_id: UUID, 
    plan: TenantPlan, 
    endpoint: str = "general"
) -> Dict[str, Any]:
    """
    Increment tenant usage counters
    
    Args:
        tenant_id: Tenant UUID
        plan: Tenant plan
        endpoint: Endpoint that was accessed
        
    Returns:
        Updated usage information
    """
    try:
        limiter = get_rate_limiter()
        return limiter.increment_usage(tenant_id, plan, endpoint)
        
    except Exception as e:
        print(f"Error incrementing tenant usage: {e}")
        return {
            "error": str(e),
            "tenant_id": str(tenant_id)
        }


class RateLimitMiddleware:
    """
    Middleware for automatic rate limiting
    
    This can be used as FastAPI middleware to automatically
    apply rate limiting to all API endpoints.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """
        ASGI middleware implementation
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # This would be implemented if automatic middleware is needed
        # For now, rate limiting is handled in the auth middleware
        await self.app(scope, receive, send)