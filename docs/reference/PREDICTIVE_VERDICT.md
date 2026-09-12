# Predictive Run Verdict Artifact (Sprint 057, Phase 16 Increment 16A)

**A verdict is a decision aid for what to study next — never evidence of a
live edge and never a promotion approval.** Nothing is promoted, filtered,
sorted, ranked, hidden, or refused because of a verdict. No consumer may
change behaviour based on one — no CI gate, no default sort order, no
warning banner that alters what a reader sees next. Strong Phase 10 metrics
remain a *precondition* for promotion consideration and never a verdict that
a model should trade (`docs/adr/ADR-0024-machine-learned-state-promotion.md`).
Phase 7 robustness testing remains a separate, unwaived gate that a verdict
does not touch, weaken, or substitute for. This restates ADR-0024's rule; it
does not soften it, and it is Sprint 057's own acceptance criterion, not
prose an implementer or a later increment may paraphrase away.

This document is the reference for `research/predictive/verdict.py` (the
vocabulary, the frozen `verdict_rules.v1` rule set, and the pure evaluation
cascade) and `application/predictive_research/evaluate_run_verdict.py` (the
I/O layer that reads a run's persisted artifacts and writes the
`verdict.json` sidecar). The binding decision record is
`docs/adr/ADR-0032-predictive-run-verdict-artifact.md`; this document
restates it in narrower, implementation-facing form and adds the worked
example. Where the two disagree, the ADR governs.

---

## 1. The eight-value vocabulary

Exactly eight values, in two groups. No ninth value, no severity score, no
numeric grade, no colour, no ordering key, and no "confidence" field exists
in v1. **Exactly one verdict per RUN** — a study of several runs (as Sprint
052's is) gets several verdicts and no aggregate; a prose synthesis across
runs, such as `BTC_PREDICTIVE_STUDY.md`'s "split result," is a human
judgement this artifact does not produce.

```text
OUTCOME group — reached only when no rejection rule fired

PASS            Beats RANDOM_PERMUTATION pooled AND on every fold
                (S044_GATE.md §1.4's strict bar). "The strongest shape a
                Phase 10 result can have; study it next." NOT: validated,
                promotable, tradeable, or approved.
WEAK_PASS       Beats RANDOM_PERMUTATION pooled and on at least two-thirds
                of folds, but not every fold. "There is something here and
                it is not stable; a further study is justified, a decision
                is not." An EXPECTED, ORDINARY outcome, not an exotic one.
INCONCLUSIVE    Beats permutation pooled but on fewer than two-thirds of
                folds, OR a required input for a rule is missing from the
                persisted artifacts. "The artifacts do not support a
                statement either way." Never a soft FAIL, never a soft
                PASS.
FAIL            Does not beat RANDOM_PERMUTATION pooled. "On this
                comparison, no effect was found." A complete, reportable
                result, not a failure of the pipeline.

REJECTION group — dominates the outcome group entirely

REJECTED_OVERFIT        The train/test relationship makes the out-of-sample
                         number uninterpretable.
REJECTED_LEAKAGE_RISK    A persisted fact indicates the guard configuration
                         or the effect size is inconsistent with a clean
                         walk-forward read. Asserts RISK, never proven
                         leakage.
REJECTED_LOW_SAMPLE      The evaluated sample is too small — in rows, in
                         folds, or in minority-class rows — for the
                         comparison to mean anything.
REJECTED_CONCENTRATION   The result rests on one fold or one window rather
                         than the walk-forward as a whole.
```

No value in this vocabulary means validated, approved, promotable,
tradeable, live-ready, or safe. `REJECTED_*` means "not interpretable as
evidence," never "this model is bad" and never "this model is banned."
`WEAK_PASS` and `INCONCLUSIVE` are expected, common outcomes — a rule set
that cannot reach them on the worked example (§4 below) is a defective rule
set, not a lucky study.

---

## 2. The v1 rule set — `verdict_rules.v1`

Every threshold below lives in one frozen, serializable `VerdictRuleSet`
object (`research/predictive/verdict.py`), carrying the version string
`"verdict_rules.v1"`, which is itself serialized into every verdict it
produces. Changing any number requires a new version string and is a
one-file diff. No caller may pass custom thresholds — there is no override
file, no per-study rule set, and no keyword argument that changes a
threshold in v1; callers evaluate against the module-level constant
`VERDICT_RULES_V1`.

### Rejection rules (evaluated first, in fixed order)

```text
R2  REJECTED_LEAKAGE_RISK   fires if ANY of:
      (a) embargo_span < the label horizon;
      (b) role_counts PURGED == 0 AND EMBARGOED == 0 while the label
          horizon is greater than zero;
      (c) an implausibility ceiling on the pooled MODEL primary metric:
          CLASSIFICATION roc_auc >= 0.75 (classification_roc_auc_ceiling),
          REGRESSION |spearman_ic| >= 0.30 (regression_spearman_ic_ceiling).
          Asserts risk, never proven leakage.

R3  REJECTED_LOW_SAMPLE     fires if ANY of:
      (a) any fold's TEST row count < 30                 (min_test_rows)
      (b) fold count < 3                                 (min_folds)
      (c) CLASSIFICATION only: pooled TEST minority-class
          share < 0.10                          (min_minority_class_share)

R4  REJECTED_CONCENTRATION  fires if ANY of:
      (a) one fold holds > 0.60 of all TEST rows
                                             (max_single_fold_test_share)
      (b) fold count >= 3, pooled baseline delta > 0, and exactly one fold
          beats RANDOM_PERMUTATION (the pooled edge rests on one window)

R1  REJECTED_OVERFIT        fires if BOTH:
      (a) train_primary > test_primary on every fold where both are
          present (unanimity — a rejection is a strong claim); AND
      (b) median over folds of (train_primary - test_primary)
          > 1.0 x effect_size_pooled              (overfit_gap_ratio)
          where effect_size_pooled = |pooled MODEL primary - neutral|,
          neutral = 0.5 for CLASSIFICATION (roc_auc),
                    0.0 for REGRESSION (spearman_ic)
```

### Outcome rules (reached only if no rejection rule fired)

```text
baseline_delta = pooled MODEL primary - pooled RANDOM_PERMUTATION primary
fold_win_rate  = folds where MODEL primary > RANDOM_PERMUTATION primary
                 / folds with both present

O1  PASS          baseline_delta > 0 AND fold_win_rate == 1.0
O2  WEAK_PASS     baseline_delta > 0 AND fold_win_rate >= 0.6667
                                                    (min_fold_win_rate)
O3  INCONCLUSIVE  baseline_delta > 0 AND fold_win_rate <  0.6667
O4  FAIL          baseline_delta <= 0
```

### Rule evaluation order, and why it is fixed

**`R2, R3, R4, R1`, then `O1..O4`. The first rejection rule that fires
determines the verdict, but every rule is still evaluated and every result
is recorded** in `verdict.json` (`VerdictReport.evaluations`, in this
order), so a reader sees everything that fired, not only the winner:

- **R2 first** — a leaky comparison makes every other statistic
  uninterpretable.
- **R3 next** — an inadequate sample makes concentration and gap statistics
  noise.
- **R4 before R1** — a single-window result's train/test gap is not the
  interesting fact about it.

### R1 is relative to the run's own pooled effect size, not absolute

This is the rule set's central, hardest-to-reverse design choice. The
existing report-quality flag (`research/reporting/predictive/quality.py`'s
`LARGE_TRAIN_TEST_GAP`, `max_train_test_gap = 0.20`, absolute) would **not**
have flagged Sprint 052's real tree-family overfitting case: its per-fold
gaps (0.027–0.147) are all individually below 0.20, yet dwarf that run's own
pooled effect size (0.024), and `BTC_PREDICTIVE_STUDY.md` §5 nevertheless
correctly calls it "the classic overfit signature." An absolute gap
threshold is blind at these effect sizes. R1 is therefore expressed relative
to the run's own pooled effect size — a rule that cannot catch the one real
overfitting case in this framework's own history is not worth persisting.
§4 below shows R1 firing exactly where it should.

### The missing-input rule

If a rule's required fact is absent from the persisted artifacts (the
realistic case: `fold_primary` is an optional field in `metrics.json`,
needed by R1), the rule is recorded as **not evaluated**, with the missing
input named (`RuleEvaluation.evaluated = False`, `missing_input=...`). It is
never silently skipped, never treated as not-fired, and never allowed to
produce `PASS`. If no rejection rule fires but one could not be evaluated
because of a missing input, the overall verdict is `INCONCLUSIVE`, naming
that missing input — the same value used when the outcome rules themselves
cannot be evaluated (e.g. no fold has both a MODEL and a RANDOM_PERMUTATION
result).

### Accepted threshold triplication (technical debt, not repaid here)

`min_test_rows=30`, `max_single_fold_test_share=0.60`, and
`min_minority_class_share=0.10` already exist in
`PredictiveReportQualityRules` (`research/reporting/predictive/quality.py`)
and its non-importing dashboard-local mirror
(`apps/dashboard/.../catalog/predictive_quality.py`, ADR-0022). The verdict
rule set declares a **third**, independent copy, and `verdict.py` never
imports `research/reporting/` — a report-warning threshold changing must
not silently change a persisted verdict. The same reasoning extends to one
naming convention, not just three numbers: `verdict.py`'s
`_primary_metric_name` / `_primary_metric_value` reproduce (do not import)
`quality.py`'s `primary_metric_name` / `primary_metric_value` convention
exactly (`roc_auc` for `CLASSIFICATION`, `spearman_ic` for `REGRESSION`),
guarded only by a parity test added during T003's QA
(`test_verdict.py`), not by a shared source of truth. This is logged as
`TD-033` in `docs/planning/TECHNICAL_DEBT.md` (LOW priority, not repaid
here).

---

## 3. The `verdict.json` sidecar

```text
PATH      user_data/workspace/research/predictive_research/runs/<run_id>/
          verdict.json — a sidecar beside metrics.json. Nothing already in
          the run directory is rewritten, moved, re-derived or
          re-persisted.

CONTENT   schema_version ("predictive_run_verdict.v1"); rule_set_version
          ("verdict_rules.v1"); the full serialized rule set (every
          threshold, by name); run_id; dataset_id; dataset_fingerprint;
          the verdict; every extracted fact with its value and its source
          artifact; and every rule with (rule_id, fired, observed,
          threshold, source, evaluated, missing_input) — including rules
          that did not fire and rules that could not be evaluated.

NO WALL-CLOCK FIELD. verdict.json carries no created_at and no duration.
This is what makes "re-running yields the same verdict" assertable as byte
equality of the file, not a value comparison with an excluded key. The run
directory already dates the run.

DETERMINISM. Evaluation is pure: no randomness, no seed, no clock, no
environment read, no ordering that depends on dict iteration order —
facts and rule evaluations are emitted in the declared order, and the
sidecar is written with sort_keys=True.

verdict.json lives under user_data/ and is never committed to git
(ADR-0002).
```

`research/predictive/verdict.py` declares and computes (`RunVerdict`,
`VerdictRuleSet`, `VerdictFacts`, `RuleEvaluation`, `VerdictReport`,
`extract_verdict_facts`, `evaluate_verdict`) — pure, library-free, no import
of `research.reporting`, `application`, `infrastructure`, `signal_model`,
`strategy`, or any ML library, enforced by
`tests/unit/test_architecture_boundaries.py`.
`application/predictive_research/evaluate_run_verdict.py` is the I/O layer:
it reads the run envelope (`PredictiveRunRepository`), the dataset envelope
(`PredictiveDatasetRepository`), and the optional `importance.json`; never
deserializes a fitted model blob; and writes `verdict.json` via
`predictive_research_run_verdict_path` (`infrastructure/storage/paths.py`).

---

## 4. The worked example — Sprint 052's three real runs

`S057_WAVE0_DECISIONS.md` D-S057-10 froze the expected verdict for each of
Sprint 052's three persisted runs **before** `verdict.py` existed. S057-T005
(maintainer-executed, 2026-09-08) evaluated `verdict_rules.v1` against the
real, persisted `manifest.json` / `metrics.json` / `importance.json` for
each run and its dataset manifest — no re-run, no re-analysis, no fitted
model blob opened:

```text
run_id             family              verdict            expected   match
f7ac893d54ae6b69   sklearn.ridge       WEAK_PASS          WEAK_PASS  YES
faa6983acd03f846   sklearn.logistic    PASS               PASS       YES
6d2842b647cd4097   lightgbm.regressor  REJECTED_OVERFIT   REJECTED_  YES
                                                           OVERFIT
```

**All three verdicts matched D-S057-10's pre-declared expectations exactly —
no STOP-and-report finding, no threshold was touched.**

- `f7ac893d54ae6b69` (ridge / regression) fires `O2` only: beats
  `RANDOM_PERMUTATION` pooled with a 5/6 fold win rate — not every fold —
  matching `BTC_PREDICTIVE_STUDY.md`'s own finding that this pass loses one
  fold.
- `faa6983acd03f846` (logistic / binary) fires `O1` only: beats
  `RANDOM_PERMUTATION` pooled and on every one of six folds.
- `6d2842b647cd4097` (lightgbm / regression) fires **both** `R1`
  (`REJECTED_OVERFIT` — unanimous train-above-test across all six folds,
  median gap 0.1033 exceeding the pooled effect size 0.023922) **and** `O2`
  (would-be `WEAK_PASS` on the raw win-rate numbers alone, 4/6 folds). `R1`
  wins, because rejection rules are evaluated before the pass/fail rules in
  the fixed cascade order (`R2, R3, R4, R1, O1..O4`) — this is the concrete
  mechanism the fixed order exists to enforce: it stops a technically-higher
  pooled number from overriding a real overfitting signature. This is
  exactly the case R1's relative design (§2 above) exists to catch, and it
  is a genuinely illustrative example of why the order is fixed and not
  left to whichever rule a caller checks first.

Re-evaluation determinism was checked directly: the ridge run's
`verdict.json` was re-evaluated a second time and its raw bytes compared
byte-for-byte identical to the first write.

**These verdicts change nothing about Sprint 052's own conclusions**, which
stand exactly as written in `docs/reference/examples/BTC_PREDICTIVE_STUDY.md` — cited
here, never amended. A verdict is a second, coarser, mechanical read of the
same persisted artifacts, reproducing by rule what `BTC_PREDICTIVE_STUDY.md`
§5 already reported by hand; it discovers nothing new about that study, and
it authorizes nothing about it either (§1 above).

---

## 5. What reads a verdict, and what may not

The dashboard (`apps/dashboard`) may read `verdict.json` and display its
contents verbatim: the verdict value, the rule-set version, and the
recorded inputs. It may not compute, re-derive, threshold, infer, default,
colour-code by severity, sort by, or filter by a verdict — including when
the file is absent, in which case it renders "no verdict recorded" rather
than a computed one. `apps/dashboard` still imports no `trading_framework`
symbol (ADR-0022); no verdict logic, threshold constant, or fallback exists
anywhere under it. The existing report-quality flags
(`research/reporting/predictive/quality.py` and its dashboard-local mirror)
are unchanged, unrenamed, and unrethresholded — they remain warnings, and
this artifact does not replace, subsume, or become them.

16C, 16D and 16G consume this artifact as readers once they exist; none of
them may extend the vocabulary, the sidecar schema, or the module placement
without a new or amending ADR (ADR-0032 Follow-up).

---

## 6. References

- `docs/adr/ADR-0032-predictive-run-verdict-artifact.md` — the binding
  contract this document restates.
- `docs/archive/phases/phase-16-research-workbench/SPRINT_057.md`, `S057_WAVE0_DECISIONS.md` — the
  sprint plan, findings, and Wave 0 decisions (D-S057-01 through -12).
- `docs/reference/examples/BTC_PREDICTIVE_STUDY.md` — the Sprint 052 study the
  worked example applies its rule set to, retrospectively; cited, never
  amended.
- `src/trading_framework/research/predictive/verdict.py`,
  `src/trading_framework/application/predictive_research/evaluate_run_verdict.py`
  — the implementation.
- `src/trading_framework/research/predictive/CLAUDE.md` — the module's
  import and metric conventions, including the verdict entry.
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — the promotion-
  precondition rule this document's §1 restates, unweakened.
- `docs/planning/TECHNICAL_DEBT.md` TD-033 — the threshold/naming-
  convention triplication accepted as LOW technical debt.
