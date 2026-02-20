"""
Performance utilities for AI pipeline execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import gc
import hashlib
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np


MODEL_METADATA_VERSION = "1.0"
DEFAULT_RANDOM_SEED = 42


@dataclass
class TimerResult:
    name: str
    seconds: float


class StepTimer:
    """Simple timer to store named performance metrics."""

    def __init__(self):
        self._start_times: Dict[str, float] = {}
        self.metrics: Dict[str, float] = {}

    def start(self, name: str):
        self._start_times[name] = time.perf_counter()

    def stop(self, name: str) -> TimerResult:
        start = self._start_times.get(name, time.perf_counter())
        seconds = time.perf_counter() - start
        self.metrics[name] = seconds
        return TimerResult(name=name, seconds=seconds)


def maybe_collect_garbage():
    """Trigger GC at known safe points to lower peak memory pressure."""
    gc.collect()


def get_svm_max_samples(default: int = 10000) -> int:
    value = os.getenv("AI_SVM_MAX_SAMPLES")
    if not value:
        return default
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except ValueError:
        return default


def sample_training_data(
    X: np.ndarray,
    max_samples: int,
    random_state: int = DEFAULT_RANDOM_SEED,
    labels: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, Optional[np.ndarray], Dict[str, Any]]:
    """
    Sample rows without replacement if X is larger than max_samples.
    If labels are provided, attempt class-preserving stratified sampling.
    """
    n_samples = int(X.shape[0])
    if n_samples <= max_samples:
        return X, None, {
            "total_samples": n_samples,
            "used_samples": n_samples,
            "sampled": False
        }

    rng = np.random.default_rng(random_state)
    selected_indices: np.ndarray

    if labels is None or len(labels) != n_samples:
        selected_indices = rng.choice(n_samples, size=max_samples, replace=False)
    else:
        unique, counts = np.unique(labels, return_counts=True)
        fractions = counts / counts.sum()
        targets = np.floor(fractions * max_samples).astype(int)
        remainder = max_samples - int(targets.sum())
        if remainder > 0:
            order = np.argsort(-(fractions * max_samples - targets))
            targets[order[:remainder]] += 1

        parts = []
        for label, target in zip(unique, targets):
            class_indices = np.flatnonzero(labels == label)
            if target <= 0:
                continue
            take = min(len(class_indices), int(target))
            chosen = rng.choice(class_indices, size=take, replace=False)
            parts.append(chosen)

        selected_indices = np.concatenate(parts) if parts else np.array([], dtype=np.int64)
        if len(selected_indices) < max_samples:
            missing = max_samples - len(selected_indices)
            pool = np.setdiff1d(np.arange(n_samples), selected_indices, assume_unique=False)
            top_up = rng.choice(pool, size=missing, replace=False)
            selected_indices = np.concatenate([selected_indices, top_up])

    rng.shuffle(selected_indices)
    return X[selected_indices], selected_indices, {
        "total_samples": n_samples,
        "used_samples": int(len(selected_indices)),
        "sampled": True
    }


def build_model_metadata(
    model_name: str,
    n_features: int,
    params: Dict[str, Any],
    extras: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "model_name": model_name,
        "metadata_version": MODEL_METADATA_VERSION,
        "n_features": int(n_features),
        "params": params,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    if extras:
        metadata.update(extras)
    checksum_src = json.dumps(metadata, sort_keys=True, default=str).encode("utf-8")
    metadata["checksum"] = hashlib.sha256(checksum_src).hexdigest()
    return metadata


def validate_model_metadata(
    metadata: Dict[str, Any],
    model_name: str,
    n_features: int,
    params: Dict[str, Any]
) -> bool:
    if not metadata:
        return False
    checksum = metadata.get("checksum")
    if not checksum:
        return False

    meta_copy = dict(metadata)
    meta_copy.pop("checksum", None)
    checksum_src = json.dumps(meta_copy, sort_keys=True, default=str).encode("utf-8")
    if hashlib.sha256(checksum_src).hexdigest() != checksum:
        return False

    if metadata.get("model_name") != model_name:
        return False
    if int(metadata.get("n_features", -1)) != int(n_features):
        return False
    return metadata.get("params") == params


def detect_gpu_backend() -> Dict[str, Any]:
    """
    Detection priority:
    1) RAPIDS cuML
    2) PyTorch CUDA
    3) TensorFlow GPU
    """
    result = {
        "gpu_available": False,
        "backend": "cpu",
        "supports_isolation_forest": False,
        "notes": ""
    }

    try:
        import cuml  # type: ignore
        _ = cuml.__version__
        result.update({
            "gpu_available": True,
            "backend": "rapids_cuml",
            "supports_isolation_forest": True,
            "notes": "cuML detected"
        })
        return result
    except Exception:
        pass

    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            result.update({
                "gpu_available": True,
                "backend": "torch_cuda",
                "supports_isolation_forest": False,
                "notes": "PyTorch CUDA detected"
            })
            return result
    except Exception:
        pass

    try:
        import tensorflow as tf  # type: ignore
        if tf.config.list_physical_devices("GPU"):
            result.update({
                "gpu_available": True,
                "backend": "tensorflow_gpu",
                "supports_isolation_forest": False,
                "notes": "TensorFlow GPU detected"
            })
            return result
    except Exception:
        pass

    result["notes"] = "No GPU backend detected"
    return result
