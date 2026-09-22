# Sprint 074: Signal Research Dashboard UI (Phase 18, 18B Milestone 2)

Status: **Open** — maintainer authorized opening this sprint 2026-09-22.
Goal: Implement Phase 18 18B's Milestone 2 — the dashboard layer
consuming all ten `signal_research_evidence` tables, six of which
(`summary_metrics`, `grouped_summaries`, `distribution_summaries`,
`conditional_comparison`, `join_diagnostics`, `metric_histograms`,
`quality_warnings`) already render today, and four of which
(`adjusted_forward_drift`, `context_timeline`, `context_persistence`,
`mfe_mae_pairs`) Sprint 073 published but no page yet surfaces.
Milestone 1's hard sequencing gate (artifacts must exist for at least
one run) is satisfied — Sprint 073 published all four for 5 of 6 real
runs.

Sources:

- `docs/product/PRD-dashboard-signal-research-evidence.md` (APPROVED
  2026-09-18) — Milestone 2's Goals list every section this sprint
  builds.
- `docs/planning/sprints/SPRINT_073.md` — this sprint's data
  prerequisite (all four new tables, real committed `projection.json`).
- `apps/dashboard/pages/6_Strategy_Research.py`,
  `docs/planning/sprints/SPRINT_071.md` — the overview-table +
  run-selector + detail-section pattern this sprint mirrors for Signal
  Research (today's page has only a bare selector, no overview table).
- `apps/dashboard/src/dashboard_app/views/projected_research.py`
  (`signal_research_evidence`, `ProjectedResearchEvidence.table` —
  unchanged, already generic enough for the new tables).

Architecture triage: two findings, resolved without a new Wave 0 pass,
mirroring Sprint 071's own inline-resolution precedent:

- **"Direction" is not a persisted, separate slicing column.** The
  PRD's Goals warn that "Signal Research can contain several horizons/
  directions in one run" and require every new view to operate on one
  explicit slice. Checked directly against all 6 real runs: each has
  exactly one (or zero) `signal_model_ids` entry -- direction is
  already baked into that single model's identity (e.g.
  `higher_low_long`), not a second axis needing its own selector.
  `horizon_bars` is the one real multi-valued axis
  (`horizon_bars_requested` has up to 4 values per run) -- resolved
  with a shared horizon selector reused by the adjusted-forward-drift
  and MFE/MAE sections (both are naturally a single-horizon slice),
  never silently defaulting to one horizon.
- **`grouped_summaries` has three distinct `group_dimension` values
  per run** (`calendar_month`, `rth_membership`, `time_of_day` --
  confirmed against the 3 real runs that have `grouped_summaries` at
  all), each with a disjoint `group_value` vocabulary (a month string,
  a boolean-like label, an hour-of-day string). A single heatmap
  cannot meaningfully mix all three on one y-axis. Resolved with a
  `group_dimension` selector; the heatmap itself plots `horizon_bars`
  by `group_value` together (its own two axes), so it needs no
  separate horizon selector -- only the dimension choice.

## Scope

In scope:

- **T001 -- Signal Research overview table.** New overview section on
  `pages/4_Market_and_Signal_Research.py`, mirroring
  `6_Strategy_Research.py`'s `_overview_row` pattern: one row per
  safely-projected run -- research question, Market/Signal Model
  identities, dataset/instrument, evaluation timeframe, requested
  horizons, sample/completion counts (from `summary_metrics`), quality
  warning count. Sortable via the native `st.dataframe` header (no new
  sort-UI code, per the PRD).
- **T002 -- Forward-drift heatmap by context and horizon.** From
  `grouped_summaries`, with the `group_dimension` selector from the
  triage above (`horizon_bars` is the heatmap's own x-axis). Honest
  "unavailable" for the 3 runs missing `grouped_summaries` (unchanged
  existing behavior).
- **T003 -- MFE/MAE relation scatter.** From the new `mfe_mae_pairs`
  artifact, filtered to the selected horizon.
- **T004 -- Adjusted forward drift view.** From the new
  `adjusted_forward_drift` artifact, filtered to the selected horizon,
  shown beside (never replacing) `grouped_summaries`' raw
  `forward_return_mean` for the same group -- a dumbbell-style
  raw-vs-adjusted comparison, plus the underlying table including
  `shrinkage_weight` for transparency.
- **T005 -- Context timeline chart and context persistence table.**
  From the two new artifacts. A `component_id` selector when a run's
  Market Model resolves more than one `STATE`-kind alias. Honest
  "unavailable" for the one real run (`e05c1fe5566e6462`) with no
  Market Model to derive these from.

Out of scope (per the PRD and Milestone 1's own Non-goals, unchanged):

- **18D (Robustness Research evidence view)** -- separate, later PRD.
- **Any new persisted artifact or backfill** -- Milestone 2 is
  presentation-only over Milestone 1's already-published tables; no new
  computation, per ADR-0034/0035 (Success metric 5).
- **Authoring a `--definition` file** for the 3 runs still missing
  `grouped_summaries` -- still deferred (D-P18B-02); those runs show
  "unavailable" for the heatmap and adjusted-drift sections, not an
  error.

## Decisions

No new Wave 0 decisions -- Milestone 2's shape was already fully
specified in the PRD's Goals; the two architecture-triage findings above
are implementer-level resolutions in the same class as Sprint 071's
exit-diagnostics tally, not open design questions.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Overview table added, sortable, shows all safely-projected runs | None | `apps/dashboard/pages/4_Market_and_Signal_Research.py` | standard | Done | -- |
| T002 | Forward-drift heatmap by context and horizon | None | `apps/dashboard/pages/4_Market_and_Signal_Research.py` | standard | Done | -- |
| T003 | MFE/MAE relation scatter | None | `apps/dashboard/pages/4_Market_and_Signal_Research.py` | standard | Done | -- |
| T004 | Adjusted forward drift view, raw vs adjusted clearly distinguished | None | `apps/dashboard/pages/4_Market_and_Signal_Research.py` | standard | Done | -- |
| T005 | Context timeline chart and context persistence table | None | `apps/dashboard/pages/4_Market_and_Signal_Research.py` | standard | Done | -- |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprints 068-073's
precedent -- bundled in one PR (T001-T005 are one coherent UI feature).

```text
main
  └── sprint/dashboard-signal-research-evidence-m2
        └── feat/signal-research-dashboard-ui  (T001-T005)
```

## Acceptance criteria

- Overview table lists every safely-projected Signal Research run with
  no filesystem scan at request time (fields sourced only from the
  already-projected bundle).
- Every new section operates on one explicit (horizon, and where
  applicable, context-dimension) slice at a time, chosen by the
  visitor -- never silently collapsed across horizons.
- Adjusted forward drift is always shown distinguishably from the raw
  `grouped_summaries` mean, never replacing it.
- A run missing any of the four new tables shows an honest
  "unavailable" message for that section, never a fabricated value or
  an unhandled exception.
- No new metric is computed by the dashboard at request time -- every
  number traces to a Milestone 1 persisted artifact (Success metric 5).
- Dashboard suite green; `ruff check`, `ruff format --check`, `mypy`
  clean; page verified rendering against the real committed bundle in a
  running dashboard (all 6 runs selectable, no exceptions).

## Closeout

**Status: DONE.** All 5 tasks (T001-T005) implemented and verified.

**Implementation**: see the PR diff for
`apps/dashboard/pages/4_Market_and_Signal_Research.py` and its test
coverage in `apps/dashboard/tests/`.

**Manual verification**: started the dashboard against the committed
bundle and exercised the overview table, the horizon/dimension
selectors, and every new section across multiple real runs, including
the one run with no Market Model (context sections correctly show
"unavailable") and the 3 runs with no `grouped_summaries` (heatmap and
adjusted-drift sections correctly show "unavailable").

**Tests**: dashboard suite green; `ruff check`, `ruff format --check`,
`mypy` (full project-configured file set) all clean.

**Acceptance criteria**: all met -- see Manual verification and Tests
above.

**Remaining work**: Phase 18 18B is now fully complete (Milestones 1
and 2 both done). 18D (Robustness Research evidence view) remains
directional and unscheduled.
