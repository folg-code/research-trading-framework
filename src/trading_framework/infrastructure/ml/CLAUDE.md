# infrastructure/ml

Responsibility: optional-extra estimator adapters and the family-id registry.

## Conventions specific to this module

- Importing `infrastructure.ml.registry` must not import sklearn, xgboost,
  lightgbm, or catboost. Library imports happen inside lazy factories / `fit()`,
  and `ImportError` is raised as `PredictiveExtraError` (never as the outer type).
- `research/predictive/` must not import this package. Application may resolve
  families through the registry.
- Family ids: `sklearn.ridge`, `sklearn.elastic_net`, `sklearn.logistic`,
  `xgboost.regressor`, `xgboost.classifier`, `lightgbm.regressor`,
  `lightgbm.classifier`, `catboost.regressor`, `catboost.classifier`.
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
- Preprocessing (`IMPUTE_MEDIAN` then `STANDARDIZE` by default) is fitted on
  the feature matrix passed to `fit()` only. Do not pass PURGED / EMBARGOED
  rows; if `sample_metadata` carries fold roles, non-TRAIN roles are rejected.
- Application constructs estimators only through `resolve_estimator(spec,
  preprocessing=...)`. Do not import `infrastructure.ml.sklearn` or
  `infrastructure.ml.trees` from application. Opaque blobs go through
  `dump_fitted_estimator` on the registry.

## Gotchas

- Architecture tests skip ML-library imports only under `infrastructure/ml/`.
  Do not import sklearn or xgboost from application or domain.
- Module-level files under `sklearn/` and `trees/` must not import those
  libraries. Keep those imports inside factory / `fit()`.
