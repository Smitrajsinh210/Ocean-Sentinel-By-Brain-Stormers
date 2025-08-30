"""
Ocean Sentinel - Ocean Service
NOAA Tides & Currents API integration for oceanographic data collection
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import httpx
import json
from dataclasses import dataclass, asdict
from geopy.distance import geodesic

# Import from our services package
from . import services_logger, get_service_config, standardize_parameter_name, validate_coordinates, calculate_data_quality_score

@dataclass
class OceanData:
    """Ocean data structure"""
    timestamp: str
    location: Dict[str, float]  # {"lat": float, "lng": float}
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    distance_km: Optional[float] = None
    tide_level: Optional[float] = None
    water_temperature: Optional[float] = None
    salinity: Optional[float] = None
    wave_height: Optional[float] = None
    wave_period: Optional[float] = None
    wave_direction: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    atmospheric_pressure: Optional[float] = None
    visibility: Optional[float] = None
    data_quality_score: Optional[float] = None
    source: str = "NOAA"
    raw_data: Optional[Dict[str, Any]] = None

class OceanService:
    """
    Ocean data service using NOAA Tides & Currents API
    Provides real-time oceanographic data from NOAA monitoring stations
    """
    
    def __init__(self):
        self.config = get_service_config("ocean")
        self.base_url = self.config.get("base_url", "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter")
        self.timeout = self.config.get("timeout", 30)
        self.retry_attempts = self.config.get("retry_attempts", 3)
        self.rate_limit = self.config.get("rate_limit", 1000)
        
        # Rate limiting
        self.last_request_time = None
        self.request_count = 0
        self.request_window_start = datetime.now()
        
        # NOAA station cache
        self.station_cache = {}
        self.cache_expiry = datetime.now() - timedelta(hours=24)
        
        # NOAA data products mapping
        self.data_products = {
            'water_level': 'water_level',
            'air_temperature': 'air_temperature',
            'water_temperature': 'water_temperature',
            'wind': 'wind',
            'air_pressure': 'air_pressure',
            'air_gap': 'air_gap',
            'conductivity': 'conductivity',
            'visibility': 'visibility',
            'humidity': 'humidity',
            'salinity': 'salinity',
            'hourly_height': 'hourly_height',
            'high_low': 'high_low',
            'daily_mean': 'daily_mean',
            'monthly_mean': 'monthly_mean',
            'one_minute_water_level': 'one_minute_water_level',
            'predictions': 'predictions',
            'datums': 'datums',
            'currents': 'currents'
        }
        
        # Parameter units
        self.parameter_units = {
            'water_level': 'meters',
            'water_temperature': 'celsius',
            'air_temperature': 'celsius',
            'wind_speed': 'knots',
            'wind_direction': 'degrees',
            'air_pressure': 'mb',
            'salinity': 'psu',
            'visibility': 'nautical_miles'
        }
        
        services_logger.info("OceanService initialized")
    
    async def get_current_ocean_data(
        self, 
        lat: float, 
        lng: float,
        radius_km: float = 50.0
    ) -> Optional[OceanData]:
        """
        Get current ocean data for specified coordinates
        """
        try:
            # Validate coordinates
            if not validate_coordinates(lat, lng):
                services_logger.error(f"Invalid coordinates: {lat}, {lng}")
                return None
            
            # Find nearest NOAA stations
            stations = await self._find_nearby_stations(lat, lng, radius_km)
            
            if not stations:
                services_logger.warning(f"No NOAA stations found within {radius_km}km of {lat}, {lng}")
                return None
            
            # Get data from the nearest station with recent data
            for station in stations[:3]:  # Try up to 3 closest stations
                ocean_data = await self._get_station_data(station, lat, lng)
                if ocean_data:
                    return ocean_data
            
            services_logger.warning("No recent ocean data available from nearby stations")
            return None
            
        except Exception as e:
            services_logger.error(f"Error getting current ocean data: {str(e)}")
            return None
    
    async def get_tide_data(
        self,
        lat: float,
        lng: float,
        hours_ahead: int = 24,
        include_predictions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get tide data including predictions
        """
        try:
            if not validate_coordinates(lat, lng):
                return []
            
            stations = await self._find_nearby_stations(lat, lng, 50.0)
            
            if not stations:
                return []
            
            tide_data = []
            
            for station in stations[:2]:  # Get from 2 closest stations
                station_id = station.get('id')
                if not station_id:
                    continue
                
                # Get current water level
                current_data = await self._get_parameter_data(
                    station_id, 'water_level', hours=6
                )
                
                if current_data:
                    for record in current_data:
                        tide_data.append({
                            'timestamp': record.get('t'),
                            'water_level': float(record.get('v', 0)),
                            'station_id': station_id,
                            'station_name': station.get('name'),
                            'type': 'observed',
                            'location': {"lat": lat, "lng": lng}
                        })
                
                # Get predictions if requested
                if include_predictions:
                    prediction_data = await self._get_tide_predictions(
                        station_id, hours_ahead
                    )
                    
                    for record in prediction_data:
                        tide_data.append({
                            'timestamp': record.get('t'),
                            'water_level': float(record.get('v', 0)),
                            'station_id': station_id,
                            'station_name': station.get('name'),
                            'type': 'predicted',
                            'location': {"lat": lat, "lng": lng}
                        })
            
            # Sort by timestamp
            tide_data.sort(key=lambda x: x.get('timestamp', ''))
            
            services_logger.info(f"Retrieved {len(tide_data)} tide data points")
            return tide_data
            
        except Exception as e:
            services_logger.error(f"Error getting tide data: {str(e)}")
            return []
    
    async def get_wave_data(
        self,
        lat: float,
        lng: float,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get wave height and period data from NOAA buoys
        """
        try:
            if not validate_coordinates(lat, lng):
                return []
            
            # Find buoy stations (different from tide stations)
            buoy_stations = await self._find_buoy_stations(lat, lng, 100.0)
            
            if not buoy_stations:
                return []
            
            wave_data = []
            
            for station in buoy_stations[:2]:
                station_id = station.get('id')
                
                # Get wave height data
                wave_height_data = await self._get_parameter_data(
                    station_id, 'hourly_height', hours=hours
                )
                
                if wave_height_data:
                    for record in wave_height_data:
                        wave_data.append({
                            'timestamp': record.get('t'),
                            'wave_height': float(record.get('s', 0)),  # Significant wave height
                            'wave_period': float(record.get('d', 0)),  # Dominant wave period
                            'station_id': station_id,
                            'station_name': station.get('name'),
                            'location': {"lat": lat, "lng": lng}
                        })
            
            services_logger.info(f"Retrieved {len(wave_data)} wave data points")
            return wave_data
            
        except Exception as e:
            services_logger.error(f"Error getting wave data: {str(e)}")
            return []
    
    async def get_ocean_conditions_summary(
        self,
        lat: float,
        lng: float
    ) -> Dict[str, Any]:
        """
        Get comprehensive ocean conditions summary
        """
        try:
            summary = {
                "location": {"lat": lat, "lng": lng},
                "timestamp": datetime.now().isoformat(),
                "current_conditions": {},
                "tide_info": {},
                "wave_info": {},
                "weather_conditions": {}
            }
            
            # Get current ocean data
            current_data = await self.get_current_ocean_data(lat, lng)
            if current_data:
                summary["current_conditions"] = {
                    "water_temperature": current_data.water_temperature,
                    "salinity": current_data.salinity,
                    "tide_level": current_data.tide_level,
                    "visibility": current_data.visibility,
                    "station": current_data.station_name,
                    "data_quality": current_data.data_quality_score
                }
            
            # Get tide information
            tide_data = await self.get_tide_data(lat, lng, 48, True)
            if tide_data:
                current_tide = next((t for t in tide_data if t['type'] == 'observed'), None)
                next_high = next((t for t in tide_data if t['type'] == 'predicted' and float(t['water_level']) > 0), None)
                next_low = next((t for t in tide_data if t['type'] == 'predicted' and float(t['water_level']) < 0), None)
                
                summary["tide_info"] = {
                    "current_level": current_tide['water_level'] if current_tide else None,
                    "next_high_tide": next_high,
                    "next_low_tide": next_low,
                    "tide_trend": self._analyze_tide_trend(tide_data)
                }
            
            # Get wave information
            wave_data = await self.get_wave_data(lat, lng, 24)
            if wave_data:
                latest_wave = wave_data[-1] if wave_data else None
                avg_wave_height = sum(w['wave_height'] for w in wave_data) / len(wave_data)
                max_wave_height = max(w['wave_height'] for w in wave_data)
                
                summary["wave_info"] = {
                    "current_height": latest_wave['wave_height'] if latest_wave else None,
                    "current_period": latest_wave['wave_period'] if latest_wave else None,
                    "average_height_24h": round(avg_wave_height, 2),
                    "max_height_24h": round(max_wave_height, 2),
                    "wave_conditions": self._assess_wave_conditions(avg_wave_height)
                }
            
            return summary
            
        except Exception as e:
            services_logger.error(f"Error getting ocean conditions summary: {str(e)}")
            return {"error": str(e)}
    
    async def _find_nearby_stations(
        self,
        lat: float,
        lng: float,
        radius_km: float
    ) -> List[Dict[str, Any]]:
        """Find NOAA stations near coordinates"""
        try:
            # Check cache first
            if datetime.now() > self.cache_expiry:
                await self._refresh_station_cache()
            
            nearby_stations = []
            
            # Search through cached stations
            for station in self.station_cache.get('stations', []):
                if 'lat' in station and 'lng' in station:
                    station_lat = float(station['lat'])
                    station_lng = float(station['lng'])
                    
                    distance = geodesic((lat, lng), (station_lat, station_lng)).kilometers
                    
                    if distance <= radius_km:
                        station['distance_km'] = distance
                        nearby_stations.append(station)
            
            # Sort by distance
            nearby_stations.sort(key=lambda x: x.get('distance_km', float('inf')))
            
            return nearby_stations
            
        except Exception as e:
            services_logger.error(f"Error finding nearby stations: {str(e)}")
            return []
    
    async def _find_buoy_stations(
        self,
        lat: float,
        lng: float,
        radius_km: float
    ) -> List[Dict[str, Any]]:
        """Find NOAA buoy stations for wave data"""
        try:
            # Rate limiting
            if not await self._check_rate_limit():
                await asyncio.sleep(60)
            
            # Get stations metadata
            params = {
                'format': 'json'
            }
            
            url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
            response = await self._make_request(url, params)
            
            if not response or 'stations' not in response:
                return []
            
            buoy_stations = []
            
            for station in response['stations']:
                if station.get('type') == 'buoy' or 'buoy' in station.get('name', '').lower():
                    if 'lat' in station and 'lng' in station:
                        station_lat = float(station['lat'])
                        station_lng = float(station['lng'])
                        
                        distance = geodesic((lat, lng), (station_lat, station_lng)).kilometers
                        
                        if distance <= radius_km:
                            station['distance_km'] = distance
                            buoy_stations.append(station)
            
            # Sort by distance
            buoy_stations.sort(key=lambda x: x.get('distance_km', float('inf')))
            
            return buoy_stations
            
        except Exception as e:
            services_logger.error(f"Error finding buoy stations: {str(e)}")
            return []
    
    async def _get_station_data(
        self,
        station: Dict[str, Any],
        lat: float,
        lng: float
    ) -> Optional[OceanData]:
        """Get comprehensive data from a NOAA station"""
        try:
            station_id = station.get('id')
            if not station_id:
                return None
            
            ocean_data = OceanData(
                timestamp=datetime.now().isoformat(),
                location={"lat": lat, "lng": lng},
                station_id=station_id,
                station_name=station.get('name'),
                distance_km=station.get('distance_km'),
                raw_data={"station": station}
            )
            
            # Get various parameters
            parameters_to_fetch = [
                ('water_level', 'tide_level'),
                ('water_temperature', 'water_temperature'),
                ('air_temperature', None),
                ('wind', 'wind_speed'),
                ('air_pressure', 'atmospheric_pressure'),
                ('salinity', 'salinity'),
                ('visibility', 'visibility')
            ]
            
            data_collected = 0
            
            for noaa_param, ocean_param in parameters_to_fetch:
                try:
                    param_data = await self._get_parameter_data(
                        station_id, noaa_param, hours=6
                    )
                    
                    if param_data and len(param_data) > 0:
                        # Get most recent value
                        latest_record = param_data[-1]
                        value = float(latest_record.get('v', 0))
                        
                        if ocean_param:
                            setattr(ocean_data, ocean_param, value)
                            data_collected += 1
                        
                        # Special handling for wind data
                        if noaa_param == 'wind' and 'd' in latest_record:
                            ocean_data.wind_direction = float(latest_record.get('d', 0))
                            data_collected += 1
                            
                except Exception as e:
                    services_logger.warning(f"Could not get {noaa_param} from station {station_id}: {str(e)}")
                    continue
            
            # Only return data if we got at least some measurements
            if data_collected > 0:
                # Calculate data quality score
                completeness = data_collected / 8  # Total possible parameters
                age_hours = 0  # Recent data
                has_errors = data_collected < 3
                
                ocean_data.data_quality_score = calculate_data_quality_score(
                    data_collected, completeness, age_hours, has_errors
                )
                
                return ocean_data
            
            return None
            
        except Exception as e:
            services_logger.error(f"Error getting station data: {str(e)}")
            return None
    
    async def _get_parameter_data(
        self,
        station_id: str,
        parameter: str,
        hours: int = 6
    ) -> List[Dict[str, Any]]:
        """Get specific parameter data from NOAA station"""
        try:
            # Rate limiting
            if not await self._check_rate_limit():
                await asyncio.sleep(60)
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            params = {
                'begin_date': start_time.strftime('%Y%m%d %H:%M'),
                'end_date': end_time.strftime('%Y%m%d %H:%M'),
                'station': station_id,
                'product': parameter,
                'datum': 'MLLW',  # Mean Lower Low Water
                'units': 'metric',
                'time_zone': 'gmt',
                'format': 'json'
            }
            
            response = await self._make_request(self.base_url, params)
            
            if response and 'data' in response:
                return response['data']
            
            return []
            
        except Exception as e:
            services_logger.error(f"Error getting parameter data: {str(e)}")
            return []
    
    async def _get_tide_predictions(
        self,
        station_id: str,
        hours_ahead: int
    ) -> List[Dict[str, Any]]:
        """Get tide predictions from NOAA"""
        try:
            # Rate limiting
            if not await self._check_rate_limit():
                await asyncio.sleep(60)
            
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=hours_ahead)
            
            params = {
                'begin_date': start_time.strftime('%Y%m%d %H:%M'),
                'end_date': end_time.strftime('%Y%m%d %H:%M'),
                'station': station_id,
                'product': 'predictions',
                'datum': 'MLLW',
                'units': 'metric',
                'time_zone': 'gmt',
                'format': 'json',
                'interval': 'h'  # Hourly predictions
            }
            
            response = await self._make_request(self.base_url, params)
            
            if response and 'predictions' in response:
                return response['predictions']
            
            return []
            
        except Exception as e:
            services_logger.error(f"Error getting tide predictions: {str(e)}")
            return []
    
    async def _refresh_station_cache(self):
        """Refresh NOAA stations cache"""
        try:
            # Rate limiting
            if not await self._check_rate_limit():
                await asyncio.sleep(60)
            
            params = {'format': 'json'}
            url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
            
            response = await self._make_request(url, params)
            
            if response and 'stations' in response:
                self.station_cache = response
                self.cache_expiry = datetime.now() + timedelta(hours=24)
                services_logger.info(f"Refreshed station cache with {len(response['stations'])} stations")
            
        except Exception as e:
            services_logger.error(f"Error refreshing station cache: {str(e)}")
    
    def _analyze_tide_trend(self, tide_data: List[Dict[str, Any]]) -> str:
        """Analyze tide trend (rising/falling)"""
        try:
            if len(tide_data) < 2:
                return "unknown"
            
            recent_data = [t for t in tide_data[-5:] if t['type'] == 'observed']
            
            if len(recent_data) < 2:
                return "unknown"
            
            first_level = float(recent_data[0]['water_level'])
            last_level = float(recent_data[-1]['water_level'])
            
            if last_level > first_level + 0.1:
                return "rising"
            elif last_level < first_level - 0.1:
                return "falling"
            else:
                return "stable"
                
        except Exception as e:
            services_logger.error(f"Error analyzing tide trend: {str(e)}")
            return "unknown"
    
    def _assess_wave_conditions(self, avg_wave_height: float) -> str:
        """Assess wave conditions based on average height"""
        try:
            if avg_wave_height < 1.0:
                return "calm"
            elif avg_wave_height < 2.0:
                return "slight"
            elif avg_wave_height < 4.0:
                return "moderate"
            elif avg_wave_height < 6.0:
                return "rough"
            else:
                return "very_rough"
                
        except Exception as e:
            services_logger.error(f"Error assessing wave conditions: {str(e)}")
            return "unknown"
    
    async def _make_request(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make HTTP request to NOAA API"""
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        services_logger.warning("Rate limit exceeded, retrying...")
                        await asyncio.sleep(60)
                        continue
                    else:
                        services_logger.error(f"API request failed: {response.status_code}")
                        
            except httpx.TimeoutException:
                services_logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                services_logger.error(f"Request error: {str(e)}")
                
        return None
    
    async def _check_rate_limit(self) -> bool:
        """Check if we can make another request within rate limits"""
        try:
            current_time = datetime.now()
            
            # Reset counter every minute
            if (current_time - self.request_window_start).seconds >= 60:
                self.request_count = 0
                self.request_window_start = current_time
            
            # Check if we're under the rate limit
            if self.request_count >= self.rate_limit:
                return False
            
            self.request_count += 1
            self.last_request_time = current_time
            return True
            
        except Exception as e:
            services_logger.error(f"Error checking rate limit: {str(e)}")
            return True
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health and status information"""
        try:
            status = {
                "service": "OceanService",
                "api_provider": "NOAA Tides & Currents",
                "rate_limit": self.rate_limit,
                "current_request_count": self.request_count,
                "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
                "timeout": self.timeout,
                "retry_attempts": self.retry_attempts,
                "station_cache_size": len(self.station_cache.get('stations', [])),
                "cache_expiry": self.cache_expiry.isoformat()
            }
            
            # Test API connectivity
            test_response = await self._make_request(
                "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json",
                {"format": "json"}
            )
            status["api_accessible"] = bool(test_response)
            
            return status
            
        except Exception as e:
            services_logger.error(f"Error getting service status: {str(e)}")
            return {"error": str(e)}

# Global instance
ocean_service = OceanService()