# Custom Strategy Authoring (`strategy_file`)

This is the operator-facing how-to guide for writing your own Strategy Model
and running it through `trading-cli research run strategy` (Phase 12,
Sprint 047). The design record — why one config key, why no sandbox, the
full loading mechanism — lives in
`docs/adr/ADR-0027-operator-authored-strategy-loading.md`. This document
does not repeat that reasoning; it explains how to author, run and debug a
strategy file as an operator.

---

## 1. The convention

A strategy file is an ordinary `.py` file with exactly one required export:

```python
def build_strategy() -> StrategyModelDefinition:
    ...
```

```text
Name        build_strategy           fixed, conventional, NOT configurable
Signature   zero required arguments  (optional/defaulted parameters are fine)
Returns     StrategyModelDefinition  Market x Signal x Exit x Risk (ADR-0016)
```

Point a config at it with the `strategy_file` key, and run it exactly like
any other `research run strategy` config:

```yaml
research:
  kind: strategy
  strategy:
    dataset_ref: "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1"
    timeframe: 1m
    strategy_file: user_data/components/strategies/my_strategy.py   # NEW
```

```powershell
uv run trading-cli research run --config <path> --dry-run   # proves it loads
uv run trading-cli research run --config <path>              # runs it
```

`strategy_file` is **optional**. Leave it out and `research run strategy`
behaves exactly as it always has — the Sprint 013 canonical example runs.
This is purely additive; every existing config keeps working unchanged.

There is no function-name field and no `module:function` pair — one path,
one fixed entry point. A dotted import path was deliberately rejected too
(ADR-0027 Alternative 1): it would couple your strategy to `sys.path` layout
this CLI never touches.

---

## 2. The trust model — no sandbox

**Loading a `strategy_file` has the exact same blast radius as running that
file yourself: `uv run python <that file>`.**

> No sandbox. No import restriction. No AST inspection. No subprocess
> isolation. The security model is exactly the model of running any local
> script the operator already trusts. — ADR-0027 §2

That is a deliberate design choice, not an oversight. Sandboxing an
arbitrary operator-supplied Python file is a stated non-goal of the PRD, and
arguably incoherent with the premise that this is *your own code*: an
unrestricted interpreter is one line away regardless of what the loader
restricts. What is not acceptable is leaving this implicit — which is why it
is stated here, in `--help`, and in `docs/reference/OPERATOR_CLI.md`.

Practically:

- a strategy file that reads a file, writes a file, opens a socket, or reads
  an environment variable will do exactly that, the moment it is imported;
- **`--dry-run`'s "touches nothing" guarantee narrows.** The CLI itself
  performs no side effect under `--dry-run` — no dataset registration, no
  simulation, no persisted run. But the loaded module is *your* code and it
  executes at import time (loading happens during plan resolution, so a
  typo'd entry-point name or a wrong return type fails pre-flight instead of
  after a multi-minute dataset read). A strategy file that writes to disk at
  import time will still do so under `--dry-run`. See ADR-0027 §4.
- never put credentials in the strategy file's *config* — the CLI still
  rejects any credential-shaped key in the YAML document itself. What the
  Python file itself does with an environment variable is entirely its own
  business; the CLI neither helps nor blocks it.

---

## 3. Error table

Every failure is pre-flight (loading happens during plan resolution, before
any framework side effect) and every message names
`research.strategy.strategy_file` or the resolved absolute path, so you are
never left staring at a stack trace mid-simulation. The dividing line: if
something is wrong with the file, the convention, or the object it returned,
that's a configuration problem (exit code 2, `ConfigError`). Only an
exception your own `build_strategy()` body raises is a workflow failure
(exit code 1, `WorkflowError`).

| What went wrong | What you'll see | Exit code |
|---|---|---|
| The path doesn't exist, isn't a file, or is a directory | `ConfigError` naming `research.strategy.strategy_file` and the resolved absolute path | 2 |
| The file's extension isn't `.py` | `ConfigError` naming the actual extension | 2 |
| Importing the file raises (a syntax error, a missing import, anything at module scope) | `ConfigError` naming the file, chained from your original exception (`--verbose` shows your traceback) | 2 |
| The file has no `build_strategy` at all | `ConfigError` stating the convention verbatim: a zero-argument `build_strategy()` | 2 |
| `build_strategy` exists but isn't callable (e.g. it's a variable) | `ConfigError` naming the attribute's actual type | 2 |
| `build_strategy` requires one or more arguments | `ConfigError` naming those parameter names | 2 |
| `build_strategy()` itself raises | `WorkflowError`, chained from your original exception | 1 |
| `build_strategy()` returns something that isn't a `StrategyModelDefinition` | `ConfigError` naming the actual returned type | 2 |
| The returned `StrategyModelDefinition` fails the framework's own validation (e.g. an unsupported Exit/Risk model combination) | `ConfigError` carrying the framework's own validation message | 2 |

No exception is ever swallowed: every chained error keeps `__cause__`, so
`--verbose` always shows you your own stack, not just the CLI's summary.

---

## 4. Composing with the catalog

Everything you compose a strategy from is `model_authoring`'s typed DSL —
the same one `user_data/components/strategies/*.py` and the framework's own
canonical examples use. Two components were added this sprint:

- **`candle.wick`** — `candle.upper_wick_ratio()`, `candle.lower_wick_ratio()`,
  `candle.body_ratio()`. Bar-local, causal, no warmup — a rejection candle
  at a level is a common building block.
- **`structure.level_distance`** — `structure.distance_to_session_high(period=14)`,
  `structure.distance_to_session_low(period=14)`. ATR-normalized distance
  from price to the running session high/low. This exists as a *component*,
  not an expression, because the DSL only supports comparisons
  (`==`, `!=`, `>`, `>=`, `<`, `<=`) — there is no arithmetic (`-`, `/`) on an
  `Operand`, so `(price - level) / atr` cannot be written directly in a
  Market/Signal Model condition. `structure.level_distance` does that
  normalization for you.

## 5. Worked examples

Two example strategies live in this sprint's demo, one per new component.
Both are **gitignored** (`user_data/` is not shipped with the repository,
per `docs/adr/ADR-0002-separate-src-and-user-data.md`) — recreate the file
below verbatim before pointing a config at it. Each has a matching, committed
example config under `apps/cli/examples/` you can copy and edit.

### `candle.wick` — a wick-rejection strategy

`user_data/components/strategies/candle_wick_rejection.py`
(config: `apps/cli/examples/research_run_strategy_candle_wick.yaml`):

```python
from decimal import Decimal

from trading_framework.model_authoring import (
    LONG,
    ON_TRUE_EDGE,
    VolatilityState,
    candle,
    market_model,
    signal_model,
    volatility,
)
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "candle_wick_rejection_market",
        when=(volatility.state(period=14, threshold=5.0) == VolatilityState.HIGH),
    ).definition

    signal = signal_model(
        "candle_wick_rejection_signal",
        direction=LONG,
        when=(candle.lower_wick_ratio() > candle.body_ratio()),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="candle_wick_rejection",
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=10),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(1)),
    )
```

### `structure.level_distance` — a session-low pullback strategy

`user_data/components/strategies/level_distance_pullback.py`
(config: `apps/cli/examples/research_run_strategy_level_distance.yaml`):

```python
from decimal import Decimal

from trading_framework.model_authoring import LONG, market_model, signal_model, structure
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)
from trading_framework.time.models.timeframe import Timeframe


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "level_distance_pullback_market",
        when=(structure.distance_to_session_low(period=14) < 0.5),
    ).definition

    signal = signal_model(
        "level_distance_pullback_signal",
        direction=LONG,
        when=structure.higher_low_event(pivot_range=15, timeframe=Timeframe("5m")),
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="level_distance_pullback",
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=10),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(1)),
    )
```

Both use the existing `FixedBarsExitModel` / `FixedQuantityRiskModel` —
those were the only Exit/Risk models the simulator supported at the time
Sprint 047 wrote these two examples.
`BracketExitModel` / `EquityPercentRiskModel` (stop-loss, take-profit,
equity-relative sizing) were scoped in `docs/adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md`,
declined for Sprint 047, and resumed and shipped in Sprint 048 — see the
next section for worked examples using them.

### Worked examples — Sprint 048 (bracket exits + equity-percent sizing)

Three more example strategies, per `S048_WAVE0_DECISIONS.md` D-S048-11, each
composing at least one of Sprint 048's new catalog components
(`trend.ema_distance`, `volatility.range_expansion`) with one or both of the
new Exit/Risk models. Like the two above, all three are **gitignored**
(`user_data/` — ADR-0002) — recreate the file below verbatim before pointing
a config at it. Each has a matching, committed example config under
`apps/cli/examples/`.

#### `ema_reversion_bracket.py` — `BracketExitModel` in isolation

`user_data/components/strategies/ema_reversion_bracket.py`
(config: `apps/cli/examples/research_run_strategy_ema_reversion_bracket.yaml`):

```python
from decimal import Decimal

from trading_framework.model_authoring import LONG, market_model, signal_model, trend
from trading_framework.strategy import (
    BracketExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)


def build_strategy() -> StrategyModelDefinition:
    stretched_below_ema = (
        trend.ema_distance(period=20, atr_period=14) < -0.5
    )

    market = market_model(
        "ema_reversion_bracket_market",
        when=stretched_below_ema,
    ).definition

    signal = signal_model(
        "ema_reversion_bracket_signal",
        direction=LONG,
        when=stretched_below_ema,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="ema_reversion_bracket",
        market_model=market,
        signal_model=signal,
        exit_model=BracketExitModel(
            stop_loss_bps=10.0,
            take_profit_bps=10.0,
            max_bars=15,
        ),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(1)),
    )
```

`BracketExitModel` in isolation, on the bracket kernel
(`research/simulation/kernels/bracket.py`) — stop, target and timeout are
all reachable. The stop/target/timeout above are not arbitrary: on the
committed OHLCV fixture (`tests/fixtures/market_data/ohlcv_sample_1m.csv`)
this strategy produces **43 trades, split 3 `stop_loss` / 3 `take_profit` /
37 `max_bars`** — verified by an actual run before being committed, not
asserted without checking. A bracket example that only ever times out
would prove nothing (D-S048-11).

#### `range_expansion_breakout.py` — both new models together

`user_data/components/strategies/range_expansion_breakout.py`
(config: `apps/cli/examples/research_run_strategy_range_expansion_breakout.yaml`):

```python
from decimal import Decimal

from trading_framework.model_authoring import (
    LONG,
    ON_TRUE_EDGE,
    market_model,
    price,
    signal_model,
    structure,
    volatility,
)
from trading_framework.strategy import (
    BracketExitModel,
    EquityPercentRiskModel,
    StrategyModelDefinition,
)


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "range_expansion_breakout_market",
        when=(volatility.range_expansion(period=14) > 1.5),
    ).definition

    signal = signal_model(
        "range_expansion_breakout_signal",
        direction=LONG,
        when=(price.close > structure.session_high()),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="range_expansion_breakout",
        market_model=market,
        signal_model=signal,
        exit_model=BracketExitModel(
            stop_loss_bps=15.0,
            take_profit_bps=30.0,
            max_bars=40,
        ),
        risk_model=EquityPercentRiskModel(
            account_equity=Decimal(100_000),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("2"),
        ),
    )
```

Composes `BracketExitModel` and `EquityPercentRiskModel` together, end to
end through the CLI (PRD success metric 1). The `EquityPercentRiskModel`
`stop_distance` (2 points) is the operator's own estimate of what the
bracket's 15 bps stop is worth near this instrument's price level — v1
does not cross-validate the two (D-S048-05), so keeping them consistent is
the operator's responsibility.

**A structural note, not a bug in this example specifically:**
`structure.session_high()` is a running, current-bar-**inclusive** high
(`max(session_high[i-1], high[i])`). Because a bar's own `high` is always
`>= close`, the condition `price.close > structure.session_high()` can only
become true on a bar whose close equals its own (freshly-set) high — a
narrow condition that the committed one-day fixture does not happen to
contain, so this example produces **0 trades** on that fixture specifically.
The strategy still loads and runs end to end through the CLI with no error;
`session_high_breakout.py` (Sprint 047, above) uses the same comparison and
has the same characteristic. Point it at a longer/live dataset to see it
actually fire.

#### `quiet_wick_rejection.py` — the risk-model isolation case

`user_data/components/strategies/quiet_wick_rejection.py`
(config: `apps/cli/examples/research_run_strategy_quiet_wick_rejection.yaml`):

```python
from decimal import Decimal

from trading_framework.model_authoring import LONG, ON_TRUE_EDGE, candle, market_model, signal_model, volatility
from trading_framework.strategy import (
    EquityPercentRiskModel,
    FixedBarsExitModel,
    StrategyModelDefinition,
)


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "quiet_wick_rejection_market",
        when=(volatility.range_expansion(period=14) < 0.8),
    ).definition

    signal = signal_model(
        "quiet_wick_rejection_signal",
        direction=LONG,
        when=(candle.lower_wick_ratio() > 0.4),
        firing=ON_TRUE_EDGE,
    ).definition

    return StrategyModelDefinition(
        strategy_model_id="quiet_wick_rejection",
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=10),
        risk_model=EquityPercentRiskModel(
            account_equity=Decimal(100_000),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("2"),
        ),
    )
```

The deliberate isolation case (D-S048-11): `EquityPercentRiskModel` on the
**unchanged** fixed-bars kernel (`kernels/fixed_bars.py`, not touched this
sprint), proving the new sizing model is orthogonal to the new bracket
exit-model change — a strategy can adopt equity-percent sizing without
touching its exit model at all. On the committed OHLCV fixture this
produces 53 trades, every one with `exit_reason == "fixed_bars"` (the only
reason `FixedBarsExitModel` ever emits — intentionally only one distinct
reason here, unlike `ema_reversion_bracket.py` above).

---

## 6. The advisory import convention (not enforced)

Your strategy file can import anything your own Python environment can
import — nothing stops it, and nothing scans it (§7 below). For
portability across environments and framework versions, it *should* only
need:

```text
trading_framework.model_authoring        the DSL (market_model, signal_model, price, ...)
trading_framework.strategy.*             StrategyModelDefinition, Exit/Risk models
trading_framework.time.models.timeframe  Timeframe
```

Reaching deeper — into `research.*`, `infrastructure.*`, or an application
workflow — is legal and will work, but it's a smell: it usually means the
strategy is trying to do something a Market/Signal Model should express
instead. This is **advisory only, never checked at runtime.** Breaking it
costs you portability; it costs the framework nothing, which is exactly why
nothing enforces it.

If your strategy needs a sibling file (a shared helper module, a constants
file), the CLI never mutates `sys.path` on your behalf — that is a
deliberate choice (ADR-0027 §3), not a gap. Set `PYTHONPATH` yourself before
invoking `trading-cli`, or keep your strategy self-contained in one file.

---

## 7. Why the boundary test can't see your strategy file (and never will)

`tests/unit/test_apps_boundaries.py` enforces `apps/cli`'s own 17-module
import allow-list by statically scanning `apps/cli/src`. Your strategy file
is not part of `apps/cli/src` — it typically lives in gitignored
`user_data/`, and CI never sees it. The loader itself needed **zero**
widening of that allow-list to exist: `trading_framework.strategy` was
already on it, and it exports everything the loader needs
(`StrategyModelDefinition`, `StrategyModelDefinitionError`,
`validate_strategy_model_definition`).

A green boundary test is proof about this repository's own source tree. It
is not, and was never intended to be, proof that nothing outside that list
was imported by a loaded strategy at runtime — that gap is logged as
**TD-025** in `docs/planning/TECHNICAL_DEBT.md`, so it is never mistaken for
an oversight.

---

## 8. Related

- `docs/adr/ADR-0027-operator-authored-strategy-loading.md` — the design
  record: loading mechanism, the two import boundaries, error taxonomy.
- `docs/adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md` — the
  Exit/Risk expansion: declined for Sprint 047, resumed and accepted for
  Sprint 048 (`BracketExitModel`, `EquityPercentRiskModel`).
- `docs/reference/OPERATOR_CLI.md` — the full CLI operator guide.
- `apps/cli/CLAUDE.md` — module context for anyone editing `apps/cli`.
- `docs/planning/sprints/SPRINT_048.md`, `S048_WAVE0_DECISIONS.md` — the
  sprint that shipped the three worked examples in §5's second block.
- `docs/planning/sprints/SPRINT_047.md`, `S047_WAVE0_DECISIONS.md` — sprint
  scope and binding decisions.
- `docs/planning/TECHNICAL_DEBT.md` TD-025 — the boundary test's blind spot.
