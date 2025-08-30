"""
Ocean Sentinel - Threats API Endpoint
Serverless function for threat detection and management
"""

import json
import os
import sys
import asyncio
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

# Add backend path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

try:
    from backend.app.ml_models.threat_detection import threat_detector
    from backend.app.ml_models.anomaly_detection import anomaly_detector
    from backend.app.ml_models.prediction_models import threat_predictor
    from backend.app.services.weather_service import weather_service
    from backend.app.services.air_quality_service import air_quality_service
    from backend.app.services.ocean_service import ocean_service
    from backend.app.utils.blockchain_utils import blockchain_utils
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    """Threats API serverless function handler"""
    
    def do_GET(self):
        """Handle GET requests for threat data"""
        try:
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            if not BACKEND_AVAILABLE:
                self._send_error_response("Backend services not available", 503)
                return
            
            # Remove /api/threats prefix
            route = route.replace('/api/threats', '').strip('/')
            
            if route == '' or route == 'status':
                self._send_threats_status()
            elif route == 'detect':
                self._handle_threat_detection(query_params)
            elif route == 'predict':
                self._handle_threat_prediction(query_params)
            elif route == 'anomalies':
                self._handle_anomaly_detection(query_params)
            elif route == 'history':
                self._handle_threat_history(query_params)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_POST(self):
        """Handle POST requests for threat reporting"""
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
            route = parsed_url.path.replace('/api/threats', '').strip('/')
            
            if route == 'report':
                self._handle_threat_report(data)
            elif route == 'verify':
                self._handle_threat_verification(data)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._send_cors_response()
    
    def _send_threats_status(self):
        """Send threats API status"""
        status_data = {
            "service": "Threats API",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "backend_available": BACKEND_AVAILABLE,
            "capabilities": {
                "threat_detection": BACKEND_AVAILABLE,
                "anomaly_detection": BACKEND_AVAILABLE,
                "threat_prediction": BACKEND_AVAILABLE,
                "blockchain_verification": bool(os.getenv("STARTON_API_KEY"))
            },
            "endpoints": [
                "GET /api/threats/detect?lat={lat}&lng={lng}",
                "GET /api/threats/predict?lat={lat}&lng={lng}&hours={hours}",
                "GET /api/threats/anomalies?lat={lat}&lng={lng}",
                "GET /api/threats/history?lat={lat}&lng={lng}&days={days}",
                "POST /api/threats/report",
                "POST /api/threats/verify"
            ]
        }
        
        self._send_json_response(status_data)
    
    def _handle_threat_detection(self, query_params):
        """Handle threat detection request"""
        try:
            # Extract coordinates
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                self._send_error_response("Invalid coordinates", 400)
                return
            
            # Run threat detection
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._run_threat_detection(lat, lng))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Threat detection failed: {str(e)}")
    
    def _handle_threat_prediction(self, query_params):
        """Handle threat prediction request"""
        try:
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            hours = self._get_int_param(query_params, 'hours', 4)
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Run threat prediction
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._run_threat_prediction(lat, lng, hours))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Threat prediction failed: {str(e)}")
    
    def _handle_anomaly_detection(self, query_params):
        """Handle anomaly detection request"""
        try:
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Run anomaly detection
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._run_anomaly_detection(lat, lng))
                self._send_json_response(result)
            finally:
                loop.close()
                
        except Exception as e:
            self._send_error_response(f"Anomaly detection failed: {str(e)}")
    
    def _handle_threat_history(self, query_params):
        """Handle threat history request"""
        try:
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            days = self._get_int_param(query_params, 'days', 7)
            
            if lat is None or lng is None:
                self._send_error_response("Missing lat or lng parameters", 400)
                return
            
            # Mock threat history (would integrate with database in production)
            history_data = {
                "location": {"lat": lat, "lng": lng},
                "period_days": days,
                "threats_detected": [
                    {
                        "timestamp": (datetime.now()).isoformat(),
                        "threat_type": "storm",
                        "severity": 3,
                        "confidence": 0.85,
                        "description": "Moderate storm system approaching"
                    }
                ],
                "total_threats": 1,
                "summary": {
                    "high_severity": 0,
                    "medium_severity": 1,
                    "low_severity": 0
                }
            }
            
            self._send_json_response(history_data)
            
        except Exception as e:
            self._send_error_response(f"Threat history failed: {str(e)}")
    
    def _handle_threat_report(self, data):
        """Handle threat reporting"""
        try:
            # Validate required fields
            required_fields = ['location', 'threat_type', 'description']
            for field in required_fields:
                if field not in data:
                    self._send_error_response(f"Missing required field: {field}", 400)
                    return
            
            # Create threat report
            report_data = {
                "report_id": f"TR-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "location": data['location'],
                "threat_type": data['threat_type'],
                "description": data['description'],
                "reporter": data.get('reporter', 'anonymous'),
                "severity": data.get('severity', 'unknown'),
                "status": "reported",
                "verification_required": True
            }
            
            # Log to blockchain if available
            if os.getenv("STARTON_API_KEY"):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    blockchain_record = loop.run_until_complete(
                        blockchain_utils.log_environmental_data(
                            report_data, 
                            data['location'], 
                            "threat_report"
                        )
                    )
                    
                    if blockchain_record:
                        report_data["blockchain_hash"] = blockchain_record.transaction_hash
                        report_data["verified"] = True
                finally:
                    loop.close()
            
            response_data = {
                "success": True,
                "message": "Threat report submitted successfully",
                "report": report_data
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Threat reporting failed: {str(e)}")
    
    def _handle_threat_verification(self, data):
        """Handle threat verification"""
        try:
            # Validate required fields
            if 'report_id' not in data:
                self._send_error_response("Missing report_id", 400)
                return
            
            # Mock verification process
            verification_result = {
                "report_id": data['report_id'],
                "verification_status": "verified",
                "verified_at": datetime.now().isoformat(),
                "verified_by": "ai_system",
                "confidence_score": 0.92,
                "verification_details": {
                    "environmental_data_checked": True,
                    "satellite_imagery_analyzed": True,
                    "historical_patterns_compared": True,
                    "expert_review_pending": False
                }
            }
            
            self._send_json_response(verification_result)
            
        except Exception as e:
            self._send_error_response(f"Threat verification failed: {str(e)}")
    
    async def _run_threat_detection(self, lat: float, lng: float):
        """Run threat detection analysis"""
        try:
            # Collect environmental data
            weather_data = await weather_service.get_current_weather(lat, lng)
            air_quality_data = await air_quality_service.get_current_air_quality(lat, lng)
            ocean_data = await ocean_service.get_current_ocean_data(lat, lng)
            
            # Prepare data for threat detection
            environmental_data = []
            
            if weather_data:
                environmental_data.append({
                    "data_type": "weather",
                    "temperature": weather_data.temperature,
                    "pressure": weather_data.pressure,
                    "humidity": weather_data.humidity,
                    "wind_speed": weather_data.wind_speed,
                    "timestamp": weather_data.timestamp
                })
            
            if air_quality_data:
                environmental_data.append({
                    "data_type": "air_quality",
                    "pm25": air_quality_data.pm25,
                    "pm10": air_quality_data.pm10,
                    "ozone": air_quality_data.ozone,
                    "aqi": air_quality_data.aqi,
                    "timestamp": air_quality_data.timestamp
                })
            
            if ocean_data:
                environmental_data.append({
                    "data_type": "ocean",
                    "water_temperature": ocean_data.water_temperature,
                    "wave_height": ocean_data.wave_height,
                    "tide_level": ocean_data.tide_level,
                    "timestamp": ocean_data.timestamp
                })
            
            # Run threat detection
            threat_result = await threat_detector.detect_threats(
                environmental_data, 
                {"lat": lat, "lng": lng}
            )
            
            # Format response
            return {
                "location": {"lat": lat, "lng": lng},
                "timestamp": datetime.now().isoformat(),
                "threats_detected": threat_result.threats_detected if threat_result else [],
                "overall_threat_level": threat_result.overall_threat_level if threat_result else "unknown",
                "confidence_score": threat_result.confidence_score if threat_result else 0.0,
                "data_sources": len(environmental_data),
                "next_check_recommended": (datetime.now()).isoformat()
            }
            
        except Exception as e:
            return {
                "location": {"lat": lat, "lng": lng},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _run_threat_prediction(self, lat: float, lng: float, hours: int):
        """Run threat prediction analysis"""
        try:
            # Mock prediction data (would use real historical data in production)
            mock_historical_data = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "temperature": 25.0,
                    "pressure": 1013.25,
                    "humidity": 65.0,
                    "wind_speed": 15.0
                }
            ]
            
            # Run prediction
            prediction_result = await threat_predictor.predict_threats(
                mock_historical_data,
                {"lat": lat, "lng": lng},
                [2, 4, hours]
            )
            
            return {
                "location": {"lat": lat, "lng": lng},
                "prediction_hours": hours,
                "timestamp": datetime.now().isoformat(),
                "predictions": prediction_result.predictions if prediction_result else {},
                "forecast_hours": prediction_result.forecast_hours if prediction_result else [],
                "alerts_predicted": prediction_result.alerts_predicted if prediction_result else [],
                "confidence": "medium"
            }
            
        except Exception as e:
            return {
                "location": {"lat": lat, "lng": lng},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _run_anomaly_detection(self, lat: float, lng: float):
        """Run anomaly detection analysis"""
        try:
            # Mock current data
            mock_current_data = [
                {
                    "temperature": 28.5,
                    "pressure": 1010.2,
                    "humidity": 72.0,
                    "timestamp": datetime.now().isoformat()
                }
            ]
            
            # Run anomaly detection
            anomaly_result = await anomaly_detector.detect_anomalies(
                mock_current_data,
                None,
                {"lat": lat, "lng": lng}
            )
            
            return {
                "location": {"lat": lat, "lng": lng},
                "timestamp": datetime.now().isoformat(),
                "is_anomaly": anomaly_result.is_anomaly if anomaly_result else False,
                "anomaly_score": anomaly_result.anomaly_score if anomaly_result else 0.0,
                "severity": anomaly_result.severity if anomaly_result else 1,
                "affected_parameters": anomaly_result.affected_parameters if anomaly_result else [],
                "description": anomaly_result.description if anomaly_result else "No anomalies detected"
            }
            
        except Exception as e:
            return {
                "location": {"lat": lat, "lng": lng},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
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
    
    def _send_not_found_response(self):
        """Send 404 not found response"""
        error_data = {
            "error": True,
            "message": "Threat endpoint not found",
            "status_code": 404,
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [
                "/api/threats/detect",
                "/api/threats/predict",
                "/api/threats/anomalies",
                "/api/threats/history",
                "/api/threats/report",
                "/api/threats/verify"
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
            "service": "threats"
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
        self.send_header('Cache-Control', 's-maxage=60, stale-while-revalidate=300')
        self.end_headers()
        
        self.wfile.write(json_data.encode('utf-8'))
    
    def _set_cors_headers(self):
        """Set CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '3600')