"""
CLI Command Routes
Provides API endpoints for CLI command execution and documentation
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
import shlex
from datetime import datetime

from config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/cli", tags=["CLI"])


class CommandRequest(BaseModel):
    """Request model for CLI command execution"""
    command: str
    args: Optional[List[str]] = []


class CommandResponse(BaseModel):
    """Response model for CLI command execution"""
    command: str
    output: str
    error: Optional[str] = None
    exit_code: int
    executed_at: datetime


class CommandDocumentation(BaseModel):
    """Documentation for a CLI command"""
    command: str
    description: str
    usage: str
    examples: List[str]
    category: str


# CLI Command documentation
CLI_COMMANDS_DOC = {
    "system": [
        {
            "command": "quorum status",
            "description": "Display system overview and health status",
            "usage": "quorum status",
            "examples": ["quorum status"],
            "category": "System"
        },
        {
            "command": "quorum init",
            "description": "Initialize Quorum database and configuration",
            "usage": "quorum init",
            "examples": ["quorum init"],
            "category": "System"
        }
    ],
    "logs": [
        {
            "command": "quorum ingest scan",
            "description": "Auto-discover system log files",
            "usage": "quorum ingest scan",
            "examples": ["quorum ingest scan"],
            "category": "Logs"
        },
        {
            "command": "quorum ingest collect",
            "description": "Collect and import discovered logs into database",
            "usage": "quorum ingest collect",
            "examples": ["quorum ingest collect"],
            "category": "Logs"
        },
        {
            "command": "quorum ingest file",
            "description": "Import a specific log file",
            "usage": "quorum ingest file <file_path>",
            "examples": ["quorum ingest file Security.evtx"],
            "category": "Logs"
        }
    ],
    "analysis": [
        {
            "command": "quorum analyze run",
            "description": "Run AI anomaly detection",
            "usage": "quorum analyze run --algorithm <algorithm>",
            "examples": [
                "quorum analyze run --algorithm ensemble",
                "quorum analyze run --algorithm isolation_forest",
                "quorum analyze run --algorithm one_class_svm"
            ],
            "category": "Analysis"
        },
        {
            "command": "quorum analyze sessions",
            "description": "List all analysis sessions",
            "usage": "quorum analyze sessions",
            "examples": ["quorum analyze sessions"],
            "category": "Analysis"
        }
    ],
    "monitor": [
        {
            "command": "quorum monitor watch",
            "description": "Start real-time log monitoring",
            "usage": "quorum monitor watch [--auto]",
            "examples": ["quorum monitor watch --auto"],
            "category": "Monitor"
        },
        {
            "command": "quorum monitor status",
            "description": "Show real-time monitor status",
            "usage": "quorum monitor status",
            "examples": ["quorum monitor status"],
            "category": "Monitor"
        }
    ],
    "devices": [
        {
            "command": "quorum devices scan",
            "description": "Scan for USB devices and LAN nodes",
            "usage": "quorum devices scan",
            "examples": ["quorum devices scan"],
            "category": "Devices"
        },
        {
            "command": "quorum devices watch",
            "description": "Monitor for USB hotplug events",
            "usage": "quorum devices watch",
            "examples": ["quorum devices watch"],
            "category": "Devices"
        },
        {
            "command": "quorum devices history",
            "description": "Show device connection history",
            "usage": "quorum devices history",
            "examples": ["quorum devices history"],
            "category": "Devices"
        }
    ],
    "hub": [
        {
            "command": "quorum hub register",
            "description": "Register this machine as a node",
            "usage": "quorum hub register --role <role>",
            "examples": ["quorum hub register --role terminal"],
            "category": "Hub"
        },
        {
            "command": "quorum hub export",
            "description": "Export sync package for USB transfer",
            "usage": "quorum hub export",
            "examples": ["quorum hub export"],
            "category": "Hub"
        },
        {
            "command": "quorum hub scan-usb",
            "description": "Scan USB drives for sync packages",
            "usage": "quorum hub scan-usb",
            "examples": ["quorum hub scan-usb"],
            "category": "Hub"
        },
        {
            "command": "quorum hub nodes",
            "description": "List all registered nodes",
            "usage": "quorum hub nodes",
            "examples": ["quorum hub nodes"],
            "category": "Hub"
        },
        {
            "command": "quorum hub correlate",
            "description": "Find cross-node attack correlations",
            "usage": "quorum hub correlate",
            "examples": ["quorum hub correlate"],
            "category": "Hub"
        }
    ],
    "reports": [
        {
            "command": "quorum report generate",
            "description": "Generate threat analysis report",
            "usage": "quorum report generate --type <type>",
            "examples": ["quorum report generate --type pdf"],
            "category": "Reports"
        },
        {
            "command": "quorum report list",
            "description": "List all generated reports",
            "usage": "quorum report list",
            "examples": ["quorum report list"],
            "category": "Reports"
        }
    ]
}


@router.get("/commands")
async def get_all_commands() -> Dict[str, List[CommandDocumentation]]:
    """
    Get documentation for all CLI commands organized by category
    
    Returns:
        Dictionary of commands organized by category
    """
    try:
        return CLI_COMMANDS_DOC
    except Exception as e:
        logger.error(f"Failed to retrieve command documentation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve command documentation"
        )


@router.get("/commands/{category}")
async def get_commands_by_category(category: str) -> List[CommandDocumentation]:
    """
    Get documentation for CLI commands in a specific category
    
    Args:
        category: Command category (system, logs, analysis, monitor, devices, hub, reports)
        
    Returns:
        List of command documentation for the specified category
    """
    try:
        if category not in CLI_COMMANDS_DOC:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found"
            )
        
        return CLI_COMMANDS_DOC[category]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve commands for category {category}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve command documentation"
        )


@router.post("/execute", response_model=CommandResponse)
async def execute_command(request: CommandRequest) -> CommandResponse:
    """
    Execute a CLI command and return the output
    
    WARNING: This endpoint executes system commands and should be properly secured
    in production environments. Consider implementing authentication, authorization,
    and command whitelisting.
    
    Args:
        request: Command execution request
        
    Returns:
        Command execution result with output and exit code
    """
    try:
        # Validate command starts with 'quorum'
        if not request.command.startswith("quorum"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only 'quorum' commands are allowed"
            )
        
        # Build the full command
        full_command = [request.command] + (request.args or [])
        
        logger.info(f"Executing command: {' '.join(full_command)}")
        
        # Execute the command
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        return CommandResponse(
            command=' '.join(full_command),
            output=result.stdout,
            error=result.stderr if result.stderr else None,
            exit_code=result.returncode,
            executed_at=datetime.now()
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command execution timed out: {request.command}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Command execution timed out"
        )
    except FileNotFoundError:
        logger.error(f"Command not found: {request.command}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found. Is Quorum CLI installed?"
        )
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command execution failed: {str(e)}"
        )


@router.get("/help")
async def get_cli_help() -> Dict[str, Any]:
    """
    Get general CLI help information
    
    Returns:
        CLI help information and getting started guide
    """
    return {
        "title": "Quorum CLI Interface",
        "version": "2.4.1",
        "description": "Command-line interface for Quorum cybersecurity platform",
        "getting_started": [
            "All commands start with 'quorum'",
            "Use --help flag on any command for detailed usage",
            "Commands are organized by category: System, Logs, Analysis, Monitor, Devices, Hub, and Reports",
            "Run 'quorum status' to check system health",
            "Run 'quorum ingest collect' to import system logs",
            "Run 'quorum analyze run --algorithm ensemble' to run AI detection"
        ],
        "categories": list(CLI_COMMANDS_DOC.keys()),
        "total_commands": sum(len(cmds) for cmds in CLI_COMMANDS_DOC.values())
    }
