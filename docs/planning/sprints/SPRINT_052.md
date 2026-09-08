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
| S052-T003 | **The baseline run** (maintainer-executed, `ml` extra): build the dataset, run the regression and the classification study, render both reports. Record run IDs, dataset fingerprint, seeds and wall-clock | the dataset builds through the **unmodified** `build_predictive_dataset`; fold role counts (TRAIN/TEST/PURGED/EMBARGOED) match Wave 0's plan within a stated tolerance and any deviation is explained, not adjusted away; both runs complete; **no file under a §5 forbidden path is modified** (asserted by a clean `git status` on `src/`); report HTML stays out of git | T002 | DONE |

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

**Resolution (2026-09-08): option (a) adopted, maintainer-approved.**
`S052_WAVE0_DECISIONS.md` D-S052-03/D-S052-04/D-S052-05 now carry the
correction (`V` 15m -> 1m, range/F/T/E/M unchanged, the ten frozen
components' evaluation-bar parameters scaled x15 -- Option A). Both
committed T002 spec files were updated to match and their
`definition_hash` header values recomputed; the parse test
(`tests/unit/research/predictive/test_btc_momentum_regime_study.py`, 11
cases) passes against the corrected specs. A diagnostic benchmark of the
full-range 1m matrix build (~45s wall-clock, ~5.3GB peak memory) confirmed
the range does not need to be trimmed for cost reasons. **S052-T003 is
ready to be re-attempted** against the corrected specs; its Status above
returns to `TODO` for that re-attempt.

**S052-T003 outcome (re-attempt, 2026-09-08, `docs/btc-predictive-study-baseline-run`,
maintainer-authorized delegation): SUCCESS. Both baseline passes completed
through the unmodified Phase 10 pipeline.** `ml` extra confirmed present
(`sklearn==1.9.0`) before either run; nothing was installed. Both passes
were invoked as `trading-cli research run --config <path>` from the repo
root (`storage_root: user_data/workspace`), each preceded by a `--dry-run`
that printed the resolved plan and touched nothing.

```text
REGRESSION pass (ridge)
  config:               apps/cli/examples/research_run_predictive.yaml
                         (definition: btc_momentum_regime_study_regression.yaml,
                         estimator: btc_momentum_regime_ridge.yaml)
  dataset_id:            f9f042f9042bcafb
  dataset_fingerprint:   f9f042f9042bcafb26964c01e480d6df52af84b77f0cb9ea02d05911797c2867
  run_id:                f7ac893d54ae6b69
  seed:                  42 (sklearn.ridge, alpha=1.0)
  wall-clock:            3m40.581s (real; build + fit + persist + render)
  report:                user_data/workspace/research/predictive_research/runs/f7ac893d54ae6b69/report.html
                         (not committed -- user_data/ is gitignored)

BINARY pass (logistic)
  config:               scratch config, same shape as research_run_predictive.yaml,
                         pointed at definition: btc_momentum_regime_study_binary.yaml,
                         estimator: btc_momentum_regime_logistic.yaml (both already
                         committed at T002; the binary pass has no dedicated
                         committed CLI config per apps/cli/examples/README.md's
                         own note -- one was assembled ad hoc for this run only
                         and was not committed, matching D-S052-08's "COMMITTED"
                         list, which names only the spec/estimator YAML themselves)
  dataset_id:            98a893f56549c96b
  dataset_fingerprint:   98a893f56549c96b607d929d85ac2902ace4be86df73ab332b8ac9d7ace1117b
  run_id:                faa6983acd03f846
  seed:                  42 (sklearn.logistic, C=1.0) -- same seed as the ridge pass,
                         per D-S052-06's "same seed" requirement
  wall-clock:            3m34.293s (real; build + fit + persist + render)
  report:                user_data/workspace/research/predictive_research/runs/faa6983acd03f846/report.html
                         (not committed)
```

Both dataset manifests confirm `evaluation_timeframe: 1m`, the ten frozen
D-S052-05 features with their x15-scaled parameters, `label.horizon: 1h`,
`split: {mode: EXPANDING, fold_count: 6, test_span: 30d, embargo_span: 1d,
min_train_rows: 2000}`, and `source_dataset_ref:
BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1` -- i.e. exactly
D-S052-03/04/05's corrected plan, on `BTCUSDT.P` and nothing else. The two
dataset fingerprints differ (as expected -- `label.kind` differs between
the two `PredictiveStudySpec` files, so `definition_hash` and therefore
`dataset_fingerprint` differ), but the **fold role counts are identical
between the two passes**, confirming both were built over the same fold
plan and sample universe:

```text
per-fold role counts (both passes, byte-identical):
fold  test window                     TRAIN      TEST    EMBARGOED  PURGED
0     2025-12-26 -> 2026-01-25      1,043,820   43,200     1,440      60
1     2026-01-26 -> 2026-02-25      1,087,080   43,200     2,880       0
2     2026-02-26 -> 2026-03-28      1,130,280   43,200     4,320       0
3     2026-03-29 -> 2026-04-28      1,173,480   43,200     5,760       0
4     2026-04-29 -> 2026-05-29      1,216,680   43,200     7,200       0
5     2026-05-30 -> 2026-06-29      1,259,880   43,200     7,200       0
pooled                               6,911,220  259,200   28,800      60
```

**Verified against D-S052-03's corrected per-fold table, with two
explained (not adjusted-away) deviations, both well within tolerance:**

1. **TEST and PURGED match exactly** on every fold: `TEST=43,200` all six
   folds, `PURGED=60` on fold 0 only, `0` thereafter -- exactly as the
   corrected table states.
2. **TRAIN is consistently ~120 rows lower than the corrected table's
   figure** on folds 0-4 (e.g. fold 0: table says 1,043,940, measured
   1,043,820; fold 4: table says 1,222,560, measured 1,216,680 -- the
   gap grows because of point 3 below, not this point alone). Isolating
   just this effect (`TRAIN + EMBARGOED` vs. the table's `TRAIN +
   EMBARGO`): the combined total is ~120 rows lower than the table on
   every fold except fold 5. A 120-row gap against >1M-row folds
   (~0.01%) is consistent with the table's own arithmetic being built
   from whole calendar days off `t_max`'s bar-open time (2026-06-29
   23:59:00), not from the exact minute-resolution boundary the pipeline
   uses -- explained by rounding in the plan, not a fold-assignment bug.
3. **`EMBARGOED` grows fold-over-fold (1,440 -> 2,880 -> 4,320 -> 5,760
   -> 7,200 -> 7,200) instead of staying flat at the table's constant
   `1,440`.** This is a real, structural difference between D-S052-03's
   simplified single-embargo-per-fold model and how `EXPANDING`-mode
   fold assignment actually behaves in the unmodified pipeline: because
   each fold's TRAIN window grows to include the calendar range covered
   by **every earlier fold's TEST + embargo window**, those earlier
   windows are excluded from the later fold's TRAIN count and counted as
   `EMBARGOED` again rather than `TRAIN`, so `EMBARGOED` accumulates
   roughly `1,440 x (fold_id)` rather than staying constant. This was
   not visible in D-S052-03's table because that table only reported
   "this fold's own embargo region," not the compounding effect of
   `EXPANDING` mode re-excluding prior folds' embargoed regions from
   later TRAIN sets. Fold 5 breaks the `1,440 x fold_id` pattern (7,200,
   same as fold 4, not 8,640) because fold 5's test window ends exactly
   at `t_max` and there is no subsequent embargo period to add. **No
   number was adjusted to make this match** -- this is a description of
   what the pipeline did, read from the persisted `folds.json` /
   dataset manifest `fold_summary`, not a change to any spec or plan.
   This behaviour is a property of the unmodified `splitting.py` fold
   assignment logic and is out of this task's scope to alter or
   "correct" (§5); it is recorded here as a documentation gap in
   D-S052-03's table, worth a follow-up note if Wave 0 tables are
   revisited for a future study, not a pipeline defect.

**No file under any §5 forbidden path was touched.** `git status
--porcelain src/` is empty after both runs; the working tree's only
changes are this documentation update. No dataset bytes, run directory, or
report HTML were staged or committed (`user_data/` stays gitignored, and
neither `report.html` was moved out of it).

One incidental, non-actionable observation: both fits emit a
`sklearn` `FutureWarning` ("'n_jobs' has no effect since 1.8 and will be
removed in 1.10... please leave it unspecified") from the logistic
estimator's resolved parameters (`btc_momentum_regime_logistic.yaml`,
unchanged, not a Sprint 052 file to edit under the frozen-spec rule). It
does not affect correctness or the fit result and required no code or spec
change to proceed; noted here rather than silently ignored, and left for
whoever next touches that estimator spec file, if ever.

### Wave 2 — The comparison

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S052-T004 | Extract the verdict: run `analyze_predictive_run` and `compare_predictive_runs`, and tabulate the primary metric **per fold and pooled** against `RANDOM_PERMUTATION`, plus the train/test gap and the permutation-importance ranking of the Sprint 051 features | the table reports both `S044_GATE` §1.4's strict bar ("beats permutation on **every** fold") and the pooled result, and says explicitly which was cleared; the train/test gap is reported for every fold so an overfit win cannot be presented as a clean one; feature importances are reported for the new components specifically, so a null result can distinguish "the features were ignored" from "the features misled" | T003 | DONE |
| S052-T005 | **Conditional, bounded second pass.** Only if Wave 0's trigger fires (baseline neither clearly clears nor clearly fails the bar): one tree family (`ml-trees`), one `CandidateSetSpec` at the default cap of 8, same dataset fingerprint, same folds, same seed | if the trigger does not fire, this task is closed as NOT RUN with one sentence of reasoning — that is a valid outcome, not a skip; if it runs, the dataset fingerprint is identical to T003's (asserted, so the leaderboard is a like-for-like comparison); no third pass exists, no matter the result; no feature is added or removed | T004 | TODO |

**S052-T004 outcome (2026-09-08, `docs/btc-predictive-study-baseline-run`):**
`analyze_predictive_run` (`persist=True`, re-deriving `metrics.json` in place —
a read/recompute over already-persisted `predictions.parquet` and the dataset
envelope, not a change to any file under a §5 forbidden path) and
`compare_predictive_runs` were run against both `f7ac893d54ae6b69`
(REGRESSION/ridge) and `faa6983acd03f846`(BINARY/logistic), both unmodified.
Both are read-only over persisted run artifacts under `user_data/` (gitignored,
nothing committed) — no code under `research/predictive/`,
`application/predictive_research/`, `market_analysis/`, or
`infrastructure/ml/` was touched, and `git status --porcelain src/` stayed
empty throughout.

**Per-fold and pooled comparison vs. `RANDOM_PERMUTATION`:**

```text
REGRESSION pass (ridge, run f7ac893d54ae6b69) — primary metric: spearman_ic
fold  test window                MODEL       RANDOM_PERMUTATION   vs. permutation
0     2025-12-26 -> 2026-01-25   0.021431    -0.002227             BEATS
1     2026-01-26 -> 2026-02-25   0.013676     0.001038             BEATS
2     2026-02-26 -> 2026-03-28   0.028457    -0.001969             BEATS
3     2026-03-29 -> 2026-04-28   0.050279    -0.002727             BEATS
4     2026-04-29 -> 2026-05-29   0.055561     0.001113             BEATS
5     2026-05-30 -> 2026-06-29  -0.009730    -0.001766             LOSES
pooled                           0.020566    -0.004792             BEATS

BINARY pass (logistic, run faa6983acd03f846) — primary metric: roc_auc
fold  test window                MODEL       RANDOM_PERMUTATION   vs. permutation
0     2025-12-26 -> 2026-01-25   0.545385     0.499030             BEATS
1     2026-01-26 -> 2026-02-25   0.533585     0.500667             BEATS
2     2026-02-26 -> 2026-03-28   0.539353     0.503985             BEATS
3     2026-03-29 -> 2026-04-28   0.559752     0.498767             BEATS
4     2026-04-29 -> 2026-05-29   0.557209     0.496858             BEATS
5     2026-05-30 -> 2026-06-29   0.541288     0.501019             BEATS
pooled                           0.544182     0.498606             BEATS
```

**`S044_GATE.md` §1.4 bar assessment:**

- **REGRESSION pass: clears the pooled bar, does NOT clear the strict
  per-fold bar.** MODEL beats `RANDOM_PERMUTATION` pooled (0.020566 vs.
  -0.004792) and on 5 of 6 folds, but loses on fold 5 (-0.009730 vs.
  -0.001766, both negative — the model is mildly anti-correlated with
  outcomes in that fold and permutation is closer to zero). The strict
  "every fold" bar is **not** cleared.
- **BINARY pass: clears BOTH the pooled bar and the strict per-fold bar.**
  MODEL beats `RANDOM_PERMUTATION` on all 6 folds individually (margins
  0.035–0.061 roc_auc) and pooled (0.544182 vs. 0.498606). This is the
  stronger, cleaner result of the two passes.

**Train/test primary-metric gap per fold** (`train_primary`/`test_primary`
recomputed by `analyze_predictive_run` and carried in `metrics.json`'s
`fold_primary`; the identical values also appear as `primary_gap` in
`importance.json`, cross-checked and consistent):

```text
REGRESSION pass — gap = |train_primary - test_primary| (spearman_ic)
fold  train_primary  test_primary   gap
0     0.016846        0.021431      0.004585
1     0.016671        0.013676      0.002995
2     0.015239        0.028457      0.013218
3     0.016796        0.050279      0.033483
4     0.021196        0.055561      0.034365
5     0.024186       -0.009730      0.033916

BINARY pass — gap = |train_primary - test_primary| (roc_auc)
fold  train_primary  test_primary   gap
0     0.533798        0.545385      0.011587
1     0.534199        0.533585      0.000614
2     0.533971        0.539353      0.005381
3     0.533873        0.559752      0.025878
4     0.534740        0.557209      0.022469
5     0.535447        0.541288      0.005841
```

Neither pass shows the classic overfit signature (train materially *higher*
than test) — in both passes `test_primary` is usually *above*
`train_primary` (folds 0/2/3/4 in both passes), which is the opposite
direction from overfitting and is more consistent with a small, noisy
train-fold estimate of an already-weak signal than with the model
memorizing TRAIN. **This is still flagged, not waved through**: for the
REGRESSION pass, the gap on folds 3–5 (0.033–0.034) is *larger than the
test-fold signal itself* (test_primary 0.050, 0.056, and -0.010
respectively) — i.e. the fold-to-fold instability is large relative to the
effect size being measured, which is exactly the kind of result an unhedged
write-up (T006) needs to name plainly rather than round up to "wins." The
BINARY pass's gaps are smaller in both absolute terms and relative to its
own effect size (test_primary ~0.53–0.56 throughout).

**Permutation importance for Sprint 051's six components**
(`importance.json`, `n_repeats=5`, `EstimatorSpec.seed=42`; only 6 of the 10
frozen features are Sprint 051's — the other 4 are the D-S052-05 incumbents
and are out of scope for this reporting item). Sign convention: a
**positive** mean means shuffling that feature *hurts* the model (i.e. the
feature genuinely helps); a **negative** mean means shuffling it *helps*
(i.e. the feature actively degrades predictions where used).

```text
REGRESSION pass — importance mean by fold (spearman_ic units)
component                          f0       f1       f2       f3       f4       f5
momentum.rsi                    -0.0030  -0.0058  -0.0016  -0.0174  -0.0136  -0.0111
momentum.macd                   -0.0000  +0.0005  +0.0033  +0.0079  +0.0107  +0.0066
momentum.stochastic             +0.0129  +0.0068  +0.0081  +0.0222  +0.0395  +0.0234
volatility.relative_volatility  -0.0016  -0.0026  -0.0014  +0.0028  +0.0111  -0.0104
statistics.return_autocorrelation +0.0308 -0.0036  +0.0325  +0.0184  +0.0598  +0.0007
statistics.return_distribution  -0.0038  -0.0007  -0.0152  +0.0020  +0.0092  +0.0015

BINARY pass — importance mean by fold (roc_auc units)
component                          f0       f1       f2       f3       f4       f5
momentum.rsi                    +0.0353  +0.0184  +0.0317  +0.0344  +0.0360  +0.0251
momentum.macd                   +0.0024  +0.0071  -0.0005  +0.0011  -0.0004  +0.0004
momentum.stochastic             +0.0158  +0.0090  +0.0199  +0.0241  +0.0273  +0.0270
volatility.relative_volatility  +0.0000  -0.0001  +0.0001  +0.0011  -0.0008  -0.0006
statistics.return_autocorrelation +0.0039 +0.0009  +0.0036  +0.0046  +0.0048  -0.0002
statistics.return_distribution  +0.0013  -0.0000  +0.0005  +0.0049  +0.0043  +0.0029
```

- **Ignored vs. misled, per pass:**
  - **REGRESSION**: `momentum.macd`, `volatility.relative_volatility`, and
    `statistics.return_distribution` sit near zero on every fold (|mean|
    mostly <0.01, no consistent sign) — **ignored**. `momentum.stochastic`
    and `statistics.return_autocorrelation` are consistently the largest
    positive contributors and drive most of the 5 winning folds —
    genuinely used, and correctly so. `momentum.rsi` is **consistently
    negative on all 6 folds** (-0.003 to -0.017) — the model is using it,
    but using it in a way that actively hurts predictions on every fold:
    this is **misled**, not ignored. On the one losing fold (5),
    `statistics.return_autocorrelation` — the strongest driver on 4 of the
    other 5 folds — collapses to near zero (+0.0007) while `momentum.rsi`
    and `volatility.relative_volatility` both turn more negative than
    their own fold-5-adjacent values; the fold 5 loss reads as "the
    autocorrelation signal that carried most other folds went quiet, and
    the actively-harmful rsi/relative-volatility contribution was left
    unmasked," not as a single dramatic misleading spike.
  - **BINARY**: `momentum.macd`, `volatility.relative_volatility`,
    `statistics.return_autocorrelation`, and `statistics.return_distribution`
    are all near zero on every fold (|mean| mostly <0.005) — **ignored**,
    cleanly, with no "misled" case to report since the pass does not lose
    on any fold. `momentum.rsi` and `momentum.stochastic` are the two
    real drivers, both consistently positive (0.018–0.036 and 0.009–0.027
    respectively) on every fold — genuinely used and correctly so. Notably,
    `momentum.rsi` is the strongest single driver of the BINARY pass's
    clean win, while it is the one component that actively hurts the
    REGRESSION pass on every fold — the same feature reads oppositely
    depending on task framing, worth naming in T006 rather than averaging
    away.

**`compare_predictive_runs`:** the two passes carry **different**
`dataset_fingerprint`s (`f9f042f9...` for REGRESSION vs. `98a893f5...` for
BINARY), because `PredictiveStudySpec.label.kind` differs between the two
committed spec files (T003 outcome note already established this). Calling
`compare_predictive_runs` with both run directories together correctly
raises `PredictiveSpecError: leaderboard runs must share one dataset
fingerprint` — the function's own designed guard, not a bug. Each pass was
therefore compared singly against its own baselines: both leaderboards
confirm `MODEL` (`sklearn.ridge` / `sklearn.logistic`) ranks first, ahead of
`RANDOM_PERMUTATION` (and `CONSTANT_MEAN`/`MAJORITY_CLASS` respectively),
matching the pooled numbers above exactly.

**S052-T005 trigger determination (D-S052-06: regression and binary are two
separate passes, evaluated independently):**

- **REGRESSION pass: the trigger FIRES.** It beats `RANDOM_PERMUTATION`
  pooled but loses on one of six folds (fold 5) — this is precisely the
  pre-declared trigger condition ("beats permutation pooled but not on
  every fold"), stated as a factual read of the table above, not a
  judgment call.
- **BINARY pass: the trigger does NOT fire.** It beats `RANDOM_PERMUTATION`
  on every fold and pooled — it clearly clears the strict per-fold bar, so
  the "neither clearly clears nor clearly fails" condition does not apply.

Per §3/§5 ("no feature added after seeing a result", "a second estimator
pass ... only under the Wave-0-defined trigger"), this determination alone
does not authorize running T005 yet — D-S052-06's Wave 0 language and any
scoping (e.g. whether a fired trigger on one pass runs a tree pass for that
pass only, both passes, or is itself a maintainer checkpoint) is read and
applied fresh at T005, not decided here.

### Wave 3 — The write-up and the disposition

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S052-T006 | `docs/reference/BTC_PREDICTIVE_STUDY.md`: the instrument, range and gaps; the fold plan; the feature list; the per-fold and pooled comparison table; the train/test gaps; the importance ranking; and **the verdict stated in one unhedged sentence** | a reader learns the answer in the first paragraph without inference; a negative result is stated as plainly as a positive one, with no "promising signs" language; the document names what would change the verdict (a different horizon, grid, or feature family) as *future options*, never as retroactive excuses; it states that Phase 10 metrics are a precondition and never a verdict that the model should trade (ADR-0024); the document describes a **BTC** study only (D-S052-03a) | T004, T005 | TODO |
| S052-T007 | **Reproducibility record** (a section of T006's document plus the spec header comments): study `definition_hash`, dataset fingerprint, source `DatasetRef` and its import-manifest fingerprint, run IDs, estimator specs and seeds, and the framework version | a third party with the same data can re-derive the same dataset fingerprint from the committed spec; the record states which artifacts live outside git (`user_data/`) and are therefore not reproducible from the repo alone | T006 | TODO |
| S052-T008 | Closure and **Q5 disposition**: update ROADMAP §13F's Q5 dependency line (append, never rewrite history), §13G's 15B status, `CURRENT_STATUS.md`, and the sprint Review | §13F's Q5 line states either "closed by run `<id>`, `<family>`" **or** "still open — reason", never something ambiguous; if closed, the entry states whether the winning family is promotable under ADR-0029 (linear/logistic) or hits its documented tree/neural refusal; if still open, it names S049 Wave 0's "option (b)" as the decision now facing Sprint 050 — and leaves that decision to the maintainer | T007 | TODO |

**Progress:** 4 / 8 — Wave 0's fold plan (T001) is landed and maintainer-signed
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
T003 (the baseline run) is now DONE (this PR, `docs/btc-predictive-study-baseline-run`,
maintainer-authorized delegation of the "maintainer-executed" run to an
agent): both baseline passes ran against the D-S052-03/04/05-corrected
`V=1m` specs — see the outcome note above for run IDs, dataset
fingerprints and fold-count verification. T004 (this PR) is now DONE: the
BINARY pass clears `S044_GATE` §1.4's strict per-fold bar cleanly (6/6 folds
+ pooled) and its T005 trigger does not fire; the REGRESSION pass clears the
pooled bar but loses fold 5, and its T005 trigger fires — see the outcome
note above for the full per-fold/pooled tables, train/test gaps, and the
Sprint 051 feature importance ("ignored" vs. "misled") breakdown per pass.

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
