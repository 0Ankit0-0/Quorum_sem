"""
Log Service - UPGRADED
Adds: Windows EVTX scan, Application logs, offline log discovery, USB scan
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import platform

from parsers.parser_factory import ParserFactory
from models.log_entry import LogEntry
from core.database import db
from core.exceptions import ParserError, DatabaseError
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


# ─── Known offline log locations by OS ───────────────────────────────────────

WINDOWS_LOG_SOURCES = {
    'Security':     r'C:\Windows\System32\winevt\Logs\Security.evtx',
    'System':       r'C:\Windows\System32\winevt\Logs\System.evtx',
    'Application':  r'C:\Windows\System32\winevt\Logs\Application.evtx',
    'PowerShell':   r'C:\Windows\System32\winevt\Logs\Windows PowerShell.evtx',
    'TaskScheduler':r'C:\Windows\System32\winevt\Logs\Microsoft-Windows-TaskScheduler%4Operational.evtx',
    'RDP':          r'C:\Windows\System32\winevt\Logs\Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx',
    'WinDefender':  r'C:\Windows\System32\winevt\Logs\Microsoft-Windows-Windows Defender%4Operational.evtx',
}

LINUX_LOG_SOURCES = {
    'syslog':   '/var/log/syslog',
    'messages': '/var/log/messages',
    'auth':     '/var/log/auth.log',
    'secure':   '/var/log/secure',
    'kern':     '/var/log/kern.log',
    'daemon':   '/var/log/daemon.log',
    'dpkg':     '/var/log/dpkg.log',
    'apache2':  '/var/log/apache2/error.log',
    'nginx':    '/var/log/nginx/error.log',
}

MACOS_LOG_SOURCES = {
    'system':  '/var/log/system.log',
    'install': '/var/log/install.log',
}


class LogService:
    """Service for log ingestion with full offline log discovery"""

    def __init__(self):
        self.batch_size = settings.BATCH_SIZE

    # ─── Core Ingestion ───────────────────────────────────────────────────────

    def ingest_file(
        self,
        file_path: Path,
        source_type: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Ingest a single log file"""
        start = time.time()
        file_path = Path(file_path)
        logger.info(f"Starting ingestion: {file_path}")

        try:
            parser = ParserFactory.create_parser(file_path, source_type)
            batch = []
            total_inserted = 0
            error_count = 0

            for entry in parser.parse():
                batch.append(entry.to_dict())
                if len(batch) >= self.batch_size:
                    try:
                        db.insert_batch('logs', batch)
                        total_inserted += len(batch)
                        if progress_callback:
                            progress_callback(total_inserted, None,
                                              f"Ingested {total_inserted} entries")
                        batch.clear()
                    except Exception as e:
                        logger.error(f"Batch insert failed: {e}")
                        error_count += len(batch)
                        batch.clear()

            if batch:
                try:
                    db.insert_batch('logs', batch)
                    total_inserted += len(batch)
                except Exception as e:
                    logger.error(f"Final batch insert failed: {e}")
                    error_count += len(batch)

            duration = time.time() - start
            stats = {
                'file_path': str(file_path),
                'file_size_mb': round(file_path.stat().st_size / (1024 * 1024), 4),
                'entries_inserted': total_inserted,
                'parse_errors': parser.error_count,
                'insert_errors': error_count,
                'duration_seconds': round(duration, 2),
                'entries_per_second': round(total_inserted / duration, 2) if duration > 0 else 0,
                'timestamp': datetime.utcnow().isoformat()
            }

            logger.info(f"Ingestion complete: {total_inserted} entries in {duration:.2f}s")
            return stats

        except ParserError:
            raise
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise DatabaseError(f"Log ingestion failed: {e}")

    def ingest_directory(
        self,
        directory_path: Path,
        recursive: bool = False,
        file_pattern: str = "*",
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Ingest all matching files from a directory"""
        directory_path = Path(directory_path)
        if not directory_path.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")

        files = (list(directory_path.rglob(file_pattern)) if recursive
                 else list(directory_path.glob(file_pattern)))
        files = [f for f in files if f.is_file()]

        logger.info(f"Found {len(files)} file(s) to ingest")
        results = []
        for i, fp in enumerate(files, 1):
            if progress_callback:
                progress_callback(i, len(files), f"Processing {fp.name}")
            try:
                results.append(self.ingest_file(fp))
            except Exception as e:
                logger.error(f"Failed to ingest {fp}: {e}")
                results.append({'file_path': str(fp), 'error': str(e),
                                 'timestamp': datetime.utcnow().isoformat()})
        return results

    # ─── System Log Discovery & Collection ───────────────────────────────────

    def scan_available_logs(self) -> Dict[str, Any]:
        """
        Scan the current system for all available offline log sources.
        Returns what's found without ingesting.
        """
        system = platform.system()
        found = {}

        if system == 'Windows':
            sources = WINDOWS_LOG_SOURCES
        elif system == 'Linux':
            sources = LINUX_LOG_SOURCES
        elif system == 'Darwin':
            sources = MACOS_LOG_SOURCES
        else:
            sources = {}

        for name, path in sources.items():
            p = Path(path)
            if p.exists() and p.is_file():
                try:
                    size_mb = round(p.stat().st_size / (1024 * 1024), 2)
                    found[name] = {
                        'path': str(p),
                        'size_mb': size_mb,
                        'readable': self._is_readable(p),
                        'type': 'evtx' if p.suffix.lower() == '.evtx' else 'syslog'
                    }
                except Exception:
                    pass

        # Also scan USB/removable drives
        usb_logs = self._scan_usb_for_logs()

        return {
            'system': system,
            'system_logs': found,
            'usb_logs': usb_logs,
            'total_found': len(found) + len(usb_logs)
        }

    def ingest_system_logs(
        self,
        log_types: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Collect and ingest logs from the host system.
        log_types: e.g. ['Security', 'System'] for Windows or ['auth', 'syslog'] for Linux
        """
        system = platform.system()
        logger.info(f"Collecting system logs from {system}")

        if system == 'Windows':
            collected = self._collect_windows_logs(log_types)
        elif system == 'Linux':
            collected = self._collect_linux_logs(log_types)
        elif system == 'Darwin':
            collected = self._collect_macos_logs(log_types)
        else:
            raise ValueError(f"Unsupported OS: {system}")

        results = []
        for i, fp in enumerate(collected, 1):
            if progress_callback:
                progress_callback(i, len(collected), f"Ingesting {fp.name}")
            try:
                stats = self.ingest_file(fp)
                results.append(stats)
            except Exception as e:
                logger.error(f"Failed to ingest {fp}: {e}")
                results.append({'file_path': str(fp), 'error': str(e)})

        return {
            'system': system,
            'files_collected': len(collected),
            'files_ingested': len([r for r in results if 'entries_inserted' in r]),
            'total_entries': sum(r.get('entries_inserted', 0) for r in results),
            'details': results
        }

    def ingest_from_scan(
        self,
        selected_sources: Optional[List[str]] = None,
        include_usb: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Ingest from discovered sources (output of scan_available_logs).
        selected_sources: list of source names to ingest (None = all found)
        """
        scan_result = self.scan_available_logs()
        all_sources = {**scan_result['system_logs']}
        if include_usb:
            all_sources.update(scan_result['usb_logs'])

        if selected_sources:
            all_sources = {k: v for k, v in all_sources.items()
                           if k in selected_sources}

        results = []
        items = list(all_sources.items())

        for i, (name, info) in enumerate(items, 1):
            if not info.get('readable', False):
                logger.warning(f"Skipping unreadable source: {name}")
                continue

            if progress_callback:
                progress_callback(i, len(items), f"Ingesting {name}")

            try:
                fp = Path(info['path'])
                src_type = info.get('type')
                stats = self.ingest_file(fp, src_type)
                stats['source_name'] = name
                results.append(stats)
                logger.info(f"Ingested {name}: {stats['entries_inserted']} entries")
            except Exception as e:
                logger.error(f"Failed to ingest {name}: {e}")
                results.append({'source_name': name, 'error': str(e)})

        return {
            'sources_scanned': len(all_sources),
            'sources_ingested': len([r for r in results if 'entries_inserted' in r]),
            'total_entries': sum(r.get('entries_inserted', 0) for r in results),
            'details': results
        }

    # ─── OS-Specific Collectors ───────────────────────────────────────────────

    def _collect_windows_logs(self, log_types: Optional[List[str]] = None) -> List[Path]:
        """Export Windows EVTX logs using wevtutil"""
        import subprocess
        import tempfile

        if log_types is None:
            log_types = ['Security', 'System', 'Application']

        collected = []
        temp_dir = Path(tempfile.gettempdir()) / "quorum_logs"
        temp_dir.mkdir(exist_ok=True)

        for log_type in log_types:
            # First check if .evtx already exists at known path
            known_path = Path(WINDOWS_LOG_SOURCES.get(log_type, ''))
            if known_path.exists() and self._is_readable(known_path):
                collected.append(known_path)
                logger.info(f"Using existing EVTX: {known_path}")
                continue

            # Export via wevtutil
            output_path = temp_dir / f"{log_type.replace(' ', '_')}.evtx"
            try:
                cmd = ['wevtutil', 'epl', log_type, str(output_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and output_path.exists():
                    collected.append(output_path)
                    logger.info(f"Exported {log_type} log via wevtutil")
                else:
                    logger.warning(f"wevtutil failed for {log_type}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error collecting {log_type}: {e}")

        return collected

    def _collect_linux_logs(self, log_types: Optional[List[str]] = None) -> List[Path]:
        """Collect Linux syslog files"""
        sources = LINUX_LOG_SOURCES
        if log_types:
            sources = {k: v for k, v in sources.items() if k in log_types}

        collected = []
        for name, path in sources.items():
            p = Path(path)
            if p.exists() and self._is_readable(p):
                collected.append(p)
                logger.info(f"Found: {p}")
            else:
                logger.debug(f"Not available: {p}")

        return collected

    def _collect_macos_logs(self, log_types: Optional[List[str]] = None) -> List[Path]:
        """Collect macOS logs via log command"""
        import subprocess
        import tempfile

        collected = []
        temp_dir = Path(tempfile.gettempdir()) / "quorum_logs"
        temp_dir.mkdir(exist_ok=True)
        output_path = temp_dir / "macos_system.log"

        try:
            cmd = ['log', 'show', '--style', 'syslog', '--last', '1d']
            with open(output_path, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE,
                                        text=True, timeout=60)
            if output_path.exists() and output_path.stat().st_size > 0:
                collected.append(output_path)
        except Exception as e:
            logger.error(f"macOS log export failed: {e}")

        return collected

    def _scan_usb_for_logs(self) -> Dict[str, Any]:
        """Scan USB/removable drives for log files"""
        import psutil
        usb_logs = {}

        try:
            for partition in psutil.disk_partitions():
                opts = partition.opts.lower()
                is_removable = ('removable' in opts or 'usb' in opts)

                if not is_removable:
                    continue

                mount = Path(partition.mountpoint)
                for ext in ['*.evtx', '*.log', '*.syslog']:
                    for log_file in mount.rglob(ext):
                        if log_file.is_file():
                            key = f"usb_{log_file.stem}"
                            usb_logs[key] = {
                                'path': str(log_file),
                                'size_mb': round(log_file.stat().st_size / (1024*1024), 2),
                                'readable': self._is_readable(log_file),
                                'type': 'evtx' if log_file.suffix == '.evtx' else 'syslog'
                            }
        except Exception as e:
            logger.error(f"USB scan error: {e}")

        return usb_logs

    def _is_readable(self, path: Path) -> bool:
        """Check if file is readable"""
        try:
            with open(path, 'rb') as f:
                f.read(1)
            return True
        except (PermissionError, OSError):
            return False

    # ─── Stats & Management ───────────────────────────────────────────────────

    def get_log_statistics(self) -> Dict[str, Any]:
        """Get statistics about ingested logs"""
        try:
            stats = {'total_logs': db.get_table_count('logs')}

            stats['by_severity'] = {
                r['severity']: r['count'] for r in db.fetch_all(
                    "SELECT severity, COUNT(*) as count FROM logs "
                    "WHERE severity IS NOT NULL GROUP BY severity ORDER BY count DESC"
                )
            }

            stats['top_sources'] = db.fetch_all(
                "SELECT source, COUNT(*) as count FROM logs "
                "GROUP BY source ORDER BY count DESC LIMIT 10"
            )

            stats['time_range'] = db.fetch_one(
                "SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest FROM logs"
            )

            stats['top_event_types'] = db.fetch_all(
                "SELECT event_type, COUNT(*) as count FROM logs "
                "WHERE event_type IS NOT NULL GROUP BY event_type "
                "ORDER BY count DESC LIMIT 10"
            )

            return stats

        except Exception as e:
            logger.error(f"Statistics error: {e}")
            return {}

    def delete_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        source: Optional[str] = None
    ) -> int:
        """Delete logs matching criteria"""
        try:
            conditions, params = [], []
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            if source:
                conditions.append("source = ?")
                params.append(source)

            where = " AND ".join(conditions) if conditions else "1=1"
            count_r = db.fetch_one(f"SELECT COUNT(*) as count FROM logs WHERE {where}",
                                   tuple(params))
            count = count_r['count'] if count_r else 0
            db.execute(f"DELETE FROM logs WHERE {where}", tuple(params))
            logger.info(f"Deleted {count} log entries")
            return count
        except Exception as e:
            logger.error(f"Delete logs error: {e}")
            raise DatabaseError(f"Log deletion failed: {e}")


# Global instance
log_service = LogService()