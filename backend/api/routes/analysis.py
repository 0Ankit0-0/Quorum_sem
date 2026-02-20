"""
Analysis Routes
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional
from datetime import datetime

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
            threshold=request.threshold
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
                   logs_analyzed, anomalies_detected
            FROM analysis_sessions
            ORDER BY start_time DESC
            LIMIT ?
        """
        
        sessions = db.fetch_all(query, (limit,))
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
