# Increment 16C — Signal Quality Scoring

Detailed outcome and criteria from the accepted phase plan. Return to the [Phase 16 index](../../../planning/roadmap/PHASE_16_QUANT_WORKBENCH.md).

## 13H.3 — Increment 16C — Signal Quality Scoring

### Purpose

The first real bridge between classical strategies and ML, and the reason the
preceding two increments exist. A classical strategy proposes candidates; a
model scores their quality; the simulator — unchanged — decides what that is
worth in PnL terms. **This is the phase's key vertical slice.**

It is also the point at which the framework's three standing model-artifact
debts stop being theoretical. `TD-021` (no model registry), `TD-022` (opaque,
non-portable fitted blobs) and `TD-029` (tree/neural promotion deferred) all
describe the same missing thing from different angles: **how a fitted
predictive model becomes something a Strategy Research config can safely
name.** Until now nothing needed to name one from a config; 16C does. TD-021
and TD-022's promotion branch are repaid *inside* 16C; TD-029 is explicitly
re-deferred to 16G by maintainer decision (§13H.12 Q6, Option B) so that this
increment stays a vertical slice (§13H.13).

### Expected capabilities

- A predictive study over signal occurrences with a forward-outcome quality
  label (binary threshold or continuous), i.e. the first real
  `SIGNAL_QUALITY` task.
- Estimator comparison and score-threshold sensitivity analysis, **restricted
  to promotable families** (`sklearn.ridge`, `sklearn.elastic_net`,
  `sklearn.logistic`) for anything that may gate a strategy — see "Q6
  resolution" below.
- Strategy Research able to consume a score as an ordinary gating condition,
  through explicit strategy semantics only:

```text
signal fired
AND market state is true
AND predictive score passes threshold
```

- A baseline-vs-filtered comparison: signal counts, performance, rejected
  losers, rejected winners, false rejects, fold stability, feature importance.
- **A declared scorer-reference contract**: how a Strategy Research config
  identifies *which* fitted model produces the score, and what durability
  guarantee that reference carries. This is the TD-021/TD-022 repayment
  surface, not a side effect.

### Primary flow

```text
Strategy / SignalModel  -> signal occurrences
  -> feature snapshot at each occurrence
  -> forward-outcome quality label
  -> model scores setup quality
  -> Strategy Research simulates baseline vs score-filtered variants
  -> dashboard compares them
```

### In scope as debt repayment (not merely referenced)

**TD-021 — no model registry.** 16C must state, and demonstrate with the
worked example, how a strategy config names its scorer. The expected answer
is the existing content-addressed promoted-artifact directory
(`research/predictive_research/promoted/{artifact_fingerprint}/`, ADR-0029
§2) referenced by fingerprint — i.e. ADR-0024 condition 5's negative
constraint ("no index, no `latest` pointer, no lifecycle field") holds even
with a machine-readable consumer. TD-021 is repaid by that being *confirmed
against a real consumer and written down*, not by a registry appearing. If
16C's design shows a bare fingerprint reference is genuinely unusable from a
config, that is an ADR-0024 revisit and a maintainer decision — 16C may not
add an index inline.

**TD-022 — opaque, non-portable fitted blobs.** The score path 16C defines
must depend only on artifacts with a stated durability guarantee: either
ADR-0029's portable plain-number parameter format, or a materialized score
column persisted with its own provenance. **No part of 16C may depend on
reloading `models/fold_{n}.bin`.** The Sprint 049 disposition's boundary is
preserved: research-run blobs stay opaque, and TD-022's residual (opacity of
never-promoted runs) is explicitly *not* claimed as repaid by 16C.

**TD-029 — tree/neural promotion deferred. Q6 RESOLVED: Option B (maintainer,
2026-09-04).** 16C's premise is comparing estimator families, including the
tree and neural families Sprints 042/043 already ship. Today only
`sklearn.ridge`, `sklearn.elastic_net` and `sklearn.logistic` can reach a
promoted artifact, so a tree scorer could win 16C's comparison and be unusable
downstream. The maintainer's resolution is binding and no longer a choice:

```text
16C's scope STAYS NARROW.  Estimator comparison that may gate a strategy is
                           restricted to promotable families. Tree and neural
                           scorers are RESEARCH-ONLY and are refused at config
                           load time, with a named error, if declared as a
                           strategy gate.
TD-029 moves to 16G.       Its repayment is restated there (§13H.7), not
                           silently dropped. TD-029 stays ACCEPTED longer;
                           its safe operating boundary is unchanged.
```

Growing 16C to also design the version-pinned joblib/ONNX-style promotion path
("Option A") was **considered and not chosen** — it lands a
runtime-deployment-footprint change inside the phase's central vertical slice.
It is recorded here as history, not as a live alternative; reopening it is a
new maintainer decision, not an architect's call at 16C's Wave 0.

The named refusal in `infrastructure/ml/promotion.py` stays in place until an
ADR replaces it (which, under Option B, is 16G's ADR).

### Completion criteria

- One end-to-end worked example on real data: a strategy, its scorer, and both
  simulated variants, with the comparison written down whether or not the
  score helps.
- **The simulator is not bypassed.** Entries, exits, fills, slippage,
  commissions, sizing, the trade ledger and the equity curve stay owned by
  Strategy Research. A prediction is never treated as a trade.
- The score enters simulation only as a declared strategy condition, evaluated
  under the same `available_at` discipline as every other component — no
  look-ahead through the model.
- A negative result ("the score does not improve the strategy") is a complete,
  reportable outcome. So is "only the linear model is usable as a gate" —
  that is Option B's expected shape, not a shortfall.
- **TD-021 is repaid:** the scorer-reference contract is written down, the
  worked example exercises it, and either ADR-0024 condition 5 is confirmed
  sufficient or a maintainer-decided revisit is opened. No registry is
  introduced as a side effect.
- **TD-022's promotion branch is repaid:** the shipped score path depends on
  no opaque blob, and this is asserted by a test, not by convention. The
  remaining residual is stated explicitly in the increment's closing notes.
- **TD-029 is explicitly re-deferred, in writing and in code:** 16C's
  estimator comparison refuses, **at config load time and with a named
  error**, to use a non-promotable family as a strategy gate; that refusal is
  covered by a test; and TD-029's re-deferral is recorded against 16G. Silence
  is not an acceptable outcome — silence is how a tree scorer quietly becomes
  a strategy gate nobody can promote.
- **`MODEL_FAMILY_ALLOWLIST` is unchanged by this increment.** Any diff to it
  is out of scope by definition.

### Dependencies

- 16B (`signal_occurrences` samples), 16A (verdict on the scoring run),
  Phase 6A Strategy Research, Phase 7 Robustness for the follow-up check.
- **Co-requisite: `TD-021` and `TD-022`.** Their repayment is inside this
  increment, not a prerequisite for it — 16C cannot ship without resolving
  how a config names a durable scorer.
- **`TD-029` scope decision — RESOLVED** (§13H.12 Q6, Option B, 2026-09-04).
  This is no longer a blocking prerequisite for planning 16C; the narrow scope
  is settled and 16C may be planned into a sprint on that basis.
- ADR-0024 and ADR-0029 are consumed as binding constraints, not reopened,
  except through the explicit routes named above.
- Sprint 052 has run (§13H.0 entry condition; the Q3 carve-out covers 16B
  only).

### Main risks

- **Threshold overfitting.** Picking the score cutoff that flatters the
  backtest is trivial and invalidating. Mitigation: threshold sensitivity is a
  required output, not an optional chart; the cutoff is chosen out of sample.
- **Double-dipping the same data** for both signal design and score training.
  Mitigation: the purged walk-forward discipline is applied to the *combined*
  workflow, not to the model in isolation.
- **Runtime model loading.** Scoring inside simulation must not become a path
  that loads `models/fold_*.bin` into Strategy Research (an explicit non-goal
  of the source note, §12). How a score reaches the simulator without that
  coupling is this increment's key design question and is ADR-worthy
  (§13H.9 row 2). **This is a different question from TD-029's** — see
  §13H.9's note: one is a research-side boundary decision, the other a
  runtime-deployment-footprint decision.
- **Option B's honest cost.** 16C cannot claim "the best model gates the
  strategy", only "the best *promotable* model does", and Phase 10B/10C's
  shipped tree/neural capability stays unreachable from the workbench until
  16G. This was accepted knowingly (Q6); it is a stated limitation of the
  increment's result, and reports must say so rather than implying the
  comparison was unrestricted.
- Survivorship of the interesting cases: rejected winners matter as much as
  rejected losers and must be reported.

### Out of scope

- Trade-outcome and no-trade models (16F).
- Promotion of any scorer to runtime or dry-run (16G).
- **Any change to `MODEL_FAMILY_ALLOWLIST` whatsoever** (Q6 = Option B).
- Designing the tree/neural serialization path — that is 16G's, under its own
  ADR.
- Replacing any rule-based strategy with an opaque model.
- TD-022's residual (never-promoted research-run blob opacity).

### Completion note (added at closure, 2026-09-09 — append-only, does not replace the text above)

**16C is DONE.** Delivered by Sprint 058
(`docs/archive/phases/phase-16-research-workbench/SPRINT_058.md`), 6/6 tasks, working PRs #472
(planning docs, ADR-0033) / #473 (T001) / #474 (T002) / #475+#476 (T003 +
a manifest-parsing robustness fix found by review) / #477 (T004 + a
warm-up-sizing fix found by review) / #478 (T005) into
`sprint/signal-quality-scoring`. ADR-0033 (score delivery boundary) was
accepted 2026-09-08 and implemented exactly as designed: a strategy
condition (`ScoreConditionSpec`) names a promoted artifact by
content-addressed fingerprint only, resolved once at config load time
(`resolve_score_condition`, T003), evaluated in-process at simulation
time via the unmodified pure-NumPy evaluator (ADR-0029) under the same
`available_at` discipline as every other component (`score_gate.py`, T004)
— never a fitted blob, never `infrastructure.ml`, never bypassing the
simulator.

Every completion criterion above was assessed against the shipped result:

1. **One end-to-end worked example on real data — MET.** Sprint 051's real
   RSI / relative-volatility strategy, a real `signal_occurrences`
   `SIGNAL_QUALITY` study over real `BTCUSDT.P` data (16,415 occurrences),
   a real promoted `sklearn.logistic` scorer, and a real baseline-vs-
   scored Strategy Research comparison — all reproducible via three
   committed scripts. `docs/reference/examples/BTC_SIGNAL_QUALITY_STUDY.md` is the
   full write-up.
2. **The simulator is not bypassed — MET.** `apply_score_gate` composes
   strictly after the existing market/signal gate, as one further Polars
   filter on `{available_at, direction}`; `research/simulation/engine.py`
   is untouched by this sprint's diff, confirmed by direct inspection in
   T004's independent review.
3. **No look-ahead through the model — MET, independently verified.**
   `available_at` in the score path is the byte-identical
   `timestamp + evaluation_timeframe` formula the market/signal gate
   already uses (`model_expression/evaluation/frame_adapter.py`), over the
   same preloaded OHLCV batch — confirmed by direct source comparison in
   T004's review, not merely asserted.
4. **A negative result is a complete outcome — MET, and is the actual
   result.** The worked example's ROC AUC (0.524) barely clears the
   0.507 random-permutation baseline; at the declared, non-cherry-picked
   threshold (0.5, fixed before the threshold-sensitivity table was
   computed), the score gate rejects 2 of 6,200 baseline trades —
   statistically indistinguishable from noise. The 16A verdict applied to
   the underlying predictive run is `INCONCLUSIVE` (rule O3: a positive
   pooled baseline delta, but a per-fold win rate of only 0.5). This is
   reported plainly, not smoothed over — `docs/reference/
   BTC_SIGNAL_QUALITY_STUDY.md` §7 states the honest headline before
   anything downstream is built on it.
5. **TD-021 is repaid — MET.** A real Strategy Research config named a
   real promoted artifact by bare content-addressed fingerprint alone; no
   index, alias, or `latest` pointer was introduced anywhere in the
   phase. `docs/planning/TECHNICAL_DEBT.md` TD-021 is marked **REPAID**.
6. **TD-022's promotion branch is repaid — MET, asserted by test.** The
   score path depends only on `artifact.json`, never `models/fold_{n}
   .bin` — enforced by
   `tests/unit/test_architecture_boundaries.py::
   test_strategy_research_does_not_import_ml_infrastructure`, not merely
   observed. The residual (never-promoted research-run blob opacity)
   stays open, as required.
7. **TD-029 is explicitly re-deferred, in writing and in code — MET.**
   `resolve_score_condition` refuses a non-allowlisted `model_family` at
   config load time with a named error
   (`ScoreConditionFamilyRefusedError`), asserted by test; a real
   promotable-vs-research-only comparison (`sklearn.logistic` vs.
   `xgboost.classifier`) was exercised and correctly partitioned in T002.
   `MODEL_FAMILY_ALLOWLIST` is confirmed byte-for-byte unchanged by this
   sprint, asserted by test, not by convention.

**This closure produced a real predictive study, a real promoted scorer,
and a real Strategy Research comparison — and a complete negative
result.** No market claim is made; ADR-0024's rule (a backtest is never
evidence of a live edge) is restated in the worked example's own write-up.
16D, 16E, and 16G may now consume this increment's artifacts (the
`ScoreConditionSpec` contract, the promoted-artifact reference mechanism,
`docs/reference/examples/BTC_SIGNAL_QUALITY_STUDY.md`'s worked example) as readers;
none may extend the scorer-reference contract or the score-gate mechanism
without a new or amending ADR (ADR-0033 Follow-up).
