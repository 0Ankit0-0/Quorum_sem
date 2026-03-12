"""
Logging Configuration
Structured logging with JSON support
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime
import csv
import io


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Standard text formatter"""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


class CSVFormatter(logging.Formatter):
    """CSV formatter for structured logs."""

    COLUMNS = [
        "timestamp",
        "level",
        "logger",
        "message",
        "module",
        "function",
        "line",
        "exception",
        "extra",
    ]

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        extra = getattr(record, "extra", None)
        if extra:
            try:
                log_data["extra"] = json.dumps(extra)
            except Exception:
                log_data["extra"] = str(extra)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([log_data.get(col, "") for col in self.COLUMNS])
        return output.getvalue().strip("\r\n")


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: str = None,
    log_dir: Path = None,
    log_csv_file: str = None
) -> None:
    """
    Setup application logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type (json or text)
        log_file: Log file name
        log_dir: Directory for log files
    """
    # Create formatter
    if log_format == "json":
        formatter = JSONFormatter()
    elif log_format == "csv":
        formatter = CSVFormatter()
    else:
        formatter = TextFormatter()
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if log_csv_file and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        csv_path = log_dir / log_csv_file
        needs_header = not csv_path.exists() or csv_path.stat().st_size == 0
        csv_handler = logging.FileHandler(csv_path)
        csv_handler.setFormatter(CSVFormatter())
        root_logger.addHandler(csv_handler)
        if needs_header:
            try:
                with csv_path.open("a", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(CSVFormatter.COLUMNS)
            except Exception:
                pass
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module"""
    return logging.getLogger(name)
