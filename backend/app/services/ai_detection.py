"""
Ocean Sentinel - AI Threat Detection Service
Machine learning models for environmental threat detection
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4
import json

from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pandas as pd

from app.config import settings, THREAT_TYPES
from app.utils.database import create_supabase_client
from app.models.threats import ThreatCreate

logger = logging.getLogger(__name__)

class ThreatDetectionAI:
    """Advanced AI threat detection system using ensemble models"""
    
    def __init__(self):
        self.supabase = create_supabase_client()
        self.models = {}
        self.scalers = {}
        self.is_initialized = False
        
        # Threat detection thresholds
        self.confidence_threshold = settings.threat_confidence_threshold
        
        # Model configurations
        self.model_configs = {
            'storm': {
                'features': ['temperature', 'pressure', 'wind_speed', 'humidity', 'precipitation'],
                'thresholds': THREAT_TYPES['storm']['severity_thresholds'],
                'model_type': 'ensemble'
            },
            'pollution': {
                'features': ['pm2_5', 'pm10', 'no2', 'so2', 'co', 'o3', 'aqi'],
                'thresholds': THREAT_TYPES['pollution']['severity_thresholds'],
                'model_type': 'classification'
            },
            'erosion': {
                'features': ['wave_height', 'wind_speed', 'water_level', 'current_speed'],
                'thresholds': THREAT_TYPES['erosion']['severity_thresholds'],
                'model_type': 'ensemble'
            },
            'algal_bloom': {
                'features': ['water_temperature', 'ph', 'dissolved_oxygen', 'turbidity'],
                'thresholds': THREAT_TYPES['algal_bloom']['severity_thresholds'],
                'model_type': 'anomaly'
            },
            'illegal_dumping': {
                'features': ['chemical_anomaly', 'visual_anomaly', 'pollution_spike'],
                'thresholds': THREAT_TYPES['illegal_dumping']['severity_thresholds'],
                'model_type': 'anomaly'
            }
        }
    
    async def load_models(self) -> bool:
        """Load or initialize AI models for threat detection"""
        try:
            logger.info("🤖 Loading AI threat detection models...")
            
            for threat_type, config in self.model_configs.items():
                model_type = config['model_type']
                
                if model_type == 'ensemble':
                    # Create ensemble model (Random Forest + Isolation Forest)
                    classifier = RandomForestClassifier(
                        n_estimators=100,
                        max_depth=10,
                        random_state=42
                    )
                    anomaly_detector = IsolationForest(
                        contamination=0.1,
                        random_state=42
                    )
                    
                    self.models[threat_type] = {
                        'classifier': classifier,
                        'anomaly_detector': anomaly_detector,
                        'type': 'ensemble'
                    }
                    
                elif model_type == 'classification':
                    # Classification model for pollution
                    classifier = RandomForestClassifier(
                        n_estimators=150,
                        max_depth=15,
                        random_state=42
                    )
                    
                    self.models[threat_type] = {
                        'classifier': classifier,
                        'type': 'classification'
                    }
                    
                elif model_type == 'anomaly':
                    # Anomaly detection model
                    anomaly_detector = IsolationForest(
                        contamination=0.15,
                        random_state=42
                    )
                    
                    self.models[threat_type] = {
                        'anomaly_detector': anomaly_detector,
                        'type': 'anomaly'
                    }
                
                # Initialize scaler for each threat type
                self.scalers[threat_type] = StandardScaler()
                
                logger.info(f"✅ {threat_type.title()} model initialized")
            
            # Train models with synthetic data (in production, use real historical data)
            await self._train_models_with_synthetic_data()
            
            self.is_initialized = True
            logger.info("✅ All AI models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load AI models: {e}")
            return False
    
    async def detect_threats(self, environmental_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect threats from environmental data using AI models
        Args:
            environmental_data: Environmental data from multiple sources
        Returns:
            List of detected threats
        """
        if not self.is_initialized:
            logger.warning("AI models not initialized")
            return []
        
        try:
            logger.info("🔍 Running AI threat detection analysis...")
            detected_threats = []
            
            # Extract and process data for each location
            locations_data = self._extract_location_data(environmental_data)
            
            for location_name, location_data in locations_data.items():
                # Run detection for each threat type
                for threat_type in self.model_configs.keys():
                    threats = await self._detect_threat_type(
                        threat_type, location_data, location_name
                    )
                    detected_threats.extend(threats)
            
            # Filter by confidence threshold
            high_confidence_threats = [
                threat for threat in detected_threats 
                if threat['confidence'] >= self.confidence_threshold
            ]
            
            logger.info(f"🎯 Detected {len(high_confidence_threats)} high-confidence threats")
            
            # Store threats in database
            stored_threats = []
            for threat in high_confidence_threats:
                stored_threat = await self._store_threat(threat)
                if stored_threat:
                    stored_threats.append(stored_threat)
            
            return stored_threats
            
        except Exception as e:
            logger.error(f"Error in threat detection: {e}")
            return []
    
    async def _detect_threat_type(
        self, 
        threat_type: str, 
        location_data: Dict[str, Any], 
        location_name: str
    ) -> List[Dict[str, Any]]:
        """Detect specific threat type for a location"""
        try:
            model_config = self.model_configs[threat_type]
            features = model_config['features']
            
            # Extract feature values
            feature_values = self._extract_features(location_data, features)
            
            if not feature_values:
                return []
            
            # Prepare feature array
            X = np.array([list(feature_values.values())]).reshape(1, -1)
            
            # Scale features
            if threat_type in self.scalers:
                X_scaled = self.scalers[threat_type].transform(X)
            else:
                X_scaled = X
            
            # Get model
            model = self.models[threat_type]
            model_type = model['type']
            
            threats = []
            
            if model_type == 'ensemble':
                # Use both classifier and anomaly detector
                classifier_pred = model['classifier'].predict_proba(X_scaled)[0]
                anomaly_score = model['anomaly_detector'].decision_function(X_scaled)[0]
                
                # Combine predictions
                threat_prob = max(classifier_pred) if len(classifier_pred) > 1 else classifier_pred[0]
                anomaly_confidence = (anomaly_score + 1) / 2  # Normalize to 0-1
                
                combined_confidence = (threat_prob + anomaly_confidence) / 2
                
                if combined_confidence > 0.5:
                    severity = self._calculate_severity(threat_type, feature_values, combined_confidence)
                    threat = self._create_threat_object(
                        threat_type, location_data, location_name, 
                        severity, combined_confidence, feature_values
                    )
                    threats.append(threat)
            
            elif model_type == 'classification':
                # Use classifier only
                prediction_proba = model['classifier'].predict_proba(X_scaled)[0]
                confidence = max(prediction_proba)
                
                if confidence > 0.6:
                    severity = self._calculate_severity(threat_type, feature_values, confidence)
                    threat = self._create_threat_object(
                        threat_type, location_data, location_name,
                        severity, confidence, feature_values
                    )
                    threats.append(threat)
            
            elif model_type == 'anomaly':
                # Use anomaly detector only
                anomaly_score = model['anomaly_detector'].decision_function(X_scaled)[0]
                anomaly_confidence = (anomaly_score + 1) / 2
                
                if anomaly_confidence > 0.7:  # Higher threshold for anomalies
                    severity = self._calculate_severity(threat_type, feature_values, anomaly_confidence)
                    threat = self._create_threat_object(
                        threat_type, location_data, location_name,
                        severity, anomaly_confidence, feature_values
                    )
                    threats.append(threat)
            
            return threats
            
        except Exception as e:
            logger.error(f"Error detecting {threat_type} threat: {e}")
            return []
    
    def _extract_location_data(self, environmental_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract and organize environmental data by location"""
        locations_data = {}
        
        try:
            # Process data from different sources
            for source_type, source_data in environmental_data.items():
                if isinstance(source_data, list):
                    for record in source_data:
                        location_name = record.get('location_name', 'Unknown')
                        
                        if location_name not in locations_data:
                            locations_data[location_name] = {
                                'latitude': record.get('latitude'),
                                'longitude': record.get('longitude'),
                                'timestamp': record.get('timestamp'),
                                'data': {}
                            }
                        
                        # Merge data from different sources
                        record_data = record.get('data', {})
                        locations_data[location_name]['data'].update(record_data)
            
            return locations_data
            
        except Exception as e:
            logger.error(f"Error extracting location data: {e}")
            return {}
    
    def _extract_features(self, location_data: Dict[str, Any], features: List[str]) -> Dict[str, float]:
        """Extract specific features from location data"""
        feature_values = {}
        data = location_data.get('data', {})
        
        for feature in features:
            value = data.get(feature)
            if value is not None:
                try:
                    feature_values[feature] = float(value)
                except (ValueError, TypeError):
                    # Handle non-numeric values
                    if feature == 'aqi' and isinstance(value, str):
                        # Convert AQI categories to numbers
                        aqi_map = {'Good': 50, 'Moderate': 100, 'Unhealthy for Sensitive Groups': 150,
                                  'Unhealthy': 200, 'Very Unhealthy': 250, 'Hazardous': 300}
                        feature_values[feature] = aqi_map.get(value, 100)
                    else:
                        logger.warning(f"Could not convert {feature} value: {value}")
        
        return feature_values
    
    def _calculate_severity(self, threat_type: str, features: Dict[str, float], confidence: float) -> int:
        """Calculate threat severity based on features and thresholds"""
        try:
            thresholds = self.model_configs[threat_type]['thresholds']
            
            # Start with base severity from confidence
            base_severity = min(5, max(1, int(confidence * 5)))
            
            # Adjust based on feature thresholds
            max_severity = 1
            
            for severity_level in range(1, 6):
                if str(severity_level) in thresholds:
                    level_thresholds = thresholds[str(severity_level)]
                    meets_threshold = True
                    
                    for param, threshold_value in level_thresholds.items():
                        if param in features:
                            if features[param] < threshold_value:
                                meets_threshold = False
                                break
                    
                    if meets_threshold:
                        max_severity = severity_level
            
            # Return the higher of confidence-based or threshold-based severity
            return max(base_severity, max_severity)
            
        except Exception as e:
            logger.error(f"Error calculating severity: {e}")
            return min(5, max(1, int(confidence * 5)))
    
    def _create_threat_object(
        self, 
        threat_type: str, 
        location_data: Dict[str, Any], 
        location_name: str,
        severity: int, 
        confidence: float, 
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """Create threat object with all required fields"""
        
        # Generate description based on threat type and severity
        description = self._generate_threat_description(threat_type, severity, features)
        
        # Generate recommendations
        recommendation = self._generate_recommendations(threat_type, severity)
        
        # Estimate impact
        estimated_impact, affected_population = self._estimate_impact(threat_type, severity, location_name)
        
        threat = {
            'id': str(uuid4()),
            'type': threat_type,
            'severity': severity,
            'confidence': confidence,
            'latitude': location_data.get('latitude'),
            'longitude': location_data.get('longitude'),
            'description': description,
            'estimated_impact': estimated_impact,
            'affected_population': affected_population,
            'recommendation': recommendation,
            'timestamp': datetime.utcnow().isoformat(),
            'location_name': location_name,
            'raw_features': features,
            'data_sources': ['ai_detection']
        }
        
        return threat
    
    def _generate_threat_description(self, threat_type: str, severity: int, features: Dict[str, float]) -> str:
        """Generate human-readable threat description"""
        severity_text = ['Minor', 'Moderate', 'Significant', 'Dangerous', 'Extreme'][severity - 1]
        
        descriptions = {
            'storm': f"{severity_text} storm conditions detected with ",
            'pollution': f"{severity_text} air pollution levels detected with ",
            'erosion': f"{severity_text} coastal erosion risk identified with ",
            'algal_bloom': f"{severity_text} algal bloom conditions detected with ",
            'illegal_dumping': f"{severity_text} environmental contamination anomaly detected with "
        }
        
        base_desc = descriptions.get(threat_type, f"{severity_text} environmental threat detected")
        
        # Add specific feature details
        feature_details = []
        
        if threat_type == 'storm':
            if 'wind_speed' in features:
                feature_details.append(f"wind speeds of {features['wind_speed']:.1f} m/s")
            if 'pressure' in features:
                feature_details.append(f"pressure at {features['pressure']:.1f} hPa")
        
        elif threat_type == 'pollution':
            if 'pm2_5' in features:
                feature_details.append(f"PM2.5 at {features['pm2_5']:.1f} µg/m³")
            if 'aqi' in features:
                feature_details.append(f"AQI of {features['aqi']:.0f}")
        
        elif threat_type == 'erosion':
            if 'wave_height' in features:
                feature_details.append(f"wave height of {features['wave_height']:.1f}m")
            if 'water_level' in features:
                feature_details.append(f"elevated water levels")
        
        if feature_details:
            base_desc += " and ".join(feature_details[:2])  # Limit to 2 details
        else:
            base_desc += "multiple environmental indicators"
        
        return base_desc + "."
    
    def _generate_recommendations(self, threat_type: str, severity: int) -> str:
        """Generate action recommendations based on threat type and severity"""
        recommendations = {
            'storm': {
                1: "Monitor weather conditions and avoid unnecessary outdoor activities",
                2: "Secure loose objects and avoid coastal areas during high tide",
                3: "Avoid all water activities and secure property. Consider evacuation preparation",
                4: "Evacuate coastal areas immediately. Seek shelter in sturdy buildings",
                5: "IMMEDIATE EVACUATION required. This is a life-threatening emergency"
            },
            'pollution': {
                1: "Limit prolonged outdoor activities for sensitive individuals",
                2: "Reduce outdoor activities and consider wearing masks",
                3: "Avoid outdoor activities. Keep windows closed and use air purifiers",
                4: "Stay indoors. Seek medical attention if experiencing breathing difficulties",
                5: "EMERGENCY: Stay indoors with sealed windows. Seek immediate medical help if affected"
            },
            'erosion': {
                1: "Avoid cliff edges and unstable coastal structures",
                2: "Stay away from beaches and coastal walkways during high tide",
                3: "Evacuate beachfront properties and avoid all coastal areas",
                4: "IMMEDIATE evacuation of all coastal areas. Risk of structural collapse",
                5: "EMERGENCY EVACUATION of entire coastal zone. Extreme risk to life and property"
            },
            'algal_bloom': {
                1: "Avoid contact with discolored water. Do not consume local seafood",
                2: "No swimming or water activities. Avoid eating locally caught fish",
                3: "Complete water activity ban. Boil all tap water before consumption",
                4: "Water emergency protocols in effect. Seek alternative water sources",
                5: "CRITICAL water contamination. Evacuate if dependent on local water supply"
            },
            'illegal_dumping': {
                1: "Report suspicious activities to environmental authorities",
                2: "Avoid the affected area and report to emergency services",
                3: "Area quarantine recommended. Contact hazmat response teams",
                4: "IMMEDIATE area evacuation. This is a hazmat emergency",
                5: "EXTREME HAZMAT situation. Full emergency response and evacuation required"
            }
        }
        
        return recommendations.get(threat_type, {}).get(
            severity, 
            "Monitor the situation closely and follow local emergency guidelines"
        )
    
    def _estimate_impact(self, threat_type: str, severity: int, location_name: str) -> Tuple[str, int]:
        """Estimate threat impact and affected population"""
        
        # Population estimates for major coastal areas (simplified)
        population_estimates = {
            'NYC Harbor': 500000,
            'LA Coast': 300000,
            'Miami Beach': 150000,
            'Seattle Port': 200000,
            'Boston Harbor': 250000,
            'San Francisco Bay': 400000,
            'Galveston Bay': 100000,
            'Chesapeake Bay': 80000
        }
        
        base_population = population_estimates.get(location_name, 50000)
        
        # Impact multipliers by severity and threat type
        impact_multipliers = {
            'storm': [0.1, 0.3, 0.6, 0.8, 1.0],
            'pollution': [0.2, 0.4, 0.6, 0.8, 1.0],
            'erosion': [0.05, 0.15, 0.3, 0.5, 0.7],
            'algal_bloom': [0.1, 0.25, 0.4, 0.6, 0.8],
            'illegal_dumping': [0.15, 0.3, 0.5, 0.7, 0.9]
        }
        
        multiplier = impact_multipliers.get(threat_type, [0.1, 0.2, 0.4, 0.6, 0.8])[severity - 1]
        affected_population = int(base_population * multiplier)
        
        # Impact descriptions
        impact_levels = [
            "Minimal local impact expected",
            "Moderate local disruption possible", 
            "Significant regional impact likely",
            "Major regional emergency situation",
            "Catastrophic widespread emergency"
        ]
        
        estimated_impact = impact_levels[severity - 1]
        
        return estimated_impact, affected_population
    
    async def _store_threat(self, threat_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Store detected threat in database"""
        try:
            # Create threat record
            threat_record = {
                'id': threat_data['id'],
                'type': threat_data['type'],
                'severity': threat_data['severity'],
                'confidence': threat_data['confidence'],
                'location': f"POINT({threat_data['longitude']} {threat_data['latitude']})",
                'description': threat_data['description'],
                'estimated_impact': threat_data['estimated_impact'],
                'affected_population': threat_data['affected_population'],
                'recommendation': threat_data['recommendation'],
                'timestamp': threat_data['timestamp'],
                'data_sources': threat_data['data_sources'],
                'raw_features': threat_data['raw_features']
            }
            
            result = await self.supabase.table('threats').insert(threat_record).execute()
            
            if result.data:
                logger.info(f"✅ Threat stored: {threat_data['type']} (severity {threat_data['severity']})")
                return result.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to store threat: {e}")
            return None
    
    async def _train_models_with_synthetic_data(self):
        """Train models with synthetic data (replace with real historical data in production)"""
        try:
            logger.info("🎓 Training AI models with synthetic data...")
            
            for threat_type, model in self.models.items():
                # Generate synthetic training data
                X_train, y_train = self._generate_synthetic_training_data(threat_type, 1000)
                
                if X_train is not None and len(X_train) > 0:
                    # Fit scaler
                    self.scalers[threat_type].fit(X_train)
                    X_train_scaled = self.scalers[threat_type].transform(X_train)
                    
                    # Train models based on type
                    if model['type'] == 'ensemble':
                        model['classifier'].fit(X_train_scaled, y_train)
                        model['anomaly_detector'].fit(X_train_scaled)
                    elif model['type'] == 'classification':
                        model['classifier'].fit(X_train_scaled, y_train)
                    elif model['type'] == 'anomaly':
                        model['anomaly_detector'].fit(X_train_scaled)
                    
                    logger.info(f"✅ {threat_type.title()} model trained")
            
            logger.info("✅ All models trained successfully")
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
    
    def _generate_synthetic_training_data(self, threat_type: str, n_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for threat detection models"""
        try:
            config = self.model_configs[threat_type]
            features = config['features']
            n_features = len(features)
            
            # Create feature ranges based on threat type
            feature_ranges = self._get_feature_ranges(threat_type)
            
            # Generate normal data (no threat)
            normal_samples = int(n_samples * 0.7)
            X_normal = np.random.normal(0, 1, (normal_samples, n_features))
            y_normal = np.zeros(normal_samples)
            
            # Apply feature ranges to normal data
            for i, feature in enumerate(features):
                if feature in feature_ranges:
                    min_val, max_val = feature_ranges[feature]['normal']
                    X_normal[:, i] = np.random.uniform(min_val, max_val, normal_samples)
            
            # Generate threat data
            threat_samples = n_samples - normal_samples
            X_threat = np.random.normal(0, 1, (threat_samples, n_features))
            y_threat = np.ones(threat_samples)
            
            # Apply feature ranges to threat data
            for i, feature in enumerate(features):
                if feature in feature_ranges:
                    min_val, max_val = feature_ranges[feature]['threat']
                    X_threat[:, i] = np.random.uniform(min_val, max_val, threat_samples)
            
            # Combine data
            X = np.vstack([X_normal, X_threat])
            y = np.hstack([y_normal, y_threat])
            
            # Shuffle
            indices = np.random.permutation(len(X))
            X = X[indices]
            y = y[indices]
            
            return X, y
            
        except Exception as e:
            logger.error(f"Error generating synthetic data for {threat_type}: {e}")
            return None, None
    
    def _get_feature_ranges(self, threat_type: str) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """Get realistic feature ranges for synthetic data generation"""
        ranges = {
            'storm': {
                'temperature': {'normal': (10, 30), 'threat': (-5, 45)},
                'pressure': {'normal': (1000, 1020), 'threat': (950, 1040)},
                'wind_speed': {'normal': (0, 15), 'threat': (25, 60)},
                'humidity': {'normal': (30, 80), 'threat': (60, 100)},
                'precipitation': {'normal': (0, 5), 'threat': (10, 50)}
            },
            'pollution': {
                'pm2_5': {'normal': (0, 25), 'threat': (35, 150)},
                'pm10': {'normal': (0, 50), 'threat': (75, 250)},
                'no2': {'normal': (0, 40), 'threat': (50, 200)},
                'so2': {'normal': (0, 20), 'threat': (30, 100)},
                'co': {'normal': (0, 10), 'threat': (15, 50)},
                'o3': {'normal': (0, 100), 'threat': (120, 300)},
                'aqi': {'normal': (0, 100), 'threat': (150, 300)}
            },
            'erosion': {
                'wave_height': {'normal': (0, 2), 'threat': (3, 8)},
                'wind_speed': {'normal': (0, 20), 'threat': (30, 70)},
                'water_level': {'normal': (-1, 1), 'threat': (1.5, 5)},
                'current_speed': {'normal': (0, 1), 'threat': (1.5, 4)}
            },
            'algal_bloom': {
                'water_temperature': {'normal': (15, 25), 'threat': (28, 35)},
                'ph': {'normal': (7, 8.5), 'threat': (6, 9.5)},
                'dissolved_oxygen': {'normal': (6, 12), 'threat': (0, 4)},
                'turbidity': {'normal': (0, 10), 'threat': (20, 100)}
            },
            'illegal_dumping': {
                'chemical_anomaly': {'normal': (0, 0.3), 'threat': (0.7, 1.0)},
                'visual_anomaly': {'normal': (0, 0.2), 'threat': (0.6, 1.0)},
                'pollution_spike': {'normal': (0, 0.4), 'threat': (0.8, 1.0)}
            }
        }
        
        return ranges.get(threat_type, {})
    
    async def get_threat_predictions(self, location_data: Dict[str, Any]) -> Dict[str, float]:
        """Get threat probability predictions for a location"""
        if not self.is_initialized:
            return {}
        
        try:
            predictions = {}
            
            for threat_type in self.model_configs.keys():
                features = self.model_configs[threat_type]['features']
                feature_values = self._extract_features(location_data, features)
                
                if feature_values:
                    X = np.array([list(feature_values.values())]).reshape(1, -1)
                    X_scaled = self.scalers[threat_type].transform(X)
                    
                    model = self.models[threat_type]
                    
                    if model['type'] in ['ensemble', 'classification'] and 'classifier' in model:
                        proba = model['classifier'].predict_proba(X_scaled)[0]
                        predictions[threat_type] = max(proba) if len(proba) > 1 else proba[0]
                    elif model['type'] == 'anomaly':
                        score = model['anomaly_detector'].decision_function(X_scaled)[0]
                        predictions[threat_type] = (score + 1) / 2
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error getting predictions: {e}")
            return {}
