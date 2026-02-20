"""
Statistical Anomaly Detector
Simple statistical methods for anomaly detection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import joblib
import numpy as np

from ai_engine.utils.performance import build_model_metadata, validate_model_metadata
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class StatisticalDetector:
    """Statistical anomaly detection using Z-score and IQR methods."""

    def __init__(self, method: str = "zscore", threshold: float = 3.0):
        self.method = method
        self.threshold = threshold

        self.means = None
        self.stds = None
        self.q1 = None
        self.q3 = None
        self.iqr = None

        self.is_fitted = False
        self.model_path = settings.MODELS_DIR / "statistical.pkl"

    def fit(self, X: np.ndarray) -> "StatisticalDetector":
        logger.info(f"Training Statistical Detector ({self.method}) on {X.shape[0]:,} samples")

        if self.method == "zscore":
            self.means = np.mean(X, axis=0)
            self.stds = np.std(X, axis=0)
            self.stds = np.where(self.stds == 0, 1e-10, self.stds)
        elif self.method == "iqr":
            self.q1 = np.percentile(X, 25, axis=0)
            self.q3 = np.percentile(X, 75, axis=0)
            self.iqr = self.q3 - self.q1
            self.iqr = np.where(self.iqr == 0, 1e-10, self.iqr)
        else:
            raise ValueError(f"Unknown method: {self.method}")

        self.is_fitted = True
        logger.info("Statistical Detector training complete")
        return self

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        if self.method == "zscore":
            z_scores = np.abs((X - self.means) / self.stds)
            max_z_scores = np.max(z_scores, axis=1)
            predictions = np.where(max_z_scores > self.threshold, -1, 1)
            anomaly_scores = self._normalize_scores(max_z_scores)
        elif self.method == "iqr":
            lower_bound = self.q1 - self.threshold * self.iqr
            upper_bound = self.q3 + self.threshold * self.iqr
            outliers = (X < lower_bound) | (X > upper_bound)
            outlier_counts = np.sum(outliers, axis=1)
            predictions = np.where(outlier_counts > 0, -1, 1)
            anomaly_scores = outlier_counts / X.shape[1]
        else:
            raise ValueError(f"Unknown method: {self.method}")

        return predictions, anomaly_scores

    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        self.fit(X)
        return self.predict(X)

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        min_score = scores.min()
        max_score = scores.max()
        if max_score - min_score == 0:
            return np.zeros_like(scores)
        return (scores - min_score) / (max_score - min_score)

    def _model_params(self):
        return {"method": self.method, "threshold": self.threshold}

    def save(self, path: Optional[Path] = None):
        if not self.is_fitted:
            logger.warning("Cannot save unfitted model")
            return

        save_path = path or self.model_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        params = {
            "method": self.method,
            "threshold": self.threshold,
            "means": self.means,
            "stds": self.stds,
            "q1": self.q1,
            "q3": self.q3,
            "iqr": self.iqr,
        }

        n_features = 0
        if self.means is not None:
            n_features = int(len(self.means))
        elif self.q1 is not None:
            n_features = int(len(self.q1))

        metadata = build_model_metadata(
            model_name="statistical",
            n_features=n_features,
            params=self._model_params(),
        )

        joblib.dump({"params": params, "metadata": metadata}, save_path)
        logger.info(f"Model saved to {save_path}")

    def load(self, path: Optional[Path] = None, n_features: Optional[int] = None) -> bool:
        load_path = path or self.model_path

        if not load_path.exists():
            logger.info(f"No saved model found at {load_path}")
            return False

        try:
            data = joblib.load(load_path)

            if isinstance(data, dict) and "params" in data:
                params = data["params"]
                metadata = data.get("metadata")
                if n_features is not None and metadata:
                    if not validate_model_metadata(
                        metadata,
                        model_name="statistical",
                        n_features=n_features,
                        params=self._model_params(),
                    ):
                        logger.info("Saved Statistical Detector metadata mismatch; retraining required")
                        return False
            else:
                params = data

            self.method = params["method"]
            self.threshold = params["threshold"]
            self.means = params["means"]
            self.stds = params["stds"]
            self.q1 = params["q1"]
            self.q3 = params["q3"]
            self.iqr = params["iqr"]

            self.is_fitted = True
            logger.info(f"Model loaded from {load_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
