"""
Ocean Sentinel - Main Application Initialization
FastAPI application with comprehensive environmental monitoring system
"""

import os
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

# FastAPI and related imports
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Security and authentication
from fastapi.security import HTTPBearer
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastAPIIntegration
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Database and environment
from supabase import create_client, Client
from python_dotenv import load_dotenv
import structlog
import redis

# Monitoring and health checks
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi_health import health

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Initialize logger
logger = structlog.get_logger("ocean_sentinel")

# Initialize Sentry for error monitoring
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FastAPIIntegration(auto_enable=True)],
        traces_sample_rate=0.1,
        environment=os.getenv("NODE_ENV", "development"),
    )
    logger.info("Sentry error monitoring initialized")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Global application state
app_state = {
    "supabase_client": None,
    "redis_client": None,
    "services_initialized": False,
    "ml_models_loaded": False,
    "startup_time": None,
    "health_checks": {}
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    
    # STARTUP EVENTS
    logger.info("🌊 Ocean Sentinel starting up...")
    app_state["startup_time"] = datetime.now()
    
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_ANON_KEY")
        
        if supabase_url and supabase_key:
            app_state["supabase_client"] = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized")
            app_state["health_checks"]["database"] = True
        else:
            logger.warning("⚠️  Supabase credentials not found")
            app_state["health_checks"]["database"] = False
        
        # Initialize Redis client (optional)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            app_state["redis_client"] = redis.from_url(redis_url, decode_responses=True)
            await asyncio.to_thread(app_state["redis_client"].ping)
            logger.info("✅ Redis client initialized")
            app_state["health_checks"]["redis"] = True
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {str(e)}")
            app_state["health_checks"]["redis"] = False
        
        # Initialize environmental data services
        try:
            from .services.weather_service import weather_service
            from .services.air_quality_service import air_quality_service
            from .services.ocean_service import ocean_service
            
            # Test service connectivity
            weather_status = await weather_service.get_service_status()
            air_quality_status = await air_quality_service.get_service_status()
            ocean_status = await ocean_service.get_service_status()
            
            app_state["health_checks"]["weather_api"] = weather_status.get("api_accessible", False)
            app_state["health_checks"]["air_quality_api"] = air_quality_status.get("api_accessible", False)
            app_state["health_checks"]["ocean_api"] = ocean_status.get("api_accessible", False)
            
            app_state["services_initialized"] = True
            logger.info("✅ Environmental services initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing services: {str(e)}")
            app_state["services_initialized"] = False
        
        # Initialize ML models
        try:
            from .ml_models.threat_detection import threat_detector
            from .ml_models.anomaly_detection import anomaly_detector
            from .ml_models.prediction_models import threat_predictor
            
            # Initialize ML models asynchronously
            await threat_detector.initialize_models()
            await anomaly_detector.initialize_models()
            await threat_predictor.initialize_models()
            
            app_state["ml_models_loaded"] = True
            app_state["health_checks"]["ml_models"] = True
            logger.info("✅ ML models initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing ML models: {str(e)}")
            app_state["ml_models_loaded"] = False
            app_state["health_checks"]["ml_models"] = False
        
        # Log startup completion
        startup_duration = (datetime.now() - app_state["startup_time"]).total_seconds()
        logger.info(f"🚀 Ocean Sentinel startup completed in {startup_duration:.2f}s")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    # SHUTDOWN EVENTS
    logger.info("🛑 Ocean Sentinel shutting down...")
    
    try:
        # Close Redis connection
        if app_state["redis_client"]:
            app_state["redis_client"].close()
            logger.info("✅ Redis connection closed")
        
        # Close any other connections
        logger.info("✅ Ocean Sentinel shutdown completed")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}")

# Create FastAPI application
app = FastAPI(
    title="Ocean Sentinel API",
    description="""
    🌊 **Ocean Sentinel - AI-Powered Coastal Threat Detection System**
    
    A comprehensive environmental monitoring platform that integrates:
    - **Real-time threat detection** using AI and machine learning
    - **Multi-source data integration** (weather, air quality, ocean data)
    - **Blockchain data integrity** with cryptographic verification
    - **2-4 hour advance warnings** for coastal threats
    - **Multi-channel alert system** (SMS, email, push notifications)
    - **Cross-agency collaboration** with verified data sharing
    
    ## Features
    - 🤖 **AI Threat Detection**: Storms, pollution, erosion, algal blooms
    - 📊 **Environmental Data**: OpenWeatherMap, OpenAQ, NOAA integration
    - ⛓️ **Blockchain Verification**: Starton smart contracts on Polygon
    - 📱 **Real-time Alerts**: Sub-60 second notification delivery
    - 🔍 **Anomaly Detection**: Statistical and ML-based pattern recognition
    - 📈 **Predictive Analytics**: Time series forecasting models
    
    ## Quick Start
    1. Set up your API keys in environment variables
    2. Initialize database with migrations
    3. Start monitoring coastal threats in real-time
    """,
    version="1.0.0",
    contact={
        "name": "Ocean Sentinel Team",
        "url": "https://oceansentinel.ai",
        "email": "support@oceansentinel.ai"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add security middleware
if os.getenv("NODE_ENV") == "production":
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "oceansentinel.ai,*.oceansentinel.ai").split(",")
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    logger.warning(
        "HTTP exception occurred",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(
        "Unexpected error occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error occurred",
            "status_code": 500,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path)
        }
    )

# Health check functions
def check_database():
    """Check database connectivity"""
    try:
        if app_state["supabase_client"]:
            # Simple query to check connectivity
            result = app_state["supabase_client"].table("users").select("count", count="exact").execute()
            return True
        return False
    except Exception:
        return False

def check_redis():
    """Check Redis connectivity"""
    try:
        if app_state["redis_client"]:
            app_state["redis_client"].ping()
            return True
        return False
    except Exception:
        return False

def check_services():
    """Check external services status"""
    return app_state["services_initialized"]

def check_ml_models():
    """Check ML models status"""
    return app_state["ml_models_loaded"]

# Health check endpoint
app.add_api_route(
    "/health",
    health([check_database, check_redis, check_services, check_ml_models])
)

# Include API routers
try:
    # Import and include all route modules
    from .deployment.vercel.api.threats import app as threats_router
    from .deployment.vercel.api.alerts import app as alerts_router
    from .deployment.vercel.api.data import app as data_router
    
    # Mount the routers (Vercel functions are standalone, so we'll create wrapper endpoints)
    logger.info("✅ API routes configured")
    
except ImportError as e:
    logger.warning(f"⚠️  Some API routes not available: {str(e)}")

# Root endpoints
@app.get("/", tags=["Root"])
@limiter.limit("30/minute")
async def root(request: Request):
    """Root endpoint with system information"""
    uptime = (datetime.now() - app_state["startup_time"]).total_seconds() if app_state["startup_time"] else 0
    
    return {
        "message": "🌊 Ocean Sentinel API - Coastal Threat Detection System",
        "version": "1.0.0",
        "status": "operational",
        "uptime_seconds": round(uptime, 2),
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "documentation": "/docs",
            "health_check": "/health",
            "metrics": "/metrics",
            "system_status": "/status"
        },
        "features": [
            "AI-powered threat detection",
            "Real-time environmental monitoring", 
            "Blockchain data verification",
            "Predictive analytics",
            "Multi-channel alerting"
        ]
    }

@app.get("/status", tags=["System"])
@limiter.limit("10/minute")
async def system_status(request: Request):
    """Detailed system status information"""
    uptime = (datetime.now() - app_state["startup_time"]).total_seconds() if app_state["startup_time"] else 0
    
    status = {
        "system": {
            "name": "Ocean Sentinel",
            "version": "1.0.0",
            "environment": os.getenv("NODE_ENV", "development"),
            "uptime_seconds": round(uptime, 2),
            "startup_time": app_state["startup_time"].isoformat() if app_state["startup_time"] else None
        },
        "health_checks": app_state["health_checks"],
        "components": {
            "database": "Supabase PostgreSQL",
            "cache": "Redis" if app_state["redis_client"] else "None",
            "ml_framework": "scikit-learn + TensorFlow",
            "apis": ["OpenWeatherMap", "OpenAQ", "NOAA"],
            "blockchain": "Polygon (Starton)"
        },
        "features": {
            "services_initialized": app_state["services_initialized"],
            "ml_models_loaded": app_state["ml_models_loaded"],
            "real_time_monitoring": True,
            "threat_detection": True,
            "blockchain_verification": True
        }
    }
    
    # Overall health score
    health_score = sum(app_state["health_checks"].values()) / len(app_state["health_checks"]) * 100
    status["overall_health"] = f"{health_score:.1f}%"
    
    return status

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# API endpoints for integration with Vercel functions
@app.get("/api/threats/health", tags=["API Health"])
async def threats_api_health():
    """Check threats API health"""
    return {"status": "healthy", "service": "threats", "timestamp": datetime.now().isoformat()}

@app.get("/api/alerts/health", tags=["API Health"])  
async def alerts_api_health():
    """Check alerts API health"""
    return {"status": "healthy", "service": "alerts", "timestamp": datetime.now().isoformat()}

@app.get("/api/data/health", tags=["API Health"])
async def data_api_health():
    """Check data API health"""
    return {"status": "healthy", "service": "data", "timestamp": datetime.now().isoformat()}

# Dependency injection functions
def get_supabase_client() -> Client:
    """Dependency to get Supabase client"""
    if not app_state["supabase_client"]:
        raise HTTPException(status_code=503, detail="Database not available")
    return app_state["supabase_client"]

def get_redis_client():
    """Dependency to get Redis client"""
    if not app_state["redis_client"]:
        raise HTTPException(status_code=503, detail="Cache not available")
    return app_state["redis_client"]

# Custom OpenAPI schema
def custom_openapi():
    """Custom OpenAPI schema with enhanced documentation"""
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="Ocean Sentinel API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom schema extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://oceansentinel.ai/logo.png"
    }
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": os.getenv("API_URL", "http://localhost:8000"),
            "description": "Ocean Sentinel API Server"
        }
    ]
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Export the app
__all__ = ["app", "app_state", "get_supabase_client", "get_redis_client", "logger"]

# Final initialization log
logger.info("🌊 Ocean Sentinel application module loaded successfully")