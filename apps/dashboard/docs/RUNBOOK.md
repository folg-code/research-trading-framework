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

4. Prefer binding Compose Caddy to localhost/`DASHBOARD_HTTP_PORT` (default
   `8080`) and terminate TLS on a **shared VPS edge** (e.g. `/opt/edge`), not
   inside another application Compose stack.
5. Do **not** mount writable research output into the dashboard container.
6. After new research runs, refresh the browser; Overview cache keys use a storage
   fingerprint and invalidate when top-level `research/` / `market_data/` mtimes change.
7. Live Paper stale heartbeat: fix the **AWS worker**, not the dashboard.

### Public hostname (ops)

Production URL pattern: `https://dashboard.<domain>` → edge reverse-proxy →
`127.0.0.1:8080` (this Compose Caddy). Edge lives outside this repository
(shared with other apps on the same VPS). Dashboard CI/CD only rebuilds the
Compose stack on `:8080`; it does not manage edge TLS.

## CI/CD (GitHub → VPS)

After the one-time VPS prep below, merges to `main` that touch
`apps/dashboard/**` (or `.github/workflows/deploy-dashboard.yml`) run
**Deploy dashboard** (`.github/workflows/deploy-dashboard.yml`). The job SSHs
to the VPS, fast-forward pulls `main`, then rebuilds Compose.

`user_data` / storage sync is **not** part of this pipeline — mount and sync
remain operator-managed.

### GitHub secrets

Configure these on the repository (Settings → Secrets and variables → Actions).
Prefer attaching them to the `dashboard-vps` Environment (the workflow uses it).

| Name | Purpose |
|------|---------|
| `DASHBOARD_VPS_HOST` | VPS hostname or IP |
| `DASHBOARD_VPS_USER` | SSH user that can `git pull` and run Docker Compose |
| `DASHBOARD_VPS_SSH_KEY` | Private key for that user (deploy-only; never commit). Paste the
  full OpenSSH private key including `BEGIN`/`END` lines and keep newlines.
  Do not paste the `.pub` file. Prefer Environment secrets on `dashboard-vps`. |
| `DASHBOARD_VPS_PORT` | SSH port (use `22` if default) |
| `DASHBOARD_VPS_REPO_PATH` | Absolute path to the repo clone on the VPS |

### One-time VPS prep

1. Install Docker Engine + Compose plugin.
2. Clone this repository to `DASHBOARD_VPS_REPO_PATH` and check out `main`.
3. Ensure the deploy user can `git pull --ff-only origin main` (deploy key or
   machine credentials with read access).
4. Add the deploy user to the `docker` group (or equivalent) so Compose runs
   without interactive sudo.
5. Create a deploy-only SSH keypair; put the **public** key in that user's
   `authorized_keys`; store the **private** key only as `DASHBOARD_VPS_SSH_KEY`.
6. Put Compose env next to the app (shell profile, systemd, or
   `apps/dashboard/.env` that is **not** committed), e.g.
   `DASHBOARD_STORAGE_HOST_PATH`, `DASHBOARD_STATUS_URL`, `DASHBOARD_HTTP_PORT`.
7. Confirm a manual start works:

```bash
cd "$DASHBOARD_VPS_REPO_PATH/apps/dashboard"
docker compose -f deploy/docker-compose.yml up --build -d
```

### Force redeploy

GitHub → Actions → **Deploy dashboard** → **Run workflow**.

If `git pull --ff-only` fails, the remote tree is dirty or diverged — fix on
the VPS before retrying.

### SSH auth troubleshooting

If Actions fails with `unable to authenticate` / `publickey`:

1. Confirm the secret is the **private** key (`dashboard_deploy`), not `.pub`.
2. Re-paste the key into the Environment secret (full `BEGIN`/`END` block).
3. On the VPS, confirm the matching public line exists:

```bash
grep github-actions-dashboard ~/.ssh/authorized_keys
ssh-keygen -lf ~/.ssh/authorized_keys
```

4. From your laptop, key-only login must work without a password:

```powershell
ssh -i $HOME\.ssh\dashboard_deploy -o IdentitiesOnly=yes ubuntu@HOST "echo ok"
```

## Backfill Parquet sidecars

Existing pre-S028 runs may lack analytics Parquet. From the repo root:

```powershell
uv run python scripts/ops/backfill_dashboard_analytics_parquet.py --storage-root user_data
```
