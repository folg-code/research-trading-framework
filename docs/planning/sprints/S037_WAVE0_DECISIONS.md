# Sprint 037 — Wave 0 Decisions

Binding decisions for Component Libraries + DSL Simplification. Date: 2026-08-25.
Amended 2026-08-25 after maintainer Wave 0 discussion (scope option 2; strategy/ML continuity).

Basis: `S037_GATE.md`, maintainer track (audit → DSL/components → AI/ML), existing
`model_authoring` surface, engine catalog, and skipped Sprint 007 candidates.

---

## D-S037-01 — Problem statement

The engine can grow components today (S036 gate is open; compile is cheap). Authors cannot
yet use the full existing catalog from `model_authoring`, and the first research-enabling
Features from Sprint 007 were never built.

S037 closes that gap **without** changing IR, without Stage 4 `MarketFrame`, without a
training language, and without treating S007 as a mandate to ship every leftover name.

---

## D-S037-02 — Sprint branch and PR base

```text
Integration branch: sprint/component-libraries-dsl
Working branches:   feat/ | fix/ | docs/ | test/  (not nested under sprint/)
PR base:            sprint/component-libraries-dsl  (never main until sprint integration)
```

---

## D-S037-03 — Sprint slice (maintainer: option 2)

Gate §5 question 2. There is no pending named research experiment that requires a different
set. S007 names are **candidates**, not a dump.

**This sprint ships exactly:**

| Order | Slice | Why |
|-------|--------|-----|
| 1 | DSL for components that **already exist** | Authors describe high-level dependencies without IR |
| 2 | **One** new component: `trend.slope` | Thin causal Feature on close; same shelf ML will later consume as a named column |

**Not this sprint:** `structure.session_range`, wick ratio, distance-to-level, Trend State,
Liquidity Sweep. Session Range stays the natural **next** catalog PR after S037 (S007 Structure
gap; Sweep still waits for Range + levels).

`trend.slope` is the one new klocek (not Session Range) because it needs no session model and
fits one reviewable PR.

---

## D-S037-04 — DSL fill-in is Wave 1, not bundled

Gate §5 question 3.

ATR / true-range namespace functions, and the remaining **author-facing** swing outputs, ship
in their own PRs **before** `trend.slope`.

Do not hide ATR behind the slope PR. Authors should be able to write
`price.close > volatility.atr(period=14)` without waiting for slope.

Swing fill-in includes HH/HL/LH/LL **events** and **latest_*_level** outputs. It does **not**
expose observed-index internals (`*_observed_index`) unless a later component PR demonstrates
an author need.

---

## D-S037-05 — Slope contract (the one new component)

### Slope (`trend.slope`)

- Feature on **close** over `period` bars (ordinary least-squares slope per bar, causal window).
- Default `period` round-trips through `parameter_schema.canonicalize` (canonical default to
  pick in the component PR; 20 is the EMA precedent, not binding until schema lands).
- Do **not** add a generic “slope of any series” combinator in this sprint. Slope-of-EMA can
  be a later component that **depends on** `trend.ema` if a research question needs it.

### Deferred catalog notes (not S037 contracts)

Session Range, wick ratio, and distance-to-latest-swing-level remain S007 candidates for a
follow-on sprint. Do not start their PRs here.

---

## D-S037-06 — Correctness and library gates

Every new component PR must include `S037_GATE.md` §3.1 items.

Additionally:

- No new IR nodes without an ADR-0006 amendment and a reason a library function cannot
  express the idea.
- Public `evaluate_models` / `run_analysis` / `StrategyModelDefinition` contracts unchanged.
- Fixture research facts unchanged unless the PR adds a **new** model that did not exist.
- If `model_authoring/compile.py` changes, re-run
  `uv run python scripts/ops/bench_authoring_analysis_evaluate.py --json` and record
  `p1_compile` (must remain negligible vs `p2`; today ~0.2 ms).
- No `fit` / estimators / training APIs in `model_authoring`.

---

## D-S037-07 — Out of scope (this sprint)

- Session Range, wick ratio, distance-to-level, Trend State, Liquidity Sweep.
- Stage 3 / Stage 4 implementation (`available_at` column, lineage sidecar, `MarketFrame`).
- D-REP-04b / D-REP-06 storage changes.
- IDEA-014 training workflows, model registry, feature-vector product.
- Phase 4B / 6B / Replay, PBO/CSCV.
- New dunder operators, YAML/JSON dual source of truth, Polars/Python lambdas in models.
- `list[MarketBar]` on bulk compute paths; pandas; `pl.Decimal`.
- Dashboard visualization increment.
- Second session-resolver rewrite.

---

## D-S037-08 — Follow-on ownership

| Sprint / track | Owns |
|----------------|------|
| **037** | Existing-catalog DSL, `trend.slope`, copy-pasteable authoring example |
| Next catalog PRs | Session Range, then wick / distance; Trend State and Liquidity Sweep when a research question exists |
| Independent | Stage 3 availability/lineage; Stage 4 `MarketFrame` |
| After authoring UX is stable | Fitted States (IDEA-014): training workflow + artefact identity; strategy file still uses DSL |

---

## D-S037-09 — Discretionary and ML share one strategy surface

Maintainer intent (2026-08-25): rule-based and ML strategies are **written the same way**.

```text
Strategy Model = Market Model × Signal Model × Exit Model × Risk Model
Authors compose named catalog outputs in model_authoring (`when=...`).
```

A fitted model (XGBoost, regression, later a net) **enters as another catalog State or
Feature** — the same kind of klocek as `volatility.state` — not as a second Strategy type
and not as `fit` inside `when=`.

Training, labels, folds and artefact hashes live in a later research workflow. They are not
part of writing the strategy file. Live and historical evaluation consume the same
`StrategyModelDefinition`.

S037 does not implement IDEA-014. It only keeps the shelf consistent: every new output is a
named, causal, identity-bearing series that both a discretionary `when=` and a future
feature matrix can point at.

---

## Wave 0 checklist status

- [x] Confirm sprint branch: `sprint/component-libraries-dsl` (D-S037-02)
- [x] Slice: existing-catalog DSL, then **one** new component `trend.slope` (D-S037-03)
- [x] DSL fill-in is Wave 1, not bundled with slope (D-S037-04)
- [x] Discretionary and ML share Strategy Model + DSL (D-S037-09)
- [x] Confirm IR stays stable (D-S037-06)
- [x] Session Range / wick / distance / IDEA-014 training out of this sprint (D-S037-07)
