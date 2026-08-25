# Sprint 038 — Wave 0 Decisions

Binding decisions for Session Range. Date: 2026-08-25.
Locked 2026-08-25: maintainer chose **A** for D-S038-04 … D-S038-07.

Basis: `S037_GATE.md`, `SPRINT_007.md` Session Range semantics, ADR-MA-013, existing
`TradingSessionMetadata` / `AnalysisWorkspaceView`.

---

## D-S038-01 — Problem statement

Authors need a causal Session Range Structure for ES RTH research models. Sprint 005
already classifies bars (`trading_day`, `session_id`, `is_rth`). No catalog component
can read those columns: `AnalysisWorkspace` holds `session_metadata`, but
`AnalysisWorkspaceView.compute` does not receive it.

S038 adds **one** Structure and the minimum plumbing so that Structure can see injected
session metadata. It does **not** invent a new calendar and does not wait for
`MarketFrame`.

---

## D-S038-02 — Sprint branch and PR base

```text
Integration branch: sprint/session-range
Working branches:   feat/ | fix/ | docs/ | test/  (not nested under sprint/)
PR base:            sprint/session-range  (never main until sprint integration)
```

---

## D-S038-03 — Sprint slice

D-S037-08 already named Session Range as the next catalog increment, then wick /
distance.

**This sprint ships exactly:**

| Order | Slice | Why |
|-------|--------|-----|
| 1 | Session metadata on the component compute view | Blocker; no kernel can group sessions today |
| 2 | **One** Structure: `structure.session_range` + DSL | S007 outputs; same shelf as swing |

**Not this sprint:** wick ratio, distance-to-level, Trend State, Liquidity Sweep,
Globex/ETH calendar, IDEA-014.

---

## D-S038-04 — How compute sees session metadata (locked: A)

Fact: `ComponentImplementation.compute` receives `AnalysisWorkspaceView`
(`market` OHLCV arrays + dependency results). Session columns are not on that view.

**Locked:** add optional `session_metadata: TradingSessionMetadata | None` to
`AnalysisWorkspaceView` and pass it from `view_for()`. Session Range fails closed if
it is `None`. Other components ignore it.

The workspace also keeps the injected `TradingSessionResolver` so HTF views can
re-resolve (D-S038-07). Evaluation-grid metadata already resolved in `run_analysis`
is reused as-is (holidays preserved). Do **not** re-resolve inside the NumPy kernel
and do **not** flatten session columns onto `AnalysisDataView`.

---

## D-S038-05 — Running vs final outputs (locked: A)

S007: distinguish live/incomplete session values from **final** values; final high/low
unavailable before session end. Follow ADR-MA-009 (no third availability story).

Author-facing names stay the S007 set: `session_open`, `session_high`, `session_low`,
`session_close`, `session_range`, `session_completed`.

**Locked:** named OHLC/range outputs are **running** (causal, forward-filled inside the
RTH group). `session_completed` is 1.0 only on the last RTH bar of a `trading_day`
group that has a later bar proving the group ended (next bar `is_rth=False` or a new
`trading_day`). An in-progress session at the end of the series stays 0.0. No
separate `*_final` outputs this sprint. Authors who need “only after the bell”
compose with `session_completed`.

Do not write final extrema back onto earlier bars (PHASE_4_5 lookahead-free
integration).

---

## D-S038-06 — OUTSIDE_RTH bars (locked: A)

Resolver `session_id` is `"ES_RTH"` or `"OUTSIDE_RTH"` — **not** a per-day instance key.
Grouping is `(trading_day, is_rth=True)` for RTH range.

**Locked:** on `is_rth=False` bars, all Session Range outputs are NaN (RTH-only
structure). Do not carry overnight. Do not treat `OUTSIDE_RTH` as its own session
group.

---

## D-S038-07 — Computation grid / MTF (locked: A)

Session metadata is resolved today on the **evaluation-grid** timestamps (usually 1m)
in `run_analysis`. Resample is UTC buckets, not session-boundary aware.

**Locked:** Session Range accumulates on the component `computation_timeframe` bars.
Session labels for a resampled view are **re-resolved** from those bars’ timestamps
with the same resolver as `run_analysis`. A 5m `session_high` uses 5m bar highs.

Cache per resample identity so `view_for()` does not re-resolve on every component.

---

## D-S038-08 — Kernel engine

Follow `S037_GATE.md` §3.3: NumPy adapter, no `list[MarketBar]` bulk path, no
`MarketFrame` migration.

**Locked default:** single-pass NumPy scan (same family as swing running state). Polars
`group_by` is allowed in tests as a golden check, not as the CI reference kernel.

This is **not** a performance sprint. Do not fuse or rewrite `CmeEsRthSessionResolver`.

---

## Wave 0 checklist status

- [x] Confirm sprint branch: `sprint/session-range` (D-S038-02)
- [x] Slice: Session Range only (D-S038-03)
- [x] D-S038-04 plumbing A
- [x] D-S038-05 running vs final A
- [x] D-S038-06 OUTSIDE_RTH A
- [x] D-S038-07 computation grid A
- [x] NumPy scan default (D-S038-08)
