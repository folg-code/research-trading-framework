# Sprint 037 — Wave 0 Decisions

Binding decisions for Component Libraries + DSL Simplification. Date: 2026-08-25.

Basis: `S037_GATE.md`, maintainer track (audit → DSL/components → AI/ML), existing
`model_authoring` surface, engine catalog, and skipped Sprint 007 candidates.

---

## D-S037-01 — Problem statement

The engine can grow components today (S036 gate is open; compile is cheap). Authors cannot
yet use the full existing catalog from `model_authoring`, and the first research-enabling
Features/Structures from Sprint 007 were never built.

S037 closes that gap **without** changing IR, without Stage 4 `MarketFrame`, and without
treating S007 as a mandate to ship every leftover name.

---

## D-S037-02 — Sprint branch and PR base

```text
Integration branch: sprint/component-libraries-dsl
Working branches:   feat/ | fix/ | docs/ | test/  (not nested under sprint/)
PR base:            sprint/component-libraries-dsl  (never main until sprint integration)
```

Slug answers gate §5 question 1. It names the outcome, not the task IDs.

---

## D-S037-03 — First catalog slice

Gate §5 question 2: S007 leftovers vs a named next experiment.

There is **no** pending named research experiment that requires a different set. Sprint 008
already ran on the current five-component catalog. S037 therefore takes the S007
research-enabling set as **candidates**, not a dump:

| Order | Slice | Why this order |
|-------|--------|----------------|
| 1 | DSL for components that **already exist** | Unblocks authors immediately; no new identity/schema work |
| 2 | `trend.slope` (Feature, OLS of close over `period`) | Thin transform of price; no session model; composition-friendly |
| 3 | `structure.session_range` (Structure) | Uses S005 `TradingSessionMetadata`; was the S007 Structure gap |
| 4 | wick ratio, then distance to latest swing level | In-sprint if each stays one PR; otherwise follow-on |

**Not this sprint:** Trend State (definition still open: EMA-sign vs HH/HL sequence) and
Liquidity Sweep (S007 deferred until Session Range + levels exist — Session Range lands
here; Sweep still waits for a research question).

---

## D-S037-04 — DSL fill-in is Wave 1, not bundled

Gate §5 question 3.

**Decision:** ATR / true-range namespace functions, and the remaining **author-facing**
swing outputs, ship in their own PRs **before** the first new component.

Do not hide ATR behind a new Feature PR. Authors should be able to write
`price.close > volatility.atr(period=14)` without waiting for slope.

Swing fill-in includes HH/HL/LH/LL **events** and **latest_*_level** outputs. It does
**not** expose observed-index internals (`*_observed_index`) unless a later component PR
demonstrates an author need.

---

## D-S037-05 — Slope and Session Range contracts (Wave 0 shape)

### Slope (`trend.slope`)

- Feature on **close** over `period` bars (ordinary least-squares slope per bar, causal window).
- Default `period` round-trips through `parameter_schema.canonicalize` (canonical default to
  pick in the component PR; 20 is the EMA precedent, not binding until schema lands).
- Do **not** add a generic “slope of any series” combinator in this sprint. Slope-of-EMA can
  be a later component that **depends on** `trend.ema` if a research question needs it.

### Session Range (`structure.session_range`)

- Consumes S005 session metadata (`trading_day` / `session_id` / `is_rth`). CME ES RTH only
  for MVP, matching the existing resolver.
- Distinguish **incomplete** (live session) vs **completed** session high/low/close.
  Final high/low of the session are unavailable before session end (S007 semantics).
- Do not rewrite `cme_es_rth` mapping in this sprint (gate: residual timezone pass is not
  S037 work).

### Wick ratio and distance-to-level

- Wick ratio is an OHLC Feature (no new session model).
- Distance-to-level **composes** existing `structure.swing` latest levels (close vs
  `latest_swing_high_level` / `latest_swing_low_level`). No mini-language of combinators.

---

## D-S037-06 — Correctness and library gates

Every new component PR must include `S037_GATE.md` §3.1 items.

Additionally:

- No new IR nodes without an ADR-0006 amendment and a reason a library function cannot
  express the idea.
- Public `evaluate_models` / `run_analysis` contracts unchanged.
- Fixture research facts unchanged unless the PR adds a **new** model that did not exist.
- If `model_authoring/compile.py` changes, re-run
  `uv run python scripts/ops/bench_authoring_analysis_evaluate.py --json` and record
  `p1_compile` (must remain negligible vs `p2`; today ~0.2 ms).

---

## D-S037-07 — Out of scope (this sprint)

- Stage 3 / Stage 4 implementation (`available_at` column, lineage sidecar, `MarketFrame`).
- D-REP-04b / D-REP-06 storage changes.
- IDEA-014, Phase 4B / 6B / Replay, PBO/CSCV.
- New dunder operators, YAML/JSON dual source of truth, Polars/Python lambdas in models.
- `list[MarketBar]` on bulk compute paths; pandas; `pl.Decimal`.
- Trend State, Liquidity Sweep, dashboard visualization increment.
- Second session-resolver rewrite.

---

## D-S037-08 — Follow-on ownership

| Sprint / track | Owns |
|----------------|------|
| **037** | DSL fill-in, slope, Session Range, optional wick/distance, authoring docs |
| Later catalog PRs | Trend State, Liquidity Sweep, slope-of-EMA if needed |
| Independent | Stage 3 availability/lineage; Stage 4 `MarketFrame` |
| After authoring UX is stable | AI/ML (IDEA-014) |

---

## Wave 0 checklist status

- [x] Confirm sprint branch: `sprint/component-libraries-dsl` (D-S037-02)
- [x] First catalog slice: existing DSL, then slope, then Session Range (D-S037-03)
- [x] DSL fill-in is Wave 1, not bundled with the first new component (D-S037-04)
- [x] Confirm IR stays stable (D-S037-06)
- [x] Confirm Stage 3/4, IDEA-014, Trend State, Liquidity Sweep out of sprint (D-S037-07)
