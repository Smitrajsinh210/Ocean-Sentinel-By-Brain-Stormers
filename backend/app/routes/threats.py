"""
Ocean Sentinel - Threats API Routes
FastAPI endpoints for threat management
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.threats import (
    ThreatModel, ThreatCreate, ThreatUpdate, ThreatSummary,
    ThreatFilter, ThreatResponse, ThreatStatistics, ThreatGeoJSON,
    BulkThreatOperation
)
from app.utils.database import create_supabase_client
from app.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = create_supabase_client()

@router.get("/", response_model=List[ThreatSummary])
async def get_threats(
    type: Optional[str] = Query(None, description="Filter by threat type"),
    severity_min: Optional[int] = Query(None, ge=1, le=5, description="Minimum severity"),
    severity_max: Optional[int] = Query(None, ge=1, le=5, description="Maximum severity"),
    verified: Optional[bool] = Query(None, description="Filter by verification status"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    hours_back: Optional[int] = Query(24, ge=1, le=8760, description="Hours to look back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get list of threats with optional filtering"""
    try:
        logger.info(f"Fetching threats with filters: type={type}, severity={severity_min}-{severity_max}")
        
        # Build query
        query = supabase.table('threats').select('*')
        
        # Apply filters
        if type:
            query = query.eq('type', type)
        if severity_min:
            query = query.gte('severity', severity_min)
        if severity_max:
            query = query.lte('severity', severity_max)
        if verified is not None:
            query = query.eq('verified', verified)
        if resolved is not None:
            query = query.eq('resolved', resolved)
        
        # Time filter
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        query = query.gte('timestamp', time_threshold.isoformat())
        
        # Order and pagination
        query = query.order('timestamp', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = await query.execute()
        
        if result.data:
            logger.info(f"✅ Retrieved {len(result.data)} threats")
            return [ThreatSummary(**threat) for threat in result.data]
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching threats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch threats")

@router.get("/{threat_id}", response_model=ThreatModel)
async def get_threat(threat_id: UUID):
    """Get specific threat by ID"""
    try:
        result = await supabase.table('threats')\
            .select('*')\
            .eq('id', str(threat_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Threat not found")
        
        return ThreatModel(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching threat {threat_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch threat")

@router.post("/", response_model=ThreatResponse)
async def create_threat(
    threat: ThreatCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Create new threat (manual reporting)"""
    try:
        logger.info(f"Creating new threat: {threat.type}")
        
        # Prepare threat data
        threat_data = threat.dict()
        threat_data['id'] = str(UUID.uuid4())
        threat_data['timestamp'] = datetime.utcnow().isoformat()
        threat_data['location'] = f"POINT({threat.longitude} {threat.latitude})"
        threat_data['created_by'] = current_user.get('id') if current_user else None
        
        # Insert into database
        result = await supabase.table('threats').insert(threat_data).execute()
        
        if result.data:
            created_threat = result.data[0]
            
            # Background task: Send alerts if severity is high
            if threat.severity >= 4:
                background_tasks.add_task(send_threat_alerts, created_threat)
            
            logger.info(f"✅ Threat created: {created_threat['id']}")
            
            return ThreatResponse(
                success=True,
                message="Threat created successfully",
                data=created_threat
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to create threat")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating threat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create threat")

@router.put("/{threat_id}", response_model=ThreatResponse)
async def update_threat(
    threat_id: UUID,
    threat_update: ThreatUpdate,
    current_user = Depends(get_current_user)
):
    """Update existing threat"""
    try:
        logger.info(f"Updating threat: {threat_id}")
        
        # Check if threat exists
        existing = await supabase.table('threats')\
            .select('*')\
            .eq('id', str(threat_id))\
            .execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Threat not found")
        
        # Prepare update data
        update_data = {k: v for k, v in threat_update.dict().items() if v is not None}
        update_data['updated_at'] = datetime.utcnow().isoformat()
        update_data['updated_by'] = current_user.get('id') if current_user else None
        
        # Update in database
        result = await supabase.table('threats')\
            .update(update_data)\
            .eq('id', str(threat_id))\
            .execute()
        
        if result.data:
            logger.info(f"✅ Threat updated: {threat_id}")
            return ThreatResponse(
                success=True,
                message="Threat updated successfully",
                data=result.data[0]
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update threat")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating threat {threat_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update threat")

@router.delete("/{threat_id}", response_model=ThreatResponse)
async def delete_threat(
    threat_id: UUID,
    current_user = Depends(get_current_user)
):
    """Delete threat (admin only)"""
    try:
        # Check user permissions
        if not current_user or current_user.get('role') not in ['admin', 'emergency_manager']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        logger.info(f"Deleting threat: {threat_id}")
        
        # Soft delete (mark as deleted)
        result = await supabase.table('threats')\
            .update({
                'deleted': True,
                'deleted_at': datetime.utcnow().isoformat(),
                'deleted_by': current_user.get('id')
            })\
            .eq('id', str(threat_id))\
            .execute()
        
        if result.data:
            logger.info(f"✅ Threat deleted: {threat_id}")
            return ThreatResponse(
                success=True,
                message="Threat deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Threat not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting threat {threat_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete threat")

@router.get("/statistics", response_model=ThreatStatistics)
async def get_threat_statistics(
    days_back: int = Query(30, ge=1, le=365, description="Days to analyze")
):
    """Get threat statistics and trends"""
    try:
        logger.info(f"Generating threat statistics for last {days_back} days")
        
        # Time range
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get all threats in time range
        result = await supabase.table('threats')\
            .select('*')\
            .gte('timestamp', start_date.isoformat())\
            .execute()
        
        threats = result.data or []
        
        # Calculate statistics
        total_threats = len(threats)
        active_threats = len([t for t in threats if not t.get('resolved')])
        resolved_threats = len([t for t in threats if t.get('resolved')])
        critical_threats = len([t for t in threats if t.get('severity', 0) >= 4])
        verified_threats = len([t for t in threats if t.get('verified')])
        
        # Average severity
        severities = [t.get('severity', 1) for t in threats]
        avg_severity = sum(severities) / len(severities) if severities else 0
        
        # Group by type and severity
        threats_by_type = {}
        threats_by_severity = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for threat in threats:
            threat_type = threat.get('type', 'unknown')
            severity = threat.get('severity', 1)
            
            threats_by_type[threat_type] = threats_by_type.get(threat_type, 0) + 1
            threats_by_severity[severity] += 1
        
        # Determine trend
        mid_point = len(threats) // 2
        recent_threats = threats[:mid_point] if threats else []
        older_threats = threats[mid_point:] if threats else []
        
        if len(recent_threats) > len(older_threats) * 1.1:
            trend = "increasing"
        elif len(recent_threats) < len(older_threats) * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        statistics = ThreatStatistics(
            total_threats=total_threats,
            active_threats=active_threats,
            resolved_threats=resolved_threats,
            critical_threats=critical_threats,
            verified_threats=verified_threats,
            average_severity=round(avg_severity, 2),
            threats_by_type=threats_by_type,
            threats_by_severity=threats_by_severity,
            recent_trend=trend
        )
        
        logger.info(f"✅ Generated statistics: {total_threats} threats analyzed")
        return statistics
        
    except Exception as e:
        logger.error(f"Error generating threat statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate statistics")

@router.get("/geojson", response_model=ThreatGeoJSON)
async def get_threats_geojson(
    bbox: Optional[str] = Query(None, description="Bounding box: min_lon,min_lat,max_lon,max_lat"),
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back"),
    min_severity: int = Query(1, ge=1, le=5, description="Minimum severity")
):
    """Get threats as GeoJSON for mapping"""
    try:
        logger.info("Fetching threats as GeoJSON")
        
        # Build query
        query = supabase.table('threats').select('*')
        
        # Time filter
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        query = query.gte('timestamp', time_threshold.isoformat())
        
        # Severity filter
        query = query.gte('severity', min_severity)
        
        # Execute query
        result = await query.execute()
        threats = result.data or []
        
        # Convert to threat models
        threat_models = [ThreatModel(**threat) for threat in threats]
        
        # Convert to GeoJSON
        geojson = ThreatGeoJSON.from_threats(threat_models)
        
        logger.info(f"✅ Generated GeoJSON with {len(geojson.features)} features")
        return geojson
        
    except Exception as e:
        logger.error(f"Error generating GeoJSON: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate GeoJSON")

@router.post("/bulk-operation", response_model=ThreatResponse)
async def bulk_threat_operation(
    operation: BulkThreatOperation,
    current_user = Depends(get_current_user)
):
    """Perform bulk operations on multiple threats"""
    try:
        if not current_user or current_user.get('role') not in ['admin', 'emergency_manager']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        logger.info(f"Performing bulk {operation.action} on {len(operation.threat_ids)} threats")
        
        # Prepare update data based on action
        update_data = {'updated_at': datetime.utcnow().isoformat()}
        
        if operation.action == 'resolve':
            update_data.update({
                'resolved': True,
                'resolved_at': datetime.utcnow().isoformat(),
                'resolved_by': current_user.get('id')
            })
        elif operation.action == 'verify':
            update_data.update({
                'verified': True,
                'verified_at': datetime.utcnow().isoformat(),
                'verified_by': current_user.get('id')
            })
        elif operation.action == 'unverify':
            update_data.update({'verified': False})
        elif operation.action == 'unresolve':
            update_data.update({'resolved': False})
        
        # Apply to all threat IDs
        updated_count = 0
        for threat_id in operation.threat_ids:
            try:
                result = await supabase.table('threats')\
                    .update(update_data)\
                    .eq('id', str(threat_id))\
                    .execute()
                
                if result.data:
                    updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to update threat {threat_id}: {e}")
        
        logger.info(f"✅ Bulk operation completed: {updated_count}/{len(operation.threat_ids)} updated")
        
        return ThreatResponse(
            success=True,
            message=f"Bulk {operation.action} completed on {updated_count} threats",
            data={'updated_count': updated_count, 'total_requested': len(operation.threat_ids)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk operation: {e}")
        raise HTTPException(status_code=500, detail="Bulk operation failed")

async def send_threat_alerts(threat_data: dict):
    """Background task to send threat alerts"""
    try:
        from app.services.notifications import NotificationService
        
        notification_service = NotificationService()
        await notification_service.send_critical_alert(threat_data)
        
    except Exception as e:
        logger.error(f"Failed to send threat alerts: {e}")
