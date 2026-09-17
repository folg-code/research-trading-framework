# Phase 18 — Dashboard Research Evidence Views

Status: **DIRECTIONAL** — captured 2026-09-17. No increment has an accepted
PRD, ADR or sprint yet. This is the index for a phase that does not exist as
approved work; [Current Status](../CURRENT_STATUS.md) remains authoritative
for what is actually active.

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
| 18A Strategy Research evidence views | Backtest assumptions/provenance, KPI summary, simulated equity and drawdown | Directional — recommended first slice (see below) |
| 18B Signal Research evidence views | Workflow overview, forward-drift heatmap, adjusted forward drift, MFE/MAE relation, context timeline and persistence | Directional |
| 18C Strategy context and diagnostics | Conditional expectancy by market context, exit diagnostics, drawdown structure, capital and exposure | Directional; vision doc flags drawdown-structure and capital/exposure methodology as unresolved even at PRD-question level |
| 18D Robustness Research evidence view | Rolling-window robustness (correct formula, not the historical erroneous one) | Directional |

## Recommended sequencing

**18A first.** Its most direct data source is
[IDEA-027](../registries/idea-market-analysis.md#idea-027)'s not-yet-scheduled
Validation Approach: once that idea's components are implemented and its
validation series runs, it will produce new Strategy Research studies — the
successor to the now-superseded
[Sprint 063 draft](../../archive/superseded/SPRINT_063_STRATEGY_SIMULATION_SERIES.md),
which never ran. So 18A is the increment most likely to have real
persisted evidence to display without first resolving harder
multi-horizon/context-join questions. 18B/18C/18D remain unordered relative
to each other until 18A's PRD and delivery validate the pattern (routing,
comparison-compatibility disclosure, publication-safety review) that later
increments would reuse.

18C is explicitly the highest-uncertainty increment: the vision doc itself
notes drawdown-episode and capital/exposure semantics "need review before
PRD acceptance criteria are fixed" — its PRD cannot simply restate the
vision doc's table.

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

- [IDEA-027](../registries/idea-market-analysis.md#idea-027)'s not-yet-scheduled
  validation series is not a hard blocker for 18A's PRD work, but 18A has
  little to display without at least one published study first.
- No dependency on Phase 16E's Strategy Families machinery (PRB-020): 18A's
  data source is the existing single-run Strategy Research orchestration,
  the same one IDEA-027's validation series plans to use.

## Open questions before any PRD

Carried from the vision doc, scoped to whichever increment opens first:

- Which run identity/routing contract opens a run's detail view, including
  incomplete or unsupported runs, and returns to the overview?
- Which persisted fields already exist in supported artifacts today, versus
  requiring new upstream analytics or public-projection work?
- For 18A specifically: what is the default time-range/PnL presentation
  when currency, starting capital or cost assumptions differ across runs
  shown together?

## Review rule

Update this file's increment states after a material decision (a PRD
accepted, an increment's scope narrowed or dropped, or a maintainer
resequencing). Keep the source of truth for *why* a decision was made in
the relevant PRD or ADR, not here.
