# Research Data Strategy

This is the detailed planning record extracted from the accepted roadmap. Use [Roadmap](../ROADMAP.md) for phase status and navigation; use [Reference](../../reference/README.md) for current behavior.

# 14. Research Data Strategy

**Status:** ACCEPTED (2026-07-12)

## Purpose

The Market Data layer must **not** aim to collect every available market feed.

It must collect the **smallest set of source datasets** from which the framework can derive the largest number of analytical features.

Priorities:

- information density,
- research value,
- long-term maintainability,
- storage efficiency,
- vendor independence.

## Design Principles

### Store facts, not indicators

Persist raw market facts. Compute derived datasets internally.

Examples of derived data (not primary storage formats):

```text
Footprint, Delta, CVD, Volume Profile, Imbalance, Stacked Imbalance,
VWAP, ATR, Session statistics, Gamma Exposure, Dealer positioning
```

### Evaluate every new dataset

Each new source must justify itself:

- additional information,
- implementation complexity,
- storage requirements,
- acquisition cost,
- long-term usefulness.

## Target Research Scope

```text
Instruments:   ES / NQ futures (initial focus)
Style:         day trading
Holding time:  minutes to several hours
Not in scope:  HFT, nanosecond market reconstruction
```

## Futures Data

### Initial source dataset

Primary stored facts:

```text
OHLCV              (Phase 2A — Sprint 002)
Tick Trades        (Phase 2C — primary expansion target)
Instrument Definitions
Market Statistics
Market Status
```

**Tick Trades** are the primary source dataset for order-flow research.

From trades, derive internally:

```text
Footprint, Bid/Ask Delta, CVD, Volume Profile, Imbalance, Stacked Imbalance,
Absorption proxies, Session Delta, Large Trades, Execution statistics
```

### Level 1 Quotes

Secondary dataset. Enables spread, mid price, microprice, quote imbalance, slippage estimation.

### Level 2 Order Book (MBP-10)

**Initially rejected as a primary dataset.**

Reasons:

- ~2 TB/year for NQ (MBP-10),
- high storage cost,
- uncertain marginal research value for the target holding horizon.

Current decision:

- do not build the framework around MBP-10,
- validate research value on selected samples later,
- add only if measurable improvement is demonstrated.

## Order-Flow Philosophy

Reproduce analyses typically available in ATAS-class tooling.

Required analytical outputs (mostly reconstructible from Tick Trades without full L2 history):

```text
Footprint, Delta, CVD, Imbalance, Stacked Imbalance, Volume Profile,
Cluster Analysis, Absorption, Execution Analysis
```

## Options Data

Options are **independent market context**, not a substitute for futures order flow.

Preferred source: **option chain snapshots** (not raw option tick streams).

Preferred frequency: **1 minute**.

Required fields include timestamp, expiry, strike, call/put, bid, ask, volume, open interest, implied volatility, delta, gamma, theta, vega.

Derive internally:

```text
Gamma Exposure, Delta Exposure, Gamma Flip, Call Wall, Put Wall,
IV Surface, IV Skew, Term Structure, Dealer Positioning metrics
```

Raw option trade streams are currently unnecessary.

## Vendor Independence

Providers terminate at **importer boundaries** only. The framework must not depend on any vendor API at runtime.

```text
Databento DBN OHLCV  →  Importer  →  Canonical MarketBar   →  Published Dataset   (Phase 2B)
Databento DBN trades →  Importer  →  Canonical MarketTrade →  Published Dataset   (Phase 2C)
Sierra SCID          →  Importer  →  Canonical MarketTrade →  Published Dataset   (Phase 2C.2+)
```

Each path must produce identical internal models for the same fact type.

## Data Providers

### Futures — Phase 2B / 2C (archive import)

**Databento** — initial archive provider (**Phase 2B**).

Reasons: startup credits, Python API, DBN format, fast pipeline development, clean normalization.

Initial scope:

- archive import workflow on DBN OHLCV (Sprint 011 recommended slice),
- then `MarketTrade` import (**Phase 2C.1**),
- instrument definitions, validation and publication wiring.

### Futures — Phase 2C.2+ (historical expansion)

**Sierra Chart** — acquisition tool only, not a runtime dependency.

```text
Sierra  →  SCID  →  Importer  →  Canonical MarketTrade  →  Validation  →  Parquet  →  Published Dataset
```

Download once, convert once, store locally. Never depend on Sierra afterward.

### Options

**Intrinio** — preferred provider for option chain snapshots (Greeks, IV, open interest).

Plan: start with standard history (~5 years); purchase longer history (e.g. back to 2008) only after validating research value.

## Data Acquisition Roadmap

This is the **Data Capability Track** expansion sequence. It runs in parallel with Research and Execution tracks where dependencies allow.

| Roadmap phase | Provider | Scope | Purpose |
|---------------|----------|-------|---------|
| **2B** | Databento | DBN archive import foundation; first slice: OHLCV bars | Provider-independent import workflow; validate lifecycle on archives |
| **2C.1** | Databento | `MarketTrade` datasets, instrument definitions | Canonical trade model; orderflow input |
| **2C.2+** | Databento / Sierra | Quotes; optional bulk historical via Sierra SCID | Spread, microprice; one-time local archive expansion |
| **2D** | Intrinio | Option chain snapshots, Greeks, IV, OI | Options context research |

Phase 2B does not block Signal Research or Phase 6A Strategy Research on existing OHLCV. Trades and options extend analytical depth when ready (**§6**, **§15**).

## Architectural Principle

Maximize reusable information while minimizing external dependencies, storage and vendor lock-in.

The framework becomes more capable through **better analytical models**, not through continuously hoarding raw market data.

---
