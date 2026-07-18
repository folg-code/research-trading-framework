# Dashboard deploy runbook

Read-only Streamlit dashboard over a mounted research workspace, plus optional
Live Paper status from the AWS dry-run status API.

**Primary UI:** `apps/dashboard` (Streamlit).  
**Legacy:** HTML demo artifacts under `artifacts/demo/` and
`scripts/portfolio_live/` (aiohttp) — keep for reference; new polish goes here.

## Local Compose

From `apps/dashboard`:

```powershell
$env:DASHBOARD_STORAGE_HOST_PATH = (Resolve-Path ..\..\user_data).Path
$env:DASHBOARD_HTTP_PORT = "8080"
$env:DASHBOARD_STATUS_URL = "https://279rmuo95c.execute-api.eu-north-1.amazonaws.com/status"
docker compose -f deploy/docker-compose.yml up --build
```

Open `http://localhost:8080`.

Storage is mounted **read-only** at `/data` (`DASHBOARD_STORAGE_ROOT=/data`).
`DASHBOARD_STATUS_URL` is passed into the container for Live Paper (optional;
the app also has a built-in default).

## Live Paper status URL

Default (built into `dashboard_app.config.DEFAULT_LIVE_PAPER_STATUS_URL`):

```text
https://279rmuo95c.execute-api.eu-north-1.amazonaws.com/status
```

Override with env or the Streamlit sidebar. The dashboard **never** writes to
DynamoDB or starts the ECS worker.

Operator check: `GET` the URL in a browser — expect JSON with `"simulated": true`
and a fresh `last_heartbeat_at` when the worker is running.

## Health

- Streamlit: `GET /_stcore/health` on port 8501
- Compose `healthcheck` waits for that endpoint before starting Caddy

## VPS publish

1. On the VPS, clone/pull this repo (or deploy only `apps/dashboard` + compose).
2. Sync a workspace with `market_data/` and `research/` to a host path
   (e.g. `/var/lib/trading-dashboard/user_data`).
3. Export env and start Compose from `apps/dashboard`:

```bash
export DASHBOARD_STORAGE_HOST_PATH=/var/lib/trading-dashboard/user_data
export DASHBOARD_HTTP_PORT=8080
export DASHBOARD_STATUS_URL=https://279rmuo95c.execute-api.eu-north-1.amazonaws.com/status
docker compose -f deploy/docker-compose.yml up --build -d
```

4. Prefer binding Caddy to localhost and terminate TLS on an outer reverse proxy.
5. Do **not** mount writable research output into the dashboard container.
6. After new research runs, refresh the browser; Overview cache keys use a storage
   fingerprint and invalidate when top-level `research/` / `market_data/` mtimes change.
7. Live Paper stale heartbeat: fix the **AWS worker**, not the dashboard.

## Backfill Parquet sidecars

Existing pre-S028 runs may lack analytics Parquet. From the repo root:

```powershell
uv run python scripts/ops/backfill_dashboard_analytics_parquet.py --storage-root user_data
```
