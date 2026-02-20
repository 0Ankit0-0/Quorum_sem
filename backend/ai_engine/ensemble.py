"""
Ensemble Detector - UPGRADED
Hybrid AI combining multiple algorithms with realistic scoring.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple
import time

import numpy as np

from ai_engine.isolation_forest import IsolationForestDetector
from ai_engine.one_class_svm import OneClassSVMDetector
from ai_engine.statistical_detector import StatisticalDetector
from config.logging_config import get_logger

logger = get_logger(__name__)


SUSPICIOUS_KEYWORDS = {
    "failed password": 0.95,
    "authentication failed": 0.95,
    "invalid user": 0.95,
    "sasl login authentication failed": 0.95,
    "suspicious command": 0.98,
    "failed mfa": 0.97,
    "unauthorized": 0.93,
    "rootkit": 1.0,
    "malware": 1.0,
    "failed": 0.80,
    "error": 0.75,
    "disconnect": 0.72,
    "warning": 0.70,
    "denied": 0.78,
    "reject": 0.76,
    "blocked": 0.74,
    "sudo": 0.60,
    "root": 0.62,
    "admin": 0.58,
    "privilege": 0.65,
    "connect from unknown": 0.68,
    "accepted publickey": 0.35,
    "started session": 0.25,
    "cmd": 0.30,
    "container started": 0.28,
    "user login succeeded": 0.30,
}

EVENT_SEVERITY_RULES = {
    "kernel": 0.65,
    "auditd": 0.60,
    "sshd": 0.50,
    "sudo": 0.65,
    "cron": 0.20,
    "systemd": 0.20,
    "dockerd": 0.25,
    "nginx": 0.40,
    "postfix": 0.45,
    "app-worker": 0.50,
}


class EnsembleDetector:
    """Hybrid Ensemble Anomaly Detector."""

    def __init__(self):
        self.detectors = {
            "isolation_forest": IsolationForestDetector(),
            "one_class_svm": OneClassSVMDetector(),
            "statistical": StatisticalDetector(method="zscore"),
        }

        self.weights = {
            "isolation_forest": 0.35,
            "one_class_svm": 0.25,
            "statistical": 0.20,
            "keyword": 0.20,
        }

    def detect(
        self,
        X: np.ndarray,
        algorithm: str = "isolation_forest",
        contamination: float = 0.05,
        raw_logs: List[Dict[str, Any]] = None,
        force_retrain: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using a specific algorithm or the full ensemble.
        Returns (predictions, anomaly_scores).
        """
        logger.info(f"Running anomaly detection: {algorithm}")

        if algorithm == "ensemble":
            return self._hybrid_ensemble_detect(
                X,
                contamination,
                raw_logs,
                force_retrain=force_retrain,
            )

        if algorithm not in self.detectors:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        detector = self.detectors[algorithm]
        self._set_contamination(detector, contamination)

        loaded = False
        if not force_retrain:
            loaded = self._safe_load(detector, n_features=X.shape[1])

        start = time.perf_counter()
        if loaded:
            logger.info(f"Using pre-trained {algorithm} model")
            predictions, ml_scores = detector.predict(X)
        else:
            logger.info(f"Training new {algorithm} model")
            predictions, ml_scores = detector.fit_predict(X)
            detector.save()

        elapsed = time.perf_counter() - start
        metric_name = {
            "isolation_forest": "Isolation Forest time",
            "one_class_svm": "SVM time",
            "statistical": "Statistical Detector time",
        }.get(algorithm, f"{algorithm} time")
        logger.info(f"{metric_name}: {elapsed:.3f} sec")

        if raw_logs:
            keyword_scores = self._keyword_score(raw_logs)
            blended = 0.75 * ml_scores + 0.25 * keyword_scores
        else:
            blended = ml_scores

        final_scores = self._redistribute_scores(blended)
        threshold = np.percentile(final_scores, 85)
        predictions = np.where(final_scores >= threshold, -1, 1)
        return predictions, final_scores

    def _hybrid_ensemble_detect(
        self,
        X: np.ndarray,
        contamination: float,
        raw_logs: List[Dict[str, Any]] = None,
        force_retrain: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray]:
        logger.info("Running full hybrid ensemble detection")

        all_scores: Dict[str, np.ndarray] = {}
        timings: Dict[str, float] = {}

        def run_detector(name: str, detector):
            start = time.perf_counter()
            self._set_contamination(detector, contamination)

            loaded = False
            if not force_retrain:
                loaded = self._safe_load(detector, n_features=X.shape[1])

            if loaded:
                _, scores = detector.predict(X)
            else:
                _, scores = detector.fit_predict(X)
                detector.save()

            elapsed = time.perf_counter() - start
            return name, scores, elapsed

        with ThreadPoolExecutor(max_workers=min(len(self.detectors), 4)) as executor:
            futures = [
                executor.submit(run_detector, name, detector)
                for name, detector in self.detectors.items()
            ]
            for future in as_completed(futures):
                try:
                    name, scores, elapsed = future.result()
                    all_scores[name] = scores
                    timings[name] = elapsed
                    metric_name = {
                        "isolation_forest": "Isolation Forest time",
                        "one_class_svm": "SVM time",
                        "statistical": "Statistical Detector time",
                    }.get(name, f"{name} time")
                    logger.info(f"{metric_name}: {elapsed:.3f} sec")
                except Exception as e:
                    logger.error(f"Error running detector in ensemble: {e}")

        for name in self.detectors:
            if name not in all_scores:
                all_scores[name] = np.zeros(len(X), dtype=np.float64)

        keyword_start = time.perf_counter()
        keyword_scores = self._keyword_score(raw_logs) if raw_logs else np.zeros(len(X), dtype=np.float64)
        timings["keyword"] = time.perf_counter() - keyword_start
        all_scores["keyword"] = keyword_scores
        logger.info(f"Keyword Engine time: {timings['keyword']:.3f} sec")

        combined = np.zeros(len(X), dtype=np.float64)
        for name, weight in self.weights.items():
            combined += weight * all_scores.get(name, 0)

        final_scores = self._redistribute_scores(combined)
        threshold = np.percentile(final_scores, 85)
        predictions = np.where(final_scores >= threshold, -1, 1)

        logger.info(f"Ensemble complete: {int(np.sum(predictions == -1))} anomalies detected")
        return predictions, final_scores

    def _safe_load(self, detector, n_features: int) -> bool:
        try:
            return detector.load(n_features=n_features)
        except TypeError:
            return detector.load()
        except Exception as e:
            logger.warning(f"Model load failed, retraining detector: {e}")
            return False

    def _keyword_score(self, raw_logs: List[Dict[str, Any]]) -> np.ndarray:
        messages = np.asarray([(log.get("message") or "").lower() for log in raw_logs], dtype=str)
        sources = np.asarray([(log.get("source") or "").lower() for log in raw_logs], dtype=str)
        severities = np.asarray([(log.get("severity") or "INFO").upper() for log in raw_logs], dtype=str)

        severity_base_map = {
            "CRITICAL": 0.85,
            "HIGH": 0.70,
            "MEDIUM": 0.50,
            "ERROR": 0.70,
            "WARNING": 0.45,
            "WARN": 0.45,
            "INFO": 0.25,
            "DEBUG": 0.10,
        }

        scores = np.fromiter(
            (severity_base_map.get(sev, 0.25) for sev in severities),
            dtype=np.float64,
            count=len(raw_logs),
        )

        for keyword, weight in SUSPICIOUS_KEYWORDS.items():
            mask = np.char.find(messages, keyword) >= 0
            scores = np.where(mask, np.maximum(scores, weight), scores)

        for src, base_weight in EVENT_SEVERITY_RULES.items():
            mask = np.char.find(sources, src) >= 0
            adjusted = np.maximum(scores, base_weight) * 0.9
            scores = np.where(mask, adjusted, scores)

        return np.clip(scores, 0.0, 1.0)

    def _redistribute_scores(self, scores: np.ndarray) -> np.ndarray:
        if len(scores) == 0:
            return scores

        min_s, max_s = scores.min(), scores.max()
        if max_s - min_s < 1e-8:
            n = len(scores)
            return np.linspace(0.1, 0.9, n)[np.argsort(np.argsort(scores))]

        normalized = (scores - min_s) / (max_s - min_s)
        spread = 1.0 / (1.0 + np.exp(-6.0 * (normalized - 0.5)))
        return 0.1 + 0.89 * spread

    def _set_contamination(self, detector, contamination: float):
        try:
            if hasattr(detector, "contamination"):
                detector.contamination = contamination
                if hasattr(detector.model, "contamination"):
                    detector.model.contamination = contamination
            elif hasattr(detector, "nu"):
                detector.nu = max(contamination, 0.001)
                detector.model.nu = max(contamination, 0.001)
        except Exception:
            pass
