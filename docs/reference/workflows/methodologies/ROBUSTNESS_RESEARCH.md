# Robustness Research — methodology

Return to the [methodology chooser](../RESEARCH_METHODOLOGIES.md). This page explains the research question and evaluation method; the workflow reference owns contracts and persisted outputs.

## 7. Robustness Research

### Research Question

> Does the apparent strategy edge survive variation in parameters, time, regimes and execution assumptions?

### Workflow

```text
Strategy Definition
  → Experiment Variants
  → Repeated Strategy Runs
  → Persisted Child Results
  → Aggregate Analysis
  → Robustness Verdict
```

### Main Methods

- parameter sweeps,
- walk-forward analysis,
- stress testing,
- Monte Carlo analysis,
- regime analysis,
- sensitivity analysis,
- statistical diagnostics,
- execution-assumption testing.

### What It Should Detect

- narrow parameter peaks,
- unstable performance,
- regime dependency,
- sensitivity to costs,
- sensitivity to slippage,
- dependence on a small number of trades,
- degradation out of sample,
- concentration in one time period,
- unrealistic execution assumptions.

### Main Outputs

- experiment manifest,
- child-run references,
- parameter surfaces,
- walk-forward results,
- stress scenarios,
- Monte Carlo distributions,
- quality diagnostics,
- PASS / CONDITIONAL / FAIL verdict.

### Interpretation Rule

Robustness Research does not prove that an edge will persist.

Its purpose is to expose fragility, concentration and unsupported assumptions before a strategy is considered for execution.

---
