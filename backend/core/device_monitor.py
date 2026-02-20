"""
Real-Time Log Monitor
Tails log files like `tail -f`, parses new lines as they arrive,
runs lightweight anomaly scoring, and emits events via callbacks/SSE queue.
"""
import threading
import time
import queue
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum

from config.logging_config import get_logger

logger = get_logger(__name__)


class StreamEvent(str, Enum):
    NEW_LOG    = "new_log"
    ANOMALY    = "anomaly"
    FILE_ADDED = "file_added"
    FILE_LOST  = "file_lost"
    ERROR      = "error"


class LogStreamEntry:
    """A single log entry received in real-time"""
    def __init__(self, file_path: str, raw_line: str, parsed: Dict[str, Any],
                 anomaly_score: float = 0.0, severity: str = 'INFO'):
        self.file_path    = file_path
        self.raw_line     = raw_line.strip()
        self.parsed       = parsed
        self.anomaly_score = anomaly_score
        self.severity     = severity
        self.received_at  = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path':    self.file_path,
            'raw_line':     self.raw_line,
            'parsed':       self.parsed,
            'anomaly_score': round(self.anomaly_score, 4),
            'severity':     self.severity,
            'received_at':  self.received_at.isoformat(),
        }


class FileTailer:
    """
    Tails a single file, yielding new lines as they appear.
    Handles log rotation (file truncation / re-creation).
    """
    def __init__(self, file_path: Path, poll_interval: float = 0.5):
        self.file_path     = file_path
        self.poll_interval = poll_interval
        self._fp           = None
        self._inode        = None
        self._running      = False

    def start(self):
        self._running = True
        try:
            self._fp = open(self.file_path, 'r', encoding='utf-8',
                            errors='replace')
            self._fp.seek(0, 2)          # Seek to end
            self._inode = os.stat(self.file_path).st_ino
        except Exception as e:
            logger.error(f"Cannot open {self.file_path}: {e}")
            self._running = False

    def stop(self):
        self._running = False
        if self._fp:
            self._fp.close()
            self._fp = None

    def read_new_lines(self) -> List[str]:
        """Return any new lines since last call"""
        if not self._running or not self._fp:
            return []

        lines = []
        try:
            # Detect rotation (file replaced)
            try:
                current_inode = os.stat(self.file_path).st_ino
                if current_inode != self._inode:
                    logger.info(f"Log rotation detected: {self.file_path}")
                    self._fp.close()
                    self._fp = open(self.file_path, 'r', encoding='utf-8',
                                    errors='replace')
                    self._inode = current_inode
            except FileNotFoundError:
                return []

            # Read new content
            while True:
                line = self._fp.readline()
                if not line:
                    break
                if line.strip():
                    lines.append(line)

        except Exception as e:
            logger.error(f"Tail read error {self.file_path}: {e}")

        return lines


class RealtimeMonitor:
    """
    Watches multiple log files simultaneously.
    New lines are parsed, scored, and dispatched to registered callbacks
    and an internal queue (for SSE streaming).

    Usage:
        monitor = RealtimeMonitor()
        monitor.add_file('/var/log/auth.log')
        monitor.add_file('/var/log/syslog')
        monitor.on_event(my_callback)
        monitor.start()
        # ... later ...
        monitor.stop()
    """

    def __init__(self, poll_interval: float = 0.5, max_queue_size: int = 1000):
        self._tailers:       Dict[str, FileTailer]  = {}
        self._running        = False
        self._thread:        Optional[threading.Thread] = None
        self._callbacks:     List[Callable[[StreamEvent, LogStreamEntry], None]] = []
        self._event_queue:   queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._poll_interval  = poll_interval
        self._session_id:    Optional[str] = None
        self._stats = {
            'lines_processed': 0,
            'anomalies_found': 0,
            'files_watched':   0,
            'started_at':      None
        }

        # Lazy-loaded parser & scorer
        self._parser    = None
        self._scorer    = None

    # ─── File Management ─────────────────────────────────────────────────────

    def add_file(self, file_path: str) -> bool:
        """Add a file to watch"""
        p = Path(file_path)
        if not p.exists():
            logger.warning(f"File not found: {file_path}")
            return False
        if file_path in self._tailers:
            logger.debug(f"Already watching: {file_path}")
            return True

        tailer = FileTailer(p, self._poll_interval)
        tailer.start()

        if tailer._running:
            self._tailers[file_path] = tailer
            self._stats['files_watched'] = len(self._tailers)
            logger.info(f"Now watching: {file_path}")
            self._emit_raw(StreamEvent.FILE_ADDED, file_path, {})
            return True
        return False

    def remove_file(self, file_path: str):
        """Stop watching a file"""
        tailer = self._tailers.pop(file_path, None)
        if tailer:
            tailer.stop()
            self._stats['files_watched'] = len(self._tailers)
            logger.info(f"Stopped watching: {file_path}")

    def list_files(self) -> List[str]:
        return list(self._tailers.keys())

    # ─── Lifecycle ───────────────────────────────────────────────────────────

    def start(self, session_id: Optional[str] = None):
        """Start the monitoring loop"""
        if self._running:
            return
        self._running = True
        self._session_id = session_id
        self._stats['started_at'] = datetime.utcnow().isoformat()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="QuorumRealtimeMonitor"
        )
        self._thread.start()
        logger.info(f"Real-time monitor started ({len(self._tailers)} files)")

    def stop(self):
        """Stop the monitoring loop"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        for tailer in self._tailers.values():
            tailer.stop()
        logger.info("Real-time monitor stopped")

    def is_running(self) -> bool:
        return self._running

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, 'files': self.list_files()}

    # ─── Events ──────────────────────────────────────────────────────────────

    def on_event(self, callback: Callable[[StreamEvent, LogStreamEntry], None]):
        """Register event callback"""
        self._callbacks.append(callback)

    def get_event(self, timeout: float = 1.0) -> Optional[LogStreamEntry]:
        """Get next event from queue (for SSE / polling consumers)"""
        try:
            return self._event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    # ─── Core Loop ───────────────────────────────────────────────────────────

    def _monitor_loop(self):
        """Main polling loop"""
        while self._running:
            for file_path, tailer in list(self._tailers.items()):
                try:
                    lines = tailer.read_new_lines()
                    for raw_line in lines:
                        self._process_line(file_path, raw_line)
                except Exception as e:
                    logger.error(f"Monitor loop error for {file_path}: {e}")

            time.sleep(self._poll_interval)

    def _process_line(self, file_path: str, raw_line: str):
        """Parse, score, and dispatch a new log line"""
        try:
            # Parse
            parsed = self._parse_line(file_path, raw_line)
            if not parsed:
                return

            # Score (lightweight - no full ML on each line)
            score, severity = self._quick_score(raw_line, parsed)

            entry = LogStreamEntry(
                file_path     = file_path,
                raw_line      = raw_line,
                parsed        = parsed,
                anomaly_score = score,
                severity      = severity
            )

            self._stats['lines_processed'] += 1
            if score >= 0.70:
                self._stats['anomalies_found'] += 1

            # Persist high-severity entries
            if score >= 0.55:
                self._persist_entry(entry)

            # Dispatch
            event_type = StreamEvent.ANOMALY if score >= 0.70 else StreamEvent.NEW_LOG
            self._emit(event_type, entry)

        except Exception as e:
            logger.error(f"Line processing error: {e}")

    def _parse_line(self, file_path: str, raw_line: str) -> Optional[Dict[str, Any]]:
        """Lightweight parse without full parser overhead"""
        import re
        from datetime import datetime as dt

        line = raw_line.strip()
        if not line:
            return None

        parsed: Dict[str, Any] = {
            'raw': line,
            'source_file': Path(file_path).name,
            'timestamp': datetime.utcnow().isoformat(),
        }

        # RFC 3164: <pri>Mon DD HH:MM:SS host tag: message
        m = re.match(
            r'(?:<\d+>)?(\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+'
            r'(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s*(.*)', line
        )
        if m:
            parsed.update({
                'timestamp': m.group(1),
                'hostname':  m.group(2),
                'source':    m.group(3),
                'pid':       m.group(4),
                'message':   m.group(5),
            })
            return parsed

        # RFC 5424: <pri>1 timestamp hostname app pid msgid - message
        m = re.match(
            r'<(\d+)>1\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+\S+\s+-\s+(.*)', line
        )
        if m:
            parsed.update({
                'priority': m.group(1),
                'timestamp': m.group(2),
                'hostname':  m.group(3),
                'source':    m.group(4),
                'pid':       m.group(5),
                'message':   m.group(6),
            })
            return parsed

        # Fallback
        parsed['message'] = line
        return parsed

    def _quick_score(self, raw_line: str, parsed: Dict[str, Any]) -> tuple:
        """
        Fast keyword-based scoring (no ML overhead per line).
        Returns (score 0-1, severity string)
        """
        line_lower = raw_line.lower()
        message    = (parsed.get('message') or '').lower()

        score = 0.20  # baseline

        # Critical patterns
        if any(w in message for w in [
            'failed password', 'authentication failed', 'invalid user',
            'sasl login', 'brute', 'exploit', 'rootkit', 'malware'
        ]):
            score = 0.95

        elif any(w in message for w in [
            'failed', 'failure', 'denied', 'rejected', 'error',
            'refused', 'blocked', 'unauthorized'
        ]):
            score = max(score, 0.72)

        elif any(w in message for w in [
            'sudo', 'root', 'admin', 'privilege', 'escalat',
            'warning', 'warn', 'connect from unknown'
        ]):
            score = max(score, 0.55)

        elif any(w in message for w in [
            'accepted', 'started', 'success', 'opened'
        ]):
            score = max(score, 0.25)

        # After-hours bonus
        try:
            hour = datetime.utcnow().hour
            if hour < 6 or hour > 22:
                score = min(score + 0.10, 1.0)
        except Exception:
            pass

        # Map to severity
        if score >= 0.90:
            severity = 'CRITICAL'
        elif score >= 0.72:
            severity = 'HIGH'
        elif score >= 0.55:
            severity = 'MEDIUM'
        elif score >= 0.35:
            severity = 'LOW'
        else:
            severity = 'INFO'

        return score, severity

    def _emit(self, event_type: StreamEvent, entry: LogStreamEntry):
        """Dispatch event to queue and callbacks"""
        try:
            self._event_queue.put_nowait(entry)
        except queue.Full:
            # Drop oldest
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait(entry)
            except Exception:
                pass

        for cb in self._callbacks:
            try:
                cb(event_type, entry)
            except Exception:
                pass

    def _emit_raw(self, event_type: StreamEvent, file_path: str, data: dict):
        """Emit a system event (file added/removed)"""
        entry = LogStreamEntry(
            file_path=file_path, raw_line='', parsed=data,
            anomaly_score=0, severity='INFO'
        )
        for cb in self._callbacks:
            try:
                cb(event_type, entry)
            except Exception:
                pass

    def _persist_entry(self, entry: LogStreamEntry):
        """Persist anomalous entry to database"""
        try:
            from core.database import db
            from models.log_entry import LogEntry

            parsed = entry.parsed
            log = LogEntry(
                timestamp    = datetime.utcnow(),
                source       = parsed.get('source', Path(entry.file_path).name),
                message      = parsed.get('message', entry.raw_line),
                event_type   = 'realtime',
                severity     = entry.severity,
                hostname     = parsed.get('hostname'),
                raw_data     = entry.raw_line,
                metadata     = {'stream': True, 'score': entry.anomaly_score}
            )
            db.insert_batch('logs', [log.to_dict()])
        except Exception as e:
            logger.debug(f"Persist entry error: {e}")


# Global singleton
realtime_monitor = RealtimeMonitor()