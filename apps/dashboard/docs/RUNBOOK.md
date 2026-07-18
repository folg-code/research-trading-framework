# Dashboard deploy runbook (Sprint 028)

Read-only Streamlit dashboard over a mounted research workspace.

## Local Compose

From `apps/dashboard`:

```powershell
$env:DASHBOARD_STORAGE_HOST_PATH = (Resolve-Path ..\..\user_data).Path
$env:DASHBOARD_HTTP_PORT = "8080"
docker compose -f deploy/docker-compose.yml up --build
```

Open `http://localhost:8080`.

Storage is mounted **read-only** at `/data` inside the container (`DASHBOARD_STORAGE_ROOT=/data`).

## Live Paper status URL

Default (built into `dashboard_app.config.DEFAULT_LIVE_PAPER_STATUS_URL`):

```text
https://279rmuo95c.execute-api.eu-north-1.amazonaws.com/status
```

Override with env or the Streamlit sidebar:

```powershell
$env:DASHBOARD_STATUS_URL = "https://<api-gateway>/status"
```

The dashboard never writes to DynamoDB or starts the ECS worker.

## Health

- Streamlit: `GET /_stcore/health` on port 8501
- Compose `healthcheck` waits for that endpoint before starting Caddy

## VPS notes

1. Sync or rsync a workspace that contains `market_data/` and `research/` to the host.
2. Set `DASHBOARD_STORAGE_HOST_PATH` to that directory.
3. Prefer binding Caddy to localhost + an outer reverse proxy / TLS terminator.
4. Do not mount writable research output into the dashboard container.
5. After new research runs, refresh the browser; Overview cache keys use a storage fingerprint and invalidate when top-level research/market_data mtimes change.

## Backfill Parquet sidecars

Existing pre-S028 runs may lack analytics Parquet. From the repo root:

```powershell
uv run python scripts/ops/backfill_dashboard_analytics_parquet.py --storage-root user_data
```
