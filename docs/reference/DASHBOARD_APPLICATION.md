# Research Dashboard Application (Sprint 028)

Read-only Streamlit + DuckDB consumer of persisted research artifacts.

## Boundary

```text
mounted workspace (market_data/ + research/)
  → DashboardQueryService (DuckDB / Parquet)
  → Streamlit pages in apps/dashboard
```

Must **not** import `trading_framework.research` engines, execution, or providers.
Optional shared presentation DTOs live inside `dashboard_app.contracts`.

## Contracts

| Type | Role |
|------|------|
| `RunSummary` / `RunManifest` | Catalog + identity envelope |
| `ChartWindow` | Bounded OHLCV request |
| `TradeView` | Strategy trade markers/table |
| `HistoricalRunDataSource` | Historical Parquet source protocol |
| `AwsDryRunDataSource` | Protocol for live paper status |
| `HttpAwsDryRunDataSource` | GET-only client (`DASHBOARD_STATUS_URL`) |
| `UnimplementedAwsDryRunDataSource` | Raises until a status URL is configured |

Schema version: `dashboard.presentation.v1`.

## Live Paper (Sprint 031 / 025)

Page: `pages/5_Live_Paper.py` with helpers in `dashboard_app.views.live_paper`.

- Configure `DASHBOARD_STATUS_URL` or the sidebar (falls back to `DEFAULT_LIVE_PAPER_STATUS_URL`).
- Shows simulated banner, stale-heartbeat warning, candlestick from `recent_bars`, fill markers.
- Dashboard only GETs the status API — never starts the worker or submits orders.
- See `docs/reference/LIVE_PAPER_PIPELINE_INSPECTION.md` and `apps/dashboard/docs/RUNBOOK.md`.

## Adding a page

1. Add `pages/N_Name.py` using `configure_page` + `render_sidebar_storage_root`.
2. Prefer `DashboardQueryService` / catalog helpers over ad-hoc filesystem walks.
3. Use `dashboard_app.caching.streamlit.cached_*` helpers with `storage_fingerprint` for expensive reads.
4. Keep engines out of the page — only read mounted artifacts (or read-only HTTP status).

## Adding an overlay renderer

1. Register a kind on `OverlayKind` in `dashboard_app.charts.overlays`.
2. Provide a renderer or leave `implemented=False` as a placeholder (orderflow).
3. Call `OverlayRegistry.apply(figure, kind, payload)` from chart builders.

## Publishing runs to a VPS

1. Produce research artifacts locally (or on a worker) under a workspace root.
2. Optionally run `scripts/ops/backfill_dashboard_analytics_parquet.py` for older runs.
3. Rsync the workspace to the VPS host path used by Compose.
4. Follow `apps/dashboard/docs/RUNBOOK.md` (read-only mount + Caddy).

## Cache / size limits

- Streamlit cache keys include a storage fingerprint (top-level `research/` / `market_data/` mtimes).
- OHLCV reads are windowed with `max_bars` (default 5000).
- Generic Parquet reads are capped by `max_parquet_rows` (default 50_000).
