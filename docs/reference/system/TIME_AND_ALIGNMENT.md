# Time and Alignment — As-Built Reference

> Merged from the former `docs/reference/system/ARCHITECTURE_TECHNICAL.md`
> ("Time Model": Timestamp Policy, Timezone Policy, Futures Contract Rolls,
> Clock Abstraction, Observed Time and Available Time, Time Model Rules) and
> the former `docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md`
> ("Multitimeframe Architecture", "Resampling", "Temporal Alignment and
> Look-Ahead Protection") by Sprint 055 T007, per the maintainer-approved
> merge in `docs/archive/phases/cross-cutting/SPRINT_055_T004_DECISIONS.md` §1. Per
> T001's dedup policy, the longer/more-complete version of each duplicated
> section (both files independently state `observed_at`/`available_at`
> semantics) is kept verbatim as the body, with genuinely unique material
> from the other copy appended — no paraphrasing. Both source files
> originated in `docs/vision/` and were moved into `docs/reference/` by
> Sprint 054 T002/T004; the CURRENT/MIXED as-built classification notes from
> that move are preserved below.
>
> The Market Analysis engine's non-time responsibilities (component
> contract, registry, DAG, cache) live in
> [`MARKET_ANALYSIS_ARCHITECTURE.md`](MARKET_ANALYSIS_ARCHITECTURE.md).

---

## Timestamp Policy

All internal timestamps must be timezone-aware.

The canonical internal representation is:

```text
UTC
```

Correct:

```python
datetime(..., tzinfo=timezone.utc)
```

Incorrect:

```python
datetime(...)
```

Every timestamp entering the framework must be normalized before it reaches domain logic.

---

## Timezone Policy

The framework follows:

```text
UTC internally
Local or exchange time only at boundaries
```

Boundaries include:

- provider adapters,
- broker adapters,
- user interfaces,
- reports,
- exchange calendar definitions,
- configuration files.

Provider-specific timestamps must be converted to UTC during normalization.

The original timezone and conversion assumptions should be retained in metadata where relevant.

---

## Futures Contract Rolls

> As-built note: the Contract-vs-Continuous-Dataset distinction and the roll
> workflow are implemented (`application/market_data/build_roll_schedule.py`,
> `application/market_data/derive_continuous_ohlcv.py`,
> `infrastructure/storage/{roll_schedule_manifest_store,roll_schedule_repository,continuous_manifest_store}.py`).
> The exact named metadata fields below were not individually diffed against
> the roll schedule schema — field-level parity is unverified.

The framework distinguishes:

```text
Contract Dataset
```

from:

```text
Continuous Futures Dataset
```

Examples:

```text
NQM26
NQU26
NQ Continuous
```

Contract-roll metadata should include:

```text
source_contract
destination_contract
roll_timestamp
roll_policy
roll_trigger
adjustment_method
adjustment_value
construction_version
```

Roll logic must not be hidden inside provider adapters.

Continuous futures are explicit derived datasets.

---

## Clock Abstraction

> As-built note: the `Clock` protocol and `SystemClock`/`FixedClock` are
> implemented (`time/clocks/{protocol,system,fixed}.py`,
> `tests/unit/test_clocks.py`). `ResearchClock` and `ReplayClock` have no
> matching implementation, consistent with Replay Execution itself being
> unbuilt (see `docs/vision/MARKET_DATA_FUTURE.md` §3.16 and
> `docs/vision/EXECUTION_RUNTIME_FUTURE.md` §7.3, both merged from former
> `ARCHITECTURE_TECHNICAL.md` by Sprint 055 T008).

Time-dependent application and Strategy Execution logic depend on a `Clock` contract.

Conceptual example:

```python
class Clock(Protocol):
    def now(self) -> datetime:
        ...
```

Possible implementations:

```text
SystemClock
FixedClock
ResearchClock
ReplayClock
```

Direct use of `datetime.now()` inside domain and application logic is forbidden.

---

## Multitimeframe Architecture

### Core Principle

Multitimeframe is not a special strategy type and not a special Market Model type.

It is a natural property of analytical component requests.

Each Market Analysis component may be instantiated on a selected timeframe.

Example:

```text
Trend State 4h
Volatility Regime 1h
Structural State 30m
Price Above VWAP 1m
```

Market and Signal Models may compose these outputs without requiring separate multitimeframe logic.

### Timeframe Is Part of Component Identity

Current computation identity includes material timeframe information; one
component can be requested at multiple timeframes without creating a separate
component class for each. `market_analysis/identity/computation.py` and
`mtf.py` define the implemented keys. Resampling/alignment policy and calendar
version are not all fields of one current public identity object; see
[Market Analysis Future](../../vision/MARKET_ANALYSIS_FUTURE.md) for the
proposed richer identity.

### Source, Computation and Evaluation Timeframe

> As-built note: `market_analysis/models/request.py`'s `ComponentRequest`
> has `computation_timeframe` and a `resolved_computation_timeframe(...)`
> method; `docs/reference/system/DOMAIN_MODEL.md`'s domain-relationship
> content confirms `observed_at`/`available_at` semantics exist. The
> computation-timeframe distinction is concretely implemented; a distinct,
> separately-named **evaluation timeframe** field was not found as an
> implementation field as of Sprint 054 T003 — the three-way conceptual
> distinction is real but not fully reified as three separate fields in one
> contract.

The framework must distinguish three concepts.

#### Source Timeframe

The granularity of the source dataset.

Example:

```text
NQ 1m bars
```

#### Computation Timeframe

The granularity on which an analytical component is calculated.

Examples:

```text
Volatility Regime on 30m
Trend State on 1h
Market Phase on 4h
```

#### Evaluation Timeframe

The granularity on which the Market Model or Signal Model is evaluated.

Example:

```text
Signal evaluated every 1m
```

Example configuration:

```text
source timeframe:       1m
signal evaluation:      1m
volatility computation: 30m
trend computation:      1h
market phase:            4h
```

These concepts must not be conflated.

---

## Resampling

### Resampling Is a Shared Dependency

Resampling must be represented as an explicit node in the dependency graph.

Example:

```text
NQ 1m Bars
   ├── Resample to 30m
   │      └── Volatility Regime 30m
   ├── Resample to 1h
   │      └── Trend State 1h
   └── Resample to 4h
          └── Market Phase 4h
```

The same resampled dataset should be reused by all components requiring it.

A component must not privately resample source data inside its own calculation method.

### Resampling Contract

> As-built note: resampling logic exists and is reused across
> `market_analysis/` (see "Resampling Is a Shared Dependency" above). The
> literal `ResampleRequest`/`BoundaryPolicy` dataclass types below returned
> zero matches in `src/` as of Sprint 054 T003 — only the underlying resample
> function is implemented, not this specific contract shape.

Conceptual model:

```python
@dataclass(frozen=True, slots=True)
class ResampleRequest:
    source_timeframe: Timeframe
    target_timeframe: Timeframe
    calendar_id: str
    boundary_policy: BoundaryPolicy
```

The resampling implementation should be reusable by:

- Market Analysis Engine,
- dataset generation workflows,
- research workflows,
- replay and execution preparation.

---

## Temporal Alignment and Look-Ahead Protection

### Main Risk

The main multitimeframe risk is not resampling itself.

It is making higher-timeframe information available before that information was known.

Example:

```text
Decision time: 10:37
Higher timeframe: 1h
Current 1h interval: 10:00–11:00
```

At 10:37, the final high, low, close, volume, ATR and regime of the 10:00–11:00 bar are not available.

The framework must not expose their final values to a 1m decision at 10:37.

### Default Alignment Policy

> As-built note: `observed_at`/`available_at` fields are pervasively
> implemented (`market_analysis/models/{alignment,outputs,result}.py`,
> `market_analysis/data/align.py`), directly realizing the "no early
> exposure" rule. The literal string `LAST_CLOSED_BAR` returned zero
> matches in `src/` as of Sprint 054 T003 — the named policy constant is not
> present verbatim, though the alignment module's default behavior is
> consistent with this rule.

The default policy is:

```text
LAST_CLOSED_BAR
```

A higher-timeframe result becomes available only after the underlying higher-timeframe interval is closed and the result is calculated.

Example:

```text
4h interval:   08:00–12:00
available_at:  12:00
```

The value may then be used by lower-timeframe observations occurring at or after `available_at`.

### As-Of Alignment

Higher-timeframe outputs should normally be aligned to lower-timeframe observations using backward as-of semantics.

Conceptually:

```text
For each lower-timeframe timestamp,
use the most recent higher-timeframe result
whose available_at <= evaluation timestamp.
```

A normal equality join is insufficient.

A blind forward-fill is unsafe unless it is based on explicit `available_at` semantics.

### Observed Time and Available Time

Temporal analytical outputs must preserve or allow derivation of:

```text
observed_at
available_at
```

`observed_at` identifies the market interval or event being described (or, per the Multitimeframe source, "describes the source market interval").

`available_at` identifies when the output may legally be consumed.

Conceptual model:

```python
@dataclass(frozen=True, slots=True)
class TemporalAnalysisResult:
    component_key: ComponentKey
    timeframe: Timeframe
    observed_at: TimestampRange
    available_at: datetime
    payload: AnalysisPayload
```

This distinction is mandatory for:

- multitimeframe alignment,
- look-ahead prevention,
- replay consistency,
- research/runtime parity,
- correct multitimeframe joins.

---

## G-04 — Alignment honours `available_at`; the executor does not enforce it at inference time

> Added Sprint 055 T007, newly-authored per D-S055-04 (this is new prose, not
> a verbatim move — flagged explicitly here and in the commit message).

Every section above describes **alignment** semantics: how a higher-timeframe
result's `available_at` is computed and how backward as-of joins use it. That
is implemented and exercised for batch multitimeframe alignment.

It is a separate, narrower claim that **the executor rejects a component
reading data before its legal `available_at` at inference time** — and that
claim is **not true today**. S049-T001 verified line-by-line that the
executor does not enforce inference-time `available_at` rejection
(`executor.py`, `planner.py`, `assembler.py` all checked; no such mechanism
exists — see the [Sprint 049 finding](../../archive/phases/phase-14-predictive-promotion/S049_AVAILABILITY_FINDING.md)).
The [ADR index](../../adr/README.md) tracks the fix as
**ADR-0030 — Inference-Time Availability Enforcement (PLANNED)**.

In short: alignment honours `available_at` for batch MTF joins; nothing
today stops a component from reading a feature before it was legally
available at inference time. Treat every "uses legal `available_at`
semantics" statement above as describing alignment behaviour only, not an
executor-level guarantee, until ADR-0030 lands.

---

## Time Model Rules

The current contracts require UTC-aware domain time, reject naive datetimes,
normalize provider timestamps at boundaries, and use Clock abstractions in
application/domain time-dependent logic. Market Analysis consumes session
contracts without owning global time policy. Futures rolls have explicit
identity and lineage. Batch higher-timeframe alignment respects
`available_at` and does not expose an unfinished bar as a closed value;
**inference-time availability rejection remains unimplemented** (G-04 above).
Multitimeframe does not create a separate model type, and a list of research
candidates does not imply logical `OR` or an unbounded Cartesian expansion.

Broader configurable sessions, exchange calendars, holidays and calendar
versioning belong to [Time Model Future](../../vision/TIME_MODEL_FUTURE.md).
A complete cross-workflow temporal-parity guarantee must be demonstrated by
its own contract and tests rather than inferred from the batch alignment path.
