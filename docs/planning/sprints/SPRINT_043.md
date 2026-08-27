# Sprint 043 — Neural Predictive Models: Feedforward and LSTM (Phase 10C)

## Metadata

```text
Sprint: 043
Phase: Phase 10C — Neural Predictive Models
Status: IN PROGRESS (Wave 0)
Planned Start: 2026-08-26
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_040 (estimator seam), SPRINT_041 (report panels), SPRINT_042 (leaderboard)
Sprint Branch: sprint/predictive-neural-models
Task branch convention: feat/ | fix/ | docs/ | test/
Wave 0 decisions: docs/planning/sprints/S043_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§13A Phase 10C)
  - docs/adr/ADR-0023 (Predictive Research boundary — S039)
  - docs/planning/sprints/SPRINT_039.md (fold roles, availability columns)
  - docs/planning/sprints/SPRINT_042.md (determinism and bounded-selection precedent)
```

---

## 0. Slice choice

Two capabilities are missing and only one of them is really about neural networks.

The first is **sequence modelling**: every estimator so far sees one row at a time, so temporal shape
— the last 60 bars of a feature, not just its current value — is invisible. An LSTM is the vehicle,
but the durable contribution is the windowed dataset contract and the proof that windows respect
fold boundaries.

The second is a fair comparison. A feedforward network on the same tabular rows the trees consume
isolates *architecture* from *input representation*, so a win by the LSTM can be attributed to
sequence structure rather than to neural networks in general.

A word on expectations, stated here so it is not litigated at review time: with a few thousand
samples per fold and noisy financial labels, deep models frequently lose to gradient-boosted trees.
This sprint is complete when the comparison is trustworthy — not when a network wins. A well-run
negative result closes a real question and is an acceptable outcome.

**Out of scope:** transformers, GPU, pretraining, multi-asset models.

---

## 1. Sprint Goal

```text
PredictiveDatasetEnvelope (S039)
    ↓
SequenceWindowSpec (lookback, stride) — windows confined to a single fold
    ↓
EstimatorSpec family = feedforward | lstm | gru
    ↓
per fold: fit scaler + train with inner-validation early stopping → predict TEST
    ↓
PredictiveRunEnvelope (unchanged schema) + leaderboard entry
    ↓
report extended with learning curves
```

Success: a network trains reproducibly on CPU, its predictions land in the same envelope schema as
every other family, and the leaderboard shows honestly how it compares to trees and baselines.

---

## 2. In scope

- [ ] Optional extra `dl` = PyTorch (CPU build).
- [ ] `SequenceWindowSpec` in the domain — windowing rules, no tensor library.
- [ ] Window builder enforcing fold containment (§4).
- [ ] Torch adapter in `infrastructure/ml/torch/`: training loop, early stopping, seeding.
- [ ] Feedforward MLP (tabular) and LSTM/GRU (sequence) architectures.
- [ ] Determinism configuration and a documented tolerance policy (§5).
- [ ] Environment-gated test tier, keeping standard CI fast (§6).
- [ ] Report panel: learning curves per fold with stopping epoch.
- [ ] Leaderboard entries alongside trees and baselines.

## 3. Out of scope

- Transformers and attention architectures.
- GPU or distributed training.
- Pretraining, transfer learning, self-supervised objectives.
- Automated architecture search — architectures are declared, candidate sets stay capped as in S042.
- Multi-instrument or cross-sectional sequence models.
- Online / incremental learning.

---

## 4. Sequence window contract

```text
SequenceWindowSpec
  lookback_bars     int      number of past rows per sample
  stride            int      sampling step between windows
  padding_policy    DROP     incomplete windows are dropped, never padded
```

Binding rules:

```text
A window contributing to a TRAIN sample may contain only TRAIN rows
A window ending in the TEST fold may not reach back into PURGED or EMBARGOED rows
Windows never cross a fold boundary — the builder drops them instead of truncating
Row gaps (session breaks, missing bars) break a window; the builder does not silently bridge them
Window construction happens after fold assignment, never before
```

The third rule deserves emphasis. A 60-bar lookback silently extends every test sample 60 bars into
the past, which quietly undoes the purge computed in S039 unless windowing is fold-aware. A test
asserts that no `TEST` window contains a row with a non-`TEST` role.

Dropped-window accounting is persisted: a long lookback on short folds can discard most of the
dataset, and the report must show that rather than reporting a strong metric on 200 surviving rows.

---

## 5. Determinism and its limits

```text
Seeded: python, numpy, torch global and per-generator seeds
Deterministic algorithms enabled; non-deterministic kernels rejected
Thread count pinned and recorded
DataLoader shuffling seeded with a recorded generator
```

Unlike trees, bit-identical reproduction across platforms is not always achievable for
floating-point reductions. The policy is explicit rather than aspirational: **identical results are
required on the same machine and library version**, and the reproducibility test asserts equality
within a declared numerical tolerance, with the tolerance recorded in the manifest. If a
configuration cannot meet even that, the adapter rejects it.

---

## 6. Test tiering

PyTorch is heavy and training is slow. Standard CI must stay fast and network-free, following the
existing opt-in pattern used for Databento and Binance:

```text
Default CI            contract tests only — specs, windowing, validation, error paths (no torch)
TRADING_FRAMEWORK_RUN_TORCH_TESTS=1    training tests on tiny fixtures, few epochs
```

Windowing and spec validation are pure-domain and therefore always covered. Only the adapter's
training loop sits behind the gate. The `dl` extra is never installed in the default CI job.

---

## 7. Task breakdown

### Wave 0 — Planning

| Task | Description | Status |
|------|-------------|--------|
| S043-T001 | Wave 0 decisions (architectures, tolerance policy, CI tier) | DONE |

### Wave 1 — Sequence windowing (domain, no torch)

| Task | Description | Status |
|------|-------------|--------|
| S043-T002 | `SequenceWindowSpec` + validation | TODO |
| S043-T003 | Window builder with fold containment and gap handling | TODO |
| S043-T004 | Dropped-window accounting persisted on the run manifest | TODO |
| S043-T005 | Window leakage tests (no cross-role, no cross-fold windows) | TODO |

### Wave 2 — Torch adapter

| Task | Description | Status |
|------|-------------|--------|
| S043-T006 | Optional extra `dl` + missing-extra error | TODO |
| S043-T007 | Adapter skeleton implementing `PredictiveEstimator` | TODO |
| S043-T008 | Training loop: batching, optimizer, loss per task type | TODO |
| S043-T009 | Early stopping on inner validation split (never outer TEST) | TODO |
| S043-T010 | Seeding + deterministic algorithm configuration | TODO |

### Wave 3 — Architectures

| Task | Description | Status |
|------|-------------|--------|
| S043-T011 | Feedforward MLP (regression + classification) | TODO |
| S043-T012 | LSTM / GRU sequence estimator (regression + classification) | TODO |
| S043-T013 | Per-fold scaler fitted on training rows only | TODO |
| S043-T014 | Reproducibility test within declared tolerance | TODO |

### Wave 4 — Reporting and comparison

| Task | Description | Status |
|------|-------------|--------|
| S043-T015 | Learning curve capture (train/validation loss per epoch, stopping epoch) | TODO |
| S043-T016 | Report panel: learning curves per fold | TODO |
| S043-T017 | Report panel: window accounting (dropped windows, effective sample) | TODO |
| S043-T018 | Leaderboard entries for neural families | TODO |

### Wave 5 — Closure

| Task | Description | Status |
|------|-------------|--------|
| S043-T019 | Comparison study: baselines vs trees vs feedforward vs LSTM | TODO |
| S043-T020 | Import test: framework usable without the `dl` extra | TODO |
| S043-T021 | Docs: RESEARCH_METHODOLOGIES, MODULE_MAP, CURRENT_STATUS | TODO |

**Progress:** 1 / 21 tasks

---

## 8. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/predictive-neural-models-planning` | T001 Wave 0 |
| 2 | `feat/predictive-sequence-windowing` | T002–T005 windowing (no torch dependency) |
| 3 | `feat/predictive-torch-adapter` | T006–T010 adapter + training loop |
| 4 | `feat/predictive-neural-architectures` | T011–T014 MLP + LSTM |
| 5 | `feat/predictive-report-learning-curves` | T015–T018 report + leaderboard |
| 6 | `docs/predictive-neural-models-closure` | T019–T021 study + docs |

PR 2 is deliberately independent of PyTorch: windowing is domain logic and must be reviewable and
testable without the extra installed.

Each PR targets `sprint/predictive-neural-models`.

---

## 9. Acceptance criteria

1. Feedforward and LSTM families run through the unchanged `PredictiveEstimator` protocol.
2. No `TEST` window contains a row with a non-`TEST` fold role; a test proves it.
3. Windows never cross fold boundaries; incomplete windows are dropped, never padded.
4. Dropped-window counts appear in the manifest and in the report.
5. Early stopping uses an inner validation split; using outer `TEST` is rejected at validation.
6. Scaler statistics differ per fold, proven by test.
7. Repeated training on one machine reproduces results within the declared tolerance.
8. Standard CI passes without the `dl` extra installed and runs no training.
9. Gated tier trains on tiny fixtures and completes within a documented time budget.
10. Learning curves show train and validation loss per fold with the stopping epoch marked.
11. Leaderboard reports neural families beside trees and baselines on one dataset fingerprint.
12. Sprint closes with a written comparison conclusion, whichever family wins.
13. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Lookback windows silently undo the purge | Fold-aware windowing + explicit leakage test (T005) |
| Long lookback destroys effective sample size | Dropped-window accounting surfaced in the report |
| Slow CI from heavy dependency | `dl` extra excluded from default CI; gated test tier |
| Non-reproducible floating-point results | Declared tolerance policy; rejection of unstable configs |
| Architecture tinkering consumes the sprint | Declared architectures only; capped candidates as in S042 |
| Negative result treated as sprint failure | §0 states the success condition is a trustworthy comparison |
| Overfitting on small folds | Early stopping, train/test gap panel from S042 applies unchanged |

---

## 11. Dependencies

**Required:** S040 estimator seam, S041 report registry, S042 leaderboard and gap diagnostics.

**Not required:** dashboard, robustness experiments, execution.

---

## 12. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Plus, before closing the sprint:

```bash
TRADING_FRAMEWORK_RUN_TORCH_TESTS=1 uv run pytest -m torch
```

---

## 13. Post-sprint direction

Sprint 044 surfaces all of this in the dashboard and writes the gate document deciding under what
conditions a trained model may become a Market Analysis State component (IDEA-014).
