# Trading Research Framework

# MARKET_ANALYSIS_FUTURE.md

> **Target architecture / not-yet-built content.** This file was created by
> Sprint 055 T008 out of `docs/vision/ARCHITECTURE_TECHNICAL.md` §4.4/§5.9
> and `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §3.5/§7.2/
> §8.5/§9 (both source files now dissolved — their remaining CURRENT
> content already lives in `docs/reference/system/`). It groups the
> still-future or ambiguous-status portion of the Market Analysis
> States/Structures taxonomy, the intrabar exception, resampling-derived
> datasets, and the `ComponentRequest` shape. Content below is preserved
> verbatim from the original files; only classification headers, this merge
> header, and provenance notes are newly authored/added. See
> `docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
> and
> `docs/planning/sprints/SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md`
> for the full section-by-section evidence.

---

## States

*(Longest/primary copy — merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md`
§3.5, now dissolved. Classified MIXED by Sprint 054 T003 — the
Feature/Structure/State taxonomy is real and implemented for at least
volatility (`market_analysis/components/volatility/state.py`, registered as
`component_id = "volatility.state"`), but none of the specific named State
types below — `TrendState`, `VolatilityRegime`, `MomentumState`,
`LiquidityState`, `StructuralState`, `MarketPhase` — exist under those
names anywhere in `src/`.)*

States classify reusable market conditions from Features, Structures and Market Data.

Examples:

```text
trend = bullish
volatility = high
momentum = weakening
structure = ranging
liquidity = compressed
market_phase = expansion
```

Possible State families:

```text
States
├── Trend States
├── Volatility Regimes
├── Momentum States
├── Liquidity States
├── Structural States
└── Market Phases
```

Examples:

- `TrendState`,
- `VolatilityRegime`,
- `MomentumState`,
- `LiquidityState`,
- `StructuralState`,
- `MarketPhase`.

A State component remains reusable and strategy-independent.

It may depend on:

- Features,
- Structures,
- raw or normalized Market Data,
- time abstractions,
- sessions,
- calendars.

> **Merged from: `ARCHITECTURE_TECHNICAL.md` §4.4, now dissolved.** That
> section (classified MIXED by Sprint 054 T002 — Features and Structures
> are clearly built; no distinct "State" output type or `states/` directory
> was found beyond the single generically-named `volatility.state`
> component) restated the same taxonomy under the heading "State", adding
> one unique example not present above:
>
> ```text
> Pivot Structures
> + Slope Feature
> + Volatility Feature
>         ↓
> Trend / Range State
> ```

---

## Intrabar Components

*(Longest/primary copy — merged from: `ARCHITECTURE_TECHNICAL.md` §5.9, now
dissolved. Classified AMBIGUOUS by Sprint 054 T002 — no dedicated
"intrabar" contract or module was located.)*

Partial higher-timeframe data is allowed only through an explicit intrabar contract.

Such a component declares:

```text
partial interval input
update frequency
available_at policy
research/runtime parity assumptions
cache identity
output stability policy
```

Intrabar behaviour must never arise accidentally from ordinary resampling.

> **Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §8.5
> "Intrabar Exception", now dissolved.** That section (classified AMBIGUOUS
> by Sprint 054 T003 — no explicit "intrabar" flag, declaration mechanism,
> or component metadata field was found) restated the same rule in prose
> rather than as a field list, adding one framing not present above:
> incomplete higher-timeframe data "may be used only when the model
> explicitly studies intrabar state," and the component must declare
> "whether research and live execution use identical semantics" (the
> research/runtime parity assumptions field above is the same concept).

---

## Derived Datasets (Resampling)

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §7.2, now
dissolved. Classified AMBIGUOUS by Sprint 054 T003 — this describes a
user-workspace storage convention rather than a `src/trading_framework/`
code contract; verifying the actual on-disk `user_data/data/derived/`
layout and its lineage metadata was out of scope for the grep-level
verification pass.)*

Resampled datasets belong to the derived data layer.

Suggested location:

```text
user_data/data/derived/
```

A derived dataset should preserve:

- source dataset identity,
- source timeframe,
- target timeframe,
- resampling rules,
- calendar version,
- boundary convention,
- dataset version,
- checksum where applicable.

---

## Component Request

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §9, now
dissolved. Classified MIXED by Sprint 054 T003 — the actual
`market_analysis/models/request.py` `ComponentRequest` has only three
fields (`component_id`, `parameters`, `computation_timeframe`) — materially
smaller than the 7-field version below. The core idea (an explicit,
non-hidden request object driving the planner) is implemented; the
specific contract shape below is not.)*

A timeframe-aware analytical component request may be represented as:

```python
@dataclass(frozen=True, slots=True)
class ComponentRequest:
    component_key: ComponentKey
    parameters: ParameterSet
    source_timeframe: Timeframe
    computation_timeframe: Timeframe
    evaluation_timeframe: Timeframe
    resampling_policy: ResamplingPolicy
    alignment_policy: AlignmentPolicy
```

A decorator may exist as optional syntax sugar, but it must produce or register an explicit `ComponentRequest`.

A decorator must not hide:

- timeframe dependencies,
- resampling rules,
- alignment rules,
- warm-up requirements,
- cache identity,
- data lineage.

The framework contract must remain explicit and serializable.

> **Sprint 055 T008 note:** the multitimeframe fields above
> (`source_timeframe`/`computation_timeframe`/`evaluation_timeframe`/
> `resampling_policy`/`alignment_policy`) are no longer purely aspirational
> — Sprint 004's `ADR-MA-012` (ACCEPTED) delivered batch multitimeframe
> computation (resolved computation/evaluation timeframe roles, an
> `AlignmentPolicy.LAST_CLOSED_BAR` default) via `RequestResolver` and
> `ResolvedComponentRequest`, a different concrete shape than the
> `ComponentRequest` dataclass sketched above. See `ADR-MA-012` for the
> as-built contract and `MARKET_ANALYSIS_DECISIONS.md` (D-029 annotation)
> for the related decision-register correction.
