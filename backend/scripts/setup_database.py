"""
Database Setup Script
Initialize database schema
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import db
from config.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Initialize database"""
    print("Initializing Quorum database...")
    
    try:
        # Database is auto-initialized in DatabaseManager
        # This script just verifies it
        
        total_logs = db.get_table_count('logs')
        total_anomalies = db.get_table_count('anomalies')
        total_techniques = db.get_table_count('mitre_techniques')
        
        print(f"✓ Database initialized")
        print(f"  Logs: {total_logs}")
        print(f"  Anomalies: {total_anomalies}")
        print(f"  MITRE Techniques: {total_techniques}")
    
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        logger.error(f"DB init error: {e}", exc_info=True)


if __name__ == '__main__':
    main()