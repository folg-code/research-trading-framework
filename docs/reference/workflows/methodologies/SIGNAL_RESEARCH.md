# Signal Research — methodology

Return to the [methodology chooser](../RESEARCH_METHODOLOGIES.md). This page explains the research question and evaluation method; the workflow reference owns contracts and persisted outputs.

## 4. Signal Research

### Research Question

> Does a market feature, state, signal or context describe repeatable forward market behaviour?

### Suitable For

- feature validation,
- market-state research,
- signal research,
- conditional behaviour analysis,
- forward returns,
- MFE and MAE,
- occurrence distributions,
- context-aware comparisons.

### Not Suitable For

- trade sequencing,
- exits,
- position sizing,
- transaction costs,
- drawdown,
- equity curves,
- simulated PnL.

These belong to Strategy Research.

### Workflow

```text
Published Dataset
  → Analytical Components
  → Market or Signal Model
  → Occurrences or Observations
  → Forward Outcomes
  → Persisted Research Facts
  → Read-Only Analytics
```

### Main Outputs

- signal occurrences,
- market-model observations,
- contextual facts,
- forward outcomes,
- grouped metrics,
- sample-size diagnostics,
- quality warnings.

### Typical Questions

- Does a signal predict positive forward returns?
- Does a market state change the distribution of outcomes?
- Does the result hold across sessions, periods or regimes?
- Is the observed effect supported by a sufficient sample?
- Is the effect concentrated in a small subset of the data?

---
