# Sprint 052 — Real-Data BTC Predictive Study (Phase 15B)

## Metadata

```text
Sprint: 052
Phase: Phase 15 — Predictive Research Catalog Expansion and Real-Data Study;
       increment 15B (closing increment)
Status: APPROVED (2026-09-08) — Wave 0 Checklist signed off
        (S052_WAVE0_DECISIONS.md D-S052-11). Gate condition satisfied: Sprint
        051 is complete and merged to `main` (#409), and
        docs/planning/sprints/S051_BTC_DATA_INVENTORY.md records a usable
        published BTCUSDT.P dataset (911 days, 1,311,840 rows, zero gaps).
        `engineer` may start S052-T001.
Planned Start: 2026-09-08 (`sprint/btc-predictive-study` cut from `main` @
        6cb0826, S052-T001 landed same day)
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
  - docs/planning/roadmap/PHASE_15_PREDICTIVE_CATALOG.md (§13G) — APPROVED
    (corrected 2026-09-08; formerly ROADMAP_INCREMENT_PHASE_15.md, spliced
    into ROADMAP.md and then extracted to this file by a roadmap
    defragmentation pass — same decision, moved location)
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

**CORRECTION (2026-09-08, post-T003 STOP — see the T003 outcome note under
Wave 1 above).** This finding's central claim was wrong:
`PredictiveStudySpec.evaluation_timeframe` is validated **source-or-finer**
(`validate_evaluation_timeframe`, `ADR-MA-012` "Timeframe roles" —
Evaluation, not Computation), not source-or-coarser. It is not a
no-code-change knob for coarsening the study's own row grid; the actual
per-feature coarsening role (`ComponentRequest.computation_timeframe`) is
not wireable from `PredictiveStudySpec` today and wiring it would itself be
a forbidden `research/predictive/` change (§5). `S052_WAVE0_DECISIONS.md`
D-S052-03/D-S052-04's corrections (2026-09-08) adopt option (a) from the
T003 STOP note instead: `V` is corrected to `1m` (matching source), the
range is kept exactly as signed off, and the ten frozen components'
evaluation-bar-denominated parameters are scaled x15 (D-S052-05's
correction) to hold their wall-clock window constant. A diagnostic
benchmark of the full-range 1m matrix build (~45s wall-clock, ~5.3GB peak
memory) confirmed no range trim is needed for cost reasons either.

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
| S052-T001 | Land `S052_WAVE0_DECISIONS.md`, including the **fold plan computed from `S051_BTC_DATA_INVENTORY.md`**: evaluation timeframe, label kind and horizon, `fold_count`, `test_span`, `embargo_span`, `min_train_rows`, mode, and the exact feature list | every number traces to a measured value in the inventory (the range is fixed by D-S051-07, but the row count and gap list are not assumed); `embargo_span >= label horizon` is shown arithmetically; the resulting per-fold TEST windows are listed as concrete date ranges with their approximate row counts; the document states the minimum row count below which the study is declared under-powered and NOT run; the dataset is `BTCUSDT.P` and nothing else | Sprint 051 closed with a usable BTC inventory; maintainer approval | DONE |

**S052-T001 outcome (docs-only, `docs/btc-predictive-study-planning`):** the
fold plan is confirmed, **not corrected** — D-S052-03's "expected
instantiation" (`V=15m`, `BINARY` label/1h horizon for the classification
pass, `forward_return`/`FORWARD_RETURN` over the same 1h horizon for the
regression pass, `F=6`, `T=30d`, `E=1d`, `M=2000`) matches the measured
`S051_BTC_DATA_INVENTORY.md` facts (911 days, 1,311,840 rows, zero gaps) with
wide margins on every LOCKED bound: initial TRAIN is ~726 days (725 days
23:59:00 exactly, ~23.9 months, vs. the 12-month floor), `embargo_span` is
24x the label horizon (applies identically to both passes, since they share
one horizon), and the measured 1,311,840-row / 911-day dataset is more than
double the computed 632,160-row / 439-day under-powered floor. The study is
**NOT under-powered** — the per-fold TEST windows, the arithmetic, and the
floor derivation are recorded in `S052_WAVE0_DECISIONS.md` D-S052-03.
D-S052-05's feature list is frozen at ten components (Sprint 051's six plus
the four suggested incumbents; family mix momentum:3/volatility:3/
statistics:2/trend:1/candle:1, no family over 30%), all confirmed present
under their suggested names in `registry/builtins.py` (read-only check; no
`research/predictive/` or `market_analysis/` file was touched).

**Reviewer follow-up (same PR, `docs/btc-predictive-study-planning`):** closed
one Warning — the original T001 pass locked the BINARY pass's label but left
D-S052-06's REGRESSION pass label undecided, a real judgment call that would
otherwise have fallen to T002. D-S052-03 now explicitly locks both passes'
label configuration (same horizon, `PredictiveTask=FORWARD_RETURN` for the
regression pass) before this goes to the maintainer. Three cheap Suggestions
were also folded in: the rounding note on the ~726-day figure, the family
tally on the frozen feature list, and a trimmed embargo-margin sentence.

**One item remains before T002/T003 may proceed:** the maintainer must review
and check D-S052-11's "fold table produced by T001 reviewed and accepted"
box — that box is intentionally left unchecked by this task, per D-S052-11's
own instruction that it is checked by the maintainer, not by an agent.

**Progress: 1 / 8.**

Wave 0 is DONE when the maintainer has checked off the Wave 0 Checklist.

### Wave 1 — The study, as declared configuration

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S052-T002 | Commit `apps/cli/examples/predictive/btc_momentum_regime_study.yaml` (the `PredictiveStudySpec`) and the baseline `EstimatorSpec` YAMLs, plus a network-free parse test | both files load through their own loaders (`load_predictive_study_spec`, the estimator loader) with no code change; the study's `definition_hash` is recorded in the file's header comment; the feature list matches Wave 0 exactly; `research_run_predictive.yaml`'s dangling `configs/predictive/...` reference is repointed at the real files (Finding 5); the test runs in default CI without the `ml` extra and without network | T001 | DONE |
| S052-T003 | **The baseline run** (maintainer-executed, `ml` extra): build the dataset, run the regression and the classification study, render both reports. Record run IDs, dataset fingerprint, seeds and wall-clock | the dataset builds through the **unmodified** `build_predictive_dataset`; fold role counts (TRAIN/TEST/PURGED/EMBARGOED) match Wave 0's plan within a stated tolerance and any deviation is explained, not adjusted away; both runs complete; **no file under a §5 forbidden path is modified** (asserted by a clean `git status` on `src/`); report HTML stays out of git | T002 | **STOP — see below** |

**S052-T003 outcome: STOP-and-report, per SPRINT_052.md §5's own instruction.**
Neither pass ran. `uv run trading-cli research run --config
apps/cli/examples/research_run_predictive.yaml` (regression pass, `ml`
extra confirmed installed: `sklearn==1.9.0`) and the equivalent config for
the binary pass both fail identically, in ~2s, before any fold assignment
or model fit, with:

```text
WorkflowError: 'research run predictive' failed: evaluation_timeframe
cannot be coarser than source timeframe: 15m vs 1m
```

This is raised by `RequestResolver.run_context` ->
`validate_evaluation_timeframe`
(`src/trading_framework/market_analysis/models/timeframes.py`), called from
`build_predictive_dataset` with `timeframe=spec.dataset_ref.dataset_id.timeframe`
(1m, the published BTCUSDT.P source) and
`evaluation_timeframe=spec.evaluation_timeframe` (15m, both committed T002
specs, D-S052-03/D-S052-04's `V=15m`). Both committed spec files are
byte-for-byte frozen per D-S052-05 and were not edited to investigate this
— reading the validator and its own docstring
(`"Ensure the evaluation grid is not coarser than the source dataset"`)
against `ADR-MA-012` §"Timeframe roles" is what identified the mismatch:

- `ADR-MA-012` documents **three** timeframe roles: Source, **Computation**
  (`ComponentRequest.computation_timeframe`, may be coarser than source —
  the actual per-feature resample knob) and **Evaluation**
  (`RunAnalysisRequest.evaluation_timeframe`, defaults to source and is the
  grid results are aligned back onto — the ADR's own words: "align results
  onto a finer evaluation grid without look-ahead"). `PredictiveStudySpec.
  evaluation_timeframe` feeds directly into this run-level Evaluation role,
  not the per-component Computation role.
- Wave 0's Finding 3 / D-S052-04 (`SPRINT_052.md` §4, `S052_WAVE0_DECISIONS.md`
  D-S052-04) describes `PredictiveStudySpec.evaluation_timeframe` as "the
  existing, no-code-change knob" for evaluating on a grid **coarser** than
  the 1m source, specifically to keep the ~1.31M-row 1m import's row count
  and memory footprint sane. The code enforces the opposite: the run-level
  evaluation grid must be **no coarser than** the source. No committed
  regression, unit, or spec-parse test (`test_spec.py`,
  `test_build_predictive_dataset.py`) exercises
  `evaluation_timeframe` strictly coarser than the dataset's source
  timeframe — every existing fixture uses `1m`/`1m` or an explicit
  same-or-finer pair, which is why this was never caught before real data
  and a real 15m/1m pair reached the pipeline.
- **No file under any §5 forbidden path was modified to investigate or
  work around this** — `git status` on the full working tree (not just
  `src/`) is clean; only reads. No attempt was made to patch
  `market_analysis/`, `research/predictive/`, or
  `application/predictive_research/`, and none was made to loosen the
  committed spec files, weaken the fold plan, or invent a different
  evaluation timeframe on the spot — any of those would themselves be
  scope violations (unmodified pipeline; frozen D-S052-05 feature/grid
  plan).
- **Consequence:** Wave 0's fold-plan arithmetic (D-S052-03, `S052_BTC_DATA_
  INVENTORY.md`-derived row counts, the ~87k 15m-evaluation-row estimate)
  assumed a working coarsening path that does not exist at the
  `PredictiveStudySpec` level today. The actual, working coarsening
  mechanism (`ComponentRequest.computation_timeframe`, per feature) does
  not reduce the run's own output row count the way a run-level
  `evaluation_timeframe` was assumed to — components would compute on a
  resampled 15m view, but the labelled feature matrix and fold assignment
  would still run over the full 1m grid (~1.31M rows), which is exactly
  the memory/wall-clock risk Finding 3 was written to avoid.
- **This is a Wave 0 replanning question, not an engineering workaround.**
  It requires deciding, with maintainer sign-off, one of: (a) re-derive the
  fold plan and both committed specs with `evaluation_timeframe` left at
  `1m` (matching source) and accept the full 1m row count/memory cost,
  (b) find or add a supported, no-pipeline-change way to reduce the study's
  own row grid before folding (not identified in the current code by this
  read), or (c) treat this as a genuine pipeline gap and open an ADR/TD
  entry proposing one. None of these is this task's call to make.

Recorded facts: no run IDs, no dataset fingerprint, and no fold role counts
exist for T003 — the failure occurs before `build_predictive_dataset`
reaches fold assignment. Total wall-clock across both failed attempts: ~4s.
`ml` extra was independently confirmed present (`sklearn 1.9.0`) so this is
not an environment/dependency gap.

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

**Progress:** 2 / 8 — Wave 0's fold plan (T001) is landed and maintainer-signed
off (D-S052-11's fold-table box checked). S052-T002 (`feat/btc-predictive-study-specs`)
commits the study/estimator YAML: because `PredictiveStudySpec.label` is a
single `LabelSpec`
(`src/trading_framework/research/predictive/spec.py`) and D-S052-06's Pass 1
declares one REGRESSION run and one BINARY run over the SAME fold plan and
feature list, the "one file" description above is delivered as **two**
`PredictiveStudySpec` files that are byte-for-byte identical except
`label.kind` —
`apps/cli/examples/predictive/btc_momentum_regime_study_regression.yaml` and
`..._binary.yaml` — paired with `btc_momentum_regime_ridge.yaml`
(`sklearn.ridge`) and `btc_momentum_regime_logistic.yaml`
(`sklearn.logistic`), both seed `42`. All four declare D-S052-05's frozen
ten-feature list and D-S052-03's locked fold plan (`EXPANDING`, `F=6`,
`T=30d`, `E=1d`, `M=2000`, `V=15m`) exactly, each `definition_hash` recorded
in its own header comment and asserted against the loader in
`tests/unit/research/predictive/test_btc_momentum_regime_study.py` (11 tests,
network-free, extra-free). `research_run_predictive.yaml`'s dangling
`configs/predictive/my_study.yaml` reference is repointed at the real
regression-pass pair (Finding 5); the binary pass is documented alongside it
in `apps/cli/examples/README.md` for an operator who wants that pass instead.
T003 (the baseline run) remains maintainer-executed with the `ml` extra.

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

**Required:** ROADMAP §13G approved — **satisfied** (APPROVED 2026-09-04;
now `docs/planning/roadmap/PHASE_15_PREDICTIVE_CATALOG.md` §13G after the
2026-09-08 roadmap defragmentation).

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
