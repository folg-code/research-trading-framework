# Sprint 041 — Predictive Research Report v1 (Phase 10A)

## Metadata

```text
Sprint: 041
Phase: Phase 10A — Predictive Research Foundation
Status: Approved
Planned Start: 2026-08-26
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_040 (PredictiveRunEnvelope, metrics schema)
Sprint Branch: sprint/predictive-research-report
Task branch convention: feat/ | fix/ | docs/ | test/
Wave 0 decisions: docs/planning/sprints/S041_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§13A Phase 10)
  - docs/adr/ADR-0013-signal-research-analytics-boundary.md (read-only analytics boundary)
  - docs/adr/ADR-0020 (report v2 pattern)
  - docs/planning/sprints/S041_WAVE0_DECISIONS.md
  - src/trading_framework/research/reporting/signal_research/ (structural template)
```

---

## 0. Slice choice

Sprint 040 emits `metrics.json`. Reading a JSON file is a poor way to decide whether a model found
structure or memorized a fold, and it is an actively bad way to notice that the split itself was
wrong.

This sprint delivers one offline HTML file that answers a specific question: **would a sceptical
reviewer believe this result?** The panels are chosen to make failure visible, not to make output
look impressive. Fold instability, calibration drift and purge losses get more space than headline
metrics.

The report is the deliverable that makes the whole track reviewable, which is why it lands before
tree models rather than after them.

**Out of scope:** interactive dashboard (→ S044), model comparison across studies, live updates.

---

## 1. Sprint Goal

```text
PredictiveRunEnvelope (S040)
    ↓
build_predictive_report_view_model  (read-only, no recomputation of predictions)
    ↓
Plotly figures + plain-language section intros
    ↓
render_predictive_research_report → standalone offline HTML
```

Success: a maintainer opens one HTML file and can state, without reading code, whether the model
beat its baselines, whether it did so consistently across folds, and how much data the leakage
guards removed.

---

## 2. In scope

- [ ] `research/reporting/predictive/` mirroring the Signal Research reporting layout.
- [ ] View model built read-only from the persisted envelope.
- [ ] Nine report panels (§4).
- [ ] Quality flags surfaced as warnings, not hidden in a metrics table.
- [ ] Plain-language section intros — the report explains what each panel means.
- [ ] Offline rendering: no CDN, no network at view time.
- [ ] CLI `scripts/predictive_research/render_predictive_report.py`.
- [ ] Extension points documented for S042 importance and S043 learning curves.

## 3. Out of scope

- Streamlit dashboard page (→ S044).
- Cross-run leaderboards (→ S042, within one study).
- Recomputing predictions or metrics — the report reads, never calculates model output.
- PDF export, theming, branding.
- Any panel that requires re-fitting a model.

---

## 4. Report panels

Ordered as they appear. The first two exist to challenge the result before the reader sees it.

### 1. Fold timeline

Horizontal bands per fold showing `TRAIN`, `PURGED`, `EMBARGOED`, `TEST` spans against calendar
time, with row counts per band.

This is the most important panel in the report. Most leakage errors are visible here as a purge band
that is suspiciously thin or a test window that overlaps its neighbour. It also shows the honest
cost of the guards — if purging removed 40% of training rows, the reader should know that
immediately.

### 2. Metric stability across folds

Per-fold primary metric as points with the pooled value as a reference line, plus min/max spread.

A pooled AUC of 0.58 built from folds scoring 0.71, 0.49, 0.52 and 0.60 is not a 0.58 model. This
panel makes that distinction impossible to miss.

### 3. Model versus reference baselines

Grouped bars: model, constant/majority, permutation — per fold and pooled. Where the model bar sits
inside the permutation spread, the panel says so in text.

### 4. Prediction quality (regression)

Predicted versus realized scatter with a fitted line, rank IC per fold, residual distribution.

### 5. Discrimination (classification)

ROC and precision-recall curves per fold, overlaid, with the pooled curve emphasized.

### 6. Calibration

Reliability curve with confidence bands plus Brier score decomposition. A model with good AUC and
broken calibration is usable for ranking and dangerous for thresholding — the report distinguishes
the two.

### 7. Prediction buckets

Mean `forward_return` per prediction decile, out-of-sample only, with sample counts per bucket and
the all-rows mean as a reference line. Monotonicity across buckets matters more than the top bucket.

### 8. Label and sample composition

Label distribution, class balance per fold, excluded-row accounting (incomplete horizon, null
features, purge, embargo).

### 9. Quality flags

Explicit warnings in the spirit of `research/analytics/quality_flags.py`:

```text
SMALL_TEST_SAMPLE            test fold below the declared minimum
SEVERE_CLASS_IMBALANCE       minority class below the declared share
UNSTABLE_ACROSS_FOLDS        per-fold metric spread above the declared tolerance
WITHIN_PERMUTATION_SPREAD    model does not clear its own permutation baseline
HIGH_EXCLUSION_SHARE         guards removed more than the declared share of rows
SINGLE_FOLD_DOMINANCE        one fold contributes most of the pooled result
POOR_CALIBRATION             reliability curve deviates beyond tolerance
```

Flags are warnings with thresholds declared in the study spec. They never block a run and never
convert into a verdict — Phase 10 deliberately has no PASS/FAIL equivalent to the Robustness
verdict, because a predictive model is not a strategy candidate.

---

## 5. Module layout

```text
research/reporting/predictive/contracts.py        report input contracts
research/reporting/predictive/view_models.py      envelope -> view model (read-only)
research/reporting/predictive/plotly_figures.py   figure builders, one per panel
research/reporting/predictive/formatting.py       number/label formatting
research/reporting/predictive/report_html.py      assembly + offline HTML
application/predictive_research/render_report.py  orchestration
scripts/predictive_research/render_predictive_report.py
```

### Binding rules

```text
The view model is a pure function of the persisted envelope
No panel triggers model fitting, prediction or dataset rebuilding
Figures are built from the view model only — never from raw parquet reads inside a figure builder
Panel registry is extensible: S042 adds importance, S043 adds learning curves, no rewrite
Missing optional data (no probabilities, no importance) degrades to a skipped panel with a note
```

---

## 6. Task breakdown

### Wave 1 — View model

| Task | Description | Status |
|------|-------------|--------|
| S041-T001 | Report contracts + view model builder from `PredictiveRunEnvelope` | DONE |
| S041-T002 | Quality flag evaluation with spec-declared thresholds | DONE |
| S041-T003 | Panel registry with optional-panel degradation | DONE |

### Wave 2 — Diagnostic panels

| Task | Description | Status |
|------|-------------|--------|
| S041-T004 | Fold timeline figure (train / purge / embargo / test bands) | DONE |
| S041-T005 | Metric stability across folds | DONE |
| S041-T006 | Model versus reference baselines | DONE |
| S041-T007 | Label and sample composition | DONE |

### Wave 3 — Task-specific panels

| Task | Description | Status |
|------|-------------|--------|
| S041-T008 | Regression: scatter, rank IC, residuals | TODO |
| S041-T009 | Classification: ROC + precision-recall | TODO |
| S041-T010 | Calibration curve + Brier decomposition | TODO |
| S041-T011 | Prediction decile buckets versus forward return | TODO |

### Wave 4 — Assembly and CLI

| Task | Description | Status |
|------|-------------|--------|
| S041-T012 | HTML assembly, offline asset embedding, section intros | TODO |
| S041-T013 | `render_predictive_research_report` orchestration | TODO |
| S041-T014 | CLI `render_predictive_report.py` | TODO |
| S041-T015 | Report smoke test: regression run and classification run | TODO |
| S041-T016 | Docs: RESEARCH_METHODOLOGIES, MODULE_MAP, CURRENT_STATUS | TODO |

**Progress:** 7 / 16 tasks

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `feat/predictive-report-view-model` | T001–T003 view model + flags |
| 2 | `feat/predictive-report-diagnostic-panels` | T004–T007 diagnostics |
| 3 | `feat/predictive-report-task-panels` | T008–T011 regression + classification |
| 4 | `feat/predictive-report-html` | T012–T014 assembly + CLI |
| 5 | `docs/predictive-report-closure` | T015–T016 tests + docs |

Each PR targets `sprint/predictive-research-report`.

---

## 8. Acceptance criteria

1. One command renders a standalone HTML file from a persisted run.
2. The file opens with no network access and no external assets.
3. Fold timeline shows all four roles with row counts.
4. Every metric appears per fold, never pooled-only.
5. Reference baselines appear alongside model results in the same panel.
6. Quality flags render as visible warnings with the threshold that triggered them.
7. A classification run without probabilities skips calibration with an explanatory note rather
   than failing.
8. Every panel carries a plain-language intro explaining what a bad result looks like.
9. Adding a panel requires registering it, not editing the assembly function.
10. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Report flatters weak results | Baselines and flags are mandatory panels, not optional sections |
| Panels recompute model output | Read-only view model contract + review checklist |
| Rigid assembly blocks S042/S043 panels | Panel registry designed for extension in T003 |
| Large HTML from many folds | Downsample scatter points; document size expectations |
| Report drifts from metrics schema | Smoke tests over both task types on fixtures |

---

## 10. Dependencies

**Required:** SPRINT_040 envelope with per-fold metrics and reference baselines.

**Not required:** trees, networks, dashboard, robustness experiments.

---

## 11. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 12. Post-sprint direction

Phase 10A is complete after this sprint: a study can be declared, trained, measured and reviewed.
Sprints 042 and 043 add estimator families and extend this report; neither changes the dataset or
run contracts.
