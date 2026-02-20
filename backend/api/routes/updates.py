"""
Update Management Routes (SOUP)
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from pathlib import Path
from typing import Optional

from services.update_service import update_service
from config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/updates", tags=["Updates"])


@router.post("/verify")
async def verify_update_package(package_path: str):
    """Verify an update package's signature and integrity"""
    try:
        path = Path(package_path)
        
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package not found: {package_path}"
            )
        
        result = update_service.verify_update(path)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/apply")
async def apply_update(package_path: str):
    """Apply a verified update package"""
    try:
        path = Path(package_path)
        
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package not found: {package_path}"
            )
        
        result = update_service.apply_update(path)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update application failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/rollback")
async def rollback_update(update_type: str):
    """Rollback to previous version"""
    try:
        result = update_service.rollback_update(update_type)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get('message', 'Rollback failed')
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/history")
async def get_update_history():
    """Get history of applied updates"""
    try:
        history = update_service.get_update_history()
        return {"history": history}
    
    except Exception as e:
        logger.error(f"Failed to get update history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/scan")
async def scan_for_updates():
    """Scan connected devices for update packages"""
    try:
        packages = update_service.scan_for_updates()
        
        return {
            "packages_found": len(packages),
            "packages": [str(p) for p in packages]
        }
    
    except Exception as e:
        logger.error(f"Update scan failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )