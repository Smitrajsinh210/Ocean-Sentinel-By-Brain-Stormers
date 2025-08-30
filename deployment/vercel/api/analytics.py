"""
Ocean Sentinel - Analytics API Endpoint
Serverless function for analytics and reporting
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
    """Analytics API serverless function handler"""
    
    def do_GET(self):
        """Handle GET requests for analytics data"""
        try:
            path = self.path
            parsed_url = urlparse(path)
            route = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Remove /api/analytics prefix
            route = route.replace('/api/analytics', '').strip('/')
            
            if route == '' or route == 'status':
                self._send_analytics_status()
            elif route == 'threats':
                self._handle_threat_analytics(query_params)
            elif route == 'environmental':
                self._handle_environmental_analytics(query_params)
            elif route == 'performance':
                self._handle_performance_analytics(query_params)
            elif route == 'trends':
                self._handle_trend_analytics(query_params)
            elif route == 'reports':
                self._handle_reports(query_params)
            elif route == 'dashboard':
                self._handle_dashboard_data(query_params)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_POST(self):
        """Handle POST requests for custom analytics"""
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
            route = parsed_url.path.replace('/api/analytics', '').strip('/')
            
            if route == 'custom':
                self._handle_custom_analytics(data)
            elif route == 'export':
                self._handle_data_export(data)
            else:
                self._send_not_found_response()
                
        except Exception as e:
            self._send_error_response(str(e))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._send_cors_response()
    
    def _send_analytics_status(self):
        """Send analytics API status"""
        status_data = {
            "service": "Analytics API",
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "capabilities": {
                "threat_analytics": True,
                "environmental_trends": True,
                "performance_metrics": True,
                "custom_reports": True,
                "real_time_dashboard": True,
                "blockchain_audit": bool(os.getenv("STARTON_API_KEY"))
            },
            "data_retention": {
                "real_time_data": "24 hours",
                "daily_aggregates": "90 days",
                "monthly_summaries": "2 years",
                "blockchain_records": "permanent"
            },
            "analytics_types": [
                "threat_frequency",
                "environmental_patterns",
                "prediction_accuracy",
                "alert_response_times",
                "data_quality_metrics",
                "geographic_distributions"
            ],
            "endpoints": [
                "GET /api/analytics/threats",
                "GET /api/analytics/environmental",
                "GET /api/analytics/performance", 
                "GET /api/analytics/trends",
                "GET /api/analytics/reports",
                "POST /api/analytics/custom"
            ]
        }
        
        self._send_json_response(status_data)
    
    def _handle_threat_analytics(self, query_params):
        """Handle threat analytics request"""
        try:
            # Extract parameters
            time_period = query_params.get('period', ['7d'])[0]
            threat_type = query_params.get('type', [None])[0]
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            radius = self._get_int_param(query_params, 'radius', 50)
            
            # Mock threat analytics data
            analytics_data = {
                "analysis_period": time_period,
                "location": {"lat": lat, "lng": lng, "radius_km": radius} if lat and lng else None,
                "threat_filter": threat_type,
                "timestamp": datetime.now().isoformat(),
                
                "threat_summary": {
                    "total_threats": 145,
                    "active_threats": 3,
                    "resolved_threats": 142,
                    "average_resolution_time_hours": 4.2,
                    "false_positive_rate": 0.08
                },
                
                "threat_distribution": {
                    "storm": 45,
                    "air_quality": 38,
                    "coastal_erosion": 28,
                    "algal_bloom": 18,
                    "extreme_weather": 16
                },
                
                "severity_breakdown": {
                    "low": 68,
                    "medium": 52,
                    "high": 21,
                    "critical": 4
                },
                
                "geographic_distribution": [
                    {"lat": 40.7128, "lng": -74.0060, "threat_count": 12, "severity_avg": 2.3},
                    {"lat": 34.0522, "lng": -118.2437, "threat_count": 8, "severity_avg": 1.9},
                    {"lat": 25.7617, "lng": -80.1918, "threat_count": 15, "severity_avg": 3.1}
                ],
                
                "temporal_patterns": {
                    "peak_hours": [6, 14, 18, 22],
                    "peak_days": ["Monday", "Wednesday", "Friday"],
                    "seasonal_trend": "increasing",
                    "hourly_distribution": [
                        {"hour": 0, "threats": 2}, {"hour": 6, "threats": 8},
                        {"hour": 12, "threats": 12}, {"hour": 18, "threats": 15},
                        {"hour": 22, "threats": 7}
                    ]
                },
                
                "prediction_accuracy": {
                    "overall_accuracy": 0.847,
                    "precision": 0.823,
                    "recall": 0.891,
                    "f1_score": 0.856,
                    "by_threat_type": {
                        "storm": {"accuracy": 0.912, "confidence": 0.95},
                        "air_quality": {"accuracy": 0.789, "confidence": 0.82},
                        "coastal_erosion": {"accuracy": 0.834, "confidence": 0.88}
                    }
                }
            }
            
            self._send_json_response(analytics_data)
            
        except Exception as e:
            self._send_error_response(f"Threat analytics failed: {str(e)}")
    
    def _handle_environmental_analytics(self, query_params):
        """Handle environmental analytics request"""
        try:
            # Extract parameters
            time_period = query_params.get('period', ['30d'])[0]
            data_type = query_params.get('type', [None])[0]
            lat = self._get_float_param(query_params, 'lat')
            lng = self._get_float_param(query_params, 'lng')
            
            # Mock environmental analytics
            analytics_data = {
                "analysis_period": time_period,
                "data_type_filter": data_type,
                "location": {"lat": lat, "lng": lng} if lat and lng else None,
                "timestamp": datetime.now().isoformat(),
                
                "data_collection_stats": {
                    "total_measurements": 45280,
                    "data_sources": 3,
                    "average_quality_score": 87.3,
                    "completeness_rate": 0.923,
                    "measurements_per_day": 1509
                },
                
                "environmental_trends": {
                    "temperature": {
                        "average": 24.8,
                        "min": 12.3,
                        "max": 38.7,
                        "trend": "increasing",
                        "trend_rate_per_day": 0.12,
                        "anomalies_detected": 8
                    },
                    "air_quality": {
                        "average_aqi": 68,
                        "best_aqi": 15,
                        "worst_aqi": 178,
                        "trend": "improving", 
                        "days_above_threshold": 12,
                        "anomalies_detected": 3
                    },
                    "ocean_conditions": {
                        "average_tide_level": 1.2,
                        "max_wave_height": 4.8,
                        "water_temperature_avg": 22.1,
                        "trend": "stable",
                        "storm_events": 2
                    }
                },
                
                "correlation_analysis": {
                    "temperature_air_quality": -0.34,
                    "pressure_storm_activity": 0.78,
                    "tide_coastal_erosion": 0.62,
                    "wind_air_quality": -0.45
                },
                
                "anomaly_summary": {
                    "total_anomalies": 23,
                    "by_severity": {
                        "minor": 15,
                        "moderate": 6,
                        "severe": 2
                    },
                    "most_common_type": "temperature_spike",
                    "average_duration_hours": 3.7
                },
                
                "data_quality_metrics": {
                    "weather_data": {"completeness": 0.956, "accuracy": 0.923, "timeliness": 0.981},
                    "air_quality_data": {"completeness": 0.834, "accuracy": 0.889, "timeliness": 0.901},
                    "ocean_data": {"completeness": 0.743, "accuracy": 0.912, "timeliness": 0.856}
                }
            }
            
            self._send_json_response(analytics_data)
            
        except Exception as e:
            self._send_error_response(f"Environmental analytics failed: {str(e)}")
    
    def _handle_performance_analytics(self, query_params):
        """Handle system performance analytics request"""
        try:
            time_period = query_params.get('period', ['7d'])[0]
            
            # Mock performance analytics
            performance_data = {
                "analysis_period": time_period,
                "timestamp": datetime.now().isoformat(),
                
                "api_performance": {
                    "total_requests": 125634,
                    "average_response_time_ms": 247,
                    "error_rate": 0.023,
                    "uptime_percentage": 99.87,
                    "requests_per_second_avg": 52.3,
                    "peak_requests_per_second": 184
                },
                
                "endpoint_performance": [
                    {"endpoint": "/api/threats", "avg_response_ms": 189, "requests": 34521, "error_rate": 0.012},
                    {"endpoint": "/api/data", "avg_response_ms": 156, "requests": 45123, "error_rate": 0.008},
                    {"endpoint": "/api/alerts", "avg_response_ms": 98, "requests": 28734, "error_rate": 0.015},
                    {"endpoint": "/api/analytics", "avg_response_ms": 423, "requests": 17256, "error_rate": 0.019}
                ],
                
                "ml_model_performance": {
                    "threat_detection": {
                        "average_processing_time_ms": 342,
                        "accuracy": 0.847,
                        "predictions_count": 8934,
                        "model_version": "v1.2.3"
                    },
                    "anomaly_detection": {
                        "average_processing_time_ms": 156,
                        "accuracy": 0.792,
                        "detections_count": 12456,
                        "model_version": "v1.1.8"
                    },
                    "prediction_models": {
                        "average_processing_time_ms": 789,
                        "accuracy": 0.823,
                        "forecasts_count": 5678,
                        "model_version": "v1.0.9"
                    }
                },
                
                "data_processing": {
                    "total_data_points_processed": 2456789,
                    "average_processing_time_ms": 12,
                    "data_validation_pass_rate": 0.934,
                    "preprocessing_success_rate": 0.978,
                    "quality_improvement_rate": 0.156
                },
                
                "blockchain_performance": {
                    "transactions_logged": 1234,
                    "average_confirmation_time_s": 15.7,
                    "verification_success_rate": 0.999,
                    "gas_cost_avg_gwei": 25.4,
                    "blockchain_uptime": 99.99
                },
                
                "alert_system_performance": {
                    "alerts_sent": 456,
                    "delivery_success_rate": 0.987,
                    "average_delivery_time_s": 2.8,
                    "sms_success_rate": 0.995,
                    "email_success_rate": 0.981,
                    "push_notification_rate": 0.976
                }
            }
            
            self._send_json_response(performance_data)
            
        except Exception as e:
            self._send_error_response(f"Performance analytics failed: {str(e)}")
    
    def _handle_trend_analytics(self, query_params):
        """Handle trend analytics request"""
        try:
            time_period = query_params.get('period', ['30d'])[0]
            trend_type = query_params.get('type', ['all'])[0]
            
            # Mock trend analytics
            trend_data = {
                "analysis_period": time_period,
                "trend_type": trend_type,
                "timestamp": datetime.now().isoformat(),
                
                "overall_trends": {
                    "threat_frequency": {
                        "direction": "increasing",
                        "rate_change": 0.12,
                        "confidence": 0.87,
                        "statistical_significance": 0.95
                    },
                    "environmental_degradation": {
                        "direction": "worsening", 
                        "rate_change": 0.08,
                        "confidence": 0.93,
                        "primary_factors": ["pollution", "climate_change"]
                    },
                    "system_accuracy": {
                        "direction": "improving",
                        "rate_change": 0.05,
                        "confidence": 0.91,
                        "contributing_factors": ["model_updates", "data_quality"]
                    }
                },
                
                "seasonal_patterns": {
                    "threat_seasonality": {
                        "peak_season": "hurricane_season",
                        "low_season": "winter",
                        "variance_coefficient": 0.34
                    },
                    "environmental_cycles": {
                        "temperature_cycle": "predictable",
                        "air_quality_cycle": "moderate",
                        "ocean_conditions": "irregular"
                    }
                },
                
                "geographic_trends": [
                    {
                        "region": "Northeast Coast",
                        "threat_trend": "increasing",
                        "primary_threats": ["storms", "coastal_erosion"],
                        "severity_trend": "stable"
                    },
                    {
                        "region": "Gulf Coast", 
                        "threat_trend": "stable",
                        "primary_threats": ["hurricanes", "algal_blooms"],
                        "severity_trend": "increasing"
                    },
                    {
                        "region": "West Coast",
                        "threat_trend": "decreasing",
                        "primary_threats": ["air_quality", "extreme_weather"],
                        "severity_trend": "improving"
                    }
                ],
                
                "predictive_insights": {
                    "next_30_days": {
                        "threat_likelihood": "moderate",
                        "expected_threat_types": ["storm", "air_quality"],
                        "confidence": 0.78
                    },
                    "next_90_days": {
                        "seasonal_outlook": "above_normal_activity",
                        "key_risk_factors": ["climate_patterns", "pollution_levels"],
                        "preparation_recommendations": ["infrastructure_check", "alert_system_test"]
                    }
                },
                
                "correlation_insights": {
                    "strongest_correlations": [
                        {"factors": ["temperature", "air_quality"], "correlation": -0.67},
                        {"factors": ["storm_activity", "coastal_erosion"], "correlation": 0.84},
                        {"factors": ["pollution_levels", "health_alerts"], "correlation": 0.72}
                    ],
                    "emerging_patterns": [
                        "Increasing correlation between urban development and air quality issues",
                        "Stronger link between climate events and coastal threats"
                    ]
                }
            }
            
            self._send_json_response(trend_data)
            
        except Exception as e:
            self._send_error_response(f"Trend analytics failed: {str(e)}")
    
    def _handle_reports(self, query_params):
        """Handle reports request"""
        try:
            report_type = query_params.get('type', ['summary'])[0]
            format_type = query_params.get('format', ['json'])[0]
            time_period = query_params.get('period', ['7d'])[0]
            
            # Mock reports data
            reports_data = {
                "report_type": report_type,
                "format": format_type,
                "period": time_period,
                "generated_at": datetime.now().isoformat(),
                
                "executive_summary": {
                    "total_threats_detected": 45,
                    "alerts_issued": 12,
                    "system_uptime": "99.8%",
                    "data_quality_score": 87.3,
                    "response_time_avg": "2.4 minutes",
                    "key_findings": [
                        "Threat detection accuracy improved by 5%",
                        "Air quality alerts increased by 23%", 
                        "Storm prediction lead time extended to 4.2 hours"
                    ]
                },
                
                "detailed_metrics": {
                    "threat_detection": {
                        "storms": {"detected": 15, "accuracy": 0.92, "false_positives": 2},
                        "air_quality": {"detected": 18, "accuracy": 0.84, "false_positives": 3},
                        "coastal_erosion": {"detected": 8, "accuracy": 0.89, "false_positives": 1},
                        "other": {"detected": 4, "accuracy": 0.75, "false_positives": 1}
                    },
                    "system_performance": {
                        "api_calls": 125634,
                        "error_rate": "2.3%",
                        "average_latency": "247ms",
                        "peak_load_handled": "184 req/s"
                    },
                    "data_sources": {
                        "weather_api_uptime": "99.9%",
                        "air_quality_coverage": "78%",
                        "ocean_data_availability": "84%"
                    }
                },
                
                "recommendations": [
                    "Increase air quality monitoring station coverage",
                    "Optimize ML models for coastal erosion detection",
                    "Implement additional backup data sources",
                    "Enhance alert delivery mechanisms"
                ],
                
                "compliance_status": {
                    "data_retention": "compliant",
                    "privacy_protection": "compliant", 
                    "api_security": "compliant",
                    "blockchain_integrity": "verified",
                    "audit_trail": "complete"
                }
            }
            
            # Add download link for non-JSON formats
            if format_type != 'json':
                reports_data["download_url"] = f"/api/analytics/reports/download/{report_type}_{time_period}.{format_type}"
            
            self._send_json_response(reports_data)
            
        except Exception as e:
            self._send_error_response(f"Reports generation failed: {str(e)}")
    
    def _handle_dashboard_data(self, query_params):
        """Handle dashboard data request"""
        try:
            # Mock dashboard data
            dashboard_data = {
                "timestamp": datetime.now().isoformat(),
                "refresh_interval": 30,  # seconds
                
                "key_metrics": {
                    "active_threats": 3,
                    "system_health": 98.7,
                    "data_quality": 87.3,
                    "alert_response_avg": 2.4,  # minutes
                    "predictions_accuracy": 84.7
                },
                
                "real_time_alerts": [
                    {
                        "id": "ALT-001",
                        "type": "storm",
                        "severity": "high",
                        "location": "Northeast Coast",
                        "time_active": "45 minutes"
                    },
                    {
                        "id": "ALT-002", 
                        "type": "air_quality",
                        "severity": "medium",
                        "location": "Metropolitan Area",
                        "time_active": "2.5 hours"
                    }
                ],
                
                "recent_threats": [
                    {"time": "2 hours ago", "type": "storm", "location": "Coastal Region", "resolved": True},
                    {"time": "4 hours ago", "type": "air_quality", "location": "Urban Area", "resolved": True},
                    {"time": "6 hours ago", "type": "algal_bloom", "location": "Bay Area", "resolved": False}
                ],
                
                "system_status": {
                    "api_status": "operational",
                    "ml_models": "operational",
                    "data_sources": "operational",
                    "blockchain": "operational",
                    "notifications": "operational"
                },
                
                "geographic_summary": [
                    {"region": "Northeast", "active_threats": 2, "risk_level": "high"},
                    {"region": "Southeast", "active_threats": 1, "risk_level": "medium"},
                    {"region": "Gulf Coast", "active_threats": 0, "risk_level": "low"},
                    {"region": "West Coast", "active_threats": 0, "risk_level": "low"}
                ],
                
                "performance_indicators": {
                    "api_response_time": "247ms",
                    "detection_latency": "1.8s", 
                    "alert_delivery_time": "2.4s",
                    "data_freshness": "3 minutes",
                    "model_accuracy": "84.7%"
                }
            }
            
            self._send_json_response(dashboard_data)
            
        except Exception as e:
            self._send_error_response(f"Dashboard data failed: {str(e)}")
    
    def _handle_custom_analytics(self, data):
        """Handle custom analytics request"""
        try:
            # Validate required fields
            if 'query' not in data:
                self._send_error_response("Missing query field", 400)
                return
            
            # Mock custom analytics processing
            custom_result = {
                "query_id": f"CUSTOM-{int(datetime.now().timestamp())}",
                "query": data['query'],
                "parameters": data.get('parameters', {}),
                "executed_at": datetime.now().isoformat(),
                "processing_time_ms": 1247,
                "status": "completed",
                
                "results": {
                    "data_points": 1234,
                    "aggregations": {
                        "count": 1234,
                        "average": 25.7,
                        "min": 12.3,
                        "max": 45.8
                    },
                    "trends": ["increasing"],
                    "insights": [
                        "Data shows upward trend over selected period",
                        "Seasonal patterns detected in measurements"
                    ]
                },
                
                "visualization_data": {
                    "chart_type": "line",
                    "data_series": [
                        {"name": "Series 1", "values": [10, 15, 12, 18, 22, 25, 23]},
                        {"name": "Series 2", "values": [8, 12, 14, 16, 19, 21, 24]}
                    ],
                    "labels": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]
                }
            }
            
            response_data = {
                "success": True,
                "message": "Custom analytics completed",
                "result": custom_result
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Custom analytics failed: {str(e)}")
    
    def _handle_data_export(self, data):
        """Handle data export request"""
        try:
            # Validate required fields
            required_fields = ['export_type', 'format', 'time_range']
            for field in required_fields:
                if field not in data:
                    self._send_error_response(f"Missing required field: {field}", 400)
                    return
            
            # Mock export processing
            export_result = {
                "export_id": f"EXP-{int(datetime.now().timestamp())}",
                "export_type": data['export_type'],
                "format": data['format'],
                "time_range": data['time_range'],
                "filters": data.get('filters', {}),
                "requested_at": datetime.now().isoformat(),
                "status": "processing",
                "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat(),
                "download_url": None,
                "size_estimate": "2.5 MB",
                "records_estimate": 15000
            }
            
            # Simulate immediate completion for small exports
            if data.get('size', 'small') == 'small':
                export_result.update({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "download_url": f"/api/analytics/exports/download/{export_result['export_id']}.{data['format']}",
                    "actual_size": "1.8 MB",
                    "actual_records": 12456
                })
            
            response_data = {
                "success": True,
                "message": "Export request processed",
                "export": export_result
            }
            
            self._send_json_response(response_data)
            
        except Exception as e:
            self._send_error_response(f"Data export failed: {str(e)}")
    
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
            "message": "Analytics endpoint not found",
            "status_code": 404,
            "timestamp": datetime.now().isoformat(),
            "available_endpoints": [
                "/api/analytics/threats",
                "/api/analytics/environmental",
                "/api/analytics/performance",
                "/api/analytics/trends", 
                "/api/analytics/reports",
                "/api/analytics/dashboard"
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
            "service": "analytics"
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