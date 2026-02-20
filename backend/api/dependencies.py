"""
API Dependencies
Shared dependencies for FastAPI routes
"""
from fastapi import HTTPException, status
from typing import Optional

from core.database import db
from config.logging_config import get_logger

logger = get_logger(__name__)


def verify_session_exists(session_id: str) -> dict:
    """
    Verify that an analysis session exists
    
    Args:
        session_id: Session ID to verify
    
    Returns:
        Session data
    
    Raises:
        HTTPException: If session not found
    """
    query = "SELECT * FROM analysis_sessions WHERE session_id = ?"
    session = db.fetch_one(query, (session_id,))
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return session


def get_database_status() -> dict:
    """Get database connection status"""
    try:
        total_logs = db.get_table_count('logs')
        total_anomalies = db.get_table_count('anomalies')
        
        return {
            'connected': True,
            'total_logs': total_logs,
            'total_anomalies': total_anomalies
        }
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return {
            'connected': False,
            'error': str(e)
        }