"""
Ocean Sentinel - Threat Models
Pydantic models for threat detection and management
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator
from geojson_pydantic import Point

class ThreatBase(BaseModel):
    """Base threat model"""
    type: str = Field(..., description="Type of threat (storm, pollution, erosion, etc.)")
    severity: int = Field(..., ge=1, le=5, description="Severity level 1-5")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    description: str = Field(..., min_length=10, description="Threat description")
    estimated_impact: Optional[str] = Field(None, description="Estimated impact assessment")
    affected_population: Optional[int] = Field(None, ge=0, description="Estimated affected population")
    affected_area_km2: Optional[float] = Field(None, ge=0, description="Affected area in km²")
    recommendation: Optional[str] = Field(None, description="Recommended actions")
    
    @validator('type')
    def validate_threat_type(cls, v):
        allowed_types = ['storm', 'pollution', 'erosion', 'algal_bloom', 'illegal_dumping', 'anomaly']
        if v not in allowed_types:
            raise ValueError(f'Threat type must be one of: {", ".join(allowed_types)}')
        return v

class ThreatCreate(ThreatBase):
    """Model for creating new threats"""
    data_sources: Optional[List[str]] = Field(default_factory=list, description="Data sources used")
    raw_features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw AI features")

class ThreatUpdate(BaseModel):
    """Model for updating existing threats"""
    severity: Optional[int] = Field(None, ge=1, le=5)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    description: Optional[str] = Field(None, min_length=10)
    estimated_impact: Optional[str] = None
    affected_population: Optional[int] = Field(None, ge=0)
    affected_area_km2: Optional[float] = Field(None, ge=0)
    recommendation: Optional[str] = None
    verified: Optional[bool] = None
    resolved: Optional[bool] = None

class ThreatModel(ThreatBase):
    """Complete threat model with database fields"""
    id: UUID = Field(..., description="Unique threat identifier")
    address: Optional[str] = Field(None, description="Human-readable address")
    timestamp: datetime = Field(..., description="Detection timestamp")
    verified: bool = Field(default=False, description="Human verification status")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")
    raw_features: Dict[str, Any] = Field(default_factory=dict, description="Raw AI features")
    resolved: bool = Field(default=False, description="Resolution status")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    resolved_by: Optional[UUID] = Field(None, description="User who resolved threat")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class ThreatSummary(BaseModel):
    """Simplified threat summary for lists"""
    id: UUID
    type: str
    severity: int
    confidence: float
    latitude: float
    longitude: float
    description: str
    timestamp: datetime
    verified: bool
    resolved: bool
    
    class Config:
        from_attributes = True

class ThreatStatistics(BaseModel):
    """Threat statistics model"""
    total_threats: int = Field(..., description="Total number of threats")
    active_threats: int = Field(..., description="Currently active threats")
    resolved_threats: int = Field(..., description="Resolved threats")
    critical_threats: int = Field(..., description="Critical severity threats (4-5)")
    verified_threats: int = Field(..., description="Human-verified threats")
    average_severity: float = Field(..., description="Average severity score")
    threats_by_type: Dict[str, int] = Field(..., description="Threats grouped by type")
    threats_by_severity: Dict[int, int] = Field(..., description="Threats grouped by severity")
    recent_trend: str = Field(..., description="Recent trend (increasing/decreasing/stable)")
    
class ThreatGeoJSON(BaseModel):
    """GeoJSON representation of threats for mapping"""
    type: str = Field(default="FeatureCollection")
    features: List[Dict[str, Any]] = Field(..., description="GeoJSON features")
    
    @classmethod
    def from_threats(cls, threats: List[ThreatModel]) -> 'ThreatGeoJSON':
        """Convert threat models to GeoJSON format"""
        features = []
        
        for threat in threats:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [threat.longitude, threat.latitude]
                },
                "properties": {
                    "id": str(threat.id),
                    "type": threat.type,
                    "severity": threat.severity,
                    "confidence": threat.confidence,
                    "description": threat.description,
                    "timestamp": threat.timestamp.isoformat(),
                    "verified": threat.verified,
                    "resolved": threat.resolved,
                    "estimated_impact": threat.estimated_impact,
                    "affected_population": threat.affected_population
                }
            }
            features.append(feature)
        
        return cls(features=features)

class ThreatFilter(BaseModel):
    """Filtering options for threat queries"""
    type: Optional[List[str]] = Field(None, description="Filter by threat types")
    severity_min: Optional[int] = Field(None, ge=1, le=5, description="Minimum severity")
    severity_max: Optional[int] = Field(None, ge=1, le=5, description="Maximum severity")
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence")
    verified: Optional[bool] = Field(None, description="Verification status filter")
    resolved: Optional[bool] = Field(None, description="Resolution status filter")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Center latitude for radius search")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Center longitude for radius search")
    radius_km: Optional[float] = Field(None, gt=0, description="Search radius in kilometers")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and values['start_date'] and v:
            if v <= values['start_date']:
                raise ValueError('end_date must be after start_date')
        return v
    
    @validator('severity_max')
    def validate_severity_range(cls, v, values):
        if 'severity_min' in values and values['severity_min'] and v:
            if v < values['severity_min']:
                raise ValueError('severity_max must be >= severity_min')
        return v

class ThreatResponse(BaseModel):
    """Response model for threat API endpoints"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    total: Optional[int] = Field(None, description="Total count for paginated results")
    page: Optional[int] = Field(None, description="Current page number")
    
class BulkThreatOperation(BaseModel):
    """Model for bulk threat operations"""
    threat_ids: List[UUID] = Field(..., min_items=1, description="List of threat IDs")
    action: str = Field(..., description="Action to perform (resolve, verify, delete)")
    reason: Optional[str] = Field(None, description="Reason for bulk action")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['resolve', 'verify', 'delete', 'unverify', 'unresolve']
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of: {", ".join(allowed_actions)}')
        return v
