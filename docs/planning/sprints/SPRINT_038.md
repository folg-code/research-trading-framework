# Sprint 038 — Session Range Structure

## Metadata

```text
Sprint: 038
Phase: Research authoring catalog (pre–AI/ML)
Status: WAVE 0 OPEN (maintainer lock pending)
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
pass it through. That plumbing is in scope and **needs a maintainer lock** before
implementation.

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

## 2. In scope (after Wave 0 lock)

- Pass Sprint 005 session metadata into component compute (contract change; option in
  `S038_WAVE0_DECISIONS.md`).
- Structure `structure.session_range` / implementation `numpy.session_range`.
- Author-facing outputs from S007: `session_open`, `session_high`, `session_low`,
  `session_close`, `session_range`, `session_completed`.
- Distinguish live/incomplete running values from final values (how is a Wave 0 fork).
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
| S038-T001 | Wave 0: sprint branch, this file, maintainer lock | IN PROGRESS |
| S038-T002 | Session metadata on the component compute view | BLOCKED on Wave 0 |
| S038-T003 | Structure `structure.session_range` + NumPy kernel | BLOCKED on Wave 0 |
| S038-T004 | `model_authoring` structure namespace functions | BLOCKED on Wave 0 |
| S038-T005 | Catalog docs + authored model on the fixture path | BLOCKED on Wave 0 |
| S038-T006 | CURRENT_STATUS / ROADMAP closeout | BLOCKED on Wave 0 |

Suggested PR waves (into `sprint/session-range`, never `main` until integration):

1. Wave 0 decisions + this file (docs)
2. Workspace-view plumbing (T002) — only after lock
3. Component + kernel + tests (T003)
4. DSL + catalog example (T004–T005)
5. Closeout (T006)

One coherent catalog outcome per PR. Target 100–400 meaningful lines.

---

## 5. Wave 0 decision checklist

- [x] Confirm sprint branch: `sprint/session-range` (proposed D-S038-02)
- [x] Slice: Session Range only; wick / distance stay follow-on (proposed D-S038-03)
- [ ] Lock session-metadata plumbing (D-S038-04)
- [ ] Lock running vs final outputs (D-S038-05)
- [ ] Lock OUTSIDE_RTH policy (D-S038-06)
- [ ] Lock computation grid / MTF (D-S038-07)

See `S038_WAVE0_DECISIONS.md`. Do not start T002–T005 until the four locks land.

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
