# Sprint 049 — Wave 0 Decisions

Binding decisions for the Promotable Predictive Artifact (Phase 14A).
Date: 2026-09-02. Reconciled against `docs/product/PRD-ml-signal-promotion.md`,
then updated with the maintainer's answers to the five remaining forks.

```text
Status: APPROVED (2026-09-02) — Wave 0 Checklist below signed off in full by
        the maintainer. ADR-0029 is separately ACCEPTED.

Numbering: drafted as "Sprint 048 / Phase 13A" against a stale base. Those
        numbers are taken by merged work (Sprint 048 = Exit/Risk Model
        Expansion and Catalog Growth, Phase 13, ROADMAP §13E). This is
        Sprint 049 / Phase 14A / ROADMAP §13F; the runtime successor is
        Sprint 050 / Phase 14B.

Answered by the PRD:        Q1 (format) -> D-S049-13
                            Q3 (fold)   -> D-S049-04
Answered by the maintainer:  Q2 -> D-S049-14   (extract from the existing blob)
                             Q4 -> D-S049-15   (trading-cli research promote)
                             Q7 -> D-S049-06   (exact linear; ulp-bounded logistic)
                             Q8 -> D-S049-08   (move FittedNumpyPreprocessor)
                             Q9 -> D-S049-05   (parameter values stay out)
Standing prerequisites (NOT sprint tasks): Q5, Q6 — see below.

ADR-0029 is WRITTEN and ACCEPTED (2026-09-02, Filip Folga):
        docs/adr/ADR-0029-promoted-predictive-artifact.md
        It records these answers and names Q7 explicitly as a maintainer
        decision that overruled the architect's recommendation.

Basis:  docs/product/PRD-ml-signal-promotion.md — AUTHORITATIVE
        docs/adr/ADR-0029 (ACCEPTED) — the mechanism
        docs/adr/ADR-0024-machine-learned-state-promotion.md (ACCEPTED) — the five conditions
        docs/planning/sprints/S044_GATE.md — entry criteria + parity sketch §4
        docs/adr/ADR-0023-predictive-research-boundary.md (ACCEPTED) §4, §7
        docs/adr/ADR-MA-002 / ADR-MA-005 / ADR-MA-009 (ACCEPTED)
        docs/adr/ADR-0022 (ACCEPTED) — apps boundary, extras policy
        docs/adr/ADR-0026 (ACCEPTED) + Amendment 1 — trading-cli config + allow-list
        docs/planning/sprints/SPRINT_049.md
        docs/planning/ROADMAP.md §13F (PROPOSED)
        src/trading_framework/ as on main at d65de4c (after Sprint 047 and 048)
```

**Phase 14 is two sprints, not one** (SPRINT_049.md §0). This document locks
Sprint 049 — the promotable artifact — only. The split was re-checked against
the PRD's narrower v1 scope and confirmed: the format decision no longer argues
for it, but conditions 2/3 and the online half of condition 4 are
executor/runtime work whose cost is independent of the serialization format.

---

## Inherited locks (do not reopen)

```text
ADR-0029: the parameter format, promotion store, both parity bars, the
        promotion-time guard, and the narrow ADR-0023 §7 amendment — ACCEPTED
ADR-0024: all five promotion conditions, as accepted 2026-08-28
ADR-0024 condition 5: NO model registry. Content-addressed store only.
ADR-0023 §4: purge / embargo / dataset fingerprint / availability on the matrix
ADR-0023 §8: synthetic CI fixtures only (D-S039-CI-dataset); no NQ dependency
ADR-0022: apps/* are deployable consumers; scripts/ stay thin
ADR-0026 Amendment 1: the apps/cli import allow-list; widening it is a new
        amendment with maintainer approval, never a test-file edit
ADR-0027 / ADR-0028: Sprint 047 and 048's loader, Exit/Risk models and catalog
        components are UNCHANGED by this sprint (SPRINT_049.md §4 Finding 8)
ml / ml-trees / dl stay out of the default install and out of default CI
Standard CI stays network-free
research/predictive/ imports no ML library, ever
        (NumPy is NOT an ML library here — it is a default-install dependency,
         pyproject.toml:15, already imported by five modules in that package)
IDEA-003 (feature/model store) stays deferred; TD-021 (no registry) stays deferred

From the PRD:
        no real-money trading; no multi-instrument; no auto-retraining;
        no model registry; NO ONNX in v1; NO tree/neural families in v1;
        BTC futures on the existing Phase 8A dry-run infrastructure;
        exact-match parity as the RELEASE GATE (see D-S049-06 for what that
        does and does not cover)
```

---

## D-S049-01 — Problem statement

Phase 10 (Sprints 039–044) can train and evaluate models offline and produce
metrics reports. Nothing trained is reachable from a strategy: `models/fold_*.bin`
are joblib blobs whose own manifest declares them non-reloadable, and no Market
Analysis component can produce a State from a model.

ADR-0024 states five conditions for closing that gap. Conditions 3 and, in
part, 1 and 5 are already satisfied by Phase 10 infrastructure; conditions 2
and 4 are genuine new work (S044_GATE §2).

**Sprint 049 ships exactly:** a `promote_predictive_run` workflow producing one
content-addressed **parameter file** per (run, last fold), whose fitted
preprocessing statistics travel inside it, an evaluator that reads it with
**NumPy alone**, and a test proving that loading it and re-predicting reproduces
the run's own recorded predictions.

**Not this sprint:** any Market Analysis component; any executor change; any
dry-run or live runtime change; Path B of the parity harness; a registry; a
real-data candidate model; tree/neural families; any change to Sprint 048's
Exit/Risk work.

---

## D-S049-02 — Sprint branch and PR base

```text
Integration branch: sprint/promotable-predictive-artifact   (cut from main @ d65de4c)
Working branches:   feat/ | fix/ | docs/ | test/ | refactor/ + descriptive slug
PR base:            sprint/promotable-predictive-artifact   (never main until integration)
```

Working-branch PRs squash-merge into the sprint branch; one integration PR
`sprint/promotable-predictive-artifact` -> `main` at the end. Branch names
describe the change, never the task ID.

```text
NOTE  `spike/` is NOT a valid prefix in this project's git-workflow. The
      availability spike (S049-T001) uses `docs/inference-availability-enforcement-spike`,
      because its entire output is a document.
```

---

## D-S049-03 — The promoted artifact is a SEPARATE category from a research blob

```text
LOCKED  research/predictive_research/runs/{run_id}/models/fold_*.bin stay
        opaque and NOT reloadable by any workflow EXCEPT the single, explicit
        promotion-time read locked in D-S049-14. The manifest's policy string
        is not edited.
LOCKED  a PROMOTED artifact is produced by a separate, explicit workflow, into a
        separate, content-addressed directory, and IS loadable by contract.
LOCKED  promotion never mutates the source run directory (asserted, S049-T008).
LOCKED  ADR-0029 §7 amends ADR-0023 §7 for this ONE workflow and ONE purpose.
        Blanket "blobs are now loadable" is rejected.
```

Store layout:

```text
research/predictive_research/promoted/{artifact_fingerprint}/
    manifest.json     independently readable; never requires the payload
    artifact.json     coefficients + intercept + fitted preprocessing
                      statistics + ordered features, as PLAIN NUMBERS, one unit
```

```text
LOCKED  nothing else in that directory. No index, no `latest` pointer, no
        status field, no lock file. ADR-0024 condition 5, asserted by a test.
```

---

## D-S049-04 — One promotion produces exactly ONE artifact: THE LAST FOLD

```text
LOCKED  one (run_id, fold_id) -> one artifact_fingerprint -> one directory.
LOCKED  the promoted fold_id is recorded in the manifest, never implicit.
LOCKED  *** the promoted fold is the LAST walk-forward fold *** — the one fitted
        on the most recent available TRAIN span. Maintainer's explicit choice
        (PRD, Goals).
LOCKED  the honest limitation is DOCUMENTED, not hidden: the last fold's TRAIN
        window ends before the last TEST window, so a promoted artifact is
        already stale by one fold at promotion time (S049-T013).
```

Rejected: a final refit on all non-embargoed rows (out-of-sample performance
would be by construction unmeasured — the exact drift ADR-0024 warns about);
per-fold artifacts resolved by as-of date (pushes an as-of rule into the
runtime, which is Sprint 050 scope).

---

## D-S049-05 — Fingerprint derivation (Q9 ANSWERED)

```text
compute_promoted_artifact_fingerprint = sha256(canonical_json({
    run_fingerprint, fold_id, format, format_version, model_family,
    features: [ordered OutputRef identities],
    preprocessing_spec, estimator_spec,
}))
canonical_json: json.dumps(..., sort_keys=True, separators=(",", ":"))
```

```text
LOCKED  identical canonicalization to compute_run_fingerprint.
LOCKED  *** Q9 ANSWERED: fitted PARAMETER VALUES stay OUT of the fingerprint. ***
        Maintainer confirmed. The original lock's rationale (unpredictable blob
        bytes) does not apply to an explicit NumPy parameter format, and the
        exclusion is kept anyway on its own merit: identity is "which run,
        which fold, which spec".
LOCKED  feature ORDER is part of the identity — the evaluator's column order is
        positional.
LOCKED  model_family is part of the identity.
LOCKED  the fingerprint (not the run_id) is the directory name.
```

Because the fingerprint is carried as a `STR` component parameter in Sprint 050,
it lands in `CanonicalParameters` -> `Lineage.parameters` -> cache identity with
no new mechanism. Sprint 050 must not invent a parallel "model lineage" concept.

---

## D-S049-06 — Parity: TWO comparisons, TWO bars (Q7 ANSWERED)

The reconciliation established that "exact match" names two structurally
different comparisons. Both are locked here, separately, because conflating them
is the most likely way this gets misread later.

```text
COMPARISON 1 — OFFLINE vs ONLINE.  The RELEASE GATE. Sprint 050, Path B.
    NumPy evaluator (research) == NumPy evaluator (dry-run runtime)
    Same code, same artifact, same float64 inputs.
LOCKED  EXACT, unconditionally. This is what the PRD's success metric 1 means
        and what ADR-0024 condition 4 gates on. Q7's answer does NOT weaken it.

COMPARISON 2 — NUMPY vs SKLEARN.   The cross-check. Sprint 049, Path A (T010b).
    NumPy evaluator == predictions.parquet, which scikit-learn produced.
    Two different implementations of the same mathematics.
```

**Q7 ANSWERED — maintainer's decision, which OVERRULED the architect's
recommendation.** The architect recommended requiring exact equality for both
families and dropping logistic from v1 if it failed. The maintainer chose
instead to **keep both families in v1**, accepting a documented ulp-bounded
tolerance for the logistic probability. The trade accepted: broader model
coverage now, at the cost of one named, bounded inexactness.

Because `predictions.parquet` carries `y_pred` and `y_proba` as separate
columns, the tolerance is confined to one column of one family:

| Compared value | Family | Bar |
|---|---|---|
| `y_pred` | ridge, elastic_net | **exact** (`==` on float64) |
| `y_pred` (class label) | logistic | **exact** — a tie at `z == 0` is a defect, not rounding |
| decision function `z = Xw + b` | logistic | **exact**, asserted separately so the tolerance cannot hide an upstream error |
| `y_proba` | logistic | **`rtol=0, atol=1e-15`** (≈4 ulp of 1.0), and ONLY here |

```text
LOCKED  the tolerance applies to EXACTLY ONE column of ONE family in
        Comparison 2. Anywhere else a non-exact result is a DEFECT.
LOCKED  the implementation MEASURES and RECORDS the observed maximum deviation.
        An observed deviation ABOVE the ceiling is a STOP-and-report, never a
        reason to widen the ceiling. Widening mid-sprint is a STOP-and-ask.
LOCKED  every parity test carries a MUTATION CHECK — a deliberately perturbed
        coefficient must make it fail.
LOCKED  the tolerance is NOT inherited by Sprint 050. If Comparison 1 is ever
        non-exact, that is a failure of the release gate.
LOCKED  no test may assert against a hand-copied expected-prediction constant
        taken from a previous run of the code under test. For T010b the oracle
        is predictions.parquet; for T010a the expected values are computed
        independently inside the test.
```

---

## D-S049-07 — Guards: one relaxed at load time, one ADDED at promotion time

```text
LOCKED  load_promoted_artifact refuses on ANY of:
          - an unknown format_version
          - a model_family outside the linear/logistic allow-list
          - a preprocessing_spec step the evaluator does not implement
          - a feature-count / feature-order mismatch between manifest and payload
        Hard failure, before any arithmetic.
LOCKED  no `strict=False`, no `allow_mismatch`, no environment variable, no
        compatible-range check. The API surface has no bypass parameter, and a
        test asserts that.
LOCKED  RELAXATION, stated plainly: a difference in the TRAINING library version
        does NOT refuse a load. A parameter file has no coupling to sklearn,
        because sklearn is not involved in reading it. The training library and
        version are recorded for PROVENANCE only.
LOCKED  *** a PROMOTION-TIME library version guard IS required (a consequence of
        D-S049-14). *** Unpickling a joblib blob under a different scikit-learn
        version than wrote it is unsafe. Promotion refuses if the run manifest's
        library_version differs from the installed one; the remedy is to re-run
        the study. The two guards protect different operations.
LOCKED  the remedy for a refused LOAD is re-promotion.
```

---

## D-S049-08 — Layering, and the FittedNumpyPreprocessor move (Q8 ANSWERED)

```text
research/predictive/        *** the pure-NumPy promoted-artifact EVALUATOR ***,
                            PromotedPredictor structural Protocol, error types,
                            fingerprint derivation. NumPy only.
research/datasets/          PromotedArtifactManifest / Ref / Repository
infrastructure/ml/          promotion.py: blob read + parameter extraction — the
                            ONLY place sklearn is touched, inside lazy imports
application/                promote_predictive_run: orchestration only
predictive_research/
apps/cli/, scripts/         thin operator surface
```

```text
LOCKED  the EVALUATOR lives in the DOMAIN layer, not infrastructure/ml/.
        Reason: Sprint 050's Market Analysis component must reach it, and
        market_analysis/ may not import infrastructure/ml/.
LOCKED  *** Q8 ANSWERED: MOVE FittedNumpyPreprocessor / fit_numpy_preprocessor
        from infrastructure/ml/torch/preprocessing.py into research/predictive/,
        and have the torch adapter import them downward. *** Maintainer
        confirmed. NOT copied (a second copy of the same arithmetic is what
        later drifts and breaks parity silently), and the boundary allow-list is
        NOT widened.
LOCKED  the move touches Sprint 043's torch path and its tests. That churn is
        expected and approved; it is not scope creep. The `dl` extra's tests
        are a quality gate for this sprint (SPRINT_049.md §11).
LOCKED  the architecture boundary test's allow-list stays byte-identical to
        main. If an implementation detail appears to require widening it, STOP.
LOCKED  module-level ML imports are forbidden even inside infrastructure/ml/.
```

---

## D-S049-09 — Testing and CI

```text
Default CI (extra-free, network-free)  <- carries the headline work
    contracts, fingerprint determinism, repository round-trip, refuse-overwrite,
    no-registry assertion, architecture boundaries,
    *** THE NUMPY EVALUATOR AND ITS EXACTNESS SUITE (S049-T010a) ***,
    the format/family guard and all four of its refusals
`ml` CI job (Sprint 040's dedicated job)
    the blob read + parameter extraction adapter (S049-T006b),
    promote_predictive_run end to end (S049-T008) — it reads a joblib blob,
    Path A replay against predictions.parquet (S049-T010b) + its mutation check
`dl` extra
    Sprint 043's torch tests, because of the Q8 move
Fixtures
    synthetic only (D-S039-CI-dataset). No NQ, no network, no committed blob.
```

```text
LOCKED  the EVALUATOR half of parity runs in DEFAULT CI with no ML extra
        installed. This is the executable proof that the dry-run/live runtime
        needs no ML dependency — the whole point of D-S049-13.
LOCKED  PROMOTION requires the `ml` extra; INFERENCE requires nothing. That
        asymmetry is deliberate: promotion is an offline operator act on a
        research machine, not a runtime path.
```

---

## D-S049-10 — S049-T001 is a spike and ships no code

```text
LOCKED  the Finding 2 investigation produces S049_AVAILABILITY_FINDING.md and
        modifies no production file.
LOCKED  its verdict may CHANGE SPRINT 050's size. It may not change Sprint 049's
        scope.
LOCKED  if the mechanism ADR-0024 condition 2 presupposes does not exist, that is
        reported to the maintainer as a finding about ADR-0024's pricing, and
        ADR-0030 is proposed, not written-and-implemented.
LOCKED  its branch is `docs/inference-availability-enforcement-spike` — `spike/`
        is not a valid prefix in this project (D-S049-02).
```

---

## D-S049-13 — The promoted artifact format (Q1, from the PRD)

```text
LOCKED  format: a FRAMEWORK-OWNED PARAMETER FILE — coefficients, intercept, and
        the fitted preprocessing statistics — evaluated by PURE NUMPY on both
        the research and the runtime side.
LOCKED  scope: LINEAR AND LOGISTIC FAMILIES ONLY for v1
        (sklearn.ridge, sklearn.elastic_net, sklearn.logistic).
LOCKED  ZERO ML dependency enters the dry-run/live runtime image. NumPy is
        already a default-install dependency (pyproject.toml:15).
LOCKED  tree (xgboost/lightgbm/catboost) and neural (torch) families: promotion
        is REFUSED with a message naming them as DEFERRED to a later increment
        via a version-pinned joblib path — deferred, not unsupported forever,
        and the deferral gets a tracked owner (S049-T013).
REJECTED ONNX or any cross-library exchange format for v1 — a second numerical
        implementation directly threatens the exact-match bar.
REJECTED pinned joblib for v1 — it would put an ML extra in the runtime image
        and pull the parity gate out of default CI.
```

Two verified code facts that make this cheap: `FittedSklearnPreprocessor.statistics()`
already emits the fitted statistics as JSON-stable numbers, and
`FittedNumpyPreprocessor` already implements the exact NumPy arithmetic that
consumes them.

---

## D-S049-14 — Promotion EXTRACTS from the existing blob (Q2 ANSWERED)

```text
LOCKED  *** promote_predictive_run performs a ONE-TIME, PROMOTION-TIME READ of
        the run's models/fold_{last}.bin, extracts coefficients, intercept and
        fitted preprocessing statistics, and writes them as the parameter file.
        It does NOT re-fit. *** Maintainer's decision.
LOCKED  RATIONALE, recorded so it is not re-litigated: the promoted artifact's
        values must match exactly what the original run already reported. A
        re-fit could drift from the metrics the operator looked at when deciding
        to promote, making the promoted model a different object from the
        evaluated one.
LOCKED  this read is the NARROW thing ADR-0023 §7 is amended for: ONE workflow,
        ONE read, ONE purpose, operator-triggered. It is NOT a standing "reload
        the blob" capability, and no other workflow gains one.
LOCKED  no change to the Phase 10 run pipeline. run_predictive_research is not
        touched by this sprint.
LOCKED  consequence: promotion requires the `ml` extra (joblib + sklearn) and a
        promotion-time version guard (D-S049-07). Inference still requires
        nothing.
```

Concrete extraction path (recorded so the engineer does not have to rediscover
it): `serialize_artifact()` writes `{"family", "estimator", "preprocessor"}`
where `preprocessor` is the raw fitted sklearn `Pipeline`. There is **no loader
today** — one is added in `infrastructure/ml/promotion.py`. The fitted
statistics are then read by wrapping that pipeline back into a
`FittedSklearnPreprocessor` and calling its existing `statistics()`, which reads
`named_steps` — so no statistics logic is re-implemented.

Rejected alternatives: re-fitting the fold (drift risk, full re-fit cost);
extracting parameters at **run** time (cleanest answer to §7 and a genuine
future improvement, but it changes the Phase 10 pipeline, which is out of scope
— recorded in ADR-0029's Follow-up).

---

## D-S049-15 — The operator surface is `trading-cli research promote` (Q4 ANSWERED)

```text
LOCKED  *** promotion is exposed as `trading-cli research promote`, a subcommand
        of the EXISTING research group, alongside a thin script. *** Maintainer
        confirmed the architect's recommendation.
LOCKED  it reuses ADR-0026's config contract. No ML-only bespoke path.
LOCKED  RATIONALE: the PRD requires the operator surface to feel like the
        existing strategy_file flow (ADR-0026, ADR-0027), not a research-only
        side door.
LOCKED  if wiring it requires a new module on ADR-0026 Amendment 1's apps/cli
        import allow-list, that is a FRESH AMENDMENT with maintainer approval —
        NEVER a test-file edit. This is the standing lesson ADR-0026
        Amendment 1 exists to record.
LOCKED  OPERATOR_CLI.md is updated as part of S049-T009.
```

---

## D-S049-11 — Standing prerequisites (Q5, Q6) — NOT sprint tasks

Both are recorded here so they cannot be forgotten. **No task in SPRINT_049.md
§6 depends on either.** They gate Sprint 050 and the PRD's success metrics 2
and 3.

### Q5 — A real (non-synthetic) candidate model

Phase 10's validated results are on **synthetic known-signal fixtures**
(ADR-0023 §8, D-S039-CI-dataset). S044_GATE §1.4 requires a candidate run
beating the permutation baseline **on every fold**, on real data. That model
does not exist.

```text
STATED  PREREQUISITE TRACKED OUTSIDE SPRINT 049. Sprint 049's machinery is
        proven against a synthetic fixture exactly like the rest of Phase 10.
```

Before Sprint 050 is planned, the maintainer must decide: (a) run a real
candidate study first, or (b) accept that Sprint 050 promotes a synthetic
artifact as **plumbing only**, with an explicit documented statement that no
tradeable claim is made and §1.4 is waived-with-reason for a plumbing
increment. Option (b) is legitimate and cheap; option (b) *left implicit* is how
a fixture ends up in production.

### Q6 — The named downstream robustness plan

S044_GATE §1.5 requires a **named** downstream Signal Model / Strategy Research
plan for validating the promoted State through Phase 7 robustness. The PRD makes
this success metric 3. It does not exist today.

```text
STATED  PREREQUISITE TRACKED OUTSIDE SPRINT 049. It gates the PRD's 3-5 day
        dry-run being treated as meaningful evidence, and it gates Sprint 050's
        planning — "we will figure it out" fails the gate's §1.3 explicitly.
NEW     That plan must account for TD-027: the Robustness delay stress still
        REJECTS bracket exits (ROADMAP §13E). If the promoted-model strategy
        uses Sprint 048's BracketExitModel, not every stress dimension is
        available. Flagged by SPRINT_049.md §4 Finding 8 for Sprint 050.
```

---

## D-S049-12 — Wave 0 Checklist (maintainer)

Nothing below may be checked off by an agent. `engineer` must refuse to start
while any box is unchecked. The question boxes are **transcription checks** —
confirming the answers were recorded correctly, not re-deciding them.

- [x] **ROADMAP §13F approved** (`PROPOSED` -> accepted): Phase 14 exists, and it is **two** increments (14A this sprint, 14B Sprint 050), not one.
- [x] **The renumbering confirmed** — Sprint 049 / Phase 14A / ROADMAP §13F for this sprint, Sprint 050 / Phase 14B for its successor; the earlier "Sprint 048 / Phase 13A" drafts referred to numbers now taken by merged Exit/Risk work.
- [x] **ADR-0029 on the sprint branch** with its ACCEPTED status and `Approved-by` line preserved exactly as given, plus the `docs/adr/README.md` index row.
- [x] **The two-sprint split re-confirmed** after reconciliation (SPRINT_049.md §0, reason 4).
- [x] **D-S049-13 transcription confirmed** — NumPy parameter format, linear/logistic only, zero ML dependency in the runtime, ONNX and v1-joblib rejected, tree/neural deferred with a tracked owner.
- [x] **D-S049-04 transcription confirmed** — last walk-forward fold; one-fold staleness documented.
- [x] **D-S049-14 transcription confirmed (Q2)** — extract from the existing blob, one-time promotion-time read, no re-fit, no Phase 10 pipeline change — **and the two consequences accepted: promotion needs the `ml` extra, and a promotion-time library-version guard is added.**
- [x] **D-S049-15 transcription confirmed (Q4)** — `trading-cli research promote`; any ADR-0026 allow-list change is a fresh amendment, not a test edit.
- [x] **D-S049-06 transcription confirmed (Q7)** — **this is the answer that overruled the architect's recommendation.** Confirm specifically: both families stay in v1; the `rtol=0, atol=1e-15` tolerance applies to `y_proba` for logistic **only**, in Comparison 2 **only**; Comparison 1 (the release gate) stays exact; an observed deviation above the ceiling is a STOP-and-report, never a widening.
- [x] **D-S049-08 transcription confirmed (Q8)** — `FittedNumpyPreprocessor` **moves** into `research/predictive/`; the torch path and its tests are updated and gated; the boundary allow-list is not widened.
- [x] **D-S049-05 transcription confirmed (Q9)** — fitted parameter values stay out of the fingerprint.
- [x] **Q5 and Q6 acknowledged as PREREQUISITES TRACKED OUTSIDE THIS SPRINT** — no Sprint 049 task depends on them; they still need answers before Sprint 050 is planned, and Q6's plan must account for TD-027.
- [x] **Finding 8 acknowledged** — Sprint 047/048's merged Exit/Risk and catalog work does not collide with this sprint; it improves Sprint 050's dry-run composition; TD-027 is flagged for Sprint 050's robustness plan.
- [x] **D-S049-03 confirmed:** the ADR-0023 §7 amendment is narrow — one workflow, one read, one purpose; research-run blobs stay non-reloadable by everything else and their manifest policy string is untouched.
- [x] **D-S049-07 confirmed:** the load-time guard has no bypass; the training-library relaxation is accepted; the new promotion-time version guard is accepted.
- [x] **D-S049-09 confirmed:** the evaluator and its exactness suite run in **default CI**; S049-T006b, T008 and T010b run in the `ml` job; the `dl` torch tests are a gate because of the Q8 move.
- [x] **D-S049-10 confirmed:** S049-T001 is a docs-only spike whose verdict may resize Sprint 050 but may not expand Sprint 049.
- [x] **Sprint 049 scope approved as 15 tasks, 5 waves**, explicitly shipping **no** Market Analysis component and **no** runtime change.
- [x] **Branch `sprint/promotable-predictive-artifact` approved**, cut from `main` at `d65de4c`.

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-02. The maintainer was
shown this checklist's full content and scope (all 16 items above, including
ROADMAP §13F, the 15-task/5-wave split, and the branch cut point) and answered:
"Tak, zatwierdzam całą checklistę Wave 0" — explicit approval of the checklist
as a whole, in addition to the item-by-item answers to Q2/Q4/Q7/Q8/Q9 already
recorded earlier in this document and ADR-0029's separate ACCEPTED status.

Once every box is checked, the first task for `engineer` is **S049-T001** (the
docs-only availability spike) on `docs/inference-availability-enforcement-spike`,
cut from `sprint/promotable-predictive-artifact`.
