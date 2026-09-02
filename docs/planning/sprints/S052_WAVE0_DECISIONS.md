# Sprint 052 — Wave 0 Decisions

Binding decisions for the Real-Data BTC Predictive Study (Phase 15B).
Date: 2026-09-02.

```text
Status: PROPOSED — requires the maintainer's Wave 0 Checklist sign-off
        (D-S052-11). `engineer` must refuse to start while any box is unchecked.
        One item (D-S052-03a, the NQ hard stop) is already ANSWERED by the
        maintainer on 2026-09-02.

ADDITIONALLY GATED: D-S052-03's fold table is INTENTIONALLY INCOMPLETE. It is
        completed by S052-T001 from docs/planning/sprints/S051_BTC_DATA_INVENTORY.md
        — the MEASURED dataset range, row count and gaps. No number in this
        document may be finalized against an assumed date range. This is the
        specific failure mode this project has already paid for once (a plan
        pinned to a stale assumption); the fold plan is the place it would
        recur.

Basis:  docs/product/PRD-predictive-research-catalog-expansion.md — AUTHORITATIVE
        docs/planning/ROADMAP_INCREMENT_PHASE_15.md (§13G) — PROPOSED
        docs/planning/sprints/SPRINT_052.md
        docs/planning/sprints/SPRINT_051.md + S051_WAVE0_DECISIONS.md
                (D-S051-07 and D-S051-07a are INHERITED WHOLE)
        docs/adr/ADR-0023 (ACCEPTED) §4, §8, §9
        docs/adr/ADR-0024 (ACCEPTED) + S044_GATE.md §1.4
        docs/adr/ADR-0029 (ACCEPTED) — relevant only to the promotability note
        src/trading_framework/ as on origin/main @ 5bd9969 (2026-09-02)
```

---

## Inherited locks (do not reopen)

```text
D-S051-07:  the study's data is BTCUSDT.P, 1m, 2024-01-01 -> 2026-06-30,
        imported in Sprint 051. Maintainer-chosen; the import's wall-clock cost
        is a priced, accepted cost
D-S051-07a: NON-BTC DATA IS A HARD STOP, not a fallback (restated as D-S052-03a)
ADR-0023 §4: purge, embargo, dataset fingerprint, matrix availability
ADR-0023 §8: CI fixtures stay synthetic-only; standard CI stays network-free.
        This study is a maintainer-triggered research run, NEVER a CI fixture
ADR-0023 §9: one instrument, one horizon
ADR-0024: strong Phase 10 metrics are a PRECONDITION for promotion, never a
        verdict that a model should trade. Phase 7 robustness is unwaived
S044_GATE §1.4: the strict candidate bar is "beats the permutation baseline on
        EVERY fold", not pooled. Both are reported; the write-up says which held
The Phase 10 pipeline is CONSUMED and UNMODIFIED (SPRINT_052.md §5)
Sprint 051's six components are consumed as delivered; no new component here
No estimator-family restriction is invented (PRD Non-goals)

From the PRD:
        OHLCV only; one instrument; a negative result is a legitimate outcome;
        no widening of the feature set in response to a result
```

---

## D-S052-01 — Problem statement

Phase 10's methodology has only ever been validated against synthetic
known-signal fixtures. ROADMAP §13F records the consequence as "Q5": no real,
non-synthetic trained candidate model exists, and that gates Phase 14B.

**Sprint 052 ships exactly:** one declared study on real `BTCUSDT.P` bars using
Sprint 051's expanded catalog, run through the unmodified pipeline, and a
written, per-fold comparison against `RANDOM_PERMUTATION` — plus the resulting
disposition of Q5.

**Not this sprint:** any new component, any pipeline change, any promotion, any
trading claim, and any second study to chase a better number.

---

## D-S052-02 — Sprint branch and PR base

```text
Integration branch: sprint/btc-predictive-study  (cut from main AFTER Sprint 051 merges)
Working branches:   feat/ | fix/ | docs/ | test/ | refactor/ + descriptive slug
PR base:            sprint/btc-predictive-study  (never main until integration)
```

Re-check `origin/main` before cutting the branch.

---

## D-S052-03 — Fold design: the formula now, the numbers at T001

The fold plan is **computed**, not chosen. T001 fills the table below from
`S051_BTC_DATA_INVENTORY.md`.

```text
Inputs from the inventory (measured, not assumed):
        R      = published range [start_at, end_at]
        N_1m   = row_count on the 1m dataset
        G      = the recorded gap list

Locked policy shape:
        mode            = EXPANDING           (each fold trains on all history
                                               before its test window; the
                                               standard walk-forward posture)
        test_span       = T                   (one contiguous calendar span)
        embargo_span    = E >= label horizon  (shown arithmetically at T001)
        fold_count      = F                   (chosen so F*T fits the tail of R
                                               while leaving >= 12 months of
                                               initial TRAIN before fold 1)
        min_train_rows  = M                   (>= 20 x the feature count, so a
                                               fold cannot train on fewer rows
                                               than a linear model can support)
        evaluation_timeframe = V              (see D-S052-04)

Derived and REPORTED at T001, per fold:
        the concrete TEST window dates, the approximate evaluation-bar row
        count, and the TRAIN row count entering that fold
```

**Expected instantiation** — the maintainer has now fixed the import range
(D-S051-07: 2024-01-01 → 2026-06-30, 1m), so this is the plan T001 should
arrive at unless the inventory's measured gaps or row count say otherwise:

```text
V  = 15m          evaluation timeframe
label = BINARY, horizon 1h (4 evaluation bars), threshold 0.0
F  = 6            folds
T  = 30d          test span  -> 180d total out-of-sample tail
E  = 1d           embargo    -> comfortably exceeds the 1h label horizon
M  = 2000         min train rows
```

Sanity check: ~30 months of 15m bars is roughly 87,000 evaluation rows; six
30-day test windows are roughly 2,880 rows each, and fold 1 still trains on well
over a year of history. **These numbers are still confirmed against the measured
inventory at T001, not assumed here** — the range is now known, the exact row
count and gap list are not.

```text
LOCKED  If the measured range cannot support F >= 5 folds with T >= 14d each
        AND >= 12 months of initial TRAIN, the study is declared UNDER-POWERED
        and NOT run. That is a reportable outcome and a STOP-and-ask, not a
        prompt to shrink the embargo, the horizon or the fold count until the
        arithmetic fits.
LOCKED  Recorded gaps are never filled or synthesized. A fold whose TEST window
        overlaps a material gap is moved or dropped, and the write-up says so.
LOCKED  Purge/embargo policy is inherited from ADR-0023 §4 and is not tuned.
```

---

## D-S052-03a — Non-BTC data is a HARD STOP (ANSWERED by the maintainer, 2026-09-02)

Inherited whole from `S051_WAVE0_DECISIONS.md` D-S051-07a and restated here so
this sprint's own document cannot be read in isolation and misunderstood.

```text
LOCKED  NQ.c.0 — or any other non-BTC dataset — is REJECTED as a substitute for
        BTCUSDT.P in this study. This is a HARD STOP, not a ranked fallback and
        not a soft preference.

IF the BTC data is unavailable, incomplete, or the import proved impractical
(as recorded in S051_BTC_DATA_INVENTORY.md):
        1. This sprint DOES NOT OPEN. Wave 0 stays unlocked.
        2. STOP and return to the maintainer with what is known.
        3. Do NOT run the study on NQ.c.0 or any other instrument.
        4. Do NOT re-scope Phase 15B to a different instrument to keep moving.

REASON (the maintainer's own): NQ does not satisfy ROADMAP §13F's Q5 wording
        ("... on BTC data"). Running the study on NQ and reporting it against
        Q5 would look like closing the prerequisite while not closing it —
        exactly the silent scope drift this project's governance exists to
        prevent.

CONSEQUENCE FOR THE WRITE-UP: docs/reference/BTC_PREDICTIVE_STUDY.md may only
        ever describe a study on BTC data. If some future study on another
        instrument is wanted, it is a separate, separately-approved piece of
        work with its own document — never an appendix to this one.
```

Any sentence in `SPRINT_051.md` §4, `SPRINT_052.md` §4/§5, or elsewhere that
reads as "wait, substitute NQ, or defer" is a documentation defect to be
corrected, **not** a licence to choose. The only two paths are: BTC data
arrives and the sprint proceeds, or the maintainer decides otherwise.

---

## D-S052-04 — Evaluation grid and the 1m-noise problem

```text
LOCKED  The source dataset stays 1m (TD-023: the importer supports no other
        interval). The study evaluates on a COARSER grid via
        PredictiveStudySpec.evaluation_timeframe — the existing, no-code-change
        knob (SPRINT_052.md §4 Finding 3).
LOCKED  Sprint 051's rolling higher moments (statistics.return_distribution) use
        a window of at least 60 evaluation bars, per D-S051-03's documented
        warning that short windows are outlier-dominated.
LOCKED  If memory or wall-clock forces a change, the RANGE is trimmed or the
        GRID coarsened — never the pipeline modified, and never the INSTRUMENT
        changed (D-S052-03a). A pipeline change is a STOP-and-report finding.
```

---

## D-S052-05 — Feature list

```text
LOCKED  The declared features are Sprint 051's six components plus a small,
        named set of incumbents (suggested: volatility.atr, trend.slope,
        candle.wick, volatility.range_expansion) so the study is not a
        single-family bet. T001 fixes the exact list and it does not change
        afterwards.
LOCKED  Single-timeframe only — MTF features are not declarable in a
        PredictiveStudySpec today (D-S051-06).
LOCKED  Feature transforms stay within FeatureTransform's existing bounded set;
        RANK is rejected at matrix-build time in this slice and is not used.
LOCKED  THE FEATURE LIST IS FROZEN AT T001. Adding a feature after seeing a
        result is forbidden (PRD's named risk) and is reviewable as a diff
        against the committed spec (SPRINT_052.md acceptance criterion 8).
```

---

## D-S052-06 — Estimator plan (Q3 ANSWERED)

**Answers PRD Open Question 3.**

```text
LOCKED  Pass 1 (always): sklearn baselines via the `ml` extra —
        one REGRESSION run (ridge or elastic net) and one BINARY classification
        run (logistic), same folds, same seed, fold-local preprocessing as
        delivered (IMPUTE_MEDIAN then STANDARDIZE).
LOCKED  Pass 2 (conditional, bounded): ONE tree family via `ml-trees`, ONE
        CandidateSetSpec at the default cap of 8, identical dataset fingerprint,
        identical folds and seed.
LOCKED  Pass 2's TRIGGER, declared in advance: the baseline neither clearly
        clears S044_GATE §1.4's per-fold bar nor clearly fails it — i.e. it
        beats permutation pooled but not on every fold. A clear pass and a clear
        failure BOTH end the sprint at pass 1.
LOCKED  There is NO pass 3, whatever pass 2 shows.
LOCKED  Neural (`dl`) families are excluded from this sprint.
```

Reasoning: cheapest iteration, smallest tuning surface, and the least confounded
read on whether the *features* carry anything — a regularized linear model that
beats permutation out of sample is a much stronger claim than a boosted tree
doing the same, because it has far less capacity to memorize noise.

```text
NOTE (a consequence, NOT a restriction) — ADR-0029's promotion v1 supports
        linear and logistic families only. A baseline winner is therefore
        immediately promotable and closes Q5 outright; a tree winner hits
        ADR-0029's documented refusal and makes the deferred joblib path
        (TD-029) the next question. §13F already lists this as a known risk.
        The PRD forbids inventing an estimator-family restriction, and none is
        invented here: trees remain fully in scope under the trigger above.
```

---

## D-S052-07 — What gets reported, and how

```text
LOCKED  Per fold AND pooled, for every run: the primary metric, the
        RANDOM_PERMUTATION comparator, and the |train - test| primary-metric gap.
LOCKED  Both bars are stated: S044_GATE §1.4's strict "every fold" bar and the
        pooled bar — with an explicit sentence saying which was cleared.
LOCKED  Permutation importance is reported for Sprint 051's components
        specifically, so a null result distinguishes "the new features were
        ignored" from "the new features misled".
LOCKED  The verdict appears in ONE unhedged sentence in the first paragraph of
        docs/reference/BTC_PREDICTIVE_STUDY.md. No "promising signs", no
        "directionally encouraging", in either direction.
LOCKED  "What would change the verdict" is written as FUTURE OPTIONS, never as
        a retroactive excuse for the result obtained.
```

---

## D-S052-08 — What is committed and what is not

```text
COMMITTED     apps/cli/examples/predictive/*.yaml — the study spec and estimator
              specs, with definition_hash in a header comment
COMMITTED     docs/reference/BTC_PREDICTIVE_STUDY.md — the result and the
              reproducibility record
COMMITTED     one network-free, extra-free parse test for the spec files
NOT COMMITTED dataset bytes, run directories, model blobs, report HTML, anything
              under user_data/ (gitignored, maintainer-owned)
FIXED         research_run_predictive.yaml currently points at
              configs/predictive/my_study.yaml, which does not exist in the
              repo. T002 repoints it at the real committed specs.
```

---

## D-S052-09 — Q5 disposition is a decision the maintainer makes, not the sprint

```text
LOCKED  T008 updates ROADMAP §13F's Q5 dependency line to state EITHER
        "closed by run <id>, family <family>" OR "still open — <reason>".
        Nothing ambiguous, and history is appended to, never rewritten.
LOCKED  If Q5 stays open, T008 names S049_WAVE0_DECISIONS.md's "option (b)"
        (Sprint 050 promotes a synthetic artifact as PLUMBING ONLY, loudly
        labelled) as the decision now facing the maintainer — and stops there.
        Sprint 052 does not choose it.
LOCKED  Q5 can only ever be closed by a BTC result (D-S052-03a). A study on any
        other instrument does not close it, however good the numbers look.
LOCKED  Sprint 052 promotes nothing and re-plans nothing about Phase 14B.
```

---

## D-S052-10 — Reserved

Intentionally unused, so decision IDs already referenced elsewhere do not shift.

---

## D-S052-11 — Wave 0 Checklist (maintainer)

Nothing below may be checked off by an agent. `engineer` must refuse to start
while any box is unchecked.

- [ ] **Sprint 051 is closed and `S051_BTC_DATA_INVENTORY.md` records a usable published `BTCUSDT.P` dataset.** If it does not, this sprint does not open (SPRINT_052.md §4 Finding 1, D-S052-03a).
- [ ] **ROADMAP §13G approved**, and Sprint 052 / Phase 15B confirmed as its closing increment; **Sprint 050 stays reserved for Phase 14B.**
- [ ] **D-S052-03 confirmed** — the fold plan is computed from measured facts at T001; the under-powered STOP rule is accepted; gaps are never filled and the embargo/purge policy is never tuned to make the arithmetic work.
- [ ] **The fold table produced by T001 reviewed and accepted** (this box is checked after T001, before T003 runs).
- [x] **D-S052-03a — ANSWERED by the maintainer, 2026-09-02.** Non-BTC data (NQ.c.0 or otherwise) is **REJECTED as a substitute**: a hard stop, not a fallback. If BTC data is unavailable the sprint does not open and the work returns to the maintainer. Q5 can only be closed by a BTC result.
- [ ] **D-S052-04 confirmed** — coarser `evaluation_timeframe`; range or grid is adjusted under pressure, never the pipeline and never the instrument.
- [ ] **D-S052-05 confirmed** — the feature list is frozen at T001 and adding features after seeing a result is forbidden.
- [ ] **PRD Open Question 3 answered as D-S052-06** — sklearn baselines first; one bounded tree pass only under the pre-declared trigger; no pass 3; no neural; and the note that this is a sequencing choice, not an invented family restriction.
- [ ] **D-S052-07 confirmed** — both permutation bars reported, per-fold train/test gaps mandatory, one unhedged verdict sentence, no hedging in either direction.
- [ ] **A negative result is accepted in advance as a completed sprint**, and will not be treated as a reason to widen the catalog inside this sprint.
- [ ] **D-S052-08 confirmed** — specs and the write-up are committed; no `user_data/` content, dataset bytes or run outputs enter git.
- [ ] **D-S052-09 confirmed** — Q5's disposition is recorded unambiguously, and the "option (b)" decision for Sprint 050 is surfaced to the maintainer, not taken by the sprint.
- [ ] **Sprint 052 scope approved as 8 tasks, 4 waves**, shipping **no** component, **no** pipeline change and **no** promotion.
- [ ] **Branch `sprint/btc-predictive-study` approved**, to be cut from `main` after Sprint 051 integrates.

Approved-by: _(pending — no agent may fill this in. The D-S052-03a entry above
is a recorded decision on one item, not sign-off of this checklist.)_

Once every box is checked, the first task for `engineer` is **S052-T001** (the
Wave 0 locks plus the fold plan computed from the inventory, docs only) on
`docs/btc-predictive-study-planning`, cut from `sprint/btc-predictive-study`.
