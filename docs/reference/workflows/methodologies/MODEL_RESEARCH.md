# Model Research Methodology — methodology

Return to the [methodology chooser](../RESEARCH_METHODOLOGIES.md). This page explains the research question and evaluation method; the workflow reference owns contracts and persisted outputs.

## 5. Model Research Methodology

Model Research Methodology defines how Market Model and Signal Model studies
are framed. It guides studies run through the technical Signal Research
workflow; it is not a separate executable workflow.

Its purpose is not to create another independent compute engine. It defines
how a Market Model or Signal Model study should be specified, bounded,
diagnosed and reported. Statistical and machine-learning estimators belong to
Predictive Research instead.

### Research Question

> Is the Market Model or Signal Model study well-defined, reproducible,
> bounded and diagnostically credible?

### Adds to Signal Research

- declarative study definitions,
- explicit research scope,
- baselines,
- grouping rules,
- occurrence policies,
- quality rules,
- bounded Market Model or Signal Model family comparison,
- persisted analytics,
- standardized reporting.

### Method outline and workflow mapping

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

A Market Model or Signal Model study should define in advance:

- the hypothesis,
- the studied Market Model or Signal Model and its family,
- the dataset and time range,
- the evaluation horizons,
- the occurrence policy,
- the comparison baseline,
- the quality thresholds,
- the allowed variant count.

---
