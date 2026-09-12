# Sprint 044 — Wave 0 Decisions

Binding decisions for Predictive Research in the Dashboard and the IDEA-014
gate (Phase 10C closing increment). Date: 2026-08-27.

Inherited locks from S039–S043 / ADR-0022 / ADR-0023 are restated, not
reopened. Maintainer go-ahead 2026-08-27 (`masz zielone światło` after
S043 integration PR #342 landed on `main`).

**No ADR in this PR.** ADR-0024 remains reserved for Wave 3 (T011–T013).
Wave 0 records **proposed** IDEA-014 positions so Wave 3 does not reopen
the slice; Wave 3 writes the ADR and gate document.

Basis: `SPRINT_044.md`, `ROADMAP.md` §13A Phase 10C, ADR-0022 (apps
boundary), ADR-0023 §1 (IDEA-014 → S044 / ADR-0024),
`docs/planning/IDEA_INBOX.md` (IDEA-014 SCHEDULED),
`apps/dashboard/` catalog / caching / pages as implemented on `main`.

S043 neural models are on `main` (#342). This sprint starts from that tip.

---

## Inherited locks (do not reopen)

```text
ADR-0022: apps/* must not import research/execution engines or adapters
ADR-0023: Phase 10 is a research methodology; models do not trade
research/predictive/ stays ML-free
Durable facts are predictions.parquet + metrics.json; blobs are opaque (TD-022)
No model registry product (TD-021 / IDEA-003)
Phase 10 has no PASS/FAIL robustness verdict
SHAP stays deferred (SPRINT_042.md §9)
Synthetic fixtures only for CI — no NQ as S044 acceptance
```

---

## D-S044-01 — Problem statement

Studies are browsable only as loose HTML files, one per run. The dashboard
already solves comparison for Signal, Strategy and Robustness research. A
Predictive page is the sibling, not a new product.

The second deliverable is a **written gate**, not an implementation. IDEA-014
(trained models producing Market Analysis States) was deferred until research
infrastructure existed. That infrastructure now exists. This sprint answers
*when may a model be promoted?* with testable conditions. It does **not**
promote anything.

```text
Persisted predictive datasets + runs
    ↓
Filesystem catalog scan (apps/dashboard, read-only)
    ↓
Predictive Research page: study picker → leaderboard → run detail → HTML link
    +
ADR-0024 + gate document (conditions, not a component)
```

---

## D-S044-02 — Sprint branch and PR base

```text
Integration branch: sprint/predictive-dashboard-and-gate
                    (cut from main @ S043 #342 / 15fbb1f)
Working branches:   feat/ | fix/ | docs/ | test/   (cloud: cursor/<slug>-b5e7)
PR base:            sprint/predictive-dashboard-and-gate
                    (never main until sprint integration)
```

Working-branch PRs squash-merge into the sprint branch. When S044 is complete,
one integration PR goes `sprint/predictive-dashboard-and-gate` → `main`.

---

## D-S044-03 — Sprint slice

**This sprint ships exactly:** a read-only Predictive Research page in
`apps/dashboard`, and ADR-0024 plus a gate document for IDEA-014.

| Order | Slice | Why |
|-------|--------|-----|
| 0 | Wave 0 | Binding locks before catalog or ADR prose |
| 1 | Catalog | Paths, contracts, scan, cache keys |
| 2 | Page | Picker, leaderboard, detail, empty states |
| 3 | Gate | ADR-0024 + five IDEA-014 answers (docs; may parallel page) |
| 4 | Closure | Boundary test + IDEA-014 status + Phase 10 docs |

**Not this sprint:** ML Market Analysis component; training from the UI;
live inference; model registry product; installing `ml` / `ml-trees` /
`dl` in the dashboard; deserializing `models/fold_*.bin`; recomputing
research metrics in the UI; SHAP; NQ as acceptance.

Wave 0 does **not** add a numbered catalog task. T001–T018 stay as in
`SPRINT_044.md`. Progress remains **0 / 18** until Wave 1. Wave 0 is
planning DONE when this file is merged to the sprint branch.

---

## D-S044-04 — Catalog is a filesystem walk, not a DuckDB registry

`SPRINT_044.md` §1 says "DuckDB catalog scan". The existing dashboard
catalog is a **filesystem walk** of `manifest.json` (`list_runs` in
`apps/dashboard/src/dashboard_app/catalog/scanner.py`). DuckDB
(`DashboardQueryService`) is for **Parquet reads**, not a registry DB.

**Locked:**

```text
Listing     filesystem walk of predictive dataset and run manifests
Parquet     DuckDB via DashboardQueryService (predictions, market bars)
Registry    none — do not introduce a DuckDB catalog table
Import      do not import trading_framework.infrastructure.storage.paths
```

Predictive listing is a sibling of MARKET / SIGNAL / STRATEGY /
ROBUSTNESS. Missing directories are ignored. Corrupt or incomplete
manifests become `CatalogIssue` and are omitted from listings — same as
today.

`SPRINT_044.md` §2 checkbox "DuckDB catalog entries" is this scan plus
DuckDB reads of persisted Parquet, not a new registry.

---

## D-S044-05 — Path helpers (dashboard-local mirrors)

Add helpers in `apps/dashboard/src/dashboard_app/catalog/paths.py`.
Mirror the framework layout; do not import it.

```text
<storage_root>/research/predictive_research/datasets/{dataset_id}/
<storage_root>/research/predictive_research/runs/{run_id}/
```

Known sidecars under a run directory (read if present, skip if absent):

```text
manifest.json
metrics.json
predictions.parquet
report.html
importance.json
learning_curves.json
window_accounting.json
selection.json
leaderboard.json          optional compare sidecar — not required
models/fold_*.bin         opaque — never deserialize
```

Dataset envelope: `manifest.json` plus matrix Parquet. Listing the study
picker reads dataset `manifest.json` only.

---

## D-S044-06 — Workflow kind and two-level UI

```text
WorkflowKind.PREDICTIVE = "predictive"
```

Add the member in `apps/dashboard/src/dashboard_app/contracts.py`.
Research Catalog (page `1_`) includes Predictive in listings and counts
once the scanner emits the kind. The dedicated UX is page 6.

**Two-level page:**

1. **Study picker** — one row per predictive **dataset** envelope
   (`dataset_id`). Display `dataset_fingerprint`, source dataset ref,
   label kind, horizon, evaluation timeframe, run count. Grouping key
   for runs is `dataset_fingerprint` (learning-problem identity), not
   `dataset_id` alone, so rebuilds of the same fingerprint still group.
2. **Leaderboard** — runs whose `dataset_fingerprint` matches the
   selected study.
3. **Run detail** — one run.

Do **not** require `leaderboard.json`. Group from run `manifest.json` +
`metrics.json`. The S042 sidecar may exist from `compare_predictive_runs`;
the dashboard must not use its `rank` as the primary sort (D-S044-07).

A dataset with zero runs still appears in the picker; the leaderboard
empty-state says no runs for that fingerprint.

---

## D-S044-07 — Leaderboard sort is baseline delta

S042 `leaderboard.json` ranks by **raw** pooled primary (`MODEL`
`roc_auc` or `spearman_ic`). Dashboard **must not** use that rank as
the primary sort.

**Locked:**

```text
primary_metric     CLASSIFICATION → pooled MODEL roc_auc
                   REGRESSION     → pooled MODEL spearman_ic
                   (task_type from metrics.json)

baseline_delta     MODEL pooled primary
                   − RANDOM_PERMUTATION pooled primary

sort               descending baseline_delta
missing perm       no delta; sort last; surface a missing-baseline flag
```

This matches `SPRINT_044.md` §4: a run at 0.61 vs permutation 0.58 must
not outrank a run at 0.57 vs 0.50.

Compute delta from persisted `metrics.json` only. Do not recompute
research metrics. Do not call `build_predictive_leaderboard`.

Show family, primary metric, baseline delta, and quality flags on the
row. Secondary display of the raw pooled primary is allowed; it is not
the sort key.

---

## D-S044-08 — Quality flags are presentation-local

`evaluate_predictive_quality_flags` lives in
`research/reporting/predictive/quality.py`. The dashboard **must not**
import it (or any `trading_framework` module).

**Locked:** a dashboard-local evaluator reads persisted JSON and applies
the same default thresholds as `PredictiveReportQualityRules` so listing
flags match the HTML report when both have the same inputs:

```text
min_test_rows                 30
min_minority_class_share      0.10
max_fold_metric_spread        0.15
max_exclusion_share           0.40
max_single_fold_test_share    0.60
max_calibration_abs_error     0.15
max_train_test_gap            0.20
```

Codes to consider (domain names, copied as string literals):

```text
SMALL_TEST_SAMPLE
UNSTABLE_ACROSS_FOLDS
WITHIN_PERMUTATION_SPREAD
HIGH_EXCLUSION_SHARE
SINGLE_FOLD_DOMINANCE
LARGE_TRAIN_TEST_GAP
POOR_CALIBRATION
SEVERE_CLASS_IMBALANCE
```

Listing rows read **JSON only** (`metrics.json`, dataset
`exclusion_counts` / `fold_summary`). Do not open `predictions.parquet`
to compute listing flags.

Missing inputs → skip that flag; do not fail the page. In particular
`SEVERE_CLASS_IMBALANCE` is skipped unless minority-class counts are
already in JSON (do not scan labels on the listing).

Flags are warnings. They never become a PASS/FAIL verdict.

---

## D-S044-09 — Page, empty states, and panels

```text
apps/dashboard/pages/6_Predictive_Research.py
```

Place after Live Paper `5_`. Do not reorder pages 1–5.

The page is **read-only**. No training, no estimator import, no blob
deserialize.

| State | Behaviour |
|-------|-----------|
| Storage not configured | Same warning as other pages; stop |
| No datasets | Info empty-state; stop |
| Dataset without runs | Picker works; leaderboard empty-state |
| Missing `metrics.json` | Omit from leaderboard; `CatalogIssue` |
| Missing `report.html` | Hide the report link |
| Missing importance / calibration / learning curves / window accounting | Skip that panel |
| Per-fold metrics absent | Do not render pooled-only (AC3) |

Run detail **requires** per-fold metrics. Provenance shows dataset
fingerprint, estimator spec, seeds, library name **and** version.

Link to `report.html` when present (path under storage_root). Do not
inline the full HTML.

Importance, calibration, learning curves, and window accounting: show
if the sidecar exists, else skip. Same degrade-gracefully rule as
`SPRINT_044.md` AC4.

---

## D-S044-10 — Caching

Reuse `compute_storage_fingerprint`
(`apps/dashboard/src/dashboard_app/caching/fingerprint.py`). It already
hashes `research/` children, so `predictive_research/` participates
when that directory appears or its mtime moves.

Extend `cache_key_parts` with `dataset_id` (and keep `run_id`) so study
and run views invalidate independently. Do not introduce a second
fingerprint scheme.

---

## D-S044-11 — ADR-0022 extras and CI

Dashboard must not import research engines, estimators, adapters, or
`trading_framework` at all.

Do **not** add scikit-learn, XGBoost, LightGBM, CatBoost, or torch to
`apps/dashboard/pyproject.toml`. Do not add extras `ml` / `ml-trees` /
`dl` to the dashboard environment.

CI job `dashboard` already runs:

```bash
uv run --package trading-dashboard ruff check apps/dashboard
uv run --package trading-dashboard pytest apps/dashboard/tests -q
```

T014 (Wave 4) adds an AST / import boundary test **in dashboard tests**.
Framework `tests/test_architecture_boundaries.py` currently does not
cover `apps/dashboard`; do not wait on expanding it.

Framework extra-free `pytest` must stay green. Dashboard tests use
synthetic `manifest.json` / `metrics.json` / tiny parquet under a tmp
`storage_root`. No NQ. No torch.

---

## D-S044-12 — IDEA-014 proposed positions (Wave 3 confirms)

Leave `IDEA_INBOX.md` as **SCHEDULED** until T015. Wave 3 writes
ADR-0024 and the gate document. Wave 0 locks these **proposed**
answers so later PRs do not drift. They are not an approval to
implement a component.

### 1. Artifact identity

A promoted model is identified by a fingerprint covering dataset,
estimator spec, seed, and library versions. That fingerprint is
recorded in the lineage of every State it produces.

Durable serialization is the main promotion cost. Current
`models/fold_*.bin` blobs are opaque and non-portable (TD-022). This
sprint does not implement a new format.

### 2. Leakage

Inference-time feature availability is an `available_at` rule on the
component contract, not a convention. Training purge and embargo
already exist (S039). The open risk is serving a feature before it
was available.

### 3. Feature lineage

Declared `OutputRef` like other Market Analysis components (S039). A
model component declares feature dependencies the same way a
rule-based component declares inputs.

### 4. Offline / online parity

Preprocessing must be part of the artifact and executable on both the
batch research path and the dry-run runtime. Minimum bar: a parity
test on recorded data producing identical State values for identical
inputs.

This sprint **sketches** that test (T013). It does not implement the
component or the test harness.

### 5. Registry

Content-addressed artifact store only. **No** registry product
(IDEA-003 / TD-021). State this explicitly so a future sprint does not
assume registry infrastructure exists.

### What is not sufficient

Strong out-of-sample metrics alone. A promoted model becomes a Market
Analysis input; downstream strategies must still pass Phase 7
robustness. Phase 10 metrics are a precondition, never a substitute.

ADR-0024 states **conditions**. Implementation is a later sprint. Do
not imply promotion is approved.

---

## D-S044-13 — Docs this Wave 0 PR touches

```text
docs/planning/sprints/S044_WAVE0_DECISIONS.md     this file (new)
docs/planning/sprints/SPRINT_044.md               IN PROGRESS; Wave 0; PR 0
docs/planning/CURRENT_STATUS.md                   Active Sprint S044 Wave 0
docs/planning/ROADMAP.md                          S044 in progress; Phase 10 not closed
```

**Not this PR:** ADR-0024, IDEA_INBOX status change, MODULE_MAP,
DATA_WORKFLOWS, RESEARCH_METHODOLOGIES, ROADMAP §13A marked COMPLETE.

---

## D-S044-14 — Recommended PR sequence (cloud branch names)

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `cursor/predictive-dashboard-planning-b5e7` | Wave 0 locks (this file) |
| 1 | `cursor/dashboard-predictive-catalog-b5e7` | T001–T003 catalog + contracts |
| 2 | `cursor/dashboard-predictive-page-b5e7` | T004–T010 page views |
| 3 | `cursor/idea-014-promotion-gate-b5e7` | T011–T013 gate + ADR-0024 |
| 4 | `cursor/phase-10-closure-b5e7` | T014–T018 boundary test + closure docs |

PR 3 is documentation only and may run in parallel with PR 2. PR 2
depends on PR 1. Each PR targets `sprint/predictive-dashboard-and-gate`.
