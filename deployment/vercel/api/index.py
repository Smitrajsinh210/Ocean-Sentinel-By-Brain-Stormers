"""
Ocean Sentinel - Main Vercel API Handler
Entry point for all Ocean Sentinel serverless functions
"""

import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

# Add backend path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

try:
    from backend.app import app as fastapi_app
    from backend.app.utils.blockchain_utils import blockchain_utils
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    """
    Main Vercel serverless function handler
    Routes requests to appropriate endpoints
    """
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Root endpoint
            if route == '/' or route == '/api':
                self._send_root_response()
            
            # Health check
            elif route == '/health' or route == '/api/health':
                self._send_health_response()
            
            # System status
            elif route == '/status' or route == '/api/status':
                self._send_status_response()
            
            # API documentation
            elif route == '/docs' or route == '/api/docs':
                self._send_docs_response()
            
            # Metrics endpoint
            elif route == '/metrics' or route == '/api/metrics':
                self._send_metrics_response()
            
            # API endpoints info
            elif route == '/api/endpoints':
                self._send_endpoints_response()
            
            # Default response for unmatched routes
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_POST(self):
        """Handle POST requests"""
        self._send_method_not_allowed()
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._send_cors_response()
    
    def _send_root_response(self):
        """Send root API response"""
        response_data = {
            "message": "🌊 Ocean Sentinel API - Coastal Threat Detection System",
            "version": "1.0.0",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "platform": "Vercel Serverless",
            "endpoints": {
                "threats": "/api/threats",
                "alerts": "/api/alerts", 
                "data": "/api/data",
                "analytics": "/api/analytics",
                "health": "/api/health",
                "status": "/api/status",
                "docs": "/api/docs"
            },
            "features": [
                "AI-powered threat detection",
                "Real-time environmental monitoring",
                "Blockchain data verification",
                "Predictive analytics",
                "Multi-channel alerting"
            ]
        }
        
        self._send_json_response(response_data)
    
    def _send_health_response(self):
        """Send health check response"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "platform": "vercel",
            "backend_available": BACKEND_AVAILABLE,
            "services": {
                "api": "operational",
                "database": "unknown",
                "ml_models": "unknown",
                "blockchain": "unknown"
            }
        }
        
        # Test blockchain utils if available
        if BACKEND_AVAILABLE:
            try:
                network_info = blockchain_utils.get_network_info()
                health_data["services"]["blockchain"] = "operational" if network_info else "degraded"
            except:
                health_data["services"]["blockchain"] = "error"
        
        self._send_json_response(health_data)
    
    def _send_status_response(self):
        """Send detailed system status"""
        status_data = {
            "system": {
                "name": "Ocean Sentinel API",
                "version": "1.0.0",
                "platform": "Vercel Serverless",
                "runtime": "Python 3.12",
                "region": os.getenv("VERCEL_REGION", "unknown"),
                "timestamp": datetime.now().isoformat()
            },
            "backend_integration": {
                "available": BACKEND_AVAILABLE,
                "ml_models": "loaded" if BACKEND_AVAILABLE else "unavailable",
                "services": "initialized" if BACKEND_AVAILABLE else "unavailable"
            },
            "environment": {
                "supabase_configured": bool(os.getenv("SUPABASE_URL")),
                "weather_api_configured": bool(os.getenv("OPENWEATHER_API_KEY")),
                "blockchain_configured": bool(os.getenv("STARTON_API_KEY")),
                "node_env": os.getenv("NODE_ENV", "production")
            },
            "features": {
                "threat_detection": BACKEND_AVAILABLE,
                "environmental_monitoring": BACKEND_AVAILABLE,
                "blockchain_verification": bool(os.getenv("STARTON_API_KEY")),
                "real_time_alerts": bool(os.getenv("PUSHER_KEY")),
                "predictive_analytics": BACKEND_AVAILABLE
            }
        }
        
        self._send_json_response(status_data)
    
    def _send_docs_response(self):
        """Send API documentation response"""
        docs_data = {
            "title": "Ocean Sentinel API Documentation",
            "version": "1.0.0",
            "description": "AI-powered coastal threat detection and environmental monitoring system",
            "base_url": "https://ocean-sentinel-api.vercel.app",
            "endpoints": {
                "/api/threats": {
                    "description": "Threat detection and management",
                    "methods": ["GET", "POST"],
                    "examples": {
                        "GET /api/threats/detect": "Detect threats at coordinates",
                        "POST /api/threats/report": "Report new threat"
                    }
                },
                "/api/alerts": {
                    "description": "Alert management and notifications",
                    "methods": ["GET", "POST", "PUT"],
                    "examples": {
                        "GET /api/alerts": "Get active alerts",
                        "POST /api/alerts/subscribe": "Subscribe to alerts"
                    }
                },
                "/api/data": {
                    "description": "Environmental data collection",
                    "methods": ["GET", "POST"],
                    "examples": {
                        "GET /api/data/weather": "Get weather data",
                        "GET /api/data/ocean": "Get ocean conditions"
                    }
                },
                "/api/analytics": {
                    "description": "Analytics and reporting",
                    "methods": ["GET"],
                    "examples": {
                        "GET /api/analytics/threats": "Threat analytics",
                        "GET /api/analytics/trends": "Environmental trends"
                    }
                }
            },
            "authentication": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer <token>"
            },
            "rate_limits": {
                "authenticated": "1000 requests/hour",
                "anonymous": "100 requests/hour"
            }
        }
        
        self._send_json_response(docs_data)
    
    def _send_metrics_response(self):
        """Send metrics response"""
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "platform": "vercel",
            "status": "operational",
            "uptime": "99.9%",
            "response_time_avg": "150ms",
            "requests_total": 0,  # Would be populated from actual metrics
            "errors_total": 0,
            "version": "1.0.0"
        }
        
        self._send_json_response(metrics_data)
    
    def _send_endpoints_response(self):
        """Send available endpoints response"""
        endpoints_data = {
            "available_endpoints": [
                {
                    "path": "/api/threats",
                    "file": "threats.py",
                    "description": "Threat detection and management"
                },
                {
                    "path": "/api/alerts", 
                    "file": "alerts.py",
                    "description": "Alert management and notifications"
                },
                {
                    "path": "/api/data",
                    "file": "data.py", 
                    "description": "Environmental data collection"
                },
                {
                    "path": "/api/analytics",
                    "file": "analytics.py",
                    "description": "Analytics and reporting"
                }
            ],
            "utility_endpoints": [
                {
                    "path": "/api/health",
                    "description": "Health check"
                },
                {
                    "path": "/api/status",
                    "description": "System status"
                },
                {
                    "path": "/api/docs",
                    "description": "API documentation"
                }
            ]
        }
        
        self._send_json_response(endpoints_data)
    
    def _send_not_found_response(self):
        """Send 404 not found response"""
        error_data = {
            "error": True,
            "message": "Endpoint not found",
            "status_code": 404,
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [
                "/api/threats",
                "/api/alerts",
                "/api/data", 
                "/api/analytics",
                "/api/health",
                "/api/status"
            ]
        }
        
        self._send_json_response(error_data, status_code=404)
    
    def _send_method_not_allowed(self):
        """Send 405 method not allowed response"""
        error_data = {
            "error": True,
            "message": "Method not allowed",
            "status_code": 405,
            "timestamp": datetime.now().isoformat(),
            "allowed_methods": ["GET", "OPTIONS"]
        }
        
        self._send_json_response(error_data, status_code=405)
    
    def _send_error_response(self, error_message: str):
        """Send error response"""
        error_data = {
            "error": True,
            "message": f"Internal server error: {error_message}",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
        
        self._send_json_response(error_data, status_code=500)
    
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