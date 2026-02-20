"""
Base Parser Interface
Abstract base class for all log parsers
"""
from abc import ABC, abstractmethod
from typing import List, Iterator, Optional
from pathlib import Path
from models.log_entry import LogEntry
from config.logging_config import get_logger

logger = get_logger(__name__)


class BaseParser(ABC):
    """Abstract base parser class"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.parse_errors = []
        self.parsed_count = 0
        self.error_count = 0
    
    @abstractmethod
    def parse(self) -> Iterator[LogEntry]:
        """
        Parse log file and yield LogEntry objects
        
        Yields:
            LogEntry objects
        """
        pass
    
    @abstractmethod
    def detect_format(self) -> bool:
        """
        Detect if file matches this parser's format
        
        Returns:
            True if format matches, False otherwise
        """
        pass
    
    def validate_file(self) -> bool:
        """Validate that file exists and is readable"""
        if not self.file_path.exists():
            logger.error(f"File not found: {self.file_path}")
            return False
        
        if not self.file_path.is_file():
            logger.error(f"Not a file: {self.file_path}")
            return False
        
        return True
    
    def get_statistics(self) -> dict:
        """Get parsing statistics"""
        return {
            'file_path': str(self.file_path),
            'parsed_count': self.parsed_count,
            'error_count': self.error_count,
            'success_rate': self.parsed_count / max(self.parsed_count + self.error_count, 1)
        }