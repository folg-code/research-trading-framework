# Sprint 017 — Wave 0 Architecture Decisions (Model Research Methodology MVP)

## Metadata

```text
Task: S017-T001
Sprint: 017 — Model Research Methodology MVP (Phase 5B)
Status: ACCEPTED (planning)
Planned Start: 2026-07-15
Branch: sprint/model-research-methodology-mvp
Direction: docs/planning/sprints/SPRINT_017.md
Depends on: SPRINT_008–010 merged to main (ADR-0011–0013); SPRINT_015 merged (continuous NQ OHLCV)
Scope: methodology layer on Signal Research — definition spec, quality diagnostics, report v2, bounded experiments
```

---

## 0. Rationale

Phase 5 (Sprints 008–010) answers:

```text
Can we compute, persist and analyze signal outcomes on stored runs?
```

Sprint 017 answers a different question:

```text
Can we run a bounded, repeatable study of Market Models, Signal Models, and their combination
with a professional report that makes sample size, stability and overfitting risk visible?
```

This is **not** a new compute kernel. It is a **methodology and product layer** on top of existing
Signal Research persistence and analytics (ADR-0011–0013).

Strategy Research (Phase 6A) and Robustness Research (Phase 7) remain separate workflows.

---

## 1. Increment, not replacement

**Decision D-S017-01:** Model Research Methodology **extends** Phase 5 Signal Research. It does not
replace ADR-0011 persistence, ADR-0012 scopes, or ADR-0013 analytics boundary.

```text
Existing (keep):  run_signal_research, analyze_signal_research_run, SignalResearchDatasetRepository
New (add):        SignalResearchDefinitionSpec, quality flags, report v2, CLI, bounded experiment runner
```

Breaking changes to persisted Parquet schemas require a new ADR — not in Sprint 017 MVP.

---

## 2. Research question and bounded space

**Decision D-S017-02:** Every study declares:

```text
research_question     — human-readable intent
research_scope        — MARKET_MODEL_ONLY | SIGNAL_MODEL_ONLY | MARKET_AND_SIGNAL
dataset_ref           — published DatasetRef
time_range            — explicit UTC bounds
model identities      — market_model_id, signal_model_id (scope-dependent)
candidate_bounds      — max variants evaluated (explicit integer)
```

Research proceeds incrementally:

```text
single component → single model → small variant family → combination → stability review
```

Unbounded cartesian grids over components, timeframes, parameters and models are **out of scope**.
The definition and experiment manifest must record:

```text
candidates_generated
candidates_evaluated
candidates_skipped
```

---

## 3. Research definition artifact

**Decision D-S017-03:** Introduce `SignalResearchDefinitionSpec` as the declarative study contract.

Serialized forms: **YAML and JSON** (YAML for human authoring; JSON for machine interchange).

The spec records at minimum:

```text
research_id
research_question
research_scope
dataset_ref
time_range
market_model_id (optional by scope)
signal_model_id (optional by scope)
resolved_parameters (after canonical builder resolution)
forward_horizons
baseline
grouping_dimensions
occurrence_policy
quality_rules
component_lineage_hashes
definition_hash
```

`definition_hash` fingerprints the normalized spec (excluding run_id). It is stored on the run
manifest and echoed in analytics/report metadata.

Loader maps spec → existing `RunSignalResearchRequest` / `AnalyzeSignalResearchRequest` without
changing evaluation semantics unless occurrence policy requires a new materialization path (see §7).

---

## 4. Evaluation protocol (unchanged core)

**Decision D-S017-04:** Sprint 017 adopts the Sprint 010 protocol without redefining outcome math:

| Metric | Definition |
|--------|------------|
| Primary grain | one `ForwardOutcome` row = `entity_id × horizon_bars` |
| Default aggregates | `outcome_status == COMPLETE` only |
| Hit rate | `count(forward_return > 0) / sample_size_complete` |
| Timestamp basis | `AVAILABLE_AT` (MVP default, explicit in metadata) |
| MFE / MAE | per ADR-0011 direction-normalized semantics |

Sprint 017 **adds presentation and diagnostic layers** — not alternate outcome definitions.

---

## 5. Baseline semantics by scope

**Decision D-S017-05:** Baseline comparison is scope-specific:

### MARKET_MODEL_ONLY

```text
model_active    vs    model_inactive
```

Compare forward outcomes when the market model state is active vs inactive on the same observation
grain.

### SIGNAL_MODEL_ONLY

```text
after_signal    vs    unconditional_market_sample
```

`unconditional_market_sample` = bar- or time-based reference sample over the same dataset and
time_range (not conditioned on signal firing). MVP uses existing analytics frame with appropriate
entity_kind filter.

### MARKET_AND_SIGNAL

```text
signal_only     vs    signal_under_market_model
```

Primary headline for combination studies:

```text
marginal_contribution = metric(conditioned) - metric(signal_only)
```

Reported for: expectancy (mean/median return), hit rate, MFE, MAE, sample size, sample_retention.

```text
sample_retention = combined_sample_size / signal_only_sample_size
```

---

## 6. Frequency and coverage metrics

**Decision D-S017-06:** Add scope-specific frequency metrics to analytics summaries:

| Scope | Metrics |
|-------|---------|
| Signal Model | `signals_per_day`, `signals_per_session`, `median_time_between_signals` |
| Market Model | `coverage` (share of bars/time model is active) |
| Combined | `sample_retention` (see §5) |

These are computed in **read-only analytics** from persisted occurrence/observation tables — not
re-derived from raw market data during report rendering.

---

## 7. Occurrence policy

**Decision D-S017-07:** MVP occurrence policies:

```text
KEEP_ALL         — every detection is a separate observation
FIRST_PER_BAR    — at most one occurrence per bar per model
COOLDOWN         — ignore subsequent occurrences for duration after each accepted occurrence
```

Policy is declared in `SignalResearchDefinitionSpec` and recorded on run manifest.

**Binding split:**

| Policy | Where applied |
|--------|---------------|
| `KEEP_ALL`, `FIRST_PER_BAR` | Prefer materialization-time dedup when cheap; otherwise analytics-time filter on persisted facts |
| `COOLDOWN` | Materialization-time in `run_signal_research` when it changes persisted facts; analytics must not silently invent cooldown on stored runs with different policy |

Analytics records `filtered_observations_count` when post-hoc filters are applied for reporting
only. Diagnostics must show filtered vs persisted counts.

This does **not** replace Signal Model **firing policy** (`ON_EVENT`, `ON_TRUE_EDGE`) — firing
controls when a predicate becomes an occurrence; occurrence policy controls overlap deduplication.

---

## 8. Model families

**Decision D-S017-08:** MVP supports **manual model families** — ordered variant lists declared in
the research definition:

```yaml
model_family:
  id: sweep_family
  variants:
    - id: sweep
      signal_model: sweep_basic
    - id: sweep_reclaim
      signal_model: sweep_reclaim
```

Goals:

```text
compare sample_size, mean/median return, hit rate, MFE, MAE, stability across variants
detect whether added conditions shrink sample without repeatable improvement
```

No automatic "pick the best" ranking. Family comparison is tabular + grouped charts.

First concrete family in Wave 5 may use canonical builders or thin wrapper definitions — not a new
DSL.

---

## 9. Quality diagnostic flags

**Decision D-S017-09:** Analytics emits `SignalResearchQualityFlag` list — **warnings only**, never
auto-validation.

MVP flags:

```text
LOW_SAMPLE_SIZE
HIGH_PERIOD_CONCENTRATION
UNSTABLE_DIRECTION
WEAK_BASELINE_IMPROVEMENT
HIGH_SAMPLE_LOSS
OUTLIER_DEPENDENT
INCOMPLETE_OUTCOMES
```

Configurable rules (defaults in spec):

```yaml
quality_rules:
  minimum_sample_size: 100
  maximum_single_period_contribution: 0.40
  minimum_positive_period_share: 0.60
  maximum_incomplete_outcome_share: 0.05
```

Flags appear in report Diagnostics alongside incomplete/rejected observation counts.

---

## 10. Analytics vs reporting split

**Decision D-S017-10:** Preserve ADR-0013 boundary and sharpen module ownership:

```text
research/analytics/           — queries, metrics, grouped, comparison (no HTML)
research/reporting/signal_research/  — view models, Plotly figures, HTML assembly
application/signal_research/  — orchestration entrypoints
```

Public API (minimum):

```python
analyze_signal_research_run(run, filters=None, group_by=None) -> SignalResearchAnalytics
build_signal_research_report(analytics, output_path) -> ReportRef
analyze_and_build_report(run, output_path)  # optional convenience only
```

Existing `render_signal_research_report` in `research/analytics/reports.py` migrates to
`research/reporting/signal_research/` in Wave 3 — analytics module must not grow HTML templates.

MVP stack: **Polars → typed view models → Plotly → inline HTML** (Jinja2 deferred).

---

## 11. Dashboard content (MVP v1)

**Decision D-S017-11:** First report version includes exactly these sections:

```text
1. Run metadata (dataset, models, lineage, definition_hash)
2. KPI cards
3. Metrics by horizon table + chart
4. Forward return histogram (selected horizon)
5. MFE distribution
6. MAE distribution
7. Results by month
8. Results by session
9. Baseline comparison + marginal contribution
10. Diagnostics (incomplete, filtered, quality flags)
```

Every aggregate metric displayed with its **sample size** (complete count used).

Plotly for interactivity; single-file HTML opened locally — no server.

---

## 12. CLI and demo

**Decision D-S017-12:** Production scripts under `scripts/signal_research/`:

```text
run_signal_research.py       — from definition spec or flags
analyze_signal_research.py   — persist analytics JSON envelope (optional)
render_signal_research_report.py
```

Demo script:

```text
scripts/demo/run_model_research_nq_demo.py
```

Uses `user_data/storage_nq_half_year` and canonical models. Produces portfolio-ready HTML under
`demo/output/`.

---

## 13. Persistence extensions

**Decision D-S017-13:** MVP may add **optional** sidecar artifacts without changing core Parquet
fact tables:

```text
signal_research/<run_id>/
  manifest.json              — add definition_hash, occurrence_policy, research_question
  analytics/summary.json     — cached analytics envelope (optional, for fast re-report)
  report/report.html         — rendered output path convention
```

Re-reporting from `analytics/summary.json` must not invoke model evaluation.

---

## 14. Out of scope (Phase 5B MVP)

Binding exclusions:

```text
Exit Model, Risk Model, order simulation, PnL, equity curve
Monte Carlo, automatic optimization, ML model search
PBO, CSCV, Deflated Sharpe, formal hypothesis tests
FastAPI, React, PostgreSQL analytics store
Cross-run leaderboard across thousands of models
Jinja2 template engine (deferred)
Price-path or order-book research
```

---

## 15. Decision index

| ID | Summary |
|----|---------|
| D-S017-01 | Methodology increment on Phase 5, not replacement |
| D-S017-02 | Bounded research space + candidate accounting |
| D-S017-03 | `SignalResearchDefinitionSpec` + definition_hash |
| D-S017-04 | Sprint 010 protocol unchanged for outcome math |
| D-S017-05 | Scope-specific baselines + marginal contribution |
| D-S017-06 | Frequency / coverage / sample_retention metrics |
| D-S017-07 | Occurrence policy KEEP_ALL / FIRST_PER_BAR / COOLDOWN |
| D-S017-08 | Manual model families, no auto-ranking |
| D-S017-09 | Quality flags as diagnostics only |
| D-S017-10 | Analytics vs reporting module split |
| D-S017-11 | Ten-section HTML dashboard MVP |
| D-S017-12 | CLI + NQ half-year demo |
| D-S017-13 | Optional analytics sidecar, manifest extensions |

---

## 16. References

- `docs/planning/sprints/SPRINT_017.md`
- `docs/adr/ADR-0020-model-research-methodology-mvp.md`
- `docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md`
- `docs/adr/ADR-0012-combined-research-scopes-and-context-alignment.md`
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
- `docs/planning/sprints/S010_WAVE0_DECISIONS.md`
