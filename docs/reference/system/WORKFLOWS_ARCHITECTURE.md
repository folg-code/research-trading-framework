# Workflows Architecture — As-Built Reference

> Moved from `docs/vision/WORKFLOWS_AI_ADR.md` §1–§5/§8 by Sprint 054 T006c
> (vision reclassification and reference layering). The sections below were
> classified **CURRENT** (or are the current-behavior portion of a section
> that was classified **MIXED**, by inheritance from restated content) against
> the codebase as of 2026-09-03. See
> `docs/planning/sprints/SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references. Content is reproduced verbatim from the vision document — this
> move does not rewrite any architectural decision.
>
> Future-facing, ambiguous-status, and MIXED-without-a-clean-subsection-split
> content (Strategy Families, Broker Abstraction, Reconciliation, Recovery,
> the Replay/Live execution modes, on-disk storage layouts, and several
> sections whose "suggested" contract has diverged from what is actually
> built) remains in
> [`docs/vision/WORKFLOWS_AI_ADR.md`](../../vision/WORKFLOWS_AI_ADR.md). §6
> (AI Agent Contract) was consolidated into `AGENTS.md` /
> `.cursor/rules/ARCHITECTURE_CONTROL.md` by Sprint 054 T006b, and §7 (ADR
> process) into `docs/adr/README.md` by Sprint 054 T006a — see those files
> for current guidance on those two topics.

---

## Workflow Architecture

### Core Rule

The framework must not be represented as:

```text
Signal Research
        ↓
Strategy Research
        ↓
Strategy Execution
```

This would incorrectly imply that every workflow requires the output of the previous workflow.

The correct architecture is:

```text
                         Shared Domains
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       Signal Research   Strategy Research   Strategy Execution
```

Shared domains include:

- Market,
- Market Analysis,
- Strategy,
- Research,
- Execution,
- Time,
- Configuration,
- Infrastructure contracts.

Each workflow has:

- its own purpose,
- its own inputs,
- its own orchestration,
- its own outputs,
- its own persistence model,
- its own analytics or runtime state.

---

### Workflow Definitions

A workflow definition is a validated configuration describing one use case.

It may define:

- datasets,
- assets,
- model definitions,
- logical expressions,
- parameter spaces,
- execution assumptions,
- output policies,
- research scope,
- alignment and timeframe rules.

A workflow definition is not a domain model.

It belongs to the application and configuration layers.

---

### Computation and Analytics

Every research workflow separates:

```text
Research Computation
```

from:

```text
Research Analytics
```

Research Computation creates reusable factual datasets.

Research Analytics interprets stored results.

A new report, filter, ranking or family analysis must not automatically recalculate unchanged source results.

---

## Signal Research

### Purpose

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

### Core Questions

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

### Research Scope

Every Signal Research definition must explicitly declare one scope:

```text
MARKET_MODEL_ONLY
SIGNAL_MODEL_ONLY
MARKET_AND_SIGNAL
```

The workflow must not infer scope from missing fields.

#### MARKET_MODEL_ONLY

Evaluates one or more Market Models independently.

Example questions:

- future return distribution by market context,
- regime persistence,
- transition behaviour,
- conditional volatility,
- MFE and MAE after entering a state.

#### SIGNAL_MODEL_ONLY

Evaluates one or more Signal Models without an additional Market Model filter.

Example questions:

- forward-return distribution after a SignalOccurrence,
- event frequency,
- directional asymmetry,
- time-of-day behaviour,
- stability by period.

#### MARKET_AND_SIGNAL

Evaluates Signal Models under one or more Market Models.

Example questions:

- marginal contribution of market context,
- signal quality by regime,
- context-specific sample size,
- stability across Market Model variants.

---

### Inputs

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

### Market Model and Signal Model Semantics

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

### Independent Experiment Expansion

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

---

### Logical Composition

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

### Single-Condition Models

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

### SignalOccurrence

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

### Market Model Results

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

### Shared Dependency Plan

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

### Signal Research Computation Output

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

### Reuse Rule

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

---

### Signal Research Rules

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

> Note: this rules list restates §3.1–§3.16 above (see
> `SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §3.17
> for the by-inheritance classification). The source document's §3.12
> (planner telemetry), §3.14 (analytics coverage) and §3.16 (on-disk storage
> layout) carry MIXED/AMBIGUOUS nuance not fully captured by this summary —
> see [`docs/vision/WORKFLOWS_AI_ADR.md`](../../vision/WORKFLOWS_AI_ADR.md)
> §3.12/§3.14/§3.16 for those caveats.

---

## Strategy Research

### Purpose

Strategy Research evaluates complete Strategy Models.

Its research vector is:

```text
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

Strategy Research evaluates:

- profitability,
- stability,
- robustness,
- execution sensitivity,
- component interactions,
- capital and exposure behaviour.

---

### Core Question

Strategy Research answers:

```text
How does a complete Strategy Model perform under explicit historical and execution assumptions?
```

It does not merely ask whether a signal contains predictive information.

It evaluates how the complete composition behaves as a trading system.

---

### Strategy Model

A Strategy Model is composed from:

```text
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

Position sizing belongs to the Risk Model in Version 1.

A Strategy Model preserves:

- component identities,
- versions or definition hashes,
- parameters,
- dependency lineage,
- composition identity.

A Strategy Model is not a monolithic class that calculates:

- Market Analysis,
- entries,
- exits,
- position sizing,
- broker interaction.

---

### Composition Rules

Market Models and Signal Models may use explicit logical expression trees.

Exit Models and Risk Models are contract-based components.

They may use:

- declarative conditions,
- deterministic calculation logic,
- controlled references to Strategy and Market Analysis state.

Version 1 should normally select one Exit Model and one Risk Model per Strategy Model unless composite contracts are explicitly defined.

---

### Historical Strategy Simulation

Batch or vectorized backtesting belongs to Research.

It is optimized for:

- large strategy spaces,
- historical performance analysis,
- explicit simulation assumptions,
- reusable Strategy Research Datasets.

It may simulate:

- order generation,
- fills,
- commissions,
- slippage,
- latency,
- position state,
- cash state,
- realized PnL,
- unrealized PnL.

Historical Strategy Simulation consumes Strategy Models.

It does not define them.

---

### Strategy Research Computation Output

The computation phase produces a persistent:

```text
Strategy Research Dataset
```

It may contain:

- Strategy Model identity,
- component identities,
- definition hashes,
- individual simulated trades,
- simulated orders,
- simulated fills,
- position history,
- equity curve,
- return series,
- performance facts,
- execution assumptions,
- experiment dimensions,
- failure states.

Raw trade-level and time-series results should be preserved where practical.

Aggregated metrics alone are insufficient for future analysis.

---

### Strategy Analytics

Analytics may calculate:

- total return,
- CAGR where meaningful,
- expectancy,
- profit factor,
- Sharpe ratio,
- Sortino ratio,
- maximum drawdown,
- MAR ratio,
- win rate,
- payoff ratio,
- exposure,
- turnover,
- tail loss,
- stability by period,
- parameter sensitivity,
- asset sensitivity,
- execution-cost sensitivity,
- component contribution.

No single metric determines strategy quality.

---

### Walk Forward

Walk-forward analysis is a Research validation tool.

It records:

- train windows,
- validation windows,
- test windows,
- step size,
- parameter selection rules,
- retraining policy,
- aggregation policy.

It is not a Strategy Model component.

---

### Monte Carlo

Monte Carlo analysis evaluates uncertainty and path dependence.

Possible methods:

- trade-order reshuffling,
- bootstrap resampling,
- block bootstrap,
- execution-cost perturbation,
- return perturbation,
- missed-trade simulation.

Every method must state its assumptions.

Monte Carlo outputs are derived analytics, not replacements for raw results.

---

### Robustness

Robustness analysis may include:

- parameter perturbation,
- neighbouring model variants,
- subperiod analysis,
- cross-asset analysis,
- cost sensitivity,
- delayed entry,
- worse fills,
- missing trades,
- regime segmentation,
- out-of-sample validation.

A candidate must not be described as validated without explicit robustness criteria.

---

### Reuse Rule

If the following remain unchanged:

```text
Market Dataset
Market Analysis definitions
Strategy component definitions
execution assumptions
simulation engine version
configuration
random seeds
```

then the existing Strategy Research Dataset should be reused.

New rankings, filters and family analyses should not trigger a new backtest automatically.

---

## Strategy Execution

### Core Question

Strategy Execution answers:

```text
How should a selected Strategy Model interact with a runtime environment and broker safely and consistently?
```

It does not answer:

- whether a signal has predictive information,
- which Strategy Model ranks highest,
- which strategy family is most robust.

---

### Inputs

Strategy Execution may consume:

- selected Strategy Model,
- live or replay Market Data,
- required Market Analysis outputs,
- SignalOccurrences,
- runtime account state,
- execution configuration,
- broker configuration,
- instrument mapping,
- operational risk limits.

It must not require:

- Signal Research Dataset,
- Strategy Research Dataset,
- research ranking,
- research report,
- research insight,
- notebook state,
- walk-forward output,
- Monte Carlo output.

---

### Runtime Flow

Conceptual flow:

```text
Market Data
        ↓
Market Analysis Updates
        ↓
Market Model Evaluation
        ↓
Signal Model Evaluation
        ↓
SignalOccurrence
        ↓
Exit Model / Risk Model Evaluation
        ↓
Strategy Decision
        ↓
Operational Risk Controls
        ↓
Order Command
        ↓
Broker Adapter
        ↓
Order / Fill Events
        ↓
Position Update
```

This is a Strategy Execution workflow.

It does not define Signal Research or Strategy Research.

> As-built note: this flow's structure and sequencing is implemented through
> `execution/runtime/decision_step.py`, `live_signals.py`, `strategy_orders.py`
> and `execution/safety.py` for the one supported `DRY_RUN` mode, ending at
> `execution/broker_sim/paper_broker.py` and `execution/models/{orders,positions}.py`.
> "Broker Adapter" in the sense of a pluggable real-broker interface does not
> exist — see §5.11 (Broker Abstraction, classified FUTURE) in
> [`docs/vision/WORKFLOWS_AI_ADR.md`](../../vision/WORKFLOWS_AI_ADR.md).

---

### Position Management

Position state is derived from accepted execution facts.

It includes where relevant:

- quantity,
- side,
- average entry price,
- realized PnL,
- unrealized PnL,
- exposure,
- open orders,
- lifecycle status.

Internal state must be reconcilable with broker state.

> As-built note: the position-derivation mechanism is implemented
> (`execution/models/positions.py`, `execution/broker_sim/paper_broker.py`).
> "Reconcilable with broker state" has no code counterpart today, since no
> external broker exists to reconcile against — see §5.12 (Reconciliation,
> classified FUTURE) in
> [`docs/vision/WORKFLOWS_AI_ADR.md`](../../vision/WORKFLOWS_AI_ADR.md).

---

### Strategy Risk vs Operational Risk

The Strategy Domain Risk Model answers:

```text
How much exposure should the strategy request?
```

It includes position sizing in Version 1.

Execution Risk Controls answer:

```text
Is the requested action operationally allowed?
```

Examples:

- maximum daily loss,
- maximum account drawdown,
- maximum position size,
- maximum number of open positions,
- duplicate-order prevention,
- stale-data protection,
- connection health checks,
- kill switch.

These responsibilities must remain separate.

---

### Persistence

Persist where relevant:

- commands,
- orders,
- acknowledgements,
- fills,
- positions,
- operational risk decisions,
- errors,
- reconciliation results,
- correlation identifiers.

Execution records belong to operational storage.

They are not Research Datasets.

> As-built note: operational persistence for orders/fills/positions/events is
> implemented (`execution/repositories/{protocols,read_models}.py`,
> `execution/models/events.py`), structurally separate from
> `research/datasets/`. "Reconciliation results" cannot be persisted since
> reconciliation itself does not exist yet — see §5.12 in
> [`docs/vision/WORKFLOWS_AI_ADR.md`](../../vision/WORKFLOWS_AI_ADR.md).
