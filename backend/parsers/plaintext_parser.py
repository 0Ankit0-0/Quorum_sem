"""
Flexible Text Log Parser
Supports generic plaintext, JSON/JSONL, CSV, and key-value style logs.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Any
import csv
import json
import re

from parsers.base_parser import BaseParser
from models.log_entry import LogEntry
from core.exceptions import ParserError
from config.logging_config import get_logger

logger = get_logger(__name__)


class PlainTextParser(BaseParser):
    """Fallback parser for flexible text-based logs."""

    ISO_LINE_REGEX = re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ][0-9:.+-Z]+)\s+(?P<msg>.*)$"
    )
    KV_REGEX = re.compile(r'([A-Za-z0-9_.-]+)=(".*?"|\'.*?\'|\S+)')
    CSV_EXTENSIONS = {".csv", ".tsv"}
    TS_KEYS = ("timestamp", "time", "ts", "@timestamp", "datetime", "date")
    MSG_KEYS = ("message", "msg", "log", "event", "description")
    SRC_KEYS = ("source", "service", "app", "application", "logger")
    SEV_KEYS = ("severity", "level", "log_level", "priority")
    HOST_KEYS = ("hostname", "host", "computer")
    USER_KEYS = ("username", "user", "account")
    EVENT_KEYS = ("event_type", "event", "type", "category")

    def detect_format(self) -> bool:
        """Detect generic plaintext content."""
        if not self.validate_file():
            return False

        # Never attempt to parse EVTX binaries as plaintext.
        if self.file_path.suffix.lower() == ".evtx":
            return False

        try:
            with self.file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                for _ in range(25):
                    line = handle.readline()
                    if not line:
                        break
                    if line.strip():
                        return True
        except Exception as exc:
            logger.debug(f"Plaintext detection failed for {self.file_path}: {exc}")
            return False

        return False

    def parse(self) -> Iterator[LogEntry]:
        """Parse line-by-line text logs with flexible format handling."""
        if not self.validate_file():
            raise ParserError(f"Invalid file: {self.file_path}")

        source_name = self.file_path.name

        try:
            if self._looks_like_csv():
                yield from self._parse_csv(source_name)
                return

            with self.file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line_num, raw in enumerate(handle, 1):
                    line = raw.strip()
                    if not line:
                        continue

                    try:
                        entry = self._parse_line(line, source_name, line_num)
                        if entry is None:
                            continue
                        self.parsed_count += 1
                        yield entry
                    except Exception as exc:
                        self.error_count += 1
                        logger.debug(f"Plaintext parse error line {line_num}: {exc}")

        except Exception as exc:
            logger.error(f"Plaintext parsing failed: {exc}")
            raise ParserError(f"Plaintext parsing failed: {exc}")

    def _parse_line(
        self, line: str, source_name: str, line_num: int
    ) -> Optional[LogEntry]:
        if line.startswith("{") and line.endswith("}"):
            parsed = self._parse_json_line(line)
            if parsed:
                return self._to_log_entry(parsed, source_name, line_num, "json")

        if "=" in line:
            kv = self._parse_kv_line(line)
            if kv:
                return self._to_log_entry(kv, source_name, line_num, "kv")

        timestamp, message = self._extract_timestamp_and_message(line)
        return LogEntry(
            timestamp=timestamp,
            source=source_name,
            event_type="plaintext",
            severity=self._infer_severity(message),
            message=message[:4000],
            raw_data=line[:8000],
            metadata={"format": "plaintext", "line_number": line_num},
        )

    def _parse_json_line(self, line: str) -> Optional[dict[str, Any]]:
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                return value
        except Exception:
            return None
        return None

    def _parse_kv_line(self, line: str) -> Optional[dict[str, str]]:
        pairs = self.KV_REGEX.findall(line)
        if not pairs:
            return None
        result: dict[str, str] = {}
        for key, value in pairs:
            cleaned = value.strip().strip('"').strip("'")
            result[key.lower()] = cleaned
        if result:
            return result
        return None

    def _extract_timestamp_and_message(self, line: str) -> tuple[datetime, str]:
        match = self.ISO_LINE_REGEX.match(line)
        if not match:
            return datetime.utcnow(), line

        raw_ts = match.group("ts").replace(" ", "T")
        message = match.group("msg").strip() or line

        try:
            timestamp = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.utcnow()

        return timestamp, message

    def _looks_like_csv(self) -> bool:
        if self.file_path.suffix.lower() in self.CSV_EXTENSIONS:
            return True
        try:
            with self.file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                lines = [line.strip() for line in handle.readlines(10)]
            lines = [line for line in lines if line]
            if not lines:
                return False

            first = lines[0]
            if first.startswith("{") or first.startswith("["):
                return False
            if "," not in first:
                return False

            return any(
                token in first.lower()
                for token in ("timestamp", "time", "message", "level", "severity")
            )
        except Exception:
            return False

    def _parse_csv(self, source_name: str) -> Iterator[LogEntry]:
        with self.file_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            for line_num, row in enumerate(reader, start=2):
                if not row:
                    continue
                entry = self._to_log_entry(row, source_name, line_num, "csv")
                if entry:
                    self.parsed_count += 1
                    yield entry
                else:
                    self.error_count += 1

    def _to_log_entry(
        self,
        data: dict[str, Any],
        source_name: str,
        line_num: int,
        fmt: str,
    ) -> Optional[LogEntry]:
        normalized = {str(k).lower().strip(): v for k, v in data.items()}

        raw_message = self._pick_first(normalized, self.MSG_KEYS)
        if not raw_message:
            raw_message = self._fallback_message(normalized)
        if not raw_message:
            return None

        source = self._pick_first(normalized, self.SRC_KEYS) or source_name
        severity = self._pick_first(normalized, self.SEV_KEYS) or self._infer_severity(raw_message)
        event_type = self._pick_first(normalized, self.EVENT_KEYS) or fmt
        hostname = self._pick_first(normalized, self.HOST_KEYS)
        username = self._pick_first(normalized, self.USER_KEYS)
        timestamp_raw = self._pick_first(normalized, self.TS_KEYS)
        timestamp = self._parse_flexible_time(timestamp_raw)

        return LogEntry(
            timestamp=timestamp,
            source=str(source)[:255],
            event_type=str(event_type)[:255],
            severity=str(severity).upper()[:32],
            message=str(raw_message)[:4000],
            hostname=(str(hostname)[:255] if hostname else None),
            username=(str(username)[:255] if username else None),
            raw_data=json.dumps(data, default=str)[:8000] if fmt in {"json", "csv", "kv"} else str(raw_message)[:8000],
            metadata={
                "format": fmt,
                "line_number": line_num,
            },
        )

    def _pick_first(self, data: dict[str, Any], keys: tuple[str, ...]) -> Optional[str]:
        for key in keys:
            value = data.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    def _fallback_message(self, data: dict[str, Any]) -> Optional[str]:
        filtered = {
            k: v
            for k, v in data.items()
            if k not in self.TS_KEYS + self.SEV_KEYS + self.SRC_KEYS and v is not None
        }
        if not filtered:
            return None
        return " | ".join(f"{k}={v}" for k, v in list(filtered.items())[:8])

    def _parse_flexible_time(self, value: Optional[str]) -> datetime:
        if not value:
            return datetime.utcnow()

        raw = value.strip()
        # Unix epoch seconds/milliseconds
        if raw.isdigit():
            try:
                iv = int(raw)
                if iv > 10_000_000_000:
                    return datetime.utcfromtimestamp(iv / 1000.0)
                return datetime.utcfromtimestamp(iv)
            except Exception:
                return datetime.utcnow()

        raw_iso = raw.replace(" ", "T").replace("Z", "+00:00")
        for candidate in (raw_iso, raw):
            try:
                return datetime.fromisoformat(candidate)
            except Exception:
                continue

        # Common format: 2026-02-23 10:22:14,123
        for fmt in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S", "%b %d %H:%M:%S"):
            try:
                parsed = datetime.strptime(raw, fmt)
                if fmt == "%b %d %H:%M:%S":
                    return parsed.replace(year=datetime.utcnow().year)
                return parsed
            except Exception:
                continue
        return datetime.utcnow()

    def _infer_severity(self, message: str) -> str:
        m = message.lower()
        if any(token in m for token in ("critical", "panic", "fatal")):
            return "CRITICAL"
        if any(token in m for token in ("error", "failed", "denied", "exception")):
            return "HIGH"
        if any(token in m for token in ("warn", "warning")):
            return "MEDIUM"
        return "LOW"
