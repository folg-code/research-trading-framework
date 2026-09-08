# Sprint 057 — Analyst Verdict Artifact (Phase 16, Increment 16A)

## Metadata

```text
Sprint: 057
Phase: Phase 16 — Quant Research Workbench; increment 16A (Analyst Verdict
       Artifact)
Status: APPROVED (2026-09-08) — Wave 0 Checklist signed off
        (S057_WAVE0_DECISIONS.md D-S057-12). `engineer` may start S057-T001.
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: Phase 10 pipeline (Sprints 039-044, COMPLETE, CONSUMED),
            Sprint 041 (report quality flags — the fact-extraction precedent),
            Sprint 044 / S044_GATE.md §1.4 (the per-fold vs pooled bar),
            **Sprint 052 HAS RUN** (merged to `main` via #461-#463) — the hard
            entry condition for 16A (§13H.0 / §13H.12 Q3; the parallel-start
            carve-out covers 16B only and never 16A),
            Sprint 056 / ADR-0031 (merged via #457) — consumed as context, not
            required by any task here
Does NOT depend on: 16C, 16D, 16E, 16F, 16G — none of which exist. Nothing in
            this sprint may assume a scorer, a promotion gate, a strategy
            family or a Quant Lab dashboard.
Depended On By: 16D (displays the verdict), 16C (a verdict on the scoring run),
            16G (analyst diagnostics feed the promotion gate)
Sprint Branch: sprint/analyst-verdict-artifact (cut from `main` at its
            then-current head; not yet cut)
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/analyst-verdict-artifact (never `main` until sprint integration)
Wave 0 decisions: docs/planning/sprints/S057_WAVE0_DECISIONS.md
ADR: docs/adr/ADR-0032-predictive-run-verdict-artifact.md (to be drafted as
            S057-T001, `Status: Proposed`; its acceptance gates Wave 1). Phase
            16 §13H.9 did NOT anticipate an ADR for 16A — see Finding 6; the
            maintainer confirms or declines it at Wave 0.
Numbering: verified against docs/planning/sprints/. 051-056 are taken; 050 stays
            RESERVED for Phase 14B and is not taken here. 057 is the first free
            number. ADR-0032 is the first free ADR number (highest existing:
            ADR-0031).
Architecture Sources:
  - docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md §13H.0, §13H.1, §13H.8,
    §13H.11 — AUTHORITATIVE for this increment (APPROVED, maintainer,
    2026-09-04). This sprint turns §13H.1 into a plan; it does not redesign it.
  - docs/planning/ROADMAP.md (Status: ACCEPTED) §13H stub
  - docs/reference/BTC_PREDICTIVE_STUDY.md — the Sprint 052 result this sprint
    must apply its rule set to retrospectively (the worked example)
  - docs/planning/sprints/SPRINT_052.md + S052_WAVE0_DECISIONS.md — the runs,
    their artifacts, and the FORBIDDEN/ALLOWED posture this sprint adapts
  - docs/adr/ADR-0023 §4, §8 — leakage guards; synthetic-only, network-free CI
  - docs/adr/ADR-0024 — a strong metric is a precondition, never a verdict that
    a model should trade. Restated, never weakened.
  - docs/adr/ADR-0022 — repository layout; `apps/dashboard` may not import
    `trading_framework`, which is why the dashboard must READ a persisted
    verdict rather than compute one
  - src/trading_framework/research/predictive/CLAUDE.md — the module's import
    and metric conventions
  - src/trading_framework/research/reporting/predictive/quality.py — the
    existing report quality flags (Sprint 041, D-S044-08): warnings, explicitly
    never a PASS/FAIL verdict. 16A does not change that; it adds a separate,
    versioned artifact.
```

---

## 0. Slice choice — a contract sprint whose only evidence is one real study

16A ships **a persisted judgement contract**, not a research result and not a
capability that makes anything faster. That shapes the plan in four ways:

- **The rule set is declared before it is run.** Wave 0 freezes the thresholds
  *and* the three verdicts they are expected to produce on the Sprint 052 runs.
  Implementation then either reproduces those verdicts or reports a mismatch —
  it never re-tunes a threshold to reach them. This is the sprint's answer to
  §13H.1's "threshold tuning to produce nicer verdicts" risk, and it is the one
  device that makes a rule set designed from a single study defensible.
- **The vocabulary must not become an authority.** `WEAK_PASS` and
  `INCONCLUSIVE` are the expected common outcomes, and the worked example is
  designed to demonstrate exactly that: of Sprint 052's three runs, one is
  expected to be `PASS`, one `WEAK_PASS`, and one a rejection. A rule set that
  produced three `PASS`es would be evidence the rules are wrong, not that the
  study was good.
- **Deliberately few rules.** Eight verdict values, eight rules, one version.
  Feature-importance sanity is *recorded* alongside the verdict but does not
  drive it in v1 (§13H.1's "keep the first version deliberately conservative and
  few-ruled").
- **The dashboard is a reader, never a computer.** ADR-0022 already forbids
  `apps/dashboard` from importing `trading_framework`; §13H.1 forbids verdict
  logic there. Those two point the same way: a JSON sidecar.

---

## 1. Sprint Goal

```text
persisted run artifacts (all already written by the unmodified Phase 10 pipeline)
  runs/<run_id>/metrics.json        pooled + per-fold MODEL and RANDOM_PERMUTATION,
                                    fold_primary train/test/gap, task_type, seed
  runs/<run_id>/manifest.json       run_id, dataset_fingerprint, estimator, library
  runs/<run_id>/importance.json     per-fold permutation importance (recorded, not scored)
  datasets/<dataset_id>/manifest.json  study_spec, fold_summary, exclusion_counts,
                                    sample_provenance, time range
  datasets/<dataset_id>/features.parquet  TEST labels (minority-class share only)
      |
      v
  declared, VERSIONED verdict rule set  (verdict_rules.v1 — frozen in Wave 0)
      |
      v
  runs/<run_id>/verdict.json        one verdict + every fact that produced it,
                                    every rule evaluated, every threshold compared
      |
      v
  dashboard DISPLAYS it             no thresholds, no arithmetic, no verdict logic
```

Success: "is this result any good?" stops being re-answered by each reader, and
starts being a reproducible read of a persisted file whose rules are diffable.

---

## 2. In scope

- [ ] The verdict vocabulary as a declared enum with exact, written semantics:
      `PASS`, `WEAK_PASS`, `INCONCLUSIVE`, `FAIL`, `REJECTED_OVERFIT`,
      `REJECTED_LEAKAGE_RISK`, `REJECTED_LOW_SAMPLE`, `REJECTED_CONCENTRATION`.
- [ ] A versioned, frozen, serializable rule set (`verdict_rules.v1`) declaring
      every threshold, with the version recorded in every verdict it produces.
- [ ] Fact extraction from persisted artifacts only, with each contributing
      input recorded alongside the verdict (value, threshold, comparison, and
      the artifact it came from).
- [ ] A pure, deterministic evaluation function: same artifacts -> byte-identical
      verdict payload.
- [ ] `verdict.json` persisted as a sidecar in the run directory, plus its path
      helper.
- [ ] An application-layer entry point that reads the run and dataset envelopes
      (never a model blob) and writes the sidecar.
- [ ] Synthetic-fixture tests reaching **every** vocabulary value, including
      each `REJECTED_*` one.
- [ ] **Retrospective application to Sprint 052's three real runs**
      (`f7ac893d54ae6b69`, `faa6983acd03f846`, `6d2842b647cd4097`) as the worked
      example, compared against Wave 0's pre-declared expectations.
- [ ] `docs/reference/PREDICTIVE_VERDICT.md`: the vocabulary, the rule set, the
      worked example, and the ADR-0024 restatement.
- [ ] A read-only dashboard display of the persisted verdict (descopable —
      Finding 5).

## 3. Out of scope

- **Verdicts for Strategy or Robustness runs.** The first version is
  predictive-run only (§13H.1 Out of scope). No neutral, run-type-agnostic
  abstraction is built "for later".
- **Any automatic consequence of a verdict.** Nothing is promoted, filtered,
  hidden, ranked, sorted or refused because of one.
- **Any change to Sprint 052's scope, instrument, specs, numbers or write-up.**
  Its study document is read, cited, and not edited (D-S057-11, Finding 8).
- **Any change to `research/reporting/predictive/quality.py`'s flags or
  thresholds**, or to the dashboard-local mirror's thresholds. Report flags stay
  warnings (D-S044-08); the verdict is a separate artifact.
- **Any change to the Phase 10 pipeline's build/run/analyze behaviour**:
  `build_predictive_dataset`, `run_predictive_research`, `analyze_predictive_run`,
  `compare_predictive_runs`, `metrics.py`, `splitting.py`, `matrix.py`,
  `importance.py` (§5).
- Re-running, re-fitting or re-analyzing any Sprint 052 study. The verdict reads
  what is on disk.
- A CLI subcommand for the verdict (`trading-cli research verdict`) — named as a
  follow-up, not built here (Finding 7).
- A rule set v2, a threshold override file, per-study rule customization, or any
  mechanism for a caller to pass its own thresholds at a call site.
- Any new dependency, extra, estimator family, component or sample kind.

---

## 4. Findings — read before Wave 0 is signed off

### Finding 1 — the existing train/test-gap flag would MISS the exact overfitting the study reported

`research/reporting/predictive/quality.py` flags `LARGE_TRAIN_TEST_GAP` at
`max_train_test_gap = 0.20`, absolute. Sprint 052's tree pass
(`6d2842b647cd4097`) has per-fold gaps of **0.027-0.147** — every one of them
*below* 0.20 — and `BTC_PREDICTIVE_STUDY.md` §5 nevertheless calls it "the
classic overfit signature", correctly: train is above test on **all six folds**
and the gaps "dwarf the pooled effect size being measured (0.024)".

An absolute gap threshold is blind at these effect sizes. The verdict's overfit
rule is therefore **relative and directional** (D-S057-06): unanimous
train-above-test across folds, *and* a median gap larger than the pooled effect
size. Verified by hand against all three Sprint 052 runs in D-S057-10 — it fires
on the tree run and on neither baseline run.

This is the sprint's central design finding. If it is wrong, the rule set is
wrong, and that is a Wave 0 conversation, not an implementation detail.

### Finding 2 — three sets of thresholds would exist, in three places

There are already two: `PredictiveReportQualityRules`
(`research/reporting/predictive/quality.py`) and its deliberate,
non-importing mirror in
`apps/dashboard/src/dashboard_app/catalog/predictive_quality.py` (ADR-0022).
The verdict rule set is a third.

D-S057-04 decides it stays a third — the verdict declares its own frozen,
versioned thresholds and never imports `research/reporting/`, because a report
*warning* threshold changing must not silently change a persisted *verdict*.
Three numeric values are duplicated by that choice (`min_test_rows=30`,
`max_single_fold_test_share=0.60`, `min_minority_class_share=0.10`). That
duplication is a knowingly accepted shortcut: `engineer` logs it in
`TECHNICAL_DEBT.md` (LOW) as part of T007, with "a future consolidation
increment" as its repayment trigger. It is not repaid here.

### Finding 3 — minority-class share is not in any JSON; it needs the dataset parquet

The dashboard-local mirror already documents this: "`SEVERE_CLASS_IMBALANCE` is
always skipped: minority-class counts are not persisted anywhere the listing
reads." The framework-side flag computes it from `test_labels`, which come from
the labelled dataset, not from a manifest.

Consequence for 16A: the verdict computer must read the **dataset envelope**
(`features.parquet` via `PredictiveDatasetRepository`), exactly as
`analyze_predictive_run` already does for its TRAIN baselines. That is a read of
a persisted artifact and needs no pipeline change. The alternative — persisting
a minority-class count into the dataset manifest — would be a Phase 10 manifest
change, which §5 forbids and which is 16B-shaped work, not 16A's.

**Open item for the maintainer:** confirm that reading `features.parquet` is an
acceptable verdict input, or accept that class imbalance drops out of v1
entirely. D-S057-05 assumes the former.

### Finding 4 — `fold_primary` is optional in `metrics.json`, and the overfit rule needs it

`PredictiveMetricsReport.fold_primary` is a `| None` field.
`analyze_predictive_run` preserves it when re-analyzing but does not create it;
it is written by the run path. A run without it cannot be evaluated for
overfitting.

The rule set therefore has a **missing-input rule** (D-S057-07): a required fact
that is absent yields `INCONCLUSIVE` with the missing input named — never a
silent `PASS`, and never a rule quietly skipped. All three Sprint 052 runs do
carry `fold_primary` (SPRINT_052.md S052-T004/T005 outcome notes report it), so
the worked example is unaffected.

### Finding 5 — whether the dashboard read belongs to 16A or to 16D

§13H.1's completion criteria say "the dashboard reads the verdict; no verdict
logic exists in `apps/dashboard`". §13H.4 makes the dashboard 16D's increment.
Read literally, 16A owes a display; read structurally, 16D owns the surface.

This plan includes **one deliberately minimal** dashboard task (S057-T006:
render the persisted verdict string, its rule-set version, and its recorded
inputs; zero constants, zero arithmetic, zero new thresholds) and marks it first
in the descope order. **The maintainer decides at Wave 0** whether to keep it or
defer the whole display to 16D (D-S057-09). Either answer is consistent with the
phase text; deferring it means 16A's completion criterion 3 is met in its
negative half only ("no verdict logic in `apps/dashboard`" — trivially true if
nothing there changes) and the positive half moves to 16D.

### Finding 6 — Phase 16 §13H.9 anticipated no ADR for 16A

Five ADRs are anticipated for the phase (16B, 16C, 16G x2, 16E); none for 16A.
This plan nevertheless proposes **ADR-0032**, because 16A ships three
hard-to-reverse things: a vocabulary that 16C/16D/16G will consume, a persisted
sidecar schema, and a module-placement decision. Changing any of them later
invalidates persisted verdicts.

§13H.9 says the list is what "is anticipated", not what is permitted, so this is
not a departure from the approved phase — but it is an addition, and the
maintainer confirms or declines it at Wave 0 (D-S057-12). If declined, D-S057-02
through D-S057-08 stand alone as the binding record and T001 becomes a Wave 0
document-only task.

### Finding 7 — there is no CLI path to a verdict, and there is no CLI path to a `CandidateSetSpec` either

Sprint 052's S052-T005 already recorded that `trading-cli research run` has no
config key for `RunPredictiveResearchRequest.candidate_set`, and ran the tree
pass by calling the application function directly from an uncommitted scratch
script. The retrospective task here (S057-T005) uses the same, already-precedented
mechanism: a direct call to the new application function, no committed script, no
CLI change. A `trading-cli research verdict` subcommand is a reasonable follow-up
and is **out of scope** (§3) — adding it would drag `apps/cli` config plumbing
into a sprint whose subject is a contract.

### Finding 8 — the worked example depends on run directories that live only on the maintainer's machine

`user_data/` is gitignored and maintainer-owned (D-S052-08). Sprint 052's three
run directories and their two dataset directories are the only inputs the
retrospective task can use, and **re-running the study to recreate them is out of
scope** (§3) — that would be new research, not a retrospective application.

```text
REQUIRED, and to be confirmed by the maintainer at Wave 0:
  runs/f7ac893d54ae6b69/{manifest.json, metrics.json, importance.json}
  runs/faa6983acd03f846/{manifest.json, metrics.json, importance.json}
  runs/6d2842b647cd4097/{manifest.json, metrics.json, importance.json}
  datasets/f9f042f9042bcafb/{manifest.json, features.parquet}
  datasets/98a893f56549c96b/{manifest.json, features.parquet}
  all under user_data/workspace/research/predictive_research/
IF ANY IS MISSING:  S057-T005 is a STOP-and-report, not a task to work around
                    with a synthetic stand-in. A synthetic worked example would
                    be precisely the failure mode §13G/§13H.0 exist to prevent.
```

---

## 5. Boundaries this sprint must not cross

```text
FORBIDDEN   any behavioural change to the Phase 10 build/run/analyze path:
            application/predictive_research/{build_predictive_dataset,
            run_predictive_research, analyze_predictive_run,
            compare_predictive_runs, promote_predictive_run}.py and
            research/predictive/{matrix,splitting,metrics,importance,labels,
            features,selection,estimators,preprocessing,sample}.py.
            The verdict CONSUMES their output; it does not alter, re-derive or
            re-persist any of it. Re-running analyze_predictive_run to
            regenerate metrics.json is NOT part of this sprint
FORBIDDEN   any edit under research/predictive/promotion/, infrastructure/ml/,
            market_analysis/, research/strategy_research/,
            research/simulation/, execution/
FORBIDDEN   any diff to MODEL_FAMILY_ALLOWLIST, ADR-0022, ADR-0023, ADR-0024,
            ADR-0029, ADR-0031
FORBIDDEN   changing any threshold, flag code or behaviour in
            research/reporting/predictive/quality.py or in
            apps/dashboard/.../catalog/predictive_quality.py
FORBIDDEN   any verdict computation, threshold constant or fallback rule inside
            apps/dashboard/ (§13H.1). The dashboard reads verdict.json or
            displays nothing
FORBIDDEN   editing docs/reference/BTC_PREDICTIVE_STUDY.md, SPRINT_052.md,
            S052_*, SPRINT_051.md, S051_* — Sprint 052 is closed history and is
            cited, never amended (D-S057-11)
FORBIDDEN   re-running, re-fitting or re-analyzing any Sprint 052 study, or
            running any new study on any instrument
FORBIDDEN   tuning any threshold after seeing a verdict it produced. A mismatch
            against D-S057-10's pre-declared expectations is a STOP-and-report
FORBIDDEN   any test that reads real data, user_data/, or the network
            (ADR-0023 §8 untouched). The retrospective run is a
            MAINTAINER-TRIGGERED action, never a CI action
FORBIDDEN   a new dependency, extra, estimator family, component or sample kind
FORBIDDEN   committing dataset bytes, run directories, verdict.json files or
            report HTML
ALLOWED     new src/trading_framework/research/predictive/verdict.py (+ tests)
ALLOWED     new application/predictive_research/evaluate_run_verdict.py (+ tests)
ALLOWED     an additive path helper in infrastructure/storage/paths.py
ALLOWED     a read-only display addition in apps/dashboard (S057-T006 only,
            reading verdict.json, no logic)
ALLOWED     docs/adr/ADR-0032, docs/reference/PREDICTIVE_VERDICT.md,
            docs/planning/sprints/, research/predictive/CLAUDE.md
```

If a verdict rule cannot be computed without touching a forbidden path, **stop
and report**. A missing persisted fact is a finding about what the pipeline
persists — worth more than the rule.

---

## 6. Task breakdown

**7 tasks, 4 waves.** Every task below was checked against
`docs/planning/PROJECT_MANAGEMENT.md`'s Definition of Ready: a single stated
goal, acceptance criteria that can be evaluated without judgement, declared
dependencies, the documents it is bound by, and a size that fits one PR.

### Wave 0 — The binding contract

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S057-T001 | Land `S057_WAVE0_DECISIONS.md` and draft **ADR-0032** (verdict vocabulary and semantics, the versioned rule-set format, the `verdict.json` schema, module placement) as `Status: Proposed`; carry it through maintainer review to `ACCEPTED` and fold any correction it attracts back into the Wave 0 decisions | ADR-0032 exists with Context / Decision / Consequences / Alternatives / Follow-up, is linked from `docs/adr/README.md`, and reaches `ACCEPTED` **by an explicit maintainer statement — no agent flips it**; every Wave 0 decision the review changed is amended in place and D-S057-01..11 are individually confirmed; the pre-declared expected verdicts in D-S057-10 are recorded **before** any implementation exists; **no code file is touched by this task** | maintainer approval to open the sprint | TODO |

Wave 0 is DONE when the maintainer has checked every box in
`S057_WAVE0_DECISIONS.md` D-S057-12 **and** ADR-0032 is `ACCEPTED` (or the
maintainer has explicitly declined the ADR per Finding 6, in which case the Wave
0 decisions alone are the binding record).

### Wave 1 — The rule set, library-free and pure

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S057-T002 | `research/predictive/verdict.py`: the `RunVerdict` vocabulary enum, the frozen `VerdictRuleSet` (version string + every threshold), `VerdictFacts` (the extracted inputs), `RuleEvaluation` (rule id, fired, observed, threshold, source artifact), `VerdictReport` with `to_dict()`/`from_dict()`, and the pure `evaluate_verdict(facts, rules)` cascade in D-S057-08's fixed rule order | every one of the eight vocabulary values is produced by at least one synthetic fixture, including each `REJECTED_*`; the rejection precedence order is asserted by a fixture where two rejection rules fire at once and the earlier one wins, with **both** recorded in the evaluations list; a missing required fact yields `INCONCLUSIVE` naming the missing input (never `PASS`, never a skipped rule); `evaluate_verdict` is pure — same input, byte-identical `to_dict()` output, asserted by a round-trip equality test; the payload contains **no wall-clock field** (D-S057-07); `research/predictive/` gains no import of sklearn/xgboost/lightgbm/catboost/torch, `signal_model`, `strategy`, `application`, or `research.reporting` (architecture boundary test green) | T001 | TODO |
| S057-T003 | Fact extraction: turn a `PredictiveMetricsReport`, a dataset manifest's `study_spec` / `fold_summary` / `exclusion_counts`, the pooled TEST labels, and the `importance.json` payload into a `VerdictFacts` record, with every fact carrying the artifact it was read from | each fact in D-S057-05's table is extracted, and each records its source artifact name; the baseline delta uses pooled `MODEL` minus pooled `RANDOM_PERMUTATION` on the task's primary metric, matching the existing `primary_metric_name` convention (`roc_auc` / `spearman_ic`) exactly — not a second definition of "primary metric"; per-fold win counting uses the same metric per fold; feature-importance facts are extracted and **recorded only**, driving no rule in v1 (asserted by a fixture whose importances are absurd and whose verdict is unchanged); extraction is total — a missing optional artifact produces a named missing-input marker, never an exception | T002 | TODO |

### Wave 2 — Persistence and the entry point

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S057-T004 | `application/predictive_research/evaluate_run_verdict.py` (request/result dataclasses mirroring `analyze_predictive_run`'s shape) plus `predictive_research_run_verdict_path` in `infrastructure/storage/paths.py`; reads the run envelope, the dataset envelope and the optional `importance.json`, evaluates, and writes `runs/<run_id>/verdict.json` | the sidecar is written at `runs/<run_id>/verdict.json` and contains: rule-set version, `run_id`, `dataset_fingerprint`, the verdict, every extracted fact with its source, and every rule with fired/not-fired + observed + threshold; **no fitted model blob is opened** (asserted the same way `analyze_predictive_run` is: no `joblib.load`, no `models/fold_*.bin` read — covered by a test); evaluating the same run directory twice produces a **byte-identical** file; `metrics.json`, `manifest.json`, `importance.json` and the dataset directory are opened read-only and are byte-identical afterwards (asserted); nothing under §5's forbidden list is modified; the whole path runs on a synthetic fixture in default CI without the `ml` extra and without network | T003 | TODO |

### Wave 3 — The worked example, the read surface, and closing out

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S057-T005 | **Retrospective application (maintainer-executed, reads `user_data/`, never CI).** Evaluate the rule set over Sprint 052's three runs — `f7ac893d54ae6b69` (ridge/regression), `faa6983acd03f846` (logistic/binary), `6d2842b647cd4097` (lightgbm/tree) — and record each verdict with the facts that produced it | all three verdicts are produced from the persisted artifacts alone, with no re-run and no re-analysis; each is compared against D-S057-10's **pre-declared** expectation (`WEAK_PASS`, `PASS`, `REJECTED_OVERFIT` respectively); **any mismatch is reported as a STOP-and-report finding with the offending fact and threshold named — no threshold is changed to resolve it**; the three `verdict.json` files stay under `user_data/` and are not committed (`git status --porcelain` clean apart from documentation); the recorded output states plainly that these verdicts change nothing about Sprint 052's own conclusions, which stand as written | T004; maintainer confirmation that the run directories in Finding 8 exist | TODO |
| S057-T006 | **Descopable.** Dashboard displays the persisted verdict: the verdict value, the rule-set version, and the recorded inputs, read from `verdict.json` only | no threshold constant, no comparison and no fallback verdict is added anywhere under `apps/dashboard/` (reviewable as a diff); a run with no `verdict.json` renders "no verdict recorded" rather than a computed one; the existing `predictive_quality.py` mirror is **not modified**; `apps/dashboard` still imports no `trading_framework` symbol (ADR-0022) | T004; D-S057-09 kept rather than deferred | TODO |
| S057-T007 | `docs/reference/PREDICTIVE_VERDICT.md` (vocabulary and exact semantics, the v1 rule set with every threshold, the rule order, the missing-input rule, the worked example from T005, and the ADR-0024 restatement); `research/predictive/CLAUDE.md` conventions; the Finding 2 technical-debt entry; sprint closure (Review, `CURRENT_STATUS.md`, and an **appended** 16A note in `PHASE_16_QUANT_WORKBENCH.md` §13H.1) | the reference document states in its own first section that a verdict is **a decision aid for what to study next — never evidence of a live edge and never a promotion approval** (ADR-0024's rule, restated not weakened), and that nothing is promoted, filtered or hidden because of one; each of §13H.1's four completion criteria is named as met or not met with evidence; the closure states that this sprint produced **no study, no scorer, no promotion and no new market claim**; the Finding 2 duplication is logged in `TECHNICAL_DEBT.md` by its owner, not summarized here; the roadmap edit is an append, never a rewrite | T005 (and T006 if kept) | TODO |

**Progress: 0 / 7.**

**Descope order:** T006 first (Finding 5 — the display may simply be 16D's).
Then T005's scope may shrink to the two baseline runs if the tree run's
directory is unavailable — but **T005 is never dropped entirely**: a verdict
contract with no real run behind it is exactly what §13H.0's entry condition
exists to prevent. T002-T004 are indivisible; a rule set that is not persisted
and not deterministic ships nothing.

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/predictive-verdict-adr` | T001: ADR-0032 + Wave 0 decisions confirmed |
| 1 | `feat/predictive-verdict-rules` | T002: vocabulary, versioned rule set, pure cascade |
| 2 | `feat/predictive-verdict-facts` | T003: fact extraction from persisted artifacts |
| 3 | `feat/predictive-verdict-sidecar` | T004: application entry point + `verdict.json` |
| 4 | `docs/predictive-verdict-worked-example` | T005: the Sprint 052 retrospective |
| 5 | `feat/dashboard-verdict-display` | T006: read-only display (if kept) |
| 6 | `docs/predictive-verdict-reference` | T007: reference doc, module docs, closure |

PR boundaries are the agent's call within these outcomes (`git-workflow`); the
table is a suggestion, not a mandate. Every PR targets
`sprint/analyst-verdict-artifact`.

---

## 8. Acceptance criteria

1. A predictive run carries a verdict **and** the inputs behind it, both
   reproducible from the persisted artifacts alone (§13H.1 completion criterion
   1).
2. Re-running the rule set over the same artifacts yields the **same** verdict —
   asserted as byte equality of the payload, not as "the same value" (§13H.1
   criterion 2).
3. No verdict logic, threshold or fallback exists anywhere under
   `apps/dashboard/`; if T006 is kept, the dashboard reads `verdict.json` and
   nothing else (§13H.1 criterion 3).
4. The documentation states plainly that a verdict is a decision aid for what to
   study next — never evidence of a live edge, never a promotion approval
   (§13H.1 criterion 4, ADR-0024).
5. The rule set is **declared and versioned**; its version appears in every
   verdict, and changing a threshold is a diff in one file.
6. All eight vocabulary values are reachable and covered by synthetic fixtures;
   `WEAK_PASS` and `INCONCLUSIVE` are demonstrably ordinary outcomes, not
   exotic ones.
7. The Sprint 052 worked example produced the three pre-declared verdicts, or
   every deviation is reported with the fact and threshold that caused it and
   **no threshold was changed in response**.
8. Nothing under §5's forbidden list was modified; the Phase 10 build/run/analyze
   path is byte-unchanged.
9. Default CI stays synthetic-only, network-free and extra-free; the real-run
   evaluation is maintainer-triggered only.
10. No study, scorer, promotion, sample kind, dependency or market claim was
    produced by this sprint.
11. `research/predictive/` gained no forbidden import; the architecture boundary
    test is green.
12. No `user_data/` content — including any `verdict.json` — entered git.

---

## 9. Dependencies

**Required:** `ROADMAP.md` `Status: ACCEPTED` (it is); Phase 16 APPROVED (it is,
2026-09-04); **Sprint 052 has actually run** (it has — merged via #461-#463),
which is 16A's hard entry condition and is not waivable; ADR-0032 `ACCEPTED`
before Wave 1 (or explicitly declined per Finding 6).

**Required for T005 only:** the maintainer's local Sprint 052 run and dataset
directories (Finding 8), and the maintainer executing that task.

**Explicitly not required:** 16C, 16D, 16E, 16F, 16G; the `ml` extra for any CI
path; network access; a CLI change; any new sample kind; Sprint 056's
`signal_occurrences` capability (consumed as context only — no verdict rule
depends on it, and `sample_provenance` is recorded as a fact, not scored).

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **A verdict becomes an authority** (§13H.1's first named risk) | The vocabulary carries no "validated"/"approved" value (D-S057-02); the ADR-0024 restatement is an acceptance criterion, not prose; the worked example is deliberately mixed (`PASS` / `WEAK_PASS` / rejection) so a reader sees the scale is real; no consumer may act on a verdict (D-S057-03). |
| **Thresholds tuned to produce nicer verdicts** (§13H.1's second) | D-S057-10 freezes the three expected verdicts in Wave 0, *before* implementation; a mismatch is a STOP, and any threshold change is a maintainer-reviewed diff to one versioned object (§5). |
| **A rule set designed from one study is thin evidence** (§13H.1's third) | v1 is eight rules with unanimity requirements on the rejection side, and feature importance is recorded but not scored. The rule set is versioned so v2 can be a visible diff once a second study exists. |
| **The relative overfit rule is wrong** (Finding 1) | Hand-verified against all three Sprint 052 runs in D-S057-10 before implementation; T005 re-verifies it mechanically. If the mechanical result disagrees with the hand calculation, that is a finding about the rule, not about the run. |
| **Verdict logic leaks into the dashboard** | ADR-0022 already blocks the import; §5 forbids the constants; T006's acceptance is stated as a reviewable diff property ("no threshold constant added"). |
| **The worked example is unavailable** (Finding 8) | Confirmed by the maintainer at Wave 0 before the sprint opens; if unavailable, T005 is a STOP — re-running the study is out of scope and a synthetic stand-in is forbidden. |
| **Threshold triplication drifts** (Finding 2) | Logged as LOW technical debt with a named repayment trigger; the verdict's own thresholds are versioned and serialized into every verdict, so a drift is visible in the artifact itself. |
| **Scope creep into 16D** | T006 is minimal, descopable, and first in the descope order; the deferral question is a Wave 0 checkbox (D-S057-09). |

---

## 11. Quality gates

- `ruff`, `mypy`, `pytest` green; default CI stays network-free and extra-free.
- `tests/unit/test_architecture_boundaries.py` green — it is the enforcement of
  D-S057-04's placement decision and may not be amended to permit a new import.
- Each PR is one coherent outcome (`git-workflow`); PR base is the sprint branch.
- No `user_data/` content, dataset bytes, run outputs or `verdict.json` enters
  git.
- Every threshold that appears in code also appears in
  `docs/reference/PREDICTIVE_VERDICT.md` with the same value.

---

## 12. Post-sprint direction

16A unblocks the diagnostics half of 16D (a verdict to display) and supplies
16C with a verdict on its scoring run. 16G consumes analyst diagnostics as one
input to a promotion gate — **and nothing in this sprint moves anything closer
to a promotion**: the gate is 16G's, is explicitly human, and no verdict value
produced here is an input a machine may act on. This sprint's closure must not
imply otherwise.

---

## 13. Review

_To be written at closure by `tech-writer`. Empty until then._
