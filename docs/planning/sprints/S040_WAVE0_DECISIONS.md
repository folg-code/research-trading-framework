# Sprint 040 — Wave 0 Decisions

Binding decisions for Baseline Regression and Classification (Phase 10A). Date: 2026-08-26.
Inherited locks from S039 / ADR-0023 (2026-08-26) are restated, not reopened.
New S040 locks below are Proposed until the maintainer checks off the Wave 0
checklist.

Basis: `SPRINT_040.md`, `ROADMAP.md` §13A, ADR-0023 (ACCEPTED),
`S039_WAVE0_DECISIONS.md`. Architecture source:
`docs/adr/ADR-0023-predictive-research-boundary.md`. No new ADR — ADR-0024
remains reserved for IDEA-014.

---

## Inherited locks (do not reopen)

Human-locked in S039 / ADR-0023 (2026-08-26):

```text
Extra `ml` = scikit-learn; optional; NOT in default `dev` group; standard CI extra-free
Dedicated CI job installs extras `ml` (policy locked; job itself is S040 work)
Later extras `ml-trees` (S042) and `dl` (S043) — do not add them now
research/predictive/ imports polars / numpy / framework only — no sklearn
Adapter lives in infrastructure/ml/sklearn/
Durable facts = predictions + metrics; fitted blobs opaque, version-tagged, not portable
Reproduce by re-fitting from the manifest — never by deserializing a blob
CI / acceptance datasets: synthetic fixtures only — no NQ as S040 acceptance
Preprocessing fitted per fold on TRAIN only; PURGED / EMBARGOED never reach fit()
No signals / strategy / signal_model / simulation / IDEA-014 promotion
Models do not trade
```

---

## D-S040-01 — Problem statement

Sprint 039 produced a fingerprinted learning problem. Nobody has learned from it
yet. This sprint introduces the **estimator seam** and the **measurement
vocabulary**, using models simple enough that a surprising result means a bug
rather than a discovery.

Linear and logistic baselines are the control group: every later tree or network
is judged against them. A gradient-boosted model that cannot beat ridge on the
same folds is a statement about the features, not the estimator.

This remains a **research methodology**, not a trading capability. Models do not
trade.

---

## D-S040-02 — Sprint branch and PR base

```text
Integration branch: sprint/predictive-baselines
Working branches:   feat/ | fix/ | docs/ | test/  (not nested under sprint/)
PR base:            sprint/predictive-baselines  (never main until sprint integration)
```

Working-branch PRs squash-merge into the sprint branch. When S040 is complete,
one integration PR goes `sprint/predictive-baselines` → `main`. Do not open
working PRs against `main`.

---

## D-S040-03 — Sprint slice

**This sprint ships exactly:** estimator protocol + spec, fold-local
preprocessing, optional extra `ml` (scikit-learn), sklearn adapter for ridge /
elastic net / logistic, naive reference baselines, per-fold run orchestration,
statistical + finance-aware metrics (per fold and pooled), run envelope +
identity, thin CLIs, determinism and known-signal tests.

| Order | Slice | Why |
|-------|--------|-----|
| 1 | Wave 0 | Binding S040 locks before extras or adapters |
| 2 | Protocol + extra | Domain seam + extra-free default install |
| 3 | sklearn adapter | Three baseline families behind the protocol |
| 4 | Run orchestration | Per-fold fit / predict / persist |
| 5 | Metrics + references | Honest measurement vocabulary |
| 6 | CLI | One-command run and analyze |
| 7 | Determinism + known-signal | Prove reproducibility and catch leakage |
| 8 | Docs | Close the sprint |

**Not this sprint:** trees, networks, hyperparameter search, HTML reports,
feature selection, class rebalancing, sample weighting, ternary classifiers,
NQ as acceptance, IDEA-014.

---

## D-S040-04 — Methodology boundary

Restate of ADR-0023 §1 / D-S039-04. **Locked:**

```text
no signals
no strategy/
no signal_model/
no simulation
no promotion to Market Analysis components (IDEA-014 → S044 gate / ADR-0024)
```

A trained model is never a tradable signal inside Phase 10.

---

## D-S040-05 — Package layout

Locked from `SPRINT_040.md` §4, plus S039 packages that already exist:

```text
research/predictive/estimators.py        PredictiveEstimator protocol, EstimatorSpec, TaskType
research/predictive/preprocessing.py     preprocessing spec (fit-on-train contract)
research/predictive/metrics.py           metric computation over predictions (library-free)
research/predictive/errors.py            PredictiveSpecError + PredictiveExtraError (extend)
research/datasets/predictive_run.py      PredictiveRunEnvelope + repository + run identity
infrastructure/ml/registry.py            family-id registry (see D-S040-07)
infrastructure/ml/sklearn/               adapter: spec -> sklearn estimator -> protocol
application/predictive_research/         run + analyze orchestration (existing package)
scripts/predictive_research/             run_predictive_research.py, analyze_predictive_run.py
```

S039 files (`spec.py`, `features.py`, `labels.py`, `matrix.py`, `splitting.py`,
`datasets/predictive.py`, `build_predictive_dataset.py`) stay. Do not move them.

**Locked:** `research/predictive/` still imports **polars**, **numpy**, and
framework contracts only. Metrics in domain use numpy/polars — not sklearn
metric helpers — so extra-free unit tests can cover metric formulae.

---

## D-S040-06 — Protocol, EstimatorSpec, TaskType

```text
PredictiveEstimator
  fit(features, target, sample_metadata) -> FittedPredictiveEstimator
FittedPredictiveEstimator
  predict(features) -> array
  predict_proba(features) -> array | None      (classification only)
  describe() -> EstimatorDescription           (library, version, resolved params)
```

`EstimatorSpec` is a frozen value object hashed into run identity:

```text
family            str          (D-S040-15)
hyperparameters   mapping      canonical, JSON-stable
seed              int          required — unseeded specs are invalid
task_type         TaskType     REGRESSION | CLASSIFICATION
```

`TaskType.CLASSIFICATION` in S040 means **binary** logistic. S039 `LabelKind.TERNARY`
datasets are rejected at run start this sprint (multinomial / ternary estimators
are a later increment, not a silent sklearn `multi_class` default).

`describe()` output is persisted. An unrecorded hyperparameter breaks
reproducibility.

Protocol types live in `research/predictive/estimators.py`. They are structural
(`typing.Protocol`). They do **not** subclass sklearn types.

---

## D-S040-07 — Family registry location

**Locked:** the family registry lives in `infrastructure/ml/registry.py`, not
in domain and not in application.

Selection is by **family identifier string** through the registry. **Not**
`isinstance` on sklearn classes.

Why infrastructure, from existing patterns:

- ADR-0023 already places adapters in `infrastructure/ml/<lib>/`.
- `tests/unit/test_architecture_boundaries.py` forbids sklearn imports in
  `research/predictive/`, in **all** domain modules except `infrastructure/ml`,
  and in `application/predictive_research` + datasets + scripts (Wave 4 paths).
- Market Analysis can own `ComponentRegistry` in domain because NumPy kernels
  are always installed. sklearn is an **optional extra**, so a domain-owned
  factory map would either import the adapter (wrong dependency direction) or
  become an empty shell filled from infrastructure.
- Application is the composition root but must remain importable without the
  extra (T022). A registry that imported sklearn factories at application
  import time would break the extra-free install.

Shape:

```text
infrastructure/ml/registry.py     family_id -> extra name + lazy factory
infrastructure/ml/sklearn/        registers sklearn.* families (lazy import)
application/predictive_research   resolves family via the registry; never imports sklearn
research/predictive/              protocol only; never imports infrastructure.ml
```

Importing `infrastructure.ml.registry` must not import sklearn. Sklearn family
registration uses factories that import sklearn **inside** `fit()` / construction,
not at module import.

Later extras (`ml-trees`, `dl`) register additional families on the same
registry without changing domain import graphs.

---

## D-S040-08 — Missing-extra error

**Locked:** requesting a family whose extra is not installed raises an explicit
framework error naming the extra, never a raw `ImportError`.

```text
Type:    PredictiveExtraError(ValidationError)   in research/predictive/errors.py
Message: must name extra `ml` (and the requested family id)
Cause:   ImportError may be chained (__cause__) but must not be the raised type
```

Domain owns the error type so application and tests can catch it without
importing sklearn. The registry / adapter raises it.

---

## D-S040-09 — Extra `ml` in pyproject.toml

Policy inherited (D-S039-06 / ADR-0023 §3). S040 implements it.

**Locked:**

```text
[project.optional-dependencies]
ml = ["scikit-learn>=1.6,<2.0"]
```

```text
requires-python is >=3.12; sklearn 1.6+ supports 3.12 and NumPy 2
Upper bound <2.0 avoids a major-version API break
Do not add scikit-learn to [dependency-groups] dev
Do not add extras `ml-trees` or `dl`
joblib arrives transitively with sklearn — do not add a separate extra for it
```

Exact pin is `uv lock` work in PR 2 (T005). The extra is installed with
`uv sync --locked --extra ml --dev`. Default `uv sync --locked --dev` stays
extra-free. Fingerprint records the resolved sklearn version, so a lockfile
bump is a different experiment.

---

## D-S040-10 — Dedicated CI job

**Locked:** add one job to the **existing** `.github/workflows/ci.yml`. Do not
create a second workflow file.

```text
Job id:     ml
Name:       ML extra tests
Install:    uv sync --locked --extra ml --dev
Run:        uv run pytest -m ml -q
```

Standard jobs **must** remain extra-free:

```text
quality / unit / integration / build / dashboard
  continue to use: uv sync --locked --dev   (no --extra ml)
```

The unit job additionally filters markers once `ml` is registered:

```text
uv run pytest tests/unit -m "not ml" --cov=...
```

Do **not** put `-m "not ml"` in global `addopts` — maintainers who installed
the extra should still be able to run the full suite locally.

The `ml` job lands in the same PR that first has a `@pytest.mark.ml` test
(PR 2 may add a smoke `import sklearn` test so the job is never empty; pytest
exit code 5 on zero collected tests is not acceptable). Until that PR, do not
add the job.

---

## D-S040-11 — pytest marker

**Locked:** marker name is `ml` (matches the extra). Register it in
`pyproject.toml` `[tool.pytest.ini_options] markers` because `--strict-markers`
is already on.

```text
Marked:     known-signal, adapter, determinism, and any test that imports sklearn
Unmarked:   domain protocol / spec / preprocessing-contract tests that do not import sklearn
```

ML test modules also call `pytest.importorskip("sklearn")` at module level so
local `uv run pytest tests/unit` without the extra **skips** instead of failing
at collection. The dedicated CI job has sklearn installed, so skip does not
fire there.

---

## D-S040-12 — mypy, lazy import, architecture-test honesty

Default quality job runs `uv run mypy` **without** sklearn installed.

**Locked:**

```text
[[tool.mypy.overrides]]
module = ["sklearn", "sklearn.*", "joblib", "joblib.*"]
ignore_missing_imports = true
```

The sklearn adapter uses a **lazy import**. Module-level `infrastructure/ml/sklearn/`
code must not import sklearn at import time. The first sklearn import happens
inside the factory / `fit()` path; failure becomes `PredictiveExtraError`
(D-S040-08).

Architecture tests are AST-based and walk **every** `Import` / `ImportFrom`,
including `if TYPE_CHECKING:` blocks.

**Locked:** `research/predictive/` never imports sklearn — not at runtime, not
under `TYPE_CHECKING`. Do not weaken
`test_predictive_research_does_not_import_ml_libraries`,
`test_domain_modules_do_not_import_ml_libraries`, or the Wave 4 path tests.
Do not add a TYPE_CHECKING exception to the AST walker. The protocol is
structural; it does not subclass sklearn.

`infrastructure/ml/` remains the only skip-root for sklearn imports
(`test_domain_modules_do_not_import_ml_libraries`). Application and scripts
may import `infrastructure.ml.registry` but must not import `sklearn`.

---

## D-S040-13 — First study dataset (known-signal fixture)

**Locked:** S040 tests use **synthetic fixtures only**. No NQ. No optional NQ
demo script.

Reuse S039 synthetic matrix / fold machinery where possible
(`tests/unit/research/predictive/`,
`tests/unit/application/predictive_research/test_build_predictive_dataset.py`
helpers). Do not require a persisted workspace dataset for unit tests — in-
memory labelled frames with fold roles are enough.

Known-signal fixture (`SPRINT_040.md` §9):

1. Label is a known function of one feature plus noise. Ridge recovers a
   positive rank IC well above `RANDOM_PERMUTATION`.
2. Binary variant: logistic recovers AUC well above 0.5.
3. Pure-noise label: every family lands within the permutation-baseline spread.
4. Shuffling the label column destroys performance for every family.

Test 3 is the leakage tripwire for later refactors.

---

## D-S040-14 — Preprocessing spec

**Locked:** fitted transforms do not belong in the dataset builder (D-S039-10).
S040 fits them **inside each fold**, on `TRAIN` rows only, and never reuses a
fitted pipeline across folds. `PURGED` and `EMBARGOED` rows never reach
`fit()`.

Bounded transform set (do not grow this sprint):

```text
IMPUTE_MEDIAN     median imputation, numeric features
STANDARDIZE       zero-mean unit-variance
```

Default pipeline: `IMPUTE_MEDIAN` then `STANDARDIZE`. No encoding, PCA, winsor,
class rebalancing, or feature selection.

A test must assert that preprocessing statistics differ across folds (acceptance
criterion 5). The preprocessing spec is hashed into run identity.

---

## D-S040-15 — Family identifiers

Stable strings, hashed into run identity. Namespaced by adapter so S042/S043
cannot collide.

```text
sklearn.ridge          TaskType.REGRESSION
sklearn.elastic_net    TaskType.REGRESSION
sklearn.logistic       TaskType.CLASSIFICATION   (binary)
```

Unknown family ids fail with a framework error (missing extra vs unknown family
must be distinguishable: unknown family is a validation error even when the
extra is installed).

Reference baselines (D-S040-20) are **not** estimator-registry families.

---

## D-S040-16 — Determinism

**Locked:**

```text
EstimatorSpec.seed is required (int)
Adapter pins n_jobs=1 where the estimator accepts it
Do not rely on process-wide thread-pool env vars for the determinism test
```

T020 (PR 7): same spec + same dataset fingerprint → identical predictions and
identical `run_id`. A library upgrade changes the fingerprint by design.

---

## D-S040-17 — Model blob persistence

Restate of ADR-0023 §7 / D-S039-14.

**Locked:**

```text
Durable facts:      predictions.parquet + metrics.json
Fitted blobs:       models/fold_{n}.bin — opaque, one file per fold
Serializer:         joblib.dump / joblib.load (sklearn's joblib dependency)
Tagged with:        library name + version in the manifest
Not portable across library upgrades
Reproduce by re-fitting from the manifest — no workflow reloads blobs
```

`analyze_predictive_run` reads predictions + metrics only. Inspection of blobs
is convenience for later sprints (S042 importance); S040 must not make analysis
depend on `joblib.load`.

---

## D-S040-18 — Run identity fingerprint

Locked from `SPRINT_040.md` §6. The fingerprint hashes:

```text
dataset fingerprint (S039)
estimator spec (family + hyperparameters + seed)
preprocessing spec
library name + version of the adapter backend
framework version
```

It never hashes prediction bytes or fitted blobs.

`run_id` is the first 16 hex characters of SHA-256, matching S039 `dataset_id`
/ Signal Research `derive_run_id`. Two runs sharing a `run_id` must produce
identical predictions.

---

## D-S040-19 — Storage layout

```text
<workspace>/research/predictive_research/
  datasets/{dataset_id}/          (S039 — unchanged)
  runs/{run_id}/
    manifest.json                 dataset fingerprint, estimator spec, preprocessing, seeds, versions
    predictions.parquet           entity_id, fold_id, y_true, y_pred, y_proba
    metrics.json                  per-fold + pooled, including reference baselines
    models/fold_{n}.bin           fitted artifact (opaque, D-S040-17)
```

`entity_id` / `fold_id` reuse the S039 labelled-matrix columns. `y_true` is the
matrix `label` on TEST rows only. `y_proba` is null for regression.

Path helpers land next to existing `predictive_research_dataset_dir` in
`infrastructure/storage/paths.py` (T013). Register the `runs/` layout in the
paths module docstring.

---

## D-S040-20 — Reference baselines

Every run reports the same metrics for:

```text
CONSTANT_MEAN        predict the training-fold mean (regression)
MAJORITY_CLASS       predict the training-fold majority (classification)
RANDOM_PERMUTATION   shuffle model predictions within the test fold, fixed seed
```

These are metric-layer references, not sklearn registry families. They are
computed from TRAIN statistics / shuffled TEST predictions inside the fold.
`RANDOM_PERMUTATION` uses `EstimatorSpec.seed` so it is reproducible.

An AUC of 0.54 is meaningless without the permutation floor. These baselines
make that comparison automatic.

---

## D-S040-21 — Metrics

Two layers, both mandatory. Reported **per fold and pooled**. Pooled-only
output is rejected in review.

### Statistical

```text
Regression       RMSE, MAE, R², Spearman rank IC, Pearson IC
Classification   accuracy, balanced accuracy, ROC AUC, PR AUC, log loss, Brier score
                 + calibration bins (10 equal-width predicted-probability bins)
```

### Finance-aware

```text
Mean forward_return per prediction decile (out-of-sample / TEST only)
Top-decile minus bottom-decile spread
Hit rate at the declared decision threshold
Coverage: share of test rows above threshold
Mean forward_return of selected rows vs all test rows
```

Declared decision threshold lives on the run / analyze spec:

```text
Classification default: 0.5 on predicted positive-class probability
Regression default:     0.0 on y_pred  ("predicted positive forward return")
```

Forward return for finance-aware metrics is the S039 label source
(`forward_return` at the declared horizon), carried on TEST rows — not a
recomputed outcome.

Domain `research/predictive/metrics.py` implements these with numpy/polars.
Do not call `sklearn.metrics` from domain code.

---

## D-S040-22 — Out of scope (S040)

- Tree-based estimators (→ S042) and neural estimators (→ S043).
- Hyperparameter search of any kind — hyperparameters are declared, not searched.
- HTML reports and dashboards (→ S041, S044).
- Feature selection, class rebalancing, sample weighting, encoding, PCA.
- Ternary / multinomial classification (S039 label kind exists; S040 does not train it).
- Model artifact portability / model registry (TECHNICAL_DEBT.md §6).
- Reloading blobs as a reproduce path.
- Any path from predictions to orders, signals, or strategies.
- IDEA-014 promotion (→ S044 / ADR-0024).
- Extras `ml-trees` and `dl`.
- Continuous NQ run or NQ demo (D-S039-CI-dataset).
- A second GitHub Actions workflow file.

---

## D-S040-23 — PR sequence

Locked from `SPRINT_040.md` §10. No split required for size. Each PR targets
`sprint/predictive-baselines`.

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-baselines-planning` | T001 Wave 0 |
| 2 | `feat/predictive-estimator-protocol` | T002–T005 seam + extra |
| 3 | `feat/predictive-sklearn-adapter` | T006–T009 adapter |
| 4 | `feat/predictive-run-orchestration` | T010–T013 run + envelope |
| 5 | `feat/predictive-metrics` | T014–T018 metrics + baselines |
| 6 | `feat/predictive-cli` | T019 CLIs |
| 7 | `test/predictive-determinism-and-signal` | T020–T022 test suite |
| 8 | `docs/predictive-baselines-closure` | T023 documentation |

Wait for squash-merge of PR *n* before opening a dependent PR *n+1*.

PR 2 also: declare extra `ml`, register pytest marker `ml`, add the dedicated
CI job **if** it includes at least one marked smoke test (D-S040-10). mypy
sklearn override may wait until PR 3 if `infrastructure/ml/sklearn/` does not
yet exist; it must land with the first adapter module.

---

## Wave 0 checklist status

These boxes are the maintainer approval of S040 Wave 0. They stay unchecked
until that approval. Inherited S039 / ADR-0023 locks are already human-locked
and are not re-asked here.

- [ ] Confirm sprint branch: `sprint/predictive-baselines` (D-S040-02)
- [ ] Slice: baselines only — ridge, elastic net, logistic + naive references (D-S040-03)
- [ ] Registry in `infrastructure/ml/`; domain stays ML-free (D-S040-07)
- [ ] Extra `ml` = `scikit-learn>=1.6,<2.0`; not in `dev`; dedicated CI job in existing `ci.yml` (D-S040-09, D-S040-10)
- [ ] Marker `ml` + importorskip; default unit CI stays extra-free (D-S040-11)
- [ ] mypy override + lazy import; no sklearn under TYPE_CHECKING in domain (D-S040-12)
- [ ] Synthetic known-signal fixture; no NQ (D-S040-13)
- [ ] Preprocessing: median impute + standardize, TRAIN-only, per fold (D-S040-14)
- [ ] Family ids `sklearn.ridge` / `sklearn.elastic_net` / `sklearn.logistic` (D-S040-15)
- [ ] Artifact policy restated; joblib dump; re-fit to reproduce (D-S040-17)
- [ ] Metrics per fold and pooled; three reference baselines (D-S040-20, D-S040-21)
- [ ] Out of scope S040 confirmed (D-S040-22)
- [ ] PR sequence from SPRINT_040 §10 (D-S040-23)

Approved by:
Approved date:
