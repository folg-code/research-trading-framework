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

## Gotchas

- Architecture tests skip sklearn imports only under `infrastructure/ml/`.
  Do not import sklearn from application or domain.
- Stub factories exist so the registry can resolve family ids before Wave 2
  ships `describe()` / `fit()` adapters. Do not grow stubs into full estimators
  here without the Wave 2 tasks.
