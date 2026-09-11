# Trading Research Dashboard

Read-only Streamlit application for presenting a sanitized, immutable public
projection of persisted research evidence. Production never mounts the private
research workspace into the long-running dashboard container.

This package is intentionally **separate** from `trading-framework`: it must not
import research engines, execution, or market-data providers (Sprint 028 /
`S028_WAVE0_DECISIONS.md`).

## Run locally

Prefer syncing from the **repository root** (uv workspace member). The committed
projection is used automatically:

```powershell
cd <repo-root>
uv sync --all-packages
cd apps/dashboard
uv run --package trading-dashboard streamlit run Project_Overview.py
```

Or from this directory after a root workspace sync:

```powershell
cd apps/dashboard
uv run streamlit run Project_Overview.py
```

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
`docs/reference/modules/DASHBOARD_APPLICATION.md` for architecture notes.

## Quality gates

From the repository root, `uv run mypy` covers framework code and tests plus
`apps/dashboard/src`, every Streamlit page, and `scripts/dashboard`. The
pre-push hook runs both the framework and dashboard pytest suites. CI repeats
the dashboard Ruff and pytest checks in its dedicated dashboard job.
