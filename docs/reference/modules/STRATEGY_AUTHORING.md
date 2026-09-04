# Custom Strategy Authoring (`strategy_file`)

> Moved from `docs/reference/STRATEGY_AUTHORING.md` to
> `docs/reference/modules/STRATEGY_AUTHORING.md` by Sprint 054 T008
> (`docs/reference` system/workflows/runbooks/modules split). Content
> unchanged.
>
> Trimmed by Sprint 055 T007 to §1-3/§6-8 plus the Sprint 048 Exit/Risk
> semantics block, per
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1. The former §4
> (per-component semantics — not specific to strategy authoring) moved to
> [`ANALYSIS_COMPONENT_CATALOG.md`](ANALYSIS_COMPONENT_CATALOG.md); the
> former §5 (worked examples) moved to
> [`STRATEGY_EXAMPLES.md`](STRATEGY_EXAMPLES.md).

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
is stated here, in `--help`, and in `docs/reference/modules/OPERATOR_CLI.md`.

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

> Former §4 ("Composing with the catalog") moved to
> [`ANALYSIS_COMPONENT_CATALOG.md`](ANALYSIS_COMPONENT_CATALOG.md); former §5
> ("Worked examples") moved to
> [`STRATEGY_EXAMPLES.md`](STRATEGY_EXAMPLES.md).

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
- `docs/reference/modules/OPERATOR_CLI.md` — the full CLI operator guide.
- [`ANALYSIS_COMPONENT_CATALOG.md`](ANALYSIS_COMPONENT_CATALOG.md) — per-component
  semantics for every component named below (formerly this file's §4).
- [`STRATEGY_EXAMPLES.md`](STRATEGY_EXAMPLES.md) — the worked examples
  (formerly this file's §5).
- `apps/cli/CLAUDE.md` — module context for anyone editing `apps/cli`.
- `docs/planning/sprints/SPRINT_048.md`, `S048_WAVE0_DECISIONS.md` — the
  sprint that shipped the three worked examples in `STRATEGY_EXAMPLES.md`'s
  second block.
- `docs/planning/sprints/SPRINT_051.md`, `S051_WAVE0_DECISIONS.md` — the
  sprint that shipped the momentum/regime catalog in
  `ANALYSIS_COMPONENT_CATALOG.md`'s third block and the worked example in
  `STRATEGY_EXAMPLES.md`'s third block; §13 Review records the two warm-up
  text corrections referenced above.
- `docs/planning/sprints/SPRINT_047.md`, `S047_WAVE0_DECISIONS.md` — sprint
  scope and binding decisions.
- `docs/planning/TECHNICAL_DEBT.md` TD-025 — the boundary test's blind spot.
