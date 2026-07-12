# ADR-0006 — Declarative Market and Signal Models

## Status

ACCEPTED

## Context

Sprint 006 introduces declarative Market Models and Signal Models composed from Market
Analysis component outputs and canonical OHLCV fields. Two audiences exist:

1. **Framework internals** — serializable expression IR, dependency extraction, validation,
   evaluation on aligned `AnalysisFrame` columns.
2. **Model authors** — readable definitions of market hypotheses and signal conditions without
   manually constructing AST nodes, parameter canonicalization, or `ComponentOutputReference`
   objects.

Without an explicit boundary, authoring convenience leaks into domain packages or strategic
semantics leak into Market Analysis helpers.

## Decision

### Internal IR (unchanged ownership)

Packages:

```text
model_expression/   references, expression AST, validation, evaluation adapter
market_model/       MarketModelDefinition, dense evaluator
signal_model/       SignalModelDefinition, firing policies, sparse emissions
```

Expression IR remains explicit, inspectable and serializable:

```text
CompareExpression
BinaryCompareExpression
AndExpression / OrExpression / NotExpression
ComponentOutputReference
MarketFieldReference
```

Application orchestration (`evaluate_models`) extracts dependencies, runs Market Analysis once,
evaluates all models on one frame.

### User-facing authoring DSL

New package `model_authoring/` compiles to the same IR:

```text
price.close
trend.ema(period=20)
volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH
structure.higher_low_event(pivot_range=15, timeframe="5m")
market_model(...) / signal_model(...)
```

Rules:

- DSL operator overloading produces deterministic, inspectable IR (`authored.expression`).
- Convenience helpers remain semantically neutral (`price_above_ema`, `volatility.high`).
- Strategic intent (`buy_setup`, `allow_entry`) stays out of Market Analysis and out of DSL
  helpers.
- `SignalFiringPolicy` is always explicit on resolved `SignalModelDefinition`; DSL may infer
  a default (`ON_EVENT` when event outputs present, otherwise `ON_TRUE_EDGE`) but never hides
  the resolved policy.
- String timeframes (`"5m"`) are converted to `Timeframe` at compile time; resolved dependencies
  retain full temporal identity.

### Domain boundaries

| Layer | Owns |
|-------|------|
| Market Analysis | component computation, schemas, registry, workspace |
| model_expression | operand references, boolean IR, validation, Polars evaluation |
| market_model / signal_model | model definitions and evaluators |
| model_authoring | typed references, conditions, builders |
| application/model_evaluation | orchestration (`evaluate_models`) |
| strategy (future) | position logic — not Sprint 006 |

Market Models and Signal Models are **not** Strategy.

### Null and firing semantics

Binding from S006 Wave 0 (D-S006-08 … D-S006-10):

- three-valued AND/OR/NOT,
- null operands do not fire,
- `ON_TRUE_EDGE` for state conditions,
- `ON_EVENT` for event outputs.

### Component catalog

Technical metadata (parameters, outputs, kind) comes from registered component schemas.
Documentation catalog adds summaries, tags and DSL examples only — no duplicate output lists.

## Consequences

### Positive

- authors write models in few lines without losing rigour,
- one IR serves Python DSL, future YAML/JSON config and tests,
- dependency deduplication and validation stay centralized.

### Negative

- additional compile step and package surface to maintain,
- binary operand comparisons required IR extension (`BinaryCompareExpression`).

## Related

- `docs/planning/sprints/S006_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_006.md`
- ADR-MA-001 (Market Analysis boundaries)
