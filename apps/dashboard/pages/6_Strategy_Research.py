"""Strategy Research — overview table and detailed run evidence."""

from __future__ import annotations

import plotly.express as px
import pyarrow as pa
import streamlit as st

from dashboard_app.formatting import format_kpi, humanize_dataset_ref, humanize_model_id
from dashboard_app.publication.paths import projection_bundle_path
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)
from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.projected_research import (
    ProjectedResearchEvidence,
    strategy_research_evidence,
)

_SUMMARY_KPI_KEYS = (
    "net_pnl",
    "total_return",
    "sharpe_ratio",
    "sortino_ratio",
    "profit_factor",
    "expectancy",
    "trade_count",
    "win_rate",
    "avg_win",
    "avg_loss",
    "total_costs",
    "max_drawdown",
    "current_drawdown",
)

configure_page(title="Strategy Research")
render_app_chrome()

st.title("Strategy Research Evidence")
st.caption(
    "Every persisted Strategy Research run for a complete Market x Signal x Exit x Risk "
    "composition. These are historical simulation facts, not live performance or deployment "
    "approval. Sorting or comparing a column never constructs a ranking, promotion or "
    "live-edge claim."
)

bundle = load_projection_bundle_from_path(projection_bundle_path())
if isinstance(bundle, PublicationUnavailable):
    st.warning("Published Strategy Research evidence is unavailable for this release.")
    st.stop()

runs = strategy_research_evidence(bundle)
if not runs:
    st.info("No safely projected Strategy Research run is included in this release.")
    st.stop()


def _overview_row(run: ProjectedResearchEvidence) -> dict[str, object]:
    fields = run.fields
    row: dict[str, object] = {
        "run_id": fields.get("run_id"),
        "strategy": humanize_model_id(fields.get("strategy_model_id")),
        "market model": humanize_model_id(fields.get("market_model_id")),
        "signal model": humanize_model_id(fields.get("signal_model_id")),
        "dataset": humanize_dataset_ref(fields.get("source_dataset_ref")),
        "timeframe": fields.get("evaluation_timeframe"),
        "initial capital": fields.get("initial_capital"),
        "commission (bps)": fields.get("commission_per_side"),
        "slippage (bps)": fields.get("slippage_bps"),
    }
    summary_table = run.table("summary_metrics")
    summary = summary_table.to_pylist()[0] if summary_table is not None else {}
    for key in _SUMMARY_KPI_KEYS:
        row[key] = summary.get(key)
    return row


st.subheader("Overview — every persisted run")
st.caption(
    "Material differences in dataset, instrument, capital and cost assumptions are visible "
    "beside the KPIs, not papered over. Click a column header to sort; a missing value sorts "
    "as unavailable, never as zero."
)
overview_table = pa.Table.from_pylist([_overview_row(run) for run in runs])
st.dataframe(overview_table.to_pandas(), use_container_width=True, hide_index=True)

st.divider()

st.subheader("Run detail")
run_by_id = {run.fields.get("run_id"): run for run in runs}
selected_id = st.selectbox(
    "Research run",
    options=list(run_by_id),
    format_func=lambda run_id: (
        f"{humanize_model_id(run_by_id[run_id].fields.get('strategy_model_id'))} · {run_id}"
    ),
    key="strategy_research_selected_run",
)
selected = run_by_id[selected_id]
fields = selected.fields

st.caption(
    "Every number below was copied from persisted analytics at publication time. The public "
    "application does not scan the research workspace, rerun the backtester or recompute "
    "metrics."
)

st.subheader("Backtest assumptions and provenance")
st.write(
    {
        "run": fields.get("run_id"),
        "dataset": fields.get("source_dataset_ref"),
        "timeframe": fields.get("evaluation_timeframe"),
        "strategy model": fields.get("strategy_model_id"),
        "market model": fields.get("market_model_id"),
        "signal model": fields.get("signal_model_id"),
        "exit model": fields.get("exit_model_id"),
        "risk model": fields.get("risk_model_id"),
        "fill policy (entry / exit)": (
            f"{fields.get('fill_policy_entry', '—')} / {fields.get('fill_policy_exit', '—')}"
        ),
        "slippage (bps)": fields.get("slippage_bps", "—"),
        "commission per side (bps)": fields.get("commission_per_side", "—"),
        "initial capital": fields.get("initial_capital", "—"),
        "strategy source": fields.get("strategy_source_ref", "unavailable"),
    }
)

st.subheader("KPI summary")
summary_table = selected.table("summary_metrics")
if summary_table is None:
    st.info("No allowlisted simulation summary is published for this run.")
else:
    summary_row = summary_table.to_pylist()[0]
    kpi_columns = st.columns(4)
    for index, key in enumerate(_SUMMARY_KPI_KEYS):
        kpi_columns[index % 4].metric(
            key.replace("_", " ").title(), format_kpi(key, summary_row.get(key))
        )
    st.caption(
        f"Absolute PnL and drawdown figures are in the run's initial-capital basis "
        f"({fields.get('initial_capital', 'unknown')}); total return is the separate, "
        "already-normalized measure."
    )

st.subheader("Simulated equity and drawdown")
equity_table = selected.table("equity_curve")
if equity_table is None or equity_table.num_rows == 0:
    st.info("No persisted equity curve is published for this run.")
else:
    equity_df = equity_table.to_pandas()
    st.plotly_chart(
        px.line(equity_df, x="observed_at", y="equity", title="Simulated equity"),
        use_container_width=True,
    )
    st.plotly_chart(
        px.area(equity_df, x="observed_at", y="drawdown", title="Drawdown"),
        use_container_width=True,
    )
    st.caption(
        "Actual persisted simulation series, downsampled to at most 2,000 points for "
        "publication — not an overlapping forward-return pseudo-equity curve."
    )

st.subheader("Trade outcome (PnL) distribution")
trades_table = selected.table("trades")
if trades_table is None or trades_table.num_rows == 0:
    st.info("No persisted trades are published for this run.")
else:
    trades_df = trades_table.to_pandas()
    st.plotly_chart(
        px.histogram(trades_df, x="net_pnl", title="Net PnL per trade"),
        use_container_width=True,
    )
    st.caption(
        f"{trades_df.shape[0]:,} persisted trades, full population (not a sample). Shown as "
        "net PnL per trade -- R-multiples are unavailable (no per-trade initial risk is "
        "persisted)."
    )

    st.subheader("Exit diagnostics")
    exit_counts = trades_df["exit_reason"].value_counts().reset_index()
    exit_counts.columns = ["exit_reason", "trade_count"]
    st.plotly_chart(
        px.bar(exit_counts, x="exit_reason", y="trade_count", title="Trades by exit reason"),
        use_container_width=True,
    )
    st.caption(
        "Counted directly from the persisted exit reason on each published trade -- a "
        "display tally over the complete population, not a derived research metric."
    )

st.subheader("Conditional expectancy by market context")
context_table = selected.table("context_expectancy")
if context_table is None or context_table.num_rows == 0:
    st.info(
        "No categorical market-context component is available for this run's Market Model "
        "-- this is not an error, just nothing to show."
    )
else:
    st.dataframe(context_table.to_pandas(), use_container_width=True, hide_index=True)
    st.caption(
        "A group's `net_pnl_mean`/`net_pnl_median`/`win_rate` are null when `eligible` is "
        "false (too few trades) -- never a fabricated value."
    )

st.subheader("Drawdown structure")
episodes_table = selected.table("drawdown_episodes")
if episodes_table is None or episodes_table.num_rows == 0:
    st.info("No drawdown episode is published for this run (equity never dipped below its peak).")
else:
    episodes_df = episodes_table.to_pandas()
    episodes_df["recovery_bars"] = episodes_df["recovery_bars"].astype("Int64")
    st.dataframe(episodes_df, use_container_width=True, hide_index=True)
    st.caption("A blank `recovery_bars` means the episode had not yet recovered by run end.")

st.subheader("Capital and exposure")
exposure_table = selected.table("exposure")
if exposure_table is None or exposure_table.num_rows == 0:
    st.info("No persisted exposure series is published for this run.")
else:
    exposure_df = exposure_table.to_pandas()
    st.plotly_chart(
        px.line(exposure_df, x="observed_at", y="exposure_ratio", title="Exposure / equity ratio"),
        use_container_width=True,
    )
    st.caption(
        "Notional exposure divided by concurrent equity. This simulator has no margin/leverage "
        "model -- this ratio is the only exposure measure available."
    )
