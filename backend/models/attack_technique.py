"""
MITRE ATT&CK Technique Model
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json


@dataclass
class AttackTechnique:
    """MITRE ATT&CK technique representation"""
    
    technique_id: str
    technique_name: str
    tactic: str
    description: str
    detection: Optional[str] = None
    mitigation: Optional[str] = None
    platforms: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'technique_id': self.technique_id,
            'technique_name': self.technique_name,
            'tactic': self.tactic,
            'description': self.description,
            'detection': self.detection,
            'mitigation': self.mitigation,
            'platforms': json.dumps(self.platforms),
            'data_sources': json.dumps(self.data_sources),
            'metadata': json.dumps(self.metadata) if self.metadata else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttackTechnique':
        """Create AttackTechnique from dictionary"""
        platforms = data.get('platforms', [])
        if isinstance(platforms, str):
            platforms = json.loads(platforms)
        
        data_sources = data.get('data_sources', [])
        if isinstance(data_sources, str):
            data_sources = json.loads(data_sources)
        
        metadata = data.get('metadata', {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        
        return cls(
            technique_id=data['technique_id'],
            technique_name=data['technique_name'],
            tactic=data['tactic'],
            description=data.get('description', ''),
            detection=data.get('detection'),
            mitigation=data.get('mitigation'),
            platforms=platforms,
            data_sources=data_sources,
            metadata=metadata
        )
