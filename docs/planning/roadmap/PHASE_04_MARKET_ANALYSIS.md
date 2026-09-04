# Phase 4 Family — Market Analysis Capability

```text
Status: 4A COMPLETE / 4B PLANNED / 4C PLANNED
```

Full detail for `ROADMAP.md` §8 — this is the LIVE, canonically-updated location for this
phase; `ROADMAP.md` carries only a short pointer stub under the same section number.

**This file is expected to keep changing** as the phase progresses (Wave 0 decisions, sprint
openings, status flips). Unlike `docs/planning/ROADMAP_COMPLETED_PHASES.md` — which is
frozen history — edits to this phase's detail happen **HERE**, not by re-inflating the
`ROADMAP.md` stub.

Internal heading numbering is preserved exactly as it was in `ROADMAP.md`, so a citation of
the form `roadmap/PHASE_04_MARKET_ANALYSIS.md §8` resolves, matching the convention already
used in `ROADMAP_COMPLETED_PHASES.md`.

---

# 8. Market Analysis Capability — Phase 4 Family

## Purpose

Support timeframe-aware Market Analysis safely and reproducibly.

Phase 4 is a **family of increments**, not a single delivery:

```text
Phase 4A — Bar-Based and Multitimeframe Foundation     COMPLETE
Phase 4B — Orderflow Market Analysis                   PLANNED
Phase 4C — Options-Derived Market Analysis             PLANNED
```

Sprints 004–006 delivered Phase 4A. Sprints 007–010 belong to other phases (007 optional catalog; 008–010 Signal Research / Phase 5). Historical sprint files are not rewritten.

---

## Phase 4A — Bar-Based and Multitimeframe Foundation (COMPLETE)

### Sprint increments (historical)

| Sprint | Increment | Focus |
|--------|-----------|-------|
| 004 | Multitimeframe Foundation MVP | DONE — `SPRINT_004.md` |
| 005 | Calendar + Pivot + visual inspection | DONE — `SPRINT_005.md` |
| 006 | Declarative models | DONE — `SPRINT_006.md` |
| 007 | Research-enabling catalog (conditional) | SKIPPED — scope gate — `SPRINT_007.md` |

**Direction (binding for 004–006):** `docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md`

### Delivered capabilities

- source, computation and evaluation timeframe distinction,
- explicit resampling nodes,
- derived dataset lineage,
- `observed_at`,
- `available_at`,
- `LAST_CLOSED_BAR`,
- backward as-of alignment,
- intrabar component contract,
- Trading Session integration,
- Trading Calendar integration,
- controlled `MarketFieldReference`,
- Market Model expression evaluation,
- Signal Model expression evaluation,
- initial reusable Features, Structures and States.

## Suggested Initial Analytical Set

```text
Features:
- ATR
- slope
- wick ratio
- distance to level

Structures:
- Pivot
- HH / HL / LH / LL
- Session Range
- Liquidity Sweep

States:
- trend / range
- volatility state
- active session state
```

This is an initial research-enabling set, not a permanent mandatory taxonomy.

## Completion Criteria

- higher-timeframe final values are unavailable before bar close,
- resampling is explicit and reused,
- temporal alignment is covered by regression tests,
- DST and session boundaries are tested,
- Market Models and Signal Models remain declarative,
- models cannot access arbitrary DataFrames,
- one-condition Market and Signal Models are supported,
- framework and local components use the same public contracts.

## Dependencies

- Market Data MVP,
- Market Analysis Engine MVP,
- Time Model and calendars.

## Main Risks

- look-ahead bias,
- timestamp-boundary ambiguity,
- incorrect session semantics,
- mixing implementation patterns with output categories,
- excessive early taxonomy,
- divergence between Research and runtime semantics.

## Out of Scope (Phase 4A)

- unrestricted component grid searches,
- complete Strategy Research,
- live broker execution,
- orderflow and options-derived analysis (Phase 4B/4C).

---

## Phase 4B — Orderflow Market Analysis (PLANNED)

Orderflow belongs in **Market Analysis**, not Market Data storage of derived indicators.

```text
MarketTrade / MarketQuote (Phase 2C)
    ↓
Market Data normalization
    ↓
Market Analysis components
    ↓
orderflow Features / Structures / States
```

**Features (examples):** traded volume, buy/sell volume, delta, CVD, imbalance, execution intensity, large-trade concentration, absorption ratio.

**Structures (examples):** footprint bar, imbalance cluster, absorption event, aggressive sweep, volume node.

**States (examples):** buying/selling pressure, balanced flow, aggressive expansion, absorption, liquidity exhaustion.

Not one monolithic indicator or one giant DataFrame.

### Dependencies

- Phase 2C (`MarketTrade` minimum).

---

## Phase 4C — Options-Derived Market Analysis (PLANNED)

Interpretation of options context belongs in Market Analysis.

```text
OptionsSnapshot (Phase 2D)
    ↓
Options-derived Features
    ↓
Options Structures / States
    ↓
Market Model inputs
```

**Examples:** net gamma proxy, gamma concentration by strike, zero-gamma estimate, call/put wall, IV regime, expiration concentration, positioning state.

Market Models compose finished outputs (e.g. `negative_gamma_state AND price_below_zero_gamma`). Market Models do **not** compute GEX internally.

### Dependencies

- Phase 2D (options snapshots).
