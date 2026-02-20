"""
Pydantic Schemas for API Request/Response Validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class LogSourceType(str, Enum):
    """Log source types"""
    EVTX = "evtx"
    SYSLOG = "syslog"
    AUTO = "auto"


class SeverityLevel(str, Enum):
    """Severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AnalysisAlgorithm(str, Enum):
    """Analysis algorithms"""
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    STATISTICAL = "statistical"
    ENSEMBLE = "ensemble"


# Request Schemas

class LogIngestRequest(BaseModel):
    """Log ingestion request"""
    file_path: str = Field(..., description="Path to log file")
    source_type: LogSourceType = Field(LogSourceType.AUTO, description="Log format type")
    
    class Config:
        use_enum_values = True


class AnalysisRequest(BaseModel):
    """Analysis request"""
    algorithm: AnalysisAlgorithm = Field(AnalysisAlgorithm.ISOLATION_FOREST, description="Algorithm to use")
    start_time: Optional[datetime] = Field(None, description="Start of time range")
    end_time: Optional[datetime] = Field(None, description="End of time range")
    threshold: float = Field(0.95, ge=0.0, le=1.0, description="Anomaly threshold")
    log_source: Optional[str] = Field(None, description="Log source: 'all', 'latest', or specific filename")
    
    class Config:
        use_enum_values = True


class SQLQueryRequest(BaseModel):
    """SQL query request"""
    query: str = Field(..., description="SQL query to execute", min_length=1)
    limit: int = Field(1000, ge=1, le=100000, description="Maximum results to return")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate SQL query for safety"""
        v = v.strip().upper()
        
        # Block dangerous operations
        forbidden_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in forbidden_keywords:
            if keyword in v:
                raise ValueError(f"Query contains forbidden keyword: {keyword}")
        
        # Must be SELECT query
        if not v.startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        return v


class ReportGenerationRequest(BaseModel):
    """Report generation request"""
    report_type: str = Field(..., description="Type of report (csv or pdf)")
    session_id: Optional[str] = Field(None, description="Analysis session ID")
    include_graphs: bool = Field(True, description="Include visualizations (PDF only)")
    
    @validator('report_type')
    def validate_report_type(cls, v):
        if v.lower() not in ['csv', 'pdf']:
            raise ValueError("report_type must be 'csv' or 'pdf'")
        return v.lower()


# Response Schemas

class LogEntryResponse(BaseModel):
    """Log entry response"""
    id: int
    timestamp: datetime
    source: str
    event_type: Optional[str]
    severity: Optional[str]
    message: str
    hostname: Optional[str]
    username: Optional[str]


class AnomalyResponse(BaseModel):
    """Anomaly response"""
    id: int
    log_id: int
    anomaly_score: float
    algorithm: str
    severity: str
    explanation: Optional[str]
    mitre_technique_id: Optional[str]
    mitre_tactic: Optional[str]
    detected_at: datetime


class AnalysisSessionResponse(BaseModel):
    """Analysis session response"""
    session_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    logs_analyzed: int
    anomalies_detected: int
    summary: Dict[str, Any]


class QueryResultResponse(BaseModel):
    """SQL query result response"""
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float


class SystemStatusResponse(BaseModel):
    """System status response"""
    status: str
    environment_type: str
    database_size_mb: float
    total_logs: int
    total_anomalies: int
    uptime_seconds: float


class MitreTechniqueResponse(BaseModel):
    """MITRE technique response"""
    technique_id: str
    technique_name: str
    tactic: str
    description: str
    detection: Optional[str]
    platforms: List[str]