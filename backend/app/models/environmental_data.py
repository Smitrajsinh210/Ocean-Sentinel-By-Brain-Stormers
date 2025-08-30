"""
Ocean Sentinel - Environmental Data Models
Pydantic models for environmental monitoring data
"""

from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

class EnvironmentalDataBase(BaseModel):
    """Base environmental data model"""
    source: str = Field(..., description="Data source identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Measurement latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Measurement longitude")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    data: Dict[str, Any] = Field(..., description="Measurement data")
    
    @validator('source')
    def validate_source(cls, v):
        allowed_sources = ['openweather', 'openaq', 'noaa', 'nasa', 'manual', 'sensor']
        if v not in allowed_sources:
            raise ValueError(f'Source must be one of: {", ".join(allowed_sources)}')
        return v

class EnvironmentalDataCreate(EnvironmentalDataBase):
    """Model for creating environmental data records"""
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Data quality score")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class EnvironmentalDataModel(EnvironmentalDataBase):
    """Complete environmental data model"""
    id: UUID = Field(..., description="Unique record identifier")
    summary_id: UUID = Field(..., description="Associated summary record ID")
    quality_score: float = Field(default=1.0, description="Data quality score")
    verified: bool = Field(default=False, description="Verification status")
    hash: Optional[str] = Field(None, description="Data integrity hash")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class EnvironmentalDataSummary(BaseModel):
    """Summary of environmental data collection"""
    id: UUID = Field(..., description="Summary record ID")
    data_hash: str = Field(..., description="Unique hash of collected data")
    timestamp: datetime = Field(..., description="Collection timestamp")
    total_locations: int = Field(..., description="Number of measurement locations")
    successful_sources: int = Field(..., description="Successfully collected sources")
    failed_sources: int = Field(default=0, description="Failed data collection attempts")
    data_completeness: float = Field(..., ge=0.0, le=100.0, description="Data completeness percentage")
    aggregated_metrics: Dict[str, Any] = Field(..., description="Aggregated environmental metrics")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain verification hash")
    detail_records_count: Optional[int] = Field(None, description="Number of detail records")
    data_sources: Optional[List[str]] = Field(None, description="List of data sources used")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True

class WeatherData(BaseModel):
    """Weather-specific data structure"""
    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    pressure: float = Field(..., description="Atmospheric pressure in hPa")
    wind_speed: float = Field(..., ge=0, description="Wind speed in m/s")
    wind_direction: float = Field(..., ge=0, le=360, description="Wind direction in degrees")
    precipitation: float = Field(..., ge=0, description="Precipitation in mm")
    visibility: Optional[float] = Field(None, ge=0, description="Visibility in meters")
    cloud_cover: Optional[float] = Field(None, ge=0, le=100, description="Cloud cover percentage")
    uv_index: Optional[float] = Field(None, ge=0, description="UV index")
    conditions: Optional[str] = Field(None, description="Weather conditions description")

class AirQualityData(BaseModel):
    """Air quality specific data structure"""
    aqi: Optional[int] = Field(None, ge=0, description="Air Quality Index")
    pm2_5: Optional[float] = Field(None, ge=0, description="PM2.5 concentration µg/m³")
    pm10: Optional[float] = Field(None, ge=0, description="PM10 concentration µg/m³")
    no2: Optional[float] = Field(None, ge=0, description="NO2 concentration µg/m³")
    so2: Optional[float] = Field(None, ge=0, description="SO2 concentration µg/m³")
    co: Optional[float] = Field(None, ge=0, description="CO concentration µg/m³")
    o3: Optional[float] = Field(None, ge=0, description="O3 concentration µg/m³")
    category: Optional[str] = Field(None, description="Air quality category")
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            allowed_categories = ['Good', 'Moderate', 'Unhealthy for Sensitive Groups', 
                                'Unhealthy', 'Very Unhealthy', 'Hazardous']
            if v not in allowed_categories:
                raise ValueError(f'Category must be one of: {", ".join(allowed_categories)}')
        return v

class OceanData(BaseModel):
    """Ocean/coastal specific data structure"""
    water_level: Optional[float] = Field(None, description="Water level in meters")
    wave_height: Optional[float] = Field(None, ge=0, description="Wave height in meters")
    wave_period: Optional[float] = Field(None, ge=0, description="Wave period in seconds")
    wave_direction: Optional[float] = Field(None, ge=0, le=360, description="Wave direction degrees")
    current_speed: Optional[float] = Field(None, ge=0, description="Current speed in m/s")
    current_direction: Optional[float] = Field(None, ge=0, le=360, description="Current direction degrees")
    water_temperature: Optional[float] = Field(None, description="Water temperature in Celsius")
    salinity: Optional[float] = Field(None, ge=0, description="Salinity in PSU")
    turbidity: Optional[float] = Field(None, ge=0, description="Turbidity in NTU")
    ph: Optional[float] = Field(None, ge=0, le=14, description="pH level")
    dissolved_oxygen: Optional[float] = Field(None, ge=0, description="Dissolved oxygen mg/L")
    tidal_stage: Optional[str] = Field(None, description="Tidal stage (rising/falling)")

class SatelliteData(BaseModel):
    """Satellite imagery/remote sensing data"""
    image_url: Optional[str] = Field(None, description="Satellite image URL")
    cloud_score: Optional[float] = Field(None, ge=0, le=1, description="Cloud coverage score")
    vegetation_index: Optional[float] = Field(None, description="NDVI or similar vegetation index")
    water_index: Optional[float] = Field(None, description="Water detection index")
    thermal_anomaly: Optional[bool] = Field(None, description="Thermal anomaly detected")
    surface_temperature: Optional[float] = Field(None, description="Surface temperature in Celsius")
    resolution: Optional[float] = Field(None, description="Image resolution in meters")
    acquisition_date: Optional[datetime] = Field(None, description="Image acquisition timestamp")

class EnvironmentalMetrics(BaseModel):
    """Aggregated environmental metrics"""
    avg_temperature: Optional[float] = Field(None, description="Average temperature")
    max_wind_speed: Optional[float] = Field(None, description="Maximum wind speed")
    total_precipitation: Optional[float] = Field(None, description="Total precipitation")
    avg_air_quality: Optional[float] = Field(None, description="Average air quality index")
    max_wave_height: Optional[float] = Field(None, description="Maximum wave height")
    water_quality_score: Optional[float] = Field(None, ge=0, le=1, description="Water quality score")
    environmental_stress_index: Optional[float] = Field(None, ge=0, le=1, description="Overall stress index")
    anomaly_count: int = Field(default=0, description="Number of detected anomalies")

class DataCollectionStatus(BaseModel):
    """Status of data collection process"""
    collection_id: str = Field(..., description="Collection process identifier")
    status: str = Field(..., description="Collection status")
    started_at: datetime = Field(..., description="Collection start time")
    completed_at: Optional[datetime] = Field(None, description="Collection completion time")
    total_sources: int = Field(..., description="Total data sources attempted")
    successful_sources: int = Field(..., description="Successfully collected sources")
    failed_sources: int = Field(..., description="Failed collection attempts")
    errors: List[str] = Field(default_factory=list, description="Collection errors")
    next_collection: Optional[datetime] = Field(None, description="Next scheduled collection")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

class EnvironmentalDataFilter(BaseModel):
    """Filtering options for environmental data queries"""
    sources: Optional[List[str]] = Field(None, description="Filter by data sources")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Center latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Center longitude")
    radius_km: Optional[float] = Field(None, gt=0, description="Search radius in km")
    quality_min: Optional[float] = Field(None, ge=0, le=1, description="Minimum quality score")
    verified_only: bool = Field(default=False, description="Return only verified data")
    include_metadata: bool = Field(default=False, description="Include metadata in response")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")

class EnvironmentalDataResponse(BaseModel):
    """Response model for environmental data endpoints"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    total: Optional[int] = Field(None, description="Total records available")
    collection_info: Optional[DataCollectionStatus] = Field(None, description="Collection status")
    
class HistoricalTrend(BaseModel):
    """Historical trend analysis"""
    parameter: str = Field(..., description="Environmental parameter name")
    time_period: str = Field(..., description="Time period analyzed")
    trend_direction: str = Field(..., description="Trend direction (increasing/decreasing/stable)")
    rate_of_change: float = Field(..., description="Rate of change per time unit")
    confidence: float = Field(..., ge=0, le=1, description="Trend confidence level")
    seasonal_pattern: Optional[Dict[str, float]] = Field(None, description="Seasonal patterns detected")
    anomalies_detected: List[datetime] = Field(default_factory=list, description="Anomaly timestamps")
    
    @validator('trend_direction')
    def validate_trend_direction(cls, v):
        allowed_directions = ['increasing', 'decreasing', 'stable', 'irregular', 'unknown']
        if v not in allowed_directions:
            raise ValueError(f'Trend direction must be one of: {", ".join(allowed_directions)}')
        return v
