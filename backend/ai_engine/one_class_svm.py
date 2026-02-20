"""
One-Class SVM Anomaly Detector
Support Vector Machine for novelty detection with smart sampling.
"""
from __future__ import annotations

from typing import Optional, Tuple
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM as SKOneClassSVM

from ai_engine.utils.performance import (
    build_model_metadata,
    get_svm_max_samples,
    maybe_collect_garbage,
    sample_training_data,
    validate_model_metadata,
)
from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


SVM_MAX_SAMPLES = get_svm_max_samples(getattr(settings, "AI_SVM_MAX_SAMPLES", 10000))


class OneClassSVMDetector:
    """One-Class SVM for anomaly detection."""

    def __init__(
        self,
        kernel: str = "rbf",
        nu: float = 0.01,
        gamma: str = "auto",
        random_state: int = 42,
        max_samples: int = SVM_MAX_SAMPLES,
    ):
        self.kernel = kernel
        self.nu = nu
        self.gamma = gamma
        self.random_state = random_state
        self.max_samples = max_samples

        self.model = SKOneClassSVM(
            kernel=kernel,
            nu=nu,
            gamma=gamma,
        )

        self.scaler = StandardScaler()
        self.is_fitted = False
        self.model_path = settings.MODELS_DIR / "one_class_svm.pkl"

    def fit(self, X: np.ndarray, labels: Optional[np.ndarray] = None) -> "OneClassSVMDetector":
        """Train the model with optional capped sampling."""
        sampled_X, _, stats = sample_training_data(
            X,
            max_samples=self.max_samples,
            random_state=self.random_state,
            labels=labels,
        )

        if stats["sampled"]:
            logger.info(
                "Training One-Class SVM on %s / %s samples (sampled)",
                f"{stats['used_samples']:,}",
                f"{stats['total_samples']:,}",
            )
        else:
            logger.info(f"Training One-Class SVM on {sampled_X.shape[0]:,} samples")

        X_scaled = self.scaler.fit_transform(sampled_X)
        self.model.fit(X_scaled)
        self.is_fitted = True

        maybe_collect_garbage()
        logger.info("One-Class SVM training complete")
        return self

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        raw_scores = self.model.decision_function(X_scaled)
        anomaly_scores = self._normalize_scores(raw_scores)
        return predictions, anomaly_scores

    def fit_predict(self, X: np.ndarray, labels: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        self.fit(X, labels=labels)
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
            "kernel": self.kernel,
            "nu": self.nu,
            "gamma": self.gamma,
            "max_samples": self.max_samples,
        }

    def save(self, path: Optional[Path] = None):
        if not self.is_fitted:
            logger.warning("Cannot save unfitted model")
            return

        save_path = path or self.model_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = build_model_metadata(
            model_name="one_class_svm",
            n_features=int(self.model.n_features_in_),
            params=self._model_params(),
        )

        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "metadata": metadata,
            },
            save_path,
        )
        logger.info(f"Model saved to {save_path}")

    def load(self, path: Optional[Path] = None, n_features: Optional[int] = None) -> bool:
        load_path = path or self.model_path

        if not load_path.exists():
            logger.info(f"No saved model found at {load_path}")
            return False

        try:
            data = joblib.load(load_path)

            # Backward compatibility with pre-metadata model files.
            if isinstance(data, dict) and "model" in data and "scaler" in data:
                metadata = data.get("metadata")
                if n_features is not None and metadata:
                    if not validate_model_metadata(
                        metadata,
                        model_name="one_class_svm",
                        n_features=n_features,
                        params=self._model_params(),
                    ):
                        logger.info("Saved One-Class SVM metadata mismatch; retraining required")
                        return False

                self.model = data["model"]
                self.scaler = data["scaler"]
                self.is_fitted = True
                logger.info(f"Model loaded from {load_path}")
                return True

            logger.info("Saved One-Class SVM model format not recognized; retraining required")
            return False

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
