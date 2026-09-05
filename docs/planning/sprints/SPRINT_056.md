# Sprint 056 — SampleSpec Foundation (Phase 16, Increment 16B)

## Metadata

```text
Sprint: 056
Phase: Phase 16 — Quant Research Workbench; increment 16B (SampleSpec Foundation)
Status: APPROVED (2026-09-04) — Wave 0 Checklist signed off, ADR-0031
        ACCEPTED. `engineer` may start S056-T001. Branch
        sprint/sample-spec-foundation not yet cut.
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: Phase 10 pipeline (Sprints 039-044, COMPLETE and CONSUMED),
            Phase 5 Signal Research semantics (Sprints 008-010, COMPLETE),
            ADR-0031 (PROPOSED — must be ACCEPTED before Wave 1 starts)
Does NOT depend on: Sprint 052's RESULT, Sprint 052 being open, or increment
            16A. The §13H.0 Q3 carve-out permits 16B to be planned and run in
            parallel with Sprint 052; 16A's REJECTED_LOW_SAMPLE verdict does
            not exist yet and nothing in this sprint may assume it does.
Depended On By: 16C (signal_occurrences samples), 16F (strategy_trades, which
            this sprint declares but does NOT implement)
Sprint Branch: sprint/sample-spec-foundation
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/sample-spec-foundation (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S056_WAVE0_DECISIONS.md
ADR: docs/adr/ADR-0031-predictive-sample-spec-and-task.md (PROPOSED, drafted
            with this plan — its acceptance is S056-T001 and gates Wave 1)
Numbering: verified against the docs/planning/sprints/ directory. 051-055 are
        taken (055 merged to main @ a004e8d); 050 stays RESERVED for Phase 14B
        and is not taken here. 056 is the first free number.
Architecture Sources:
  - docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md §13H.0, §13H.2, §13H.8,
    §13H.9 row 1, §13H.11, §13H.12 Q3 — AUTHORITATIVE for this increment
  - docs/planning/ROADMAP.md (Status: ACCEPTED) §13H stub
  - docs/adr/ADR-0023 §4 (leakage guards) and §8 (synthetic-only, network-free
    CI) — consumed as binding constraints, never relaxed
  - docs/adr/ADR-0024, ADR-0029 — untouched by this sprint, restated as limits
  - src/trading_framework/research/predictive/CLAUDE.md — the module's own
    import and leakage conventions
  - docs/planning/sprints/SPRINT_052.md §5 — the FORBIDDEN-paths list this
    sprint must not make impossible to satisfy
```

---

## 0. Slice choice — a contract sprint, planned as a behaviour-preserving one

16B ships a **contract**, not a result. The framework gains the ability to ask a
different question of the same pipeline; it answers none of them here. That
shapes the plan in three ways:

- **The `every_bar` default must be provably a no-op.** Not "roughly
  equivalent", not "same numbers" — the same `definition_hash` for every spec
  that exists today. That is a testable property and it is acceptance criterion
  1. It is also the sprint's entire non-interference story with Sprint 052
  (§5): a pipeline whose default behaviour is byte-identical cannot disturb a
  study that consumes it.
- **The new capability is one thin vertical slice**: a declared
  `signal_occurrences` sample resolves to real firings, builds a dataset, and
  the row count is *asserted* against the Signal Model's own occurrence table.
  Not a study, not a scorer, not a verdict.
- **Leakage is the deliverable, not a side-condition.** Irregularly-spaced rows
  are this increment's central technical risk (§13H.2). Wave 2 spends a whole
  task on it, and the guards may only be strengthened or left alone
  (ADR-0023 §4).

---

## 1. Sprint Goal

```text
PredictiveStudySpec today
  = DatasetRef + range + FeatureSpec[] + LabelSpec + split
  -> one row per evaluation bar, implicitly

PredictiveStudySpec after this sprint
  = DatasetRef + range + SampleSpec + PredictiveTask
    + FeatureSpec[] + LabelSpec + split
  -> sample: {kind: every_bar}          identical to today, identical hash
  -> sample: {kind: signal_occurrences} rows are a Signal Model's firings,
                                        count asserted against the occurrence
                                        table, provenance persisted
```

Success: a research question that used to require forking the pipeline is now a
three-line change in a YAML file, and the pipeline that answers the old question
is bit-for-bit the pipeline it was yesterday.

---

## 2. In scope

- [ ] `SampleSpec` (`every_bar`, `signal_occurrences`) and the `PredictiveTask`
      enum as declared contract types, with `strategy_trades` and
      `labelled_setups` present as **reserved names refused at load time**.
- [ ] `PredictiveStudySpec.sample` / `.task` fields with default elision from
      `to_dict()`, so today's specs keep today's `definition_hash` (ADR-0031).
- [ ] Load-time validation: the sample-kind x task compatibility matrix, with a
      named error for every refusal.
- [ ] Sample provenance persisted in the predictive dataset manifest (kind,
      task, resolved row counts and drop reasons) — for **both** kinds.
- [ ] Application-layer resolution of `signal_occurrences` from a declared
      Signal Model, reusing `evaluate_models` and
      `materialize_signal_occurrences` unchanged.
- [ ] The row-count identity assertion (occurrences in, candidate rows out).
- [ ] Purge/embargo correctness for sparse, irregularly-spaced rows, with tests
      that the existing guards still fire and are not weakened.
- [ ] One committed synthetic example spec + a network-free, extra-free parse
      test.
- [ ] Documentation: module conventions, the reference page, and ADR-0031.

## 3. Out of scope

- `strategy_trades` (16F), `labelled_setups`, `sessions_or_windows` sample
  kinds — **declared in the contract, not implemented, and refused at load**.
- Any new estimator family, extra, or dependency.
- MTF-capable `FeatureSpec` (§13G's separately-tracked structural gap).
- Any verdict artifact or verdict vocabulary (16A — which does not exist yet
  and may not be assumed by anything here).
- Any scoring path into Strategy Research (16C), any promotion, any dashboard
  change, any `MODEL_FAMILY_ALLOWLIST` diff.
- Running a real-data study of any kind. This sprint produces no research
  result and no claim about any market.
- Anything Sprint 052 owns: its specs, its write-up, its planning documents.

---

## 4. Findings — read before Wave 0 is signed off

### Finding 1 — purge/embargo is already datetime-based, so the risk is not where the roadmap text implies

`research/predictive/splitting.py` places fold windows with `timedelta`
arithmetic over `available_at`, and roles are decided by comparing
`available_at` / `label_end_at` against window bounds. There is **no bar
counting** in the split policy. §13H.2's "an embargo expressed in bars is not
the same guard it was" therefore describes a risk the code does not currently
have.

The real irregular-row exposure is elsewhere, and it is worse:

1. **`label_end_at` is grid-derived** (`matrix.py::_label_end_timestamps` walks
   `timestamps[index + horizon_bars]`). If a sample filter were applied to the
   frame *before* labelling, `label_end_at` would silently be computed over the
   *sampled* sequence — a 4-bar horizon over sparse firings could span weeks.
   Purge would then be computed against a fabricated label window. This is the
   leakage path this sprint must close by construction, not by test.
   **D-S056-05 forbids filter-early.**
2. **Row-count guards become live.** `_assign_one_fold` raises when a fold has
   zero TEST rows or fewer than `min_train_rows` TRAIN rows. With a selective
   signal these fire often and legitimately. They must stay errors
   (**D-S056-07**) — an under-powered sample is a reportable stop, not a reason
   to shrink the embargo.

### Finding 2 — the sample universe cannot be resolved inside `research/predictive/`

That package may not import `signal_model`, `strategy`, or `application`
(ADR-0023, `research/predictive/CLAUDE.md`; enforced by
`tests/unit/test_architecture_boundaries.py`, which walks every import node).
Resolving a Signal Model's firings requires exactly those.

So the split is: `research/predictive/` owns the **declaration** (`SampleSpec`,
`PredictiveTask` — pure data, no new imports) and accepts an already-resolved,
provenance-carrying row selection; `application/predictive_research/` owns the
**resolution** (it already imports `run_analysis`, and may equally import
`evaluate_models`). ADR-0031 §Decision fixes this; it is the one structural
decision in the sprint that is expensive to reverse.

### Finding 3 — `definition_hash` comparability is a Sprint 052 interface, not just a nicety

Sprint 052 T002's acceptance records the study's `definition_hash` in a
committed YAML header comment, and T007's reproducibility record depends on a
third party re-deriving it. If 16B adds `sample`/`task` keys unconditionally to
`PredictiveStudySpec.to_dict()`, every hash in the repo and in every persisted
manifest changes. **Default elision (ADR-0031) is what makes the two sprints
non-interfering**, and it is why acceptance criterion 1 is stated as byte
equality rather than "equivalent behaviour".

### Finding 4 — occurrence direction must be honoured, and it is cheaper than ignoring it

`materialize_signal_occurrences` already carries `direction`, and
`compute_forward_outcomes_for_horizons` already consumes it — Signal Research
has done this since Sprint 008. The current predictive matrix builder
synthesizes `direction="long"` for every bar because every bar has no direction.
Forcing occurrences to long would be *extra* code that mislabels every short
signal. 16B passes the occurrence's own direction through (**D-S056-06**) and
adds no bespoke outcome logic.

### Finding 5 — sample provenance is a bias-visibility requirement, not telemetry

Rows conditioned on a signal firing are a biased slice by construction
(§13H.2 risks). The mitigation named in the phase is *visible provenance*. That
means the dataset manifest, which is the artifact every downstream consumer
already reads, and it means provenance is written for `every_bar` too — "the
whole grid" is itself a sample choice, and a reader should not have to infer it
from a missing key.

---

## 5. Boundaries this sprint must not cross

```text
FORBIDDEN   any edit under infrastructure/ml/, research/predictive/promotion/,
            apps/dashboard/, research/strategy_research/, execution/
FORBIDDEN   any diff to MODEL_FAMILY_ALLOWLIST, ADR-0023, ADR-0024 or ADR-0029
FORBIDDEN   relaxing any leakage guard: purge, embargo, min_train_rows, the
            zero-TEST-rows error, or the available_at <= detected_at rule. They
            may be strengthened or left alone, never widened to make a sparse
            sample fit (ADR-0023 §4)
FORBIDDEN   filtering the analysis frame before labels and label_end_at are
            computed on the full evaluation grid (D-S056-05, Finding 1)
FORBIDDEN   implementing strategy_trades, labelled_setups or sessions_or_windows
FORBIDDEN   a new estimator family, extra, dependency, or component
FORBIDDEN   any test that reads real data, user_data/, or the network
            (ADR-0023 §8 untouched)
FORBIDDEN   -- SPRINT 052 REVERSE BOUNDARY (D-S056-02) --
            editing apps/cli/examples/predictive/research_run_predictive.yaml,
            any apps/cli/examples/predictive/btc_*.yaml,
            docs/reference/BTC_PREDICTIVE_STUDY.md,
            docs/planning/sprints/SPRINT_051.md, SPRINT_052.md,
            S051_*, S052_*, or ROADMAP §13F/§13G
FORBIDDEN   changing any DEFAULT behaviour of the Phase 10 pipeline. Sprint 052
            runs it unmodified; a new field with a non-eliding default IS a
            modification for its purposes
ALLOWED     research/predictive/ (new sample module + spec/matrix wiring),
            application/predictive_research/, research/datasets/predictive.py
ALLOWED     one new apps/cli/examples/predictive/*.yaml with a
            sample_/signal_ prefixed name, never a btc_ one
ALLOWED     docs/adr/ADR-0031, docs/reference/, docs/planning/sprints/
```

If the `signal_occurrences` slice cannot be built without relaxing a guard or
touching a forbidden path, **stop and report**. That finding is worth more than
the sample kind.

---

## 6. Task breakdown

**7 tasks, 4 waves.** Every task below was checked against
`PROJECT_MANAGEMENT.md` §14 Definition of Ready (§10).

### Wave 0 — The binding contract

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S056-T001 | Carry **ADR-0031** (`SampleSpec` contract shape + `PredictiveTask` taxonomy) through maintainer review to `ACCEPTED`, apply any corrections it attracts, and land the corresponding corrections in `S056_WAVE0_DECISIONS.md` | ADR-0031's status is `ACCEPTED` by an explicit maintainer statement (no agent flips it); `docs/adr/README.md`'s index row matches; every decision in `S056_WAVE0_DECISIONS.md` that the review changed is amended, and D-S056-01..09 are individually confirmed; no code is touched by this task | maintainer approval to open the sprint | **DONE** — 2026-09-04, maintainer reviewed the full plan and stated explicit approval in conversation ("Zgadzam się"); ADR-0031 accepted with no corrections; index row and Wave 0 checklist updated to match |

Wave 0 is DONE when the maintainer has checked off the Wave 0 Checklist
(`S056_WAVE0_DECISIONS.md` D-S056-10) **and** ADR-0031 is `ACCEPTED`.

### Wave 1 — The contract, with zero behaviour change

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S056-T002 | `research/predictive/sample.py`: `SampleKind`, `SampleSpec`, `PredictiveTask`; wire `sample` / `task` into `PredictiveStudySpec` with **default elision** in `to_dict()`; load-time validation of the kind x task matrix with named errors | every study spec fixture in the repo loads unchanged and yields a **byte-identical `definition_hash`** to the value produced on `main` (asserted against recorded values, not recomputed on both sides); an explicit `sample: {kind: every_bar}` + `task: FORWARD_RETURN` spec hashes **identically** to one that omits both; each of `strategy_trades`, `labelled_setups`, `sessions_or_windows`, `TRADE_OUTCOME`, `REGIME_CLASSIFICATION`, `VOLATILITY_FORECAST`, `NO_TRADE_FILTER`, `DISCRETIONARY_SETUP_CLASSIFICATION` raises a named `PredictiveSpecError` naming the owning increment; `research/predictive/` gains no new import (architecture boundary test green) | T001 | DONE — 2026-09-04, `feat/predictive-sample-spec-contract`; byte-identical hash asserted against a value recorded before the change; reserved names refused via `ReservedSampleKindError` / `ReservedPredictiveTaskError` (never a generic error), compatibility matrix refused via `IncompatibleSampleTaskError`; architecture boundary test green |
| S056-T003 | Persist **sample provenance** in `PredictiveDatasetManifest`: sample kind, task, resolved row counts and per-reason drop counts; additive field with a `PREDICTIVE_DATASET_SCHEMA_VERSION` bump and a documented read-compat rule for manifests written before it | an `every_bar` build records provenance stating the whole grid was used; the **dataset fingerprint is unchanged** by this task (it is derived from `definition_hash` + lineage + `dataset_ref` + range, and this is asserted); a manifest at the previous schema version still loads, or the refusal is explicit and documented — silent tolerance of an old manifest is not acceptable | T002 | **DONE** — 2026-09-04, `SampleProvenance` (kind, task, `universe_row_count`, `resolved_row_count`, `drop_counts`) added to `research/predictive/sample.py` (pure data, no new import) and persisted on `PredictiveDatasetManifest.sample_provenance` in `research/datasets/predictive.py`. `PREDICTIVE_DATASET_SCHEMA_V2` is additive over the existing `PREDICTIVE_DATASET_SCHEMA_VERSION` (v1), mirroring the read/write-version split `research/datasets/signal_research.py` already established for its own v1→v2 migration: v1 manifests still **load** (`sample_provenance is None`, tested directly against a hand-written legacy `manifest.json` with no `sample_provenance` key), while `PredictiveDatasetRepository.write` refuses a v2 manifest lacking `sample_provenance` (`ValidationError`, tested). `build_predictive_dataset` now writes v2 and always populates provenance; for `every_bar` this is `universe_row_count == resolved_row_count` with `drop_counts == {}`, stated explicitly rather than inferred from an absent key (Finding 5). Because `signal_occurrences` resolution does not exist until T004, `build_predictive_dataset` refuses (`PredictiveDatasetError`, tested) any spec declaring a `signal_occurrences` sample rather than silently building the whole grid under a manifest that would claim otherwise. The `signal_occurrences` provenance *shape* (round-trip, drop-count-sum validation) is covered by a manually constructed `SampleProvenance` fixture in `tests/unit/research/predictive/test_sample.py`, since T004's resolver does not exist yet — full pipeline coverage of that path is T004's job. Fingerprint independence is asserted directly: `compute_dataset_fingerprint` takes no `sample_provenance` argument, and two manifests sharing fingerprint inputs but carrying different provenance content produce the identical `dataset_fingerprint` (`tests/unit/research/datasets/test_predictive_fingerprint.py::test_dataset_fingerprint_unaffected_by_sample_provenance`). `research/predictive/CLAUDE.md` documents the convention. All existing manifest-constructing test fixtures elsewhere in the suite (leaderboard, promotion, ML runs) were left on v1 unmodified — the field is additive and optional, so they were unaffected. |

### Wave 2 — The new sample kind, and the leakage work

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S056-T004 | Resolve `signal_occurrences` in `application/predictive_research/`: `evaluate_models` -> emissions -> `materialize_signal_occurrences` -> a resolved row selection handed to the matrix builder, which **filters late** (after labels and `label_end_at` are computed on the full evaluation grid). `entity_id` becomes the `occurrence_id`; the occurrence's own `direction` is passed through | on a synthetic fixture, `candidate_rows` for the built dataset **equals** the occurrence table's row count over the same range and evaluation timeframe — asserted as an equality, not a bound (D-S056-08); every occurrence that did not become a labelled row is accounted for by exactly one reason in the exclusion counts, and the reasons sum to the occurrence count; a short-direction signal produces direction-adjusted `forward_return` identical to what Signal Research computes for the same occurrence; `research/predictive/` still imports no `signal_model` / `strategy` symbol | T002, T003 | **DONE** — `research/predictive/matrix.py::build_labelled_feature_matrix` now also returns `LabelledFeatureMatrix.candidates` (the full, unfiltered evaluation grid, additive field) so a resolver can read `label_end_at`/feature values/outcome status for one bar without re-deriving them from a filtered sequence; `label_expr` made public for reuse. New `application/predictive_research/resolve_signal_occurrences.py`: calls `evaluate_models` -> `materialize_signal_occurrences` (unchanged) to get the occurrence table, joins it against the already-labelled full grid (filter-late, D-S056-05), recomputes `forward_return`/`label` for the resolved subset with the occurrence's own direction via a second `compute_forward_outcomes_for_horizons` call (D-S056-06), and writes `entity_id = occurrence_id`. `build_predictive_dataset.py`'s hard refusal is replaced by this real dispatch; `BuildPredictiveDatasetRequest` gains `signal_model: SignalModelDefinition | None` (the caller supplies the resolved definition directly — no `signal_model_file` on-disk loader exists anywhere in the framework yet, a scope boundary flagged in the PR, not a shortcut taken silently). All D-S056-08 mechanism assertions (`candidate_rows == occurrences.height`, per-reason accounting, entity_id subset across folds), the direction-adjusted `forward_return` equality against a direct `compute_forward_outcomes_for_horizons` call, and the `label_end_at` structural-equality test between an `every_bar` and a `signal_occurrences` build (SPRINT_056.md sec8 AC5, T005's foundation) are covered by new tests in `tests/unit/application/predictive_research/test_build_predictive_dataset.py`. A pre-existing, broader "wave4" architecture test (`tests/unit/test_architecture_boundaries.py`) also forbade `application/predictive_research/` from importing `signal_model`/`strategy`, predating and conflicting with ADR-0031 Decision 3 / D-S056-04's already-accepted layering; narrowed to exclude that one path (still forbidding `research.simulation`/`execution` there, via a new dedicated test), not weakened or removed. `research/predictive/` gained no new import; `tests/unit/test_architecture_boundaries.py` stays green throughout. |
| S056-T005 | **Leakage under irregular spacing.** Tests and, only if a defect is found, fixes: fold roles for sparse rows are derived from `available_at`/`label_end_at` datetime arithmetic; `label_end_at` for a sampled row equals the value it had on the full grid; the zero-TEST-rows and `min_train_rows` guards still raise on an under-powered sparse sample; a purged row stays `PURGED` and an embargoed row stays `EMBARGOED` under the existing precedence | a test asserts `label_end_at` equality between the `every_bar` and `signal_occurrences` builds for rows present in both — this is the filter-late property, asserted directly; an under-powered sparse sample raises `PredictiveMatrixError` and the test asserts the **error**, not a degraded result; no guard threshold, span, or precedence rule is weakened anywhere in the diff (reviewable as a diff against ADR-0023 §4's rules); if a real leakage defect is found, it is fixed here and recorded — widening a guard to accommodate the new kind is forbidden | T004 | TODO |

### Wave 3 — Making it usable and closing out

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S056-T006 | One committed **synthetic** example: `apps/cli/examples/predictive/signal_occurrences_sample_example.yaml` plus a network-free, extra-free parse test; update `research/predictive/CLAUDE.md` conventions and the predictive reference page with the sample contract, the kind x task matrix, and the filter-late rule | the example loads through `load_predictive_study_spec` with no code change and its `definition_hash` appears in a header comment; the parse test runs in default CI without the `ml` extra and without network; **no `btc_*.yaml` and not `research_run_predictive.yaml` is touched** (D-S056-02, reviewable as a diff); the documentation states plainly that `strategy_trades` / `labelled_setups` are declared-and-refused and names 16F | T004 | TODO |
| S056-T007 | Sprint closure: the Review section, `CURRENT_STATUS.md` §2/§3/§6, and the 16B status flip in `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` (append, never rewrite) | every task above is `DONE` or explicitly recorded as not done with a reason; the closure states which of 16B's completion criteria (§13H.2) were met and names any that were not; it restates that **no verdict, no scorer and no study** was produced, so a reader cannot mistake 16B for 16A or 16C; any new problem or debt is logged in its own registry by its own owner, not summarized here | T005, T006 | TODO |

**Progress:** 4 / 7 — T001 done (ADR-0031 accepted, Wave 0 signed off); T002
done (SampleSpec/PredictiveTask contract, default elision, refusals); T003
done (sample provenance persisted in the manifest for both kinds, schema v2
bump, v1 read-compat, fingerprint independence asserted); T004 done
(`signal_occurrences` resolved for real in `application/predictive_research/`,
filter-late structural, direction passed through, row-count identity asserted
on a synthetic fixture). Wave 2's leakage task (T005) may now start.

**Descope order:** T006's example may shrink to the parse test alone. **T005 is
never dropped** — without it this sprint ships a new way to build a dataset with
no evidence that its leakage guards still hold, which is the one outcome that
would be worse than not shipping the sample kind at all.

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/sample-spec-contract-adr` | T001: ADR-0031 accepted, Wave 0 confirmed |
| 1 | `feat/predictive-sample-spec-contract` | T002: contract types, elision, refusals |
| 2 | `feat/predictive-sample-provenance` | T003: manifest provenance + schema bump |
| 3 | `feat/predictive-signal-occurrence-samples` | T004: the new sample kind, resolved and asserted |
| 4 | `test/predictive-irregular-row-leakage` | T005: the leakage evidence |
| 5 | `docs/predictive-sample-spec-usage` | T006-T007: example, docs, closure |

---

## 8. Acceptance criteria

1. **Every existing `PredictiveStudySpec` loads and produces a byte-identical
   `definition_hash`** under the `every_bar` default, asserted against recorded
   pre-sprint values.
2. An explicitly-declared `every_bar` spec is hash-indistinguishable from one
   that omits `sample` entirely.
3. A `signal_occurrences` study builds a dataset whose **candidate row count
   equals** the Signal Model's occurrence count over the same range and
   evaluation timeframe — an asserted equality with every drop accounted for.
4. Purge/embargo roles are shown correct for irregularly-spaced rows, and no
   leakage guard was relaxed anywhere in the sprint's diff (ADR-0023 §4
   strengthened or unchanged).
5. `label_end_at` for a sampled row equals its full-grid value (filter-late,
   D-S056-05).
6. Sample provenance is persisted for both kinds, and the dataset fingerprint is
   unchanged by its addition.
7. `strategy_trades`, `labelled_setups`, `sessions_or_windows` and every
   non-shipped `PredictiveTask` are **refused at load time with a named error**,
   covered by tests — not silently accepted no-ops.
8. `research/predictive/` gained no import of `signal_model`, `strategy`,
   `application`, or any ML library (architecture boundary test green).
9. ADR-0031 is `ACCEPTED` before any Wave 1 code merged.
10. CI stays synthetic-only and network-free; no new dependency, extra,
    estimator family or component was introduced (ADR-0023 §8 untouched).
11. No file on the Sprint 052 reverse-boundary list (§5, D-S056-02) was
    modified.
12. No research result, verdict, scorer or promotion was produced or implied.

---

## 9. Dependencies

**Required:** `ROADMAP.md` `Status: ACCEPTED` (it is) and Phase 16 approved (it
is, 2026-09-04) — but **not** Sprint 052 having run: the §13H.0 Q3 carve-out is
the entire basis for opening this sprint now.

**Required:** ADR-0031 `ACCEPTED` before Wave 1.

**Explicitly not required:** increment 16A (it does not exist; its
`REJECTED_LOW_SAMPLE` verdict may not be referenced as a mitigation by any task
here — see §10 Risk 3), Sprint 052 being open or closed, the `ml` extra, real
data, network access, any dashboard change.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **Leakage moves house with irregular rows** (the increment's central risk) | Finding 1 locates it precisely: not the embargo (already datetime-based) but `label_end_at` derivation and the row-count guards. D-S056-05 makes filter-late structural; T005 asserts it; §5 forbids weakening any guard. |
| **`definition_hash` churn breaks Sprint 052's reproducibility record** | Default elision (ADR-0031), asserted as byte equality in acceptance criterion 1, not as "equivalent". |
| **Small sample universes make folds unbuildable** — and 16A's `REJECTED_LOW_SAMPLE` verdict, the phase's named mitigation, **does not exist yet** | This sprint may not lean on 16A. Instead: the existing `min_train_rows` / zero-TEST guards raise a loud error (D-S056-07), and the sprint ships no automatic accommodation. An under-powered sample is a stop-and-report, and 16A can later classify it. |
| **Sample selection bias hidden from the reader** | Provenance persisted in the manifest for both kinds (T003, Finding 5), so "which rows and why" is a read, not an inference. |
| **Parallel-start collision with Sprint 052** | D-S056-02's explicit reverse boundary (§5), plus the behaviour-preserving default. Sprint 052's own FORBIDDEN list keeps it out of the pipeline; this list keeps 16B out of its outputs. Merge ordering to `main` remains the maintainer's call (D-S056-03). |
| **Scope creep into 16C/16F** | `strategy_trades` and `labelled_setups` are refused at load time by design, so the contract advertises the direction without inviting an implementation. |
| **The reserved-name list becomes a silent no-op surface** | Acceptance criterion 7 requires a *named error and a test* per reserved name. |

---

## 11. Quality gates

- `ruff`, `mypy`, `pytest` green; default CI stays network-free and extra-free.
- `tests/unit/test_architecture_boundaries.py` green — it is the enforcement of
  Finding 2 and is not to be amended to permit a new import.
- Each PR is one coherent outcome (`git-workflow`).
- No `user_data/` content, dataset bytes or run outputs enter git.

---

## 12. Post-sprint direction

16B unblocks 16C (Signal Quality Scoring), which remains gated on Sprint 052
having run (§13H.0 — the Q3 carve-out is 16B's alone). 16F inherits the
`strategy_trades` name this sprint reserves. Nothing here advances 16A, and this
sprint's closure must not imply it does.

---

## 13. Review

_(to be written at closure by `tech-writer`)_
