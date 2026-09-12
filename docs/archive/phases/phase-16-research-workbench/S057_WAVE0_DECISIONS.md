# Sprint 057 — Wave 0 Decisions

Binding decisions for the Analyst Verdict Artifact (Phase 16, increment 16A).
Date: 2026-09-08.

```text
Status: APPROVED (2026-09-08) — Wave 0 Checklist (D-S057-12) signed off by
        the maintainer (conversational approval). `engineer` may start
        S057-T001.

Basis:  docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md §13H.0, §13H.1,
                §13H.8, §13H.11 — AUTHORITATIVE (APPROVED, maintainer 2026-09-04)
        docs/planning/ROADMAP.md (Status: ACCEPTED) §13H stub
        docs/planning/sprints/SPRINT_057.md
        docs/reference/BTC_PREDICTIVE_STUDY.md — the worked example's real numbers
        docs/planning/sprints/SPRINT_052.md §5 + S052_WAVE0_DECISIONS.md
        docs/planning/sprints/SPRINT_056.md + S056_WAVE0_DECISIONS.md (precedent)
        docs/adr/ADR-0022, ADR-0023 §4/§8, ADR-0024, ADR-0029, ADR-0031
        docs/adr/ADR-0032 (to be drafted with this sprint; Status: Proposed)
        docs/planning/sprints/S044_GATE.md §1.4 — the per-fold vs pooled bar
        src/trading_framework/ as on `main` @ 6a13ff9 (2026-09-08)
```

---

## Inherited locks (do not reopen)

```text
§13H.1 Expected capabilities: the eight-value vocabulary exactly as named; the
        verdict computed from facts the pipeline ALREADY persists, with each
        contributing input recorded alongside it; a declared, VERSIONED rule
        set; applied retrospectively to the Sprint 052 run
§13H.1 Completion criteria: verdict + inputs reproducible from persisted
        artifacts alone; re-running yields the same verdict; the dashboard READS
        the verdict and no verdict logic exists in apps/dashboard; the
        documentation restates ADR-0024's rule unweakened
§13H.1 Out of scope: no change to Sprint 052's scope, instrument or acceptance;
        no Strategy or Robustness verdicts (predictive-run only in v1); NO
        AUTOMATIC CONSEQUENCE of a verdict — nothing promoted, filtered or hidden
§13H.0: Sprint 052 having RUN is 16A's hard entry condition. The Q3
        parallel-start carve-out covers 16B ONLY and never 16A
§13H.8: the dashboard stays read-only over persisted artifacts (no fitting, no
        metric recomputation, no research-engine import, no silent promotion, no
        "validated" claim); leakage guards never relaxed; CI synthetic-only and
        network-free; no registry as a side effect; nothing depends on reloading
        models/fold_{n}.bin; the family allow-list is 16G's alone; a negative
        result is a deliverable; APPROVING A PHASE IS NOT OPENING A SPRINT
ADR-0022: apps/dashboard may not import trading_framework
ADR-0023 §4/§8: leakage guards strengthened or unchanged; CI fixtures synthetic
        only, standard CI network-free
ADR-0024, ADR-0029, ADR-0031: consumed as constraints, not reopened, not amended
research/predictive/CLAUDE.md: no sklearn / xgboost / lightgbm / catboost /
        torch imports; no signal_model, strategy or application import; no
        run_analysis call from the domain package. Enforced by
        tests/unit/test_architecture_boundaries.py
D-S044-08 / SPRINT_041 §4.9: report quality FLAGS are warnings and never become
        a PASS/FAIL verdict. This sprint does not change that and does not
        rename, re-thresholds or repurpose them
```

---

## D-S057-01 — Problem statement

"Is this result any good?" is re-answered by every reader of a run, from a table
of numbers, with no record of what was compared against what. Sprint 052
answered it once, in prose, for one study — correctly, and unrepeatably.

**Sprint 057 ships exactly:** a declared, versioned rule set over facts the
Phase 10 pipeline already persists; one verdict per predictive run from a fixed
eight-value vocabulary; a `verdict.json` sidecar recording the verdict, every
contributing fact, its source artifact, and every rule with the threshold it was
compared against; a deterministic re-evaluation; and the rule set applied
retrospectively to Sprint 052's three real runs as the worked example.

**Not this sprint:** any study, any re-run, any scorer, any promotion, any
Strategy or Robustness verdict, any consequence of a verdict, any CLI command,
any change to the pipeline that produced the artifacts being read.

---

## D-S057-02 — The vocabulary and its exact semantics

Eight values, exactly as §13H.1 names them, in two groups. The **rejection**
group states that the run's headline comparison is not interpretable; the
**outcome** group states what the comparison showed.

```text
OUTCOME group — reached only when NO rejection rule fired

PASS           The model beats RANDOM_PERMUTATION pooled AND on EVERY fold
               (S044_GATE.md §1.4's strict bar). Semantics: "this is the
               strongest shape a Phase 10 result can have; study it next."
               NOT: validated, promotable, tradeable, or approved.
WEAK_PASS      Beats RANDOM_PERMUTATION pooled and on at least two thirds of
               folds, but not on every fold. Semantics: "there is something
               here and it is not stable; a further study is justified,
               a decision is not." This is an EXPECTED, ORDINARY outcome.
INCONCLUSIVE  Either: beats permutation pooled but on fewer than two thirds of
               folds; or a REQUIRED input for a rule is missing from the
               persisted artifacts. Semantics: "the artifacts do not support a
               statement either way." Never a soft FAIL and never a soft PASS.
FAIL           Does not beat RANDOM_PERMUTATION pooled. Semantics: "on this
               comparison, no effect was found." A complete, reportable result.

REJECTION group — dominates the outcome group entirely

REJECTED_OVERFIT           The train/test relationship makes the out-of-sample
                           number uninterpretable (D-S057-06 R1).
REJECTED_LEAKAGE_RISK      A persisted fact indicates the guard configuration or
                           the effect size is inconsistent with a clean
                           walk-forward read (D-S057-06 R2). It asserts RISK,
                           never proven leakage.
REJECTED_LOW_SAMPLE        The evaluated sample is too small — in rows, in folds,
                           or in minority-class rows — for the comparison to mean
                           anything (D-S057-06 R3).
REJECTED_CONCENTRATION     The result rests on one fold or one window rather than
                           on the walk-forward as a whole (D-S057-06 R4).
```

```text
LOCKED  These eight values are the WHOLE vocabulary. No ninth value, no
        severity score, no numeric grade, no colour, no ordering key and no
        "confidence" field is added in v1.
LOCKED  No value in this vocabulary means validated, approved, promotable,
        tradeable, live-ready or safe. REJECTED_* means "not interpretable as
        evidence", never "this model is bad" and never "this model is banned".
LOCKED  WEAK_PASS and INCONCLUSIVE are EXPECTED, COMMON outcomes (§13H.1's
        first named risk). A rule set that cannot reach them on the worked
        example is a defective rule set, not a lucky study.
LOCKED  Exactly ONE verdict per RUN. A study consisting of several runs (as
        Sprint 052's does) gets several verdicts and NO aggregate. The prose
        "split verdict" in BTC_PREDICTIVE_STUDY.md is a human synthesis and is
        NOT what this artifact produces.
```

---

## D-S057-03 — A verdict is a decision aid, never evidence and never an approval

```text
LOCKED  A verdict is a DECISION AID FOR WHAT TO STUDY NEXT — never evidence of a
        live edge, never a promotion approval (ADR-0024's rule, restated, not
        weakened; §13H.1 completion criterion 4).
LOCKED  NOTHING may act on a verdict. No promotion, no filtering, no hiding, no
        default sort order, no ranking, no refusal, no warning banner that
        changes behaviour, no CI gate, no automated notification. A verdict is
        displayed and read; that is all it does (§13H.1 Out of scope).
LOCKED  Strong Phase 10 metrics remain a PRECONDITION for promotion
        consideration and never a verdict that a model should trade (ADR-0024).
        Phase 7 robustness testing remains a separate, unwaived gate that a
        verdict does not touch, weaken or substitute for.
LOCKED  This rule is written into docs/reference/PREDICTIVE_VERDICT.md's FIRST
        section, not a footnote, and is an acceptance criterion (SPRINT_057.md
        §8.4) — not prose an implementer may paraphrase away.
```

---

## D-S057-04 — Module placement (the structural decision)

```text
DECIDED  research/predictive/verdict.py          the DECLARATION and the RULES
         - RunVerdict (the eight-value enum), VerdictRuleSet (frozen, versioned,
           serializable), VerdictFacts, RuleEvaluation, VerdictReport
         - evaluate_verdict(facts, rules) -> VerdictReport : a PURE function
         - polars/numpy/framework contracts only, exactly like metrics.py

DECIDED  application/predictive_research/evaluate_run_verdict.py   the I/O
         - reads the run envelope (PredictiveRunRepository), the dataset
           envelope (PredictiveDatasetRepository) and the optional
           importance.json; extracts facts; evaluates; writes verdict.json
         - mirrors analyze_predictive_run.py's request/result shape exactly,
           including its "never deserializes fitted model blobs" rule

DECIDED  infrastructure/storage/paths.py         one additive path helper
         - predictive_research_run_verdict_path(root, run_id)
           -> runs/<run_id>/verdict.json, alongside metrics.json /
              importance.json / leaderboard.json
```

**Why here, and not somewhere else:**

```text
REASON  The rules are pure functions over already-parsed facts — the same shape
        as research/predictive/metrics.py, which is library-free by convention
        and enforced by an architecture test. A verdict is a statement about
        metrics, and it belongs beside them.
REASON  research/reporting/ already imports research/predictive/. Putting the
        verdict in reporting would either invert that layering or force the
        application layer to import a reporting module to persist a
        non-report artifact. Layering stays one-directional:
        reporting -> predictive, application -> both, dashboard -> neither.
REASON  The I/O split is the one 16B already established and ADR-0031 already
        fixed: the domain package declares and computes, the application
        package reads, resolves and persists.

REJECTED  A new top-level research/analyst/ (or research/verdict/) module.
          v1 is predictive-run-only by §13H.1's own Out of scope; a top-level
          module would advertise a Strategy/Robustness generality this increment
          explicitly does not ship, and would invite 16D to extend a contract
          that has been exercised against exactly one study. Extraction to a
          neutral module is a later, evidence-driven decision — recorded here so
          it is a decision and not an omission.
REJECTED  Extending research/reporting/predictive/quality.py. Its flags are
          WARNINGS that D-S044-08 explicitly forbids from becoming a PASS/FAIL
          verdict. Growing a verdict inside that module would break that rule by
          proximity even if the code stayed separate.
REJECTED  Any placement inside apps/dashboard/, apps/cli/, or a script. §13H.1
          forbids the first outright; the other two are not where contracts live.
LOCKED    research/predictive/verdict.py may not import research.reporting,
          application, infrastructure, signal_model, strategy, or any ML library.
          Enforced by tests/unit/test_architecture_boundaries.py, which is not
          to be amended to permit a new import.
```

---

## D-S057-05 — Which persisted fact each rule reads, and from where

Every fact below is already written by the unmodified Phase 10 pipeline. **No
new field is persisted by the pipeline in this sprint** (SPRINT_057.md §5).

```text
FACT                          SOURCE ARTIFACT                       USED BY
primary metric name           metrics.json task_type                 all
  (roc_auc for CLASSIFICATION, spearman_ic for REGRESSION — the SAME convention
   as research/reporting/predictive/quality.py::primary_metric_name; the verdict
   does NOT define a second one)
pooled MODEL primary          metrics.json pooled.MODEL.statistical  O1-O4, R1, R2
pooled RANDOM_PERMUTATION     metrics.json pooled.RANDOM_PERMUTATION O1-O4
  primary                        .statistical
per-fold MODEL primary        metrics.json folds.<id>.MODEL          O1-O3, R4
per-fold RANDOM_PERMUTATION   metrics.json folds.<id>.RANDOM_        O1-O3, R4
  primary                        PERMUTATION
per-fold train_primary /      metrics.json fold_primary.<id>         R1
  test_primary / primary_gap     (OPTIONAL — see D-S057-07)
fold count                    metrics.json folds (key count)          R3, R4
per-fold TEST row counts      dataset manifest.json fold_summary      R3, R4
                                 .per_fold[].TEST
role counts (TRAIN/TEST/      dataset manifest.json fold_summary      R2
  PURGED/EMBARGOED)              .role_counts
label horizon, embargo_span,  dataset manifest.json study_spec        R2
  test_span, fold mode
exclusion counts              dataset manifest.json exclusion_counts  R3 (recorded)
sample provenance             dataset manifest.json sample_provenance recorded only
minority-class share          dataset features.parquet, TEST-role     R3
  (CLASSIFICATION only)          label column (Finding 3)
per-fold feature importance   importance.json (OPTIONAL)              RECORDED ONLY
run identity                  run manifest.json run_id,               recorded
                                 dataset_fingerprint, estimator_spec,
                                 library, library_version,
                                 framework_version
```

```text
LOCKED  Reading dataset features.parquet is permitted and is the ONLY way
        minority-class share is obtainable today (Finding 3);
        analyze_predictive_run already reads the same envelope. Persisting a
        minority-class count into the dataset manifest would be a Phase 10
        manifest change and is FORBIDDEN here.
LOCKED  No fitted model blob is opened, ever — no joblib.load, no
        models/fold_*.bin read (ADR-0029/TD-022's boundary, unchanged).
LOCKED  predictions.parquet is NOT read. Every fact above is available without
        it, and reading it would make the verdict a second metrics computation
        rather than a read of the metrics that were persisted.
LOCKED  Every fact recorded in verdict.json carries the artifact it came from.
        "Reproducible from the persisted artifacts alone" (§13H.1) means a
        reader can point at the file each number was read from.
LOCKED  Feature-importance facts are RECORDED and drive NO rule in v1. §13H.1
        names importance sanity as a contributing input; recording it satisfies
        that, and scoring it from one study would be exactly the over-fitting of
        the rule set to one result that §13H.1's third risk warns about.
```

---

## D-S057-06 — The v1 rule set: `verdict_rules.v1`

Declared here in full. The implementation is a transcription of this table; a
value in code that differs from a value here is a defect.

### Rejection rules (evaluated first, in this order)

```text
R2  REJECTED_LEAKAGE_RISK   fires if ANY of:
      (a) study_spec.split.embargo_span < the label horizon
          (an embargo shorter than the label window cannot protect the fold);
      (b) role_counts PURGED == 0 AND EMBARGOED == 0 while the label horizon
          is greater than zero (guards configured to do nothing);
      (c) an IMPLAUSIBILITY CEILING on the pooled MODEL primary:
              CLASSIFICATION  roc_auc      >= 0.75
              REGRESSION      |spearman_ic| >= 0.30
          Semantics: at these effect sizes on a purged walk-forward over
          financial data, "look again at the label and the features" is the
          honest reading. It asserts RISK, never proven leakage.

R3  REJECTED_LOW_SAMPLE     fires if ANY of:
      (a) any fold's TEST row count < 30            (min_test_rows)
      (b) fold count < 3                            (min_folds)
      (c) CLASSIFICATION only: pooled TEST minority-class share < 0.10
                                                    (min_minority_class_share)

R4  REJECTED_CONCENTRATION  fires if ANY of:
      (a) one fold holds > 0.60 of all TEST rows    (max_single_fold_test_share)
      (b) fold count >= 3, pooled baseline delta > 0, and EXACTLY ONE fold beats
          RANDOM_PERMUTATION  (the pooled edge rests on a single window)

R1  REJECTED_OVERFIT        fires if BOTH:
      (a) train_primary > test_primary on EVERY fold where both are present
          (unanimity — a rejection is a strong claim and v1 requires one), AND
      (b) median over folds of (train_primary - test_primary)
              > 1.0 x effect_size_pooled            (overfit_gap_ratio)
          where effect_size_pooled = |pooled MODEL primary - neutral|,
              neutral = 0.5 for CLASSIFICATION (roc_auc),
              neutral = 0.0 for REGRESSION      (spearman_ic)
```

### Outcome rules (reached only if no rejection rule fired)

```text
baseline_delta = pooled MODEL primary - pooled RANDOM_PERMUTATION primary
fold_win_rate  = folds where MODEL primary > RANDOM_PERMUTATION primary
                 / folds with both present

O1  PASS          baseline_delta > 0 AND fold_win_rate == 1.0
O2  WEAK_PASS     baseline_delta > 0 AND fold_win_rate >= 0.6667  (min_fold_win_rate)
O3  INCONCLUSIVE  baseline_delta > 0 AND fold_win_rate <  0.6667
O4  FAIL          baseline_delta <= 0
```

```text
LOCKED  RULE ORDER IS FIXED AND PART OF THE CONTRACT: R2, R3, R4, R1, then
        O1..O4. The FIRST rejection that fires determines the verdict; ALL
        rules are still evaluated and ALL results are recorded in verdict.json,
        so a reader sees everything that fired, not only the winner.
REASON  R2 first: a leaky comparison makes every other statistic
        uninterpretable. R3 next: an inadequate sample makes concentration and
        gap statistics noise. R4 before R1: a single-window result's train/test
        gap is not the interesting fact about it.
LOCKED  Every threshold above lives in ONE frozen VerdictRuleSet object carrying
        the version string "verdict_rules.v1", which is serialized into every
        verdict it produces. Changing any number requires a new version string
        and is a one-file diff (§13H.1's mitigation for threshold tuning).
LOCKED  No caller may pass custom thresholds. There is no override file, no
        per-study rule set and no keyword argument that changes a threshold in
        v1. The rule set is a constant, not a configuration surface.
LOCKED  R1's thresholds are RELATIVE by deliberate design (SPRINT_057.md
        Finding 1): the existing absolute report flag (max_train_test_gap =
        0.20) would NOT have flagged Sprint 052's tree run, whose gaps are
        0.027-0.147 and which BTC_PREDICTIVE_STUDY.md §5 correctly calls the
        classic overfit signature. The verdict must catch that case or it is
        not worth persisting.
LOCKED  The three thresholds that coincide with PredictiveReportQualityRules
        (min_test_rows, max_single_fold_test_share, min_minority_class_share)
        are DECLARED INDEPENDENTLY and the verdict never imports
        research/reporting/. A report-warning threshold changing must not
        silently change a persisted verdict. The resulting duplication is a
        knowingly accepted shortcut, logged as LOW technical debt in S057-T007
        (SPRINT_057.md Finding 2), not repaid here.
```

---

## D-S057-07 — The verdict artifact: format, determinism, and missing inputs

```text
LOCKED  PATH        user_data/workspace/research/predictive_research/runs/
                    <run_id>/verdict.json  — a SIDECAR beside metrics.json.
                    Nothing already in the run directory is rewritten, moved,
                    re-derived or re-persisted.
LOCKED  CONTENT     schema_version; rule_set_version ("verdict_rules.v1"); the
                    full serialized rule set (every threshold, by name);
                    run_id; dataset_id; dataset_fingerprint; the verdict; every
                    extracted fact with its value and its SOURCE ARTIFACT; and
                    every rule with (rule_id, fired, observed, threshold,
                    inputs_used) — including rules that did not fire and rules
                    that could not be evaluated.
LOCKED  NO WALL-CLOCK FIELD. verdict.json carries no created_at and no
        duration. This is what makes §13H.1's completion criterion 2
        ("re-running yields the same verdict") assertable as BYTE EQUALITY of
        the file rather than as a value comparison with an excluded key. The
        run directory already dates the run.
LOCKED  DETERMINISM. evaluate_verdict is pure: no randomness, no seed, no clock,
        no environment read, no ordering that depends on dict iteration order
        (facts and rule evaluations are emitted in the declared order).
LOCKED  MISSING INPUTS. If a rule's required fact is absent from the persisted
        artifacts, the rule is recorded as NOT EVALUATED with the missing input
        named, and the verdict is INCONCLUSIVE. It is never silently skipped,
        never treated as not-fired, and never allowed to produce PASS.
        (Finding 4: fold_primary is optional in metrics.json, so R1 is the
        realistic case.)
LOCKED  verdict.json lives under user_data/ and is NEVER committed to git
        (ADR-0002; D-S052-08's posture, unchanged).
```

---

## D-S057-08 — What consumes a verdict, and what may not

```text
LOCKED  The dashboard may READ verdict.json and DISPLAY its contents verbatim.
        It may not compute, re-derive, threshold, infer, default, colour-code
        by severity, sort by, filter by, or synthesize a verdict — including
        when the file is absent, in which case it renders "no verdict recorded"
        (§13H.1 completion criterion 3; ADR-0022 already blocks the import that
        would make anything else possible).
LOCKED  The existing report quality FLAGS stay exactly as they are, in both the
        framework module and the dashboard-local mirror: same codes, same
        thresholds, same "warnings, never a verdict" semantics (D-S044-08). The
        verdict does not replace, subsume, rename or re-threshold them, and this
        sprint changes neither file.
LOCKED  No other consumer is built. No leaderboard ordering, no CLI, no report
        panel, no promotion input, no notification. 16D and 16G may consume the
        artifact later; this sprint ships the artifact and one read-only
        display.
```

---

## D-S057-09 — The dashboard display is descopable, and the maintainer chooses

```text
DECISION REQUIRED (maintainer, at D-S057-12):
        KEEP    S057-T006 in this sprint — a minimal read-only display, so
                §13H.1's completion criterion 3 is met in both halves here.
        DEFER   the display to 16D (§13H.4), which owns the dashboard surface.
                16A then meets criterion 3's negative half only ("no verdict
                logic exists in apps/dashboard" — trivially true, nothing there
                changes), and 16D inherits the positive half.
LOCKED  Either way, NO verdict logic, threshold or fallback enters
        apps/dashboard/ (§13H.1, D-S057-08). The choice is about WHERE the
        display lands, never about whether the dashboard may compute.
LOCKED  T006 is first in the sprint's descope order regardless of this choice.
```

---

## D-S057-10 — The worked example, and its verdicts PRE-DECLARED

Sprint 052's three persisted runs are the worked example (§13H.1: "applied
retrospectively to the Sprint 052 run"). The verdicts D-S057-06's rules are
expected to produce are recorded **here, in Wave 0, before any implementation
exists** — so that a threshold cannot be adjusted afterwards to reach a nicer
answer.

```text
run f7ac893d54ae6b69   REGRESSION / sklearn.ridge     EXPECTED: WEAK_PASS
  baseline_delta = 0.020566 - (-0.004792) = +0.025358  > 0
  fold_win_rate  = 5/6 = 0.8333                        >= 0.6667, < 1.0
  R1: train > test on folds 1 and 5 only, NOT unanimous -> does not fire
  R2: embargo 1d vs 1h horizon (24x); PURGED=60, EMBARGOED>0;
      |spearman_ic| 0.0206 < 0.30                       -> does not fire
  R3: TEST = 43,200 rows on every fold; 6 folds; REGRESSION (no class rule)
                                                        -> does not fire
  R4: each fold holds 1/6 of TEST rows; 5 folds win, not 1
                                                        -> does not fire

run faa6983acd03f846   BINARY / sklearn.logistic       EXPECTED: PASS
  baseline_delta = 0.544182 - 0.498606 = +0.045576      > 0
  fold_win_rate  = 6/6 = 1.0                            == 1.0
  R1: train > test on fold 1 only, NOT unanimous        -> does not fire
  R2: pooled roc_auc 0.5442 < 0.75; guards as above     -> does not fire
  R3: TEST rows and fold count as above; minority-class share to be READ from
      the persisted TEST labels — a 0.0-threshold binary label on 1h forward
      return is expected near 0.5, comfortably above 0.10, BUT this is the one
      fact in the worked example not already tabulated in
      BTC_PREDICTIVE_STUDY.md and is therefore VERIFIED AT T005, NOT ASSUMED
  R4: as above                                          -> does not fire

run 6d2842b647cd4097   REGRESSION / lightgbm.regressor EXPECTED: REJECTED_OVERFIT
  R2, R3 evaluated first and do not fire (same guards, same dataset; pooled
      |spearman_ic| 0.0239 < 0.30)
  R4: 4 of 6 folds win, not exactly 1; TEST evenly split -> does not fire
  R1(a): train > test on ALL SIX folds
         0.1478>0.0342, 0.0504>0.0187, 0.0720>-0.0209,
         0.1035>0.0768, 0.1384>-0.0085, 0.1863>0.0547   -> unanimous
  R1(b): gaps 0.1136, 0.0317, 0.0930, 0.0267, 0.1469, 0.1316
         median = (0.0930 + 0.1136)/2 = 0.1033
         effect_size_pooled = |0.023922 - 0.0| = 0.023922
         0.1033 > 1.0 x 0.023922                        -> fires
  NOTE: the existing absolute report flag (gap > 0.20) would NOT have fired on
        any of these folds. This run is exactly why R1 is relative (Finding 1).
```

```text
LOCKED  These three expectations are FROZEN by this document. If the implemented
        rule set produces a different verdict for any run, that is a
        STOP-AND-REPORT finding naming the fact and the threshold responsible —
        NOT a reason to change a threshold, a rule, a rule order, or an
        expectation. Resolving a mismatch is a maintainer decision.
LOCKED  The rule set was designed with knowledge of these numbers. That is
        unavoidable — 16A has exactly one study behind it (§13H.1's third risk)
        — and it is stated here rather than hidden: the mitigation is that both
        the thresholds AND the expected outcomes are frozen before
        implementation, so any later movement in either is a reviewable diff.
LOCKED  These verdicts change NOTHING about Sprint 052's own conclusions. Its
        split result stands exactly as written; a verdict is a second, coarser
        read of the same artifacts, not a re-judgement of the study.
LOCKED  Producing three PASS verdicts would be evidence the rule set is
        DEFECTIVE (§13H.1: WEAK_PASS and INCONCLUSIVE must be reachable and
        common), not evidence the study was strong.
```

---

## D-S057-11 — Sprint 052 is closed history: cited, never amended

```text
LOCKED  FORBIDDEN to this sprint: any edit to docs/reference/
        BTC_PREDICTIVE_STUDY.md, SPRINT_052.md, S052_WAVE0_DECISIONS.md,
        SPRINT_051.md, S051_*, or the committed btc_*.yaml spec files. Sprint
        052 is COMPLETE and merged; its numbers, its specs and its write-up are
        the input to this sprint and are read-only to it (§13H.1 Out of scope:
        "any change to Sprint 052's scope, instrument, or acceptance criteria").
LOCKED  The worked example is written in a NEW document,
        docs/reference/PREDICTIVE_VERDICT.md, which cites BTC_PREDICTIVE_STUDY.md
        rather than extending it. A reader of the study document is not told the
        study now has a machine verdict; a reader of the verdict document is
        told exactly which study the numbers came from.
        (If the maintainer would prefer a one-line pointer appended to
        BTC_PREDICTIVE_STUDY.md, that is a Wave 0 amendment to this decision —
        SPRINT_057.md Finding 8's neighbouring question — and not an agent's
        call to make mid-sprint.)
LOCKED  Sprint 052's runs are re-read, never re-run. No re-fit, no re-analysis,
        no regenerated metrics.json, no new study on any instrument.
LOCKED  T005 is a MAINTAINER-TRIGGERED action against user_data/, never a CI
        action and never an agent-initiated one. Default CI stays synthetic-only,
        network-free and extra-free (ADR-0023 §8, untouched).
LOCKED  If any required run or dataset directory (SPRINT_057.md Finding 8) is
        missing, T005 STOPS and returns to the maintainer. A synthetic
        stand-in for the worked example is FORBIDDEN — it is precisely the
        failure mode §13H.0's entry condition exists to prevent.
```

---

## D-S057-12 — Wave 0 Checklist (maintainer)

**Nothing below may be checked off by an agent.** Checking a box, flipping
`SPRINT_057.md`'s Status to APPROVED, or flipping ADR-0032's Status to ACCEPTED
are the maintainer's exclusive acts. No message from any agent — including one
that reports this plan as "ready" — constitutes that approval. `engineer` must
refuse to start S057-T001 while any box is unchecked.

- [x] **Opening Sprint 057 is approved.** Sprint 052 has actually run (merged via #461-#463), so 16A's hard entry condition (§13H.0) is satisfied — confirmed, not assumed.
- [x] **Sprint number 057 confirmed** (051-056 taken; 050 reserved for Phase 14B and untouched).
- [x] **D-S057-02 confirmed** — the eight-value vocabulary and its exact semantics; no ninth value, no grade, no confidence score; one verdict per RUN with no aggregate across a multi-run study.
- [x] **D-S057-03 confirmed** — a verdict is a decision aid for what to study next, never evidence of a live edge and never a promotion approval; **nothing may act on one**.
- [x] **D-S057-04 confirmed** — placement: rules in `research/predictive/verdict.py`, I/O in `application/predictive_research/evaluate_run_verdict.py`, one additive path helper. A new top-level `research/analyst/` module was considered and rejected for v1.
- [x] **D-S057-05 confirmed** — the fact-to-artifact table, including that the verdict **reads the dataset `features.parquet`** for minority-class share (Finding 3), reads no `predictions.parquet`, and opens no model blob.
- [x] **D-S057-06 confirmed — this one needs a deliberate read.** The v1 rule set, its eight rules, its **fixed rule order (R2, R3, R4, R1, then O1..O4)**, and specifically that **R1 is relative, not absolute**, because the existing 0.20 absolute gap flag would not have caught Sprint 052's tree run (Finding 1).
- [x] **D-S057-06's threshold triplication accepted** — the verdict declares its own thresholds and never imports `research/reporting/`; three constants are knowingly duplicated and logged as LOW technical debt, not repaid here (Finding 2).
- [x] **D-S057-07 confirmed** — `verdict.json` as a sidecar, its content, **no wall-clock field**, byte-identical re-evaluation, and the missing-input rule (a missing required fact yields `INCONCLUSIVE`, never a silent `PASS`).
- [x] **D-S057-08 confirmed** — the dashboard reads and displays only; the existing report quality flags are unchanged in both files; no other consumer is built.
- [x] **D-S057-09 decided — KEPT.** S057-T006 (the read-only dashboard display) stays in this sprint, in its minimal form (verdict string, rule-set version, recorded inputs — zero new constants, zero arithmetic). Not deferred to 16D.
- [x] **D-S057-10 confirmed — the pre-declared verdicts.** `f7ac893d54ae6b69` -> `WEAK_PASS`, `faa6983acd03f846` -> `PASS`, `6d2842b647cd4097` -> `REJECTED_OVERFIT`, frozen before implementation; a mismatch is a STOP, never a threshold change.
- [x] **The Sprint 052 run and dataset directories listed in SPRINT_057.md Finding 8 exist on the maintainer's machine** — confirmed by inspection (independently verified 2026-09-08: all three `runs/<id>/` and both `datasets/<id>/` directories present under `user_data/workspace/research/predictive_research/`).
- [x] **D-S057-11 confirmed** — Sprint 052 is closed history: cited, never amended; the worked example lands in a new `docs/reference/PREDICTIVE_VERDICT.md`; T005 is maintainer-triggered and never a CI action.
- [x] **ADR-0032 decided — ACCEPTED path.** 16A ships three hard-to-reverse things (vocabulary, sidecar schema, module placement) that 16C/16D/16G will depend on; §13H.9's silence on an ADR for 16A is "not anticipated," not "not permitted." ADR-0032 is written and carried to `ACCEPTED` as S057-T001.
- [x] **Sprint 057 scope approved as 7 tasks, 4 waves**, shipping **no study, no re-run, no scorer, no promotion, no CLI command, no new dependency** and **no consequence of a verdict**.
- [x] **Branch `sprint/analyst-verdict-artifact` approved**, to be cut from `main` at its then-current head.

Approved-by: Project Maintainer, 2026-09-08 (conversational approval: full Wave 0
checklist and the four judgment-call findings — D-S057-09 dashboard scope,
ADR-0032, threshold-triplication debt, D-S057-11 worked-example placement —
presented with recommendations; confirmed with explicit "Zgadzam się z
rekomendacjami").

Once every box is checked and ADR-0032 is `ACCEPTED` (or explicitly declined),
the first task for `engineer` is **S057-T001** (ADR draft/acceptance
follow-through and Wave 0 amendments, **docs only, no code**) on
`docs/predictive-verdict-adr`, cut from `sprint/analyst-verdict-artifact`.
