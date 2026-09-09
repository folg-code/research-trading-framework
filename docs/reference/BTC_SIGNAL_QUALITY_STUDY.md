# BTC Signal Quality Study — Phase 16 Increment 16C Worked Example

Status: COMPLETE (Sprint 058 T005, 2026-09-09)

## 1. Purpose

Phase 16 increment 16C ("Signal Quality Scoring",
`docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.3) is the phase's
central vertical slice: a classical strategy proposes candidates, a model
scores their quality, and the simulator — unchanged — decides what that is
worth in PnL terms. This document is Sprint 058 T005's required worked
example: one real strategy, its scorer, both simulated variants (baseline
and score-filtered), with the comparison written down whether or not the
score helps. **It does not.** That is a complete, reportable outcome per
§13H.3's own framing ("A negative result... is a complete, reportable
outcome"), not a shortfall of this study.

## 2. Strategy

`scripts/strategy_research/_btc_rsi_relative_volatility.py` — the same
composition Sprint 051 (S051-T009) authored and committed as
`apps/cli/tests/fixtures/strategies/uses_rsi_relative_volatility.py`,
reproduced here (that file lives in a separate project, `apps/cli/`, not
importable from these scripts' own venv):

```text
Market Model : volatility.relative_volatility_ratio(period=20, baseline_period=100) > 1.0
Signal Model : momentum.rsi(period=14) < 30.0, fired ON_TRUE_EDGE, direction LONG
Exit Model   : BracketExitModel(stop_loss_bps=20, take_profit_bps=20, max_bars=20)
Risk Model   : EquityPercentRiskModel(account_equity=$100,000, risk_percent=1%, stop_distance=2)
Instrument   : BTCUSDT.P, 1m, 2024-01-01 -> 2026-06-30 (published, binance-usdm-klines-v1@1)
```

## 3. Signal Quality study (`SIGNAL_QUALITY`, `signal_occurrences`)

Built by `scripts/strategy_research/build_btc_signal_quality_study.py`.
The sample universe is every occurrence of the strategy's own Signal
Model above (a `signal_occurrences` `SampleSpec`, ADR-0031) — not every
bar. No `signal_model_file` loader exists yet (TD-031), so the script
supplies the already-constructed `SignalModelDefinition` in-process via
`BuildPredictiveDatasetRequest.signal_model`, the sanctioned seam every
test in this sprint already uses.

Feature list (10 features) is reused byte-for-byte from Sprint 052's
proven, already-computable list
(`apps/cli/examples/predictive/btc_momentum_regime_study_binary.yaml`) —
momentum (RSI, MACD histogram, stochastic K), volatility (relative
volatility ratio, ATR, range expansion), statistics (return
autocorrelation, return distribution skew), trend slope, and candle upper
wick ratio. Label: `BINARY`, horizon 20m (matching the strategy's own
bracket-exit timeout), threshold 0.0 on forward return — "did price move
favorably shortly after this RSI-oversold signal fired."

```text
dataset_id:        437f6b7f9240208f
fingerprint:       437f6b7f9240208f93af9024a8e790cd1ff520a7c8c74de1d16500b72b3da156
candidate rows (occurrences): 16,415
labelled rows:                16,397  (18 dropped: null_features)
folds: 4, EXPANDING, test_span=60d, embargo_span=1d, min_train_rows=50
  fold  TRAIN   TEST  EMBARGOED  PURGED
  0     11,809  1,110    16       1
  1     12,920  1,227    28       0
  2     14,147  1,056    44       0
  3     15,203  1,150    44       0
```

## 4. Estimator

`sklearn.logistic` (promotable, Q6 = Option B), seed 42, default
hyperparameters. Fit via `scripts/predictive_research/run_predictive_research.py`.

```text
run_id:      2ef6426b3cc06463
fingerprint: 2ef6426b3cc0646307425f768b608565724a58b485a70426cba5a195aebb7468

pooled metrics (TEST rows, all 4 folds):
  source              roc_auc   accuracy  balanced_accuracy
  MODEL                0.524     0.551     0.500
  MAJORITY_CLASS        0.500     0.551     0.500
  RANDOM_PERMUTATION    0.507     0.551     0.500

per-fold train/test primary-metric gap: 0.003 - 0.023 (no overfitting signal)
```

**The model barely clears the random-permutation baseline** (ROC AUC 0.524
vs. 0.507) and its `balanced_accuracy` is exactly 0.500 at the default 0.5
decision threshold — indistinguishable from always predicting the
majority class. This is the honest headline result, stated plainly before
anything downstream is built on it.

### Threshold sensitivity (`analyze_threshold_sensitivity`, Sprint 058 T002)

```text
threshold  coverage  hit_rate  mean_forward_return_selected
0.05-0.50    1.000     0.551      5.6e-05
0.55         0.822     0.555      7.3e-05
0.60         0.013     0.644      1.5e-04
0.65         0.000     1.000      3.3e-03   (a handful of rows)
```

Coverage collapses sharply above 0.55 — the fitted probabilities cluster
tightly around 0.5, as expected from a near-random classifier. A thin
high-confidence tail (threshold >= 0.60, ~1.3% of TEST rows) shows a
higher apparent hit rate, but the sample is far too small to trust, and
selecting that threshold *after* seeing this table would be exactly the
threshold-overfitting risk §13H.3 requires guarding against ("the cutoff
is chosen out of sample"). **This study's chosen threshold (0.5, §5) was
fixed before this table was computed**, precisely to avoid that trap. The
high-confidence tail is noted here as a candidate for future
investigation — a larger sample, a different feature set, or a different
base signal — not adopted as this study's result.

## 5. Promotion

`scripts/predictive_research/promote_predictive_run.py`, last walk-forward
fold (fold 3, ADR-0029 §3).

```text
artifact_fingerprint: 00e919cc8f950eb8da7217b9e00f8bfb463642c4f2e114d325372404b9b368a3
directory: research/predictive_research/promoted/00e919cc8f.../
```

## 6. Strategy Research: baseline vs. score-filtered

`scripts/strategy_research/run_btc_signal_quality_comparison.py` runs the
strategy from §2 twice on the same real data: once unscored, once with a
`ScoreConditionSpec(artifact_fingerprint=<§5>, threshold=0.5)` — the
natural logistic decision midpoint, chosen for the same reason as above
(never picked after looking at results). Per ADR-0033, the score is
evaluated in-process via the pure-NumPy promoted-artifact evaluator,
composed as a further filter after the existing market/signal gate; the
simulator (fills, slippage, sizing, the trade ledger) is untouched and
identical in both runs.

```text
                    baseline (unscored)      scored (threshold=0.5)
run_id              8d050f623a034a58         4dbf98822e6ae591
trade_count         6,200                    6,198
win_count            3,184                    3,183
loss_count            3,016                    3,015
win_rate              51.35%                   51.36%
total_net_pnl      1,198,499.90              1,206,906.60
mean_net_pnl            193.31                   194.73

rejected occurrences (in baseline, filtered out by the score): 2
  rejected winners: 1
  rejected losers:  1
```

## 7. What this study is, and is not

**The score does not meaningfully filter this strategy's trades.** At the
declared, non-cherry-picked threshold, exactly 2 of 6,200 occurrences (1
winner, 1 loser) are rejected — a difference indistinguishable from noise.
Both variants' win rate, trade count and net PnL are effectively
identical. This directly reflects §4's finding: a classifier whose
`balanced_accuracy` is 0.500 at its own decision threshold cannot be
expected to separate winners from losers when used as a threshold gate,
and it does not here.

**This is a complete, negative result, not an incomplete study.** Per
§13H.3: *"So is 'only the linear model is usable as a gate' — that is
Option B's expected shape, not a shortfall."* The equivalent finding here
— "the promotable model does not help this strategy" — is the same shape
of honest outcome.

**What this study is NOT:**
- Not evidence the `signal_occurrences` + `SIGNAL_QUALITY` pipeline is
  broken — §8 confirms the plumbing worked exactly as designed (16,415
  real occurrences resolved, a real model fit, promoted, and consumed by
  Strategy Research with no code path other than the one every other test
  in this sprint already exercises).
- Not evidence that no BTC signal can ever be usefully scored — only that
  *this* feature set, *this* label, and *this* signal did not produce one
  in this pass. A different label (e.g., a longer or shorter horizon), a
  feature set tailored to the RSI-oversold-in-a-volatility-regime setup
  specifically (rather than Sprint 052's general-purpose ten-feature
  list), or a different base signal are the natural next things to try —
  explicitly out of scope for this task, which asked for one worked
  example, not a search.
- Not a trading recommendation of any kind (ADR-0024's rule, restated by
  every Phase 16 increment so far: a backtest is never evidence of a live
  edge).

## 8. TD-021 / TD-022 repayment evidence (for T006)

- **TD-021 (no model registry):** §5's promoted artifact was referenced by
  a bare content-addressed `artifact_fingerprint` from `ScoreConditionSpec`
  (§6) — no index, no alias, no `latest` pointer. `resolve_score_condition`
  (Sprint 058 T003) resolved it successfully from a real Strategy Research
  config path, confirming ADR-0024 condition 5's negative constraint holds
  even with a machine-readable consumer.
- **TD-022 (opaque fitted blobs), promotion branch:** the score path in
  §6 depends only on `artifact.json` (a plain-number parameter file) via
  the pure-NumPy evaluator (ADR-0029) — `models/fold_3.bin` (the fitted
  joblib blob) was never read by any part of this comparison.
- **TD-029 (tree/neural promotion):** not applicable to this pass — only
  `sklearn.logistic` (promotable) was used as a gate, consistent with Q6 =
  Option B. No tree or neural family was declared as a strategy gate in
  this study.

## 9. Reproducibility

```bash
# 1. Build the SIGNAL_QUALITY dataset (signal_occurrences, real BTC data)
uv run python scripts/strategy_research/build_btc_signal_quality_study.py \
    --storage-root /absolute/path/to/user_data/workspace

# 2. Fit sklearn.logistic
uv run python scripts/predictive_research/run_predictive_research.py \
    --storage-root /absolute/path/to/user_data/workspace \
    --dataset-id 437f6b7f9240208f \
    --family sklearn.logistic --seed 42 --task-type CLASSIFICATION

# 3. Promote
uv run python scripts/predictive_research/promote_predictive_run.py \
    --storage-root /absolute/path/to/user_data/workspace \
    --run-id 2ef6426b3cc06463

# 4. Baseline vs. score-filtered comparison
uv run python scripts/strategy_research/run_btc_signal_quality_comparison.py \
    --storage-root /absolute/path/to/user_data/workspace \
    --artifact-fingerprint 00e919cc8f950eb8da7217b9e00f8bfb463642c4f2e114d325372404b9b368a3 \
    --threshold 0.5
```

`user_data/workspace` is gitignored (ADR-0002); the published `BTCUSDT.P`
dataset it must contain is the same one Sprint 052 used
(`docs/reference/BTC_PREDICTIVE_STUDY.md`), already present on the
maintainer's machine as of this study.

## Related

- `docs/adr/ADR-0033-predictive-score-delivery-boundary.md` — the score
  delivery mechanism this study exercises end to end.
- `docs/planning/sprints/SPRINT_058.md` — T001-T005's task-level record.
- `docs/reference/BTC_PREDICTIVE_STUDY.md` — Sprint 052's `every_bar` /
  `FORWARD_RETURN` study, whose feature list this study reuses.
- `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.3 — 16C's
  completion criteria, satisfied by this document plus T001-T004's
  implementation.
