# Ocean Sentinel API Documentation

## Overview

The Ocean Sentinel API is a comprehensive REST API built with FastAPI that provides real-time coastal threat detection, environmental data monitoring, and multi-channel alert distribution. The API integrates AI-powered threat detection with blockchain data integrity to enable immediate response and multi-agency collaboration.

**Base URL:** `https://your-project.vercel.app/api`
**Version:** v1.0.0
**Last Updated:** August 30, 2025

## Authentication

The API uses API key authentication for protected endpoints:

```http
Authorization: Bearer YOUR_API_KEY
```

### Getting an API Key
1. Register at the Ocean Sentinel dashboard
2. Navigate to API Settings
3. Generate a new API key
4. Include in all requests to protected endpoints

## Core Endpoints

### 🌊 Environmental Data Endpoints

#### Get Environmental Data
```http
GET /api/data/environmental
```

**Query Parameters:**
- `source` (optional): Data source filter (weather_api, sensor_network, noaa, nasa)
- `data_type` (optional): Type filter (temperature, humidity, air_quality, ocean_temp)
- `location` (optional): Geographic filter (lat,lng,radius_km)
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `limit` (optional): Max results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "source": "weather_api",
      "data_type": "temperature",
      "value": 25.5,
      "unit": "celsius",
      "location": {
        "lat": 40.7128,
        "lng": -74.0060
      },
      "timestamp": "2025-08-30T06:00:00Z",
      "verified": true,
      "blockchain_hash": "0xabc123...",
      "created_at": "2025-08-30T06:00:00Z"
    }
  ],
  "pagination": {
    "total": 1250,
    "limit": 100,
    "offset": 0,
    "has_next": true
  }
}
```

#### Submit Environmental Data
```http
POST /api/data/environmental
```

**Request Body:**
```json
{
  "source": "sensor_network",
  "data_type": "air_quality",
  "value": 45.2,
  "unit": "aqi",
  "location": {
    "lat": 40.7128,
    "lng": -74.0060
  },
  "timestamp": "2025-08-30T06:00:00Z",
  "metadata": {
    "sensor_id": "NYC_AQ_001",
    "calibration_date": "2025-08-01"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Environmental data submitted successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "blockchain_hash": "0xdef456...",
    "verification_pending": true
  }
}
```

#### Get Data Sources
```http
GET /api/data/sources
```

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "name": "weather_api",
      "display_name": "OpenWeatherMap API",
      "data_types": ["temperature", "humidity", "pressure", "wind_speed"],
      "update_frequency": "hourly",
      "status": "active",
      "last_update": "2025-08-30T06:00:00Z"
    },
    {
      "name": "noaa",
      "display_name": "NOAA Tides & Currents",
      "data_types": ["ocean_temperature", "tide_level", "wave_height"],
      "update_frequency": "6_minutes",
      "status": "active",
      "last_update": "2025-08-30T05:54:00Z"
    }
  ]
}
```

### 🚨 Threat Detection Endpoints

#### Get Active Threats
```http
GET /api/threats/active
```

**Query Parameters:**
- `type` (optional): Threat type (storm, pollution, erosion, algal_bloom, illegal_dumping)
- `severity` (optional): Minimum severity (1-5)
- `location` (optional): Geographic filter (lat,lng,radius_km)
- `limit` (optional): Max results (default: 50)

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": "threat_001",
      "type": "storm",
      "severity": 4,
      "confidence": 0.92,
      "location": {
        "lat": 25.7617,
        "lng": -80.1918
      },
      "address": "Miami Beach, FL",
      "description": "Severe tropical storm conditions detected with high winds and heavy rainfall",
      "estimated_impact": "Potential flooding, power outages affecting 500,000+ residents",
      "affected_population": 500000,
      "timestamp": "2025-08-30T06:00:00Z",
      "verified": true,
      "blockchain_hash": "0x789abc...",
      "ai_detection_model": "storm_v2.1",
      "supporting_data": [
        {
          "source": "weather_api",
          "data_type": "wind_speed",
          "value": 85,
          "unit": "mph"
        }
      ]
    }
  ],
  "total": 3
}
```

#### Register New Threat
```http
POST /api/threats/register
```

**Request Body:**
```json
{
  "type": "pollution",
  "severity": 3,
  "confidence": 0.87,
  "location": {
    "lat": 40.7128,
    "lng": -74.0060
  },
  "description": "Elevated air pollution levels detected in downtown Manhattan",
  "supporting_data_ids": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ],
  "estimated_impact": "Respiratory health risks for sensitive populations",
  "affected_population": 150000
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Threat registered successfully",
  "data": {
    "threat_id": "threat_002",
    "blockchain_transaction": "0x456def...",
    "alert_created": true,
    "alert_id": "alert_001"
  }
}
```

#### Update Threat Status
```http
PUT /api/threats/{threat_id}/status
```

**Request Body:**
```json
{
  "status": "resolved",
  "resolution_notes": "Air quality returned to normal levels. All clear issued.",
  "resolved_by": "EPA_Monitor_001"
}
```

#### Verify Threat
```http
POST /api/threats/{threat_id}/verify
```

**Request Body:**
```json
{
  "verified": true,
  "verifier_id": "NOAA_Expert_123",
  "verification_notes": "Confirmed through satellite imagery and ground sensors"
}
```

### 📢 Alert System Endpoints

#### Get Alerts
```http
GET /api/alerts
```

**Query Parameters:**
- `threat_id` (optional): Filter by threat ID
- `status` (optional): Alert status (pending, sent, delivered, failed)
- `severity` (optional): Minimum severity (1-5)
- `channel` (optional): Alert channel (web, email, sms, push)
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": "alert_001",
      "threat_id": "threat_001",
      "message": "URGENT: Hurricane warning for Miami-Dade County. Evacuate immediately if in evacuation zones A and B.",
      "severity": 5,
      "channels": ["web", "email", "sms", "push"],
      "recipients": {
        "web": ["all_subscribers"],
        "email": ["emergency@miami.gov", "alerts@noaa.gov"],
        "sms": ["+1-305-EMERGENCY"]
      },
      "status": "delivered",
      "sent_at": "2025-08-30T06:05:00Z",
      "delivered_at": "2025-08-30T06:05:15Z",
      "delivery_time_ms": 15000,
      "is_emergency": true,
      "blockchain_hash": "0x123456...",
      "created_at": "2025-08-30T06:04:45Z"
    }
  ]
}
```

#### Create Alert
```http
POST /api/alerts/create
```

**Request Body:**
```json
{
  "threat_id": "threat_001",
  "message": "Storm warning: Seek shelter immediately. Heavy rain and winds expected.",
  "severity": 4,
  "channels": ["web", "email", "push"],
  "recipients": {
    "web": ["location:25.7617,-80.1918,50km"],
    "email": ["emergency@miami.gov"],
    "push": ["topic:miami_alerts"]
  },
  "schedule": {
    "send_immediately": true,
    "repeat_interval": 1800,
    "repeat_until": "threat_resolved"
  }
}
```

#### Get Alert Statistics
```http
GET /api/alerts/stats
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_alerts": 1250,
    "last_24_hours": 23,
    "emergency_alerts": 5,
    "delivery_stats": {
      "average_delivery_time": 12500,
      "success_rate": 0.98,
      "failed_deliveries": 25
    },
    "channel_stats": {
      "web": {
        "sent": 1200,
        "delivered": 1195
      },
      "email": {
        "sent": 800,
        "delivered": 792
      },
      "sms": {
        "sent": 300,
        "delivered": 298
      }
    }
  }
}
```

### 📊 Analytics Endpoints

#### Get Threat Analytics
```http
GET /api/analytics/threats
```

**Query Parameters:**
- `period` (optional): Time period (24h, 7d, 30d, 1y)
- `group_by` (optional): Grouping (type, severity, location)

**Response:**
```json
{
  "status": "success",
  "data": {
    "period": "30d",
    "total_threats": 45,
    "by_type": {
      "storm": 15,
      "pollution": 12,
      "erosion": 8,
      "algal_bloom": 7,
      "illegal_dumping": 3
    },
    "by_severity": {
      "1": 5,
      "2": 12,
      "3": 15,
      "4": 10,
      "5": 3
    },
    "trends": {
      "threat_frequency": [
        {"date": "2025-08-01", "count": 2},
        {"date": "2025-08-02", "count": 1}
      ]
    },
    "ai_accuracy": {
      "overall": 0.94,
      "by_type": {
        "storm": 0.97,
        "pollution": 0.91
      }
    }
  }
}
```

#### Get System Health
```http
GET /api/analytics/health
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "system_status": "healthy",
    "uptime": "99.97%",
    "last_downtime": "2025-08-25T03:15:00Z",
    "services": {
      "api": {
        "status": "healthy",
        "response_time": 145,
        "last_check": "2025-08-30T06:00:00Z"
      },
      "database": {
        "status": "healthy",
        "connection_pool": 85,
        "last_check": "2025-08-30T06:00:00Z"
      },
      "blockchain": {
        "status": "healthy",
        "last_transaction": "2025-08-30T05:55:00Z",
        "gas_price": 25
      },
      "ai_models": {
        "status": "healthy",
        "models_loaded": 6,
        "inference_time": 250
      }
    },
    "data_sources": {
      "weather_api": "active",
      "noaa": "active", 
      "nasa": "active",
      "openaq": "delayed"
    }
  }
}
```

### 🔗 Blockchain Integration Endpoints

#### Get Blockchain Audit Trail
```http
GET /api/blockchain/audit
```

**Query Parameters:**
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `event_type` (optional): Event type (data_logged, threat_registered, alert_created)
- `contract` (optional): Contract name

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "transaction_hash": "0xabc123def456...",
      "block_number": 45672891,
      "timestamp": "2025-08-30T06:00:00Z",
      "event_type": "data_logged",
      "contract": "OceanSentinelData",
      "data": {
        "data_hash": "0x789abc...",
        "source": "weather_api",
        "data_type": "temperature"
      },
      "gas_used": 150000,
      "verified": true
    }
  ]
}
```

#### Verify Data Integrity
```http
POST /api/blockchain/verify
```

**Request Body:**
```json
{
  "data_hash": "0x789abc123def456...",
  "data": {
    "source": "weather_api",
    "value": 25.5,
    "timestamp": "2025-08-30T06:00:00Z"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "verified": true,
    "blockchain_record": {
      "transaction_hash": "0xabc123...",
      "block_number": 45672891,
      "timestamp": "2025-08-30T06:00:00Z"
    },
    "integrity_check": "passed"
  }
}
```

## Webhook Endpoints

Ocean Sentinel supports webhooks for real-time notifications:

### Webhook Configuration
```http
POST /api/webhooks/configure
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["threat_registered", "alert_created", "data_verified"],
  "secret": "your_webhook_secret"
}
```

### Webhook Events

#### Threat Registered
```json
{
  "event": "threat_registered",
  "timestamp": "2025-08-30T06:00:00Z",
  "data": {
    "threat_id": "threat_001",
    "type": "storm",
    "severity": 4,
    "location": {"lat": 25.7617, "lng": -80.1918}
  }
}
```

#### Alert Created
```json
{
  "event": "alert_created",
  "timestamp": "2025-08-30T06:05:00Z", 
  "data": {
    "alert_id": "alert_001",
    "threat_id": "threat_001",
    "severity": 5,
    "is_emergency": true
  }
}
```

## Rate Limits

- **Free Tier:** 1,000 requests per hour
- **Pro Tier:** 10,000 requests per hour
- **Enterprise:** Unlimited

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1625097600
```

## Error Handling

All endpoints return errors in a consistent format:

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "The 'severity' parameter must be between 1 and 5",
    "details": {
      "parameter": "severity",
      "provided_value": "10",
      "valid_range": "1-5"
    }
  },
  "timestamp": "2025-08-30T06:00:00Z",
  "request_id": "req_123abc"
}
```

### Common Error Codes

- `UNAUTHORIZED` - Invalid or missing API key
- `RATE_LIMITED` - Too many requests
- `INVALID_PARAMETER` - Parameter validation failed
- `NOT_FOUND` - Resource not found
- `INTERNAL_ERROR` - Server error
- `BLOCKCHAIN_ERROR` - Blockchain transaction failed
- `AI_MODEL_ERROR` - AI inference failed

## SDK Examples

### Python SDK
```python
from ocean_sentinel import OceanSentinelAPI

# Initialize client
client = OceanSentinelAPI(api_key="your_api_key")

# Get active threats
threats = client.threats.get_active(severity=3)

# Submit environmental data
data = client.data.submit({
    "source": "sensor_network",
    "data_type": "air_quality",
    "value": 45.2,
    "location": {"lat": 40.7128, "lng": -74.0060}
})

# Create alert
alert = client.alerts.create({
    "threat_id": "threat_001",
    "message": "Air quality alert",
    "severity": 3,
    "channels": ["web", "email"]
})
```

### JavaScript SDK
```javascript
import { OceanSentinelAPI } from '@ocean-sentinel/api';

// Initialize client
const client = new OceanSentinelAPI({ apiKey: 'your_api_key' });

// Get active threats
const threats = await client.threats.getActive({ severity: 3 });

// Submit environmental data
const data = await client.data.submit({
  source: 'sensor_network',
  dataType: 'air_quality',
  value: 45.2,
  location: { lat: 40.7128, lng: -74.0060 }
});

// Real-time threat monitoring
client.threats.monitor((threat) => {
  console.log('New threat detected:', threat);
});
```

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error
- `502` - Bad Gateway
- `503` - Service Unavailable

## Support

- **Documentation:** https://docs.ocean-sentinel.com
- **Status Page:** https://status.ocean-sentinel.com
- **Support Email:** support@ocean-sentinel.com
- **Community:** https://community.ocean-sentinel.com

## Changelog

### v1.0.0 (2025-08-30)
- Initial API release
- Core threat detection endpoints
- Environmental data ingestion
- Multi-channel alert system
- Blockchain integration
- Real-time webhooks

---

*Last updated: August 30, 2025*