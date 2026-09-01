# ADR-0028 — Bracket Exits and Equity-Relative Sizing: Widening the Strategy Model Gate

## Status

PROPOSED — declined for Sprint 047 (2026-09-01)

Declined-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-01, in response to a
summary of this ADR's request to narrow the PRD non-goal on
`BarSequentialSimulator` (§2: four bounded engine changes + a new kernel,
guarded by a golden-run regression). The maintainer chose to leave the engine
untouched for Sprint 047 rather than approve the narrowing.

Per this ADR's own pre-agreed fallback (§2, and `SPRINT_047.md` §4 Finding
1): Wave 2 (`BracketExitModel`, `EquityPercentRiskModel`, the engine dispatch
changes, `kernels/bracket.py`) is **dropped from Sprint 047**. Sprint 047
ships Waves 1/3/4 only (the `strategy_file` loader and the two new
components). This ADR's domain design (§3 bracket semantics, §4 equity-percent
sizing) remains a candidate starting point if a future sprint reopens this
question with its own engine-focused ADR — nothing here is discarded, it is
deferred. Status stays `PROPOSED` rather than a rejected/closed state: this
records a decision not to build it *now*, not a permanent architectural
verdict.

## Context

`docs/product/PRD-strategy-authoring.md` asks to "expand Exit/Risk models
beyond the two placeholders — realistic variants (candidates:
stop-loss/take-profit exit, equity-percentage risk sizing), **implementing the
existing `ExitModel`/`RiskModel` protocols unchanged**", and separately lists
as a non-goal: "any change to the simulation/backtesting engine
(`BarSequentialSimulator`) itself."

Reading the code before designing anything shows those two sentences cannot
both hold. Four hard blockers:

### Blocker 1 — the `ExitModel` protocol cannot express a price-based exit

```python
# src/trading_framework/strategy/exit_model.py
def exit_bar_index(self, *, entry_fill_bar_index: int) -> int: ...
```

The entire contract is a pure function of one integer. It sees no price, no
bar, no direction. A stop-loss is by definition a function of the price path.
**No implementation of this protocol, however clever, can be a stop-loss.**
"Implementing the existing protocol unchanged" and "stop-loss/take-profit" are
mutually exclusive, and the only exit variants that *are* expressible
(`entry + k`) are the one that already exists.

### Blocker 2 — the simulator hard-gates on the concrete classes

```python
# research/simulation/engine.py
def _require_fixed_bars_exit(...):    if not isinstance(exit_model, FixedBarsExitModel): raise
def _require_fixed_quantity_risk(...): if not isinstance(risk_model, FixedQuantityRiskModel): raise
```

Both `simulate()` and `simulate_from_columnar()` reject anything else, by
class, not by protocol. So even a *protocol-conformant* new model — one that
needs no engine semantics at all — is refused before it reaches the kernel.

### Blocker 3 — `validate_strategy_model_definition` repeats the same gate

```python
# strategy/strategy_model.py
if not isinstance(definition.exit_model, FixedBarsExitModel):     "MVP supports FixedBarsExitModel only"
if not isinstance(definition.risk_model, FixedQuantityRiskModel): "MVP supports FixedQuantityRiskModel only"
```

An ADR-0016-era MVP guard. Any new model fails here too, one layer earlier.

### Blocker 4 — the kernel is bar-index-only by construction

`kernels/fixed_bars.py::simulate_fixed_bars_exit_kernel` is an `@njit` loop
over `open_prices` alone, computing `exit_signal_bar_index = entry_fill +
exit_after_bars`. It never reads `high` or `low`, which is exactly what a stop
or a target requires.

### Consequence

A new Exit or Risk model added without touching the engine would be dead code:
constructible, never runnable, and unable to satisfy PRD success metric 2 ("at
least one new Exit or Risk model is exercised by a real, passing example
composed through the new loader") or PRD goal 4 ("prove the three pieces
actually work together"). The non-goal, read literally, forbids delivering the
goal.

## Decision

### 1. What gets added (domain)

```text
BracketExitModel        stop-loss + take-profit as price offsets from the entry
                        fill, plus a mandatory max_bars timeout so every trade
                        terminates. Fields: stop_loss_bps, take_profit_bps,
                        max_bars, exit_model_id = "bracket".
ExitReason              += STOP_LOSS, TAKE_PROFIT, MAX_BARS  (FIXED_BARS kept)
EquityPercentRiskModel  quantity resolved once, at construction, from
                        account_equity x risk_percent / stop_distance.
                        risk_model_id = "equity_percent".
```

`ExitModel` and `RiskModel` **Protocols are not modified.** `BracketExitModel`
still satisfies `ExitModel` (`exit_bar_index` returns the `max_bars` timeout
bar — its worst-case exit) and additionally satisfies a new, additive
`PriceBracketExit` protocol the simulator dispatches on. Existing consumers
that only know `ExitModel` keep working against it.

`EquityPercentRiskModel` satisfies `RiskModel` **unchanged and completely** —
see §4 for what that costs.

### 2. What gets changed in the engine, and the non-goal this narrows

This is the decision that needs the maintainer's explicit answer.

```text
Requested narrowing of the PRD non-goal, from:
    "no change to BarSequentialSimulator"
to:
    "no change to the FIXED-BARS path's fill or accounting semantics;
     dispatch to an additional kernel is allowed."
```

Concretely, four bounded changes:

| # | Change | Blast radius |
|---|---|---|
| 1 | `validate_strategy_model_definition`: the two `isinstance` MVP guards become a supported-combination check (any `ExitModel` the engine can dispatch x any `RiskModel`) | `strategy/strategy_model.py`, ~10 lines |
| 2 | `engine.py`: `_require_fixed_quantity_risk` becomes a structural `RiskModel` check (`position_quantity()` is all the engine calls) | 2 call sites |
| 3 | `engine.py`: `_require_fixed_bars_exit` becomes a dispatch — `FixedBarsExitModel` -> existing kernel, `PriceBracketExit` -> new kernel, anything else -> the same clear `SimulationEngineError` as today | 2 call sites |
| 4 | new `research/simulation/kernels/bracket.py`, an `@njit` kernel alongside `fixed_bars.py`, which is **not edited** | new file |

The existing kernel file is not touched. The binding acceptance criterion is a
**golden-run regression**: the canonical strategy on the committed fixture
produces a byte-identical run fingerprint, trades table and equity table before
and after this sprint. If it does not, the change is wrong, not the golden run.

**If the maintainer declines this narrowing**, the fallback is stated in
`SPRINT_047.md` §4 and is not a disaster: drop Wave 2 entirely, ship the loader
+ catalog (PRD success metric 1 and part of 2 via a new *component*), and open
the Exit/Risk expansion as its own sprint with an engine-focused ADR. That is
a legitimate choice; it just needs to be a choice, not a discovery mid-sprint.

### 3. Bracket exit semantics — the parts OHLCV cannot answer

A bracket exit on OHLCV bars has two genuinely ambiguous cases. Both are
decided pessimistically and documented in the operator guide, because a silent
optimistic assumption here is how backtests lie.

**Same-bar ambiguity.** If a bar's `low` reaches the stop *and* its `high`
reaches the target, the bar's OHLC cannot say which came first.

```text
LOCKED: the stop-loss wins. Always. No intrabar path reconstruction,
        no open-proximity heuristic, no configuration flag.
```

**Fill price.** The existing fixed-bars path fills at the **next bar's open**
with slippage. A bracket that filled at the next open would not be a bracket —
it would be "exit when the level was breached, at whatever price came next",
which under-reports stop losses in fast markets.

```text
LOCKED: a stop or target fills at its own trigger price, with the existing
        slippage_bps applied AGAINST the trade (as _apply_exit_slippage does).
        The max_bars timeout exit keeps the next-bar-open convention, identical
        to FixedBarsExitModel.
```

So one strategy can produce exits under two fill conventions. That is
deliberate and must appear in the trade record: `exit_reason` already
distinguishes them (`STOP_LOSS` / `TAKE_PROFIT` / `MAX_BARS`).

**Trigger scan window.** Bars are scanned from the entry fill bar *inclusive*.
A gap through the stop on the entry bar itself is a stop-out at the trigger
price, not a skipped trade.

**Offsets are in basis points**, not price points, so a strategy is portable
across instruments and price levels. `max_bars` is mandatory (>= 1) so no
position can be held to the end of the dataset.

### 4. Equity-percent sizing — an honest, limited version

`RiskModel.position_quantity()` takes no arguments and returns a `Decimal`.
It has no access to running equity, entry price, or the trade being sized. So
"equity-percentage sizing" can only mean **sizing resolved once, at authoring
time**, from values the author supplies:

```text
quantity = (account_equity * risk_percent) / stop_distance     [computed in __post_init__]
```

This is a real improvement over hand-computing a lot size — the author writes
"risk 1% of 100k on a 50-point stop" instead of "quantity = 20" — but it is
**not** compounding, equity-curve-following position sizing, and calling it
that would be dishonest. The limitation goes in the class docstring, the
operator guide, and `TECHNICAL_DEBT.md` as **TD-026**, with the repayment
trigger named: dynamic sizing requires passing simulation state into
`position_quantity()`, which is a `RiskModel` protocol change affecting the
paper broker and live execution runtime (`execution/runtime/strategy_orders.py`,
`execution/broker_sim/paper_broker.py`) — a separate increment with its own ADR.

Consistency guard: `EquityPercentRiskModel.stop_distance` and
`BracketExitModel.stop_loss_bps` describe the same stop from two directions and
can silently disagree. v1 does **not** cross-validate them (the risk model has
no reference price to convert bps to points). The guide states the operator owns
that consistency; a validation helper is a follow-on, not a v1 promise.

## Consequences

### Positive

- PRD success metric 2 becomes achievable: a new Exit *and* a new Risk model
  are exercised end-to-end through the loader on real bars.
- The two ADR-0016-era `isinstance` MVP guards — which were always labelled
  "MVP" — stop blocking every future exit/risk model, not just this one.
- Bracket exits make the Robustness Research stress dimensions (Sprint 016)
  meaningful for the first time: a fixed-bars-only strategy has no stop to
  stress.
- Pessimistic same-bar and trigger-fill rules mean the new path cannot flatter
  a strategy relative to the existing one.

### Negative

- **It narrows a PRD non-goal.** Four files in the simulation engine change,
  including two gate functions and a new kernel. The golden-run regression
  bounds the risk; it does not eliminate it.
- Two fill conventions inside one strategy (trigger-price for bracket exits,
  next-bar-open for the timeout) is a real cognitive cost for whoever reads a
  trades table next.
- A second `@njit` kernel is a second thing to keep numerically consistent with
  the reference implementation (`kernels/reference.py`) and a second JIT warm-up
  cost in tests.
- `EquityPercentRiskModel` invites a misreading as dynamic sizing. Mitigated
  only by documentation and TD-026.
- `PriceBracketExit` as a second protocol means "what is an exit model" now has
  two answers; consumers outside the simulator (robustness templates, live
  order construction) must be audited for assumptions about `FixedBarsExitModel`.

### Neutral

- `ExitReason` is a `StrEnum`; adding members is additive for persisted trade
  records, but any consumer exhaustively matching on `FIXED_BARS` needs the
  new members handled. The audit is an explicit sprint task, not an assumption.
- Nothing here touches Predictive, Signal or Robustness Research *definitions*
  — only what a strategy may compose.

## Alternatives Considered

1. **Add the models, do not touch the engine.** Rejected: they would be
   unrunnable dead code, failing PRD goal 4 and success metric 2. It honours
   the non-goal's letter and defeats its purpose.
2. **Change the `ExitModel` protocol to take prices.** Rejected: it breaks
   every existing implementation and consumer, including the live execution
   path, for a benefit an additive second protocol delivers without the churn.
3. **Extend `FixedBarsExitModel` with optional stop/target fields.** Rejected:
   a model named "fixed bars" that sometimes is not is worse than a new class,
   and it would silently change the meaning of every persisted
   `exit_model_id: "fixed_bars"`.
4. **Modify the existing `fixed_bars` kernel to handle brackets conditionally.**
   Rejected: it puts the golden-run regression at risk on every future bracket
   change and adds branches to a hot `@njit` loop that 100% of existing runs
   pay for.
5. **Optimistic or configurable same-bar resolution.** Rejected: a flag here is
   a flag for "how flattering should this backtest be". Pessimistic, fixed, and
   documented.
6. **Stop/target offsets in price points instead of basis points.** Rejected:
   not portable across instruments; an author would have to re-tune every
   strategy per symbol.
7. **True equity-relative sizing now** (pass simulation state into
   `position_quantity()`). Rejected for this sprint: it changes a protocol the
   live execution path also implements. Logged as TD-026 with its trigger.
8. **Split Exit/Risk into its own sprint.** Not rejected — it is the documented
   fallback if the maintainer declines §2 (see `SPRINT_047.md` §4).

## Follow-up

- `S047_WAVE0_DECISIONS.md` D-S047-07/08 bind the exact field sets and the
  audit list for `ExitReason` consumers.
- TD-026: static equity-percent sizing; repayment requires a `RiskModel`
  protocol change with execution-path impact.
- Robustness Research stress dimensions over `stop_loss_bps` / `take_profit_bps`
  are an obvious follow-on and are explicitly **not** in Sprint 047.

## Related

- `docs/product/PRD-strategy-authoring.md` (confirmed)
- `docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md` (the MVP gates this widens)
- `docs/adr/ADR-0027-operator-authored-strategy-loading.md`
- `docs/planning/sprints/SPRINT_047.md` §4, `S047_WAVE0_DECISIONS.md`
- `docs/planning/TECHNICAL_DEBT.md` TD-026
</content>
</invoke>
