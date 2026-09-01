# Sprint 048 — Wave 0 Decisions

Binding decisions for Exit/Risk Model Expansion, Catalog Growth and New
Strategies (Phase 13). Date: 2026-09-01.

```text
Status: APPROVED — Wave 0 Checklist (D-S048-14) signed off by the maintainer
        on 2026-09-01.
Basis:  docs/product/PRD-exit-risk-and-catalog-expansion.md (confirmed)
        docs/adr/ADR-0028 (ACCEPTED — declined for S047, resumed with
            corrections for S048; Status flipped in place, decline history
            preserved in the ADR's own "History" note)
        docs/adr/ADR-0027 (ACCEPTED) — the loader, reused unchanged
        docs/adr/ADR-0016 (ACCEPTED) — the MVP gates this widens
        docs/planning/sprints/SPRINT_048.md
        src/trading_framework/ as it stands post-Sprint-047 (PR #366 merged to main)
```

This is **one sprint with dependent waves**, not two tracks — same reasoning
Sprint 047 used for itself. The engine, the two models, the catalog and the
example strategies are gated on each other for a working demonstration: an
Exit model the engine refuses is dead code, and a strategy with nothing new to
compose proves nothing.

---

## Inherited locks (do not reopen)

```text
ADR-0022: apps/* are deployable consumers; scripts/ stay thin
ADR-0026 §2 + Amendment 1: apps/cli's import allow-list — NOT widened by this sprint
ADR-0026 §4: one config schema, unknown keys are an error, spec files by path
ADR-0027: the strategy_file loader and build_strategy() convention — NOT changed
ADR-0016: Strategy Model = Market x Signal x Exit x Risk
ADR-0005: Feature/Structure/State is a component KIND; volatility./structure./
          trend./candle. are domain FAMILIES (D-S047-10)
ML/DL extras stay out of default installs and default CI
Standard CI stays network-free
```

---

## D-S048-01 — Problem statement

`BracketExitModel` and `EquityPercentRiskModel` were designed in full (ADR-0028
§1/§3/§4) and dropped from Sprint 047 as a scope decision, not a technical
objection. Three layers of ADR-0016-era `isinstance` gates still refuse any
Exit/Risk model but the two placeholders, and the only kernel reads
`open_prices` alone, so no price-triggered exit is expressible at all. The
component catalog has nine entries and nothing that expresses "how far is price
from its mean" or "is volatility expanding", because the authoring DSL has no
arithmetic.

**This sprint ships exactly:** the five bounded engine changes of ADR-0028's
"Resumption for Sprint 048" section;
`BracketExitModel` + `EquityPercentRiskModel`; one new `@njit` bracket kernel;
two Market Analysis components; three example strategies that exercise both new
models through the existing CLI; and a golden-run regression proving the
fixed-bars path did not move.

**Not this sprint:** dynamic equity-curve-following sizing (TD-026); any change
to the `ExitModel`/`RiskModel` Protocols; any change to `kernels/fixed_bars.py`,
`compile.py` or `input.py`; a declarative YAML strategy format; bracket-aware
Robustness stress dimensions; arithmetic in the model-expression IR; any change
to the Sprint 047 loader.

---

## D-S048-02 — Sprint branch and PR base

```text
Integration branch: sprint/exit-risk-and-catalog     (cut from main)
Working branches:   feat/ | fix/ | docs/ | test/  + descriptive slug
PR base:            sprint/exit-risk-and-catalog     (never main until integration)
```

Working-branch PRs squash-merge into the sprint branch; one integration PR
`sprint/exit-risk-and-catalog` -> `main` at the end. Branch names describe the
change, never the task ID.

**Precondition:** Sprint 047's integration PR (#366) is merged to `main`. This
sprint edits `src/trading_framework/research/simulation/`,
`src/trading_framework/strategy/` and
`src/trading_framework/application/strategy_research/`, none of which Sprint 047
touched — but the new example strategies build on Sprint 047's components and
loader, so the branch is cut from `main` after #366.

---

## D-S048-03 — Re-verification result: what changed since ADR-0028 (BINDING)

`ADR-0028`'s "Resumption for Sprint 048" section holds the evidence. Summary,
binding on the task breakdown:

```text
STILL ACCURATE   ADR-0028 Blockers 1-4, verbatim, line for line.
                 ADR-0028 §3 bracket semantics and §4 equity-percent sizing.
                 No drift in exit_model.py, risk_model.py, strategy_model.py,
                 engine.py or kernels/fixed_bars.py since ADR-0028 was written.

INCOMPLETE       ADR-0028 §2's four-change list. Corrected to FIVE changes
                 across THREE files plus one new file (ADR-0028's Resumption
                 section).

  + a third pair of identical isinstance gates in
    application/strategy_research/run_strategy_research.py:106-107, 269-282
    — the layer the CLI actually calls. Without it, PRD metric 1 is unreachable.
  + derive_strategy_run_id (research/datasets/strategy_research.py:107-142)
    takes exit_after_bars: int and hashes it into run identity. A bracket has
    no such field. Highest-risk item in the sprint; ADR-0028 never mentions it.
  + materialize_kernel_trades takes ONE scalar exit_reason; a bracket run emits
    three different reasons per run.
  + "byte-identical run fingerprint" names a field that does not exist for
    Strategy Research (no run_fingerprint on StrategyResearchRunManifest).
  + the FixedBarsExitModel consumer audit was left open; it is closed in
    ADR-0028 Correction 4, per consumer, with a reason each.

GOOD NEWS        CompiledBarSeries ALREADY carries high/low/close, populated by
                 both compile paths. compile.py and input.py need NO change.
```

---

## D-S048-04 — `BracketExitModel` (adopted from ADR-0028 §3, unchanged)

```text
Fields         stop_loss_bps: float, take_profit_bps: float,
               max_bars: int, exit_model_id: str = "bracket"
Validation     stop_loss_bps > 0; take_profit_bps > 0; max_bars >= 1;
               exit_model_id non-empty (same normalization as FixedBarsExitModel)
Protocols      satisfies ExitModel UNCHANGED — exit_bar_index(entry_fill_bar_index)
               returns entry_fill_bar_index + max_bars, i.e. its WORST-CASE exit
               PLUS a new, additive PriceBracketExit protocol the simulator
               dispatches on
ExitReason     += STOP_LOSS, TAKE_PROFIT, MAX_BARS      (FIXED_BARS unchanged)
```

Locked semantics — the parts OHLCV genuinely cannot answer, decided
pessimistically because a silent optimistic assumption is how backtests lie:

```text
SAME-BAR AMBIGUITY  if a bar's low reaches the stop AND its high reaches the
                    target, THE STOP WINS. Always. No intrabar path
                    reconstruction, no open-proximity heuristic, NO CONFIG FLAG.
FILL PRICE          a stop or target fills at ITS OWN TRIGGER PRICE, with the
                    existing slippage_bps applied AGAINST the trade (the same
                    direction _apply_exit_slippage already applies).
                    The max_bars timeout keeps the NEXT-BAR-OPEN convention,
                    byte-identical to the FixedBars path.
                    => one strategy can produce exits under two fill conventions.
                    Deliberate; exit_reason distinguishes them per trade.
SCAN WINDOW         from the entry fill bar INCLUSIVE. A gap through the stop on
                    the entry bar is a stop-out at the trigger price, not a
                    skipped trade.
OFFSETS             BASIS POINTS, not price points, so a strategy is portable
                    across instruments and price levels.
```

---

## D-S048-05 — `EquityPercentRiskModel` (adopted from ADR-0028 §4, unchanged)

```text
Fields         account_equity: Decimal, risk_percent: Decimal,
               stop_distance: Decimal, risk_model_id: str = "equity_percent",
               max_positions: int = 1
Derived        quantity = (account_equity * risk_percent) / stop_distance
               computed ONCE in __post_init__, stored, returned by
               position_quantity()
Validation     account_equity > 0; 0 < risk_percent <= 1; stop_distance > 0;
               the derived quantity > 0; max_positions >= 1
Protocols      satisfies RiskModel UNCHANGED and completely
               (position_quantity + allows_new_entry)
```

```text
LOCKED  this is STATIC, AUTHORING-TIME sizing. It is NOT compounding,
        equity-curve-following sizing, and must NEVER be described as such — in
        the docstring, the operator guide, a test name, or a commit message.
LOCKED  v1 does NOT cross-validate stop_distance against BracketExitModel's
        stop_loss_bps. The risk model has no reference price to convert bps to
        price points. The OPERATOR owns that consistency; the guide says so
        plainly, and a validation helper is a follow-on, not a v1 promise.
TD-026  dynamic sizing requires passing simulation state into
        position_quantity() — a RiskModel protocol change also affecting
        execution/runtime/strategy_orders.py and
        execution/broker_sim/paper_broker.py. Separate increment, own ADR.
```

---

## D-S048-06 — Engine changes and their hard boundary (CORRECTED — five, not four)

```text
Requested narrowing, from:
    "no change to BarSequentialSimulator"
to:
    "no change to the FIXED-BARS path's fill, accounting or RUN-IDENTITY
     semantics; dispatch to an additional kernel is allowed"
```

Five bounded changes, nothing more:

```text
1  strategy/strategy_model.py — validate_strategy_model_definition: the two
   isinstance MVP guards become a supported-combination / structural check
2  research/simulation/engine.py — _require_fixed_quantity_risk becomes a
   structural RiskModel check (position_quantity() is all the engine calls)
3  research/simulation/engine.py — _require_fixed_bars_exit becomes a dispatch:
   FixedBarsExitModel -> existing kernel; PriceBracketExit -> new kernel;
   anything else -> the same clear SimulationEngineError as today.
   Applied at BOTH call sites (simulate + simulate_from_columnar).
4  application/strategy_research/run_strategy_research.py — the SAME two gates
   at lines 106-107 / 269-282 become the same dispatch/structural checks, and
   manifest + run-id construction stop reading exit_model.exit_after_bars
   directly.  [NEW — ADR-0028 Correction 1]
5  research/simulation/kernels/bracket.py — NEW FILE: an @njit kernel over
   open/high/low, PLUS its own result dataclass and its own materialize_*
   functions emitting a PER-TRADE exit reason.  [materializer split is
   ADR-0028 Correction 3]
```

Run-identity generalization (ADR-0028's Resumption section, Correction 2), binding:

```text
derive_strategy_run_id's `exit_after_bars: int` becomes
`exit_model_parameters: str`.

LOCKED  FixedBarsExitModel MUST produce exactly str(exit_after_bars), so the
        joined payload string — and therefore EVERY EXISTING run_id — is
        byte-identical. This is asserted by the golden run (D-S048-07), not
        assumed.
LOCKED  BracketExitModel produces a deterministic, documented encoding of
        (stop_loss_bps, take_profit_bps, max_bars). Two different exit models
        must never be able to collide on one run identity.
```

Hard boundaries:

```text
LOCKED  kernels/fixed_bars.py is NOT edited — not one character.
LOCKED  research/simulation/compile.py and input.py are NOT edited.
LOCKED  ExitModel and RiskModel Protocol definitions are NOT modified.
LOCKED  apps/cli is NOT modified. The Sprint 047 loader already returns any
        StrategyModelDefinition; nothing in the loader knows about exit models.
LOCKED  if implementation reveals a SIXTH engine change is needed, that is a
        STOP-and-ask — a new ADR amendment with fresh maintainer approval,
        never a quiet widening. This is the exact lesson ADR-0026 Amendment 1
        exists to record.
```

---

## D-S048-07 — What "the golden run" concretely means (ADR-0028 Correction 5)

`StrategyResearchRunManifest` has no `run_fingerprint` field — ADR-0028 and the
PRD both named one. The criterion is therefore defined explicitly:

```text
The canonical Sprint 013 strategy (build_canonical_strategy_model()), on the
committed OHLCV fixture, through run_strategy_research, produces before and
after this sprint:

  IDENTICAL  the trades DataFrame — every column, every row, exact values
  IDENTICAL  the equity DataFrame — every column, every row, exact values
  IDENTICAL  manifest.run_id                    <- enforces D-S048-06's payload lock
  IDENTICAL  manifest.exit_model_id, risk_model_id, strategy_model_id,
             market_model_id, signal_model_id, evaluation_timeframe,
             source_dataset_ref, schema_version,
             simulation_assumptions_fingerprint

  EXCLUDED (legitimately nondeterministic): created_at_utc, framework_version,
             and any storage path derived from them.

LOCKED  the expected values are CAPTURED FIRST, on the pre-change tree, and
        committed as a fixture. Capturing them after the engine change would
        make the test tautological.
LOCKED  if any of the above drifts, THE CHANGE IS WRONG, not the golden run.
        Adjusting the fixture to match new output is forbidden without a
        maintainer decision recorded in this file.
```

---

## D-S048-08 — `FixedBarsExitModel` / `ExitReason` consumer audit — CLOSED

Each consumer, with a reason. "Probably fine" is not an audit.

| Consumer | Disposition |
|---|---|
| `research/robustness/stress.py:250-257` (delay stress) | **Keeps rejecting** non-FixedBars exits, with an error naming `BracketExitModel` and stating why (a bracket's exit is price-driven; "delay by N bars" is undefined for it). Logged as debt with a repayment trigger. See D-S048-09. |
| `research/simulation/kernels/reference.py:42,70,145` | **No bracket counterpart in v1.** See D-S048-09. |
| `research/robustness/strategy_template.py:82-83` | Safe — constructs FixedBars/FixedQuantity itself; unaffected. |
| `execution/runtime/live_signals.py:73` | Safe — docstring mention, no gate, no behaviour. |
| `research/analytics/strategy_dashboard.py:41,212,373` and `strategy_dashboard_report.py:389` | Safe — reads `exit_reason` as an opaque `str`, no exhaustive match; new members render as their string values. |
| `research/simulation/facts.py:66,120` | Safe — persists `exit_reason.value` into a `pl.String` column; adding `StrEnum` members is additive for existing records. |
| `strategy/canonical_examples.py`, `strategy/btc_futures_demo.py` | Safe — construct FixedBars/FixedQuantity explicitly; unchanged, and covered by the golden run. |

```text
LOCKED  this table is the audit. A task may ADD a row it discovers; it may not
        downgrade a row to "probably fine".
```

---

## D-S048-09 — Two knowingly accepted gaps (technical debt, logged with triggers)

```text
TD-027  The Robustness DELAY stress dimension rejects bracket exits.
        Why accepted: "delay a price-triggered exit by N bars" has no obviously
        correct meaning; inventing one inside an engine sprint would be an
        unreviewed research-semantics decision.
        Repayment trigger: the first request to stress a bracket strategy, or
        the bracket-parameter stress dimensions named as a follow-on.

TD-028  kernels/bracket.py has NO independent reference implementation, unlike
        kernels/fixed_bars.py (which is cross-checked against kernels/reference.py).
        Why accepted: a second reference doubles the surface that must stay
        numerically consistent, for a path with no legacy behaviour to protect.
        Compensating control: hand-computed fixtures (D-S048-10) whose expected
        fill prices are written out by hand in the test, never derived from the
        implementation.
        Repayment trigger: the first bracket-path numerical bug, or the first
        change to bracket fill semantics.
```

Both are MEDIUM. Neither is a substitute for the golden run, which protects the
*fixed-bars* path and is not optional.

---

## D-S048-10 — Component catalog additions (exactly two)

Chosen by the same discipline as D-S047-10, and by the **same structural
argument** that justified `structure.level_distance`: the authoring DSL's
`Operand` implements comparisons only (`__eq__`, `__ne__`, `__gt__`, `__ge__`,
`__lt__`, `__le__`) and has no `__sub__` / `__truediv__` (SPRINT_047.md §4
Finding 3). Anything requiring a ratio or a difference **must** be a component.
Both additions below are unexpressible in the DSL today; neither is added
because it is a popular indicator.

**C1 — `trend.ema_distance`** (existing `trend` family; `ComponentKind.FEATURE`)

```text
Component id   trend.ema_distance            version 1.0.0
Outputs        distance_atr                  (float64) — signed
               (close - ema(period)) / atr(atr_period)
Parameters     period (int, default 20, min 1)      — the EMA period
               atr_period (int, default 14, min 1)  — the ATR period
Dependencies   trend.ema(period), volatility.atr(atr_period)
History        inherits max(EMA, ATR) warmup; valid_from_index respects it
Zero/NaN ATR   behaviour is DEFINED and documented (not a surprise NaN); the
               exact convention is the implementer's call, stated in the
               docstring and asserted by a test — same bar as D-S047-10's
               zero-range rule
DSL            trend.ema_distance(period=20, atr_period=14, timeframe=None)
```

Why: the catalog can say "close above the EMA" but not "close is 1.5 ATR below
the EMA". Scale-free stretch-from-mean is the natural entry condition for a
strategy whose exit is a bracket, and it is the direct structural sibling of
`structure.level_distance` (same component-depends-on-two-components shape).

**C2 — `volatility.range_expansion`** (existing `volatility` family; FEATURE)

```text
Component id   volatility.range_expansion    version 1.0.0
Outputs        ratio                         (float64) — dimensionless
               true_range(bar) / atr(period)
Parameters     period (int, default 14, min 1)
Dependencies   volatility.true_range, volatility.atr(period)
History        inherits the ATR warmup
Zero/NaN ATR   defined and documented, as C1
DSL            volatility.range_expansion(period=14, timeframe=None)
```

Why: `volatility.state` is a coarse HIGH/NOT-HIGH classification with a fixed
threshold; there is no continuous, scale-free "is this bar's range unusual"
operand, and `true_range() / atr()` cannot be written in the DSL. It is also
the honest companion to a **basis-point** bracket: bps offsets are
volatility-agnostic, so an operator needs a way to filter for the regimes where
a fixed-bps stop is sane.

```text
LOCKED  EXACTLY TWO components. A third is a separate increment, however cheap
        it looks mid-sprint — the same lock as D-S047-10.
LOCKED  no arithmetic in the model-expression IR is opened by this sprint
        (SPRINT_047.md §4 Finding 3 stays open, deliberately).
LOCKED  no new component FAMILY. Both land in existing namespaces.
```

**Explicitly rejected candidates**, so the choice is visible as a choice:

- `momentum.rsi` — expressible-adjacent and popular, but its only justification
  is "everyone has one". It is a bounded oscillator the catalog lacks; that is
  a real gap, but not one this sprint's strategies need. Deferred by name.
- `structure.session_position` (close's position within the running session
  range, 0..1) — overlaps `structure.level_distance` too heavily to justify now.
- Any Bollinger/Keltner-style band — C1 covers the same idea with fewer outputs
  and no second parameterization of "what is a band".

---

## D-S048-11 — Example strategies (exactly three)

Under `user_data/components/strategies/` — gitignored per ADR-0002, therefore
**reproduced verbatim in `docs/reference/STRATEGY_AUTHORING.md`**, exactly as
Sprint 047 did for its two. Each is loaded through the existing `strategy_file`
CLI mechanism with **no change to the loader**, and ships with a committed
example config under the Sprint 046 examples location.

| # | File | Composes (new) | Exit | Risk | What it proves |
|---|---|---|---|---|---|
| E1 | `ema_reversion_bracket.py` | `trend.ema_distance` (C1) | `BracketExitModel` | `FixedQuantityRiskModel` | `BracketExitModel` in isolation, on the **new** kernel — stop, target and timeout exits all reachable |
| E2 | `range_expansion_breakout.py` | `volatility.range_expansion` (C2) + `structure.session_high` | `BracketExitModel` | `EquityPercentRiskModel` | both new models together, end to end through the CLI (PRD success metric 1) |
| E3 | `quiet_wick_rejection.py` | `volatility.range_expansion` (C2) + `candle.lower_wick_ratio` (S047) | `FixedBarsExitModel` | `EquityPercentRiskModel` | **the isolation case:** the new Risk model on the UNCHANGED fixed-bars kernel — proving the risk-model widening is orthogonal to the bracket kernel |

```text
LOCKED  E3 exists specifically to prove the risk-model change is independent of
        the exit-model change. It is not a filler example and is NOT a descope
        target ahead of E1/E2.
LOCKED  each example is copy-pasteable and commented in the style of the five
        files already in user_data/components/strategies/.
LOCKED  no edit to trading_cli/strategy_loader.py, config.py or research.py.
        If the examples reveal a loader limitation, that is a finding to record,
        not a change to make in this sprint.
LOCKED  E1's parameters must be chosen so the committed fixture actually
        produces at least one STOP_LOSS, one TAKE_PROFIT and one MAX_BARS trade
        — a bracket example that only ever times out proves nothing.
```

---

## D-S048-12 — Testing

```text
tests/unit/strategy/
    BracketExitModel field validation, exit_bar_index == entry + max_bars,
    ExitModel + PriceBracketExit protocol conformance
    EquityPercentRiskModel derivation arithmetic, validation, allows_new_entry

tests/unit/research/simulation/
    GOLDEN RUN (D-S048-07) — captured on the pre-change tree, committed as a
        fixture, asserted after. THE binding acceptance criterion.
    bracket kernel against HAND-COMPUTED fixtures:
        stop-only  |  target-only  |  same-bar both (STOP WINS)  |
        gap through the stop on the ENTRY bar  |  timeout (MAX_BARS)  |
        long and short, each  |  slippage applied against the trade, each
    engine dispatch: FixedBars -> old kernel, bracket -> new kernel,
        an unknown ExitModel -> the same SimulationEngineError message as today
    run-id payload: str(exit_after_bars) is emitted byte-identically for
        FixedBars; two exit models cannot collide on one run_id

tests/unit/market_analysis/
    C1/C2 causality, warmup / valid_from_index, zero-or-NaN-ATR convention,
    MTF alignment consistent with their dependencies

tests/unit/application/ + apps/cli/tests/
    end to end: a bracket strategy loaded via strategy_file produces a trades
    table containing MORE THAN ONE distinct exit_reason (PRD success metric 1);
    the assertion is on distinct reasons, not just "a run happened"

No network. No ML/DL extra. Committed fixture data only.
The @njit warm-up cost of a second kernel is accepted; no test may skip the
kernel to save time.
```

---

## D-S048-13 — Sequencing and descope order

```text
Wave 1  golden run captured + engine gates widened (no new models yet)
Wave 2  BracketExitModel + EquityPercentRiskModel + kernels/bracket.py
Wave 3  catalog: C1, C2
Wave 4  example strategies, docs, closure
```

```text
LOCKED DESCOPE ORDER (if the sprint overruns): C2 (and with it E2's C2 filter
       simplifies to a session-high breakout, E3 falls back to candle.wick
       alone), then E3, then C1 with E1.
LOCKED WAVE 1 IS NEVER DROPPED. Without the golden run, no engine change is
       safe to make at all; capturing it is the FIRST commit of the sprint.
LOCKED WAVE 2 IS NEVER DROPPED. It is the sprint's reason to exist. If Wave 2
       cannot land, the sprint is abandoned and reopened, not descoped into a
       catalog-only sprint — that is what Sprint 047 already was.
```

---

## D-S048-14 — Wave 0 Checklist (maintainer)

Nothing below may be checked off by an agent. `engineer` must refuse to start
while any box is unchecked.

- [x] **ADR-0028 resumption approved** (Status flipped PROPOSED-declined -> ACCEPTED, in place) — the maintainer chose a **Status flip on ADR-0028 itself** over the architect's proposed new superseding ADR-0029; ADR-0029's content was merged into ADR-0028's new "Resumption for Sprint 048" section, ADR-0029 was deleted, and ADR-0028's original decline record is preserved verbatim under "History" within the Status section.
- [x] **The corrected non-goal narrowing accepted (D-S048-06):** from "no change to `BarSequentialSimulator`" to "no change to the fixed-bars path's fill, **accounting or run-identity** semantics; dispatch to an additional kernel is allowed" — explicitly acknowledging this is **five changes across three files plus a new kernel**, a wider blast radius than the four-change version declined on 2026-09-01.
- [x] **The run-identity change accepted (D-S048-06):** `derive_strategy_run_id`'s `exit_after_bars: int` becomes `exit_model_parameters: str`, with fixed-bars runs emitting a byte-identical payload so no existing `run_id` moves. This touches persisted-run identity and is the sprint's highest-risk item.
- [x] **The golden-run definition accepted (D-S048-07)**, including that expected values are captured on the **pre-change** tree first, and that adjusting the fixture to match new output is forbidden without a recorded maintainer decision.
- [x] **D-S048-04 / D-S048-05 confirmed:** the locked pessimistic bracket semantics (stop wins on the same bar, always, no flag; trigger-price fills with adverse slippage; entry bar inclusive) and that `EquityPercentRiskModel` is **static, authoring-time** sizing that must never be described as equity-curve-following.
- [x] **D-S048-09 accepted:** TD-027 (delay stress rejects bracket exits — a capability the operator loses) and TD-028 (the bracket kernel has no independent reference implementation) are knowingly accepted MEDIUM debt with the stated triggers, not oversights.
- [x] **D-S048-10 confirmed:** exactly two components, `trend.ema_distance` and `volatility.range_expansion`; `momentum.rsi` and `structure.session_position` explicitly rejected for now; no arithmetic in the expression IR.
- [x] **D-S048-11 confirmed:** exactly three example strategies with the stated Exit/Risk pairings, including E3 as the deliberate risk-model isolation case; no change to the Sprint 047 loader.
- [x] **Sprint 048 scope approved as 13 tasks, 4 waves**, with the D-S048-13 descope order and the "Waves 1 and 2 are never dropped" rule.
- [x] **Branch `sprint/exit-risk-and-catalog` approved**, cut from `main` after #366.
- [x] **ROADMAP Phase 13 (§13E) approved** — applied in this same planning PR, matching the #349 / Sprint 047 precedent; its `Status:` line is `PROPOSED` until this box is checked.

Approved-by: Filip Folga (project maintainer), 2026-09-01, via a structured
four-question approval in conversation with the orchestrating Claude Code
session. Verbatim choices: (1) on ADR-0029 vs. a Status flip on ADR-0028 —
"Nie, wolę flip statusu ADR-0028" (No, I prefer to flip ADR-0028's status);
(2) on the corrected five-change engine scope + run-identity change — "Tak,
akceptuję 5 zmian + run-identity" (Yes, I accept 5 changes + run-identity);
(3) on the catalog/example-strategy set — "Tak, zestaw zaakceptowany" (Yes,
the set is accepted); (4) on sprint structure, branch, ROADMAP §13E and
TD-027/TD-028 — "Tak, wszystko zatwierdzone" (Yes, everything approved). Per
choice (1), ADR-0029 was deleted and its content merged into ADR-0028's own
"Resumption for Sprint 048" section rather than kept as a separate document.

Once every box is checked, the first task for `engineer` is **S048-T001**
(capture the golden run on the unmodified tree) on
`test/strategy-research-golden-run`, cut from `sprint/exit-risk-and-catalog`.
