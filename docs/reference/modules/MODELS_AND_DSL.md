# Models and DSL — implementation map

This page records the existing packages and entry points for models and dsl. Start with the [module map](../system/MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Packages and entry points

### Responsibilities

| Responsibility | Package |
|---|---|
| Expression tree and references | `model_expression/` |
| Expression validation | `model_expression/` |
| Expression evaluation | `model_expression/evaluation/` |
| User-facing typed DSL | `model_authoring/` (incl. `references/candle.py` -- `candle.upper_wick_ratio`/`lower_wick_ratio`/`body_ratio`, and `references/structure.py`'s `distance_to_session_high`/`distance_to_session_low` -- both Sprint 047 / ADR-0027; and, Sprint 051 / Phase 15A: `references/momentum.py` -- `momentum.rsi`/`macd_line`/`macd_signal`/`macd_histogram`/`stochastic_k`/`stochastic_d`, and `references/statistics.py` -- `statistics.return_autocorrelation`/`return_skew`/`return_excess_kurtosis` (the new `statistics.` namespace)) |
| Market Model contracts | `market_model/` |
| Signal Model contracts | `signal_model/` |
| Shared model evaluation workflow | `application/model_evaluation/` |

### Layer distinction

```text
model_authoring/
    user-facing DSL

model_expression/
    internal representation

market_model/ and signal_model/
    model definitions and evaluation contracts
```

`model_authoring/` is the layer users interact with.

`model_expression/` is the internal representation executed by the framework.

### Workflow mapping

```text
User DSL
  → model_authoring
  → model_expression
  → application/model_evaluation
  → Market Model and Signal Model results
```

### Tests

```text
tests/unit/model_authoring/
tests/unit/model_expression/
tests/unit/market_model/
tests/unit/signal_model/
tests/unit/application/model_evaluation/
```

### Deep references

- [System Overview](../system/SYSTEM_OVERVIEW.md)
- [Model authoring DSL](MODEL_AUTHORING.md)
- [ADR-0006 declarative models](../../adr/ADR-0006-declarative-market-and-signal-models.md)

---
