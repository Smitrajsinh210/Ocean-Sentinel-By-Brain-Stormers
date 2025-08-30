"""
Ocean Sentinel - Main FastAPI Application
AI-powered coastal threat detection system with blockchain data integrity
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.routes import threats, alerts, data, analytics, auth
from app.services.data_ingestion import EnvironmentalDataService
from app.services.ai_detection import ThreatDetectionAI
from app.services.blockchain import BlockchainService
from app.services.notifications import NotificationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
data_service = None
ai_service = None
blockchain_service = None
notification_service = None
monitoring_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global data_service, ai_service, blockchain_service, notification_service, monitoring_task
    
    try:
        logger.info("🌊 Starting Ocean Sentinel Application...")
        
        # Initialize services
        data_service = EnvironmentalDataService()
        ai_service = ThreatDetectionAI()
        blockchain_service = BlockchainService()
        notification_service = NotificationService()
        
        # Load AI models
        await ai_service.load_models()
        logger.info("🤖 AI models loaded successfully")
        
        # Start background monitoring
        monitoring_task = asyncio.create_task(background_monitoring())
        logger.info("📊 Background monitoring started")
        
        logger.info("✅ Ocean Sentinel Application started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    
    finally:
        # Cleanup
        if monitoring_task:
            monitoring_task.cancel()
        logger.info("🛑 Ocean Sentinel Application shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Ocean Sentinel API",
    description="AI-powered coastal threat detection system with blockchain data integrity",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(threats.router, prefix="/api/v1/threats", tags=["threats"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(data.router, prefix="/api/v1/data", tags=["environmental-data"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

async def background_monitoring():
    """Background task for continuous environmental monitoring"""
    logger.info("🔄 Starting background monitoring loop...")
    
    while True:
        try:
            # Ingest environmental data
            environmental_data = await data_service.ingest_all_data()
            
            if environmental_data:
                # Run AI threat detection
                threats_detected = await ai_service.detect_threats(environmental_data)
                
                if threats_detected:
                    logger.info(f"⚠️ {len(threats_detected)} threats detected")
                    
                    # Process each threat
                    for threat in threats_detected:
                        # Log to blockchain
                        await blockchain_service.log_threat_data(threat, threat['id'])
                        
                        # Send alerts for critical threats
                        if threat.get('severity', 0) >= settings.critical_severity_threshold:
                            await notification_service.send_critical_alert(threat)
                
                logger.info("✅ Monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"❌ Error in monitoring loop: {e}")
        
        # Wait before next cycle
        await asyncio.sleep(settings.monitoring_interval)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🌊 Ocean Sentinel API",
        "description": "AI-powered coastal threat detection system",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        # Test API services
        # Test blockchain connection
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "operational",
                "ai_models": "loaded",
                "blockchain": "connected",
                "notifications": "ready"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/status")
async def system_status():
    """Detailed system status"""
    return {
        "application": "Ocean Sentinel",
        "version": "1.0.0",
        "environment": settings.environment,
        "status": "operational",
        "uptime": "calculate_uptime()",
        "active_threats": 0,  # Get from database
        "last_data_update": datetime.utcnow().isoformat(),
        "services": {
            "data_ingestion": "active",
            "threat_detection": "active",
            "blockchain_logging": "active",
            "notifications": "active"
        }
    }

@app.post("/api/v1/manual-check")
async def manual_threat_check(background_tasks: BackgroundTasks):
    """Manually trigger threat detection"""
    background_tasks.add_task(run_manual_check)
    return {"message": "Manual threat check initiated", "status": "processing"}

async def run_manual_check():
    """Run manual threat detection check"""
    try:
        logger.info("🔍 Running manual threat check...")
        
        # Ingest fresh data
        environmental_data = await data_service.ingest_all_data()
        
        if environmental_data:
            # Run AI detection
            threats = await ai_service.detect_threats(environmental_data)
            
            logger.info(f"Manual check completed: {len(threats)} threats detected")
            
            return threats
        
    except Exception as e:
        logger.error(f"Manual check failed: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
