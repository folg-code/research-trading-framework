# Signal Research — As-Built Reference

> Extracted from the former `docs/reference/system/WORKFLOWS_ARCHITECTURE.md`
> ("Signal Research" section) by Sprint 055 T007, per the maintainer-approved
> reversal of Sprint 054 T007's rejection in
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1 — this is a section
> extraction with no new prose, not authoring. That source file's own content
> originated in `docs/vision/WORKFLOWS_AI_ADR.md`, moved by Sprint 054 T006c.
> The section was classified **CURRENT** (or is the current-behavior portion
> of a section classified **MIXED**) against the codebase as of 2026-09-03.
> See
> `docs/planning/sprints/SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references.
>
> **This file answers "what are Signal Research's scopes, contracts and
> persisted outputs".** For "which methodology should I choose, and what
> question does it answer", see
> [`RESEARCH_METHODOLOGIES.md`](RESEARCH_METHODOLOGIES.md) §4 — the two
> documents are deliberately not merged (see that file's reciprocal note).

---

## Purpose

Signal Research evaluates analytical hypotheses without requiring a complete Strategy Model.

Supported research scopes are:

```text
Market Model only
Signal Model only
Market Model × Signal Model
```

Signal Research does not evaluate a complete trading system.

It does not require:

- Exit Model,
- Risk Model,
- position sizing,
- account state,
- broker simulation,
- portfolio construction.

---

## Core Questions

Signal Research may answer:

```text
How does a Market Model segment or describe future market behaviour?
```

```text
How does a Signal Model behave without an additional market-context filter?
```

```text
How does a Signal Model behave under a selected Market Model?
```

Examples:

```text
Bullish Trend Market Model
```

```text
Bullish Liquidity Sweep Signal Model
```

```text
Bullish Trend Market Model × Bullish Liquidity Sweep Signal Model
```

---

## Research Scope

Every Signal Research definition must explicitly declare one scope:

```text
MARKET_MODEL_ONLY
SIGNAL_MODEL_ONLY
MARKET_AND_SIGNAL
```

The workflow must not infer scope from missing fields.

### MARKET_MODEL_ONLY

Evaluates one or more Market Models independently.

Example questions:

- future return distribution by market context,
- regime persistence,
- transition behaviour,
- conditional volatility,
- MFE and MAE after entering a state.

### SIGNAL_MODEL_ONLY

Evaluates one or more Signal Models without an additional Market Model filter.

Example questions:

- forward-return distribution after a SignalOccurrence,
- event frequency,
- directional asymmetry,
- time-of-day behaviour,
- stability by period.

### MARKET_AND_SIGNAL

Evaluates Signal Models under one or more Market Models.

Example questions:

- marginal contribution of market context,
- signal quality by regime,
- context-specific sample size,
- stability across Market Model variants.

---

## Inputs

Signal Research may consume:

- published Market Datasets,
- Market Analysis outputs,
- Market Models,
- Signal Models,
- controlled MarketFieldReferences,
- logical expressions,
- asset lists,
- time ranges,
- forward horizons,
- bounded research spaces,
- research configuration.

It must not require a Strategy Model.

---

## Market Model and Signal Model Semantics

Both Market Models and Signal Models are declarative compositions over Market Analysis outputs.

```text
Market Model:
Which analytical conditions define the market context?
```

```text
Signal Model:
Which analytical events and conditions define a trading opportunity?
```

They may consume the same underlying:

- Features,
- Structures,
- States,
- controlled MarketFieldReferences.

They must not:

- calculate analytical dependencies internally,
- resample data internally,
- open storage,
- instantiate providers,
- access arbitrary DataFrames.

---

## Independent Experiment Expansion

Independent alternatives create separate experiments.

Example:

```yaml
signal_research:
  scope: MARKET_AND_SIGNAL

  assets:
    - NQ
    - ES

  signal_models:
    experiments:
      - bullish_sweep
      - breakout_reclaim

  market_models:
    experiments:
      - bullish_trend
      - ranging_market
```

This may create:

```text
NQ × Bullish Sweep × Bullish Trend
NQ × Bullish Sweep × Ranging Market
NQ × Breakout Reclaim × Bullish Trend
NQ × Breakout Reclaim × Ranging Market
ES × ...
```

Expansion must remain bounded and observable.

> As-built note (Sprint 054 T003b): `research/signal_research/family_planning.py`'s
> `FamilyExperimentPlan` implements bounded, observable expansion for the
> Signal Research family case — see the reuse rule below and PRB-020.

---

## Logical Composition

Logical composition creates one model definition.

Example Signal Model:

```yaml
signal_model:
  id: sweep_or_reclaim

  expression:
    operator: OR
    children:
      - component: bullish_sweep
      - component: bullish_reclaim
```

Equivalent:

```text
Bullish Sweep OR Bullish Reclaim
```

Example Market Model:

```yaml
market_model:
  id: bullish_normal_or_high_volatility

  expression:
    operator: AND
    children:
      - component: bullish_trend
      - operator: OR
        children:
          - component: normal_volatility
          - component: high_volatility
```

The system must never confuse:

```text
list of independent experiments
```

with:

```text
logical OR
```

---

## Single-Condition Models

A single Market Analysis component may be researched through a one-condition model.

Examples:

```text
Market Model:
trend_state == bullish
```

```text
Signal Model:
liquidity_sweep exists
```

The workflow should not bypass model contracts merely because a hypothesis contains one condition.

This preserves:

- consistent lineage,
- common expression evaluation,
- reusable model identity,
- consistent research methodology.

---

## SignalOccurrence

A Signal Model produces a provider-independent:

```text
SignalOccurrence
```

`SignalOccurrence` belongs to the Strategy Domain.

Suggested fields:

```text
signal_model_id
signal_model_version or definition_hash
instrument
detected_at
direction
reference_price
strength
analytical_lineage
```

Research may wrap SignalOccurrence with research-specific metadata, but must not redefine its core meaning.

SignalOccurrence datasets may be reused by:

- different Market Models,
- multiple forward horizons,
- multiple analytics,
- Strategy Research,
- diagnostic reports.

Reuse is optional and contract-based.

It is not a mandatory dependency between workflows.

---

## Market Model Results

Market Models may produce reusable context results such as:

```text
Boolean mask
Categorical state
Numeric score
Multi-label context
Typed context record
```

These results must preserve:

- Market Model identity,
- version or definition hash,
- component lineage,
- dataset identity,
- timeframe semantics,
- available_at semantics.

---

## Shared Dependency Plan

Signal Research uses one shared dependency graph.

Example:

```text
Bullish Trend Market Model
├── Pivot Structure
├── Slope Feature
└── Volatility State

Bullish Sweep Signal Model
├── Liquidity Level
├── Liquidity Sweep Structure
└── Reclaim Feature
```

Each unique deterministic dependency is calculated once per computation identity.

The engine must not recalculate shared Market Analysis components independently for every:

- model,
- asset,
- horizon,
- analytical report,
- experiment variant.

---

## Signal Research Computation Output

The computation phase produces a persistent:

```text
Signal Research Dataset
```

Depending on scope, it may contain:

- Market Model observations,
- SignalOccurrences,
- joined Market Model × Signal Model observations,
- forward prices,
- forward returns,
- MFE,
- MAE,
- event metadata,
- experiment dimensions,
- analytical lineage,
- sample membership,
- model fingerprints.

The dataset must remain queryable without loading implementation classes.

---

## Reuse Rule

If the following remain unchanged:

```text
Market Dataset
Market Analysis definitions
Market Model definitions
Signal Model definitions
parameters
time assumptions
forward horizon definitions
```

then the existing Signal Research Dataset should be reused.

New analytics should query stored data.

They should not automatically trigger recomputation.

**PRB-020 note (added Sprint 055 T007, per D-S055-04 SS3 G-03):** Signal
Research's "family" concept (bounded experiment expansion, reuse, dedicated
dataset) is real and implemented (`research/signal_research/family_planning.py`,
`research/datasets/signal_research_family.py`). Strategy Research has **no**
equivalent family concept in code — see
[`STRATEGY_RESEARCH.md`](STRATEGY_RESEARCH.md)'s reuse rule and
`docs/planning/PROBLEM_REGISTRY.md` **PRB-020** (OPEN, MEDIUM).

---

## Signal Research Rules

1. Signal Research supports Market Model only, Signal Model only and combined scope.
2. Exit and Risk Models are excluded.
3. Market and Signal Models are declarative compositions.
4. Independent expansion and logical composition are distinct.
5. Single analytical hypotheses use one-condition models.
6. Computation and analytics are separate.
7. Shared dependencies are calculated once.
8. SignalOccurrences are reusable Strategy Domain artifacts.
9. Market Model outputs are reusable artifacts.
10. Research datasets are persistent and versioned.
11. Working components and models used in research require fingerprints.
12. New analytics should not rerun unchanged computations.
13. Signal Research does not depend on Strategy Research.
14. Signal Research does not form a pipeline into Strategy Execution.

> Note: this rules list restates the sections above (see
> `SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §3.17
> for the by-inheritance classification). The source document's §3.12
> (planner telemetry), §3.14 (analytics coverage) and §3.16 (on-disk storage
> layout) carry MIXED/AMBIGUOUS nuance not fully captured by this summary —
> see [`docs/vision/WORKFLOWS_AI_ADR.md`](../../vision/WORKFLOWS_AI_ADR.md)
> §3.12/§3.14/§3.16 for those caveats.
