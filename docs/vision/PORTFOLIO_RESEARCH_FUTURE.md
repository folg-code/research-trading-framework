# Portfolio Research — Future Direction

Portfolio Research is a planned methodology, not a current Research workflow.
The [implemented research methods](../reference/workflows/RESEARCH_METHODOLOGIES.md)
evaluate signals, models, individual strategies, robustness and predictive
tasks; they do not combine multiple strategies into one allocation engine.

## Research question

How should multiple strategies be combined, allocated and evaluated as a
portfolio under explicit temporal and execution assumptions?

## Potential scope

- correlation, diversification and risk contribution between strategies;
- capital allocation and allocation history;
- portfolio equity, drawdown, turnover and capacity;
- robustness of the combined portfolio;
- execution constraints, replacement and deactivation rules.

## Proposed workflow

```text
Persisted Strategy Results
  → Temporal Alignment
  → Portfolio Composition and Allocation Rules
  → Portfolio Simulation
  → Portfolio Analytics
```

Possible outputs include portfolio equity, strategy/risk contribution,
allocation history and portfolio-level robustness diagnostics. Exact contracts,
storage and acceptance criteria require a future architecture and delivery
decision; this page does not imply an implemented Portfolio Research engine.
