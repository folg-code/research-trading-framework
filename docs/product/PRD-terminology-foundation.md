# PRD — Terminology Foundation

```text
Status: ACCEPTED
Discovery: maintainer discussion completed 2026-09-15
Architecture triage: completed 2026-09-15; ADR-0045 proposed
Approved-by: Filip Folga, 2026-09-15 — instructed implementation to continue
             after review of the proposed PRD and ADR-0045 direction
```

## Problem

The framework has coherent domain boundaries, but its vocabulary does not
consistently expose them to users and maintainers.

`Research` names the domain, several methodologies and workflows, application
surfaces, commands and persisted locations. `Signal Research` additionally
supports Market Model-only, Signal Model-only and combined scopes, so its name
can imply a narrower activity than the workflow actually performs.

`Model` also names materially different concepts: Market Models, Signal
Models, statistical or machine-learning estimators, exit behaviour, risk and
position-sizing behaviour, and complete strategy composition. Unqualified
labels such as `model` require the reader to infer the intended meaning from
context.

The terms `study`, `definition`, `experiment`, `run`, `methodology`,
`workflow`, `pipeline` and `artifact` do not have one stable relationship
across documentation and product surfaces. Some user-facing material also
uses specialist abbreviations without a nearby explanation.

This creates avoidable cognitive load and increases the risk that future
features freeze accidental terminology into new contracts. The first
increment must improve user-facing and explanatory language without renaming
or migrating existing framework contracts, persisted artifacts or workspace
layouts.

## Goals / Non-goals

### Goals

- Establish one canonical glossary for maintained product and reference
  documentation with these distinctions:
  - `Research` is the umbrella domain and product area;
  - `Methodology` describes how a research question is evaluated;
  - `Workflow` is executable orchestration provided by the framework;
  - `Definition` or `Spec` declares what is to be executed;
  - `Experiment` is a workflow-local controlled comparison of variants;
  - `Run` is one execution of a definition;
  - `Artifact` is a persisted result or evidence item;
  - `Portfolio Study` is editorial presentation grouping and does not imply a
    framework-level Study aggregate;
  - `Market Model` and `Signal Model` retain their accepted domain meanings;
  - `Estimator` identifies a statistical or machine-learning estimator;
  - `Exit Policy`, `Risk Policy` and `Strategy Definition` are the preferred
    explanatory names for concepts represented by the existing technical
    contracts `ExitModel`, `RiskModel` and `StrategyModelDefinition`.
- Use `Market & Signal Study` as the product-facing name for configuring and
  running the capability technically identified as Signal Research. Always
  display its scope explicitly as Market Model-only, Signal Model-only or
  combined.
- Preserve `Signal Research` where text identifies the existing technical
  workflow or compatibility contract, and explain its relationship to the
  product-facing name.
- Replace unqualified user-facing uses of `model` with the applicable
  qualified term whenever the concept is known.
- Distinguish methodologies, executable workflows, individual use cases and
  data-processing pipelines in maintained documentation.
- Expand or locally explain OHLCV, MFE, MAE, PnL, DAG, DSL, RTH and bps at
  their first user-facing occurrence in the scoped entry points.
- Update scoped Workbench copy, CLI help and maintained documentation
  additively, without changing workflow behaviour.
- Record a compatibility boundary so future terminology work cannot silently
  become a contract or artifact migration.

### Non-goals

- Renaming Python packages, modules, classes, protocols or imports.
- Renaming schema versions, serialized fields, workflow identifiers,
  `research_id`, `experiment_id`, `run_id` or existing CLI commands.
- Renaming or migrating directories under `user_data/`, including
  `research/market_research/`.
- Rewriting historical manifests, configurations, reports, snapshots,
  accepted ADRs, archived planning records or persisted artifacts.
- Changing `definition_hash`, run identity, lineage, comparison semantics or
  research behaviour.
- Introducing a framework-level Study aggregate or redefining the existing
  dashboard-local `PortfolioStudyManifest`.
- Adding compatibility aliases or deprecating `ExitModel`, `RiskModel` or
  `StrategyModelDefinition`; that requires a separate code-contract decision.
- Replacing the catalog's inferred `model` value with typed subject fields;
  that belongs to a separate Typed Research Catalog increment.
- Creating schema v2 or committing to a removal date for existing
  terminology.
- Redesigning historical documentation or every research workflow.
- Changing the independence of research workflows and Strategy Execution.

Any future compatibility-breaking migration requires separate approval,
explicit versioning, preservation of historical hashes and artifacts, and a
defined dual-read or alias policy where needed.

## Success metrics

- Every glossary term has one documented meaning, scope and relationship to
  existing technical names.
- In the scoped Workbench flow, a Market Model-only definition is presented
  as a `Market & Signal Study` with explicit `Market Model-only` scope and is
  never described as requiring a signal.
- Scoped user-facing surfaces contain no unqualified `model` label when the
  underlying concept is known.
- Maintained methodology and workflow indexes consistently distinguish
  methodology from executable workflow and do not imply a mandatory pipeline.
- Selected specialist abbreviations are expanded or explained at first
  occurrence in scoped entry-point documentation and UI copy.
- Existing Signal Research configuration fixtures, persisted artifact
  fixtures and compatibility tests remain unchanged and continue to load.
- Existing CLI invocations retain the same behaviour; updated help connects
  the technical command name to the product-facing terminology.
- Focused terminology checks detect explicitly retired ambiguous labels on
  scoped surfaces and allow legitimate technical and historical identifiers.
- A maintainer walkthrough can correctly distinguish methodology, workflow,
  definition, experiment, run and artifact, and Market Model, Signal Model
  and estimator.
- Verification shows no change to serialized identities, persisted paths,
  definition hashes or research results.

## User stories

- As a new framework user, I can tell whether I am choosing a methodology,
  configuring a workflow or inspecting a run without inferring lifecycle
  concepts from context.
- As a local researcher, I can configure a Market Model-only, Signal
  Model-only or combined study and see its selected scope stated plainly.
- As a local researcher, I can distinguish a Market Model, Signal Model and
  machine-learning estimator wherever they appear.
- As a strategy author, I can understand exit behaviour, risk and sizing, and
  complete strategy composition without treating every concept as the same
  kind of model.
- As a reader without specialist quant knowledge, I can find a nearby
  expansion or explanation for abbreviations on the main product path.
- As an experienced operator, I can continue using existing commands,
  configurations, imports and workspace paths without migration.
- As a maintainer, I can distinguish preferred product language from frozen
  compatibility identifiers.
- As a contributor, I can check new UI and documentation against a small
  canonical vocabulary so terminology does not drift again.

## Resolved questions

- First-use abbreviation expansions are limited to the root and current system,
  module and workflow entry points changed by this increment.
- `ExitModel`, `RiskModel` and `StrategyModelDefinition` remain unchanged at
  technical boundaries. Current explanatory copy uses Exit Policy, Risk Policy
  and Strategy Definition and names the technical contract where relevant.
- The regression guard covers the canonical lifecycle, frozen compatibility
  identifiers, retired ambiguous Workbench labels and scope-to-baseline
  compatibility. It does not scan historical or archived material.
- The public dashboard retains its current naming until a separately approved
  Typed Research Catalog increment can expose explicit research subjects.
