# infrastructure/ml

Responsibility: optional-extra estimator adapters and the family-id registry.

## Conventions specific to this module

- Importing `infrastructure.ml.registry` must not import sklearn, xgboost,
  lightgbm, catboost, or torch. Library imports happen inside lazy factories / `fit()`,
  and `ImportError` is raised as `PredictiveExtraError` (never as the outer type).
- `research/predictive/` must not import this package. Application may resolve
  families through the registry.
- Family ids: `sklearn.ridge`, `sklearn.elastic_net`, `sklearn.logistic`,
  `xgboost.regressor`, `xgboost.classifier`, `lightgbm.regressor`,
  `lightgbm.classifier`, `catboost.regressor`, `catboost.classifier`,
  `torch.feedforward.regressor`, `torch.feedforward.classifier`,
  `torch.lstm.regressor`, `torch.lstm.classifier`,
  `torch.gru.regressor`, `torch.gru.classifier`.
  Unknown ids are `PredictiveSpecError` even if extras are installed.
  Classifier families are binary only.
- Sklearn adapters pin `n_jobs=1` when accepted, and `random_state` from
  `EstimatorSpec.seed`. `sklearn.logistic` is binary only.
- XGBoost adapters pin `n_jobs=1` / `nthread=1`, `tree_method="hist"`,
  `device="cpu"`, and `random_state` from `EstimatorSpec.seed`. GPU options
  are `PredictiveSpecError`.
- LightGBM adapters pin `n_jobs=1` / `num_threads=1`, `deterministic=True`,
  `force_row_wise=True`, `boosting_type="gbdt"`. GPU `device` / `device_type`
  and non-gbdt boosters are `PredictiveSpecError`.
- CatBoost adapters pin `thread_count=1`, `task_type="CPU"`,
  `allow_writing_files=False`. GPU `task_type` and bootstrap types other than
  Bernoulli / Bayesian / MVS are `PredictiveSpecError`.
- Tree families reuse fold-local sklearn preprocessing, so resolving them
  requires extras `ml` and `ml-trees`.
- Torch feedforward families live in `torch/` and require extra `dl` only
  (numpy `PreprocessingSpec`, not extra `ml`). They always inner-split TRAIN
  for early stopping, pin `num_threads=1`, reject GPU/CUDA/MPS, and reject a
  `SequenceWindowSpec`. Sequence families (`torch.lstm.*`, `torch.gru.*`)
  require a `SequenceWindowSpec`, rank-3 windows, and 2d TRAIN `scaler_features`
  in `sample_metadata` — the scaler is never fitted on windowed tensors.
  Application builds those windows before `fit()` / `predict()`; adapters do
  not import the domain window builder.
  `native_feature_importance()` is `None`.
- Preprocessing (`IMPUTE_MEDIAN` then `STANDARDIZE` by default) is fitted on
  the feature matrix passed to `fit()` only. Do not pass PURGED / EMBARGOED
  rows; if `sample_metadata` carries fold roles, non-TRAIN roles are rejected.
- `FittedNumpyPreprocessor` / `fit_numpy_preprocessor` (and their matrix/window
  coercion helpers) moved to `research/predictive/promotion/preprocessing.py`
  in Sprint 049 (Q8 / D-S049-08) — they are the promoted-artifact evaluator's
  preprocessing half and live in the domain layer now. The torch adapter
  (`torch/adapter.py`, `torch/sequence.py`) imports them downward from there;
  do not re-add a copy under `infrastructure/ml/torch/`.
- Application constructs estimators only through `resolve_estimator(spec,
  preprocessing=...)`. Do not import `infrastructure.ml.sklearn`,
  `infrastructure.ml.trees`, or `infrastructure.ml.torch` from application.
  Opaque blobs go through `dump_fitted_estimator` on the registry.

## Gotchas

- Architecture tests skip ML-library imports only under `infrastructure/ml/`.
  Do not import sklearn or xgboost from application or domain.
- Module-level files under `sklearn/` and `trees/` must not import those
  libraries. Keep those imports inside factory / `fit()`. The same rule
  applies to `torch/` — no module-level `import torch`.
