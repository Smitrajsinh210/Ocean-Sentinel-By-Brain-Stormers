"""
Ocean Sentinel - Prediction Models
Advanced time series prediction models for 2-4 hour threat forecasting
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import dataclass
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Import from our existing codebase
from . import ML_MODEL_CONFIG, ml_logger

@dataclass
class PredictionResult:
    """Result of threat prediction analysis"""
    predictions: Dict[str, List[float]]  # parameter: [values] for each forecast hour
    forecast_hours: List[int]  # [2, 4, 8, 24]
    confidence_intervals: Dict[str, List[Tuple[float, float]]]  # (lower, upper) bounds
    model_performance: Dict[str, float]  # accuracy metrics
    trend_analysis: Dict[str, str]  # increasing/decreasing/stable
    risk_assessment: Dict[str, int]  # severity level 1-5
    alerts_predicted: List[Dict[str, Any]]  # predicted threat conditions
    metadata: Dict[str, Any]

class ThreatPredictor:
    """
    Time series prediction system for environmental threat forecasting
    Provides 2-4 hour advance warning for coastal threats
    """
    
    def __init__(self):
        self.models = {}  # parameter -> forecast_hour -> model
        self.scalers = {}
        self.is_trained = {}
        self.model_performance = {}
        
        # Configuration from ML_MODEL_CONFIG
        self.config = ML_MODEL_CONFIG.get('prediction', {})
        self.forecast_horizons = self.config.get('forecast_horizon_hours', [2, 4, 8, 24])
        self.update_frequency = self.config.get('update_frequency_minutes', 15)
        self.min_data_points = self.config.get('minimum_data_points', 50)
        
        # Prediction parameters
        self.prediction_parameters = [
            'temperature', 'pressure', 'wind_speed', 'humidity',
            'pm25', 'pm10', 'ozone', 'water_temperature', 'wave_height',
            'tide_level', 'visibility', 'salinity'
        ]
        
        # Risk thresholds for each parameter
        self.risk_thresholds = {
            'wind_speed': [39, 62, 88, 118],  # km/h - levels 1-4
            'pressure': [1000, 990, 980, 970],  # hPa (descending)
            'pm25': [25, 35, 55, 75],  # μg/m³ 
            'pm10': [50, 100, 150, 250],  # μg/m³
            'wave_height': [2, 4, 6, 8],  # meters
            'temperature': [30, 35, 40, 45],  # °C (heat)
            'water_temperature': [25, 28, 30, 32],  # °C (algal bloom risk)
            'visibility': [5, 3, 2, 1]  # km (descending)
        }
        
        ml_logger.info("ThreatPredictor initialized")

    async def initialize_models(self):
        """Initialize prediction models for each parameter and forecast horizon"""
        try:
            for parameter in self.prediction_parameters:
                self.models[parameter] = {}
                self.scalers[parameter] = {}
                self.is_trained[parameter] = {}
                
                for forecast_hour in self.forecast_horizons:
                    # Create ensemble of models for each forecast horizon
                    ensemble = {
                        'linear': LinearRegression(),
                        'ridge': Ridge(alpha=1.0),
                        'random_forest': RandomForestRegressor(
                            n_estimators=50,
                            max_depth=10,
                            random_state=42,
                            n_jobs=1
                        ),
                        'gradient_boost': GradientBoostingRegressor(
                            n_estimators=50,
                            learning_rate=0.1,
                            random_state=42
                        ),
                        'neural_network': MLPRegressor(
                            hidden_layer_sizes=(50, 25),
                            max_iter=500,
                            random_state=42
                        )
                    }
                    
                    self.models[parameter][forecast_hour] = ensemble
                    self.scalers[parameter][forecast_hour] = StandardScaler()
                    self.is_trained[parameter][forecast_hour] = False
            
            ml_logger.info(f"Initialized prediction models for {len(self.prediction_parameters)} parameters")
            return True
            
        except Exception as e:
            ml_logger.error(f"Error initializing prediction models: {str(e)}")
            return False

    async def predict_threats(
        self,
        historical_data: List[Dict[str, Any]],
        location: Dict[str, float],
        forecast_hours: Optional[List[int]] = None
    ) -> PredictionResult:
        """
        Generate threat predictions for specified forecast horizons
        """
        try:
            start_time = datetime.now()
            forecast_hours = forecast_hours or self.forecast_horizons
            
            # Preprocess historical data
            df = self._prepare_features(historical_data)
            
            if df.empty or len(df) < self.min_data_points:
                return self._create_empty_prediction("Insufficient historical data")
            
            # Generate predictions for each parameter
            predictions = {}
            confidence_intervals = {}
            trend_analysis = {}
            risk_assessment = {}
            alerts_predicted = []
            
            for parameter in self.prediction_parameters:
                if parameter in df.columns:
                    param_predictions, param_confidence, param_trend, param_risk = await self._predict_parameter(
                        df, parameter, forecast_hours, location
                    )
                    
                    predictions[parameter] = param_predictions
                    confidence_intervals[parameter] = param_confidence
                    trend_analysis[parameter] = param_trend
                    risk_assessment[parameter] = param_risk
                    
                    # Check for potential alerts
                    for i, hour in enumerate(forecast_hours):
                        if param_predictions and i < len(param_predictions):
                            predicted_value = param_predictions[i]
                            severity = self._assess_threat_severity(parameter, predicted_value)
                            
                            if severity >= 3:  # Medium severity or higher
                                alerts_predicted.append({
                                    'parameter': parameter,
                                    'forecast_hour': hour,
                                    'predicted_value': predicted_value,
                                    'severity': severity,
                                    'confidence': param_confidence[i][1] - param_confidence[i][0] if param_confidence else 0.5,
                                    'description': self._generate_alert_description(parameter, predicted_value, severity, hour)
                                })
            
            # Calculate overall model performance
            overall_performance = await self._calculate_performance_metrics(predictions)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return PredictionResult(
                predictions=predictions,
                forecast_hours=forecast_hours,
                confidence_intervals=confidence_intervals,
                model_performance=overall_performance,
                trend_analysis=trend_analysis,
                risk_assessment=risk_assessment,
                alerts_predicted=alerts_predicted,
                metadata={
                    'location': location,
                    'processing_time_ms': processing_time,
                    'data_points_used': len(df),
                    'parameters_predicted': len(predictions),
                    'alerts_count': len(alerts_predicted)
                }
            )
            
        except Exception as e:
            ml_logger.error(f"Error in threat prediction: {str(e)}")
            return self._create_empty_prediction(f"Prediction error: {str(e)}")

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
            
            # Fill missing values with 0 (simple approach)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            
            # Sort by timestamp if available
            if 'timestamp' in df.columns:
                df = df.sort_values('timestamp')
            
            return df
            
        except Exception as e:
            ml_logger.error(f"Error preparing features: {str(e)}")
            return pd.DataFrame()

    async def _predict_parameter(
        self,
        df: pd.DataFrame,
        parameter: str,
        forecast_hours: List[int],
        location: Dict[str, float]
    ) -> Tuple[List[float], List[Tuple[float, float]], str, int]:
        """Predict single parameter for multiple forecast horizons"""
        try:
            predictions = []
            confidence_intervals = []
            
            # Prepare time series data
            values = df[parameter].dropna()
            if len(values) < 10:
                return [], [], "insufficient_data", 1
            
            # Create features for time series prediction
            X, y = self._create_time_series_features(values, max(forecast_hours))
            
            if len(X) == 0:
                return [], [], "insufficient_features", 1
            
            # Generate predictions for each forecast horizon
            for forecast_hour in forecast_hours:
                try:
                    # Check if models are trained for this parameter and forecast hour
                    if not self.is_trained.get(parameter, {}).get(forecast_hour, False):
                        # Train models if not already trained
                        await self._train_parameter_models(parameter, X, y, forecast_hour)
                    
                    # Get ensemble predictions
                    ensemble_predictions = []
                    models = self.models.get(parameter, {}).get(forecast_hour, {})
                    
                    if not models:
                        # Fallback to simple trend analysis
                        trend_pred = self._simple_trend_prediction(values, forecast_hour)
                        predictions.append(trend_pred)
                        confidence_intervals.append((trend_pred * 0.9, trend_pred * 1.1))
                        continue
                    
                    # Use latest data point for prediction
                    latest_features = X[-1:] if len(X) > 0 else np.array([[0] * X.shape[1]])
                    
                    for model_name, model in models.items():
                        try:
                            pred = model.predict(latest_features)[0]
                            ensemble_predictions.append(pred)
                        except Exception as e:
                            ml_logger.warning(f"Model {model_name} prediction failed: {str(e)}")
                    
                    if ensemble_predictions:
                        # Ensemble average
                        avg_prediction = np.mean(ensemble_predictions)
                        std_prediction = np.std(ensemble_predictions)
                        
                        predictions.append(avg_prediction)
                        confidence_intervals.append((
                            avg_prediction - 1.96 * std_prediction,
                            avg_prediction + 1.96 * std_prediction
                        ))
                    else:
                        # Fallback
                        last_value = values.iloc[-1]
                        predictions.append(last_value)
                        confidence_intervals.append((last_value * 0.95, last_value * 1.05))
                        
                except Exception as e:
                    ml_logger.error(f"Error predicting {parameter} for {forecast_hour}h: {str(e)}")
                    last_value = values.iloc[-1]
                    predictions.append(last_value)
                    confidence_intervals.append((last_value * 0.95, last_value * 1.05))
            
            # Analyze trend
            trend = self._analyze_trend(values, predictions)
            
            # Assess risk level
            max_predicted = max(predictions) if predictions else 0
            risk_level = self._assess_threat_severity(parameter, max_predicted)
            
            return predictions, confidence_intervals, trend, risk_level
            
        except Exception as e:
            ml_logger.error(f"Error predicting parameter {parameter}: {str(e)}")
            return [], [], "error", 1

    def _create_time_series_features(self, values: pd.Series, max_forecast_hour: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create features for time series prediction"""
        try:
            # Use sliding window approach
            window_size = min(24, len(values) // 3)  # Use up to 24 hours or 1/3 of data
            window_size = max(3, window_size)  # Minimum window size
            
            X, y = [], []
            
            for i in range(window_size, len(values) - max_forecast_hour):
                # Features: previous 'window_size' values + statistical features
                window = values.iloc[i-window_size:i]
                
                features = list(window.values)  # Historical values
                features.extend([
                    window.mean(),      # Mean
                    window.std(),       # Standard deviation
                    window.min(),       # Minimum
                    window.max(),       # Maximum
                    window.iloc[-1] - window.iloc[-2] if len(window) > 1 else 0,  # Last change
                    (window.iloc[-1] - window.iloc[0]) / len(window) if len(window) > 1 else 0  # Trend
                ])
                
                X.append(features)
                y.append(values.iloc[i + max_forecast_hour])  # Target value
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            ml_logger.error(f"Error creating time series features: {str(e)}")
            return np.array([]), np.array([])

    async def _train_parameter_models(
        self,
        parameter: str,
        X: np.ndarray,
        y: np.ndarray,
        forecast_hour: int
    ):
        """Train ensemble models for specific parameter and forecast horizon"""
        try:
            if len(X) < 10:  # Need minimum data
                return False
            
            # Split data for training
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = self.scalers[parameter][forecast_hour]
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train each model in ensemble
            trained_models = {}
            performance_scores = {}
            
            for model_name, model in self.models[parameter][forecast_hour].items():
                try:
                    model.fit(X_train_scaled, y_train)
                    
                    # Evaluate performance
                    y_pred = model.predict(X_test_scaled)
                    mse = mean_squared_error(y_test, y_pred)
                    mae = mean_absolute_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    
                    performance_scores[model_name] = {
                        'mse': mse,
                        'mae': mae,
                        'r2': r2
                    }
                    
                    trained_models[model_name] = model
                    ml_logger.info(f"Trained {model_name} for {parameter} ({forecast_hour}h): R²={r2:.3f}")
                    
                except Exception as e:
                    ml_logger.warning(f"Failed to train {model_name} for {parameter}: {str(e)}")
            
            if trained_models:
                self.models[parameter][forecast_hour] = trained_models
                self.is_trained[parameter][forecast_hour] = True
                
                if parameter not in self.model_performance:
                    self.model_performance[parameter] = {}
                self.model_performance[parameter][forecast_hour] = performance_scores
                
                return True
            
            return False
            
        except Exception as e:
            ml_logger.error(f"Error training models for {parameter}: {str(e)}")
            return False

    def _simple_trend_prediction(self, values: pd.Series, forecast_hour: int) -> float:
        """Simple trend-based prediction as fallback"""
        try:
            if len(values) < 2:
                return values.iloc[-1] if len(values) > 0 else 0.0
            
            # Linear trend
            recent_values = values.tail(min(12, len(values)))  # Last 12 points
            x = np.arange(len(recent_values))
            y = recent_values.values
            
            # Fit linear regression
            slope, intercept = np.polyfit(x, y, 1)
            
            # Predict
            prediction = slope * (len(recent_values) + forecast_hour) + intercept
            
            return float(prediction)
            
        except Exception as e:
            ml_logger.error(f"Error in simple trend prediction: {str(e)}")
            return values.iloc[-1] if len(values) > 0 else 0.0

    def _analyze_trend(self, historical_values: pd.Series, predictions: List[float]) -> str:
        """Analyze trend direction"""
        try:
            if len(predictions) == 0 or len(historical_values) == 0:
                return "unknown"
            
            current_value = historical_values.iloc[-1]
            future_value = predictions[-1]  # Furthest prediction
            
            change_percent = ((future_value - current_value) / current_value) * 100
            
            if abs(change_percent) < 5:
                return "stable"
            elif change_percent > 0:
                return "increasing"
            else:
                return "decreasing"
                
        except Exception as e:
            ml_logger.error(f"Error analyzing trend: {str(e)}")
            return "unknown"

    def _assess_threat_severity(self, parameter: str, value: float) -> int:
        """Assess threat severity based on parameter value"""
        try:
            if parameter not in self.risk_thresholds:
                return 1
            
            thresholds = self.risk_thresholds[parameter]
            
            # Special handling for descending thresholds (pressure, visibility)
            if parameter in ['pressure', 'visibility']:
                for i, threshold in enumerate(thresholds):
                    if value <= threshold:
                        return i + 2  # Severity 2-5
                return 1
            else:
                # Ascending thresholds
                severity = 1
                for i, threshold in enumerate(thresholds):
                    if value >= threshold:
                        severity = i + 2  # Severity 2-5
                return min(severity, 5)
            
        except Exception as e:
            ml_logger.error(f"Error assessing threat severity: {str(e)}")
            return 1

    def _generate_alert_description(
        self,
        parameter: str,
        predicted_value: float,
        severity: int,
        forecast_hour: int
    ) -> str:
        """Generate human-readable alert description"""
        try:
            severity_labels = {
                1: "Low",
                2: "Moderate", 
                3: "High",
                4: "Severe",
                5: "Extreme"
            }
            
            severity_text = severity_labels.get(severity, "Unknown")
            
            parameter_descriptions = {
                'wind_speed': f"{predicted_value:.1f} km/h winds",
                'pressure': f"{predicted_value:.1f} hPa pressure",
                'pm25': f"{predicted_value:.1f} μg/m³ PM2.5",
                'wave_height': f"{predicted_value:.1f}m wave height",
                'temperature': f"{predicted_value:.1f}°C temperature",
                'water_temperature': f"{predicted_value:.1f}°C water temperature"
            }
            
            param_desc = parameter_descriptions.get(parameter, f"{parameter}: {predicted_value:.2f}")
            
            return f"{severity_text} {parameter.replace('_', ' ')} predicted in {forecast_hour} hours: {param_desc}"
            
        except Exception as e:
            ml_logger.error(f"Error generating alert description: {str(e)}")
            return f"Alert predicted for {parameter} in {forecast_hour} hours"

    async def _calculate_performance_metrics(self, predictions: Dict[str, List[float]]) -> Dict[str, float]:
        """Calculate overall model performance metrics"""
        try:
            all_r2_scores = []
            all_mae_scores = []
            parameters_with_performance = 0
            
            for parameter in predictions.keys():
                if parameter in self.model_performance:
                    param_performance = self.model_performance[parameter]
                    
                    # Average across all forecast horizons
                    for forecast_hour, models_perf in param_performance.items():
                        for model_name, metrics in models_perf.items():
                            if 'r2' in metrics and 'mae' in metrics:
                                all_r2_scores.append(metrics['r2'])
                                all_mae_scores.append(metrics['mae'])
                                parameters_with_performance += 1
            
            if parameters_with_performance > 0:
                return {
                    'average_r2': np.mean(all_r2_scores),
                    'average_mae': np.mean(all_mae_scores),
                    'parameters_trained': parameters_with_performance,
                    'prediction_accuracy': max(0, min(100, np.mean(all_r2_scores) * 100))
                }
            else:
                return {
                    'average_r2': 0.0,
                    'average_mae': 0.0,
                    'parameters_trained': 0,
                    'prediction_accuracy': 0.0
                }
                
        except Exception as e:
            ml_logger.error(f"Error calculating performance metrics: {str(e)}")
            return {'error': str(e)}

    def _create_empty_prediction(self, message: str) -> PredictionResult:
        """Create empty prediction result for error cases"""
        return PredictionResult(
            predictions={},
            forecast_hours=self.forecast_horizons,
            confidence_intervals={},
            model_performance={'error': message},
            trend_analysis={},
            risk_assessment={},
            alerts_predicted=[],
            metadata={'error': message}
        )

    async def get_model_status(self) -> Dict[str, Any]:
        """Get current status of prediction models"""
        try:
            status = {
                'parameters': self.prediction_parameters,
                'forecast_horizons': self.forecast_horizons,
                'trained_models': {},
                'performance_summary': {},
                'configuration': {
                    'update_frequency_minutes': self.update_frequency,
                    'min_data_points': self.min_data_points
                }
            }
            
            # Count trained models
            total_trained = 0
            for parameter in self.prediction_parameters:
                param_trained = 0
                if parameter in self.is_trained:
                    for forecast_hour in self.forecast_horizons:
                        if self.is_trained[parameter].get(forecast_hour, False):
                            param_trained += 1
                            total_trained += 1
                
                status['trained_models'][parameter] = {
                    'total_horizons': len(self.forecast_horizons),
                    'trained_horizons': param_trained,
                    'training_complete': param_trained == len(self.forecast_horizons)
                }
            
            # Performance summary
            if self.model_performance:
                all_r2_scores = []
                for param_perf in self.model_performance.values():
                    for hour_perf in param_perf.values():
                        for model_perf in hour_perf.values():
                            if 'r2' in model_perf:
                                all_r2_scores.append(model_perf['r2'])
                
                if all_r2_scores:
                    status['performance_summary'] = {
                        'average_accuracy': np.mean(all_r2_scores),
                        'total_trained_models': total_trained,
                        'best_performance': max(all_r2_scores),
                        'worst_performance': min(all_r2_scores)
                    }
            
            return status
            
        except Exception as e:
            ml_logger.error(f"Error getting model status: {str(e)}")
            return {'error': str(e)}

# Global instance
threat_predictor = ThreatPredictor()