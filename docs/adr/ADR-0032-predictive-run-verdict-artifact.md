# ADR-0032 — Predictive Run Verdict Artifact: Vocabulary, Rule Set, and Sidecar Schema

## Status

ACCEPTED (2026-09-08)

Approved-by: Project Maintainer, 2026-09-08 (conversational approval, recorded
in `docs/planning/sprints/S057_WAVE0_DECISIONS.md` D-S057-12: "ADR-0032
decided — ACCEPTED path", part of the full Wave 0 Checklist sign-off —
"Zgadzam się z rekomendacjami"). This ADR's content is a transcription of
`S057_WAVE0_DECISIONS.md` D-S057-02 through D-S057-08, D-S057-10, already
individually confirmed at Wave 0; acceptance here executes that decision, it
does not make a new one. `SPRINT_057.md` Wave 1 (`S057-T002`) may start once
this document and its index entry are merged.

Drafted for Sprint 057 (Phase 16, increment 16A — Analyst Verdict Artifact),
2026-09-08, as `S057-T001`.

## Context

Phase 10's predictive pipeline (Sprints 039–044) already persists everything a
reader needs to judge a run: `metrics.json` (pooled and per-fold `MODEL` /
`RANDOM_PERMUTATION` statistics, `fold_primary`, task type), `manifest.json`
(run identity, dataset fingerprint, estimator), `importance.json` (per-fold
permutation importance), and the dataset's own manifest (`study_spec`,
`fold_summary`, `exclusion_counts`, `sample_provenance`). Nothing turns those
facts into a judgement. Sprint 052 answered "is this result any good?" once,
by hand, in prose (`docs/reference/BTC_PREDICTIVE_STUDY.md`) — correctly, and
unrepeatably. Every other reader of a run re-answers the same question from a
table of numbers, with no record of what was compared against what.

`docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.1 names the fix: a
declared, versioned rule set producing one of eight verdict values per run,
computed only from facts the pipeline already persists, applied retrospectively
to Sprint 052's runs as the worked example. §13H.9's list of ADRs anticipated
for Phase 16 does not include one for 16A — five are named, for 16B/16C/16G/16E
— but as `SPRINT_057.md` Finding 6 states, that list is what was *anticipated*
when the phase was approved, not a ceiling on what is *permitted*. 16A ships
three things that are hard to reverse once real `verdict.json` sidecars exist
on disk and other increments start reading them:

1. **A fixed eight-value vocabulary** that 16C, 16D and 16G will consume as
   readers, not redesign.
2. **A persisted sidecar schema**, because changing its shape after real
   verdicts are written invalidates every one of them.
3. **A module-placement decision**, because the import boundaries
   `tests/unit/test_architecture_boundaries.py` enforces are expensive to
   redraw once other code depends on where a symbol lives.

Two further constraints, load-bearing for the decisions below:

- **The existing report-quality gap flag is measurably wrong for this
  purpose.** `research/reporting/predictive/quality.py` flags
  `LARGE_TRAIN_TEST_GAP` at an absolute `max_train_test_gap = 0.20`. Sprint
  052's tree run (`6d2842b647cd4097`) has per-fold train/test gaps of
  **0.027–0.147** — every one below 0.20 — and `BTC_PREDICTIVE_STUDY.md` §5
  nevertheless correctly calls it "the classic overfit signature": train beats
  test on all six folds, and the gaps "dwarf the pooled effect size being
  measured (0.024)". An absolute threshold is blind at these effect sizes.
- **ADR-0024 already settled what a metric may and may not authorize.** A
  strong Phase 10 result is a *precondition* for promotion consideration, never
  itself a promotion approval. A verdict artifact sits closer to "evidence a
  human might act on" than a report warning does, which makes restating that
  boundary — not weakening it — a requirement of this ADR, not an
  afterthought.

## Decision

### 1. The vocabulary — eight values, exactly, no ninth

```text
OUTCOME group — reached only when no rejection rule fired
  PASS            Beats RANDOM_PERMUTATION pooled AND on every fold
                  (S044_GATE.md §1.4's strict bar). "The strongest shape a
                  Phase 10 result can have; study it next." Not: validated,
                  promotable, tradeable, or approved.
  WEAK_PASS       Beats RANDOM_PERMUTATION pooled and on at least two-thirds
                  of folds, but not every fold. "There is something here and
                  it is not stable; a further study is justified, a decision
                  is not." An EXPECTED, ORDINARY outcome, not an exotic one.
  INCONCLUSIVE    Beats permutation pooled but on fewer than two-thirds of
                  folds, OR a required input for a rule is missing from the
                  persisted artifacts. "The artifacts do not support a
                  statement either way." Never a soft FAIL, never a soft PASS.
  FAIL            Does not beat RANDOM_PERMUTATION pooled. "On this
                  comparison, no effect was found." A complete, reportable
                  result, not a failure of the pipeline.

REJECTION group — dominates the outcome group entirely
  REJECTED_OVERFIT           The train/test relationship makes the
                             out-of-sample number uninterpretable.
  REJECTED_LEAKAGE_RISK      A persisted fact indicates the guard
                             configuration or the effect size is inconsistent
                             with a clean walk-forward read. Asserts RISK,
                             never proven leakage.
  REJECTED_LOW_SAMPLE        The evaluated sample is too small — in rows, in
                             folds, or in minority-class rows — for the
                             comparison to mean anything.
  REJECTED_CONCENTRATION     The result rests on one fold or one window
                             rather than the walk-forward as a whole.
```

These eight values are the whole vocabulary. No ninth value, no severity
score, no numeric grade, no colour, no ordering key, no "confidence" field is
added in v1. No value means validated, approved, promotable, tradeable,
live-ready or safe; `REJECTED_*` means "not interpretable as evidence," never
"this model is bad" and never "this model is banned." `WEAK_PASS` and
`INCONCLUSIVE` are expected, common outcomes — a rule set that cannot reach
them on the worked example is a defective rule set, not a lucky study.
**Exactly one verdict per RUN.** A study of several runs (as Sprint 052's is)
gets several verdicts and no aggregate; the prose "split verdict" in
`BTC_PREDICTIVE_STUDY.md` is a human synthesis, not what this artifact
produces.

### 2. The v1 rule set — `verdict_rules.v1`

Eight rules, one frozen version. Every threshold below lives in one frozen,
serializable `VerdictRuleSet` object carrying the version string
`"verdict_rules.v1"`, serialized into every verdict it produces. Changing any
number requires a new version string and is a one-file diff. No caller may
pass custom thresholds — there is no override file, no per-study rule set, no
keyword argument that changes a threshold in v1.

**Fixed evaluation order: `R2, R3, R4, R1`, then `O1..O4`.** The first
rejection rule that fires determines the verdict, but **every rule is still
evaluated and every result is recorded** in `verdict.json`, so a reader sees
everything that fired, not only the winner. R2 is checked first because a
leaky comparison makes every other statistic uninterpretable; R3 next, because
an inadequate sample makes concentration and gap statistics noise; R4 before
R1, because a single-window result's train/test gap is not the interesting
fact about it.

```text
R2  REJECTED_LEAKAGE_RISK   fires if ANY of:
      (a) embargo_span < the label horizon;
      (b) role_counts PURGED == 0 AND EMBARGOED == 0 while the label horizon
          is greater than zero;
      (c) an implausibility ceiling on the pooled MODEL primary metric:
          CLASSIFICATION roc_auc >= 0.75, REGRESSION |spearman_ic| >= 0.30.
          Asserts risk, never proven leakage.

R3  REJECTED_LOW_SAMPLE     fires if ANY of:
      (a) any fold's TEST row count < 30 (min_test_rows);
      (b) fold count < 3 (min_folds);
      (c) CLASSIFICATION only: pooled TEST minority-class share < 0.10
          (min_minority_class_share).

R4  REJECTED_CONCENTRATION  fires if ANY of:
      (a) one fold holds > 0.60 of all TEST rows (max_single_fold_test_share);
      (b) fold count >= 3, pooled baseline delta > 0, and exactly one fold
          beats RANDOM_PERMUTATION.

R1  REJECTED_OVERFIT        fires if BOTH:
      (a) train_primary > test_primary on every fold where both are present
          (unanimity — a rejection is a strong claim); AND
      (b) median over folds of (train_primary - test_primary)
          > 1.0 x effect_size_pooled (overfit_gap_ratio), where
          effect_size_pooled = |pooled MODEL primary - neutral|,
          neutral = 0.5 for CLASSIFICATION (roc_auc), 0.0 for REGRESSION
          (spearman_ic).

baseline_delta = pooled MODEL primary - pooled RANDOM_PERMUTATION primary
fold_win_rate  = folds where MODEL primary > RANDOM_PERMUTATION primary
                 / folds with both present

O1  PASS          baseline_delta > 0 AND fold_win_rate == 1.0
O2  WEAK_PASS     baseline_delta > 0 AND fold_win_rate >= 0.6667
O3  INCONCLUSIVE  baseline_delta > 0 AND fold_win_rate <  0.6667
O4  FAIL          baseline_delta <= 0
```

**R1 is relative to the run's own pooled effect size, not an absolute
threshold — by deliberate design.** The existing absolute report flag
(`max_train_test_gap = 0.20`) would not have flagged Sprint 052's tree run,
whose per-fold gaps (0.027–0.147) are individually small but dwarf that run's
own pooled effect size (0.024). At these effect sizes, an absolute gap
threshold is blind; a rule that cannot catch the one real overfitting case in
this framework's own history is not worth persisting. This is the ADR's
central, hardest-to-reverse rule, and it is the sprint's answer to §13H.1's
named risk of "threshold tuning to produce nicer verdicts": the rule and its
expected effect on real data were fixed *before* implementation (see §3
below), specifically because Finding 1 identified this failure mode in the
existing, weaker mechanism.

**Missing-input rule.** If a rule's required fact is absent from the
persisted artifacts (the realistic case: `fold_primary` is an optional field
in `metrics.json`, needed by R1), the rule is recorded as not evaluated with
the missing input named, and the verdict is `INCONCLUSIVE`. It is never
silently skipped, never treated as not-fired, and never allowed to produce
`PASS`.

**Accepted threshold triplication (technical debt, not repaid here).** Two
threshold sets already exist for a subset of these numbers:
`PredictiveReportQualityRules` (`research/reporting/predictive/quality.py`)
and its non-importing dashboard-local mirror
(`apps/dashboard/.../catalog/predictive_quality.py`, ADR-0022). The verdict
rule set is a third, independent declaration of `min_test_rows=30`,
`max_single_fold_test_share=0.60`, and `min_minority_class_share=0.10`. The
verdict never imports `research/reporting/`, because a report-warning
threshold changing must not silently change a persisted verdict — but this
means the same three numbers now live in three places. This is a knowingly
accepted, LOW-priority shortcut. It is logged in `TECHNICAL_DEBT.md` by
`S057-T007`, with a future consolidation increment as its repayment trigger,
and it is **not** consolidated by this ADR.

### 3. The worked example's verdicts are frozen before implementation

`S057_WAVE0_DECISIONS.md` D-S057-10 records, hand-verified against Sprint
052's three persisted runs, the verdict each is expected to produce, *before*
`research/predictive/verdict.py` exists:

```text
f7ac893d54ae6b69  (REGRESSION / sklearn.ridge)      EXPECTED: WEAK_PASS
faa6983acd03f846  (BINARY / sklearn.logistic)        EXPECTED: PASS
6d2842b647cd4097  (REGRESSION / lightgbm.regressor)  EXPECTED: REJECTED_OVERFIT
```

If the implemented rule set produces a different verdict for any of these
runs when `S057-T005` runs it, that is a STOP-and-report finding naming the
fact and threshold responsible — never a reason to change a threshold, a rule,
the rule order, or the expectation itself. Producing three `PASS` verdicts
would be evidence the rule set is defective, not evidence the study was
strong.

### 4. The `verdict.json` sidecar

```text
PATH      user_data/workspace/research/predictive_research/runs/<run_id>/
          verdict.json — a sidecar beside metrics.json. Nothing already in
          the run directory is rewritten, moved, re-derived or re-persisted.

CONTENT   schema_version; rule_set_version ("verdict_rules.v1"); the full
          serialized rule set (every threshold, by name); run_id; dataset_id;
          dataset_fingerprint; the verdict; every extracted fact with its
          value and its source artifact; and every rule with
          (rule_id, fired, observed, threshold, inputs_used) — including
          rules that did not fire and rules that could not be evaluated.

NO WALL-CLOCK FIELD. verdict.json carries no created_at and no duration. This
is what makes "re-running yields the same verdict" assertable as byte
equality of the file, rather than a value comparison with an excluded key.
The run directory already dates the run.

DETERMINISM. Evaluation is pure: no randomness, no seed, no clock, no
environment read, no ordering that depends on dict iteration order — facts
and rule evaluations are emitted in the declared order. Same artifacts on
disk, byte-identical verdict.json.

verdict.json lives under user_data/ and is never committed to git (ADR-0002).
```

### 5. Module placement

```text
research/predictive/verdict.py               the DECLARATION and the RULES
  RunVerdict (the eight-value enum), VerdictRuleSet (frozen, versioned,
  serializable), VerdictFacts, RuleEvaluation, VerdictReport,
  evaluate_verdict(facts, rules) -> VerdictReport : a PURE function.
  polars/numpy/framework-contract types only, exactly like metrics.py.

application/predictive_research/evaluate_run_verdict.py       the I/O
  Reads the run envelope (PredictiveRunRepository), the dataset envelope
  (PredictiveDatasetRepository) and the optional importance.json; extracts
  facts; evaluates; writes verdict.json. Mirrors analyze_predictive_run.py's
  request/result shape exactly, including its "never deserializes fitted
  model blobs" rule.

infrastructure/storage/paths.py               one additive path helper
  predictive_research_run_verdict_path(root, run_id)
    -> runs/<run_id>/verdict.json, alongside metrics.json / importance.json /
       leaderboard.json.
```

**Why here:**

- The rules are pure functions over already-parsed facts — the same shape as
  `research/predictive/metrics.py`, which is library-free by convention and
  enforced by an architecture test. A verdict is a statement about metrics,
  and belongs beside them.
- `research/reporting/` already imports `research/predictive/`. Putting the
  verdict in `reporting` would either invert that layering or force the
  application layer to import a reporting module to persist a non-report
  artifact. Layering stays one-directional: `reporting -> predictive`,
  `application -> both`, `dashboard -> neither`.
- The I/O split (domain declares and computes; application reads, resolves,
  persists) is the one ADR-0031 already established for 16B. This ADR follows
  the same seam rather than inventing a second one.

**A new top-level `research/analyst/` (or `research/verdict/`) module was
considered and rejected.** v1 is predictive-run-only, by §13H.1's own explicit
Out-of-scope. A top-level module would advertise a Strategy/Robustness
generality this increment does not ship, and would invite later increments to
extend a contract that has been exercised against exactly one study —
premature generalization beyond what §13H.1 asks for. Extraction to a neutral
module is a later, evidence-driven decision, recorded here as considered and
declined rather than left as a silent omission.

Extending `research/reporting/predictive/quality.py` was also considered and
rejected: its flags are warnings that the project's existing convention
(report-quality flags never become a PASS/FAIL verdict) explicitly forbids
turning into a verdict. Growing a verdict inside that module would break that
rule by proximity even if the code stayed physically separate. Placement
inside `apps/dashboard/`, `apps/cli/`, or a script was rejected outright:
§13H.1 forbids verdict logic in the dashboard, and the other two are not
where a contract like this lives.

`research/predictive/verdict.py` may not import `research.reporting`,
`application`, `infrastructure`, `signal_model`, `strategy`, or any ML
library, enforced by `tests/unit/test_architecture_boundaries.py`, which is
not to be amended to permit a new import.

### 6. A verdict is a decision aid, never evidence and never an approval

This restates ADR-0024's rule; it does not weaken it.

A verdict is a decision aid for what to study next — never evidence of a live
edge, never a promotion approval. Nothing may act on a verdict: no promotion,
no filtering, no hiding, no default sort order, no ranking, no refusal, no
warning banner that changes behaviour, no CI gate, no automated notification.
A verdict is displayed and read; that is all it does. Strong Phase 10 metrics
remain a precondition for promotion consideration and never a verdict that a
model should trade (ADR-0024). Phase 7 robustness testing remains a separate,
unwaived gate that a verdict does not touch, weaken, or substitute for. This
rule is written into `docs/reference/PREDICTIVE_VERDICT.md`'s first section,
not a footnote, and is a sprint acceptance criterion, not prose an
implementer may paraphrase away.

## Alternatives Considered

**A neutral, run-type-agnostic `research/analyst/` module for all verdict
kinds (predictive, Strategy, Robustness) from the start.** More architecturally
tidy on paper — one abstraction instead of a predictive-only one that might
need generalizing later. Rejected: §13H.1 scopes v1 to predictive runs only,
and building a general abstraction exercised by exactly one concrete case is
speculative generality the sprint's own findings warn against. If a second
verdict kind is built later, generalizing then is a reviewable, evidence-driven
decision rather than a guess made now.

**An absolute train/test-gap threshold for R1, matching the existing report
flag.** Simpler — one fewer derived quantity (the pooled effect size) to
compute and record. Rejected outright: `SPRINT_057.md` Finding 1 demonstrates
this would not have caught Sprint 052's real overfitting case, which is the
sprint's central design finding. Shipping a rule known not to catch the one
case it exists to catch would make the artifact worse than no artifact.

**Importing `research/reporting/predictive/quality.py`'s thresholds directly
into the verdict rule set, instead of declaring a third copy.** Would remove
the triplication named in Finding 2. Rejected for v1: a report-quality
threshold is explicitly a warning that may move for display reasons; coupling
a persisted, versioned verdict to it would mean a report-flag change silently
changes historical verdicts' meaning, or forces a verdict rule-set version bump
for an unrelated reporting change. The duplication is accepted knowingly as
LOW technical debt instead, with its own repayment trigger.

**A numeric confidence score or severity grade alongside the verdict.** Would
let a reader rank runs without reading the facts. Rejected: §13H.1's first
named risk is the vocabulary becoming an authority, and a numeric score is
exactly the kind of "aggregate quality" (D-S057-02) that invites acting on a
verdict automatically rather than reading it.

## Consequences

### Positive

- "Is this result any good?" becomes a reproducible read of a persisted,
  diffable file instead of a re-derivation by each reader.
- The rule set catches the one real overfitting case in the framework's own
  history that the existing absolute gap flag misses (Finding 1), because R1
  is relative to the run's own effect size.
- The vocabulary, sidecar schema and module placement are fixed once, in one
  document, before any implementation exists — later increments (16C, 16D,
  16G) can build against a contract rather than a moving target.
- `WEAK_PASS` and `INCONCLUSIVE` are structurally as reachable as `PASS`,
  which keeps the artifact from becoming a rubber stamp.
- Nothing in `apps/dashboard/` may compute a verdict; ADR-0022's import
  boundary and this ADR's placement decision together make that structurally
  true, not just documented.

### Negative

- **Three sets of near-identical thresholds now exist** (report flags,
  dashboard mirror, verdict rule set). A future drift between them is
  possible and is only visible because each is independently versioned and
  serialized — this is accepted as LOW technical debt, not resolved here.
- **The rule set was designed from a single study.** Every threshold and every
  expected verdict was calibrated against Sprint 052's three runs. A second,
  differently-shaped study could expose a rule that is an artifact of this one
  case. Mitigated, not eliminated, by freezing the rule set's version and the
  worked-example's expected outcomes before implementation, so any later
  correction is a reviewable, versioned diff.
- **v1 is deliberately thin**: eight rules, no feature-importance scoring, no
  Strategy or Robustness coverage. A real research question that needs a rule
  this version does not have gets `INCONCLUSIVE` or no verdict at all, not a
  best-effort guess.
- A missing-input `INCONCLUSIVE` (the `fold_primary`-absent case) means older
  runs written before this sprint may never reach a decisive verdict without
  being re-run — which this ADR does not authorize.

### Neutral

- `MODEL_FAMILY_ALLOWLIST`, promotion, the Phase 10 pipeline's build/run/
  analyze behaviour, and every leakage guard are untouched.
- CI stays synthetic-only and network-free (ADR-0023 §8); the retrospective
  application to Sprint 052's real runs is a maintainer-triggered action
  against `user_data/`, never a CI action.

## Follow-up

- `S057-T002`–`T004` implement exactly this vocabulary, rule set, and sidecar
  schema; a deviation found during implementation is a defect in the
  implementation, not license to redesign this ADR.
- `S057-T005` (maintainer-executed) applies the frozen rule set to Sprint
  052's three real runs and compares against §3's pre-declared expectations. A
  mismatch is a STOP-and-report, never a threshold adjustment.
- `S057-T007` logs the threshold-triplication debt (§2) in
  `TECHNICAL_DEBT.md` as LOW priority, with a future consolidation increment
  as its trigger, and writes `docs/reference/PREDICTIVE_VERDICT.md`.
- 16C, 16D and 16G consume this artifact as readers once it exists; none of
  them may extend the vocabulary, the sidecar schema, or the module placement
  without a new or amending ADR.
- A `research/analyst/` (or similarly-named) generalization for Strategy or
  Robustness verdicts remains a later, evidence-driven decision — not
  authorized, not scheduled, by this ADR.

## References

- `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.0, §13H.1, §13H.8,
  §13H.9, §13H.11
- `docs/planning/sprints/SPRINT_057.md` — Findings 1–8, §5 boundaries, task
  breakdown
- `docs/planning/sprints/S057_WAVE0_DECISIONS.md` — D-S057-02 through
  D-S057-10, D-S057-12 (the maintainer approval this ADR's Status traces to)
- `docs/reference/BTC_PREDICTIVE_STUDY.md` — the Sprint 052 result this ADR's
  worked example applies its rule set to, retrospectively
- `docs/planning/sprints/SPRINT_052.md`, `S052_WAVE0_DECISIONS.md` — the runs
  and artifacts the worked example reads; cited, never amended
- `docs/adr/ADR-0022-repository-top-level-layout.md` — `apps/dashboard` may
  not import `trading_framework`, which is why the dashboard reads a
  persisted verdict rather than computing one
- `docs/adr/ADR-0023-predictive-research-boundary.md` §4, §8 — leakage guards
  and synthetic-only, network-free CI, both untouched
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — the promotion-
  precondition rule this ADR restates, unweakened
- `docs/adr/ADR-0029-promoted-predictive-artifact.md` — the layering
  precedent (domain declares/computes, application resolves/persists,
  infrastructure touches libraries)
- `docs/adr/ADR-0031-predictive-sample-spec-and-task.md` — the immediately
  prior ADR in `research/predictive/`, same declare/resolve seam
- `src/trading_framework/research/predictive/CLAUDE.md` — the module's import
  and metric conventions
- `src/trading_framework/research/reporting/predictive/quality.py` — the
  existing report-quality flags this ADR's rule set deliberately does not
  import from
- `docs/planning/TECHNICAL_DEBT.md` — destination of the threshold-
  triplication entry (`S057-T007`)
