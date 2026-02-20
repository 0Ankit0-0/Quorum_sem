"""
Threat Classification Model
Represents classified threats with severity and context
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ThreatCategory(str, Enum):
    """Threat categories based on behavior"""
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_EXFILTRATION = "data_exfiltration"
    PERSISTENCE = "persistence"
    COMMAND_EXECUTION = "command_execution"
    RECONNAISSANCE = "reconnaissance"
    RESOURCE_HIJACKING = "resource_hijacking"
    DENIAL_OF_SERVICE = "denial_of_service"
    MALWARE_ACTIVITY = "malware_activity"
    SUSPICIOUS_NETWORK = "suspicious_network"
    POLICY_VIOLATION = "policy_violation"
    UNKNOWN = "unknown"


class ThreatSeverity(str, Enum):
    """Threat severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class ThreatIndicator:
    """Individual threat indicator"""
    
    indicator_type: str
    value: str
    confidence: float
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'indicator_type': self.indicator_type,
            'value': self.value,
            'confidence': self.confidence,
            'description': self.description
        }


@dataclass
class Threat:
    """Classified threat with full context"""
    
    threat_id: str
    category: ThreatCategory
    severity: ThreatSeverity
    title: str
    description: str
    confidence_score: float
    timestamp: datetime
    affected_systems: List[str] = field(default_factory=list)
    indicators: List[ThreatIndicator] = field(default_factory=list)
    mitre_techniques: List[str] = field(default_factory=list)
    mitre_tactics: List[str] = field(default_factory=list)
    related_log_ids: List[int] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'threat_id': self.threat_id,
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'confidence_score': self.confidence_score,
            'timestamp': self.timestamp.isoformat(),
            'affected_systems': self.affected_systems,
            'indicators': [ind.to_dict() for ind in self.indicators],
            'mitre_techniques': self.mitre_techniques,
            'mitre_tactics': self.mitre_tactics,
            'related_log_ids': self.related_log_ids,
            'remediation_steps': self.remediation_steps,
            'metadata': self.metadata
        }
    
    def get_risk_score(self) -> float:
        """
        Calculate overall risk score (0-100)
        Based on severity, confidence, and affected systems
        """
        # Severity weights
        severity_weights = {
            ThreatSeverity.CRITICAL: 1.0,
            ThreatSeverity.HIGH: 0.75,
            ThreatSeverity.MEDIUM: 0.5,
            ThreatSeverity.LOW: 0.25,
            ThreatSeverity.INFO: 0.1
        }
        
        base_score = severity_weights.get(self.severity, 0.5) * 100
        
        # Adjust by confidence
        confidence_adjusted = base_score * self.confidence_score
        
        # Adjust by scope (number of affected systems)
        scope_multiplier = min(1.0 + (len(self.affected_systems) * 0.1), 2.0)
        
        final_score = min(confidence_adjusted * scope_multiplier, 100.0)
        
        return round(final_score, 2)
    
    def add_indicator(self, indicator_type: str, value: str, 
                     confidence: float, description: str):
        """Add threat indicator"""
        indicator = ThreatIndicator(
            indicator_type=indicator_type,
            value=value,
            confidence=confidence,
            description=description
        )
        self.indicators.append(indicator)
    
    def add_remediation_step(self, step: str):
        """Add remediation step"""
        self.remediation_steps.append(step)


@dataclass
class ThreatSummary:
    """Summary of threats for reporting"""
    
    total_threats: int
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    top_affected_systems: List[Dict[str, Any]]
    average_confidence: float
    time_range: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_threats': self.total_threats,
            'by_severity': self.by_severity,
            'by_category': self.by_category,
            'top_affected_systems': self.top_affected_systems,
            'average_confidence': self.average_confidence,
            'time_range': self.time_range
        }


class ThreatClassifier:
    """Classifies anomalies into specific threat types"""
    
    # Event ID to threat category mapping (Windows)
    WINDOWS_THREAT_MAP = {
        '4625': ThreatCategory.UNAUTHORIZED_ACCESS,  # Failed logon
        '4672': ThreatCategory.PRIVILEGE_ESCALATION,  # Special privileges
        '4720': ThreatCategory.PERSISTENCE,  # Account created
        '4732': ThreatCategory.PRIVILEGE_ESCALATION,  # Group membership change
        '4688': ThreatCategory.COMMAND_EXECUTION,  # Process created
        '5140': ThreatCategory.LATERAL_MOVEMENT,  # Network share access
        '7045': ThreatCategory.PERSISTENCE,  # Service installed
    }
    
    # Keyword-based threat detection
    THREAT_KEYWORDS = {
        ThreatCategory.UNAUTHORIZED_ACCESS: [
            'unauthorized', 'failed login', 'access denied', 'invalid credentials'
        ],
        ThreatCategory.PRIVILEGE_ESCALATION: [
            'privilege', 'administrator', 'sudo', 'elevation', 'root'
        ],
        ThreatCategory.COMMAND_EXECUTION: [
            'powershell', 'cmd.exe', 'bash', 'script', 'execute'
        ],
        ThreatCategory.MALWARE_ACTIVITY: [
            'virus', 'malware', 'trojan', 'ransomware', 'suspicious'
        ],
        ThreatCategory.DATA_EXFILTRATION: [
            'exfiltration', 'data transfer', 'upload', 'copy'
        ]
    }
    
    @staticmethod
    def classify(log_entry: 'LogEntry', anomaly_score: float) -> Optional[Threat]:
        """
        Classify log entry as a specific threat
        
        Args:
            log_entry: Log entry to classify
            anomaly_score: Anomaly score from detection
        
        Returns:
            Threat object if classified, None otherwise
        """
        from models.log_entry import LogEntry
        import uuid
        
        # Try event ID mapping first
        category = ThreatClassifier.WINDOWS_THREAT_MAP.get(
            log_entry.event_id,
            ThreatCategory.UNKNOWN
        )
        
        # Try keyword matching if still unknown
        if category == ThreatCategory.UNKNOWN:
            message_lower = log_entry.message.lower()
            for threat_cat, keywords in ThreatClassifier.THREAT_KEYWORDS.items():
                if any(keyword in message_lower for keyword in keywords):
                    category = threat_cat
                    break
        
        # Determine severity based on anomaly score
        if anomaly_score >= 0.95:
            severity = ThreatSeverity.CRITICAL
        elif anomaly_score >= 0.85:
            severity = ThreatSeverity.HIGH
        elif anomaly_score >= 0.70:
            severity = ThreatSeverity.MEDIUM
        else:
            severity = ThreatSeverity.LOW
        
        # Create threat
        threat = Threat(
            threat_id=str(uuid.uuid4()),
            category=category,
            severity=severity,
            title=f"{category.value.replace('_', ' ').title()} Detected",
            description=log_entry.message[:200],
            confidence_score=anomaly_score,
            timestamp=log_entry.timestamp,
            affected_systems=[log_entry.hostname] if log_entry.hostname else [],
            metadata={
                'event_id': log_entry.event_id,
                'event_type': log_entry.event_type,
                'source': log_entry.source
            }
        )
        
        # Add indicators
        if log_entry.username:
            threat.add_indicator(
                'username',
                log_entry.username,
                anomaly_score,
                'User account involved in suspicious activity'
            )
        
        if log_entry.process_name:
            threat.add_indicator(
                'process',
                log_entry.process_name,
                anomaly_score,
                'Process involved in suspicious activity'
            )
        
        return threat