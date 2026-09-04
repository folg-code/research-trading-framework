# Phase 16 — Quant Research Workbench

```text
Status: APPROVED (maintainer, 2026-09-04) — no sprint opened for any increment
```

Full detail for `ROADMAP.md` §13H — this is the LIVE, canonically-updated location for this
phase; `ROADMAP.md` carries only a short pointer stub under the same section number.

**This file is expected to keep changing** as the phase progresses (Wave 0 decisions, sprint
openings, status flips). Unlike `docs/planning/ROADMAP_COMPLETED_PHASES.md` — which is
frozen history — edits to this phase's detail happen **HERE**, not by re-inflating the
`ROADMAP.md` stub.

Internal heading numbering is preserved exactly as it was in `ROADMAP.md`, so citations of
the form `roadmap/PHASE_16_QUANT_WORKBENCH.md §13H.12` resolve, matching the convention
already used in `ROADMAP_COMPLETED_PHASES.md`.

The body below is a **verbatim relocation**. Its substance was negotiated with the maintainer
on 2026-09-04 (eight resolved decisions, Q1–Q8); any wording change goes through that same
process, never through a file move.

---

# 13H. Phase 16 — Quant Research Workbench (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-04). Approving the phase is
**not** approving a sprint: no sprint is opened, planned or numbered for any
increment. 16A–16C are the committed direction; 16D–16G are directional and
will be re-specified from evidence before any of them is planned (§2.9, §2.8).
Increment-level decisions deliberately left open at phase approval — 16E's
port-vs-bespoke confirmation (§13H.12 Q4), 16G's numeric parity tolerances
(§13H.12 Q7) — are Wave 0 decisions for the sprint that plans that increment.
**Source:** `docs/planning/RESEARCH_SIMULATION_DEVELOPMENT_DIRECTION.md`
(`Status: DRAFT`) — the maintainer's directional note. That note remains the
originating record; **this section is the canonical roadmap location**. An
adjacent DRAFT note, `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md`,
covers presentation direction and informs 16D without governing it.
**Sprints:** none. Increment numbering (16A–16G) is deliberately independent
of sprint numbering, per the practice already used for 13A–13G and 15A/15B.
**ADRs:** **five are anticipated, none written.** Under the resolved §13H.12
Q6 (Option B) the tree/neural serialization ADR belongs to **16G**, not 16C.
See §13H.9 — writing them before an increment is planned would be premature
specification of a phase this roadmap requires to stay directional (§2.9).
**Registry entries this phase plans to close:** `PRB-012`, `PRB-013`,
`PRB-020`, `TD-021`, `TD-022`, `TD-029` — see §13H.13. All remain
OPEN/ACCEPTED until the owning increment ships; phase approval names the
planned closure route and closes nothing.

## Purpose

The framework today is a set of capable but independently-reached runners:
Signal Research, Strategy Research, Robustness Research, Predictive Research
and a read-only dashboard. Each already consumes the same Market Analysis
component catalog (Phase 3/4A, extended by Sprints 047/048/051), which is the
hard part and is done.

What does not exist is a **workflow** across them: a classical strategy cannot
be scored by a model, a model cannot be trained on a strategy's own trades, a
research result carries no standardized quality verdict, and nothing separates
"a good metric" from "a candidate worth promoting" except a human reading a
report.

Phase 16 closes that gap without changing what each runner owns:

```text
Market Components
  -> Feature Sets
  -> Research Samples
  -> Predictive / Strategy / Robustness Runs
  -> Analyst Diagnostics
  -> Dashboard Review
  -> Optional Promotion Candidate
```

The organizing principle, restated from the source note:

```text
One neutral market-component catalog, many research consumers.
```

Components stay neutral analytical facts. Interpretation belongs to the model
or the workflow, never to the component. No "ML-only feature" concept is
created — that would fork the catalog, which is the one thing this phase
exists to prevent.

## Increment family

```text
16A — Analyst Verdict Artifact                   entry condition: Phase 15B
16B — SampleSpec Foundation                      every_bar + signal_occurrences
                                                 MAY start in parallel with
                                                 Sprint 052 (§13H.0)
16C — Signal Quality Scoring                     THE vertical slice of this phase
                                                 closes TD-021 and TD-022's
                                                 promotion branch; TD-029 is
                                                 explicitly re-deferred to 16G
                                                 (Q6 = Option B, resolved)
16D — Quant Lab Dashboard                        read-only, over 16A/16C artifacts
16E — Strategy Families                          closes PRB-020 and PRB-012
16F — Trade Outcome and No-Trade Models          strategy_trades sample kind
16G — Promotion Candidate Gate                   closes PRB-013 and TD-029;
                                                 explicit gate, no auto-approval
```

Ordering is a dependency chain, not a schedule. 16A–16C are the committed
direction; 16D–16G are directional and will be re-specified from evidence
before any of them is planned (§2.9, §2.8).

## 13H.0 — Relationship to Phase 15B / Sprint 052 (read first)

The source note's "Increment 1 — Real-Data Predictive Study and Verdict"
overlaps an already-planned, already-numbered piece of work. The
reconciliation is binding and was confirmed by the maintainer on 2026-09-04
(§13H.12 Q2):

```text
The STUDY stays where it is.   Phase 15B / Sprint 052, unchanged, unrenamed,
                               unrenumbered, unwidened. It is Phase 16's
                               ENTRY CONDITION, not Phase 16's first
                               increment.
The VERDICT ARTIFACT moves.    Phase 16 increment 16A.
```

Why the split, rather than folding the verdict into Sprint 052:

- Sprint 052's binding rule is that the Phase 10 pipeline is **consumed, never
  modified**, and `research/predictive/`, `application/predictive_research/`
  are on its FORBIDDEN-paths list (`SPRINT_052.md` §5). A *persisted,
  standardized* verdict artifact is by definition a change to the analysis
  layer that emits artifacts. It cannot be built inside Sprint 052 without
  breaking that sprint's central discipline.
- Sprint 052's acceptance already requires the verdict **as prose**, in one
  unhedged sentence (`SPRINT_052.md` T006, acceptance criterion 9). That is
  the right deliverable for a study whose outcome is unknown at planning time.
- 16A therefore has a real, non-duplicative job: turn that prose judgement
  into a contract derived from persisted facts, with one worked example — the
  Sprint 052 run — to validate it against.

### Entry condition, with the 16B carve-out (maintainer, 2026-09-04, Q3)

```text
16A and every increment after it   do NOT open before Sprint 052 has
                                   actually RUN. A verdict contract designed
                                   with no real run behind it would be
                                   designed against synthetic fixtures —
                                   precisely the failure mode §13G exists to
                                   correct.
16B (SampleSpec Foundation)        MAY start in parallel with Sprint 052.
                                   16B depends on Sprint 052 existing as a
                                   planned study, not on its RESULT: the
                                   SampleSpec contract and PredictiveTask
                                   taxonomy are unchanged whether the study
                                   comes back positive or negative.
```

This carve-out is explicit and narrow. It does not make 16B a Sprint 052
dependency in the other direction — Sprint 052 must remain runnable on the
unmodified Phase 10 pipeline, so 16B may not land any change Sprint 052 would
then be consuming. If 16B is planned into a sprint while Sprint 052 is open,
that non-interference is a Wave 0 decision for 16B's sprint.

## 13H.1 — Increment 16A — Analyst Verdict Artifact

### Purpose

Make "is this result any good?" a persisted, reviewable fact rather than a
judgement re-made by each reader (and, worse, re-made inside the dashboard).

### Expected capabilities

- A standardized verdict vocabulary over research runs:
  `PASS`, `WEAK_PASS`, `INCONCLUSIVE`, `FAIL`, `REJECTED_OVERFIT`,
  `REJECTED_LEAKAGE_RISK`, `REJECTED_LOW_SAMPLE`, `REJECTED_CONCENTRATION`.
- The verdict computed from facts the pipeline **already persists** — baseline
  delta vs `RANDOM_PERMUTATION`, per-fold stability, train/test gap, sample
  size, class imbalance, period and regime concentration, feature-importance
  sanity — with each contributing input recorded alongside the verdict.
- The rule set is declared and versioned, so a verdict is reproducible and a
  changed threshold is visible as a diff, not as a silently different answer.
- Applied retrospectively to the Sprint 052 run as the worked example.

### Primary flow

```text
persisted run artifacts (metrics, folds, importances)
  -> declared verdict rule set (versioned)
  -> verdict + the facts that produced it, persisted as a sidecar
  -> dashboard displays it; dashboard never computes it
```

### Completion criteria

- A run carries a verdict and the inputs behind it, both reproducible from the
  persisted artifacts alone.
- Re-running the rule set over the same artifacts yields the same verdict.
- The dashboard reads the verdict; no verdict logic exists in `apps/dashboard`.
- Documentation states plainly that a verdict is a decision aid for what to
  study next — never evidence of a live edge, never a promotion approval
  (ADR-0024's rule, restated, not weakened).

### Dependencies

- Phase 10 (Sprints 039–044) — complete.
- **Phase 15B / Sprint 052 has run** — hard entry condition (§13H.0). The Q3
  parallel-start carve-out applies to 16B only, never to 16A.

### Main risks

- **A verdict becomes an authority.** A green `PASS` is easier to over-trust
  than a table of metrics. Mitigation: the vocabulary carries no "validated"
  or "approved" value, and `WEAK_PASS`/`INCONCLUSIVE` must be reachable and
  common outcomes, not rare ones.
- **Threshold tuning to produce nicer verdicts.** Mitigation: the rule set is
  versioned and diffable; changing a threshold after seeing a result is a
  reviewable act.
- Designing the rule set from one study is thin evidence. Mitigation: keep the
  first version deliberately conservative and few-ruled.

### Out of scope

- Any change to Sprint 052's scope, instrument, or acceptance criteria.
- Verdicts for Strategy or Robustness runs (16D onward may extend the
  vocabulary; the first version is predictive-run only).
- Any automatic consequence of a verdict — nothing is promoted, filtered or
  hidden because of one.

## 13H.2 — Increment 16B — SampleSpec Foundation

### Purpose

Predictive rows today are effectively evaluation bars. That is one question
("what happens next, from anywhere?") and it is the *least* interesting one
for a strategy-centric framework. An explicit sample-universe contract lets
the same pipeline answer materially different questions without forking it.

### Expected capabilities

- An explicit `sample:` block in `PredictiveStudySpec`, defaulting to today's
  behaviour so every existing spec keeps working unchanged.
- Two kinds only in this increment:

```text
every_bar             the current behaviour, made explicit
signal_occurrences    rows are a Signal/Strategy Model's firings
```

- `strategy_trades` and `labelled_setups` are declared in the contract's
  design intent but **not implemented here** (16F, and a later discretionary
  labelling increment).
- A higher-level `PredictiveTask` distinguishing the research question from
  the statistical task type. `REGRESSION | CLASSIFICATION` remains the
  estimator's task type; `PredictiveTask` records intent:
  `FORWARD_RETURN`, `SIGNAL_QUALITY`, `TRADE_OUTCOME`, `REGIME_CLASSIFICATION`,
  `VOLATILITY_FORECAST`, `NO_TRADE_FILTER`,
  `DISCRETIONARY_SETUP_CLASSIFICATION`. Only the kinds a shipped sample/label
  builder supports are accepted at load time; the rest are reserved names, not
  silently-accepted no-ops.
- Label builders become the extension point. The framework's next unit of
  value is more **label builders**, not more estimator classes.

### Primary flow

```text
PredictiveStudySpec
  = DatasetRef + range + SampleSpec + FeatureSpec[] + LabelSpec
      + PredictiveTask + purged walk-forward split
  -> sample universe resolved FIRST
  -> features computed AT those rows
  -> labels built for those rows
  -> the unchanged fit / fold / metrics path
```

### Completion criteria

- Every existing `PredictiveStudySpec` still loads and produces an identical
  `definition_hash`-comparable result under the `every_bar` default.
- A `signal_occurrences` study builds a dataset whose row count equals the
  Signal Model's firing count over the same range — asserted, not assumed.
- Purge/embargo semantics are re-derived for irregularly-spaced rows and shown
  correct; leakage guards (ADR-0023 §4) are strengthened or unchanged, never
  relaxed to accommodate a new sample kind.
- CI stays synthetic-only and network-free (ADR-0023 §8 untouched).

### Dependencies

- Phase 10 pipeline; Phase 5 Signal Research semantics.
- **Entry condition (maintainer, 2026-09-04, §13H.12 Q3): 16B is exempt from
  the phase's Sprint 052 gate and MAY be planned and started in parallel with
  Sprint 052.** 16B depends on Sprint 052 existing as a study, not on its
  result. The exemption carries one obligation: 16B must not land a change
  that Sprint 052 would then be consuming, because Sprint 052 runs the Phase
  10 pipeline unmodified — non-interference is a Wave 0 decision for 16B's
  sprint if the two overlap in time.
- 16A only if the maintainer wants verdicts on the new sample kinds from day
  one (not required).

### Main risks

- **Leakage moves house.** With irregular rows, an embargo expressed in bars
  is not the same guard it was. This is the increment's central technical
  risk and its central test target.
- **Sample selection bias.** Rows conditioned on a signal firing are a biased
  slice of the market by construction. The contract must make that visible
  (persisted sample provenance), not hide it.
- Small sample universes: a selective signal may yield too few rows per fold
  to learn anything. `REJECTED_LOW_SAMPLE` (16A) exists for exactly this.
- **Parallel-start friction with Sprint 052** (new, from the Q3 carve-out): a
  shared-file collision between 16B's contract work and Sprint 052's run is
  possible if both are open at once. Mitigation: Sprint 052's FORBIDDEN-paths
  discipline already keeps it out of the pipeline; 16B's sprint declares the
  reverse boundary at Wave 0.

### Out of scope

- `strategy_trades`, `labelled_setups`, `sessions_or_windows` sample kinds.
- Any new estimator family, extra or dependency.
- MTF-capable `FeatureSpec` (a known, separately-tracked structural gap,
  §13G "Main risks").

### ADR

The `SampleSpec` contract shape and the `PredictiveTask` taxonomy are
hard-to-reverse contract decisions that every later increment depends on.
**An ADR is required for this increment** (§13H.9).

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

## 13H.4 — Increment 16D — Quant Lab Dashboard (directional)

### Purpose

Evolve `apps/dashboard` from run browsing into an analyst review surface over
what 16A–16C now persist.

### Expected capabilities

- Sections along the lines of Model Lab, Signal Quality Lab, Strategy Family
  Lab, Robustness Lab, Promotion Candidates.
- Study / feature-set / run navigation; a leaderboard ordered by baseline
  delta; the 16A verdict; threshold sensitivity; accepted-vs-rejected signal
  breakdown; fold stability, train/test gap, sample and concentration warnings.

### Completion criteria (directional)

- Every number displayed is read from a persisted artifact. The dashboard
  **fits nothing, recomputes no research metric, imports no research engine,
  promotes nothing and declares nothing validated** — the existing read-only
  boundary is preserved, not renegotiated.
- A reviewer can reach a defensible accept/reject opinion on a run without
  opening a terminal.

### Dependencies

16A (verdict), 16C (the comparison it displays). Informed by
`DASHBOARD_DEVELOPMENT_DIRECTION.md` (DRAFT).

### Main risks

Presentation pressure to compute "just one small metric" in the app; scope
sprawl across five labs at once (this increment should itself be sliced).

## 13H.5 — Increment 16E — Strategy Families (directional)

### Purpose

Give Strategy Research the bounded-expansion machinery Signal Research already
has. **This increment is the planned closure route for `PRB-020`** (OPEN,
MEDIUM) **and for `PRB-012`** (OPEN, MEDIUM) — see `PROBLEM_REGISTRY.md`. Both
are planned, not closed; both remain OPEN until this increment ships.

The two belong together and are deliberately not split: `PRB-020` asks for
bounded candidate generation in Strategy Research, and `PRB-012` asks for the
default limits that make "bounded" mean something. Building the first without
the second would produce a planner whose only bound is the user's own YAML —
which is the situation PRB-012 already describes.

### Direction decisions already taken (maintainer, 2026-09-04)

```text
Q4 — PRB-020's direction.  DEFAULT DIRECTION SET: port
                           research/signal_research/family_planning.py's
                           pattern to a new
                           research/strategy_research/family_planning.py,
                           mirroring the Signal Research design.
                           NOT unconditional: if 16E's own design work finds
                           Strategy Research's combinatorics genuinely differ
                           (multi-model composition vs. single-model parameter
                           sweeps), that finding is SURFACED EXPLICITLY at
                           16E's Wave 0 and decided there — never decided
                           unilaterally by an architect mid-implementation.
Q8 — PRB-012 back-         NOT RETROFITTED to Signal Research's existing
     application.          planner. Deliberate, not an oversight: no runaway
                           incident has been reported, and retrofitting would
                           change existing working configs' behaviour with no
                           demonstrated trigger (§2.7). PRB-012 closes for the
                           NEW Strategy Research planner only; the asymmetry
                           is accepted explicitly and revisited if a concrete
                           incident or need arises.
```

### Expected capabilities

- Bounded candidate generation with `candidates_generated` /
  `candidates_evaluated` / `candidates_skipped` bookkeeping, mirroring
  `research/signal_research/family_planning.py`'s established pattern (Q4's
  default direction).
- Family identifiers, nested model comparison, marginal-contribution analysis,
  parameter sensitivity, cost/slippage sensitivity.
- A ranking-objective contract with eligibility filters.
- **Planner limits with conservative defaults** (`PRB-012`): a maximum
  candidate count, a maximum number of model conditions, a maximum parameter
  dimensionality, a warning/confirmation threshold below the hard maximum,
  and a preflight cost estimate. Every limit is overridable explicitly, and
  exceeding one is reported, never silently applied.

### Why it belongs in this phase

ML scoring creates families by construction:

```text
baseline signal
baseline signal + regime filter
baseline signal + volatility filter
baseline signal + ML quality score
baseline signal + ML quality score + bracket exit
```

Without family machinery, 16C's comparison is a hand-assembled pair of runs.

### Completion criteria (directional)

- A Strategy Research config declaring alternatives produces a bounded,
  observable candidate set with counts preserved — the search space is
  **observable before it is large**.
- Multiple-testing exposure is recorded, not implied.
- `PRB-020`'s resolution criteria are met along Q4's default direction, or a
  documented Wave 0 divergence from it is recorded with its rationale.
- **`PRB-012`'s resolution criteria are met** as part of this increment:
  - initial conservative default limits ship enabled, not opt-in;
  - every limit has an explicit, documented override;
  - planner tests cover both the default-limit path and the override path,
    including the refusal at the boundary;
  - **no silent pruning** — a candidate set that would exceed a limit is
    refused or reported with counts, never quietly truncated. A truncation
    that is not visible in `candidates_skipped` is a defect, not a
    performance feature.
- The Signal Research asymmetry (Q8: not retrofitted) is restated in the
  increment's closing notes, so PRB-012 does not close leaving the reader to
  discover the gap themselves.

### Dependencies

- Phase 6A.
- **PRB-020's direction** — resolved as a default (Q4); no longer a blocking
  prerequisite for planning 16E, but its confirmation-or-divergence is a
  required Wave 0 item.
- **PRB-012** — co-requisite, resolved inside this increment. Its default
  *values* remain a Wave 0 decision for 16E's sprint.
- Independent of 16B/16C in principle, though 16C is what makes it urgent.
- Sprint 052 has run (§13H.0).

### Main risks

Unbounded search dressed up as a family; a ranking objective that quietly
becomes an optimizer over noise; limits set so high on first pass that they
satisfy PRB-012's letter while bounding nothing in practice (mitigation:
defaults are chosen to be *inconvenient*, with an easy documented override,
rather than generous); the Q8 asymmetry drifting out of memory and someone
"fixing" Signal Research's planner as a side effect of 16E — which would be
exactly the unrequested behaviour change Q8 declined.

### ADR

Confirming (or departing from) Q4's default port direction is a binding
architectural decision — **ADR expected** (§13H.9). PRB-012's default limits
are a parameter choice recorded in that ADR's consequences, not a separate
ADR, and so is the Q8 non-retrofit boundary.

## 13H.6 — Increment 16F — Trade Outcome and No-Trade Models (directional)

### Purpose

Extend the sample universe to simulated trades and to rejected/accepted
candidates, closing the loop between simulation and ML.

### Expected capabilities (directional)

- `strategy_trades` sample kind over a Strategy Research run's `trades`
  artifact, with entry-time feature/state context.
- Labels from realized outcomes: win/loss, realized R, MAE/MFE, exit reason,
  holding-time quality.
- A no-trade filter — "when should an otherwise valid setup be ignored?" —
  which is frequently more useful than an entry model.

### Completion criteria (directional)

- A trade-outcome study reproducible from a persisted strategy run ID alone.
- Entry-time context is provably entry-time: no post-entry information reaches
  a feature.
- Results feed strategy filtering only through 16C's explicit gating path —
  including its Option B family restriction, which 16F inherits and does not
  relax.

### Dependencies

16B (contract), 16C (the gating path, including its scorer-reference
contract), Phase 6A trade artifacts.

### Main risks

Label leakage from realized outcomes into features; trade counts far too small
for stable fitting; conditioning on a strategy's own simulated fills makes the
result inherit every execution assumption in that simulation.

## 13H.7 — Increment 16G — Promotion Candidate Gate (directional)

### Purpose

Make promotion an explicit, evidenced act. Strong predictive metrics are never
sufficient on their own, and Sprint 049's artifact path is a mechanism, not an
approval.

**This increment is the planned closure route for `PRB-013`** (OPEN, HIGH) —
Research/Runtime parity is not yet measurable. The flow below already names an
"offline/online parity test" step; PRB-013 is the definition of what that step
means, and 16G cannot ship a defensible gate against an undefined parity bar.
Parity is therefore in 16G's scope, not adjacent to it.

**It is also `TD-029`'s owning increment** (§13H.12 Q6, Option B, resolved
2026-09-04): the tree/neural promoted-artifact serialization path that 16C was
explicitly kept clear of lands here, behind its own ADR, or is re-deferred
again by an explicit decision — never lifted implicitly.

### Expected capabilities (directional)

```text
positive research result
  -> analyst diagnostics (16A)
  -> robustness / stability review (Phase 7)
  -> explicit promotion candidate record
  -> offline/online parity test          <- PRB-013's formal suite
  -> optional Market Analysis State or strategy score component
  -> dry-run validation
```

- A promotion-candidate manifest listing required diagnostics, the parity
  checklist, and the human who accepted it.
- Dashboard visibility of candidates and their gate status.
- **A formal parity test suite** (`PRB-013`): canonical decision fixtures,
  the same component implementations exercised across batch backtest, replay
  and paper modes, and a comparison of `SignalOccurrences` and decisions
  between them.
- **`TD-029`'s repayment surface**: a version-pinned joblib/ONNX-style
  promotion path for tree and neural families, designed through its own ADR,
  reusing `infrastructure/ml/promotion.py::require_supported_model_family`'s
  guard ordering (family allow-list check, then version guard, before any
  unpickling) as its starting shape.

### Completion criteria (directional)

- **Nothing is promoted automatically.** No verdict, metric or leaderboard
  position causes promotion; a human act does.
- **`PRB-013`'s resolution criteria are met:**
  - a formal parity test suite exists and runs in CI under the synthetic-only,
    network-free constraint (ADR-0023 §8 untouched);
  - **accepted tolerances are declared numerically and versioned** — a
    tolerance changed after seeing a failure is a visible diff, on the same
    principle as 16A's verdict rule set. **The numbers themselves are NOT set
    by Phase 16's approval** (§13H.12 Q7, deferred by decision): they are a
    16G Wave 0 item requiring maintainer sign-off, once real parity-suite data
    exists to set them against;
  - unavoidable Research/Execution differences are documented as a named,
    finite list, not left as "may differ";
  - a promotion candidate that has not passed the suite cannot reach the
    accepted state — the gate reads the parity result, it does not re-derive
    or waive it.
- **`TD-029` is repaid here, or re-deferred here in writing.** Tree and
  deep-learning families stay gated at runtime until a durable serialization
  and parity story exists. Widening `MODEL_FAMILY_ALLOWLIST` requires an
  accepted ADR; **16G does not lift the deferral implicitly**, and no other
  increment may lift it at all.
- A model may be useful for research and dashboard scoring long before it is
  safe in execution, and the gate says so explicitly.

### Dependencies

- Phase 14 (Sprint 049's mechanism), Phase 7, 16A, 16D.
- **`PRB-013`** — co-requisite, resolved inside this increment. Its accepted
  tolerances are a Wave 0 decision for 16G's sprint and require maintainer
  sign-off (a tolerance is a risk acceptance, not an implementation detail).
- **`TD-029`** — inherited as this increment's scope (Q6 Option B). 16G is
  materially larger than it would have been under the rejected Option A
  ordering, and its sprint should expect at least two waves (parity suite;
  serialization ADR + allow-list widening) or an explicit split.

### Main risks

The gate becomes a rubber stamp; parity testing turns out to be the hard part
and is deferred into invisibility — which is exactly PRB-013's current state
and the reason it is written into completion criteria rather than listed as a
risk; tolerances set wide enough to pass whatever the first candidate does;
16G becoming a two-headed increment (parity + serialization) and needing to be
split — an expected consequence of Q6's Option B, to be handled at planning
time rather than absorbed silently.

### ADR

The candidate-manifest contract and its relationship to ADR-0024/ADR-0029 —
**ADR expected** (§13H.9 row 5). The tree/neural serialization decision is a
**separate** ADR (§13H.9 row 3), now owned by this increment. Parity
tolerances are recorded in the manifest ADR's consequences and in the suite
itself, not as a separate ADR.

## 13H.8 — Binding rules for the whole phase

```text
ONE catalog. Market Analysis components stay neutral analytical facts. No
    "ML feature" concept, no parallel feature library, no interpretation
    baked into a component
The SIMULATOR owns PnL. Entries, exits, fills, slippage, commissions, sizing,
    the trade ledger and the equity curve stay in Strategy Research. A
    prediction is never a trade
ML enters simulation ONLY through explicit strategy semantics (a declared
    score condition), never by loading model binaries inside Strategy Research
The DASHBOARD stays read-only over persisted artifacts: no fitting, no metric
    recomputation, no research-engine import, no silent promotion, no
    "validated" claim
LEAKAGE GUARDS are never relaxed to accommodate a new sample kind. ADR-0023
    §4 is strengthened or unchanged
CI stays synthetic-only and network-free (ADR-0023 §8 untouched)
NO REGISTRY appears as a side effect. ADR-0024 condition 5's negative
    constraint holds for the whole phase; TD-021 is repaid by confirming it
    against a real consumer, not by building the thing it forbids
NO WORKFLOW in this phase depends on reloading models/fold_{n}.bin (TD-022's
    safe operating boundary, unchanged)
THE FAMILY ALLOW-LIST is widened only behind an accepted ADR, and only in 16G
    (TD-029, Q6 = Option B). Until then the named refusal in
    infrastructure/ml/promotion.py is the only gate, and 16C additionally
    refuses a non-promotable family as a strategy gate at config load time
NO SILENT PRUNING in any planner this phase builds (PRB-012)
A NEGATIVE result is a deliverable. No increment is repaired by adding
    features until something sticks
Phase 15B / Sprint 052 is neither re-scoped nor absorbed (§13H.0), and
    remains separately gated on its own maintainer approval
APPROVING THIS PHASE IS NOT OPENING A SPRINT. Every increment still needs its
    own SPRINT_0XX.md and Wave 0 decisions before implementation
No increment of this phase constitutes trading approval of anything
```

## 13H.9 — Anticipated ADRs (none written; not required by phase approval)

| # | Increment | Decision | Why it is ADR-worthy |
|---|---|---|---|
| 1 | 16B | `SampleSpec` contract shape + `PredictiveTask` taxonomy | Every later increment depends on it; changing it later breaks persisted specs and `definition_hash` comparability |
| 2 | 16C | **Score delivery boundary** — how a model score reaches the simulator without coupling Strategy Research to model artifacts, and how a strategy config *references* its scorer (TD-021/TD-022 repayment surface) | Directly governs the phase's central boundary and decides whether ADR-0024's no-registry constraint survives a machine consumer |
| 3 | **16G** | **Tree/neural promoted-artifact serialization** — the version-pinned joblib/ONNX-style path TD-029's Repayment Direction prescribes | Changes the dry-run/live **runtime deployment footprint**, which ADR-0029 exists to keep at zero. Assigned to 16G by the resolved §13H.12 Q6 (Option B); it is explicitly **not** 16C's |
| 4 | 16E | Confirm or depart from Q4's default direction (port Signal Research's family contract) — with PRB-012's planner-limit defaults and the Q8 non-retrofit boundary recorded in its consequences | PRB-020 explicitly asks for this decision, and Q4 set a default, not a mandate |
| 5 | 16G | Promotion-candidate manifest and its relation to ADR-0024 / ADR-0029, including PRB-013's accepted parity tolerances | Touches the execution boundary and an existing accepted decision |

### Are ADR #2 and ADR #3 the same decision?

**No — they are two decisions, and this section says so deliberately.** The
Q6 resolution makes the separation structural: they now live in different
increments.

- **#2 is a research-side boundary decision (16C).** Its question is: what does
  Strategy Research *consume* at simulation time — a pre-materialized score
  column joined under `available_at`, or an in-process call to a loaded
  model? Its blast radius is the Strategy Research / Predictive Research
  boundary. It changes no deployment artifact and adds no runtime dependency.
- **#3 is a deployment-footprint decision (16G).** Its question is: can a
  fitted tree or neural estimator become a portable, version-pinned artifact
  that is safe to load *outside* the research process at all? Its blast radius
  is the dry-run/live runtime image — ADR-0029's entire rationale was keeping
  scikit-learn, XGBoost/LightGBM/CatBoost and torch out of it.

They are related but not equivalent, and under Option B the relationship is
one-directional and settled:

```text
16C's answer to #2 must not require #3. If #2's chosen mechanism would make a
    non-promotable family necessary for the research loop, that is a design
    failure of #2 under Option B, not a trigger to pull #3 forward
Because #3 is not written, 16C's config-load refusal of non-promotable
    families as strategy gates is the only honest boundary, and it is a
    completion criterion, not a nicety
```

Collapsing them into one ADR would bury a runtime-footprint change inside a
research-boundary decision — precisely the "added as a side effect of another
sprint" outcome TD-029's Repayment Direction forbids.

These are **named, not written.** Writing them now would over-specify
increments this roadmap requires to stay directional (§2.9). Each is authored
when its increment is proposed for a sprint.

## 13H.10 — Phase dependencies

- Phase 10A/10B/10C — complete (Sprints 039–044).
- Phase 15B / Sprint 052 — **the entry condition** (§13H.0); Phase 16 does not
  open before it has run, with the single exception of 16B (Q3 carve-out).
- Phase 5 (Signal Research) and Phase 6A (Strategy Research) — consumed.
- Phase 7 (Robustness) — consumed by 16C and 16G.
- Phase 14 (promotion mechanism) — consumed by 16G; **Phase 14B / Sprint 050
  is not planned, resized or pre-empted by this phase.** Their relative
  sequencing is a deliberately deferred decision (§13H.12 Q5): it is revisited
  once Sprint 052 supplies its Q5 input, and Phase 16's approval neither
  resolves nor pre-empts it.
- Phase 11/12/13 (CLI, authoring, exit/risk catalog) — consumed as precedent.
- ADR-0023, ADR-0024, ADR-0029 — consumed as binding constraints. Only
  ADR-0029's family allow-list may be widened by this phase, only in 16G, and
  only behind a new ADR (§13H.9 row 3).

## 13H.11 — Out of scope for Phase 16

- Replacing rule-based strategies with opaque ML strategies.
- Automatic feature or strategy search of any unbounded kind.
- A remote or dedicated feature store (§17 deferred; local reuse must first be
  proven insufficient).
- MTF-capable `FeatureSpec` and the contract change it needs (§13G).
- Orderflow, options-derived or cross-asset features (Phases 4B/4C).
- Online/incremental learning, live inference, GPU or distributed training
  (§17).
- A model registry, index or lifecycle field (ADR-0024 condition 5 stands;
  TD-021's repayment is a confirmation, not a construction).
- Making never-promoted research-run blobs portable (TD-022's residual).
- **Lifting ADR-0029's tree/neural runtime-promotion deferral anywhere before
  16G** (TD-029, §13H.12 Q6 = Option B). 16C explicitly may not touch
  `MODEL_FAMILY_ALLOWLIST`; 16G owns the repayment behind its own ADR.
- **Retrofitting PRB-012's planner limits to Signal Research's existing
  `family_planning.py`** (§13H.12 Q8, decided not to). Revisited only on a
  concrete incident or need.
- Deciding Phase 16's sequencing relative to Phase 14B / Sprint 050 (§13H.12
  Q5, deferred by decision).
- Treating any backtest, metric or verdict produced here as live-trading
  approval.

## 13H.12 — Maintainer decisions (all RESOLVED 2026-09-04)

All eight questions this phase was proposed with were **resolved by the
maintainer on 2026-09-04**. Three of them (Q5, Q7, Q8) were resolved *as
deliberate deferrals or refusals* — those are decisions with a recorded
rationale, not questions still hanging.

| # | Question | Resolution (maintainer, 2026-09-04) |
|---|---|---|
| Q1 | Phase number and shape | **APPROVED.** Phase 16, increments 16A–16G, as a new top-level capability track rather than an extension of Phase 10 |
| Q2 | The §13H.0 reconciliation | **APPROVED as recommended.** Sprint 052 stays exactly as planned, unmodified and not widened; the verdict artifact becomes 16A |
| Q3 | Entry condition | **APPROVED with a carve-out.** Phase 16 does not open before Sprint 052 has run — **except 16B**, which may start in parallel. 16A and everything after it still wait |
| Q4 | PRB-020's direction | **Default direction set: port** the Signal Research pattern. Not unconditional — a genuine combinatorics difference found by 16E's design work is surfaced at 16E's Wave 0 |
| Q5 | Sequencing vs. Phase 14B / Sprint 050 | **Deferred, by decision.** Explicitly NOT decided now; revisited once Sprint 052 supplies its Q5 input |
| Q6 | TD-029 scope for 16C | **Option B chosen.** 16C stays narrow; TD-029's repayment moves to 16G. Option A is historical, not a live alternative |
| Q7 | PRB-013's parity tolerances | **Deferred, by decision.** Numeric tolerances are NOT part of this approval; set at 16G's Wave 0 against real suite data, with maintainer sign-off |
| Q8 | PRB-012 back-application to Signal Research | **Not retrofitted, by decision.** PRB-012 closes for the new Strategy Research planner only; the asymmetry is accepted explicitly |

### Q1 — Phase number and shape (RESOLVED: approved)

Phase 16 is a new top-level capability track in §3's Research Capability
Track, with increments 16A–16G numbered independently of sprints.

### Q2 — The Sprint 052 reconciliation (RESOLVED: approved as recommended)

Sprint 052 is **not** widened to also build the verdict artifact; doing so
would break its consumed-not-modified rule. The verdict artifact is 16A.
Sprint 052's own opening remains gated on its own separate maintainer
approval, unchanged by Phase 16's approval.

### Q3 — Entry condition (RESOLVED: approved, with the 16B carve-out)

```text
16B  MAY start in parallel with Sprint 052 — it depends on Sprint 052
     existing as a study, not on its result
16A  and every increment after it wait for Sprint 052 to have ACTUALLY RUN
```

Applied in §13H.0, §13H.1 Dependencies, §13H.2 Dependencies and §13H.10.

### Q4 — PRB-020's direction (RESOLVED: default direction, not a mandate)

Port `research/signal_research/family_planning.py`'s pattern to a new
`research/strategy_research/family_planning.py`, mirroring the Signal Research
design. **Unless** 16E's own design work finds Strategy Research's
combinatorics genuinely differ (multi-model composition vs. single-model
parameter sweeps) — in which case that finding is surfaced **explicitly at
16E's Wave 0** and decided there, never decided unilaterally by an architect
mid-implementation. This is the maintainer's chosen default direction, and
16E's ADR records whichever way it lands.

### Q5 — Sequencing against Phase 14B / Sprint 050 (RESOLVED: deferred)

**This decision is explicitly NOT made now.** It is revisited once Sprint 052
supplies its Q5 input, per Sprint 052's own scope. Phase 16 does not resolve
or pre-empt Phase 14B's sequencing, and no increment of Phase 16 may assume an
answer. Recorded here so the deferral is visible rather than lost.

### Q6 — TD-029 scope for 16C (RESOLVED: Option B)

**16C's scope stays narrow.** Estimator comparison that may gate a strategy is
restricted to promotable families (`sklearn.ridge`, `sklearn.elastic_net`,
`sklearn.logistic` today); tree and neural scorers are research-only and are
**refused at config load time, with a named error**, as a strategy gate.
TD-029's repayment moves to **16G**.

Option A — growing 16C to design the version-pinned joblib/ONNX-style
promotion path in the same increment — was **considered and not chosen**,
because it lands a runtime-deployment-footprint change inside the phase's
central vertical slice. It is recorded as history. Reopening it is a new
maintainer decision.

Accepted cost, stated plainly: 16C cannot claim "the best model gates the
strategy", only "the best promotable model does", and Phase 10B/10C's shipped
tree/neural capability stays unreachable from the workbench until 16G. That
was the trade knowingly made to keep the vertical slice a vertical slice.

Applied in §13H.3, §13H.7, §13H.8, §13H.9 (row 3 and the #2-vs-#3 note),
§13H.11, §13H.13 and the increment-family summary.

### Q7 — PRB-013's accepted parity tolerances (RESOLVED: deferred)

**Numeric tolerances are not part of Phase 16's approval.** They are deferred
to 16G's own Wave 0 planning, once real parity-suite data exists to set
numbers against. A tolerance is a risk acceptance requiring maintainer
sign-off, not an implementation detail an architect picks. 16G may not be
planned as a gate with parity deferred out of it — only the *numbers* are
deferred, never the suite.

### Q8 — PRB-012 back-application to Signal Research (RESOLVED: not retrofitted)

Signal Research's existing `family_planning.py` is **not** retrofitted with
16E's default limits. This is a deliberate decision, consistent with §2.7
("do not introduce infrastructure for hypothetical scale"): Signal Research's
planner has run without a reported runaway incident, so retrofitting now would
change existing working configs' behaviour with no demonstrated trigger.
PRB-012 closes for the **new Strategy Research planner only**; the resulting
asymmetry is noted explicitly as accepted, and is revisited if a concrete
incident or need arises.

## 13H.13 — Registry entries this phase plans to close

Each entry below keeps its current status until the owning increment ships.
This table is the forward index; the annotations in `PROBLEM_REGISTRY.md` /
`TECHNICAL_DEBT.md` are the back-links.

| Entry | Current status | Owning increment | How it is repaid |
|---|---|---|---|
| `PRB-012` — planner limits need defaults | OPEN / MEDIUM | 16E (§13H.5) | Conservative defaults, explicit override, planner tests, no silent pruning — in 16E's completion criteria. Scoped to the new Strategy Research planner only (Q8) |
| `PRB-013` — parity not measurable | OPEN / HIGH | 16G (§13H.7) | Formal parity suite, versioned numeric tolerances (numbers set at 16G's Wave 0, Q7), documented unavoidable differences — the concrete meaning of 16G's "offline/online parity test" step |
| `PRB-020` — Strategy Research lacks family machinery | OPEN / MEDIUM | 16E (§13H.5) | Bounded candidate generation with generated/evaluated/skipped bookkeeping, along Q4's default port direction (or a Wave 0 divergence recorded with rationale) |
| `TD-021` — no model registry | ACCEPTED / MEDIUM | 16C (§13H.3) | Confirmed, against a real config consumer, that content-addressed fingerprint reference suffices; ADR-0024 condition 5 upheld, no registry built |
| `TD-022` — opaque fitted blobs | ACCEPTED / LOW | 16C (§13H.3) | Score path provably depends on no `models/fold_{n}.bin`; promotion branch repaid, never-promoted-blob residual explicitly left open |
| `TD-029` — tree/neural promotion deferred | ACCEPTED / LOW | **16G** (§13H.7) | Q6 = Option B: 16C refuses non-promotable families as strategy gates at config load time; the version-pinned serialization ADR and any allow-list widening belong to 16G |

None of these is closed by approving this phase. Approval only makes the
routes above the *planned* routes.
