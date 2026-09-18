# Sprint 069: Strategy Source Reference and Context Expectancy (Phase 18, 18A Milestone 1b)

Status: **Open** — maintainer authorized opening this sprint 2026-09-18.
Goal: Implement Phase 18 18A's Milestone 1b — the one genuinely novel
mechanism identified in Wave 0 (D-P18-05): a `strategy_source_ref` manifest
field that makes a run's Market Model builder generically resolvable, and
`context_expectancy.parquet`, computed by recomputing Market Analysis
components over the run's own dataset and joining STATE-kind context to
trades. Backfilled for all 3 existing runs.

Sources:

- `docs/product/PRD-dashboard-strategy-research-evidence.md` (APPROVED 2026-09-18)
- `docs/planning/roadmap/PHASE_18_WAVE0_DECISIONS.md` — D-P18-02
  (context-expectancy mechanism), D-P18-04 (eligibility thresholds),
  D-P18-05 (4-sprint split; this is Sprint N+1 / Milestone 1b) — all
  ACCEPTED (maintainer, 2026-09-18)
- `docs/planning/sprints/SPRINT_068.md` — Milestone 1a, this sprint's
  prerequisite (manifest assumptions fields, established the
  `write_*`/backfill-script pattern this sprint reuses)
- `src/trading_framework/market_model/results.py` (`market_model_result_dataframe`
  — confirmed boolean-only, the reason this can't be pure post-hoc reading)
- `src/trading_framework/market_analysis/models/kind.py` (`ComponentKind` —
  `STATE` is the actual categorical-context discriminator, not dtype;
  every component's `OutputSchema` field is `float64` regardless of kind)
- `src/trading_framework/model_expression/planning.py`
  (`collect_model_dependencies`, `build_analysis_frame_request` — already
  used by `evaluate_models`, reused here rather than reinvented)
- `src/trading_framework/application/market_analysis/run_analysis.py`
  (`run_analysis`/`RunAnalysisRequest` — the same Market Analysis
  computation pipeline every model evaluation already goes through)
- `src/trading_framework/strategy/canonical_examples.py`,
  `scripts/strategy_research/_btc_rsi_relative_volatility.py` (the two
  builder sources for the 3 existing runs' Market Models)

Architecture triage: **complete, resolved directly during this sprint's
implementation** (documented here rather than a separate Wave 0 pass,
since D-P18-02 already set the mechanism's shape and only its concrete
resolution — which frame column carries which component, how to detect
"categorical" — needed confirming against real code):

- **STATE is a `ComponentKind`, not a dtype.** Every component's
  `OutputSchema` field is declared `float64` regardless of whether the
  component is `FEATURE`, `STRUCTURE` or `STATE` — there is no dtype-level
  signal to filter on. The real discriminator is
  `registry.get_component(component_id).kind is ComponentKind.STATE`.
- **The live-run path needs no extra computation.** `run_strategy_research.py`
  already assembles an `AnalysisFrame` (`frame = eval_result.analysis.frame`)
  covering every model dependency's aliased output column, via the same
  `collect_model_dependencies`/`build_analysis_frame_request` pair
  `evaluate_models` already uses. `context_expectancy` for a *new* run
  reuses that frame directly — no second computation pass, no
  `strategy_source_ref` resolution needed (the `StrategyModelDefinition`
  is already an in-memory object). `strategy_source_ref` is needed only to
  recompute a *past* run's Market Model when its original in-memory object
  is gone.
- **Real data confirms the "riskiest assumption."** The canonical
  example's Market Model (`volatility.state == HIGH`) has a genuine
  STATE-kind dependency; backfilling it produced 2 real label groups
  (7,706 trades in one, correctly ineligible in the other at 4 trades).
  Both `s058_t005_*` runs' Market Model (`volatility.relative_volatility_ratio
  > threshold`) depends only on a `FEATURE`-kind component — their
  `context_expectancy.parquet` is correctly empty. This is exactly the
  "some runs will have nothing to show" outcome the PRD's Riskiest
  assumption anticipated, now confirmed rather than hypothetical.

## Scope

In scope:

- **T001 — `strategy_source_ref` manifest field.** `StrategyResearchRunManifest`
  gains an optional `strategy_source_ref: str | None` (dotted
  `module:callable` path). `RunStrategyResearchRequest` gains an optional
  `strategy_source_ref: str | None` field the caller may supply; when
  given, it is written into the manifest. `StrategyResearchDatasetRepository`
  gains `update_strategy_source_ref` for backfilling an existing run.
- **T002 — `analytics/context_expectancy.parquet` (live-run path).** New
  `research/analytics/context_expectancy.py`:
  - `state_context_aliases`: maps a frame column alias to its owning
    component id, filtered to (a) components the Market Model's own
    expression references and (b) `ComponentKind.STATE` only.
  - `compute_context_expectancy`: joins trades to the frame at
    `entry_signal_at`, groups by (component, label), computes
    `sample_count`, `missing_context_count`, `net_pnl_mean`,
    `net_pnl_median`, `win_rate`, gated by `eligible`
    (`sample_count >= min_sample_size`, default 5) and `interpretable`
    (`sample_count >= interpretation_min_sample_size`, default 30) per
    D-P18-04 — both explicit, calibratable parameters, not literals.
    A run with no qualifying component or no trades produces an empty
    table, not an error.
  - `run_strategy_research.py`'s persist step computes and writes this for
    every future run, reusing the already-assembled `frame` in memory —
    no second Market Analysis computation pass.
- **T003 — Legacy backfill (recompute path).**
  `scripts/strategy_research/backfill_context_expectancy.py`: given a
  run id and a `strategy_source_ref`, resolves the builder, recomputes
  Market Analysis components over the run's own published dataset via
  `run_analysis` (deterministic, read-only — not a simulator rerun),
  computes `context_expectancy`, writes it, and backfills
  `strategy_source_ref` onto the manifest. Run once against all 3
  existing runs during this sprint.

Out of scope (per D-P18-05):

- **Any publication-layer or dashboard change** — Milestone 2a/2b,
  Sprints N+2/N+3. Not touched here.
- **A market-model-id registry** for generic id-to-builder resolution —
  D-P18-02 explicitly declined this; `strategy_source_ref` is the
  narrower, sufficient fix.
- **Any change to `BarSequentialSimulator`** — the recompute path uses
  only the Market Analysis computation pipeline, never the simulator.

## Decisions

Binding detail and rationale:
[`PHASE_18_WAVE0_DECISIONS.md`](../roadmap/PHASE_18_WAVE0_DECISIONS.md)
D-P18-02, D-P18-04, D-P18-05, all ACCEPTED (maintainer, 2026-09-18). The
`ComponentKind.STATE`-not-dtype discriminator and the live-run-reuses-
existing-frame simplification are this sprint's own implementer-level
findings (see Architecture triage above) — consistent with, not
contradicting, D-P18-02's mechanism.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `strategy_source_ref` on manifest + request, round-trips, `update_strategy_source_ref` repository method | Sprint 068's manifest-editing pattern | `research/datasets/strategy_research.py`, `application/strategy_research/run_strategy_research.py` | standard | Done | — |
| T002 | `context_expectancy.py` (`state_context_aliases`, `compute_context_expectancy`); wired into `run_strategy_research.py`'s persist step reusing the in-memory frame; `write_context_expectancy` repository method | T001 (shares manifest pattern, not a hard dependency) | `research/analytics/` | high | Done | — |
| T003 | `backfill_context_expectancy.py`; run against all 3 existing runs | T001, T002 | `scripts/strategy_research/` | standard | Done | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprint 068's precedent —
bundled in one PR since T001-T003 share `StrategyResearchDatasetRepository`
and `run_strategy_research.py`'s persist step.

```text
main
  └── sprint/dashboard-strategy-research-evidence-m1b
        └── feat/strategy-source-ref-context-expectancy  (T001-T003)
```

- Integration branch: `sprint/dashboard-strategy-research-evidence-m1b`,
  cut from `main` at its then-current head after approval.
- PR base is the sprint branch; one final integration PR to `main` at
  sprint close.
- Squash merge.

## Acceptance criteria

- `strategy_source_ref` round-trips through `to_dict`/`from_dict`,
  defaults to `None` when absent (no legacy-manifest break).
- `context_expectancy.parquet` exists for all 3 existing runs; the
  canonical example run's is non-empty (2 label groups, one eligible, one
  correctly not); both `s058_t005_*` runs' are correctly empty (no
  `STATE`-kind dependency).
- A group below `min_sample_size` has `eligible=False` and null metric
  fields, never a fabricated value.
- No new run of `BarSequentialSimulator` occurs anywhere in this sprint's
  code paths — verified by code review, not just by absence of a failing
  test.
- Full suite green; `ruff check`, `ruff format --check`, `mypy` clean.

## Descope order

If the sprint must shrink, drop in this order — never the reverse:

```text
1. T003 (legacy backfill) — the live-run path (T001+T002) is the higher-value slice; backfilling 3 known runs can follow later without blocking future runs from getting real data.
```

## Closeout

**Status: DONE.** All 3 tasks (T001-T003) implemented and verified.

**Implementation**:

- `src/trading_framework/research/datasets/strategy_research.py` —
  `StrategyResearchRunManifest.strategy_source_ref: str | None = None`;
  `StrategyResearchDatasetRepository` gained `write_context_expectancy`
  and `update_strategy_source_ref`.
- `src/trading_framework/application/strategy_research/run_strategy_research.py`
  — `RunStrategyResearchRequest.strategy_source_ref: str | None = None`;
  persist step now also computes and writes `context_expectancy`, reusing
  the already-assembled `AnalysisFrame` (no second computation pass).
- `src/trading_framework/research/analytics/context_expectancy.py` (new) —
  `state_context_aliases` (the `ComponentKind.STATE`-not-dtype filter,
  scoped to components the Market Model's own expression references) and
  `compute_context_expectancy` (join, group, two-tier eligibility per
  D-P18-04: `min_sample_size=5`, `interpretation_min_sample_size=30`).
- `src/trading_framework/infrastructure/storage/paths.py` — added
  `strategy_research_context_expectancy_path`.
- `scripts/strategy_research/backfill_context_expectancy.py` (new) —
  resolves a `module:callable` builder, recomputes Market Analysis
  components via `run_analysis` (not a simulator rerun), writes
  `context_expectancy` and backfills `strategy_source_ref`.

**Backfill result** (all 3 runs,
`user_data/workspace/research/strategy_research/runs/`):

- `eb80de6c9a6e3ab1` (canonical example) →
  `strategy_source_ref = trading_framework.strategy.canonical_examples:build_canonical_strategy_model`.
  `context_expectancy`: 2 rows — `volatility.state` label `"0.0"`
  (4 trades, `eligible=False`), label `"1.0"` (7,706 trades,
  `eligible=True`, `interpretable=True`, `net_pnl_mean=-1.53`,
  `win_rate=0.4875`).
- `4dbf98822e6ae591`, `8d050f623a034a58` (both `s058_t005_rsi_relative_volatility*`)
  → `strategy_source_ref = scripts.strategy_research._btc_rsi_relative_volatility:build_strategy`.
  `context_expectancy`: 0 rows each — their Market Model's
  `volatility.relative_volatility_ratio` dependency is `FEATURE`-kind, not
  `STATE`-kind, per direct registry lookup. Correctly empty, not a bug —
  confirms the PRD's Riskiest assumption was a real, now-observed
  possibility, not just a hypothetical.

**Tests**: `tests/unit/research/analytics/test_context_expectancy.py`
(new, 6 cases — alias resolution, market-model-scoping, empty-when-no-
state-component, empty-when-no-trades, label grouping with eligibility
tiers, missing-context counting), `tests/unit/research/datasets/test_strategy_research_repository.py`
(+4 cases: `strategy_source_ref` round-trip and default, both new
repository methods), `tests/integration/test_s013_run_strategy_research.py`
(extended: asserts `context_expectancy.parquet` exists after a real
persisted run — correctly empty for this fixture's zero-trade case, with
the non-empty happy path covered by the unit tests instead). Full suite:
**2057 passed, 26 skipped** (pre-existing optional-dependency skips only).
`ruff check`, `ruff format --check`, `mypy` clean on every changed file.

**Acceptance criteria**: all met — see Tests and Backfill result above.

**Remaining work**: Sprint N+2 (Milestone 2a — generic Strategy Research
publisher, per D-P18-03) is next per D-P18-05's 4-sprint plan.
