"""
Ocean Sentinel - AI Model Utilities
TensorFlow.js model helpers and ML utilities
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class ModelManager:
    """Manage AI/ML models for threat detection"""
    
    def __init__(self):
        self.models_path = "models/"  # Would be cloud storage in production
        self.loaded_models = {}
        
    def save_model_metadata(self, model_name: str, metadata: Dict[str, Any]) -> bool:
        """Save model metadata for TensorFlow.js"""
        try:
            metadata_path = f"{self.models_path}{model_name}_metadata.json"
            
            # Ensure models directory exists
            os.makedirs(self.models_path, exist_ok=True)
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Saved metadata for model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model metadata: {e}")
            return False
    
    def create_tensorflowjs_model_spec(self, model_name: str, input_shape: List[int], output_classes: List[str]) -> Dict[str, Any]:
        """Create TensorFlow.js model specification"""
        model_spec = {
            "format": "graph-model",
            "generatedBy": "Ocean Sentinel AI",
            "convertedBy": "TensorFlow.js Converter",
            "signature": {
                "inputs": {
                    "input": {
                        "name": "input:0",
                        "dtype": "DT_FLOAT",
                        "tensorShape": {
                            "dim": [{"size": -1}, *[{"size": dim} for dim in input_shape]]
                        }
                    }
                },
                "outputs": {
                    "output": {
                        "name": "output:0",
                        "dtype": "DT_FLOAT"
                    }
                }
            },
            "modelTopology": self._create_model_topology(input_shape, len(output_classes)),
            "weightsManifest": [{
                "paths": [f"{model_name}.bin"],
                "weights": self._create_weights_spec(model_name)
            }],
            "userDefinedMetadata": {
                "model_name": model_name,
                "input_features": input_shape,
                "output_classes": output_classes,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }
        }
        
        return model_spec
    
    def _create_model_topology(self, input_shape: List[int], num_classes: int) -> Dict[str, Any]:
        """Create simple neural network topology for TensorFlow.js"""
        return {
            "class_name": "Sequential",
            "config": {
                "name": "ocean_sentinel_model",
                "layers": [
                    {
                        "class_name": "Dense",
                        "config": {
                            "units": 64,
                            "activation": "relu",
                            "use_bias": True,
                            "input_shape": input_shape
                        }
                    },
                    {
                        "class_name": "Dropout",
                        "config": {
                            "rate": 0.2
                        }
                    },
                    {
                        "class_name": "Dense",
                        "config": {
                            "units": 32,
                            "activation": "relu",
                            "use_bias": True
                        }
                    },
                    {
                        "class_name": "Dense",
                        "config": {
                            "units": num_classes,
                            "activation": "softmax" if num_classes > 1 else "sigmoid",
                            "use_bias": True
                        }
                    }
                ]
            }
        }
    
    def _create_weights_spec(self, model_name: str) -> List[Dict[str, Any]]:
        """Create weights specification for TensorFlow.js model"""
        # This would contain actual weight specifications
        # For now, return a template structure
        return [
            {"name": "dense/kernel", "shape": [5, 64], "dtype": "float32"},
            {"name": "dense/bias", "shape": [64], "dtype": "float32"},
            {"name": "dense_1/kernel", "shape": [64, 32], "dtype": "float32"},
            {"name": "dense_1/bias", "shape": [32], "dtype": "float32"},
            {"name": "dense_2/kernel", "shape": [32, 1], "dtype": "float32"},
            {"name": "dense_2/bias", "shape": [1], "dtype": "float32"}
        ]

class FeatureEngineer:
    """Feature engineering utilities for environmental data"""
    
    @staticmethod
    def normalize_weather_features(weather_data: Dict[str, Any]) -> List[float]:
        """Normalize weather data for ML models"""
        try:
            # Define normalization ranges based on typical environmental values
            normalization_ranges = {
                'temperature': (-40, 50),      # Celsius
                'humidity': (0, 100),          # Percentage
                'pressure': (950, 1050),       # hPa
                'wind_speed': (0, 100),        # m/s
                'precipitation': (0, 100)      # mm
            }
            
            normalized_features = []
            
            for feature in ['temperature', 'humidity', 'pressure', 'wind_speed', 'precipitation']:
                value = weather_data.get(feature, 0)
                min_val, max_val = normalization_ranges[feature]
                
                # Min-max normalization to [0, 1]
                normalized = (value - min_val) / (max_val - min_val)
                normalized = max(0, min(1, normalized))  # Clamp to [0, 1]
                
                normalized_features.append(normalized)
            
            return normalized_features
            
        except Exception as e:
            logger.error(f"Error normalizing weather features: {e}")
            return [0.5] * 5  # Return neutral values on error
    
    @staticmethod
    def normalize_air_quality_features(air_quality_data: Dict[str, Any]) -> List[float]:
        """Normalize air quality data for ML models"""
        try:
            normalization_ranges = {
                'pm2_5': (0, 250),    # μg/m³
                'pm10': (0, 350),     # μg/m³
                'no2': (0, 200),      # μg/m³
                'so2': (0, 500),      # μg/m³
                'co': (0, 50),        # mg/m³
                'o3': (0, 300),       # μg/m³
                'aqi': (0, 500)       # AQI scale
            }
            
            normalized_features = []
            
            for feature in ['pm2_5', 'pm10', 'no2', 'so2', 'co', 'o3', 'aqi']:
                value = air_quality_data.get(feature, 0)
                min_val, max_val = normalization_ranges[feature]
                
                normalized = (value - min_val) / (max_val - min_val)
                normalized = max(0, min(1, normalized))
                
                normalized_features.append(normalized)
            
            return normalized_features
            
        except Exception as e:
            logger.error(f"Error normalizing air quality features: {e}")
            return [0.5] * 7
    
    @staticmethod
    def normalize_ocean_features(ocean_data: Dict[str, Any]) -> List[float]:
        """Normalize ocean/tidal data for ML models"""
        try:
            normalization_ranges = {
                'water_level': (-5, 5),        # meters relative to datum
                'wave_height': (0, 10),        # meters
                'water_temperature': (0, 35),  # Celsius
                'current_speed': (0, 5)        # m/s
            }
            
            normalized_features = []
            
            for feature in ['water_level', 'wave_height', 'water_temperature', 'current_speed']:
                value = ocean_data.get(feature, 0)
                min_val, max_val = normalization_ranges[feature]
                
                normalized = (value - min_val) / (max_val - min_val)
                normalized = max(0, min(1, normalized))
                
                normalized_features.append(normalized)
            
            return normalized_features
            
        except Exception as e:
            logger.error(f"Error normalizing ocean features: {e}")
            return [0.5] * 4
    
    @staticmethod
    def create_feature_vector(environmental_data: Dict[str, Any]) -> List[float]:
        """Create complete feature vector from environmental data"""
        feature_vector = []
        
        # Weather features
        weather_features = FeatureEngineer.normalize_weather_features(
            environmental_data.get('weather', {})
        )
        feature_vector.extend(weather_features)
        
        # Air quality features
        air_quality_features = FeatureEngineer.normalize_air_quality_features(
            environmental_data.get('air_quality', {})
        )
        feature_vector.extend(air_quality_features)
        
        # Ocean features
        ocean_features = FeatureEngineer.normalize_ocean_features(
            environmental_data.get('ocean', {})
        )
        feature_vector.extend(ocean_features)
        
        # Temporal features
        now = datetime.utcnow()
        hour_sin = np.sin(2 * np.pi * now.hour / 24)
        hour_cos = np.cos(2 * np.pi * now.hour / 24)
        day_sin = np.sin(2 * np.pi * now.timetuple().tm_yday / 365)
        day_cos = np.cos(2 * np.pi * now.timetuple().tm_yday / 365)
        
        feature_vector.extend([hour_sin, hour_cos, day_sin, day_cos])
        
        return feature_vector

class ThresholdClassifier:
    """Rule-based classifier using environmental thresholds"""
    
    def __init__(self):
        self.thresholds = {
            'storm': {
                'wind_speed': 25,      # m/s
                'pressure_drop': 10,   # hPa below normal
                'precipitation': 25    # mm/hour
            },
            'pollution': {
                'pm2_5': 35,          # μg/m³
                'aqi': 100,           # AQI
                'no2': 100            # μg/m³
            },
            'erosion': {
                'wave_height': 3,     # meters
                'wind_speed': 15,     # m/s
                'water_level': 2      # meters above normal
            }
        }
    
    def classify_threat(self, environmental_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify threats based on threshold rules"""
        threats = []
        
        # Storm detection
        storm_score = self._check_storm_conditions(environmental_data)
        if storm_score > 0.5:
            threats.append({
                'type': 'storm',
                'confidence': storm_score,
                'severity': min(5, int(storm_score * 5) + 1)
            })
        
        # Pollution detection
        pollution_score = self._check_pollution_conditions(environmental_data)
        if pollution_score > 0.5:
            threats.append({
                'type': 'pollution',
                'confidence': pollution_score,
                'severity': min(5, int(pollution_score * 5) + 1)
            })
        
        # Erosion detection
        erosion_score = self._check_erosion_conditions(environmental_data)
        if erosion_score > 0.5:
            threats.append({
                'type': 'erosion',
                'confidence': erosion_score,
                'severity': min(5, int(erosion_score * 5) + 1)
            })
        
        return {
            'threats_detected': threats,
            'total_threats': len(threats),
            'max_severity': max([t['severity'] for t in threats], default=0)
        }
    
    def _check_storm_conditions(self, data: Dict[str, Any]) -> float:
        """Check for storm conditions"""
        weather = data.get('weather', {})
        
        score = 0.0
        factors = 0
        
        # Wind speed factor
        wind_speed = weather.get('wind_speed', 0)
        if wind_speed > self.thresholds['storm']['wind_speed']:
            score += min(1.0, wind_speed / 50.0)  # Max at 50 m/s
            factors += 1
        
        # Pressure factor
        pressure = weather.get('pressure', 1013)
        if pressure < 1000:  # Low pressure system
            score += min(1.0, (1013 - pressure) / 50.0)  # Max at 50 hPa drop
            factors += 1
        
        # Precipitation factor
        precipitation = weather.get('precipitation', 0)
        if precipitation > self.thresholds['storm']['precipitation']:
            score += min(1.0, precipitation / 100.0)  # Max at 100mm
            factors += 1
        
        return score / max(1, factors)
    
    def _check_pollution_conditions(self, data: Dict[str, Any]) -> float:
        """Check for pollution conditions"""
        air_quality = data.get('air_quality', {})
        
        score = 0.0
        factors = 0
        
        # PM2.5 factor
        pm25 = air_quality.get('pm2_5', 0)
        if pm25 > self.thresholds['pollution']['pm2_5']:
            score += min(1.0, pm25 / 200.0)  # Max at 200 μg/m³
            factors += 1
        
        # AQI factor
        aqi = air_quality.get('aqi', 0)
        if aqi > self.thresholds['pollution']['aqi']:
            score += min(1.0, aqi / 300.0)  # Max at 300 AQI
            factors += 1
        
        # NO2 factor
        no2 = air_quality.get('no2', 0)
        if no2 > self.thresholds['pollution']['no2']:
            score += min(1.0, no2 / 200.0)  # Max at 200 μg/m³
            factors += 1
        
        return score / max(1, factors)
    
    def _check_erosion_conditions(self, data: Dict[str, Any]) -> float:
        """Check for coastal erosion conditions"""
        ocean = data.get('ocean', {})
        weather = data.get('weather', {})
        
        score = 0.0
        factors = 0
        
        # Wave height factor
        wave_height = ocean.get('wave_height', 0)
        if wave_height > self.thresholds['erosion']['wave_height']:
            score += min(1.0, wave_height / 8.0)  # Max at 8m waves
            factors += 1
        
        # Wind speed factor (coastal)
        wind_speed = weather.get('wind_speed', 0)
        if wind_speed > self.thresholds['erosion']['wind_speed']:
            score += min(1.0, wind_speed / 40.0)  # Max at 40 m/s
            factors += 1
        
        # Water level factor
        water_level = ocean.get('water_level', 0)
        if water_level > self.thresholds['erosion']['water_level']:
            score += min(1.0, water_level / 5.0)  # Max at 5m above normal
            factors += 1
        
        return score / max(1, factors)

# Global instances
model_manager = ModelManager()
feature_engineer = FeatureEngineer()
threshold_classifier = ThresholdClassifier()
