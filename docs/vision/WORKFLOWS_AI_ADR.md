# Trading Research Framework

# WORKFLOWS_AI_ADR.md

> **Sprint 054 T006c note:** most of this document's §1–§5/§8 content was
> classified CURRENT (already built, verified against
> `src/trading_framework/`) by
> `docs/planning/sprints/SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md`
> and has moved to
> [`docs/reference/system/WORKFLOWS_ARCHITECTURE.md`](../reference/system/WORKFLOWS_ARCHITECTURE.md).
> What remains here is future-facing, ambiguous-status, or a section whose
> "suggested" contract has diverged from what is actually built (notably
> Strategy Families §4.14, Broker Abstraction §5.11, Reconciliation §5.12
> and Recovery §5.13 — all confirmed FUTURE with zero code counterpart). See
> the classification doc for the full section-by-section reasoning and
> evidence before assuming anything below is or is not built.
>
> §6 "AI Agent Contract" was consolidated into `AGENTS.md` /
> `.cursor/rules/ARCHITECTURE_CONTROL.md` by Sprint 054 T006b, and §7
> "Architectural Decision Records" into `docs/adr/README.md` by Sprint 054
> T006a — see those sections below for pointers to the current, authoritative
> versions.

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

## 2.3 Workflow Execution

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §2.3. The
pipeline shape and the "workflow layer coordinates, does not implement
domain logic" rule both hold on the research side
(`research/signal_research/family_planning.py` → `research/simulation/engine.py`
→ `research/datasets/` → `research/analytics/`). On the execution/runtime
side only the `DRY_RUN` path exists, so the "Persistent Results or
Operational State" outcome is correspondingly narrower than described below.)*

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

## 2.5 Workflow Identity

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §2.5.
`run_id`-based identity/fingerprinting is pervasive, and
`research/simulation/assumptions.py`'s `simulation_assumptions_fingerprint()`
is a concrete, narrower instance of "execution_assumptions included in run
identity." No single class implements the exact 18-field identity list
below, and a literal `random_seed` component of workflow identity does not
exist; the general principle — stable, input-derived run identity — is real,
the literal field list is not.)*

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

## 3.12 Research Space Boundaries

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §3.12. The
four-way conceptual distinction is real and implemented, and
`FamilyExperimentPlan` exposes `candidates_generated`/`candidates_evaluated`/
`candidates_skipped` — a subset of the telemetry fields suggested below. The
literal fields `number_of_unique_dependencies`, `number_of_reused_nodes`,
`number_of_new_nodes` and `estimated_output_size` do not exist in the
planner.)*

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

## 3.14 Signal Research Analytics

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §3.14.
`research/analytics/{conditional,diagnostics,grouping,distribution,histograms,aggregates}.py`
implement a substantial subset of the operations below (conditional
analysis, distributions, grouping/aggregation). "Clustering" and general
"insight generation" have no code counterpart.)*

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

## 3.16 Storage

*(Classified AMBIGUOUS by T003b — as-built status unclear as of Sprint 054,
see `SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §3.16.
This describes a `user_data/` workspace on-disk convention, not a
`src/trading_framework/` code contract; per ADR-0022 `user_data/` is a
private workspace outside the framework repo's own tree, out of `src/`-grep
scope.)*

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

# 4. Strategy Research

## 4.3 Inputs

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.3.
`SimulationAssumptions` confirms commission/slippage/fill-policy/capital
assumptions exist as inputs; no `latency` field exists in
`research/simulation/assumptions.py`, so latency assumptions specifically
are not modeled. "May reuse Signal Research artifacts without requiring a
run ID" was not independently verified.)*

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

## 4.5 Strategy Research Space

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.5. No
`research/strategy_research/` package equivalent to
`research/signal_research/family_planning.py` was found; only
`application/strategy_research/` exists, which orchestrates but does not
implement family-style bounded multi-dimension expansion. The
`experiments:` YAML example below is presented as already-working syntax
but has no implementing module.)*

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

## 4.7 Computational Reuse

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.7. The
underlying Market Analysis dependency-graph reuse mechanism is confirmed
CURRENT; `execution/runtime/strategy_orders.py`/`decision_step.py` and
`research/simulation/engine.py` consume already-resolved Market Analysis
outputs. Whether "entry candidate datasets" specifically are cached/reused
across multiple Strategy Models in one run was not independently verified.)*

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

## 4.9 Research Backtest vs Replay Execution

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.9. The
Research Backtest side is fully built (`research/simulation/engine.py`).
`Grep` for `ReplayClock`/`replay_clock`/`class Replay` returned zero matches
anywhere in `src/` — Replay Execution has no code counterpart at all,
consistent with `ExecutionMode` supporting only `DRY_RUN`.)*

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

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.10.
`SimulationAssumptions` (`fill_policy_entry`, `fill_policy_exit`,
`slippage_bps`, `commission_per_side`, `initial_capital`) is a concrete,
fingerprinted, narrower instance of "material assumption changes run
identity." `latency_model`, `position_netting_policy`,
`contract_specification`, `roll_policy`, `currency_conversion_policy` and
`simulation_engine_version` as named fields were not found.)*

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

## 4.13 Rankings

*(Classified AMBIGUOUS by T003b — as-built status unclear as of Sprint 054,
see `SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.13.
`Grep` for `ranking`/`Ranking` found matches only in `research/robustness/`
(verdict/report formatting) and `research/predictive/leaderboard.py` (a
different research track). No `strategy_research`-scoped ranking module
with the six-field contract below was found; the search was not exhaustive.)*

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

*(Classified FUTURE by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.14.
Unlike Signal Research (`family_planning.py`, `signal_research_family.py` —
confirmed CURRENT), there is no Strategy-Research-side "family" concept in
code at all. The `families/` subfolder in §4.20's suggested storage layout
is itself inconsistent with this finding.)*

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

## 4.18 Multiple Testing

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.18.
`candidates_generated`/`candidates_evaluated`/`candidates_skipped` are
confirmed CURRENT for Signal Research families, and
`research/predictive/splitting.py` confirms validation-split definitions
exist for the Predictive Research track. For Strategy Research specifically,
no equivalent candidate-count bookkeeping was found, consistent with §4.5/
§4.14's finding that Strategy Research lacks a family/bounded-expansion
mechanism analogous to Signal Research's.)*

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

## 4.20 Storage

*(Classified AMBIGUOUS by T003b — same reasoning as §3.16: a `user_data/`
workspace convention, out of `src/`-grep scope per ADR-0022. See
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.20.
Note the `families/` subfolder below is inconsistent with §4.14's confirmed
finding that Strategy Families have no code counterpart today.)*

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

*(Classified MIXED by T003b, by inheritance — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §4.21.
Most of the 14 rules below restate §4.1–§4.20 content that is largely
CURRENT (moved to
[`docs/reference/system/WORKFLOWS_ARCHITECTURE.md`](../reference/system/WORKFLOWS_ARCHITECTURE.md)),
but rules 6/7 restate the §4.9 Replay-vs-Backtest split (MIXED — Replay
absent) and rule 11 restates §4.14 Strategy Families (FUTURE).)*

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

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.1.
Order lifecycle/fill processing/position state exist for the `DRY_RUN` mode;
"independent from research workflows" is confirmed. No broker communication,
reconciliation, or recovery code was found anywhere in `execution/` — see
§5.11–§5.13 below.)*

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

## 5.4 Execution Modes

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.4.
`execution/modes.py` defines `SUPPORTED_EXECUTION_MODES = frozenset({ExecutionMode.DRY_RUN})`:
only one mode is enabled today, named `DRY_RUN` rather than literally "Paper
Execution" (though `PaperBroker` is functionally close to Paper Execution's
"simulated broker interaction"). Replay Execution and Live Execution have
zero code counterpart.)*

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

## 5.6 Event-Driven Runtime

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.6.
`execution/models/events.py`'s `ExecutionEventType` overlaps conceptually
but is not name-identical to the event list below (only one combined
`SIMULATED_ORDER_FILLED`, no `MarketBarReceived`/`AnalysisStateUpdated`
equivalents). `Grep` for `EventBus`/`class Event\b` returned zero matches —
there is no generic pub/sub EventBus; the top-level `events/` package is an
empty stub.)*

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

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.7.
`execution/models/orders.py`'s `OrderStatus` has only `CREATED`,
`SIMULATED_FILLED`, `SIMULATED_REJECTED` — a 3-state simplified lifecycle
for the `DRY_RUN` case, not the full 8-state normalized lifecycle described
below. "Broker-specific statuses normalized at the adapter boundary" has no
code counterpart since no broker adapter exists — see §5.11.)*

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

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.8.
`SimulatedFill` has `fill_id`, `order_id`, `quantity`, `price`, `liquidity`
fields, consistent with "accepted fills are facts." No partial-fill support
(one fill per simulated order), no commission/fee field on `SimulatedFill`
itself, and no duplicate-fill detection or correction-event mechanism were
found.)*

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

## 5.11 Broker Abstraction

*(Classified FUTURE by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.11.
`Grep` for all nine named method signatures below in `execution/protocols.py`
returned zero matches. `PaperBroker` is a single-symbol, single-process
dataclass with no `connect`/`disconnect`/adapter-boundary methods — there is
no broker abstraction layer, pluggable or otherwise, only one hardcoded
simulated implementation.)*

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

*(Classified FUTURE by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.12. No
reconciliation module, incident type, or mismatch-detection logic was found
anywhere in `src/trading_framework/`. Consistent with §5.11 — reconciliation
requires an external broker to reconcile against, which does not exist.)*

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

*(Classified FUTURE by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.13. No
recovery/restart module was located in `execution/`, and recovery depends on
the reconciliation mechanism confirmed absent at §5.12.)*

Strategy Execution supports recovery after:

- process restart,
- network disconnect,
- broker reconnect,
- provider interruption.

Recovery uses persisted execution state and broker reconciliation.

In-memory state alone is insufficient.

---

## 5.15 Observability

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.15.
`execution/runtime/health_policy.py` implements health-check logic, and
`ExecutionEvent`'s `RUNTIME_FAILED`/`HEARTBEAT_RECORDED` event types provide
a basis for audit trails and failure monitoring. No dedicated
metrics/alerting module or latency-monitoring instrumentation was found.)*

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

*(Classified MIXED by T003b, by inheritance — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §5.16.
Most of the 12 rules below restate §5.1–§5.15 content (CURRENT/MIXED), but
rule 8 ("Broker state is reconciled") and rule 10 ("Recovery is explicit")
restate the confirmed-FUTURE §5.12/§5.13 content.)*

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

**Consolidated into `AGENTS.md` (root) and `.cursor/rules/ARCHITECTURE_CONTROL.md`
as of Sprint 054 T006b (2026-09-03).** Domain ownership, dependency
direction, workflow independence and prohibited-behaviour rules already
lived in `.cursor/rules/ARCHITECTURE_CONTROL.md` §3-§11 and duplicated
this section; the required-reading order contradiction between this
section and `AGENTS.md` was resolved in favor of `AGENTS.md` (loaded on
every agent session — see its Required Reading Order, which now also lists
this file's §1-5/§8 explicitly). The genuinely new material — the local
component lifecycle / promotion gate, fingerprint rules, the test-level
matrix and the completion checklist — was folded into
`.cursor/rules/ARCHITECTURE_CONTROL.md` §6a, §6b and §12. See those files
for current agent guidance; this section is retained here only as a
historical record and is no longer authoritative.

---

# 7. Architectural Decision Records

The ADR process (when an ADR is required, numbering/location, status
vocabulary, template, review rules and ownership) and the decision register
(established decisions, deferred items and their reconsideration triggers)
were consolidated into **[`docs/adr/README.md`](../adr/README.md) as of
Sprint 054 T006a** — see there for the current, authoritative version. This
section previously duplicated, and in places contradicted, that file (a
different status vocabulary, a different template, and a "suggested
location: docs/adr/" fossil from before `docs/adr/` existed with 30+ real
ADRs). Nothing in the decision register was dropped: decisions already
covered by an `ACCEPTED` ADR were removed as duplicates, and every decision,
deferred item and reconsideration trigger without an ADR yet is carried
forward in `docs/adr/README.md`'s "ADR Backlog" section.

---

# 8. Final Contract

*(Classified MIXED by T003b — see
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md` §8. Every
substantive claim below is a restatement of content classified above; its
MIXED status is inherited from §5.4's confirmed partial-execution-mode
finding — "Strategy Execution runs selected Strategy Models in Replay,
Paper or Live modes" only holds for one mode (`DRY_RUN`) today.)*

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
