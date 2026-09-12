# Strategy Research — methodology

Return to the [methodology chooser](../RESEARCH_METHODOLOGIES.md). This page explains the research question and evaluation method; the workflow reference owns contracts and persisted outputs.

## 6. Strategy Research

### Research Question

> Does a complete strategy produce acceptable simulated performance under explicit execution assumptions?

### Strategy Composition

```text
Market Model
  × Signal Model
  × Entry
  × Risk
  × Exit
```

A strategy is treated as a composition of independent lower-level elements rather than one monolithic implementation.

### Workflow

```text
Published Dataset
  → Shared Analysis
  → Model Evaluation
  → Entry Decisions
  → Sequential Simulation
  → Trades and Equity
  → Persisted Run
  → Read-Only Analytics
```

### Main Outputs

- trade ledger,
- equity curve,
- returns,
- drawdown,
- hit rate,
- holding periods,
- exposure,
- execution diagnostics,
- performance summaries.

### Methodological Requirements

Strategy Research should make the following assumptions explicit:

- signal timing,
- entry timing,
- fill price,
- slippage,
- commissions and fees,
- exit behaviour,
- position sizing,
- incomplete positions,
- session boundaries,
- warm-up requirements.

### Typical Questions

- Does the full strategy generate acceptable risk-adjusted performance?
- How sensitive is the result to fill assumptions?
- Are results driven by a small number of trades?
- Does the strategy remain stable across periods and regimes?
- Is the strategy behaviour consistent with the original research hypothesis?

---
