"""
Ocean Sentinel - ML Models Package
AI-powered threat detection and prediction models
"""

import logging
import os
from typing import Dict, Any

__version__ = "1.0.0"
__author__ = "Ocean Sentinel Team"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

ml_logger = logging.getLogger('ocean_sentinel.ml')

# Model configurations
ML_MODEL_CONFIG = {
    "threat_detection": {
        "models": ["storm", "pollution", "erosion", "algal_bloom", "illegal_dumping"],
        "confidence_threshold": 0.75,
        "ensemble_voting": "soft",
        "retrain_interval_hours": 168  # 1 week
    },
    "anomaly_detection": {
        "window_size": 24,  # hours
        "contamination": 0.1,  # 10% anomaly rate
        "algorithms": ["isolation_forest", "local_outlier_factor", "one_class_svm"]
    },
    "prediction": {
        "forecast_horizon_hours": [2, 4, 8, 24],
        "update_frequency_minutes": 15,
        "minimum_data_points": 50
    },
    "preprocessing": {
        "normalization_method": "robust_scaler",
        "feature_selection": "automated",
        "missing_value_strategy": "interpolation"
    }
}

# Threat type mappings
THREAT_TYPE_MAPPING = {
    0: "storm",
    1: "pollution", 
    2: "erosion",
    3: "algal_bloom",
    4: "illegal_dumping",
    5: "tsunami",
    6: "oil_spill",
    7: "anomaly"
}

REVERSE_THREAT_MAPPING = {v: k for k, v in THREAT_TYPE_MAPPING.items()}

# Feature importance thresholds
FEATURE_IMPORTANCE_THRESHOLDS = {
    "storm": {
        "wind_speed": 0.3,
        "pressure": 0.25, 
        "temperature": 0.15,
        "humidity": 0.15,
        "visibility": 0.15
    },
    "pollution": {
        "pm25": 0.4,
        "pm10": 0.3,
        "ozone": 0.15,
        "wind_speed": 0.15
    },
    "algal_bloom": {
        "water_temperature": 0.35,
        "salinity": 0.25,
        "visibility": 0.2,
        "wave_height": 0.2
    },
    "erosion": {
        "wave_height": 0.4,
        "tide_level": 0.3,
        "wind_speed": 0.2,
        "precipitation": 0.1
    }
}

# Model performance metrics targets
PERFORMANCE_TARGETS = {
    "accuracy": 0.90,
    "precision": 0.85,
    "recall": 0.88,
    "f1_score": 0.86,
    "false_positive_rate": 0.05,
    "detection_latency_seconds": 30
}

def get_model_config(model_type: str) -> Dict[str, Any]:
    """Get configuration for specific model type"""
    return ML_MODEL_CONFIG.get(model_type, {})

def get_threat_id(threat_name: str) -> int:
    """Get numeric ID for threat type"""
    return REVERSE_THREAT_MAPPING.get(threat_name.lower(), 7)  # Default to anomaly

def get_threat_name(threat_id: int) -> str:
    """Get threat name from numeric ID"""
    return THREAT_TYPE_MAPPING.get(threat_id, "anomaly")

def validate_model_performance(metrics: Dict[str, Any], model_type: str = "general") -> bool:
    """Validate if model performance meets minimum requirements"""
    accuracy_threshold = PERFORMANCE_TARGETS["accuracy"]
    if model_type == "anomaly_detection":
        accuracy_threshold = 0.80  # Lower threshold for anomaly detection
    
    return (
        metrics.get("accuracy", 0) >= accuracy_threshold and
        metrics.get("precision", 0) >= PERFORMANCE_TARGETS["precision"] and
        metrics.get("recall", 0) >= PERFORMANCE_TARGETS["recall"]
    )

# Export main classes (will be imported when files are created)
__all__ = [
    "ML_MODEL_CONFIG",
    "THREAT_TYPE_MAPPING", 
    "REVERSE_THREAT_MAPPING",
    "FEATURE_IMPORTANCE_THRESHOLDS",
    "PERFORMANCE_TARGETS",
    "get_model_config",
    "get_threat_id", 
    "get_threat_name",
    "validate_model_performance",
    "ml_logger"
]

ml_logger.info("Ocean Sentinel ML Models package initialized")