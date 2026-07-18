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
uv run --package trading-dashboard streamlit run Project_Overview.py
```

Or from this directory after a root workspace sync:

```powershell
cd apps/dashboard
$env:DASHBOARD_STORAGE_ROOT = (Resolve-Path ..\..\user_data).Path
uv run streamlit run Project_Overview.py
```

Or paste the storage root path in System diagnostics (local only).

## Layout

```text
apps/dashboard/
  Project_Overview.py
  pages/
  src/dashboard_app/
  deploy/
    Dockerfile
    docker-compose.yml
    Caddyfile
  docs/RUNBOOK.md
  docs/ARCHITECTURE.md
  tests/
```

See `docs/RUNBOOK.md` for Compose + read-only storage mount,
`docs/ARCHITECTURE.md` for the public architecture one-pager, and
`docs/reference/DASHBOARD_APPLICATION.md` for architecture notes.
