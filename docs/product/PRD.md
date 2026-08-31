# PRD — Binance Historical Data Ingestion + Universal Operator CLI

Feature-level PRD within the existing Trading Research Framework product (not a
new product). Scaled to project size per `devteam:discovery`: this project
already has `docs/vision/`, `ROADMAP.md`, and a sprint-based planning system —
this PRD scopes one new capability track before it becomes a sprint.

## Problem

Two related gaps surfaced while using the Predictive Research + Strategy
Research pipeline hands-on:

1. **No historical Binance data ingestion.** `infrastructure/providers/binance/futures_rest.py`
   only exposes `fetch_closed_klines` — the latest N closed candles (limit
   ≤1500, no `startTime`/`endTime`), built for dry-run reconnect gap-fill
   (Sprint 019). There is no paginated historical archive import comparable
   to the Databento flow (`import_databento_trades_archive`,
   `derive_ohlcv_from_trades`), so Binance data cannot become a queryable,
   published `DatasetRef` usable by Predictive/Strategy Research.
2. **No unified operator interface.** 45 scripts under `scripts/` (market_data,
   predictive_research, strategy_research, robustness_research,
   signal_research, execution, live_data, portfolio_live, ops, demo), each
   its own `argparse` entry point with its own flag set. Running the actual
   research loop (fetch data → build dataset → run research → render report)
   means manually chaining several `uv run python scripts/.../foo.py --flag
   value --flag2 value2` invocations in the right order, from memory.

## Goals (v1)

- **Binance historical OHLCV import**: paginated REST klines fetch over an
  arbitrary date range, USD-M futures only, published into the *same* dataset
  registry Databento uses — same `DatasetId`/`DatasetRef` contract,
  `provider="binance"`, same `finalize_dataset`/`publish_dataset` workflow
  (ADR-0007/ADR-0008 apply unchanged). Downstream Predictive/Strategy
  Research must not need to know or care which provider produced the bars.
- **Mode selector, OHLCV-only for v1**: the import command takes a `--mode`
  (or config field) that today only supports `ohlcv` (direct klines), but is
  designed so a future `trades` mode (fetch trades, derive OHLCV — symmetric
  to the Databento Sprint 011/012 pattern) is an additive change, not a
  rearchitecture.
- **Optional API key, market-data rate limits only**: an API key may be
  configured to raise the weight-based rate limit on public market-data
  endpoints. It is never used for account or order endpoints in this scope —
  no authenticated/private Binance API surface is touched. Never committed
  (same rule as `user_data/`: proprietary/secret material stays out of
  version control). This PRD left the exact storage mechanism open; ADR-0025
  §5 settled it as **environment variable only**
  (`TRADING_FRAMEWORK_BINANCE_API_KEY`) — no config file convention exists.
- **Universal CLI (`trading-cli`)**: one entry point, YAML config per
  invocation instead of long flag lists, covering four command groups:
  - `data fetch` — Binance (new) and Databento (existing) historical import
  - `research run` — Predictive Research and Strategy Research
  - `dry-run start` — wraps the existing BTC futures dry-run runtime
    (Sprint 018–024); no new execution logic
  - `report render` — offline HTML reports / dashboards for the above
  
  The CLI is a thin wrapper delegating to existing application-layer
  workflows and script `main()` functions where they already exist — not a
  rewrite of business logic. This bounds blast radius: existing scripts,
  tests, and demo code that call those `main()` functions directly keep
  working.

## Non-goals (v1)

- Binance **spot** market (USD-M futures only, matching existing live-data
  infrastructure).
- Any **authenticated/account** Binance endpoint — no order placement, no
  account balance, no real trading. Dry-run wrapping only.
- Binance **trades**-level import (mode is reserved, not built, in v1).
- Replacing all 45 scripts — only the four command groups above. Scripts
  outside that scope (ops, demo, robustness_research, signal_research) are
  untouched.
- Any change to execution/order-routing logic — `dry-run start` only wires
  the CLI to the existing runtime, it does not modify it.

## Success metrics

Four CLI commands work end-to-end against a YAML config, replacing today's
manual script chaining:

1. `trading-cli data fetch binance --config <path>` — publishes a queryable
   `DatasetRef` from a Binance USD-M futures historical OHLCV range.
2. `trading-cli research run --config <path>` — runs Predictive Research or
   Strategy Research (config selects which).
3. `trading-cli dry-run start --config <path>` — starts the existing BTC
   futures dry-run runtime.
4. `trading-cli report render --config <path>` — renders the corresponding
   offline HTML report/dashboard.

Plus: CI green on both workspaces, an architecture boundary test proving no
Binance credential ever needs to touch a committed file, and rate-limit
backoff verified against Binance's documented weight limits (no busy-loop
retry).

## Riskiest assumption

That 45 heterogeneous scripts can be unified behind 4 command groups purely
as **thin wrappers** without needing to touch their internals. If any
script's `main()` isn't cleanly callable as a function (e.g. relies on
`sys.argv` parsing side effects, or lacks a stable programmatic entry point),
wrapping it cheaply breaks down and the CLI work grows unpredictably. The
architect should audit the actual `main()` signatures of the scripts each
command group needs to wrap before committing to the wrapper-only approach.

## User stories

- As the maintainer, I can pull N months of BTCUSDT 1m OHLCV from Binance
  into the same dataset registry Databento uses, without touching Databento
  code.
- As the maintainer, I can run `trading-cli research run --config
  configs/my_study.yaml` instead of remembering the exact sequence of
  `build_predictive_dataset.py` → `run_predictive_research.py` →
  `render_predictive_report.py` flags.
- As the maintainer, I can start the existing BTC futures dry-run from the
  same CLI I use for research, with one config file instead of a separate
  invocation pattern.

## Open questions

- Exact CLI framework (`click`/`typer`/stdlib `argparse` subcommands) —
  architect decision, likely an ADR given it's a new cross-cutting
  dependency.
- Where `trading-cli` physically lives: a new `apps/cli` package (consistent
  with ADR-0022's `apps/*` consumer-boundary convention) vs. a `scripts/cli/`
  entry point. Leans `apps/cli` since it's a genuine deployable consumer, but
  needs the same "no research-engine internals reimplemented" boundary check
  ADR-0022 already applies to `apps/dashboard`.
- Exact shared YAML schema across the four command groups (how much is
  common vs. per-command) — architect design.
- Precise credential storage location (`user_data/config/binance.yaml` vs.
  an environment variable) — must land on one convention, never both,
  documented once.

## Handoff

Architect: design the Binance ingestion (dataset registry integration, REST
pagination/backoff, mode-selector shape) and the CLI (command structure, YAML
schema, `apps/cli` vs. `scripts/` placement, credential handling) as a Wave 0
decision set before implementation starts, per `docs/planning/PROJECT_MANAGEMENT.md`
conventions this project already follows.
