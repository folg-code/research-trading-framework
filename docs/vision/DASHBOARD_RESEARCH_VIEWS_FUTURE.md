# Research Evidence Views in the Public Dashboard — Future Direction

```text
Status: DRAFT — maintainer intent captured 2026-09-14; PRD scope not approved
Scope: future read-only Signal, Strategy and Robustness Research evidence
       in apps/dashboard
Owner: Product direction
```

## Existing baseline (found 2026-09-17)

This document was drafted without accounting for two evidence pages already
shipped in `apps/dashboard` since 2026-09-11 (`feat(dashboard): recruiter-facing
readability, navigation and styling pass`), predating this draft:

- [`pages/6_Strategy_Research.py`](../../apps/dashboard/pages/6_Strategy_Research.py)
  — one representative Strategy Research run: run identity, model, dataset,
  timeframe, time range, verdict, and a KPI summary limited to net PnL, trade
  count and win rate. Partial coverage of the "KPI summary" row below; no
  backtest assumptions/provenance, equity/drawdown, R-multiple distribution,
  conditional expectancy, exit diagnostics, drawdown structure or
  capital/exposure.
- [`pages/4_Market_and_Signal_Research.py`](../../apps/dashboard/pages/4_Market_and_Signal_Research.py)
  — representative Market Data identity plus a selectable Signal Research
  run showing summary metrics, grouped metrics, forward-return percentiles by
  horizon (a line chart, not the heatmap-by-context row below), conditional
  comparison, metric histograms, quality warnings and join diagnostics.
  Meaningfully overlaps several "Market and Signal Research" rows below, but
  none was verified field-by-field against this table.

Both pages read the same `projection.json` / publication-boundary pattern
this document assumes (ADR-0034/ADR-0035) and already have real persisted
runs behind them (3 Strategy Research runs, 4 Signal/Predictive Research
runs, per `apps/dashboard/publication_data/`). Any future PRD for the rows
below should treat these two pages as the starting baseline, not greenfield,
and should re-verify per-row coverage against the actual persisted schema
rather than trusting this summary.

## Purpose and relationship to existing scope

This direction extends the accepted [Portfolio Dashboard Development
Direction](../planning/DASHBOARD_DEVELOPMENT_DIRECTION.md) with analytical
views for different Signal and Strategy Research runs and a related Robustness
Research view. It is an input to a
future PRD, not a revision of the accepted [Portfolio Dashboard MVP
PRD](../product/PRD-portfolio-dashboard-mvp.md), its first-release success
test, or the Phase 16D sprint scope. The public dashboard remains a read-only
consumer of persisted, safely projected evidence. The local Research Workbench
retains its separate control boundary.

The result should let a visitor compare the coverage and persisted outcomes of
many runs, open the evidence for one run, and understand how a strategy behaved
without changing dashboard code for each strategy definition. It should show
negative, zero-trade, incomplete and unsupported runs honestly. Sorting or
plotting a metric does not create a ranking verdict, promotion decision or
claim of a live trading edge.

## Workflow overviews and detail navigation

Signal Research and Strategy Research each receive a workflow-specific
overview and a detailed view for a selected run. The existing Research Catalog
remains the study-grouped discovery surface across workflows; these overviews
provide analytical inspection within one workflow. Each overview lists every
safely identifiable published run, including one with no eligible KPI.
Available persisted fields may be filtered and sorted. Missing metrics display
as unavailable, never as zero.

A row opens the selected run using a validated public run identity and a
stable detail URL. A run lacking detailed evidence still opens a truthful
identity/status view explaining what is unavailable; it does not disappear or
fall back to private storage. The detail view links back to its overview.
Neither navigation nor filtering constructs a workspace path from a run id.

### Strategy Research overview

The table presents run identity, strategy composition, dataset and instrument,
evaluation timeframe and interval, simulation and capital assumptions, trade
count, persisted performance/risk/cost KPIs, warnings and upstream verdict
where available. Visitors may sort by different eligible KPIs without the
dashboard selecting a universal winner.

A time-range/PnL view marks every run separately over its actual evaluation
interval. A run without usable PnL keeps its interval and status marker. The
view never connects separate runs into one equity curve or sums their PnL.
Absolute PnL carries its currency and capital basis; a normalized return is a
separate selectable measure only when persisted and meaningful. Material
differences in instrument, capital, costs and simulation assumptions remain
visible beside the chart and table.

### Signal Research overview

The table presents run identity, research question, Market and Signal Model
identities, dataset and instrument, evaluation interval and timeframe,
direction, outcome horizon, sample/completion counts, persisted outcome
measures and quality warnings. A cross-run chart may place one selected
eligible measure against research range or horizon.

Signal Research can contain several horizons and directions in one run.
Sorting and plotting therefore require an explicit metric, direction and
horizon slice, or another clearly labelled unit of comparison chosen by the
future PRD; the dashboard must not silently collapse them to one score per
run. Forward returns, drift and MFE/MAE are not Strategy Research PnL. The
Market Data identity on the combined Market and Signal page is not a research
result to rank.

## Strategy-defined analytical context

Evidence views must work with different Market Analysis components and model
expressions. They do not assume fixed volatility, trend or momentum labels,
a fixed number of states, or a particular indicator such as ATR. The stable
core shows each run's persisted facts and assumptions. Context-dependent views
appear only when the owning workflow has persisted a suitable context contract.

An entry's source is the Signal Model; market context comes from the Market
Model evaluation and its used components. A run-level `signal_model_id` or
`market_model_id` is an identity, normally constant within that run. Grouping
one run by that constant cannot yield meaningful entry or context buckets.
Conditional analysis needs observed values joined at a defined event time,
with model/component identity, resolved parameters, version, value type,
supported labels or units, availability time, sample coverage and missingness.
The dashboard does not infer entry reasons from a strategy name or invent tags
or state boundaries. Unused components and labels a component cannot emit are
not shown as observed context.

The owning research or analytics layer computes and persists new metrics,
state series, group results and their eligibility. The dashboard may filter,
sort and render these facts but does not import strategy code or research
engines, compute metrics or verdicts, or form implicit Cartesian combinations
of context dimensions. Only explicitly allowlisted, safe persisted fields may
enter the immutable public projection, consistent with [ADR-0034](../adr/ADR-0034-portfolio-publication-boundary.md)
and [ADR-0035](../adr/ADR-0035-complete-public-catalog-publication.md).

## Desired evidence views

These are product-level analytical questions to support across runs when the
required evidence is available. They are not a single mandated page layout.
A view with unmet data or eligibility conditions reports unavailability; it
does not substitute another workflow's metric.

| Surface | Desired view | Required evidence or condition |
|---|---|---|
| Market and Signal Research | Forward-drift heatmap by context and horizon | Persisted forward outcomes grouped by observed Market Model result or an explicitly named component state, with sample counts. |
| Market and Signal Research | Adjusted forward drift | Research-owned adjustment method, eligible sample counts and persisted adjusted measure; the dashboard applies no shrinkage. |
| Market and Signal Research | MFE/MAE relation | Persisted forward-excursion definition, denominator policy and eligibility. Trade-level excursion would be a separate Strategy Research measure. |
| Market and Signal Research | Context timeline | Dated Market Model results or values of used categorical components, with supported labels and missingness. A Boolean gate is not expanded into a fabricated regime taxonomy. |
| Market and Signal Research | Context persistence | Research-owned run lengths over the same context definition and evaluation grid as the timeline. |
| Strategy Research | Backtest assumptions and provenance | Safely publishable dataset, composition, period, execution and capital assumptions; display only fields actually persisted. |
| Strategy Research | KPI summary | Persisted performance, risk, activity and cost metrics with units, eligibility and warnings. |
| Strategy Research | Simulated equity and drawdown | Actual persisted simulation series, not overlapping forward-return pseudo-equity. |
| Strategy Research | Trade outcome distribution in R | Initial risk defined and persisted per trade. Otherwise offer a separately named PnL/return distribution when available. |
| Strategy Research | Conditional expectancy by market context | Research-owned event-time join, group and missing-context counts, metric values and eligibility; no empty group is represented as zero expectancy. |
| Strategy Research | Exit diagnostics | Persisted Exit Model reasons and associated trade outcomes rather than report-specific exit tags. |
| Strategy Research | Drawdown structure | Persisted episode depth, duration and recovery facts. Exact methodology and source-report semantics need review before PRD acceptance criteria are fixed. |
| Strategy Research | Capital and exposure | Persisted capital and position/exposure behavior with units and simulation assumptions. Exact panels and measures need review before PRD acceptance criteria are fixed. |
| Robustness Research | Rolling-window robustness | Correctly computed persisted windows, coverage, overlap policy and limitations; do not reuse the historical erroneous formula. |

The purpose-built simplified views in the accepted portfolio direction remain
distinct from these reusable technical evidence components. The selected
Signal, Strategy and Robustness views do not turn their independent workflows
into one mandatory research pipeline.

## Comparison and publication rules

Both overviews expose material compatibility differences before the visitor
interprets a sort or chart. Signal comparisons identify dataset, instrument,
time coverage, timeframe, direction, horizon, sample eligibility and metric
definition. Strategy comparisons identify those relevant inputs plus model
composition, capital basis, currency, cost model and simulation assumptions.
Visitors may inspect incompatible runs, but the UI states why direct
comparison is limited. Negative and incomplete evidence stays discoverable.

The public dashboard consumes only the immutable, deny-by-default projection
defined by accepted ADRs. A publisher may copy approved persisted facts; it
does not derive new research metrics or classifications. Public views never
read the private research workspace at request time, execute a strategy or
expose private configuration, source, binary models or storage paths.

## Questions for the future PRD

- Which workflow overviews and detail views form the first bounded delivery
  slice, and when should the Robustness view follow?
- What is the row and selection model for multi-horizon, multi-direction Signal
  runs? Which metrics are sortable within each explicit comparison slice?
- What is the default Strategy time-range/PnL presentation when currencies,
  starting capital or cost assumptions differ? How are runs without a usable
  metric marked on the same chart?
- Which public identity and routing contract opens a run's detail view,
  including incomplete or unsupported runs, and returns to the overview?
- Which event-time context artifacts are worth persisting, at what bounded
  resolution, and how are labels, units, missingness and publication safety
  validated?
- Which research-owned definitions and eligibility rules govern adjusted
  drift, MFE/MAE, R multiples, drawdown episodes, exposure and rolling windows?
  The source excerpt did not define the drawdown-structure and capital/exposure
  panels precisely.
- Which of these facts already exist in supported artifacts, and what minimum
  upstream analytics and public-projection work is needed for each slice?

This document records future direction. It does not approve a PRD, architecture
change, sprint or publication of new data. For current behavior, use the
[Dashboard Application reference](../reference/modules/DASHBOARD_APPLICATION.md);
for possible state families, use [Market Analysis Future](MARKET_ANALYSIS_FUTURE.md).
