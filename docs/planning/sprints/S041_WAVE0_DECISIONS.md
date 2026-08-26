# Sprint 041 — Wave 0 Decisions

Binding decisions for Predictive Research Report v1 (Phase 10A). Date: 2026-08-26.
Inherited locks from S039 / S040 / ADR-0023 are restated, not reopened.
Maintainer go-ahead 2026-08-26 after S040 merged to main (`pracuj dalej`).

Basis: `SPRINT_041.md`, `ROADMAP.md` §13A, ADR-0013 (read-only analytics),
ADR-0023 (ACCEPTED), `S040_WAVE0_DECISIONS.md`. No new ADR — ADR-0024 remains
reserved for IDEA-014.

---

## Inherited locks (do not reopen)

```text
research/predictive/ stays ML-free
Report never fits, predicts, or rebuilds a dataset
Durable facts are predictions.parquet + metrics.json; blobs are opaque
Synthetic fixtures only — no NQ as S041 acceptance
No signals / strategy / simulation / IDEA-014
Models do not trade
Phase 10 has no PASS/FAIL robustness verdict
```

---

## D-S041-01 — Problem statement

S040 emits `metrics.json`. A sceptical reviewer still cannot see fold
instability, purge cost, or calibration failure without reading code. This
sprint ships one offline HTML file that makes those failures visible.

---

## D-S041-02 — Sprint branch and PR base

```text
Integration branch: sprint/predictive-research-report
Working branches:   feat/ | fix/ | docs/ | test/
PR base:            sprint/predictive-research-report  (never main until sprint integration)
```

---

## D-S041-03 — Sprint slice

Nine panels, quality flags, panel registry, standalone HTML, thin CLI.
Not this sprint: Streamlit (S044), trees (S042), networks (S043),
cross-run leaderboards, PDF, theming.

---

## D-S041-04 — Read-only report inputs

The view model is a pure function of persisted envelopes. It does **not**
call estimators, `run_predictive_research`, or `build_predictive_dataset`.

Required inputs:

```text
PredictiveRunEnvelope       predictions.parquet + manifest
PredictiveMetricsReport     metrics.json (per-fold + pooled + baselines)
PredictiveDatasetEnvelope   labelled matrix + fold roles + exclusion counts
```

The dataset envelope is required for the fold-timeline and composition
panels (D-S039-09: purged/embargoed rows are retained). The report never
deserializes `models/fold_*.bin`.

Figures may derive **display series** from persisted predictions
(scatter, ROC/PR points). That is visualization, not model output.
They must not import `infrastructure.ml` or sklearn.

---

## D-S041-05 — Package layout

```text
research/reporting/predictive/contracts.py
research/reporting/predictive/quality.py
research/reporting/predictive/view_models.py
research/reporting/predictive/panels.py       registry + skip rules
research/reporting/predictive/plotly_figures.py   (later PRs)
research/reporting/predictive/formatting.py
research/reporting/predictive/report_html.py      (later PRs)
application/predictive_research/render_report.py  (later PRs)
scripts/predictive_research/render_predictive_report.py
```

`research/reporting/predictive/` imports polars, numpy, plotly (presentation),
and framework contracts. No sklearn. No `infrastructure.ml`.

---

## D-S041-06 — Quality-flag thresholds

Flags live on `PredictiveReportQualityRules` (frozen value object), not on
the study spec and not as a verdict. Defaults:

```text
min_test_rows                30
min_minority_class_share     0.10
max_fold_metric_spread       0.15     primary metric max−min across folds
max_exclusion_share          0.40
max_single_fold_test_share   0.60
max_calibration_abs_error    0.15     mean |predicted−observed| over occupied bins
```

Primary metric: `spearman_ic` (regression) or `roc_auc` (classification).

`WITHIN_PERMUTATION_SPREAD`: pooled model primary metric does not strictly
exceed the pooled `RANDOM_PERMUTATION` primary metric.

Flags never block rendering and never become PASS/FAIL.

---

## D-S041-07 — Panel registry

Panels are registered as data. Assembly iterates the registry; adding a
panel (S042 importance, S043 learning curves) does not edit the assembler.

Default panel ids, in report order:

```text
fold_timeline
metric_stability
model_vs_baselines
prediction_quality      (regression only)
discrimination          (classification only)
calibration             (classification; skip if no probabilities)
prediction_buckets
sample_composition
quality_flags
```

Reserved (not registered this sprint): `feature_importance`, `learning_curves`.

A skipped panel records an explanatory note. Missing probabilities skip
`calibration` rather than failing the report (AC 7).

---

## D-S041-08 — Offline HTML

The HTML file must open with **no network access**. Do not copy Signal
Research's CDN `<script src="https://cdn.plot.ly/...">`. Embed Plotly
inline (`include_plotlyjs="inline"` on the first figure).

---

## D-S041-09 — CI and fixtures

Synthetic in-memory envelopes only. Report tests are unmarked (no sklearn).
Smoke tests build view models from fake predictions + metrics, not a live
sklearn run.

---

## D-S041-10 — PR sequence

Locked from `SPRINT_041.md` §7.

| PR | Branch | Outcome |
|----|--------|---------|
| 1 | `feat/predictive-report-view-model` | Wave 0 + T001–T003 |
| 2 | `feat/predictive-report-diagnostic-panels` | T004–T007 |
| 3 | `feat/predictive-report-task-panels` | T008–T011 |
| 4 | `feat/predictive-report-html` | T012–T014 |
| 5 | `docs/predictive-report-closure` | T015–T016 |

---

## Wave 0 checklist status

Maintainer approved S041 Wave 0 after S040 merged to main (go-ahead 2026-08-26).

- [x] Sprint branch `sprint/predictive-research-report` (D-S041-02)
- [x] Slice: offline HTML report only (D-S041-03)
- [x] Read-only: run + metrics + dataset envelopes; no fit/predict (D-S041-04)
- [x] Package under `research/reporting/predictive/` (D-S041-05)
- [x] Quality-flag thresholds on `PredictiveReportQualityRules` (D-S041-06)
- [x] Panel registry + skip notes; reserved S042/S043 ids (D-S041-07)
- [x] Offline Plotly embed; no CDN (D-S041-08)
- [x] Synthetic extra-free tests (D-S041-09)
- [x] PR sequence from SPRINT_041 §7 (D-S041-10)

Approved by: Project Maintainer
Approved date: 2026-08-26
