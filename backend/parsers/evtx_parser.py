"""
Windows EVTX Log Parser
Parses Windows Event Log files (.evtx)
"""
from typing import Iterator, Optional
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

try:
    import Evtx.Evtx as evtx
    import Evtx.Views as views
    EVTX_AVAILABLE = True
except ImportError:
    EVTX_AVAILABLE = False
    import warnings
    warnings.warn("python-evtx not installed. EVTX parsing will not work.")

from parsers.base_parser import BaseParser
from models.log_entry import LogEntry
from core.exceptions import ParserError
from config.logging_config import get_logger

logger = get_logger(__name__)


class EVTXParser(BaseParser):
    """Windows EVTX log parser"""
    
    # Event ID to Event Type mapping (common Windows events)
    EVENT_TYPE_MAP = {
        '4624': 'Account Logon',
        '4625': 'Failed Logon',
        '4634': 'Account Logoff',
        '4672': 'Special Privileges Assigned',
        '4720': 'User Account Created',
        '4726': 'User Account Deleted',
        '4732': 'Member Added to Security Group',
        '4733': 'Member Removed from Security Group',
        '4688': 'Process Created',
        '4689': 'Process Terminated',
        '5140': 'Network Share Accessed',
        '5145': 'Network Share Checked',
        '1': 'Application Error',
        '1000': 'Application Error',
        '7045': 'Service Installed',
    }
    
    # Severity mapping
    SEVERITY_MAP = {
        '0': 'INFO',
        '1': 'CRITICAL',
        '2': 'HIGH',
        '3': 'MEDIUM',
        '4': 'INFO',
        '5': 'INFO',
    }
    
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        
        if not EVTX_AVAILABLE:
            raise ParserError("python-evtx library not installed")
    
    def detect_format(self) -> bool:
        """Detect if file is EVTX format"""
        if not self.validate_file():
            return False
        
        # Check file extension
        if self.file_path.suffix.lower() != '.evtx':
            return False
        
        # Check magic bytes
        try:
            with open(self.file_path, 'rb') as f:
                magic = f.read(8)
                return magic == b'ElfFile\x00'
        except Exception as e:
            logger.error(f"Error detecting EVTX format: {e}")
            return False
    
    def parse(self) -> Iterator[LogEntry]:
        """Parse EVTX file and yield LogEntry objects"""
        if not self.validate_file():
            raise ParserError(f"Invalid file: {self.file_path}")
        
        logger.info(f"Parsing EVTX file: {self.file_path}")
        
        try:
            with evtx.Evtx(str(self.file_path)) as log:
                for record in log.records():
                    try:
                        entry = self._parse_record(record)
                        if entry:
                            self.parsed_count += 1
                            yield entry
                    except Exception as e:
                        self.error_count += 1
                        logger.warning(f"Error parsing record: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Fatal error parsing EVTX file: {e}")
            raise ParserError(f"EVTX parsing failed: {e}")
        
        logger.info(f"EVTX parsing complete: {self.parsed_count} entries, {self.error_count} errors")
    
    def _parse_record(self, record) -> Optional[LogEntry]:
        """Parse individual EVTX record"""
        try:
            # Get XML representation
            xml_string = record.xml()
            root = ET.fromstring(xml_string)
            
            # Extract namespace
            namespace = {'ns': 'http://schemas.microsoft.com/win/2004/08/events/event'}
            
            # Extract System section
            system = root.find('ns:System', namespace)
            if system is None:
                return None
            
            # Extract fields
            event_id_elem = system.find('ns:EventID', namespace)
            event_id = event_id_elem.text if event_id_elem is not None else 'Unknown'
            
            # Timestamp
            time_created = system.find('ns:TimeCreated', namespace)
            timestamp_str = time_created.get('SystemTime') if time_created is not None else None
            timestamp = self._parse_timestamp(timestamp_str) if timestamp_str else datetime.utcnow()
            
            # Computer/Hostname
            computer = system.find('ns:Computer', namespace)
            hostname = computer.text if computer is not None else None
            
            # Level/Severity
            level = system.find('ns:Level', namespace)
            severity_code = level.text if level is not None else '4'
            severity = self.SEVERITY_MAP.get(severity_code, 'INFO')
            
            # Provider
            provider = system.find('ns:Provider', namespace)
            source = provider.get('Name') if provider is not None else 'Unknown'
            
            # Event Data
            event_data = root.find('ns:EventData', namespace)
            username = None
            process_name = None
            process_id = None
            
            if event_data is not None:
                for data in event_data.findall('ns:Data', namespace):
                    name = data.get('Name', '')
                    value = data.text
                    
                    if name in ['TargetUserName', 'SubjectUserName']:
                        username = value
                    elif name == 'ProcessName':
                        process_name = value
                    elif name == 'ProcessId':
                        try:
                            process_id = int(value, 16) if value and value.startswith('0x') else int(value)
                        except (ValueError, TypeError):
                            pass
            
            # Message
            message_elem = root.find('.//ns:RenderingInfo/ns:Message', namespace)
            message = message_elem.text if message_elem is not None else f"Event ID {event_id}"
            
            # Event type
            event_type = self.EVENT_TYPE_MAP.get(event_id, f"Event-{event_id}")
            
            return LogEntry(
                timestamp=timestamp,
                source=source,
                event_id=event_id,
                event_type=event_type,
                severity=severity,
                message=message or '',
                hostname=hostname,
                username=username,
                process_name=process_name,
                process_id=process_id,
                raw_data=xml_string,
                metadata={
                    'format': 'evtx',
                    'record_number': record.record_num()
                }
            )
        
        except Exception as e:
            logger.debug(f"Error parsing EVTX record: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse Windows timestamp string"""
        try:
            # Windows uses ISO 8601 format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.debug(f"Error parsing timestamp '{timestamp_str}': {e}")
            return datetime.utcnow()
