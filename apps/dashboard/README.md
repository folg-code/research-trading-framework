# Trading Research Dashboard

Read-only Streamlit + DuckDB application for browsing research artifacts under a
workspace root (`market_data/` + `research/`).

This package is intentionally **separate** from `trading-framework`: it must not
import research engines, execution, or market-data providers (Sprint 028 /
`S028_WAVE0_DECISIONS.md`).

## Run locally

From the repository root:

```bash
cd apps/dashboard
uv sync
set DASHBOARD_STORAGE_ROOT=..\..\user_data
uv run streamlit run app.py
```

PowerShell:

```powershell
cd apps/dashboard
uv sync
$env:DASHBOARD_STORAGE_ROOT = (Resolve-Path ..\..\user_data).Path
uv run streamlit run app.py
```

Or paste the storage root path in the sidebar.

## Layout

```text
apps/dashboard/
  app.py                 # home
  pages/                 # Streamlit multipage placeholders
  src/dashboard_app/     # config + shared UI helpers
  tests/
```

Presentation contracts (`RunSummary`, `ChartWindow`, `TradeView`, …), the
filesystem run catalog (`list_runs`), and `DashboardQueryService` (DuckDB windowed
OHLCV + Parquet column projection) live under `src/dashboard_app/`.

Strategy / research page UIs land in later Sprint 028 PRs.
