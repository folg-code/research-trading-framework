# Sprint 043 — Wave 0 Decisions

Binding decisions for Neural Predictive Models (Phase 10C). Date: 2026-08-26.
Inherited locks from S039–S042 / ADR-0023 are restated, not reopened.
Maintainer go-ahead 2026-08-26 (`ruszamy z sprintem 43` after S042
integration PR #335 landed on `main`). No new ADR — ADR-0024 remains
reserved for IDEA-014.

Basis: `SPRINT_043.md`, `ROADMAP.md` §13A Phase 10C, ADR-0023 (ACCEPTED),
`S042_WAVE0_DECISIONS.md` (determinism, bounded selection, leaderboard,
reserved panel `learning_curves`), `S041_WAVE0_DECISIONS.md` (panel
registry), `S040_WAVE0_DECISIONS.md` (estimator protocol).

S042 tree-based models are on `main` (#335). This sprint starts from that
tip. Waves 1–5 do **not** wait on any other PR.

---

## Inherited locks (do not reopen)

```text
research/predictive/ stays ML-free (no sklearn / xgboost / lightgbm / catboost / torch)
Adapters live in infrastructure/ml/<lib>/ behind PredictiveEstimator
Durable facts are predictions.parquet + metrics.json; blobs are opaque (TD-022)
No model registry (TD-021)
Synthetic fixtures only — no NQ as S043 acceptance
No signals / strategy / simulation / IDEA-014
Models do not trade
Phase 10 has no PASS/FAIL robustness verdict
CandidateSetSpec cap 8 default / 16 hard max; inner validation is TRAIN-only
SHAP stays deferred (SPRINT_042.md §9)
```

---

## D-S043-01 — Problem statement

Every estimator so far sees one row at a time. Temporal shape — the last
N bars of a feature, not just its current value — is invisible. This sprint
adds **sequence windows** as a domain contract, then two neural families
through the unchanged estimator protocol:

```text
feedforward   tabular control — same rows the trees consume
lstm / gru    sequence families — windowed lookback, fold-contained
```

The feedforward is not a consolation prize. It isolates *architecture*
from *input representation*, so an LSTM win can be attributed to sequence
structure rather than to neural networks in general.

With a few thousand samples per fold and noisy financial labels, deep
models frequently lose to gradient-boosted trees. **This sprint is complete
when the comparison is trustworthy, not when a network wins.** A well-run
negative result closes a real question and is an acceptable outcome.

---

## D-S043-02 — Sprint branch and PR base

```text
Integration branch: sprint/predictive-neural-models   (cut from main @ S042 #335)
Working branches:   feat/ | fix/ | docs/ | test/   (cloud: cursor/<slug>-b5e7)
PR base:            sprint/predictive-neural-models  (never main until sprint integration)
```

Working-branch PRs squash-merge into the sprint branch. When S043 is complete,
one integration PR goes `sprint/predictive-neural-models` → `main`.

---

## D-S043-03 — Sprint slice

**This sprint ships exactly:** extra `dl` (CPU PyTorch), `SequenceWindowSpec`
+ fold-aware window builder, torch adapter with seeded training and inner-fold
early stopping, declared feedforward / LSTM / GRU architectures, learning-curve
and window-accounting report panels, leaderboard rows beside trees and
baselines, a written comparison on synthetic fixtures.

| Order | Slice | Why |
|-------|--------|-----|
| 1 | Wave 0 | Binding S043 locks before extras or tensors |
| 2 | Sequence windowing | Domain contract, reviewable without torch |
| 3 | Extra + adapter | Training loop, seeding, early stopping, CI job |
| 4 | Architectures | Declared MLP + LSTM/GRU, scaler, tolerance test |
| 5 | Report + leaderboard | `learning_curves` + `window_accounting` |
| 6 | Closure | Comparison study + extra-free import test + docs |

**Not this sprint:** transformers, attention, GPU, pretraining, transfer
learning, architecture search, multi-instrument sequences, online /
incremental learning, NQ as acceptance, IDEA-014, SHAP.

---

## D-S043-04 — Methodology boundary

Restate of ADR-0023 §1. **Locked:**

```text
no signals
no strategy/
no signal_model/
no simulation
no promotion to Market Analysis components (IDEA-014 → S044 / ADR-0024)
```

A trained network is never a tradable signal inside Phase 10.

---

## D-S043-05 — Package layout

```text
research/predictive/windows.py             SequenceWindowSpec + builder + accounting
research/predictive/estimators.py          unchanged protocol (rank-2 or rank-3 ndarray)
research/predictive/importance.py          rank-3 permutation in Wave 4 (numpy only)
infrastructure/ml/registry.py              register torch families (lazy factories)
infrastructure/ml/torch/                   adapter, training loop, architectures
application/predictive_research/           window-then-fit orchestration
research/reporting/predictive/panels.py    register learning_curves + window_accounting
```

`research/predictive/` still imports **polars**, **numpy**, and framework
contracts only. Architecture tests already forbid torch outside
`infrastructure/ml/`. Do not weaken them. Do not import torch under
`TYPE_CHECKING` in domain code.

Application resolves families only through `resolve_estimator`. It must not
import `torch` or `infrastructure.ml.torch.*`.

---

## D-S043-06 — Extra `dl`

Policy inherited (D-S039-06 / ADR-0023 §3). S043 implements it.

**Locked:**

```text
[project.optional-dependencies]
dl = ["torch>=2.6,<2.10"]
```

```text
CPU wheels only — uv source is the pytorch-cpu index (no CUDA / nvidia-nccl)
Do not add torch to [dependency-groups] dev
Do not add torch to extra `ml` or extra `ml-trees`
Default `uv sync --locked --dev` stays extra-free
```

Exact pins are `uv lock` work in PR 3 (T006). The adapter rejects GPU / CUDA
/ MPS device options at spec validation even if a CUDA wheel is somehow
installed.

Neural families apply `PreprocessingSpec` (`IMPUTE_MEDIAN` then
`STANDARDIZE`) with a **numpy implementation inside the torch adapter**.
Resolving a neural family therefore requires extra `dl` only — not extra
`ml`. Missing `dl` raises `PredictiveExtraError` naming extra `dl`.

Module-level files under `infrastructure/ml/torch/` must not import torch
at import time. The first import happens inside the factory / `fit()` path;
failure becomes `PredictiveExtraError`.

mypy: add `ignore_missing_imports` overrides for `torch`, `torch.*`. Default
quality job stays extra-free.

---

## D-S043-07 — Dedicated CI job, marker, and env gate

**Locked:** add one job to the **existing** `.github/workflows/ci.yml`. Do not
create a second workflow file.

```text
Job id:     dl
Name:       DL extra tests
Install:    uv sync --locked --extra dl --dev
Env:        TRADING_FRAMEWORK_RUN_TORCH_TESTS=1
Run:        uv run pytest -m torch -q
```

Standard jobs remain extra-free. The unit job additionally excludes the new
marker once it exists:

```text
uv run pytest tests/unit -m "not ml and not ml_trees and not torch" --cov=...
```

Do **not** put `-m "not torch"` in global `addopts`.

Marker name is `torch`. Extra name stays `dl` (already locked in ADR-0023).
Register the marker in `pyproject.toml` because `--strict-markers` is on.

Two layers, both required for training tests:

```text
@pytest.mark.torch
@pytest.mark.skipif(os.getenv("TRADING_FRAMEWORK_RUN_TORCH_TESTS") != "1", ...)
```

The env gate follows the Binance / Databento opt-in pattern so a developer
who happens to have torch installed does not train on every local pytest.
The dedicated CI job **sets the env**, because these tests are network-free
and must actually run in CI (unlike Binance smoke). Domain windowing and
spec tests are unmarked and always run.

The `dl` job lands in the same PR that first has a `@pytest.mark.torch`
test (PR 3). Until that PR, do not add the job.

Torch test modules also call `pytest.importorskip("torch")` at module level
so local extra-free pytest **skips** instead of failing at collection.

Gated-tier time budget (recorded here so review does not relitigate it):

```text
<= 64 TRAIN rows per fold
lookback_bars <= 4
max_epochs <= 5
hidden size <= 16
must finish in 120 seconds on ubuntu-latest CPU
```

---

## D-S043-08 — Family identifiers

Stable strings, hashed into run identity. Namespaced by adapter (D-S040-15).

```text
torch.feedforward.regressor     TaskType.REGRESSION          tabular
torch.feedforward.classifier    TaskType.CLASSIFICATION      tabular, binary
torch.lstm.regressor            TaskType.REGRESSION          sequence
torch.lstm.classifier           TaskType.CLASSIFICATION      sequence, binary
torch.gru.regressor             TaskType.REGRESSION          sequence
torch.gru.classifier            TaskType.CLASSIFICATION      sequence, binary
```

Unknown ids are `PredictiveSpecError` even when extra `dl` is installed.
Task-type mismatch is `PredictiveSpecError`. Multiclass / ternary targets
are rejected, same as `sklearn.logistic`.

Tabular families **reject** a `SequenceWindowSpec` (`PredictiveSpecError`).
Sequence families **require** a `SequenceWindowSpec`. That split is the
point of the feedforward control.

Reference baselines remain **not** registry families.

---

## D-S043-09 — Sequence window contract

New domain value object in `research/predictive/windows.py` (no ML imports):

```text
SequenceWindowSpec
  lookback_bars     int      past rows per sample, inclusive of the end row
  stride            int      sampling step between window end-rows
  padding_policy    DROP     incomplete windows are dropped, never padded
```

Validation:

```text
lookback_bars in [2, 256]
stride >= 1
padding_policy is DROP only — any other value is PredictiveSpecError
```

Binding construction rules (after fold assignment, never before):

```text
A window contributing to a TRAIN sample may contain only TRAIN rows
A window ending in the TEST fold may not reach back into PURGED, EMBARGOED, or TRAIN
Windows never cross an outer fold-role boundary — the builder drops them instead of truncating
Windows are ordered by (entity_id, available_at); entity_id changes always break a window
Row gaps (see D-S043-10) break a window; the builder does not silently bridge them
```

A test asserts that no `TEST` window contains a row with a non-`TEST` role.

Inner-train / inner-validation (D-S043-13) are both outer `TRAIN` rows.
Windows **may** reach across that inner cut. That is not outer-test leakage.

Default fixture lookback is 4. Production defaults are not advice; tests
must not depend on a hidden default lookback larger than the fixture.

`SequenceWindowSpec` is hashed into run identity when present (D-S043-18).

---

## D-S043-10 — Gaps and dropped-window accounting

A prospective window is gapped when any adjacent pair of rows, ordered by
`available_at` within one `entity_id`, is separated by more than the study's
`evaluation_timeframe` (from `PredictiveStudySpec`). The builder takes
`bar_duration` as an argument; it does not invent a timeframe.

Dropped-window accounting is persisted as `window_accounting.json` next to
the run (not inside `predictions.parquet`):

```text
per outer fold, per role in {TRAIN, TEST}:
  candidate_end_rows
  windows_built
  windows_dropped_incomplete
  windows_dropped_gap
  windows_dropped_fold_boundary
  effective_sample
```

`effective_sample` is `windows_built`. A long lookback on a short fold can
discard most of the dataset; the report must show that rather than a strong
metric on 200 surviving rows.

A fold whose TEST `effective_sample` is below 10 after windowing raises
`PredictiveSpecError` (too little honest sample to score). TRAIN below 10
inner-train or 10 inner-validation windows after windowing is the same
error (inherit S042 minima, applied to windows not raw rows).

---

## D-S043-11 — Protocol rank

The `PredictiveEstimator` protocol is **unchanged**: `fit` / `predict` take
`np.ndarray`. Rank is a family concern, not a protocol change.

```text
tabular families     rank-2   (n_samples, n_features)
sequence families    rank-3   (n_windows, lookback_bars, n_features)
```

Application builds windows **before** `fit()` / `predict()` for sequence
families. Domain windowing returns numpy arrays, not tensors. The adapter
validates rank and raises `PredictiveSpecError` on mismatch.

`native_feature_importance()` returns `None` for every neural family
(same as sklearn). Permutation importance stays library-free numpy.

Rank-2 permutation path is unchanged. Rank-3 path (Wave 4): shuffle one
feature channel across windows with the same permutation on axis 0, so
lookback structure is preserved but that feature is broken across samples.
`importance.py` currently rejects non-2d input; Wave 4 extends it. Do not
flatten the last bar as a substitute.

---

## D-S043-12 — Declared architectures and hyperparameters

Architectures are declared, not searched. Unknown hyperparameter keys are
`PredictiveSpecError`. Candidate sets stay capped as in S042.

Shared (all neural families):

```text
max_epochs          positive int, default 50, hard max 200
batch_size          positive int, default 32
learning_rate       (0, 1], default 1e-3
weight_decay        >= 0, default 0
patience            positive int, default 5
min_delta           >= 0, default 0
dropout             [0, 0.5], default 0
```

Optimizer is **Adam** only. Loss is **MSE** (regression) or
**BCE-with-logits** (binary classification). Any other optimizer, loss,
activation, or device key is `PredictiveSpecError`.

Feedforward extras:

```text
hidden_sizes        tuple[int, ...], each >= 1, length 1..3, default (32, 16)
activation          "relu" only
```

LSTM / GRU extras:

```text
hidden_size         positive int, default 32, hard max 128
num_layers          1 or 2, default 1
```

`bidirectional`, GPU device keys, and `num_layers > 2` are rejected.
Dropout on a single-layer recurrent net is accepted as a no-op after the
last layer (PyTorch constraint); do not invent a different meaning.

Default fixture hyperparameters (tests, not production advice):

```text
max_epochs=5
batch_size=16
hidden_sizes=(16,)
hidden_size=8
num_layers=1
lookback_bars=4
```

---

## D-S043-13 — Training loop and early stopping

Neural families **always** carve an inner validation split from outer
TRAIN, even without `CandidateSetSpec`. Trees without a candidate set do
not split; networks need a stopping set. That difference is explicit.

Procedure per outer fold:

1. Take outer `TRAIN` rows only. `PURGED` / `EMBARGOED` never enter fit.
2. Split them chronologically: last `inner_validation_fraction` (default
   0.20, in `(0, 0.5]`) is inner validation, the prefix is inner train.
3. Build windows (sequence families) or use rows (feedforward) **separately**
   on each inner partition. TEST windows are not built yet.
4. Fit scaler on outer-TRAIN 2d feature rows (D-S043-15). Apply it to
   inner-train and inner-val (every timestep of each window).
5. Train on inner-train. Early-stop on inner-val loss. Record
   `stopping_epoch` and the learning curve.
6. If `CandidateSetSpec` is present, score `selection_metric` on inner-val
   predictions, select the winner (ties: declaration order), then continue
   with the winner only. The same inner split is used for selection **and**
   early stopping — do not split twice.
7. Refit the winner on the full outer TRAIN for **exactly** `stopping_epoch`
   epochs, no further early stopping.
8. Predict the outer TEST rows / windows once.

Using outer `TEST` as an early-stopping set is `PredictiveSpecError`. A
unit test constructs that configuration and asserts the rejection.

Last batch may be smaller than `batch_size`. Empty inner-train after
windowing is `PredictiveSpecError`.

---

## D-S043-14 — Determinism and tolerance

```text
Seeded: python, numpy, torch global RNG, and a recorded torch.Generator
torch.use_deterministic_algorithms(True)
non-deterministic kernels rejected (do not catch and continue)
torch.set_num_threads(1); thread count recorded in resolved_params
device = cpu; CUDA / MPS / cuda:0 rejected at validation
DataLoader shuffle uses the recorded Generator
```

Unlike trees, bit-identical reproduction across platforms is not always
achievable for floating-point reductions. **Locked policy:**

```text
Identical results are required on the same machine and library version
Reproducibility test asserts allclose with atol=1e-5, rtol=1e-4
Tolerance is recorded in the run manifest and EstimatorDescription.resolved_params
If a configuration cannot meet that, the adapter rejects it
```

Do not rely on process-wide `OMP` / `MKL` / `CUBLAS` env vars for the
determinism test. Reproducibility outranks throughput.

---

## D-S043-15 — Fold-local scaler

Reuse `PreprocessingSpec` (`IMPUTE_MEDIAN` then `STANDARDIZE`). Implement
the steps in numpy inside the torch adapter so extra `dl` does not require
extra `ml`.

Fit on the 2d TRAIN feature rows of the outer fold (the same rows trees
would see), then apply the fitted transform to every timestep of every
window. Do not fit on windowed 3d tensors. `PURGED` / `EMBARGOED` never
reach `fit()`.

A test must assert that scaler statistics differ across folds (same
acceptance as D-S040-14).

---

## D-S043-16 — Report panels

S041 reserved `learning_curves`. S043 registers two panels; it does not
edit the assembly function:

```text
learning_curves      train and inner-validation loss per epoch, stopping epoch marked
window_accounting    dropped windows and effective sample per fold / role
```

`window_accounting` is a new id (not reserved in S041). Wave 4 adds it to
the registry and removes `learning_curves` from `RESERVED_PANEL_IDS`.
Skip notes: missing sidecar → skip, do not fail the report.

Learning-curve payload (`learning_curves.json`):

```text
per outer fold:
  epochs: list[int]
  train_loss: list[float]
  validation_loss: list[float]
  stopping_epoch: int
```

Curves come from the **inner** training run (where early stopping happened),
not from the refit.

---

## D-S043-17 — Leaderboard and comparison study

S042 `compare_predictive_runs` is unchanged. Neural families appear as
rows on the same dataset fingerprint, beside trees and S040 baselines.

T019 comparison study is the same synthetic known-signal / noise-label
fixtures, not a live market. The written conclusion states which family
won and whether the LSTM beat the feedforward on the same folds. A tree
win is an acceptable close.

---

## D-S043-18 — Artifact persistence and run identity

Restate of D-S040-17 / TD-022, plus window sidecars:

```text
Durable facts:     predictions.parquet + metrics.json
                   + learning_curves.json + window_accounting.json
                   + selection_trace.json (when CandidateSetSpec is used)
Fitted blobs:      models/fold_{n}.bin — opaque via serialize_artifact
                   (torch.save into bytes; still not portable)
Not portable across library upgrades
Reproduce by re-fitting from the manifest
analyze_predictive_run still must not deserialize blobs
```

Run identity additionally hashes `SequenceWindowSpec` when present, and
the torch library name + version. It never hashes prediction bytes,
tensors, or fitted blobs.

---

## D-S043-19 — First study dataset

**Locked:** S043 tests use **synthetic fixtures only**. No NQ.

Reuse S040 / S042 known-signal and noise-label fixtures. Additional
neural-specific assertions:

1. Window leakage: no TEST window contains a non-TEST role.
2. Known-signal: feedforward recovers primary metric above
   `RANDOM_PERMUTATION` on the tabular fixture (same folds as ridge).
3. Sequence vs tabular: LSTM is trained on windowed features of the same
   study; the leaderboard comparison is the result, not a required win.
4. Noise label: neural families land within the permutation-baseline
   spread (leakage tripwire).
5. Reproducibility: two fits, `allclose` within D-S043-14 tolerance.
6. Extra-free: importing `infrastructure.ml.registry` does not import
   torch.

---

## D-S043-20 — PR sequence

Locked from `SPRINT_043.md` §8.

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-neural-models-planning` | T001 Wave 0 |
| 2 | `feat/predictive-sequence-windowing` | T002–T005 windowing (no torch) |
| 3 | `feat/predictive-torch-adapter` | T006–T010 extra + adapter + CI job |
| 4 | `feat/predictive-neural-architectures` | T011–T014 MLP + LSTM/GRU |
| 5 | `feat/predictive-report-learning-curves` | T015–T018 report + leaderboard |
| 6 | `docs/predictive-neural-models-closure` | T019–T021 study + docs |

PR 2 is independent of PyTorch: windowing is domain logic and must be
reviewable and testable without the extra installed.

Each PR targets `sprint/predictive-neural-models`.

---

## Wave 0 checklist status

- [x] Sprint branch `sprint/predictive-neural-models` cut from `main` @ #335 (D-S043-02)
- [x] Slice: windows + feedforward control + LSTM/GRU; no GPU / transformers (D-S043-03)
- [x] Extra `dl` CPU-only; not in `dev`; independent of extra `ml` (D-S043-06)
- [x] CI job `dl` + marker `torch` + env `TRADING_FRAMEWORK_RUN_TORCH_TESTS` (D-S043-07)
- [x] Family ids namespaced `torch.{feedforward,lstm,gru}.*` (D-S043-08)
- [x] Fold-contained windows, DROP padding, gap breaks, accounting sidecar (D-S043-09/10)
- [x] Protocol unchanged; rank-2 tabular vs rank-3 sequence (D-S043-11)
- [x] Declared architectures; Adam / MSE / BCE; candidate cap inherited (D-S043-12)
- [x] Neural runs always inner-split for early stopping; outer TEST once (D-S043-13)
- [x] Tolerance policy atol=1e-5 rtol=1e-4; threads=1; CPU only (D-S043-14)
- [x] Numpy scaler in the adapter; statistics differ per fold (D-S043-15)
- [x] Panels `learning_curves` + `window_accounting` (D-S043-16)
- [x] Synthetic fixtures only (D-S043-19)
- [x] PR sequence from SPRINT_043 §8 (D-S043-20)

Approved by: Project Maintainer (go-ahead `ruszamy z sprintem 43`, 2026-08-26)
Approved date: 2026-08-26
