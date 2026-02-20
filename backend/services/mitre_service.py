"""
MITRE ATT&CK Service
Handles MITRE ATT&CK framework integration and mapping
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from core.database import db
from models.attack_technique import AttackTechnique
from core.exceptions import ConfigurationError
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class MitreService:
    """Service for MITRE ATT&CK operations"""
    
    def __init__(self):
        self.mitre_data_path = settings.MITRE_DIR / "enterprise-attack.json"
        self.techniques_loaded = False
    
    def load_mitre_data(self) -> int:
        """
        Load MITRE ATT&CK data into database
        
        Returns:
            Number of techniques loaded
        """
        logger.info("Loading MITRE ATT&CK data...")
        
        if not self.mitre_data_path.exists():
            logger.warning(f"MITRE data file not found: {self.mitre_data_path}")
            logger.info("Attempting to download MITRE ATT&CK data...")
            self._download_mitre_data()
        
        try:
            with open(self.mitre_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            techniques = []
            
            for obj in data.get('objects', []):
                if obj.get('type') == 'attack-pattern':
                    technique = self._parse_technique(obj)
                    if technique:
                        techniques.append(technique.to_dict())
            
            # Clear existing data
            db.execute("DELETE FROM mitre_techniques")
            
            # Insert new data
            if techniques:
                db.insert_batch('mitre_techniques', techniques)
            
            self.techniques_loaded = True
            logger.info(f"Loaded {len(techniques)} MITRE ATT&CK techniques")
            
            return len(techniques)
        
        except Exception as e:
            logger.error(f"Failed to load MITRE data: {e}")
            raise ConfigurationError(f"MITRE data loading failed: {e}")
    
    def _parse_technique(self, obj: Dict[str, Any]) -> Optional[AttackTechnique]:
        """Parse MITRE technique object"""
        try:
            # Extract technique ID (e.g., T1078)
            external_refs = obj.get('external_references', [])
            technique_id = None
            for ref in external_refs:
                if ref.get('source_name') == 'mitre-attack':
                    technique_id = ref.get('external_id')
                    break
            
            if not technique_id:
                return None
            
            # Extract kill chain phases (tactics)
            kill_chain = obj.get('kill_chain_phases', [])
            tactics = [phase.get('phase_name', '').replace('-', '_') for phase in kill_chain]
            tactic = tactics[0] if tactics else 'unknown'
            
            # Platforms
            platforms = obj.get('x_mitre_platforms', [])
            
            # Data sources
            data_sources = []
            for ds in obj.get('x_mitre_data_sources', []):
                data_sources.append(ds)
            
            technique = AttackTechnique(
                technique_id=technique_id,
                technique_name=obj.get('name', ''),
                tactic=tactic,
                description=obj.get('description', ''),
                platforms=platforms,
                data_sources=data_sources,
                metadata={
                    'created': obj.get('created'),
                    'modified': obj.get('modified'),
                    'version': obj.get('x_mitre_version')
                }
            )
            
            return technique
        
        except Exception as e:
            logger.debug(f"Failed to parse technique: {e}")
            return None
    
    def _download_mitre_data(self):
        """Download MITRE ATT&CK data from official repository"""
        import urllib.request
        
        url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
        
        try:
            logger.info(f"Downloading MITRE ATT&CK data from {url}")
            
            settings.MITRE_DIR.mkdir(parents=True, exist_ok=True)
            
            urllib.request.urlretrieve(url, self.mitre_data_path)
            
            logger.info("MITRE ATT&CK data downloaded successfully")
        
        except Exception as e:
            logger.error(f"Failed to download MITRE data: {e}")
            raise ConfigurationError(
                f"Could not download MITRE data. Please manually download from {url} "
                f"and place at {self.mitre_data_path}"
            )
    
    def map_log_to_techniques(self, log_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map log entry to MITRE ATT&CK techniques
        
        Args:
            log_data: Log entry data
        
        Returns:
            List of matching techniques
        """
        if not self.techniques_loaded:
            count = db.get_table_count('mitre_techniques')
            if count == 0:
                self.load_mitre_data()
            else:
                self.techniques_loaded = True
        
        matches = []
        
        # Event ID based mapping
        event_id = log_data.get('event_id', '')
        if event_id:
            technique = self._map_by_event_id(event_id)
            if technique:
                matches.append(technique)
        
        # Keyword based mapping
        message = log_data.get('message', '').lower()
        event_type = log_data.get('event_type', '').lower()
        
        keyword_matches = self._map_by_keywords(message, event_type)
        matches.extend(keyword_matches)
        
        # Remove duplicates
        seen = set()
        unique_matches = []
        for match in matches:
            if match['technique_id'] not in seen:
                seen.add(match['technique_id'])
                unique_matches.append(match)
        
        return unique_matches
    
    def _map_by_event_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Map Windows event ID to MITRE technique"""
        
        # Event ID to Technique mapping
        EVENT_TECHNIQUE_MAP = {
            '4624': 'T1078',  # Valid Accounts
            '4625': 'T1110',  # Brute Force
            '4672': 'T1078.002',  # Domain Accounts
            '4720': 'T1136.001',  # Create Account: Local Account
            '4732': 'T1098',  # Account Manipulation
            '4688': 'T1059',  # Command and Scripting Interpreter
            '4698': 'T1053.005',  # Scheduled Task/Job
            '4720': 'T1136',  # Create Account
            '5140': 'T1021.002',  # SMB/Windows Admin Shares
            '7045': 'T1543.003',  # Create or Modify System Process: Windows Service
        }
        
        technique_id = EVENT_TECHNIQUE_MAP.get(event_id)
        
        if technique_id:
            query = "SELECT * FROM mitre_techniques WHERE technique_id = ?"
            result = db.fetch_one(query, (technique_id,))
            return result
        
        return None
    
    def _map_by_keywords(self, message: str, event_type: str) -> List[Dict[str, Any]]:
        """Map based on keywords in message"""
        
        # Keyword to Technique mapping
        KEYWORD_MAP = {
            'powershell': 'T1059.001',
            'cmd.exe': 'T1059.003',
            'wmic': 'T1047',
            'mimikatz': 'T1003',
            'credential': 'T1003',
            'password': 'T1003',
            'registry': 'T1112',
            'scheduled task': 'T1053',
            'service': 'T1543',
            'remote desktop': 'T1021.001',
            'ssh': 'T1021.004',
            'lateral movement': 'T1021',
            'privilege escalation': 'T1068',
            'persistence': 'T1546',
        }
        
        matches = []
        combined_text = f"{message} {event_type}"
        
        for keyword, technique_id in KEYWORD_MAP.items():
            if keyword in combined_text:
                query = "SELECT * FROM mitre_techniques WHERE technique_id = ?"
                result = db.fetch_one(query, (technique_id,))
                if result:
                    matches.append(result)
        
        return matches
    
    def get_technique(self, technique_id: str) -> Optional[Dict[str, Any]]:
        """Get technique by ID"""
        try:
            query = "SELECT * FROM mitre_techniques WHERE technique_id = ?"
            return db.fetch_one(query, (technique_id,))
        except Exception as e:
            logger.error(f"Failed to get technique {technique_id}: {e}")
            return None
    
    def get_techniques_by_tactic(self, tactic: str) -> List[Dict[str, Any]]:
        """Get all techniques for a tactic"""
        try:
            query = "SELECT * FROM mitre_techniques WHERE tactic = ? ORDER BY technique_name"
            return db.fetch_all(query, (tactic,))
        except Exception as e:
            logger.error(f"Failed to get techniques for tactic {tactic}: {e}")
            return []
    
    def get_all_tactics(self) -> List[str]:
        """Get list of all tactics"""
        try:
            query = "SELECT DISTINCT tactic FROM mitre_techniques ORDER BY tactic"
            results = db.fetch_all(query)
            return [r['tactic'] for r in results]
        except Exception as e:
            logger.error(f"Failed to get tactics: {e}")
            return []
    
    def get_matrix_summary(self) -> Dict[str, Any]:
        """Get summary of MITRE ATT&CK matrix with detected techniques"""
        try:
            # Get all tactics
            tactics = self.get_all_tactics()
            
            # Get detected techniques (from anomalies)
            detected_query = """
                SELECT 
                    mitre_technique_id,
                    COUNT(*) as detection_count
                FROM anomalies
                WHERE mitre_technique_id IS NOT NULL
                GROUP BY mitre_technique_id
            """
            detected = db.fetch_all(detected_query)
            detected_map = {d['mitre_technique_id']: d['detection_count'] for d in detected}
            
            # Build matrix
            matrix = {}
            for tactic in tactics:
                techniques = self.get_techniques_by_tactic(tactic)
                
                matrix[tactic] = {
                    'total_techniques': len(techniques),
                    'detected_techniques': sum(1 for t in techniques if t['technique_id'] in detected_map),
                    'techniques': [
                        {
                            'technique_id': t['technique_id'],
                            'technique_name': t['technique_name'],
                            'detected': t['technique_id'] in detected_map,
                            'detection_count': detected_map.get(t['technique_id'], 0)
                        }
                        for t in techniques
                    ]
                }
            
            return {
                'tactics': list(matrix.keys()),
                'matrix': matrix,
                'total_techniques': sum(m['total_techniques'] for m in matrix.values()),
                'total_detected': sum(m['detected_techniques'] for m in matrix.values())
            }
        
        except Exception as e:
            logger.error(f"Failed to get matrix summary: {e}")
            return {}
    
    def search_techniques(self, query: str) -> List[Dict[str, Any]]:
        """Search techniques by name or description"""
        try:
            search_query = """
                SELECT * FROM mitre_techniques
                WHERE technique_name LIKE ? OR description LIKE ?
                ORDER BY technique_name
                LIMIT 50
            """
            search_term = f"%{query}%"
            return db.fetch_all(search_query, (search_term, search_term))
        except Exception as e:
            logger.error(f"Failed to search techniques: {e}")
            return []


# Global MITRE service instance
mitre_service = MitreService()