# PRD — Dashboard Strategy Research Evidence Views (Phase 18, Increment 18A)

```text
Status: APPROVED (maintainer, 2026-09-18)
```

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for Phase 2F/11/12/13,
the ML runtime-promotion track and
`docs/product/PRD-market-analysis-catalog-expansion-2026-09.md`.

Source input:
[`docs/vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md`](../vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md)
(§"Desired evidence views", Strategy Research rows) and
[`docs/planning/roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md`](../planning/roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md),
scoped to increment **18A** only (18B/18C/18D remain separate, future PRDs).
This document is that PRD for 18A.

## Problem

`apps/dashboard` has shipped a partial Strategy Research evidence page since
2026-09-11
([`pages/6_Strategy_Research.py`](../../apps/dashboard/pages/6_Strategy_Research.py)),
predating both source vision docs above, which were drafted without
accounting for it. That page:

- Hardcodes `runs[0]` — no run selector, no overview table across the 3
  persisted Strategy Research runs
  (`user_data/workspace/research/strategy_research/runs/`).
- Shows only 3 KPIs (net PnL, trade count, win rate) although
  `analytics/summary_metrics.parquet` already persists 9 more
  (`total_return`, `max_drawdown`, `current_drawdown`, `sharpe_ratio`,
  `sortino_ratio`, `profit_factor`, `expectancy`, `avg_win`, `avg_loss`,
  `total_costs`).
- Shows nothing from `equity.parquet` (per-bar `equity`, `drawdown`,
  `open_position_count` — already persisted) or `trades.parquet` (per-trade
  `exit_reason`, `net_pnl`, `commission_paid`, `quantity`, entry/exit
  price/time — already persisted).
- Shows no backtest assumptions. `manifest.json` stores only a
  `simulation_assumptions_fingerprint` (a one-way SHA-256 hash); the actual
  `SimulationAssumptions` field values (`initial_capital`,
  `commission_per_side`, `slippage_bps`, fill policy —
  `src/trading_framework/research/simulation/assumptions.py:29`) are computed
  at run time and then discarded, never persisted per run.
- Has no conditional-expectancy, drawdown-structure or capital/exposure view.
  None of these three are computed or persisted anywhere today; the vision
  doc itself flags their methodology as unresolved.

Most of the vision doc's Strategy Research "Desired evidence views" rows
therefore split into two very different cost tiers: some need only
publication-boundary allowlisting and UI work because the source data
already exists; three need genuinely new research/analytics-layer work with
methodology that had never been decided before this PRD. Both docs above are
being corrected (2026-09-17/18) to record this baseline instead of assuming
greenfield.

## Goals (v1)

Two sequential milestones, matching the maintainer's stated natural
workflow: extend research/analytics first, then extend the dashboard that
consumes it. Milestone 2 is gated on Milestone 1 landing.

### Milestone 1 — Research/analytics layer (new persisted facts)

All new artifacts are computed **post-hoc** from already-persisted
`equity.parquet`/`trades.parquet`/`manifest.json`, following the existing
`analytics/summary_metrics.parquet` convention (same per-run `analytics/`
folder, no simulator rerun, no dashboard-side computation).

- **Persist real `SimulationAssumptions` values.** Extend
  `run_strategy_research.py`'s manifest write to also store
  `fill_policy_entry`, `fill_policy_exit`, `slippage_bps`,
  `commission_per_side` and `initial_capital` as plain fields alongside the
  existing fingerprint — the fingerprint stays for identity/dedup, these new
  fields make it human-readable and publishable. This is the sole data
  source for the "Backtest assumptions and provenance" row.
- **`analytics/drawdown_episodes.parquet`** — one row per drawdown episode
  extracted from `equity.parquet`. Episode = from a new equity peak to the
  next new peak (recovery). Fields: `peak_at`, `peak_equity`, `trough_at`,
  `trough_equity`, `depth_pct` (`min(equity/peak) - 1` within the episode),
  `duration_bars` (peak→trough), `recovery_bars` (trough→peak, `null` if the
  run ends before recovery — an explicit "not yet recovered" episode, not a
  zero). No minimum-depth threshold — every peak-to-recovery cycle is one
  episode, however shallow.
- **`analytics/context_expectancy.parquet`** — generic, not hardcoded to any
  one component. **Corrected in Wave 0 (2026-09-18):** this is *not* pure
  post-hoc reading of already-persisted files. The persisted Market Model
  result (`market_model_result_dataframe`) is a single boolean gate column
  only — every intermediate component value is discarded, and there is no
  market-model-id → definition registry to resolve "the run's Market Model"
  generically. The actual mechanism: (1) `run_strategy_research.py` gains a
  new `strategy_source_ref` manifest field (the module path that built the
  run's strategy, already available at request time via the CLI's
  `strategy_file` config key or the launching script's own path) so future
  runs can resolve their Market Model builder generically; (2) for a
  resolved run, recompute Market Analysis components over
  `source_dataset_ref` by calling that builder — a deterministic, read-only
  computation, not a simulator rerun — and inspect the resulting components
  for boolean/small-cardinality-categorical outputs; (3) join those to
  `trades.parquet` at `entry_signal_at`. Persist per (component, label):
  `sample_count`, `net_pnl_mean`, `net_pnl_median`, `win_rate`, and a
  `missing_context_count`, gated by the eligibility thresholds in
  [Wave 0 D-P18-04](../planning/roadmap/PHASE_18_WAVE0_DECISIONS.md#d-p18-04--context-expectancy-eligibility-thresholds)
  (`min_sample_size=5` to compute, `interpretation_min_sample_size=30` to
  mark interpretable — both explicit, calibratable parameters, reusing the
  existing Signal Research analytics convention rather than a new scheme).
  A run whose Market Model emits no categorical/boolean output produces an
  empty table, not an error. See
  [Wave 0 D-P18-02](../planning/roadmap/PHASE_18_WAVE0_DECISIONS.md#d-p18-02--context-expectancy-computation-mechanism)
  for the full investigation and the 3 legacy runs' one-time builder
  resolution.
- **`analytics/exposure.parquet`** — per-bar `notional_exposure`
  (`sum(open trade quantity × entry_fill_price)` for positions open at that
  bar) and `exposure_ratio` (`notional_exposure / equity` at the same bar,
  from `equity.parquet`) — a leverage-like series built purely from already
  -persisted `trades.parquet` + `equity.parquet`. No margin/leverage model
  exists in the simulator; this is the only exposure measure v1 supports.
- **Backfill for the 3 existing runs — resolved in Wave 0 (2026-09-18).**
  `drawdown_episodes` and `exposure` are fully recoverable by rerunning the
  post-hoc computation against each run's existing `equity.parquet`/
  `trades.parquet` — no simulator rerun needed. The `SimulationAssumptions`
  field values, despite only a one-way fingerprint being stored, are also
  fully recovered: all 3 runs share fingerprint `1aa6ee647c5cc636`, which
  Wave 0 confirmed by direct hash verification equals the
  `SimulationAssumptions` dataclass's own defaults (`initial_capital=100000`,
  `commission_per_side=0`, `slippage_bps=0`, both fill policies
  `next_bar_open`). No Sprint 064/058/013 config archaeology was needed;
  see [Wave 0 D-P18-01](../planning/roadmap/PHASE_18_WAVE0_DECISIONS.md#d-p18-01--simulationassumptions-backfill-for-the-3-existing-runs).
  The "assumptions not recovered" contingency originally written here does
  not apply to any of the 3 existing runs.

### Milestone 2 — Dashboard/publication layer

- **Build a generic Strategy Research evidence publisher — corrected in
  Wave 0 (2026-09-18), larger than "extend the allowlist".**
  `publication/workspace.py`'s only existing Strategy Research path
  (`discover_catalog_inputs`) emits identity only; the richer
  `strategy_research_run_summary` role is today produced by a one-off
  script hardcoding exactly 2 of the 3 runs
  (`scripts/dashboard/generate_btc_signal_quality_projection.py`) — the
  3rd run has no summary published at all. Add a sibling function in
  `publication/workspace.py` that, for every run the existing scanner
  safely discovers, emits: the full `summary_metrics` field set (folding in
  the newly-persisted `SimulationAssumptions` fields), a new
  `strategy_research_equity_curve` role from `equity.parquet`, a new
  `strategy_research_trades` role (`net_pnl`/`exit_reason` only) from
  `trades.parquet`, and roles for the three new Milestone-1 artifacts. Each
  role's `frozenset[str]` allowlist in `sanitizers.py` is extended/added
  following the existing pattern; the publisher change is the larger,
  previously-unstated part. See
  [Wave 0 D-P18-03](../planning/roadmap/PHASE_18_WAVE0_DECISIONS.md#d-p18-03--generic-strategy-research-publication-pipeline).
  A publisher copies these approved facts; it computes nothing new.
- **Strategy Research overview table** (new — today there is none): every
  safely-projected run, including ones with no eligible KPI, with identity,
  strategy composition, dataset/instrument, timeframe, simulation/capital
  assumptions, trade count, persisted KPIs, warnings and verdict. Sortable
  by any eligible KPI column; a run missing that KPI sorts as unavailable,
  never as zero.
- **Run selector replacing the hardcoded `runs[0]`.** Selecting a row opens
  a detail view for that run (in-page `st.selectbox`-driven state, matching
  the existing pattern already used in
  `pages/4_Market_and_Signal_Research.py`, not a new URL-routing mechanism —
  no precedent for URL-based run routing exists in this Streamlit app today,
  and inventing one is out of scope for this PRD). The detail view links
  back to the overview.
- **Detail view sections**, each independently reporting "unavailable" (not
  hidden, not zero) when its data is missing for that run:
  - Backtest assumptions and provenance (Milestone 1's new manifest fields).
  - Full KPI summary (all `summary_metrics` fields, not just 3).
  - Simulated equity and drawdown chart, from `equity.parquet` directly.
  - Trade outcome (PnL/return) distribution histogram, from `trades.parquet`
    `net_pnl` — **not** R-multiples (see Non-goals).
  - Exit diagnostics: trade outcomes grouped by `exit_reason`.
  - Conditional expectancy by market context, from
    `context_expectancy.parquet`, when non-empty for that run.
  - Drawdown structure table, from `drawdown_episodes.parquet`.
  - Capital and exposure chart, from `exposure.parquet`.
- **Time-range/PnL presentation.** Each run's chart marks its own actual
  evaluation interval; runs are never merged into one combined equity curve
  or summed PnL. Absolute PnL is labeled with its currency/`initial_capital`
  basis; the already-persisted `total_return` is offered as a separate,
  clearly labeled normalized measure — no new normalization logic is
  invented.
- **Comparison-compatibility disclosure.** The overview table and any
  cross-run chart surface material differences (instrument, capital basis,
  cost model, simulation assumptions) inline, per the vision doc's rule —
  sorting or charting never implies a ranking, promotion or live-edge claim.

## Non-goals (v1)

- **R-multiple trade distribution.** No trade has a persisted `initial_risk`
  today; adding one means changing `RiskModel`/`BarSequentialSimulator` to
  persist a per-trade risk basis — a simulator-engine change, materially
  larger than this PRD's analytics/dashboard scope. v1 ships PnL/return
  distribution only, per the vision doc's explicit fallback.
- **18B (Signal Research evidence), 18C (context/diagnostics), 18D
  (Robustness Research)** — separate, later PRDs. This PRD does not extend
  `pages/4_Market_and_Signal_Research.py`.
- **IDEA-027's Signal/Strategy Research validation series.** Unscheduled,
  unrelated to this PRD — see that idea's Review note
  (`docs/planning/registries/idea-market-analysis.md`). This PRD's data
  source is the 3 already-persisted Strategy Research runs, not any new
  research campaign.
- **Any change to `BarSequentialSimulator`'s simulation logic.** Milestone
  1's manifest change is additive persistence only, not a behavior change.
- **URL-based run routing.** No precedent exists in this app; deferred to
  whichever future increment actually needs shareable deep links.
- **Ranking, promotion or live-trading-edge claims** from any sort, chart or
  comparison — carried over as a hard, non-negotiable constraint from both
  source docs and ADR-0034/0035, not re-litigated here.
- **Reading the private research workspace at request time.** The public
  dashboard only ever reads the immutable projection; Milestone 1's new
  artifacts reach it only through the Milestone 2 publisher step.

## Success metrics

1. **Milestone 1 artifacts exist and are backfilled** for all 3 existing
   runs (`drawdown_episodes.parquet`, `context_expectancy.parquet`,
   `exposure.parquet` for all three; `SimulationAssumptions` fields for at
   least newly-run studies, with an explicit disclosed gap for the 3
   pre-existing runs if Sprint 064's config cannot be recovered).
2. **The Strategy Research overview table lists all 3 persisted runs**,
   sortable by at least `net_pnl`, `sharpe_ratio` and `win_rate`, with no
   run silently dropped for missing an unrelated field.
3. **Every detail-view section renders for at least one run without
   fabricating data** — a run lacking eligible data for a section shows an
   explicit "unavailable" state, verified by testing against whichever of
   the 3 runs has the weakest data (e.g. no categorical Market Model
   component, if any).
4. **`context_expectancy` computation is verified generic** — demonstrated
   against at least one run whose Market Model emits a categorical/boolean
   component (not hardcoded to a single named component).
5. **No new metric is computed by the dashboard at request time** — every
   number in the detail view traces to a Milestone 1 persisted artifact,
   verifiable by code review against ADR-0034/0035.

## Riskiest assumption

**That the 3 existing runs actually have Market Model compositions rich
enough to exercise `context_expectancy` meaningfully.** If none of their
Market Models emit a categorical or boolean component output, Milestone 1's
generic join logic will be implemented and tested only against
zero-context-available cases, and its "works for any categorical component"
claim (Success metric 4) will be unverified until a future run happens to
use one. If Wave 0 / implementation finds this is the case, that is a
stop-and-report finding, not a reason to fabricate a synthetic test run.

## Constraints

- Milestone 2 does not start implementation until Milestone 1's artifacts
  exist for at least one run — this is a hard sequencing gate, matching the
  maintainer's stated preferred workflow order.
- No new ADR expected by default: Milestone 1 additions are post-hoc
  analytics artifacts following an established per-run `analytics/` folder
  convention (precedent: `summary_metrics.parquet`), and Milestone 2 follows
  the established publication-boundary pattern (ADR-0034/0035) without
  changing it. If implementation finds the generic context-join needs a new
  registry capability, that finding earns its own ADR at that point.
- Every Wave 0 / architect decision set goes back to the maintainer for
  explicit review before implementation starts, per this project's
  governance convention.

## User story

As the maintainer, I want the dashboard's existing but minimal Strategy
Research page replaced by a real overview-plus-detail evidence view backed
by data that mostly already exists in the research workspace, with the
three genuinely new analytical facts (drawdown episodes, context-conditional
expectancy, exposure) computed and persisted in the research layer first, so
the dashboard work that follows is pure display of already-approved facts —
never a place where new metrics get invented under UI pressure.

## Open questions

All four originally listed here are **resolved by Wave 0 (2026-09-18)** —
see [PHASE_18_WAVE0_DECISIONS.md](../planning/roadmap/PHASE_18_WAVE0_DECISIONS.md):
Sprint 064 config recoverability turned out unnecessary (D-P18-01, resolved
by direct fingerprint verification against known defaults); the allowlist
diff is now a generic publisher, not just a `frozenset` diff (D-P18-03); the
minimum-sample-count question is resolved by reusing the existing Signal
Research `min_sample_size`/`interpretation_min_sample_size` convention
(D-P18-04). None of these are re-opened here.

## Handoff

Wave 0 is complete — see
[PHASE_18_WAVE0_DECISIONS.md](../planning/roadmap/PHASE_18_WAVE0_DECISIONS.md),
accepted by the maintainer 2026-09-18. Two of its findings materially
corrected this PRD's Goals (D-P18-02 on `context_expectancy`'s real
mechanism, D-P18-03 on the publisher's real scope) — those edits are
already applied above. Implementation proceeds per D-P18-05's 4-sprint
split: Sprint N (manifest backfill + `drawdown_episodes` + `exposure`),
Sprint N+1 (`strategy_source_ref` + `context_expectancy`), Sprint N+2
(generic publisher), Sprint N+3 (dashboard UI). Milestone ordering
(analytics before dashboard), the drawdown-episode definition, the
exposure-ratio formula and the PnL-not-R-multiple decision remain as
originally decided — see Goals and Non-goals; do not re-litigate them.
