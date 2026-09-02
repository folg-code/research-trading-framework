# Sprint 052 — Real-Data BTC Predictive Study (Phase 15B)

## Metadata

```text
Sprint: 052
Phase: Phase 15 — Predictive Research Catalog Expansion and Real-Data Study;
       increment 15B (closing increment)
Status: PLANNED — requires maintainer approval. **Additionally gated:** this
        sprint may not open until Sprint 051 is complete AND
        docs/planning/sprints/S051_BTC_DATA_INVENTORY.md records a usable
        published BTCUSDT.P dataset. Its Wave 0 fold design is computed FROM
        that document and cannot be locked without it. Substituting another
        instrument to unblock it is forbidden (D-S052-03a).
Planned Start: TBD (after Sprint 051 closes)
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_051 (the six components + the BTC dataset inventory),
            SPRINT_039-044 (the Phase 10 pipeline this sprint CONSUMES unmodified),
            SPRINT_045 (the imported data)
Depended On By: SPRINT_050 (Phase 14B) — this sprint supplies, or explicitly
            fails to supply, its tracked "Q5" prerequisite (ROADMAP §13F)
Sprint Branch: sprint/btc-predictive-study
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/btc-predictive-study (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S052_WAVE0_DECISIONS.md
Numbering: verified against origin/main @ 5bd9969 (2026-09-02). Sprint 050 is
        reserved for Phase 14B by merged documents and is NOT taken here.
Architecture Sources:
  - docs/product/PRD-predictive-research-catalog-expansion.md — AUTHORITATIVE
  - docs/planning/ROADMAP_INCREMENT_PHASE_15.md (§13G) — PROPOSED
  - docs/planning/sprints/SPRINT_051.md + S051_WAVE0_DECISIONS.md
    (D-S051-07 and D-S051-07a inherited whole)
  - docs/planning/sprints/S051_BTC_DATA_INVENTORY.md — the measured input
  - docs/adr/ADR-0023 §4/§8/§9 — leakage guards, synthetic-only CI, one instrument
  - docs/adr/ADR-0024 + docs/planning/sprints/S044_GATE.md §1.4 — what a
    candidate model must clear before it may be considered for promotion
  - docs/planning/sprints/S049_WAVE0_DECISIONS.md D-S049-11 "Q5" — the
    prerequisite this sprint targets
  - docs/reference/RESEARCH_METHODOLOGIES.md
```

---

## 0. Slice choice — a research sprint, and it is planned like one

This sprint's deliverable is **a reported comparison**, not a positive result.
That distinction shapes everything below:

- Acceptance criteria are about *rigour and reporting*, never about the number
  going the right way. A study that shows the expanded catalog does not beat
  `RANDOM_PERMUTATION` on real BTC futures is a completed sprint.
- The pipeline is consumed, not built. If a task cannot be done without changing
  `research/predictive/` or `application/predictive_research/`, that is a
  STOP-and-report finding, not a task to absorb.
- The only conditional task (a second estimator pass) is bounded in advance, so
  "try one more thing" cannot become an open-ended search. Feature-set widening
  in response to a negative result is explicitly forbidden — that is exactly how
  spurious discoveries are manufactured, and it is the PRD's named risk.
- **The instrument is not a variable.** BTC data or no sprint (§4 Finding 1).

---

## 1. Sprint Goal

```text
S051_BTC_DATA_INVENTORY.md  (measured range, rows, gaps — BTCUSDT.P only)
    ↓ Wave 0 computes the fold plan FROM those numbers
PredictiveStudySpec (BTCUSDT.P, Sprint 051 components as FeatureSpecs)
  + EstimatorSpec (sklearn baseline first)
    ↓ build_predictive_dataset → run_predictive_research → analyze_predictive_run
    ↓ (all three UNMODIFIED)
per-fold + pooled comparison vs RANDOM_PERMUTATION
    ↓
docs/reference/BTC_PREDICTIVE_STUDY.md — the verdict, positive or negative
    ↓
ROADMAP §13F's "Q5" dependency line, updated with the answer
```

Success: the maintainer gets a straight, walk-forward-validated answer to "is
there structure here?", and the answer is written down either way.

---

## 2. In scope

- [ ] Wave 0 fold design computed from the measured dataset range.
- [ ] A committed `PredictiveStudySpec` YAML declaring the Sprint 051
      components (plus selected incumbents) as features on `BTCUSDT.P`.
- [ ] Committed `EstimatorSpec` YAMLs for the baseline pass.
- [ ] The baseline run: one regression and one classification study through the
      unmodified pipeline, with reports rendered.
- [ ] The `RANDOM_PERMUTATION` comparison, per fold and pooled.
- [ ] **Conditional and bounded:** one tree-family second pass, only under the
      Wave-0-defined trigger.
- [ ] `docs/reference/BTC_PREDICTIVE_STUDY.md` — the honest write-up.
- [ ] A network-free regression test that the committed spec files still parse.
- [ ] Reproducibility record: definition hash, dataset fingerprint, source
      `DatasetRef`, import-manifest fingerprint, run IDs, seeds.
- [ ] §13F Q5 disposition + `CURRENT_STATUS.md` + ROADMAP §13G closure.

## 3. Out of scope

- **Any change to `research/predictive/`, `application/predictive_research/`,
  `market_analysis/`, or Sprint 049's promotion code.** The pipeline is consumed.
- **Any instrument other than `BTCUSDT.P`** — see §4 Finding 1 and D-S052-03a.
- **Promoting anything.** Promotion is a separate, merged mechanism and the
  maintainer's own act.
- **New components.** If the study wants a feature that does not exist, that is
  an Idea Inbox entry and a future sprint.
- **Widening the feature set in response to a negative result.**
- Neural (`dl`) families; any estimator family beyond the Wave-0-locked set.
- Hyperparameter search beyond Phase 10B's existing bounded `CandidateSetSpec`.
- Any CI dependency on real data or the network (ADR-0023 §8 untouched).
- Multi-instrument, cross-asset, orderflow or options-derived features.
- Sprint 050 / Phase 14B planning.

---

## 4. Findings — read before Wave 0 is signed off

### Finding 1 — this sprint's input is produced by the previous sprint, and there is no substitute for it

`S051_BTC_DATA_INVENTORY.md` is a Sprint 051 deliverable, and Sprint 051's
acceptance explicitly permits it to record a *failed or impractical* import. If
it does, **this sprint does not open.**

```text
MAINTAINER DECISION (2026-09-02), inherited as D-S051-07a / D-S052-03a:
        NQ.c.0 — or any other non-BTC dataset — is REJECTED as a substitute.
        This is a HARD STOP, not a ranked fallback and not a soft preference.
        If BTC data is unavailable: STOP, and return to the maintainer.
        Do NOT run the study on another instrument to keep the sprint moving.
        Do NOT re-scope Phase 15B to a different instrument.
REASON (the maintainer's own): NQ does not satisfy ROADMAP §13F's Q5 wording
        ("... on BTC data"). Reporting an NQ study against Q5 would look like
        closing the prerequisite while not closing it — precisely the silent
        scope drift this project's governance exists to prevent.
```

The data range itself is no longer open: the maintainer fixed it at
`BTCUSDT.P`, 1m, **2024-01-01 → 2026-06-30** (D-S051-07), with the import's
wall-clock cost accepted as a priced, known cost. **Nothing in this plan assumes
the resulting row count or gap list** — every fold number below is a formula
over the inventory's measured values, deliberately.

### Finding 2 — the estimator family choice (PRD Open Question 3)

Recommended: **sklearn baselines first** (`ml` extra only), then one tree family
only if triggered.

- Cheapest to iterate: one already-installed extra, seconds-to-minutes fits,
  a small hyperparameter surface, and the least confounded read on whether the
  *features* carry anything.
- A regularized linear/logistic model that beats permutation out of sample on
  real data is a far stronger claim than a boosted tree doing the same, because
  it has much less capacity to fit noise. If it fails, that is informative; if a
  tree then succeeds where linear failed, the write-up can say specifically that
  the structure is non-linear.
- **A useful side effect, not a constraint:** Sprint 049's promotion v1 accepts
  linear and logistic families only (ADR-0029). If the baseline pass wins, the
  resulting candidate is *immediately promotable* and closes §13F's Q5 with no
  follow-up increment. If a tree wins, the operator hits ADR-0029's documented
  refusal and the deferred joblib path becomes the next question — which §13F
  already names as a risk. Either way the write-up states which case occurred.
  **This is not an estimator-family restriction**: the PRD forbids inventing
  one, and trees remain in scope under the Wave 0 trigger.
- Neural (`dl`) is excluded: highest iteration cost, largest tuning surface, and
  Sprint 043 already characterized those families on synthetic data. Nothing is
  learned about *this* question by adding them.

### Finding 3 — the evaluation grid is the answer to the 1m-noise problem

`PredictiveStudySpec.evaluation_timeframe` already lets a study evaluate on a
coarser grid than the source dataset's 1m bars, and
`build_predictive_dataset` passes it straight through to `run_analysis` while
component requests carry no computation timeframe (so components compute *on*
that grid). This is the existing, no-code-change knob for:

- keeping row counts and memory sane over the ~1.31M-bar 1m import,
- making Sprint 051's rolling higher moments (`statistics.return_distribution`)
  usable rather than outlier-dominated,
- giving the label horizon room to be economically meaningful.

Wave 0 locks the grid; under memory or wall-clock pressure the **range or grid**
moves — never the pipeline, and never the instrument.

### Finding 4 — `RANDOM_PERMUTATION` is a metric-layer comparator, not a family

It is computed inside the metrics layer per fold using `EstimatorSpec.seed`
(`research/predictive/CLAUDE.md`), and it appears as a leaderboard row rather
than as a registry family. So the comparison this sprint reports is already
produced by the unmodified pipeline — there is nothing to build, only something
to report correctly. `S044_GATE` §1.4's bar ("beats permutation on **every**
fold") is stricter than "beats it pooled"; the write-up must report both and say
which bar was cleared.

### Finding 5 — the study spec belongs in the repo, the data does not

`user_data/` is gitignored and maintainer-owned. The existing precedent for
committed, runnable configuration is `apps/cli/examples/*.yaml` — and
`research_run_predictive.yaml` currently points at `configs/predictive/my_study.yaml`,
a path that does not exist in the repo. This sprint commits real study and
estimator specs under `apps/cli/examples/predictive/`, which both makes the
study reproducible and fixes that dangling reference. No dataset bytes, no run
outputs, and no `user_data/` content are ever committed.

---

## 5. Boundaries this sprint must not cross

```text
FORBIDDEN   any edit under research/predictive/, application/predictive_research/,
            market_analysis/, infrastructure/ml/, or research/predictive/promotion/
FORBIDDEN   running the study on ANY instrument other than BTCUSDT.P. If the BTC
            data is missing or unusable, the sprint STOPS and returns to the
            maintainer (D-S052-03a). NQ.c.0 is not a fallback; it is a rejected
            substitute, and no agent may choose it
FORBIDDEN   a new component, a new estimator family, a new extra, a new dependency
FORBIDDEN   any test that reads real data, user_data/, or the network
FORBIDDEN   adding features after seeing a negative result (PRD's named risk)
FORBIDDEN   relaxing purge/embargo, fold count, or the horizon to improve a metric
FORBIDDEN   committing dataset bytes, run directories, or report HTML
ALLOWED     new YAML under apps/cli/examples/predictive/
ALLOWED     new documentation under docs/reference/ and docs/planning/
ALLOWED     a parse-only regression test for the committed specs
```

If the study cannot run without touching a forbidden path, **stop and report**.
That is a finding worth an ADR in its own right — it would mean Phase 10's
pipeline does not actually work on real data, which is precisely the kind of
thing a synthetic-only validation can hide.

---

## 6. Task breakdown

**8 tasks, 4 waves.**

### Wave 0 — Decisions, computed from measured facts

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S052-T001 | Land `S052_WAVE0_DECISIONS.md`, including the **fold plan computed from `S051_BTC_DATA_INVENTORY.md`**: evaluation timeframe, label kind and horizon, `fold_count`, `test_span`, `embargo_span`, `min_train_rows`, mode, and the exact feature list | every number traces to a measured value in the inventory (the range is fixed by D-S051-07, but the row count and gap list are not assumed); `embargo_span >= label horizon` is shown arithmetically; the resulting per-fold TEST windows are listed as concrete date ranges with their approximate row counts; the document states the minimum row count below which the study is declared under-powered and NOT run; the dataset is `BTCUSDT.P` and nothing else | Sprint 051 closed with a usable BTC inventory; maintainer approval | TODO |

Wave 0 is DONE when the maintainer has checked off the Wave 0 Checklist.

### Wave 1 — The study, as declared configuration

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S052-T002 | Commit `apps/cli/examples/predictive/btc_momentum_regime_study.yaml` (the `PredictiveStudySpec`) and the baseline `EstimatorSpec` YAMLs, plus a network-free parse test | both files load through their own loaders (`load_predictive_study_spec`, the estimator loader) with no code change; the study's `definition_hash` is recorded in the file's header comment; the feature list matches Wave 0 exactly; `research_run_predictive.yaml`'s dangling `configs/predictive/...` reference is repointed at the real files (Finding 5); the test runs in default CI without the `ml` extra and without network | T001 | TODO |
| S052-T003 | **The baseline run** (maintainer-executed, `ml` extra): build the dataset, run the regression and the classification study, render both reports. Record run IDs, dataset fingerprint, seeds and wall-clock | the dataset builds through the **unmodified** `build_predictive_dataset`; fold role counts (TRAIN/TEST/PURGED/EMBARGOED) match Wave 0's plan within a stated tolerance and any deviation is explained, not adjusted away; both runs complete; **no file under a §5 forbidden path is modified** (asserted by a clean `git status` on `src/`); report HTML stays out of git | T002 | TODO |

### Wave 2 — The comparison

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S052-T004 | Extract the verdict: run `analyze_predictive_run` and `compare_predictive_runs`, and tabulate the primary metric **per fold and pooled** against `RANDOM_PERMUTATION`, plus the train/test gap and the permutation-importance ranking of the Sprint 051 features | the table reports both `S044_GATE` §1.4's strict bar ("beats permutation on **every** fold") and the pooled result, and says explicitly which was cleared; the train/test gap is reported for every fold so an overfit win cannot be presented as a clean one; feature importances are reported for the new components specifically, so a null result can distinguish "the features were ignored" from "the features misled" | T003 | TODO |
| S052-T005 | **Conditional, bounded second pass.** Only if Wave 0's trigger fires (baseline neither clearly clears nor clearly fails the bar): one tree family (`ml-trees`), one `CandidateSetSpec` at the default cap of 8, same dataset fingerprint, same folds, same seed | if the trigger does not fire, this task is closed as NOT RUN with one sentence of reasoning — that is a valid outcome, not a skip; if it runs, the dataset fingerprint is identical to T003's (asserted, so the leaderboard is a like-for-like comparison); no third pass exists, no matter the result; no feature is added or removed | T004 | TODO |

### Wave 3 — The write-up and the disposition

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S052-T006 | `docs/reference/BTC_PREDICTIVE_STUDY.md`: the instrument, range and gaps; the fold plan; the feature list; the per-fold and pooled comparison table; the train/test gaps; the importance ranking; and **the verdict stated in one unhedged sentence** | a reader learns the answer in the first paragraph without inference; a negative result is stated as plainly as a positive one, with no "promising signs" language; the document names what would change the verdict (a different horizon, grid, or feature family) as *future options*, never as retroactive excuses; it states that Phase 10 metrics are a precondition and never a verdict that the model should trade (ADR-0024); the document describes a **BTC** study only (D-S052-03a) | T004, T005 | TODO |
| S052-T007 | **Reproducibility record** (a section of T006's document plus the spec header comments): study `definition_hash`, dataset fingerprint, source `DatasetRef` and its import-manifest fingerprint, run IDs, estimator specs and seeds, and the framework version | a third party with the same data can re-derive the same dataset fingerprint from the committed spec; the record states which artifacts live outside git (`user_data/`) and are therefore not reproducible from the repo alone | T006 | TODO |
| S052-T008 | Closure and **Q5 disposition**: update ROADMAP §13F's Q5 dependency line (append, never rewrite history), §13G's 15B status, `CURRENT_STATUS.md`, and the sprint Review | §13F's Q5 line states either "closed by run `<id>`, `<family>`" **or** "still open — reason", never something ambiguous; if closed, the entry states whether the winning family is promotable under ADR-0029 (linear/logistic) or hits its documented tree/neural refusal; if still open, it names S049 Wave 0's "option (b)" as the decision now facing Sprint 050 — and leaves that decision to the maintainer | T007 | TODO |

**Progress:** 0 / 8 — not started; sprint not approved and its input does not yet exist.

**Descope order:** T005 is conditional by construction. T007 may merge into T006.
**T004 and T006 are never dropped** — without them the sprint has run a model and
reported nothing, which is the one outcome that would waste the compute.

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/btc-predictive-study-planning` | T001: Wave 0 locks incl. the computed fold plan |
| 1 | `feat/btc-predictive-study-specs` | T002: committed study + estimator YAML, parse test, dangling-reference fix |
| 2 | `docs/btc-predictive-study-baseline` | T003–T004: run record and the comparison table |
| 3 | `docs/btc-predictive-study-tree-pass` | T005, only if triggered |
| 4 | `docs/btc-predictive-study-result` | T006–T008: the write-up, reproducibility record, Q5 disposition, closure |

---

## 8. Acceptance criteria

1. The fold plan was **computed from measured data facts**, and the document
   shows the arithmetic — no assumed row count or gap list appears anywhere.
2. The study and estimator specs are committed, parse in default CI, and carry
   their `definition_hash`.
3. The dataset build and both baseline runs completed through the **unmodified**
   Phase 10 pipeline, **on `BTCUSDT.P`**; `src/` is untouched.
4. The `RANDOM_PERMUTATION` comparison is reported **per fold and pooled**, and
   the write-up says which of `S044_GATE` §1.4's bar and the pooled bar was met.
5. Train/test gaps are reported per fold, so an overfit result cannot pass as a
   clean one.
6. Permutation importance is reported for the Sprint 051 features specifically.
7. The second pass either ran under the pre-declared trigger with an identical
   dataset fingerprint, or is recorded as NOT RUN with a reason. No third pass.
8. **No feature was added after seeing a result.** Reviewable as a fact: the
   feature list in the committed spec equals the Wave 0 list.
9. `docs/reference/BTC_PREDICTIVE_STUDY.md` states the verdict in one unhedged
   sentence, positive or negative.
10. ROADMAP §13F's Q5 line is updated unambiguously, and the promotability
    consequence (ADR-0029 family support) is stated.
11. ADR-0023 §8 is untouched: no CI test depends on real data or the network.
12. No new dependency, extra, component, or estimator family was introduced.

---

## 9. Dependencies

**Required:** ROADMAP §13G approved (**Status: PROPOSED**).

**Required:** Sprint 051 complete, **including a usable
`S051_BTC_DATA_INVENTORY.md` for `BTCUSDT.P`**. This is a hard gate: Wave 0 is
unlockable without it, and per D-S052-03a it may not be unblocked by
substituting another instrument (Finding 1).

**Required:** the `ml` extra (Sprint 040) for T003. `ml-trees` (Sprint 042) only
if T005 is triggered.

**Not required:** network access (the data is already local by then); the `dl`
extra; any dashboard change; Sprint 049's promotion mechanism; any new ADR.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **The study finds nothing, and the sprint feels like a failure** | Reframed in the goal, the acceptance criteria and the PRD: a rigorous negative result is the deliverable. T006's acceptance forbids hedging language in either direction. |
| **"One more feature" creep after a negative result** | §3 and §5 forbid it; acceptance criterion 8 makes it reviewable as a diff against the Wave 0 feature list. |
| **A win that is actually overfitting** | Purged/embargoed folds are inherited, not re-tuned; per-fold train/test gaps are mandatory reporting; the strict per-fold permutation bar is reported alongside the pooled one. |
| **The 1m data is too large for the in-memory pipeline** | Finding 3's `evaluation_timeframe` knob is locked in Wave 0 with a row-count estimate; Wave 0 also names the row count above which the range is trimmed rather than the pipeline changed. A pipeline change is a STOP-and-report. |
| **The data never arrives** (Sprint 051 T002 impractical) | The sprint does not open. Per D-S052-03a this is a **hard stop back to the maintainer**, not a prompt to substitute NQ.c.0 or any other instrument. |
| **A tree model wins and cannot be promoted** | Already anticipated by §13F's risk list and ADR-0029's deferral. T008 states the consequence rather than treating it as a surprise. |
| **The result is quietly used to justify trading** | T006 restates ADR-0024's rule: strong Phase 10 metrics are a precondition for promotion, never a verdict that a model should trade. Phase 7 robustness remains the separate, unwaived gate. |

---

## 11. Quality gates

- `ruff`, `mypy`, `pytest` green; default CI stays network-free and extra-free.
- The only new test is a parse-only spec regression — it must not require `ml`.
- `git status` on `src/` is clean at the end of every run task.
- Each PR is one coherent outcome.

---

## 12. Post-sprint direction

Phase 15 closes here. The maintainer's stated **third** ML/AI priority
(report/dashboard expansion for predictive results) becomes the next candidate
track, and Sprint 050 / Phase 14B proceeds with either a real candidate model or
S049 Wave 0's explicitly-labelled "option (b)".

Candidates raised but not taken: MTF-capable `FeatureSpec`, a second instrument
(which would be its own approved work with its own document, never an appendix
to this study), ATR-adjusted labels (deferred since D-S039-17), and the deferred
tree/neural promotion path (TD-029) if a tree family wins here.

---

## 13. Review

_(to be written at closure by `tech-writer`)_
