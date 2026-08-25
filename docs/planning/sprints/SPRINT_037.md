# Sprint 037 — Component Libraries + DSL Simplification

## Metadata

```text
Sprint: 037
Phase: Research authoring foundation (pre–AI/ML)
Status: IN_PROGRESS
Planned Start: 2026-08-25
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: S036 on main (#288); S037_GATE.md
Sprint Branch: sprint/component-libraries-dsl
Task branch convention: feat/ | fix/ | docs/ | test/
Wave 0 decisions: docs/planning/sprints/S037_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/sprints/S037_GATE.md
  - docs/adr/ADR-0006-declarative-market-and-signal-models.md
  - docs/adr/ADR-MA-002 / ADR-MA-010 / ADR-MA-014
  - docs/planning/sprints/SPRINT_007.md (skipped catalog candidates)
  - docs/reference/DATA_REPRESENTATION_AUDIT.md
```

---

## 0. Why this sprint

Sprint 036 measured the authoring → analysis → evaluate path and wrote the S037 gate.
Compile cost is definition-sized (~0.2 ms, flat in bar count). Catalog growth does **not**
wait for Stage 4 `MarketFrame`.

Today the engine catalog is five components (`volatility.true_range`, `volatility.atr`,
`volatility.state`, `trend.ema`, `structure.swing`) but the authoring DSL only exposes
`volatility.state`, `trend.ema`, and `structure.higher_low_event`. Sprint 007's
research-enabling set (slope, wick ratio, distance-to-level, Session Range) was skipped.

```text
existing catalog reachable from model_authoring
  -> first S007-class Features / Structure
  -> authors write models without importing model_expression
```

---

## 1. Goal

```text
Make the catalog grow as components + namespace functions
  -> fill DSL holes for components that already exist
  -> land the first research-enabling S007 pieces
  -> keep IR stable (ADR-0006)
```

Success (from `S037_GATE.md`): a maintainer can add a catalog component and a matching
`trend.foo(...)` (or `structure.` / `volatility.`) reference in one PR, and an author can
write a market + signal model using only `model_authoring` exports.

---

## 2. In scope

- Namespace functions for **existing** catalog outputs authors actually write
  (`volatility.atr`, `volatility.true_range`, remaining author-facing `structure.swing` events
  and latest levels).
- Shorter authoring docs: one copy-pasteable market + signal model that imports only
  `trading_framework.model_authoring`.
- New Market Analysis components that follow `S037_GATE.md` §3.1 (identity, schema, NumPy
  adapter, registry, DSL reference, tests).
- First new slice: **slope** Feature, then **Session Range** Structure, then **wick ratio**
  and **distance to latest swing level** if they stay one-PR each.
- Re-run `scripts/ops/bench_authoring_analysis_evaluate.py` if `model_authoring/compile.py`
  changes; `p1_compile` must stay negligible vs `p2`.

---

## 3. Out of scope

- New IR nodes, dunder operators, YAML/JSON as a second source of truth, Polars/Python
  lambdas in models (gate §2.3).
- Stage 3 `available_at` column / lineage sidecar; Stage 4 `MarketFrame` (independently
  sequenced).
- D-REP-04b `price_nanos`; D-REP-06 tz-aware Parquet.
- IDEA-014 / AI-ML; Phase 4B / 6B / Replay.
- Trend State and Liquidity Sweep (need a research question and extra contracts).
- Dashboard visualization increment (S007-T007); S006 inspection overlay is enough.
- New bulk consumers of `list[MarketBar]`; pandas; `pl.Decimal`.
- Second rewrite of the CME ES RTH session resolver.

---

## 4. Tasks

| ID | Task | Status |
|----|------|--------|
| S037-T001 | Wave 0: sprint branch, binding decisions, this file | DONE |
| S037-T002 | DSL fill-in: `volatility.atr` and `volatility.true_range` | TODO |
| S037-T003 | DSL fill-in: author-facing `structure.swing` events and latest levels (not index internals) | TODO |
| S037-T004 | Authoring docs: one copy-pasteable model using only `model_authoring` exports | TODO |
| S037-T005 | Feature `trend.slope` — OLS slope of close over `period` + DSL | TODO |
| S037-T006 | Structure `structure.session_range` — RTH session OHLC / range / completed + DSL | TODO |
| S037-T007 | Feature `price.wick_ratio` (or `volatility.wick_ratio`) + DSL | TODO |
| S037-T008 | Feature `structure.distance_to_latest_swing_*` composing existing swing levels + DSL | TODO |
| S037-T009 | Compile bench check if `compile.py` changed; `p1_compile` still negligible | TODO |
| S037-T010 | CURRENT_STATUS / ROADMAP closeout | TODO |

T007 and T008 may slip to a follow-on PR after Session Range if a single component PR exceeds
~400 meaningful lines. They must not invent a combinator language.

---

## 5. Suggested PR waves

Working PRs into `sprint/component-libraries-dsl` (never `main` until sprint integration):

1. Wave 0 decisions + this file (docs)
2. Volatility DSL fill-in (T002)
3. Swing DSL fill-in (T003) + authoring copy-paste example (T004) if they stay reviewable together; otherwise split
4. Slope Feature (T005)
5. Session Range Structure (T006)
6. Wick ratio and/or distance-to-level (T007–T008)
7. Bench confirmation + closeout (T009–T010)

One coherent catalog outcome per PR (gate §3.4). Target 100–400 meaningful lines.

---

## 6. Wave 0 decision checklist

- [x] Confirm sprint branch: `sprint/component-libraries-dsl`
- [x] First catalog slice: existing-catalog DSL, then slope, then Session Range
- [x] DSL fill-in is Wave 1, not bundled with the first new component
- [x] Confirm IR stays stable (ADR-0006)
- [x] Confirm Stage 3/4, IDEA-014, Trend State, Liquidity Sweep are out of this sprint

See `S037_WAVE0_DECISIONS.md` for D-S037-01 … D-S037-08.

---

## 7. Acceptance criteria

1. Gate rules in `S037_GATE.md` still hold (IR stable; no new operators; no `list[MarketBar]` bulk paths).
2. Existing catalog components that authors need are reachable from `model_authoring` namespaces.
3. At least **slope** and **Session Range** land as components + DSL + tests on the fixture harness path.
4. An authored market + signal model in docs/tests imports only `model_authoring` (no `model_expression`).
5. If compile changed, `p1_compile` remains negligible vs `p2` on `bench_authoring_analysis_evaluate.py`.
6. Quality gates pass.

---

## 8. Follow-on (not this sprint)

- Trend State and Liquidity Sweep when a concrete research question needs them.
- Stage 3 availability/lineage code; Stage 4 `MarketFrame`.
- AI/ML (IDEA-014) after authoring UX is stable.

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| New syntax disguised as helpers | Reject PRs that add IR nodes or dunder operators; namespace functions only |
| Waiting for MarketFrame | Gate forbids it; new batch components use the current view + NumPy adapter |
| Session Range rewrites the resolver | Consume S005 session metadata; do not change CME ES RTH mapping |
| Mega-component PRs | One component or tight family per PR; split if > ~400 lines |
