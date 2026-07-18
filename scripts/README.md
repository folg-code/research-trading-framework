# Scripts

Thin CLIs over `trading_framework.application` use cases. Prefer calling
application APIs from these entry points rather than embedding domain logic.

| Folder | Purpose |
|--------|---------|
| `databento/` | Databento archive download / import helpers |
| `market_data/` | Continuous futures, derived bars, half-year backtests |
| `signal_research/` | Signal / model research runners and reports |
| `strategy_research/` | Strategy research runners and HTML dashboard export |
| `robustness_research/` | Robustness experiment runners and reports |
| `demo/` | Portfolio / marketing demo HTML generation → `artifacts/demo/output/` |
| `execution/` | Dry-run / execution operator CLIs |
| `live_data/` | Live feed smoke helpers |
| `portfolio_live/` | Portfolio live / dry-run dashboard server |
| `ops/` | Workspace migration, dashboard analytics backfill, maintenance |

Layout rules: **ADR-0022**. Containers and local AWS runbooks live under
`deploy/` (or `apps/<app>/deploy/`), not under `scripts/`.
