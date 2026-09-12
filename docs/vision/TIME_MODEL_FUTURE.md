# Time Model — Future Direction

Current UTC, Clock and multitimeframe alignment rules are in [Time and Alignment](../reference/system/TIME_AND_ALIGNMENT.md). This page describes broader session/calendar/holiday capabilities. The [pre-review snapshot](../archive/snapshots/TIME_MODEL_FUTURE_pre_review.md) preserves the earlier mixed current/future wording.

## Configurable sessions

A broader Trading Session contract may carry identity, timezone, open/close time, weekdays, calendar, breaks and holiday policy. It should represent when a session exists, not calculate session highs, lows, ranges or sweeps; those are Market Analysis outputs. Additional exchange or regional session definitions should be configuration-driven rather than hard-coded inside analytical components.

## Trading calendars

A provider-independent calendar abstraction should describe trading days, weekends, holidays, shortened sessions, exchange closures, daylight-saving transitions and exceptions. External calendar libraries may implement framework contracts behind adapters. Calendar version is material to reproducible research and dataset gap classification.

## Holidays and missing ranges

Holiday rules should be explicit and versionable. Known closures must not be classified as missing data. The same rules affect session duration, resampling boundaries, data completeness and Execution availability. [Market Data Future](MARKET_DATA_FUTURE.md) describes the planned missing-range resolver that depends on this capability.
