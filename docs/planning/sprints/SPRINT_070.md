# Sprint 070: Generic Strategy Research Publisher (Phase 18, 18A Milestone 2a)

Status: **Open** — maintainer authorized opening this sprint 2026-09-18.
Goal: Implement Phase 18 18A's Milestone 2a — the generic Strategy Research
evidence publisher identified in Wave 0 (D-P18-03), closing the gap where
today's richer `strategy_research_run_summary` role is produced by a
one-off script hardcoding 2 of the 3 persisted runs. Regenerate the
committed `projection.json` for real.

Sources:

- `docs/product/PRD-dashboard-strategy-research-evidence.md` (APPROVED 2026-09-18)
- `docs/planning/roadmap/PHASE_18_WAVE0_DECISIONS.md` — D-P18-03 (generic
  publisher), D-P18-05 (4-sprint split; this is Sprint N+2 / Milestone 2a)
  — both ACCEPTED (maintainer, 2026-09-18)
- `docs/planning/sprints/SPRINT_068.md`, `SPRINT_069.md` — Milestones 1a/1b,
  this sprint's data prerequisite (the 3 runs' `summary_metrics`,
  `equity`/`trades`, `drawdown_episodes`, `exposure`, `context_expectancy`)
- `apps/dashboard/src/dashboard_app/publication/evidence.py`
  (`discover_research_evidence_inputs`/`sanitize_signal_research_evidence`
  — the exact multi-table pattern this sprint's new role copies)
- `apps/dashboard/src/dashboard_app/publication/workspace.py`
  (`discover_catalog_inputs` — the sibling function this sprint extends,
  per D-P18-03)
- `apps/dashboard/src/dashboard_app/catalog/scanner.py`
  (`_scan_run_tree`'s existing `experiment_id` exclusion for
  robustness-experiment child runs — confirmed still correctly applies)
- `scripts/dashboard/generate_btc_signal_quality_projection.py` (the
  one-off script this sprint's generic path supersedes for Strategy
  Research; left untouched for its unique Signal/Predictive artifacts)

Architecture triage: **two findings during implementation, both resolved
without reopening D-P18-03**:

- **A second, unrelated private root exists:
  `user_data/research/strategy_research/runs/`** (44 directories) — these
  are walk-forward/parameter-sweep child runs of the one legacy
  `demo-robustness-nq-half-year` robustness experiment, already excluded
  from the catalog by `scanner.py`'s existing `experiment_id` filter
  (`_scan_run_tree`, lines 284-291) and never discovered by this sprint's
  function anyway, since it reads `storage_root` (`user_data/workspace`),
  a different physical root from `evidence_root`
  (`user_data/research`, used only by the older signal/robustness evidence
  path). No new filtering was needed — confirmed by a dedicated test
  (`test_discovery_excludes_robustness_experiment_child_runs`) rather than
  assumed safe.
- **Per-bar dense series need bounded sampling.** `equity.parquet`/
  `exposure.parquet` are 500K-1.3M rows for the 3 real runs — publishing
  every point is impractical for a committed static bundle. Bounded to
  `STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS = 2000` (deterministic,
  endpoint-preserving), reusing the exact technique
  `evidence.py`'s `walk_forward_equity` table already established (there,
  1,200 points). `trades` (6K-8K rows) and the analytics tables (one row
  per trade/episode/label) are never bounded — sampling a trade population
  would misrepresent the distribution and exit-diagnostics views that need
  it, and the PRD's Non-goals already forbid per-trade entry/exit
  price/quantity, keeping each trade row small (`net_pnl`/`exit_reason`
  only).

## Scope

In scope:

- **T001 — New multi-table `strategy_research_evidence` role.**
  `sanitizers.py` gains `_STRATEGY_EVIDENCE_ALLOWED_FIELDS` (manifest
  identity, including the Sprint 068/069 assumption and
  `strategy_source_ref` fields) and `_STRATEGY_EVIDENCE_TABLE_COLUMNS`
  (six tables: `summary_metrics`, `equity_curve`, `trades`,
  `drawdown_episodes`, `context_expectancy`, `exposure`), plus
  `sanitize_strategy_research_evidence`, mirroring
  `sanitize_signal_research_evidence`'s exact shape. Registered in
  `_SANITIZERS`. The existing 4-field `strategy_research_run_summary` role
  stays registered (still read by the pre-Sprint-070
  `pages/6_Strategy_Research.py`) but is not extended further.
- **T002 — Shared table-loading helpers.** New
  `publication/table_loading.py` (`load_table`, `bounded_row_indexes`,
  `json_value`, `read_json_mapping`, `required_string`) — the same logic
  `evidence.py` already has privately, extracted so the new discovery
  function doesn't duplicate it. `evidence.py` itself is left unchanged
  (no refactor risk taken on working, tested code outside this sprint's
  necessary blast radius).
- **T003 — `discover_strategy_research_evidence_inputs` in `workspace.py`.**
  Sibling to `discover_catalog_inputs`: same scanner
  (`catalog.scanner.list_runs`), same build-time-only reading rule,
  filtered to `WorkflowKind.STRATEGY`. For each discovered run, reads
  `equity.parquet`/`trades.parquet` (run root) and
  `analytics/{summary_metrics,drawdown_episodes,context_expectancy,exposure}.parquet`,
  applying the dense-table bound to `equity_curve`/`exposure` only. A run
  missing `summary_metrics` is skipped (not fatal); a run missing any
  other single table simply omits that table.
- **T004 — Wire into `generate_public_projection.py`; regenerate the
  committed bundle.** The general orchestrator now also calls the new
  discovery function. `generator.py`'s `refresh_publication_projection_bundle`
  gains `STRATEGY_RESEARCH_EVIDENCE_ROLE` in its `refreshable_roles` set
  (needed for idempotent re-runs, not just the first one). The committed
  `apps/dashboard/publication_data/projection.json` regenerated for real
  against the actual 3 persisted runs — not a demonstration, the real
  fix for the one-off-script gap D-P18-03 identified.

Out of scope (per D-P18-05):

- **Dashboard UI changes** — Milestone 2b, Sprint N+3. Nothing in
  `apps/dashboard/pages/` reads the new role yet; `pages/6` keeps using
  the old 4-field role unchanged.
- **Refactoring `evidence.py`** to use the new shared `table_loading.py`
  helpers — its own private copies still work; touching it isn't needed
  for this sprint's goal and would add regression risk for zero benefit
  to Milestone 2a.
- **Any change to the legacy `generate_btc_signal_quality_projection.py`
  script** — left as-is; this sprint only moves *Strategy Research*
  evidence onto the generic path, per D-P18-03's explicit scope.

## Decisions

Binding detail and rationale:
[`PHASE_18_WAVE0_DECISIONS.md`](../roadmap/PHASE_18_WAVE0_DECISIONS.md)
D-P18-03 and D-P18-05, both ACCEPTED (maintainer, 2026-09-18). The
dense-table bound value (2000 points) and the second-root/exclusion
finding are this sprint's own implementer-level resolutions (see
Architecture triage above), consistent with, not contradicting, D-P18-03.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `strategy_research_evidence` role: allowlists + sanitizer, registered | None | `publication/sanitizers.py` | standard | Done | — |
| T002 | `table_loading.py` shared helpers | None | `publication/table_loading.py` | standard | Done | — |
| T003 | `discover_strategy_research_evidence_inputs`; robustness-child-run exclusion verified by test | T001, T002 | `publication/workspace.py` | high | Done | — |
| T004 | Generator wiring + `refreshable_roles` fix + real committed `projection.json` regeneration, verified against a running dashboard (pages/6, pages/4 both still render, no server errors) | T003 | `scripts/dashboard/`, `publication/generator.py`, `publication_data/projection.json` | standard | Done | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprint 068/069's precedent —
bundled in one PR (T001-T004 are one coherent change to the publication
layer).

```text
main
  └── sprint/dashboard-strategy-research-evidence-m2a
        └── feat/generic-strategy-research-publisher  (T001-T004)
```

- Integration branch: `sprint/dashboard-strategy-research-evidence-m2a`,
  cut from `main` at its then-current head after approval.
- PR base is the sprint branch; one final integration PR to `main` at
  sprint close.
- Squash merge.

## Acceptance criteria

- All 3 existing runs produce a `strategy_research_evidence` artifact in
  the committed `projection.json`, each with all 6 tables present (or
  correctly omitting `context_expectancy` where empty).
- The 44 robustness-experiment child runs never appear as independent
  `strategy_research_evidence` or `research_catalog_entry` artifacts —
  verified by a dedicated test, not just absence of a failing assertion.
- `equity_curve`/`exposure` are capped at 2000 rows each; `trades` is not
  capped.
- No per-trade `entry_fill_price`/`quantity` reaches the public projection
  (verified by the sanitizer-drop test).
- Re-running the generator against the same runs a second time does not
  raise `DuplicateArtifactIdError`.
- `pages/6_Strategy_Research.py` and `pages/4_Market_and_Signal_Research.py`
  both still render correctly against the regenerated bundle, verified in
  a running dashboard, not just by unit test.
- Full suite green (root + dashboard, run separately per this project's
  own convention); `ruff check`, `ruff format --check`, `mypy` clean.

## Descope order

If the sprint must shrink, drop in this order — never the reverse:

```text
1. T004's real projection.json regeneration — the mechanism (T001-T003) is the higher-value slice; regenerating the committed bundle can follow in a small follow-up if time runs short.
```

## Closeout

**Status: DONE.** All 4 tasks (T001-T004) implemented and verified.

**Implementation**:

- `apps/dashboard/src/dashboard_app/publication/sanitizers.py` —
  `_STRATEGY_EVIDENCE_ALLOWED_FIELDS`, `_STRATEGY_EVIDENCE_TABLE_COLUMNS`,
  `sanitize_strategy_research_evidence`, registered as
  `strategy_research_evidence`.
- `apps/dashboard/src/dashboard_app/publication/table_loading.py` (new) —
  `load_table`, `bounded_row_indexes`, `json_value`, `read_json_mapping`,
  `required_string`.
- `apps/dashboard/src/dashboard_app/publication/workspace.py` —
  `STRATEGY_RESEARCH_EVIDENCE_ROLE`, `STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS = 2000`,
  `discover_strategy_research_evidence_inputs`.
- `apps/dashboard/src/dashboard_app/publication/generator.py` —
  `STRATEGY_RESEARCH_EVIDENCE_ROLE` added to `refreshable_roles`.
- `scripts/dashboard/generate_public_projection.py` — calls the new
  discovery function alongside the existing two.
- `apps/dashboard/publication_data/projection.json` — regenerated for
  real: 20 artifacts total (was 17), including 3 new
  `strategy_research_evidence` entries (`4dbf98822e6ae591`:
  `drawdown_episodes` 39 rows, `equity_curve`/`exposure` capped at 2000,
  `trades` 6,198, `context_expectancy` 0 rows; `8d050f623a034a58`:
  analogous, `context_expectancy` 0 rows; `eb80de6c9a6e3ab1`:
  `drawdown_episodes` 10 rows, `trades` 7,710, `context_expectancy` 2
  rows). The existing `strategy_research_run_summary` (2 artifacts, from
  the legacy script) preserved unchanged.

**Manual verification**: started the dashboard (`uv run --project
apps/dashboard streamlit run apps/dashboard/Project_Overview.py`) against
the regenerated `projection.json`. `pages/6_Strategy_Research.py` and
`pages/4_Market_and_Signal_Research.py` both rendered correctly with no
server errors (`preview_logs` checked). Neither page reads the new role
yet (Milestone 2b's job); this confirms the regeneration didn't disturb
what already works.

**Tests**: `apps/dashboard/tests/test_strategy_research_evidence.py` (new,
7 cases): full-field/table discovery, robustness-child-run exclusion
(the second-root finding above), skip-when-no-summary-metrics, dense-table
bounding, sanitizer field/table dropping, `bounded_row_indexes` endpoint
preservation, `load_table` absent-file handling. Full dashboard suite:
**295 passed** (up from 288), root suite unaffected (**2057 passed**, this
sprint touched only `apps/dashboard`). `ruff check`, `ruff format --check`,
`mypy` (`apps/dashboard/src`, `scripts/dashboard` — the project's own mypy
scope, which does not include `apps/dashboard/tests`) all clean.

**Acceptance criteria**: all met — see Tests and Manual verification above.

**Remaining work**: Sprint N+3 (Milestone 2b — dashboard UI: overview
table, run selector, 8-section detail view consuming
`strategy_research_evidence`) is next per D-P18-05's 4-sprint plan, and
the last of the four.
