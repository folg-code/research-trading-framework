# Strategy — module guide

`src/trading_framework/strategy/` owns the stateless composition contract used by Strategy Research and Strategy Execution. It does not own either workflow's state, simulation engine, broker connection, or persisted results.

## Composition

The strategy combines Market Model, Signal Model, Exit Model and Risk Model decisions. The package contains `strategy_model.py`, `exit_model.py`, `risk_model.py`, `signal_occurrence.py`, `reference_price.py` and `score_condition.py`. Worked canonical examples live alongside these contracts; user strategies live under `user_data/` and are loaded through the approved authoring boundary.

```text
Market + Market Analysis → Market/Signal Models → Strategy contract
                                              ├→ Strategy Research simulation
                                              └→ Strategy Execution runtime
```

Research and execution consume the same strategy definitions through their own application paths; the Strategy package does not import either implementation. The [dependency rules](../system/DEPENDENCY_RULES.md) and [domain model](../system/DOMAIN_MODEL.md) define this boundary.

## Read next

- [Strategy Authoring](STRATEGY_AUTHORING.md): custom `strategy_file` contract and trust model.
- [Strategy Examples](STRATEGY_EXAMPLES.md): concrete compositions.
- [Strategy Research](../workflows/STRATEGY_RESEARCH.md): simulation and persisted evidence.
- [Strategy Execution](../workflows/STRATEGY_EXECUTION.md): runtime consumption and state.
- [ADR-0028](../../adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md): bracket exits and equity-relative sizing decision.
