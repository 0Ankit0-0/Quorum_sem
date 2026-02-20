"""
Feature Extractor - UPGRADED
Vectorized feature extraction with precompiled regex patterns.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple
from datetime import datetime
import re

import numpy as np

from config.logging_config import get_logger

logger = get_logger(__name__)


RISK_KEYWORDS = {
    "failed password": 0.95, "authentication failed": 0.95,
    "invalid user": 0.90, "sasl login": 0.88, "failed mfa": 0.97,
    "suspicious command": 0.98, "unauthorized": 0.93,
    "brute": 0.96, "exploit": 0.99, "rootkit": 1.0,
    "failed": 0.65, "error": 0.55, "warning": 0.45,
    "denied": 0.70, "rejected": 0.68, "blocked": 0.60,
    "sudo": 0.55, "root": 0.52, "admin": 0.50,
    "disconnect": 0.40, "connect from unknown": 0.65,
    "accepted publickey": 0.25, "started session": 0.15,
    "container started": 0.20, "user login succeeded": 0.20,
}

SOURCE_RISK = {
    "sshd": 0.50, "sudo": 0.60, "kernel": 0.55,
    "auditd": 0.55, "postfix": 0.45, "nginx": 0.40,
    "cron": 0.15, "systemd": 0.15, "dockerd": 0.20,
    "app-worker": 0.45,
}

FAILURE_TOKENS = ("failed", "failure", "denied", "rejected")
PRIVILEGE_TOKENS = ("sudo", "root", "admin", "privilege")
AUTH_TOKENS = ("ssh", "publickey", "password", "login")

IP_REGEX = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
PORT_REGEX = re.compile(r"\bport\s+\d+\b")


class FeatureExtractor:
    """Extract 20 rich features from log data for ML analysis."""

    SEVERITY_MAP = {
        "CRITICAL": 5, "HIGH": 4, "ERROR": 4,
        "MEDIUM": 3, "WARN": 3, "WARNING": 3,
        "LOW": 2, "INFO": 1, "DEBUG": 0, None: 1
    }

    def __init__(self):
        self.feature_names: List[str] = []
        self.source_encoder: Dict[str, int] = {}
        self.event_type_encoder: Dict[str, int] = {}

    def extract_batch(self, logs: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str]]:
        """Extract features from a batch of logs using vectorized operations."""
        if not logs:
            return np.array([]), []

        total = len(logs)
        logger.info(f"Extracting features from {total} logs")
        self._build_encoders(logs)

        timestamps = np.array([self._normalize_timestamp(log.get("timestamp")) for log in logs], dtype=object)
        severities = np.array([self.SEVERITY_MAP.get(log.get("severity"), 1) for log in logs], dtype=np.float64)
        sources = np.array([(log.get("source") or "unknown") for log in logs], dtype=object)
        sources_lower = np.char.lower(sources.astype(str))
        event_types = np.array([(log.get("event_type") or "unknown") for log in logs], dtype=object)
        messages = np.array([(log.get("message") or "") for log in logs], dtype=object)
        msg_lower = np.char.lower(messages.astype(str))
        usernames = np.array([1.0 if log.get("username") else 0.0 for log in logs], dtype=np.float64)
        hostnames = np.array([1.0 if log.get("hostname") else 0.0 for log in logs], dtype=np.float64)
        process_names = np.array([1.0 if log.get("process_name") else 0.0 for log in logs], dtype=np.float64)

        hours = np.fromiter(((ts.hour if ts else 12) for ts in timestamps), dtype=np.float64, count=total)
        weekdays = np.fromiter(((ts.weekday() if ts else 0) for ts in timestamps), dtype=np.float64, count=total)
        after_hours = np.where((hours < 6) | (hours > 22), 1.0, 0.0)

        source_encoded = np.fromiter(
            (self.source_encoder.get(src, 0) for src in sources),
            dtype=np.float64,
            count=total
        )
        source_risk = np.fromiter(
            (SOURCE_RISK.get(src, 0.30) for src in sources_lower),
            dtype=np.float64,
            count=total
        )
        event_type_encoded = np.fromiter(
            (self.event_type_encoder.get(et, 0) for et in event_types),
            dtype=np.float64,
            count=total
        )

        message_len = np.char.str_len(messages.astype(str)).astype(np.float64)
        word_count = np.minimum(
            np.fromiter((len(m.split()) for m in messages), dtype=np.float64, count=total),
            50.0
        )

        keyword_risk = np.zeros(total, dtype=np.float64)
        for kw, risk in RISK_KEYWORDS.items():
            mask = np.char.find(msg_lower, kw) >= 0
            keyword_risk = np.where(mask, np.maximum(keyword_risk, risk), keyword_risk)

        event_id_hash = np.fromiter(
            (
                hash(str(log.get("event_id", ""))) % 10000 if log.get("event_id")
                else 0
                for log in logs
            ),
            dtype=np.float64,
            count=total
        )

        process_id_norm = np.fromiter(
            (
                (int(log.get("process_id")) % 1000) if log.get("process_id") else 0
                for log in logs
            ),
            dtype=np.float64,
            count=total
        )

        has_failure = np.fromiter(
            (1.0 if any(token in msg for token in FAILURE_TOKENS) else 0.0 for msg in msg_lower),
            dtype=np.float64,
            count=total
        )
        has_privilege = np.fromiter(
            (1.0 if any(token in msg for token in PRIVILEGE_TOKENS) else 0.0 for msg in msg_lower),
            dtype=np.float64,
            count=total
        )
        has_auth = np.fromiter(
            (1.0 if any(token in msg for token in AUTH_TOKENS) else 0.0 for msg in msg_lower),
            dtype=np.float64,
            count=total
        )
        has_ip = np.fromiter(
            (1.0 if IP_REGEX.search(msg) else 0.0 for msg in messages),
            dtype=np.float64,
            count=total
        )
        has_port = np.fromiter(
            (1.0 if PORT_REGEX.search(msg) else 0.0 for msg in msg_lower),
            dtype=np.float64,
            count=total
        )

        matrix = np.column_stack(
            [
                hours, weekdays, after_hours,
                severities, source_encoded, source_risk,
                event_type_encoded, message_len, word_count,
                keyword_risk, event_id_hash,
                usernames, hostnames, process_names, process_id_norm,
                has_failure, has_privilege, has_auth,
                has_ip, has_port
            ]
        ).astype(np.float64, copy=False)

        logger.info(f"Extracted {matrix.shape[1]} features")
        return matrix, self.feature_names

    def extract_single(self, log: Dict[str, Any]) -> np.ndarray:
        """Fallback single-log extraction through batch path for consistency."""
        matrix, _ = self.extract_batch([log])
        return matrix[0]

    def _normalize_timestamp(self, timestamp: Any):
        if isinstance(timestamp, datetime):
            return timestamp
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except Exception:
                return None
        return None

    def _build_encoders(self, logs: List[Dict[str, Any]]):
        sources = sorted(set((log.get("source") or "unknown") for log in logs))
        event_types = sorted(set((log.get("event_type") or "unknown") for log in logs))

        self.source_encoder = {s: i for i, s in enumerate(sources)}
        self.event_type_encoder = {e: i for i, e in enumerate(event_types)}

        self.feature_names = [
            "hour_of_day", "day_of_week", "after_hours",
            "severity_level", "source_encoded", "source_risk",
            "event_type_encoded", "message_length", "word_count",
            "keyword_risk", "event_id_hash",
            "has_username", "has_hostname", "has_process", "process_id_norm",
            "has_failure_signal", "has_privilege_signal", "has_auth_signal",
            "has_ip_address", "has_port_number"
        ]

    def explain_anomaly(
        self,
        feature_vector: np.ndarray,
        feature_names: List[str],
        anomaly_score: float
    ) -> str:
        """Generate human-readable explanation."""
        reasons = []
        fv = dict(zip(feature_names, feature_vector))

        if fv.get("after_hours", 0) == 1:
            reasons.append(f"activity at unusual hour ({int(fv.get('hour_of_day', 0)):02d}:00)")
        if fv.get("keyword_risk", 0) >= 0.85:
            reasons.append("high-risk keywords detected")
        elif fv.get("keyword_risk", 0) >= 0.60:
            reasons.append("suspicious keywords present")
        if fv.get("has_failure_signal", 0) == 1:
            reasons.append("authentication/access failure")
        if fv.get("has_privilege_signal", 0) == 1:
            reasons.append("privilege escalation activity")
        if fv.get("severity_level", 0) >= 4:
            reasons.append("high severity event")
        if fv.get("message_length", 0) > 300:
            reasons.append("unusually long message")
        if fv.get("source_risk", 0) >= 0.60:
            reasons.append("high-risk source")

        if reasons:
            return f"Anomaly (score {anomaly_score:.3f}): " + "; ".join(reasons)
        return f"Statistical anomaly detected (score {anomaly_score:.3f})"
