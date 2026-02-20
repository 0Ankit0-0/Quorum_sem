"""
Log Entry Data Model
Represents a parsed log entry
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class LogEntry:
    """Structured log entry model"""
    
    timestamp: datetime
    source: str
    message: str
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    hostname: Optional[str] = None
    username: Optional[str] = None
    process_name: Optional[str] = None
    process_id: Optional[int] = None
    raw_data: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'source': self.source,
            'event_id': self.event_id,
            'event_type': self.event_type,
            'severity': self.severity,
            'message': self.message,
            'raw_data': self.raw_data,
            'hostname': self.hostname,
            'username': self.username,
            'process_name': self.process_name,
            'process_id': self.process_id,
            'metadata': json.dumps(self.metadata) if self.metadata else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create LogEntry from dictionary"""
        # Parse timestamp if string
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Parse metadata if JSON string
        metadata = data.get('metadata', {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        
        return cls(
            timestamp=timestamp,
            source=data.get('source', 'unknown'),
            message=data.get('message', ''),
            event_id=data.get('event_id'),
            event_type=data.get('event_type'),
            severity=data.get('severity'),
            hostname=data.get('hostname'),
            username=data.get('username'),
            process_name=data.get('process_name'),
            process_id=data.get('process_id'),
            raw_data=data.get('raw_data'),
            metadata=metadata
        )
    
    def __repr__(self) -> str:
        return f"LogEntry(timestamp={self.timestamp}, source={self.source}, event_type={self.event_type})"