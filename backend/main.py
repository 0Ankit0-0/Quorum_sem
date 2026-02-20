"""
Quorum - Main Entry Point
AI-Powered Log Analysis for Secure Offline Environments
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from cli.main import cli

if __name__ == '__main__':
    cli()