# Research Dashboard Application (Sprint 028)

> Moved from `docs/reference/DASHBOARD_APPLICATION.md` to
> `docs/reference/modules/DASHBOARD_APPLICATION.md` by Sprint 054 T008
> (`docs/reference` system/workflows/runbooks/modules split). Content
> unchanged.

Read-only Streamlit + DuckDB consumer of persisted research artifacts.

## Boundary

```text
mounted workspace (market_data/ + research/)
  → DashboardQueryService (DuckDB / Parquet)
  → Streamlit pages in apps/dashboard
```

Must **not** import `trading_framework.research` engines, execution, or providers.
Optional shared presentation DTOs live inside `dashboard_app.contracts`.
The import-boundary test (`tests/unit/test_apps_boundaries.py`) scans both
`apps/dashboard/src/` and `apps/dashboard/pages/*.py` (Sprint 059 T003,
PRB-022) — a page file is checked exactly like a `src/` module.

## Public portfolio publication boundary (ADR-0034, Sprint 059)

A second, stricter boundary sits inside the one above, for the public
portfolio path only (the refreshed `Project_Overview.py` today; more pages
in later 16D sprints). See `docs/adr/ADR-0034-portfolio-publication-boundary.md`
for the full decision record.

| Package | Role |
|---|---|
| `dashboard_app.publication` | A versioned, deny-by-default `PublicProjectionBundle` (`dashboard.public.v1`) built at build/deploy time from raw persisted artifacts, plus a dashboard-local `PortfolioStudyManifest` (`dashboard.study_manifest.v1`) grouping projected artifacts into a named study by explicit role. Never carries `storage_path` or any filesystem path. |
| `dashboard_app.content` | A hand-parsed frontmatter + restricted-Markdown content loader (`load_content_document`), required metadata (`slug`, `title`, `status`, `updated`, `order`, `links`), and a stable-slug routing contract (`is_valid_slug`, `resolve_query_slug`). Content files live under `apps/dashboard/content/*.md`, version-controlled like code. |

Both packages fail closed: every load/validate function returns an explicit
`...Unavailable` result (`PublicationUnavailable`, `ContentUnavailable`)
rather than raising into a page render or falling back to a raw workspace
scan. The existing catalog scanner and its `storage_path`-carrying contracts
(`RunSummary`, `PredictiveDatasetSummary`, `PredictiveRunSummary`) are
grandfathered for the existing technical pages (`pages/1-6_*.py`) — they are
not migrated onto the projection in this sprint.

## Contracts

| Type | Role |
|------|------|
| `RunSummary` / `RunManifest` | Catalog + identity envelope |
| `ChartWindow` | Bounded OHLCV request |
| `TradeView` | Strategy trade markers/table |
| `HistoricalRunDataSource` | Historical Parquet source protocol |
| `LivePaperStatusDataSource` | Protocol for live paper status |
| `HttpLivePaperStatusDataSource` | GET-only client (`DASHBOARD_STATUS_URL`) |
| `UnimplementedLivePaperStatusDataSource` | Raises until a status URL is configured |

Schema version: `dashboard.presentation.v1`.

## Live Paper (Sprint 031 / 025)

Page: `pages/5_Live_Paper_Trading.py` with helpers in `dashboard_app.views.live_paper`.

- Configure `DASHBOARD_STATUS_URL` or the sidebar (falls back to `DEFAULT_LIVE_PAPER_STATUS_URL`).
- Shows simulated banner, stale-heartbeat warning, candlestick from `recent_bars`, fill markers.
- Dashboard only GETs the status API — never starts the worker or submits orders.
- See `docs/reference/runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md` and `apps/dashboard/docs/RUNBOOK.md`.

## Predictive Research (Sprint 044)

Page: `pages/6_Predictive_Research.py` with helpers in
`dashboard_app.views.predictive` and `dashboard_app.catalog.predictive_quality`.

- Catalog scan reads `research/predictive_research/datasets/{dataset_id}/` and
  `research/predictive_research/runs/{run_id}/` — the same directory tree
  `scripts/predictive_research/*` writes (`docs/reference/workflows/RESEARCH_METHODOLOGIES.md` §8).
- Study picker → leaderboard (sorted by baseline delta, not the raw metric) →
  run detail (per-fold metrics, stability, buckets, calibration) → provenance
  (dataset fingerprint, estimator spec, seeds, library versions) → link to the
  offline `report.html`.
- Never deserializes `models/fold_*.bin`; never imports
  `trading_framework.research`, `trading_framework.application.predictive_research`,
  `sklearn`, `xgboost` or `torch` — enforced by
  `tests/unit/test_apps_boundaries.py`.
- Importance and calibration panels degrade gracefully when a run did not
  persist that sidecar file.

## Project Overview (Sprint 059 T005)

Entry page: `Project_Overview.py` with helpers in `dashboard_app.views.overview`.

- The product thesis is loaded from `apps/dashboard/content/portfolio-overview.md`
  through `dashboard_app.content.loader.load_content_document` — an absent or
  invalid content document renders an explicit `st.warning`, never a crash.
- `SHARED_DOMAIN_MERMAID` is a hub-and-spoke diagram: one shared node
  (Market Analysis, Time Model, Data Contracts) with six independent
  workflow spokes and no edges between workflow nodes — deliberately not a
  linear pipeline (`docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` §3).
- `WORKFLOW_ENTRIES` names all six workflows (Market Data, Signal Research,
  Strategy Research, Robustness Research, Predictive Research, Strategy
  Execution) with a `StudyMaturity` badge each — reused from
  `dashboard_app.publication.manifest`, not a second enum. Market Data has
  no page of its own today and shares `pages/2_Market_and_Signal_Research.py`
  with Signal Research; Strategy Execution is `IN_DEVELOPMENT` per
  ADR-0021 ("Strategy Execution remains a future capability").

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
3. Rsync the workspace to the VPS host path used by Compose (`user_data` sync is
   operator-managed — not part of CI/CD).
4. Follow `apps/dashboard/docs/RUNBOOK.md` (read-only mount + Compose on `:8080`).
5. App code deploy: merges to `main` under `apps/dashboard/**` trigger
   `.github/workflows/deploy-dashboard.yml` (SSH → `git pull --ff-only` →
   `docker compose up --build -d`). Secrets and VPS prep are documented in the
   RUNBOOK **CI/CD** section.
6. Public TLS for the dashboard hostname belongs to a shared VPS edge proxy
   (outside this repo), not to another application Compose stack.

## Cache / size limits

- Streamlit cache keys include a storage fingerprint (top-level `research/` / `market_data/` mtimes).
- OHLCV reads are windowed with `max_bars` (default 5000).
- Generic Parquet reads are capped by `max_parquet_rows` (default 50_000).
