# Terminology

This page defines the vocabulary used by maintained product and reference
documentation. It separates user-facing language from stable technical
identifiers. Existing schemas, commands, packages and persisted paths retain
their names; see [ADR-0045](../../adr/ADR-0045-layered-research-terminology.md)
for the compatibility boundary.

## Research lifecycle

| Term | Meaning | Not a synonym for |
|---|---|---|
| Research | The umbrella business domain and product area | One mandatory end-to-end pipeline |
| Methodology | Rules for framing a question and evaluating its evidence | Executable orchestration |
| Workflow | Executable orchestration provided by the application layer | Methodology or pipeline |
| Use case | One callable operation inside or alongside a workflow | The whole workflow |
| Pipeline | A data-transformation chain with ordered stages | Every workflow |
| Definition / Spec | A declaration of what a workflow should execute | An execution or its result |
| Experiment | A workflow-local controlled comparison of variants | A framework-wide aggregate |
| Run | One execution with its own identity | Definition or experiment |
| Artifact | Persisted output or evidence | The computation that produced it |
| Portfolio Study | Editorial grouping in the presentation layer | Shared `StudyId`, repository or cross-workflow lineage |

The usual relationship is:

```text
Methodology guides a question
  → Definition declares one intended execution
  → Workflow executes it as a Run
  → Run persists Artifacts

Experiment (where supported)
  → controls multiple variant Runs
  → persists comparison Artifacts
```

These relationships do not require every workflow to implement an Experiment.
They also do not introduce a common framework-level Study aggregate.

## Market & Signal Study

**Market & Signal Study** is the product-facing name for configuring and
running the workflow technically named **Signal Research**. The technical name
remains visible at CLI, configuration, API and source-code boundaries.

The selected scope must be stated explicitly:

| Product scope | Stable value | Meaning |
|---|---|---|
| Market Model-only | `MARKET_MODEL_ONLY` | Evaluate market context without requiring a signal |
| Signal Model-only | `SIGNAL_MODEL_ONLY` | Evaluate a signal without an additional market-context filter |
| Market Model and Signal Model | `MARKET_AND_SIGNAL` | Evaluate a signal within selected market context |

The command `trading-cli research run signal` and the
`SignalResearchDefinitionSpec` name are compatibility identifiers. They are not
renamed by product copy.

## Qualified model language

Use a qualified term whenever the concept is known:

| Preferred term | Meaning | Existing technical contract |
|---|---|---|
| Market Model | Declarative market-context hypothesis | `MarketModelDefinition` |
| Signal Model | Declarative trading-opportunity hypothesis | `SignalModelDefinition` |
| Estimator | Statistical or machine-learning estimator | `EstimatorSpec` and estimator adapters |
| Exit Policy | Rules for reducing or closing exposure | `ExitModel` |
| Risk Policy | Position sizing and exposure constraints | `RiskModel` |
| Strategy Definition | Complete strategy composition | `StrategyModelDefinition` |
| View Model | Read-oriented presentation structure | Presentation-layer types |

The explanatory names Exit Policy, Risk Policy and Strategy Definition do not
create aliases or deprecate the existing Python contracts. Avoid a bare
user-facing label such as `Model` when Market Model, Signal Model or Estimator
is known.

## Specialist abbreviations

Expand these terms at first use on a user-facing entry point. Technical pages
may use the abbreviation after defining it or linking here.

| Abbreviation | Expansion |
|---|---|
| OHLCV | Open, high, low, close and volume market bars |
| MFE | Maximum favorable excursion |
| MAE | Maximum adverse excursion |
| PnL | Profit and loss |
| DAG | Directed acyclic graph |
| DSL | Domain-specific language |
| RTH | Regular trading hours |
| bps | Basis points; one basis point is 0.01 percentage point |

## Writing and compatibility rules

- Use product language on user-facing surfaces and name the technical mapping
  where a user crosses into a command, configuration, API or code contract.
- Use technical identifiers verbatim in code examples and compatibility
  documentation.
- Do not rewrite historical manifests, archived plans, accepted ADRs, schema
  fields, hashes or persisted paths to match current editorial terminology.
- Distinguish what guides evaluation (methodology), what runs (workflow or use
  case), what transforms data (pipeline), what is declared (definition), what
  executes (run) and what remains as evidence (artifact).
- Treat catalog subject typing as a separate contract change. The current
  dashboard's inferred `model` field is not made canonical by this glossary.
