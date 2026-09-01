# ADR-0028 — Bracket Exits and Equity-Relative Sizing: Widening the Strategy Model Gate

## Status

ACCEPTED — resumed for Sprint 048 (2026-09-01), with the corrections in
"Resumption for Sprint 048" below. §2's original four-change list is
superseded by the corrected five-change list in that section; §1/§3/§4 (the
domain design) are adopted unchanged.

History (preserved, not overwritten):

Declined-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-01, in response to a
summary of this ADR's request to narrow the PRD non-goal on
`BarSequentialSimulator` (§2: four bounded engine changes + a new kernel,
guarded by a golden-run regression). The maintainer chose to leave the engine
untouched for Sprint 047 rather than approve the narrowing.

Per this ADR's own pre-agreed fallback (§2, and `SPRINT_047.md` §4 Finding
1): Wave 2 (`BracketExitModel`, `EquityPercentRiskModel`, the engine dispatch
changes, `kernels/bracket.py`) was **dropped from Sprint 047**. Sprint 047
shipped Waves 1/3/4 only (the `strategy_file` loader and the two new
components). This ADR's domain design (§3 bracket semantics, §4 equity-percent
sizing) was kept as a candidate starting point for a future sprint — nothing
was discarded, it was deferred.

Accepted-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-01, via a structured
approval covering four points: (1) resuming this ADR by flipping its own
Status rather than writing a separate superseding ADR — the maintainer chose
"flip status of ADR-0028" over the architect's proposed new-ADR approach; (2)
the corrected, wider engine-change scope (five changes across three files
plus a new kernel, versus the four originally declined) together with the
`derive_strategy_run_id` run-identity generalization; (3) the two new catalog
components (`trend.ema_distance`, `volatility.range_expansion`) and the three
example strategies (E1/E2/E3) as the architect proposed them; (4) the overall
Sprint 048 branch/PR structure, TD-027 and TD-028 as accepted technical debt,
and the ROADMAP §13E addition. All four given as explicit answers to a
structured approval question, not inferred.

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

## Resumption for Sprint 048 (corrections)

Before resuming this ADR, the code was re-read against the tree as it stands
after Sprint 047 (PR #366 merged to `main`), per the PRD's own riskiest
assumption. Result: **§1/§3/§4's domain design and Blockers 1-4 hold,
verbatim; §2's four-change engine list is incomplete.**

### Re-verification: what still holds

| Blocker / claim | Current location | Verdict |
|---|---|---|
| Blocker 1 — `ExitModel.exit_bar_index(*, entry_fill_bar_index: int) -> int`, no price | `strategy/exit_model.py:27` | unchanged |
| Blocker 2 — engine gates on concrete classes, both call sites | `research/simulation/engine.py:168-181` | unchanged |
| Blocker 3 — `validate_strategy_model_definition` repeats the gate | `strategy/strategy_model.py:39-44` | unchanged |
| Blocker 4 — the kernel is `open_prices`-only | `kernels/fixed_bars.py:197-302` | unchanged |
| `ExitReason` has only `FIXED_BARS`; `RiskModel.position_quantity()` takes no arguments | `strategy/exit_model.py`, `strategy/risk_model.py` | unchanged |

§3 (bracket semantics) and §4 (equity-percent sizing) are adopted **verbatim**.
One piece of good news: `CompiledBarSeries` already carries `high_prices`,
`low_prices` and `close_prices` on both compile paths
(`research/simulation/compile.py:84-156`) — no change to `compile.py` or
`input.py` is needed.

### Five corrections to §2's change list

**Correction 1 — a third pair of identical gates, one layer above the
engine.** `application/strategy_research/run_strategy_research.py:106-107,
269-282` repeats the same `isinstance` checks and raises
`StrategyResearchError`. §2 named only `strategy/strategy_model.py` and
`research/simulation/engine.py`; but `trading-cli research run strategy`
calls `run_strategy_research`, so without this change PRD success metric 1 is
unreachable. **Four changes becomes five, across three files.**

**Correction 2 — run identity bakes in a FixedBars-only field.**
`derive_strategy_run_id` (`research/datasets/strategy_research.py:107-142`)
hashes `str(exit_after_bars)` into the run-id payload.
`BracketExitModel` has no such field. §2 never mentions this; it is the
single highest-risk item in the sprint, because any change to the payload's
composition changes the `run_id` of **existing fixed-bars runs**, which the
golden-run regression exists to forbid. Fix (minimum blast radius): the
parameter generalizes to `exit_model_parameters: str`, and
`FixedBarsExitModel` MUST emit exactly `str(exit_after_bars)` so the hashed
payload — and therefore every existing `run_id` — is byte-identical.
`BracketExitModel` emits a deterministic, documented encoding of
`(stop_loss_bps, take_profit_bps, max_bars)`.

**Correction 3 — trade materialization takes one scalar exit reason.**
`materialize_kernel_trades` (`kernels/fixed_bars.py:127-135`) takes a single
`exit_reason: ExitReason` for the whole run. A bracket run produces
`STOP_LOSS`, `TAKE_PROFIT` and `MAX_BARS` within **one** run, so it needs a
per-trade reason array. Resolution: the new `kernels/bracket.py` carries its
own result dataclass and its own `materialize_*` functions; `fixed_bars.py`
stays byte-identical — not edited to accommodate this.

**Correction 4 — the `FixedBarsExitModel`/`ExitReason` consumer audit, left
open in §2, is closed:**

| Consumer | Disposition |
|---|---|
| `research/robustness/stress.py:250-257` (delay stress) | Keeps rejecting non-FixedBars exits, with an error naming `BracketExitModel` and stating why (a bracket's exit is price-driven; "delay by N bars" is undefined for it). Logged as **TD-027**. |
| `research/simulation/kernels/reference.py:42,70,145` | No bracket counterpart in v1. Verified instead against hand-computed fixtures. Logged as **TD-028**. |
| `research/robustness/strategy_template.py:82-83` | Safe — constructs FixedBars/FixedQuantity itself. |
| `execution/runtime/live_signals.py:73` | Safe — docstring mention only, no gate. |
| `research/analytics/strategy_dashboard*.py` | Safe — reads `exit_reason` as an opaque `str`. |
| `research/simulation/facts.py:66,120` | Safe — persists `exit_reason.value` into a `pl.String` column; additive. |

**Correction 5 — "byte-identical run fingerprint" names a field that does not
exist for Strategy Research.** `StrategyResearchRunManifest` has `run_id` and
`simulation_assumptions_fingerprint`, no `run_fingerprint`
(`compute_run_fingerprint` is Predictive-Research-only). The golden-run
criterion is redefined concretely: identical trades DataFrame, identical
equity DataFrame, identical `manifest.run_id`, and identical
`exit_model_id` / `risk_model_id` / `strategy_model_id` / `market_model_id` /
`signal_model_id` / `evaluation_timeframe` / `source_dataset_ref` /
`schema_version` / `simulation_assumptions_fingerprint` — excluding the
legitimately nondeterministic `created_at_utc`, `framework_version`, and any
path derived from them. If any of the above drifts, **the change is wrong,
not the golden run.**

### §2's change list, corrected — five changes, three files, one new file

| # | Change | File | Blast radius |
|---|---|---|---|
| 1 | The two `isinstance` MVP guards become a supported-combination check | `strategy/strategy_model.py` | ~10 lines |
| 2 | `_require_fixed_quantity_risk` -> structural `RiskModel` check | `research/simulation/engine.py` | 2 call sites |
| 3 | `_require_fixed_bars_exit` -> dispatch (FixedBars -> existing kernel; `PriceBracketExit` -> new kernel; anything else -> the same `SimulationEngineError` as today) | `research/simulation/engine.py` | 2 call sites |
| 4 | **NEW (Correction 1)** the same two gates become the same dispatch/structural checks; run-id/manifest construction stops reading `exit_model.exit_after_bars` directly | `application/strategy_research/run_strategy_research.py` + `research/datasets/strategy_research.py` | ~25 lines |
| 5 | New `@njit` kernel over `open/high/low`, plus its own result dataclass and materializers (Correction 3) | `research/simulation/kernels/bracket.py` (new file) | new file |

```text
LOCKED  kernels/fixed_bars.py is NOT edited — not one character.
LOCKED  compile.py and input.py are NOT edited (high/low already compiled).
LOCKED  ExitModel and RiskModel Protocol definitions are NOT modified.
LOCKED  if implementation reveals a SIXTH engine change is needed, that is a
        STOP-and-ask — a new ADR amendment with fresh maintainer approval,
        never a quiet widening.
```

The requested non-goal narrowing is restated accordingly:

```text
From: "no change to BarSequentialSimulator"
To:   "no change to the FIXED-BARS path's fill, accounting or run-identity
       semantics; dispatch to an additional kernel is allowed."
```

### Additional alternatives considered for the resumption

11. **Write a separate ADR-0029 superseding this one**, leaving this ADR's
    decline record untouched. This was the architect's original proposal.
    **Rejected by the maintainer** in favor of flipping this ADR's own
    Status: the maintainer preferred one document carrying the full history
    (declined, then accepted-with-corrections) over two documents. The
    decline record is preserved above under "History", not deleted.
12. **Keep `exit_after_bars: int` in `derive_strategy_run_id` and pass a
    sentinel (e.g. `max_bars`) for brackets.** Rejected: two different exit
    models could then collide on one run identity, and the parameter name
    would lie about its contents.
13. **Add a new `exit_model_fingerprint` field to the manifest and the run-id
    payload**, rather than generalizing the existing parameter. Rejected: it
    changes the payload for existing fixed-bars runs and therefore every
    existing `run_id` — the one thing the golden run forbids.
14. **Generalize the robustness delay stress to brackets now.** Rejected:
    "delay a price-triggered exit by N bars" has no obvious correct meaning;
    deciding it inside an engine sprint would be an unreviewed research
    decision (Correction 4).
15. **Write a bracket reference kernel too.** Rejected for v1 (Correction 4)
    — doubles the consistency surface for a path with no legacy behaviour;
    logged as TD-028 with a named repayment trigger rather than pretended
    away.

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
  audit list for `ExitReason` consumers (Sprint 047 planning).
- `S048_WAVE0_DECISIONS.md` binds the exact field sets, the catalog set, the
  example-strategy compositions, and the golden-run definition for the
  resumption (Sprint 048 planning).
- TD-026: static equity-percent sizing; repayment requires a `RiskModel`
  protocol change with execution-path impact.
- TD-027 (new, Sprint 048): the Robustness delay stress dimension rejects
  bracket exits; repayment trigger is the first request to stress a bracket
  strategy.
- TD-028 (new, Sprint 048): `kernels/bracket.py` has no independent reference
  implementation; repayment trigger is the first bracket-path numerical bug.
- Robustness Research stress dimensions over `stop_loss_bps` / `take_profit_bps`
  are an obvious follow-on and are explicitly **not** in Sprint 048 either.

## Related

- `docs/product/PRD-strategy-authoring.md` (Sprint 047, confirmed)
- `docs/product/PRD-exit-risk-and-catalog-expansion.md` (Sprint 048, confirmed)
- `docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md` (the MVP gates this widens)
- `docs/adr/ADR-0027-operator-authored-strategy-loading.md` (the loader, reused unchanged)
- `docs/planning/sprints/SPRINT_047.md` §4, `S047_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_048.md`, `S048_WAVE0_DECISIONS.md`
- `docs/planning/TECHNICAL_DEBT.md` TD-026, TD-027, TD-028
</content>
</invoke>
