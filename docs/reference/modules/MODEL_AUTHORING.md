# Model Authoring DSL (thin guide)

> **Reference doc** — [as-implemented layer](../README.md).  
> Index: [docs/README.md](../../README.md).

Authors write Market and Signal models from `trading_framework.model_authoring`. That package
compiles to `model_expression` IR. Do not construct IR, canonicalize parameters, or call
`compute()` in an authored model.

ADR: [ADR-0006](../../adr/ADR-0006-declarative-market-and-signal-models.md).

---

## Copy-pasteable market + signal model

This is the happy path. It imports only `model_authoring` exports (no `model_expression`).

```python
from trading_framework.model_authoring import (
    LONG,
    market_model,
    price,
    signal_model,
    structure,
    trend,
    volatility,
)

trend_and_range = market_model(
    "trend_and_range",
    when=(
        (price.close > trend.ema(period=20))
        & (price.close > volatility.atr(period=14))
    ),
)

higher_low_long = signal_model(
    "higher_low_long",
    direction=LONG,
    when=structure.higher_low_event(pivot_range=15, timeframe="5m"),
)
```

`signal_model` infers `ON_EVENT` when the condition includes an event output, otherwise
`ON_TRUE_EDGE`. Pass `firing=` only to override.

Evaluate compiled definitions with `evaluate_models` in application code. That import is
orchestration, not part of the authored model.

---

## Namespaces

| Namespace | Typical use |
|-----------|-------------|
| `price` | Canonical OHLCV fields on the evaluation grid (`price.close`) |
| `trend` | Features such as `trend.ema(period=20)` |
| `volatility` | `volatility.atr(period=14)`, `volatility.true_range()`, `volatility.state(...)` |
| `structure` | HH/HL/LH/LL events and `latest_*_level` (not `*_observed_index`) |

Helpers such as `trend.price_above_ema` and `volatility.high` stay semantically neutral.
Strategic names (`buy_setup`, `allow_entry`) stay out of this package.
