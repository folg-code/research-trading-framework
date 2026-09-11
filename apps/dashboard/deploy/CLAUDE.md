# apps/dashboard/deploy

Responsibility: Compose stack and Dockerfile wiring for the VPS dashboard
deployment (dashboard, caddy, and — since Sprint 062 T004 — the BTC futures
dry-run worker and status service).

## Gotchas

- `docker-compose.yml` lives at `apps/dashboard/deploy/`. `dashboard`'s and
  `caddy`'s builds use `context: ..` (i.e. `apps/dashboard`), because
  `deploy/Dockerfile` only needs the dashboard app subtree. `dry-run-worker`
  and `dry-run-status` build from `deploy/vps/*/Dockerfile`, which reuse
  top-level `src/` and `scripts/` unchanged — those need `context: ../../..`
  (the repository root), **not** `../..`. Getting the `..` count wrong fails
  silently at `COPY src ./src` with a "not found" error deep in the build,
  not at `docker compose config` time.
- Validate the file with `docker compose -f deploy/docker-compose.yml config
  --quiet` before assuming a YAML edit is correct; `tests/unit/deploy/
  test_dashboard_docker_compose.py` also asserts the port/volume/network
  invariants ADR-0036 requires (no port on the worker, `expose`-only on the
  status service, read-only vs. read-write state-volume mounts, no state
  volume on `dashboard`).
