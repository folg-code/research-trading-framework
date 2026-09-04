# Trading Research Framework

# EVENT_SYSTEM_FUTURE.md

> **Target architecture / not-yet-built content.** This file was created by
> Sprint 055 T008 out of `docs/vision/ARCHITECTURE_TECHNICAL.md` §8 (all)
> and §10.10, and `docs/vision/WORKFLOWS_AI_ADR.md` §5.6 (both source files
> now dissolved). This is the largest single fully-unbuilt block found
> across Sprint 054 T001-T003 (`src/trading_framework/events/__init__.py`
> contains only a one-line docstring; no `Event`, `EventBus`, handler, or
> command implementation exists anywhere in `src/trading_framework/`).
> Content below is preserved verbatim from the original files; only
> classification headers, this merge header, and provenance notes are
> newly authored/added.

---

## Purpose

*(Classified FUTURE by Sprint 054 T002 in full — see
`docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
§8 for the full evidence, including the negative-result greps for every
named type below.)*

The Event System decouples components where asynchronous or reactive communication provides real value.

The architecture is hybrid:

```text
Direct Calls for deterministic Research
Events for Strategy Execution where justified
```

The framework does not use event-driven architecture everywhere.

---

## Events and Commands

Events represent facts that occurred.

Examples:

```text
MarketBarReceived
SignalGenerated
OrderSubmitted
OrderFilled
PositionUpdated
```

Commands represent requested actions.

Examples:

```text
SubmitOrder
CancelOrder
ClosePosition
```

Events and commands must not be confused.

---

## Research Usage

Research uses direct calls and explicit orchestration by default.

Events may support:

- progress reporting,
- audit logging,
- monitoring,
- result persistence.

Events must not define the computational semantics of Research.

---

## Strategy Execution Usage

Strategy Execution may use an EventBus for:

- provider input,
- analytical updates,
- SignalOccurrence publication,
- order lifecycle,
- broker events,
- monitoring,
- retry boundaries.

Critical state transitions must remain explicit.

> **Merged from: `WORKFLOWS_AI_ADR.md` §5.6 "Event-Driven Runtime", now
> dissolved.** That section (classified MIXED by Sprint 054 T003b —
> `execution/models/events.py`'s `ExecutionEventType` overlaps conceptually
> but is not name-identical to the event list below — only one combined
> `SIMULATED_ORDER_FILLED`, no `MarketBarReceived`/`AnalysisStateUpdated`
> equivalents; `Grep` for `EventBus`/`class Event\b` returned zero matches —
> there is no generic pub/sub `EventBus`, the top-level `events/` package is
> an empty stub) restated the same usage list with a fuller example event
> list:
>
> ```text
> MarketBarReceived
> AnalysisStateUpdated
> SignalGenerated
> OrderSubmitted
> OrderAccepted
> OrderFilled
> PositionUpdated
> ```
>
> and adds one rule not present above: "An EventBus must not hide: order
> state transitions, risk checks, failure policy, reconciliation,
> persistence requirements."

---

## Event Model

Events are immutable.

Conceptual example:

```python
@dataclass(frozen=True, slots=True)
class Event:
    event_id: UUID
    occurred_at: datetime
    correlation_id: UUID | None
```

Provider SDK objects must not be published directly.

---

## Event Bus

Conceptual contract:

```python
class EventBus(Protocol):
    def publish(self, event: Event) -> None:
        ...

    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> Subscription:
        ...
```

Possible implementations:

```text
InMemoryEventBus
AsyncEventBus
RedisEventBus
```

Version 1 begins with an in-memory implementation unless a demonstrated requirement justifies more.

---

## Event System Rules

1. Research uses direct calls by default.
2. Strategy Execution may use events where justified.
3. Events represent facts.
4. Commands represent requested actions.
5. Events are immutable.
6. Provider and broker objects do not cross boundaries.
7. Handlers are focused and testable.
8. Execution event handling is idempotent where required.
9. Critical events are not silently dropped.
10. Distributed messaging is deferred.

---

## Events Module Directory Layout

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §10.10 "Events Module", now
dissolved. Classified FUTURE by Sprint 054 T002 — `events/` contains only
`__init__.py` with a one-line docstring; none of the subdirectories below
exist. Same finding as the sections above.)*

```text
src/trading_framework/events/
├── models/
├── bus/
├── handlers/
├── commands/
└── protocols.py
```

Domain-specific events may live near their owning domain where clearer.

> **Sprint 055 T008 note:** this subsection is duplicated in
> `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md` §1 as part of the
> wholesale eviction of `ARCHITECTURE_TECHNICAL.md` §10 (Module Structure).
> Unlike the rest of §10, this specific subsection is genuinely
> forward-looking rather than superseded-and-abandoned — it describes the
> future layout of the same Event System documented above, not a layout
> that diverged from the real `src/trading_framework/` tree and was
> dropped. It is kept here (its natural topic home) rather than removed
> from the historical file, since duplication of ~10 lines is cheaper than
> re-litigating which file the eviction table's wholesale "§10" reference
> was meant to exclude.
