# Phase 18 — Dashboard Research Evidence Views

Status: **DIRECTIONAL** — captured 2026-09-17, revised 2026-09-17. No
increment has an accepted PRD, ADR or sprint yet. This is the index for a
phase that does not exist as approved work; [Current Status](../CURRENT_STATUS.md)
remains authoritative for what is actually active.

**Revision note (2026-09-17):** this phase file and the vision doc it
extends were originally drafted assuming no evidence views existed yet. That
was wrong — `apps/dashboard` has shipped a partial Strategy Research page and
a richer Market/Signal Research page since 2026-09-11, reading real persisted
runs through the existing publication boundary. See the vision doc's
["Existing baseline"](../../vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md#existing-baseline-found-2026-09-17)
section. Sequencing below is revised accordingly: 18A/18B no longer need new
research runs to have something to display — they extend an existing
baseline — but per-row coverage still needs verifying against the real schema
before any PRD is written.

## Purpose

Extend the accepted [Portfolio Dashboard Development
Direction](../DASHBOARD_DEVELOPMENT_DIRECTION.md) with read-only analytical
evidence views for Signal Research, Strategy Research and Robustness
Research runs in the public dashboard (`apps/dashboard`), per
[`docs/vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md`](../../vision/DASHBOARD_RESEARCH_VIEWS_FUTURE.md)
(status: DRAFT, PRD scope not approved). The dashboard stays a read-only
consumer of persisted, safely projected evidence; it does not compute new
research metrics, classifications or verdicts, and it does not read the
private research workspace at request time (ADR-0022, ADR-0034, ADR-0035).

This phase is deliberately **not Phase 16E–16G**: those increments extend
research/analytics capability itself (Strategy Families, trade-outcome
models, promotion gates). Phase 18 only surfaces evidence that those and
existing workflows already persist. It does not depend on 16E–16G, and
16E–16G do not depend on it.

## Increment family

Increments are grouped by the vision doc's "Desired evidence views" table,
not by a fixed page layout. None is scheduled; each opens only after its own
PRD answers the relevant subset of the vision doc's "Questions for the
future PRD".

| Increment | Scope | State |
|---|---|---|
| 18A Strategy Research evidence views | All Strategy Research rows: backtest assumptions/provenance, full KPI summary, simulated equity and drawdown, PnL/return trade distribution, exit diagnostics, conditional expectancy by market context, drawdown structure, capital and exposure. Overview table + run selector, replacing the existing hardcoded single-run page. | **APPROVED (maintainer, 2026-09-18)** — [PRD](../../product/PRD-dashboard-strategy-research-evidence.md); Wave 0 complete and accepted ([decisions](PHASE_18_WAVE0_DECISIONS.md)); [Sprint 068](../sprints/SPRINT_068.md) (Milestone 1a) merged to `main` via #574; [Sprint 069](../sprints/SPRINT_069.md) (Milestone 1b) merged to `main` via #577; [Sprint 070](../sprints/SPRINT_070.md) (Milestone 2a: generic Strategy Research publisher, real `projection.json` regenerated) done, PR pending; Sprint N+3 (dashboard UI) not opened. Absorbs what this table previously called 18C — see that row. |
| 18B Signal Research evidence views | Workflow overview, forward-drift heatmap, adjusted forward drift, MFE/MAE relation, context timeline and persistence | Directional |
| ~~18C Strategy context and diagnostics~~ | ~~Conditional expectancy by market context, exit diagnostics, drawdown structure, capital and exposure~~ | **Folded into 18A (2026-09-18)** — these are all Strategy Research rows; the maintainer chose to scope them into 18A's PRD rather than as a separate increment. The methodology this row's "Directional" state used to flag as unresolved is now decided in 18A's PRD (Goals: Milestone 1). |
| 18D Robustness Research evidence view | Rolling-window robustness (correct formula, not the historical erroneous one) | Directional |

## Recommended sequencing

**18A first**, now as an extension of the existing
[`pages/6_Strategy_Research.py`](../../../apps/dashboard/pages/6_Strategy_Research.py)
baseline rather than a greenfield build — 3 Strategy Research runs are
already persisted and projected today, so 18A does not need
[IDEA-027](../registries/idea-market-analysis.md#idea-027)'s validation
series (now implemented as a component pack, see that idea's Review; its
Signal/Strategy Research validation runs remain a separate, unscheduled
follow-on and are **not** a dependency for 18A — dashboard work builds on
whatever evidence already exists, it does not commission new research).
18A's PRD (approved 2026-09-18) resolved this field-by-field: most Strategy
Research rows only needed publication-boundary and UI work because the data
already existed (`equity.parquet`, `trades.parquet`,
`summary_metrics.parquet`); three rows (conditional expectancy, drawdown
structure, capital/exposure — previously this table's 18C) needed genuinely
new research/analytics-layer artifacts with methodology decided directly
with the maintainer rather than left open. See the PRD's Goals for the
drawdown-episode definition, the generic categorical-context join, and the
notional-exposure-ratio formula. 18B is similarly an extension of
[`pages/4_Market_and_Signal_Research.py`](../../../apps/dashboard/pages/4_Market_and_Signal_Research.py),
still directional. 18D remains unordered until 18B's PRD validates the
pattern (routing, comparison-compatibility disclosure, publication-safety
review) that it would reuse.

## Binding rules for the whole phase

- Every increment needs its own accepted PRD before implementation; this
  phase file does not substitute for one, and no increment may open a
  sprint directly from this document.
- Only explicitly allowlisted, safely projected persisted fields may enter
  the public projection (ADR-0034, ADR-0035); a publisher copies approved
  facts, it does not derive new ones.
- No page assumes a fixed set of Market Analysis components, states or
  indicators — evidence views must work across differing model
  compositions, including ones introduced by future component work (e.g.
  [IDEA-027](../registries/idea-market-analysis.md#idea-027)).
- Negative, zero-trade, incomplete and unsupported runs are shown honestly;
  a missing metric displays as unavailable, never as zero, and sorting or
  charting a metric never constructs a ranking, promotion or live-edge
  claim.
- Material differences in dataset, instrument, capital, cost model and
  simulation assumptions must be visible beside any comparison, not
  papered over by the UI.

## Dependencies

- None blocking 18A or 18B: real persisted runs already exist and are
  already projected (`apps/dashboard/publication_data/`), and both
  increments extend an existing page rather than starting from nothing.
  [IDEA-027](../registries/idea-market-analysis.md#idea-027)'s validation
  series remains unscheduled and is not a dependency for either increment.
- No dependency on Phase 16E's Strategy Families machinery (PRB-020): 18A's
  data source is the existing single-run Strategy Research orchestration.

## Open questions before any PRD

Carried from the vision doc, scoped to whichever increment opens next
(18A's own instance of each is resolved — see its PRD's Goals/Open
questions):

- Which run identity/routing contract opens a run's detail view, including
  incomplete or unsupported runs, and returns to the overview? (18A answer:
  in-page selector state, no URL routing — no precedent for it existed in
  this Streamlit app; 18B/18D still need their own answer.)
- Which persisted fields already exist in supported artifacts today, versus
  requiring new upstream analytics or public-projection work? (18A answer:
  see its PRD's Problem section for the field-by-field split.)
- What is the default time-range/PnL presentation when currency, starting
  capital or cost assumptions differ across runs shown together? (18A
  answer: per-run interval marking, currency/capital-labeled absolute PnL,
  persisted `total_return` as the separate normalized measure — no new
  normalization logic invented.)

## Review rule

Update this file's increment states after a material decision (a PRD
accepted, an increment's scope narrowed or dropped, or a maintainer
resequencing). Keep the source of truth for *why* a decision was made in
the relevant PRD or ADR, not here.
