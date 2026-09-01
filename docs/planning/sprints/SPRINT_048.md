# Sprint 048 — Exit/Risk Model Expansion, Catalog Growth and New Strategies (Phase 13)

## Metadata

```text
Sprint: 048
Phase: Phase 13 — Exit/Risk Model Expansion (opening and, in scope terms, closing increment)
Status: APPROVED — Wave 0 Checklist (D-S048-14) signed off by the maintainer on 2026-09-01
Planned Start: 2026-09-01
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_047 (strategy_file loader + candle.wick/structure.level_distance;
                        merged to main via #366),
            SPRINT_013 (Strategy Model, Exit/Risk contracts, BarSequentialSimulator),
            SPRINT_046 (the CLI this runs through; merged via #361),
            SPRINT_037/038 (model_authoring DSL, component reference pattern)
Sprint Branch: sprint/exit-risk-and-catalog
Task branch convention: feat/ | fix/ | docs/ | test/
PR base: sprint/exit-risk-and-catalog (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S048_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/product/PRD-exit-risk-and-catalog-expansion.md (confirmed)
  - docs/adr/ADR-0028 (bracket exits + equity sizing) — ACCEPTED (declined for S047,
    resumed with corrections for S048), blocks this sprint
  - docs/adr/ADR-0027 (the loader) — ACCEPTED, reused UNCHANGED
  - docs/adr/ADR-0016 (the Strategy Research MVP; its MVP gates are what this widens)
  - docs/adr/ADR-0026 + Amendment 1 (the CLI boundary this must not touch)
  - docs/planning/ROADMAP.md §13E (Phase 13, applied in this sprint's planning PR)
```

---

## 0. Slice choice

Sprint 047 shipped two of its PRD's three pieces. The third —
`BracketExitModel` / `EquityPercentRiskModel` — was designed in full (ADR-0028),
and the maintainer declined it **for that sprint**, as a scope decision, not a
technical objection. The design was kept, explicitly, for a sprint like this one.

So this sprint is **not new design work**. It is the resumption of a designed,
deferred wave — with one obligation attached, which the PRD names as its own
riskiest assumption: re-verify ADR-0028's engine-change list against the code as
it stands, rather than resurrecting a stale analysis. §4 is that verification.
It found ADR-0028's blockers entirely intact and its **change list incomplete**.

Like Sprint 047 (and unlike Phase 2F/11's two independent tracks), the four
pieces are **gated on each other for a working demonstration**:

```text
engine unchanged        -> the new models are constructible dead code
new models, no catalog  -> nothing interesting to compose them with
catalog, no strategies  -> nothing proves the pieces work together
strategies, no engine   -> the run refuses at three separate isinstance gates
```

**One sprint, sequential waves.**

**Out of scope by design:** dynamic equity-curve-following sizing (TD-026), a
declarative YAML strategy format, bracket-aware Robustness stress dimensions,
and arithmetic in the model-expression IR — all four deliberately left open, all
four named in the PRD's non-goals.

---

## 1. Sprint Goal

```text
user_data/.../ema_reversion_bracket.py
    def build_strategy() -> StrategyModelDefinition
        market/signal composed from trend.ema_distance
        exit_model = BracketExitModel(stop_loss_bps=..., take_profit_bps=..., max_bars=...)
        ↓
research.strategy.strategy_file: <that path>        (Sprint 047, unchanged)
        ↓
trading-cli research run strategy --config <path>
        ↓
validate_strategy_model_definition   -> supported-combination check, not "MVP only"
run_strategy_research                -> structural check, not isinstance
BarSequentialSimulator               -> dispatch: PriceBracketExit -> kernels/bracket.py
        ↓
trades table with MORE THAN ONE distinct exit_reason:
    stop_loss | take_profit | max_bars

and, simultaneously, unchanged:
    the canonical Sprint 013 strategy produces a byte-identical trades table,
    equity table and run_id.
```

New to compose with:

```text
trend.ema_distance          (close - EMA) / ATR, signed, scale-free
volatility.range_expansion  true_range / ATR, dimensionless
BracketExitModel            stop / target in bps + mandatory max_bars timeout
EquityPercentRiskModel      static, authoring-time equity-percent sizing
```

Success: an operator writes "risk 1% of 100k, stop 50 bps, target 120 bps, give
up after 40 bars" and gets a run whose trades table shows which of those three
things actually happened, trade by trade — while every existing fixed-bars run
is provably untouched.

---

## 2. In scope

- [ ] Golden-run capture on the **unmodified** tree, committed as a fixture (D-S048-07).
- [ ] `BracketExitModel` + `PriceBracketExit` protocol + `ExitReason` new members.
- [ ] `EquityPercentRiskModel` (static, authoring-time) + TD-026.
- [ ] The five bounded engine changes of ADR-0028's Resumption section / D-S048-06, including the run-identity generalization.
- [ ] New `research/simulation/kernels/bracket.py` with its own result type and per-trade-reason materializers. `kernels/fixed_bars.py` untouched.
- [ ] `trend.ema_distance` and `volatility.range_expansion` components + DSL references.
- [ ] Three example strategies + committed example configs, loaded through the **unchanged** Sprint 047 mechanism.
- [ ] `STRATEGY_AUTHORING.md` bracket/sizing sections (both fill conventions, the operator-owned stop consistency); `MODULE_MAP.md` / `ARCHITECTURE_OVERVIEW.md`; TD-026/027/028.

## 3. Out of scope

- Dynamic, equity-curve-following position sizing (TD-026).
- **Any** modification to the `ExitModel` / `RiskModel` Protocol definitions.
- **Any** edit to `kernels/fixed_bars.py`, `research/simulation/compile.py`, or `research/simulation/input.py`.
- **Any** edit to `apps/cli` — the loader returns any `StrategyModelDefinition` already and knows nothing about exit models.
- A declarative (YAML/JSON) strategy specification format.
- Bracket-aware Robustness stress dimensions; generalizing the delay stress (TD-027).
- A reference (non-njit) implementation of the bracket kernel (TD-028).
- Arithmetic in the model-expression IR.
- Cross-validating `EquityPercentRiskModel.stop_distance` against `BracketExitModel.stop_loss_bps` (D-S048-05: the operator owns it).
- Any third catalog component, any fourth example strategy.

---

## 4. Findings — the re-verification the PRD demanded

Read against the current tree (post-Sprint-047), before anything was planned.
**ADR-0028's blockers are entirely intact. Its change list is not.**

### Finding 1 — ADR-0028's Blockers 1-4 still hold, verbatim

| Blocker | Current location | Status |
|---|---|---|
| `ExitModel.exit_bar_index(*, entry_fill_bar_index: int) -> int` — no price, no bar, no direction | `strategy/exit_model.py:27` | unchanged |
| `_require_fixed_bars_exit` / `_require_fixed_quantity_risk` gate on concrete classes at both simulator entry points | `research/simulation/engine.py:168-181`, called at `:72-73` and `:124-125` | unchanged |
| `validate_strategy_model_definition` repeats both guards, message verbatim ("MVP supports FixedBarsExitModel only") | `strategy/strategy_model.py:39-44` | unchanged |
| `simulate_fixed_bars_exit_kernel` is an `@njit` loop over `observed_at_ns` + `open_prices` only | `kernels/fixed_bars.py:197-302` | unchanged |

Also confirmed unchanged: `ExitReason` has only `FIXED_BARS`;
`RiskModel.position_quantity()` still takes no arguments. **ADR-0028 §3 (bracket
semantics) and §4 (equity-percent sizing) are adopted with zero edits.**

### Finding 2 — a THIRD pair of identical gates, one layer above the engine

```python
# application/strategy_research/run_strategy_research.py:106-107
exit_model = _require_fixed_bars_exit(strategy_model)      # StrategyResearchError
risk_model = _require_fixed_quantity_risk(strategy_model)  # StrategyResearchError
```

ADR-0028 §2 and `S047_WAVE0_DECISIONS.md` D-S047-12 name only
`strategy/strategy_model.py` and `research/simulation/engine.py`. But
`trading-cli research run strategy` calls `run_strategy_research`, so this gate
fires **before** the engine's ever does. Building ADR-0028's four changes exactly
as written would produce a bracket model that passes validation and the
simulator, and is still refused by the application layer — i.e. PRD success
metric 1 unreachable, discovered mid-sprint. **Four changes becomes five.**

### Finding 3 — run identity hashes a FixedBars-only field (the highest-risk item)

```python
# research/datasets/strategy_research.py:107-142
def derive_strategy_run_id(*, ..., exit_model_id: str, exit_after_bars: int, ...)
    payload = "|".join([..., exit_model_id, str(exit_after_bars), risk_model_id, ...])
    return sha256(payload).hexdigest()[:16]
```

Called at `run_strategy_research.py:143-150` with
`exit_after_bars=exit_model.exit_after_bars`. `BracketExitModel` has no such
field. ADR-0028 never mentions this at all — and it is the one place where a
careless change silently re-identifies **every existing persisted run**.

**Consequence for the design.** D-S048-06 locks the minimum-blast-radius fix:
the parameter becomes `exit_model_parameters: str`, and `FixedBarsExitModel`
must emit exactly `str(exit_after_bars)` so the hashed payload is byte-identical.
The golden run asserts `manifest.run_id` for exactly this reason.

### Finding 4 — trade materialization takes one scalar exit reason

```python
# kernels/fixed_bars.py:127-135
def materialize_kernel_trades(result, *, ..., exit_reason: ExitReason, ...)
```

One reason for the whole run. A bracket run emits three, per trade. That
function lives in the file ADR-0028 locks as not-edited. Resolved cleanly rather
than awkwardly: `kernels/bracket.py` carries its own result dataclass and its own
materializers, with a per-trade reason array. `fixed_bars.py` stays
byte-identical, and the golden run proves it.

### Finding 5 — "byte-identical run fingerprint" names a field that doesn't exist

`StrategyResearchRunManifest` (`research/datasets/strategy_research.py:41-56`)
has `run_id` and `simulation_assumptions_fingerprint`. There is no
`run_fingerprint`; `compute_run_fingerprint` belongs to Predictive Research
alone. ADR-0028 and the PRD both use the phrase. D-S048-07 replaces it with an
explicit field-by-field list, plus the excluded nondeterministic fields
(`created_at_utc`, `framework_version`) — so "the golden run passed" means
something checkable rather than approximately reassuring.

### Finding 6 — unexpectedly good news: the compile layer already carries high/low

`CompiledBarSeries` has `high_prices`, `low_prices` and `close_prices`
(`research/simulation/input.py:16-29`), populated by **both**
`_compile_bar_series` and `_compile_bar_series_from_columnar`
(`compile.py:84-156`). ADR-0028's Blocker 4 is about the kernel, not the data:
the bars a stop needs are already compiled and passed in.

```text
No change to compile.py. No change to input.py. Nothing to re-approve there.
```

### Finding 7 — the consumer audit ADR-0028 left open, closed

ADR-0028 said `FixedBarsExitModel` consumers "must be audited". The audit is in
D-S048-08, per consumer with a reason. Two need decisions, not just notes:

- `research/robustness/stress.py:250-257` — the delay stress dimension
  reconstructs `FixedBarsExitModel(exit_after_bars + extra)`. A bracket strategy
  hits its `isinstance` gate. There is no obviously correct meaning for "delay a
  price-triggered exit by N bars", so it **keeps raising**, with a message that
  explains why, logged as TD-027. Inventing a semantic here would be an
  unreviewed research decision smuggled into an engine sprint.
- `research/simulation/kernels/reference.py` — the non-njit cross-check for the
  fixed-bars kernel, typed to `FixedBarsExitModel`. The bracket kernel gets **no**
  reference counterpart in v1 (TD-028); it is verified against hand-computed
  fixtures whose expected fills are written by hand, never derived from the
  implementation.

The remaining consumers (dashboard analytics, `facts.py`, `strategy_template.py`,
`live_signals.py`) are safe, each for a stated reason.

---

## 5. Boundaries this sprint must not cross

```text
Unchanged     kernels/fixed_bars.py — not one character
Unchanged     research/simulation/compile.py and input.py (Finding 6)
Unchanged     ExitModel and RiskModel Protocol definitions
Unchanged     apps/cli — the loader, the config schema, the allow-list
Unchanged     the numeric output AND run_id of the fixed-bars path (D-S048-07)
Unchanged     every existing script, its flags and its tests
Unchanged     the five existing files in user_data/components/strategies/
Not built     a bracket reference kernel (TD-028), bracket-aware stress (TD-027)
STOP-and-ask  a sixth engine change, if implementation reveals one is needed
```

---

## 6. Task breakdown

### Wave 0 — Planning

Binding locks: `S048_WAVE0_DECISIONS.md`. No numbered task. Wave 0 is DONE when
that file is on the sprint branch, **ADR-0028 is ACCEPTED (resumed)**, and the maintainer
has checked off the Wave 0 Checklist (D-S048-14).

### Wave 1 — The safety net, then the gates (never dropped)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S048-T001 | Capture the golden run on the **unmodified** tree: run the canonical Sprint 013 strategy on the committed OHLCV fixture through `run_strategy_research`, serialize the trades and equity DataFrames and the deterministic manifest fields (D-S048-07's list) as a committed fixture, and add the regression test that asserts them | the test passes on the unmodified tree; the fixture was produced by a script/test committed alongside it, not pasted by hand; `created_at_utc` and `framework_version` are excluded and the exclusion is commented with its reason | Wave 0 | TODO |
| S048-T002 | Widen the two ADR-0016-era MVP gates in `strategy/strategy_model.py` into a supported-combination / structural check (any dispatchable `ExitModel` x any `RiskModel` exposing `position_quantity` + `allows_new_entry`); keep a clear rejection message for genuinely unsupported combinations | a `FixedBarsExitModel`/`FixedQuantityRiskModel` definition validates exactly as before; a plain object missing `position_quantity` is still rejected, by structure, with a message naming what is missing; the `SignalDirection.NEUTRAL` check is untouched | T001 | TODO |
| S048-T003 | `engine.py`: `_require_fixed_quantity_risk` -> structural `RiskModel` check; `_require_fixed_bars_exit` -> dispatch (FixedBars -> existing kernel; `PriceBracketExit` -> new kernel, stubbed to raise until T006; anything else -> the same `SimulationEngineError` message as today). Applied at **both** call sites | the golden run (T001) still passes byte-identically; an unknown exit model produces the identical error message it produces on `main`; both `simulate()` and `simulate_from_columnar()` dispatch through the same helper, not two copies | T002 | TODO |
| S048-T004 | `run_strategy_research.py` (Finding 2) + `derive_strategy_run_id` (Finding 3): replace the application-layer `isinstance` gates with the same dispatch/structural checks; generalize `exit_after_bars: int` -> `exit_model_parameters: str` with `FixedBarsExitModel` emitting exactly `str(exit_after_bars)`; manifest construction stops reading exit-model-specific attributes | the golden run's `manifest.run_id` is byte-identical (this is the acceptance criterion, not a side effect); a unit test asserts the emitted payload substring for FixedBars is unchanged; two different exit models with coincidentally similar parameters cannot produce one `run_id` | T003 | TODO |

Depends on: Wave 0 only. **T001 lands first and alone.** No engine change may be
committed before the golden run exists on the sprint branch.

### Wave 2 — The models and the kernel (never dropped)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S048-T005 | `BracketExitModel` + `PriceBracketExit` protocol + `ExitReason` `STOP_LOSS` / `TAKE_PROFIT` / `MAX_BARS`, per D-S048-04; `ExitModel` Protocol unmodified; run the D-S048-08 consumer audit and implement its two decisions (TD-027 message in `stress.py`; no reference kernel) | `BracketExitModel` satisfies `ExitModel` (`exit_bar_index` returns `entry_fill + max_bars`) and `PriceBracketExit`; `max_bars < 1` and non-positive bps are `ValidationError`s; `stress.py` rejects a bracket exit with a message naming the model and the reason; every row of D-S048-08 has a passing test or an explicit "no behaviour to test" note | T004 | TODO |
| S048-T006 | `research/simulation/kernels/bracket.py`: an `@njit` kernel over `open/high/low` implementing D-S048-04's locked semantics, plus its own result dataclass and per-trade-reason materializers (Finding 4). `fixed_bars.py` not edited | hand-computed fixtures pass for stop-only, target-only, same-bar both (**stop wins**), gap through the stop on the entry bar, and timeout — long and short each, with slippage applied against the trade; the timeout exit's fill matches the fixed-bars next-bar-open convention exactly; `git diff` shows zero changes to `fixed_bars.py` | T005 | TODO |
| S048-T007 | `EquityPercentRiskModel` per D-S048-05: `quantity` derived once in `__post_init__`, `RiskModel` satisfied unchanged; docstring states the static limitation in plain words; TD-026 logged with its named repayment trigger | the derivation is asserted against hand-computed values including a `Decimal` rounding case; `risk_percent > 1`, `stop_distance <= 0` and a derived quantity of 0 are all `ValidationError`s; no docstring, test name or log line describes it as equity-curve-following | T004 | TODO |
| S048-T008 | Wire the dispatch to the real kernel and prove both models run end to end through `BarSequentialSimulator` and `run_strategy_research` on the committed fixture | a bracket strategy produces a trades table with more than one distinct `exit_reason`; an `EquityPercentRiskModel` strategy on the **fixed-bars** kernel runs unchanged (the isolation case); the golden run still passes | T006, T007 | TODO |

Depends on: Wave 1 complete. **This wave is the sprint's reason to exist. If it
cannot land, the sprint is abandoned and reopened — not descoped into a
catalog-only sprint, which is what Sprint 047 already was.**

### Wave 3 — Component catalog (exactly two)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S048-T009 | `trend.ema_distance` FEATURE component (depends on `trend.ema` + `volatility.atr`) outputting signed `distance_atr`; DSL `trend.ema_distance(period=20, atr_period=14, timeframe=None)` following the `LevelDistanceComponent` shape exactly | causal, no look-ahead; `valid_from_index` respects `max(EMA, ATR)` warmup; the zero-or-NaN-ATR convention is documented in the docstring and asserted by a test; the DSL returns an `Operand` usable in a `Condition`; MTF behaviour matches its dependencies | T004 | TODO |
| S048-T010 | `volatility.range_expansion` FEATURE component (depends on `volatility.true_range` + `volatility.atr`) outputting dimensionless `ratio`; DSL `volatility.range_expansion(period=14, timeframe=None)` | causal; ATR warmup respected; zero-or-NaN-ATR convention documented and tested; a hand-computed fixture asserts `ratio == true_range / atr` on known bars | T009 | TODO |

Depends on: Wave 1 (for a stable tree), not on Wave 2. **This is the descope
wave** — drop T010 first, then T009. Never Waves 1 or 2.

### Wave 4 — Composition, docs, closure

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S048-T011 | Three example strategies per D-S048-11 (`ema_reversion_bracket`, `range_expansion_breakout`, `quiet_wick_rejection`) under `user_data/components/strategies/`, each with a committed example config under the Sprint 046 examples location, and each reproduced verbatim in the docs (ADR-0002 — the directory is gitignored) | all three run through `trading-cli research run strategy` with **no** edit to `apps/cli`; E1's parameters produce at least one `stop_loss`, one `take_profit` and one `max_bars` trade on the fixture; E3 runs on the unchanged fixed-bars kernel with `EquityPercentRiskModel` | T008, T010 | TODO |
| S048-T012 | Framework-side end-to-end test: a bracket strategy loaded through `strategy_file` produces a run whose trades table contains more than one distinct `exit_reason` and whose manifest carries `exit_model_id == "bracket"` (PRD success metric 1) | the test fails if the run silently falls back to a fixed-bars path or if only one exit reason ever appears; committed fixture data only, no network, no ML extra | T011 | TODO |
| S048-T013 | Docs and closure: `STRATEGY_AUTHORING.md` gains bracket + sizing sections (both fill conventions in one strategy; the operator-owned stop-consistency caveat; the three examples verbatim); `MODULE_MAP.md` + `ARCHITECTURE_OVERVIEW.md` entries for `kernels/bracket.py` and the two components; TD-026/027/028 in `TECHNICAL_DEBT.md`; `CURRENT_STATUS.md` §2/§6/§11/§12; ROADMAP §13E Status PROPOSED -> COMPLETE; the sprint Review section | a reader of the trades table can learn from the guide why two exit rows in the same run used different fill conventions; every TD entry has a named repayment trigger; the config schema still appears exactly once | T012 | TODO |

**Progress:** 0 / 13

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/exit-risk-catalog-planning` | Wave 0 locks + ADR-0028 Status flip to ACCEPTED with corrections + ROADMAP §13E |
| 1 | `test/strategy-research-golden-run` | T001 — the safety net, alone, before anything moves |
| 2 | `refactor/widen-exit-risk-model-gates` | T002-T003: the validation and engine gates, golden run still green |
| 3 | `refactor/generalize-strategy-run-identity` | T004: the application gate + `exit_model_parameters`, `run_id` proven stable |
| 4 | `feat/bracket-exit-model` | T005: the model, the protocol, the ExitReason members, the consumer audit |
| 5 | `feat/bracket-simulation-kernel` | T006: `kernels/bracket.py` + its hand-computed fixtures |
| 6 | `feat/equity-percent-risk-model` | T007: the risk model + TD-026 |
| 7 | `feat/bracket-exit-end-to-end` | T008: dispatch wired to the real kernel, both models proven |
| 8 | `feat/ema-distance-component` | T009 |
| 9 | `feat/range-expansion-component` | T010 |
| 10 | `feat/bracket-example-strategies` | T011-T012: the three examples + the metric test |
| 11 | `docs/bracket-exits-and-sizing` | T013: guide, module map, TD entries, closure |

PR 1 lands first and **alone**: nothing else in this sprint is safe to merge
before the fixed-bars path has a committed regression. PRs 8 and 9 are
independent of PRs 4-7 and may run in parallel once PR 3 has merged. Each PR
targets `sprint/exit-risk-and-catalog`.

---

## 8. Acceptance criteria

1. A strategy using `BracketExitModel` runs end to end through `trading-cli research run strategy` and produces trades whose `exit_reason` values include more than one of `stop_loss` / `take_profit` / `max_bars`.
2. **Golden run:** the canonical Sprint 013 strategy on the committed fixture produces byte-identical trades and equity DataFrames, an identical `manifest.run_id`, and identical deterministic manifest fields, before and after this sprint (D-S048-07).
3. `kernels/fixed_bars.py`, `research/simulation/compile.py`, `research/simulation/input.py`, and both `ExitModel` / `RiskModel` Protocol definitions are **unchanged** — provable from the diff, not asserted in prose.
4. `apps/cli` is unchanged; the ADR-0026 Amendment 1 allow-list is byte-identical to `main`.
5. Bracket semantics behave exactly as D-S048-04 locks them: stop wins on the same bar (always, no flag), stop/target fill at the trigger price with adverse slippage, timeout fills at the next bar's open, the entry bar is scanned inclusively.
6. `EquityPercentRiskModel` derives its quantity once at construction and satisfies `RiskModel` unchanged; nothing in the codebase or docs describes it as equity-curve-following.
7. The three `isinstance` MVP gates (`strategy_model.py`, `engine.py`, `run_strategy_research.py`) no longer hard-block Exit/Risk models by class, and still reject genuinely unsupported models with a clear message.
8. `derive_strategy_run_id` emits a byte-identical payload for `FixedBarsExitModel`, asserted by a unit test independent of the golden run.
9. `trend.ema_distance` and `volatility.range_expansion` are registered, causal, warmup-correct, reachable from the `model_authoring` DSL, and have a documented, tested zero/NaN-ATR convention.
10. Three example strategies run through the CLI with no loader change; E1 exercises all three exit reasons; E3 exercises `EquityPercentRiskModel` on the unchanged fixed-bars kernel.
11. The D-S048-08 consumer audit is complete — every row has a test or an explicit "no behaviour to test" note; none says "probably fine".
12. TD-026 (static sizing), TD-027 (delay stress rejects brackets), TD-028 (no bracket reference kernel) are logged with named repayment triggers.
13. CI is green for all workspaces: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
14. No new runtime dependency was added.

---

## 9. Dependencies

**Required:** Sprint 047 merged to `main` (#366) — the example strategies compose
`candle.wick` and use the `strategy_file` loader. **Satisfied.**

**Required:** ADR-0028 ACCEPTED (resumed), including the corrected (wider)
non-goal narrowing and the run-identity change. **Satisfied** — approved by
the maintainer on 2026-09-01 (see ADR-0028's Status section). Unlike
Sprint 047, there was **no fallback**: had this been declined, this sprint
would not exist. There is no useful subset of it that does not touch the
engine, which is precisely what Sprint 047 established.

**Required:** the committed OHLCV fixture used by the existing Sprint 013
integration tests, for the golden run and every kernel fixture.

**Not required:** any new dependency, any ML/DL extra, any dashboard change, any
network access, any change to `scripts/` or `apps/`.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| The engine change silently alters existing fixed-bars results | The golden run (T001) is captured **first**, on the unmodified tree, and lands alone in PR 1. No engine PR merges without it green. |
| `derive_strategy_run_id` re-identifies every existing persisted run | The payload for FixedBars must be byte-identical, asserted twice: by `manifest.run_id` in the golden run and by a dedicated payload unit test (T004, criterion 8). |
| Scope creep past ADR-0028's five corrected changes | A sixth engine change is a STOP-and-ask requiring a fresh ADR amendment, locked in D-S048-06 — the ADR-0026 Amendment 1 lesson. |
| The bracket kernel is numerically wrong and nothing catches it | TD-028 is an accepted gap, compensated by hand-computed fixtures whose expected fills are written by hand in the test, never derived from the implementation. |
| Two fill conventions in one trades table confuse the next reader | Deliberate and documented: `exit_reason` distinguishes them per trade, and the guide explains why (T013, criterion 5). |
| `EquityPercentRiskModel` read as dynamic sizing | Locked wording in D-S048-05, enforced in docstring, guide and TD-026; explicitly a review checkpoint, not just an intention. |
| A bracket strategy hits the Robustness delay stress and crashes confusingly | TD-027: it raises with a message naming the model and explaining why the dimension is undefined for it — a decision, not an accident. |
| Catalog scope creep (a third component) | Exactly two, locked in D-S048-10, with the rejected candidates named. |
| Sprint overruns | Descope order pre-agreed: T010, then T009. Waves 1 and 2 are never dropped. |
| A future reader assumes ADR-0028 was simply resurrected unchanged | §4 Findings 2-5 and ADR-0028's "Resumption for Sprint 048" section record exactly what the re-verification changed, and why the approved blast radius is wider than the one declined in September. |

---

## 11. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest

uv run pytest tests/unit/research/simulation -q          # golden run + bracket kernel
uv run --package trading-cli pytest apps/cli/tests -q
uv run pytest tests/unit/test_apps_boundaries.py -q

git diff --stat main -- src/trading_framework/research/simulation/kernels/fixed_bars.py \
                        src/trading_framework/research/simulation/compile.py \
                        src/trading_framework/research/simulation/input.py \
                        src/trading_framework/strategy/exit_model.py::Protocol \
                        apps/cli
```

The last two lines are called out separately because "these files are unchanged"
is an acceptance criterion (§8.3, §8.4), not an incidental property. The
golden-run test is called out because it is the sprint's binding criterion, not
one test among many.

---

## 12. Post-sprint direction

Candidates, none scheduled by default:

- **Bracket-aware Robustness stress dimensions** (stress over `stop_loss_bps` /
  `take_profit_bps`) — the most direct follow-on, and the repayment trigger for
  TD-027. Bracket exits are what made stress dimensions meaningful in the first
  place.
- **Dynamic, equity-curve-following position sizing** (TD-026) — needs a
  `RiskModel` protocol change with paper-broker and live-execution impact; its
  own ADR.
- A reference (non-njit) bracket kernel (TD-028), if a numerical bug appears.
- A validation helper cross-checking `stop_distance` against `stop_loss_bps`
  once a reference price is available to convert between them.
- `momentum.rsi` / `structure.session_position` — the two catalog candidates
  named and rejected in D-S048-10.
- Arithmetic in the model-expression IR, which would make `ema_distance`,
  `range_expansion` and `level_distance` all expressible as DSL composition
  instead of components — the third time this has been deferred, which is itself
  a signal worth weighing.
- Exposing `SimulationAssumptions` and the session resolver through config (the
  remaining third of SPRINT_046.md §4 Finding 2).
- A declarative strategy format, only if the Python loader proves limiting.
