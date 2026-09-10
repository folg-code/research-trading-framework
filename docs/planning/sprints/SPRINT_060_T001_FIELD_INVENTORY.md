# Sprint 060 T001 — Phase 16C Artifact-to-Public-Field Inventory

Freezes exactly which persisted field feeds each of the four study
questions (`SPRINT_060.md` Scope) and the three accepted charts (D060-01),
for the real BTC Signal Quality study (`run_id=2ef6426b3cc06463`,
`dataset_id=437f6b7f9240208f`, Strategy Research runs `8d050f623a034a58`
baseline / `4dbf98822e6ae591` scored). Every field below was verified
directly against the real persisted file during this task — none is
inferred from documentation alone.

## STOP-and-report finding, resolved

The Strategy Research "rejected winners and losers" fact (D060-01 chart 3;
the sprint's own acceptance criterion: "two rejected occurrences (one
winner, one loser)") **is not persisted in any JSON or parquet artifact.**
It exists only as a `print()` in
`scripts/strategy_research/run_btc_signal_quality_comparison.py` (the
in-memory `_summarize` computation), never written to disk. The same is
true of `win_count`, `loss_count`, `mean_net_pnl`, `total_net_pnl` and the
Strategy Research score-gate threshold (0.5) — none are fields of
`summary_metrics.parquet` or any other persisted artifact; all exist only
as narrative numbers in `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` §6.

**Maintainer decision (2026-09-09):** these facts are sourced as reviewed
narrative content through the Sprint 059 `dashboard_app.content` pipeline,
copied from the already-accepted `BTC_SIGNAL_QUALITY_STUDY.md`, not
computed or derived by the dashboard and not added as a new research-layer
artifact this sprint. No `publication/` sanitizer role covers them — doing
so would require deriving a fact from raw trade rows, which contradicts
`sanitizers.py`'s copy-never-derive rule (ADR-0034 §1.4). T002 (methodology
content) authors this content document, explicitly linking to
`BTC_SIGNAL_QUALITY_STUDY.md` as its source rather than restating a number
with no traceable origin.

## Q1 — What was studied

| Fact | Artifact | Field | Status |
|---|---|---|---|
| Dataset identity | `metrics.json` (`user_data/workspace/research/predictive_research/runs/2ef6426b3cc06463/metrics.json`) | top-level `run_id`, `task_type` | CONFIRMED PERSISTED |
| Fold plan | same file | `folds` (keys `"0".."3"`, verified 4 folds) | CONFIRMED PERSISTED |
| Estimator family, seed | same file | `seed` (verified `42`) | CONFIRMED PERSISTED |
| Dataset id/fingerprint | `verdict.json` (same run dir) | `dataset_id`, `dataset_fingerprint` | CONFIRMED PERSISTED, but **not allowlisted** by Sprint 059's `sanitize_verdict_report` (deliberately withheld — see its docstring) |

## Q2 — Against what baseline/assumptions

| Fact | Artifact | Field | Status |
|---|---|---|---|
| Decision threshold | `metrics.json` | top-level `decision_threshold` (verified `0.5`) | CONFIRMED PERSISTED |
| Baseline comparators | `metrics.json` | `pooled.MAJORITY_CLASS`, `pooled.RANDOM_PERMUTATION` (verified present alongside `pooled.MODEL`) | CONFIRMED PERSISTED |
| Strategy Research score-gate threshold (0.5) | — | — | **NOT PERSISTED** as a field anywhere (CLI arg only); NARRATIVE-SOURCED from `BTC_SIGNAL_QUALITY_STUDY.md` §6 |

## Q3 — What result was persisted

| Fact | Artifact | Field | Status |
|---|---|---|---|
| Verdict | `verdict.json` | `verdict` (verified `INCONCLUSIVE`) | CONFIRMED PERSISTED + already allowlisted (`predictive_run_verdict` sanitizer) |
| Fired rule + observed/threshold | `verdict.json` | `rules[]` (`rule_id`, `fired`, `observed`, `threshold`, `source`, `evaluated`, `missing_input`) | CONFIRMED PERSISTED + already allowlisted (renamed `evaluations`) |
| Promoted artifact fingerprint | promoted `manifest.json` | `artifact_fingerprint` | CONFIRMED PERSISTED + already allowlisted (`promoted_artifact_identity` sanitizer) |
| Baseline/scored trade count, win rate, net PnL | `summary_metrics.parquet` (both run dirs, `analytics/`) | `run_id`, `trade_count`, `win_rate`, `net_pnl` — verified by reading both files directly: baseline `trade_count=6200, win_rate=0.5135, net_pnl=1198499.90`; scored `trade_count=6198, win_rate=0.5136, net_pnl=1206906.60` | CONFIRMED PERSISTED. **No sanitizer role exists yet** — new for T003. Note: the real column is `net_pnl`, not `total_net_pnl` (the narrative doc's label) — a T003 sanitizer must use the real column name. |
| Win count, loss count, mean net PnL | — | — | **NOT PERSISTED** (`summary_metrics.parquet`'s actual columns, verified: `schema_version, run_id, net_pnl, total_return, max_drawdown, current_drawdown, sharpe_ratio, sortino_ratio, profit_factor, expectancy, trade_count, win_rate, avg_win, avg_loss, total_costs` — no win/loss count or mean-PnL column). NARRATIVE-SOURCED from `BTC_SIGNAL_QUALITY_STUDY.md` §6. Recommend chart 3 does not need them: `trade_count` + `win_rate` + `net_pnl` per side already answers "did the score change the outcome". |
| Rejected occurrences (2 total: 1 winner, 1 loser) | — | — | **NOT PERSISTED anywhere** (ephemeral script output only). NARRATIVE-SOURCED from `BTC_SIGNAL_QUALITY_STUDY.md` §6 (see STOP-and-report resolution above). |

## Q4 — What limitations/warnings were persisted

| Fact | Artifact | Field | Status |
|---|---|---|---|
| Missing-input / not-evaluated rules | `verdict.json` | `rules[].missing_input`, `rules[].evaluated` | CONFIRMED PERSISTED + already allowlisted |
| Train/test gap per fold | `metrics.json` | `fold_primary.<fold_id>.{train_primary,test_primary}` | CONFIRMED PERSISTED (per `research/predictive/CLAUDE.md`: "Train vs TEST primary-metric gap is stored as added `fold_primary` keys on `metrics.json`"). No sanitizer role yet — bundled into the proposed `predictive_run_metrics` role below if a future chart needs it; not required by the three accepted D060-01 charts. |

## Chart 1 — Model vs. random-permutation ROC AUC across persisted folds

`metrics.json`: `pooled.MODEL.statistical.roc_auc` (verified `0.5239017101047371`), `pooled.RANDOM_PERMUTATION.statistical.roc_auc` (verified `0.506974571690442`), `folds.<fold_id>.MODEL.statistical.roc_auc`, `folds.<fold_id>.RANDOM_PERMUTATION.statistical.roc_auc` (4 folds, keys `"0".."3"`). CONFIRMED PERSISTED. No sanitizer role exists — proposed as **`predictive_run_metrics`** (see below).

## Chart 2 — Threshold sensitivity emphasizing coverage collapse

`threshold_sensitivity.json` (same run dir): top-level `schema_version`, `run_id`, `points[]` (verified 19 points). Each point: `threshold`, `finance.coverage`, `finance.hit_rate` (verified point 0: `threshold=0.05, coverage=1.0, hit_rate=0.551`). CONFIRMED PERSISTED. No sanitizer role exists — proposed as **`predictive_threshold_sensitivity`** (see below).

## Chart 3 — Baseline-vs-scored trade disposition

`trade_count`, `win_rate`, `net_pnl` from `summary_metrics.parquet` (both runs) — CONFIRMED PERSISTED, see Q3. The "rejected winners/losers" element is NARRATIVE-SOURCED, see the STOP-and-report resolution above. No sanitizer role exists for the persisted half — proposed as **`strategy_research_run_summary`** (see below).

## New sanitizer roles required for T003

None of these exist yet; Sprint 059 shipped exactly two roles
(`predictive_run_verdict`, `promoted_artifact_identity`). Adding these is
additive per ADR-0034 §5 (new role + new registry entry, no change to
existing roles):

| Role | Source artifact | Allowlisted fields |
|---|---|---|
| `predictive_run_metrics` | `metrics.json` | `pooled.{MODEL,RANDOM_PERMUTATION}.statistical.roc_auc`, `folds.<fold_id>.{MODEL,RANDOM_PERMUTATION}.statistical.roc_auc`, `decision_threshold`, `seed` |
| `predictive_threshold_sensitivity` | `threshold_sensitivity.json` | `points[].threshold`, `points[].finance.coverage`, `points[].finance.hit_rate` |
| `strategy_research_run_summary` | `summary_metrics.parquet` | `run_id`, `trade_count`, `win_rate`, `net_pnl` |

## Content-vs-projection boundary (binding for T002/T003)

- **`publication/` (raw-artifact projection)** carries only fields listed
  as CONFIRMED PERSISTED above, via the three new sanitizer roles.
- **`content/` (narrative, T002)** carries the two NARRATIVE-SOURCED facts
  (rejected-occurrence counts; score-gate threshold), explicitly linking to
  `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` as their source. Neither the
  dashboard nor a sanitizer computes, derives, or re-verifies these numbers
  — they are copied from already-reviewed prose, exactly as
  `dashboard_app.content`'s deny-by-default Markdown pipeline already
  requires "no hand-authored conclusion," here narrowed to "no
  hand-recomputed fact."
