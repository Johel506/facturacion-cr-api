"""
Error monitoring and alerting system for Costa Rica Electronic Invoice API
Provides error rate tracking, alerting, and health metrics
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorMetric:
    """Error metric data structure"""
    error_code: str
    category: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    severity: str
    is_retryable: bool
    affected_tenants: set = field(default_factory=set)
    sample_messages: List[str] = field(default_factory=list)


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    level: AlertLevel
    title: str
    message: str
    error_code: str
    category: str
    count: int
    threshold: int
    time_window: int
    created_at: datetime
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ErrorMonitor:
    """
    Error monitoring system with rate tracking and alerting
    """
    
    def __init__(self):
        self.error_metrics: Dict[str, ErrorMetric] = {}
        self.error_history: deque = deque(maxlen=10000)  # Keep last 10k errors
        self.active_alerts: Dict[str, Alert] = {}
        self.resolved_alerts: List[Alert] = []
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.monitoring_enabled = True
        
        # Time windows for rate calculation (in seconds)
        self.time_windows = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "24h": 86400
        }
        
        logger.info("Error monitor initialized")
    
    def _initialize_alert_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """Initialize alert thresholds for different error types"""
        return {
            # Critical errors - immediate alert
            "CERTIFICATE_ERROR": {
                "threshold": 1,
                "time_window": 60,
                "level": AlertLevel.CRITICAL,
                "message": "Certificate error detected - immediate attention required"
            },
            "MINISTRY_AUTHENTICATION_ERROR": {
                "threshold": 3,
                "time_window": 300,
                "level": AlertLevel.CRITICAL,
                "message": "Ministry authentication failures - check credentials"
            },
            "DATABASE_CONNECTION_ERROR": {
                "threshold": 5,
                "time_window": 300,
                "level": AlertLevel.CRITICAL,
                "message": "Database connection issues detected"
            },
            
            # High priority errors
            "MINISTRY_API_ERROR": {
                "threshold": 10,
                "time_window": 900,
                "level": AlertLevel.ERROR,
                "message": "High rate of Ministry API errors"
            },
            "VALIDATION_ERROR": {
                "threshold": 50,
                "time_window": 900,
                "level": AlertLevel.WARNING,
                "message": "High rate of validation errors - check data quality"
            },
            "BUSINESS_RULE_VALIDATION": {
                "threshold": 25,
                "time_window": 900,
                "level": AlertLevel.WARNING,
                "message": "High rate of business rule violations"
            },
            
            # System errors
            "INTERNAL_SERVER_ERROR": {
                "threshold": 20,
                "time_window": 900,
                "level": AlertLevel.ERROR,
                "message": "High rate of internal server errors"
            },
            "RATE_LIMIT_EXCEEDED": {
                "threshold": 100,
                "time_window": 3600,
                "level": AlertLevel.WARNING,
                "message": "High rate of rate limit violations"
            },
            
            # Network and external service errors
            "NETWORK_ERROR": {
                "threshold": 15,
                "time_window": 600,
                "level": AlertLevel.WARNING,
                "message": "Network connectivity issues detected"
            },
            "CACHE_ERROR": {
                "threshold": 30,
                "time_window": 900,
                "level": AlertLevel.WARNING,
                "message": "Cache system issues detected"
            }
        }
    
    def record_error(
        self,
        error_code: str,
        category: str,
        severity: str,
        message: str,
        tenant_id: Optional[str] = None,
        is_retryable: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Record an error occurrence for monitoring
        
        Args:
            error_code: Error code identifier
            category: Error category
            severity: Error severity level
            message: Error message
            tenant_id: Optional tenant identifier
            is_retryable: Whether error is retryable
            context: Additional error context
        """
        if not self.monitoring_enabled:
            return
        
        try:
            now = datetime.utcnow()
            
            # Update or create error metric
            if error_code in self.error_metrics:
                metric = self.error_metrics[error_code]
                metric.count += 1
                metric.last_occurrence = now
                if tenant_id:
                    metric.affected_tenants.add(tenant_id)
                if len(metric.sample_messages) < 5:
                    metric.sample_messages.append(message)
            else:
                metric = ErrorMetric(
                    error_code=error_code,
                    category=category,
                    count=1,
                    first_occurrence=now,
                    last_occurrence=now,
                    severity=severity,
                    is_retryable=is_retryable,
                    affected_tenants={tenant_id} if tenant_id else set(),
                    sample_messages=[message]
                )
                self.error_metrics[error_code] = metric
            
            # Add to error history
            error_record = {
                "timestamp": now.isoformat(),
                "error_code": error_code,
                "category": category,
                "severity": severity,
                "message": message,
                "tenant_id": tenant_id,
                "is_retryable": is_retryable,
                "context": context or {}
            }
            self.error_history.append(error_record)
            
            # Check for alert conditions
            self._check_alert_conditions(error_code, category, now)
            
        except Exception as e:
            logger.error(f"Error recording error metric: {e}")
    
    def _check_alert_conditions(self, error_code: str, category: str, timestamp: datetime):
        """Check if error conditions warrant an alert"""
        try:
            # Check specific error code thresholds
            if error_code in self.alert_thresholds:
                threshold_config = self.alert_thresholds[error_code]
                self._evaluate_threshold(error_code, threshold_config, timestamp)
            
            # Check category-based thresholds
            category_thresholds = {
                "validation": {"threshold": 100, "time_window": 3600, "level": AlertLevel.WARNING},
                "external_service": {"threshold": 50, "time_window": 1800, "level": AlertLevel.ERROR},
                "system": {"threshold": 30, "time_window": 900, "level": AlertLevel.ERROR},
                "certificate": {"threshold": 5, "time_window": 300, "level": AlertLevel.CRITICAL}
            }
            
            if category in category_thresholds:
                threshold_config = category_thresholds[category]
                self._evaluate_category_threshold(category, threshold_config, timestamp)
                
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
    
    def _evaluate_threshold(
        self,
        error_code: str,
        threshold_config: Dict[str, Any],
        timestamp: datetime
    ):
        """Evaluate if error code exceeds threshold"""
        time_window = threshold_config["time_window"]
        threshold = threshold_config["threshold"]
        
        # Count errors in time window
        cutoff_time = timestamp - timedelta(seconds=time_window)
        error_count = sum(
            1 for record in self.error_history
            if (record["error_code"] == error_code and 
                datetime.fromisoformat(record["timestamp"]) >= cutoff_time)
        )
        
        if error_count >= threshold:
            alert_id = f"{error_code}_{int(timestamp.timestamp())}"
            if alert_id not in self.active_alerts:
                self._create_alert(
                    alert_id=alert_id,
                    error_code=error_code,
                    category=self.error_metrics[error_code].category,
                    count=error_count,
                    threshold_config=threshold_config,
                    timestamp=timestamp
                )
    
    def _evaluate_category_threshold(
        self,
        category: str,
        threshold_config: Dict[str, Any],
        timestamp: datetime
    ):
        """Evaluate if error category exceeds threshold"""
        time_window = threshold_config["time_window"]
        threshold = threshold_config["threshold"]
        
        # Count errors in category within time window
        cutoff_time = timestamp - timedelta(seconds=time_window)
        error_count = sum(
            1 for record in self.error_history
            if (record["category"] == category and 
                datetime.fromisoformat(record["timestamp"]) >= cutoff_time)
        )
        
        if error_count >= threshold:
            alert_id = f"{category}_category_{int(timestamp.timestamp())}"
            if alert_id not in self.active_alerts:
                self._create_alert(
                    alert_id=alert_id,
                    error_code=f"{category.upper()}_CATEGORY_THRESHOLD",
                    category=category,
                    count=error_count,
                    threshold_config=threshold_config,
                    timestamp=timestamp
                )
    
    def _create_alert(
        self,
        alert_id: str,
        error_code: str,
        category: str,
        count: int,
        threshold_config: Dict[str, Any],
        timestamp: datetime
    ):
        """Create a new alert"""
        try:
            alert = Alert(
                id=alert_id,
                level=threshold_config["level"],
                title=f"Error Threshold Exceeded: {error_code}",
                message=threshold_config.get("message", f"Error rate exceeded for {error_code}"),
                error_code=error_code,
                category=category,
                count=count,
                threshold=threshold_config["threshold"],
                time_window=threshold_config["time_window"],
                created_at=timestamp,
                metadata={
                    "error_rate": count / (threshold_config["time_window"] / 60),  # errors per minute
                    "affected_tenants": len(self.error_metrics.get(error_code, ErrorMetric("", "", 0, timestamp, timestamp, "", False)).affected_tenants)
                }
            )
            
            self.active_alerts[alert_id] = alert
            
            # Log the alert
            logger.warning(
                f"Alert created: {alert.title}",
                extra={
                    "alert_id": alert_id,
                    "level": alert.level.value,
                    "error_code": error_code,
                    "category": category,
                    "count": count,
                    "threshold": threshold_config["threshold"]
                }
            )
            
            # Send alert notification (implement based on your notification system)
            asyncio.create_task(self._send_alert_notification(alert))
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def _send_alert_notification(self, alert: Alert):
        """Send alert notification (implement based on your notification system)"""
        try:
            # This is a placeholder - implement actual notification logic
            # Examples: email, Slack, webhook, etc.
            
            notification_data = {
                "alert_id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "error_code": alert.error_code,
                "category": alert.category,
                "count": alert.count,
                "threshold": alert.threshold,
                "created_at": alert.created_at.isoformat(),
                "metadata": alert.metadata
            }
            
            logger.info(f"Alert notification sent: {json.dumps(notification_data)}")
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    def resolve_alert(self, alert_id: str, resolution_note: Optional[str] = None):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts.pop(alert_id)
            alert.resolved_at = datetime.utcnow()
            alert.is_resolved = True
            if resolution_note:
                alert.metadata["resolution_note"] = resolution_note
            
            self.resolved_alerts.append(alert)
            
            logger.info(f"Alert resolved: {alert_id}")
    
    def get_error_rates(self, time_window: str = "1h") -> Dict[str, Any]:
        """Get error rates for specified time window"""
        if time_window not in self.time_windows:
            raise ValueError(f"Invalid time window: {time_window}")
        
        window_seconds = self.time_windows[time_window]
        cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        # Filter errors within time window
        recent_errors = [
            record for record in self.error_history
            if datetime.fromisoformat(record["timestamp"]) >= cutoff_time
        ]
        
        # Calculate rates by category and error code
        category_counts = defaultdict(int)
        error_code_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for error in recent_errors:
            category_counts[error["category"]] += 1
            error_code_counts[error["error_code"]] += 1
            severity_counts[error["severity"]] += 1
        
        return {
            "time_window": time_window,
            "window_seconds": window_seconds,
            "total_errors": len(recent_errors),
            "error_rate_per_minute": len(recent_errors) / (window_seconds / 60),
            "by_category": dict(category_counts),
            "by_error_code": dict(error_code_counts),
            "by_severity": dict(severity_counts),
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        now = datetime.utcnow()
        
        # Calculate metrics for different time windows
        metrics = {}
        for window_name, window_seconds in self.time_windows.items():
            cutoff_time = now - timedelta(seconds=window_seconds)
            recent_errors = [
                record for record in self.error_history
                if datetime.fromisoformat(record["timestamp"]) >= cutoff_time
            ]
            
            metrics[window_name] = {
                "total_errors": len(recent_errors),
                "error_rate": len(recent_errors) / (window_seconds / 60),  # per minute
                "critical_errors": sum(1 for e in recent_errors if e["severity"] == "critical"),
                "retryable_errors": sum(1 for e in recent_errors if e["is_retryable"]),
                "unique_error_codes": len(set(e["error_code"] for e in recent_errors)),
                "affected_tenants": len(set(e["tenant_id"] for e in recent_errors if e["tenant_id"]))
            }
        
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "total_error_types": len(self.error_metrics),
            "active_alerts": len(self.active_alerts),
            "resolved_alerts": len(self.resolved_alerts),
            "metrics_by_window": metrics,
            "top_errors": self._get_top_errors(10),
            "calculated_at": now.isoformat()
        }
    
    def _get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top errors by count"""
        sorted_errors = sorted(
            self.error_metrics.items(),
            key=lambda x: x[1].count,
            reverse=True
        )
        
        return [
            {
                "error_code": error_code,
                "category": metric.category,
                "count": metric.count,
                "severity": metric.severity,
                "first_occurrence": metric.first_occurrence.isoformat(),
                "last_occurrence": metric.last_occurrence.isoformat(),
                "affected_tenants": len(metric.affected_tenants),
                "is_retryable": metric.is_retryable
            }
            for error_code, metric in sorted_errors[:limit]
        ]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [
            {
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "error_code": alert.error_code,
                "category": alert.category,
                "count": alert.count,
                "threshold": alert.threshold,
                "time_window": alert.time_window,
                "created_at": alert.created_at.isoformat(),
                "metadata": alert.metadata
            }
            for alert in self.active_alerts.values()
        ]
    
    def clear_old_data(self, days_to_keep: int = 7):
        """Clear old error data to prevent memory issues"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Clear old error history
            self.error_history = deque(
                [record for record in self.error_history 
                 if datetime.fromisoformat(record["timestamp"]) >= cutoff_time],
                maxlen=10000
            )
            
            # Clear old resolved alerts
            self.resolved_alerts = [
                alert for alert in self.resolved_alerts
                if alert.resolved_at and alert.resolved_at >= cutoff_time
            ]
            
            logger.info(f"Cleared error data older than {days_to_keep} days")
            
        except Exception as e:
            logger.error(f"Error clearing old data: {e}")
    
    def enable_monitoring(self):
        """Enable error monitoring"""
        self.monitoring_enabled = True
        logger.info("Error monitoring enabled")
    
    def disable_monitoring(self):
        """Disable error monitoring"""
        self.monitoring_enabled = False
        logger.info("Error monitoring disabled")
    
    def reset_metrics(self):
        """Reset all error metrics (use with caution)"""
        self.error_metrics.clear()
        self.error_history.clear()
        self.active_alerts.clear()
        self.resolved_alerts.clear()
        logger.warning("All error metrics have been reset")


# Global error monitor instance
error_monitor = ErrorMonitor()