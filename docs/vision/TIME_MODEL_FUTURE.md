# Trading Research Framework

# TIME_MODEL_FUTURE.md

> **Sprint 055 T008 note:** this file is new. It consolidates
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §2.1, §2.4, §2.5 and §2.6 — the
> not-yet-built portion of the Time Model (calendars, holidays, and the
> as-built-vs-suggested gap in trading sessions). Calendars/holidays/sessions
> are a distinct domain (`src/trading_framework/time/`) and are the stated
> precondition for missing-range detection (see `MARKET_DATA_FUTURE.md`) —
> keeping them inside a market-data file would hide that dependency. Content
> below is preserved verbatim from `ARCHITECTURE_TECHNICAL.md`; only this
> header is newly authored. See
> `docs/planning/sprints/SPRINT_055_T002_VISION_TARGET_IA.md` and
> `SPRINT_055_T004_DECISIONS.md` for the rationale.

---

## 1. Purpose

The Time Model defines how the framework represents, normalizes, compares and interprets time.

Time handling affects:

- market data normalization,
- sessions,
- holidays,
- trading calendars,
- daylight saving time,
- futures contract rolls,
- Market Analysis,
- multitimeframe alignment,
- research,
- replay,
- Strategy Execution,
- reproducibility,
- look-ahead protection.

Time rules must be explicit.

No module may introduce an independent timezone convention.

---

## 2. Trading Sessions

*(Classified MIXED by Sprint 054 T002 — as-built status is nuanced, see
`docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
§2.4. A session protocol/contract exists (`time/sessions/protocol.py`), but
only one concrete session resolver is implemented (CME ES RTH); the other
named sessions below have no matching implementation.)*

A Trading Session is a configuration-driven time abstraction.

Suggested fields:

```text
id
name
timezone
start_time
end_time
weekdays
calendar_id
breaks
holiday_policy
```

Examples:

```text
Asia
London
New York
CME RTH
CME ETH
```

A Trading Session defines when a session exists.

It does not calculate:

- session high,
- session low,
- session midpoint,
- session range,
- session sweep.

These are Market Analysis outputs.

Rule:

```text
Time Model:
When does the session exist?

Market Analysis:
What happened during the session?
```

Hard-coded session-hour checks inside analytical components are prohibited.

---

## 3. Trading Calendars

*(Classified AMBIGUOUS by Sprint 054 T002 — as-built status unclear as of
Sprint 054, see
`docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
§2.5. No dedicated `Calendar` class or `time/calendars/` directory was
found; the one session resolver that exists is timezone/session-boundary
focused, not a separate generic calendar abstraction.)*

A Trading Calendar defines when a market is open.

Responsibilities include:

- trading days,
- weekends,
- holidays,
- shortened sessions,
- exchange closures,
- daylight saving transitions,
- session exceptions.

Examples:

```text
CME Calendar
NYSE Calendar
NASDAQ Calendar
Crypto 24/7 Calendar
Forex Calendar
```

The calendar abstraction must remain provider-independent.

External calendar libraries may be used behind adapters.

Domain and application code depend on framework contracts.

---

## 4. Holidays

*(Classified AMBIGUOUS by Sprint 054 T002 — as-built status unclear as of
Sprint 054, see
`docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
§2.6. No dedicated holiday-rule module or `holiday_policy` field was
located.)*

Holiday rules must be explicit and versionable.

They affect:

- expected market closures,
- missing-range detection,
- data completeness,
- session duration,
- resampling boundaries,
- research assumptions,
- Strategy Execution availability.

A known market closure must not be classified as missing data.

Holiday logic belongs to the calendar layer, not to analytical feature code.
