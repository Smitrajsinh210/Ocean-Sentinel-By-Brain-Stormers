"""
Ocean Sentinel - Environmental Data Ingestion Service
Multi-source environmental data collection with blockchain logging
"""

import asyncio
import aiohttp
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from app.config import settings, API_CONFIG
from app.utils.database import create_supabase_client
from app.utils.api_clients import (
    OpenWeatherClient, 
    OpenAQClient, 
    NOAAClient, 
    NASAClient
)
from app.services.blockchain import BlockchainService

logger = logging.getLogger(__name__)

class EnvironmentalDataService:
    """Comprehensive environmental data ingestion service"""
    
    def __init__(self):
        self.supabase = create_supabase_client()
        self.blockchain_service = BlockchainService()
        
        # Initialize API clients
        self.openweather_client = OpenWeatherClient()
        self.openaq_client = OpenAQClient()
        self.noaa_client = NOAAClient()
        self.nasa_client = NASAClient()
        
        # Default monitoring locations (can be configured)
        self.monitoring_locations = [
            {"name": "NYC Harbor", "lat": 40.7589, "lon": -73.9851},
            {"name": "LA Coast", "lat": 34.0522, "lon": -118.2437},
            {"name": "Miami Beach", "lat": 25.7617, "lon": -80.1918},
            {"name": "Seattle Port", "lat": 47.6062, "lon": -122.3321},
            {"name": "Boston Harbor", "lat": 42.3601, "lon": -71.0589},
            {"name": "San Francisco Bay", "lat": 37.7749, "lon": -122.4194},
            {"name": "Galveston Bay", "lat": 29.3013, "lon": -94.7977},
            {"name": "Chesapeake Bay", "lat": 39.1612, "lon": -76.2863}
        ]
    
    async def ingest_all_data(self) -> Optional[Dict[str, Any]]:
        """
        Comprehensive data ingestion from all sources
        Returns: Processed environmental data summary
        """
        try:
            logger.info("🔄 Starting comprehensive environmental data ingestion...")
            
            collection_id = str(uuid4())
            collection_start = datetime.utcnow()
            
            # Collect data from all sources in parallel
            data_sources = await asyncio.gather(
                self._collect_weather_data(),
                self._collect_air_quality_data(), 
                self._collect_ocean_data(),
                self._collect_satellite_data(),
                return_exceptions=True
            )
            
            # Process results
            weather_data, air_quality_data, ocean_data, satellite_data = data_sources
            
            # Count successful vs failed collections
            successful_sources = 0
            failed_sources = 0
            errors = []
            
            all_data = {}
            
            # Process weather data
            if isinstance(weather_data, Exception):
                failed_sources += 1
                errors.append(f"Weather data: {str(weather_data)}")
                logger.error(f"Weather data collection failed: {weather_data}")
            else:
                successful_sources += 1
                all_data['weather'] = weather_data
                logger.info(f"✅ Weather data collected: {len(weather_data)} locations")
            
            # Process air quality data
            if isinstance(air_quality_data, Exception):
                failed_sources += 1
                errors.append(f"Air quality data: {str(air_quality_data)}")
                logger.error(f"Air quality data collection failed: {air_quality_data}")
            else:
                successful_sources += 1
                all_data['air_quality'] = air_quality_data
                logger.info(f"✅ Air quality data collected: {len(air_quality_data)} locations")
            
            # Process ocean data
            if isinstance(ocean_data, Exception):
                failed_sources += 1
                errors.append(f"Ocean data: {str(ocean_data)}")
                logger.error(f"Ocean data collection failed: {ocean_data}")
            else:
                successful_sources += 1
                all_data['ocean'] = ocean_data
                logger.info(f"✅ Ocean data collected: {len(ocean_data)} locations")
            
            # Process satellite data
            if isinstance(satellite_data, Exception):
                failed_sources += 1
                errors.append(f"Satellite data: {str(satellite_data)}")
                logger.error(f"Satellite data collection failed: {satellite_data}")
            else:
                successful_sources += 1
                all_data['satellite'] = satellite_data
                logger.info(f"✅ Satellite data collected: {len(satellite_data)} locations")
            
            if successful_sources == 0:
                logger.error("❌ All data sources failed")
                return None
            
            # Create aggregated summary
            processed_data = await self._process_and_store_data(
                all_data, successful_sources, failed_sources, errors, collection_id
            )
            
            # Log to blockchain
            if processed_data:
                data_hash = self._generate_data_hash(processed_data)
                await self.blockchain_service.log_environmental_data(
                    data_hash, 
                    collection_start.isoformat(),
                    "multi_source_ingestion"
                )
                
                # Update summary with blockchain hash
                processed_data['blockchain_hash'] = data_hash
            
            collection_end = datetime.utcnow()
            collection_duration = (collection_end - collection_start).total_seconds()
            
            logger.info(f"✅ Data ingestion completed in {collection_duration:.2f}s")
            logger.info(f"📊 Success: {successful_sources}/{successful_sources + failed_sources} sources")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Critical error in data ingestion: {e}")
            return None
    
    async def _collect_weather_data(self) -> List[Dict[str, Any]]:
        """Collect weather data from OpenWeatherMap"""
        weather_data = []
        
        for location in self.monitoring_locations:
            try:
                data = await self.openweather_client.get_current_weather(
                    location['lat'], location['lon']
                )
                
                if data:
                    processed = {
                        'source': 'openweather',
                        'location_name': location['name'],
                        'latitude': location['lat'],
                        'longitude': location['lon'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': data,
                        'quality_score': self._assess_data_quality(data, 'weather')
                    }
                    weather_data.append(processed)
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to collect weather data for {location['name']}: {e}")
        
        return weather_data
    
    async def _collect_air_quality_data(self) -> List[Dict[str, Any]]:
        """Collect air quality data from OpenAQ"""
        air_quality_data = []
        
        for location in self.monitoring_locations:
            try:
                data = await self.openaq_client.get_air_quality(
                    location['lat'], location['lon']
                )
                
                if data:
                    processed = {
                        'source': 'openaq',
                        'location_name': location['name'],
                        'latitude': location['lat'],
                        'longitude': location['lon'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': data,
                        'quality_score': self._assess_data_quality(data, 'air_quality')
                    }
                    air_quality_data.append(processed)
                
                # Rate limiting
                await asyncio.sleep(6)  # OpenAQ has stricter limits
                
            except Exception as e:
                logger.warning(f"Failed to collect air quality data for {location['name']}: {e}")
        
        return air_quality_data
    
    async def _collect_ocean_data(self) -> List[Dict[str, Any]]:
        """Collect ocean/tidal data from NOAA"""
        ocean_data = []
        
        # NOAA stations near our monitoring locations
        noaa_stations = [
            {"name": "The Battery, NY", "station_id": "8518750", "lat": 40.7, "lon": -74.0},
            {"name": "Los Angeles, CA", "station_id": "9410660", "lat": 34.0, "lon": -118.2},
            {"name": "Virginia Key, FL", "station_id": "8723214", "lat": 25.7, "lon": -80.2},
            {"name": "Seattle, WA", "station_id": "9447130", "lat": 47.6, "lon": -122.3}
        ]
        
        for station in noaa_stations:
            try:
                data = await self.noaa_client.get_tidal_data(station['station_id'])
                
                if data:
                    processed = {
                        'source': 'noaa',
                        'location_name': station['name'],
                        'latitude': station['lat'],
                        'longitude': station['lon'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': data,
                        'quality_score': self._assess_data_quality(data, 'ocean'),
                        'station_id': station['station_id']
                    }
                    ocean_data.append(processed)
                
                # Rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Failed to collect ocean data for {station['name']}: {e}")
        
        return ocean_data
    
    async def _collect_satellite_data(self) -> List[Dict[str, Any]]:
        """Collect satellite imagery data from NASA"""
        satellite_data = []
        
        # Sample key locations for satellite data
        key_locations = self.monitoring_locations[:4]  # Limit to avoid quota issues
        
        for location in key_locations:
            try:
                data = await self.nasa_client.get_earth_imagery(
                    location['lat'], location['lon']
                )
                
                if data:
                    processed = {
                        'source': 'nasa',
                        'location_name': location['name'],
                        'latitude': location['lat'],
                        'longitude': location['lon'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': data,
                        'quality_score': self._assess_data_quality(data, 'satellite')
                    }
                    satellite_data.append(processed)
                
                # Rate limiting - NASA has generous limits but still be careful
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Failed to collect satellite data for {location['name']}: {e}")
        
        return satellite_data
    
    def _assess_data_quality(self, data: Dict[str, Any], data_type: str) -> float:
        """Assess quality score for collected data"""
        try:
            if not data:
                return 0.0
            
            quality_score = 1.0
            
            if data_type == 'weather':
                # Check for missing critical weather parameters
                required_fields = ['temperature', 'humidity', 'pressure', 'wind_speed']
                missing_fields = sum(1 for field in required_fields if field not in data)
                quality_score -= (missing_fields / len(required_fields)) * 0.5
                
                # Check for reasonable value ranges
                if 'temperature' in data:
                    temp = data['temperature']
                    if temp < -50 or temp > 60:  # Extreme temperatures
                        quality_score -= 0.2
                
            elif data_type == 'air_quality':
                # Check for AQI data availability
                if 'aqi' not in data and 'pm2_5' not in data:
                    quality_score -= 0.5
                
                # Check for multiple pollutants
                pollutants = ['pm2_5', 'pm10', 'no2', 'so2', 'co', 'o3']
                available_pollutants = sum(1 for p in pollutants if p in data)
                if available_pollutants < 3:
                    quality_score -= 0.3
            
            elif data_type == 'ocean':
                # Check for tidal data completeness
                required_tidal = ['water_level', 'prediction']
                missing_tidal = sum(1 for field in required_tidal if field not in data)
                quality_score -= (missing_tidal / len(required_tidal)) * 0.4
            
            elif data_type == 'satellite':
                # Check for image availability and metadata
                if 'image_url' not in data:
                    quality_score -= 0.6
                if 'cloud_score' not in data:
                    quality_score -= 0.2
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            logger.warning(f"Error assessing data quality: {e}")
            return 0.5  # Default moderate quality
    
    async def _process_and_store_data(
        self, 
        all_data: Dict[str, Any], 
        successful_sources: int,
        failed_sources: int,
        errors: List[str],
        collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """Process collected data and store in database"""
        try:
            # Create aggregated metrics
            aggregated_metrics = self._create_aggregated_metrics(all_data)
            
            # Calculate data completeness
            total_expected_locations = len(self.monitoring_locations)
            total_collected = sum(len(source_data) for source_data in all_data.values())
            data_completeness = (total_collected / (total_expected_locations * 4)) * 100  # 4 sources
            
            # Create summary record
            summary_data = {
                'data_hash': self._generate_data_hash(all_data),
                'timestamp': datetime.utcnow().isoformat(),
                'total_locations': len(set(
                    item['location_name'] 
                    for source_data in all_data.values() 
                    for item in source_data
                )),
                'successful_sources': successful_sources,
                'failed_sources': failed_sources,
                'data_completeness': round(data_completeness, 2),
                'aggregated_metrics': aggregated_metrics
            }
            
            # Store summary in database
            result = await self.supabase.table('environmental_data_summary').insert(summary_data).execute()
            
            if result.data:
                summary_id = result.data[0]['id']
                
                # Store detailed records
                await self._store_detailed_records(all_data, summary_id)
                
                logger.info(f"✅ Data stored successfully - Summary ID: {summary_id}")
                
                return {
                    'collection_id': collection_id,
                    'summary_id': summary_id,
                    'summary': summary_data,
                    'details': all_data,
                    'errors': errors,
                    'collection_status': 'completed'
                }
            
        except Exception as e:
            logger.error(f"Failed to process and store data: {e}")
            return None
    
    async def _store_detailed_records(self, all_data: Dict[str, Any], summary_id: str):
        """Store detailed environmental data records"""
        detail_records = []
        
        for source_type, source_data in all_data.items():
            for record in source_data:
                detail_record = {
                    'summary_id': summary_id,
                    'source': record['source'],
                    'latitude': record['latitude'],
                    'longitude': record['longitude'],
                    'data': record['data'],
                    'timestamp': record['timestamp']
                }
                detail_records.append(detail_record)
        
        if detail_records:
            await self.supabase.table('environmental_data_details').insert(detail_records).execute()
            logger.info(f"✅ Stored {len(detail_records)} detailed records")
    
    def _create_aggregated_metrics(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create aggregated environmental metrics from collected data"""
        metrics = {
            'collection_timestamp': datetime.utcnow().isoformat(),
            'total_data_points': sum(len(source) for source in all_data.values())
        }
        
        # Weather metrics
        if 'weather' in all_data:
            weather_data = all_data['weather']
            temperatures = [item['data'].get('temperature') for item in weather_data if 'temperature' in item['data']]
            wind_speeds = [item['data'].get('wind_speed') for item in weather_data if 'wind_speed' in item['data']]
            
            if temperatures:
                metrics['avg_temperature'] = sum(temperatures) / len(temperatures)
                metrics['max_temperature'] = max(temperatures)
                metrics['min_temperature'] = min(temperatures)
            
            if wind_speeds:
                metrics['avg_wind_speed'] = sum(wind_speeds) / len(wind_speeds)
                metrics['max_wind_speed'] = max(wind_speeds)
        
        # Air quality metrics
        if 'air_quality' in all_data:
            aq_data = all_data['air_quality']
            aqi_values = [item['data'].get('aqi') for item in aq_data if 'aqi' in item['data']]
            pm25_values = [item['data'].get('pm2_5') for item in aq_data if 'pm2_5' in item['data']]
            
            if aqi_values:
                metrics['avg_aqi'] = sum(aqi_values) / len(aqi_values)
                metrics['max_aqi'] = max(aqi_values)
            
            if pm25_values:
                metrics['avg_pm25'] = sum(pm25_values) / len(pm25_values)
        
        # Ocean metrics
        if 'ocean' in all_data:
            ocean_data = all_data['ocean']
            water_levels = [item['data'].get('water_level') for item in ocean_data if 'water_level' in item['data']]
            
            if water_levels:
                metrics['avg_water_level'] = sum(water_levels) / len(water_levels)
                metrics['max_water_level'] = max(water_levels)
                metrics['min_water_level'] = min(water_levels)
        
        # Calculate environmental stress index
        stress_factors = []
        
        if 'max_wind_speed' in metrics and metrics['max_wind_speed'] > 15:
            stress_factors.append(min(metrics['max_wind_speed'] / 50, 1.0))
        
        if 'max_aqi' in metrics and metrics['max_aqi'] > 100:
            stress_factors.append(min(metrics['max_aqi'] / 300, 1.0))
        
        if stress_factors:
            metrics['environmental_stress_index'] = sum(stress_factors) / len(stress_factors)
        else:
            metrics['environmental_stress_index'] = 0.0
        
        return metrics
    
    def _generate_data_hash(self, data: Dict[str, Any]) -> str:
        """Generate SHA-256 hash of environmental data for blockchain"""
        try:
            # Create a consistent string representation of the data
            data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            return hashlib.sha256(data_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to generate data hash: {e}")
            return hashlib.sha256(str(data).encode()).hexdigest()
    
    async def get_latest_data(self, hours_back: int = 24) -> Optional[Dict[str, Any]]:
        """Retrieve latest environmental data from database"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            result = await self.supabase.table('environmental_data_summary')\
                .select('*, environmental_data_details(*)')\
                .gte('timestamp', start_time.isoformat())\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve latest data: {e}")
            return None
    
    async def get_data_by_location(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float = 50
    ) -> List[Dict[str, Any]]:
        """Get environmental data near a specific location"""
        try:
            # Use PostGIS to find data within radius
            result = await self.supabase.rpc(
                'get_latest_environmental_data',
                {
                    'center_lat': latitude,
                    'center_lon': longitude,
                    'radius_km': radius_km
                }
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get location data: {e}")
            return []
