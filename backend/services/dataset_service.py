"""
Dataset Service
Creates one isolated DuckDB database per uploaded file and serves dataset-scoped data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv

import duckdb

from config.settings import settings
from config.logging_config import get_logger
from parsers.parser_factory import ParserFactory

logger = get_logger(__name__)


@dataclass
class DatasetRecord:
    dataset_id: str
    filename: str
    file_path: str
    db_path: str
    sha256: str
    size_bytes: int
    uploaded_at: str


class DatasetService:
    def __init__(self):
        self.datasets_dir = settings.DB_DIR / "datasets"
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir = settings.DATA_DIR / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.datasets_dir / "manifest.json"
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        if self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception:
                logger.warning("Failed to parse dataset manifest, recreating")
        return {"datasets": []}

    def _save_manifest(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self._manifest, indent=2),
            encoding="utf-8",
        )

    def _safe_filename(self, filename: str) -> str:
        return Path(filename).name.replace("..", "").strip()

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(8192)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _dataset_id(self, filename: str, sha256: str) -> str:
        stem = Path(filename).stem.lower()
        safe = "".join(ch if ch.isalnum() else "_" for ch in stem)[:32] or "dataset"
        return f"{safe}_{sha256[:12]}"

    def _dataset_db_path(self, dataset_id: str) -> Path:
        return self.datasets_dir / f"{dataset_id}.duckdb"

    def _ensure_schema(self, conn: duckdb.DuckDBPyConnection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id BIGINT,
                timestamp TIMESTAMP,
                source VARCHAR,
                event_id VARCHAR,
                event_type VARCHAR,
                severity VARCHAR,
                message TEXT,
                raw_data TEXT,
                hostname VARCHAR,
                username VARCHAR,
                process_name VARCHAR,
                process_id BIGINT,
                metadata JSON,
                ingestion_time TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id VARCHAR,
                created_at TIMESTAMP,
                model VARCHAR,
                threat_score DOUBLE,
                risk_level VARCHAR,
                confidence DOUBLE,
                reason TEXT,
                metadata JSON
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports_meta (
                report_id VARCHAR,
                created_at TIMESTAMP,
                report_dir VARCHAR,
                hash_sha256 VARCHAR,
                files JSON
            )
            """
        )

    def register_dataset(self, file_path: Path) -> DatasetRecord:
        safe_name = self._safe_filename(file_path.name)
        size_bytes = file_path.stat().st_size
        file_hash = self._hash_file(file_path)
        dataset_id = self._dataset_id(safe_name, file_hash)
        db_path = self._dataset_db_path(dataset_id)

        record = DatasetRecord(
            dataset_id=dataset_id,
            filename=safe_name,
            file_path=str(file_path),
            db_path=str(db_path),
            sha256=file_hash,
            size_bytes=size_bytes,
            uploaded_at=datetime.utcnow().isoformat(),
        )

        existing = next(
            (r for r in self._manifest["datasets"] if r["dataset_id"] == dataset_id),
            None,
        )
        if existing is None:
            self._manifest["datasets"].append(record.__dict__)
            self._save_manifest()

        conn = duckdb.connect(str(db_path))
        try:
            self._ensure_schema(conn)
        finally:
            conn.close()
        return record

    def ingest_uploaded_file(self, file_path: Path, source_type: Optional[str] = None) -> Dict[str, Any]:
        record = self.register_dataset(file_path)
        parser = ParserFactory.create_parser(file_path, source_type)
        conn = duckdb.connect(record.db_path)
        try:
            self._ensure_schema(conn)
            existing_row = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
            existing_total = int(existing_row[0]) if existing_row else 0
            if existing_total > 0:
                return {
                    "dataset_id": record.dataset_id,
                    "db_path": record.db_path,
                    "records_total": existing_total,
                    "inserted_now": 0,
                }

            rows = []
            for entry in parser.parse():
                payload = entry.to_dict()
                rows.append(
                    (
                        None,
                        payload.get("timestamp"),
                        payload.get("source"),
                        payload.get("event_id"),
                        payload.get("event_type"),
                        payload.get("severity"),
                        payload.get("message"),
                        payload.get("raw_data"),
                        payload.get("hostname"),
                        payload.get("username"),
                        payload.get("process_name"),
                        payload.get("process_id"),
                        payload.get("metadata"),
                        datetime.utcnow(),
                    )
                )
            if rows:
                conn.executemany(
                    """
                    INSERT INTO logs (
                        id, timestamp, source, event_id, event_type, severity, message,
                        raw_data, hostname, username, process_name, process_id, metadata, ingestion_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            count_row = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
            total = int(count_row[0]) if count_row else 0
            return {
                "dataset_id": record.dataset_id,
                "db_path": record.db_path,
                "records_total": total,
                "inserted_now": len(rows),
            }
        finally:
            conn.close()

    def ensure_dataset_for_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        safe = self._safe_filename(filename)
        if not safe:
            return None
        existing = self.get_dataset_by_filename(safe)
        if existing and Path(existing.get("db_path", "")).exists():
            return existing

        file_path = (self.uploads_dir / safe).resolve()
        if not file_path.exists() or self.uploads_dir.resolve() not in file_path.parents:
            return existing

        try:
            result = self.ingest_uploaded_file(file_path)
            dataset = self.get_dataset_by_filename(safe) or {}
            return {**dataset, **result}
        except Exception as exc:
            logger.warning(f"Auto-dataset ingest skipped for {safe}: {exc}")
            return existing

    def list_datasets(self) -> List[Dict[str, Any]]:
        datasets = []
        for raw in self._manifest.get("datasets", []):
            db_path = Path(raw["db_path"])
            record_count = 0
            if db_path.exists():
                conn = duckdb.connect(str(db_path), read_only=True)
                try:
                    row = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
                    record_count = int(row[0]) if row else 0
                except Exception:
                    record_count = 0
                finally:
                    conn.close()
            datasets.append({**raw, "record_count": record_count})
        datasets.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        return datasets

    def get_dataset_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        safe = self._safe_filename(filename)
        matches = [r for r in self._manifest.get("datasets", []) if r.get("filename") == safe]
        if not matches:
            return None
        matches.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        return matches[0]

    def fetch_recent_logs(
        self,
        filename: str,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        dataset = self.ensure_dataset_for_filename(filename)
        if not dataset:
            return []
        db_path = Path(dataset["db_path"])
        if not db_path.exists():
            return []

        conn = duckdb.connect(str(db_path), read_only=True)
        try:
            where = "1=1"
            params: List[Any] = []
            if search:
                where = "(lower(message) LIKE ? OR lower(source) LIKE ? OR lower(severity) LIKE ?)"
                pattern = f"%{search.lower()}%"
                params.extend([pattern, pattern, pattern])

            params.append(limit)
            query = f"""
                SELECT
                    row_number() OVER () AS id,
                    timestamp,
                    source,
                    event_type,
                    severity,
                    message,
                    hostname,
                    username
                FROM logs
                WHERE {where}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            result = conn.execute(query, tuple(params))
            columns = [d[0] for d in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]
        finally:
            conn.close()

    def add_report_metadata(
        self,
        filename: str,
        report_id: str,
        report_dir: Path,
        hash_sha256: str,
        files: List[str],
    ) -> None:
        dataset = self.get_dataset_by_filename(filename)
        if not dataset:
            return
        conn = duckdb.connect(str(dataset["db_path"]))
        try:
            self._ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO reports_meta (report_id, created_at, report_dir, hash_sha256, files)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    datetime.utcnow(),
                    str(report_dir),
                    hash_sha256,
                    json.dumps(files),
                ),
            )
        finally:
            conn.close()

    def list_reports(self, filename: str) -> List[Dict[str, Any]]:
        dataset = self.get_dataset_by_filename(filename)
        if not dataset:
            return []
        conn = duckdb.connect(str(dataset["db_path"]), read_only=True)
        try:
            result = conn.execute(
                """
                SELECT report_id, created_at, report_dir, hash_sha256, files
                FROM reports_meta
                ORDER BY created_at DESC
                """
            )
            columns = [d[0] for d in result.description]
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            for row in rows:
                try:
                    row["files"] = json.loads(row.get("files") or "[]")
                except Exception:
                    row["files"] = []
            return rows
        finally:
            conn.close()

    def generate_report_bundle(self, filename: str) -> Dict[str, Any]:
        dataset = self.get_dataset_by_filename(filename)
        if not dataset:
            raise FileNotFoundError("Dataset not found")
        db_path = Path(dataset["db_path"])
        if not db_path.exists():
            raise FileNotFoundError("Dataset DB not found")

        report_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        report_dir = settings.REPORTS_DIR / f"report_{report_id}"
        report_dir.mkdir(parents=True, exist_ok=True)

        conn = duckdb.connect(str(db_path), read_only=True)
        try:
            total_logs_row = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
            total_logs = int(total_logs_row[0]) if total_logs_row else 0
            sev_rows = conn.execute(
                """
                SELECT upper(coalesce(severity, 'LOW')) AS severity, COUNT(*) AS cnt
                FROM logs
                GROUP BY 1
                """
            ).fetchall()
            severity_distribution = {row[0]: int(row[1]) for row in sev_rows}

            high_risk_rows = conn.execute(
                """
                SELECT timestamp, source, severity, message
                FROM logs
                WHERE lower(coalesce(severity, '')) IN ('critical', 'high', 'error')
                   OR lower(message) LIKE '%failed%'
                   OR lower(message) LIKE '%unauthorized%'
                ORDER BY timestamp DESC
                LIMIT 500
                """
            ).fetchall()
        finally:
            conn.close()

        summary = {
            "report_id": report_id,
            "dataset_id": dataset["dataset_id"],
            "filename": dataset["filename"],
            "generated_at": datetime.utcnow().isoformat(),
            "total_logs": total_logs,
            "high_risk_records": len(high_risk_rows),
            "severity_distribution": severity_distribution,
        }

        summary_path = report_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        anomalies_path = report_dir / "anomalies.csv"
        with anomalies_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp", "source", "severity", "message"])
            for row in high_risk_rows:
                writer.writerow(list(row))

        ai_analysis = {
            "threat_score": round(min(1.0, (len(high_risk_rows) / max(total_logs, 1)) * 3.0), 4),
            "risk_level": "HIGH" if len(high_risk_rows) > 0 else "LOW",
            "confidence": round(min(0.99, 0.65 + (len(high_risk_rows) / max(total_logs, 1))), 4),
            "reason": "High-risk severity/messages detected in dataset logs",
            "model": "hybrid_rules_v1",
        }
        ai_path = report_dir / "ai_analysis.json"
        ai_path.write_text(json.dumps(ai_analysis, indent=2), encoding="utf-8")

        file_hash = self._hash_file(summary_path) + self._hash_file(anomalies_path) + self._hash_file(ai_path)
        bundle_hash = hashlib.sha256(file_hash.encode("utf-8")).hexdigest()
        (report_dir / "integrity.sha256").write_text(bundle_hash, encoding="utf-8")

        self.add_report_metadata(
            filename=filename,
            report_id=report_id,
            report_dir=report_dir,
            hash_sha256=bundle_hash,
            files=["summary.json", "anomalies.csv", "ai_analysis.json", "integrity.sha256"],
        )
        return {
            "report_id": report_id,
            "report_dir": str(report_dir),
            "hash_sha256": bundle_hash,
            "files": ["summary.json", "anomalies.csv", "ai_analysis.json", "integrity.sha256"],
        }


dataset_service = DatasetService()
