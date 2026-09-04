# Strategy Execution — As-Built Reference

> Extracted from the former `docs/reference/system/WORKFLOWS_ARCHITECTURE.md`
> ("Strategy Execution" section) by Sprint 055 T007, per the maintainer-approved
> reversal of Sprint 054 T007's rejection ("group runbooks, don't merge-write")
> in `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1 — this is a
> section extraction with no new prose, not authoring. That source file's own
> content originated in `docs/vision/WORKFLOWS_AI_ADR.md`, moved by Sprint 054
> T006c. The section was classified **CURRENT** (or is the current-behavior
> portion of a section classified **MIXED**) against the codebase as of
> 2026-09-03. See
> `docs/planning/sprints/SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references.
>
> For how to run the one supported (`DRY_RUN`) execution mode end to end,
> see the `docs/reference/runbooks/` demos.

---

## Core Question

Strategy Execution answers:

```text
How should a selected Strategy Model interact with a runtime environment and broker safely and consistently?
```

It does not answer:

- whether a signal has predictive information,
- which Strategy Model ranks highest,
- which strategy family is most robust — **not yet implemented for Strategy
  Research, see PRB-020** (`docs/planning/PROBLEM_REGISTRY.md`).

---

## Inputs

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

## Runtime Flow

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

## Position Management

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

## Strategy Risk vs Operational Risk

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

## Persistence

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
