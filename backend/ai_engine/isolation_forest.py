"""
Isolation Forest Anomaly Detector
Fast tree-based anomaly detection with optional GPU backend.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest as SKIsolationForest

from ai_engine.utils.performance import (
    build_model_metadata,
    detect_gpu_backend,
    maybe_collect_garbage,
    validate_model_metadata,
)
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class IsolationForestDetector:
    """Isolation Forest anomaly detection."""

    def __init__(
        self,
        contamination: float = 0.01,
        n_estimators: int = 100,
        max_samples: int = 256,
        random_state: int = 42,
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state

        self._gpu_info = detect_gpu_backend()
        self.backend = "cpu"
        self.model = self._build_model()

        self.is_fitted = False
        self.model_path = settings.MODELS_DIR / "isolation_forest.pkl"

    def _build_model(self):
        if self._gpu_info.get("backend") == "rapids_cuml":
            try:
                from cuml.ensemble import IsolationForest as CUIsolationForest  # type: ignore

                self.backend = "gpu"
                logger.info("Using RAPIDS cuML IsolationForest (GPU)")
                return CUIsolationForest(
                    contamination=self.contamination,
                    n_estimators=self.n_estimators,
                    max_samples=self.max_samples,
                    random_state=self.random_state,
                )
            except Exception:
                logger.info("GPU detected but compatible libraries not installed - using CPU")

        self.backend = "cpu"
        return SKIsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            random_state=self.random_state,
            n_jobs=-1,
        )

    def fit(self, X: np.ndarray) -> "IsolationForestDetector":
        logger.info(f"Training Isolation Forest on {X.shape[0]:,} samples")
        self.model.fit(X)
        self.is_fitted = True
        maybe_collect_garbage()
        logger.info("Isolation Forest training complete")
        return self

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        predictions = self.model.predict(X)
        try:
            raw_scores = self.model.decision_function(X)
        except Exception:
            raw_scores = self.model.score_samples(X)

        anomaly_scores = self._normalize_scores(np.asarray(raw_scores))
        predictions = np.asarray(predictions)
        predictions = np.where(predictions <= 0, -1, 1)
        return predictions, anomaly_scores

    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        self.fit(X)
        return self.predict(X)

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        inverted = -scores
        min_score = inverted.min()
        max_score = inverted.max()
        if max_score - min_score == 0:
            return np.zeros_like(inverted)
        return (inverted - min_score) / (max_score - min_score)

    def _model_params(self):
        return {
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "max_samples": self.max_samples,
            "random_state": self.random_state,
            "backend": self.backend,
        }

    def save(self, path: Optional[Path] = None):
        if not self.is_fitted:
            logger.warning("Cannot save unfitted model")
            return

        save_path = path or self.model_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        n_features = int(getattr(self.model, "n_features_in_", 0) or 0)
        metadata = build_model_metadata(
            model_name="isolation_forest",
            n_features=n_features,
            params=self._model_params(),
        )

        joblib.dump({"model": self.model, "metadata": metadata}, save_path)
        logger.info(f"Model saved to {save_path}")

    def load(self, path: Optional[Path] = None, n_features: Optional[int] = None) -> bool:
        load_path = path or self.model_path

        if not load_path.exists():
            logger.info(f"No saved model found at {load_path}")
            return False

        try:
            data = joblib.load(load_path)

            if isinstance(data, dict) and "model" in data:
                metadata = data.get("metadata")
                if n_features is not None and metadata:
                    if not validate_model_metadata(
                        metadata,
                        model_name="isolation_forest",
                        n_features=n_features,
                        params=self._model_params(),
                    ):
                        logger.info("Saved Isolation Forest metadata mismatch; retraining required")
                        return False

                self.model = data["model"]
                self.is_fitted = True
                logger.info(f"Model loaded from {load_path}")
                return True

            # Backward compatibility for plain persisted estimator.
            self.model = data
            self.is_fitted = True
            logger.info(f"Model loaded from {load_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def get_feature_importance(self) -> np.ndarray:
        if not self.is_fitted:
            return np.array([])

        n_features = int(getattr(self.model, "n_features_in_", 0) or 0)
        if n_features <= 0:
            return np.array([])
        return np.ones(n_features) / n_features
