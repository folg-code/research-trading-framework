# PRD — Exit/Risk Model Expansion, Market/Signal Catalog Growth, and New Strategies

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for Phase 2F/11/12.
This sprint resumes work that Sprint 047 explicitly scoped, designed, and
deferred — not a new idea.

## Problem

Sprint 047 (Phase 12) closed the strategy-authoring loop (`strategy_file` +
`build_strategy()`) but shipped only two of its three originally-scoped
pieces. `BracketExitModel`/`EquityPercentRiskModel` — the third — turned out
to require narrowing a non-goal on `BarSequentialSimulator`, because
`ExitModel`'s entire contract (`exit_bar_index(*, entry_fill_bar_index: int)
-> int`) is a pure function of a bar index with no access to price. ADR-0028
designed the narrowing in full (four bounded engine changes, one new kernel,
a golden-run regression as the safety net) and the maintainer declined it
*for that sprint*, explicitly as a scope decision, not a technical
objection — the design was kept, not discarded, precisely for this moment.

Separately, the Market/Signal component catalog remains thin even after
Sprint 047's two additions (`candle.wick`, `structure.level_distance`) —
`volatility.{atr,true_range,state}`, `structure.{swing,session_range,
level_distance}`, `trend.{ema,slope}`, `candle.wick`. There isn't yet a
critical mass of components to compose genuinely varied strategies from.

## Goals (v1)

- **Resume ADR-0028 as designed.** `BracketExitModel` (stop-loss /
  take-profit / mandatory `max_bars` timeout, basis-point offsets,
  pessimistic same-bar stop-wins rule, trigger-price fill with adverse
  slippage) and `EquityPercentRiskModel` (static, authoring-time sizing —
  `quantity = account_equity * risk_percent / stop_distance`, resolved once
  at construction, explicitly not equity-curve-following). The four bounded
  engine changes ADR-0028 §2 scoped (the two ADR-0016-era MVP `isinstance`
  gates become supported-combination/structural checks; a new
  `kernels/bracket.py` `@njit` kernel; dispatch in both `simulate()` and
  `simulate_from_columnar()`), with `kernels/fixed_bars.py` untouched and a
  golden-run byte-identity regression as the binding acceptance criterion.
- **Grow the Market/Signal component catalog.** Architect proposes the
  specific set, chosen for genuine composability into this sprint's new
  strategies (same discipline as Sprint 047's wick/level_distance choice) —
  not an arbitrary indicator dump.
- **2-3 new worked example strategies** composing the new catalog components
  with the new Exit/Risk models, loaded through the existing `strategy_file`
  CLI mechanism (Sprint 047) — a demonstration pattern, not a research
  deliverable in its own right.

## Non-goals (v1)

- Dynamic, equity-curve-following position sizing (TD-026 — still requires a
  `RiskModel` protocol change with paper-broker and live-execution impact,
  explicitly out of scope here too).
- Any change to `kernels/fixed_bars.py` or the `ExitModel`/`RiskModel`
  Protocol definitions themselves — `BracketExitModel` satisfies `ExitModel`
  unchanged plus an additive `PriceBracketExit` protocol, exactly as
  ADR-0028 designed.
- A declarative (YAML/JSON) strategy specification format (still no
  serialization exists for `StrategyModelDefinition`; still a phase, not a
  task).
- Robustness Research stress dimensions over the new bracket parameters —
  a natural follow-on, not this sprint's job.
- Arithmetic in the model-expression IR (Sprint 047 Finding 3) — components
  remain the mechanism for anything the comparison-only DSL can't express.

## Success metrics

- A strategy using `BracketExitModel` and/or `EquityPercentRiskModel` runs
  end to end through `trading-cli research run strategy` and produces real
  stop/target/timeout exits distinguishable by `exit_reason` in the trades
  table.
- Golden-run regression: the canonical Sprint 013 strategy (fixed-bars path)
  produces a byte-identical run fingerprint, trades table, and equity table
  before and after this sprint's engine changes.
- At least 2-3 new example strategies each compose at least one new
  Market/Signal component with the new Exit/Risk models, loaded through the
  existing CLI mechanism with no changes to the loader itself.
- The two ADR-0016-era MVP `isinstance` gates (`strategy/strategy_model.py`,
  `research/simulation/engine.py`) stop hard-blocking every future Exit/Risk
  model, not just this sprint's two.

## Riskiest assumption

That the engine changes stay genuinely bounded to what ADR-0028 §2 scoped.
The golden-run regression is the enforcement mechanism, not a hope — if the
fixed-bars path's fingerprint drifts even slightly, the change is wrong, not
the regression test. The architect should re-verify ADR-0028's four-change
list against the current state of `research/simulation/engine.py` (it may
have shifted since Sprint 047 was planned) before treating the design as
still accurate.

## Open questions

- Exact new Market/Signal component set — architect proposes.
- Exact new example strategies' composition (which components + which
  Exit/Risk model each) — architect proposes, consistent with proving both
  `BracketExitModel` and `EquityPercentRiskModel` are actually exercised.
- Whether this needs a fresh ADR (an ADR-0028 "resurrection" amendment
  recording the new approval) or whether ADR-0028 itself can simply flip
  from "PROPOSED, declined for Sprint 047" to "ACCEPTED" with a dated
  approval note — architect's call, but the approval record must be genuine
  and specific either way, per this project's established governance bar.

## Handoff

Architect: design this as a single sprint (the four pieces — engine, new
Exit/Risk models, catalog growth, example strategies — are gated on each
other for a working demonstration, same reasoning as Sprint 047 itself).
Re-verify ADR-0028's engine-change scope against current code before
resurrecting it. Propose the specific catalog additions and example
strategies as a Wave 0 decision set, per this project's established
sprint-opening conventions.
