"""
Anomaly Detection Result Model
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class Anomaly:
    """Anomaly detection result"""
    
    log_id: int
    anomaly_score: float
    algorithm: str
    severity: str
    features: Dict[str, Any] = field(default_factory=dict)
    explanation: Optional[str] = None
    mitre_technique_id: Optional[str] = None
    mitre_tactic: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'log_id': self.log_id,
            'anomaly_score': self.anomaly_score,
            'algorithm': self.algorithm,
            'features': json.dumps(self.features) if self.features else None,
            'explanation': self.explanation,
            'severity': self.severity,
            'detected_at': self.detected_at.isoformat() if isinstance(self.detected_at, datetime) else self.detected_at,
            'mitre_technique_id': self.mitre_technique_id,
            'mitre_tactic': self.mitre_tactic
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Anomaly':
        """Create Anomaly from dictionary"""
        detected_at = data.get('detected_at')
        if isinstance(detected_at, str):
            detected_at = datetime.fromisoformat(detected_at)
        
        features = data.get('features', {})
        if isinstance(features, str):
            features = json.loads(features) if features else {}
        
        return cls(
            log_id=data['log_id'],
            anomaly_score=data['anomaly_score'],
            algorithm=data['algorithm'],
            severity=data.get('severity', 'UNKNOWN'),
            features=features,
            explanation=data.get('explanation'),
            mitre_technique_id=data.get('mitre_technique_id'),
            mitre_tactic=data.get('mitre_tactic'),
            detected_at=detected_at or datetime.utcnow()
        )
    
    def get_severity_level(self) -> str:
        """Determine severity based on anomaly score"""
        if self.anomaly_score >= 0.95:
            return "CRITICAL"
        elif self.anomaly_score >= 0.85:
            return "HIGH"
        elif self.anomaly_score >= 0.70:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass
class AnomalyBatch:
    """Batch of anomalies with metadata"""
    
    anomalies: List[Anomaly]
    session_id: str
    total_logs_analyzed: int
    algorithm: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    analysis_duration_seconds: float = 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        severity_counts = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        }
        
        for anomaly in self.anomalies:
            severity = anomaly.get_severity_level()
            severity_counts[severity] += 1
        
        return {
            'total_anomalies': len(self.anomalies),
            'total_logs_analyzed': self.total_logs_analyzed,
            'anomaly_rate': len(self.anomalies) / max(self.total_logs_analyzed, 1),
            'severity_distribution': severity_counts,
            'algorithm': self.algorithm,
            'analysis_duration_seconds': self.analysis_duration_seconds
        }