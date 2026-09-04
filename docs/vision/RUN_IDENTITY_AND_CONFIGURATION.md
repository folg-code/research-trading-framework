# Trading Research Framework

# RUN_IDENTITY_AND_CONFIGURATION.md

> **Target architecture / not-yet-built content.** This file was created by
> Sprint 055 T008 out of `docs/vision/ARCHITECTURE_TECHNICAL.md` §9.1,
> §9.2, §9.4, §9.6, §9.10; and `docs/vision/WORKFLOWS_AI_ADR.md` §2.3,
> §2.5, §3.16 (record-fields portion only), §4.3, §4.7, §4.10, §4.20
> (record-fields portion only), §4.21 (both source files now dissolved).
> "What a run resolves, records and fingerprints" — configuration layering,
> workflow identity and execution assumptions — is one reproducibility
> question, previously answered in two files with overlapping field lists.
> Content below is preserved verbatim from the original files; only
> classification headers, this merge header, and provenance notes are
> newly authored/added.

---

## Workflow Execution

*(Merged from: `WORKFLOWS_AI_ADR.md` §2.3, now dissolved. Classified MIXED
by Sprint 054 T003b — the pipeline shape and the "workflow layer
coordinates, does not implement domain logic" rule both hold on the
research side (`research/signal_research/family_planning.py` →
`research/simulation/engine.py` → `research/datasets/` →
`research/analytics/`). On the execution/runtime side only the `DRY_RUN`
path exists, so the "Persistent Results or Operational State" outcome is
correspondingly narrower than described below.)*

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

## Workflow Identity

*(Longest/primary copy — merged from: `WORKFLOWS_AI_ADR.md` §2.5, now
dissolved. Classified MIXED by Sprint 054 T003b — `run_id`-based
identity/fingerprinting is pervasive, and
`research/simulation/assumptions.py`'s `simulation_assumptions_fingerprint()`
is a concrete, narrower instance of "execution_assumptions included in run
identity." No single class implements the exact 18-field identity list
below, and a literal `random_seed` component of workflow identity does not
exist; the general principle — stable, input-derived run identity — is
real, the literal field list is not.)*

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

> **Merged from: `ARCHITECTURE_TECHNICAL.md` §9.10 "Configuration
> Versioning", now dissolved.** That section (classified FUTURE by Sprint
> 054 T002 at the general-rule level — dataset-level and
> predictive-run-level fingerprinting is confirmed CURRENT elsewhere, but a
> generic, framework-wide "every persisted run records resolved
> configuration + framework version" guarantee applying uniformly across
> all workflows was not found) restated a narrower 6-field version of the
> same idea:
>
> ```text
> resolved configuration
> configuration schema version
> component versions or fingerprints
> model versions or fingerprints
> dataset versions
> framework version
> ```
>
> No field here is unique versus the 18-field list above; "configuration
> schema version" is the only wording not already implied by "resolved
> configuration."
>
> **Merged from: `WORKFLOWS_AI_ADR.md` §3.16 "Storage" (record-fields
> portion only), now dissolved.** That section's per-run record list —
> `run_id`, `research_scope`, `resolved_config`, `dataset_references`,
> `component_versions or hashes`, `model_versions or hashes`,
> `execution_plan`, `result_manifest`, `validation_summary` — is a
> Signal-Research-scoped instance of the same identity concept. Its
> `user_data/` directory-layout portion is evicted to
> `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md` §5.

---

## Strategy Research Inputs

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.3, now dissolved. Classified MIXED
by Sprint 054 T003b — `SimulationAssumptions` confirms
commission/slippage/fill-policy/capital assumptions exist as inputs; no
`latency` field exists in `research/simulation/assumptions.py`, so latency
assumptions specifically are not modeled. "May reuse Signal Research
artifacts without requiring a run ID" was not independently verified.)*

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

## Computational Reuse

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.7, now dissolved. Classified MIXED
by Sprint 054 T003b — the underlying Market Analysis dependency-graph reuse
mechanism is confirmed CURRENT; `execution/runtime/strategy_orders.py`/
`decision_step.py` and `research/simulation/engine.py` consume
already-resolved Market Analysis outputs. Whether "entry candidate
datasets" specifically are cached/reused across multiple Strategy Models in
one run was not independently verified.)*

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

## Execution Assumptions

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.10, now dissolved. Classified MIXED
by Sprint 054 T003b — `SimulationAssumptions` (`fill_policy_entry`,
`fill_policy_exit`, `slippage_bps`, `commission_per_side`,
`initial_capital`) is a concrete, fingerprinted, narrower instance of
"material assumption changes run identity." `latency_model`,
`position_netting_policy`, `contract_specification`, `roll_policy`,
`currency_conversion_policy` and `simulation_engine_version` as named
fields were not found.)*

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

## Strategy Research Rules

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.21, now dissolved. Classified MIXED
by Sprint 054 T003b, by inheritance — most of the 14 rules below restate
content that is largely CURRENT (moved into the former
`docs/reference/system/WORKFLOWS_ARCHITECTURE.md`, which Sprint 055 T007
split into [`docs/reference/workflows/STRATEGY_RESEARCH.md`](../reference/workflows/STRATEGY_RESEARCH.md)
and [`docs/reference/workflows/STRATEGY_EXECUTION.md`](../reference/workflows/STRATEGY_EXECUTION.md)),
but rules 6/7 restate the Research-Backtest-vs-Replay-Execution split
(MIXED — Replay absent, see `EXECUTION_RUNTIME_FUTURE.md`) and rule 11
restates Strategy Families (FUTURE, see
`RESEARCH_SPACE_AND_ANALYTICS.md`).)*

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

## Configuration Architecture Purpose

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §9.1, now dissolved.)*

Configuration defines how framework components are selected, instantiated and composed.

Configuration remains separate from implementation.

Supported configuration areas include:

- system,
- market data,
- Market Analysis,
- model definitions,
- research,
- Strategy Execution.

---

## Configuration Principles

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §9.2, now dissolved. Classified
MIXED by Sprint 054 T002. "Explicit" and "validated" are confirmed via
Pydantic-backed config (`config/loader.py`); "versionable"/"reproducible"
in the sense of persisted resolved-configuration-per-run was not found as a
general framework capability.)*

Configuration must be:

- explicit,
- validated,
- versionable,
- serializable,
- reproducible,
- environment-independent where possible.

Arbitrary executable Python code is forbidden in configuration files.

---

## Configuration Layers

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §9.4, now dissolved. Classified
FUTURE by Sprint 054 T002 — `config/loader.py` implements a single-file
TOML loader with no layered precedence/merge logic; no environment-variable
overlay or run-override merge step was found.)*

Suggested precedence:

```text
Framework Defaults
        ↓
Environment Configuration
        ↓
User Configuration
        ↓
Run-Specific Overrides
```

Resolved configuration is persisted with each run.

---

## Model Configuration

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §9.6, now dissolved. Classified
MIXED by Sprint 054 T002. `model_expression/` and `model_authoring/`
implement expression-tree-based model definitions, consistent with "no
arbitrary executable logic"; a literal YAML-file model-config loader
matching this exact example schema was not independently located.)*

Market and Signal Model configuration uses explicit expression trees.

Example:

```yaml
signal_model:
  id: bullish_sweep
  version: 1

  expression:
    operator: AND
    children:
      - component: liquidity_sweep
        timeframe: 1m
        condition:
          field: direction
          equals: bullish

      - component: price_reclaim
        timeframe: 1m
        condition:
          equals: true
```

Model configuration must not embed arbitrary executable logic.
