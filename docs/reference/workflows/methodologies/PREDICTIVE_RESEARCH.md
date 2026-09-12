# Predictive Research — methodology

Return to the [methodology chooser](../RESEARCH_METHODOLOGIES.md). This page explains the research question and evaluation method; the workflow reference owns contracts and persisted outputs.

## 8. Predictive Research

Predictive Research is a methodology **alongside** Signal, Strategy and Robustness research.
It answers a learning question. It does **not** produce signals, extend Strategy Research,
or promote a trained model to a tradable component.

Phase 10A now covers the dataset foundation (Sprint 039), baseline estimators
(Sprint 040), and the offline HTML report (Sprint 041). Linear and logistic
baselines are the control group. Phase 10B (Sprint 042) adds tree families
through the same estimator protocol, plus bounded candidate selection,
permutation importance, a single-study leaderboard, and three report panels.
Phase 10C (Sprint 043) adds optional extra `dl` (CPU PyTorch): feedforward
MLP on tabular rows and LSTM/GRU on fold-contained sequence windows, plus
learning-curve and window-accounting report panels. Sprint 044 closes Phase
10 with a read-only Predictive Research page in `apps/dashboard` (study
picker, leaderboard sorted by baseline delta, run detail, provenance, and a
link out to the offline HTML report) and ADR-0024, the IDEA-014 promotion
gate. Models do not trade.

### Research Question

> Is there predictable structure in these declared features, under a split that makes an out-of-sample claim honest?

### Suitable For

- declaring a supervised learning problem over Market Analysis outputs,
- labelling evaluation bars from reused forward outcomes,
- proving absence of temporal leakage before any model is fit,
- training declared baselines (ridge, elastic net, logistic) per fold,
- training declared tree families (XGBoost, LightGBM, CatBoost) per fold,
- training declared neural families (feedforward MLP; LSTM/GRU on sequence windows) per fold,
- bounded inner-fold candidate selection and a single-study leaderboard,
- measuring statistical and finance-aware metrics against naive reference baselines,
- reviewing one run as standalone offline HTML (fold timeline, baselines, calibration,
  native vs permutation importance, selection trace, study leaderboard,
  learning curves, window accounting),
- browsing studies and runs side by side in the dashboard's Predictive
  Research page (Sprint 044): study picker, baseline-delta leaderboard,
  per-fold run detail, and provenance, all read from persisted facts.

### Not Suitable For

- emitting tradable signals,
- Strategy Research (trades, equity, PnL),
- Robustness Research (parameter / stress verdicts),
- computing metrics inside the dashboard (it reads persisted facts only; ADR-0022),
- promoting a trained model to Market Analysis (IDEA-014 → ADR-0024, gated, not implemented).

### Samples

`PredictiveStudySpec` declares *which rows* a study is about via an explicit
`sample` block plus a `task` (Sprint 056 / ADR-0031, increment 16B). This
answers a different question from the one Phase 10 always answered
implicitly: not just "what happens next, from anywhere?", but optionally
"what happens after this specific thing fires?".

```text
sample.kind = every_bar             one row per complete evaluation bar --
                                     the default, and today's original
                                     behaviour, made explicit.
sample.kind = signal_occurrences    rows are a declared Signal Model's
                                     firings, referenced by declaration only
                                     (signal_model_file + signal_model_id),
                                     never by a run id or a persisted
                                     occurrence artifact. An optional
                                     direction filter (ANY | LONG | SHORT,
                                     default ANY) narrows the firings kept.
```

Both `sample` and `task` default-elide out of the spec's serialized form when
they hold their default value (`every_bar` / `FORWARD_RETURN`), so every
study that predates this feature keeps the exact `definition_hash` it always
had — an explicitly-declared default hashes identically to an omitted one.

`task` records research *intent*, distinct from `LabelKind`/the estimator's
statistical task type. Only two combinations of `sample.kind` x `task` are
implemented; every other pairing is refused at load time with a named error:

| sample kind | task | |
|---|---|---|
| `every_bar` | `FORWARD_RETURN` | accepted — today's behaviour |
| `signal_occurrences` | `FORWARD_RETURN` | accepted — plain forward return over a selected universe |
| `signal_occurrences` | `SIGNAL_QUALITY` | accepted — is this signal's own firing predictive? |
| `every_bar` | `SIGNAL_QUALITY` | refused — there is no signal whose quality could be judged |

`strategy_trades` and `labelled_setups` (rows from a simulated trade or a
discretionary setup) are **declared in the contract's design intent and
refused at load time, not silently accepted as no-ops** — increment **16F**
owns implementing them. `sessions_or_windows` is reserved the same way, for a
later, unassigned increment.

For `every_bar`, rows are **evaluation bars**, not `SignalOccurrence` objects:
the matrix builder constructs a synthetic long-only occurrence table (one row
per bar) so `compute_forward_outcomes_for_horizons` can be reused. For
`signal_occurrences`, rows are the declared Signal Model's real firings,
resolved by `application/predictive_research/resolve_signal_occurrences.py`
(`evaluate_models` -> `materialize_signal_occurrences`), with the
occurrence's own direction passed through to `forward_return` — never
synthesized as long-only. In both cases incomplete and non-finite rows are
excluded and counted in the manifest; they never receive a label, and the
manifest's sample provenance (kind, task, resolved row counts, per-reason
drop counts) is persisted for both kinds, so "which rows and why" is always a
read, never an inference.

**Sample selection is applied after labelling, on the full evaluation grid,
never before (the filter-late rule, D-S056-05).** `label_end_at` is derived
*positionally* from the complete bar sequence (`timestamps[index +
horizon_bars]`); computing it over an already-filtered, sparse sequence would
silently fabricate a wider label window than the study declared and leak
across it. This is why the implementation order is the opposite of the
naive reading ("resolve the sample universe first, then compute features at
those rows") — the full grid is always labelled first, and only afterwards
is a `signal_occurrences` sample's row selection applied to it. No leakage
guard (purge, embargo, `min_train_rows`, the zero-TEST-rows error) is ever
relaxed to accommodate a sparse sample; an under-powered sample raises the
same hard error it always did.

A committed synthetic example — `apps/cli/examples/predictive/signal_occurrences_sample_example.yaml`
— declares a `signal_occurrences` sample and parses through
`load_predictive_study_spec` with no code change. It cannot be run end to
end yet: no loader in the framework turns a declared `signal_model_file`
path into a `SignalModelDefinition` (TD-031, `docs/planning/TECHNICAL_DEBT.md`),
so pointing a CLI config at it fails fast with a named
`PredictiveDatasetError` naming the missing `signal_model` input, rather than
a silent no-op.

### Features and transforms

A feature is a declared analysis output (`FeatureSpec` → `AnalysisFrame` column with
`OutputRef` lineage). The builder never recomputes analysis.

Bounded transforms this slice: `NONE`, `LOG`, `DIFF`, `PCT_CHANGE`.
`RANK` is **rejected** at matrix build — cross-sectional versus expanding rank is
ambiguous, and a global rank would leak.

Preprocessing that must be fitted (scaling, imputation) is **not** part of the
dataset builder. Sprint 040 fits `IMPUTE_MEDIAN` then `STANDARDIZE` inside each
fold on `TRAIN` rows only. `PURGED` and `EMBARGOED` rows never reach `fit()`.

### Workflow

```text
Published DatasetRef
  → PredictiveStudySpec (YAML/JSON)
  → declared FeatureSpec columns via run_analysis
  → labelled matrix (entity_id, horizon_bars, availability, label)
  → purged + embargoed walk-forward fold roles
  → PredictiveDatasetEnvelope (manifest + fingerprint)
  → EstimatorSpec (family + hyperparameters + seed)
      or CandidateSetSpec (declared, capped; inner TRAIN split, TEST once)
  → run_predictive_research (per-fold fit on TRAIN, predict on TEST;
      sequence families: application builds windows, then fit / predict)
  → PredictiveRunEnvelope (predictions.parquet, metrics.json, opaque blobs)
  → analyze_predictive_run (writes metrics.json from predictions; never deserializes model blobs)
  → compare_predictive_runs (optional leaderboard.json on one dataset fingerprint)
  → render_predictive_research_report (read-only HTML; optional importance/selection/leaderboard/learning_curves/window_accounting sidecars)
  → apps/dashboard Predictive Research page (DuckDB catalog scan of the same
      persisted datasets/runs directory tree; study picker → leaderboard →
      run detail → link to the offline HTML report)
```

CLIs: `scripts/predictive_research/build_predictive_dataset.py`,
`run_predictive_research.py`, `analyze_predictive_run.py`,
`compare_predictive_runs.py`, `render_predictive_report.py`.

Dashboard: `apps/dashboard` (`pages/6_Predictive_Research.py`, Sprint 044) reads
the same `manifest.json` / `metrics.json` / `predictions.parquet` facts through
a read-only catalog scan and its own DTOs — it never imports
`trading_framework.research` or an ML library (ADR-0022; enforced by
`tests/unit/test_apps_boundaries.py`).

### Fold roles

Fold assignment is persisted data, not a training-time courtesy.

```text
TRAIN | TEST | PURGED | EMBARGOED
```

Purged and embargoed rows are **retained with a role label**, not deleted.

### Fingerprint and storage

The dataset fingerprint hashes:

```text
study spec (definition_hash)
feature lineage (OutputRef per column)
DatasetRef
time range
```

It never hashes materialized frame bytes. `dataset_id` is the first 16 hex
characters of that fingerprint.

```text
<workspace>/research/predictive_research/datasets/{dataset_id}/
  manifest.json
  features.parquet
  folds.json
<workspace>/research/predictive_research/runs/{run_id}/
  manifest.json
  predictions.parquet
  metrics.json
  report.html            # offline Plotly; first figure embeds JS inline
  selection.json         # optional; bounded candidate selection
  importance.json        # native + permutation importance and train/test gap
  leaderboard.json       # optional; single-study comparison of run dirs
  learning_curves.json   # optional; inner-train / inner-val loss per fold
  window_accounting.json # optional; dropped windows and effective sample
  models/fold_{n}.bin    # opaque; reproduce by re-fitting from the manifest
```

Durable facts of a run are predictions and metrics. Fitted blobs are convenience
only, tagged with library name and version. No workflow depends on reloading them.

### Typical Questions

- Can these analysis columns be assembled into a leakage-safe labelled matrix?
- How many rows does purge / embargo remove from each fold?
- Does rebuilding an unchanged spec yield the same fingerprint?
- Do ridge / elastic net / logistic beat constant, majority, and permutation baselines out of sample?
- Do XGBoost / LightGBM / CatBoost beat those S040 baselines on the same dataset fingerprint?
- Do feedforward and LSTM families recover a known synthetic signal, and which ranks higher?
- Is native gain aligned with out-of-sample permutation importance, or only with the training fold?
- How large is the |train - test| gap on the primary metric per fold?
- Is the result stable across folds, or does one fold carry the pooled metric?
- Did inner early stopping restore an epoch before the last recorded loss?
- How many sequence windows were dropped by incomplete lookback, gaps, or fold boundaries?

---
