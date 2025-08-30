"""
Ocean Sentinel Configuration Management
Centralized settings using Pydantic for validation
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseSettings, validator, Field

class Settings(BaseSettings):
    """Application settings with environment variable validation"""
    
    # Application settings
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    secret_key: str = Field(env="SECRET_KEY")
    
    # Database settings (Supabase)
    supabase_url: str = Field(env="SUPABASE_URL")
    supabase_anon_key: str = Field(env="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(env="SUPABASE_SERVICE_ROLE_KEY")
    
    # External API keys
    openweather_api_key: str = Field(env="OPENWEATHER_API_KEY")
    openaq_api_key: Optional[str] = Field(default=None, env="OPENAQ_API_KEY")
    noaa_api_key: Optional[str] = Field(default=None, env="NOAA_API_KEY")
    nasa_api_key: Optional[str] = Field(default=None, env="NASA_API_KEY")
    
    # Blockchain settings
    starton_api_key: str = Field(env="STARTON_API_KEY")
    contract_address: str = Field(env="CONTRACT_ADDRESS")
    polygon_network: str = Field(default="mumbai", env="POLYGON_NETWORK")
    
    # AI/ML settings
    google_ai_studio_key: Optional[str] = Field(default=None, env="GOOGLE_AI_STUDIO_KEY")
    
    # Real-time notifications
    pusher_app_id: str = Field(env="PUSHER_APP_ID")
    pusher_key: str = Field(env="PUSHER_KEY")
    pusher_secret: str = Field(env="PUSHER_SECRET")
    pusher_cluster: str = Field(default="us2", env="PUSHER_CLUSTER")
    
    # SMS notifications
    twilio_sid: Optional[str] = Field(default=None, env="TWILIO_SID")
    twilio_token: Optional[str] = Field(default=None, env="TWILIO_TOKEN")
    twilio_phone: Optional[str] = Field(default=None, env="TWILIO_PHONE")
    
    # Email notifications
    resend_api_key: Optional[str] = Field(default=None, env="RESEND_API_KEY")
    
    # Bubble.io integration
    bubble_api_key: Optional[str] = Field(default=None, env="BUBBLE_API_KEY")
    bubble_app_id: Optional[str] = Field(default=None, env="BUBBLE_APP_ID")
    
    # Security settings
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    
    # Performance settings
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    worker_timeout: int = Field(default=30, env="WORKER_TIMEOUT")
    
    # Geographic boundaries
    min_latitude: float = Field(default=-90.0, env="MIN_LATITUDE")
    max_latitude: float = Field(default=90.0, env="MAX_LATITUDE")
    min_longitude: float = Field(default=-180.0, env="MIN_LONGITUDE")
    max_longitude: float = Field(default=180.0, env="MAX_LONGITUDE")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Monitoring settings
    monitoring_interval: int = Field(default=300, env="MONITORING_INTERVAL")  # 5 minutes
    data_retention_days: int = Field(default=365, env="DATA_RETENTION_DAYS")
    
    # Threat detection settings
    threat_confidence_threshold: float = Field(default=0.7, env="THREAT_CONFIDENCE_THRESHOLD")
    critical_severity_threshold: int = Field(default=4, env="CRITICAL_SEVERITY_THRESHOLD")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v
    
    @property
    def allowed_origins(self) -> List[str]:
        """Get allowed CORS origins based on environment"""
        if self.environment == "development":
            return ["*"]
        elif self.environment == "staging":
            return [
                "https://your-staging-domain.com",
                "https://your-bubble-staging.bubbleapps.io"
            ]
        else:  # production
            return [
                "https://your-production-domain.com",
                "https://your-bubble-app.bubbleapps.io"
            ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# API Configuration
API_CONFIG = {
    "openweather": {
        "base_url": "https://api.openweathermap.org/data/2.5",
        "geo_url": "https://api.openweathermap.org/geo/1.0",
        "rate_limit": 60,  # requests per minute
        "timeout": 10
    },
    "openaq": {
        "base_url": "https://api.openaq.org/v2",
        "rate_limit": 10,  # requests per minute
        "timeout": 15
    },
    "noaa": {
        "base_url": "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
        "rate_limit": 30,  # requests per minute
        "timeout": 20
    },
    "nasa": {
        "base_url": "https://api.nasa.gov",
        "earth_url": "https://api.nasa.gov/planetary/earth",
        "rate_limit": 1000,  # requests per hour
        "timeout": 30
    },
    "starton": {
        "base_url": "https://api.starton.com/v3",
        "timeout": 30
    }
}

# Threat Detection Configuration
THREAT_TYPES = {
    "storm": {
        "parameters": ["wind_speed", "pressure", "precipitation", "temperature"],
        "severity_thresholds": {
            1: {"wind_speed": 25, "pressure": 1010},
            2: {"wind_speed": 40, "pressure": 1005},
            3: {"wind_speed": 60, "pressure": 995},
            4: {"wind_speed": 85, "pressure": 980},
            5: {"wind_speed": 120, "pressure": 960}
        }
    },
    "pollution": {
        "parameters": ["pm2_5", "pm10", "no2", "so2", "co", "o3"],
        "severity_thresholds": {
            1: {"pm2_5": 15, "pm10": 25},
            2: {"pm2_5": 35, "pm10": 50},
            3: {"pm2_5": 55, "pm10": 75},
            4: {"pm2_5": 125, "pm10": 150},
            5: {"pm2_5": 250, "pm10": 300}
        }
    },
    "erosion": {
        "parameters": ["wave_height", "wind_speed", "tidal_range"],
        "severity_thresholds": {
            1: {"wave_height": 1.5, "wind_speed": 20},
            2: {"wave_height": 2.5, "wind_speed": 30},
            3: {"wave_height": 4.0, "wind_speed": 45},
            4: {"wave_height": 6.0, "wind_speed": 65},
            5: {"wave_height": 8.0, "wind_speed": 85}
        }
    },
    "algal_bloom": {
        "parameters": ["chlorophyll", "temperature", "nutrients"],
        "severity_thresholds": {
            1: {"chlorophyll": 10, "temperature": 20},
            2: {"chlorophyll": 25, "temperature": 24},
            3: {"chlorophyll": 50, "temperature": 28},
            4: {"chlorophyll": 100, "temperature": 32},
            5: {"chlorophyll": 200, "temperature": 35}
        }
    },
    "illegal_dumping": {
        "parameters": ["anomaly_score", "chemical_indicators"],
        "severity_thresholds": {
            1: {"anomaly_score": 0.3},
            2: {"anomaly_score": 0.5},
            3: {"anomaly_score": 0.7},
            4: {"anomaly_score": 0.85},
            5: {"anomaly_score": 0.95}
        }
    }
}

# Notification Channels Configuration
NOTIFICATION_CHANNELS = {
    "sms": {
        "enabled": bool(settings.twilio_sid),
        "rate_limit": 50,  # per hour
        "character_limit": 1600
    },
    "email": {
        "enabled": bool(settings.resend_api_key),
        "rate_limit": 100,  # per hour
        "template_name": "threat_alert"
    },
    "push": {
        "enabled": bool(settings.pusher_app_id),
        "rate_limit": 1000,  # per hour
        "channels": ["threat-alerts", "system-updates"]
    },
    "webhook": {
        "enabled": True,
        "rate_limit": 200,  # per hour
        "timeout": 10
    }
}

# Database Table Names
DB_TABLES = {
    "threats": "threats",
    "environmental_data_summary": "environmental_data_summary",
    "environmental_data_details": "environmental_data_details",
    "alert_notifications": "alert_notifications",
    "users": "users",
    "system_logs": "system_logs",
    "blockchain_transactions": "blockchain_transactions",
    "monitoring_stations": "monitoring_stations"
}

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "ocean_sentinel.log"
        }
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["console", "file"]
        }
    }
}
