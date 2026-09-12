# Model Research Methodology — methodology

Return to the [methodology chooser](../RESEARCH_METHODOLOGIES.md). This page explains the research question and evaluation method; the workflow reference owns contracts and persisted outputs.

## 5. Model Research Methodology

Model Research Methodology is a methodological layer built on Signal Research.

Its purpose is not to create another independent compute engine. It defines how a model study should be specified, bounded, diagnosed and reported.

### Research Question

> Is the model study well-defined, reproducible, bounded and diagnostically credible?

### Adds to Signal Research

- declarative study definitions,
- explicit research scope,
- baselines,
- grouping rules,
- occurrence policies,
- quality rules,
- bounded model-family comparison,
- persisted analytics,
- standardized reporting.

### Workflow

```text
Study Definition
  → Validation
  → Signal Research Run
  → Quality Diagnostics
  → Baseline Comparison
  → Persisted Analytics
  → Report
```

### Methodological Focus

- reproducibility,
- bounded search space,
- controlled comparison,
- explicit baselines,
- quality diagnostics,
- interpretability,
- avoidance of uncontrolled model mining.

### Recommended Boundaries

A model study should define in advance:

- the hypothesis,
- the studied model or model family,
- the dataset and time range,
- the evaluation horizons,
- the occurrence policy,
- the comparison baseline,
- the quality thresholds,
- the allowed variant count.

---
