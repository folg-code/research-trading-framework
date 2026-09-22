# Sprint 073: Signal Research Milestone 1 Remaining Artifacts (Phase 18, 18B)

Status: **Open** — maintainer authorized opening this sprint 2026-09-22.
Goal: Implement Milestone 1's remaining new artifacts, deferred out of
Sprint 072 — `mfe_mae_pairs`, `adjusted_forward_drift`, `context_timeline`,
`context_persistence` — per D-P18B-03/04. Wire them into the publication
layer and regenerate the committed `projection.json` for real, against the
6 real Signal Research runs.

Sources:

- `docs/product/PRD-dashboard-signal-research-evidence.md` (APPROVED 2026-09-18)
- `docs/planning/roadmap/PHASE_18B_WAVE0_DECISIONS.md` — D-P18B-03
  (Bayesian-average shrinkage, `k=100`, for `adjusted_forward_drift`),
  D-P18B-04 (`state_context_aliases` reuse for `context_timeline`/
  `context_persistence`), both ACCEPTED (maintainer, 2026-09-22)
- `docs/planning/sprints/SPRINT_072.md` — Milestone 1's prior sprint;
  explicitly deferred these four artifacts to "Sprint N+1" (this sprint)
- `src/trading_framework/research/analytics/context_expectancy.py`
  (18A precedent this sprint extracts `state_context_aliases` out of,
  D-P18-02's mechanism) and `drawdown_episodes.py` (run-length-encoding
  precedent for `context_persistence`)

Architecture triage: **`market_model_result_dataframe` persists only a
single boolean gate column** — no intermediate Market Analysis component
value survives Signal Research's own persistence step. Publishing
`context_timeline`/`context_persistence` therefore requires
*recomputing* Market Analysis over the run's own published dataset via
`run_analysis`, the same approach 18A's `context_expectancy` already
uses (D-P18-02) — not reading any existing persisted field. To avoid
duplicating that mechanism, `state_context_aliases` is extracted out of
`context_expectancy.py` into a new, workflow-agnostic
`market_model_context.py` module both Strategy's and Signal's analytics
import identically.

## Scope

In scope:

- **T001 — `adjusted_forward_drift`.** New
  `src/trading_framework/research/analytics/adjusted_drift.py`:
  sample-size-weighted (empirical-Bayes) shrinkage of each
  `grouped_summaries` group's forward-return mean toward the run's own
  `summary_metrics` global mean at the same horizon, `k=100`
  (`DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE`, D-P18B-03). Pure post-hoc
  computation over two already-persisted tables — no analysis-engine
  rerun.
- **T002 — `context_timeline` / `context_persistence`.** New
  `src/trading_framework/research/analytics/market_model_context.py`
  (extracted `state_context_aliases`, reused by both workflows) and
  `context_timeline.py`: the raw dated STATE-context series and its
  run-length encoding, via `run_analysis` recomputation (D-P18B-04).
- **T003 — `mfe_mae_pairs`.** No new research-layer code — a bounded,
  publication-time-only copy of `(horizon_bars, forward_return, mfe,
  mae)` straight from the run's already-persisted raw `outcomes.parquet`
  (sibling to `analytics/`, not inside it). No new computation, per the
  PRD's Milestone 1 Goals.
- **T004 — Backfill the 4 new tables against the 6 real runs.** New
  `scripts/signal_research/backfill_adjusted_drift.py` and
  `backfill_context_timeline.py` (one-time tools, mirroring Sprint
  068/069's Strategy Research backfill precedent). `mfe_mae_pairs`
  needs no backfill script — it is derived at publication time.
- **T005 — Wire into the publication layer; regenerate the committed
  `projection.json`.** `apps/dashboard/src/dashboard_app/publication/evidence.py`
  (`_SIGNAL_TABLES`, bounded read for `context_timeline`, new
  `outcomes.parquet`-sourced path for `mfe_mae_pairs`) and
  `sanitizers.py` (`_SIGNAL_EVIDENCE_TABLE_COLUMNS` allowlists for all
  four tables).

Out of scope (per the PRD and Wave 0):

- **18B's Milestone 2 (dashboard UI consuming these tables)** — later,
  after Milestone 1 fully completes, per the PRD's hard sequencing gate.
  This sprint's tables are published but not yet rendered on any page.
- **Authoring a `--definition` file** for the 3 runs still missing
  `grouped_summaries` (deferred in Sprint 072, D-P18B-02) — unchanged;
  those 3 runs' `adjusted_forward_drift` stays honestly empty.
- **The one Signal Research run with no `market_model_ids`
  (`e05c1fe5566e6462`)** — has no Market Model to derive
  `context_timeline`/`context_persistence` from; intentionally skipped
  for those two tables, not fabricated.

## Decisions

Binding detail and rationale:
[`PHASE_18B_WAVE0_DECISIONS.md`](../roadmap/PHASE_18B_WAVE0_DECISIONS.md)
D-P18B-03/04, both ACCEPTED (maintainer, 2026-09-22).

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `adjusted_forward_drift` computed via shrinkage, tested | None | `src/trading_framework/research/analytics/adjusted_drift.py` | standard | Done | — |
| T002 | `context_timeline`/`context_persistence` computed via Market Analysis recomputation, tested | None | `src/trading_framework/research/analytics/{market_model_context,context_timeline}.py` | standard | Done | — |
| T003 | `mfe_mae_pairs` published from raw `outcomes.parquet`, bounded | None | `apps/dashboard/src/dashboard_app/publication/evidence.py` | standard | Done | — |
| T004 | All 4 tables backfilled against the 6 real runs | T001, T002 | (workspace data only, no code) | standard | Done | — |
| T005 | Publication layer wired; committed `projection.json` regenerated for real | T001-T004 | `apps/dashboard/src/dashboard_app/publication/`, `apps/dashboard/publication_data/` | standard | Done | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprints 068-072's
precedent — bundled in one PR (T001-T005 are one coherent feature).

```text
main
  └── sprint/dashboard-signal-research-evidence-m1b
        └── feat/signal-research-remaining-artifacts  (T001-T005)
```

## Acceptance criteria

- `adjusted_forward_drift`, `context_timeline`, `context_persistence`,
  `mfe_mae_pairs` all publish for the 5 real runs with a Market Model
  (6th run intentionally excluded from the two context tables only).
- `context_timeline` is bounded the same deterministic,
  endpoint-preserving way `walk_forward_equity` already is (real runs
  can exceed 300K rows).
- `mfe_mae_pairs` is sourced from raw `outcomes.parquet`, not any
  `analytics/` file — no new computation.
- Sanitizer allowlists drop every field not explicitly listed for each
  new table (verified by test, mirroring the existing
  `test_evidence_sanitizers_drop_unknown_nested_fields` pattern).
- `pages/4_Market_and_Signal_Research.py` still renders correctly
  against the regenerated bundle, verified in a running dashboard.
- Unit, research/analytics, and dashboard suites green; `ruff check`,
  `ruff format --check`, `mypy` (full project-configured file set)
  clean.

## Closeout

**Status: DONE.** All 5 tasks (T001-T005) implemented and verified.

**Implementation**:

- `src/trading_framework/research/analytics/market_model_context.py`
  (NEW) — `state_context_aliases` extracted from `context_expectancy.py`
  so both Strategy's and Signal's analytics reuse the identical
  mechanism (D-P18-02/D-P18B-04).
- `src/trading_framework/research/analytics/context_expectancy.py` —
  now imports `state_context_aliases` instead of defining it locally;
  unused imports removed.
- `src/trading_framework/research/analytics/adjusted_drift.py` (NEW) —
  `compute_adjusted_forward_drift`, `k=100` shrinkage
  (`DEFAULT_SHRINKAGE_PRIOR_STRENGTH`, reusing
  `DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE`'s value). Empty output, not
  an error, when either input table is empty or the join is empty.
- `src/trading_framework/research/analytics/context_timeline.py` (NEW) —
  `compute_context_timeline` (raw dated series) and
  `compute_context_persistence` (run-length encoding, open run at
  series end gets `end_at = null`).
- `scripts/signal_research/backfill_adjusted_drift.py`,
  `backfill_context_timeline.py` (NEW) — one-time backfill tools, run
  against all 6 real runs in `user_data/research/market_research/runs/`
  (gitignored).
- `apps/dashboard/src/dashboard_app/publication/evidence.py` —
  `_SIGNAL_TABLES` gained `adjusted_forward_drift`, `context_timeline`,
  `context_persistence`; `_load_tables`'s bounding logic generalized
  from a single `if name == "walk_forward_equity"` check to a
  `_BOUNDED_TABLE_MAX_POINTS` name→limit mapping covering both
  `walk_forward_equity` and the new `context_timeline`
  (`_CONTEXT_TIMELINE_MAX_POINTS = 2_000`); new `_load_mfe_mae_pairs`
  reads and bounds the run's raw `outcomes.parquet` and is spliced into
  `_load_signal_run`'s `tables` dict alongside the `analytics/`-sourced
  ones.
- `apps/dashboard/src/dashboard_app/publication/sanitizers.py` —
  `_SIGNAL_EVIDENCE_TABLE_COLUMNS` gained allowlists for all 4 new
  tables.
- `apps/dashboard/publication_data/projection.json` — regenerated for
  real via `scripts/dashboard/generate_public_projection.py`: 32
  artifacts (unchanged count from Sprint 072 — no new runs, only new
  tables per existing `signal_research_evidence` artifacts), 26
  projected inputs, 0 skipped. All 6 real runs now publish
  `adjusted_forward_drift` and `mfe_mae_pairs`; 5 of 6 also publish
  `context_timeline`/`context_persistence` (the 6th,
  `e05c1fe5566e6462`, has no `market_model_ids` and is correctly
  excluded from those two, not fabricated).
- `tests/unit/research/analytics/test_adjusted_drift.py`,
  `test_context_timeline.py` (NEW) — 5 tests each, covering empty
  inputs, shrinkage behavior at large/small sample sizes, and
  run-length encoding including the still-open final run.
- `apps/dashboard/tests/test_projected_research_evidence.py` — new
  `test_discovery_projects_new_signal_tables_bounded_and_sourced_from_outcomes`,
  covering discovery, bounding (`context_timeline` from 3,000 rows down
  to 2,000), and the `mfe_mae_pairs`/`outcomes.parquet` sourcing path.

**Backfill result** (all outside git, `user_data/` is gitignored): all 6
real Signal Research runs backfilled with `adjusted_forward_drift` (3 of
6 honestly empty — no `grouped_summaries`, per Sprint 072's D-P18B-02
deferral); 5 of 6 backfilled with `context_timeline`/`context_persistence`
(`a6dff1e5365fe839`: 334,456 timeline rows / 6,135 persistence episodes;
`25ca54931e1f16e6`: 2,470 / 82; the 6th run, `e05c1fe5566e6462`,
intentionally skipped — no `market_model_ids`).

**Manual verification**: started the dashboard against the regenerated
bundle and opened `4_Market_and_Signal_Research.py`. Page renders with
no exceptions and no server errors; Summary metrics, Forward-return
distributions, Conditional comparison, and Metric histograms sections
all display correctly (Milestone 2's UI for the 4 new tables is out of
scope for this sprint, so they are published but not yet surfaced on the
page).

**Tests**: research/analytics + dashboard suites both green — unit
suite **2067 passed**, dashboard suite **298 passed** (9 in
`test_projected_research_evidence.py`, up from 8 — one new test added).
`ruff check`, `ruff format --check`, `mypy` (full project-configured
file set, including the two new backfill scripts) all clean.

**Acceptance criteria**: all met — see Manual verification and Tests
above.

**Remaining work**: Milestone 2 (dashboard UI consuming all 10 Signal
Research tables, including these 4 new ones) is next, per the PRD's
sequencing gate.
