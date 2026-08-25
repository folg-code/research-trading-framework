# Sprint 038 — Wave 0 Decisions

Binding decisions for Session Range. Date: 2026-08-25.

**Lock status:** D-S038-01 … D-S038-03 are proposed from already-binding S037 follow-on
and S007 semantics. **D-S038-04 … D-S038-07 are not locked** — they change the compute
contract, lookahead, or session grouping. Implementation of T002–T005 waits on those
four maintainer answers.

Basis: `S037_GATE.md`, `SPRINT_007.md` Session Range semantics, ADR-MA-013, existing
`TradingSessionMetadata` / `AnalysisWorkspaceView`.

---

## D-S038-01 — Problem statement (proposed)

Authors need a causal Session Range Structure for ES RTH research models. Sprint 005
already classifies bars (`trading_day`, `session_id`, `is_rth`). No catalog component
can read those columns: `AnalysisWorkspace` holds `session_metadata`, but
`AnalysisWorkspaceView.compute` does not receive it.

S038 adds **one** Structure and the minimum plumbing so that Structure can see injected
session metadata. It does **not** invent a new calendar and does not wait for
`MarketFrame`.

---

## D-S038-02 — Sprint branch and PR base (proposed)

```text
Integration branch: sprint/session-range
Working branches:   feat/ | fix/ | docs/ | test/  (not nested under sprint/)
PR base:            sprint/session-range  (never main until sprint integration)
```

---

## D-S038-03 — Sprint slice (proposed)

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

## D-S038-04 — How compute sees session metadata (PENDING)

Fact: `ComponentImplementation.compute` receives `AnalysisWorkspaceView`
(`market` OHLCV arrays + dependency results). Session columns are not on that view.

| Option | Change | Cost |
|--------|--------|------|
| **A (recommended)** | Add optional `session_metadata: TradingSessionMetadata \| None` to `AnalysisWorkspaceView` and pass it from `view_for()`. Session Range fails closed if it is `None`. Other components ignore it. | Small public compute-contract extension; preserves resolver injection (holidays). |
| B | Re-resolve `CmeEsRthSessionResolver` inside the kernel from `market.timestamps`. | Duplicates the resolver; drops holiday / alternate resolver injection. |
| C | Flatten `trading_day` / `is_rth` onto `AnalysisDataView`. | Widens the OHLCV view for every consumer; larger than needed. |

HTF note: if Session Range runs on a resampled view, option A must also say whether
metadata is re-resolved on HTF timestamps or downsampled from the evaluation grid
(see D-S038-07).

**Maintainer: pick A, B, or C.**

---

## D-S038-05 — Running vs final outputs (PENDING)

S007: distinguish live/incomplete session values from **final** values; final high/low
unavailable before session end. Follow ADR-MA-009 (no third availability story).

Author-facing names stay the S007 set: `session_open`, `session_high`, `session_low`,
`session_close`, `session_range`, `session_completed`.

| Option | Semantics |
|--------|-----------|
| **A (recommended)** | Named OHLC/range outputs are **running** (causal, forward-filled inside the RTH group). `session_completed` is 1.0 only on/after the last RTH bar of that `trading_day` that the series contains. No separate `*_final` outputs this sprint. Authors who need “only after the bell” compose with `session_completed`. |
| B | Add extra `session_high_final` / `session_low_final` / `session_close_final` that stay NaN until the session is complete (retrospective). Running series still exist under the S007 names. |

Do not write final extrema back onto earlier bars (PHASE_4_5 lookahead-free integration).

**Maintainer: pick A or B.**

---

## D-S038-06 — OUTSIDE_RTH bars (PENDING)

Resolver `session_id` is `"ES_RTH"` or `"OUTSIDE_RTH"` — **not** a per-day instance key.
Grouping is `(trading_day, is_rth=True)` for RTH range.

| Option | On `is_rth=False` bars |
|--------|-------------------------|
| **A (recommended)** | All Session Range outputs are NaN (RTH-only structure). |
| B | Carry the last **completed** RTH session’s values through overnight (stateful overnight). |
| C | Treat `OUTSIDE_RTH` as its own session group (ETH/Globex range). That is a different session model; S037_GATE forbids a second resolver rewrite unless this option is chosen. |

**Maintainer: pick A, B, or C.**

---

## D-S038-07 — Computation grid / MTF (PENDING)

Session metadata is resolved today on the **evaluation-grid** timestamps (usually 1m)
in `run_analysis`. Resample is UTC buckets, not session-boundary aware. HTF components
see resampled OHLCV without session columns.

| Option | Where Session Range accumulates |
|--------|----------------------------------|
| **A (recommended)** | On the component `computation_timeframe` bars, with session labels **re-resolved** from those bars’ timestamps (same resolver as `run_analysis`). 5m `session_high` uses 5m bar highs. |
| B | Always accumulate on the evaluation grid (1m), then align to HTF with existing `LAST_CLOSED_BAR`. 5m models still see 1m-accurate session extrema. |
| C | MVP: Session Range is evaluation-grid only; referencing it on a coarser `timeframe=` is an error until a later PR. |

**Maintainer: pick A, B, or C.**

---

## D-S038-08 — Kernel engine (proposed default)

Follow `S037_GATE.md` §3.3: NumPy adapter, no `list[MarketBar]` bulk path, no
`MarketFrame` migration.

**Proposed:** single-pass NumPy scan (same family as swing running state). Polars
`group_by` is allowed in tests as a golden check, not as the CI reference kernel.

This is **not** a performance sprint. Do not fuse or rewrite `CmeEsRthSessionResolver`
unless D-S038-06 option C is chosen.

---

## Wave 0 checklist status

- [x] Confirm sprint branch: `sprint/session-range` (D-S038-02 proposed)
- [x] Slice: Session Range only (D-S038-03 proposed)
- [ ] D-S038-04 plumbing A / B / C
- [ ] D-S038-05 running vs final A / B
- [ ] D-S038-06 OUTSIDE_RTH A / B / C
- [ ] D-S038-07 computation grid A / B / C
- [x] NumPy scan default (D-S038-08 proposed; override if a performance fork is wanted)
