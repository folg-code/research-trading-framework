# Sprint 051 — Wave 0 Decisions

Binding decisions for the Momentum and Regime Component Catalog (Phase 15A).
Date: 2026-09-02.

```text
Status: APPROVED (2026-09-02) — Wave 0 Checklist D-S051-12 signed off in
        full by the maintainer, in addition to the item-level A1/A2/A3
        answers recorded below.

Basis:  docs/product/PRD-predictive-research-catalog-expansion.md — AUTHORITATIVE
        docs/planning/ROADMAP_INCREMENT_PHASE_15.md (§13G) — PROPOSED
        docs/planning/sprints/SPRINT_051.md
        docs/adr/ADR-0005, ADR-0006, ADR-MA-001..014 (ACCEPTED)
        docs/adr/ADR-0023 §4/§8/§9, ADR-0025, ADR-0026(+Am.1), ADR-0027, ADR-0028
        src/trading_framework/ as on origin/main @ 5bd9969 (2026-09-02), the
        Sprint 049 integration commit

Numbering: verified against live origin/main, not from memory. Sprint 050 is
        NOT free — merged documents bind it by name to Phase 14B (ROADMAP §13F,
        ADR-0029, PREDICTIVE_PROMOTION.md, SPRINT_049.md, S049_WAVE0_DECISIONS.md).
        This is Sprint 051 / Phase 15A / ROADMAP §13G; the successor is
        Sprint 052 / Phase 15B.
```

---

## Maintainer answers received (2026-09-02)

Given by the maintainer after reviewing this document's open items, relayed
through the coordinating session. These three are **final** and are not
reopened by implementation.

```text
A1  D-S051-07 — BTC import range: ACCEPTED as recommended.
        BTCUSDT.P, 1m, 2024-01-01 -> 2026-06-30 (~1.31M bars).
        The wall-clock cost under Binance weight limits is accepted as a
        KNOWN, PRICED cost (ADR-0025 "Consequences"), not a discovered surprise.

A2  NEW — the NQ.c.0 fallback is REJECTED as an automatic substitute.
        If the BTC import proves impractical, the work STOPS and returns to the
        maintainer. Substituting NQ data is NOT an engineer decision and NOT a
        soft preference — it is a HARD STOP. Reason given: NQ does not satisfy
        ROADMAP §13F's Q5 wording ("on BTC data"), and treating it as
        equivalent would be exactly the silent scope drift this project's
        governance exists to prevent. Locked as D-S051-07a.

A3  D-S051-04 — momentum.stochastic zero-range window: 50.0 CONFIRMED.
        The deliberate deviation from the project's 0.0-on-zero-denominator
        convention, and its reasoning (avoiding a false "close is at the low"
        signal), must be stated in the COMPONENT DOCSTRING itself, so a future
        reader does not "fix" it back to 0.0 as an inconsistency.
```

These were the only two items flagged as open forks in the sprint plan. No
other decision in this document has changed.

---

## Inherited locks (do not reopen)

```text
ADR-0023 §8: CI fixtures stay SYNTHETIC-ONLY (D-S039-CI-dataset). This sprint
        adds no real-data test and no network test. The real-data import is an
        operator act producing a document, never a fixture
ADR-0023 §4: purge / embargo / dataset fingerprint / matrix availability
ADR-0023 §9: one instrument, one horizon
ADR-0025: the Binance importer is RUN, never modified; 1m only (TD-023);
        credentials come from the environment, never from a file
ADR-0026 Amendment 1: the apps/cli import allow-list. Widening it is a fresh
        amendment with maintainer approval — NEVER a test-file edit
ADR-0027 / ADR-0028: the strategy_file loader and Exit/Risk models are CONSUMED
ADR-0029 and everything under research/predictive/promotion/: untouched
ml / ml-trees / dl stay out of the default install and default CI; this sprint
        needs none of them
research/predictive/ imports no ML library, ever

From the PRD:
        OHLCV only; one instrument; no ML-only component concept; no
        estimator-family restriction invented; a negative study result (Sprint
        052) is a legitimate outcome
```

---

## D-S051-01 — Problem statement

The Market Analysis catalog holds thirteen components, most built to prove the
DSL and MTF machinery rather than chosen for predictive value. Predictive
Research can only declare features from that narrow set, so a real-data study
would be under-featured before it starts — a negative result would prove only
that the framework did not look hard enough.

**Sprint 051 ships exactly:** six new causal FEATURE components through the
existing `model_authoring` DSL and registry pattern, proof that each is
consumable by *both* a rule-based Signal Model and a predictive `FeatureSpec`,
and a written inventory of a real, imported `BTCUSDT.P` dataset.

**Not this sprint:** any study, any run, any verdict, any MTF variant, any
change to the Phase 10 pipeline, and any promotion work.

---

## D-S051-02 — Sprint branch and PR base

```text
Integration branch: sprint/momentum-and-regime-catalog  (cut from origin/main @ 5bd9969)
Working branches:   feat/ | fix/ | docs/ | test/ | refactor/ + descriptive slug
PR base:            sprint/momentum-and-regime-catalog   (never main until integration)
```

Working-branch PRs squash-merge into the sprint branch; one integration PR at
the end. Branch names describe the change, never the task ID. `spike/` is not a
valid prefix in this project — the data-acquisition task uses
`docs/btc-dataset-inventory`, because its entire output is a document.

**Re-check `origin/main` before cutting the branch.** This is Sprint 049's
recorded lesson: a plan drafted against a stale base collided with merged work.

---

## D-S051-03 — The six components, locked

```text
momentum.rsi                     params: period=14 (min 2)
                                 outputs: value            (0..100)
momentum.macd                    params: fast_period=12, slow_period=26,
                                         signal_period=9   (fast < slow enforced)
                                 outputs: line, signal, histogram
                                 depends on: trend.ema(fast), trend.ema(slow)
momentum.stochastic              params: period=14, smoothing_period=3
                                 outputs: k, d             (0..100)
volatility.relative_volatility   params: period=20, baseline_period=100
                                         (period < baseline_period enforced)
                                 outputs: value, ratio
statistics.return_autocorrelation params: period=60 (min 8), lag=1
                                         (lag < period - 1 enforced)
                                 outputs: value            (-1..1)
statistics.return_distribution   params: period=60 (min 8)
                                 outputs: skew, excess_kurtosis
```

All six are `ComponentKind.FEATURE`, `Causality.CAUSAL`, NumPy-implemented,
registered `default=True`, and exposed through `model_authoring` references
(`references/momentum.py`, `references/statistics.py`, and an addition to
`references/volatility.py`).

```text
LOCKED  `momentum.` and `statistics.` are new dotted namespaces. This needs no
        ADR — `candle.` was introduced the same way in Sprint 047.
LOCKED  Six components. A seventh is an IDEA_INBOX entry, not a scope change.
LOCKED  Log returns everywhere: r_t = ln(close_t / close_{t-1}). One definition,
        used by relative_volatility, return_autocorrelation and
        return_distribution alike, so the three compose coherently.
```

**Answers PRD Open Question 1** (the return-distribution statistic): rolling
**population Fisher–Pearson skew and excess kurtosis of log returns** over one
`period` window, not a simpler proxy. Reasons: both are computable with the same
rolling-window machinery the other five use, both are causal with a warm-up the
existing `HistoryRequirement` already expresses, both are directly interpretable
to the maintainer, and putting them in one component keeps the shared window and
mean computation in one place. The known weakness — short windows on 1m crypto
bars are dominated by single outliers — is handled by documentation plus Sprint
052's choice of a coarser evaluation grid, not by picking a weaker statistic.
Quantile-based (Bowley) skew is the recorded fallback if Sprint 052 finds the
moment estimator unusable; that would be a new component, not a silent change.

---

## D-S051-04 — Degenerate-window conventions (CONFIRMED by the maintainer, A3)

```text
LOCKED  momentum.rsi        no losses in the window  -> 100.0
                            entirely flat window     -> 50.0
LOCKED  momentum.stochastic zero-range window        -> 50.0   (DIVERGENT)
LOCKED  volatility.relative_volatility  zero baseline -> 0.0
LOCKED  statistics.*        zero-variance window     -> 0.0
LOCKED  Warm-up bars are always NaN and always excluded by valid_from_index
```

The `50.0` for stochastic **deliberately diverges** from the project's existing
`0.0`-on-zero-denominator convention (`candle.wick` D-S047-10,
`trend.ema_distance` / `volatility.range_expansion` D-S048-10). Reason: %K = 0
already means "close sits at the window's low", a real and actionable reading. A
flat window is not that, and emitting `0.0` would **fabricate a signal** rather
than merely avoid an `inf`. Every other component keeps the `0.0` convention,
because there `0.0` is genuinely neutral.

```text
LOCKED (A3)  The deviation AND its reasoning are stated in the COMPONENT
        DOCSTRING itself — not only here, not only in tests. The maintainer's
        stated purpose: a future reader must not "fix" 50.0 back to 0.0 as an
        apparent inconsistency. S051-T005's acceptance requires the docstring
        to name the convention it diverges from, the reason, and this decision
        ID.
LOCKED  It additionally appears in the test name and in STRATEGY_AUTHORING.md,
        so the deviation is discoverable from three directions.
```

---

## D-S051-05 — Estimator conventions (no library matching)

```text
LOCKED  RSI uses Wilder smoothing (recursive, alpha = 1/period), not a simple
        moving average of gains/losses
LOCKED  MACD's signal line is the shared `ema` kernel applied to the MACD line,
        computed inside the component (trend.ema cannot smooth another
        component's output — SPRINT_051.md §4 Finding 4)
LOCKED  Rolling stdev, skew and kurtosis use POPULATION moments (no n-1 or
        Fisher small-sample bias correction). One documented estimator beats
        matching any particular library's default
LOCKED  Autocorrelation is the rolling Pearson correlation of the return series
        against its own lag-k shift, computed within the window (not a global mean)
LOCKED  Tests compute expected values from first principles inside the test —
        never by calling the implementation, and never by importing pandas,
        scipy or any library not already a default dependency
```

---

## D-S051-06 — Single timeframe, and why that is structural (Q4 ANSWERED)

**Answers PRD Open Question 4.** Single-timeframe first — but the reason is
stronger than "precedent suggests it".

Verified in code on `origin/main` @ `5bd9969`:

```text
research/predictive/features.py       FeatureSpec: component_id, parameters,
                                      output_id, alias, transform. No timeframe.
market_analysis/assembly/frame.py     AnalysisFrameColumnSpec: same four fields.
application/predictive_research/build_predictive_dataset.py
                                      _component_requests(...) builds
                                      ComponentRequest(component_id, parameters)
                                      — no computation_timeframe anywhere.
```

```text
LOCKED  MTF features are NOT declarable in a PredictiveStudySpec today. Adding
        them is a contract change across two packages, out of scope for a
        catalog sprint and not required by the PRD.
LOCKED  The DSL reference functions MAY accept an optional `timeframe=` kwarg
        for Signal Model consumers, exactly as volatility.range_expansion
        already does. Cheap, no new machinery, keeps the shared-catalog claim
        honest.
LOCKED  The study-side coarse-grid knob is PredictiveStudySpec.
        evaluation_timeframe, which already exists. Sprint 052 uses it.
```

---

## D-S051-07 — The data does not exist; acquiring it is a task (ANSWERED, A1)

Verified 2026-09-02 against the maintainer's canonical workspace
(`C:\Users\Folga\research-trading-framework\user_data`):
`market_data/metadata/` contains **only** NQ Databento datasets — nine
per-contract trades datasets plus `NQ.c.0` trades and 1m OHLCV. **No Binance
dataset of any kind has ever been imported.**

The PRD states that `BTCUSDT.P` bars are "a real, imported `DatasetRef`, not a
fixture". That is the one PRD premise live state contradicts. Sprint 045
delivered the importer; nobody has run it for a real range.

```text
LOCKED (A1)  RANGE: BTCUSDT.P, interval 1m, 2024-01-01 -> 2026-06-30
        (~30 months, ~1.31M bars). Chosen by the maintainer, matching the
        architect's recommendation.
LOCKED (A1)  The wall-clock cost of that import under Binance weight limits is
        an ACCEPTED, PRICED cost (ADR-0025 "Consequences" states a year of 1m
        bars takes real time). Slowness is therefore NOT a finding, NOT a
        reason to trim the range mid-flight, and NOT a trigger for the D-S051-07a
        stop — only genuine impracticability is (see below).
LOCKED  S051-T002 runs the import and produces
        docs/planning/sprints/S051_BTC_DATA_INVENTORY.md with MEASURED facts
        read from the registry metadata JSON and import_manifest.json —
        DatasetRef, start_at, end_at, row_count, every recorded gap,
        api_key_used, observed wall-clock and backoff behaviour.
LOCKED  Nothing from user_data/ is committed. The inventory document is the
        only artifact that enters git.
LOCKED  A failed or abandoned import is a documented outcome, never a silent one.
```

Rationale for this range, recorded so it is not re-litigated: long enough for
six 30-day out-of-sample folds with a multi-year expanding train window;
comparable in order of magnitude to the `NQ.c.0` dataset the pipeline already
handles (334,816 rows); and deliberately short of the full 2019-onward history,
whose import cost is several times larger for questionable marginal relevance to
current market structure.

---

## D-S051-07a — The NQ fallback is a HARD STOP, not an option (ANSWERED, A2)

```text
LOCKED (A2)  NQ.c.0 (or any non-BTC dataset) is REJECTED as an automatic
        substitute for BTCUSDT.P. This is a HARD STOP, not a soft preference
        and not a ranked fallback.

IF the BTC import proves IMPRACTICAL (not merely slow — slowness is priced,
see D-S051-07):
        1. STOP.
        2. Record what was attempted and why it is impractical in
           S051_BTC_DATA_INVENTORY.md.
        3. RETURN TO THE MAINTAINER for a decision.
        4. Do NOT substitute NQ.c.0. Do NOT proceed to Sprint 052 on non-BTC
           data. Do NOT re-scope Phase 15 to a different instrument.

REASON (the maintainer's own): NQ does not satisfy ROADMAP §13F's Q5 wording
        ("a real (non-synthetic) trained candidate model showing genuine
        out-of-sample structure on BTC data"). Treating NQ as equivalent would
        be exactly the silent scope drift this project's governance exists to
        prevent — the study would look like it closed Q5 while not closing it.

BINDING ON: SPRINT_051.md §4 Finding 1, SPRINT_052.md §4 Finding 1 and §5, and
        S052_WAVE0_DECISIONS.md D-S052-03a. Any of those reading as a menu of
        options rather than a stop is a documentation defect to fix, not a
        licence to choose.
```

---

## D-S051-08 — Both consumption paths get a test, not a claim

```text
LOCKED  S051-T009 proves the rule-based path: an example strategy composing at
        least two new components, loaded through the UNMODIFIED strategy_file
        loader, with a test asserting the new components appear in the run's
        analysis lineage — not merely that the run succeeded.
LOCKED  S051-T010 proves the predictive path: a PredictiveStudySpec declaring
        at least three new components as FeatureSpec entries, built against the
        EXISTING SYNTHETIC CI fixture, asserting the labelled matrix's
        available_at <= detected_at invariant for the new features.
LOCKED  Neither test touches real data or the network. ADR-0023 §8 is untouched.
```

This is PRD success metric 1, made executable. "Shared catalog" is a claim about
this framework's architecture; a sprint that asserts it in prose and not in a
test has not delivered it.

---

## D-S051-09 — Testing and CI

```text
LOCKED  Everything in this sprint runs in DEFAULT CI: no extra, no network.
LOCKED  Per component: value correctness against independently computed
        expectations; warm-up / valid_from_index; the degenerate window; and a
        CAUSALITY test (truncating the series after bar n leaves values at and
        before n unchanged).
LOCKED  MACD additionally gets a planner/DAG test proving its two trend.ema
        dependencies resolve through the normal dependency machinery.
LOCKED  No test may read from user_data/ or hit the network.
```

---

## D-S051-10 — Why no ADR

Considered and declined. Every element has a merged precedent that needed none:

```text
new component + NumPy impl + DSL reference + registry entry
        -> candle.wick (S047), trend.ema_distance / volatility.range_expansion (S048)
a new dotted namespace
        -> candle. (S047)
a component depending on two other components' outputs
        -> volatility.range_expansion (S048)
running an existing importer
        -> no decision at all; ADR-0025 already governs it
```

No new dependency, no boundary change, no contract change, no new storage
format, no reversal of an accepted decision. Writing one here would be the "an
ADR for every class" anti-pattern. If Sprint 052 finds the Phase 10 pipeline
must change to run a real-data study, *that* earns an ADR — then, not now.

---

## D-S051-11 — What this sprint hands to Sprint 052

```text
1. Six component IDs with locked parameter and output names (D-S051-03).
2. S051_BTC_DATA_INVENTORY.md — the measured dataset facts Sprint 052's fold
   design is computed from. Without it, Sprint 052's Wave 0 cannot be locked,
   and D-S051-07a forbids substituting a different instrument to unblock it.
3. The documented warning that short-window higher moments are outlier-dominated
   at 1m (D-S051-03), which Sprint 052 answers with evaluation_timeframe.
```

Nothing else. Sprint 051 makes no claim about whether these features predict
anything.

---

## D-S051-12 — Wave 0 Checklist (maintainer)

Nothing below may be checked off by an agent. `engineer` must refuse to start
while any box is unchecked.

Boxes marked `[x] — ANSWERED (A#)` record a decision the maintainer gave
directly on 2026-09-02, relayed through the coordinating session. **The
remaining unchecked boxes are still outstanding: this sprint is NOT approved to
start.**

- [x] **ROADMAP §13G approved** (`PROPOSED` -> accepted): Phase 15 exists and is **two** increments (15A this sprint, 15B Sprint 052).
- [x] **The numbering confirmed** — Sprint 051 / Phase 15A / §13G; **Sprint 050 stays reserved for Phase 14B** and is not consumed here.
- [x] **D-S051-03 confirmed** — exactly these six components, these parameter names and defaults, these output names; new `momentum.` and `statistics.` namespaces; a seventh component is out of scope.
- [x] **PRD Open Question 1 answered as D-S051-03** — rolling population skew + excess kurtosis of log returns, with Bowley skew recorded as a fallback that would be a *new* component, not a silent substitution.
- [x] **D-S051-04 confirmed — ANSWERED (A3), 2026-09-02.** `momentum.stochastic` returns **50.0** on a zero-range window, deliberately diverging from the project's `0.0` convention. **The deviation and its reasoning (avoiding a false "close is at the low" signal) go in the component docstring itself**, so a future reader does not "fix" it back to `0.0` as an inconsistency; plus the test name and `STRATEGY_AUTHORING.md`.
- [x] **D-S051-05 confirmed** — Wilder RSI; MACD signal computed in-component from the shared kernel; population moments; no library-matching.
- [x] **PRD Open Question 4 answered as D-S051-06** — single timeframe, because MTF features are currently **inexpressible** in a `PredictiveStudySpec`; the optional DSL `timeframe=` kwarg for Signal Model consumers is accepted; the `FeatureSpec` contract change is explicitly NOT taken.
- [x] **D-S051-07 — ANSWERED (A1), 2026-09-02.** No `BTCUSDT.P` data exists today (contradicting the PRD's premise). Import range: **`BTCUSDT.P`, 1m, 2024-01-01 → 2026-06-30 (~1.31M bars)**. The wall-clock cost under Binance weight limits is accepted as a **known, priced cost** per ADR-0025's Consequences — slowness is not a finding and not a trigger to trim the range.
- [x] **D-S051-07a — ANSWERED (A2), 2026-09-02.** The NQ.c.0 fallback is **REJECTED as an automatic substitute**. If the import proves impractical the work **STOPS and returns to the maintainer**; substituting NQ data is not an engineer decision. Reason: NQ does not satisfy §13F's Q5 wording ("on BTC data"), and treating it as equivalent is precisely the silent scope drift governance exists to prevent.
- [x] **D-S051-08 confirmed** — both consumption paths get a test, and the predictive-path test stays on the synthetic CI fixture (ADR-0023 §8 untouched).
- [x] **D-S051-09 confirmed** — everything runs in default CI; no extra, no network, no `user_data/` reads in tests.
- [x] **D-S051-10 confirmed** — no ADR for this sprint, with the reasoning above.
- [x] **Sprint 051 scope approved as 11 tasks, 4 waves**, shipping **no** study, **no** run and **no** verdict.
- [x] **Branch `sprint/momentum-and-regime-catalog` approved**, cut from `origin/main` @ `5bd9969` (re-verified by the orchestrating session before this checklist's approval).

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-02. The maintainer was
shown this checklist's full content and scope (all 15 items above, including
the six-component set, the single-timeframe-first decision, the no-new-ADR
reasoning, and the branch cut point) and answered: "Tak, zatwierdzam całą
checklistę Wave 0 Sprintu 051" — explicit approval of the checklist as a
whole, in addition to the item-by-item answers (A1/A2/A3) already recorded
above.

Once every box is checked, the first task for `engineer` is **S051-T001**
(Wave 0 locks + the ROADMAP §13G splice, docs only) on
`docs/momentum-regime-catalog-planning`, cut from
`sprint/momentum-and-regime-catalog`. **S051-T002 (the import) should be started
by the maintainer at the same time**, since it is the sprint's only long-lead
item and the only input Sprint 052 cannot proceed without — and, per
D-S051-07a, the only acceptable input.
