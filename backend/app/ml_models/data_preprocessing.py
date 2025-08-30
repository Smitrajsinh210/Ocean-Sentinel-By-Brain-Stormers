"""
Ocean Sentinel - Data Preprocessing Module
Advanced preprocessing pipeline for environmental data
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_regression
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import from our existing codebase
from . import ML_MODEL_CONFIG, ml_logger

@dataclass
class PreprocessingResult:
    """Result of data preprocessing operation"""
    processed_data: pd.DataFrame
    feature_names: List[str]
    scaling_info: Dict[str, Any]
    quality_metrics: Dict[str, float]
    transformations_applied: List[str]
    missing_data_summary: Dict[str, int]
    outliers_detected: Dict[str, int]
    processing_time_ms: int

class DataPreprocessor:
    """
    Comprehensive data preprocessing pipeline for environmental data
    Handles missing values, outliers, feature scaling, and transformation
    """
    
    def __init__(self):
        self.scalers = {}
        self.feature_selector = None
        self.is_fitted = False
        
        # Configuration from ML_MODEL_CONFIG
        self.config = ML_MODEL_CONFIG.get('preprocessing', {})
        self.normalization_method = self.config.get('normalization_method', 'robust_scaler')
        self.missing_value_strategy = self.config.get('missing_value_strategy', 'interpolation')
        self.feature_selection = self.config.get('feature_selection', 'automated')
        
        # Data quality thresholds
        self.quality_thresholds = {
            'missing_data_ratio': 0.3,  # 30% max missing data
            'outlier_ratio': 0.1,       # 10% max outliers
            'variance_threshold': 0.01,  # Minimum variance
            'correlation_threshold': 0.95  # Max correlation between features
        }
        
        # Parameter mappings and units
        self.parameter_mappings = {
            'temp': 'temperature',
            'air_temp': 'temperature',
            'water_temp': 'water_temperature',
            'sea_temp': 'water_temperature',
            'rh': 'humidity',
            'relative_humidity': 'humidity',
            'wspd': 'wind_speed',
            'wind': 'wind_speed',
            'wdir': 'wind_direction',
            'pres': 'pressure',
            'atm_pressure': 'pressure',
            'vis': 'visibility',
            'wave': 'wave_height',
            'tide': 'tide_level',
            'sal': 'salinity',
            'o3': 'ozone',
            'no2': 'nitrogen_dioxide',
            'so2': 'sulfur_dioxide',
            'co': 'carbon_monoxide'
        }
        
        # Valid ranges for environmental parameters
        self.parameter_ranges = {
            'temperature': (-50, 60),      # Celsius
            'water_temperature': (-5, 40),  # Celsius
            'humidity': (0, 100),          # Percentage
            'pressure': (900, 1100),       # hPa
            'wind_speed': (0, 200),        # km/h
            'wind_direction': (0, 360),    # degrees
            'visibility': (0, 50),         # km
            'wave_height': (0, 30),        # meters
            'tide_level': (-5, 5),         # meters
            'salinity': (0, 45),           # psu
            'pm25': (0, 500),              # μg/m³
            'pm10': (0, 1000),             # μg/m³
            'ozone': (0, 300),             # ppb
            'nitrogen_dioxide': (0, 200),  # ppb
            'sulfur_dioxide': (0, 100),    # ppb
            'carbon_monoxide': (0, 50)     # ppm
        }
        
        ml_logger.info("DataPreprocessor initialized")

    async def prepare_features(
        self,
        raw_data: List[Dict[str, Any]],
        target_variable: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Main preprocessing pipeline
        """
        start_time = datetime.now()
        
        try:
            if not raw_data:
                ml_logger.warning("No raw data provided for preprocessing")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(raw_data)
            
            if df.empty:
                ml_logger.warning("Empty DataFrame after conversion")
                return pd.DataFrame()
            
            # Step 1: Data cleaning and standardization
            df = await self._clean_and_standardize(df)
            
            # Step 2: Handle missing values
            df = await self._handle_missing_values(df)
            
            # Step 3: Detect and handle outliers
            df = await self._handle_outliers(df)
            
            # Step 4: Feature engineering
            df = await self._engineer_features(df)
            
            # Step 5: Feature scaling/normalization
            df = await self._scale_features(df)
            
            # Step 6: Feature selection (if enabled)
            if self.feature_selection != 'none' and target_variable and target_variable in df.columns:
                df = await self._select_features(df, target_variable)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            ml_logger.info(f"Preprocessing completed in {processing_time}ms, output shape: {df.shape}")
            
            return df
            
        except Exception as e:
            ml_logger.error(f"Error in data preprocessing: {str(e)}")
            return pd.DataFrame()

    async def _clean_and_standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize column names and data types"""
        try:
            # Standardize column names
            df.columns = [self._standardize_column_name(col) for col in df.columns]
            
            # Map parameter names to standard names
            rename_mapping = {}
            for col in df.columns:
                if col in self.parameter_mappings:
                    rename_mapping[col] = self.parameter_mappings[col]
            
            df = df.rename(columns=rename_mapping)
            
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
                
                # Clean column names again after pivot
                df.columns = [self._standardize_column_name(col) for col in df.columns]
            
            # Convert data types
            for col in df.columns:
                if col in ['timestamp', 'created_at', 'updated_at']:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                elif col in ['location', 'lat', 'lng', 'latitude', 'longitude']:
                    continue  # Handle spatial data separately
                else:
                    # Try to convert to numeric
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove completely empty columns
            df = df.dropna(axis=1, how='all')
            
            # Filter valid parameter ranges
            for col in df.select_dtypes(include=[np.number]).columns:
                if col in self.parameter_ranges:
                    min_val, max_val = self.parameter_ranges[col]
                    # Set outliers to NaN for later handling
                    df.loc[(df[col] < min_val) | (df[col] > max_val), col] = np.nan
            
            ml_logger.info(f"Cleaned data shape: {df.shape}")
            return df
            
        except Exception as e:
            ml_logger.error(f"Error in data cleaning: {str(e)}")
            return df

    def _standardize_column_name(self, column_name: str) -> str:
        """Standardize column names"""
        # Convert to lowercase and replace spaces/special chars with underscores
        standardized = str(column_name).lower().strip()
        standardized = standardized.replace(' ', '_').replace('-', '_').replace('.', '_')
        # Remove multiple underscores
        while '__' in standardized:
            standardized = standardized.replace('__', '_')
        # Remove leading/trailing underscores
        return standardized.strip('_')

    async def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values using various strategies"""
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return df
            
            missing_summary = df[numeric_cols].isnull().sum()
            total_missing = missing_summary.sum()
            
            if total_missing == 0:
                return df
            
            ml_logger.info(f"Handling {total_missing} missing values across {len(numeric_cols)} columns")
            
            if self.missing_value_strategy == 'interpolation':
                # Time-based interpolation for time series data
                if 'timestamp' in df.columns:
                    df = df.sort_values('timestamp')
                    for col in numeric_cols:
                        if df[col].isnull().any():
                            df[col] = df[col].interpolate(method='linear', limit_direction='both')
                else:
                    # Forward/backward fill
                    for col in numeric_cols:
                        if df[col].isnull().any():
                            df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
            
            elif self.missing_value_strategy == 'mean':
                # Mean imputation
                for col in numeric_cols:
                    if df[col].isnull().any():
                        mean_val = df[col].mean()
                        df[col] = df[col].fillna(mean_val)
            
            elif self.missing_value_strategy == 'median':
                # Median imputation (robust to outliers)
                for col in numeric_cols:
                    if df[col].isnull().any():
                        median_val = df[col].median()
                        df[col] = df[col].fillna(median_val)
            
            # Final check - drop rows with still missing critical values
            remaining_missing = df[numeric_cols].isnull().sum().sum()
            if remaining_missing > 0:
                ml_logger.warning(f"{remaining_missing} missing values remain after imputation")
                # Fill remaining with 0
                df[numeric_cols] = df[numeric_cols].fillna(0)
            
            return df
            
        except Exception as e:
            ml_logger.error(f"Error handling missing values: {str(e)}")
            return df

    async def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect and handle outliers"""
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return df
            
            outliers_detected = {}
            
            for col in numeric_cols:
                values = df[col].dropna()
                if len(values) < 10:  # Need sufficient data
                    continue
                
                # Method 1: IQR method
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                iqr_outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
                
                # Method 2: Z-score method
                z_scores = np.abs(stats.zscore(values))
                zscore_outliers = z_scores > 3
                
                # Combine methods
                outlier_mask = iqr_outliers | df[col].isin(values[zscore_outliers])
                outlier_count = outlier_mask.sum()
                
                if outlier_count > 0:
                    outliers_detected[col] = outlier_count
                    
                    # Handle outliers based on severity
                    outlier_ratio = outlier_count / len(df)
                    
                    if outlier_ratio > self.quality_thresholds['outlier_ratio']:
                        # Too many outliers - cap at percentiles
                        lower_cap = values.quantile(0.05)
                        upper_cap = values.quantile(0.95)
                        df[col] = df[col].clip(lower=lower_cap, upper=upper_cap)
                        ml_logger.info(f"Capped {outlier_count} outliers in {col}")
                    else:
                        # Few outliers - set to median
                        median_val = values.median()
                        df.loc[outlier_mask, col] = median_val
                        ml_logger.info(f"Replaced {outlier_count} outliers in {col}")
            
            total_outliers = sum(outliers_detected.values())
            if total_outliers > 0:
                ml_logger.info(f"Handled {total_outliers} outliers across {len(outliers_detected)} parameters")
            
            return df
            
        except Exception as e:
            ml_logger.error(f"Error handling outliers: {str(e)}")
            return df

    async def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create engineered features from raw data"""
        try:
            # Time-based features
            if 'timestamp' in df.columns:
                df['hour'] = df['timestamp'].dt.hour
                df['day_of_week'] = df['timestamp'].dt.dayofweek
                df['month'] = df['timestamp'].dt.month
                df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
                
                # Cyclical encoding for time features
                df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
                df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
                df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
                df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            
            # Weather-related derived features
            if 'temperature' in df.columns and 'humidity' in df.columns:
                # Heat index calculation (simplified)
                df['heat_index'] = df['temperature'] + (0.33 * df['humidity']) - 0.7
            
            if 'wind_speed' in df.columns and 'wind_direction' in df.columns:
                # Wind components
                df['wind_u'] = -df['wind_speed'] * np.sin(np.radians(df['wind_direction']))
                df['wind_v'] = -df['wind_speed'] * np.cos(np.radians(df['wind_direction']))
            
            if 'temperature' in df.columns and 'pressure' in df.columns:
                # Density altitude approximation
                df['density_altitude'] = df['temperature'] - (df['pressure'] - 1013.25) / 3.6
            
            # Air quality index calculation
            if 'pm25' in df.columns:
                df['aqi_pm25'] = self._calculate_aqi_pm25(df['pm25'])
            
            if 'pm10' in df.columns:
                df['aqi_pm10'] = self._calculate_aqi_pm10(df['pm10'])
            
            # Ocean-related features
            if 'wave_height' in df.columns and 'wind_speed' in df.columns:
                # Wave energy proxy
                df['wave_energy'] = df['wave_height'] ** 2 * df['wind_speed']
            
            ml_logger.info(f"Feature engineering completed, new shape: {df.shape}")
            return df
            
        except Exception as e:
            ml_logger.error(f"Error in feature engineering: {str(e)}")
            return df

    def _calculate_aqi_pm25(self, pm25_values: pd.Series) -> pd.Series:
        """Calculate AQI for PM2.5"""
        def pm25_to_aqi(pm25):
            if pd.isna(pm25):
                return np.nan
            
            breakpoints = [
                (0, 12.0, 0, 50),
                (12.1, 35.4, 51, 100),
                (35.5, 55.4, 101, 150),
                (55.5, 150.4, 151, 200),
                (150.5, 250.4, 201, 300),
                (250.5, 350.4, 301, 400)
            ]
            
            for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
                if bp_lo <= pm25 <= bp_hi:
                    aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo
                    return round(aqi)
            
            return 500  # Hazardous
        
        return pm25_values.apply(pm25_to_aqi)

    def _calculate_aqi_pm10(self, pm10_values: pd.Series) -> pd.Series:
        """Calculate AQI for PM10"""
        def pm10_to_aqi(pm10):
            if pd.isna(pm10):
                return np.nan
            
            breakpoints = [
                (0, 54, 0, 50),
                (55, 154, 51, 100),
                (155, 254, 101, 150),
                (255, 354, 151, 200),
                (355, 424, 201, 300),
                (425, 504, 301, 400)
            ]
            
            for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
                if bp_lo <= pm10 <= bp_hi:
                    aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm10 - bp_lo) + aqi_lo
                    return round(aqi)
            
            return 500  # Hazardous
        
        return pm10_values.apply(pm10_to_aqi)

    async def _scale_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scale numerical features"""
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) == 0:
                return df
            
            # Choose scaler based on configuration
            if self.normalization_method == 'standard_scaler':
                scaler = StandardScaler()
            elif self.normalization_method == 'robust_scaler':
                scaler = RobustScaler()
            elif self.normalization_method == 'min_max_scaler':
                scaler = MinMaxScaler()
            else:
                # No scaling
                return df
            
            # Fit and transform
            scaled_data = scaler.fit_transform(df[numeric_cols])
            
            # Replace original columns with scaled versions
            df[numeric_cols] = scaled_data
            
            # Store scaler for later use
            self.scalers['main'] = scaler
            
            ml_logger.info(f"Scaled {len(numeric_cols)} features using {self.normalization_method}")
            return df
            
        except Exception as e:
            ml_logger.error(f"Error in feature scaling: {str(e)}")
            return df

    async def _select_features(self, df: pd.DataFrame, target_variable: str) -> pd.DataFrame:
        """Select most relevant features"""
        try:
            if target_variable not in df.columns:
                ml_logger.warning(f"Target variable {target_variable} not found")
                return df
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            feature_cols = [col for col in numeric_cols if col != target_variable]
            
            if len(feature_cols) < 2:
                return df
            
            X = df[feature_cols].fillna(0)
            y = df[target_variable].fillna(0)
            
            # Remove features with zero variance
            X = X.loc[:, X.var() > self.quality_thresholds['variance_threshold']]
            
            # Remove highly correlated features
            corr_matrix = X.corr().abs()
            upper_tri = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )
            to_drop = [
                column for column in upper_tri.columns 
                if any(upper_tri[column] > self.quality_thresholds['correlation_threshold'])
            ]
            X = X.drop(columns=to_drop)
            
            if len(X.columns) > 20:  # Too many features
                # Use statistical feature selection
                k_best = min(15, len(X.columns))
                selector = SelectKBest(score_func=f_regression, k=k_best)
                X_selected = selector.fit_transform(X, y)
                selected_features = X.columns[selector.get_support()]
                
                # Keep only selected features
                df = df[[target_variable] + list(selected_features)]
                
                ml_logger.info(f"Selected {len(selected_features)} features from {len(feature_cols)}")
            else:
                # Keep all remaining features
                df = df[[target_variable] + list(X.columns)]
            
            return df
            
        except Exception as e:
            ml_logger.error(f"Error in feature selection: {str(e)}")
            return df

    async def get_data_quality_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate data quality report"""
        try:
            report = {
                'shape': df.shape,
                'columns': list(df.columns),
                'data_types': df.dtypes.to_dict(),
                'missing_values': df.isnull().sum().to_dict(),
                'missing_percentage': (df.isnull().sum() / len(df) * 100).to_dict(),
                'duplicate_rows': df.duplicated().sum(),
                'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024
            }
            
            # Numeric column statistics
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                report['numeric_stats'] = df[numeric_cols].describe().to_dict()
                
                # Data quality scores
                quality_scores = {}
                for col in numeric_cols:
                    missing_ratio = df[col].isnull().sum() / len(df)
                    variance = df[col].var()
                    
                    # Simple quality score (0-100)
                    score = 100
                    score -= missing_ratio * 50  # Penalize missing data
                    score -= (1 - min(variance / 10, 1)) * 20  # Penalize low variance
                    
                    quality_scores[col] = max(0, score)
                
                report['quality_scores'] = quality_scores
                report['overall_quality_score'] = np.mean(list(quality_scores.values()))
            
            return report
            
        except Exception as e:
            ml_logger.error(f"Error generating data quality report: {str(e)}")
            return {'error': str(e)}

    def get_preprocessing_config(self) -> Dict[str, Any]:
        """Get current preprocessing configuration"""
        return {
            'normalization_method': self.normalization_method,
            'missing_value_strategy': self.missing_value_strategy,
            'feature_selection': self.feature_selection,
            'quality_thresholds': self.quality_thresholds,
            'parameter_ranges': self.parameter_ranges,
            'is_fitted': self.is_fitted,
            'available_scalers': list(self.scalers.keys())
        }

# Global instance
data_preprocessor = DataPreprocessor()