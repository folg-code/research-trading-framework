# Sprint 017 — Model Research Methodology MVP

## Metadata

```text
Sprint: 017
Phase: Phase 5B — Model Research Methodology (Signal Research increment)
Status: COMPLETE (Wave 6 closure)
Planned Start: 2026-07-15
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_008–010 merged to main (ADR-0011–0013); SPRINT_015 merged (continuous NQ OHLCV)
Sprint Branch: sprint/model-research-methodology-mvp
Task branch convention: feat/ | fix/ | docs/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S017_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§9 Phase 5 — Signal Research MVP)
  - docs/vision/WORKFLOWS_AI_ADR_UPDATED.md (§3.12–3.14 Signal Research)
  - docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md
  - docs/adr/ADR-0012-combined-research-scopes-and-context-alignment.md
  - docs/adr/ADR-0013-signal-research-analytics-boundary.md
  - docs/adr/ADR-0020-model-research-methodology-mvp.md
Track choice: Model Research Methodology selected over Phase 4B orderflow — 2026-07-15
```

---

## 0. Slice choice

Phase 5 (Sprints 008–010) delivers **Signal Research computation and analytics** on persisted runs.
The missing capability is a **repeatable research methodology** — bounded experiments, explicit
definitions, quality diagnostics, and a professional HTML dashboard for Market Models, Signal Models,
and their combination.

Phase 5B MVP answers:

```text
Does the studied model describe repeatable and useful market behaviour?
```

It does **not** answer whether a complete strategy is ready to trade (Strategy Research / Phase 6A)
or whether edge survives validation (Robustness Research / Phase 7).

Supported research scopes (unchanged from ADR-0012):

```text
MARKET_MODEL_ONLY
SIGNAL_MODEL_ONLY
MARKET_AND_SIGNAL
```

**Final artifact:** documented NQ half-year experiment with interactive HTML reports per scope,
plus a repeatable definition → run → analyze → report workflow.

**Out of scope:** Exit Model, Risk Model, order simulation, PnL/equity, Monte Carlo, automatic
optimization, advanced statistics, ML, cross-run ranking at scale, FastAPI, React, PostgreSQL.

---

## 1. Sprint Goal

```text
SignalResearchDefinitionSpec (YAML/JSON)
        ↓
run_signal_research (bounded, lineage-recorded)
        ↓
analyze_signal_research_run (read-only Polars analytics)
        ↓
SignalResearchQualityFlags + baseline comparison
        ↓
Signal Research Report HTML (Plotly, offline)
        ↓
NQ half-year demo (3 scopes × canonical models)
```

Success: on published continuous NQ 1m OHLCV (`user_data/storage_nq_half_year`), a maintainer
defines a research study in YAML, runs bounded experiments, and receives HTML reports showing sample
size alongside every metric, baseline marginal contribution, stability by period/session, and
quality diagnostics — **without re-running model evaluation** when adding visualizations.

---

## 2. MVP scope checklist (completion criteria)

Phase 5B MVP is complete when the system can:

- [x] Declare a reproducible Signal Research study (`SignalResearchDefinitionSpec`).
- [x] Load definition from YAML/JSON and map to `run_signal_research` / `analyze_signal_research_run`.
- [x] Run bounded experiments (explicit candidate count, no unbounded grid search).
- [x] Analyze a persisted Signal Research run without recompute (ADR-0013).
- [x] Support all three research scopes with scope-appropriate baselines.
- [x] Report sample size, mean/median return, hit rate, MFE, MAE, quantiles per horizon.
- [x] Group results by horizon, calendar period, session, and time-of-day.
- [x] Compare signal-only vs signal-under-market-model (marginal contribution).
- [x] Apply occurrence policy semantics (`KEEP_ALL`, `FIRST_PER_BAR`, `COOLDOWN`) at definition level.
- [x] Compare small model families (manual variant list, not auto-optimization).
- [x] Emit quality diagnostic flags (`LOW_SAMPLE_SIZE`, `HIGH_PERIOD_CONCENTRATION`, …).
- [x] Generate offline HTML report with interactive Plotly charts.
- [x] Show incomplete and filtered observations in diagnostics.
- [x] Preserve dataset, model and component lineage in report metadata.
- [x] Run NQ half-year vertical slice demo producing portfolio-ready HTML.

---

## 3. Research protocol (binding summary)

Every model is evaluated under the same protocol (detail in `S017_WAVE0_DECISIONS.md`):

| Area | MVP metrics |
|------|-------------|
| Sample size | total, complete, incomplete, per period/session |
| Forward returns | mean, median, stdev, positive rate, p10–p90 per horizon |
| MFE / MAE | mean/median per horizon (price units; ATR-normalized optional) |
| Hit rate | `forward_return > 0` on COMPLETE outcomes |
| Frequency | signals/day, signals/session (signal); coverage (market) |
| Stability | grouped by month, quarter, session, time-of-day |
| Baseline | scope-specific comparison + marginal contribution |
| Quality | configurable warning flags, not auto-acceptance |

---

## 4. Six outcomes (waves)

| Wave | Outcome | Key deliverables |
|------|---------|------------------|
| **0** | Planning | Wave 0 decisions, ADR-0020, sprint doc |
| **1** | Research Definition | `SignalResearchDefinitionSpec`, YAML loader, lineage hashes |
| **2** | Quality Diagnostics | `SignalResearchQualityFlag`, configurable rules, diagnostics section |
| **3** | Report v2 | Dashboard §11 (10 sections), baseline table, MFE/MAE histograms |
| **4** | Production CLI | `scripts/signal_research/run.py`, `analyze.py`, `render_report.py` |
| **5** | Model Families | bounded variant comparison, candidate accounting |
| **6** | NQ Demo + closure | `run_model_research_nq_demo.py`, MODULE_MAP, DATA_WORKFLOWS |

Wave 2 and Wave 3 may proceed in parallel after Wave 1.

---

## 5. Domain boundary

```text
research/analytics/                  read-only metrics (existing + extensions)
research/reporting/signal_research/  offline HTML view models (new, split from analytics)
application/signal_research/         run + analyze orchestration (existing + definition mapping)
application/model_evaluation/        canonical model builders (unchanged)
research/datasets/signal_research.py persisted envelope (unchanged contract)
```

### Binding rules

```text
Analytics must not re-run evaluate_models or outcome calculation (ADR-0013)
Research definition records occurrence policy and candidate bounds explicitly
Quality flags are diagnostics — never auto-label a model "validated"
Model families compare variants — they do not rank thousands of models
Strategy Research and Robustness Research remain independent workflows
```

---

## 6. NQ half-year vertical slice

Canonical demo dataset:

```text
storage_root: user_data/storage_nq_half_year
dataset_id:   NQ.c.0|ohlcv|1m|derived|volume-rth-close@1
instrument:   NQ continuous (volume RTH close roll)
time_range:   published manifest range (~6 months)
```

Canonical models (from `canonical_examples.py`):

```text
MARKET_MODEL_ONLY:   high_volatility
SIGNAL_MODEL_ONLY: higher_low_long (ON_EVENT)
MARKET_AND_SIGNAL: high_volatility × higher_low_long
```

Horizons: `5m`, `15m`, `30m`, `60m` (bar counts on 1m base).

Demo output target: `demo/output/08_model_research_nq_half_year.html` (multi-scope index or
per-scope reports under `demo/output/model_research/`).

---

## 7. Research definition example

```yaml
research:
  id: nq_half_year_model_research
  scope: MARKET_AND_SIGNAL
  research_question: >
    Does higher-low structure show repeatable forward returns when filtered by high volatility?

  dataset_ref:
    dataset_id: NQ.c.0|ohlcv|1m|derived|volume-rth-close@1
    version: 1

  time_range:
    start: 2025-07-14
    end: 2026-01-13

  market_model: high_volatility
  signal_model: higher_low_long

  horizons:
    - 5m
    - 15m
    - 30m
    - 60m

  baseline:
    type: SIGNAL_ONLY

  occurrence_policy:
    type: COOLDOWN
    duration: 15m

  grouping:
    - month
    - session
    - time_of_day

  quality_rules:
    minimum_sample_size: 100
    maximum_single_period_contribution: 0.40
    minimum_positive_period_share: 0.60
    maximum_incomplete_outcome_share: 0.05
```

---

## 8. Dashboard sections (MVP v1)

First report version includes only:

```text
1. Run metadata
2. KPI cards (sample size beside every headline metric)
3. Metrics by horizon
4. Forward return histogram
5. MFE distribution
6. MAE distribution
7. Results by month
8. Results by session
9. Signal-only vs conditioned signal (baseline table + marginal contribution)
10. Diagnostics (incomplete, filtered, quality flags)
```

Deferred: multi-screen SPA, live refresh, cross-run comparison UI, interactive filter builder.

---

## 9. Task index (planned)

| Task | Wave | Outcome |
|------|------|---------|
| S017-T001 | 0 | Wave 0 decisions + ADR-0020 |
| S017-T002 | 1 | `SignalResearchDefinitionSpec` contract |
| S017-T003 | 1 | YAML/JSON loader + request mapping |
| S017-T004 | 2 | Quality flags + rules engine |
| S017-T005 | 3 | Report view model split + Plotly sections |
| S017-T006 | 3 | Baseline comparison + marginal contribution table |
| S017-T007 | 4 | `scripts/signal_research/` CLI trio |
| S017-T008 | 5 | Model family bounded comparison |
| S017-T009 | 6 | NQ half-year demo script |
| S017-T010 | 6 | MODULE_MAP, DATA_WORKFLOWS, `RESEARCH_METHODOLOGIES.md`, sprint closure |

---

## 11. Sprint closure (2026-07-15)

| Wave | PR | Branch | Outcome |
|------|-----|--------|---------|
| 0 | #142 | `docs/model-research-methodology-planning` | Wave 0 decisions, ADR-0020 |
| 1 | #143 | `feat/signal-research-definition-spec` | `SignalResearchDefinitionSpec`, loader, mapping |
| 2 | #144 | `feat/signal-research-quality-flags` | Quality flags + wiring |
| 3 | #145 | `feat/signal-research-report-v2` | Plotly dashboard v2, reporting split |
| 4 | #146 | `feat/signal-research-cli` | Production CLI trio + analytics sidecar |
| 5 | #147 | `feat/signal-research-model-family` | Bounded model-family comparison |
| 6 | #148 | `feat/model-research-nq-demo` | NQ half-year demo + reference doc updates |
| closure | (pending) | `docs/sprint-017-research-methodologies` | [RESEARCH_METHODOLOGIES.md](../../reference/RESEARCH_METHODOLOGIES.md) — all research workflows |

**Integration:** one final PR `sprint/model-research-methodology-mvp` → `main` after closure merge.

**Canonical methodology index:** `docs/reference/RESEARCH_METHODOLOGIES.md`

---

## 10. References

- `docs/planning/sprints/S017_WAVE0_DECISIONS.md`
- `docs/adr/ADR-0020-model-research-methodology-mvp.md`
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
- `docs/planning/sprints/SPRINT_010.md` (analytics baseline)
- `src/trading_framework/application/signal_research/`
- `docs/reference/RESEARCH_METHODOLOGIES.md` (all research workflows — Sprint 017 closure)
