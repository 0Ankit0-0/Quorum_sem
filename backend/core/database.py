"""
DuckDB Database Manager
Handles all database operations with connection pooling
"""
import duckdb
from typing import List, Dict, Any, Optional
from pathlib import Path
from contextlib import contextmanager
import threading
from datetime import datetime
import atexit
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Singleton database manager for DuckDB"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = settings.database_path
            self.connection = None
            self.initialized = True
            atexit.register(self.close)
            self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and schema"""
        try:
            self._connect_database()
            
            # Configure DuckDB
            self.connection.execute(f"SET threads={settings.DB_THREADS}")
            self.connection.execute(f"SET max_memory='{settings.DB_MAX_MEMORY}'")
            
            # Create schema
            self._create_schema()
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _connect_database(self):
        """Connect to DuckDB, with recovery for incompatible/corrupt file databases."""
        if settings.DB_MEMORY:
            self.connection = duckdb.connect(':memory:')
            logger.info("DuckDB initialized in-memory mode")
            return

        try:
            self.connection = duckdb.connect(str(self.db_path))
            logger.info(f"DuckDB initialized at {self.db_path}")
        except Exception as e:
            if self._is_deserialization_error(e):
                backup_path = self._backup_corrupt_database_file()
                logger.warning(
                    "Detected unreadable DuckDB file at %s. Backed it up to %s and creating a fresh database.",
                    self.db_path,
                    backup_path,
                )
                self.connection = duckdb.connect(str(self.db_path))
                logger.info(f"DuckDB reinitialized at {self.db_path}")
            else:
                raise

    def _is_deserialization_error(self, error: Exception) -> bool:
        """Check whether an exception indicates a DuckDB file deserialization failure."""
        if isinstance(error, duckdb.SerializationException):
            return True
        message = str(error).lower()
        return "serialization error" in message or "failed to deserialize" in message

    def _backup_corrupt_database_file(self) -> Path:
        """Move unreadable database file aside so a new one can be created."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        backup_path = self.db_path.with_name(f"{self.db_path.stem}.corrupt.{timestamp}{self.db_path.suffix}")
        self.db_path.rename(backup_path)
        return backup_path
    
    def _create_schema(self):
        """Create database tables and indexes"""
        try:
            # Logs table
            if not self._table_exists('logs'):
                self.connection.execute("""
                    CREATE TABLE logs (
                        id INTEGER PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        source VARCHAR NOT NULL,
                        event_id VARCHAR,
                        event_type VARCHAR,
                        severity VARCHAR,
                        message TEXT,
                        raw_data TEXT,
                        hostname VARCHAR,
                        username VARCHAR,
                        process_name VARCHAR,
                        process_id INTEGER,
                        metadata JSON,
                        ingestion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            # Create indexes
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
                ON logs(timestamp)
            """)
            
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_event_type 
                ON logs(event_type)
            """)
            
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_severity 
                ON logs(severity)
            """)
            
            # Anomalies table
            if not self._table_exists('anomalies'):
                self.connection.execute("""
                    CREATE TABLE anomalies (
                        id INTEGER PRIMARY KEY,
                        log_id INTEGER,
                        anomaly_score FLOAT NOT NULL,
                        algorithm VARCHAR NOT NULL,
                        features JSON,
                        explanation TEXT,
                        severity VARCHAR,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        mitre_technique_id VARCHAR,
                        mitre_tactic VARCHAR
                    )
                """)
            
            # MITRE ATT&CK techniques table
            if not self._table_exists('mitre_techniques'):
                self.connection.execute("""
                    CREATE TABLE mitre_techniques (
                        technique_id VARCHAR PRIMARY KEY,
                        technique_name VARCHAR NOT NULL,
                        tactic VARCHAR NOT NULL,
                        description TEXT,
                        detection TEXT,
                        mitigation TEXT,
                        platforms JSON,
                        data_sources JSON,
                        metadata JSON
                    )
                """)
            
            # Analysis sessions table
            if not self._table_exists('analysis_sessions'):
                self.connection.execute("""
                    CREATE TABLE analysis_sessions (
                        session_id VARCHAR PRIMARY KEY,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        status VARCHAR NOT NULL,
                        logs_analyzed INTEGER,
                        anomalies_detected INTEGER,
                        parameters JSON,
                        metadata JSON
                    )
                """)

            # Hub node registry
            if not self._table_exists('node_registry'):
                self.connection.execute("""
                    CREATE TABLE node_registry (
                        node_id VARCHAR PRIMARY KEY,
                        hostname VARCHAR NOT NULL,
                        role VARCHAR NOT NULL,
                        status VARCHAR NOT NULL,
                        ip_address VARCHAR,
                        os_info VARCHAR,
                        quorum_version VARCHAR,
                        last_seen TIMESTAMP,
                        last_sync TIMESTAMP,
                        total_logs INTEGER DEFAULT 0,
                        total_anomalies INTEGER DEFAULT 0,
                        sync_method VARCHAR,
                        metadata JSON
                    )
                """)

            # Imported anomalies aggregated across nodes
            if not self._table_exists('hub_anomalies'):
                self.connection.execute("""
                    CREATE TABLE hub_anomalies (
                        original_id INTEGER,
                        source_node VARCHAR NOT NULL,
                        anomaly_score FLOAT,
                        severity VARCHAR,
                        algorithm VARCHAR,
                        mitre_technique_id VARCHAR,
                        mitre_tactic VARCHAR,
                        log_timestamp TIMESTAMP,
                        source VARCHAR,
                        event_type VARCHAR,
                        message TEXT,
                        hostname VARCHAR,
                        username VARCHAR,
                        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

            # Hub sync audit log
            if not self._table_exists('node_sync_log'):
                self.connection.execute("""
                    CREATE TABLE node_sync_log (
                        sync_id VARCHAR PRIMARY KEY,
                        source_node VARCHAR,
                        target_node VARCHAR,
                        sync_method VARCHAR,
                        anomalies_synced INTEGER,
                        synced_at TIMESTAMP,
                        package_path VARCHAR
                    )
                """)

            self._create_index("""
                CREATE INDEX idx_node_registry_last_seen
                ON node_registry(last_seen)
            """)

            self._create_index("""
                CREATE INDEX idx_hub_anomalies_source_node
                ON hub_anomalies(source_node)
            """)

            self._create_index("""
                CREATE INDEX idx_hub_anomalies_mitre
                ON hub_anomalies(mitre_technique_id)
            """)

            self._create_index("""
                CREATE UNIQUE INDEX idx_hub_anomalies_original_source
                ON hub_anomalies(original_id, source_node)
            """)
            
            logger.info("Database schema created successfully")
            
        except Exception as e:
            logger.error(f"Schema creation failed: {e}")
            raise

    def _table_exists(self, table_name: str) -> bool:
        """Check whether a table exists in the main schema."""
        result = self.connection.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_name = ?
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()
        return result is not None

    def _create_index(self, query: str) -> None:
        """
        Create an index while tolerating duplicate-index errors on DuckDB versions
        that don't reliably handle IF NOT EXISTS for all index variants.
        """
        try:
            self.connection.execute(query)
        except Exception as e:
            message = str(e).lower()
            if "already exists" in message and "index" in message:
                logger.debug(f"Skipping existing index: {e}")
                return
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            yield self.connection
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute a query and return results"""
        try:
            with self.get_connection() as conn:
                if params:
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query)
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute a query multiple times with different parameters"""
        try:
            with self.get_connection() as conn:
                conn.executemany(query, params_list)
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute query and fetch all results as dictionaries"""
        try:
            result = self.execute(query, params)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Fetch all failed: {e}")
            raise
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Execute query and fetch one result as dictionary"""
        try:
            result = self.execute(query, params)
            columns = [desc[0] for desc in result.description]
            row = result.fetchone()
            return dict(zip(columns, row)) if row else None
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            raise
    
    def insert_batch(self, table: str, data: List[Dict[str, Any]]) -> int:
        """Batch insert data into table"""
        if not data:
            return 0
        
        try:
            if table in {'logs', 'anomalies'} and 'id' not in data[0]:
                next_id = self._get_next_id(table)
                data = [{**record, 'id': next_id + idx} for idx, record in enumerate(data)]

            # Get column names from first record
            columns = list(data[0].keys())
            placeholders = ', '.join(['?' for _ in columns])
            column_names = ', '.join(columns)
            
            query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
            
            # Prepare parameter list
            params_list = [tuple(record.get(col) for col in columns) for record in data]
            
            self.execute_many(query, params_list)
            
            logger.info(f"Inserted {len(data)} records into {table}")
            return len(data)
            
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            raise

    def _get_next_id(self, table: str) -> int:
        """Get next integer id for tables that do not auto-generate primary keys."""
        result = self.execute(f"SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM {table}")
        return int(result.fetchone()[0])
    
    def get_table_count(self, table: str) -> int:
        """Get row count for a table"""
        try:
            result = self.execute(f"SELECT COUNT(*) as count FROM {table}")
            return result.fetchone()[0]
        except Exception as e:
            logger.error(f"Count query failed: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.connection:
            try:
                # Flush pending changes before process exit.
                self.connection.execute("CHECKPOINT")
            except Exception:
                pass
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")


# Global database instance
db = DatabaseManager()
