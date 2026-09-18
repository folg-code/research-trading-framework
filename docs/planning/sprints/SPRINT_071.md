# Sprint 071: Strategy Research Dashboard UI (Phase 18, 18A Milestone 2b)

Status: **Open** — maintainer authorized opening this sprint 2026-09-18.
Goal: Implement Phase 18 18A's Milestone 2b — the last of D-P18-05's four
sprints. Replace `pages/6_Strategy_Research.py`'s hardcoded single-run
page with an overview table (every persisted run) and a run-selectable
detail view covering all eight "Desired evidence views" rows the PRD's
Goals named, consuming Sprint 070's `strategy_research_evidence` role.

Sources:

- `docs/product/PRD-dashboard-strategy-research-evidence.md` (APPROVED
  2026-09-18) — Milestone 2's Goals list the overview table, run
  selector and eight detail sections this sprint builds.
- `docs/planning/roadmap/PHASE_18_WAVE0_DECISIONS.md` — D-P18-05 (this is
  the fourth and final sprint in its plan)
- `docs/planning/sprints/SPRINT_070.md` — this sprint's data prerequisite
  (the `strategy_research_evidence` role, six tables, real committed
  `projection.json`)
- `apps/dashboard/pages/4_Market_and_Signal_Research.py`,
  `apps/dashboard/src/dashboard_app/views/projected_research.py`
  (`signal_research_evidence`/`ProjectedResearchEvidence.table` — the
  exact overview+selector+multi-table pattern this sprint mirrors)

Architecture triage: **one finding, resolved without a new Wave 0 pass**
— client-side display aggregation over an already-fully-published
population is not "computing a new research metric":

- **Exit diagnostics needs a count-by-`exit_reason`, which isn't itself a
  persisted field.** The PRD's Goals name this section, but no published
  table pre-aggregates it. Resolved as a simple, transparent tally
  (`pandas.value_counts()`) over the `trades` table's already-fully-
  disclosed, unsampled `exit_reason` column — every trade is already
  public in full; counting how many share a label is a display
  convenience (the same class of operation `px.histogram`'s automatic
  binning already performs on published `net_pnl` values one section
  above), not deriving a new fact the research layer never reviewed.
  Distinguished explicitly from an aggregate that would need research-
  layer review (e.g. a computed Sharpe ratio never persisted) — the
  page's caption states this distinction rather than leaving it implicit.
  ADR-0034/0035's "does not compute metrics or verdicts" rule is read as
  targeting derived *research* facts, not the ordinary tallying/binning
  every chart library performs on data already public without exception.

## Scope

In scope:

- **T001 — `strategy_research_evidence()` view accessor.** New function
  in `views/projected_research.py`, mirroring `signal_research_evidence`'s
  exact shape (newest-first, `ProjectedResearchEvidence` wrapping the new
  role). `formatting.py`'s `format_kpi` extended with `sortino_ratio`,
  `expectancy`, `avg_win`, `avg_loss`, `current_drawdown` (same additive
  pattern as its existing keys — no new formatting logic invented).
- **T002 — Overview table.** Every persisted run, one row: identity
  (strategy/market/signal model, dataset, timeframe), assumptions
  (initial capital, commission, slippage) and the full KPI set from
  `summary_metrics`. Rendered via `st.dataframe`, whose native column-
  header sort satisfies "visitors may sort by different eligible KPIs"
  without new sort-UI code. Material differences (dataset, capital, cost)
  sit in the same table as the KPIs, not papered over.
- **T003 — Run selector.** Replaces the old hardcoded `runs[0]`;
  in-page `st.selectbox` state (per 18A's PRD-time decision — no URL
  routing precedent exists in this app).
- **T004 — Eight detail sections** for the selected run: backtest
  assumptions/provenance, full KPI summary, simulated equity and
  drawdown (two charts), trade PnL distribution (histogram), exit
  diagnostics (tally + bar chart, see Architecture triage), conditional
  expectancy by market context (table, honestly reporting "nothing to
  show" when the run's Market Model has no `STATE`-kind dependency),
  drawdown structure (table, blank `recovery_bars` for an unresolved
  episode), capital and exposure (chart). Every section reports
  unavailable, not fabricated, when its table is absent or empty.

Out of scope:

- **18B/18C/18D** — separate, later, still-directional tracks. This
  sprint touches only `pages/6_Strategy_Research.py` and its immediate
  view/formatting dependencies.
- **R-multiple trade distribution** — PRD non-goal, unchanged; no
  per-trade initial risk is persisted.
- **URL-based deep links to a specific run** — no precedent in this app;
  the PRD already deferred this.

## Decisions

No new Wave 0 decisions. The exit-diagnostics tally question (Architecture
triage above) is this sprint's own implementer-level resolution, consistent
with, not contradicting, the PRD's existing "publisher copies facts, never
derives metrics" rule — the tally happens in the browser over data already
fully public, the same operation any chart's binning already performs.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `strategy_research_evidence()` accessor; `format_kpi` extended | Sprint 070 | `views/projected_research.py`, `formatting.py` | standard | Done | — |
| T002 | Overview table, sortable, all runs | T001 | `pages/6_Strategy_Research.py` | standard | Done | — |
| T003 | Run selector replacing hardcoded `runs[0]` | T001 | `pages/6_Strategy_Research.py` | standard | Done | — |
| T004 | 8 detail sections | T001, T003 | `pages/6_Strategy_Research.py` | high | Done | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprints 068-070's
precedent — bundled in one PR (T001-T004 are one page rewrite).

```text
main
  └── sprint/dashboard-strategy-research-evidence-m2b
        └── feat/strategy-research-dashboard-ui  (T001-T004)
```

## Acceptance criteria

- All 3 persisted runs appear in the overview table; none silently
  dropped for missing an unrelated field.
- Selecting any run in the dropdown updates every detail section.
- The canonical example run (`eb80de6c9a6e3ab1`) shows a non-empty,
  correctly-eligible-flagged conditional-expectancy table; both
  `s058_t005_*` runs show the honest "nothing to show" message, not an
  empty table rendered as if it were data.
- A drawdown episode still open at run end shows a blank `recovery_bars`,
  never a fabricated number.
- No new metric is computed from raw per-trade/per-bar data beyond the
  documented exit-reason tally (verified by code review, not just test
  absence).
- Verified in a running dashboard (`streamlit run
  apps/dashboard/Project_Overview.py`), not only by `AppTest`.
- Dashboard suite green; `ruff check`, `ruff format --check`, `mypy`
  clean.

## Closeout

**Status: DONE.** All 4 tasks (T001-T004) implemented and verified.

**Implementation**:

- `apps/dashboard/src/dashboard_app/views/projected_research.py` —
  `strategy_research_evidence()`.
- `apps/dashboard/src/dashboard_app/formatting.py` — `format_kpi` gained
  `sortino_ratio`, `expectancy`, `avg_win`, `avg_loss`,
  `current_drawdown`.
- `apps/dashboard/pages/6_Strategy_Research.py` — fully rewritten:
  overview table (`pa.Table.from_pylist` of per-run identity +
  assumptions + KPI fields, `.to_pandas()` into `st.dataframe`), run
  selector, eight detail sections per Scope above.

**Manual verification**: started the dashboard against the real
committed `projection.json` (Sprint 070's regeneration). Confirmed by
screenshot: overview table lists all 3 runs with sortable columns; run
selector switches correctly; KPI summary shows all 13 fields for
`4dbf98822e6ae591` (net PnL +1,206,906.60, Sharpe 0.65, etc.); equity/
drawdown/exposure charts render from the bounded 2,000-point series;
trade PnL histogram and exit-reason bar chart render from the full 6,198-
trade population; switching to `eb80de6c9a6e3ab1` shows the real,
non-empty conditional-expectancy table (label `1.0`: 7,706 trades,
`eligible=true`, `net_pnl_mean=-1.53`, `win_rate=0.4875` — matching
Sprint 069's backfill exactly) instead of the "nothing to show" message
the other two runs correctly display; drawdown structure table renders
39/37/10 episodes per run with blank `recovery_bars` for unresolved ones.
No server errors in any state.

**Tests**: `apps/dashboard/tests/test_strategy_research_evidence.py`
(+2 cases, both `AppTest`-driven against the real committed
`projection.json`, mirroring `test_signal_page_renders_projected_tables_and_charts`'s
existing pattern): full page render (overview + all 8 subheaders + ≥3
plotly charts, no exception), and run-switching to the canonical example
confirming the conditional-expectancy table appears instead of the
"nothing to show" info box. Full dashboard suite: **297 passed** (up
from 295), 1 skipped. Root suite unaffected: **2057 passed**. `ruff
check`, `ruff format --check`, `mypy` (`apps/dashboard/src`,
`apps/dashboard/pages` — both in this project's mypy scope) all clean.

**Acceptance criteria**: all met — see Manual verification and Tests
above.

**Remaining work**: none for this PRD's Milestone 1/2 scope. All four
sprints in D-P18-05's plan (068, 069, 070, 071) are now closed. 18A's
PRD is fully implemented. Remaining Phase 18 work (18B/18C/18D) is
separate, still-directional, and not scheduled by this closeout.
