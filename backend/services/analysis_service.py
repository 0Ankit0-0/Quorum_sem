"""
Analysis Service - UPGRADED
Orchestrates hybrid AI analysis with performance-aware execution.
"""
from __future__ import annotations

from datetime import datetime
import time
import uuid
from typing import Any, Dict, List, Optional

from ai_engine.utils.performance import StepTimer, maybe_collect_garbage
from config.logging_config import get_logger
from config.settings import settings
from core.database import db
from core.exceptions import AIEngineError, DatabaseError
from models.anomaly import Anomaly, AnomalyBatch

logger = get_logger(__name__)


LARGE_DATASET_THRESHOLD = int(getattr(settings, "AI_LARGE_DATASET_THRESHOLD", 100000))


class AnalysisService:
    """Service for log analysis with hybrid AI."""

    def __init__(self):
        self.current_session_id: Optional[str] = None

    def analyze_logs(
        self,
        algorithm: str = "ensemble",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        threshold: float = 0.70,
        log_source: Optional[str] = None,
        contamination: float = 0.05,
        progress_callback: Optional[callable] = None,
        auto_report: bool = True,
        force_retrain: bool = False,
    ) -> Dict[str, Any]:
        start_analysis_time = time.perf_counter()
        timer = StepTimer()
        timings: Dict[str, float] = {
            "load_logs_seconds": 0.0,
            "feature_extraction_seconds": 0.0,
            "detection_seconds": 0.0,
            "insert_anomalies_seconds": 0.0,
            "mitre_map_seconds": 0.0,
            "report_seconds": 0.0,
        }

        session_id = str(uuid.uuid4())
        self.current_session_id = session_id

        logger.info(f"Starting analysis session {session_id} | algorithm={algorithm}")

        try:
            requested_algorithm = str(algorithm or "ensemble").lower()
            self._create_session(
                session_id, requested_algorithm, start_time, end_time, threshold, log_source
            )

            load_start = time.perf_counter()
            logs_data = self._load_logs(start_time, end_time, log_source)
            timings["load_logs_seconds"] = time.perf_counter() - load_start
            total_logs = len(logs_data)
            if total_logs == 0:
                return {
                    "session_id": session_id,
                    "status": "completed",
                    "logs_analyzed": 0,
                    "anomalies_detected": 0,
                    "message": "No logs found in specified range",
                }

            resolved_algorithm = self._resolve_algorithm(
                requested_algorithm=requested_algorithm,
                total_logs=total_logs,
            )

            logger.info(
                "Loaded %s logs for analysis (requested=%s, resolved=%s)",
                f"{total_logs:,}",
                requested_algorithm,
                resolved_algorithm,
            )

            from ai_engine.ensemble import EnsembleDetector
            from ai_engine.feature_extractor import FeatureExtractor

            feature_extractor = FeatureExtractor()
            detector = EnsembleDetector()

            anomalies: List[Anomaly] = []

            if total_logs > LARGE_DATASET_THRESHOLD:
                chunk_size = 10000
                logger.info(
                    "Large dataset detected (%s logs); enabling chunked processing with chunk size %s",
                    f"{total_logs:,}",
                    f"{chunk_size:,}",
                )
            else:
                chunk_size = total_logs

            processed = 0
            feature_names: List[str] = []

            for offset in range(0, total_logs, chunk_size):
                chunk = logs_data[offset : offset + chunk_size]

                if progress_callback:
                    progress_callback(
                        processed,
                        total_logs,
                        f"Processing logs {offset + 1}-{min(offset + len(chunk), total_logs)}",
                    )

                timer.start("feature_extraction")
                features, feature_names = feature_extractor.extract_batch(chunk)
                feat_elapsed = timer.stop("feature_extraction").seconds
                timings["feature_extraction_seconds"] += feat_elapsed
                logger.info(f"Feature extraction time: {feat_elapsed:.3f} sec")

                timer.start("detection")
                predictions, anomaly_scores = detector.detect(
                    features,
                    algorithm=resolved_algorithm,
                    contamination=contamination,
                    raw_logs=chunk,
                    force_retrain=force_retrain,
                )
                detect_elapsed = timer.stop("detection").seconds
                timings["detection_seconds"] += detect_elapsed
                logger.info(f"Detection time: {detect_elapsed:.3f} sec")

                anomalies.extend(
                    self._build_anomalies(
                        logs_chunk=chunk,
                        features=features,
                        feature_names=feature_names,
                        predictions=predictions,
                        anomaly_scores=anomaly_scores,
                        threshold=threshold,
                        algorithm=resolved_algorithm,
                        feature_extractor=feature_extractor,
                    )
                )

                processed += len(chunk)
                maybe_collect_garbage()

            logger.info(f"Detected {len(anomalies):,} anomalies above threshold {threshold}")

            if progress_callback:
                progress_callback(total_logs, total_logs, "Saving results")

            if anomalies:
                anomaly_dicts = [a.to_dict() for a in anomalies]
                insert_start = time.perf_counter()
                db.insert_batch("anomalies", anomaly_dicts)
                timings["insert_anomalies_seconds"] = time.perf_counter() - insert_start

            mitre_start = time.perf_counter()
            self._map_to_mitre(anomalies)
            timings["mitre_map_seconds"] = time.perf_counter() - mitre_start

            duration = time.perf_counter() - start_analysis_time
            timings["total_seconds"] = duration

            batch = AnomalyBatch(
                anomalies=anomalies,
                session_id=session_id,
                total_logs_analyzed=total_logs,
                algorithm=resolved_algorithm,
                parameters={"threshold": threshold, "contamination": contamination},
                analysis_duration_seconds=duration,
            )

            summary = batch.get_summary()

            if auto_report and anomalies:
                try:
                    from services.report_service import report_service
                    report_start = time.perf_counter()
                    report_service.generate_session_reports(session_id)
                    timings["report_seconds"] = time.perf_counter() - report_start
                    logger.info(f"Auto-generated reports for session {session_id}")
                except Exception as e:
                    logger.warning(f"Auto-report generation failed: {e}")

            logger.info(f"Total pipeline time: {duration:.3f} sec")
            self._update_session(
                session_id,
                status="completed",
                logs_analyzed=total_logs,
                anomalies_detected=len(anomalies),
                duration=duration,
                metadata={"timings": {k: round(v, 3) for k, v in timings.items()}},
            )

            return {
                "session_id": session_id,
                "status": "completed",
                "logs_analyzed": total_logs,
                "anomalies_detected": len(anomalies),
                "duration_seconds": round(duration, 2),
                "algorithm": resolved_algorithm,
                "requested_algorithm": requested_algorithm,
                "threshold": threshold,
                "log_source": log_source,
                "summary": summary,
                "timings": {k: round(v, 3) for k, v in timings.items()},
            }

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self._update_session(
                session_id,
                status="failed",
                error=str(e),
                metadata={"timings": {k: round(v, 3) for k, v in timings.items()}},
            )
            raise AIEngineError(f"Analysis failed: {e}")

    def _build_anomalies(
        self,
        logs_chunk: List[Dict[str, Any]],
        features,
        feature_names,
        predictions,
        anomaly_scores,
        threshold,
        algorithm,
        feature_extractor,
    ) -> List[Anomaly]:
        results: List[Anomaly] = []
        for i, (log_data, score, pred) in enumerate(zip(logs_chunk, anomaly_scores, predictions)):
            if pred == -1 and float(score) >= threshold:
                explanation = feature_extractor.explain_anomaly(features[i], feature_names, float(score))
                severity = self._calculate_severity(float(score))
                anomaly = Anomaly(
                    log_id=log_data["id"],
                    anomaly_score=float(score),
                    algorithm=algorithm,
                    severity=severity,
                    features={name: float(features[i][j]) for j, name in enumerate(feature_names)},
                    explanation=explanation,
                )
                results.append(anomaly)
        return results

    def _load_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        log_source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            base_conditions = []
            base_params: List[Any] = []

            if start_time:
                base_conditions.append("timestamp >= ?")
                base_params.append(start_time)
            if end_time:
                base_conditions.append("timestamp <= ?")
                base_params.append(end_time)

            def fetch_with_optional_source(source_filter: Optional[str] = None):
                conditions = list(base_conditions)
                params = list(base_params)
                if source_filter:
                    conditions.append("source = ?")
                    params.append(source_filter)

                where_clause = " AND ".join(conditions) if conditions else "1=1"
                query = f"""
                    SELECT
                        id, timestamp, source, event_id, event_type,
                        severity, message, hostname, username,
                        process_name, process_id
                    FROM logs
                    WHERE {where_clause}
                    ORDER BY timestamp
                """
                return db.fetch_all(query, tuple(params) if params else None)

            normalized_source = (log_source or "").strip().lower()

            if normalized_source == "latest":
                latest = db.fetch_one(
                    "SELECT source FROM logs ORDER BY ingestion_time DESC LIMIT 1"
                )
                latest_source = latest.get("source") if latest else None
                if latest_source:
                    return fetch_with_optional_source(str(latest_source))
                return fetch_with_optional_source()

            if normalized_source and normalized_source != "all":
                logs = fetch_with_optional_source(log_source)
                if logs:
                    return logs

                logger.warning(
                    "No logs found for source filter '%s'; falling back to all sources",
                    log_source,
                )
                return fetch_with_optional_source()

            return fetch_with_optional_source()

        except Exception as e:
            logger.error(f"Failed to load logs: {e}")
            raise DatabaseError(f"Log loading failed: {e}")

    def _resolve_algorithm(self, requested_algorithm: str, total_logs: int) -> str:
        supported = {"ensemble", "isolation_forest", "one_class_svm", "statistical"}
        normalized = requested_algorithm.strip().lower()

        if normalized in supported:
            return normalized

        if normalized in {"auto", "adaptive", "flexible"}:
            # Adaptive selection keeps inference stable across very small/large sets.
            if total_logs < 75:
                return "statistical"
            if total_logs > 100000:
                return "isolation_forest"
            return "ensemble"

        logger.warning("Unknown algorithm '%s'; falling back to ensemble", requested_algorithm)
        return "ensemble"

    def _create_session(
        self, session_id, algorithm, start_time, end_time, threshold, log_source
    ):
        import json

        session_data = {
            "session_id": session_id,
            "start_time": datetime.utcnow(),
            "status": "running",
            "logs_analyzed": 0,
            "anomalies_detected": 0,
            "parameters": json.dumps(
                {
                    "algorithm": algorithm,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "threshold": threshold,
                    "log_source": log_source,
                }
            ),
            "metadata": json.dumps({}),
        }
        db.insert_batch("analysis_sessions", [session_data])

    def _update_session(
        self,
        session_id,
        status=None,
        logs_analyzed=None,
        anomalies_detected=None,
        duration=None,
        error=None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        import json

        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
        if logs_analyzed is not None:
            updates.append("logs_analyzed = ?")
            params.append(logs_analyzed)
        if anomalies_detected is not None:
            updates.append("anomalies_detected = ?")
            params.append(anomalies_detected)
        if status == "completed":
            updates.append("end_time = ?")
            params.append(datetime.utcnow())
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
        elif error:
            updates.append("metadata = ?")
            params.append(json.dumps({"error": error}))

        params.append(session_id)
        query = f"UPDATE analysis_sessions SET {', '.join(updates)} WHERE session_id = ?"
        db.execute(query, tuple(params))

    def _calculate_severity(self, score: float) -> str:
        if score >= 0.90:
            return "CRITICAL"
        if score >= 0.75:
            return "HIGH"
        if score >= 0.55:
            return "MEDIUM"
        return "LOW"

    def _map_to_mitre(self, anomalies: List[Anomaly]):
        try:
            from services.mitre_service import mitre_service

            for anomaly in anomalies:
                log_query = "SELECT * FROM logs WHERE id = ?"
                log_data = db.fetch_one(log_query, (anomaly.log_id,))
                if not log_data:
                    continue

                techniques = mitre_service.map_log_to_techniques(log_data)
                if techniques:
                    technique = techniques[0]
                    anomaly.mitre_technique_id = technique["technique_id"]
                    anomaly.mitre_tactic = technique["tactic"]
                    db.execute(
                        "UPDATE anomalies SET mitre_technique_id = ?, mitre_tactic = ? WHERE log_id = ?",
                        (anomaly.mitre_technique_id, anomaly.mitre_tactic, anomaly.log_id),
                    )
        except Exception as e:
            logger.error(f"MITRE mapping failed: {e}")

    def get_session_results(self, session_id: str) -> Dict[str, Any]:
        try:
            session_query = "SELECT * FROM analysis_sessions WHERE session_id = ?"
            session = db.fetch_one(session_query, (session_id,))
            if not session:
                return {"error": "Session not found"}

            anomalies_query = """
                SELECT a.*, l.timestamp, l.source, l.event_type, l.message
                FROM anomalies a
                JOIN logs l ON a.log_id = l.id
                WHERE a.detected_at >= ?
                ORDER BY a.anomaly_score DESC
            """
            anomalies = db.fetch_all(anomalies_query, (session["start_time"],))

            return {
                "session": session,
                "anomalies": anomalies,
                "total_anomalies": len(anomalies),
            }
        except Exception as e:
            logger.error(f"Failed to get session results: {e}")
            return {"error": str(e)}


analysis_service = AnalysisService()
