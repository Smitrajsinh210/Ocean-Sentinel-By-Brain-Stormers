"""
Ocean Sentinel - Weather Service
OpenWeatherMap API integration for weather data collection
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import httpx
import json
from dataclasses import dataclass, asdict

# Import from our services package
from . import services_logger, get_service_config, standardize_parameter_name, validate_coordinates, calculate_data_quality_score

@dataclass
class WeatherData:
    """Weather data structure"""
    timestamp: str
    location: Dict[str, float]  # {"lat": float, "lng": float}
    temperature: Optional[float] = None
    apparent_temperature: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    pressure: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    visibility: Optional[float] = None
    cloud_cover: Optional[float] = None
    precipitation: Optional[float] = None
    weather_condition: Optional[str] = None
    weather_description: Optional[str] = None
    data_quality_score: Optional[float] = None
    source: str = "OpenWeatherMap"
    raw_data: Optional[Dict[str, Any]] = None

class WeatherService:
    """
    Weather data service using OpenWeatherMap API
    Provides current weather, forecasts, and historical data
    """
    
    def __init__(self):
        self.config = get_service_config("weather")
        self.base_url = self.config.get("base_url", "https://api.openweathermap.org/data/2.5")
        self.api_key = os.environ.get("998a7ebf2ff55fb5292259730cb84119")
        self.timeout = self.config.get("timeout", 30)
        self.retry_attempts = self.config.get("retry_attempts", 3)
        self.rate_limit = self.config.get("rate_limit", 60)
        
        # Rate limiting
        self.last_request_time = None
        self.request_count = 0
        self.request_window_start = datetime.now()
        
        services_logger.info("WeatherService initialized")
    
    async def get_current_weather(
        self, 
        lat: float, 
        lng: float,
        include_forecast: bool = False
    ) -> Optional[WeatherData]:
        """
        Get current weather data for specified coordinates
        """
        try:
            # Validate coordinates
            if not validate_coordinates(lat, lng):
                services_logger.error(f"Invalid coordinates: {lat}, {lng}")
                return None
            
            # Check API key
            if not self.api_key:
                services_logger.error("OpenWeatherMap API key not found")
                return None
            
            # Rate limiting check
            if not await self._check_rate_limit():
                services_logger.warning("Rate limit exceeded for weather service")
                await asyncio.sleep(60)  # Wait 1 minute
            
            # Prepare request parameters
            params = {
                "lat": lat,
                "lon": lng,
                "appid": self.api_key,
                "units": "metric",  # Celsius, km/h, etc.
                "exclude": "minutely,daily,alerts" if not include_forecast else "minutely,alerts"
            }
            
            # Make API request
            url = f"{self.base_url}/onecall"
            weather_data = await self._make_request(url, params)
            
            if not weather_data:
                return None
            
            # Parse and standardize weather data
            parsed_data = await self._parse_weather_data(weather_data, lat, lng)
            
            services_logger.info(f"Retrieved current weather for coordinates {lat}, {lng}")
            return parsed_data
            
        except Exception as e:
            services_logger.error(f"Error getting current weather: {str(e)}")
            return None
    
    async def get_weather_forecast(
        self,
        lat: float,
        lng: float,
        hours: int = 24
    ) -> List[WeatherData]:
        """
        Get weather forecast for specified coordinates and time range
        """
        try:
            # Validate inputs
            if not validate_coordinates(lat, lng):
                services_logger.error(f"Invalid coordinates: {lat}, {lng}")
                return []
            
            if not self.api_key:
                services_logger.error("OpenWeatherMap API key not found")
                return []
            
            # Rate limiting check
            if not await self._check_rate_limit():
                await asyncio.sleep(60)
            
            # Prepare request
            params = {
                "lat": lat,
                "lon": lng,
                "appid": self.api_key,
                "units": "metric",
                "exclude": "current,minutely,daily,alerts"
            }
            
            url = f"{self.base_url}/onecall"
            forecast_data = await self._make_request(url, params)
            
            if not forecast_data or 'hourly' not in forecast_data:
                return []
            
            # Parse hourly forecast data
            forecast_list = []
            hourly_data = forecast_data['hourly'][:hours]  # Limit to requested hours
            
            for hour_data in hourly_data:
                parsed_hour = await self._parse_hourly_data(hour_data, lat, lng)
                if parsed_hour:
                    forecast_list.append(parsed_hour)
            
            services_logger.info(f"Retrieved {len(forecast_list)} hour weather forecast")
            return forecast_list
            
        except Exception as e:
            services_logger.error(f"Error getting weather forecast: {str(e)}")
            return []
    
    async def get_weather_history(
        self,
        lat: float,
        lng: float,
        start_time: datetime,
        end_time: datetime
    ) -> List[WeatherData]:
        """
        Get historical weather data (requires time machine API - paid feature)
        """
        try:
            if not validate_coordinates(lat, lng):
                return []
            
            if not self.api_key:
                return []
            
            # Calculate time range in days
            time_diff = end_time - start_time
            if time_diff.days > 5:  # Limit to 5 days for free tier
                services_logger.warning("Historical data limited to 5 days")
                end_time = start_time + timedelta(days=5)
            
            historical_data = []
            current_time = start_time
            
            while current_time < end_time:
                # Rate limiting
                if not await self._check_rate_limit():
                    await asyncio.sleep(60)
                
                timestamp = int(current_time.timestamp())
                params = {
                    "lat": lat,
                    "lon": lng,
                    "dt": timestamp,
                    "appid": self.api_key,
                    "units": "metric"
                }
                
                url = f"{self.base_url}/onecall/timemachine"
                day_data = await self._make_request(url, params)
                
                if day_data and 'current' in day_data:
                    parsed_data = await self._parse_weather_data(day_data, lat, lng)
                    if parsed_data:
                        historical_data.append(parsed_data)
                
                current_time += timedelta(hours=6)  # Get data every 6 hours
            
            services_logger.info(f"Retrieved {len(historical_data)} historical weather records")
            return historical_data
            
        except Exception as e:
            services_logger.error(f"Error getting historical weather: {str(e)}")
            return []
    
    async def get_air_quality_weather(
        self,
        lat: float,
        lng: float
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather conditions that affect air quality
        """
        try:
            weather_data = await self.get_current_weather(lat, lng)
            
            if not weather_data:
                return None
            
            # Extract air quality relevant parameters
            aq_weather = {
                "temperature": weather_data.temperature,
                "humidity": weather_data.humidity,
                "wind_speed": weather_data.wind_speed,
                "wind_direction": weather_data.wind_direction,
                "pressure": weather_data.pressure,
                "visibility": weather_data.visibility,
                "precipitation": weather_data.precipitation,
                "timestamp": weather_data.timestamp,
                "location": weather_data.location
            }
            
            return aq_weather
            
        except Exception as e:
            services_logger.error(f"Error getting air quality weather: {str(e)}")
            return None
    
    async def _make_request(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make HTTP request to OpenWeatherMap API"""
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 401:
                        services_logger.error("Invalid API key for OpenWeatherMap")
                        return None
                    elif response.status_code == 429:
                        services_logger.warning("Rate limit exceeded, retrying...")
                        await asyncio.sleep(60)
                        continue
                    else:
                        services_logger.error(f"API request failed: {response.status_code}")
                        
            except httpx.TimeoutException:
                services_logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                services_logger.error(f"Request error: {str(e)}")
                
        return None
    
    async def _parse_weather_data(
        self, 
        raw_data: Dict[str, Any], 
        lat: float, 
        lng: float
    ) -> Optional[WeatherData]:
        """Parse raw weather data from API response"""
        try:
            current = raw_data.get('current', {})
            
            # Extract weather parameters
            weather_data = WeatherData(
                timestamp=datetime.now().isoformat(),
                location={"lat": lat, "lng": lng},
                temperature=current.get('temp'),
                apparent_temperature=current.get('feels_like'),
                pressure=current.get('pressure'),
                humidity=current.get('humidity'),
                wind_speed=current.get('wind_speed'),
                wind_direction=current.get('wind_deg'),
                visibility=current.get('visibility', 0) / 1000 if current.get('visibility') else None,  # Convert to km
                cloud_cover=current.get('clouds'),
                raw_data=raw_data
            )
            
            # Extract weather condition
            weather_list = current.get('weather', [])
            if weather_list:
                weather_data.weather_condition = weather_list[0].get('main')
                weather_data.weather_description = weather_list[0].get('description')
            
            # Handle precipitation (rain/snow)
            if 'rain' in current:
                weather_data.precipitation = current['rain'].get('1h', 0)
            elif 'snow' in current:
                weather_data.precipitation = current['snow'].get('1h', 0)
            
            # Calculate data quality score
            data_points = len([v for v in asdict(weather_data).values() if v is not None])
            completeness = data_points / 15  # Total possible parameters
            age_hours = 0  # Current data
            has_errors = False
            
            weather_data.data_quality_score = calculate_data_quality_score(
                data_points, completeness, age_hours, has_errors
            )
            
            return weather_data
            
        except Exception as e:
            services_logger.error(f"Error parsing weather data: {str(e)}")
            return None
    
    async def _parse_hourly_data(
        self,
        hour_data: Dict[str, Any],
        lat: float,
        lng: float
    ) -> Optional[WeatherData]:
        """Parse hourly forecast data"""
        try:
            timestamp = datetime.fromtimestamp(hour_data.get('dt', 0)).isoformat()
            
            weather_data = WeatherData(
                timestamp=timestamp,
                location={"lat": lat, "lng": lng},
                temperature=hour_data.get('temp'),
                apparent_temperature=hour_data.get('feels_like'),
                pressure=hour_data.get('pressure'),
                humidity=hour_data.get('humidity'),
                wind_speed=hour_data.get('wind_speed'),
                wind_direction=hour_data.get('wind_deg'),
                visibility=hour_data.get('visibility', 0) / 1000 if hour_data.get('visibility') else None,
                cloud_cover=hour_data.get('clouds'),
                raw_data=hour_data
            )
            
            # Weather condition
            weather_list = hour_data.get('weather', [])
            if weather_list:
                weather_data.weather_condition = weather_list[0].get('main')
                weather_data.weather_description = weather_list[0].get('description')
            
            # Precipitation
            if 'rain' in hour_data:
                weather_data.precipitation = hour_data['rain'].get('1h', 0)
            elif 'snow' in hour_data:
                weather_data.precipitation = hour_data['snow'].get('1h', 0)
            
            return weather_data
            
        except Exception as e:
            services_logger.error(f"Error parsing hourly data: {str(e)}")
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
            return True  # Allow request if check fails
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service health and status information"""
        try:
            status = {
                "service": "WeatherService",
                "api_provider": "OpenWeatherMap",
                "api_key_configured": bool(self.api_key),
                "rate_limit": self.rate_limit,
                "current_request_count": self.request_count,
                "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
                "timeout": self.timeout,
                "retry_attempts": self.retry_attempts
            }
            
            # Test API connectivity
            if self.api_key:
                test_response = await self._make_request(
                    f"{self.base_url}/weather",
                    {"q": "London", "appid": self.api_key, "units": "metric"}
                )
                status["api_accessible"] = bool(test_response)
            else:
                status["api_accessible"] = False
            
            return status
            
        except Exception as e:
            services_logger.error(f"Error getting service status: {str(e)}")
            return {"error": str(e)}

# Global instance
weather_service = WeatherService()