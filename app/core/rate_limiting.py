"""
Redis-based rate limiting system with sliding window algorithm
"""
import time
import json
from typing import Dict, List, Optional, Tuple, NamedTuple
from datetime import datetime, timezone, timedelta
from enum import Enum

from app.core.redis import redis_manager
from app.core.config import settings


class RateLimitType(str, Enum):
    """Types of rate limits"""
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"
    DOCUMENT_CREATION = "document_creation"
    API_REQUESTS = "api_requests"


class RateLimitResult(NamedTuple):
    """Result of rate limit check"""
    allowed: bool
    current_count: int
    limit: int
    reset_time: int
    retry_after: Optional[int] = None
    window_type: str = "sliding"


class TenantPlan(str, Enum):
    """Tenant subscription plans"""
    BASICO = "basico"
    PRO = "pro"
    EMPRESA = "empresa"


class RateLimitConfig:
    """Rate limit configuration for different plans and endpoints"""
    
    # Plan-based limits (requests per hour)
    PLAN_LIMITS = {
        TenantPlan.BASICO: {
            RateLimitType.HOURLY: 100,
            RateLimitType.DAILY: 500,
            RateLimitType.MONTHLY: 100,  # Monthly document limit
            RateLimitType.DOCUMENT_CREATION: 50,  # Documents per hour
            RateLimitType.API_REQUESTS: 100  # API requests per hour
        },
        TenantPlan.PRO: {
            RateLimitType.HOURLY: 500,
            RateLimitType.DAILY: 2000,
            RateLimitType.MONTHLY: 1000,  # Monthly document limit
            RateLimitType.DOCUMENT_CREATION: 200,  # Documents per hour
            RateLimitType.API_REQUESTS: 500  # API requests per hour
        },
        TenantPlan.EMPRESA: {
            RateLimitType.HOURLY: 2000,
            RateLimitType.DAILY: 10000,
            RateLimitType.MONTHLY: -1,  # Unlimited monthly documents
            RateLimitType.DOCUMENT_CREATION: 1000,  # Documents per hour
            RateLimitType.API_REQUESTS: 2000  # API requests per hour
        }
    }
    
    # Endpoint-specific limits (overrides plan limits for specific endpoints)
    ENDPOINT_LIMITS = {
        "/api/v1/documentos": {
            "weight": 5,  # Each document creation counts as 5 requests
            "burst_limit": 10  # Maximum burst requests in 1 minute
        },
        "/api/v1/cabys/search": {
            "weight": 1,
            "burst_limit": 50
        },
        "/api/v1/tenants": {
            "weight": 2,
            "burst_limit": 20
        }
    }
    
    @classmethod
    def get_plan_limit(cls, plan: TenantPlan, limit_type: RateLimitType) -> int:
        """Get rate limit for plan and type"""
        return cls.PLAN_LIMITS.get(plan, cls.PLAN_LIMITS[TenantPlan.BASICO]).get(
            limit_type, 100
        )
    
    @classmethod
    def get_endpoint_config(cls, endpoint: str) -> Dict:
        """Get endpoint-specific configuration"""
        return cls.ENDPOINT_LIMITS.get(endpoint, {"weight": 1, "burst_limit": 100})


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using Redis sorted sets
    
    This implementation provides more accurate rate limiting compared to
    fixed window counters by tracking individual request timestamps.
    
    Requirements: 4.3, 1.4, 1.5
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client or redis_manager
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        weight: int = 1
    ) -> RateLimitResult:
        """
        Check rate limit using sliding window algorithm
        
        Args:
            key: Unique identifier for the rate limit (e.g., tenant_id:endpoint)
            limit: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
            weight: Weight of this request (default 1)
            
        Returns:
            RateLimitResult with limit check results
        """
        if limit <= 0:  # Unlimited
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=limit,
                reset_time=int(time.time() + window_seconds)
            )
        
        now = time.time()
        window_start = now - window_seconds
        
        # Redis pipeline for atomic operations
        pipe = await self.redis.redis_client.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]
        
        # Check if adding this request would exceed limit
        if current_count + weight > limit:
            # Calculate retry after time
            oldest_request = await self.redis.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                oldest_time = oldest_request[0][1]
                retry_after = int(oldest_time + window_seconds - now)
            else:
                retry_after = window_seconds
            
            return RateLimitResult(
                allowed=False,
                current_count=current_count,
                limit=limit,
                reset_time=int(now + window_seconds),
                retry_after=max(1, retry_after)
            )
        
        # Add current request to window
        request_id = f"{now}:{weight}"
        await self.redis.redis_client.zadd(key, {request_id: now})
        
        # Set expiration for cleanup
        await self.redis.redis_client.expire(key, window_seconds + 60)
        
        return RateLimitResult(
            allowed=True,
            current_count=current_count + weight,
            limit=limit,
            reset_time=int(now + window_seconds)
        )
    
    async def get_current_usage(self, key: str, window_seconds: int) -> int:
        """Get current usage count for a key"""
        now = time.time()
        window_start = now - window_seconds
        
        # Remove expired entries and count current
        await self.redis.redis_client.zremrangebyscore(key, 0, window_start)
        return await self.redis.redis_client.zcard(key)
    
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        return await self.redis.delete(key)


class MonthlyDocumentLimiter:
    """
    Monthly document limit tracker with automatic reset
    
    Requirements: 1.4, 1.5
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client or redis_manager
    
    async def check_monthly_limit(
        self,
        tenant_id: str,
        plan: TenantPlan,
        increment: bool = True
    ) -> RateLimitResult:
        """
        Check monthly document creation limit
        
        Args:
            tenant_id: Tenant UUID
            plan: Tenant subscription plan
            increment: Whether to increment counter if allowed
            
        Returns:
            RateLimitResult with monthly limit check
        """
        limit = RateLimitConfig.get_plan_limit(plan, RateLimitType.MONTHLY)
        
        if limit <= 0:  # Unlimited
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=limit,
                reset_time=self._get_next_month_timestamp()
            )
        
        # Get current month key
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"monthly_docs:{tenant_id}:{current_month}"
        
        # Get current count
        current_count = await self._get_monthly_count(key)
        
        if current_count >= limit:
            return RateLimitResult(
                allowed=False,
                current_count=current_count,
                limit=limit,
                reset_time=self._get_next_month_timestamp(),
                retry_after=self._get_seconds_until_next_month()
            )
        
        # Increment counter if requested
        if increment:
            new_count = await self.redis.increment(key)
            # Set expiration for next month + buffer
            await self.redis.expire(key, self._get_seconds_until_next_month() + 86400)
            current_count = new_count
        
        return RateLimitResult(
            allowed=True,
            current_count=current_count,
            limit=limit,
            reset_time=self._get_next_month_timestamp()
        )
    
    async def get_monthly_usage(self, tenant_id: str) -> Dict[str, int]:
        """Get monthly usage statistics for tenant"""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"monthly_docs:{tenant_id}:{current_month}"
        
        current_count = await self._get_monthly_count(key)
        
        return {
            "current_month": current_month,
            "documents_used": current_count,
            "reset_time": self._get_next_month_timestamp()
        }
    
    async def reset_monthly_counter(self, tenant_id: str) -> bool:
        """Reset monthly counter for tenant"""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"monthly_docs:{tenant_id}:{current_month}"
        return await self.redis.delete(key)
    
    async def _get_monthly_count(self, key: str) -> int:
        """Get current monthly count"""
        count = await self.redis.get(key)
        return int(count) if count else 0
    
    def _get_next_month_timestamp(self) -> int:
        """Get timestamp for start of next month"""
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        return int(next_month.timestamp())
    
    def _get_seconds_until_next_month(self) -> int:
        """Get seconds until next month starts"""
        now = int(time.time())
        next_month = self._get_next_month_timestamp()
        return next_month - now


class ComprehensiveRateLimiter:
    """
    Comprehensive rate limiting system combining multiple strategies
    
    Requirements: 4.3, 1.4, 1.5
    """
    
    def __init__(self):
        self.sliding_limiter = SlidingWindowRateLimiter()
        self.monthly_limiter = MonthlyDocumentLimiter()
    
    async def check_all_limits(
        self,
        tenant_id: str,
        plan: TenantPlan,
        endpoint: str,
        is_document_creation: bool = False
    ) -> Tuple[bool, List[RateLimitResult], Dict[str, str]]:
        """
        Check all applicable rate limits for a request
        
        Args:
            tenant_id: Tenant UUID
            plan: Tenant subscription plan
            endpoint: API endpoint being accessed
            is_document_creation: Whether this is a document creation request
            
        Returns:
            Tuple of (allowed, limit_results, headers)
        """
        results = []
        headers = {}
        
        # Get endpoint configuration
        endpoint_config = RateLimitConfig.get_endpoint_config(endpoint)
        weight = endpoint_config["weight"]
        
        # 1. Check hourly API request limit
        hourly_limit = RateLimitConfig.get_plan_limit(plan, RateLimitType.API_REQUESTS)
        hourly_key = f"hourly_api:{tenant_id}"
        hourly_result = await self.sliding_limiter.check_rate_limit(
            hourly_key, hourly_limit, 3600, weight
        )
        results.append(hourly_result)
        
        # Add hourly limit headers
        headers.update({
            "X-RateLimit-Limit-Hour": str(hourly_limit),
            "X-RateLimit-Remaining-Hour": str(max(0, hourly_limit - hourly_result.current_count)),
            "X-RateLimit-Reset-Hour": str(hourly_result.reset_time)
        })
        
        # 2. Check daily limit
        daily_limit = RateLimitConfig.get_plan_limit(plan, RateLimitType.DAILY)
        daily_key = f"daily_api:{tenant_id}"
        daily_result = await self.sliding_limiter.check_rate_limit(
            daily_key, daily_limit, 86400, weight
        )
        results.append(daily_result)
        
        # Add daily limit headers
        headers.update({
            "X-RateLimit-Limit-Day": str(daily_limit),
            "X-RateLimit-Remaining-Day": str(max(0, daily_limit - daily_result.current_count)),
            "X-RateLimit-Reset-Day": str(daily_result.reset_time)
        })
        
        # 3. Check burst limit for endpoint
        burst_limit = endpoint_config["burst_limit"]
        burst_key = f"burst:{tenant_id}:{endpoint.replace('/', '_')}"
        burst_result = await self.sliding_limiter.check_rate_limit(
            burst_key, burst_limit, 60, weight  # 1 minute window
        )
        results.append(burst_result)
        
        # 4. Check document creation specific limits
        if is_document_creation:
            # Monthly document limit
            monthly_result = await self.monthly_limiter.check_monthly_limit(
                tenant_id, plan, increment=False  # Don't increment yet
            )
            results.append(monthly_result)
            
            # Add monthly limit headers
            headers.update({
                "X-RateLimit-Limit-Month": str(monthly_result.limit),
                "X-RateLimit-Remaining-Month": str(max(0, monthly_result.limit - monthly_result.current_count)) if monthly_result.limit > 0 else "unlimited",
                "X-RateLimit-Reset-Month": str(monthly_result.reset_time)
            })
            
            # Hourly document creation limit
            doc_hourly_limit = RateLimitConfig.get_plan_limit(plan, RateLimitType.DOCUMENT_CREATION)
            doc_hourly_key = f"hourly_docs:{tenant_id}"
            doc_hourly_result = await self.sliding_limiter.check_rate_limit(
                doc_hourly_key, doc_hourly_limit, 3600, 1
            )
            results.append(doc_hourly_result)
        
        # Check if any limit is exceeded
        allowed = all(result.allowed for result in results)
        
        # Add general headers
        headers.update({
            "X-RateLimit-Policy": "sliding-window",
            "X-RateLimit-Plan": plan.value
        })
        
        # If not allowed, add retry-after header
        if not allowed:
            retry_after_times = [r.retry_after for r in results if r.retry_after]
            if retry_after_times:
                headers["Retry-After"] = str(min(retry_after_times))
        
        return allowed, results, headers
    
    async def increment_counters(
        self,
        tenant_id: str,
        plan: TenantPlan,
        endpoint: str,
        is_document_creation: bool = False
    ) -> None:
        """
        Increment all relevant counters after successful request
        
        Args:
            tenant_id: Tenant UUID
            plan: Tenant subscription plan
            endpoint: API endpoint accessed
            is_document_creation: Whether this was document creation
        """
        # Increment monthly document counter if applicable
        if is_document_creation:
            await self.monthly_limiter.check_monthly_limit(
                tenant_id, plan, increment=True
            )
    
    async def get_usage_stats(self, tenant_id: str, plan: TenantPlan) -> Dict:
        """Get comprehensive usage statistics for tenant"""
        stats = {}
        
        # Monthly usage
        monthly_stats = await self.monthly_limiter.get_monthly_usage(tenant_id)
        stats["monthly"] = monthly_stats
        
        # Hourly API usage
        hourly_key = f"hourly_api:{tenant_id}"
        hourly_usage = await self.sliding_limiter.get_current_usage(hourly_key, 3600)
        hourly_limit = RateLimitConfig.get_plan_limit(plan, RateLimitType.API_REQUESTS)
        
        stats["hourly"] = {
            "requests_used": hourly_usage,
            "requests_limit": hourly_limit,
            "requests_remaining": max(0, hourly_limit - hourly_usage)
        }
        
        # Daily API usage
        daily_key = f"daily_api:{tenant_id}"
        daily_usage = await self.sliding_limiter.get_current_usage(daily_key, 86400)
        daily_limit = RateLimitConfig.get_plan_limit(plan, RateLimitType.DAILY)
        
        stats["daily"] = {
            "requests_used": daily_usage,
            "requests_limit": daily_limit,
            "requests_remaining": max(0, daily_limit - daily_usage)
        }
        
        return stats
    
    async def reset_all_limits(self, tenant_id: str) -> Dict[str, bool]:
        """Reset all rate limits for a tenant (admin function)"""
        results = {}
        
        # Reset monthly counter
        results["monthly"] = await self.monthly_limiter.reset_monthly_counter(tenant_id)
        
        # Reset hourly limits
        hourly_key = f"hourly_api:{tenant_id}"
        results["hourly_api"] = await self.sliding_limiter.reset_limit(hourly_key)
        
        hourly_docs_key = f"hourly_docs:{tenant_id}"
        results["hourly_docs"] = await self.sliding_limiter.reset_limit(hourly_docs_key)
        
        # Reset daily limits
        daily_key = f"daily_api:{tenant_id}"
        results["daily"] = await self.sliding_limiter.reset_limit(daily_key)
        
        return results


# Global rate limiter instance
rate_limiter = ComprehensiveRateLimiter()