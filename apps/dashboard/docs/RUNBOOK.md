# Dashboard deploy runbook

Read-only Streamlit dashboard over a sanitized public projection, plus optional
Live Paper status from the dry-run status API. The private research workspace is
mounted only into a short-lived generation container and never into Streamlit.

**Primary UI:** `apps/dashboard` (Streamlit).  
**Legacy:** HTML demo artifacts under `artifacts/demo/` and
`scripts/portfolio_live/` (aiohttp) — keep for reference; new polish goes here.

## Local Compose

From the repository root, generate and select an immutable release, then start
the dashboard:

```powershell
$env:DASHBOARD_STORAGE_HOST_PATH = (Resolve-Path user_data\workspace).Path
$env:DASHBOARD_RESEARCH_HOST_PATH = (Resolve-Path user_data\research).Path
$env:DASHBOARD_PUBLICATION_HOST_ROOT = (Resolve-Path artifacts).Path + "\dashboard-publication"
$env:DASHBOARD_PUBLICATION_RELEASE_ID = "local-001"
$env:DASHBOARD_HTTP_PORT = "8080"
bash scripts/dashboard/deploy_public_dashboard.sh
```

Open `http://localhost:8080`.

Only the selected release directory (`projection.json` plus its validated
study manifests) is mounted **read-only** at
`/opt/dashboard/publication_data`.
`DASHBOARD_STATUS_URL` is passed into the container for Live Paper (optional;
when configured).

## Live Paper status URL

`deploy/docker-compose.yml` now runs the dry-run worker and status service as
Compose services (`dry-run-worker`, `dry-run-status`) on internal-only
networks, and defaults `DASHBOARD_STATUS_URL` to
`http://dry-run-status:8090/status` — the internal Compose DNS name, never a
public URL. Override only if pointing at a different (e.g. AWS Lambda) status
endpoint. The dashboard **never** writes to execution storage or starts the
worker.

Operator check: `GET` the URL in a browser — expect JSON with `"simulated": true`
and a fresh `last_heartbeat_at` when the worker is running.

## Health

- Streamlit: `GET /_stcore/health` on port 8501
- Compose `healthcheck` waits for that endpoint before starting Caddy
- `dry-run-worker`: no HTTP endpoint; liveness is heartbeat freshness of its
  own persisted execution state, checked in-container
  (`scripts/execution/vps_worker_healthcheck.py`)
- `dry-run-status`: `GET /healthz` on the internal `status` network only
  (never published) — reports process liveness and state-volume readability,
  not whether the worker is running

### Dry-run worker: exhausted restart retries

`dry-run-worker` and `dry-run-status` restart with a **bounded** policy
(`on-failure` with a capped attempt count, ADR-0036 section 4.6) rather than
an unbounded `unless-stopped` loop, so a deterministic configuration problem
becomes visible instead of hiding behind an invisible crash loop.

If `docker compose ps` shows `dry-run-worker` **Exited** (not restarting) or
repeatedly cycling `Restarting`/`Exited` with no `Up (healthy)` state:

1. Check the exit reason first: `docker compose logs dry-run-worker --tail 50`.
   - Exit code `2` — refuse-to-start: persisted state is incompatible with the
     current configuration (ADR-0036 section 4.4). Fix the configuration to
     match the persisted state, or deliberately reset by removing/renaming the
     runtime's directory in the `dry_run_execution_state` volume (an explicit
     operator action — never automatic).
   - Exit code `1` — a configuration error or unrecoverable runtime failure;
     the log line names the problem without any container path or secret.
2. Fix the underlying cause (env var, network reachability to Binance, or the
   state reset above), then restart explicitly:
   `docker compose up -d dry-run-worker`.
3. The public status card reflects this too: once retries are exhausted the
   worker stops writing heartbeats, so the card shows a stale/offline state
   rather than a silently frozen "current" snapshot — the dashboard itself
   stays up throughout (it does not depend on the worker or status service
   being healthy).

This is a short operational note; the full provider-neutral deploy/rollback
runbook is written in a later sprint task.

## VPS publish

1. On the VPS, clone/pull this repository.
2. Sync the private workspace to a host path accessible to the deploy user.
3. Create a separate publication root. Releases are append-only directories;
   `CURRENT` is an atomically replaced release-id pointer.
4. Export env and run the deployment helper from the repository root:

```bash
export DASHBOARD_STORAGE_HOST_PATH=/var/lib/trading-research/workspace
export DASHBOARD_RESEARCH_HOST_PATH=/var/lib/trading-research/research
export DASHBOARD_PUBLICATION_HOST_ROOT=/var/lib/trading-dashboard/publication
export DASHBOARD_PUBLICATION_RELEASE_ID="$(git rev-parse HEAD)-manual-1"
export DASHBOARD_HTTP_PORT=8080
scripts/dashboard/deploy_public_dashboard.sh
```

5. Prefer binding Compose Caddy to localhost/`DASHBOARD_HTTP_PORT` (default
   `8080`) and terminate TLS on a **shared VPS edge** (e.g. `/opt/edge`), not
   inside another application Compose stack.
6. Do **not** mount the research workspace into the dashboard container. The
   deploy helper gives it only to the one-shot generator as read-only input.
7. A failed generation or schema validation leaves `CURRENT` unchanged. A
   release id is never overwritten; retry with a new id.
8. Live Paper stale heartbeat: fix the **runtime worker**, not the dashboard.

### Public hostname (ops)

Production URL pattern: `https://dashboard.<domain>` → edge reverse-proxy →
`127.0.0.1:8080` (this Compose Caddy). Edge lives outside this repository
(shared with other apps on the same VPS). Dashboard CI/CD only rebuilds the
Compose stack on `:8080`; it does not manage edge TLS.

## CI/CD (GitHub → VPS)

After the one-time VPS prep below, merges to `main` that touch
`apps/dashboard/**` (or `.github/workflows/deploy-dashboard.yml`) run
**Deploy dashboard** (`.github/workflows/deploy-dashboard.yml`). The job SSHs
to the VPS, hard-resets the deploy checkout to `origin/main`, builds the image,
generates and validates a uniquely versioned projection, atomically selects it,
and then recreates Compose. Keep Caddy published on host `:8080`
so the shared edge proxy (`172.17.0.1:8080`) can reach it; do not enable
`docker-compose.vps.yml` (loopback-only) with that edge setup.

Private workspace sync is **not** part of this pipeline and remains
operator-managed. The deployment reads the paths below from the VPS-local
`apps/dashboard/.env`; those values are not GitHub secrets and are never copied
into the public bundle.

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
6. Put deployment env in `apps/dashboard/.env` (never commit it — copy
   `apps/dashboard/.env.example` as a starting point):
   `DASHBOARD_STORAGE_HOST_PATH`, `DASHBOARD_RESEARCH_HOST_PATH`,
   `DASHBOARD_PUBLICATION_HOST_ROOT`, optional
   `DASHBOARD_STATUS_URL`, and `DASHBOARD_HTTP_PORT`.
7. Confirm a manual start works:

```bash
cd "$DASHBOARD_VPS_REPO_PATH"
export DASHBOARD_PUBLICATION_RELEASE_ID="$(git rev-parse HEAD)-manual-1"
set -a; . apps/dashboard/.env; set +a
scripts/dashboard/deploy_public_dashboard.sh
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
