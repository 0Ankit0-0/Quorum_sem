"""
Log Management Routes
"""
import shutil
from fastapi import APIRouter, HTTPException, BackgroundTasks, status, UploadFile, File, Form, Body
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from models.schemas import LogIngestRequest, LogEntryResponse
from services.log_service import log_service
from services.dataset_service import dataset_service
from config.settings import settings
from config.logging_config import get_logger
from core.exceptions import ParserError

logger = get_logger(__name__)
router = APIRouter(prefix="/logs", tags=["Logs"])
DISALLOWED_UPLOAD_SUFFIXES = {
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".com",
    ".msi",
    ".ps1",
    ".sh",
}


@router.post("/ingest")
async def ingest_log_file(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    source_type: Optional[str] = Form(None),
    request: Optional[LogIngestRequest] = Body(None),
):
    """
    Ingest a log file into the database.
    Supports either:
    1) multipart file upload (frontend uploader)
    2) JSON body with file_path (legacy/background ingestion)
    """
    try:
        # Primary path used by frontend: multipart file upload
        if file is not None:
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Missing uploaded filename"
                )

            upload_dir = settings.DATA_DIR / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            safe_name = Path(file.filename).name
            suffix = Path(safe_name).suffix.lower()
            if suffix in DISALLOWED_UPLOAD_SUFFIXES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported file type for log ingestion: {suffix}",
                )
            saved_path = upload_dir / safe_name

            try:
                with saved_path.open("wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                stats = log_service.ingest_file(saved_path, source_type)
                dataset_info = dataset_service.ingest_uploaded_file(saved_path, source_type)
                
                # Return stats with the filename preserved
                return {
                    **stats,
                    "filename": safe_name,
                    "saved_path": str(saved_path),
                    "dataset_id": dataset_info["dataset_id"],
                    "dataset_records": dataset_info["records_total"],
                }
            finally:
                try:
                    file.file.close()
                except Exception:
                    pass
                # Keep the file instead of deleting it for later analysis

        # Backward-compatible JSON path mode
        if request is not None:
            file_path = Path(request.file_path)

            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {request.file_path}"
                )

            background_tasks.add_task(
                log_service.ingest_file,
                file_path,
                request.source_type.value if request.source_type else None
            )

            return {
                "status": "accepted",
                "message": "Log ingestion started",
                "file_path": str(file_path)
            }

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either multipart file upload field 'file' or JSON body with 'file_path'"
        )
    
    except HTTPException:
        raise
    except ParserError as e:
        logger.error(f"Ingestion request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValueError as e:
        logger.error(f"Ingestion request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ingestion request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/ingest/directory", status_code=status.HTTP_202_ACCEPTED)
async def ingest_directory(
    directory_path: str,
    recursive: bool = False,
    file_pattern: str = "*"
):
    """Ingest all log files from a directory"""
    try:
        dir_path = Path(directory_path)
        
        if not dir_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directory not found: {directory_path}"
            )
        
        results = log_service.ingest_directory(dir_path, recursive, file_pattern)
        
        return {
            "status": "completed",
            "files_processed": len(results),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Directory ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/ingest/system")
async def ingest_system_logs(log_types: Optional[list] = None):
    """Automatically collect and ingest system logs"""
    try:
        result = log_service.ingest_system_logs(log_types)
        
        return {
            "status": "completed",
            "system": result['system'],
            "files_collected": result['files_collected'],
            "files_ingested": result['files_ingested'],
            "details": result['details']
        }
    
    except Exception as e:
        logger.error(f"System log ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/statistics")
async def get_log_statistics():
    """Get statistics about ingested logs"""
    try:
        stats = log_service.get_log_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/recent", response_model=list)
async def get_recent_logs(limit: int = 100, filename: Optional[str] = None, search: Optional[str] = None):
    """Get most recent log entries"""
    try:
        if filename:
            return dataset_service.fetch_recent_logs(filename=filename, limit=limit, search=search)

        from core.database import db
        
        query = """
            SELECT
                l.id,
                l.timestamp,
                l.source,
                l.event_type,
                COALESCE(a.severity, l.severity, 'LOW') AS severity,
                l.message,
                l.hostname,
                l.username,
                COALESCE(a.algorithm, 'statistical') AS algorithm,
                a.mitre_technique_id,
                a.mitre_tactic,
                a.anomaly_score
            FROM logs l
            LEFT JOIN anomalies a ON a.log_id = l.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        """
        
        logs = db.fetch_all(query, (limit,))
        return logs
    
    except Exception as e:
        logger.error(f"Failed to get recent logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/uploaded-files")
async def list_uploaded_files():
    """List all uploaded log files available for analysis"""
    try:
        upload_dir = settings.DATA_DIR / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        files = []
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size_bytes": stat.st_size,
                    "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(file_path)
                })
        
        # Sort by upload time (most recent first)
        files.sort(key=lambda x: x["uploaded_at"], reverse=True)
        
        dataset_index = {
            item["filename"]: item
            for item in dataset_service.list_datasets()
        }
        enriched = []
        for item in files:
            dataset = dataset_index.get(item["filename"])
            if dataset is None:
                ensured = dataset_service.ensure_dataset_for_filename(item["filename"])
                if ensured:
                    dataset = dataset_service.get_dataset_by_filename(item["filename"])
            enriched.append(
                {
                    **item,
                    "dataset_id": dataset.get("dataset_id") if dataset else None,
                    "record_count": dataset.get("record_count") if dataset else 0,
                    "db_path": dataset.get("db_path") if dataset else None,
                }
            )

        return {"files": enriched, "count": len(enriched)}
    
    except Exception as e:
        logger.error(f"Failed to list uploaded files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/datasets")
async def list_datasets():
    """List dataset databases derived from uploaded files."""
    return {"datasets": dataset_service.list_datasets()}


@router.delete("/")
async def delete_logs(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    source: Optional[str] = None
):
    """Delete logs matching criteria"""
    try:
        from datetime import datetime
        
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        count = log_service.delete_logs(start_dt, end_dt, source)
        
        return {
            "status": "success",
            "deleted_count": count
        }
    
    except Exception as e:
        logger.error(f"Failed to delete logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
