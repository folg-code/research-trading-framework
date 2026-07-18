# Trading Research Dashboard

Read-only Streamlit + DuckDB application for browsing research artifacts under a
workspace root (`market_data/` + `research/`).

This package is intentionally **separate** from `trading-framework`: it must not
import research engines, execution, or market-data providers (Sprint 028 /
`S028_WAVE0_DECISIONS.md`).

## Run locally

Prefer syncing from the **repository root** (uv workspace member):

```powershell
cd <repo-root>
uv sync --all-packages
cd apps/dashboard
$env:DASHBOARD_STORAGE_ROOT = (Resolve-Path ..\..\user_data).Path
uv run --package trading-dashboard streamlit run app.py
```

Or from this directory after a root workspace sync:

```powershell
cd apps/dashboard
$env:DASHBOARD_STORAGE_ROOT = (Resolve-Path ..\..\user_data).Path
uv run streamlit run app.py
```

Or paste the storage root path in the sidebar.

## Layout

```text
apps/dashboard/
  app.py
  pages/
  src/dashboard_app/
  deploy/
    Dockerfile
    docker-compose.yml
    Caddyfile
  docs/RUNBOOK.md
  tests/
```

See `docs/RUNBOOK.md` for Compose + read-only storage mount, and
`docs/reference/DASHBOARD_APPLICATION.md` for architecture notes.
