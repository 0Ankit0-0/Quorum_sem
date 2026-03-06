"""
Report Generation Routes
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
import hashlib
import io
from pathlib import Path
from typing import Optional
import zipfile

from models.schemas import ReportGenerationRequest
from services.report_service import report_service
from services.dataset_service import dataset_service
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
        valid_ext = {".pdf", ".csv"}
        
        for report_file in settings.REPORTS_DIR.rglob("*"):
            if report_file.is_file() and report_file.suffix.lower() in valid_ext:
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
            matches = [
                p for p in settings.REPORTS_DIR.rglob(requested)
                if p.is_file()
            ]
            if matches:
                matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                report_path = matches[0]

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


@router.post("/datasets/{filename}/generate")
async def generate_dataset_report(filename: str):
    """Generate dataset-scoped report bundle: summary.json, anomalies.csv, ai_analysis.json"""
    safe_name = Path(filename).name
    try:
        result = dataset_service.generate_report_bundle(safe_name)
        return {"status": "success", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"Dataset report generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/datasets/{filename}")
async def list_dataset_reports(filename: str):
    safe_name = Path(filename).name
    rows = dataset_service.list_reports(safe_name)
    return {"reports": rows}


@router.get("/datasets/{filename}/{report_id}/download")
async def download_dataset_report_file(filename: str, report_id: str, file: str = "summary.json"):
    safe_name = Path(filename).name
    safe_file = Path(file).name
    reports = dataset_service.list_reports(safe_name)
    target = next((r for r in reports if r.get("report_id") == report_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Report not found")
    report_dir = Path(target["report_dir"])
    file_path = (report_dir / safe_file).resolve()
    if not file_path.exists() or report_dir.resolve() not in file_path.parents:
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(str(file_path), filename=safe_file)


@router.get("/datasets/{filename}/{report_id}/download-all")
async def download_dataset_report_zip(filename: str, report_id: str):
    safe_name = Path(filename).name
    reports = dataset_service.list_reports(safe_name)
    target = next((r for r in reports if r.get("report_id") == report_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Report not found")
    report_dir = Path(target["report_dir"])
    if not report_dir.exists():
        raise HTTPException(status_code=404, detail="Report directory missing")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in report_dir.iterdir():
            if fp.is_file():
                zf.write(fp, arcname=fp.name)
    payload = buf.getvalue()
    bundle_hash = hashlib.sha256(payload).hexdigest()

    out = io.BytesIO(payload)
    headers = {
        "Content-Disposition": f'attachment; filename="report_{report_id}.zip"',
        "X-Integrity-SHA256": bundle_hash,
    }
    from fastapi.responses import StreamingResponse

    return StreamingResponse(out, media_type="application/zip", headers=headers)
