"""
Ocean Sentinel - Alerts API Endpoint  
Serverless function for alert management and notifications
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
    from backend.app.utils.blockchain_utils import blockchain_utils
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    """Alerts API serverless function handler"""
    
    def do_GET(self):
        """Handle GET requests for alert data"""
        try:
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Remove /api/alerts prefix
            route = route.replace('/api/alerts', '').strip('/')
            
            if route == '' or route == 'status':
                self._send_alerts_status()
            elif route == 'active':
                self._handle_active_alerts(query_params)
            elif route == 'history':
                self._handle_alert_history(query_params)
            elif route == 'subscriptions':
                self._handle_get_subscriptions(query_params)
            elif route == 'types':
                self._handle_alert_types()
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_POST(self):
        """Handle POST requests for alert management"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self._send_error_response("Invalid JSON data", 400)
                return
            
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path.replace('/api/alerts', '').strip('/')
            
            if route == 'subscribe':
                self._handle_alert_subscription(data)
            elif route == 'create':
                self._handle_create_alert(data)
            elif route == 'acknowledge':
                self._handle_acknowledge_alert(data)
            elif route == 'test':
                self._handle_test_alert(data)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_PUT(self):
        """Handle PUT requests for alert updates"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self._send_error_response("Invalid JSON data", 400)
                return
            
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path.replace('/api/alerts', '').strip('/')
            
            if route == 'update':
                self._handle_update_alert(data)
            elif route == 'settings':
                self._handle_update_settings(data)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._send_cors_response()
    
    def _send_alerts_status(self):
        """Send alerts API status"""
        status_data = {
            "service": "Alerts API",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "real_time_notifications": bool(os.getenv("PUSHER_KEY")),
                "sms_notifications": bool(os.getenv("TWILIO_SID")),
                "email_notifications": bool(os.getenv("RESEND_API_KEY")),
                "blockchain_logging": bool(os.getenv("STARTON_API_KEY"))
            },
            "notification_channels": [
                "push_notifications",
                "sms",
                "email",
                "webhook"
            ],
            "alert_types": [
                "storm",
                "air_quality",
                "coastal_erosion", 
                "algal_bloom",
                "high_tide",
                "extreme_weather"
            ],
            "endpoints": [
                "GET /api/alerts/active",
                "GET /api/alerts/history",
                "GET /api/alerts/subscriptions",
                "POST /api/alerts/subscribe",
                "POST /api/alerts/create",
                "POST /api/alerts/acknowledge"
            ]
        }
        
        self._send_json_response(status_data)
    
    def _handle_active_alerts(self, query_params):
        """Handle request for active alerts"""
        try:
            # Extract location if provided
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            radius = self._get_int_param(query_params, 'radius', 50)
            severity = query_params.get('severity', [None])[0]
            
            # Mock active alerts (would query database in production)
            active_alerts = []
            
            # Sample active alert
            if lat and lng:
                active_alerts.append({
                    "alert_id": f"ALT-{int(datetime.now().timestamp())}",
                    "alert_type": "storm",
                    "severity": "high",
                    "title": "Severe Storm Warning",
                    "description": "High winds and heavy rainfall expected in coastal area",
                    "location": {
                        "lat": lat,
                        "lng": lng,
                        "address": "Coastal Region"
                    },
                    "created_at": datetime.now().isoformat(),
                    "valid_until": (datetime.now() + timedelta(hours=6)).isoformat(),
                    "status": "active",
                    "affected_area_km": 25,
                    "confidence": 0.89,
                    "data_sources": ["weather_station", "satellite", "buoy"],
                    "recommended_actions": [
                        "Avoid coastal areas",
                        "Secure loose objects",
                        "Monitor weather updates"
                    ]
                })
            
            response_data = {
                "active_alerts": active_alerts,
                "total_count": len(active_alerts),
                "search_criteria": {
                    "location": {"lat": lat, "lng": lng} if lat and lng else None,
                    "radius_km": radius,
                    "severity_filter": severity
                },
                "timestamp": datetime.now().isoformat(),
                "next_update": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Failed to get active alerts: {str(e)}")
    
    def _handle_alert_history(self, query_params):
        """Handle request for alert history"""
        try:
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            days = self._get_int_param(query_params, 'days', 30)
            alert_type = query_params.get('type', [None])[0]
            
            # Mock historical alerts
            historical_alerts = [
                {
                    "alert_id": "ALT-1234567890",
                    "alert_type": "air_quality",
                    "severity": "medium",
                    "title": "Air Quality Advisory",
                    "description": "PM2.5 levels elevated due to local pollution",
                    "location": {
                        "lat": lat or 40.7128,
                        "lng": lng or -74.0060,
                        "address": "Metropolitan Area"
                    },
                    "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                    "resolved_at": (datetime.now() - timedelta(days=1)).isoformat(),
                    "status": "resolved",
                    "duration_hours": 24,
                    "affected_population": 150000
                }
            ]
            
            response_data = {
                "historical_alerts": historical_alerts,
                "period_days": days,
                "total_count": len(historical_alerts),
                "filters": {
                    "alert_type": alert_type,
                    "location": {"lat": lat, "lng": lng} if lat and lng else None
                },
                "summary": {
                    "total_alerts": len(historical_alerts),
                    "by_severity": {
                        "low": 0,
                        "medium": 1,
                        "high": 0,
                        "critical": 0
                    },
                    "by_type": {
                        "air_quality": 1,
                        "storm": 0,
                        "coastal_erosion": 0,
                        "other": 0
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Failed to get alert history: {str(e)}")
    
    def _handle_get_subscriptions(self, query_params):
        """Handle request for user subscriptions"""
        try:
            user_id = query_params.get('user_id', [None])[0]
            
            if not user_id:
                self._send_error_response("Missing user_id parameter", 400)
                return
            
            # Mock user subscriptions
            subscriptions = {
                "user_id": user_id,
                "active_subscriptions": [
                    {
                        "subscription_id": "SUB-001",
                        "alert_types": ["storm", "extreme_weather"],
                        "location": {
                            "lat": 40.7128,
                            "lng": -74.0060,
                            "radius_km": 25,
                            "name": "New York Area"
                        },
                        "notification_channels": ["sms", "email"],
                        "severity_threshold": "medium",
                        "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
                        "status": "active"
                    }
                ],
                "notification_preferences": {
                    "sms_number": "+1234567890",
                    "email": "user@example.com",
                    "push_notifications": True,
                    "quiet_hours": {
                        "start": "22:00",
                        "end": "07:00"
                    }
                },
                "total_subscriptions": 1
            }
            
            self._send_json_response(subscriptions)
            
        except Exception as e:
            self._send_error_response(f"Failed to get subscriptions: {str(e)}")
    
    def _handle_alert_types(self):
        """Handle request for available alert types"""
        alert_types = {
            "available_alert_types": [
                {
                    "type": "storm",
                    "name": "Storm Warning",
                    "description": "Severe weather systems including hurricanes, cyclones",
                    "severity_levels": ["low", "medium", "high", "critical"],
                    "typical_duration": "2-24 hours",
                    "advance_warning": "2-6 hours"
                },
                {
                    "type": "air_quality",
                    "name": "Air Quality Alert",
                    "description": "Poor air quality due to pollution or environmental factors",
                    "severity_levels": ["moderate", "unhealthy", "hazardous"],
                    "typical_duration": "6-48 hours",
                    "advance_warning": "1-4 hours"
                },
                {
                    "type": "coastal_erosion",
                    "name": "Coastal Erosion Warning",
                    "description": "Rapid coastal erosion or shoreline changes",
                    "severity_levels": ["low", "medium", "high"],
                    "typical_duration": "hours to days",
                    "advance_warning": "1-12 hours"
                },
                {
                    "type": "algal_bloom",
                    "name": "Harmful Algal Bloom",
                    "description": "Toxic algal blooms affecting water quality",
                    "severity_levels": ["advisory", "warning", "danger"],
                    "typical_duration": "days to weeks",
                    "advance_warning": "6-24 hours"
                },
                {
                    "type": "high_tide",
                    "name": "Extreme Tide Alert",
                    "description": "Unusually high tides causing flooding risk",
                    "severity_levels": ["minor", "moderate", "major"],
                    "typical_duration": "2-6 hours",
                    "advance_warning": "6-48 hours"
                }
            ],
            "total_types": 5,
            "notification_channels": [
                {
                    "channel": "sms",
                    "name": "SMS Text Message",
                    "availability": bool(os.getenv("TWILIO_SID"))
                },
                {
                    "channel": "email",
                    "name": "Email Notification",
                    "availability": bool(os.getenv("RESEND_API_KEY"))
                },
                {
                    "channel": "push",
                    "name": "Push Notification",
                    "availability": bool(os.getenv("PUSHER_KEY"))
                },
                {
                    "channel": "webhook",
                    "name": "Webhook Callback",
                    "availability": True
                }
            ]
        }
        
        self._send_json_response(alert_types)
    
    def _handle_alert_subscription(self, data):
        """Handle alert subscription request"""
        try:
            # Validate required fields
            required_fields = ['user_id', 'location', 'alert_types', 'notification_channels']
            for field in required_fields:
                if field not in data:
                    self._send_error_response(f"Missing required field: {field}", 400)
                    return
            
            # Create subscription
            subscription_data = {
                "subscription_id": f"SUB-{int(datetime.now().timestamp())}",
                "user_id": data['user_id'],
                "location": data['location'],
                "alert_types": data['alert_types'],
                "notification_channels": data['notification_channels'],
                "severity_threshold": data.get('severity_threshold', 'medium'),
                "radius_km": data.get('radius_km', 25),
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "verified": False
            }
            
            # Log to blockchain if available
            if BACKEND_AVAILABLE and os.getenv("STARTON_API_KEY"):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    blockchain_record = loop.run_until_complete(
                        blockchain_utils.log_environmental_data(
                            subscription_data,
                            data['location'],
                            "alert_subscription"
                        )
                    )
                    
                    if blockchain_record:
                        subscription_data["blockchain_hash"] = blockchain_record.transaction_hash
                        subscription_data["verified"] = True
                finally:
                    loop.close()
            
            response_data = {
                "success": True,
                "message": "Alert subscription created successfully",
                "subscription": subscription_data,
                "verification_required": not subscription_data["verified"]
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Subscription failed: {str(e)}")
    
    def _handle_create_alert(self, data):
        """Handle manual alert creation"""
        try:
            # Validate required fields
            required_fields = ['alert_type', 'severity', 'location', 'description']
            for field in required_fields:
                if field not in data:
                    self._send_error_response(f"Missing required field: {field}", 400)
                    return
            
            # Create alert
            alert_data = {
                "alert_id": f"ALT-{int(datetime.now().timestamp())}",
                "alert_type": data['alert_type'],
                "severity": data['severity'],
                "title": data.get('title', f"{data['alert_type'].title()} Alert"),
                "description": data['description'],
                "location": data['location'],
                "created_at": datetime.now().isoformat(),
                "created_by": data.get('created_by', 'system'),
                "valid_until": data.get('valid_until', 
                    (datetime.now() + timedelta(hours=24)).isoformat()),
                "status": "active",
                "source": "manual",
                "confidence": data.get('confidence', 1.0)
            }
            
            response_data = {
                "success": True,
                "message": "Alert created successfully",
                "alert": alert_data,
                "notifications_sent": 0  # Would be actual count in production
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Alert creation failed: {str(e)}")
    
    def _handle_acknowledge_alert(self, data):
        """Handle alert acknowledgment"""
        try:
            if 'alert_id' not in data:
                self._send_error_response("Missing alert_id", 400)
                return
            
            # Mock acknowledgment
            acknowledgment_data = {
                "alert_id": data['alert_id'],
                "acknowledged_at": datetime.now().isoformat(),
                "acknowledged_by": data.get('user_id', 'anonymous'),
                "status": "acknowledged",
                "notes": data.get('notes', '')
            }
            
            response_data = {
                "success": True,
                "message": "Alert acknowledged successfully",
                "acknowledgment": acknowledgment_data
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Alert acknowledgment failed: {str(e)}")
    
    def _handle_test_alert(self, data):
        """Handle test alert request"""
        try:
            if 'notification_channels' not in data:
                self._send_error_response("Missing notification_channels", 400)
                return
            
            # Mock test alert
            test_result = {
                "test_id": f"TEST-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "channels_tested": data['notification_channels'],
                "results": {}
            }
            
            # Mock test results for each channel
            for channel in data['notification_channels']:
                test_result['results'][channel] = {
                    "status": "success" if channel in ['sms', 'email'] else "not_configured",
                    "delivery_time_ms": 1250 if channel == 'sms' else 2800,
                    "message": "Test alert sent successfully" if channel in ['sms', 'email'] 
                             else f"{channel} not configured"
                }
            
            response_data = {
                "success": True,
                "message": "Test alerts sent",
                "test_result": test_result
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Test alert failed: {str(e)}")
    
    def _handle_update_alert(self, data):
        """Handle alert update"""
        try:
            if 'alert_id' not in data:
                self._send_error_response("Missing alert_id", 400)
                return
            
            # Mock update
            update_data = {
                "alert_id": data['alert_id'],
                "updated_at": datetime.now().isoformat(),
                "changes": data.get('changes', {}),
                "updated_by": data.get('updated_by', 'system')
            }
            
            response_data = {
                "success": True,
                "message": "Alert updated successfully",
                "update": update_data
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Alert update failed: {str(e)}")
    
    def _handle_update_settings(self, data):
        """Handle notification settings update"""
        try:
            if 'user_id' not in data:
                self._send_error_response("Missing user_id", 400)
                return
            
            # Mock settings update
            settings_data = {
                "user_id": data['user_id'],
                "updated_at": datetime.now().isoformat(),
                "settings": data.get('settings', {}),
                "notification_preferences": data.get('notification_preferences', {})
            }
            
            response_data = {
                "success": True,
                "message": "Settings updated successfully",
                "settings": settings_data
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Settings update failed: {str(e)}")
    
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
            "message": "Alert endpoint not found",
            "status_code": 404,
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [
                "/api/alerts/active",
                "/api/alerts/history",
                "/api/alerts/subscriptions",
                "/api/alerts/subscribe",
                "/api/alerts/create",
                "/api/alerts/acknowledge"
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
            "service": "alerts"
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
