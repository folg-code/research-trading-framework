# Portfolio demo

Offline HTML artifacts for showcasing research workflows and dashboards.

## Quick start

```powershell
uv pip install plotly
uv run python scripts/demo/run_portfolio_demo.py --full --open
```

Output: `demo/output/index.html` (landing page with links to all reports).

## What gets generated

| Artifact | Workflow | Notes |
|----------|----------|-------|
| `00_strategy_dashboard_nq_half_year.html` | Continuous NQ → strategy simulation → dashboard | **Hero demo** — 177k bars, Lightweight Charts, 12 KPIs. ~55 MB (embedded bars). Requires `user_data/storage_nq_half_year`. |
| `01_strategy_dashboard_fixture.html` | Same pipeline on committed CSV fixture | Fast, small — good for CI/screenshots. |
| `02_signal_research_analytics.html` | Signal Research → analytics report | Grouped metrics, conditional context. |
| `03_combined_research_inspection.html` | MARKET_AND_SIGNAL drill-down | MFE/MAE outcome window. |
| `04_model_inspection.html` | Declarative model overlays | Market + signal conditions on OHLCV. |
| `05_signal_occurrence_inspection.html` | Single occurrence inspection | |
| `06_mtf_swing_inspection.html` | MTF swing structure | RTH shading, event panel. |

## Portfolio tips

1. **Lead with** `00_strategy_dashboard_nq_half_year.html` — shows full platform depth (data → analysis → simulation → dashboard).
2. **Screenshots**: Overview KPIs, equity curve, trade markers on chart, monthly PnL panel.
3. **Narrative** (one slide): three workflows — *Signal Research* (edge discovery), *Strategy Research* (PnL simulation), *Market Analysis* (reusable components).
4. **Hosting**: upload `demo/output/` to static hosting; omit `00_*.html` if size is an issue and link to screenshots instead.
5. **Regenerate** half-year run: `--refresh-half-year` (re-runs `run_half_year_backtest.py`).

## Flags

```text
--full              Include NQ half-year strategy dashboard
--refresh-half-year Re-run strategy research before rendering
--skip-plotly       Strategy dashboards only (no Plotly reports)
--output-dir PATH   Custom output directory
```
