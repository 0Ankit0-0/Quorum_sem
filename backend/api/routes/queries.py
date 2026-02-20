"""
SQL Query Routes
"""
from fastapi import APIRouter, HTTPException, status

from models.schemas import SQLQueryRequest, QueryResultResponse
from services.query_service import query_service
from config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/queries", tags=["Queries"])


@router.post("/execute", response_model=QueryResultResponse)
async def execute_query(request: SQLQueryRequest):
    """Execute a SQL query on the log database"""
    try:
        result = query_service.execute_query(
            request.query,
            limit=request.limit
        )
        
        return QueryResultResponse(**result)
    
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/saved")
async def get_saved_queries():
    """Get list of commonly used saved queries"""
    try:
        saved = query_service.get_saved_queries()
        return {"queries": saved}
    
    except Exception as e:
        logger.error(f"Failed to get saved queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/history")
async def get_query_history(limit: int = 20):
    """Get recent query history"""
    try:
        history = query_service.get_query_history(limit)
        return {"history": history}
    
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/export")
async def export_query_results(
    query: str,
    output_path: str,
    format: str = "csv"
):
    """Export query results to file"""
    try:
        result_path = query_service.export_query_results(
            query,
            output_path,
            format
        )
        
        return {
            "status": "success",
            "output_path": result_path
        }
    
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )