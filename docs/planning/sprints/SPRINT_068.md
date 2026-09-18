# Sprint 068: Strategy Research Manifest Assumptions, Drawdown Episodes and Exposure (Phase 18, 18A Milestone 1a)

Status: **Open** — maintainer authorized opening this sprint 2026-09-18.
Goal: Implement Phase 18 18A's Milestone 1a — the two low-risk, no-new-
identity artifacts identified in Wave 0 (D-P18-05): persist real
`SimulationAssumptions` field values in the Strategy Research manifest
(replacing the fingerprint-only status quo), and add two new per-run
analytics artifacts computed purely post-hoc from already-persisted
`equity.parquet`/`trades.parquet` — `drawdown_episodes.parquet` and
`exposure.parquet`. Backfill all three for the 3 existing persisted runs.

Sources:

- `docs/product/PRD-dashboard-strategy-research-evidence.md` (APPROVED 2026-09-18)
- `docs/planning/roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md`
- `docs/planning/roadmap/PHASE_18_WAVE0_DECISIONS.md` — D-P18-01 (assumptions
  backfill, resolved: all 3 runs match `SimulationAssumptions` defaults,
  fingerprint `1aa6ee647c5cc636` verified), D-P18-05 (4-sprint split; this
  is Sprint N / Milestone 1a) — both ACCEPTED (maintainer, 2026-09-18)
- `src/trading_framework/research/simulation/assumptions.py` (`SimulationAssumptions`, `FillPolicy`)
- `src/trading_framework/research/datasets/strategy_research.py` (`StrategyResearchRunManifest`, `StrategyResearchDatasetRepository`, `validate_equity_dataframe`/`validate_trades_dataframe`)
- `src/trading_framework/application/strategy_research/run_strategy_research.py` (manifest construction, `write_summary_metrics` call site — the pattern this sprint's two new writers follow)
- `src/trading_framework/research/analytics/strategy_summary_metrics_export.py` (precedent: a small, pure `overview_kpis_to_summary_metrics_frame`-style serializer)
- `src/trading_framework/infrastructure/storage/paths.py` (`strategy_research_analytics_dir`, `strategy_research_summary_metrics_path` — the path-helper pattern this sprint's two new paths follow)
- `user_data/workspace/research/strategy_research/runs/*/{manifest.json,equity.parquet,trades.parquet}` (3 existing runs to backfill)

Architecture triage: **complete, no open design points.** D-P18-01
resolved the only substantive question (assumptions recoverability) before
this sprint opened. `drawdown_episodes` and `exposure`'s exact formulas
were already decided directly with the maintainer during PRD discovery
(peak-to-recovery episode definition, no threshold; notional-exposure /
concurrent-equity ratio) — restated in Scope below, not re-litigated.

## Scope

In scope:

- **T001 — Persist real `SimulationAssumptions` values in the manifest.**
  `StrategyResearchRunManifest` gains 5 new fields:
  `fill_policy_entry: str`, `fill_policy_exit: str`,
  `slippage_bps: str` (Decimal-as-string, matching this manifest's existing
  convention for exact-precision values), `commission_per_side: str`,
  `initial_capital: str`. `run_strategy_research.py` populates them from
  `request.assumptions` at construction time, alongside the existing
  fingerprint (kept, unchanged, for identity/dedup). Backfill: write these
  5 fields into all 3 existing runs' `manifest.json` using the verified
  default values from D-P18-01.
- **T002 — `analytics/drawdown_episodes.parquet`.** One row per episode,
  computed from `equity.parquet`'s `equity` column ordered by
  `observed_at`. Episode = from one new running-maximum equity value to the
  next new running-maximum (recovery). Fields: `episode_id` (0-indexed per
  run), `peak_at`, `peak_equity`, `trough_at`, `trough_equity`,
  `depth_pct` (`min(equity)/peak_equity - 1` over the episode, negative or
  zero), `duration_bars` (peak→trough, in observation rows),
  `recovery_bars` (trough→peak, `null` if the run ends before a new peak —
  an explicit "not yet recovered" episode). No minimum-depth threshold. A
  run whose equity never dips below its running peak produces zero rows,
  not an error. Backfilled for all 3 existing runs.
- **T003 — `analytics/exposure.parquet`.** One row per equity observation
  (same grid as `equity.parquet`), computed from `trades.parquet` (which
  positions are open at that timestamp, by `entry_fill_at`/`exit_fill_at`)
  joined against `equity.parquet`. Fields: `observed_at`,
  `notional_exposure` (`sum(quantity × entry_fill_price)` over trades open
  at that bar), `exposure_ratio` (`notional_exposure / equity` at the same
  bar; `null` when `equity` is zero or negative rather than a divide-by-
  zero artifact). Backfilled for all 3 existing runs.
- Both new writers follow the existing `write_summary_metrics` method
  pattern on `StrategyResearchDatasetRepository` (validate shape, require
  the run directory to already exist, write under `analytics/`) — new
  methods `write_drawdown_episodes` and `write_exposure`, new path helpers
  `strategy_research_drawdown_episodes_path` /
  `strategy_research_exposure_path` in `infrastructure/storage/paths.py`.
- `run_strategy_research.py`'s persist step computes and writes both new
  artifacts alongside the existing `summary_metrics.parquet` write, for
  every future run — not only as a one-time backfill script.
- A small, standalone backfill script
  (`scripts/strategy_research/backfill_run_analytics.py`) that: (a) writes
  the 5 new manifest fields into an existing run's `manifest.json` given
  known values, and (b) computes and writes `drawdown_episodes.parquet`/
  `exposure.parquet` for an existing run from its already-persisted
  `equity.parquet`/`trades.parquet` — run once against each of the 3
  existing runs as this sprint's backfill step, and reusable for any
  future backfill need.

Out of scope (explicitly, per D-P18-05's sprint split):

- **`strategy_source_ref` and `context_expectancy.parquet`** — Milestone
  1b, Sprint N+1. Not touched here.
- **Any publication-layer or dashboard change** — Milestone 2a/2b, Sprints
  N+2/N+3. This sprint only produces new research-layer artifacts; nothing
  in `apps/dashboard` reads them yet.
- **Any change to `BarSequentialSimulator`'s simulation logic** — additive
  manifest/analytics persistence only, per the PRD's explicit non-goal.

## Decisions

Binding detail and rationale: [`PHASE_18_WAVE0_DECISIONS.md`](../roadmap/PHASE_18_WAVE0_DECISIONS.md)
D-P18-01 and D-P18-05, both ACCEPTED (maintainer, 2026-09-18). The
drawdown-episode definition and exposure-ratio formula were decided
directly with the maintainer during PRD discovery (see the PRD's Goals,
Milestone 1) and are restated, not reopened, in this sprint's Scope.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `StrategyResearchRunManifest` persists 5 real `SimulationAssumptions` fields (fingerprint kept unchanged); `run_strategy_research.py` populates them; `from_dict`/`to_dict` round-trip, tolerant of legacy manifests missing the fields; backfill script updates all 3 existing runs' `manifest.json` with verified default values (D-P18-01) | None | `research/datasets/strategy_research.py`, `application/strategy_research/run_strategy_research.py` | standard | Done | — |
| T002 | `drawdown_episodes.parquet` writer + computation (peak-to-recovery, no threshold, `recovery_bars=null` for an unresolved episode at run end); wired into `run_strategy_research.py`'s persist step; backfilled for all 3 existing runs | T001 (shares the backfill script) | `research/analytics/`, `research/datasets/strategy_research.py` | standard | Done | — |
| T003 | `exposure.parquet` writer + computation (notional exposure from open trades joined to the equity grid; `exposure_ratio` null-safe on non-positive equity); wired into `run_strategy_research.py`'s persist step; backfilled for all 3 existing runs | T001 (shares the backfill script) | `research/analytics/`, `research/datasets/strategy_research.py` | standard | Done | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; no project-specific deviation.

```text
main
  └── sprint/dashboard-strategy-research-evidence-m1a
        ├── feat/manifest-assumptions-persistence  (T001)
        ├── feat/drawdown-episodes                 (T002)
        └── feat/exposure-ratio                    (T003)
```

- Integration branch: `sprint/dashboard-strategy-research-evidence-m1a`,
  cut from `main` at its then-current head after approval.
- Working branches: `<prefix>/<descriptive-slug>`, cut from the sprint
  branch's current head.
- PR base is always the sprint branch. One final integration PR to `main`
  at sprint close, after review and CI.
- Squash merge for working PRs.
- T002 and T003 may proceed in parallel once T001 lands (both need the
  backfill script T001 introduces, but not each other's artifact).

## Acceptance criteria

- All 3 existing runs' `manifest.json` files carry the 5 new
  `SimulationAssumptions` fields with the exact D-P18-01-verified default
  values; the existing `simulation_assumptions_fingerprint` field is
  unchanged.
- All 3 existing runs have `analytics/drawdown_episodes.parquet` and
  `analytics/exposure.parquet`, each schema-valid and non-corrupt.
- A new Strategy Research run (via `run_strategy_research.py`) produces
  both new artifacts automatically, without a separate backfill step.
- `recovery_bars` is `null` (not a fabricated large number or zero) for any
  episode still open at a run's last observation.
- `exposure_ratio` is `null` (not `inf`/`NaN` leaking into the Parquet
  file) for any bar with zero or negative equity.
- The full `research`/`application` test suite stays green.
- `ruff check`, `ruff format --check` and `mypy` stay clean on every PR.

## Descope order

If the sprint must shrink, drop in this order — never the reverse:

```text
1. T003 (exposure) — independently useful, not blocking T002 or the dashboard's later equity/drawdown view.
```

T001 and T002 are the higher-value slices (T001 unblocks D-P18-05's
Sprint N+1 identity work too, via the shared manifest-editing pattern; T002
is the PRD's single most-requested new artifact) and should not be dropped.

## Closeout

**Status: DONE.** All 3 tasks (T001-T003) implemented and verified locally
on `main`'s working tree; not yet committed (see note below).

**Implementation**:

- `src/trading_framework/research/datasets/strategy_research.py` —
  `StrategyResearchRunManifest` gained `fill_policy_entry`,
  `fill_policy_exit`, `slippage_bps`, `commission_per_side`,
  `initial_capital` (all `str`, defaulted to `SimulationAssumptions`'s own
  dataclass defaults so pre-Sprint-068 call sites and manifests still
  round-trip); `StrategyResearchDatasetRepository` gained
  `write_drawdown_episodes`/`write_exposure`, mirroring
  `write_summary_metrics`'s existing shape/validation pattern.
- `src/trading_framework/infrastructure/storage/paths.py` — added
  `strategy_research_drawdown_episodes_path`/`strategy_research_exposure_path`.
- `src/trading_framework/research/analytics/drawdown_episodes.py` (new) —
  `compute_drawdown_episodes`: peak-to-recovery episode extraction, O(n)
  single pass, no minimum-depth threshold, `recovery_bars=null` for an
  episode still open at the run's last observation.
- `src/trading_framework/research/analytics/exposure.py` (new) —
  `compute_exposure`: event-sweep (`join_asof` on a sorted entry/exit
  notional-delta cumulative sum) against the equity grid, `exposure_ratio`
  `null`-safe on non-positive equity.
- `src/trading_framework/application/strategy_research/run_strategy_research.py`
  — persist step now also computes and writes both new artifacts for every
  future run, and the manifest is now built with the 5 real assumption
  values.
- `scripts/strategy_research/backfill_run_analytics.py` (new) — one-time
  backfill tool; run against all 3 existing runs during this sprint.

**Backfill result** (all 3 runs, `user_data/workspace/research/strategy_research/runs/`):
manifest `fill_policy_entry`/`fill_policy_exit`/`slippage_bps`/
`commission_per_side`/`initial_capital` written per D-P18-01's verified
defaults; `analytics/drawdown_episodes.parquet` and `analytics/exposure.parquet`
written for all 3. Spot-checked: `eb80de6c9a6e3ab1` (canonical example,
2025 data) — 10 episodes, 1 unresolved at run end; the two `s058_t005_*`
runs — 39 and 37 episodes respectively, including one episode with
`depth_pct` below `-1.0` (equity legitimately went negative in these two
runs' underlying simulation, confirmed directly against `equity.parquet`
— not a computation bug).

**Tests**: `tests/unit/research/analytics/test_drawdown_episodes.py` (new,
6 cases), `tests/unit/research/analytics/test_exposure.py` (new, 5 cases),
`tests/unit/research/datasets/test_strategy_research_repository.py`
(+3 cases: manifest round-trip with the new fields, `from_dict` defaulting
when they're absent, the two new writer methods),
`tests/integration/test_s013_run_strategy_research.py` (extended: asserts
the new manifest fields and both new artifacts exist after a real,
persisted run). Full suite: **2047 passed, 26 skipped** (pre-existing
optional-dependency skips only — `sklearn`/`torch`/`lightgbm`/`xgboost`
not installed). `ruff check`, `ruff format --check`, `mypy` clean on every
changed file.

**Acceptance criteria**: all met — see Tests above for the automated ones;
the 3 backfilled runs and their spot-checked values (above) satisfy the
manual acceptance criteria.

**Git**: docs (this record, the PRD, Wave 0 decisions, roadmap corrections)
merged to `main` via [#572](https://github.com/folg-code/research-trading-framework/pull/572).
Implementation (T001-T003, bundled in one PR since the tasks share
`StrategyResearchDatasetRepository` and `run_strategy_research.py`'s
persist step) merged into `sprint/dashboard-strategy-research-evidence-m1a`
via [#573](https://github.com/folg-code/research-trading-framework/pull/573).
Final integration PR to `main`:
[#574](https://github.com/folg-code/research-trading-framework/pull/574).

**Remaining work**: Sprint N+1 (Milestone 1b — `strategy_source_ref` +
`context_expectancy.parquet`, per D-P18-02) is next per D-P18-05's
4-sprint plan.
