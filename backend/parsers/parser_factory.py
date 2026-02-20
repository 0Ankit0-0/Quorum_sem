"""
Parser Factory
Creates appropriate parser based on file format
"""
from pathlib import Path
from typing import Optional
from parsers.base_parser import BaseParser
from parsers.evtx_parser import EVTXParser
from parsers.syslog_parser import SyslogParser
from core.exceptions import ParserError
from config.logging_config import get_logger

logger = get_logger(__name__)


class ParserFactory:
    """Factory for creating log parsers"""
    
    # Available parsers
    PARSERS = [
        EVTXParser,
        SyslogParser,
    ]
    
    @staticmethod
    def create_parser(file_path: Path, parser_type: Optional[str] = None) -> BaseParser:
        """
        Create appropriate parser for the given file
        
        Args:
            file_path: Path to log file
            parser_type: Explicit parser type ('evtx', 'syslog'), or None for auto-detection
        
        Returns:
            Parser instance
        
        Raises:
            ParserError: If no suitable parser found
        """
        file_path = Path(file_path)
        
        # Explicit parser type
        if parser_type:
            parser_type = parser_type.lower()
            if parser_type == 'evtx':
                return EVTXParser(file_path)
            elif parser_type == 'syslog':
                return SyslogParser(file_path)
            else:
                raise ParserError(f"Unknown parser type: {parser_type}")
        
        # Auto-detection
        logger.info(f"Auto-detecting parser for: {file_path}")
        
        for parser_class in ParserFactory.PARSERS:
            try:
                parser = parser_class(file_path)
                if parser.detect_format():
                    logger.info(f"Detected format: {parser_class.__name__}")
                    return parser
            except Exception as e:
                logger.debug(f"Parser {parser_class.__name__} failed detection: {e}")
                continue
        
        raise ParserError(f"No suitable parser found for file: {file_path}")
    
    @staticmethod
    def get_supported_formats() -> list:
        """Get list of supported log formats"""
        return [parser.__name__.replace('Parser', '').lower() for parser in ParserFactory.PARSERS]