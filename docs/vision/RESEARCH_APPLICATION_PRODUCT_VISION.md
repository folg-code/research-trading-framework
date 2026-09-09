# Research Application — Product Vision

```text
Status: DRAFT
Discovery: maintainer Q&A completed 2026-09-09
Scope: product direction, not implementation approval or sprint scope
```

## 1. Purpose

The Research Application is the user-facing workspace for operating the
Trading Research Framework without making the framework dependent on a UI.

It turns currently separate command-line and read-only dashboard entry points
into a coherent product experience while preserving the framework's existing
domain ownership, reproducibility, and workflow independence.

The application is intended to make the common research loop discoverable and
reviewable:

```text
prepare data
    -> configure an explicit study
    -> run an existing framework workflow
    -> inspect and compare persisted results
    -> optionally publish a selected read-only view
```

This is a product direction document. It does not approve a roadmap phase,
open a sprint, select a web stack, or amend an architectural boundary.

## 2. Primary Users and Distribution Model

The first user is the project maintainer. The longer-term distribution model
is local-first and open source: another user can fork the repository, operate
the application against their own `user_data/`, and retain full access to the
underlying files and command-line workflows.

The product is not initially a hosted multi-tenant service. Accounts,
organizations, subscriptions, shared workspaces, and centrally hosted user
data are not part of the committed direction.

The user interface is English-first. Research workflows are desktop-first;
operational live monitoring and emergency controls should remain usable on a
phone-sized screen.

## 3. Product Principles

### 3.1 Application as an interface, not a second framework

The application coordinates existing framework workflows and presents their
persisted facts. It does not reimplement Market Analysis, Signal Research,
Strategy Research, predictive evaluation, strategy logic, risk logic, or
execution decisions.

```text
The application manages lifecycle.
The framework performs research and execution.
The strategy makes trading decisions.
```

### 3.2 CLI and application interoperability

The application is an additional front door, not a replacement for Python or
the CLI.

- A compatible dataset or run produced outside the application remains
  discoverable in the application.
- A configuration produced by the application remains a normal, versioned,
  human-readable file that can be inspected and used outside the UI.
- Persisted research artifacts remain the research source of truth; an
  application database may index them but must not make them proprietary to
  the application.
- Advanced or unusual strategies may remain operator-authored Python.

### 3.3 Explicit, reproducible operation

The UI reduces syntax and YAML friction without hiding material inputs. A user
can inspect the resolved configuration and validation result before starting
work. A material configuration change produces a distinct run or deployment
identity.

The application does not automatically choose a best strategy, tune
parameters, promote a model, or infer trading approval from a metric.

### 3.4 Read-only data and artifact posture

Imported source files remain untouched. Import or provider acquisition may
create a new canonical, versioned dataset, after which the application treats
the dataset as immutable.

The application does not edit market records, rewrite research artifacts,
silently migrate unsupported artifacts, or physically delete datasets and
runs. Unsupported artifacts remain visible with an explicit reason where
possible.

### 3.5 Private control and explicit publication

Private operation and public presentation are separate trust surfaces. Public
access is not implemented by hiding private controls in the browser.

Nothing becomes public automatically. A public view is created only through
an explicit publish action that produces a sanitized, read-only projection of
selected facts.

## 4. Product Surfaces

### 4.1 Local Research Workbench

The Research Workbench is the primary product surface and runs close to local
research data and compute.

Its direction includes:

- importing or acquiring market data and selecting immutable datasets,
- discovering templates and existing user models,
- creating explicit workflow configurations without requiring terminal
  syntax,
- preflight validation and run control,
- browsing persisted runs regardless of whether the UI or CLI produced them,
- workflow-specific result inspection,
- comparison with visible compatibility differences,
- optional publication of selected result snapshots.

Comparison is an analytical view, not an authority. The application may let a
user compare materially different runs, but it must show differences such as
dataset, instrument, period, timeframe, model identity, and execution
assumptions. It must not manufacture a universal winner across incompatible
methodologies.

### 4.2 Private Live/Paper Control Plane

The private control plane manages immutable strategy deployments on a VPS. A
deployment binds a strategy version to its runtime configuration, data source,
instrument, timeframe, account context, and recovery policy.

Its direction includes:

- start, graceful stop, and emergency flatten-and-stop,
- per-deployment and global emergency controls,
- runtime status, heartbeat, feed health, signals, positions, orders, fills,
  PnL, logs, and an append-only operator audit trail,
- multiple concurrent strategy sessions, initially around five on a shared
  instrument and timeframe,
- independent paper accounts per strategy,
- shared market-data consumption where compatible,
- recovery and reconciliation before automatic return to trading.

The first live capability uses live market data with simulated execution. It
does not place real broker orders.

Recovery may reconstruct signals from missing bars, but it never invents
orders or fills in the past. A recovered signal may only become eligible for
an entry on new runtime data and while its strategy-owned entry timeout is
still active.

Research training, heavy backtests, and large imports do not run on the basic
live VPS. Live strategy inference consumes only immutable artifacts already
prepared through the relevant framework lifecycle.

### 4.3 Public Portfolio

The public portfolio presents only explicitly published research and dry-run
facts.

Its direction includes:

- curated, immutable publication versions for selected research runs,
- stable public pages for explicitly published deployments,
- immutable pages for individual completed dry-run sessions,
- live, read-only dry-run status without artificial delay,
- permanent visibility of an ended session as an ended historical record,
- unmistakable `LIVE MARKET DATA / SIMULATED EXECUTION / NO REAL ORDERS`
  labelling.

Public projections exclude private configuration, strategy source, model
artifacts, infrastructure identifiers, internal paths, operational logs,
secrets, and every command surface by default. Public publication is the only
visibility mode committed for the first version; unlisted links and guest
accounts are deferred until a demonstrated need exists.

### 4.4 Strategy Builder

The Strategy Builder is a later product surface with two intended modes:

1. configure an existing strategy through its exposed parameters;
2. compose a declarative `Market Model x Signal Model x Exit Model x Risk
   Model` through structured forms and logical expression trees.

Users define domain composition and `AND` / `OR` / `NOT` relationships. The
framework resolves computational dependencies between analytical components.
The user does not manually wire an execution DAG.

The builder is not required to represent every valid Python strategy.
Operator-authored code remains a supported escape hatch for advanced cases.

## 5. Capability Direction

Delivery priority is:

```text
1. Data Manager + Signal Research Workbench
2. Strategy Research
3. Robustness Research
4. Predictive Research
5. Live/Paper Control
6. Structured Strategy Builder
```

Public publication may grow incrementally alongside research result views and
live/paper monitoring. This delivery order does not turn Signal Research,
Strategy Research, and Strategy Execution into one mandatory pipeline. Their
architectural independence remains binding.

Each capability should be delivered as a small vertical increment. Detailed
requirements belong only to the current or next increment, not to this vision.

## 6. Product Non-goals

The Research Application is not:

- a new research, simulation, or execution engine;
- a place for scorer interpretation or trading-decision logic;
- an automated strategy selector or promotion authority;
- a hyperparameter optimization, Bayesian search, or unbounded candidate
  generation product;
- a market-data editor or repair tool;
- a destructive dataset or run management interface;
- a visual node-and-wire DAG editor;
- a guarantee that every strategy can be authored without Python;
- a manual order-entry terminal;
- a real-broker execution surface in its initial live direction;
- a multi-user SaaS, collaboration suite, or account-management product;
- a reason to couple research workflows to execution state;
- a reason to replace existing CLI, scripts, artifacts, or reports at once.

## 7. Long-Term Outcome

The product succeeds when a researcher can operate the common framework loop
without memorizing command syntax, while an expert can still inspect every
material input and use the same artifacts through Python or the CLI.

It should become possible to move from data inspection to defensible research
comparison, then separately deploy a selected strategy into observable paper
operation, without the UI becoming the owner of research truth or trading
decisions.

## 8. Relationship to Existing Direction

This vision extends, and must remain subordinate to:

- `PRODUCT_DIRECTION.md` and its three independent capabilities;
- `RUN_IDENTITY_AND_CONFIGURATION.md` for explicit, versioned configuration
  and material run identity;
- the as-built Signal Research, Strategy Research, and Strategy Execution
  workflow references;
- ADR-0022's deployable-application boundary;
- Phase 16's read-only Quant Lab direction.

An implementation-facing architecture triage and, where required, ADR work
must resolve how a new control application invokes workflows without weakening
the existing read-only dashboard boundary.

## 9. Open Direction Questions

- The live VPS resource envelope and the isolation model for approximately
  five concurrent strategy sessions.
- The generic external notification transport for stale feeds, failed
  recovery, failed flatten, and runtime failure.
- The future serialized strategy-definition contract needed by the structured
  Strategy Builder.
- The future broker, reconciliation, and authorization requirements for real
  execution.
- The exact packaging and startup experience for local forks.
- Whether a demonstrated sharing need later justifies unlisted or
  authenticated guest publications.
