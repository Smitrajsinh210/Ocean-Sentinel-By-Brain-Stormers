"""
Ocean Sentinel - Alert Models
Pydantic models for alert notifications and management
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator

class AlertBase(BaseModel):
    """Base alert model"""
    threat_id: UUID = Field(..., description="Associated threat ID")
    message: str = Field(..., min_length=10, max_length=1000, description="Alert message")
    severity: int = Field(..., ge=1, le=5, description="Alert severity level")
    channels: List[str] = Field(..., min_items=1, description="Notification channels")
    recipients: List[str] = Field(..., min_items=1, description="Recipient identifiers")
    target_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Target area latitude")
    target_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Target area longitude")
    
    @validator('channels')
    def validate_channels(cls, v):
        allowed_channels = ['sms', 'email', 'push', 'webhook']
        for channel in v:
            if channel not in allowed_channels:
                raise ValueError(f'Invalid channel: {channel}. Must be one of: {", ".join(allowed_channels)}')
        return v

class AlertCreate(AlertBase):
    """Model for creating new alerts"""
    recipients_count: Optional[int] = Field(None, ge=0, description="Number of recipients")
    total_recipients: Optional[int] = Field(None, ge=0, description="Total possible recipients")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional alert metadata")

class AlertUpdate(BaseModel):
    """Model for updating alerts"""
    status: Optional[str] = Field(None, description="Alert status")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['pending', 'sent', 'failed', 'partial', 'cancelled']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

class AlertModel(AlertBase):
    """Complete alert model with database fields"""
    id: UUID = Field(..., description="Unique alert identifier")
    alert_id: str = Field(..., description="Human-readable alert ID")
    recipients_count: int = Field(default=0, description="Number of recipients reached")
    total_recipients: int = Field(default=0, description="Total target recipients")
    status: str = Field(default="pending", description="Alert status")
    sent_at: Optional[datetime] = Field(None, description="Send timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivery confirmation timestamp")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain verification hash")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class AlertSummary(BaseModel):
    """Simplified alert summary"""
    id: UUID
    alert_id: str
    threat_id: UUID
    severity: int
    channels: List[str]
    recipients_count: int
    status: str
    created_at: datetime
    sent_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class AlertStatistics(BaseModel):
    """Alert system statistics"""
    total_alerts: int = Field(..., description="Total alerts sent")
    pending_alerts: int = Field(..., description="Pending alerts")
    sent_alerts: int = Field(..., description="Successfully sent alerts")
    failed_alerts: int = Field(..., description="Failed alerts")
    average_delivery_time: float = Field(..., description="Average delivery time in seconds")
    alerts_by_channel: Dict[str, int] = Field(..., description="Alerts by notification channel")
    alerts_by_severity: Dict[int, int] = Field(..., description="Alerts by severity level")
    success_rate: float = Field(..., description="Overall success rate percentage")
    recipients_reached: int = Field(..., description="Total unique recipients reached")

class AlertTemplate(BaseModel):
    """Alert message template"""
    name: str = Field(..., description="Template name")
    threat_type: str = Field(..., description="Associated threat type")
    severity_level: int = Field(..., ge=1, le=5, description="Target severity level")
    subject_template: str = Field(..., description="Subject line template")
    message_template: str = Field(..., description="Message body template")
    channels: List[str] = Field(..., description="Applicable channels")
    variables: List[str] = Field(..., description="Available template variables")
    
    @validator('message_template')
    def validate_template_variables(cls, v, values):
        # Check for required template variables
        required_vars = ['{threat_type}', '{severity}', '{location}', '{description}']
        for var in required_vars:
            if var not in v:
                raise ValueError(f'Template must include variable: {var}')
        return v

class BulkAlert(BaseModel):
    """Model for sending bulk alerts"""
    threat_ids: List[UUID] = Field(..., min_items=1, description="Multiple threat IDs")
    message: str = Field(..., min_length=10, description="Bulk alert message")
    channels: List[str] = Field(..., min_items=1, description="Notification channels")
    recipient_filters: Dict[str, Any] = Field(..., description="Recipient selection criteria")
    priority: str = Field(default="normal", description="Alert priority level")
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ['low', 'normal', 'high', 'critical']
        if v not in allowed_priorities:
            raise ValueError(f'Priority must be one of: {", ".join(allowed_priorities)}')
        return v

class AlertResponse(BaseModel):
    """Response model for alert API endpoints"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    alert_id: Optional[str] = Field(None, description="Created alert ID")
    data: Optional[Any] = Field(None, description="Response data")
    delivery_estimate: Optional[int] = Field(None, description="Estimated delivery time in seconds")

class AlertFilter(BaseModel):
    """Filtering options for alert queries"""
    threat_id: Optional[UUID] = Field(None, description="Filter by threat ID")
    severity_min: Optional[int] = Field(None, ge=1, le=5, description="Minimum severity")
    severity_max: Optional[int] = Field(None, ge=1, le=5, description="Maximum severity")
    status: Optional[List[str]] = Field(None, description="Filter by status")
    channels: Optional[List[str]] = Field(None, description="Filter by channels")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")

class AlertDeliveryReport(BaseModel):
    """Detailed alert delivery report"""
    alert_id: str = Field(..., description="Alert identifier")
    threat_id: UUID = Field(..., description="Associated threat")
    total_recipients: int = Field(..., description="Total target recipients")
    successful_deliveries: int = Field(..., description="Successful deliveries")
    failed_deliveries: int = Field(..., description="Failed deliveries")
    delivery_rate: float = Field(..., description="Success rate percentage")
    channel_breakdown: Dict[str, Dict[str, int]] = Field(..., description="Per-channel delivery stats")
    delivery_time: float = Field(..., description="Total delivery time in seconds")
    errors: List[str] = Field(default_factory=list, description="Delivery errors")
    created_at: datetime = Field(..., description="Alert creation time")
    completed_at: Optional[datetime] = Field(None, description="Delivery completion time")
