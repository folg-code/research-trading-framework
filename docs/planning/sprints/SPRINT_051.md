# Sprint 051 — Momentum and Regime Component Catalog (Phase 15A)

## Metadata

```text
Sprint: 051
Phase: Phase 15 — Predictive Research Catalog Expansion and Real-Data Study;
       increment 15A (opening increment; NOT closing — Sprint 052 closes the phase)
Status: APPROVED (2026-09-02) — Wave 0 Checklist D-S051-12 in
        S051_WAVE0_DECISIONS.md signed off in full by the maintainer.
Planned Start: 2026-09-02
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_003/006 (component + DSL machinery), SPRINT_037/038 (catalog precedent),
            SPRINT_047/048 (the two most recent catalog additions — the pattern to copy),
            SPRINT_045 (the Binance importer this sprint RUNS but does not modify)
Depended On By: SPRINT_052 (Phase 15B — consumes these component IDs and the
            BTC dataset inventory this sprint produces)
Sprint Branch: sprint/momentum-and-regime-catalog
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/momentum-and-regime-catalog (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S051_WAVE0_DECISIONS.md
Numbering: verified against origin/main @ 5bd9969 (fetched 2026-09-02), the
        Sprint 049 integration commit. Sprint 050 is NOT free — it is bound by
        name to Phase 14B across merged documents (ROADMAP §13F, ADR-0029,
        PREDICTIVE_PROMOTION.md, SPRINT_049.md, S049_WAVE0_DECISIONS.md). This
        sprint is 051 / Phase 15A / ROADMAP §13G; its successor is 052 / 15B.
Architecture Sources:
  - docs/product/PRD-predictive-research-catalog-expansion.md — AUTHORITATIVE, wins on conflict
  - docs/planning/ROADMAP_INCREMENT_PHASE_15.md (§13G) — PROPOSED, needs approval first
  - docs/adr/ADR-0005 + ADR-MA-001..014 — component identity, lineage, MTF, availability
  - docs/adr/ADR-0006 — declarative models / model_authoring DSL
  - docs/adr/ADR-0023 §4, §8, §9 — leakage guards, synthetic-only CI, one-instrument slice
  - docs/adr/ADR-0025 — the Binance USD-M importer this sprint runs unmodified
  - docs/adr/ADR-0026 (+ Amendment 1) — trading-cli config contract and import allow-list
  - docs/adr/ADR-0027 / ADR-0028 — strategy_file loader and Exit/Risk models (consumed)
  - src/trading_framework/market_analysis/components/volatility/range_expansion.py — the
    closest structural precedent (component-on-component dependency, zero-denominator convention)
```

---

## 0. Slice choice — why this sprint stops before the study

The PRD asks for two things: a wider catalog and a real-data study. They look
like one sprint and are not.

1. **Different acceptance kinds.** A component is done when it computes the
   right numbers causally on a fixture — deterministic, testable, reviewable in
   an afternoon. A study is done when a comparison is *reported*, and its
   outcome is unknown at planning time. One sprint goal cannot honestly cover
   both.
2. **The study's input does not exist.** Verified against the maintainer's
   workspace on 2026-09-02: `user_data/market_data/metadata/` contains only NQ
   Databento datasets. **There is no imported `BTCUSDT.P` dataset.** Sprint 045
   built the importer; nobody has run it for a real range. Acquiring that data
   is network-bound, weight-limited and measured in wall-clock hours — the exact
   shape of a long-lead item that must not sit on the critical path of code that
   is otherwise ready to merge.
3. **This sprint still delivers standalone value.** Six components usable by
   rule-based strategies today, whether or not Sprint 052 ever opens.

So Sprint 051 builds the catalog **and starts the data import as its own
task**, so that Sprint 052 can open against a known dataset instead of a hope.

---

## 1. Sprint Goal

```text
model_authoring DSL + registry (unchanged machinery)
    ↓ six new CAUSAL FEATURE components, NumPy implementations
momentum.rsi | momentum.macd | momentum.stochastic
volatility.relative_volatility | statistics.return_autocorrelation
statistics.return_distribution
    ↓ consumed TWO ways, both proven by a test
Signal Model (rule-based, via strategy_file)  +  FeatureSpec (Predictive Research)
    ↓ in parallel, no framework code involved
trading-cli data fetch binance  →  published BTCUSDT.P DatasetRef
        (1m, 2024-01-01 → 2026-06-30 — maintainer-fixed, D-S051-07)
    ↓
S051_BTC_DATA_INVENTORY.md — the ACTUAL range, row count and gaps
```

Success: the catalog is wide enough that Sprint 052's study is a fair test, and
Sprint 052's Wave 0 can compute a fold plan from measured facts.

---

## 2. In scope

- [ ] `momentum.rsi` — Wilder-smoothed RSI over close.
- [ ] `momentum.macd` — fast/slow EMA difference plus signal line and histogram.
- [ ] `momentum.stochastic` — %K over the rolling high/low range, plus %D.
- [ ] `volatility.relative_volatility` — rolling realized volatility of log
      returns and its ratio to a longer baseline window (covers both the
      "rolling" and "relative" halves of the PRD's regime bullet).
- [ ] `statistics.return_autocorrelation` — rolling lag-k autocorrelation of log returns.
- [ ] `statistics.return_distribution` — rolling skew and excess kurtosis of log returns.
- [ ] `model_authoring` DSL references for all six, in `references/` modules.
- [ ] Registry registration in `registry/builtins.py`, defaults on.
- [ ] One example Signal Model / strategy composition exercising ≥ 2 new components.
- [ ] One predictive-path build test declaring new components as `FeatureSpec`
      entries **against the existing synthetic CI fixture** (never real data).
- [ ] Running the Binance import for `BTCUSDT.P` over the maintainer-fixed range
      and writing the dataset inventory.
- [ ] Docs: `STRATEGY_AUTHORING.md` catalog rows, `MODULE_MAP.md`, ROADMAP §13G
      15A status, `CURRENT_STATUS.md`.

## 3. Out of scope

- **The study itself** — Sprint 052. No run, no result, no verdict here.
- **Any change to the Phase 10 pipeline**, `research/predictive/`, or Sprint
  049's promotion code.
- **MTF variants** of the new components, and the `FeatureSpec` contract change
  they would need (§4 Finding 2).
- Any change to `fetch_closed_klines`, the importer, or the live dry-run path —
  this sprint *runs* Sprint 045's importer, it does not touch it.
- New estimator families, new dependencies, new CI jobs, new extras.
- Orderflow, options-derived, or cross-asset components.
- A seventh component "while we're in here".
- Backfilling MTF/DSL sugar for existing components.
- **Importing or substituting any instrument other than `BTCUSDT.P`** — see
  Finding 1 and D-S051-07a.

---

## 4. Findings — read before Wave 0 is signed off

### Finding 1 — the BTC data the PRD assumes does not exist

`user_data/market_data/metadata/` on the maintainer's workspace lists eleven
datasets, all NQ/Databento (`NQ.NQH6`…`NQ.NQZ7` trades, `NQ.c.0` trades and
1m OHLCV). There is **no** Binance dataset of any kind. The PRD states
`BTCUSDT.P` bars are "a real, imported `DatasetRef`, not a fixture" — that is
the one premise in the PRD that live state contradicts.

Consequence: acquisition is a real task with real cost, and Sprint 052's fold
design cannot be locked until it completes. It is S051-T002 here, deliberately
scheduled first so it runs in the background of Waves 1–2.

**Range (maintainer-fixed, D-S051-07):** `BTCUSDT.P`, 1m,
**2024-01-01 → 2026-06-30** (~1.31M bars). The wall-clock cost under Binance
weight limits is an accepted, priced cost per ADR-0025's own Consequences — a
slow import is expected, not a finding.

**If the import proves impractical — HARD STOP (D-S051-07a).** Not "fall back to
NQ". The maintainer has explicitly **rejected** `NQ.c.0` (or any non-BTC
dataset) as an automatic substitute: record what was attempted and why in the
inventory document, **stop, and return to the maintainer**. Reason, in the
maintainer's own terms: NQ does not satisfy ROADMAP §13F's Q5 wording ("on BTC
data"), and treating it as equivalent would be exactly the silent scope drift
this project's governance exists to prevent. No agent may make that
substitution, and no downstream sprint may proceed on non-BTC data.

### Finding 2 — MTF is not a "later polish" choice here; it is currently inexpressible

`FeatureSpec` (`research/predictive/features.py`) carries
`component_id / parameters / output_id / alias / transform` and nothing else.
It maps onto `AnalysisFrameColumnSpec` (`market_analysis/assembly/frame.py`),
which likewise has no computation timeframe, and
`build_predictive_dataset._component_requests` builds each `ComponentRequest`
with `component_id` and `parameters` only.

So a multi-timeframe feature **cannot be declared in a `PredictiveStudySpec`
today at all**. The PRD's question ("do the new components need MTF variants
from day one?") therefore has a stronger answer than "precedent says later":
day-one MTF would require a contract change in two packages, which is out of
scope for a catalog sprint.

What *is* cheap and in scope: the DSL reference functions may accept an optional
`timeframe=` kwarg for **Signal Model** consumers, exactly as
`volatility.range_expansion` already does — no new machinery, and it keeps the
shared-catalog claim honest. The coarse-grid knob for the study side is
`PredictiveStudySpec.evaluation_timeframe`, which already exists.

### Finding 3 — the zero-denominator convention has a precedent, and stochastic breaks it

`candle.wick` (D-S047-10), `trend.ema_distance` and `volatility.range_expansion`
(D-S048-10) all define a zero denominator as an output of `0.0` rather than an
incidental `inf`/`NaN`.

For `momentum.stochastic`, `0.0` on a zero-range window is *semantically wrong*:
%K = 0 means "close is at the window low", which is a real, meaningful signal.
A flat window is not that. **Maintainer-confirmed (D-S051-04):** stochastic
returns `50.0` (the neutral midpoint), and **the deliberate deviation plus its
reasoning go in the component docstring itself**, so a future reader does not
"fix" it back to `0.0` as an apparent inconsistency. Same reasoning gives RSI
`100.0` when there are no losses in the window and `50.0` when the window is
entirely flat.

### Finding 4 — MACD should reuse `trend.ema`, not re-derive it

`volatility.range_expansion` is the precedent for a component that depends on
two other components' outputs rather than raw fields. MACD's line is exactly
`ema(fast) - ema(slow)`, both of which `trend.ema` already computes with a
tested kernel. The **signal line**, however, is an EMA *of the MACD line*, and
`trend.ema` reads `close` from the workspace — it cannot smooth another
component's output. So the signal line is computed inside the MACD
implementation using the shared `ema` kernel from
`adapters/numpy/kernels.py`. That is reuse of the kernel, not duplication of
the component, and it keeps the dependency graph honest.

### Finding 5 — no new ADR is warranted

Every element of this sprint has a merged precedent with no ADR of its own:
new component + NumPy implementation + DSL reference + registry entry
(`candle.wick`, Sprint 047; `trend.ema_distance` / `volatility.range_expansion`,
Sprint 048), a new dotted namespace (`candle.` was new in Sprint 047), and a
component depending on two other components (`volatility.range_expansion`).
No new dependency, no boundary change, no contract change, no new storage
format. Writing an ADR here would be the "an ADR for every class" anti-pattern.
The reasoning is recorded in the Wave 0 document so a future reader can see it
was considered and declined, not overlooked.

---

## 5. Boundaries this sprint must not cross

```text
FORBIDDEN   any edit under research/predictive/ or application/predictive_research/
FORBIDDEN   any edit to infrastructure/providers/binance/ (the importer is RUN, not changed)
FORBIDDEN   any edit to execution/, apps/dashboard/, or Sprint 049's promotion code
FORBIDDEN   a new dependency, extra, or CI job
FORBIDDEN   widening tests/unit/test_apps_boundaries.py's allow-list without a
            fresh ADR-0026 amendment (the standing lesson from Amendment 1)
FORBIDDEN   committing anything from user_data/ (gitignored, maintainer-owned)
FORBIDDEN   any real-data dependency in a test — CI stays synthetic and network-free
FORBIDDEN   substituting any non-BTC dataset for BTCUSDT.P (D-S051-07a) — that
            is a STOP-and-return-to-maintainer, never an agent decision
ALLOWED     new files under market_analysis/components/{momentum,statistics,volatility}/
ALLOWED     new kernels in adapters/numpy/kernels.py
ALLOWED     new model_authoring/references/ modules and registry/builtins.py entries
ALLOWED     new example strategy + example CLI yaml, following Sprint 047/048's shape
```

---

## 6. Task breakdown

**11 tasks, 4 waves.** Every task below is one coherent, reviewable outcome with
its own acceptance; component tasks are vertical slices (kernel + component +
DSL + registry + tests + doc row), not architectural layers.

### Wave 0 — Decisions and the long-lead data task

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S051-T001 | Land `S051_WAVE0_DECISIONS.md` and the ROADMAP §13G splice (from `ROADMAP_INCREMENT_PHASE_15.md`) on the sprint branch; add the §3 track line | the decision document is byte-consistent with the roadmap section; the "why no ADR" reasoning is present; the maintainer's recorded answers A1/A2/A3 are preserved verbatim; no production file is modified | maintainer approval | DONE |
| S051-T002 | **Data acquisition (no framework code).** Run Sprint 045's importer for `BTCUSDT.P` 1m over **2024-01-01 → 2026-06-30** (D-S051-07) via `trading-cli data fetch binance` or `scripts/market_data/import_binance_ohlcv.py`. Produce `docs/planning/sprints/S051_BTC_DATA_INVENTORY.md` | the inventory records: the exact published `DatasetRef` string, `start_at`/`end_at` and `row_count` **read from the registry metadata JSON** (not from the request), every gap listed in `import_manifest.json`, `api_key_used`, and observed wall-clock + any weight-limit backoff; it states plainly whether the range is sufficient for ≥ 5 walk-forward folds at the intended horizon; **no file under `src/` is modified and nothing from `user_data/` is committed**; **if the import proves impractical, the document says so and the task STOPS and returns to the maintainer — substituting NQ.c.0 or any other instrument is forbidden (D-S051-07a)** | T001, network, maintainer | DONE |

Wave 0 is DONE when T001 is on the branch and the maintainer has checked off the
Wave 0 Checklist. **T002 runs in the background of Waves 1–2** — it blocks
Sprint 052, not this sprint's other tasks.

### Wave 1 — Momentum components

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S051-T003 | `momentum.rsi` — component + `rsi_wilder` kernel + `references/momentum.py` `rsi()` + registry entry. Params: `period` (int, default 14, min 2). Output: `value` (float64, 0–100) | values match hand-computed Wilder RSI on a fixture the test computes independently; `valid_from_index` == `period` and earlier bars are `NaN`; a monotonically rising series gives 100.0 and a flat series gives 50.0 (D-S051-04); `history_requirement` covers the recursive warm-up; causality test: truncating the series after bar *n* does not change values at or before *n* | T001 | DONE |
| S051-T004 | `momentum.macd` — component depending on two `trend.ema` outputs (Finding 4) + `references/momentum.py` `macd()` + registry entry. Params: `fast_period` (12), `slow_period` (26), `signal_period` (9), with `fast < slow` validated. Outputs: `line`, `signal`, `histogram` | `line` equals the difference of the two dependency results bar-for-bar; `signal` equals the shared `ema` kernel applied to `line`; `histogram == line - signal` exactly; warm-up is the slow EMA's plus the signal EMA's, and is asserted; `fast_period >= slow_period` raises `ComponentValidationError` naming both; the dependency declaration resolves through the planner in a DAG test | T003 | DONE |
| S051-T005 | `momentum.stochastic` — component + rolling min/max kernel + `references/momentum.py` `stochastic()` + registry entry. Params: `period` (14), `smoothing_period` (3). Outputs: `k`, `d` | %K matches an independently computed rolling `(close - min(low)) / (max(high) - min(low)) * 100`; `d` is the SMA of `k` over `smoothing_period`; **a zero-range window yields 50.0, not 0.0** (D-S051-04, Finding 3); **the component docstring states the deviation from the project's `0.0` convention, the reason ("0.0 would fabricate a false 'close is at the low' signal") and the decision ID `D-S051-04`** — the maintainer's explicit requirement so a future reader does not revert it; the test name also names the convention; warm-up covers both windows; causality test as T003 | T003 | DONE |

Depends on: Wave 0 (T001 only). No extra required; all default CI.

### Wave 2 — Regime / statistics components

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S051-T006 | `volatility.relative_volatility` — component + rolling log-return stdev kernel + `references/volatility.py` `relative_volatility()` + registry entry. Params: `period` (20), `baseline_period` (100), validated `period < baseline_period`. Outputs: `value` (rolling realized vol) and `ratio` (`value / baseline`) | `value` matches an independently computed population stdev of `log(close_t / close_{t-1})` over `period`; `ratio` uses the same estimator over `baseline_period`; **a zero baseline yields `0.0`** per the existing convention (D-S048-10) with a test; warm-up is `baseline_period` (returns lose one bar) and is asserted; `period >= baseline_period` raises naming both | T001 | DONE |
| S051-T007 | `statistics.return_autocorrelation` — new `statistics.` namespace package + component + kernel + `references/statistics.py` `return_autocorrelation()` + registry entry. Params: `period` (60, min 8), `lag` (1, min 1), validated `lag < period - 1`. Output: `value` (−1..1) | matches an independently computed rolling Pearson correlation between the return series and its lag-`k` shift within each window; a constant-return window (zero variance) yields `0.0` per convention, tested; a perfectly alternating synthetic series yields a value near −1 as a semantic sanity check; warm-up `period + lag` asserted; causality test | T001 | TODO |
| S051-T008 | `statistics.return_distribution` — component + kernel + `references/statistics.py` `return_skew()` / `return_excess_kurtosis()` + registry entry. Params: `period` (60, min 8). Outputs: `skew`, `excess_kurtosis` | Fisher–Pearson **population** moments (no small-sample bias correction — determinism and a single documented estimator beat matching any particular library, D-S051-05), verified against values the test computes from first principles; a zero-variance window yields `0.0` for both; excess kurtosis of a synthetic normal-ish sample is near 0 as a sanity check; warm-up `period + 1` asserted; the docstring states the estimator explicitly and warns that short windows on 1m bars are outlier-dominated (Sprint 052 Wave 0 consumes this warning) | T007 | TODO |

Depends on: Wave 0. T008 depends on T007 only for the shared `statistics/`
package scaffolding.

### Wave 3 — Both consumption paths, proven

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S051-T009 | **Rule-based consumption (PRD metric 1, half one).** One worked example strategy under `user_data/components/strategies/` **documented in `STRATEGY_AUTHORING.md`** plus its `apps/cli/examples/research_run_strategy_*.yaml`, composing ≥ 2 new components (suggested: `momentum.rsi` oversold gated by `volatility.relative_volatility` regime), reusing Sprint 048's Exit/Risk models unchanged; plus the framework-side end-to-end test following Sprint 047's `uses_candle_wick.py` fixture pattern | the strategy loads through the unmodified `strategy_file` loader and produces a run whose `strategy_model_id` is the loaded strategy's; the test asserts the new components actually appear in the run's analysis lineage (not merely that the run succeeded); no Exit/Risk or loader file is modified | T003, T006 | TODO |
| S051-T010 | **Predictive consumption (PRD metric 1, half two).** A test that builds a `PredictiveStudySpec` declaring ≥ 3 new components as `FeatureSpec` entries **against the existing synthetic CI fixture** (D-S039-CI-dataset) and runs `build_predictive_dataset` to a labelled matrix with fold roles | the dataset builds and the declared aliases resolve to the new components' lineage; the matrix's `available_at <= detected_at` invariant holds for every new feature (the leakage guard, ADR-0023 §4, applied to the new components specifically); **no real data and no network are involved** — ADR-0023 §8 is untouched, asserted by the test living in the standard suite | T005, T008 | TODO |
| S051-T011 | Documentation and closure: `STRATEGY_AUTHORING.md` catalog rows for all six components (parameters, outputs, conventions, the stochastic divergence), `MODULE_MAP.md`, ROADMAP §13G's 15A line, `CURRENT_STATUS.md` §2/§6/§11, and the sprint Review — including whether S051-T002 succeeded and what Sprint 052 may therefore assume | every new component appears exactly once in the catalog documentation with its zero-denominator convention stated; the Review states the **measured** BTC dataset range or, if T002 did not complete, says so plainly and records that Sprint 052 cannot open on substitute data (D-S051-07a); `CURRENT_STATUS.md` never claims Phase 15 is complete | T009, T010, T002 | TODO |

**Progress:** 6 / 11

**Descope order if the sprint overruns:** T008 first (return-distribution is the
PRD's most negotiable component), then T005. **T002, T009 and T010 are never
dropped** — they are the sprint's only proof that the catalog is real and that
Sprint 052 has an input.

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/momentum-regime-catalog-planning` | T001: Wave 0 locks + ROADMAP §13G splice |
| 1 | `docs/btc-dataset-inventory` | T002: the acquisition record (docs only; runs in parallel) |
| 2 | `feat/momentum-rsi` | T003 |
| 3 | `feat/momentum-macd-stochastic` | T004–T005 |
| 4 | `feat/relative-volatility` | T006 |
| 5 | `feat/return-statistics-components` | T007–T008 |
| 6 | `test/catalog-both-consumers` | T009–T010 |
| 7 | `docs/momentum-regime-catalog-guide` | T011 |

PR 1 is independent of everything else and should be opened as soon as the
import finishes. PRs 2–5 are independent of each other except T004/T005's shared
`momentum` package scaffolding (created by PR 2).

---

## 8. Acceptance criteria

1. Six new components exist, each `ComponentKind.FEATURE` and
   `Causality.CAUSAL`, each with a parameter schema, an output schema, a
   `history_requirement` that covers its warm-up, and a NumPy implementation.
2. Every component has a causality test proving that truncating the input series
   does not change already-emitted values.
3. Every zero-denominator / degenerate-window case has an explicitly documented,
   tested value — and stochastic's divergence from the `0.0` convention is
   stated **in the component docstring**, in the test name and in
   `STRATEGY_AUTHORING.md`, not only in Wave 0.
4. All six are registered in `registry/builtins.py` with `default=True` and are
   reachable through `model_authoring` DSL references.
5. `momentum.macd` declares its two `trend.ema` dependencies through
   `component_dependencies` and resolves through the planner — no re-derivation
   of EMA inside the component.
6. PRD success metric 1 is executable: one example strategy consumes ≥ 2 new
   components end to end, and one test declares ≥ 3 of them as predictive
   `FeatureSpec` entries that build a labelled matrix.
7. `S051_BTC_DATA_INVENTORY.md` records the **measured** dataset facts read from
   the registry metadata for the maintainer-fixed range — or an explicit
   impracticability statement plus a stop, never a substitute instrument.
8. No file under `research/predictive/`, `application/predictive_research/`,
   `infrastructure/providers/binance/`, `execution/`, or Sprint 049's promotion
   code is modified.
9. No new dependency, extra, or CI job. Default CI stays network-free and
   extra-free, and every new test runs in it.
10. Documentation states each component's parameters, outputs, warm-up and
    conventions exactly once, in `STRATEGY_AUTHORING.md`.
11. `CURRENT_STATUS.md` and ROADMAP §13G reflect 15A only — Phase 15 is not
    claimed complete.

---

## 9. Dependencies

**Required:** ROADMAP §13G (Phase 15) approved. **Status: PROPOSED.**

**Required:** the Wave 0 Checklist in `S051_WAVE0_DECISIONS.md`, signed off by
the maintainer. Three of its items (D-S051-04, D-S051-07, D-S051-07a) are
already answered; the remainder are not.

**Required for S051-T002 only:** network access and maintainer wall-clock time.
The range is no longer an open question (D-S051-07).

**Not required:** any ML extra (`ml`, `ml-trees`, `dl`); the Sprint 049
promotion mechanism; any dashboard change; any new ADR.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **The BTC import stalls or is rate-limited into impracticality** | T002 is scheduled first and runs in parallel; slowness is a priced, accepted cost (D-S051-07), so only genuine impracticability triggers anything. That trigger is a **hard stop back to the maintainer** (D-S051-07a) — never a switch to NQ or another instrument. |
| Rolling higher moments are numerically fragile | T008 locks a single documented estimator (population Fisher–Pearson) and tests it from first principles; the docstring warns about short windows, and Sprint 052's Wave 0 must choose window and grid accordingly. |
| **Stochastic's `50.0` is later "fixed" back to `0.0` as an inconsistency** | The maintainer's explicit requirement: the deviation and its reasoning live in the **component docstring**, where the person tempted to change it is already reading — plus the test name, `STRATEGY_AUTHORING.md` and D-S051-04. |
| MACD's signal line silently re-implements EMA | T004's acceptance requires the shared kernel, and the `line` output is asserted against the dependency results bar-for-bar. |
| Catalog scope creep to a seventh component | Six is the PRD-named set; §3 forbids additions; a seventh is an Idea Inbox entry. |
| A new component quietly leaks look-ahead into the predictive path | T010 asserts `available_at <= detected_at` on the new features specifically, in addition to each component's own causality test. |
| The plan drifts against `main` while awaiting approval | Sprint 049's own lesson (18 commits behind, colliding numbers). This plan is pinned to `origin/main` @ `5bd9969`; re-check before cutting the branch. |

---

## 11. Quality gates

- `ruff`, `mypy`, `pytest` green for all workspaces; default CI stays network-free
  and extra-free.
- Every new component has: a value-correctness test against independently
  computed expectations, a warm-up/`valid_from_index` test, a degenerate-window
  test, and a causality test.
- No test reads from `user_data/` or the network.
- Each PR is one coherent outcome, ≤ ~600 lines of meaningful change.

---

## 12. Post-sprint direction

Sprint 052 (Phase 15B) opens against this sprint's two outputs: the component
IDs and `S051_BTC_DATA_INVENTORY.md`. If T002 did not complete, Sprint 052 does
not open — and per D-S051-07a it may not be unblocked by substituting another
instrument; the decision returns to the maintainer.

Unscheduled candidates raised but deliberately not taken here: MTF-capable
`FeatureSpec` (needs a contract change in two packages), a volume-based regime
component (no PRD mandate), and quantile-based (Bowley) skew as a robust
alternative to the moment estimator if T008's feature proves too noisy in
Sprint 052.

---

## 13. Review

_(to be written at closure by `tech-writer`)_
