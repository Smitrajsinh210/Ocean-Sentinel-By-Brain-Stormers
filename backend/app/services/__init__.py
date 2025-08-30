"""
Ocean Sentinel - Services Package
Environmental data integration services
"""

import logging
from typing import Dict, Any

# Set up logging for services
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

services_logger = logging.getLogger('ocean_sentinel.services')

__version__ = "1.0.0"
__author__ = "Ocean Sentinel Team"

# Service configurations
SERVICE_CONFIG = {
    "weather": {
        "api_name": "OpenWeatherMap",
        "base_url": "https://api.openweathermap.org/data/2.5",
        "rate_limit": 60,  # requests per minute
        "timeout": 30,     # seconds
        "retry_attempts": 3
    },
    "air_quality": {
        "api_name": "OpenAQ",
        "base_url": "https://api.openaq.org/v2",
        "rate_limit": 100,  # requests per minute
        "timeout": 30,      # seconds
        "retry_attempts": 3
    },
    "ocean": {
        "api_name": "NOAA Tides & Currents",
        "base_url": "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
        "rate_limit": 1000,  # requests per minute
        "timeout": 30,       # seconds
        "retry_attempts": 3
    },
    "nasa": {
        "api_name": "NASA Earth Data",
        "base_url": "https://api.nasa.gov",
        "rate_limit": 60,   # requests per minute
        "timeout": 45,      # seconds
        "retry_attempts": 2
    }
}

# Data quality thresholds
DATA_QUALITY_THRESHOLDS = {
    "minimum_data_points": 3,
    "maximum_age_hours": 24,
    "confidence_threshold": 0.8,
    "completeness_threshold": 0.7
}

# Parameter mappings for standardization
PARAMETER_MAPPINGS = {
    "weather": {
        "temp": "temperature",
        "feels_like": "apparent_temperature", 
        "temp_min": "temperature_min",
        "temp_max": "temperature_max",
        "pressure": "pressure",
        "humidity": "humidity",
        "wind_speed": "wind_speed",
        "wind_deg": "wind_direction",
        "visibility": "visibility",
        "clouds": "cloud_cover",
        "rain": "precipitation",
        "snow": "snowfall"
    },
    "air_quality": {
        "pm25": "pm25",
        "pm10": "pm10", 
        "o3": "ozone",
        "no2": "nitrogen_dioxide",
        "so2": "sulfur_dioxide",
        "co": "carbon_monoxide"
    },
    "ocean": {
        "water_level": "tide_level",
        "water_temperature": "water_temperature",
        "wave_height": "wave_height",
        "dominant_period": "wave_period",
        "average_period": "wave_period_avg",
        "mean_wave_dir": "wave_direction",
        "air_pressure": "atmospheric_pressure",
        "wind_speed": "wind_speed",
        "wind_direction": "wind_direction",
        "salinity": "salinity"
    }
}

# Standard units for each parameter
PARAMETER_UNITS = {
    "temperature": "°C",
    "apparent_temperature": "°C",
    "temperature_min": "°C", 
    "temperature_max": "°C",
    "pressure": "hPa",
    "humidity": "%",
    "wind_speed": "km/h",
    "wind_direction": "degrees",
    "visibility": "km",
    "cloud_cover": "%",
    "precipitation": "mm",
    "snowfall": "mm",
    "pm25": "μg/m³",
    "pm10": "μg/m³",
    "ozone": "ppb",
    "nitrogen_dioxide": "ppb",
    "sulfur_dioxide": "ppb", 
    "carbon_monoxide": "ppm",
    "tide_level": "meters",
    "water_temperature": "°C",
    "wave_height": "meters",
    "wave_period": "seconds",
    "wave_period_avg": "seconds",
    "wave_direction": "degrees",
    "atmospheric_pressure": "hPa",
    "salinity": "psu"
}

# Service error codes
SERVICE_ERROR_CODES = {
    1001: "API_KEY_MISSING",
    1002: "API_KEY_INVALID", 
    1003: "RATE_LIMIT_EXCEEDED",
    1004: "REQUEST_TIMEOUT",
    1005: "INVALID_COORDINATES",
    1006: "DATA_NOT_AVAILABLE",
    1007: "SERVICE_UNAVAILABLE",
    1008: "PARSING_ERROR",
    1009: "DATA_QUALITY_LOW",
    1010: "CACHE_ERROR"
}

def get_service_config(service_name: str) -> Dict[str, Any]:
    """Get configuration for specific service"""
    return SERVICE_CONFIG.get(service_name, {})

def get_parameter_mapping(service_name: str) -> Dict[str, str]:
    """Get parameter mapping for specific service"""
    return PARAMETER_MAPPINGS.get(service_name, {})

def get_parameter_unit(parameter: str) -> str:
    """Get standard unit for parameter"""
    return PARAMETER_UNITS.get(parameter, "")

def standardize_parameter_name(service_name: str, original_name: str) -> str:
    """Standardize parameter name using service mapping"""
    mapping = get_parameter_mapping(service_name)
    return mapping.get(original_name, original_name.lower())

def validate_coordinates(lat: float, lng: float) -> bool:
    """Validate coordinate values"""
    try:
        return (-90 <= lat <= 90) and (-180 <= lng <= 180)
    except (TypeError, ValueError):
        return False

def calculate_data_quality_score(
    data_points: int,
    completeness: float,
    age_hours: float,
    has_errors: bool
) -> float:
    """Calculate data quality score (0-100)"""
    try:
        score = 100.0
        
        # Penalize insufficient data points
        if data_points < DATA_QUALITY_THRESHOLDS["minimum_data_points"]:
            score -= 30
        
        # Penalize incomplete data
        if completeness < DATA_QUALITY_THRESHOLDS["completeness_threshold"]:
            score -= (1 - completeness) * 40
        
        # Penalize old data
        max_age = DATA_QUALITY_THRESHOLDS["maximum_age_hours"]
        if age_hours > max_age:
            score -= min(30, (age_hours - max_age) / max_age * 30)
        
        # Penalize errors
        if has_errors:
            score -= 20
        
        return max(0.0, min(100.0, score))
        
    except Exception as e:
        services_logger.error(f"Error calculating data quality score: {str(e)}")
        return 0.0

# Export main classes and functions
__all__ = [
    "SERVICE_CONFIG",
    "DATA_QUALITY_THRESHOLDS", 
    "PARAMETER_MAPPINGS",
    "PARAMETER_UNITS",
    "SERVICE_ERROR_CODES",
    "get_service_config",
    "get_parameter_mapping",
    "get_parameter_unit", 
    "standardize_parameter_name",
    "validate_coordinates",
    "calculate_data_quality_score",
    "services_logger"
]

services_logger.info("Ocean Sentinel Services package initialized")