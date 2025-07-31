"""
Audit logging utilities and helpers for Costa Rica Electronic Invoice API
Provides convenient functions for common audit logging scenarios
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from app.core.logging import audit_logger, LogLevel, LogCategory, log_operation_context


def log_tenant_creation(
    tenant_id: str,
    tenant_data: Dict[str, Any],
    created_by: Optional[str] = None,
    client_ip: Optional[str] = None
):
    """Log tenant creation event"""
    audit_logger.log_structured(
        level=LogLevel.INFO,
        category=LogCategory.AUDIT,
        message=f"Tenant created: {tenant_id}",
        event_type="tenant_created",
        tenant_id=tenant_id,
        tenant_name=tenant_data.get("nombre_empresa"),
        cedula_juridica=tenant_data.get("cedula_juridica"),
        created_by=created_by,
        client_ip=client_ip
    )


def log_tenant_update(
    tenant_id: str,
    updated_fields: List[str],
    old_values: Dict[str, Any],
    new_values: Dict[str, Any],
    updated_by: Optional[str] = None,
    client_ip: Optional[str] = None
):
    """Log tenant update event"""
    audit_logger.log_structured(
        level=LogLevel.INFO,
        category=LogCategory.AUDIT,
        message=f"Tenant updated: {tenant_id}",
        event_type="tenant_updated",
        tenant_id=tenant_id,
        updated_fields=updated_fields,
        old_values=old_values,
        new_values=new_values,
        updated_by=updated_by,
        client_ip=client_ip
    )


def log_certificate_upload(
    tenant_id: str,
    certificate_subject: str,
    certificate_serial: str,
    expiry_date: str,
    uploaded_by: Optional[str] = None,
    client_ip: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
):
    """Log certificate upload event"""
    audit_logger.log_certificate_event(
        event_type="certificate_uploaded",
        tenant_id=tenant_id,
        certificate_subject=certificate_subject,
        certificate_serial=certificate_serial,
        expiry_date=expiry_date,
        success=success,
        error_message=error_message
    )
    
    # Also log as audit event
    audit_logger.log_structured(
        level=LogLevel.INFO if success else LogLevel.ERROR,
        category=LogCategory.AUDIT,
        message=f"Certificate {'uploaded' if success else 'upload failed'} for tenant {tenant_id}",
        event_type="certificate_upload",
        tenant_id=tenant_id,
        certificate_subject=certificate_subject,
        uploaded_by=uploaded_by,
        client_ip=client_ip,
        success=success,
        error_message=error_message
    )


def log_certificate_expiry_warning(
    tenant_id: str,
    certificate_subject: str,
    expiry_date: str,
    days_until_expiry: int
):
    """Log certificate expiry warning"""
    severity = "critical" if days_until_expiry <= 7 else "high" if days_until_expiry <= 15 else "medium"
    
    audit_logger.log_security_event(
        event_type="certificate_expiry_warning",
        severity=severity,
        description=f"Certificate expires in {days_until_expiry} days",
        tenant_id=tenant_id,
        additional_data={
            "certificate_subject": certificate_subject,
            "expiry_date": expiry_date,
            "days_until_expiry": days_until_expiry
        }
    )


def log_document_creation(
    document_id: str,
    document_type: str,
    document_key: str,
    tenant_id: str,
    created_by: Optional[str] = None,
    client_ip: Optional[str] = None,
    processing_time_ms: Optional[float] = None
):
    """Log document creation event"""
    audit_logger.log_document_lifecycle(
        event_type="document_created",
        document_id=document_id,
        document_type=document_type,
        document_key=document_key,
        tenant_id=tenant_id,
        status="created",
        processing_time_ms=processing_time_ms
    )
    
    # Also log as audit event
    audit_logger.log_structured(
        level=LogLevel.INFO,
        category=LogCategory.AUDIT,
        message=f"Document created: {document_type} {document_id}",
        event_type="document_created",
        document_id=document_id,
        document_type=document_type,
        document_key=document_key,
        tenant_id=tenant_id,
        created_by=created_by,
        client_ip=client_ip
    )


def log_document_submission(
    document_id: str,
    document_type: str,
    document_key: str,
    tenant_id: str,
    ministry_endpoint: str,
    success: bool = True,
    ministry_response: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    processing_time_ms: Optional[float] = None
):
    """Log document submission to Ministry"""
    audit_logger.log_document_lifecycle(
        event_type="document_submitted",
        document_id=document_id,
        document_type=document_type,
        document_key=document_key,
        tenant_id=tenant_id,
        status="submitted" if success else "submission_failed",
        ministry_response=ministry_response,
        error_message=error_message,
        processing_time_ms=processing_time_ms
    )
    
    # Also log Ministry interaction
    audit_logger.log_ministry_interaction(
        interaction_type="document_submission",
        endpoint=ministry_endpoint,
        response_data=ministry_response,
        duration_ms=processing_time_ms,
        tenant_id=tenant_id,
        document_id=document_id,
        success=success,
        error_message=error_message
    )


def log_document_status_change(
    document_id: str,
    document_type: str,
    document_key: str,
    tenant_id: str,
    old_status: str,
    new_status: str,
    ministry_response: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None
):
    """Log document status change"""
    audit_logger.log_document_lifecycle(
        event_type="status_changed",
        document_id=document_id,
        document_type=document_type,
        document_key=document_key,
        tenant_id=tenant_id,
        status=new_status,
        ministry_response=ministry_response
    )
    
    # Also log as audit event
    audit_logger.log_structured(
        level=LogLevel.INFO,
        category=LogCategory.AUDIT,
        message=f"Document status changed: {document_id} from {old_status} to {new_status}",
        event_type="document_status_changed",
        document_id=document_id,
        document_type=document_type,
        document_key=document_key,
        tenant_id=tenant_id,
        old_status=old_status,
        new_status=new_status,
        reason=reason
    )


def log_ministry_response_received(
    document_id: str,
    document_key: str,
    tenant_id: str,
    response_type: str,
    ministry_response: Dict[str, Any],
    processing_time_ms: Optional[float] = None
):
    """Log Ministry response received"""
    audit_logger.log_ministry_interaction(
        interaction_type="response_received",
        endpoint="ministry_callback",
        response_data=ministry_response,
        duration_ms=processing_time_ms,
        tenant_id=tenant_id,
        document_id=document_id,
        success=True
    )
    
    # Also log as document lifecycle event
    audit_logger.log_document_lifecycle(
        event_type="ministry_response_received",
        document_id=document_id,
        document_type=ministry_response.get("tipo_documento", "unknown"),
        document_key=document_key,
        tenant_id=tenant_id,
        status=response_type,
        ministry_response=ministry_response,
        processing_time_ms=processing_time_ms
    )


def log_api_key_usage(
    api_key_id: str,
    tenant_id: str,
    endpoint: str,
    method: str,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_code: Optional[str] = None
):
    """Log API key usage"""
    audit_logger.log_structured(
        level=LogLevel.INFO if success else LogLevel.WARNING,
        category=LogCategory.AUDIT,
        message=f"API key used: {api_key_id} for {method} {endpoint}",
        event_type="api_key_used",
        api_key_id=api_key_id,
        tenant_id=tenant_id,
        endpoint=endpoint,
        method=method,
        client_ip=client_ip,
        user_agent=user_agent,
        success=success,
        error_code=error_code
    )


def log_rate_limit_exceeded(
    tenant_id: str,
    api_key_id: str,
    endpoint: str,
    limit: int,
    current_usage: int,
    reset_time: Optional[int] = None,
    client_ip: Optional[str] = None
):
    """Log rate limit exceeded event"""
    audit_logger.log_security_event(
        event_type="rate_limit_exceeded",
        severity="medium",
        description=f"Rate limit exceeded for tenant {tenant_id}",
        tenant_id=tenant_id,
        client_ip=client_ip,
        additional_data={
            "api_key_id": api_key_id,
            "endpoint": endpoint,
            "limit": limit,
            "current_usage": current_usage,
            "reset_time": reset_time
        }
    )


def log_suspicious_activity(
    activity_type: str,
    description: str,
    tenant_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
):
    """Log suspicious activity"""
    audit_logger.log_security_event(
        event_type="suspicious_activity",
        severity="high",
        description=f"Suspicious activity detected: {description}",
        tenant_id=tenant_id,
        client_ip=client_ip,
        additional_data={
            "activity_type": activity_type,
            "user_agent": user_agent,
            **(additional_data or {})
        }
    )


def log_data_access(
    resource_type: str,
    resource_id: str,
    action: str,
    tenant_id: str,
    accessed_by: Optional[str] = None,
    client_ip: Optional[str] = None,
    success: bool = True,
    reason: Optional[str] = None
):
    """Log data access events"""
    audit_logger.log_structured(
        level=LogLevel.INFO if success else LogLevel.WARNING,
        category=LogCategory.AUDIT,
        message=f"Data access: {action} {resource_type} {resource_id}",
        event_type="data_access",
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        tenant_id=tenant_id,
        accessed_by=accessed_by,
        client_ip=client_ip,
        success=success,
        reason=reason
    )


def log_configuration_change(
    config_type: str,
    config_key: str,
    old_value: Any,
    new_value: Any,
    changed_by: Optional[str] = None,
    client_ip: Optional[str] = None,
    tenant_id: Optional[str] = None
):
    """Log configuration changes"""
    audit_logger.log_structured(
        level=LogLevel.WARNING,
        category=LogCategory.AUDIT,
        message=f"Configuration changed: {config_type}.{config_key}",
        event_type="configuration_changed",
        config_type=config_type,
        config_key=config_key,
        old_value=str(old_value),
        new_value=str(new_value),
        changed_by=changed_by,
        client_ip=client_ip,
        tenant_id=tenant_id
    )


def log_backup_operation(
    operation_type: str,
    backup_type: str,
    success: bool = True,
    duration_ms: Optional[float] = None,
    backup_size: Optional[int] = None,
    error_message: Optional[str] = None
):
    """Log backup operations"""
    audit_logger.log_system_event(
        event_type="backup_operation",
        description=f"Backup {operation_type} for {backup_type}",
        severity="info" if success else "error",
        additional_data={
            "operation_type": operation_type,
            "backup_type": backup_type,
            "success": success,
            "duration_ms": duration_ms,
            "backup_size": backup_size,
            "error_message": error_message
        }
    )


def log_maintenance_event(
    event_type: str,
    description: str,
    scheduled: bool = True,
    duration_ms: Optional[float] = None,
    affected_services: Optional[List[str]] = None
):
    """Log maintenance events"""
    audit_logger.log_system_event(
        event_type="maintenance",
        description=f"Maintenance event: {description}",
        severity="info",
        additional_data={
            "maintenance_type": event_type,
            "scheduled": scheduled,
            "duration_ms": duration_ms,
            "affected_services": affected_services
        }
    )


def log_integration_event(
    integration_name: str,
    event_type: str,
    success: bool = True,
    duration_ms: Optional[float] = None,
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
):
    """Log external integration events"""
    audit_logger.log_structured(
        level=LogLevel.INFO if success else LogLevel.ERROR,
        category=LogCategory.AUDIT,
        message=f"Integration event: {integration_name} {event_type}",
        event_type="integration_event",
        integration_name=integration_name,
        integration_event_type=event_type,
        success=success,
        duration_ms=duration_ms,
        request_data=request_data,
        response_data=response_data,
        error_message=error_message
    )


# Context managers for common audit scenarios
def audit_document_processing(
    document_id: str,
    document_type: str,
    tenant_id: str,
    operation: str = "processing"
):
    """Context manager for auditing document processing operations"""
    return log_operation_context(
        operation_name=f"document_{operation}",
        category=LogCategory.DOCUMENT_LIFECYCLE,
        tenant_id=tenant_id,
        additional_data={
            "document_id": document_id,
            "document_type": document_type
        }
    )


def audit_ministry_interaction(
    interaction_type: str,
    endpoint: str,
    tenant_id: Optional[str] = None,
    document_id: Optional[str] = None
):
    """Context manager for auditing Ministry interactions"""
    return log_operation_context(
        operation_name=f"ministry_{interaction_type}",
        category=LogCategory.MINISTRY_INTERACTION,
        tenant_id=tenant_id,
        additional_data={
            "endpoint": endpoint,
            "document_id": document_id
        }
    )


def audit_certificate_operation(
    operation: str,
    tenant_id: str
):
    """Context manager for auditing certificate operations"""
    return log_operation_context(
        operation_name=f"certificate_{operation}",
        category=LogCategory.CERTIFICATE,
        tenant_id=tenant_id
    )


# Utility functions for log analysis
def create_audit_search_query(
    start_time: datetime,
    end_time: datetime,
    tenant_id: Optional[str] = None,
    event_type: Optional[str] = None,
    category: Optional[str] = None,
    level: Optional[str] = None
) -> Dict[str, Any]:
    """Create search query for audit logs"""
    query = {
        "timestamp": {
            "gte": start_time.isoformat(),
            "lte": end_time.isoformat()
        }
    }
    
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    if event_type:
        query["event_type"] = event_type
    
    if category:
        query["category"] = category
    
    if level:
        query["level"] = level
    
    return query


def format_audit_report(
    logs: List[Dict[str, Any]],
    report_type: str = "summary"
) -> Dict[str, Any]:
    """Format audit logs into a report"""
    if report_type == "summary":
        return {
            "total_events": len(logs),
            "event_types": list(set(log.get("event_type") for log in logs if log.get("event_type"))),
            "categories": list(set(log.get("category") for log in logs if log.get("category"))),
            "tenants": list(set(log.get("tenant_id") for log in logs if log.get("tenant_id"))),
            "time_range": {
                "start": min(log.get("timestamp") for log in logs if log.get("timestamp")),
                "end": max(log.get("timestamp") for log in logs if log.get("timestamp"))
            } if logs else None
        }
    
    return {"logs": logs, "count": len(logs)}