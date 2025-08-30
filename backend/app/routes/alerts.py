"""
Ocean Sentinel - Alerts API Routes
FastAPI endpoints for alert management
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.alerts import (
    AlertModel, AlertCreate, AlertUpdate, AlertSummary,
    AlertFilter, AlertResponse, AlertStatistics, AlertTemplate,
    BulkAlert, AlertDeliveryReport
)
from app.services.notifications import NotificationService
from app.utils.database import create_supabase_client
from app.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = create_supabase_client()

@router.get("/", response_model=List[AlertSummary])
async def get_alerts(
    threat_id: Optional[UUID] = Query(None, description="Filter by threat ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity_min: Optional[int] = Query(None, ge=1, le=5, description="Minimum severity"),
    hours_back: Optional[int] = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get list of alerts with optional filtering"""
    try:
        logger.info(f"Fetching alerts with filters: threat_id={threat_id}, status={status}")
        
        # Build query
        query = supabase.table('alert_notifications').select('*')
        
        # Apply filters
        if threat_id:
            query = query.eq('threat_id', str(threat_id))
        if status:
            query = query.eq('status', status)
        if severity_min:
            query = query.gte('severity', severity_min)
        
        # Time filter
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        query = query.gte('created_at', time_threshold.isoformat())
        
        # Order and pagination
        query = query.order('created_at', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = await query.execute()
        
        if result.data:
            logger.info(f"✅ Retrieved {len(result.data)} alerts")
            return [AlertSummary(**alert) for alert in result.data]
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")

@router.get("/{alert_id}", response_model=AlertModel)
async def get_alert(alert_id: UUID):
    """Get specific alert by ID"""
    try:
        result = await supabase.table('alert_notifications')\
            .select('*')\
            .eq('id', str(alert_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return AlertModel(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert")

@router.post("/", response_model=AlertResponse)
async def create_alert(
    alert: AlertCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Create and send new alert"""
    try:
        logger.info(f"Creating alert for threat: {alert.threat_id}")
        
        # Verify threat exists
        threat_result = await supabase.table('threats')\
            .select('*')\
            .eq('id', str(alert.threat_id))\
            .execute()
        
        if not threat_result.data:
            raise HTTPException(status_code=404, detail="Associated threat not found")
        
        threat_data = threat_result.data[0]
        
        # Prepare alert data
        alert_data = alert.dict()
        alert_data['id'] = str(UUID.uuid4())
        alert_data['alert_id'] = f"ALERT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        alert_data['status'] = 'pending'
        alert_data['created_at'] = datetime.utcnow().isoformat()
        alert_data['created_by'] = current_user.get('id') if current_user else None
        
        # Insert alert record
        result = await supabase.table('alert_notifications').insert(alert_data).execute()
        
        if result.data:
            created_alert = result.data[0]
            
            # Send alert via NotificationService
            background_tasks.add_task(send_alert_notifications, threat_data, created_alert)
            
            logger.info(f"✅ Alert created: {created_alert['alert_id']}")
            
            return AlertResponse(
                success=True,
                message="Alert created and being sent",
                alert_id=created_alert['alert_id'],
                delivery_estimate=60  # Estimate 60 seconds
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to create alert")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert")

@router.post("/bulk", response_model=AlertResponse)
async def send_bulk_alert(
    bulk_alert: BulkAlert,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Send bulk alert for multiple threats"""
    try:
        if not current_user or current_user.get('role') not in ['admin', 'emergency_manager']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        logger.info(f"Creating bulk alert for {len(bulk_alert.threat_ids)} threats")
        
        # Verify all threats exist
        threat_results = []
        for threat_id in bulk_alert.threat_ids:
            result = await supabase.table('threats')\
                .select('*')\
                .eq('id', str(threat_id))\
                .execute()
            
            if result.data:
                threat_results.append(result.data[0])
        
        if not threat_results:
            raise HTTPException(status_code=404, detail="No valid threats found")
        
        # Create bulk alert record
        alert_data = {
            'id': str(UUID.uuid4()),
            'alert_id': f"BULK_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'message': bulk_alert.message,
            'channels': bulk_alert.channels,
            'status': 'pending',
            'bulk_alert': True,
            'threat_count': len(threat_results),
            'priority': bulk_alert.priority,
            'created_at': datetime.utcnow().isoformat(),
            'created_by': current_user.get('id')
        }
        
        result = await supabase.table('alert_notifications').insert(alert_data).execute()
        
        if result.data:
            created_alert = result.data[0]
            
            # Send bulk notifications
            background_tasks.add_task(send_bulk_notifications, threat_results, bulk_alert, created_alert)
            
            return AlertResponse(
                success=True,
                message=f"Bulk alert created for {len(threat_results)} threats",
                alert_id=created_alert['alert_id'],
                delivery_estimate=120  # Estimate 2 minutes for bulk
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bulk alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create bulk alert")

@router.get("/statistics", response_model=AlertStatistics)
async def get_alert_statistics(
    days_back: int = Query(30, ge=1, le=365, description="Days to analyze")
):
    """Get alert delivery statistics"""
    try:
        logger.info(f"Generating alert statistics for last {days_back} days")
        
        # Time range
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get all alerts in time range
        result = await supabase.table('alert_notifications')\
            .select('*')\
            .gte('created_at', start_date.isoformat())\
            .execute()
        
        alerts = result.data or []
        
        # Calculate statistics
        total_alerts = len(alerts)
        pending_alerts = len([a for a in alerts if a.get('status') == 'pending'])
        sent_alerts = len([a for a in alerts if a.get('status') == 'sent'])
        failed_alerts = len([a for a in alerts if a.get('status') == 'failed'])
        
        # Calculate average delivery time
        delivery_times = []
        for alert in alerts:
            if alert.get('sent_at') and alert.get('created_at'):
                try:
                    created = datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00'))
                    sent = datetime.fromisoformat(alert['sent_at'].replace('Z', '+00:00'))
                    delivery_time = (sent - created).total_seconds()
                    delivery_times.append(delivery_time)
                except:
                    pass
        
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        # Group by channel and severity
        alerts_by_channel = {}
        alerts_by_severity = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for alert in alerts:
            channels = alert.get('channels', [])
            if isinstance(channels, list):
                for channel in channels:
                    alerts_by_channel[channel] = alerts_by_channel.get(channel, 0) + 1
            
            severity = alert.get('severity', 1)
            alerts_by_severity[severity] += 1
        
        # Calculate success rate
        success_rate = (sent_alerts / total_alerts * 100) if total_alerts > 0 else 0
        
        # Count unique recipients reached
        recipients_reached = sum(alert.get('recipients_count', 0) for alert in alerts)
        
        statistics = AlertStatistics(
            total_alerts=total_alerts,
            pending_alerts=pending_alerts,
            sent_alerts=sent_alerts,
            failed_alerts=failed_alerts,
            average_delivery_time=round(avg_delivery_time, 2),
            alerts_by_channel=alerts_by_channel,
            alerts_by_severity=alerts_by_severity,
            success_rate=round(success_rate, 2),
            recipients_reached=recipients_reached
        )
        
        logger.info(f"✅ Generated alert statistics: {total_alerts} alerts analyzed")
        return statistics
        
    except Exception as e:
        logger.error(f"Error generating alert statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate statistics")

@router.get("/{alert_id}/delivery-report", response_model=AlertDeliveryReport)
async def get_delivery_report(alert_id: UUID):
    """Get detailed delivery report for an alert"""
    try:
        # Get alert details
        result = await supabase.table('alert_notifications')\
            .select('*')\
            .eq('id', str(alert_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert = result.data[0]
        
        # Calculate delivery metrics
        total_recipients = alert.get('total_recipients', 0)
        successful_deliveries = alert.get('recipients_count', 0)
        failed_deliveries = total_recipients - successful_deliveries
        delivery_rate = (successful_deliveries / total_recipients * 100) if total_recipients > 0 else 0
        
        # Calculate delivery time
        delivery_time = 0
        if alert.get('sent_at') and alert.get('created_at'):
            try:
                created = datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00'))
                sent = datetime.fromisoformat(alert['sent_at'].replace('Z', '+00:00'))
                delivery_time = (sent - created).total_seconds()
            except:
                pass
        
        # Mock channel breakdown (in production, this would be stored)
        channels = alert.get('channels', [])
        channel_breakdown = {}
        for channel in channels:
            channel_breakdown[channel] = {
                'successful': successful_deliveries // len(channels),
                'failed': failed_deliveries // len(channels)
            }
        
        report = AlertDeliveryReport(
            alert_id=alert.get('alert_id', ''),
            threat_id=alert.get('threat_id'),
            total_recipients=total_recipients,
            successful_deliveries=successful_deliveries,
            failed_deliveries=failed_deliveries,
            delivery_rate=round(delivery_rate, 2),
            channel_breakdown=channel_breakdown,
            delivery_time=delivery_time,
            errors=[],  # Would be populated from logs
            created_at=datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00')),
            completed_at=datetime.fromisoformat(alert['sent_at'].replace('Z', '+00:00')) if alert.get('sent_at') else None
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating delivery report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate delivery report")

async def send_alert_notifications(threat_data: dict, alert_data: dict):
    """Background task to send alert notifications"""
    try:
        notification_service = NotificationService()
        
        # Update alert status to sending
        await supabase.table('alert_notifications')\
            .update({'status': 'sending', 'sent_at': datetime.utcnow().isoformat()})\
            .eq('id', alert_data['id'])\
            .execute()
        
        # Send notifications
        result = await notification_service.send_critical_alert(threat_data)
        
        # Update alert with results
        await supabase.table('alert_notifications')\
            .update({
                'status': 'sent' if result.get('recipients_notified', 0) > 0 else 'failed',
                'recipients_count': result.get('recipients_notified', 0),
                'delivered_at': datetime.utcnow().isoformat(),
                'metadata': result
            })\
            .eq('id', alert_data['id'])\
            .execute()
        
        logger.info(f"Alert notifications sent: {alert_data['alert_id']}")
        
    except Exception as e:
        logger.error(f"Failed to send alert notifications: {e}")
        
        # Mark as failed
        await supabase.table('alert_notifications')\
            .update({'status': 'failed'})\
            .eq('id', alert_data['id'])\
            .execute()

async def send_bulk_notifications(threats: List[dict], bulk_alert: BulkAlert, alert_data: dict):
    """Background task to send bulk notifications"""
    try:
        notification_service = NotificationService()
        
        total_recipients = 0
        
        # Send notification for each threat
        for threat in threats:
            result = await notification_service.send_critical_alert(threat)
            total_recipients += result.get('recipients_notified', 0)
        
        # Update bulk alert record
        await supabase.table('alert_notifications')\
            .update({
                'status': 'sent',
                'recipients_count': total_recipients,
                'sent_at': datetime.utcnow().isoformat(),
                'delivered_at': datetime.utcnow().isoformat()
            })\
            .eq('id', alert_data['id'])\
            .execute()
        
        logger.info(f"Bulk notifications sent: {alert_data['alert_id']}")
        
    except Exception as e:
        logger.error(f"Failed to send bulk notifications: {e}")
        
        await supabase.table('alert_notifications')\
            .update({'status': 'failed'})\
            .eq('id', alert_data['id'])\
            .execute()
