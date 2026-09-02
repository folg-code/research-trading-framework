# Sprint 049 — Promotable Predictive Artifact (Phase 14A)

## Metadata

```text
Sprint: 049
Phase: Phase 14 — Predictive Model Promotion; increment 14A (opening increment; NOT closing)
Status: APPROVED (2026-09-02) — Wave 0 Checklist D-S049-12 signed off in full
Planned Start: 2026-09-02
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_039-044 (Phase 10 Predictive Research; ADR-0023, ADR-0024, S044_GATE)
            SPRINT_040 §8 (model artifact policy this sprint amends via ADR-0029)
Sprint Branch: sprint/promotable-predictive-artifact
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/promotable-predictive-artifact (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S049_WAVE0_DECISIONS.md — ALL questions ANSWERED
Numbering: this plan was drafted as "Sprint 048 / Phase 13A" against a stale base.
           Sprint 048 and Phase 13 are taken by merged work (Exit/Risk Model
           Expansion and Catalog Growth, ROADMAP §13E). This sprint is
           Sprint 049 / Phase 14A / ROADMAP §13F; its runtime successor is
           Sprint 050 / Phase 14B.
Architecture Sources:
  - docs/product/PRD-ml-signal-promotion.md — the maintainer's decisions; WINS on conflict
  - docs/adr/ADR-0029-promoted-predictive-artifact.md — **ACCEPTED** (2026-09-02);
    the parameter format, promotion store, parity bars, and the ADR-0023 §7 amendment
  - docs/adr/ADR-0024-machine-learned-state-promotion.md — ACCEPTED; the five conditions
  - docs/planning/sprints/S044_GATE.md — entry criteria + parity test design sketch (§4)
  - docs/adr/ADR-0023-predictive-research-boundary.md §4, §7 — leakage + artifact policy
  - docs/adr/ADR-MA-002 / ADR-MA-005 / ADR-MA-009 — ComponentId, Lineage/OutputRef, availability
  - docs/adr/ADR-0022 — apps boundary; extras stay out of default install and default CI
  - docs/adr/ADR-0026 + Amendment 1 — trading-cli config contract and import allow-list
  - docs/planning/ROADMAP.md §13F (Phase 14 — PROPOSED, needs approval before this sprint opens)
```

---

## 0. Slice choice — why this is two sprints, not one

**Phase 14 is split into two sprints:**

```text
Sprint 049 (this one)  — the PROMOTABLE ARTIFACT
    conditions 1 and 5 closed; condition 4's offline half (Path A) built and passing.
    Touches: research pipeline + storage. Ships NO Market Analysis component,
    NO executor change, NO runtime change, NO State.

Sprint 050 (NOT opened here) — the MODEL-BACKED STATE IN THE RUNTIME
    conditions 2, 3 and 4's runtime half (Path B) closed; the model component,
    the registry-injection seam in the dry-run runtime, and the parity harness
    as a release gate. Touches: market_analysis executor + execution runtime.
```

The split was re-checked against the PRD's narrower v1 scope and still holds,
but one of its original reasons is spent, so the argument is restated honestly:

1. ~~Sprint 050's design is not knowable until the serialization fork is
   answered.~~ **CLOSED.** ADR-0029 answers the fork; Sprint 050's runtime
   footprint is known today to be *zero extras*.
2. **Condition 4 is testable in halves, and the offline half has a stable
   target.** Every persisted run already contains `predictions.parquet`. Path A
   can be proven before any runtime exists, and it is the half that actually
   falsifies the evaluator. If the framework's NumPy `predict` cannot reproduce
   the sklearn fit's own numbers, the maintainer's named riskiest assumption has
   failed — and it fails in Sprint 049's Wave 3 rather than in Sprint 050's
   release gate, for the price of one sprint rather than two.
3. **S044_GATE §1.4 / §1.5 are not satisfiable today** (§4 Finding 5). They bind
   the sprint that ships a **State** — Sprint 050. Sprint 049 ships no State.
4. **The strongest structural reason: ADR-0024 conditions 2 and 3 and the online
   half of condition 4 are executor/runtime work whose size is independent of
   the serialization format.** The availability spike (S049-T001), the
   registry-injection seam in `application/execution/local_btc_futures.py`, and
   Path B cost the same whatever the artifact format is. Choosing the NumPy
   format shrank Sprint 050's *deployment* concerns to nothing; it did not
   shrink its *executor* concerns at all.

**This sprint deliberately does not close Phase 14.**

---

## 1. Sprint Goal

```text
research/predictive_research/runs/{run_id}/            (exists today)
    manifest.json + predictions.parquet + models/fold_*.bin
        |
        | promote_predictive_run   (NEW workflow + `trading-cli research promote`)
        |   - selects the LAST walk-forward fold (D-S049-04)
        |   - ONE-TIME read of that fold's blob (D-S049-14), guarded by a
        |     promotion-time sklearn version check
        |   - extracts coefficients + intercept + fitted preprocessing
        |     statistics as PLAIN NUMBERS — no library object travels
        |   - refuses any estimator family outside linear/logistic
        v
research/predictive_research/promoted/{artifact_fingerprint}/   (NEW)
    artifact.json         weights, intercept, preprocessing statistics, ordered features
    manifest.json         run_fingerprint, dataset_fingerprint, fold_id, feature OutputRefs
                          in declared order, model_family, format + format_version,
                          training library + version (PROVENANCE only)
        |
        | load_promoted_artifact -> PromotedPredictor   (pure NumPy, ZERO extras)
        v
    PATH A REPLAY: re-predict the run's own TEST rows
        assert against predictions.parquet under the D-S049-06 bars
```

Success: a maintainer runs one command against an existing Predictive Research
run, gets back a content-addressed directory of **plain numbers**, and a test
**in default CI, with no ML extra installed** proves the evaluator is exactly
self-consistent — with no model registry, no lifecycle state, and no Market
Analysis component in sight.

---

## 2. In scope

- [ ] **ADR-0029** — ACCEPTED (2026-09-02). It must land on the sprint branch with the ROADMAP §13F splice before any Wave 1 task starts.
- [ ] A written **finding** (no code) on whether the executor mechanism ADR-0024 condition 2 presupposes actually exists (§4 Finding 2). Sizes Sprint 050; does not change Sprint 049's scope.
- [ ] `PromotedArtifactManifest` + `PromotedArtifactRef` domain contracts and the `artifact_fingerprint` derivation.
- [ ] `PromotedArtifactRepository` over `research/predictive_research/promoted/{artifact_fingerprint}/`. Content-addressed directory only — **no registry**.
- [ ] **A pure-NumPy promoted-artifact evaluator in the domain layer** (`research/predictive/`), including the **move** of `FittedNumpyPreprocessor` out of `infrastructure/ml/torch/` (D-S049-08).
- [ ] **A blob-read + parameter-extraction adapter** in `infrastructure/ml/promotion.py`, with a **promotion-time sklearn version guard** and a **model-family allow-list**.
- [ ] Load-time **format and family guard** with no bypass.
- [ ] `promote_predictive_run` application workflow + `trading-cli research promote` (D-S049-15).
- [ ] **Path A parity replay test** under the D-S049-06 bars, plus the **evaluator exactness suite in default CI**.
- [ ] Determinism + refusal tests.
- [ ] Documentation: `docs/reference/PREDICTIVE_PROMOTION.md`, TD-022 disposition, the tree/neural deferral given a tracked owner, `research/predictive/CLAUDE.md` / `infrastructure/ml/CLAUDE.md` updates, ROADMAP §13F status.

## 3. Out of scope

- **Any Market Analysis component.** No `ComponentId`, no registry entry, no `AnalysisResult`, no State. That is Sprint 050.
- **Any change to `market_analysis/execution/`, `planning/`, or the registry.** Condition 2 is investigated (a written finding) and not implemented.
- **Any change to `execution/runtime/`, `application/execution/`, or the AWS dry-run worker.**
- **Any change to `run_predictive_research` or the Phase 10 run pipeline** (D-S049-14 explicitly excludes it — extracting parameters at run time was the rejected-for-scope alternative).
- **Path B of the parity harness** and therefore the ADR-0024 condition 4 *release gate* — that binds Sprint 050.
- **Any change to Sprint 048's Exit/Risk work** — `BracketExitModel`, `EquityPercentRiskModel`, `PriceBracketExit`, the bracket kernel, `BarSequentialSimulator`, or the two new catalog components. This sprint composes no strategy at all (see §4 Finding 8).
- **Tree and neural model families, and the version-pinned joblib format they will need.** A promotion attempt on those families is a *refusal with a clear message*, not a TODO.
- **ONNX or any other cross-library exchange format.**
- **Reopening ADR-0023 §4** — purge/embargo, dataset fingerprinting and availability on the labelled matrix are inherited locks.
- **A model registry, lifecycle states, promotion workflow tooling, or a serving API.**
- **New estimator families, new features, new metrics, cross-sectional studies, SHAP.**
- **Promoting more than one artifact per run.**

---

## 4a. What reconciliation and the maintainer's answers changed

| Was (pre-PRD plan) | Now |
|---|---|
| Q1 open: joblib / ONNX / parameter file | **CLOSED: framework-owned parameter file, pure NumPy, linear+logistic only** |
| Q3 open: last fold / final refit / per-fold as-of | **CLOSED: the last walk-forward fold** |
| Parity tolerance TBD | **Q7 ANSWERED: exact for linear; `rtol=0, atol=1e-15` for logistic `y_proba` ONLY, in Path A only. The release gate (offline==online) stays exact.** Maintainer **overruled** the architect's "exact-or-drop-logistic" recommendation in order to keep both families in v1 |
| Path A entirely in the gated `ml` job | **The evaluator exactness suite moves to default CI**; only the extraction adapter, the workflow and the sklearn cross-check stay in the `ml` job |
| Serializer/loader for "the chosen format" (T006) | Split: a **domain NumPy evaluator** (T006a, default CI) and a **blob-read + extraction adapter** (T006b, `ml` job) |
| Version guard = library+version equality at load | **Re-aimed:** load-time guard = format version + family + preprocessing step + feature count. Training-library version is provenance only. **A NEW promotion-time sklearn version guard is added** as a consequence of Q2 |
| Q2 open | **ANSWERED: extract from the existing blob**, one-time promotion-time read, no re-fit, no Phase 10 pipeline change. Consequence: **promotion needs the `ml` extra**; inference still needs nothing |
| Q4 open (default: script only) | **ANSWERED: `trading-cli research promote`** under the existing `research` group |
| Q8 open | **ANSWERED: move** `FittedNumpyPreprocessor` into `research/predictive/`; not copied, allow-list not widened |
| Q9 open | **ANSWERED: fitted parameter values stay out of the fingerprint** |
| Runtime needs `ml` installed (possible) | **Runtime needs no extra, ever.** Sprint 050's deployment footprint is zero |

---

## 4. Findings — read before Wave 0 is signed off

### Finding 1 — promotion contradicts an ACCEPTED ADR, so an ADR is mandatory

ADR-0023 §7 reads, verbatim: "Reproduce by re-fitting from the manifest — never
by deserializing a blob" and "No workflow may depend on reloading a fitted
blob." The same policy string is written into every run's `manifest.json`.

**Q2's answer makes this contradiction sharper, not softer.** Had promotion
re-fitted the fold, §7 would barely have been brushed. Extracting from the
existing blob **is** a workflow that reloads a fitted blob — precisely the thing
§7 forbids. ADR-0029 §7 therefore amends it explicitly and narrowly: one
workflow, one read, one purpose, operator-triggered; every other workflow still
reproduces by re-fitting; the run manifest's policy string is untouched.

**Consequence:** ADR-0029 is ACCEPTED, so this is satisfied — but the ADR must
be on the sprint branch before Wave 1 starts, and `reviewer` should treat any
implementation that widens the amendment as a Critical finding.

### Finding 2 — condition 2 presupposes an executor mechanism whose existence is unverified

ADR-0024 condition 2 says inference-time availability must be enforced "by the
same executor validation that already rejects a non-causal read for rule-based
components (ADR-MA-009 'engine responsibilities')." ADR-MA-009's stated engine
responsibilities are warm-up extension, output length/range validation, and
warm-up metadata — **not** per-feature `available_at` enforcement at read time.

**Consequence:** S049-T001 is a spike producing a written finding. It sizes
Sprint 050 and may require ADR-0030. It does not change Sprint 049's scope and
ships no code.

### Finding 3 — the format is a parameter file, and the runtime needs no extra

Verified while reconciling:

- **NumPy is a default-install dependency** (`pyproject.toml:15`), not an extra.
- **`research/predictive/` already imports NumPy** in five modules — the
  evaluator can live in the **domain layer**, which is where Sprint 050's Market
  Analysis component must reach it from.
- **`FittedSklearnPreprocessor.statistics()`** already emits JSON-stable
  `impute_median` / `standardize_mean` / `standardize_scale` per column.

The residual risk is not "which format" but Finding 7.

### Finding 4 — the last walk-forward fold is promoted

Documented limitation (T013): the last fold's TRAIN window ends before the last
TEST window, so the promoted artifact is already stale by one fold at promotion
time. Accepted deliberately, in preference to a final refit whose out-of-sample
performance would be by construction unmeasured.

### Finding 5 — S044_GATE §1.4 / §1.5 are unsatisfied and bind Sprint 050

No real-data candidate model exists; no named robustness plan exists.

```text
These are PREREQUISITES TRACKED OUTSIDE THIS SPRINT, not blocking tasks inside
it. No task in §6 depends on either. They gate Sprint 050 and the PRD's success
metrics 2 and 3. Recorded as Q5/Q6 in the Wave 0 document.
```

### Finding 6 — a pure-NumPy fitted preprocessor already exists, in the wrong package

`infrastructure/ml/torch/preprocessing.py` (D-S043-15) already contains
`FittedNumpyPreprocessor` / `fit_numpy_preprocessor`: a complete NumPy-only
implementation of `IMPUTE_MEDIAN -> STANDARDIZE`, importing neither sklearn nor
torch. It is already the evaluator's preprocessing half.

**Resolved by Q8: it MOVES into `research/predictive/`**, with the torch adapter
importing it downward. Not copied (a second copy drifts silently), and the
boundary allow-list is not widened. The churn to Sprint 043's torch path and
tests is expected and approved.

### Finding 7 — "exact match" names two different comparisons, and Q7 answered which bar applies where

```text
Comparison 1  OFFLINE vs ONLINE   — the PRD's release gate, Sprint 050 Path B
    NumPy evaluator (research)  ==  NumPy evaluator (dry-run runtime)
    Same code, same artifact. EXACT, unconditionally.

Comparison 2  NUMPY vs SKLEARN    — this sprint's Path A (T010b)
    NumPy evaluator  ==  predictions.parquet, produced by sklearn
    Different implementations. sklearn's logistic predict_proba uses
    scipy.special.expit, which need not agree bit-for-bit with a NumPy sigmoid.
```

**Q7's answer:** keep both families in v1; exact for linear, and a documented
ulp-bounded tolerance for the logistic probability. This **overruled** the
architect's recommendation. Because `predictions.parquet` carries `y_pred` and
`y_proba` separately, the tolerance lands on exactly one column of one family —
see D-S049-06's table, which T010b implements literally.

### Finding 8 — NEW: Sprint 047/048's delivered work does not collide with this sprint, and improves its successor

Checked as part of the rebase onto current `main`, which now contains Sprint 047
(`strategy_file` loader, ADR-0027) and Sprint 048 (`BracketExitModel`,
`EquityPercentRiskModel`, `PriceBracketExit`, the njit bracket kernel,
`volatility.range_expansion`, `trend.ema_distance`, three example strategies —
ADR-0028 ACCEPTED).

**No incompatibility, and nothing to redesign.** Sprint 049 composes no
strategy, touches no simulator, and ships no Signal/Exit/Risk model — its whole
output is an artifact file plus an evaluator. The two bodies of work do not
overlap at any file.

Two things worth recording rather than losing:

- **The PRD's success metric 2 got materially easier.** It requires the
  promoted model to run in dry-run "composed via `strategy_file` with an
  Exit/Risk model." Before Sprint 048 the only available Exit/Risk models were
  the Sprint 013 placeholders (exit `N` bars after entry, constant size); a
  dry-run so composed would have been a weak demonstration. `BracketExitModel` +
  `EquityPercentRiskModel` now make that composition a realistic strategy. This
  is an improvement to **Sprint 050**, not a change to Sprint 049.
- **One thing for Sprint 050 to check, not this sprint:** ROADMAP §13E records
  that the Robustness delay stress still *rejects* bracket exits
  (TD-027). The PRD's success metric 3 requires Phase 7 robustness on the
  promoted-model strategy. If that strategy uses `BracketExitModel`, the
  robustness plan (Q6) must account for TD-027 rather than assume every stress
  dimension is available. **Flagged for Sprint 050's planning; no action here.**

---

## 5. Boundaries this sprint must not cross

```text
Unchanged     market_analysis/ in its entirety
Unchanged     execution/runtime/ and application/execution/
Unchanged     run_predictive_research and the Phase 10 run pipeline (D-S049-14)
Unchanged     Sprint 048's Exit/Risk work: BracketExitModel, EquityPercentRiskModel,
              PriceBracketExit, kernels/bracket.py, BarSequentialSimulator, and the
              volatility.range_expansion / trend.ema_distance catalog components
Unchanged     ADR-0023 §4 leakage policy
Unchanged     research/predictive/ stays free of sklearn / xgboost / lightgbm /
              catboost / torch (NumPy is a default dependency, not an ML extra)
Unchanged     apps/dashboard's ban on importing trading_framework (ADR-0022)
Unchanged     ml / ml-trees / dl stay out of the default install; CI stays network-free
Unchanged     the existing runs/{run_id}/ layout, manifest schema version, and blobs
Unchanged     the architecture boundary test's allow-list — NOT widened
Unchanged     the run manifest's artifact policy string
Amended       ADR-0023 §7 — one workflow, one read, one purpose (ADR-0029 §7)
Not built     any registry, lifecycle state machine, or serving API
Not built     tree / neural promotion, joblib promotion, ONNX — refused, not stubbed
```

If an implementation detail appears to require crossing one of these, that is a
STOP-and-ask with a fresh ADR, never a test edit.

---

## 6. Task breakdown

**15 tasks, 5 waves.**

### Wave 0 — Decisions and sizing (no production code)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S049-T001 | **Spike (no code):** answer Finding 2. Read `market_analysis/execution/executor.py`, `planning/planner.py`, `assembly/assembler.py`, `models/availability.py`. Determine whether the engine rejects a dependency read whose `available_at` postdates the consuming result's `detected_at`, and where. Produce `docs/planning/sprints/S049_AVAILABILITY_FINDING.md` | the finding names files and line-level call sites, not impressions; it states plainly whether ADR-0030 is needed; **no production file is modified**; if the mechanism is absent, the finding says so as a STOP-and-report | Wave 0 approval | DONE (#387) — verdict: mechanism absent, ADR-0030 needed |
| S049-T002 | **ADR-0029 — already written and ACCEPTED** (2026-09-02). The remaining work is to land it on the sprint branch together with the ROADMAP §13F splice and the `docs/adr/README.md` index row | the ADR file, the roadmap splice and the index row are consistent; the `Approved-by` line and the ACCEPTED status are preserved exactly as the maintainer gave them; the numbering note is present so a future reader is not confused by the earlier "Sprint 048 / Phase 13A" drafts | — (written) | DONE |

Wave 0 is DONE when `S049_WAVE0_DECISIONS.md` and ADR-0029 are on the sprint
branch and the maintainer has checked off D-S049-12.

### Wave 1 — The promoted-artifact contract and store (no ML library involved)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S049-T003 | `PromotedArtifactManifest` + `PromotedArtifactRef` in `research/datasets/promoted_artifact.py`: schema version, `artifact_fingerprint`, `run_fingerprint`, `dataset_fingerprint`, `fold_id`, ordered feature `OutputRef` list, `model_family`, `format` + `format_version`, `preprocessing_spec`, `estimator_spec`, `training_library` + `training_library_version` (**provenance only — NOT a load gate**), `created_at_utc` | round-trip test; a missing required field is a `ValidationError` naming the field; the feature list preserves declared order; a `model_family` outside the allow-list is a `ValidationError`; the docstring states why the training library version is recorded but not enforced at load, and points at the promotion-time guard that does enforce it; the module imports no ML library | T002 | DONE |
| S049-T004 | `compute_promoted_artifact_fingerprint(...)`: SHA-256 over canonical JSON of `run_fingerprint`, `fold_id`, `format`, `format_version`, `model_family`, ordered feature `OutputRef`s, `preprocessing_spec`, `estimator_spec`. Mirrors `compute_run_fingerprint`'s canonicalization exactly | promoting the same run+fold twice yields the same fingerprint; changing the format, fold, family, or feature ORDER changes it; **fitted parameter values are not hashed** (D-S049-05 / Q9) — asserted by a test that perturbs a coefficient without perturbing the fingerprint, with a docstring stating this is a deliberate identity choice | T003 | DONE |
| S049-T005 | `PromotedArtifactRepository` over `research/predictive_research/promoted/{artifact_fingerprint}/` (path helper in `infrastructure/storage/paths.py`). `write` refuses to overwrite; `read_manifest` loads the manifest **without** reading the parameter payload | write/read round-trip on tmp_path; a second `write` raises `FileExistsError`; `read_manifest` succeeds on a directory with a corrupt payload; **no registry, no index file, no lifecycle field** — asserted by a test that the directory contains exactly two files | T004 | DONE |

Depends on: Wave 0. No ML extra required.

### Wave 2 — The NumPy evaluator, the extraction adapter, and the workflow

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S049-T006a | **The pure-NumPy promoted-artifact evaluator** in `research/predictive/promotion/` (domain layer). Defines the `PromotedArtifactParameters` payload schema and `load_promoted_artifact(manifest, payload) -> PromotedPredictor` (structural `typing.Protocol`, `predict(features) -> np.ndarray`). Evaluation: impute median, `(x - mean) / scale`, `X @ coef + intercept`, and for logistic the sigmoid. **Includes the Q8 MOVE** of `FittedNumpyPreprocessor` / `fit_numpy_preprocessor` from `infrastructure/ml/torch/preprocessing.py` into the domain, with the torch adapter re-pointed at the new location | evaluates hand-written parameter fixtures to values computed independently in the test, never to its own output; feature-count/order mismatches raise a named error before any arithmetic; **the torch adapter and all Sprint 043 tests still pass after the move**; the module imports no ML library and runs in default CI with no extra; the architecture boundary allow-list is byte-identical to `main` | T005 | TODO |
| S049-T006b | **Blob read + parameter extraction** in `infrastructure/ml/promotion.py`. Adds the **loader that does not exist today** for the `serialize_artifact()` payload (`{"family", "estimator", "preprocessor"}`, where `preprocessor` is a raw fitted sklearn `Pipeline`), then extracts `coef_` / `intercept_` and reads the fitted statistics by wrapping the pipeline back into `FittedSklearnPreprocessor` and calling its existing `statistics()` — **no statistics logic is re-implemented**. Enforces the **model-family allow-list** and the **promotion-time sklearn version guard** (D-S049-07) | a fitted Ridge/ElasticNet/Logistic round-trips blob -> extract -> load -> predict; a tree/neural family raises `PromotedFamilyUnsupportedError` naming the family and its deferral; a run manifest whose `library_version` differs from the installed sklearn raises a named error **before** unpickling, and the message states that re-running the study is the remedy; extracted statistics equal `FittedSklearnPreprocessor.statistics()` exactly; sklearn and joblib are imported lazily, never at module level; **runs in the `ml` job** | T006a | TODO |
| S049-T007 | **Load-time format and family guard.** `load_promoted_artifact` refuses on: unknown `format_version`; `model_family` outside the allow-list; a `preprocessing_spec` step the evaluator does not implement; a feature-count mismatch between manifest and payload. Raises `PromotedArtifactFormatError` (new, `research/predictive/errors.py`) | each refusal asserts a specific error type and a message naming the offending value and the fingerprint; the guard **cannot be disabled by a flag** (asserted — no bypass parameter exists); it raises before any arithmetic; **a test documents that a training-library version difference does NOT refuse the load**, and its docstring states why that is safe here and points at the promotion-time guard | T006a | TODO |
| S049-T008 | `promote_predictive_run` in `application/predictive_research/promote_predictive_run.py`: given a `PredictiveRunRef` + storage root, select the **last fold**, run the promotion-time version guard, read that fold's blob once, extract, compute the fingerprint, write the store directory, return a `PromotedArtifactRef`. Refuses unsupported manifest schema versions and non-allow-listed families **before** doing any work | promoting a fixture run produces a directory whose manifest's `run_fingerprint` matches the source; the selected `fold_id` is the last fold and is stated in the manifest; a tree/neural run is refused and **writes nothing**; a version-guard failure is refused and **writes nothing**; **the source run directory is not modified** (asserted by hashing before and after); **runs in the `ml` job** (D-S049-09) | T006b, T007 | TODO |
| S049-T009 | **`trading-cli research promote`** (D-S049-15) as a subcommand of the existing `research` group in `apps/cli/src/trading_cli/commands/research.py`, reusing ADR-0026's config contract, plus a thin `scripts/predictive_research/promote_predictive_run.py` | the command promotes a fixture run end to end and prints the `artifact_fingerprint` and absolute directory; no business logic in either surface; **if a new module is needed on ADR-0026 Amendment 1's allow-list, that is a fresh amendment proposed to the maintainer — never a test-file edit** (STOP-and-ask); `OPERATOR_CLI.md` updated | T008 | TODO |

Depends on: Wave 1. **T006b and T008 require the `ml` extra** — promotion reads
a joblib blob. T006a and T007 do not, which is the point.

### Wave 3 — Parity (the sprint's headline outcome)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S049-T010a | **Evaluator exactness suite, DEFAULT CI** (`tests/unit/research/predictive/test_promoted_evaluation.py`): property tests over the NumPy evaluator against hand-constructed fixtures — exact expected values for the linear path, the logistic path, an all-NaN column, a zero-variance column (`scale == 1.0` substitution), a single-row matrix — plus repeat-evaluation determinism | every assertion is bitwise (`==` on float64), never `approx`; expected values are computed independently inside the test; **no ML extra installed** — this is the task that proves the runtime needs none, and it is the de-risking of the maintainer's named riskiest assumption that does not depend on sklearn agreeing | T007 | TODO |
| S049-T010b | **Path A replay test** (`tests/integration/predictive_research/test_promoted_artifact_parity.py`, `ml` job): build the synthetic CI fixture dataset (D-S039-CI-dataset), run Predictive Research with a ridge and a logistic estimator, promote, load, re-predict the same TEST rows, and compare against `predictions.parquet` keyed by `(entity_id, fold_id)` **implementing D-S049-06's bar table literally**: `y_pred` exact for all families; the logistic decision function `z` exact, asserted separately; `y_proba` for logistic only at `rtol=0, atol=1e-15` | every TEST row present in both is compared (a row-count assertion prevents a vacuously-passing empty join); the four bars are asserted separately, so a failure names which one broke; **the observed maximum `y_proba` deviation is measured and recorded** in the test output and the sprint Review; an observed deviation above the ceiling is reported as a parity DEFECT (STOP-and-report), never fixed by widening; a deliberately perturbed coefficient makes the test FAIL (mutation check) | T010a, T008 | TODO |
| S049-T011 | Determinism + refusal suite: (a) promoting the same run twice yields byte-identical manifests, byte-identical payloads and the same fingerprint; (b) an unknown `format_version` refuses to load; (c) a permuted feature order produces a different fingerprint and is not silently accepted; (d) a tree/neural family is refused at promotion; (e) a promotion-time version mismatch is refused and writes nothing; (f) `read_manifest` never reads the payload | all six cases assert a specific error type and message content, not just "raises"; docstrings state which ADR-0024 condition each verifies; (a) is stronger than a blob-based plan could promise — a JSON parameter file **must** be byte-reproducible | T010b | TODO |
| S049-T012 | Condition-coverage test mapping ADR-0024 conditions 1 and 5 to executable assertions: condition 1 — the fingerprint is present, immutable, derived from dataset + estimator spec + seed + fold + format; condition 5 — the store contains no registry artifact | a reviewer can point at one test file and see which ADR-0024 condition this sprint closes; conditions 2, 3 and 4-Path-B are explicitly listed as **NOT closed here** with a pointer to Sprint 050, in the module docstring | T011 | TODO |

Depends on: Wave 2. **If the sprint overruns, T012 is the first descope, then
T009. T010a and T010b are never dropped.**

### Wave 4 — Documentation and closure

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S049-T013 | `docs/reference/PREDICTIVE_PROMOTION.md`: what a promoted artifact is and is not; the parameter-file schema and store layout; the fingerprint derivation; **both guards** (load-time and promotion-time) and what to do when each fires; the **linear/logistic-only restriction and the deferred joblib path**; the last-fold policy and its one-fold staleness; **the two parity comparisons and why only one of them carries a tolerance**; and a loud statement that a promoted artifact is **not** a tradeable verdict. Update `research/predictive/CLAUDE.md` and `infrastructure/ml/CLAUDE.md` (the latter for the `FittedNumpyPreprocessor` move) | the store layout appears exactly once across all docs; a future agent learns both guard postures and the family restriction without opening ADR-0029; TD-022's disposition is stated in `TECHNICAL_DEBT.md` with its reason; TD-021 restated as deferred; **the deferred tree/neural joblib path gets a tracked owner** (TD or Idea Inbox entry) rather than living only as a PRD Non-goal | T012 | TODO |
| S049-T014 | Closure: flip ROADMAP §13F's 14A status, update `CURRENT_STATUS.md` §2/§6/§9/§11/§12, write the sprint Review, and record which ADR-0024 conditions remain open for Sprint 050, the S049-T001 verdict, **the measured maximum `y_proba` deviation from T010b**, and Finding 8's TD-027 flag for Sprint 050's robustness plan | `CURRENT_STATUS.md` never claims Phase 14 is complete; the ADR table gains ADR-0029 (and ADR-0030 if T001 concluded it is needed); the Review states plainly that no model has been promoted to a State, and whether Path A held at the locked bars — the single most important fact for Sprint 050's planning | T013 | TODO |

**Progress:** 5 / 15

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/predictive-promotion-planning` | Wave 0 locks + ADR-0029 + the ROADMAP §13F splice |
| 1 | `docs/inference-availability-enforcement-spike` | T001: the Finding 2 investigation, docs only |
| 2 | `feat/promoted-artifact-store` | T003–T005: contracts, fingerprint, repository |
| 3 | `feat/promoted-artifact-evaluation` | T006a + T007 + T010a: the NumPy evaluator, the `FittedNumpyPreprocessor` move, the load guard, and the exactness suite — **entirely in default CI, no extra** |
| 4 | `feat/promoted-parameter-extraction` | T006b: blob loader, extraction, family allow-list, promotion-time version guard |
| 5 | `feat/promote-predictive-run-workflow` | T008–T009: workflow + `trading-cli research promote` |
| 6 | `test/promoted-artifact-parity` | T010b–T012: Path A, determinism, condition coverage |
| 7 | `docs/predictive-promotion-guide` | T013–T014: guide, TD disposition, closure |

PR 1 is independent and can run in parallel with PR 2. **PR 3 is the sprint's
highest-information PR** — it delivers the evaluator plus proof it needs no ML
dependency, and it carries the `FittedNumpyPreprocessor` move, so it should be
reviewed with Sprint 043's torch tests in mind.

---

## 8. Acceptance criteria

1. ADR-0029 is on the sprint branch with its ACCEPTED status and maintainer-written `Approved-by` line preserved, and the ADR-0023 §7 amendment stays narrow — one workflow, one read, one purpose; research-run blobs remain non-reloadable by every other workflow and the manifest policy string is untouched.
2. `promote_predictive_run` turns an existing run into a content-addressed directory containing exactly a manifest and one parameter payload.
3. The `artifact_fingerprint` covers dataset, estimator spec, seed, fold, format, model family and ordered feature `OutputRef`s — and never the fitted parameter values.
4. Promoting the same run twice is byte-identical and fingerprint-identical.
5. **Both guards hold:** the load-time guard hard-fails on the four named conditions with no bypass anywhere in the API; the promotion-time guard refuses a blob read under a mismatched sklearn version and writes nothing. A *training-library* version difference does not refuse a **load**, and the reason is documented.
6. **Path A parity passes at D-S049-06's bars** — `y_pred` exact for all families, the logistic decision function exact, `y_proba` within `atol=1e-15` for logistic only — the observed maximum deviation is recorded, and a mutation test proves the assertions have teeth.
7. The fitted preprocessing statistics travel **inside** the promoted artifact as one unit with the estimator parameters, never re-implemented or re-fitted elsewhere.
8. **The evaluator imports no ML library and runs on the default install.** The architecture boundary test's allow-list is **byte-identical to `main`**, and all Sprint 043 torch tests pass after the `FittedNumpyPreprocessor` move.
9. Promotion of a tree or neural family is refused with a message identifying it as deferred, and the deferral has a tracked owner.
10. No file under `market_analysis/`, `execution/runtime/`, `application/execution/`, `apps/dashboard/`, the Phase 10 run pipeline (`run_predictive_research`), or Sprint 048's Exit/Risk and catalog work is modified.
11. No registry, lifecycle state, mutable pointer, index file, or serving API exists in the promotion store — asserted by a test.
12. `S049_AVAILABILITY_FINDING.md` states, with file and call-site references, whether the executor mechanism ADR-0024 condition 2 presupposes exists, and sizes Sprint 050 accordingly.
13. Documentation states plainly that a promoted artifact is not a tradeable verdict, that only linear/logistic families are supported in v1, that the `y_proba` tolerance applies to Path A only, and that ADR-0024 conditions 2, 3 and 4-Path-B remain open.
14. TD-022's disposition and TD-021's continued deferral are both recorded with reasons.
15. CI is green for all workspaces and for the `ml` job; default CI remains extra-free and network-free **and carries the evaluator exactness suite (T010a)**.
16. No new dependency of any kind was added — default or extra.

---

## 9. Dependencies

**Required:** ROADMAP §13F (Phase 14) approved. **Status: PROPOSED.**

**Required:** ADR-0029. **Status: ACCEPTED** (2026-09-02) — must be on the
sprint branch before Wave 1 starts.

**Required:** Sprint 044 on `main` (ADR-0024 + `S044_GATE.md`). **Satisfied** (#348).

**Required:** the `ml` extra for **T006b, T008 and T010b**. **Satisfied** (Sprint 040).

**Not required:** a real-data candidate model or a named robustness plan
(prerequisites tracked outside this sprint — Finding 5, Wave 0 Q5/Q6); network
access; any dashboard change; the `ml-trees` or `dl` extras; anything from
Sprint 047/048 (Finding 8 — no overlap).

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **The NumPy evaluator and sklearn disagree beyond the locked `y_proba` ceiling** | T010b asserts the four bars separately and **measures** the deviation, so a failure names exactly which bar broke. Exceeding the ceiling is a STOP-and-report, never a widening. T010a proves the evaluator is exactly self-consistent regardless, so the PRD's actual release gate stays de-risked even if the sklearn cross-check concedes. |
| **A reader later mistakes the `y_proba` tolerance for a weakening of the release gate** | D-S049-06, ADR-0029 §6, and T013 all state the two comparisons separately and explicitly; T010b asserts the decision function `z` exactly, so the tolerance provably covers only the sigmoid. |
| The framework's `predict` silently drifts from sklearn's as the library evolves | T010b is the drift detector on every `ml` CI job; the promoted family set is three closed-form expressions. |
| **The `FittedNumpyPreprocessor` move breaks Sprint 043's torch path** | The move is a locked Wave 0 decision, not an in-task improvisation; T006a's acceptance requires the torch tests to pass, and PR 3 is reviewed with that in mind. |
| **Promotion needs the `ml` extra and a version guard** (a consequence of Q2) | Stated explicitly in D-S049-14 and D-S049-09; promotion is an offline operator act, so the asymmetry (promotion needs `ml`, inference needs nothing) is deliberate and documented. |
| A scikit-learn upgrade strands old runs, making them un-promotable | Accepted and documented: the remedy is re-running the study. Already-promoted artifacts are unaffected. |
| The linear/logistic restriction is discovered after someone trains a tree model | T006b refuses with a deferral message; T008 refuses before writing anything; T013 documents the restriction. |
| Promotion becomes a registry by accretion | Acceptance criterion #11 with a test, not a principle in prose. |
| **The plan drifts against `main` again while it waits for approval** | This plan was already re-based once (18 commits behind, colliding with a real Sprint 048). Finding 8 records the check; a re-check against `main` is cheap and should be repeated if approval is delayed. |
| A synthetic-fixture artifact is mistaken for a tradeable model | Q5/Q6; T013's "not a verdict" statement; this sprint promotes nothing to a State. |

---

## 11. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest

uv sync --extra ml
uv run pytest tests/integration/predictive_research -q

uv sync --extra dl
uv run pytest -m torch -q

uv run pytest tests/unit/test_architecture_boundaries.py -q
```

The `dl` block is new for this sprint and is **not** optional: the
`FittedNumpyPreprocessor` move (Q8) touches Sprint 043's torch path, so those
tests must be run even though this sprint adds no neural capability. The last
line is called out separately because "the evaluator imports no ML library and
the allow-list is byte-identical to `main`" is acceptance criterion #8.

---

## 12. Post-sprint direction

**Sprint 050 — Model-Backed Market Analysis State (Phase 14B).** Not opened
here. Its deployment shape is known (zero extras); its remaining unknowns are
S049-T001's finding and Path A's outcome. Directionally:

- the model component (`ComponentKind.STATE`) whose `artifact_fingerprint` is a
  `STR` parameter — landing it in `CanonicalParameters` -> `Lineage.parameters`
  -> cache identity for free (conditions 1 and 3 in one stroke),
- `component_dependencies(parameters)` resolved from the promoted manifest's
  ordered feature `OutputRef` list — requiring the promotion store to be
  reachable at **planning** time, a seam that does not exist today,
- a registry-injection seam in the dry-run runtime:
  `application/execution/local_btc_futures.py` constructs
  `StrategyModelLiveSignalEvaluator(strategy_model=...)` with no registry, so it
  falls through to `default_mvp_registry()` — a model component is unreachable
  from the live path until that is parameterized,
- condition 2's enforcement, sized by S049-T001, possibly with ADR-0030,
- **Path B** — Comparison 1, exact and with no inherited tolerance — as a
  release gate,
- composition via `strategy_file` (ADR-0027) against BTC futures **using Sprint
  048's `BracketExitModel` / `EquityPercentRiskModel`** (Finding 8), and the 3–5
  day dry-run session that is the PRD's success metric 2,
- S044_GATE §1.4 / §1.5 satisfied or explicitly waived-with-reason (Q5, Q6), and
  a named downstream Phase 7 robustness plan — the PRD's success metric 3 —
  **which must account for TD-027** (the Robustness delay stress still rejects
  bracket exits).

Other candidates: **the deferred joblib path for tree/neural promotion**;
**extracting parameters at run time** (ADR-0029's Follow-up — it would retire the
§7 amendment's exception entirely); extending Predictive Research itself (the
maintainer's stated next priority); report/dashboard extensions; cross-sectional
studies; SHAP.
