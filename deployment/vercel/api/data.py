"""
Ocean Sentinel - Data API Endpoint
Serverless function for environmental data collection
"""

import json
import os
import sys
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

# Add backend path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

try:
    from backend.app.services.weather_service import weather_service
    from backend.app.services.air_quality_service import air_quality_service
    from backend.app.services.ocean_service import ocean_service
    from backend.app.ml_models.data_preprocessing import data_preprocessor
    from backend.app.utils.blockchain_utils import blockchain_utils
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    """Data API serverless function handler"""
    
    def do_GET(self):
        """Handle GET requests for environmental data"""
        try:
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Remove /api/data prefix
            route = route.replace('/api/data', '').strip('/')
            
            if route == '' or route == 'status':
                self._send_data_status()
            elif route == 'weather':
                self._handle_weather_data(query_params)
            elif route == 'air-quality':
                self._handle_air_quality_data(query_params)
            elif route == 'ocean':
                self._handle_ocean_data(query_params)
            elif route == 'combined':
                self._handle_combined_data(query_params)
            elif route == 'sources':
                self._handle_data_sources()
            elif route == 'quality':
                self._handle_data_quality(query_params)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_POST(self):
        """Handle POST requests for data submission"""
        try:
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self._send_error_response("Invalid JSON data", 400)
                return
            
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path.replace('/api/data', '').strip('/')
            
            if route == 'submit':
                self._handle_data_submission(data)
            elif route == 'validate':
                self._handle_data_validation(data)
            elif route == 'process':
                self._handle_data_processing(data)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._send_cors_response()
    
    def _send_data_status(self):
        """Send data API status"""
        status_data = {
            "service": "Environmental Data API",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "backend_available": BACKEND_AVAILABLE,
            "data_sources": {
                "weather": {
                    "provider": "OpenWeatherMap",
                    "available": bool(os.getenv("OPENWEATHER_API_KEY")),
                    "parameters": ["temperature", "humidity", "pressure", "wind_speed", "precipitation"]
                },
                "air_quality": {
                    "provider": "OpenAQ",
                    "available": True,  # Free API
                    "parameters": ["pm25", "pm10", "ozone", "no2", "so2", "co"]
                },
                "ocean": {
                    "provider": "NOAA",
                    "available": True,  # Free API
                    "parameters": ["tide_level", "water_temperature", "wave_height", "salinity"]
                }
            },
            "capabilities": {
                "real_time_collection": BACKEND_AVAILABLE,
                "historical_data": BACKEND_AVAILABLE,
                "data_preprocessing": BACKEND_AVAILABLE,
                "blockchain_verification": bool(os.getenv("STARTON_API_KEY"))
            },
            "endpoints": [
                "GET /api/data/weather?lat={lat}&lng={lng}",
                "GET /api/data/air-quality?lat={lat}&lng={lng}",
                "GET /api/data/ocean?lat={lat}&lng={lng}",
                "GET /api/data/combined?lat={lat}&lng={lng}",
                "POST /api/data/submit",
                "POST /api/data/validate"
            ]
        }
        
        self._send_json_response(status_data)
    
    def _handle_weather_data(self, query_params):
        """Handle weather data request"""
        try:
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            # Extract parameters
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            include_forecast = self._get_bool_param(query_params, 'forecast', False)
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                self._send_error_response("Invalid coordinates", 400)
                return
            
            # Get weather data
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._fetch_weather_data(lat, lng, include_forecast))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Weather data request failed: {str(e)}")
    
    def _handle_air_quality_data(self, query_params):
        """Handle air quality data request"""
        try:
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            radius = self._get_int_param(query_params, 'radius', 25)
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Get air quality data
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._fetch_air_quality_data(lat, lng, radius))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Air quality data request failed: {str(e)}")
    
    def _handle_ocean_data(self, query_params):
        """Handle ocean data request"""
        try:
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            include_tides = self._get_bool_param(query_params, 'tides', True)
            include_waves = self._get_bool_param(query_params, 'waves', True)
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Get ocean data
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    self._fetch_ocean_data(lat, lng, include_tides, include_waves)
                )
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Ocean data request failed: {str(e)}")
    
    def _handle_combined_data(self, query_params):
        """Handle combined environmental data request"""
        try:
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Get combined data
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._fetch_combined_data(lat, lng))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Combined data request failed: {str(e)}")
    
    def _handle_data_sources(self):
        """Handle data sources information request"""
        sources_data = {
            "available_sources": [
                {
                    "name": "OpenWeatherMap",
                    "type": "weather",
                    "description": "Global weather data including current conditions and forecasts",
                    "parameters": [
                        "temperature", "humidity", "pressure", "wind_speed", 
                        "wind_direction", "precipitation", "cloud_cover", "visibility"
                    ],
                    "update_frequency": "15 minutes",
                    "geographic_coverage": "global",
                    "api_status": "configured" if os.getenv("OPENWEATHER_API_KEY") else "not_configured"
                },
                {
                    "name": "OpenAQ",
                    "type": "air_quality",
                    "description": "Global air quality measurements from monitoring stations",
                    "parameters": ["pm25", "pm10", "ozone", "no2", "so2", "co"],
                    "update_frequency": "1 hour",
                    "geographic_coverage": "global (station-based)",
                    "api_status": "available"
                },
                {
                    "name": "NOAA Tides & Currents",
                    "type": "ocean",
                    "description": "Ocean and coastal data from NOAA monitoring stations",
                    "parameters": [
                        "tide_level", "water_temperature", "wave_height", 
                        "wave_period", "salinity", "atmospheric_pressure"
                    ],
                    "update_frequency": "6 minutes",
                    "geographic_coverage": "US coastal waters",
                    "api_status": "available"
                }
            ],
            "data_quality_metrics": {
                "completeness_threshold": 0.7,
                "freshness_threshold_hours": 24,
                "accuracy_confidence_threshold": 0.8
            },
            "blockchain_integration": {
                "enabled": bool(os.getenv("STARTON_API_KEY")),
                "purpose": "data integrity verification",
                "network": "Polygon"
            }
        }
        
        self._send_json_response(sources_data)
    
    def _handle_data_quality(self, query_params):
        """Handle data quality assessment request"""
        try:
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            
            # Mock data quality assessment
            quality_data = {
                "location": {"lat": lat, "lng": lng} if lat and lng else None,
                "assessment_timestamp": datetime.now().isoformat(),
                "overall_score": 85.2,
                "data_sources_quality": [
                    {
                        "source": "weather",
                        "completeness": 0.95,
                        "freshness_hours": 0.25,
                        "accuracy_score": 0.92,
                        "overall_quality": 92.3,
                        "issues": []
                    },
                    {
                        "source": "air_quality",
                        "completeness": 0.78,
                        "freshness_hours": 2.1,
                        "accuracy_score": 0.87,
                        "overall_quality": 78.9,
                        "issues": ["limited_station_coverage"]
                    },
                    {
                        "source": "ocean",
                        "completeness": 0.65,
                        "freshness_hours": 4.5,
                        "accuracy_score": 0.89,
                        "overall_quality": 74.8,
                        "issues": ["sparse_station_network", "weather_dependent"]
                    }
                ],
                "recommendations": [
                    "Consider additional air quality stations for better coverage",
                    "Ocean data may be limited in this region",
                    "Overall data quality is good for threat detection"
                ]
            }
            
            self._send_json_response(quality_data)
            
        except Exception as e:
            self._send_error_response(f"Data quality assessment failed: {str(e)}")
    
    def _handle_data_submission(self, data):
        """Handle external data submission"""
        try:
            # Validate required fields
            required_fields = ['source', 'data_type', 'location', 'timestamp', 'measurements']
            for field in required_fields:
                if field not in data:
                    self._send_error_response(f"Missing required field: {field}", 400)
                    return
            
            # Process submission
            submission_data = {
                "submission_id": f"SUB-{int(datetime.now().timestamp())}",
                "source": data['source'],
                "data_type": data['data_type'],
                "location": data['location'],
                "timestamp": data['timestamp'],
                "measurements": data['measurements'],
                "submitted_at": datetime.now().isoformat(),
                "status": "received",
                "quality_score": None,
                "verified": False
            }
            
            # Log to blockchain if available
            if os.getenv("STARTON_API_KEY"):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    blockchain_record = loop.run_until_complete(
                        blockchain_utils.log_environmental_data(
                            submission_data,
                            data['location'],
                            "data_submission"
                        )
                    )
                    
                    if blockchain_record:
                        submission_data["blockchain_hash"] = blockchain_record.transaction_hash
                        submission_data["verified"] = True
                        submission_data["status"] = "verified"
                finally:
                    loop.close()
            
            response_data = {
                "success": True,
                "message": "Data submission received successfully",
                "submission": submission_data
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Data submission failed: {str(e)}")
    
    def _handle_data_validation(self, data):
        """Handle data validation request"""
        try:
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            if 'data' not in data:
                self._send_error_response("Missing data field", 400)
                return
            
            # Run data validation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._validate_data(data['data']))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Data validation failed: {str(e)}")
    
    def _handle_data_processing(self, data):
        """Handle data processing request"""
        try:
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            if 'data' not in data:
                self._send_error_response("Missing data field", 400)
                return
            
            # Run data processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._process_data(data['data']))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Data processing failed: {str(e)}")
    
    async def _fetch_weather_data(self, lat: float, lng: float, include_forecast: bool):
        """Fetch weather data from service"""
        try:
            # Get current weather
            weather_data = await weather_service.get_current_weather(lat, lng, include_forecast)
            
            result = {
                "data_type": "weather",
                "location": {"lat": lat, "lng": lng},
                "timestamp": datetime.now().isoformat(),
                "current": None,
                "forecast": None
            }
            
            if weather_data:
                result["current"] = {
                    "temperature": weather_data.temperature,
                    "apparent_temperature": weather_data.apparent_temperature,
                    "humidity": weather_data.humidity,
                    "pressure": weather_data.pressure,
                    "wind_speed": weather_data.wind_speed,
                    "wind_direction": weather_data.wind_direction,
                    "precipitation": weather_data.precipitation,
                    "cloud_cover": weather_data.cloud_cover,
                    "visibility": weather_data.visibility,
                    "weather_condition": weather_data.weather_condition,
                    "data_quality_score": weather_data.data_quality_score,
                    "timestamp": weather_data.timestamp
                }
            
            if include_forecast:
                forecast_data = await weather_service.get_weather_forecast(lat, lng, 24)
                if forecast_data:
                    result["forecast"] = [
                        {
                            "timestamp": f.timestamp,
                            "temperature": f.temperature,
                            "precipitation": f.precipitation,
                            "wind_speed": f.wind_speed,
                            "weather_condition": f.weather_condition
                        } for f in forecast_data[:6]  # Next 6 hours
                    ]
            
            return result
            
        except Exception as e:
            return {
                "data_type": "weather",
                "location": {"lat": lat, "lng": lng},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _fetch_air_quality_data(self, lat: float, lng: float, radius: int):
        """Fetch air quality data from service"""
        try:
            aq_data = await air_quality_service.get_current_air_quality(lat, lng, radius)
            
            result = {
                "data_type": "air_quality",
                "location": {"lat": lat, "lng": lng},
                "search_radius_km": radius,
                "timestamp": datetime.now().isoformat(),
                "data": None
            }
            
            if aq_data:
                result["data"] = {
                    "station_name": aq_data.station_name,
                    "distance_km": aq_data.distance_km,
                    "pm25": aq_data.pm25,
                    "pm10": aq_data.pm10,
                    "ozone": aq_data.ozone,
                    "nitrogen_dioxide": aq_data.nitrogen_dioxide,
                    "sulfur_dioxide": aq_data.sulfur_dioxide,
                    "carbon_monoxide": aq_data.carbon_monoxide,
                    "aqi": aq_data.aqi,
                    "aqi_category": aq_data.aqi_category,
                    "data_quality_score": aq_data.data_quality_score,
                    "timestamp": aq_data.timestamp
                }
            
            return result
            
        except Exception as e:
            return {
                "data_type": "air_quality",
                "location": {"lat": lat, "lng": lng},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _fetch_ocean_data(self, lat: float, lng: float, include_tides: bool, include_waves: bool):
        """Fetch ocean data from service"""
        try:
            ocean_data = await ocean_service.get_current_ocean_data(lat, lng)
            
            result = {
                "data_type": "ocean",
                "location": {"lat": lat, "lng": lng},
                "timestamp": datetime.now().isoformat(),
                "current_conditions": None,
                "tides": None,
                "waves": None
            }
            
            if ocean_data:
                result["current_conditions"] = {
                    "station_name": ocean_data.station_name,
                    "distance_km": ocean_data.distance_km,
                    "tide_level": ocean_data.tide_level,
                    "water_temperature": ocean_data.water_temperature,
                    "salinity": ocean_data.salinity,
                    "wave_height": ocean_data.wave_height,
                    "atmospheric_pressure": ocean_data.atmospheric_pressure,
                    "visibility": ocean_data.visibility,
                    "data_quality_score": ocean_data.data_quality_score,
                    "timestamp": ocean_data.timestamp
                }
            
            if include_tides:
                tide_data = await ocean_service.get_tide_data(lat, lng, 24)
                if tide_data:
                    result["tides"] = tide_data[:12]  # Next 12 hours
            
            if include_waves:
                wave_data = await ocean_service.get_wave_data(lat, lng, 24)
                if wave_data:
                    result["waves"] = wave_data[:12]  # Next 12 hours
            
            return result
            
        except Exception as e:
            return {
                "data_type": "ocean",
                "location": {"lat": lat, "lng": lng},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _fetch_combined_data(self, lat: float, lng: float):
        """Fetch combined environmental data"""
        try:
            # Fetch all data types concurrently
            weather_task = asyncio.create_task(self._fetch_weather_data(lat, lng, False))
            air_quality_task = asyncio.create_task(self._fetch_air_quality_data(lat, lng, 25))
            ocean_task = asyncio.create_task(self._fetch_ocean_data(lat, lng, True, True))
            
            weather_result, aq_result, ocean_result = await asyncio.gather(
                weather_task, air_quality_task, ocean_task, return_exceptions=True
            )
            
            # Combine results
            combined_result = {
                "location": {"lat": lat, "lng": lng},
                "timestamp": datetime.now().isoformat(),
                "weather": weather_result if not isinstance(weather_result, Exception) else None,
                "air_quality": aq_result if not isinstance(aq_result, Exception) else None,
                "ocean": ocean_result if not isinstance(ocean_result, Exception) else None,
                "data_sources_available": 0,
                "overall_data_quality": 0.0
            }
            
            # Calculate summary stats
            sources_count = 0
            quality_scores = []
            
            for data_type in ['weather', 'air_quality', 'ocean']:
                data = combined_result[data_type]
                if data and 'error' not in data:
                    sources_count += 1
                    
                    # Extract quality score
                    if data_type == 'weather' and data.get('current'):
                        score = data['current'].get('data_quality_score')
                    elif data_type == 'air_quality' and data.get('data'):
                        score = data['data'].get('data_quality_score')
                    elif data_type == 'ocean' and data.get('current_conditions'):
                        score = data['current_conditions'].get('data_quality_score')
                    else:
                        score = None
                    
                    if score is not None:
                        quality_scores.append(score)
            
            combined_result["data_sources_available"] = sources_count
            combined_result["overall_data_quality"] = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            )
            
            return combined_result
            
        except Exception as e:
            return {
                "location": {"lat": lat, "lng": lng},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _validate_data(self, data):
        """Validate environmental data"""
        try:
            # Use data preprocessor for validation
            validation_result = await data_preprocessor.validate_data(data)
            
            return {
                "validation_timestamp": datetime.now().isoformat(),
                "is_valid": validation_result.is_valid if validation_result else False,
                "quality_score": validation_result.quality_score if validation_result else 0.0,
                "issues": validation_result.issues if validation_result else [],
                "recommendations": validation_result.recommendations if validation_result else []
            }
            
        except Exception as e:
            return {
                "validation_timestamp": datetime.now().isoformat(),
                "error": str(e),
                "is_valid": False
            }
    
    async def _process_data(self, data):
        """Process environmental data"""
        try:
            # Use data preprocessor for processing
            processed_result = await data_preprocessor.preprocess_environmental_data(data)
            
            return {
                "processing_timestamp": datetime.now().isoformat(),
                "success": processed_result.success if processed_result else False,
                "processed_data": processed_result.processed_data if processed_result else None,
                "transformations_applied": processed_result.transformations_applied if processed_result else [],
                "quality_improvements": processed_result.quality_improvements if processed_result else {}
            }
            
        except Exception as e:
            return {
                "processing_timestamp": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            }
    
    def _get_float_param(self, query_params, key):
        """Extract float parameter from query string"""
        try:
            values = query_params.get(key, [])
            return float(values[0]) if values else None
        except (ValueError, IndexError):
            return None
    
    def _get_int_param(self, query_params, key, default=None):
        """Extract integer parameter from query string"""
        try:
            values = query_params.get(key, [])
            return int(values[0]) if values else default
        except (ValueError, IndexError):
            return default
    
    def _get_bool_param(self, query_params, key, default=False):
        """Extract boolean parameter from query string"""
        try:
            values = query_params.get(key, [])
            if not values:
                return default
            value = values[0].lower()
            return value in ('true', '1', 'yes', 'on')
        except (AttributeError, IndexError):
            return default
    
    def _send_not_found_response(self):
        """Send 404 not found response"""
        error_data = {
            "error": True,
            "message": "Data endpoint not found",
            "status_code": 404,
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [
                "/api/data/weather",
                "/api/data/air-quality",
                "/api/data/ocean",
                "/api/data/combined",
                "/api/data/sources",
                "/api/data/quality"
            ]
        }
        
        self._send_json_response(error_data, status_code=404)
    
    def _send_error_response(self, error_message: str, status_code: int = 500):
        """Send error response"""
        error_data = {
            "error": True,
            "message": error_message,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat(),
            "service": "data"
        }
        
        self._send_json_response(error_data, status_code=status_code)
    
    def _send_cors_response(self):
        """Send CORS response"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def _send_json_response(self, data: dict, status_code: int = 200):
        """Send JSON response with proper headers"""
        json_data = json.dumps(data, indent=2)
        
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(json_data)))
        self.send_header('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
        self.end_headers()
        
        self.wfile.write(json_data.encode('utf-8'))
    
    def _set_cors_headers(self):
        """Set CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '3600')