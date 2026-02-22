"""
Analysis Routes
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional
from datetime import datetime, timedelta
import json

from models.schemas import AnalysisRequest, AnalysisSessionResponse
from services.analysis_service import analysis_service
from api.dependencies import verify_session_exists
from config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=dict)
async def run_analysis(request: AnalysisRequest):
    """
    Run anomaly detection analysis on logs
    
    This may take several minutes for large datasets.
    """
    try:
        algorithm = (
            request.algorithm.value
            if hasattr(request.algorithm, "value")
            else str(request.algorithm)
        )
        result = analysis_service.analyze_logs(
            algorithm=algorithm,
            start_time=request.start_time,
            end_time=request.end_time,
            threshold=request.threshold,
            log_source=request.log_source,
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/sessions")
async def list_sessions(limit: int = 20):
    """List recent analysis sessions"""
    try:
        from core.database import db
        
        query = """
            SELECT session_id, start_time, end_time, status,
                   logs_analyzed, anomalies_detected, parameters
            FROM analysis_sessions
            ORDER BY start_time DESC
            LIMIT ?
        """

        rows = db.fetch_all(query, (limit,))
        sessions = []

        for row in rows:
            params_raw = row.get("parameters")
            parsed_params = {}
            if params_raw:
                try:
                    parsed_params = (
                        params_raw
                        if isinstance(params_raw, dict)
                        else json.loads(params_raw)
                    )
                except Exception:
                    parsed_params = {}

            start_time = row.get("start_time")
            end_time = row.get("end_time")
            duration_seconds = 0.0
            if start_time and end_time:
                try:
                    duration_seconds = round(
                        (end_time - start_time).total_seconds(), 2
                    )
                except Exception:
                    duration_seconds = 0.0

            sessions.append(
                {
                    "id": row.get("session_id"),
                    "algorithm": parsed_params.get("algorithm", "statistical"),
                    "threshold": float(parsed_params.get("threshold", 0.7)),
                    "total_logs": int(row.get("logs_analyzed") or 0),
                    "anomalies_found": int(row.get("anomalies_detected") or 0),
                    "duration_seconds": duration_seconds,
                    "created_at": start_time,
                    "status": str(row.get("status") or "completed").upper(),
                }
            )

        return {"sessions": sessions}
    
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}")
async def get_session_results(session_id: str):
    """Get detailed results for an analysis session"""
    try:
        # Verify session exists
        verify_session_exists(session_id)
        
        # Get results
        results = analysis_service.get_session_results(session_id)
        
        if 'error' in results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=results['error']
            )
        
        return results
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/anomalies")
async def get_anomalies(
    session_id: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100
):
    """Get detected anomalies with optional filters"""
    try:
        from core.database import db
        
        conditions = []
        params = []
        
        if session_id:
            verify_session_exists(session_id)
            conditions.append("""
                detected_at >= (
                    SELECT start_time FROM analysis_sessions WHERE session_id = ?
                )
            """)
            params.append(session_id)
        
        if severity:
            conditions.append("severity = ?")
            params.append(severity.upper())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT 
                a.id, a.anomaly_score, a.algorithm, a.severity,
                a.explanation, a.mitre_technique_id, a.mitre_tactic,
                a.detected_at,
                l.timestamp, l.source, l.event_type, l.message
            FROM anomalies a
            JOIN logs l ON a.log_id = l.id
            WHERE {where_clause}
            ORDER BY a.anomaly_score DESC
            LIMIT ?
        """
        
        params.append(limit)
        
        anomalies = db.fetch_all(query, tuple(params))
        
        return {
            "anomalies": anomalies,
            "count": len(anomalies)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get anomalies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/severity-distribution")
async def get_severity_distribution():
    """Get anomaly counts grouped by severity for dashboard charts"""
    try:
        from core.database import db

        query = """
            SELECT severity, COUNT(*) AS count
            FROM anomalies
            GROUP BY severity
        """
        rows = db.fetch_all(query)

        distribution = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for row in rows:
            severity = str(row.get("severity") or "").upper()
            if severity in distribution:
                distribution[severity] = int(row.get("count") or 0)

        return {"distribution": distribution}
    except Exception as e:
        logger.error(f"Failed to get severity distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/timeline")
async def get_anomaly_timeline():
    """Get 24h anomaly timeline in 2-hour buckets"""
    try:
        from core.database import db

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start = now - timedelta(hours=22)

        query = """
            SELECT detected_at, severity
            FROM anomalies
            WHERE detected_at >= ?
            ORDER BY detected_at ASC
        """
        rows = db.fetch_all(query, (start,))

        buckets = []
        for offset in range(0, 24, 2):
            bucket_start = start + timedelta(hours=offset)
            bucket_end = bucket_start + timedelta(hours=2)
            bucket_rows = [
                row for row in rows
                if row.get("detected_at")
                and bucket_start <= row["detected_at"] < bucket_end
            ]
            buckets.append(
                {
                    "time": bucket_start.strftime("%H:00"),
                    "anomalies": len(bucket_rows),
                    "critical": len(
                        [
                            row for row in bucket_rows
                            if str(row.get("severity") or "").upper() == "CRITICAL"
                        ]
                    ),
                }
            )

        return {"timeline": buckets}
    except Exception as e:
        logger.error(f"Failed to get anomaly timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/mitre-techniques")
async def get_mitre_techniques():
    """Get MITRE technique-level detection summary from real anomaly data"""
    try:
        from core.database import db

        query = """
            SELECT
                a.mitre_technique_id AS id,
                COALESCE(mt.technique_name, a.mitre_technique_id) AS name,
                COALESCE(a.mitre_tactic, mt.tactic, 'Unknown') AS tactic,
                COUNT(*) AS detections,
                COALESCE(MAX(a.anomaly_score), 0) AS max_score
            FROM anomalies a
            LEFT JOIN mitre_techniques mt
              ON a.mitre_technique_id = mt.technique_id
            WHERE a.mitre_technique_id IS NOT NULL
            GROUP BY 1, 2, 3
            ORDER BY detections DESC
        """
        rows = db.fetch_all(query)

        def score_to_severity(score: float) -> str:
            if score >= 0.90:
                return "CRITICAL"
            if score >= 0.75:
                return "HIGH"
            if score >= 0.55:
                return "MEDIUM"
            return "LOW"

        techniques = [
            {
                "id": str(row.get("id") or ""),
                "name": str(row.get("name") or "Unknown"),
                "tactic": str(row.get("tactic") or "Unknown"),
                "detections": int(row.get("detections") or 0),
                "severity": score_to_severity(float(row.get("max_score") or 0)),
            }
            for row in rows
        ]

        tactics = sorted({t["tactic"] for t in techniques})
        return {
            "tactics": tactics,
            "techniques": techniques,
            "total_detections": sum(t["detections"] for t in techniques),
        }
    except Exception as e:
        logger.error(f"Failed to get MITRE technique summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
