"""S006-T020 — interactive declarative model inspection (HTML, not PNG).

Run manually:

    uv pip install plotly
    uv run python tests/spike/run_inspect_declarative_models.py --open
    uv run python tests/spike/run_inspect_declarative_models.py \\
        --market-models high_volatility \\
        --signal-models higher_low_long,high_vol_and_higher_low \\
        --output model_inspection.html --open

The chart layer consumes ``evaluate_models`` output only — no model evaluation,
component compute, firing or resampling in plotting helpers.
"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
import webbrowser
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

_SPIKE_DIR = Path(__file__).resolve().parent
if str(_SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR))

from _fixture_paths import OHLCV_SAMPLE_1M, OHLCV_SAMPLE_1M_FILENAME

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_COMBINED_SIGNAL_ID,
    CANONICAL_MARKET_MODEL_ID,
    CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    CanonicalModelBundle,
    build_canonical_model_bundle,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

FIXTURE = OHLCV_SAMPLE_1M


def _write_published_dataset(storage_root: Path, csv_path: Path) -> DatasetRef:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="inspect-declarative-models",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=csv_path,
            dataset_id=dataset_id,
            import_config=OhlcvImportConfig(
                column_mapping=OhlcvColumnMapping(
                    timestamp="timestamp",
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                ),
                timeframe=Timeframe("1m"),
                timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
                source_timezone=UTC,
            ),
            schema_version="ohlcv.v1",
            normalization_version="utc-interval-start.v1",
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    return result.dataset_ref


def _filter_bundle(
    bundle: CanonicalModelBundle,
    *,
    market_model_ids: tuple[str, ...] | None,
    signal_model_ids: tuple[str, ...] | None,
) -> CanonicalModelBundle:
    market_models = bundle.market_models
    signal_models = bundle.signal_models
    if market_model_ids is not None:
        market_models = tuple(
            definition
            for definition in market_models
            if definition.market_model_id in market_model_ids
        )
    if signal_model_ids is not None:
        signal_models = tuple(
            definition
            for definition in signal_models
            if definition.signal_model_id in signal_model_ids
        )
    return CanonicalModelBundle(
        market_models=market_models,
        signal_models=signal_models,
    )


def _format_bool(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float) and math.isnan(value):
        return "null"
    return str(value)


def _timestamp_index(frame: AnalysisFrame) -> dict[datetime, int]:
    return {timestamp: index for index, timestamp in enumerate(frame.timestamps)}


def _ohlcv_for_frame(
    frame: AnalysisFrame,
    market_view: AnalysisDataView,
) -> dict[str, tuple[float, ...]]:
    """Map canonical OHLCV from the analysis market view onto the evaluation frame."""
    if "close" in frame.columns:
        return {
            field: frame.columns[field]
            for field in ("open", "high", "low", "close", "volume")
            if field in frame.columns
        }

    index_by_timestamp = {
        timestamp: index for index, timestamp in enumerate(market_view.timestamps)
    }
    columns: dict[str, list[float]] = {
        field: [] for field in ("open", "high", "low", "close", "volume")
    }
    for timestamp in frame.timestamps:
        index = index_by_timestamp.get(timestamp)
        if index is None:
            for values in columns.values():
                values.append(math.nan)
            continue
        columns["open"].append(market_view.open.values[index])
        columns["high"].append(market_view.high.values[index])
        columns["low"].append(market_view.low.values[index])
        columns["close"].append(market_view.close.values[index])
        columns["volume"].append(market_view.volume.values[index])
    return {field: tuple(values) for field, values in columns.items()}


def _close_at(
    frame: AnalysisFrame,
    timestamp: datetime,
    *,
    ohlcv: dict[str, tuple[float, ...]],
) -> float:
    index = _timestamp_index(frame).get(timestamp)
    if index is None:
        return math.nan
    close = ohlcv.get("close")
    if close is None:
        return math.nan
    return close[index]


def _print_text_report(
    *,
    market_results: dict[str, pl.DataFrame],
    signal_conditions: dict[str, pl.DataFrame],
    signal_emissions: dict[str, pl.DataFrame],
) -> None:
    for model_id, result in market_results.items():
        true_count = result.filter(pl.col("model_result").eq(True)).height
        print(f"Market model {model_id}: {true_count} true bars / {result.height} total")
    for signal_id, condition in signal_conditions.items():
        true_count = condition.filter(pl.col("condition_met").eq(True)).height
        emissions = signal_emissions[signal_id]
        print(
            f"Signal model {signal_id}: {true_count} true condition bars, "
            f"{emissions.height} emissions"
        )
        for row in emissions.iter_rows(named=True):
            print(
                f"  emission detected_at={row['detected_at'].isoformat()} "
                f"available_at={row['available_at'].isoformat()} "
                f"direction={row['direction']} policy={row['firing_policy']}"
            )


def _write_interactive_html(
    *,
    frame: AnalysisFrame,
    market_view: AnalysisDataView,
    market_results: dict[str, pl.DataFrame],
    signal_conditions: dict[str, pl.DataFrame],
    signal_emissions: dict[str, pl.DataFrame],
    output: Path,
) -> None:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as exc:
        msg = "plotly is required for interactive inspection (uv pip install plotly)"
        raise SystemExit(msg) from exc

    timestamps = list(frame.timestamps)
    ohlcv = _ohlcv_for_frame(frame, market_view)
    panel_count = 1 + len(market_results) + len(signal_conditions)
    row_heights = [0.55] + [0.45 / max(panel_count - 1, 1)] * (panel_count - 1)
    subplot_titles = (
        ["OHLCV + signal emissions"]
        + [f"Market model: {model_id}" for model_id in market_results]
        + [f"Signal condition: {signal_id}" for signal_id in signal_conditions]
    )

    fig = make_subplots(
        rows=panel_count,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=tuple(subplot_titles),
    )

    fig.add_trace(
        go.Candlestick(
            x=timestamps,
            open=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
            name="OHLCV",
            increasing_line_color="#2ca02c",
            decreasing_line_color="#d62728",
        ),
        row=1,
        col=1,
    )

    emission_colors = {
        CANONICAL_SIGNAL_HIGHER_LOW_ID: "#1565c0",
        CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID: "#c62828",
        CANONICAL_COMBINED_SIGNAL_ID: "#6a1b9a",
    }
    for signal_id, emissions in signal_emissions.items():
        if emissions.is_empty():
            continue
        xs: list[datetime] = []
        ys: list[float] = []
        texts: list[str] = []
        for row in emissions.iter_rows(named=True):
            detected_at = row["detected_at"]
            price = _close_at(frame, detected_at, ohlcv=ohlcv)
            if math.isnan(price):
                continue
            xs.append(detected_at)
            ys.append(price)
            texts.append(
                f"{signal_id} emission<br>"
                f"detected_at={detected_at.isoformat()}<br>"
                f"available_at={row['available_at'].isoformat()}<br>"
                f"direction={row['direction']}<br>"
                f"policy={row['firing_policy']}"
            )
        if not xs:
            continue
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers",
                name=f"{signal_id} emission",
                marker={
                    "symbol": "star",
                    "size": 11,
                    "color": emission_colors.get(signal_id, "#333333"),
                    "line": {"width": 1, "color": "#111111"},
                },
                text=texts,
                hoverinfo="text",
            ),
            row=1,
            col=1,
        )

    current_row = 2
    market_colors = {
        CANONICAL_MARKET_MODEL_ID: "#ef6c00",
    }
    for model_id, result in market_results.items():
        y_values = [
            None if value is None else float(value) for value in result["model_result"].to_list()
        ]
        hover_texts = [
            (
                f"{model_id}<br>"
                f"timestamp={timestamp.isoformat()}<br>"
                f"available_at={available_at.isoformat()}<br>"
                f"model_result={_format_bool(model_result)}"
            )
            for timestamp, available_at, model_result in zip(
                result["timestamp"],
                result["available_at"],
                result["model_result"],
                strict=True,
            )
        ]
        fig.add_trace(
            go.Scatter(
                x=result["timestamp"].to_list(),
                y=y_values,
                mode="lines",
                name=model_id,
                line={
                    "color": market_colors.get(model_id, "#555555"),
                    "width": 1.4,
                    "shape": "hv",
                },
                text=hover_texts,
                hoverinfo="text",
                connectgaps=False,
            ),
            row=current_row,
            col=1,
        )
        current_row += 1

    signal_colors = {
        CANONICAL_SIGNAL_HIGHER_LOW_ID: "#00838f",
        CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID: "#ad1457",
        CANONICAL_COMBINED_SIGNAL_ID: "#4527a0",
    }
    for signal_id, condition in signal_conditions.items():
        y_values = [
            None if value is None else float(value)
            for value in condition["condition_met"].to_list()
        ]
        hover_texts = [
            (
                f"{signal_id}<br>"
                f"timestamp={timestamp.isoformat()}<br>"
                f"available_at={available_at.isoformat()}<br>"
                f"condition_met={_format_bool(condition_met)}"
            )
            for timestamp, available_at, condition_met in zip(
                condition["timestamp"],
                condition["available_at"],
                condition["condition_met"],
                strict=True,
            )
        ]
        fig.add_trace(
            go.Scatter(
                x=condition["timestamp"].to_list(),
                y=y_values,
                mode="lines",
                name=f"{signal_id} condition",
                line={
                    "color": signal_colors.get(signal_id, "#777777"),
                    "width": 1.2,
                    "shape": "hv",
                },
                text=hover_texts,
                hoverinfo="text",
                connectgaps=False,
            ),
            row=current_row,
            col=1,
        )
        current_row += 1

    fig.update_layout(
        title="S006 declarative model inspection — pre-computed model overlays only",
        xaxis_rangeslider_visible=False,
        height=max(700, 220 * panel_count),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        hovermode="x unified",
        template="plotly_white",
    )
    fig.update_yaxes(title_text="price", row=1, col=1)
    for row in range(2, panel_count + 1):
        fig.update_yaxes(title_text="state", range=[-0.05, 1.15], row=row, col=1)
    fig.update_xaxes(title_text="timestamp (1m)", row=panel_count, col=1)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output), include_plotlyjs="cdn", auto_open=False)
    print(f"Wrote {output.resolve()}")


def _parse_id_list(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    return values or None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect canonical declarative models interactively."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=FIXTURE,
        help=f"CSV fixture path (default: {OHLCV_SAMPLE_1M_FILENAME})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("model_inspection.html"),
        help="Interactive HTML output path (default: model_inspection.html)",
    )
    parser.add_argument(
        "--market-models",
        type=str,
        default=None,
        help="Comma-separated market_model_id filter (default: all canonical)",
    )
    parser.add_argument(
        "--signal-models",
        type=str,
        default=None,
        help="Comma-separated signal_model_id filter (default: all canonical)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the HTML report in the default browser",
    )
    args = parser.parse_args()

    bundle = _filter_bundle(
        build_canonical_model_bundle(),
        market_model_ids=_parse_id_list(args.market_models),
        signal_model_ids=_parse_id_list(args.signal_models),
    )
    if not bundle.market_models and not bundle.signal_models:
        raise SystemExit("No models selected after filtering.")

    with tempfile.TemporaryDirectory() as tmp:
        storage_root = Path(tmp)
        dataset_ref = _write_published_dataset(storage_root, args.fixture)
        metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
        evaluation = evaluate_models(
            EvaluateModelsRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                market_models=bundle.market_models,
                signal_models=bundle.signal_models,
            )
        )
        frame = evaluation.analysis.frame
        if frame is None:
            raise SystemExit("No frame assembled.")
        _print_text_report(
            market_results=evaluation.market_model_results,
            signal_conditions=evaluation.signal_model_conditions,
            signal_emissions=evaluation.signal_model_emissions,
        )
        _write_interactive_html(
            frame=frame,
            market_view=evaluation.analysis.workspace.market_view,
            market_results=evaluation.market_model_results,
            signal_conditions=evaluation.signal_model_conditions,
            signal_emissions=evaluation.signal_model_emissions,
            output=args.output,
        )
    if args.open:
        webbrowser.open(args.output.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
