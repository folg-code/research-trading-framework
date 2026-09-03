# Trading Research Framework

# Multitimeframe and Market Model Architecture

> **Sprint 054 T004 note:** the vision index previously labeled this whole
> document "(future)". `docs/planning/sprints/SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md`
> found that label inaccurate — most of this document (§2–§10, most of
> §12/§16) describes already-built behavior and has moved to
> [`docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md`](../reference/system/MULTITIMEFRAME_MARKET_MODEL.md).
> What remains here is genuinely future-facing (sensitivity surfaces,
> multi-objective/Pareto scoring, the complexity-penalty formula), of
> ambiguous as-built status, or the still-future portion of a mixed
> section. See the classification doc for the full section-by-section
> reasoning and evidence before assuming anything below is or is not built.

## 1. Purpose

This document records the architectural decisions concerning:

- multitimeframe analysis,
- Market Analysis responsibilities,
- Market Analysis components,
- Market Model composition,
- temporal alignment,
- research-space growth,
- storage and analysis of large result spaces.

The purpose of this document is to prevent the framework from evolving toward:

- hidden timeframe dependencies,
- duplicated feature computation,
- monolithic Market Models,
- uncontrolled Cartesian-product research,
- manual inspection of millions of results,
- look-ahead bias caused by incorrect higher-timeframe alignment.

This document complements:

- `ARCHITECTURE_FOUNDATIONS.md`,
- `ARCHITECTURE_TECHNICAL.md`,
- `WORKFLOWS_AI_ADR.md`.

---

## 3. Market Analysis Responsibilities

### 3.5 States

*(Classified MIXED by T003 — as-built status is nuanced, see
`SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §3.5. The
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

---

## 7. Resampling

### 7.2 Derived Datasets

*(Classified AMBIGUOUS by T003 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §7.2.
This describes a user-workspace storage convention rather than a
`src/trading_framework/` code contract; verifying the actual on-disk
`user_data/data/derived/` layout and its lineage metadata was out of scope
for the grep-level verification pass.)*

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

## 8. Temporal Alignment and Look-Ahead Protection

### 8.5 Intrabar Exception

*(Classified AMBIGUOUS by T003 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §8.5.
No explicit "intrabar" flag, declaration mechanism, or component metadata
field for this exception was found.)*

Incomplete higher-timeframe data may be used only when the model explicitly studies intrabar state.

Such a component must declare:

- that it consumes partial intervals,
- how partial bars are constructed,
- its update frequency,
- its `available_at` policy,
- whether research and live execution use identical semantics.

Intrabar behaviour must never be the accidental result of ordinary resampling.

---

## 9. Component Request

*(Classified MIXED by T003. The actual `market_analysis/models/request.py`
`ComponentRequest` has only three fields (`component_id`, `parameters`,
`computation_timeframe`) — materially smaller than the 7-field version
below. The core idea (an explicit, non-hidden request object driving the
planner) is implemented; the specific contract shape below is not. See
`SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §9.)*

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

---

## 12. Research-Space Growth

### 11.1 The Problem

*(Note: this section is numbered `# 12` but its subsections are labeled
`## 11.1`/`## 11.2` in the source file — a pre-existing numbering
inconsistency, left as-is per T003's read-only scope.)*

Multitimeframe analysis expands the number of possible component combinations.

Example dimensions:

```text
4 analytical properties
4 timeframe alternatives
5 parameter variants
```

Naive combination growth may become extremely large before adding:

- Signals,
- Exits,
- Risk Models,
- instruments,
- periods,
- execution assumptions.

A fast engine does not solve the statistical problem.

It may only produce overfitted results faster.

---

### 11.2 No Implicit Full Cartesian Product

The framework must not interpret every list of timeframe or parameter values as a mandatory full Cartesian product.

Configuration must distinguish:

```text
fixed selection
independent alternatives
bounded search space
logical composition
```

These have different meanings.

*(§11.3 Fixed Selection and §11.4 Independent Alternatives were classified
CURRENT and moved to
[`docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md`](../reference/system/MULTITIMEFRAME_MARKET_MODEL.md#independent-alternatives-research-space-growth).)*

### 11.5 Search Constraints

*(Classified MIXED by T003. `candidate_bounds.max_candidates` — a
bound-and-prune mechanism — is confirmed implemented
(`research/signal_research/family_planning.py`). The specific named
constraint fields below (`max_distinct_timeframes`,
`require_context_timeframe_gte_signal_timeframe`,
`forbid_duplicate_analysis_category`) returned zero matches in `src/` as of
this sprint.)*

A bounded research space may declare constraints such as:

```yaml
constraints:
  max_components: 4
  max_distinct_timeframes: 3
  require_context_timeframe_gte_signal_timeframe: true
  forbid_duplicate_analysis_category: true
```

Possible semantic constraints:

```text
trend timeframe >= signal timeframe
context timeframe >= entry timeframe
maximum number of Market Model conditions
maximum number of independent parameters
maximum model complexity
```

The planner should reject or prune invalid combinations before computation.

---

## 13. Hierarchical Research Methodology

*(Classified AMBIGUOUS by T003 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §13.
This describes a research process/methodology for humans/agents to follow
rather than a system behavior with a code artifact to check. The
underlying validation techniques for Stage 5 (`research/robustness/`) do
exist as tools; whether researchers actually follow this staged
progression is a process question, not verifiable via code search.)*

The framework should encourage progressive research rather than immediate full-grid Strategy Research.

### Stage 1: Individual Components

Test one market property at a time.

Examples:

```text
Trend State 1h as a one-condition Market Model
Trend State 4h as a one-condition Market Model
Liquidity Sweep as a one-condition Signal Model
Signal Model × Trend Market Model
```

Questions:

- Does the property add information?
- Which timeframe is meaningful?
- Is the sample size sufficient?
- Is the effect stable over time?
- Does it generalize across instruments?

---

### Stage 2: Pairwise Interactions

Test only promising pairs.

Examples:

```text
Trend State 4h × Volatility Regime 1h
Trend State 1h × Structural State 30m
Market Phase 4h × Volatility Regime 30m
```

---

### Stage 3: Small Model Compositions

Build compact Market Models and Signal Models from validated components.

Preferred initial size:

```text
2–4 analytical conditions
```

A larger model requires stronger evidence and explicit complexity justification.

---

### Stage 4: Complete Strategy Research

Only selected Market Models and Signal Models are combined with:

```text
Exit Model
Risk Model
```

This produces complete Strategy Model candidates.

---

### Stage 5: Validation

Selected candidates should undergo:

- out-of-sample validation,
- walk-forward analysis,
- parameter perturbation,
- cost sensitivity,
- cross-asset analysis,
- Monte Carlo analysis,
- family analysis.

---

## 15. Automated Analysis of Large Result Spaces

Manual inspection must not be the primary method of analysing large research spaces.

The Research domain should support automated analytical passes.

### 14.1 Screening

*(Classified AMBIGUOUS by T003 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §14.1.
`research/predictive/selection.py` is a model-selection module for the
Predictive Research track, not a generalized experiment-screening
mechanism matching the criteria below; `family_planning.py`'s cap-and-skip
logic is evidence of *some* automated pruning, but not specifically of
these named screening criteria.)*

Automatically reject or flag experiments with:

- insufficient sample size,
- unstable results,
- weak out-of-sample behaviour,
- extreme parameter sensitivity,
- excessive concentration in one period,
- excessive concentration in one instrument,
- invalid temporal alignment,
- excessive complexity.

---

### 14.2 Marginal Contribution

*(Classified AMBIGUOUS by T003 — as-built status unclear as of Sprint 054,
see `SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §14.2.
No nested-model-comparison utility or metric was found via targeted search
in `research/analytics/` or `research/robustness/`.)*

The framework should compare nested models.

Example:

```text
Signal
Signal × Trend State 4h
Signal × Trend State 4h × Volatility Regime 1h
```

This measures whether an added condition creates real incremental value.

---

### 14.4 Sensitivity Surfaces

*(Classified FUTURE by T003. `Grep` for `sensitivity_surface` returned
zero matches in `src/`; no matrix/surface-shaped analytics output was
found.)*

Timeframe and parameter combinations should be summarised through matrices or surfaces.

Example:

```text
trend timeframe × volatility timeframe → research score
```

The purpose is to identify stable regions rather than one maximum point.

---

### 14.5 Multi-Objective Evaluation

*(Classified FUTURE by T003. `Grep` for `Pareto` returned zero matches in
`src/`. Individual metrics exist elsewhere, but no multi-objective
combination/ranking mechanism ties them together as described below.)*

A candidate should not be selected by one metric alone.

Possible dimensions:

```text
expectancy
stability
sample size
drawdown
complexity
out-of-sample performance
cross-asset consistency
execution sensitivity
```

The framework may use Pareto-frontier analysis or an explicit composite score.

---

### 14.6 Complexity Penalty

*(Classified FUTURE by T003. `Grep` for `complexity_penalty`/
`multiple_testing` returned zero matches in `src/`. No adjusted-score
formula of this shape was found in `research/analytics/`.)*

More complex models should require materially better and more stable evidence.

Conceptual score:

```text
adjusted_score
=
performance_score
- complexity_penalty
- instability_penalty
- multiple_testing_penalty
```

The exact formula belongs to Research Analytics configuration and should not be hard-coded globally.

---

## 17. Proposed Module Structure

*(Classified AMBIGUOUS by T003 — the actual `market_analysis/` and
`strategy/` layouts differ from both proposals below under different
directory names (see
`SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md` §17). The
document's own framing ("Start with a minimal structure... Evolve only
when...") anticipates this drift, so this section is left here as
illustrative context rather than an as-built contract. The authoritative
current package tree is
[`docs/reference/MODULE_MAP.md`](../reference/system/MODULE_MAP.md).)*

Start with a minimal structure:

```text
src/trading_framework/market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

Evolve only when the number and stability of components justify it:

```text
src/trading_framework/market_analysis/
├── features/
├── structures/
├── states/
├── engine/
├── graph/
├── registry/
├── cache/
├── alignment/
├── models/
└── protocols.py
```

Strategy definitions remain separate:

```text
src/trading_framework/strategy/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategy_models/
├── expressions/
├── occurrences/
└── protocols.py
```

The conceptual taxonomy is stable even if the directory structure evolves.

---

## 18. User Data Structure

*(Classified MIXED by T003. `component_id`/`resolved_parameters`-shaped
identity concepts are pervasively implemented elsewhere and documented as
CURRENT in `docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`. The
`reproducibility_status`/`implementation_hash` fields below returned zero
matches anywhere in `src/` as of this sprint. The on-disk `user_data/`
folder layout itself is a private workspace per ADR-0022, not part of the
framework repo's own tree, and was not independently verified here.)*

```text
user_data/
├── development/
│   └── market_analysis/
├── candidates/
│   └── market_analysis/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategies/
└── research/
```

Working components may be used in experimental research when the result records:

```text
component_id
implementation_hash
dependency_hash
resolved_parameters
reproducibility_status = EXPERIMENTAL
```

Mutable local model definitions require:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

---

## 19. Architectural Rules (remaining future-facing items)

*(Rules 1–16, 19, 22 and 24 were classified CURRENT and moved to
[`docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md`](../reference/system/MULTITIMEFRAME_MARKET_MODEL.md#architectural-rules-current-behavior-portion).
The rules below remain here because they inherit MIXED/FUTURE findings
from the sections above.)*

17. Research spaces are bounded and observable. *(Partially built — see §11.5 above.)*
18. Research progresses from small hypotheses to complete Strategy Models. *(See §13 above — process claim, AMBIGUOUS.)*
20. Large spaces require automated screening and multiple-testing metadata. *(Screening is AMBIGUOUS — see §14.1 above; multiple-testing metadata is CURRENT for the Signal Research family case only, see the reference copy of §16.)*
21. Working components and models used in research require fingerprints. *(FUTURE — see §18 above.)*
23. Replay, Paper and Live belong to Strategy Execution. *(FUTURE — `execution/modes.py` supports only `DRY_RUN` as of this sprint; see `docs/vision/ARCHITECTURE_FOUNDATIONS.md` §6.5 and `docs/vision/ARCHITECTURE_TECHNICAL.md` §7.3.)*
