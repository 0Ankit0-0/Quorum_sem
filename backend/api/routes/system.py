"""
System Status Routes
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
import time
from pathlib import Path

from models.schemas import SystemStatusResponse
from api.dependencies import get_database_status
from core.environment import env_detector
from config.settings import settings
from config.logging_config import get_logger
from services.settings_service import settings_service

logger = get_logger(__name__)
router = APIRouter(prefix="/system", tags=["System"])

# Track application start time
APP_START_TIME = time.time()
ENV_CACHE_TTL_SECONDS = 30
_env_cache = {
    "expires_at": 0.0,
    "environment_type": None,
}


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(force_refresh: bool = False):
    """Get system status and health information"""
    try:
        db_status = get_database_status()
        now = time.time()

        if (
            not force_refresh
            and _env_cache["environment_type"] is not None
            and now < float(_env_cache["expires_at"])
        ):
            environment_type = _env_cache["environment_type"]
        else:
            environment_type = env_detector.detect_all().get('environment_type').value
            _env_cache["environment_type"] = environment_type
            _env_cache["expires_at"] = now + ENV_CACHE_TTL_SECONDS
        
        return SystemStatusResponse(
            status="online",
            environment_type=environment_type,
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


@router.get("/storage")
async def get_storage_status():
    try:
        return settings_service.get_storage_status()
    except Exception as e:
        logger.error(f"Storage status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/storage/quota")
async def update_storage_quota(max_gb: float):
    try:
        return settings_service.update_storage_quota(max_gb=max_gb)
    except Exception as e:
        logger.error(f"Storage quota update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/encryption")
async def get_encryption_config():
    try:
        return settings_service.get_encryption_config()
    except Exception as e:
        logger.error(f"Encryption config fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/encryption")
async def update_encryption_config(payload: dict):
    try:
        return settings_service.update_encryption_config(payload)
    except Exception as e:
        logger.error(f"Encryption config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs/export")
async def export_system_logs(passphrase: str, encrypt: bool = False):
    try:
        result = settings_service.export_system_log(passphrase=passphrase, encrypt=encrypt)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"System log export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/export/{filename}")
async def download_exported_system_logs(filename: str):
    safe_name = Path(filename).name
    export_path = settings.DATA_DIR / "exports" / safe_name
    if not export_path.exists() or not export_path.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")
    from fastapi.responses import FileResponse

    return FileResponse(path=str(export_path), filename=safe_name)
