import os
import json
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    genai = None

# Import from our existing codebase
from . import ML_MODEL_CONFIG, THREAT_TYPE_MAPPING, FEATURE_IMPORTANCE_THRESHOLDS, ml_logger

@dataclass
class ThreatDetectionResult:
    """Result of threat detection analysis"""
    threat_type: str
    confidence: float
    severity: int
    detected: bool
    description: str
    features_used: List[str]
    model_scores: Dict[str, float]
    processing_time_ms: int
    metadata: Dict[str, Any]

class ThreatDetectionEngine:
    """
    Multi-threat detection engine using ensemble learning and AI models
    Detects: storms, pollution, erosion, algal blooms, illegal dumping
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = {}
        self.is_trained = {}
        self.model_metrics = {}
        self.ai_model = None
        
        # Initialize Google AI Studio if available
        if GOOGLE_AI_AVAILABLE and os.environ.get('AIzaSyDy-dVUVFN3wLRXhX7jYC6dqpdfkYJ46w0'):
            try:
                genai.configure(api_key=os.environ.get('AIzaSyDy-dVUVFN3wLRXhX7jYC6dqpdfkYJ46w0'))
                self.ai_model = genai.GenerativeModel('gemini-pro')
            except Exception as e:
                ml_logger.warning(f"Could not initialize Google AI: {str(e)}")
        
        # Confidence thresholds for each threat type
        self.confidence_thresholds = {
            'storm': 0.80,
            'pollution': 0.75,
            'erosion': 0.70,
            'algal_bloom': 0.80,
            'illegal_dumping': 0.85
        }
        
        # Feature mappings for each threat type
        self.threat_features = {
            'storm': ['wind_speed', 'pressure', 'temperature', 'humidity', 'visibility', 'wind_direction'],
            'pollution': ['pm25', 'pm10', 'ozone', 'wind_speed', 'temperature', 'humidity'],
            'erosion': ['wave_height', 'tide_level', 'wind_speed', 'precipitation', 'temperature'],
            'algal_bloom': ['water_temperature', 'salinity', 'visibility', 'wave_height', 'tide_level'],
            'illegal_dumping': ['visibility', 'wind_speed', 'wave_height', 'water_temperature']
        }
        
        ml_logger.info("ThreatDetectionEngine initialized")

    async def initialize_models(self):
        """Initialize and load pre-trained models"""
        try:
            model_config = ML_MODEL_CONFIG.get('threat_detection', {})
            threat_types = model_config.get('models', ['storm', 'pollution', 'erosion', 'algal_bloom'])
            
            for threat_type in threat_types:
                await self._initialize_threat_model(threat_type)
            
            ml_logger.info(f"Initialized {len(self.models)} threat detection models")
            return True
            
        except Exception as e:
            ml_logger.error(f"Error initializing models: {str(e)}")
            return False

    async def _initialize_threat_model(self, threat_type: str):
        """Initialize individual threat detection model"""
        try:
            # Create ensemble model
            ensemble_models = [
                ('rf', RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=1
                )),
                ('gb', GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    random_state=42
                )),
                ('svm', SVC(
                    kernel='rbf',
                    probability=True,
                    random_state=42
                )),
                ('mlp', MLPClassifier(
                    hidden_layer_sizes=(100, 50),
                    max_iter=500,
                    random_state=42
                ))
            ]
            
            self.models[threat_type] = ensemble_models
            self.scalers[threat_type] = StandardScaler()
            self.feature_columns[threat_type] = self.threat_features.get(threat_type, [])
            self.is_trained[threat_type] = False
            
        except Exception as e:
            ml_logger.error(f"Error initializing {threat_type} model: {str(e)}")

    async def detect_threats(
        self, 
        environmental_data: List[Dict[str, Any]], 
        location: Dict[str, float],
        detection_models: List[str] = None
    ) -> List[ThreatDetectionResult]:
        """
        Detect multiple threats from environmental data
        """
        start_time = datetime.now()
        results = []
        
        try:
            # Preprocess data
            processed_data = self._prepare_features(environmental_data)
            
            if processed_data.empty:
                ml_logger.warning("No valid environmental data for threat detection")
                return results
            
            # Determine which models to run
            models_to_run = detection_models or list(self.models.keys())
            
            for threat_type in models_to_run:
                if threat_type in self.models:
                    detection_result = await self._detect_single_threat(
                        threat_type, 
                        processed_data, 
                        location,
                        start_time
                    )
                    
                    if detection_result:
                        results.append(detection_result)
            
            ml_logger.info(f"Completed threat detection for {len(models_to_run)} models")
            return results
            
        except Exception as e:
            ml_logger.error(f"Error in threat detection: {str(e)}")
            return results

    def _prepare_features(self, environmental_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare features from environmental data"""
        try:
            if not environmental_data:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(environmental_data)
            
            # Handle different data structures
            for col in df.columns:
                if col == 'value':
                    continue
                # Convert to numeric if possible
                df[col] = pd.to_numeric(df[col], errors='ignore')
            
            # If data has 'data_type' and 'value' columns, pivot it
            if 'data_type' in df.columns and 'value' in df.columns:
                df_pivoted = df.pivot_table(
                    index=df.index if 'timestamp' not in df.columns else 'timestamp',
                    columns='data_type', 
                    values='value', 
                    aggfunc='mean'
                ).reset_index()
                df = df_pivoted
            
            # Clean column names
            df.columns = [str(col).lower().replace(' ', '_') for col in df.columns]
            
            # Fill missing values with 0 (simple approach)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            
            return df
            
        except Exception as e:
            ml_logger.error(f"Error preparing features: {str(e)}")
            return pd.DataFrame()

    async def _detect_single_threat(
        self, 
        threat_type: str, 
        data: pd.DataFrame, 
        location: Dict[str, float],
        start_time: datetime
    ) -> Optional[ThreatDetectionResult]:
        """Detect single threat type"""
        try:
            # Get required features for this threat type
            required_features = self.feature_columns[threat_type]
            available_features = [f for f in required_features if f in data.columns]
            
            if len(available_features) < 2:  # Need at least 2 features
                return None
            
            # Extract feature values
            feature_data = data[available_features].fillna(0)
            
            if self.is_trained[threat_type]:
                # Use trained ensemble models
                confidence, severity = await self._predict_with_ensemble(
                    threat_type, feature_data
                )
            else:
                # Use rule-based detection
                confidence, severity = self._rule_based_detection(
                    threat_type, feature_data, available_features
                )
            
            # Determine if threat is detected
            threshold = self.confidence_thresholds[threat_type]
            detected = confidence >= threshold
            
            # Generate description
            description = self._generate_threat_description(
                threat_type, severity, confidence, available_features, feature_data
            )
            
            # Calculate processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ThreatDetectionResult(
                threat_type=threat_type,
                confidence=round(confidence, 4),
                severity=severity,
                detected=detected,
                description=description,
                features_used=available_features,
                model_scores={
                    'ensemble_confidence': confidence,
                    'feature_count': len(available_features)
                },
                processing_time_ms=processing_time,
                metadata={
                    'location': location,
                    'detection_method': 'ensemble' if self.is_trained[threat_type] else 'rule_based',
                    'threshold_used': threshold
                }
            )
            
        except Exception as e:
            ml_logger.error(f"Error detecting {threat_type} threat: {str(e)}")
            return None

    async def _predict_with_ensemble(
        self, 
        threat_type: str, 
        feature_data: pd.DataFrame
    ) -> Tuple[float, int]:
        """Make prediction using ensemble of trained models"""
        try:
            # Scale features
            X_scaled = self.scalers[threat_type].transform(feature_data)
            
            # Get predictions from all models in ensemble
            predictions = []
            confidences = []
            
            for name, model in self.models[threat_type]:
                try:
                    pred_proba = model.predict_proba(X_scaled)
                    if pred_proba.shape[1] > 1:  # Multi-class
                        confidence = np.max(pred_proba[0])
                        prediction = np.argmax(pred_proba[0])
                    else:  # Binary
                        confidence = pred_proba[0][1] if pred_proba.shape[1] > 1 else pred_proba[0][0]
                        prediction = 1 if confidence > 0.5 else 0
                    
                    predictions.append(prediction)
                    confidences.append(confidence)
                except Exception as e:
                    ml_logger.warning(f"Model {name} prediction failed: {str(e)}")
            
            if not confidences:
                return 0.0, 1
            
            # Ensemble voting
            avg_confidence = np.mean(confidences)
            avg_prediction = np.mean(predictions)
            
            # Convert to severity (1-5)
            severity = max(1, min(5, int(avg_confidence * 5) + 1))
            
            return float(avg_confidence), severity
            
        except Exception as e:
            ml_logger.error(f"Ensemble prediction error: {str(e)}")
            return 0.0, 1

    def _rule_based_detection(
        self, 
        threat_type: str, 
        feature_data: pd.DataFrame,
        available_features: List[str]
    ) -> Tuple[float, int]:
        """Rule-based threat detection when models aren't trained"""
        try:
            latest_data = feature_data.iloc[-1] if not feature_data.empty else pd.Series()
            confidence = 0.0
            severity = 1
            
            if threat_type == 'storm':
                wind_speed = latest_data.get('wind_speed', 0)
                pressure = latest_data.get('pressure', 1013)
                
                if wind_speed > 118:  # Hurricane force
                    confidence = 0.95
                    severity = 5
                elif wind_speed > 88:  # Severe storm
                    confidence = 0.85
                    severity = 4
                elif wind_speed > 62:  # Strong winds
                    confidence = 0.75
                    severity = 3
                elif wind_speed > 39:  # Moderate winds
                    confidence = 0.65
                    severity = 2
                
                # Pressure drop indicates storm development
                if pressure < 980:
                    confidence = min(confidence + 0.15, 1.0)
                    severity = min(severity + 1, 5)
                    
            elif threat_type == 'pollution':
                pm25 = latest_data.get('pm25', 0)
                pm10 = latest_data.get('pm10', 0)
                
                if pm25 > 75:  # Very unhealthy
                    confidence = 0.90
                    severity = 5
                elif pm25 > 55:  # Unhealthy
                    confidence = 0.80
                    severity = 4
                elif pm25 > 35:  # Unhealthy for sensitive
                    confidence = 0.70
                    severity = 3
                elif pm25 > 25:  # Moderate
                    confidence = 0.60
                    severity = 2
                
                # Consider PM10 as well
                if pm10 > 150:
                    confidence = max(confidence, 0.80)
                    severity = max(severity, 4)
                    
            elif threat_type == 'algal_bloom':
                water_temp = latest_data.get('water_temperature', 20)
                visibility = latest_data.get('visibility', 10)
                salinity = latest_data.get('salinity', 35)
                
                temp_factor = 0.0
                if water_temp > 28:
                    temp_factor = 0.4
                elif water_temp > 25:
                    temp_factor = 0.2
                
                visibility_factor = 0.0
                if visibility < 2:
                    visibility_factor = 0.5
                elif visibility < 5:
                    visibility_factor = 0.3
                
                salinity_factor = 0.0
                if 30 <= salinity <= 38:  # Optimal range for some harmful algae
                    salinity_factor = 0.2
                
                confidence = min(temp_factor + visibility_factor + salinity_factor, 1.0)
                severity = max(1, min(5, int(confidence * 5) + 1))
                
            elif threat_type == 'erosion':
                wave_height = latest_data.get('wave_height', 0)
                tide_level = latest_data.get('tide_level', 0)
                wind_speed = latest_data.get('wind_speed', 0)
                
                wave_factor = min(wave_height / 10.0, 1.0)  # Normalize to 0-1
                wind_factor = min(wind_speed / 100.0, 1.0)
                
                confidence = (wave_factor * 0.6) + (wind_factor * 0.4)
                severity = max(1, min(5, int(confidence * 4) + 1))
                
            elif threat_type == 'illegal_dumping':
                # This would typically use image analysis or other sensors
                # For now, use environmental indicators
                visibility = latest_data.get('visibility', 10)
                water_temp = latest_data.get('water_temperature', 20)
                
                if visibility < 3:  # Reduced visibility might indicate contamination
                    confidence = 0.60
                    severity = 3
            
            return float(confidence), severity
            
        except Exception as e:
            ml_logger.error(f"Rule-based detection error: {str(e)}")
            return 0.0, 1

    def _generate_threat_description(
        self, 
        threat_type: str, 
        severity: int, 
        confidence: float,
        features: List[str],
        feature_data: pd.DataFrame
    ) -> str:
        """Generate human-readable threat description"""
        try:
            latest_data = feature_data.iloc[-1] if not feature_data.empty else pd.Series()
            
            # Base descriptions by threat type and severity
            base_descriptions = {
                'storm': {
                    5: "Extreme storm conditions with life-threatening winds and potential for catastrophic damage",
                    4: "Severe storm with dangerous winds causing significant property damage and power outages",
                    3: "Strong storm conditions with potential for property damage and hazardous conditions",
                    2: "Moderate storm with elevated winds and potential travel disruptions",
                    1: "Light storm conditions with minor weather impacts"
                },
                'pollution': {
                    5: "Hazardous air quality posing immediate health risks to all populations",
                    4: "Very unhealthy air quality requiring protective measures for all individuals",
                    3: "Unhealthy air quality particularly dangerous for sensitive groups",
                    2: "Moderate air quality concerns for sensitive individuals",
                    1: "Slight air quality degradation with minimal health impact"
                },
                'algal_bloom': {
                    5: "Severe harmful algal bloom with toxic conditions - avoid all water contact",
                    4: "Significant algal bloom development with potential health risks",
                    3: "Moderate algal bloom activity affecting water quality",
                    2: "Early algal bloom development detected",
                    1: "Conditions favorable for algal bloom formation"
                },
                'erosion': {
                    5: "Extreme coastal erosion threatening infrastructure and safety",
                    4: "Severe erosion with significant land loss and structural risks",
                    3: "Active erosion causing notable coastal changes",
                    2: "Moderate erosion activity detected",
                    1: "Minor erosion indicators present"
                },
                'illegal_dumping': {
                    5: "Major illegal dumping event with severe environmental contamination",
                    4: "Significant illegal dumping detected requiring immediate response",
                    3: "Moderate illegal dumping activity identified",
                    2: "Potential illegal dumping indicators observed",
                    1: "Minor environmental anomalies suggesting possible dumping"
                }
            }
            
            base_desc = base_descriptions.get(threat_type, {}).get(severity, 
                f"{threat_type.title()} threat detected with severity level {severity}")
            
            # Add specific measurements if available
            measurements = []
            if 'wind_speed' in latest_data and latest_data['wind_speed'] > 0:
                measurements.append(f"wind speed {latest_data['wind_speed']:.1f} km/h")
            if 'pm25' in latest_data and latest_data['pm25'] > 0:
                measurements.append(f"PM2.5 {latest_data['pm25']:.1f} μg/m³")
            if 'wave_height' in latest_data and latest_data['wave_height'] > 0:
                measurements.append(f"wave height {latest_data['wave_height']:.1f} m")
            if 'water_temperature' in latest_data and latest_data['water_temperature'] > 0:
                measurements.append(f"water temperature {latest_data['water_temperature']:.1f}°C")
            
            if measurements:
                measurement_text = "Current conditions: " + ", ".join(measurements[:3])
                return f"{base_desc}. {measurement_text}. Confidence: {confidence:.1%}"
            
            return f"{base_desc}. Confidence: {confidence:.1%}"
            
        except Exception as e:
            ml_logger.error(f"Error generating description: {str(e)}")
            return f"{threat_type.title()} threat detected (severity {severity}, confidence {confidence:.1%})"

    async def get_model_info(self, threat_type: str = None) -> Dict[str, Any]:
        """Get information about trained models"""
        try:
            if threat_type:
                if threat_type not in self.models:
                    return {}
                
                return {
                    'threat_type': threat_type,
                    'is_trained': self.is_trained[threat_type],
                    'features': self.feature_columns[threat_type],
                    'confidence_threshold': self.confidence_thresholds[threat_type],
                    'metrics': self.model_metrics.get(threat_type, {}),
                    'model_count': len(self.models[threat_type]) if isinstance(self.models[threat_type], list) else 0
                }
            else:
                return {
                    'total_models': len(self.models),
                    'trained_models': sum(self.is_trained.values()),
                    'model_details': {
                        t: {
                            'is_trained': self.is_trained[t],
                            'feature_count': len(self.feature_columns[t]),
                            'threshold': self.confidence_thresholds[t]
                        } for t in self.models.keys()
                    },
                    'overall_metrics': self.model_metrics
                }
                
        except Exception as e:
            ml_logger.error(f"Error getting model info: {str(e)}")
            return {}

# Global instance
threat_detector = ThreatDetectionEngine()