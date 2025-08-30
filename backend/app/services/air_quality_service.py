"""
Ocean Sentinel - Air Quality Service
OpenAQ API integration for air pollution data collection
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
class AirQualityData:
    """Air quality data structure"""
    timestamp: str
    location: Dict[str, float]  # {"lat": float, "lng": float}
    station_name: Optional[str] = None
    distance_km: Optional[float] = None
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    ozone: Optional[float] = None
    nitrogen_dioxide: Optional[float] = None
    sulfur_dioxide: Optional[float] = None
    carbon_monoxide: Optional[float] = None
    aqi: Optional[int] = None
    aqi_category: Optional[str] = None
    data_quality_score: Optional[float] = None
    source: str = "OpenAQ"
    raw_data: Optional[Dict[str, Any]] = None

class AirQualityService:
    """
    Air quality data service using OpenAQ API
    Provides real-time air pollution measurements from monitoring stations
    """
    
    def __init__(self):
        self.config = get_service_config("air_quality")
        self.base_url = self.config.get("base_url", "https://api.openaq.org/v2")
        self.api_key = os.environ.get("f3b1b42e28deedb359e278889ba17ec1b77148174922717ca657ab8e86a160f9")  # Optional for OpenAQ
        self.timeout = self.config.get("timeout", 30)
        self.retry_attempts = self.config.get("retry_attempts", 3)
        self.rate_limit = self.config.get("rate_limit", 100)
        
        # Rate limiting
        self.last_request_time = None
        self.request_count = 0
        self.request_window_start = datetime.now()
        
        # AQI calculation breakpoints (US EPA standard)
        self.aqi_breakpoints = {
            'pm25': [
                (0.0, 12.0, 0, 50),
                (12.1, 35.4, 51, 100),
                (35.5, 55.4, 101, 150),
                (55.5, 150.4, 151, 200),
                (150.5, 250.4, 201, 300),
                (250.5, 350.4, 301, 400),
                (350.5, 500.4, 401, 500)
            ],
            'pm10': [
                (0, 54, 0, 50),
                (55, 154, 51, 100),
                (155, 254, 101, 150),
                (255, 354, 151, 200),
                (355, 424, 201, 300),
                (425, 504, 301, 400),
                (505, 604, 401, 500)
            ],
            'o3': [  # 8-hour average
                (0.000, 0.054, 0, 50),
                (0.055, 0.070, 51, 100),
                (0.071, 0.085, 101, 150),
                (0.086, 0.105, 151, 200),
                (0.106, 0.200, 201, 300)
            ],
            'no2': [  # 1-hour average
                (0, 53, 0, 50),
                (54, 100, 51, 100),
                (101, 360, 101, 150),
                (361, 649, 151, 200),
                (650, 1249, 201, 300),
                (1250, 1649, 301, 400),
                (1650, 2049, 401, 500)
            ]
        }
        
        self.aqi_categories = {
            (0, 50): "Good",
            (51, 100): "Moderate",
            (101, 150): "Unhealthy for Sensitive Groups",
            (151, 200): "Unhealthy",
            (201, 300): "Very Unhealthy",
            (301, 500): "Hazardous"
        }
        
        services_logger.info("AirQualityService initialized")
    
    async def get_current_air_quality(
        self, 
        lat: float, 
        lng: float,
        radius_km: float = 25.0
    ) -> Optional[AirQualityData]:
        """
        Get current air quality data for specified coordinates
        """
        try:
            # Validate coordinates
            if not validate_coordinates(lat, lng):
                services_logger.error(f"Invalid coordinates: {lat}, {lng}")
                return None
            
            # Rate limiting check
            if not await self._check_rate_limit():
                services_logger.warning("Rate limit exceeded for air quality service")
                await asyncio.sleep(60)
            
            # Find nearest stations
            stations = await self._find_nearby_stations(lat, lng, radius_km)
            
            if not stations:
                services_logger.warning(f"No air quality stations found within {radius_km}km of {lat}, {lng}")
                return None
            
            # Get measurements from the nearest station
            station = stations[0]  # Closest station
            measurements = await self._get_station_measurements(station)
            
            if not measurements:
                services_logger.warning(f"No recent measurements from station {station.get('name')}")
                return None
            
            # Parse and aggregate measurements
            air_quality_data = await self._parse_air_quality_data(measurements, lat, lng, station)
            
            services_logger.info(f"Retrieved air quality data from station: {station.get('name')}")
            return air_quality_data
            
        except Exception as e:
            services_logger.error(f"Error getting current air quality: {str(e)}")
            return None
    
    async def get_air_quality_history(
        self,
        lat: float,
        lng: float,
        start_time: datetime,
        end_time: datetime,
        radius_km: float = 25.0
    ) -> List[AirQualityData]:
        """
        Get historical air quality data for specified time range
        """
        try:
            if not validate_coordinates(lat, lng):
                return []
            
            # Find nearby stations
            stations = await self._find_nearby_stations(lat, lng, radius_km)
            
            if not stations:
                return []
            
            historical_data = []
            
            # Get historical data from multiple stations if available
            for station in stations[:3]:  # Limit to 3 closest stations
                station_data = await self._get_station_historical_data(
                    station, start_time, end_time
                )
                
                for measurement_set in station_data:
                    parsed_data = await self._parse_air_quality_data(
                        measurement_set, lat, lng, station
                    )
                    if parsed_data:
                        historical_data.append(parsed_data)
            
            # Sort by timestamp
            historical_data.sort(key=lambda x: x.timestamp)
            
            services_logger.info(f"Retrieved {len(historical_data)} historical air quality records")
            return historical_data
            
        except Exception as e:
            services_logger.error(f"Error getting air quality history: {str(e)}")
            return []
    
    async def get_pollutant_forecast(
        self,
        lat: float,
        lng: float,
        pollutant: str = "pm25",
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get air quality forecast (limited by OpenAQ capabilities)
        Note: OpenAQ primarily provides historical/current data, not forecasts
        """
        try:
            # OpenAQ doesn't provide forecasts, so we'll return recent trend data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            historical_data = await self.get_air_quality_history(
                lat, lng, start_time, end_time
            )
            
            # Extract trend for specified pollutant
            trend_data = []
            for data_point in historical_data:
                pollutant_value = getattr(data_point, pollutant, None)
                if pollutant_value is not None:
                    trend_data.append({
                        "timestamp": data_point.timestamp,
                        "pollutant": pollutant,
                        "value": pollutant_value,
                        "aqi": data_point.aqi,
                        "category": data_point.aqi_category
                    })
            
            services_logger.info(f"Retrieved {len(trend_data)} trend points for {pollutant}")
            return trend_data
            
        except Exception as e:
            services_logger.error(f"Error getting pollutant forecast: {str(e)}")
            return []
    
    async def _find_nearby_stations(
        self,
        lat: float,
        lng: float,
        radius_km: float
    ) -> List[Dict[str, Any]]:
        """Find air quality monitoring stations near coordinates"""
        try:
            # Rate limiting
            if not await self._check_rate_limit():
                await asyncio.sleep(60)
            
            params = {
                "coordinates": f"{lat},{lng}",
                "radius": int(radius_km * 1000),  # Convert to meters
                "limit": 10,
                "order_by": "distance"
            }
            
            if self.api_key:
                params["api-key"] = self.api_key
            
            url = f"{self.base_url}/locations"
            response = await self._make_request(url, params)
            
            if not response or 'results' not in response:
                return []
            
            stations = response['results']
            
            # Calculate distances and sort
            station_list = []
            for station in stations:
                if 'coordinates' in station and station['coordinates']:
                    station_lat = station['coordinates']['latitude']
                    station_lng = station['coordinates']['longitude']
                    
                    distance = geodesic((lat, lng), (station_lat, station_lng)).kilometers
                    
                    station['distance_km'] = distance
                    station_list.append(station)
            
            # Sort by distance
            station_list.sort(key=lambda x: x.get('distance_km', float('inf')))
            
            return station_list
            
        except Exception as e:
            services_logger.error(f"Error finding nearby stations: {str(e)}")
            return []
    
    async def _get_station_measurements(self, station: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recent measurements from a specific station"""
        try:
            # Rate limiting
            if not await self._check_rate_limit():
                await asyncio.sleep(60)
            
            location_id = station.get('id')
            if not location_id:
                return []
            
            params = {
                "location_id": location_id,
                "limit": 100,
                "order_by": "datetime",
                "sort": "desc",
                "date_from": (datetime.now() - timedelta(hours=24)).isoformat(),
                "date_to": datetime.now().isoformat()
            }
            
            if self.api_key:
                params["api-key"] = self.api_key
            
            url = f"{self.base_url}/measurements"
            response = await self._make_request(url, params)
            
            if not response or 'results' not in response:
                return []
            
            return response['results']
            
        except Exception as e:
            services_logger.error(f"Error getting station measurements: {str(e)}")
            return []
    
    async def _get_station_historical_data(
        self,
        station: Dict[str, Any],
        start_time: datetime,
        end_time: datetime
    ) -> List[List[Dict[str, Any]]]:
        """Get historical data from station for date range"""
        try:
            location_id = station.get('id')
            if not location_id:
                return []
            
            # Break into daily chunks to manage API limits
            historical_data = []
            current_time = start_time
            
            while current_time < end_time:
                if not await self._check_rate_limit():
                    await asyncio.sleep(60)
                
                chunk_end = min(current_time + timedelta(days=1), end_time)
                
                params = {
                    "location_id": location_id,
                    "limit": 1000,
                    "date_from": current_time.isoformat(),
                    "date_to": chunk_end.isoformat()
                }
                
                if self.api_key:
                    params["api-key"] = self.api_key
                
                url = f"{self.base_url}/measurements"
                response = await self._make_request(url, params)
                
                if response and 'results' in response:
                    historical_data.append(response['results'])
                
                current_time = chunk_end
            
            return historical_data
            
        except Exception as e:
            services_logger.error(f"Error getting historical data: {str(e)}")
            return []
    
    async def _parse_air_quality_data(
        self,
        measurements: List[Dict[str, Any]],
        lat: float,
        lng: float,
        station: Dict[str, Any]
    ) -> Optional[AirQualityData]:
        """Parse and aggregate air quality measurements"""
        try:
            if not measurements:
                return None
            
            # Group measurements by parameter
            parameter_values = {}
            latest_timestamp = None
            
            for measurement in measurements:
                parameter = measurement.get('parameter')
                value = measurement.get('value')
                timestamp = measurement.get('date', {}).get('utc')
                
                if parameter and value is not None:
                    # Standardize parameter names
                    std_param = standardize_parameter_name("air_quality", parameter)
                    
                    if std_param not in parameter_values:
                        parameter_values[std_param] = []
                    
                    parameter_values[std_param].append({
                        'value': value,
                        'timestamp': timestamp
                    })
                    
                    if not latest_timestamp or timestamp > latest_timestamp:
                        latest_timestamp = timestamp
            
            # Average values for each parameter
            air_quality_data = AirQualityData(
                timestamp=latest_timestamp or datetime.now().isoformat(),
                location={"lat": lat, "lng": lng},
                station_name=station.get('name'),
                distance_km=station.get('distance_km'),
                raw_data={"measurements": measurements, "station": station}
            )
            
            # Set pollutant values (average recent measurements)
            for param, values in parameter_values.items():
                if values:
                    avg_value = sum(v['value'] for v in values) / len(values)
                    
                    if param == 'pm25':
                        air_quality_data.pm25 = round(avg_value, 2)
                    elif param == 'pm10':
                        air_quality_data.pm10 = round(avg_value, 2)
                    elif param == 'ozone':
                        air_quality_data.ozone = round(avg_value, 2)
                    elif param == 'nitrogen_dioxide':
                        air_quality_data.nitrogen_dioxide = round(avg_value, 2)
                    elif param == 'sulfur_dioxide':
                        air_quality_data.sulfur_dioxide = round(avg_value, 2)
                    elif param == 'carbon_monoxide':
                        air_quality_data.carbon_monoxide = round(avg_value, 2)
            
            # Calculate AQI
            aqi_value = await self._calculate_aqi(air_quality_data)
            air_quality_data.aqi = aqi_value
            air_quality_data.aqi_category = await self._get_aqi_category(aqi_value)
            
            # Calculate data quality score
            data_points = len([v for v in asdict(air_quality_data).values() if v is not None])
            completeness = data_points / 12  # Total possible parameters
            age_hours = 0 if latest_timestamp else 1
            has_errors = len(measurements) < 3
            
            air_quality_data.data_quality_score = calculate_data_quality_score(
                data_points, completeness, age_hours, has_errors
            )
            
            return air_quality_data
            
        except Exception as e:
            services_logger.error(f"Error parsing air quality data: {str(e)}")
            return None
    
    async def _calculate_aqi(self, data: AirQualityData) -> Optional[int]:
        """Calculate Air Quality Index based on pollutant concentrations"""
        try:
            aqi_values = []
            
            # Calculate AQI for each available pollutant
            if data.pm25 is not None:
                pm25_aqi = self._pollutant_to_aqi('pm25', data.pm25)
                if pm25_aqi is not None:
                    aqi_values.append(pm25_aqi)
            
            if data.pm10 is not None:
                pm10_aqi = self._pollutant_to_aqi('pm10', data.pm10)
                if pm10_aqi is not None:
                    aqi_values.append(pm10_aqi)
            
            if data.ozone is not None:
                ozone_aqi = self._pollutant_to_aqi('o3', data.ozone)
                if ozone_aqi is not None:
                    aqi_values.append(ozone_aqi)
            
            if data.nitrogen_dioxide is not None:
                no2_aqi = self._pollutant_to_aqi('no2', data.nitrogen_dioxide)
                if no2_aqi is not None:
                    aqi_values.append(no2_aqi)
            
            # Return the highest AQI value (most restrictive)
            return max(aqi_values) if aqi_values else None
            
        except Exception as e:
            services_logger.error(f"Error calculating AQI: {str(e)}")
            return None
    
    def _pollutant_to_aqi(self, pollutant: str, concentration: float) -> Optional[int]:
        """Convert pollutant concentration to AQI value"""
        try:
            if pollutant not in self.aqi_breakpoints:
                return None
            
            breakpoints = self.aqi_breakpoints[pollutant]
            
            for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
                if bp_lo <= concentration <= bp_hi:
                    # Linear interpolation
                    aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (concentration - bp_lo) + aqi_lo
                    return round(aqi)
            
            # If concentration is above all breakpoints, return maximum AQI
            return 500
            
        except Exception as e:
            services_logger.error(f"Error converting pollutant to AQI: {str(e)}")
            return None
    
    async def _get_aqi_category(self, aqi: Optional[int]) -> Optional[str]:
        """Get AQI category name from AQI value"""
        try:
            if aqi is None:
                return None
            
            for (low, high), category in self.aqi_categories.items():
                if low <= aqi <= high:
                    return category
            
            return "Hazardous"  # Above 500
            
        except Exception as e:
            services_logger.error(f"Error getting AQI category: {str(e)}")
            return None
    
    async def _make_request(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make HTTP request to OpenAQ API"""
        for attempt in range(self.retry_attempts):
            try:
                headers = {"Accept": "application/json"}
                if self.api_key:
                    headers["X-API-Key"] = self.api_key
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    
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
                "service": "AirQualityService",
                "api_provider": "OpenAQ",
                "api_key_configured": bool(self.api_key),
                "rate_limit": self.rate_limit,
                "current_request_count": self.request_count,
                "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
                "timeout": self.timeout,
                "retry_attempts": self.retry_attempts
            }
            
            # Test API connectivity
            test_response = await self._make_request(
                f"{self.base_url}/locations",
                {"limit": 1}
            )
            status["api_accessible"] = bool(test_response)
            
            return status
            
        except Exception as e:
            services_logger.error(f"Error getting service status: {str(e)}")
            return {"error": str(e)}

# Global instance
air_quality_service = AirQualityService()