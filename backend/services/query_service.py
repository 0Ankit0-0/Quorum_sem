"""
SQL Query Service
Handles safe SQL query execution with validation
"""
from typing import List, Dict, Any, Optional
import time
import re

from core.database import db
from core.exceptions import ValidationError, DatabaseError
from config.logging_config import get_logger

logger = get_logger(__name__)


class QueryService:
    """Service for SQL query operations"""
    
    # Forbidden SQL keywords (write operations)
    FORBIDDEN_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
        'CREATE', 'TRUNCATE', 'REPLACE', 'MERGE'
    ]
    
    # Dangerous functions
    FORBIDDEN_FUNCTIONS = [
        'LOAD_EXTENSION', 'ATTACH', 'DETACH'
    ]
    
    def __init__(self):
        self.query_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    def execute_query(
        self,
        query: str,
        limit: int = 1000,
        save_to_history: bool = True
    ) -> Dict[str, Any]:
        """
        Execute SQL query with validation
        
        Args:
            query: SQL query string
            limit: Maximum rows to return
            save_to_history: Save to query history
        
        Returns:
            Query results with metadata
        """
        start_time = time.time()
        
        # Validate query
        self._validate_query(query)
        
        # Add LIMIT if not present
        query_upper = query.upper()
        if 'LIMIT' not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {limit}"
        
        logger.info(f"Executing query: {query[:100]}...")
        
        try:
            # Execute query
            result = db.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in result.description] if result.description else []
            
            # Fetch rows
            rows = result.fetchall()
            
            # Convert to list of dicts
            data = [dict(zip(columns, row)) for row in rows]
            
            execution_time = time.time() - start_time
            
            result_data = {
                'columns': columns,
                'rows': data,
                'row_count': len(data),
                'execution_time_ms': round(execution_time * 1000, 2),
                'query': query
            }
            
            # Save to history
            if save_to_history:
                self._save_to_history(query, result_data, execution_time)
            
            logger.info(f"Query executed: {len(data)} rows in {execution_time:.3f}s")
            
            return result_data
        
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def _validate_query(self, query: str):
        """Validate SQL query for safety"""
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        query_upper = query.upper()
        
        # Must be SELECT
        if not query_upper.strip().startswith('SELECT'):
            raise ValidationError("Only SELECT queries are allowed")
        
        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                raise ValidationError(f"Forbidden keyword: {keyword}")
        
        # Check for forbidden functions
        for func in self.FORBIDDEN_FUNCTIONS:
            if func in query_upper:
                raise ValidationError(f"Forbidden function: {func}")
        
        # Check for comments (can be used for injection)
        if '--' in query or '/*' in query or '*/' in query:
            raise ValidationError("Comments not allowed in queries")
    
    def _save_to_history(self, query: str, result: Dict[str, Any], execution_time: float):
        """Save query to history"""
        self.query_history.append({
            'query': query,
            'row_count': result['row_count'],
            'execution_time_ms': round(execution_time * 1000, 2),
            'timestamp': time.time(),
            'columns': result['columns']
        })
        
        # Trim history
        if len(self.query_history) > self.max_history:
            self.query_history = self.query_history[-self.max_history:]
    
    def get_query_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent query history"""
        return self.query_history[-limit:]
    
    def get_saved_queries(self) -> Dict[str, str]:
        """Get commonly used queries"""
        return {
            'recent_logs': """
                SELECT timestamp, source, event_type, severity, message
                FROM logs
                ORDER BY timestamp DESC
                LIMIT 100
            """,
            'error_logs': """
                SELECT timestamp, source, event_type, message
                FROM logs
                WHERE severity IN ('CRITICAL', 'HIGH', 'ERROR')
                ORDER BY timestamp DESC
            """,
            'login_failures': """
                SELECT timestamp, hostname, username, message
                FROM logs
                WHERE event_type LIKE '%Failed%Login%'
                   OR event_type LIKE '%Failed%Logon%'
                ORDER BY timestamp DESC
            """,
            'event_type_summary': """
                SELECT event_type, COUNT(*) as count
                FROM logs
                GROUP BY event_type
                ORDER BY count DESC
            """,
            'severity_distribution': """
                SELECT severity, COUNT(*) as count
                FROM logs
                WHERE severity IS NOT NULL
                GROUP BY severity
                ORDER BY count DESC
            """,
            'logs_by_hour': """
                SELECT 
                    strftime('%Y-%m-%d %H:00', timestamp) as hour,
                    COUNT(*) as count
                FROM logs
                GROUP BY hour
                ORDER BY hour DESC
            """,
            'top_sources': """
                SELECT source, COUNT(*) as count
                FROM logs
                GROUP BY source
                ORDER BY count DESC
                LIMIT 10
            """,
            'anomaly_summary': """
                SELECT 
                    a.severity,
                    a.algorithm,
                    COUNT(*) as count,
                    AVG(a.anomaly_score) as avg_score
                FROM anomalies a
                GROUP BY a.severity, a.algorithm
                ORDER BY count DESC
            """
        }
    
    def export_query_results(
        self,
        query: str,
        output_path: str,
        format: str = 'csv'
    ) -> str:
        """
        Export query results to file
        
        Args:
            query: SQL query
            output_path: Output file path
            format: Export format ('csv' or 'json')
        
        Returns:
            Path to exported file
        """
        import csv
        import json
        from pathlib import Path
        
        # Execute query
        result = self.execute_query(query, limit=1000000, save_to_history=False)
        
        output_path = Path(output_path)
        
        if format.lower() == 'csv':
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if result['rows']:
                    writer = csv.DictWriter(f, fieldnames=result['columns'])
                    writer.writeheader()
                    writer.writerows(result['rows'])
        
        elif format.lower() == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result['rows'], f, indent=2, default=str)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported {result['row_count']} rows to {output_path}")
        return str(output_path)


# Global query service instance
query_service = QueryService()