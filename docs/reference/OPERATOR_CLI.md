# Operator CLI (`trading-cli`)

This is the operator-facing how-to-use-it guide for `trading-cli`
(`apps/cli`, Phase 11). The design record — why `argparse`, why `apps/cli`,
why the import boundary differs from `apps/dashboard`, the full YAML config
contract — lives in `docs/adr/ADR-0026-operator-cli-framework-and-placement.md`
(including Amendment 1, the named import-boundary exceptions). This document
does not repeat that schema; it explains how to drive it as an operator, and
points at a runnable example for each command group.

---

## 1. What it is

One entry point, four command groups, one YAML config:

```text
trading-cli data fetch      binance | databento
trading-cli research run    predictive | strategy
trading-cli research promote
trading-cli dry-run start
trading-cli report render   predictive | strategy
```

Every command is a thin wrapper over an existing `trading_framework.application.*`
workflow — the same workflow the equivalent `scripts/` entry point already
calls. `trading-cli` adds no new capability and reimplements nothing; it
replaces remembering a flag sequence with one config file per run.

`scripts/` is unchanged and remains a valid front door. Use whichever is more
convenient; both call the same application layer, so behaviour does not
drift between them.

---

## 2. Installation and invocation

```powershell
cd <repo-root>
uv sync --all-packages
uv run trading-cli --help
uv run trading-cli <group> <command> --config <path> [--dry-run] [--json] [--verbose]
```

`--config PATH` is required on every command. There is no global install —
every invocation goes through `uv run trading-cli ...`.

---

## 3. Global flags

| Flag | Effect |
|---|---|
| `--config PATH` | Required. Path to the YAML config document (see §4). |
| `--dry-run` | Validate and resolve the plan (workflow, arguments, output paths), print it, and stop. No file write, no dataset registration, no network call, no side effect of any kind **from the CLI itself**. **Narrowed exception (Sprint 047, ADR-0027 §4):** when `research.strategy.strategy_file` is set, resolving the plan imports and executes that file to prove it loads — the CLI performs no side effect, but the loaded module is your own code and executes at import time. See §5 `research run` and `docs/reference/STRATEGY_AUTHORING.md` §2. |
| `--json` | Print the plan (`--dry-run`) or the result as structured JSON instead of the human-readable text form — for scripting, not a different behaviour. |
| `--verbose` | Additional diagnostics on stderr. Never prints a credential in any mode, including `--dry-run` and `--verbose` (D-S046-08). |

`--dry-run` always runs config validation and plan resolution first, so a bad
config fails the same way with or without it — it only changes whether the
workflow actually executes afterward.

---

## 4. Config file

One YAML document per run: a thin common envelope (`version`,
`storage_root`), plus whichever of the four per-group blocks
(`data`, `research`, `dry_run`, `report`) the command you're running needs.
Unknown keys are always a hard error naming the offending key (and the
closest valid key, when there is an obvious one) — a typo never silently
does nothing.

**The full schema (every key, every block, every type) is documented once,
in `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` §4 — the
design record.** This guide does not restate it. Instead, `apps/cli/examples/`
has one complete, schema-valid config per command group you can copy and
edit directly:

| Command group | Example config |
|---|---|
| `data fetch` (binance) | `apps/cli/examples/data_fetch_binance.yaml` |
| `data fetch` (databento) | `apps/cli/examples/data_fetch_databento.yaml` |
| `research run` (predictive) | `apps/cli/examples/research_run_predictive.yaml` |
| `research run` (strategy, canonical example) | `apps/cli/examples/research_run_strategy.yaml` |
| `research run` (strategy, operator-authored via `strategy_file`) | `apps/cli/examples/research_run_strategy_candle_wick.yaml`, `apps/cli/examples/research_run_strategy_level_distance.yaml` |
| `research promote` | `apps/cli/examples/research_promote.yaml` |
| `dry-run start` | `apps/cli/examples/dry_run_start.yaml` |
| `report render` | `apps/cli/examples/report_render.yaml` |

Each example file says in its own header comment whether it runs as-is or
needs real data/network first (see `apps/cli/examples/README.md` for the
summary table). Every one of them passes `--dry-run` with no setup.

No credential ever belongs in a config file — a key that merely *looks*
credential-shaped (`api_key`, `secret`, `token`, `password`, `credential`,
…) anywhere in the document is rejected outright, not just discouraged. The
one Binance credential this CLI touches indirectly,
`TRADING_FRAMEWORK_BINANCE_API_KEY`, is read from the environment by the
underlying fetch layer — `trading-cli` never reads it and never forwards a
config value for it.

---

## 5. Command groups

### `data fetch`

```powershell
uv run trading-cli data fetch --config <path>
```

Selected by `data.provider: binance | databento`.

- **`binance`** fetches a historical OHLCV range over the network
  (`import_binance_futures_ohlcv`) and publishes a `DatasetRef`. Anonymous
  requests work; setting `TRADING_FRAMEWORK_BINANCE_API_KEY` in your shell
  raises the request-weight limit.
- **`databento`** *imports* a local `.dbn`/`.dbn.zst` archive already on disk
  (`import_databento_trades_archive`) — this is an archive import, not a
  network fetch, despite sharing the `data fetch` command name. `source_id`
  and `provider_symbol` default from `instrument_id`; an archive that needs a
  distinct value for either needs the existing script
  (`scripts/databento/import_trades.py`) directly.

**Known limitation — TD-023 (binding):** `data fetch binance` only works for
`interval: 1m` today. The historical reader reuses the same kline mapper the
live dry-run path uses, and that mapper only decodes 1-minute klines. A
non-`1m` interval is rejected by `resolve_plan` itself, before any network
call, naming `data.binance.interval` and pointing at TD-023 — you will never
see a raw failure from deep inside the fetch layer.

### `research run`

```powershell
uv run trading-cli research run --config <path>
```

Selected by `research.kind: predictive | strategy`.

- **`predictive`** is the only *composed* command in v1: it runs
  build → run → render as one call, passing the dataset id and run id
  between steps as typed Python values, never through stdout. `definition`
  and `estimator` reference existing `PredictiveStudySpec` /
  `EstimatorSpec` files by path; their own loaders parse them.
- **`strategy`** runs one Strategy Research simulation against a published
  `dataset_ref`. By default it evaluates the Sprint 013 canonical example.
  **Sprint 047 (ADR-0027) adds an optional `strategy_file` key** naming your
  own Python strategy file — see below.

**`research.strategy.strategy_file` (Sprint 047, ADR-0027) — run your own strategy:**

```yaml
research:
  kind: strategy
  strategy:
    dataset_ref: "..."
    timeframe: 1m
    strategy_file: user_data/components/strategies/my_strategy.py   # optional
```

`strategy_file` names a Python file with a zero-argument
`build_strategy() -> StrategyModelDefinition` entry point. When set, the run
manifest's `strategy_model_id` is *that* strategy's, not the canonical
example's. **Trust model: no sandbox, no import restriction** — loading a
`strategy_file` has the same blast radius as `uv run python <that file>`.
The full convention, error table, and worked examples are in
`docs/reference/STRATEGY_AUTHORING.md`.

**Known limitation — SPRINT_046.md §4 finding 2 (binding, two of three thirds
remain):** `research run strategy` still hardcodes the simulation
assumptions (`SimulationAssumptions()`) and the session resolver
(`CmeEsRthSessionResolver()`) the same way
`scripts/strategy_research/run_strategy_research.py` does — Sprint 047
closes only the strategy-model third of this finding. There is still no
config key to choose a different assumptions/session-resolver pair; that
requires calling `run_strategy_research` directly in Python, or a follow-on
increment to the application layer.

### `research promote`

```powershell
uv run trading-cli research promote --config <path>
```

Promotes the **last walk-forward fold** of one persisted Predictive Research
run (`research.promote.run_id`) into a content-addressed **promoted
artifact** under `research/predictive_research/promoted/{artifact_fingerprint}/`
(ADR-0029). It is a sibling subcommand of `research run`, selected by its own
`--config` block — not a `research.kind` value.

```yaml
research:
  promote:
    run_id: 0123456789abcdef
```

On success it prints `artifact_fingerprint` (the promoted artifact's
content-addressed identity) and the absolute `directory` it was written to,
plus the promoted `fold_id`. A promotion is **refused, and writes nothing**,
when:

- the run's model family is a tree or neural family (v1 supports
  `sklearn.ridge` / `sklearn.elastic_net` / `sklearn.logistic` only — a tree
  or neural family is deferred, not rejected forever),
- the run was trained under a different scikit-learn version than is
  currently installed (the remedy is to re-run the study).

**Requires the `ml` extra.** Promotion is the one operation that reads the
run's fitted joblib blob once, offline, to extract plain-number parameters
(ADR-0023 §7's narrow amendment, ADR-0029 §4) — it needs `sklearn`/`joblib`
installed on the machine you run it from. **Loading an already-promoted
artifact needs no extra at all** — that asymmetry is deliberate (promotion is
an offline operator act; inference is not). See
`docs/reference/PREDICTIVE_PROMOTION.md` for the practical reference (schema,
store layout, both guards, refusal messages) and
`docs/adr/ADR-0029-promoted-predictive-artifact.md` for the full design
record.

### `dry-run start`

```powershell
uv run trading-cli dry-run start --config <path>
```

Wraps the existing BTC futures dry-run runtime unmodified — no execution
logic changes. It connects to the live Binance USD-M websocket feed for
`dry_run.duration_minutes` and writes runtime events to
`dry_run.event_log`. It is a bounded local simulation (no real orders are
placed), not an offline replay, so it needs live network access.

### `report render`

```powershell
uv run trading-cli report render --config <path>
```

Selected by `report.kind: predictive | strategy`. Loads a persisted run by
`run_id` and writes the same offline HTML the underlying scripts already
produce. `output` is optional; when unset it falls back to the workflow's
own default path convention (the run directory for predictive;
`storage_root/reports/strategy/<run_id>.html` for strategy).

---

## 6. Exit codes

```text
0   success
1   workflow failure — a wrapped application workflow raised or failed
2   configuration or usage error — bad YAML, unknown key, missing required
    key, credential-shaped key, unsupported provider/kind, an argparse usage
    error translated from the main(argv) fallback path
```

An operator never sees a raw `argparse` usage message referring to flags
they did not type — where a script's `main(argv)` fallback is used,
`SystemExit` from `parse_args` is caught and translated into an exit-code-2
error naming the offending config key instead.

---

## 7. Known limitations (v1)

1. **`research run strategy` still hardcodes the simulation assumptions and
   session resolver.** `SimulationAssumptions()` and `CmeEsRthSessionResolver()`
   are fixed, the same way the wrapped script fixes them (SPRINT_046.md §4
   finding 2). The *strategy model* third of this finding is closed as of
   Sprint 047: `research.strategy.strategy_file` selects your own strategy
   instead of the canonical example. See §5 above and
   `docs/reference/STRATEGY_AUTHORING.md`.
2. **`data fetch binance` only supports `interval: 1m`** (TD-023). See §5
   above; `docs/planning/TECHNICAL_DEBT.md` TD-023 has the full root cause
   and repayment trigger.
3. **A loaded `strategy_file` is unsandboxed and unrestricted** (ADR-0027
   §2) — the same trust level as running any local script. `--dry-run`'s
   "touches nothing" guarantee narrows accordingly when `strategy_file` is
   set (§3 above, ADR-0027 §4).

---

## 8. Related

- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` — design
  record: framework choice, placement, import boundary, full config schema.
- `docs/adr/ADR-0027-operator-authored-strategy-loading.md` — design record
  for `research.strategy.strategy_file` (Sprint 047).
- `docs/adr/ADR-0029-promoted-predictive-artifact.md` — design record for
  `research promote` (Sprint 049): the parameter format, the promotion store,
  both guards, and the narrow ADR-0023 §7 amendment.
- `docs/reference/STRATEGY_AUTHORING.md` — the operator guide for writing
  and running your own strategy file.
- `docs/planning/sprints/SPRINT_046.md` — sprint scope, thin-wrapper
  feasibility audit, task breakdown.
- `apps/cli/CLAUDE.md` — module context for anyone editing `apps/cli`.
- `apps/cli/examples/` — one runnable example config per command group.
- `docs/planning/TECHNICAL_DEBT.md` TD-023 — Binance interval limitation.
