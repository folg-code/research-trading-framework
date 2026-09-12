# BTC Predictive Study (Sprint 052, Phase 15B)

**Verdict: on real `BTCUSDT.P` 1-minute futures data, run through the
unmodified Phase 10 pipeline, the binary-classification pass shows a real
out-of-sample effect that beats `RANDOM_PERMUTATION` on every one of six
walk-forward folds and pooled, while the regression pass does not — it beats
`RANDOM_PERMUTATION` pooled but loses on one fold with the linear estimator
and loses on two folds (with a clear overfitting signature) with the
tree-family estimator that its own trigger authorized.** This is a split
result, reported as such, not rounded up or down to a single headline
number.

This document is the write-up required by Sprint 052 (Phase 15B, Real-Data
BTC Predictive Study). It reports a statistical comparison produced by
consuming the existing, unmodified Phase 10 research pipeline
(`build_predictive_dataset`, `run_predictive_research`,
`analyze_predictive_run`) — no code under `research/predictive/`,
`application/predictive_research/`, `market_analysis/`, or
`infrastructure/ml/` was touched to produce it. It is not a trading
recommendation (§7).

---

## 1. Instrument, range and data quality

```text
Instrument:   BTCUSDT.P (Binance USD-M perpetual futures)
Source bars:  1m OHLCV
Range:        2024-01-01 -> 2026-06-30 (911 days)
Row count:    1,311,840 rows (911 days x 1,440 min/day, exact)
Gaps:         0 (import_manifest.json: gaps: [], rows_rejected: 0)
DatasetRef:   BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1
```

Source: `docs/archive/phases/phase-15-predictive-catalog/S051_BTC_DATA_INVENTORY.md` (Sprint 051's
measured import record). No other instrument was used or considered for
this study — `NQ.c.0` or any other non-BTC dataset was ruled out as a hard
stop by `S052_WAVE0_DECISIONS.md` D-S052-03a. This document may only ever
describe a study on BTC data; a study on any other instrument would be
separate, separately-approved work with its own document, never an
appendix to this one.

---

## 2. Fold plan

```text
mode            EXPANDING (each fold trains on all history before its test window)
evaluation_timeframe (V)   1m
fold_count (F)  6
test_span (T)   30d
embargo_span (E) 1d
min_train_rows (M) 2000
```

`V` was corrected from an originally-planned `15m` to `1m` (matching the
1m source) after `S052-T003`'s first attempt failed pipeline validation
(`evaluation_timeframe` is validated source-or-finer, not
source-or-coarser). The range, fold count, test span, embargo and minimum
train rows are unchanged by that correction. See
`docs/archive/phases/phase-15-predictive-catalog/S052_WAVE0_DECISIONS.md` D-S052-03's correction
section for the full incident and replanning record — it is not repeated
here.

Per-fold TEST windows (identical across both passes, since both share one
fold plan and dataset build):

```text
fold  test window                     TRAIN      TEST    EMBARGOED  PURGED
0     2025-12-26 -> 2026-01-25      1,043,820   43,200     1,440      60
1     2026-01-26 -> 2026-02-25      1,087,080   43,200     2,880       0
2     2026-02-26 -> 2026-03-28      1,130,280   43,200     4,320       0
3     2026-03-29 -> 2026-04-28      1,173,480   43,200     5,760       0
4     2026-04-29 -> 2026-05-29      1,216,680   43,200     7,200       0
5     2026-05-30 -> 2026-06-29      1,259,880   43,200     7,200       0
pooled                               6,911,220  259,200   28,800      60
```

`EMBARGOED` grows fold-over-fold rather than staying constant because
`EXPANDING` mode re-excludes every earlier fold's test+embargo window from
later folds' TRAIN sets; this is a real property of the unmodified fold
assignment logic, not an anomaly (see `SPRINT_052.md`'s S052-T003 outcome
note, point 3, for the full explanation). These are the pipeline-measured
counts, not Wave 0's simplified planning estimate, and the two differ by
small, explained margins.

---

## 3. Feature list

Ten components, frozen before either run and unchanged by any result
(`S052_WAVE0_DECISIONS.md` D-S052-05). Periods are evaluation-bar counts,
scaled x15 from their originally-planned `V=15m` values to hold each
component's wall-clock window constant now that `V=1m`.

```text
component                          family       key period(s), @V=1m
momentum.rsi                       momentum     period=210
momentum.macd                      momentum     fast=180, slow=390, signal=135
momentum.stochastic                momentum     period=210, smoothing=45
volatility.relative_volatility     volatility   period=300, baseline=1500
volatility.atr                     volatility   period=210
volatility.range_expansion         volatility   period=210
statistics.return_autocorrelation  statistics   period=900, lag=15
statistics.return_distribution     statistics   period=900
trend.slope                        trend        period=300
candle.wick                        candle       (no parameters)
```

Family tally: momentum:3, volatility:3, statistics:2, trend:1, candle:1 —
no single family exceeds 30% of the list. The first six are Sprint 051's
newly-catalogued components; the last four (`volatility.atr`,
`trend.slope`, `candle.wick`, `volatility.range_expansion`) are
pre-existing incumbents included so the study is not a single-family bet.

---

## 4. The two passes and what each measured

Two `PredictiveStudySpec` files share the same dataset, range, fold plan
and feature list; they differ only in `label.kind`, over the same 1h
label horizon:

- **REGRESSION pass**: continuous `forward_return` target
  (`PredictiveTask=FORWARD_RETURN`), estimator `sklearn.ridge` (`alpha=1.0`).
- **BINARY pass**: binary target on `forward_return` at a 0.0 threshold,
  estimator `sklearn.logistic` (`C=1.0`).

Both estimators share `seed=42`.

### 4.1 Per-fold and pooled comparison vs. `RANDOM_PERMUTATION`

```text
REGRESSION pass (ridge, run f7ac893d54ae6b69) — primary metric: spearman_ic
fold  test window                MODEL       RANDOM_PERMUTATION   vs. permutation
0     2025-12-26 -> 2026-01-25   0.021431    -0.002227             BEATS
1     2026-01-26 -> 2026-02-25   0.013676     0.001038             BEATS
2     2026-02-26 -> 2026-03-28   0.028457    -0.001969             BEATS
3     2026-03-29 -> 2026-04-28   0.050279    -0.002727             BEATS
4     2026-04-29 -> 2026-05-29   0.055561     0.001113             BEATS
5     2026-05-30 -> 2026-06-29  -0.009730    -0.001766             LOSES
pooled                           0.020566    -0.004792             BEATS

BINARY pass (logistic, run faa6983acd03f846) — primary metric: roc_auc
fold  test window                MODEL       RANDOM_PERMUTATION   vs. permutation
0     2025-12-26 -> 2026-01-25   0.545385     0.499030             BEATS
1     2026-01-26 -> 2026-02-25   0.533585     0.500667             BEATS
2     2026-02-26 -> 2026-03-28   0.539353     0.503985             BEATS
3     2026-03-29 -> 2026-04-28   0.559752     0.498767             BEATS
4     2026-04-29 -> 2026-05-29   0.557209     0.496858             BEATS
5     2026-05-30 -> 2026-06-29   0.541288     0.501019             BEATS
pooled                           0.544182     0.498606             BEATS
```

**`S044_GATE.md` §1.4 bar assessment (both the strict "every fold" bar and
the pooled bar are reported, as required):**

- **REGRESSION pass: clears the pooled bar, does NOT clear the strict
  per-fold bar.** It beats `RANDOM_PERMUTATION` pooled and on 5 of 6
  folds, but loses on fold 5 (both values negative — the model is mildly
  anti-correlated with outcomes in that fold and permutation is closer to
  zero).
- **BINARY pass: clears BOTH the pooled bar and the strict per-fold
  bar.** It beats `RANDOM_PERMUTATION` on all six folds individually
  (margins 0.035-0.061 roc_auc) and pooled. This is the cleaner, stronger
  result of the two passes.

### 4.2 Train/test gap, per fold

```text
REGRESSION pass — gap = |train_primary - test_primary| (spearman_ic)
fold  train_primary  test_primary   gap
0     0.016846        0.021431      0.004585
1     0.016671        0.013676      0.002995
2     0.015239        0.028457      0.013218
3     0.016796        0.050279      0.033483
4     0.021196        0.055561      0.034365
5     0.024186       -0.009730      0.033916

BINARY pass — gap = |train_primary - test_primary| (roc_auc)
fold  train_primary  test_primary   gap
0     0.533798        0.545385      0.011587
1     0.534199        0.533585      0.000614
2     0.533971        0.539353      0.005381
3     0.533873        0.559752      0.025878
4     0.534740        0.557209      0.022469
5     0.535447        0.541288      0.005841
```

Neither of these two passes shows the classic overfit signature (train
materially above test) — `test_primary` is usually *above* `train_primary`
in both passes, more consistent with a small, noisy train-fold estimate of
an already-weak signal than with memorization. This is still flagged, not
waved through: for the REGRESSION pass, the gap on folds 3-5 (0.033-0.034)
is *larger than the test-fold effect size itself* (0.050, 0.056, -0.010
respectively) — the fold-to-fold instability is large relative to what is
being measured. The BINARY pass's gaps are smaller both in absolute terms
and relative to its own effect size (~0.53-0.56 throughout).

### 4.3 Permutation importance for Sprint 051's six components

`n_repeats=5`, `seed=42`. Sign convention: positive mean = shuffling that
feature *hurts* the model (the feature helps); negative mean = shuffling
*helps* (the feature actively degrades predictions).

```text
REGRESSION pass — importance mean by fold (spearman_ic units)
component                          f0       f1       f2       f3       f4       f5
momentum.rsi                    -0.0030  -0.0058  -0.0016  -0.0174  -0.0136  -0.0111
momentum.macd                   -0.0000  +0.0005  +0.0033  +0.0079  +0.0107  +0.0066
momentum.stochastic             +0.0129  +0.0068  +0.0081  +0.0222  +0.0395  +0.0234
volatility.relative_volatility  -0.0016  -0.0026  -0.0014  +0.0028  +0.0111  -0.0104
statistics.return_autocorrelation +0.0308 -0.0036  +0.0325  +0.0184  +0.0598  +0.0007
statistics.return_distribution  -0.0038  -0.0007  -0.0152  +0.0020  +0.0092  +0.0015

BINARY pass — importance mean by fold (roc_auc units)
component                          f0       f1       f2       f3       f4       f5
momentum.rsi                    +0.0353  +0.0184  +0.0317  +0.0344  +0.0360  +0.0251
momentum.macd                   +0.0024  +0.0071  -0.0005  +0.0011  -0.0004  +0.0004
momentum.stochastic             +0.0158  +0.0090  +0.0199  +0.0241  +0.0273  +0.0270
volatility.relative_volatility  +0.0000  -0.0001  +0.0001  +0.0011  -0.0008  -0.0006
statistics.return_autocorrelation +0.0039 +0.0009  +0.0036  +0.0046  +0.0048  -0.0002
statistics.return_distribution  +0.0013  -0.0000  +0.0005  +0.0049  +0.0043  +0.0029
```

**Ignored vs. misled, per pass:**

- **REGRESSION**: `momentum.macd`, `volatility.relative_volatility`, and
  `statistics.return_distribution` sit near zero on every fold — **ignored**.
  `momentum.stochastic` and `statistics.return_autocorrelation` are
  consistently the largest positive contributors and drive most of the 5
  winning folds — genuinely used, correctly. `momentum.rsi` is
  **consistently negative on all six folds** (-0.003 to -0.017): the model
  uses it, but using it actively hurts predictions on every fold — this is
  **misled**, not ignored. On the one losing fold (5),
  `statistics.return_autocorrelation` — the strongest driver on 4 of the
  other 5 folds — collapses to near zero while `momentum.rsi` and
  `volatility.relative_volatility` turn more negative than elsewhere.
- **BINARY**: `momentum.macd`, `volatility.relative_volatility`,
  `statistics.return_autocorrelation`, and `statistics.return_distribution`
  are all near zero on every fold — **ignored**, cleanly, with no "misled"
  case to report since this pass does not lose on any fold. `momentum.rsi`
  and `momentum.stochastic` are the two real drivers, both consistently
  positive on every fold — genuinely used, correctly.

**A reportable asymmetry**: `momentum.rsi` is the strongest single driver
of the BINARY pass's clean win, while it is the one component that
actively hurts the REGRESSION pass on every fold. The same feature reads
oppositely depending on whether the task is framed as regression or
classification.

---

## 5. The conditional tree pass (S052-T005)

`S052_WAVE0_DECISIONS.md` D-S052-06 pre-declares a trigger, evaluated per
pass independently: a second, tree-family estimator pass runs only if a
pass beats `RANDOM_PERMUTATION` pooled but not on every fold.

- **BINARY pass: trigger did NOT fire.** It cleared the strict per-fold
  bar cleanly (6/6 folds + pooled), so no second pass was run for it.
  **NOT RUN.**
- **REGRESSION pass: trigger fired** (beats permutation pooled, loses one
  of six folds). A single tree family, `lightgbm.regressor`, was run via
  an eight-candidate `CandidateSetSpec` at the default cap (not widened),
  against the identical persisted regression-pass dataset
  (`dataset_fingerprint` asserted equal to T003's, not re-derived), same
  6-fold plan, `seed=42`, run `6d2842b647cd4097`.

```text
Tree pass (lightgbm.regressor, run 6d2842b647cd4097) — primary metric: spearman_ic
fold  test window                MODEL       RANDOM_PERMUTATION   vs. permutation
0     2025-12-26 -> 2026-01-25   0.034221     0.002931             BEATS
1     2026-01-26 -> 2026-02-25   0.018734    -0.005582             BEATS
2     2026-02-26 -> 2026-03-28  -0.020915     0.003441             LOSES
3     2026-03-29 -> 2026-04-28   0.076786    -0.000642             BEATS
4     2026-04-29 -> 2026-05-29  -0.008486     0.000812             LOSES
5     2026-05-30 -> 2026-06-29   0.054681    -0.002864             BEATS
pooled                           0.023922    -0.000445             BEATS
```

It clears the pooled bar (0.023922 vs. -0.000445, a small edge over
ridge's 0.020566) but **fails the strict per-fold bar worse than ridge did**
— it loses on two folds (2 and 4) instead of ridge's one (fold 5). The
train/test gap makes clear why this pooled edge should not be read as an
improvement:

```text
fold  train_primary  test_primary   gap
0     0.147789        0.034221      0.113568
1     0.050440        0.018734      0.031706
2     0.072038       -0.020915      0.092954
3     0.103525        0.076786      0.026739
4     0.138426       -0.008486      0.146912
5     0.186257        0.054681      0.131577
```

Unlike either baseline pass, train is **consistently and substantially
above test on every fold** — the classic overfit signature. Gaps of
0.027-0.147 dwarf the pooled effect size being measured (0.024). Read
against the per-fold table, the tree pass's small pooled edge over ridge
looks bought by folds 0/1/3/5 fitting harder, not by generalizing better —
it still loses two folds outright, one more than ridge. **This tree result
does not change the regression pass's verdict; it confirms it.** No third
pass exists — per D-S052-06's "no pass 3, whatever pass 2 shows," this
result stands as-is, not chased with a different family or a wider
candidate set.

---

## 6. What would change the verdict (future options only)

These are named as possible future work, not as a retroactive excuse for
the regression pass's result:

- A different label horizon for the regression pass (this study used one
  1h horizon for both passes; a longer or shorter horizon has not been
  tried).
- A different hyperparameter grid within the already-in-scope linear or
  tree families.
- A different feature family or a narrower/wider feature set — explicitly
  a *future* study, not a widening of this one; `S052_WAVE0_DECISIONS.md`
  and `SPRINT_052.md` §3/§5 forbid adding features in response to this
  result.
- A separate study on a different instrument is conceivable as future work
  in principle, but is out of scope for this document by construction
  (§1/D-S052-03a) and would require its own separate, separately-approved
  document.

None of the above was tried in this sprint, and trying any of them now
would violate the sprint's own "no chasing a better number" rule
(`S052_WAVE0_DECISIONS.md` D-S052-06, D-S052-07).

---

## 7. What this document is not

**ADR-0024's rule, restated**: strong Phase 10 metrics are a
**precondition** for promotion consideration, never a verdict that a model
should trade. Phase 7 robustness testing remains a separate, unwaived
gate that this study does not touch. This document reports statistical
structure found in a walk-forward comparison against a random-permutation
baseline — it is not a trading recommendation, and no position sizing,
execution, or live-readiness claim follows from it.

**Promotability consequence (ADR-0029), stated but not acted on**: this
document does not promote anything — promotion is a separate,
maintainer-only mechanism, out of scope for Sprint 052 (`SPRINT_052.md`
§3). If a maintainer were to consider promoting a result from this study:
the BINARY/logistic pass's estimator family (`sklearn.logistic`) is
immediately compatible with promotion v1, which supports linear and
logistic families only. The REGRESSION pass's tree result
(`lightgbm.regressor`) would hit ADR-0029's documented refusal for
tree/neural families if promotion were attempted — moot here, since the
regression pass did not clear `S044_GATE.md` §1.4's bar in the first
place.

**BTC only.** This document describes a study on `BTCUSDT.P` and nothing
else. No other instrument's applicability is asserted or implied.

---

## 8. Reproducibility record

```text
REGRESSION pass
  spec file:            apps/cli/examples/predictive/btc_momentum_regime_study_regression.yaml
  definition_hash:       7c219aa47fc72d03e4ca1b01f99fd8da955482bc4487175faddaa539cfc400e7
  dataset_id:            f9f042f9042bcafb
  dataset_fingerprint:   f9f042f9042bcafb26964c01e480d6df52af84b77f0cb9ea02d05911797c2867
  source DatasetRef:     BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1
  estimator:             apps/cli/examples/predictive/btc_momentum_regime_ridge.yaml
                         (sklearn.ridge, alpha=1.0, seed=42)
  run_id:                f7ac893d54ae6b69

BINARY pass
  spec file:            apps/cli/examples/predictive/btc_momentum_regime_study_binary.yaml
  definition_hash:       b5a0e074eb9bfa1d4fdfb34bea0f3ee4bfa82c4b37443693d08b2dde6b570efd
  dataset_id:            98a893f56549c96b
  dataset_fingerprint:   98a893f56549c96b607d929d85ac2902ace4be86df73ab332b8ac9d7ace1117b
  source DatasetRef:     BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1
  estimator:             apps/cli/examples/predictive/btc_momentum_regime_logistic.yaml
                         (sklearn.logistic, C=1.0, seed=42)
  run_id:                faa6983acd03f846

Tree pass (conditional, REGRESSION trigger only)
  same dataset_fingerprint as the REGRESSION pass above (asserted equal by
  an explicit check against the persisted dataset manifest before fitting,
  not assumed)
  estimator family:      lightgbm.regressor (library lightgbm 4.7.0),
                         8-candidate CandidateSetSpec at the default cap,
                         selection_metric=spearman_ic, seed=42
  run_id:                6d2842b647cd4097
  (no committed EstimatorSpec YAML for this pass — see SPRINT_052.md's
  S052-T005 outcome note for why: the CLI has no config key for
  RunPredictiveResearchRequest.candidate_set today, so a committed YAML
  would not be runnable through trading-cli research run)

Source data
  DatasetRef:            BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1
  registry checksum:     df83ecfaba111aeaad24d68905e3e978a11e8ef968f3f7429d3df0aaea28ffed
  import manifest:       rows_decoded=1,311,840, rows_rejected=0, gaps=[]
                         (docs/archive/phases/phase-15-predictive-catalog/S051_BTC_DATA_INVENTORY.md §2/§3)

Framework version:        0.1.0 (pyproject.toml [project].version,
                         src/trading_framework/__init__.py __version__ — both
                         read at the time this document was written; NOT
                         independently confirmed to be the exact version
                         active at run time for T003/T004/T005, since no
                         run manifest field recording it was checked as part
                         of this task)
```

**What lives outside git and is therefore NOT reproducible from the repo
alone**: dataset bytes, run directories (`user_data/workspace/research/
predictive_research/runs/<run_id>/`), rendered report HTML, and any model
blob — all under `user_data/`, which is gitignored and maintainer-owned
(`S052_WAVE0_DECISIONS.md` D-S052-08). A third party with the same source
data (the same `BTCUSDT.P` 1m import, reproduced via Sprint 045's importer
per `docs/archive/phases/phase-15-predictive-catalog/S051_BTC_DATA_INVENTORY.md`'s recorded command)
should be able to re-derive the same `definition_hash` and
`dataset_fingerprint` values from the two committed spec files alone,
without needing anything under `user_data/` from this run.

---

## 9. Source tasks

This document is produced by Sprint 052 tasks S052-T006 and S052-T007
(folded together per the sprint's own descope note). The full run
narrative, including the timeframe-validation incident that corrected the
fold plan mid-sprint, the exact commands used, and reviewer follow-up, is
recorded in `docs/archive/phases/phase-15-predictive-catalog/SPRINT_052.md` (S052-T003 through
S052-T005 outcome notes) and `docs/archive/phases/phase-15-predictive-catalog/S052_WAVE0_DECISIONS.md`.
