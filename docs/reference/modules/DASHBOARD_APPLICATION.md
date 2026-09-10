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

## Public portfolio publication boundary (ADR-0034 / ADR-0035)

A second, stricter boundary sits inside the one above, for the public
portfolio path: `Project_Overview.py`, the Signal Quality pages 7–9, the
version-controlled Architecture, Engineering, Future Direction and Notes
pages 10–15, and the workflow publications on pages 16–21 added by Sprint
061 T002–T004. See
`docs/adr/ADR-0034-portfolio-publication-boundary.md` for the full decision
record.

| Package | Role |
|---|---|
| `dashboard_app.publication` | A versioned, deny-by-default `PublicProjectionBundle` (`dashboard.public.v1`) built at build/deploy time from raw persisted artifacts, plus a dashboard-local `PortfolioStudyManifest` (`dashboard.study_manifest.v1`) grouping projected artifacts into a named study by explicit role. `publication.catalog` creates safe `research_catalog_entry` inputs; `publication.workspace` is the sole build-time private-workspace reader. Projected output never carries `storage_path` or any filesystem path. |
| `dashboard_app.content` | A hand-parsed frontmatter + restricted-Markdown content loader (`load_content_document`), required metadata (`slug`, `title`, `status`, `updated`, `order`, `links`), and a stable-slug routing contract (`is_valid_slug`, `resolve_query_slug`). Content files live under `apps/dashboard/content/*.md`, version-controlled like code. |

Both packages fail closed: every load/validate function returns an explicit
`...Unavailable` result (`PublicationUnavailable`, `ContentUnavailable`)
rather than raising into a page render or falling back to a raw workspace
scan. The existing catalog scanner and its `storage_path`-carrying contracts
(`RunSummary`, `PredictiveDatasetSummary`, `PredictiveRunSummary`) are
grandfathered for the existing technical pages (`pages/1-6_*.py`) until the
Sprint 061 T006 migration.

ADR-0035 extends the same `dashboard.public.v1` bundle additively. Every
safely identifiable Market, Signal, Strategy, Robustness and Predictive run
receives one `research_catalog_entry`. Its deterministic artifact id is
`catalog-<workflow>-<run-id>`; duplicate, unsupported or path-like identities
fail or are skipped before sanitization. Missing persisted verdicts stay absent
so the UI can show `NO VERDICT` without inference. The build-time
`scripts/dashboard/generate_public_projection.py` command can append these
entries to the committed study fixture and writes atomically to an explicit
output path. Production versioning and deployment selection remain T007.

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
- `SHARED_DOMAIN_MERMAID` shows the provider-adapter boundary, Market Data
  ending at a published `DatasetRef`, shared Market Analysis contracts,
  explicit `Market × Signal × Exit × Risk` strategy composition, independent
  workflow consumers, and workflow-owned persisted evidence. There is no edge
  from Market Data to a research result and no mandatory research pipeline
  (`docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` §3).
- `WORKFLOW_ENTRIES` names all six workflows (Market Data, Signal Research,
  Strategy Research, Robustness Research, Predictive Research, Strategy
  Execution) with a `StudyMaturity` badge each — reused from
  `dashboard_app.publication.manifest`, not a second enum. Each card opens a
  version-controlled workflow publication (`pages/16_*.py` through
  `pages/21_*.py`) explaining purpose, architecture, workflow, methodology
  and limits before linking to the existing technical evidence page. Strategy
  Execution is `IN_DEVELOPMENT` and limited to `DRY_RUN` per ADR-0021.

The Architecture page repeats the system map and documents every public-facing
module as consume/process/produce. It covers the Market Analysis dependency
DAG, cache identity, `available_at`/look-ahead controls, historical simulator,
ML/AI extension boundaries, persistence and publication.

## BTC Signal Quality study and evidence path (Sprint 060)

The first real consumer of the ADR-0034 publication boundary. Extends
`dashboard_app.publication.sanitizers` with three additive roles
(`predictive_run_metrics`, `predictive_threshold_sensitivity`,
`strategy_research_run_summary`), each a `frozenset` allowlist frozen by
`docs/planning/sprints/SPRINT_060_T001_FIELD_INVENTORY.md`.

- `scripts/dashboard/generate_btc_signal_quality_projection.py` reads the
  real Phase 16A–16C artifacts and writes the sanitized
  `PublicProjectionBundle`; its output,
  `apps/dashboard/publication_data/projection.json`, plus the
  hand-authored `apps/dashboard/publication_data/manifests/btc-signal-quality.json`
  (`PortfolioStudyManifest`), are committed to the repository rather than
  generated at deploy time (maintainer decision, Sprint 060 T003) — the
  dashboard renders this study without the private workspace mounted.
- `dashboard_app.views.study.render_btc_signal_quality_study` (page
  `pages/9_Signal_Quality_Study.py`) resolves the manifest against the
  bundle, renders the study content document
  (`apps/dashboard/content/btc-signal-quality-study.md`), the persisted
  verdict verbatim (`st.badge(..., color="gray")` — a fixed literal, never
  derived from the verdict text, D060-03), and the three accepted charts
  (`dashboard_app.charts.builders.build_signal_quality_*`). Every load step
  fails closed to an explicit `PublicationUnavailable`/`ContentUnavailable`
  warning, section by section — an absent optional artifact role degrades
  only its own chart, never the whole page.
- `dashboard_app.views.portfolio_content` renders the workflow-context
  (`pages/7_Signal_Quality_Workflow.py`) and methodology
  (`pages/8_Signal_Quality_Methodology.py`) content documents and links the
  evidence path: overview → workflow context → methodology → study (three
  navigation actions), then `Explore Evidence` from the study into the
  existing, grandfathered `pages/6_Predictive_Research.py` and
  `pages/3_Strategy_Research.py` (ADR-0034 §6) — linked, never duplicated.
- Contract tests (`apps/dashboard/tests/test_study_contract.py`, Sprint 060
  T005) assert traceability (every chart value equals a resolved artifact
  field verbatim, checked against both synthetic and the real committed
  bundle), that a non-`INCONCLUSIVE` verdict renders the same way, that an
  absent optional role degrades gracefully, and that the verdict badge's
  color is a source-level literal.

## Portfolio story and Future Direction (Sprint 061 T002–T004)

- Home now follows the portfolio sequence after its thesis and shared-domain
  map: six workflow entries, two real featured studies, three selected
  Research & Engineering Notes, exactly two `FUTURE IDEAS` cards, and the
  complete catalog entry.
- `views.overview` owns the small structural entry tuples and renders links;
  factual narrative remains in validated files under
  `apps/dashboard/content/`.
- `views.portfolio_content.render_static_content_page` provides the shared
  fail-closed renderer for stable Architecture, Engineering, Future Direction,
  AI Research Infrastructure, Research Application and Notes pages
  (`pages/10_*.py` through `pages/15_*.py`).
- `views.portfolio_content.render_workflow_publication` adds the publication
  layer for all six workflow cards (`pages/16_*.py` through `pages/21_*.py`):
  visitors read methodology and architecture before choosing `Explore
  Evidence` to enter a technical results/status page.
- Home and the Architecture/Market Data publications explain that the public
  BTCUSDT.P studies were chosen for accessible, high-quality OHLCV from a free
  public API. BTC is not an asset boundary; additional assets require an
  adapter and a validated, published `DatasetRef`.

## Catalog identity corrections (Sprint 061)

- A Strategy Research run carrying an `experiment_id` is treated as a nested
  child of its Robustness experiment and is omitted from top-level Strategy
  listings; the parent experiment remains the catalog entry.
- Run time ranges resolve from the immutable metadata of the referenced
  published DatasetRef. Predictive Dataset manifests expose their own explicit
  research time range. Both are displayed separately from timeframe.
- `DASHBOARD_STORAGE_ROOT` must name the actual workspace root. For the current
  development evidence this is `user_data/workspace`, not its parent
  `user_data`.
- The two Future Ideas are explicitly non-as-built. The AI page treats the
  maintainer's Polish direction note as editorial input and publishes English
  copy; the Research Application page remains subordinate to the Draft product
  vision. Neither page approves a provider, UI stack, architecture or sprint.
- `apps/dashboard/tests/test_sprint061_content.py` validates source links,
  maturity, mandatory disclaimers, Home cardinality and section order.

## Adding a page

1. Add `pages/N_Name.py` using `configure_page` + `render_app_chrome`.
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
