# Research Dashboard Application (Sprint 028)

> Moved from `docs/reference/DASHBOARD_APPLICATION.md` to
> `docs/reference/modules/DASHBOARD_APPLICATION.md` by Sprint 054 T008
> (`docs/reference` system/workflows/runbooks/modules split). Content
> unchanged.

Read-only Streamlit consumer of a versioned, immutable public projection.

## Boundary

```text
private workspace (build/deploy time only)
  → deny-by-default publication generator
  → immutable public projection release (read-only)
  → Streamlit pages in apps/dashboard
```

Must **not** import `trading_framework.research` engines, execution, or providers.
Optional shared presentation DTOs live inside `dashboard_app.contracts`.
The import-boundary test (`tests/unit/test_apps_boundaries.py`) scans both
`apps/dashboard/src/` and `apps/dashboard/pages/*.py` (Sprint 059 T003,
PRB-022) — a page file is checked exactly like a `src/` module.

## Public portfolio publication boundary (ADR-0034 / ADR-0035)

A strict publication boundary defines the public portfolio path:
`Project_Overview.py`, pages 1–6, the Signal Quality pages 7–9, the
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
scan. The legacy scanner and its `storage_path`-carrying contracts
(`RunSummary`, `PredictiveDatasetSummary`, `PredictiveRunSummary`) remain for
non-public compatibility tests, but pages 1–6 no longer import them or require
workspace access. Live Paper uses only its read-only HTTP status source.

ADR-0035 extends the same `dashboard.public.v1` bundle additively. Every
safely identifiable Market, Signal, Strategy, Robustness and Predictive run
receives one `research_catalog_entry`. Its deterministic artifact id is
`catalog-<workflow>-<run-id>`; duplicate, unsupported or path-like identities
fail or are skipped before sanitization. Missing persisted verdicts stay absent
so the UI can show `NO VERDICT` without inference. The build-time
`scripts/dashboard/generate_public_projection.py` command can append these
entries to the committed study fixture and writes atomically to an explicit
output path. Sprint 061 T007 adds immutable production releases under a host
publication root. Generation validates a candidate before atomically replacing
the `CURRENT` release-id pointer; an existing release is never overwritten.

## Projection-backed Research Catalog (Sprint 061 T006)

`pages/1_Research_Catalog.py` loads the immutable projection and
version-controlled study manifests through `publication.catalog_index`. It
does not require `DASHBOARD_STORAGE_ROOT`, import the scanner or display a
filesystem path. The reader re-applies the catalog sanitizer and rejects a
bundle entry containing any non-allowlisted field.

The hierarchy follows ADR-0035 exactly. A manifest explicitly claims catalog
artifact ids first. Every remaining run is grouped by workflow and DatasetRef,
then by persisted `experiment_id` (or `run_id` when absent). Automatic groups
are labelled `no editorial study manifest`; a missing persisted verdict is
shown as `NO VERDICT` and is never derived from metrics. The committed demo
bundle contains seven path-free real-workspace entries; production generation
and immutable release selection are implemented by the T007 release workflow.

## Projected workflow evidence (Sprint 061 T006)

Pages 2–4 consume `PublicCatalogIndex` and the allowlisted projection instead
of `DashboardQueryService`, runtime Parquet reads or scanner summaries. The
build-time publisher may read persisted Parquet analytics, but the serving
application receives only JSON-safe projected rows.

- Market Data shows one persisted DatasetRef, timeframe and research range
  exactly as referenced by the latest projected run. It does not open or chart
  private OHLCV storage.
- Signal Research publishes all three persisted historical runs through the
  explicit `signal_research_evidence` role. The page restores summary,
  grouped, distribution, conditional-comparison, histogram, warning and join
  diagnostics tables plus the two persisted-fact charts.
- Strategy Research shows one selected projected run plus the existing
  `strategy_research_run_summary` fields when that role is available. It does
  not run the backtester or derive rankings/verdicts.
- Robustness Research exposes the historical `demo-robustness-nq-half-year`
  experiment through an explicit `robustness_research_evidence` role, labelled
  `DEMO · LEGACY`. It restores the persisted verdict, walk-forward, parameter
  sweep, stress and Monte Carlo views. Its large equity series is projected as
  a deterministic ordered 1,200-point presentation sample retaining both
  endpoints. The role is not a catalog entry, so it remains excluded from
  Strategy Research/catalog grouping.

`views.workflow_evidence` owns the catalog selectors, while
`views.projected_research` reconstructs read-only Arrow tables from the
allowlisted JSON rows. Missing projected roles still render explicit unavailable
states; the UI never substitutes another workflow's evidence.

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

## Live Paper / Strategy Execution evidence (Sprints 031, 061)

Page: `pages/5_Live_Paper_Trading.py` with helpers in `dashboard_app.views.live_paper`.

- Configure `DASHBOARD_STATUS_URL` (falls back to `DEFAULT_LIVE_PAPER_STATUS_URL`).
- Shows the mandatory live-data/simulated-execution/no-real-orders banner,
  stale-heartbeat warning and one representative bounded market/position view.
- `sanitize_public_live_paper_snapshot` applies a fixed allowlist. Raw status,
  orders, events, error details and unknown API fields are not rendered.
- Dashboard only GETs the status API — it never starts the worker or submits
  orders. When the endpoint is absent, no stale snapshot is substituted.
- See `docs/reference/runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md` and `apps/dashboard/docs/RUNBOOK.md`.

## Predictive Research evidence (Sprints 044, 061)

Page: `pages/6_Predictive_Research.py` resolves the representative run named by
the Signal Quality study manifest. It renders one projected catalog identity,
the allowlisted persisted fold/pooled ROC AUC comparison and the persisted
analyst verdict.

- It never scans `research/predictive_research/`, opens `report.html`, or
  constructs a path from a projected identity.
- It never deserializes `models/fold_*.bin`; never imports
  `trading_framework.research`, `trading_framework.application.predictive_research`,
  `sklearn`, `xgboost` or `torch` — enforced by
  `tests/unit/test_apps_boundaries.py`.
- Other projected predictive runs remain discoverable in Research Catalog;
  deeper leaderboards, importance and calibration views are outside the one
  representative-view limit accepted in D061-04.

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
`docs/archive/phases/phase-16-research-workbench/SPRINT_060_T001_FIELD_INVENTORY.md`.

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
  projection-backed `pages/6_Predictive_Research.py` and
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
- Public pages do not accept or require `DASHBOARD_STORAGE_ROOT`. The private
  workspace is available only to the one-shot release generator and is never
  mounted into the serving container.
- The two Future Ideas are explicitly non-as-built. The AI page treats the
  maintainer's Polish direction note as editorial input and publishes English
  copy; the Research Application page remains subordinate to the Draft product
  vision. Neither page approves a provider, UI stack, architecture or sprint.
- `apps/dashboard/tests/test_sprint061_content.py` validates source links,
  maturity, mandatory disclaimers, Home cardinality and section order.

## Adding a page

1. Add `pages/N_Name.py` using `configure_page` + `render_app_chrome`.
2. Read facts through `dashboard_app.publication` and version-controlled content.
3. Keep engines, scanners, filesystem paths and private-workspace configuration
   out of the page.
4. Live operational views may use an explicitly configured read-only HTTP
   status source; research pages use only the selected public release.

## Enforced quality boundary (Sprint 061 T007)

- Root `uv run mypy` includes dashboard source, pages and
  `scripts/dashboard`; Streamlit's untyped cache decorator has the sole scoped
  dashboard override.
- The pre-push hook runs both framework pytest and the dashboard package test
  suite; CI retains its dedicated dashboard job.
- `tests/unit/test_apps_boundaries.py` scans publication generators separately
  and rejects any `trading_framework.*`, scikit-learn, XGBoost or Torch import.

## Adding an overlay renderer

1. Register a kind on `OverlayKind` in `dashboard_app.charts.overlays`.
2. Provide a renderer or leave `implemented=False` as a placeholder (orderflow).
3. Call `OverlayRegistry.apply(figure, kind, payload)` from chart builders.

## Publishing runs to a VPS

1. Produce research artifacts locally or on a trusted worker.
2. Run `scripts/dashboard/deploy_public_dashboard.sh`; its one-shot generator
   reads the private workspace through a read-only build-time mount, validates a
   new immutable release and atomically advances `CURRENT`.
3. Follow `apps/dashboard/docs/RUNBOOK.md`; the serving container mounts only
   the selected public release read-only and listens on `:8080`.
4. App code deploy: merges to `main` under `apps/dashboard/**` trigger
   `.github/workflows/deploy-dashboard.yml` (SSH → `git pull --ff-only` →
   `docker compose up --build -d`). Secrets and VPS prep are documented in the
   RUNBOOK **CI/CD** section.
5. Public TLS for the dashboard hostname belongs to a shared VPS edge proxy
   (outside this repo), not to another application Compose stack.

## Legacy query cache / size limits

The scanner/query compatibility layer retains storage-fingerprint cache keys,
windowed OHLCV reads (`max_bars=5000`) and capped generic Parquet reads
(`max_parquet_rows=50_000`). These controls are not part of the public render
path, which reads the bounded immutable projection.
