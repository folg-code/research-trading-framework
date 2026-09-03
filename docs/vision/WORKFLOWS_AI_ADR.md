# Trading Research Framework

# WORKFLOWS_AI_ADR.md

## 1. Purpose

This document defines:

- the Signal Research workflow,
- the Strategy Research workflow,
- the Strategy Execution workflow,
- the AI Agent Contract,
- the Architectural Decision Record process.

It complements:

- `ARCHITECTURE_FOUNDATIONS.md`,
- `ARCHITECTURE_TECHNICAL.md`.

The framework supports three independent system capabilities:

```text
Signal Research
Strategy Research
Strategy Execution
```

These capabilities share domains, models, analytical components and infrastructure contracts.

They are not stages of one mandatory pipeline.

A workflow consumes domain components.

A workflow does not redefine domain ownership.

---

# 2. Workflow Architecture

## 2.1 Core Rule

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

## 2.2 Workflow Definitions

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

## 2.3 Workflow Execution

A workflow should follow:

```text
Validated Configuration
        ↓
Definition Resolution
        ↓
Dependency Resolution
        ↓
Execution Plan
        ↓
Computation or Runtime Processing
        ↓
Persistent Results or Operational State
        ↓
Independent Analytics or Monitoring
```

The workflow layer coordinates existing components.

It must not implement:

- Market Analysis calculations,
- Market Model logic,
- Signal Model logic,
- Exit Model logic,
- Risk Model logic,
- broker-specific logic,
- storage-specific logic.

---

## 2.4 Computation and Analytics

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

## 2.5 Workflow Identity

Every workflow run must have a stable identity derived from all material inputs.

Suggested identity inputs:

```text
workflow_type
research_scope
resolved_configuration
dataset_ids
dataset_versions
component_ids
component_versions or implementation_hashes
model_ids
model_versions or definition_hashes
parameters
time_range
source_timeframe
computation_timeframe
evaluation_timeframe
alignment_policy
calendar_version
framework_version
execution_assumptions
random_seed
```

A material change creates a new run identity.

---

# 3. Signal Research

## 3.1 Purpose

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

## 3.2 Core Questions

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

## 3.3 Research Scope

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

## 3.4 Inputs

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

## 3.5 Market Model and Signal Model Semantics

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

## 3.6 Independent Experiment Expansion

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

## 3.7 Logical Composition

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

## 3.8 Single-Condition Models

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

## 3.9 SignalOccurrence

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

## 3.10 Market Model Results

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

## 3.11 Shared Dependency Plan

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

## 3.12 Research Space Boundaries

Signal Research must distinguish:

```text
fixed selection
independent alternatives
logical composition
bounded search space
```

The planner should expose where possible:

```text
number_of_candidates
number_of_unique_dependencies
number_of_reused_nodes
number_of_new_nodes
estimated_output_size
applied_constraints
```

Unrestricted Cartesian-product expansion is not the default.

---

## 3.13 Signal Research Computation Output

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

## 3.14 Signal Research Analytics

Analytics operate on stored Signal Research Datasets.

Typical operations include:

- forward-return distributions,
- MFE and MAE,
- event frequency,
- context persistence,
- hit rate,
- conditional analysis,
- Market Model comparison,
- Signal Model comparison,
- marginal contribution,
- cross-asset comparison,
- time-of-day analysis,
- stability by period,
- sample-size analysis,
- parameter sensitivity,
- timeframe sensitivity,
- family analysis,
- clustering,
- insight generation.

Analytics must not mutate the source research dataset.

---

## 3.15 Reuse Rule

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

## 3.16 Storage

Suggested structure:

```text
user_data/research/signal_research/
├── runs/
├── datasets/
├── metadata/
├── analytics/
└── reports/
```

Each run should record:

```text
run_id
research_scope
resolved_config
dataset_references
component_versions or hashes
model_versions or hashes
execution_plan
result_manifest
validation_summary
```

---

## 3.17 Signal Research Rules

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

---

# 4. Strategy Research

## 4.1 Purpose

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

## 4.2 Core Question

Strategy Research answers:

```text
How does a complete Strategy Model perform under explicit historical and execution assumptions?
```

It does not merely ask whether a signal contains predictive information.

It evaluates how the complete composition behaves as a trading system.

---

## 4.3 Inputs

Strategy Research may consume:

- published Market Datasets,
- Market Analysis outputs,
- Market Models,
- Signal Models,
- Exit Models,
- Risk Models,
- Strategy Model definitions,
- controlled MarketFieldReferences,
- capital assumptions,
- commission models,
- slippage models,
- fill models,
- latency assumptions,
- order simulation policies,
- research configuration.

It may reuse persisted compatible artifacts from Signal Research or shared stores.

It must not require a Signal Research run ID.

---

## 4.4 Strategy Model

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

## 4.5 Strategy Research Space

A Strategy Research definition may declare bounded alternatives.

Example:

```yaml
strategy_research:
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

  exit_models:
    experiments:
      - fixed_rr
      - atr_exit
      - session_exit

  risk_models:
    experiments:
      - fixed_risk
      - volatility_adjusted_risk
```

The planner should expose:

```text
number_of_candidates
estimated_dependencies
reused_nodes
new_nodes
estimated_storage
applied_constraints
```

before expensive computation.

---

## 4.6 Composition Rules

Market Models and Signal Models may use explicit logical expression trees.

Exit Models and Risk Models are contract-based components.

They may use:

- declarative conditions,
- deterministic calculation logic,
- controlled references to Strategy and Market Analysis state.

Version 1 should normally select one Exit Model and one Risk Model per Strategy Model unless composite contracts are explicitly defined.

---

## 4.7 Computational Reuse

Strategy Research must reuse deterministic upstream results where valid.

Reusable artifacts may include:

- Market Analysis outputs,
- Market Model results,
- SignalOccurrences,
- entry candidate datasets,
- resampled datasets,
- aligned multitimeframe outputs.

The engine must not calculate the same Market Analysis dependency once per Strategy Model.

---

## 4.8 Historical Strategy Simulation

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

## 4.9 Research Backtest vs Replay Execution

The following are different capabilities:

```text
Batch / Vectorized Backtest
    → Research
```

```text
Replay Execution
    → Strategy Execution
```

Research Backtest:

- is optimized for scale and experiment evaluation,
- may use batch or vectorized processing,
- produces Strategy Research Datasets.

Replay Execution:

- uses a Replay Clock,
- follows runtime order, fill and position semantics,
- validates research/runtime parity,
- belongs to Strategy Execution.

The framework must not collapse these into one ambiguous engine.

---

## 4.10 Execution Assumptions

Every Strategy Research result records where relevant:

```text
commission_model
slippage_model
fill_model
latency_model
position_netting_policy
capital_model
contract_specification
roll_policy
currency_conversion_policy
simulation_engine_version
```

Changing a material assumption creates a distinct result identity.

---

## 4.11 Strategy Research Computation Output

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

## 4.12 Strategy Analytics

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

## 4.13 Rankings

Strategy rankings are valid research outputs.

A ranking must define:

```text
ranking_objective
eligibility_filters
normalization
tie_breaking
minimum_sample_size
robustness_requirements
```

A raw ranking by net profit is insufficient.

A top-ranked strategy is not automatically validated.

---

## 4.14 Strategy Families

Related candidates should be grouped into Strategy Families.

Example:

```text
Bullish Sweep
Bullish Sweep + Trend
Bullish Sweep + Trend + Volatility
Bullish Sweep + Trend + Volatility + Session Filter
```

Family analysis evaluates:

- component contribution,
- stability across nearby variants,
- parameter sensitivity,
- timeframe sensitivity,
- cross-asset behaviour,
- isolated optimum risk,
- overfitting risk.

---

## 4.15 Walk Forward

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

## 4.16 Monte Carlo

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

## 4.17 Robustness

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

## 4.18 Multiple Testing

Large strategy spaces create false-discovery risk.

Every run should preserve:

- number of generated candidates,
- number of evaluated candidates,
- number of rejected candidates,
- pruning rules,
- selection history,
- validation splits,
- family grouping,
- ranking objective.

A high score among millions of candidates is not automatically evidence of edge.

---

## 4.19 Reuse Rule

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

## 4.20 Storage

Suggested structure:

```text
user_data/research/strategy_research/
├── runs/
├── datasets/
├── trades/
├── equity_curves/
├── analytics/
├── rankings/
├── families/
├── robustness/
└── reports/
```

---

## 4.21 Strategy Research Rules

1. Strategy Research evaluates complete Strategy Models.
2. It is independent from Signal Research.
3. Market, Signal, Exit and Risk remain separate components.
4. Position sizing belongs to the Risk Model in Version 1.
5. Shared upstream computations are reused.
6. Batch or vectorized backtesting belongs to Research.
7. Replay Execution does not belong to Research.
8. Execution assumptions are explicit and versioned.
9. Raw trade-level results are preserved where practical.
10. Rankings require explicit eligibility rules.
11. Family analysis is first-class.
12. Validation tools are not Strategy Model components.
13. Working components and models require fingerprints.
14. New analytics should reuse stored Strategy Research Datasets.

---

# 5. Strategy Execution

## 5.1 Purpose

Strategy Execution applies a selected Strategy Model in a runtime environment.

It owns:

- broker communication,
- order lifecycle,
- fill processing,
- position state,
- reconciliation,
- operational risk controls,
- runtime persistence,
- monitoring,
- recovery.

Strategy Execution is independent from research workflows.

---

## 5.2 Core Question

Strategy Execution answers:

```text
How should a selected Strategy Model interact with a runtime environment and broker safely and consistently?
```

It does not answer:

- whether a signal has predictive information,
- which Strategy Model ranks highest,
- which strategy family is most robust.

---

## 5.3 Inputs

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

## 5.4 Execution Modes

Supported modes may include:

```text
Replay Execution
Paper Execution
Live Execution
```

### Replay Execution

- consumes published historical data,
- uses a Replay Clock,
- follows runtime order, fill and position semantics,
- supports parity validation.

### Paper Execution

- consumes live market data,
- uses simulated broker interaction,
- preserves runtime semantics.

### Live Execution

- consumes live market data,
- interacts with a real broker.

The Strategy Model should not need to know which execution mode is active.

---

## 5.5 Runtime Flow

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

---

## 5.6 Event-Driven Runtime

Strategy Execution may use the Event System where reactive communication provides value.

Examples:

```text
MarketBarReceived
AnalysisStateUpdated
SignalGenerated
OrderSubmitted
OrderAccepted
OrderFilled
PositionUpdated
```

An EventBus must not hide:

- order state transitions,
- risk checks,
- failure policy,
- reconciliation,
- persistence requirements.

---

## 5.7 Order Lifecycle

Suggested lifecycle:

```text
Created
Submitted
Accepted
Partially Filled
Filled
Cancelled
Rejected
Expired
```

Transitions are explicit and validated.

Broker-specific statuses are normalized at the adapter boundary.

---

## 5.8 Fill Processing

Fill processing supports:

- partial fills,
- multiple fills per order,
- commissions,
- fees,
- slippage,
- average fill price,
- provider fill identifiers,
- duplicate detection.

Accepted fills are execution facts.

Corrections require explicit correction events or reconciliation logic.

---

## 5.9 Position Management

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

---

## 5.10 Strategy Risk vs Operational Risk

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

## 5.11 Broker Abstraction

Strategy Execution depends on broker contracts.

Suggested capabilities:

```text
connect
disconnect
submit_order
cancel_order
replace_order
get_orders
get_positions
get_account_state
stream_execution_events
```

Broker SDK objects must not leak into domain models.

---

## 5.12 Reconciliation

The runtime compares internal state with broker state.

It should detect:

- missing orders,
- unknown orders,
- quantity mismatches,
- position mismatches,
- missing fills,
- duplicate fills,
- stale account state.

A mismatch creates an explicit incident or error state.

---

## 5.13 Recovery

Strategy Execution supports recovery after:

- process restart,
- network disconnect,
- broker reconnect,
- provider interruption.

Recovery uses persisted execution state and broker reconciliation.

In-memory state alone is insufficient.

---

## 5.14 Persistence

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

---

## 5.15 Observability

Strategy Execution requires:

- structured logs,
- metrics,
- alerts,
- health checks,
- audit trails,
- latency monitoring,
- provider connection state,
- order failure monitoring.

Operational failures must be visible.

---

## 5.16 Strategy Execution Rules

1. Strategy Execution is independent from Research.
2. It consumes selected Strategy Models.
3. Replay, Paper and Live are Execution modes.
4. Broker details remain behind adapters.
5. Order transitions are explicit.
6. Duplicate events are handled idempotently where required.
7. Strategy Risk is separate from operational risk controls.
8. Broker state is reconciled.
9. Critical runtime records are persisted.
10. Recovery is explicit.
11. Execution failures are never silently ignored.
12. Execution does not consume Research workflow state.

---

# 6. AI Agent Contract

## 6.1 Purpose

AI agents may assist with:

- architecture,
- implementation,
- testing,
- documentation,
- refactoring,
- Market Analysis component development,
- model definition development,
- research tooling,
- Strategy Execution tooling.

AI-generated code follows the same contracts as human-authored code.

An AI agent must not invent architecture implicitly.

---

## 6.2 Required Reading Order

Before implementing a task, an AI agent must inspect:

1. `ARCHITECTURE_FOUNDATIONS.md`
2. `ARCHITECTURE_TECHNICAL.md`
3. `WORKFLOWS_AI_ADR.md`
4. the relevant domain or module documentation
5. existing contracts and tests
6. relevant ADRs
7. current sprint or task scope where applicable

The agent must not rely only on an issue description when repository contracts already exist.

---

## 6.3 Scope Discipline

An AI agent implements only the requested scope and directly necessary supporting changes.

It must not:

- redesign unrelated modules,
- introduce speculative abstractions,
- add infrastructure without demonstrated need,
- silently change public contracts,
- move proprietary logic into `src/`,
- collapse separate domains or workflows,
- convert a deferred decision into implementation without approval.

When a requested change conflicts with architecture, the conflict must be reported explicitly.

---

## 6.4 Domain Ownership Rules

The agent preserves:

```text
Market owns trusted market facts and dataset contracts.

Market Analysis owns reusable analytical descriptions.

Strategy owns model definitions, SignalOccurrence and composition.

Research owns historical computation, datasets and analytics.

Execution owns runtime broker interaction and operational state.
```

Forbidden violations include:

- Market calculating ATR,
- a Feature generating an Order,
- a Signal Model calculating position size,
- a Market Model opening Parquet files,
- Research redefining Strategy Model behaviour,
- Execution calculating research rankings,
- Market Analysis containing strategy-specific intent.

---

## 6.5 Workflow Independence Rules

The agent must never introduce mandatory dependencies between:

```text
Signal Research
Strategy Research
Strategy Execution
```

Forbidden examples:

- Strategy Research requiring a Signal Research run ID,
- Strategy Execution loading research rankings,
- Signal Research instantiating Exit Models,
- Strategy Research importing Signal Research analytics,
- Execution loading Monte Carlo results at runtime.

Shared reusable artifacts may be consumed through explicit contracts.

Workflow chaining is not mandatory.

---

## 6.6 `src/` and `user_data/`

Reusable framework code belongs in:

```text
src/
```

Private user assets belong in:

```text
user_data/
```

The agent must not:

- copy proprietary model definitions into framework modules,
- hard-code user paths in domain logic,
- import concrete user modules from `src`,
- commit local market data,
- expose private thresholds in public examples without permission.

User components are loaded through:

- registries,
- controlled discovery,
- configuration,
- public Protocols.

---

## 6.7 Local Component Lifecycle

Local Market Analysis components may live under:

```text
user_data/development/market_analysis/
```

Validated candidates may live under:

```text
user_data/candidates/market_analysis/
```

Promoted components belong under:

```text
src/trading_framework/market_analysis/
```

The agent must not promote a component automatically.

Promotion requires that the component is:

- stable,
- reusable,
- strategy-independent,
- tested,
- documented,
- ready for compatibility maintenance.

---

## 6.8 Fingerprint Rules

A mutable working component used in Research must preserve:

```text
component_id
implementation_hash
dependency_hash
resolved_parameters
reproducibility_status = EXPERIMENTAL
```

A mutable local model definition used in Research must preserve:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

This applies to:

- Market Models,
- Signal Models,
- Exit Models,
- Risk Models,
- Strategy Models.

The agent must not treat a mutable local file path as sufficient result identity.

---

## 6.9 Model Implementation Rules

Use:

```text
frozen dataclass
```

for immutable domain value objects where appropriate.

Use:

```text
Protocol
```

for behavioural contracts.

Use:

```text
Pydantic
```

for configuration, external DTOs and validation boundaries.

Do not use Pydantic automatically for every domain object.

Entities and aggregates require explicit identity and lifecycle semantics.

---

## 6.10 Market Analysis Rules

Market Analysis outputs are:

```text
Features
Structures
States
```

`Detector`, `Classifier` and `Transformation` are not top-level domain categories.

Every component declares:

```text
id
version or implementation hash
parameters
dependencies
input requirements
output schema
timeframe requirements
alignment policy
cache policy
determinism assumptions
```

Dependencies must be visible before execution.

Hidden component calls inside `compute()` are prohibited.

---

## 6.11 MarketFieldReference Rules

Model definitions must not access arbitrary DataFrames or storage objects.

Simple source-data references may use controlled:

```text
MarketFieldReference
```

A MarketFieldReference must preserve:

- dataset lineage,
- field identity,
- timeframe,
- temporal availability,
- dependency-graph compatibility.

The agent must not use MarketFieldReference as a bypass around repositories or lineage.

---

## 6.12 Time and Multitimeframe Rules

The agent must:

- use timezone-aware UTC timestamps,
- use Clock abstractions,
- use Trading Calendars,
- distinguish source, computation and evaluation timeframe,
- keep resampling explicit,
- preserve observed_at and available_at,
- use LAST_CLOSED_BAR by default,
- use backward as-of semantics or equivalent,
- prevent incomplete higher-timeframe look-ahead.

Naive datetimes are forbidden.

---

## 6.13 Data Rules

The agent must:

- normalize provider data at boundaries,
- preserve dataset identity and lifecycle,
- keep `finalize()` and `publish()` separate,
- consume published DatasetRefs in Research,
- avoid direct file access from Research, Strategy and Market Analysis,
- avoid hidden downloads,
- preserve futures and continuous-series lineage.

---

## 6.14 Research Rules

The agent separates:

```text
Research Computation
```

from:

```text
Research Analytics
```

Signal Research must support:

```text
Market Model only
Signal Model only
Market Model × Signal Model
```

Strategy Research evaluates complete Strategy Models.

The agent must not force recomputation because a new report or ranking was added.

---

## 6.15 Research Space Rules

The agent distinguishes:

```text
fixed selection
independent alternatives
logical composition
bounded search space
```

A list is not automatically:

- logical OR,
- full Cartesian expansion.

Large expansions require explicit configuration and visible multiple-testing metadata.

---

## 6.16 Strategy Research Rules

The agent preserves full lineage:

- Strategy Model components,
- versions or hashes,
- dataset versions,
- execution assumptions,
- simulation engine version,
- random seed.

Rankings state their objective and filters.

The highest metric value is not automatically a validated strategy.

Batch/vectorized backtesting belongs to Research.

Replay Execution does not.

---

## 6.17 Strategy Execution Rules

The agent must:

- preserve order lifecycle transitions,
- normalize broker statuses,
- make event handling idempotent where required,
- separate Strategy Risk from operational risk controls,
- persist critical runtime state,
- support reconciliation,
- expose failures,
- keep Replay, Paper and Live as Execution modes.

Live trading code must fail safely.

---

## 6.18 Error Handling Rules

Errors must be:

- typed,
- explicit,
- actionable,
- logged at boundaries.

Forbidden:

```python
except Exception:
    pass
```

Do not silently:

- drop data,
- skip failed orders,
- replace invalid values,
- ignore missing dependencies,
- continue after state corruption,
- reuse incompatible caches,
- change research scope,
- reduce a search space without metadata.

---

## 6.19 Testing Rules

Every implementation includes tests appropriate to its level.

### Unit Tests

Required for:

- domain models,
- Features,
- Structures,
- States,
- Market Models,
- Signal Models,
- SignalOccurrence,
- Exit Models,
- Risk Models,
- expression trees,
- dependency resolution,
- fingerprint generation.

### Temporal Tests

Required for:

- source/computation/evaluation timeframe,
- LAST_CLOSED_BAR,
- available_at,
- as-of alignment,
- session boundaries,
- DST transitions,
- incomplete-bar look-ahead.

### Integration Tests

Required for:

- providers,
- importers,
- brokers,
- storage,
- messaging,
- external calendars.

External tests are opt-in.

### Regression Tests

Required for:

- bug fixes,
- numerical changes,
- dataset transformations,
- temporal alignment changes,
- research metric changes.

### Workflow Tests

Required for:

- three Signal Research scopes,
- no mandatory Research-to-Execution dependency,
- no mandatory Signal Research-to-Strategy Research dependency,
- backtest/replay separation,
- reuse of stored datasets.

---

## 6.20 Documentation Rules

When changing a model, workflow or public contract, the agent updates:

- relevant architecture documentation,
- public API documentation,
- examples,
- configuration schemas,
- ADRs where architectural.

Documentation and code must not contradict each other.

---

## 6.21 Change Safety Rules

Before modifying a public contract, inspect:

- consumers,
- tests,
- user plugin compatibility,
- serialized configuration,
- persisted dataset metadata,
- persisted research metadata.

Breaking changes require:

- explicit migration plan,
- version change,
- documentation,
- ADR when architectural.

---

## 6.22 AI Agent Prohibitions

An AI agent must not:

1. create a monolithic Strategy class,
2. combine Signal Research, Strategy Research and Strategy Execution into one pipeline,
3. require Strategy Research to consume Signal Research workflow state,
4. require Strategy Execution to consume Research workflow state,
5. put proprietary user logic into `src/`,
6. bypass public contracts,
7. introduce distributed infrastructure without justification,
8. recalculate deterministic dependencies per experiment,
9. hide component dependencies,
10. use naive datetimes,
11. expose final higher-timeframe values before availability,
12. allow models to access arbitrary DataFrames,
13. silently change result semantics,
14. invent undocumented domain fields,
15. delete or rewrite user data,
16. treat rankings as proof of robustness,
17. expose credentials,
18. disable tests to make a change pass.

---

## 6.23 Completion Checklist

Before completing a task, verify:

```text
[ ] Correct domain ownership
[ ] Market Analysis terminology is used consistently
[ ] Workflow independence is preserved
[ ] Signal Research scope is explicit
[ ] Public contracts are respected
[ ] src/user_data boundary is preserved
[ ] Component and model fingerprints are preserved where required
[ ] Time and availability rules are respected
[ ] Dataset lineage is preserved
[ ] Dependencies are explicit
[ ] No hidden resampling exists
[ ] Backtest and Replay Execution remain separate
[ ] Tests were added or updated
[ ] Documentation was updated
[ ] No unnecessary infrastructure was introduced
[ ] No hidden breaking change exists
```

---

# 7. Architectural Decision Records

## 7.1 Purpose

Architectural Decision Records preserve:

```text
Why a decision was made
```

Architecture documents describe the current system.

ADRs preserve the reasoning and alternatives behind significant decisions.

---

## 7.2 When an ADR Is Required

Create an ADR when a decision:

- changes domain boundaries,
- introduces a major abstraction,
- changes dependency direction,
- changes workflow semantics,
- changes public model contracts,
- changes dataset identity or lifecycle,
- changes storage strategy,
- introduces new infrastructure technology,
- introduces distributed processing,
- introduces breaking compatibility,
- resolves a significant architectural disagreement.

Do not create ADRs for trivial implementation details.

---

## 7.3 ADR Location

Suggested location:

```text
docs/adr/
```

Suggested naming:

```text
0001-use-modular-monolith.md
0002-separate-src-and-user-data.md
0003-use-utc-internally.md
```

ADR numbers are sequential and immutable.

---

## 7.4 ADR Statuses

Supported statuses:

```text
Proposed
Accepted
Rejected
Deferred
Superseded
Deprecated
```

An accepted ADR is not rewritten to change history.

A changed decision requires a new ADR and supersession reference.

---

## 7.5 ADR Template

```markdown
# ADR-XXXX: Decision Title

## Status

Proposed | Accepted | Rejected | Deferred | Superseded

## Date

YYYY-MM-DD

## Context

What problem or constraint requires a decision?

## Decision

What has been decided?

## Rationale

Why was this option selected?

## Alternatives Considered

What other options were evaluated?

## Consequences

### Positive

- ...

### Negative

- ...

### Risks

- ...

## Compatibility and Migration

How does this affect existing code, data and user components?

## Related Decisions

- ADR-XXXX
```

---

## 7.6 Accepted Decisions

The following decisions are established and should be represented by ADRs where not already recorded.

### Modular Monolith

```text
Use a modular monolith before microservices.
```

### Independent Capabilities

```text
Signal Research, Strategy Research and Strategy Execution are independent workflows.
```

### Market Analysis Domain

```text
Use Market Analysis as the analytical domain name.
```

### Market Analysis Taxonomy

```text
Market Analysis outputs are Features, Structures and States.
```

### Declarative Models

```text
Market Models and Signal Models are declarative compositions over Market Analysis outputs.
```

### Signal Research Scope

```text
Signal Research supports Market Model only, Signal Model only and combined scope.
```

### Strategy Composition

```text
Strategy Model =
Market Model × Signal Model × Exit Model × Risk Model
```

### Position Sizing

```text
Position sizing belongs to the Risk Model in Version 1.
```

### SignalOccurrence Ownership

```text
SignalOccurrence belongs to the Strategy Domain.
```

### Market Analysis Engine

```text
Use the Market Analysis Engine for DAG-based dependency resolution, lazy execution and caching.
```

### Temporal Semantics

```text
Distinguish source, computation and evaluation timeframe.
Use observed_at and available_at.
Use LAST_CLOSED_BAR by default.
```

### MarketFieldReference

```text
Allow controlled MarketFieldReference objects.
Do not allow arbitrary DataFrame access from model expressions.
```

### Research and Execution Separation

```text
Batch/vectorized backtesting belongs to Research.
Replay, Paper and Live modes belong to Strategy Execution.
```

### Dataset Lifecycle

```text
finalize() and publish() are separate transitions.
```

### Persistent Research Datasets

```text
Separate Research Computation from Analytics and persist reusable datasets.
```

### Working Fingerprints

```text
Working components and mutable model definitions used in Research require fingerprints.
```

### Framework and User Space

```text
Reusable framework code belongs in src/.
Proprietary know-how belongs in user_data/.
```

### UTC Policy

```text
Use timezone-aware UTC internally.
```

### Hybrid Communication

```text
Use direct calls for deterministic Research and events for Strategy Execution where justified.
```

### Historical Storage

```text
Use Parquet as the primary historical market-data format.
```

### Configuration Boundaries

```text
Use Pydantic for configuration and validation boundaries, not automatically for every domain model.
```

---

## 7.7 Deferred Decisions

The following remain deferred until requirements justify them:

- distributed Market Analysis Engine,
- Kafka or another distributed event broker,
- Spark,
- Kubernetes,
- microservices,
- distributed Strategy Execution,
- dedicated feature-store product,
- automatic ML feature-vector layer,
- full DOM data model,
- options snapshot model,
- full order-flow event model,
- full event sourcing,
- workflow visual DAG editor,
- remote user component registry,
- multi-node research scheduler,
- separate Position Sizing Model.

Deferred does not mean rejected.

The current architecture must not depend on these concepts.

---

## 7.8 Future Decision Triggers

### Distributed Processing

Reconsider when:

- one machine cannot process required datasets in acceptable time,
- memory limits are repeatedly exceeded,
- independent workloads require horizontal scheduling.

### Distributed Messaging

Reconsider when:

- event durability exceeds in-memory capabilities,
- multiple independent services consume the same stream,
- partitioned ordering and replay become operational requirements.

### Microservices

Reconsider when:

- modules require independent deployment,
- modules scale independently,
- separate teams own clear bounded contexts,
- process isolation provides measurable value.

### Feature Store

Reconsider when:

- the same analytical outputs are shared across Research and Strategy Execution at significant scale,
- online/offline consistency becomes a demonstrated problem,
- local Parquet and cache solutions are insufficient.

### Position Sizing Model

Reconsider when:

- risk budget and sizing require independent composition,
- sizing variants need separate research,
- execution or portfolio requirements justify independent versioning.

---

## 7.9 ADR Review Rules

Every ADR review should verify:

```text
Does the decision solve a demonstrated problem?
Does it preserve domain ownership?
Does it preserve workflow independence?
Does it preserve reproducibility?
Does it increase operational complexity?
Can a simpler option solve the problem?
Does it affect user_data compatibility?
Does it require migration?
Is the decision reversible?
```

---

## 7.10 ADR Ownership

An ADR should identify:

- author,
- reviewers,
- affected modules,
- implementation status.

AI agents may draft ADRs.

They must not silently accept material architectural decisions without human review.

---

# 8. Final Contract

The framework preserves three independent capabilities:

```text
Signal Research
Strategy Research
Strategy Execution
```

They share:

```text
Market
Market Analysis
Strategy Definitions
Time
Configuration
Infrastructure Contracts
```

They do not share mandatory workflow state.

The implementation must ensure that:

```text
Signal Research evaluates Market Models, Signal Models or both.

Strategy Research evaluates complete Strategy Models.

Strategy Execution runs selected Strategy Models in Replay, Paper or Live modes.

Research Computation produces reusable datasets.

Research Analytics interprets stored datasets.

AI agents preserve architecture rather than inventing it.

ADRs preserve the reasoning behind significant decisions.
```

Every future workflow, implementation and architectural decision must remain consistent with this contract.
