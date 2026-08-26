# infrastructure/ml

Responsibility: optional-extra estimator adapters and the family-id registry.

## Conventions specific to this module

- Importing `infrastructure.ml.registry` must not import sklearn. Sklearn
  imports happen inside lazy factories / `fit()`, and `ImportError` is raised
  as `PredictiveExtraError` (never as the outer type).
- `research/predictive/` must not import this package. Application may resolve
  families through the registry.
- Family ids this sprint: `sklearn.ridge`, `sklearn.elastic_net`,
  `sklearn.logistic`. Unknown ids are `PredictiveSpecError` even if extra `ml`
  is installed.
- Adapters pin `n_jobs=1` when the sklearn estimator accepts it, and set
  `random_state` from `EstimatorSpec.seed` when the estimator is seedable.
- `sklearn.logistic` is binary only. Ternary / multinomial targets (or an
  explicit `multi_class="multinomial"` hyperparameter) raise
  `PredictiveSpecError`.
- Preprocessing (`IMPUTE_MEDIAN` then `STANDARDIZE` by default) is fitted on
  the feature matrix passed to `fit()` only. Do not pass PURGED / EMBARGOED
  rows; if `sample_metadata` carries fold roles, non-TRAIN roles are rejected.

## Gotchas

- Architecture tests skip sklearn imports only under `infrastructure/ml/`.
  Do not import sklearn from application or domain.
- Module-level files under `sklearn/` must not `import sklearn`. Keep those
  imports inside factory / `fit()` / `fit_sklearn_preprocessor`.
