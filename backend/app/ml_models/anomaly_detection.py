"""
Ocean Sentinel - Anomaly Detection System
Real-time environmental anomaly detection using multiple algorithms
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.covariance import EllipticEnvelope
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import from our existing codebase
from . import ML_MODEL_CONFIG, ml_logger

@dataclass
class AnomalyResult:
    """Result of anomaly detection analysis"""
    is_anomaly: bool
    anomaly_score: float
    severity: int
    confidence: float
    affected_parameters: List[str]
    detection_method: str
    baseline_comparison: Dict[str, float]
    description: str
    recommendations: List[str]
    metadata: Dict[str, Any]

class AnomalyDetector:
    """
    Multi-algorithm anomaly detection system for environmental data
    Detects unusual patterns that may indicate emerging threats
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.baseline_stats = {}
        self.is_trained = False
        
        # Configuration from ML_MODEL_CONFIG
        self.config = ML_MODEL_CONFIG.get('anomaly_detection', {})
        self.window_size = self.config.get('window_size', 24)  # hours
        self.contamination = self.config.get('contamination', 0.1)
        self.algorithms = self.config.get('algorithms', ['isolation_forest', 'local_outlier_factor'])
        
        # Anomaly thresholds
        self.severity_thresholds = {
            'low': 0.6,
            'medium': 0.75, 
            'high': 0.85,
            'critical': 0.95
        }
        
        # Parameter importance for anomaly scoring
        self.parameter_weights = {
            'temperature': 1.0,
            'pressure': 1.2,
            'wind_speed': 1.1,
            'humidity': 0.8,
            'pm25': 1.3,
            'pm10': 1.2,
            'ozone': 1.1,
            'water_temperature': 1.0,
            'salinity': 0.9,
            'wave_height': 1.0,
            'tide_level': 0.8,
            'visibility': 0.9
        }
        
        ml_logger.info("AnomalyDetector initialized")

    async def initialize_models(self):
        """Initialize anomaly detection models"""
        try:
            # Initialize multiple anomaly detection algorithms
            self.models = {
                'isolation_forest': IsolationForest(
                    contamination=self.contamination,
                    random_state=42,
                    n_jobs=1
                ),
                'local_outlier_factor': LocalOutlierFactor(
                    contamination=self.contamination,
                    n_jobs=1
                ),
                'one_class_svm': OneClassSVM(
                    gamma='scale',
                    nu=self.contamination
                ),
                'elliptic_envelope': EllipticEnvelope(
                    contamination=self.contamination,
                    random_state=42
                )
            }
            
            # Initialize scalers
            self.scalers = {
                'standard': StandardScaler(),
                'robust': RobustScaler()
            }
            
            ml_logger.info(f"Initialized {len(self.models)} anomaly detection models")
            return True
            
        except Exception as e:
            ml_logger.error(f"Error initializing anomaly models: {str(e)}")
            return False

    async def detect_anomalies(
        self,
        current_data: List[Dict[str, Any]],
        historical_data: Optional[List[Dict[str, Any]]] = None,
        location: Optional[Dict[str, float]] = None
    ) -> AnomalyResult:
        """
        Detect anomalies in current environmental data
        """
        try:
            start_time = datetime.now()
            
            # Preprocess current data
            current_df = self._prepare_features(current_data)
            if current_df.empty:
                return self._create_empty_result("No valid data for anomaly detection")
            
            # If no historical data provided and models not trained, use statistical approach
            if historical_data is None and not self.is_trained:
                return await self._statistical_anomaly_detection(current_df, location, start_time)
            
            # Use ML models if available
            if self.is_trained or historical_data:
                return await self._ml_anomaly_detection(
                    current_df, historical_data, location, start_time
                )
            
            return self._create_empty_result("Insufficient data for anomaly detection")
            
        except Exception as e:
            ml_logger.error(f"Error in anomaly detection: {str(e)}")
            return self._create_empty_result(f"Detection error: {str(e)}")

    def _prepare_features(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare features from environmental data"""
        try:
            if not data:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Handle different data structures
            if 'data_type' in df.columns and 'value' in df.columns:
                # Pivot data if it's in long format
                df_pivoted = df.pivot_table(
                    index=df.index if 'timestamp' not in df.columns else 'timestamp',
                    columns='data_type', 
                    values='value', 
                    aggfunc='mean'
                ).reset_index()
                df = df_pivoted
            
            # Clean column names
            df.columns = [str(col).lower().replace(' ', '_') for col in df.columns]
            
            # Select only numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                return pd.DataFrame()
            
            # Fill missing values
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
            
            return df[numeric_cols]
            
        except Exception as e:
            ml_logger.error(f"Error preparing features: {str(e)}")
            return pd.DataFrame()

    async def _statistical_anomaly_detection(
        self,
        current_data: pd.DataFrame,
        location: Optional[Dict[str, float]],
        start_time: datetime
    ) -> AnomalyResult:
        """Statistical anomaly detection using z-scores and IQR"""
        try:
            anomalies = []
            anomaly_scores = {}
            affected_parameters = []
            
            # Calculate statistics for each parameter
            for column in current_data.select_dtypes(include=[np.number]).columns:
                values = current_data[column].dropna()
                if len(values) == 0:
                    continue
                
                # Z-score analysis
                z_scores = np.abs(stats.zscore(values))
                z_anomalies = z_scores > 3.0  # 3-sigma rule
                
                # IQR analysis
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_anomalies = (values < lower_bound) | (values > upper_bound)
                
                # Combined anomaly score
                anomaly_count = np.sum(z_anomalies | iqr_anomalies)
                anomaly_ratio = anomaly_count / len(values)
                
                # Weight by parameter importance
                weight = self.parameter_weights.get(column, 1.0)
                weighted_score = anomaly_ratio * weight
                
                anomaly_scores[column] = {
                    'z_score_anomalies': int(np.sum(z_anomalies)),
                    'iqr_anomalies': int(np.sum(iqr_anomalies)),
                    'anomaly_ratio': float(anomaly_ratio),
                    'weighted_score': float(weighted_score),
                    'max_z_score': float(np.max(z_scores)),
                    'latest_value': float(values.iloc[-1]) if len(values) > 0 else 0.0
                }
                
                if weighted_score > 0.3:  # Threshold for considering parameter anomalous
                    affected_parameters.append(column)
                    anomalies.append(weighted_score)
            
            # Overall anomaly assessment
            overall_score = np.mean(anomalies) if anomalies else 0.0
            is_anomaly = overall_score > 0.5
            
            # Determine severity
            severity = self._calculate_severity(overall_score)
            confidence = min(overall_score * 2, 1.0)  # Convert to confidence
            
            # Generate description and recommendations
            description = self._generate_anomaly_description(
                overall_score, affected_parameters, anomaly_scores
            )
            recommendations = self._generate_recommendations(
                affected_parameters, anomaly_scores, severity
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return AnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=round(overall_score, 4),
                severity=severity,
                confidence=round(confidence, 4),
                affected_parameters=affected_parameters,
                detection_method="statistical",
                baseline_comparison=anomaly_scores,
                description=description,
                recommendations=recommendations,
                metadata={
                    'location': location,
                    'processing_time_ms': processing_time,
                    'data_points': len(current_data),
                    'parameters_analyzed': len(anomaly_scores)
                }
            )
            
        except Exception as e:
            ml_logger.error(f"Statistical anomaly detection error: {str(e)}")
            return self._create_empty_result(f"Statistical detection error: {str(e)}")

    async def _ml_anomaly_detection(
        self,
        current_data: pd.DataFrame,
        historical_data: Optional[List[Dict[str, Any]]],
        location: Optional[Dict[str, float]],
        start_time: datetime
    ) -> AnomalyResult:
        """ML-based anomaly detection using trained models"""
        try:
            # Prepare historical data if provided
            if historical_data and not self.is_trained:
                await self._train_on_historical_data(historical_data)
            
            # Select numeric columns for analysis
            numeric_columns = current_data.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) == 0:
                return self._create_empty_result("No numeric data for ML detection")
            
            # Prepare feature matrix
            X_current = current_data[numeric_columns].fillna(current_data[numeric_columns].mean())
            
            # Scale features
            X_scaled = self.scalers['robust'].transform(X_current)
            
            # Get predictions from each model
            model_results = {}
            anomaly_scores = []
            
            for model_name, model in self.models.items():
                try:
                    if model_name == 'local_outlier_factor':
                        # LOF requires fit_predict
                        if not hasattr(model, 'negative_outlier_factor_'):
                            continue  # Skip if not fitted
                        predictions = model._predict(X_scaled)
                        scores = -model.negative_outlier_factor_[-len(X_scaled):]
                    else:
                        predictions = model.predict(X_scaled)
                        if hasattr(model, 'decision_function'):
                            scores = -model.decision_function(X_scaled)  # Convert to positive scores
                        else:
                            scores = np.array([1.0] * len(predictions))  # Default score
                    
                    # Convert predictions to boolean anomalies
                    anomalies = predictions == -1
                    anomaly_count = np.sum(anomalies)
                    anomaly_ratio = anomaly_count / len(predictions)
                    avg_score = np.mean(scores) if len(scores) > 0 else 0.0
                    
                    model_results[model_name] = {
                        'anomaly_count': int(anomaly_count),
                        'anomaly_ratio': float(anomaly_ratio),
                        'avg_score': float(avg_score),
                        'max_score': float(np.max(scores)) if len(scores) > 0 else 0.0
                    }
                    
                    anomaly_scores.append(anomaly_ratio)
                    
                except Exception as e:
                    ml_logger.warning(f"Model {model_name} prediction failed: {str(e)}")
                    continue
            
            # Ensemble results
            if not anomaly_scores:
                return self._create_empty_result("No model predictions available")
            
            overall_score = np.mean(anomaly_scores)
            is_anomaly = overall_score > 0.1  # At least 10% of points anomalous
            
            # Determine severity and confidence
            severity = self._calculate_severity(overall_score * 5)  # Scale for severity
            confidence = min(overall_score * 3, 1.0)
            
            # Identify affected parameters
            affected_parameters = self._identify_affected_parameters(
                current_data, X_scaled, numeric_columns
            )
            
            # Generate description and recommendations
            description = self._generate_ml_anomaly_description(
                overall_score, affected_parameters, model_results
            )
            recommendations = self._generate_recommendations(
                affected_parameters, model_results, severity
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return AnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=round(overall_score, 4),
                severity=severity,
                confidence=round(confidence, 4),
                affected_parameters=affected_parameters,
                detection_method="ensemble_ml",
                baseline_comparison=model_results,
                description=description,
                recommendations=recommendations,
                metadata={
                    'location': location,
                    'processing_time_ms': processing_time,
                    'models_used': len(model_results),
                    'data_points': len(current_data)
                }
            )
            
        except Exception as e:
            ml_logger.error(f"ML anomaly detection error: {str(e)}")
            return self._create_empty_result(f"ML detection error: {str(e)}")

    async def _train_on_historical_data(self, historical_data: List[Dict[str, Any]]):
        """Train anomaly detection models on historical data"""
        try:
            # Preprocess historical data
            hist_df = self._prepare_features(historical_data)
            if hist_df.empty:
                return False
            
            # Select numeric columns
            numeric_columns = hist_df.select_dtypes(include=[np.number]).columns
            X_hist = hist_df[numeric_columns].fillna(hist_df[numeric_columns].mean())
            
            # Fit scalers
            X_scaled = self.scalers['robust'].fit_transform(X_hist)
            
            # Train models
            trained_models = {}
            for model_name, model in self.models.items():
                try:
                    if model_name == 'local_outlier_factor':
                        # LOF needs fit_predict
                        model.fit_predict(X_scaled)
                    else:
                        model.fit(X_scaled)
                    
                    trained_models[model_name] = model
                    ml_logger.info(f"Trained {model_name} on {len(X_hist)} historical samples")
                    
                except Exception as e:
                    ml_logger.warning(f"Failed to train {model_name}: {str(e)}")
            
            if trained_models:
                self.models = trained_models
                self.is_trained = True
                
                # Save baseline statistics
                self.baseline_stats = {
                    'mean': X_hist.mean().to_dict(),
                    'std': X_hist.std().to_dict(),
                    'min': X_hist.min().to_dict(),
                    'max': X_hist.max().to_dict(),
                    'q25': X_hist.quantile(0.25).to_dict(),
                    'q75': X_hist.quantile(0.75).to_dict()
                }
                
                return True
            
            return False
            
        except Exception as e:
            ml_logger.error(f"Error training on historical data: {str(e)}")
            return False

    def _identify_affected_parameters(
        self, 
        current_data: pd.DataFrame, 
        X_scaled: np.ndarray, 
        columns: List[str]
    ) -> List[str]:
        """Identify which parameters are most anomalous"""
        try:
            affected = []
            
            if not self.baseline_stats:
                return list(columns)  # Return all if no baseline
            
            for i, col in enumerate(columns):
                current_values = current_data[col].dropna()
                if len(current_values) == 0:
                    continue
                
                latest_value = current_values.iloc[-1]
                
                # Compare with baseline statistics
                baseline_mean = self.baseline_stats.get('mean', {}).get(col, 0)
                baseline_std = self.baseline_stats.get('std', {}).get(col, 1)
                baseline_min = self.baseline_stats.get('min', {}).get(col, 0)
                baseline_max = self.baseline_stats.get('max', {}).get(col, 0)
                
                # Calculate z-score from baseline
                if baseline_std > 0:
                    z_score = abs((latest_value - baseline_mean) / baseline_std)
                    
                    # Check if significantly different from baseline
                    if (z_score > 2.0 or 
                        latest_value < baseline_min * 0.8 or 
                        latest_value > baseline_max * 1.2):
                        affected.append(col)
            
            return affected
            
        except Exception as e:
            ml_logger.error(f"Error identifying affected parameters: {str(e)}")
            return []

    def _calculate_severity(self, score: float) -> int:
        """Calculate severity level from anomaly score"""
        if score >= self.severity_thresholds['critical']:
            return 5
        elif score >= self.severity_thresholds['high']:
            return 4
        elif score >= self.severity_thresholds['medium']:
            return 3
        elif score >= self.severity_thresholds['low']:
            return 2
        else:
            return 1

    def _generate_anomaly_description(
        self, 
        score: float, 
        affected_params: List[str],
        param_scores: Dict[str, Any]
    ) -> str:
        """Generate human-readable anomaly description"""
        try:
            if score < 0.3:
                return "Environmental conditions are within normal ranges."
            
            severity_desc = {
                1: "Minor",
                2: "Moderate", 
                3: "Significant",
                4: "Severe",
                5: "Critical"
            }
            
            severity = self._calculate_severity(score)
            severity_text = severity_desc.get(severity, "Unknown")
            
            if not affected_params:
                return f"{severity_text} environmental anomaly detected (score: {score:.2f})"
            
            param_text = ", ".join(affected_params[:3])
            if len(affected_params) > 3:
                param_text += f" and {len(affected_params) - 3} other parameters"
            
            return f"{severity_text} anomaly detected in {param_text}. " \
                   f"Anomaly score: {score:.2f}. Immediate investigation recommended."
            
        except Exception as e:
            ml_logger.error(f"Error generating description: {str(e)}")
            return f"Environmental anomaly detected (score: {score:.2f})"

    def _generate_ml_anomaly_description(
        self,
        score: float,
        affected_params: List[str], 
        model_results: Dict[str, Any]
    ) -> str:
        """Generate description for ML-based anomaly detection"""
        try:
            severity = self._calculate_severity(score * 5)
            severity_desc = ["Normal", "Minor", "Moderate", "Significant", "Severe", "Critical"][severity]
            
            model_count = len([r for r in model_results.values() if r['anomaly_ratio'] > 0.1])
            
            desc = f"{severity_desc} environmental anomaly detected by {model_count} ML models. "
            
            if affected_params:
                param_text = ", ".join(affected_params[:3])
                desc += f"Parameters affected: {param_text}. "
            
            desc += f"Anomaly score: {score:.3f}"
            
            return desc
            
        except Exception as e:
            ml_logger.error(f"Error generating ML description: {str(e)}")
            return f"ML-based anomaly detected (score: {score:.3f})"

    def _generate_recommendations(
        self, 
        affected_params: List[str],
        scores: Dict[str, Any], 
        severity: int
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        try:
            if severity >= 4:
                recommendations.append("URGENT: Initiate emergency response protocols")
                recommendations.append("Evacuate affected areas if necessary")
                recommendations.append("Contact relevant authorities immediately")
            elif severity >= 3:
                recommendations.append("Increase monitoring frequency")
                recommendations.append("Deploy additional sensors to affected area")
                recommendations.append("Notify emergency management teams")
            elif severity >= 2:
                recommendations.append("Continue monitoring conditions")
                recommendations.append("Verify sensor readings and data quality")
                
            # Parameter-specific recommendations
            for param in affected_params[:3]:  # Top 3 affected parameters
                if 'temperature' in param.lower():
                    recommendations.append("Monitor for heat stress or unusual cooling patterns")
                elif 'pressure' in param.lower():
                    recommendations.append("Check for approaching weather systems")
                elif any(p in param.lower() for p in ['pm25', 'pm10', 'ozone']):
                    recommendations.append("Issue air quality advisories")
                elif 'wind' in param.lower():
                    recommendations.append("Monitor for storm development")
                elif 'water' in param.lower():
                    recommendations.append("Test water quality and check for contamination")
                elif 'wave' in param.lower() or 'tide' in param.lower():
                    recommendations.append("Monitor coastal conditions and erosion risk")
            
            # General recommendations
            recommendations.append("Document and report anomaly findings")
            recommendations.append("Review historical data for similar patterns")
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            ml_logger.error(f"Error generating recommendations: {str(e)}")
            return ["Investigate anomaly and monitor conditions"]

    def _create_empty_result(self, message: str) -> AnomalyResult:
        """Create empty result for error cases"""
        return AnomalyResult(
            is_anomaly=False,
            anomaly_score=0.0,
            severity=1,
            confidence=0.0,
            affected_parameters=[],
            detection_method="none",
            baseline_comparison={},
            description=message,
            recommendations=["Ensure data quality and system functionality"],
            metadata={'error': message}
        )

    async def get_model_status(self) -> Dict[str, Any]:
        """Get current status of anomaly detection models"""
        try:
            return {
                'is_trained': self.is_trained,
                'models_available': list(self.models.keys()),
                'baseline_parameters': list(self.baseline_stats.get('mean', {}).keys()) if self.baseline_stats else [],
                'configuration': {
                    'window_size_hours': self.window_size,
                    'contamination_rate': self.contamination,
                    'algorithms_enabled': self.algorithms
                },
                'thresholds': self.severity_thresholds,
                'parameter_weights': self.parameter_weights
            }
        except Exception as e:
            ml_logger.error(f"Error getting model status: {str(e)}")
            return {'error': str(e)}

# Global instance
anomaly_detector = AnomalyDetector()