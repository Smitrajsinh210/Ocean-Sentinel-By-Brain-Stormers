"""
Ocean Sentinel - Environmental Data API Routes
FastAPI endpoints for environmental data management
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.environmental_data import (
    EnvironmentalDataModel, EnvironmentalDataCreate, EnvironmentalDataSummary,
    EnvironmentalDataFilter, EnvironmentalDataResponse, DataCollectionStatus,
    HistoricalTrend
)
from app.services.data_ingestion import EnvironmentalDataService
from app.utils.database import create_supabase_client
from app.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = create_supabase_client()
data_service = EnvironmentalDataService()

@router.get("/latest", response_model=EnvironmentalDataResponse)
async def get_latest_data(
    sources: Optional[str] = Query(None, description="Comma-separated list of sources"),
    hours_back: int = Query(6, ge=1, le=72, description="Hours to look back"),
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="Center latitude"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="Center longitude"),
    radius_km: Optional[float] = Query(None, gt=0, description="Search radius in km")
):
    """Get latest environmental data with optional location filtering"""
    try:
        logger.info(f"Fetching latest environmental data (last {hours_back}h)")
        
        # Time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Build query
        query = supabase.table('environmental_data_summary')\
            .select('*, environmental_data_details(*)')\
            .gte('timestamp', time_threshold.isoformat())\
            .order('timestamp', desc=True)
        
        # Execute query
        result = await query.execute()
        
        if result.data:
            latest_summary = result.data[0]
            
            # Filter by sources if specified
            if sources:
                source_list = [s.strip() for s in sources.split(',')]
                details = latest_summary.get('environmental_data_details', [])
                filtered_details = [d for d in details if d.get('source') in source_list]
                latest_summary['environmental_data_details'] = filtered_details
            
            # Filter by location if specified
            if latitude is not None and longitude is not None and radius_km:
                location_data = await data_service.get_data_by_location(
                    latitude, longitude, radius_km
                )
                latest_summary['location_filtered_data'] = location_data
            
            logger.info(f"✅ Retrieved latest environmental data: {latest_summary['id']}")
            
            return EnvironmentalDataResponse(
                success=True,
                message="Latest environmental data retrieved",
                data=latest_summary,
                collection_info=DataCollectionStatus(
                    collection_id=latest_summary['id'],
                    status='completed',
                    started_at=datetime.fromisoformat(latest_summary['timestamp'].replace('Z', '+00:00')),
                    completed_at=datetime.fromisoformat(latest_summary['created_at'].replace('Z', '+00:00')),
                    total_sources=4,  # openweather, openaq, noaa, nasa
                    successful_sources=latest_summary['successful_sources'],
                    failed_sources=latest_summary['failed_sources']
                )
            )
        
        return EnvironmentalDataResponse(
            success=False,
            message="No recent environmental data found"
        )
        
    except Exception as e:
        logger.error(f"Error fetching latest data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch environmental data")

@router.get("/history", response_model=List[EnvironmentalDataSummary])
async def get_data_history(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    sources: Optional[str] = Query(None, description="Comma-separated list of sources"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get historical environmental data"""
    try:
        logger.info("Fetching environmental data history")
        
        # Build query
        query = supabase.table('environmental_data_summary').select('*')
        
        # Apply date filters
        if start_date:
            query = query.gte('timestamp', start_date)
        if end_date:
            query = query.lte('timestamp', end_date)
        
        # Default to last 7 days if no dates specified
        if not start_date and not end_date:
            default_start = datetime.utcnow() - timedelta(days=7)
            query = query.gte('timestamp', default_start.isoformat())
        
        # Order and pagination
        query = query.order('timestamp', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = await query.execute()
        
        if result.data:
            logger.info(f"✅ Retrieved {len(result.data)} historical records")
            return [EnvironmentalDataSummary(**record) for record in result.data]
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching data history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch data history")

@router.post("/collect", response_model=EnvironmentalDataResponse)
async def trigger_data_collection(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """Manually trigger environmental data collection"""
    try:
        if not current_user or current_user.get('role') not in ['admin', 'emergency_manager', 'analyst']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        logger.info("Manual data collection triggered")
        
        # Start background collection
        background_tasks.add_task(run_manual_collection)
        
        return EnvironmentalDataResponse(
            success=True,
            message="Data collection initiated",
            collection_info=DataCollectionStatus(
                collection_id=f"manual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                status='running',
                started_at=datetime.utcnow(),
                total_sources=4,
                successful_sources=0,
                failed_sources=0
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering data collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger data collection")

@router.get("/sources/{source_name}", response_model=List[EnvironmentalDataModel])
async def get_data_by_source(
    source_name: str,
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results")
):
    """Get environmental data from specific source"""
    try:
        allowed_sources = ['openweather', 'openaq', 'noaa', 'nasa']
        if source_name not in allowed_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid source. Must be one of: {', '.join(allowed_sources)}"
            )
        
        logger.info(f"Fetching data from source: {source_name}")
        
        # Time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Query specific source data
        result = await supabase.table('environmental_data_details')\
            .select('*')\
            .eq('source', source_name)\
            .gte('timestamp', time_threshold.isoformat())\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        
        if result.data:
            logger.info(f"✅ Retrieved {len(result.data)} records from {source_name}")
            return [EnvironmentalDataModel(**record) for record in result.data]
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching data from {source_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from {source_name}")

@router.get("/location/{latitude}/{longitude}", response_model=List[EnvironmentalDataModel])
async def get_data_by_location(
    latitude: float,
    longitude: float,
    radius_km: float = Query(10, gt=0, le=1000, description="Search radius in km"),
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """Get environmental data near specific location"""
    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise HTTPException(status_code=400, detail="Invalid latitude")
        if not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="Invalid longitude")
        
        logger.info(f"Fetching data near location: {latitude}, {longitude} (radius: {radius_km}km)")
        
        # Get location data using the service
        location_data = await data_service.get_data_by_location(latitude, longitude, radius_km)
        
        if location_data:
            logger.info(f"✅ Retrieved {len(location_data)} records near location")
            return [EnvironmentalDataModel(**record) for record in location_data]
        
        return []
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching location data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch location data")

@router.get("/trends/{parameter}", response_model=HistoricalTrend)
async def get_parameter_trend(
    parameter: str,
    days_back: int = Query(30, ge=7, le=365, description="Days to analyze"),
    location_lat: Optional[float] = Query(None, description="Optional location filter latitude"),
    location_lon: Optional[float] = Query(None, description="Optional location filter longitude"),
    radius_km: Optional[float] = Query(50, description="Location filter radius")
):
    """Get historical trend analysis for environmental parameter"""
    try:
        logger.info(f"Analyzing trend for parameter: {parameter} ({days_back} days)")
        
        # Validate parameter
        valid_parameters = [
            'temperature', 'humidity', 'pressure', 'wind_speed', 'precipitation',
            'pm2_5', 'pm10', 'aqi', 'no2', 'so2', 'co', 'o3',
            'water_level', 'wave_height', 'water_temperature'
        ]
        
        if parameter not in valid_parameters:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parameter. Must be one of: {', '.join(valid_parameters)}"
            )
        
        # Time range
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get data for trend analysis
        query = supabase.table('environmental_data_details')\
            .select('*')\
            .gte('timestamp', start_date.isoformat())\
            .order('timestamp', asc=True)
        
        result = await query.execute()
        data_points = result.data or []
        
        # Filter by location if specified
        if location_lat is not None and location_lon is not None:
            # Simple distance filter (in production, use PostGIS)
            filtered_points = []
            for point in data_points:
                if abs(point.get('latitude', 0) - location_lat) <= 0.5 and \
                   abs(point.get('longitude', 0) - location_lon) <= 0.5:
                    filtered_points.append(point)
            data_points = filtered_points
        
        # Extract parameter values
        values = []
        timestamps = []
        
        for point in data_points:
            data = point.get('data', {})
            if parameter in data and data[parameter] is not None:
                try:
                    values.append(float(data[parameter]))
                    timestamps.append(datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')))
                except (ValueError, TypeError):
                    continue
        
        if len(values) < 2:
            return HistoricalTrend(
                parameter=parameter,
                time_period=f"{days_back} days",
                trend_direction="unknown",
                rate_of_change=0.0,
                confidence=0.0,
                anomalies_detected=[]
            )
        
        # Calculate trend
        from scipy import stats
        import numpy as np
        
        # Convert timestamps to numeric values for regression
        time_numeric = [(t - timestamps[0]).total_seconds() / 86400 for t in timestamps]  # Days
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(time_numeric, values)
        
        # Determine trend direction
        if abs(slope) < std_err:
            trend_direction = "stable"
        elif slope > 0:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"
        
        # Detect anomalies (simple outlier detection)
        mean_value = np.mean(values)
        std_value = np.std(values)
        threshold = 2 * std_value
        
        anomalies = []
        for i, (value, timestamp) in enumerate(zip(values, timestamps)):
            if abs(value - mean_value) > threshold:
                anomalies.append(timestamp)
        
        # Calculate confidence (R-squared)
        confidence = r_value ** 2
        
        trend = HistoricalTrend(
            parameter=parameter,
            time_period=f"{days_back} days",
            trend_direction=trend_direction,
            rate_of_change=slope,
            confidence=confidence,
            seasonal_pattern={},  # Would require more complex analysis
            anomalies_detected=anomalies[:10]  # Limit to 10 most recent
        )
        
        logger.info(f"✅ Trend analysis completed: {trend_direction} trend with {confidence:.2f} confidence")
        return trend
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing trend for {parameter}: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze parameter trend")

@router.get("/quality-report", response_model=Dict[str, Any])
async def get_data_quality_report(
    hours_back: int = Query(24, ge=1, le=168, description="Hours to analyze")
):
    """Get data quality report for recent collections"""
    try:
        logger.info(f"Generating data quality report for last {hours_back} hours")
        
        # Time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Get recent data summaries
        result = await supabase.table('environmental_data_summary')\
            .select('*')\
            .gte('timestamp', time_threshold.isoformat())\
            .execute()
        
        summaries = result.data or []
        
        if not summaries:
            return {
                "time_period": f"Last {hours_back} hours",
                "total_collections": 0,
                "message": "No data collections found in specified time period"
            }
        
        # Calculate quality metrics
        total_collections = len(summaries)
        avg_completeness = sum(s.get('data_completeness', 0) for s in summaries) / total_collections
        avg_successful_sources = sum(s.get('successful_sources', 0) for s in summaries) / total_collections
        total_failed_sources = sum(s.get('failed_sources', 0) for s in summaries)
        
        # Quality score calculation
        quality_score = (avg_completeness / 100 + avg_successful_sources / 4) / 2
        
        # Source reliability
        source_stats = {
            'openweather': {'success': 0, 'total': 0},
            'openaq': {'success': 0, 'total': 0},
            'noaa': {'success': 0, 'total': 0},
            'nasa': {'success': 0, 'total': 0}
        }
        
        # Get detailed data to analyze source reliability
        detail_result = await supabase.table('environmental_data_details')\
            .select('source')\
            .gte('timestamp', time_threshold.isoformat())\
            .execute()
        
        for detail in detail_result.data or []:
            source = detail.get('source')
            if source in source_stats:
                source_stats[source]['success'] += 1
        
        # Calculate total expected vs actual
        expected_per_source = total_collections * 8  # 8 locations per source
        for source in source_stats:
            source_stats[source]['total'] = expected_per_source
            source_stats[source]['reliability'] = (
                source_stats[source]['success'] / expected_per_source * 100
                if expected_per_source > 0 else 0
            )
        
        report = {
            "time_period": f"Last {hours_back} hours",
            "report_generated": datetime.utcnow().isoformat(),
            "overall_metrics": {
                "total_collections": total_collections,
                "average_completeness": round(avg_completeness, 2),
                "average_successful_sources": round(avg_successful_sources, 2),
                "total_failed_sources": total_failed_sources,
                "overall_quality_score": round(quality_score, 3)
            },
            "source_reliability": source_stats,
            "quality_rating": (
                "Excellent" if quality_score >= 0.9 else
                "Good" if quality_score >= 0.75 else
                "Fair" if quality_score >= 0.6 else
                "Poor"
            ),
            "recommendations": []
        }
        
        # Add recommendations based on quality
        if quality_score < 0.75:
            report["recommendations"].append("Consider increasing data collection frequency")
        if total_failed_sources > total_collections * 0.25:
            report["recommendations"].append("Investigate frequent source failures")
        if avg_completeness < 80:
            report["recommendations"].append("Review data validation and processing pipeline")
        
        logger.info(f"✅ Quality report generated: {quality_score:.3f} overall score")
        return report
        
    except Exception as e:
        logger.error(f"Error generating quality report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate quality report")

async def run_manual_collection():
    """Background task for manual data collection"""
    try:
        logger.info("🔄 Running manual data collection...")
        
        # Trigger data collection
        result = await data_service.ingest_all_data()
        
        if result:
            logger.info("✅ Manual data collection completed successfully")
        else:
            logger.warning("⚠️ Manual data collection completed with issues")
            
    except Exception as e:
        logger.error(f"❌ Manual data collection failed: {e}")
