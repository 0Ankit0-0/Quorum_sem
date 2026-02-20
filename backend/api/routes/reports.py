"""
Report Generation Routes
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional

from models.schemas import ReportGenerationRequest
from services.report_service import report_service
from config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate")
async def generate_report(request: ReportGenerationRequest):
    """Generate a report (CSV or PDF)"""
    try:
        if request.report_type == 'csv':
            report_path = report_service.generate_csv_report(
                session_id=request.session_id
            )
        elif request.report_type == 'pdf':
            report_path = report_service.generate_pdf_report(
                session_id=request.session_id,
                include_graphs=request.include_graphs
            )
        else:
            raise ValueError(f"Invalid report type: {request.report_type}")
        
        return {
            "status": "success",
            "report_type": request.report_type,
            "report_path": str(report_path),
            "filename": report_path.name
        }
    
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/list")
async def list_reports():
    """List all generated reports"""
    try:
        from config.settings import settings
        
        reports = []
        
        for report_file in settings.REPORTS_DIR.glob("*"):
            if report_file.is_file():
                reports.append({
                    "filename": report_file.name,
                    "path": str(report_file),
                    "size_mb": round(report_file.stat().st_size / (1024 * 1024), 2),
                    "created": report_file.stat().st_mtime
                })
        
        return {"reports": reports}
    
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{filename}")
async def download_report(filename: str):
    """Download a generated report file by filename."""
    try:
        from config.settings import settings

        requested = Path(filename).name
        report_path = settings.REPORTS_DIR / requested

        if not report_path.exists() or not report_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        return FileResponse(path=report_path, filename=requested)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
