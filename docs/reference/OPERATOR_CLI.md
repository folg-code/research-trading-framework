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
trading-cli data fetch     binance | databento
trading-cli research run   predictive | strategy
trading-cli dry-run start
trading-cli report render  predictive | strategy
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
| `--dry-run` | Validate and resolve the plan (workflow, arguments, output paths), print it, and stop. No file write, no dataset registration, no network call, no side effect of any kind. |
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
| `research run` (strategy) | `apps/cli/examples/research_run_strategy.yaml` |
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
  `dataset_ref`.

**Known limitation — SPRINT_046.md §4 finding 2 (binding):**
`research run strategy` inherits the same hardcoded choices
`scripts/strategy_research/run_strategy_research.py` already makes: the
canonical strategy model (`build_canonical_strategy_model()`), the
simulation assumptions (`SimulationAssumptions()`), and the session resolver
(`CmeEsRthSessionResolver()`). There is no config key to choose a different
one in v1 — this is a stated limitation, not a silently-implied one.
Selecting a different strategy model requires calling
`run_strategy_research` directly in Python, or a follow-on increment to the
application layer.

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

Two limitations are inherited from the workflows this CLI wraps, not
introduced by the CLI itself. Both are documented here and in the relevant
command's `--help` text rather than silently implied:

1. **`research run strategy` hardcodes the canonical strategy model.**
   `build_canonical_strategy_model()`, `SimulationAssumptions()` and
   `CmeEsRthSessionResolver()` are fixed, the same way the wrapped script
   fixes them (SPRINT_046.md §4 finding 2). See §5 above.
2. **`data fetch binance` only supports `interval: 1m`** (TD-023). See §5
   above; `docs/planning/TECHNICAL_DEBT.md` TD-023 has the full root cause
   and repayment trigger.

---

## 8. Related

- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` — design
  record: framework choice, placement, import boundary, full config schema.
- `docs/planning/sprints/SPRINT_046.md` — sprint scope, thin-wrapper
  feasibility audit, task breakdown.
- `apps/cli/CLAUDE.md` — module context for anyone editing `apps/cli`.
- `apps/cli/examples/` — one runnable example config per command group.
- `docs/planning/TECHNICAL_DEBT.md` TD-023 — Binance interval limitation.
