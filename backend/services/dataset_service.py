"""
Dataset Service
Creates one isolated DuckDB database per uploaded file and serves dataset-scoped data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import zipfile
import time

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
                    "duration_seconds": 0.0,
                    "parse_seconds": 0.0,
                    "insert_seconds": 0.0,
                }

            rows = []
            parse_start = time.perf_counter()
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
            parse_seconds = time.perf_counter() - parse_start
            insert_seconds = 0.0
            if rows:
                insert_start = time.perf_counter()
                conn.executemany(
                    """
                    INSERT INTO logs (
                        id, timestamp, source, event_id, event_type, severity, message,
                        raw_data, hostname, username, process_name, process_id, metadata, ingestion_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                insert_seconds = time.perf_counter() - insert_start
            count_row = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
            total = int(count_row[0]) if count_row else 0
            duration = parse_seconds + insert_seconds
            return {
                "dataset_id": record.dataset_id,
                "db_path": record.db_path,
                "records_total": total,
                "inserted_now": len(rows),
                "duration_seconds": round(duration, 2),
                "parse_seconds": round(parse_seconds, 2),
                "insert_seconds": round(insert_seconds, 2),
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
        auto_ingest: bool = True,
    ) -> List[Dict[str, Any]]:
        dataset = (
            self.ensure_dataset_for_filename(filename)
            if auto_ingest
            else self.get_dataset_by_filename(filename)
        )
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
        """Generate a full dataset report bundle and persist bundle metadata."""
        dataset = self.ensure_dataset_for_filename(filename) or self.get_dataset_by_filename(filename)
        if not dataset:
            raise FileNotFoundError("Dataset not found")
        db_path = Path(dataset["db_path"])
        if not db_path.exists():
            raise FileNotFoundError("Dataset DB not found")

        report_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        report_dir = self._create_report_workspace(report_id)
        metrics = self._collect_dataset_metrics(db_path)

        summary = self._build_summary(dataset, report_id, metrics)
        summary_path = self._write_summary_file(report_dir, summary)
        anomalies_path = self._write_anomalies_file(report_dir, metrics["high_risk_rows"])
        ai_path = self._write_ai_analysis_file(
            report_dir=report_dir,
            total_logs=metrics["total_logs"],
            high_risk_count=len(metrics["high_risk_rows"]),
        )

        file_names = ["summary.json", "anomalies.csv", "ai_analysis.json", "integrity.sha256"]
        bundle_hash = self._compute_bundle_hash([summary_path, anomalies_path, ai_path], report_dir)
        self.add_report_metadata(
            filename=filename,
            report_id=report_id,
            report_dir=report_dir,
            hash_sha256=bundle_hash,
            files=file_names,
        )
        return {
            "report_id": report_id,
            "report_dir": str(report_dir),
            "hash_sha256": bundle_hash,
            "files": file_names,
        }

    def _create_report_workspace(self, report_id: str) -> Path:
        report_dir = settings.REPORTS_DIR / f"report_{report_id}"
        report_dir.mkdir(parents=True, exist_ok=True)
        return report_dir

    def _collect_dataset_metrics(self, db_path: Path) -> Dict[str, Any]:
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
            return {
                "total_logs": total_logs,
                "severity_distribution": severity_distribution,
                "high_risk_rows": high_risk_rows,
            }
        finally:
            conn.close()

    def _build_summary(self, dataset: Dict[str, Any], report_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "report_id": report_id,
            "dataset_id": dataset["dataset_id"],
            "filename": dataset["filename"],
            "generated_at": datetime.utcnow().isoformat(),
            "total_logs": metrics["total_logs"],
            "high_risk_records": len(metrics["high_risk_rows"]),
            "severity_distribution": metrics["severity_distribution"],
        }

    def _write_summary_file(self, report_dir: Path, summary: Dict[str, Any]) -> Path:
        path = report_dir / "summary.json"
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return path

    def _write_anomalies_file(self, report_dir: Path, high_risk_rows: List[Any]) -> Path:
        path = report_dir / "anomalies.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp", "source", "severity", "message"])
            for row in high_risk_rows:
                writer.writerow(list(row))
        return path

    def _write_ai_analysis_file(self, report_dir: Path, total_logs: int, high_risk_count: int) -> Path:
        ai_analysis = {
            "threat_score": round(min(1.0, (high_risk_count / max(total_logs, 1)) * 3.0), 4),
            "risk_level": "HIGH" if high_risk_count > 0 else "LOW",
            "confidence": round(min(0.99, 0.65 + (high_risk_count / max(total_logs, 1))), 4),
            "reason": "High-risk severity/messages detected in dataset logs",
            "model": "hybrid_rules_v1",
        }
        path = report_dir / "ai_analysis.json"
        path.write_text(json.dumps(ai_analysis, indent=2), encoding="utf-8")
        return path

    def _compute_bundle_hash(self, files: List[Path], report_dir: Path) -> str:
        joined = "".join(self._hash_file(path) for path in files)
        bundle_hash = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        (report_dir / "integrity.sha256").write_text(bundle_hash, encoding="utf-8")
        return bundle_hash

    def build_report_archive(
        self,
        filename: str,
        report_id: str,
        report_dir: Path,
    ) -> tuple[bytes, str, str]:
        """Build zip payload with dataset outputs, related artifacts, and a file guide."""
        dataset_name = Path(filename).stem
        safe_dataset = "".join(ch if ch.isalnum() else "_" for ch in dataset_name).strip("_") or "dataset"
        prefix = f"{safe_dataset}_{report_id}"

        file_manifest = []
        readme_lines = [
            "QUORUM REPORT BUNDLE",
            "",
            "This archive includes dataset-level outputs and any related session artifacts found.",
            "",
            "File guide:",
            "- *_summary.json: High-level dataset summary and counts.",
            "- *_anomalies.csv: Extracted high-risk/anomalous rows.",
            "- *_ai_analysis.json: Model-derived risk summary.",
            "- *_integrity.sha256: Bundle integrity reference for core dataset files.",
            "- manifest.json: Complete list of files in this ZIP and metadata.",
        ]
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in sorted(report_dir.iterdir()):
                if not fp.is_file():
                    continue
                new_name = f"{prefix}_{fp.name}"
                arcname = f"{prefix}/{new_name}"
                zf.write(fp, arcname=arcname)
                file_manifest.append({"source": fp.name, "archived_as": new_name, "size_bytes": fp.stat().st_size})

            upload_path = self.uploads_dir / Path(filename).name
            if upload_path.exists() and upload_path.is_file():
                upload_arcname = f"{prefix}/input/{upload_path.name}"
                zf.write(upload_path, arcname=upload_arcname)
                file_manifest.append(
                    {
                        "source": str(upload_path),
                        "archived_as": upload_arcname.split("/")[-1],
                        "size_bytes": upload_path.stat().st_size,
                    }
                )
                readme_lines.append("- input/<original log file>: The raw uploaded log source used for this dataset.")

            session_id, session_dir = self._resolve_related_session_artifacts(filename)
            if session_id and session_dir:
                added = 0
                for artifact in sorted(session_dir.iterdir()):
                    if not artifact.is_file():
                        continue
                    session_arcname = f"{prefix}/session_reports/{session_id}/{artifact.name}"
                    zf.write(artifact, arcname=session_arcname)
                    file_manifest.append(
                        {
                            "source": str(artifact),
                            "archived_as": artifact.name,
                            "size_bytes": artifact.stat().st_size,
                        }
                    )
                    added += 1

                if added > 0:
                    readme_lines.extend(
                        [
                            "",
                            f"Related session artifacts included from session: {session_id}",
                            "- session_reports/<session_id>/threat_report_*.pdf: Human-readable analysis report.",
                            "- session_reports/<session_id>/anomaly_report_*.csv: Full anomaly export.",
                            "- session_reports/<session_id>/*.png: Generated chart images (severity/timeline/source/MITRE).",
                        ]
                    )

            manifest = {
                "dataset_filename": Path(filename).name,
                "report_id": report_id,
                "prefix": prefix,
                "generated_at": datetime.utcnow().isoformat(),
                "files": file_manifest,
            }
            zf.writestr(f"{prefix}/README.txt", "\n".join(readme_lines) + "\n")
            zf.writestr(f"{prefix}/manifest.json", json.dumps(manifest, indent=2))

        data = payload.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        zip_name = f"{prefix}.zip"
        return data, digest, zip_name

    def _resolve_related_session_artifacts(self, filename: str) -> tuple[Optional[str], Optional[Path]]:
        """Pick the latest completed analysis session related to this filename, if available."""
        try:
            from core.database import db

            rows = db.fetch_all(
                """
                SELECT session_id, start_time, status, parameters
                FROM analysis_sessions
                ORDER BY start_time DESC
                LIMIT 50
                """
            )
            safe_name = Path(filename).name

            def _session_matches(params_raw: Any) -> bool:
                if not params_raw:
                    return False
                try:
                    payload = params_raw if isinstance(params_raw, dict) else json.loads(params_raw)
                except Exception:
                    return False
                source = str(payload.get("log_source") or "").strip()
                return source == safe_name

            # Prefer exact source match first.
            for row in rows:
                if str(row.get("status") or "").lower() != "completed":
                    continue
                if not _session_matches(row.get("parameters")):
                    continue
                session_id = str(row.get("session_id") or "").strip()
                if not session_id:
                    continue
                session_dir = settings.REPORTS_DIR / session_id
                if session_dir.exists() and session_dir.is_dir():
                    return session_id, session_dir

            # Fallback: latest completed session with existing artifact folder.
            for row in rows:
                if str(row.get("status") or "").lower() != "completed":
                    continue
                session_id = str(row.get("session_id") or "").strip()
                if not session_id:
                    continue
                session_dir = settings.REPORTS_DIR / session_id
                if session_dir.exists() and session_dir.is_dir():
                    return session_id, session_dir
        except Exception as exc:
            logger.warning(f"Could not resolve related session artifacts: {exc}")
        return None, None

    def resolve_report_directory(self, filename: str, report_id: str) -> Path:
        reports = self.list_reports(filename)
        target = next((r for r in reports if r.get("report_id") == report_id), None)
        if not target:
            raise FileNotFoundError("Report not found")
        report_dir = Path(target["report_dir"])
        if not report_dir.exists():
            raise FileNotFoundError("Report directory missing")
        return report_dir

    def resolve_report_file(self, filename: str, report_id: str, requested_file: str) -> Path:
        report_dir = self.resolve_report_directory(filename, report_id)
        safe_file = Path(requested_file).name
        file_path = (report_dir / safe_file).resolve()
        if not file_path.exists() or report_dir.resolve() not in file_path.parents:
            raise FileNotFoundError("Report file not found")
        return file_path

dataset_service = DatasetService()
