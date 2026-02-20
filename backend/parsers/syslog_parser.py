"""
Linux Syslog Parser
Parses Linux syslog files (RFC 3164 and RFC 5424)
"""
from typing import Iterator, Optional
from pathlib import Path
from datetime import datetime
import re

from parsers.base_parser import BaseParser
from models.log_entry import LogEntry
from core.exceptions import ParserError
from config.logging_config import get_logger

logger = get_logger(__name__)


class SyslogParser(BaseParser):
    """Linux Syslog parser supporting RFC 3164 and RFC 5424"""
    
    # RFC 3164 pattern: <priority>timestamp hostname tag: message
    RFC3164_PATTERN = re.compile(
        r'^<(?P<priority>\d+)>'
        r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<tag>[^:\[]+)(?:\[(?P<pid>\d+)\])?:\s*'
        r'(?P<message>.*)$'
    )
    
    # RFC 5424 pattern: <priority>version timestamp hostname app-name procid msgid message
    RFC5424_PATTERN = re.compile(
        r'^<(?P<priority>\d+)>'
        r'(?P<version>\d+)\s+'
        r'(?P<timestamp>\S+)\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<appname>\S+)\s+'
        r'(?P<procid>\S+)\s+'
        r'(?P<msgid>\S+)\s+'
        r'(?P<structdata>\S+)?\s*'
        r'(?P<message>.*)$'
    )
    
    # Simple syslog pattern (no priority)
    SIMPLE_PATTERN = re.compile(
        r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<tag>[^:\[]+)(?:\[(?P<pid>\d+)\])?:\s*'
        r'(?P<message>.*)$'
    )
    
    # Severity levels (from priority)
    SEVERITY_MAP = {
        0: 'CRITICAL',  # Emergency
        1: 'CRITICAL',  # Alert
        2: 'CRITICAL',  # Critical
        3: 'HIGH',      # Error
        4: 'MEDIUM',    # Warning
        5: 'INFO',      # Notice
        6: 'INFO',      # Informational
        7: 'INFO',      # Debug
    }
    
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.current_year = datetime.now().year
    
    def detect_format(self) -> bool:
        """Detect if file is syslog format"""
        if not self.validate_file():
            return False
        
        try:
            # Read first few lines
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for _ in range(10):
                    line = f.readline()
                    if not line:
                        break
                    
                    # Try to match any syslog pattern
                    if (self.RFC3164_PATTERN.match(line) or 
                        self.RFC5424_PATTERN.match(line) or
                        self.SIMPLE_PATTERN.match(line)):
                        return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error detecting syslog format: {e}")
            return False
    
    def parse(self) -> Iterator[LogEntry]:
        """Parse syslog file and yield LogEntry objects"""
        if not self.validate_file():
            raise ParserError(f"Invalid file: {self.file_path}")
        
        logger.info(f"Parsing syslog file: {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = self._parse_line(line)
                        if entry:
                            self.parsed_count += 1
                            yield entry
                    except Exception as e:
                        self.error_count += 1
                        logger.debug(f"Error parsing line {line_num}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Fatal error parsing syslog file: {e}")
            raise ParserError(f"Syslog parsing failed: {e}")
        
        logger.info(f"Syslog parsing complete: {self.parsed_count} entries, {self.error_count} errors")
    
    def _parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse individual syslog line"""
        # Try RFC 5424 first
        match = self.RFC5424_PATTERN.match(line)
        if match:
            return self._parse_rfc5424(match, line)
        
        # Try RFC 3164
        match = self.RFC3164_PATTERN.match(line)
        if match:
            return self._parse_rfc3164(match, line)
        
        # Try simple format
        match = self.SIMPLE_PATTERN.match(line)
        if match:
            return self._parse_simple(match, line)
        
        return None
    
    def _parse_rfc5424(self, match, raw_line: str) -> LogEntry:
        """Parse RFC 5424 format"""
        groups = match.groupdict()
        
        priority = int(groups['priority'])
        severity_code = priority & 0x07  # Last 3 bits
        facility_code = priority >> 3    # First bits
        
        timestamp = self._parse_timestamp_rfc5424(groups['timestamp'])
        
        process_id = None
        if groups['procid'] != '-':
            try:
                process_id = int(groups['procid'])
            except ValueError:
                pass
        
        return LogEntry(
            timestamp=timestamp,
            source=groups['appname'] if groups['appname'] != '-' else 'syslog',
            event_id=groups['msgid'] if groups['msgid'] != '-' else None,
            event_type='syslog',
            severity=self.SEVERITY_MAP.get(severity_code, 'INFO'),
            message=groups['message'],
            hostname=groups['hostname'] if groups['hostname'] != '-' else None,
            process_id=process_id,
            raw_data=raw_line,
            metadata={
                'format': 'rfc5424',
                'priority': priority,
                'facility': facility_code,
                'version': groups['version']
            }
        )
    
    def _parse_rfc3164(self, match, raw_line: str) -> LogEntry:
        """Parse RFC 3164 format"""
        groups = match.groupdict()
        
        priority = int(groups['priority'])
        severity_code = priority & 0x07
        facility_code = priority >> 3
        
        timestamp = self._parse_timestamp_rfc3164(groups['timestamp'])
        
        process_id = None
        if groups['pid']:
            try:
                process_id = int(groups['pid'])
            except ValueError:
                pass
        
        return LogEntry(
            timestamp=timestamp,
            source=groups['tag'],
            event_type='syslog',
            severity=self.SEVERITY_MAP.get(severity_code, 'INFO'),
            message=groups['message'],
            hostname=groups['hostname'],
            process_name=groups['tag'],
            process_id=process_id,
            raw_data=raw_line,
            metadata={
                'format': 'rfc3164',
                'priority': priority,
                'facility': facility_code
            }
        )
    
    def _parse_simple(self, match, raw_line: str) -> LogEntry:
        """Parse simple syslog format (no priority)"""
        groups = match.groupdict()
        
        timestamp = self._parse_timestamp_rfc3164(groups['timestamp'])
        
        process_id = None
        if groups['pid']:
            try:
                process_id = int(groups['pid'])
            except ValueError:
                pass
        
        return LogEntry(
            timestamp=timestamp,
            source=groups['tag'],
            event_type='syslog',
            severity='INFO',
            message=groups['message'],
            hostname=groups['hostname'],
            process_name=groups['tag'],
            process_id=process_id,
            raw_data=raw_line,
            metadata={'format': 'simple'}
        )
    
    def _parse_timestamp_rfc5424(self, timestamp_str: str) -> datetime:
        """Parse RFC 5424 timestamp (ISO 8601)"""
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.utcnow()
    
    def _parse_timestamp_rfc3164(self, timestamp_str: str) -> datetime:
        """Parse RFC 3164 timestamp (BSD syslog format)"""
        try:
            # Format: "Jan 01 12:34:56"
            # Add current year
            timestamp_with_year = f"{timestamp_str} {self.current_year}"
            return datetime.strptime(timestamp_with_year, "%b %d %H:%M:%S %Y")
        except Exception:
            return datetime.utcnow()