# ADR-0020 — Model Research Methodology MVP (Phase 5B)

## Status

PROPOSED (Sprint 017 Wave 0)

## Context

Phase 5 (Sprints 008–010) delivers Signal Research **computation, persistence and read-only
analytics** (ADR-0011–0013). A maintainer can run `run_signal_research`, persist occurrences and
forward outcomes, and call `analyze_signal_research_run` with grouping and conditional comparison.

What is missing for day-to-day model development:

```text
declarative research definition (YAML/JSON)
bounded experiment expansion (no silent grid explosion)
scope-appropriate baselines and marginal contribution
frequency / coverage / sample retention visibility
occurrence overlap policy (KEEP_ALL, FIRST_PER_BAR, COOLDOWN)
quality diagnostic flags (sample size, period concentration, incomplete outcomes)
professional offline HTML dashboard aligned to a fixed research protocol
production CLI and NQ half-year vertical slice
```

Sprint 017 Wave 0 (`S017_WAVE0_DECISIONS.md`) narrows the first increment. This ADR records the
architectural boundary between **existing Signal Research compute** and the new **methodology
layer**.

## Decision

### Workflow identity

Model Research Methodology is a **Phase 5B increment** on Signal Research — not a fifth independent
workflow alongside Strategy Research or Robustness Research.

```text
SignalResearchDefinitionSpec   — declarative study contract
run_signal_research            — unchanged kernel (+ optional occurrence policy at materialization)
analyze_signal_research_run    — extended metrics, baselines, quality flags (read-only)
build_signal_research_report   — offline HTML (split from analytics module)
```

Analytics must not re-run model evaluation, materialization or outcome calculation (ADR-0013).

### Research definition

Introduce `SignalResearchDefinitionSpec` recording:

```text
research_id, research_question, research_scope
dataset_ref, time_range
market_model_id, signal_model_id (scope-dependent)
forward_horizons, baseline, grouping_dimensions
occurrence_policy, quality_rules
resolved_parameters, component_lineage_hashes, definition_hash
```

YAML and JSON loaders map the spec to existing run/analyze requests. `definition_hash` is stored on
the run manifest and echoed in reports.

### Bounded research space

Every study declares explicit **candidate bounds**. Experiment manifests record:

```text
candidates_generated, candidates_evaluated, candidates_skipped
```

Automatic unbounded optimization, ML search and large-scale ranking are out of scope.

### Evaluation protocol

Outcome semantics remain ADR-0011 / Sprint 010:

```text
primary grain: ForwardOutcome row (entity_id × horizon_bars)
default aggregates: COMPLETE outcomes only
hit_rate: forward_return > 0
default timestamp basis: AVAILABLE_AT
```

Sprint 017 adds reporting, grouping presentation, baselines, frequency metrics and quality flags —
not alternate outcome math.

### Baselines by scope

| Scope | Comparison |
|-------|------------|
| `MARKET_MODEL_ONLY` | active vs inactive |
| `SIGNAL_MODEL_ONLY` | after signal vs unconditional market sample |
| `MARKET_AND_SIGNAL` | signal only vs signal under market model |

Combination studies headline **marginal contribution** and **sample_retention**.

### Occurrence policy

Declared policies:

```text
KEEP_ALL, FIRST_PER_BAR, COOLDOWN(duration)
```

Firing policy (`ON_EVENT`, `ON_TRUE_EDGE`) remains on the Signal Model definition. Occurrence
policy controls overlap deduplication. `COOLDOWN` that changes persisted facts applies at
materialization time; analytics records filtered counts when reporting-only filters are used.

### Model families

Manual ordered variant lists in the research definition. Purpose: compare whether added conditions
shrink sample without repeatable improvement — not auto-select a winner.

### Quality flags

Emit diagnostic flags (`LOW_SAMPLE_SIZE`, `HIGH_PERIOD_CONCENTRATION`, …) from configurable rules.
Flags warn; they do not auto-validate a model.

### Module layout (target)

```text
research/analytics/                      metrics, grouped, comparison, quality (no HTML)
research/reporting/signal_research/      view models, Plotly, HTML assembly
application/signal_research/             run, analyze, definition loader
scripts/signal_research/                 production CLI
scripts/demo/run_model_research_nq_demo.py
```

Migrate HTML from `research/analytics/reports.py` in Wave 3 without changing analytics contracts.

### Persistence

Core Parquet fact tables unchanged. Optional extensions:

```text
signal_research/<run_id>/manifest.json     + definition_hash, occurrence_policy, research_question
signal_research/<run_id>/analytics/        optional cached analytics envelope
signal_research/<run_id>/report/           rendered HTML convention
```

### NQ vertical slice

Canonical demo uses published continuous NQ 1m OHLCV (`user_data/storage_nq_half_year`) and
`canonical_examples.py` models across all three scopes.

## Consequences

### Positive

- Repeatable, bounded studies with portfolio-ready HTML output.
- Clear separation: compute once, analyze/report many times.
- Baseline and quality diagnostics make overfitting risk visible without claiming validation.
- Reuses Phase 5 investment; no fork of outcome engine.

### Negative / trade-offs

- Occurrence policy at materialization may require a follow-up PR to `run_signal_research` when
  `COOLDOWN` is not representable as analytics-only filtering.
- Report module split touches existing `render_signal_research_report` consumers — migration in Wave 3.
- Model families start manual; richer DSL deferred.

### Out of scope

```text
Strategy Research, Robustness Research, Execution
PnL, equity, Monte Carlo, automatic optimization
FastAPI, React, PostgreSQL, Jinja2 (deferred)
formal statistical tests, ML, cross-run leaderboards at scale
```

## References

- `docs/planning/sprints/SPRINT_017.md`
- `docs/planning/sprints/S017_WAVE0_DECISIONS.md`
- `docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md`
- `docs/adr/ADR-0012-combined-research-scopes-and-context-alignment.md`
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
