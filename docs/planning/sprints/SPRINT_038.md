# Sprint 038 — Session Range Structure

## Metadata

```text
Sprint: 038
Phase: Research authoring catalog (pre–AI/ML)
Status: WAVE 0 LOCKED (A/A/A/A); implementation in progress
Planned Start: 2026-08-25
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: S037 on main (#296); S037_GATE.md; SPRINT_005 session metadata
Sprint Branch: sprint/session-range
Task branch convention: feat/ | fix/ | docs/ | test/
Wave 0 decisions: docs/planning/sprints/S038_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/sprints/S037_GATE.md (catalog PR rules still binding)
  - docs/planning/sprints/SPRINT_007.md (Session Range semantics)
  - docs/planning/sprints/S037_WAVE0_DECISIONS.md (D-S037-08 follow-on)
  - docs/adr/ADR-0005 / ADR-MA-002 / ADR-MA-009 / ADR-MA-010 / ADR-MA-013 / ADR-MA-014
  - docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
```

---

## 0. Why this sprint

Sprint 037 made the existing catalog reachable from `model_authoring` and landed
`trend.slope`. The next S007 Structure is **Session Range**: running (and completed)
RTH open/high/low/close/range on Sprint 005 session metadata.

No catalog component can read that metadata today. `AnalysisWorkspace` stores
`TradingSessionMetadata`, but `AnalysisWorkspaceView` (the compute contract) does not
pass it through. Wave 0 locked option A: pass metadata on the compute view.

```text
Sprint 005 session metadata on the analysis workspace
  -> structure.session_range (causal running OHLC + completed flag)
  -> model_authoring structure.* references
```

---

## 1. Goal

```text
Authors can write market/signal models against Session Range
  using only trading_framework.model_authoring
  without constructing IR and without a new session calendar
```

Success: one Structure `structure.session_range` + NumPy implementation + DSL, evaluated
on the fixture path with `CmeEsRthSessionResolver`. Gate `S037_GATE.md` §3.1 still holds.

---

## 2. In scope

- Pass Sprint 005 session metadata into component compute (`AnalysisWorkspaceView`,
  D-S038-04 A). Keep the resolver on the workspace for HTF re-resolve (D-S038-07 A).
- Structure `structure.session_range` / implementation `numpy.session_range`.
- Author-facing outputs from S007: `session_open`, `session_high`, `session_low`,
  `session_close`, `session_range`, `session_completed`.
- Running OHLC/range; `session_completed` only on a confirmed-ended RTH group
  (D-S038-05 A). OUTSIDE_RTH bars are NaN (D-S038-06 A).
- Registry, catalog docs, DSL namespace functions, tests on the fixture harness path.
- Clear failure when Session Range is requested but no session resolver was attached.

---

## 3. Out of scope

- Wick ratio, distance-to-level, Trend State, Liquidity Sweep.
- New IR nodes, dunder operators, YAML/JSON as a second source of truth.
- Stage 3 `available_at` column / lineage sidecar; Stage 4 `MarketFrame`.
- Second session-resolver rewrite (Globex, ETH, crypto 24h, PRB-007 remainder).
- IDEA-014 training / `fit` in DSL.
- Dashboard visualization increment (S007-T007).
- New bulk consumers of `list[MarketBar]`; pandas; `pl.Decimal`.

---

## 4. Tasks

| ID | Task | Status |
|----|------|--------|
| S038-T001 | Wave 0: sprint branch, this file, maintainer lock | DONE |
| S038-T002 | Session metadata on the component compute view | DONE |
| S038-T003 | Structure `structure.session_range` + NumPy kernel | DONE |
| S038-T004 | `model_authoring` structure namespace functions | DONE |
| S038-T005 | Catalog docs + authored model on the fixture path | DONE |
| S038-T006 | CURRENT_STATUS / ROADMAP closeout | TODO |

Suggested PR waves (into `sprint/session-range`, never `main` until integration):

1. Wave 0 decisions + this file (docs)
2. Workspace-view plumbing (T002) — only after lock
3. Component + kernel + tests (T003)
4. DSL + catalog example (T004–T005)
5. Closeout (T006)

One coherent catalog outcome per PR. Target 100–400 meaningful lines.

---

## 5. Wave 0 decision checklist

- [x] Confirm sprint branch: `sprint/session-range` (D-S038-02)
- [x] Slice: Session Range only; wick / distance stay follow-on (D-S038-03)
- [x] Lock session-metadata plumbing (D-S038-04 A)
- [x] Lock running vs final outputs (D-S038-05 A)
- [x] Lock OUTSIDE_RTH policy (D-S038-06 A)
- [x] Lock computation grid / MTF (D-S038-07 A)

See `S038_WAVE0_DECISIONS.md`.

---

## 6. Acceptance criteria

1. `S037_GATE.md` §3.1 holds (identity, schema, NumPy adapter, registry, DSL, tests).
2. Authors can reference Session Range from `model_authoring` only.
3. Running values do not leak final high/low before session end (S007).
4. Grouping uses `(trading_day, is_rth)`, not `session_id` alone (`session_id` is
   `"ES_RTH"` / `"OUTSIDE_RTH"`, not a per-day key).
5. Quality gates pass.

---

## 7. Follow-on (not this sprint)

- Wick ratio, then distance-to-level.
- Trend State and Liquidity Sweep when a research question exists.
- Fitted catalog States (IDEA-014).
- Stage 3 / Stage 4 implementation.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Components cannot see session columns | D-S038-04 — do not re-resolve inside the kernel by default |
| Grouping by `session_id` merges all RTH days | Bind `(trading_day, is_rth)` in the kernel contract |
| HTF Session Range uses 5m extrema, not 1m | D-S038-07 |
| Lookahead on “final” high/low | D-S038-05; follow MA-009 |
| Polars groupby as a new kernel engine | Stay on NumPy scan unless maintainer picks otherwise |
