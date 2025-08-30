"""
Ocean Sentinel - External API Clients
HTTP clients for environmental data APIs
"""

import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from app.config import settings, API_CONFIG

logger = logging.getLogger(__name__)

class BaseAPIClient:
    """Base class for API clients with common functionality"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, rate_limit: int = 60):
        self.base_url = base_url
        self.api_key = api_key
        self.rate_limit = rate_limit
        self.last_request_time = None
        
    async def _rate_limit(self):
        """Enforce rate limiting"""
        if self.last_request_time:
            elapsed = (datetime.utcnow() - self.last_request_time).total_seconds()
            min_interval = 60 / self.rate_limit  # seconds between requests
            
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
        
        self.last_request_time = datetime.utcnow()
    
    async def _make_request(self, endpoint: str, params: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """Make HTTP request with error handling"""
        await self._rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add API key to params if available
        if self.api_key and params is not None:
            params['appid'] = self.api_key  # OpenWeatherMap style
        elif self.api_key and 'key' not in (params or {}):
            if params is None:
                params = {}
            params['key'] = self.api_key  # Generic API key
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"API request failed: {url} - Status {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error(f"API request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"API request error: {url} - {e}")
            return None

class OpenWeatherClient(BaseAPIClient):
    """OpenWeatherMap API client"""
    
    def __init__(self):
        super().__init__(
            base_url=API_CONFIG['openweather']['base_url'],
            api_key=settings.openweather_api_key,
            rate_limit=API_CONFIG['openweather']['rate_limit']
        )
    
    async def get_current_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """Get current weather for coordinates"""
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'units': 'metric',
                'appid': self.api_key
            }
            
            data = await self._make_request('weather', params)
            
            if data:
                # Normalize weather data structure
                return {
                    'temperature': data['main']['temp'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'wind_speed': data.get('wind', {}).get('speed', 0),
                    'wind_direction': data.get('wind', {}).get('deg', 0),
                    'precipitation': data.get('rain', {}).get('1h', 0) + data.get('snow', {}).get('1h', 0),
                    'visibility': data.get('visibility', 10000),
                    'cloud_cover': data.get('clouds', {}).get('all', 0),
                    'conditions': data['weather'][0]['description'] if data.get('weather') else 'unknown',
                    'source_timestamp': datetime.utcfromtimestamp(data['dt']).isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"OpenWeather API error: {e}")
            return None
    
    async def get_weather_forecast(self, lat: float, lon: float, days: int = 5) -> Optional[List[Dict]]:
        """Get weather forecast"""
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'units': 'metric',
                'appid': self.api_key
            }
            
            data = await self._make_request('forecast', params)
            
            if data and 'list' in data:
                forecast = []
                for item in data['list'][:days * 8]:  # 8 forecasts per day (3-hour intervals)
                    forecast.append({
                        'timestamp': datetime.utcfromtimestamp(item['dt']).isoformat(),
                        'temperature': item['main']['temp'],
                        'humidity': item['main']['humidity'],
                        'pressure': item['main']['pressure'],
                        'wind_speed': item.get('wind', {}).get('speed', 0),
                        'precipitation': item.get('rain', {}).get('3h', 0),
                        'conditions': item['weather'][0]['description']
                    })
                
                return forecast
            
            return []
            
        except Exception as e:
            logger.error(f"OpenWeather forecast error: {e}")
            return []

class OpenAQClient(BaseAPIClient):
    """OpenAQ Air Quality API client"""
    
    def __init__(self):
        super().__init__(
            base_url=API_CONFIG['openaq']['base_url'],
            rate_limit=API_CONFIG['openaq']['rate_limit']
        )
    
    async def get_air_quality(self, lat: float, lon: float, radius: int = 25000) -> Optional[Dict]:
        """Get air quality data near coordinates"""
        try:
            params = {
                'coordinates': f"{lat},{lon}",
                'radius': radius,
                'limit': 100,
                'order_by': 'lastUpdated',
                'sort': 'desc'
            }
            
            data = await self._make_request('latest', params)
            
            if data and 'results' in data and data['results']:
                # Aggregate measurements by parameter
                measurements = {}
                for result in data['results']:
                    for measurement in result.get('measurements', []):
                        param = measurement['parameter']
                        value = measurement['value']
                        unit = measurement['unit']
                        
                        if param not in measurements:
                            measurements[param] = []
                        
                        measurements[param].append({
                            'value': value,
                            'unit': unit,
                            'lastUpdated': measurement['lastUpdated']
                        })
                
                # Calculate averages and format output
                air_quality = {}
                
                for param, values in measurements.items():
                    if values:
                        avg_value = sum(v['value'] for v in values) / len(values)
                        air_quality[param] = avg_value
                
                # Calculate AQI if we have PM2.5 data
                if 'pm25' in air_quality:
                    air_quality['aqi'] = self._calculate_aqi(air_quality['pm25'])
                
                return air_quality
            
            return None
            
        except Exception as e:
            logger.error(f"OpenAQ API error: {e}")
            return None
    
    def _calculate_aqi(self, pm25: float) -> int:
        """Calculate AQI from PM2.5 value (US EPA standard)"""
        if pm25 <= 12:
            return int((50 / 12) * pm25)
        elif pm25 <= 35.4:
            return int(50 + ((100 - 50) / (35.4 - 12.1)) * (pm25 - 12.1))
        elif pm25 <= 55.4:
            return int(100 + ((150 - 100) / (55.4 - 35.5)) * (pm25 - 35.5))
        elif pm25 <= 150.4:
            return int(150 + ((200 - 150) / (150.4 - 55.5)) * (pm25 - 55.5))
        elif pm25 <= 250.4:
            return int(200 + ((300 - 200) / (250.4 - 150.5)) * (pm25 - 150.5))
        else:
            return int(300 + ((500 - 300) / (500.4 - 250.5)) * (pm25 - 250.5))

class NOAAClient(BaseAPIClient):
    """NOAA Tides and Currents API client"""
    
    def __init__(self):
        super().__init__(
            base_url=API_CONFIG['noaa']['base_url'],
            rate_limit=API_CONFIG['noaa']['rate_limit']
        )
    
    async def get_tidal_data(self, station_id: str) -> Optional[Dict]:
        """Get tidal data for NOAA station"""
        try:
            # Get current water level
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=1)
            
            params = {
                'begin_date': start_date.strftime('%Y%m%d %H:%M'),
                'end_date': end_date.strftime('%Y%m%d %H:%M'),
                'station': station_id,
                'product': 'water_level',
                'datum': 'MLLW',
                'units': 'metric',
                'format': 'json'
            }
            
            water_level_data = await self._make_request('', params)
            
            # Get predictions for comparison
            predict_params = {
                'begin_date': start_date.strftime('%Y%m%d %H:%M'),
                'end_date': end_date.strftime('%Y%m%d %H:%M'),
                'station': station_id,
                'product': 'predictions',
                'datum': 'MLLW',
                'units': 'metric',
                'format': 'json'
            }
            
            prediction_data = await self._make_request('', predict_params)
            
            result = {}
            
            if water_level_data and 'data' in water_level_data:
                latest_level = water_level_data['data'][-1] if water_level_data['data'] else None
                if latest_level:
                    result['water_level'] = float(latest_level['v'])
                    result['timestamp'] = latest_level['t']
            
            if prediction_data and 'predictions' in prediction_data:
                latest_prediction = prediction_data['predictions'][-1] if prediction_data['predictions'] else None
                if latest_prediction:
                    result['prediction'] = float(latest_prediction['v'])
                    result['predicted_timestamp'] = latest_prediction['t']
            
            # Calculate additional metrics
            if 'water_level' in result and 'prediction' in result:
                result['anomaly'] = abs(result['water_level'] - result['prediction'])
                result['tidal_stage'] = 'rising' if result['water_level'] > result['prediction'] else 'falling'
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"NOAA API error: {e}")
            return None

class NASAClient(BaseAPIClient):
    """NASA Earth Data API client"""
    
    def __init__(self):
        super().__init__(
            base_url=API_CONFIG['nasa']['earth_url'],
            api_key=settings.nasa_api_key,
            rate_limit=API_CONFIG['nasa']['rate_limit']
        )
    
    async def get_earth_imagery(self, lat: float, lon: float) -> Optional[Dict]:
        """Get satellite imagery and data for coordinates"""
        try:
            # Get available imagery
            params = {
                'lat': lat,
                'lon': lon,
                'dim': 0.1,  # 0.1 degree square
                'api_key': self.api_key
            }
            
            # Get imagery metadata
            imagery_data = await self._make_request('imagery', params)
            
            if imagery_data and 'url' in imagery_data:
                result = {
                    'image_url': imagery_data['url'],
                    'acquisition_date': imagery_data.get('date'),
                    'cloud_score': 0.1,  # Mock value - would analyze actual imagery
                    'resolution': 30,  # Landsat resolution
                }
                
                # Get assets information if available
                assets_params = params.copy()
                assets_data = await self._make_request('assets', assets_params)
                
                if assets_data:
                    result.update({
                        'satellite': assets_data.get('satellite', 'Landsat'),
                        'scene_id': assets_data.get('id', 'unknown')
                    })
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"NASA API error: {e}")
            return None
    
    async def get_environmental_data(self, lat: float, lon: float) -> Optional[Dict]:
        """Get environmental parameters from NASA data"""
        try:
            # This would integrate with NASA's various environmental APIs
            # For now, return mock data structure
            return {
                'surface_temperature': 15.5,  # Would come from MODIS
                'vegetation_index': 0.3,      # NDVI from satellite data
                'water_detection': False,     # Water body detection
                'land_cover': 'urban',        # Land cover classification
                'aerosol_optical_depth': 0.1  # Atmospheric data
            }
            
        except Exception as e:
            logger.error(f"NASA environmental data error: {e}")
            return None
