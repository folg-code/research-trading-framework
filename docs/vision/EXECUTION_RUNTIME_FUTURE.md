# Trading Research Framework

# EXECUTION_RUNTIME_FUTURE.md

> **Target architecture / not-yet-built content.** This file was created by
> Sprint 055 T008 out of `docs/vision/ARCHITECTURE_FOUNDATIONS.md` §6.5;
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §7.3, §9.9;
> `docs/vision/WORKFLOWS_AI_ADR.md` §4.9, §5.1, §5.4, §5.7, §5.8, §5.11,
> §5.12, §5.13, §5.15, §5.16; and
> `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §19 rule 23
> (all four source files now dissolved). Replay/Paper/Live runtime modes
> were previously stated four times across four files; this groups them
> with the broker abstraction, reconciliation and recovery content that
> only makes sense next to them (all confirmed zero-code as of Sprint 054).
> Content below is preserved verbatim from the original files; only
> classification headers, this merge header, and provenance notes are
> newly authored/added.

---

## Execution Modes

*(Longest/primary copy — merged from: `WORKFLOWS_AI_ADR.md` §5.4, now
dissolved. Classified MIXED by Sprint 054 T003b — `execution/modes.py`
defines `SUPPORTED_EXECUTION_MODES = frozenset({ExecutionMode.DRY_RUN})`:
only one mode is enabled today, named `DRY_RUN` rather than literally
"Paper Execution" (though `PaperBroker` is functionally close to Paper
Execution's "simulated broker interaction"). Replay Execution and Live
Execution have zero code counterpart.)*

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

> **Merged from: `ARCHITECTURE_FOUNDATIONS.md` §6.5 "Execution Domain —
> Runtime Modes", now dissolved.** That section (classified MIXED by
> Sprint 054 T001 — domain ownership is CURRENT and moved to
> [`docs/reference/system/DOMAIN_MODEL.md`](../reference/system/DOMAIN_MODEL.md#execution-domain);
> the Runtime Modes themselves remain only partially built) restated the
> same three modes near-identically, adding one framing detail not present
> above: "These modes are distinct from batch or vectorized backtesting
> owned by Research" — that distinction is covered in full under "Research
> Backtest vs Replay Execution" below.
>
> **Merged from: `ARCHITECTURE_TECHNICAL.md` §7.3 "Strategy Execution
> Modes", now dissolved.** That section (classified FUTURE by Sprint 054
> T002 — same `SUPPORTED_EXECUTION_MODES` evidence) restated the same three
> modes with no unique material beyond wording.
>
> **Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §19 rule 23,
> now dissolved.** "Replay, Paper and Live belong to Strategy Execution" —
> a one-line restatement of the same finding (FUTURE — `execution/modes.py`
> supports only `DRY_RUN` as of Sprint 054).

---

## Research Backtest vs Replay Execution

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.9, now dissolved. Classified MIXED
by Sprint 054 T003b — the Research Backtest side is fully built
(`research/simulation/engine.py`). `Grep` for
`ReplayClock`/`replay_clock`/`class Replay` returned zero matches anywhere
in `src/` — Replay Execution has no code counterpart at all, consistent
with `ExecutionMode` supporting only `DRY_RUN`.)*

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

## Strategy Execution Purpose

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.1, now dissolved. Classified MIXED
by Sprint 054 T003b — order lifecycle/fill processing/position state exist
for the `DRY_RUN` mode; "independent from research workflows" is confirmed.
No broker communication, reconciliation, or recovery code was found
anywhere in `execution/` — see Broker Abstraction/Reconciliation/Recovery
below.)*

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

## Order Lifecycle

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.7, now dissolved. Classified MIXED
by Sprint 054 T003b — `execution/models/orders.py`'s `OrderStatus` has only
`CREATED`, `SIMULATED_FILLED`, `SIMULATED_REJECTED` — a 3-state simplified
lifecycle for the `DRY_RUN` case, not the full 8-state normalized lifecycle
described below. "Broker-specific statuses normalized at the adapter
boundary" has no code counterpart since no broker adapter exists — see
Broker Abstraction below.)*

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

## Fill Processing

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.8, now dissolved. Classified MIXED
by Sprint 054 T003b — `SimulatedFill` has `fill_id`, `order_id`,
`quantity`, `price`, `liquidity` fields, consistent with "accepted fills
are facts." No partial-fill support (one fill per simulated order), no
commission/fee field on `SimulatedFill` itself, and no duplicate-fill
detection or correction-event mechanism were found.)*

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

## Broker Abstraction

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.11, now dissolved. Classified
FUTURE by Sprint 054 T003b — `Grep` for all nine named method signatures
below in `execution/protocols.py` returned zero matches. `PaperBroker` is a
single-symbol, single-process dataclass with no `connect`/`disconnect`/
adapter-boundary methods — there is no broker abstraction layer, pluggable
or otherwise, only one hardcoded simulated implementation.)*

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

## Reconciliation

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.12, now dissolved. Classified
FUTURE by Sprint 054 T003b — no reconciliation module, incident type, or
mismatch-detection logic was found anywhere in `src/trading_framework/`.
Consistent with Broker Abstraction above — reconciliation requires an
external broker to reconcile against, which does not exist.)*

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

## Recovery

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.13, now dissolved. Classified
FUTURE by Sprint 054 T003b — no recovery/restart module was located in
`execution/`, and recovery depends on the reconciliation mechanism
confirmed absent above.)*

Strategy Execution supports recovery after:

- process restart,
- network disconnect,
- broker reconnect,
- provider interruption.

Recovery uses persisted execution state and broker reconciliation.

In-memory state alone is insufficient.

---

## Observability

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.15, now dissolved. Classified MIXED
by Sprint 054 T003b — `execution/runtime/health_policy.py` implements
health-check logic, and `ExecutionEvent`'s `RUNTIME_FAILED`/
`HEARTBEAT_RECORDED` event types provide a basis for audit trails and
failure monitoring. No dedicated metrics/alerting module or
latency-monitoring instrumentation was found.)*

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

## Strategy Execution Configuration

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §9.9, now dissolved. Classified
AMBIGUOUS by Sprint 054 T002 — `execution/safety.py` and
`execution/repositories/` plausibly implement part of this, but since only
`DRY_RUN` execution mode is supported (see Execution Modes above), most of
the broker/account/reconnect-policy configuration below has no live
counterpart to configure yet.)*

Defines:

- execution mode,
- broker,
- account,
- instrument mapping,
- strategy selection,
- order policy,
- operational limits,
- reconnect policy,
- execution risk controls.

Secrets are loaded from environment variables or external secret storage.

---

## Strategy Execution Rules

*(Merged from: `WORKFLOWS_AI_ADR.md` §5.16, now dissolved. Classified MIXED
by Sprint 054 T003b, by inheritance — most of the 12 rules below restate
content above (CURRENT/MIXED), but rule 8 ("Broker state is reconciled")
and rule 10 ("Recovery is explicit") restate the confirmed-FUTURE
Reconciliation/Recovery content above.)*

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
