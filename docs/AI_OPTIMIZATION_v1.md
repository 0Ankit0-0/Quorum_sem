# AI Optimization v1

## 1. Overview of Optimization Goals
This upgrade improves backend AI pipeline throughput for large log batches while preserving compatibility with Quorum v1.1.0 components (real-time monitor, hub aggregation, device scanning, API/CLI flows).

Primary goals:
- Reduce end-to-end analysis latency for ~50k logs.
- Remove SVM full-dataset bottleneck.
- Parallelize ensemble detectors.
- Keep safe CPU fallback with optional GPU detection.
- Avoid unnecessary retraining through validated model persistence.
- Improve memory safety for large datasets.

## 2. Problems Identified
- One-Class SVM was training on full input, creating O(n^2) runtime pressure.
- Ensemble detection was sequential, underutilizing multi-core systems.
- Feature extraction performed Python-heavy per-row/per-field loops.
- No centralized GPU detection/fallback messaging.
- Model loading lacked robust metadata compatibility validation.
- Large analysis runs risked higher memory pressure from non-chunked processing.

## 3. Solutions Implemented
### Smart SVM Sampling
- Added configurable cap: `SVM_MAX_SAMPLES = 10000`.
- Added random sampling without replacement for oversized datasets.
- Added stratified-preserving sampling path when labels are available.
- Added explicit training log line:
  - `Training One-Class SVM on 10,000 / 53,531 samples (sampled)`

### Parallel Ensemble Execution
- Implemented parallel detector execution in `EnsembleDetector` using `ThreadPoolExecutor` for:
  - Isolation Forest
  - One-Class SVM
  - Statistical Detector
  - Keyword Engine timing tracked in same pipeline
- Kept deterministic score fusion and redistribution behavior.

### Vectorized Feature Extraction
- Reworked feature extraction to NumPy vectorized batch operations.
- Precompiled regex for IP/port extraction.
- Removed repeated per-record regex compilation and heavy loop overhead.

### GPU Detection with Safe Fallback
- Added backend detection priority:
  1. RAPIDS cuML
  2. PyTorch CUDA
  3. TensorFlow GPU
  4. CPU fallback
- Isolation Forest now attempts GPU equivalent (cuML) when available.
- If GPU is detected but unsupported for active detector stack, logs:
  - `GPU detected but compatible libraries not installed - using CPU`
- No hard dependency introduced; pipeline remains non-crashing on CPU-only systems.

### Model Persistence Optimization
- Added metadata + checksum validation utilities.
- Added compatibility checks (`model_name`, `n_features`, params, checksum).
- Added lazy load/reuse path before training.
- Added `force_retrain` control path for explicit retraining.

### Memory Safety
- Added large-dataset chunked processing path in analysis service (`>100k` logs).
- Added explicit GC safe-points after chunk processing/training.
- Reduced intermediate duplication via vectorized matrix generation.

### Performance Logging
- Added metrics lines for:
  - `Feature extraction time: X sec`
  - `Isolation Forest time: X sec`
  - `SVM time: X sec`
  - `Statistical Detector time: X sec`
  - `Keyword Engine time: X sec`
  - `Total pipeline time: X sec`

## 4. Performance Benchmarks (Before vs After)
### Baseline (legacy behavior)
- Typical full pipeline runtime for ~50k logs: **30-120 sec**
- Dominant bottleneck: One-Class SVM full training + synchronous ensemble execution.

### Current optimized run (local synthetic benchmark, 50,000 logs)
- Feature extraction: **0.711 sec**
- Ensemble detection: **8.280 sec**
- Total pipeline: **8.991 sec**

### Expected operational range
- ~50k logs: **5-15 sec** total (hardware and data-shape dependent)

## 5. GPU Support Explanation
- GPU presence is detected dynamically at runtime.
- Isolation Forest uses GPU path only when cuML is importable and usable.
- Other detectors remain CPU (safe default) unless future GPU-native equivalents are added.
- Missing GPU stack never crashes analysis; CPU path is automatic.

## 6. Configuration Parameters
- `AI_SVM_MAX_SAMPLES` (default: `10000`)
- `AI_LARGE_DATASET_THRESHOLD` (default: `100000`)
- Existing knobs remain supported:
  - `AI_CONTAMINATION`
  - `AI_N_JOBS`

Environment override also supported for SVM cap:
- `AI_SVM_MAX_SAMPLES` env var

## 7. Future Improvement Suggestions
- Add process-based parallel option for CPU-bound detectors on very high core-count hosts.
- Add incremental/online model update mode for streaming-assisted retraining.
- Add persistent benchmark telemetry table in DB for regression tracking.
- Add GPU-native alternatives for additional detectors beyond Isolation Forest.
- Add optional feature caching keyed by `(log_id, schema_version)`.

## Modified File Structure
Modified:
- `backend/ai_engine/ensemble.py`
- `backend/ai_engine/feature_extractor.py`
- `backend/ai_engine/isolation_forest.py`
- `backend/ai_engine/one_class_svm.py`
- `backend/ai_engine/statistical_detector.py`
- `backend/services/analysis_service.py`
- `backend/config/settings.py`

Added:
- `backend/ai_engine/utils/performance.py`
- `backend/ai_engine/utils/__init__.py`
- `docs/AI_OPTIMIZATION_v1.md`
