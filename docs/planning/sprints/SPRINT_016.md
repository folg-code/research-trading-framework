# Sprint 016 — Robustness Research MVP (Phase 7)

## Metadata

```text
Sprint: 016
Phase: Phase 7 — Robustness Research
Status: PLANNED
Planned Start: 2026-07-15
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_013–015 merged to main (ADR-0016, ADR-0017, ADR-0018)
Sprint Branch: sprint/robustness-mvp
Task branch convention: feat/ | fix/ | docs/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S016_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§11 Phase 7)
  - docs/vision/WORKFLOWS_AI_ADR_UPDATED.md (§4.20–4.21)
  - docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md
  - docs/adr/ADR-0013-signal-research-analytics-boundary.md
Track choice: Phase 7 Robustness selected over Phase 4B orderflow / Phase 6B multi-data — 2026-07-15
```

---

## 0. Slice choice

Strategy Research (Sprint 013) persists reproducible runs. The missing capability is **validation
orchestration** — answering whether a candidate strategy is stable enough for paper execution.

Phase 7 MVP delivers:

```text
Experiment Infrastructure
Parameter Robustness (grid sweep)
Walk-Forward (rolling + expanding)
Stress Testing
Statistical Diagnostics + Monte Carlo
Robustness Report + explicit verdict
```

**Final artifact:** documented answer — PASS / CONDITIONAL / FAIL — not merely the best parameter set.

**Out of scope:** order-book MC, market impact, portfolio robustness, distributed execution,
Bayesian/genetic optimization, PBO/CSCV/DSR/White/Hansen SPA.

---

## 1. Sprint Goal

```text
Published OHLCV + Strategy Model template
    ↓
RobustnessExperiment (declarative spec)
    ↓
run_robustness_experiment (grid / folds / stress / MC config generation)
    ↓
batch run_strategy_research (child runs, resume-safe)
    ↓
analyze_robustness_experiment (rankings, WF stitch, stress, MC envelope, diagnostics)
    ↓
RobustnessVerdict + offline Robustness Report HTML
```

Success: on canonical NQ continuous OHLCV, a maintainer runs one experiment command, resumes after
interrupt, and receives a report with **explicit verdict** and Monte Carlo equity envelope.

---

## 2. MVP scope checklist (completion criteria)

Phase 7 MVP is complete when the system can:

- [ ] Define a reproducible robustness experiment (manifest + fingerprints + RNG seed).
- [ ] Generate and execute a parameter grid sweep with ranking.
- [ ] Assess neighbor-parameter stability and detect isolated optima.
- [ ] Run rolling and expanding walk-forward with train-only selection.
- [ ] Evaluate selected parameters on OOS and build a stitched OOS equity curve.
- [ ] Run stress scenarios (commission, slippage, delays, remove top trades/days).
- [ ] Assess temporal stability and PnL concentration.
- [ ] Run trade shuffle, trade bootstrap, and block bootstrap Monte Carlo.
- [ ] Produce Monte Carlo equity path envelopes (percentile bands + tail probabilities).
- [ ] Measure IS/OOS degradation linked to walk-forward folds.
- [ ] Emit one coherent Robustness Report HTML.
- [ ] Emit explicit verdict (PASS / CONDITIONAL / FAIL) with strengths and weaknesses.

---

## 3. Six outcomes (waves)

| Wave | Outcome | Key deliverables |
|------|---------|------------------|
| **0** | Planning | Wave 0 decisions, ADR-0019, sprint doc |
| **1** | Experiment Infrastructure | spec, grid generator, batch executor, registry, resume, run comparison |
| **2** | Parameter Robustness | sweep ranking, neighbor stability, heatmaps, isolated optimum |
| **3** | Walk-Forward | rolling/expanding folds, train select, OOS eval, stitched equity |
| **4** | Stress Testing | scenario specs, child stress runs, comparison analytics |
| **5** | Diagnostics + Monte Carlo | temporal stability, concentration, bootstrap, **MC shuffle + envelope**, IS/OOS degradation |
| **6** | Report + closure | verdict model, HTML report, docs, MODULE_MAP, DATA_WORKFLOWS |

---

## 4. Domain boundary

```text
research/robustness/                 experiment kinds, fold policy, MC/stress specs, verdict
research/datasets/robustness.py      experiment envelope + repository
application/robustness_research/     run + analyze orchestration
research/reporting/robustness/       offline HTML (Phase A)
application/strategy_research/       unchanged simulator — called by robustness batch only
```

### Binding rules

```text
Robustness orchestrates Strategy Research — does not fork simulation kernel
Analytics is read-only except declared stress re-runs (new child runs)
Walk-forward: no OOS peeking into train selection
Monte Carlo: trade-level only in MVP (no price-path simulation)
Verdict ≠ best grid rank
```

---

## 5. Storage

```text
<storage_root>/robustness_experiments/<experiment_id>/
  manifest.json
  registry.json
  folds/                    (walk-forward)
  child_runs.jsonl
  analytics/
  report/

<storage_root>/strategy_research/<run_id>/   (child runs — existing layout)
```

---

## 6. Task breakdown

### Wave 0 — Planning

| Task | Description | Status |
|------|-------------|--------|
| S016-T001 | Wave 0 decisions (`S016_WAVE0_DECISIONS.md`) | DONE |
| S016-T002 | Sprint plan (this document) | DONE |
| S016-T003 | ADR-0019 — Robustness Research MVP | DONE |

### Wave 1 — Experiment Infrastructure

| Task | Description | Status |
|------|-------------|--------|
| S016-T004 | `RobustnessExperiment` spec + validation (kinds, grids, thresholds) | DONE |
| S016-T005 | Config generator (parameter grid expansion) | DONE |
| S016-T006 | `run_robustness_experiment` batch executor | DONE |
| S016-T007 | Experiment registry + resume cursor | DONE |
| S016-T008 | Child run linkage (`experiment_id` on strategy manifest) | DONE |
| S016-T009 | Compare multiple experiments (read-only summary) | DONE |

### Wave 2 — Parameter Robustness

| Task | Description | Status |
|------|-------------|--------|
| S016-T010 | Sweep ranking over child run metrics | DONE |
| S016-T011 | Neighbor-parameter stability analysis | DONE |
| S016-T012 | Heatmap view model (grid × metric) | DONE |
| S016-T013 | Isolated optimum detection | DONE |

### Wave 3 — Walk-Forward

| Task | Description | Status |
|------|-------------|--------|
| S016-T014 | Fold planner (rolling + expanding) | DONE |
| S016-T015 | Train-only parameter selection per fold | DONE |
| S016-T016 | OOS evaluation per fold | DONE |
| S016-T017 | Stitched OOS equity curve builder | DONE |

### Wave 4 — Stress Testing

| Task | Description | Status |
|------|-------------|--------|
| S016-T018 | Stress scenario spec (commission, slippage, delay) | PLANNED |
| S016-T019 | Remove-top-trades / remove-top-days scenarios | PLANNED |
| S016-T020 | Stress batch execution + comparison table | PLANNED |

### Wave 5 — Statistical Diagnostics + Monte Carlo

| Task | Description | Status |
|------|-------------|--------|
| S016-T021 | Temporal stability metrics | PLANNED |
| S016-T022 | PnL concentration (top trades / days) | PLANNED |
| S016-T023 | Trade PnL bootstrap | PLANNED |
| S016-T024 | Block bootstrap (session-day blocks) | PLANNED |
| S016-T025 | Trade-sequence shuffle Monte Carlo | PLANNED |
| S016-T026 | Equity path envelope (p5/p50/p95) + tail probabilities | PLANNED |
| S016-T027 | IS/OOS degradation linkage (walk-forward) | PLANNED |

### Wave 6 — Report, CLI, closure

| Task | Description | Status |
|------|-------------|--------|
| S016-T028 | `RobustnessVerdict` model + threshold evaluation | PLANNED |
| S016-T029 | `analyze_robustness_experiment` orchestrator | PLANNED |
| S016-T030 | Offline Robustness Report HTML renderer | PLANNED |
| S016-T031 | CLIs: run / analyze / render | PLANNED |
| S016-T032 | Integration test on canonical strategy + fixture OHLCV | PLANNED |
| S016-T033 | Update MODULE_MAP, DATA_WORKFLOWS, CURRENT_STATUS, ROADMAP | PLANNED |
| S016-T034 | Sprint closure | PLANNED |

**Progress:** 17 / 34 tasks

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/robustness-mvp-planning` | Wave 0 + ADR-0019 + sprint doc |
| 2 | `feat/robustness-experiment-infrastructure` | T004–T009 experiment infra |
| 3 | `feat/robustness-parameter-sweep` | T010–T013 parameter robustness |
| 4 | `feat/robustness-walk-forward` | T014–T017 walk-forward |
| 5 | `feat/robustness-stress-testing` | T018–T020 stress |
| 6 | `feat/robustness-monte-carlo-diagnostics` | T021–T027 diagnostics + MC |
| 7 | `feat/robustness-report-verdict` | T028–T031 report + CLI |
| 8 | `docs/robustness-mvp-closure` | T032–T034 integration + docs |

Each PR targets `sprint/robustness-mvp`. Final integration PR → `main` when all required tasks complete.

---

## 8. Acceptance criteria

1. Declarative experiment spec validates and persists with fingerprints + MC RNG seed.
2. Parameter grid executes as batch Strategy Research with resume after interrupt.
3. Walk-forward selects on train only; stitched OOS equity is chronologically correct.
4. Stress scenarios produce comparable child runs with explicit assumption diffs.
5. Monte Carlo delivers shuffle, bootstrap, block bootstrap, and percentile equity envelope.
6. Report HTML includes verdict, heatmaps, WF, stress, MC, and diagnostics sections.
7. Best grid cell is never labeled "validated" without verdict gates passing.
8. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
9. ADR-0019 ACCEPTED; MODULE_MAP and DATA_WORKFLOWS updated.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Grid combinatorial explosion | MVP grid size limits; explicit cell count in manifest |
| Train/OOS leakage | Binding fold planner; tests with known fold boundaries |
| Monte Carlo misinterpreted as edge proof | Verdict gates + report copy; shuffle documented as order-risk |
| Long experiment runtime | Resume registry; skip completed child runs |
| Scope creep into PBO/CSCV | Explicit out-of-scope in ADR-0019 and Wave 0 |
| Duplicate simulation logic | Reuse `run_strategy_research` only |

---

## 10. Dependencies

**Required on main:**

- ADR-0016 Strategy Research, ADR-0017 dashboard pattern, ADR-0018 continuous OHLCV
- Persisted `strategy_research` envelope (manifest, trades, equity)
- Canonical strategy model (`build_canonical_strategy_model`)

**Not required:**

- Phase 8 execution / replay
- Phase 4B orderflow
- Distributed job queue

---

## 11. Quality gates

Every implementation PR must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 12. Post-sprint direction

After Sprint 016 merges to `main`:

- Paper execution readiness checklist (Phase 8),
- PBO / CSCV / deflated Sharpe increment (separate ADR),
- Robustness on multi-year NQ continuous at scale,
- optional dashboard Phase B for large MC samples.

See `ROADMAP.md` §11 and `CURRENT_STATUS.md`.
