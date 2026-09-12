# Event System — Future Direction

A general `events/` event system is a future capability; the current package is a stub. Existing execution event records are described in [Execution](../reference/modules/EXECUTION.md). The [pre-review snapshot](../archive/snapshots/EVENT_SYSTEM_FUTURE_pre_review.md) preserves the longer proposal and its evidence notes.

## Intended use

The architecture remains hybrid: deterministic Research uses direct calls and explicit orchestration by default. Strategy Execution may use events where asynchronous or reactive communication solves a demonstrated problem. Progress reporting, audit or monitoring may use events without making them the computational semantics of Research.

Events represent facts that occurred; commands request actions. Example event names include `MarketBarReceived`, `OrderSubmitted`, `OrderFilled` and `PositionUpdated`. Examples of commands include `SubmitOrder`, `CancelOrder` and `ClosePosition`. These names are conceptual, not current public types.

## Contract direction

A future event model should be immutable and carry an event ID, occurrence time and correlation identity where needed. Provider and broker SDK objects must not cross the adapter boundary. An event bus might begin in memory; distributed messaging needs separate evidence and an ADR.

Handlers should be focused and testable. Execution event handling must be idempotent where required. No event bus may hide order state transitions, risk checks, failure policy, reconciliation or persistence, and critical events must not be silently dropped.

## Possible package shape

`events/` may eventually contain models, bus protocols, handlers and commands; domain-specific events can remain near the owning domain when that is clearer. The exact package layout and transport are design choices for the implementation task, not a commitment made by this page.
