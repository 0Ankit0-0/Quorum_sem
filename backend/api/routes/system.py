"""
System Status Routes
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
import time

from models.schemas import SystemStatusResponse
from api.dependencies import get_database_status
from core.environment import env_detector
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/system", tags=["System"])

# Track application start time
APP_START_TIME = time.time()


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system status and health information"""
    try:
        db_status = get_database_status()
        
        return SystemStatusResponse(
            status="online",
            environment_type=env_detector.detect_all().get('environment_type').value,
            database_size_mb=round(
                settings.database_path.stat().st_size / (1024 * 1024), 2
            ) if settings.database_path.exists() else 0,
            total_logs=db_status.get('total_logs', 0),
            total_anomalies=db_status.get('total_anomalies', 0),
            uptime_seconds=round(time.time() - APP_START_TIME, 2)
        )
    
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/environment")
async def get_environment_info():
    """Get detailed environment detection information"""
    try:
        env_info = env_detector.detect_all()
        
        return {
            "environment": env_info,
            "detected_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Environment detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }