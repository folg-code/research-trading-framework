"""S005-T014 — interactive MTF swing inspection (HTML, not PNG).

Run manually:

    uv run python tests/spike/run_inspect_mtf_swing.py
    uv run python tests/spike/run_inspect_mtf_swing.py --open
    uv run python tests/spike/run_inspect_mtf_swing.py --output swing_inspection.html --open

Requires plotly in the active environment (``uv pip install plotly``).
Copy to ``user_data/development/inspect_mtf_swing.py`` for local iteration.
The chart layer consumes ``run_analysis`` frame output only — no extra compute.
"""

from __future__ import annotations

import argparse
import math
import tempfile
import webbrowser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
    ComponentId,
    ComponentRequest,
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "market_data"
    / "s005_swing_vertical_slice_1m.csv"
)

_SWING_OUTPUT_IDS = tuple(
    field.output_id.value for field in SwingStructureComponent().output_schema.outputs
)


@dataclass(frozen=True, slots=True)
class _HtfGrid:
    """Computation grid for structure.swing (indices in frame are on this grid)."""

    timestamps: tuple[datetime, ...]
    timeframe: Timeframe


def _resolve_htf_grid(result) -> _HtfGrid:
    swing_result = None
    for analysis_result in result.workspace.result_store.results().values():
        if analysis_result.computation_identity.component_id == ComponentId("structure.swing"):
            swing_result = analysis_result
            break
    if swing_result is None:
        raise SystemExit("structure.swing result missing from workspace")
    input_key = swing_result.computation_identity.input_identity_key
    if input_key is None:
        frame = result.frame
        if frame is None:
            raise SystemExit("No frame assembled.")
        return _HtfGrid(timestamps=frame.timestamps, timeframe=Timeframe("1m"))
    htf_view = result.workspace.market_view_for(input_key)
    return _HtfGrid(
        timestamps=htf_view.timestamps,
        timeframe=swing_result.computation_identity.computation_timeframe,
    )


def _observed_timestamp(htf_grid: _HtfGrid, observed_index_value: float) -> datetime | None:
    """Map HTF bar index (not 1m index) to the computation grid timestamp."""
    if math.isnan(observed_index_value):
        return None
    observed_index = int(observed_index_value)
    if 0 <= observed_index < len(htf_grid.timestamps):
        return htf_grid.timestamps[observed_index]
    return None


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
        source_id="inspect-mtf-swing",
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


def _swing_column_specs(parameters) -> tuple[AnalysisFrameColumnSpec, ...]:
    return tuple(
        AnalysisFrameColumnSpec(
            component_id=ComponentId("structure.swing"),
            parameters=parameters,
            output_id=OutputId(output_id),
            alias=f"{output_id}_5m",
        )
        for output_id in _SWING_OUTPUT_IDS
    )


def _run_inspection(
    *,
    storage_root: Path,
    csv_path: Path,
    pivot_range: int,
    computation_timeframe: Timeframe,
):
    dataset_ref = _write_published_dataset(storage_root, csv_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    swing_schema = SwingStructureComponent().parameter_schema
    swing_params = swing_schema.canonicalize({"pivot_range": pivot_range})
    return run_analysis(
        RunAnalysisRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            component_requests=(
                ComponentRequest.from_raw(
                    ComponentId("structure.swing"),
                    swing_schema,
                    {"pivot_range": pivot_range},
                    computation_timeframe=computation_timeframe,
                ),
            ),
            frame_request=AnalysisFrameRequest(
                market_fields=("open", "high", "low", "close", "volume"),
                analysis_columns=_swing_column_specs(swing_params),
            ),
        )
    )


def _format_value(value: float) -> str:
    if value != value:
        return "NaN"
    if value in (0.0, 1.0) and float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}"


def _build_hover_texts(frame, htf_grid: _HtfGrid) -> list[str]:
    session = frame.session_metadata
    hover_texts: list[str] = []
    for index, timestamp in enumerate(frame.timestamps):
        lines = [
            f"ltf_index={index}",
            f"ltf_time={timestamp.isoformat()}",
            f"htf_timeframe={htf_grid.timeframe.value}",
        ]
        if session is not None:
            lines.append(f"trading_day={session.trading_days[index]}")
            lines.append(f"session_id={session.session_ids[index]}")
            lines.append(f"is_rth={session.is_rth[index]}")
        for column, values in frame.columns.items():
            value = values[index]
            if column.endswith("_observed_index_5m"):
                observed_at = _observed_timestamp(htf_grid, value)
                at_column = column.replace("_observed_index_5m", "_observed_at")
                lines.append(f"{column}={_format_value(value)} (HTF bar index)")
                lines.append(f"{at_column}={observed_at.isoformat() if observed_at else 'n/a'}")
            else:
                lines.append(f"{column}={_format_value(value)}")
        hover_texts.append("<br>".join(lines))
    return hover_texts


def _print_text_report(result, htf_grid: _HtfGrid) -> None:
    frame = result.frame
    if frame is None:
        print("No frame assembled.")
        return
    session = frame.session_metadata
    print(f"Bars (1m): {len(frame.timestamps)}")
    print(f"Bars ({htf_grid.timeframe.value} computation grid): {len(htf_grid.timestamps)}")
    if session is not None:
        print(f"RTH bars: {sum(session.is_rth)}")
    event_columns = (
        "swing_high_event_5m",
        "swing_low_event_5m",
        "higher_high_event_5m",
        "lower_high_event_5m",
        "higher_low_event_5m",
        "lower_low_event_5m",
    )
    for column in event_columns:
        if column not in frame.columns:
            continue
        count = sum(value == 1.0 for value in frame.columns[column])
        print(f"{column}: {count} detections")
        if count == 0:
            continue
        price_column = column.replace("_event_5m", "_price_5m")
        observed_column = column.replace("_event_5m", "_observed_index_5m")
        prices = frame.columns.get(price_column)
        observed_indices = frame.columns.get(observed_column)
        for index, flag in enumerate(frame.columns[column]):
            if flag != 1.0:
                continue
            detected_at = frame.timestamps[index]
            observed_htf_index = (
                observed_indices[index] if observed_indices is not None else math.nan
            )
            observed_at = _observed_timestamp(htf_grid, observed_htf_index)
            price = prices[index] if prices is not None else math.nan
            print(
                f"  detected={detected_at.isoformat()} "
                f"observed_htf_index={_format_value(observed_htf_index)} "
                f"observed_at={observed_at.isoformat() if observed_at else 'n/a'} "
                f"price={_format_value(price)}"
            )


def _rth_regions(frame) -> list[tuple[object, object]]:
    session = frame.session_metadata
    if session is None:
        return []
    regions: list[tuple[object, object]] = []
    start_index: int | None = None
    for index, is_rth in enumerate(session.is_rth):
        if is_rth and start_index is None:
            start_index = index
        if not is_rth and start_index is not None:
            regions.append((frame.timestamps[start_index], frame.timestamps[index - 1]))
            start_index = None
    if start_index is not None:
        regions.append((frame.timestamps[start_index], frame.timestamps[-1]))
    return regions


def _event_marker_points(
    frame,
    htf_grid: _HtfGrid,
    *,
    event_column: str,
    price_column: str,
    symbol: str,
    color: str,
    name: str,
):
    if event_column not in frame.columns or price_column not in frame.columns:
        return None
    xs: list[object] = []
    ys: list[float] = []
    texts: list[str] = []
    for index, flag in enumerate(frame.columns[event_column]):
        if flag != 1.0:
            continue
        price = frame.columns[price_column][index]
        if math.isnan(price):
            continue
        xs.append(frame.timestamps[index])
        ys.append(price)
        observed_column = event_column.replace("_event_5m", "_observed_index_5m")
        observed_htf_index = frame.columns[observed_column][index]
        observed_at = _observed_timestamp(htf_grid, observed_htf_index)
        texts.append(
            f"{name}<br>detected={frame.timestamps[index].isoformat()}<br>"
            f"observed_htf_index={_format_value(observed_htf_index)}<br>"
            f"observed_at={observed_at.isoformat() if observed_at else 'n/a'}<br>"
            f"price={_format_value(price)}"
        )
    if not xs:
        return None
    return {
        "x": xs,
        "y": ys,
        "mode": "markers",
        "type": "scatter",
        "name": name,
        "marker": {"symbol": symbol, "size": 9, "color": color, "line": {"width": 1}},
        "text": texts,
        "hoverinfo": "text",
    }


def _observed_marker_points(
    frame,
    htf_grid: _HtfGrid,
    *,
    event_column: str,
    price_column: str,
    name: str,
):
    observed_column = event_column.replace("_event_5m", "_observed_index_5m")
    if observed_column not in frame.columns or price_column not in frame.columns:
        return None
    xs: list[object] = []
    ys: list[float] = []
    texts: list[str] = []
    for index, flag in enumerate(frame.columns[event_column]):
        if flag != 1.0:
            continue
        observed_htf_index = frame.columns[observed_column][index]
        observed_at = _observed_timestamp(htf_grid, observed_htf_index)
        if observed_at is None:
            continue
        price = frame.columns[price_column][index]
        if math.isnan(price):
            continue
        xs.append(observed_at)
        ys.append(price)
        texts.append(
            f"{name} (HTF observed bar)<br>"
            f"observed_at={observed_at.isoformat()}<br>"
            f"observed_htf_index={_format_value(observed_htf_index)}<br>"
            f"detected_at={frame.timestamps[index].isoformat()}<br>"
            f"price={_format_value(price)}"
        )
    if not xs:
        return None
    return {
        "x": xs,
        "y": ys,
        "mode": "markers",
        "type": "scatter",
        "name": name,
        "marker": {"symbol": "diamond-open", "size": 10, "color": "#6a1b9a", "line": {"width": 2}},
        "text": texts,
        "hoverinfo": "text",
    }


def _write_interactive_html(
    result,
    htf_grid: _HtfGrid,
    *,
    output: Path,
    computation_timeframe: Timeframe,
) -> None:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as exc:
        msg = "plotly is required for interactive inspection (uv pip install plotly)"
        raise SystemExit(msg) from exc

    frame = result.frame
    if frame is None:
        raise SystemExit("No frame assembled.")

    hover_texts = _build_hover_texts(frame, htf_grid)
    timestamps = list(frame.timestamps)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.78, 0.22],
        subplot_titles=(
            f"OHLCV + 5m swing state ({computation_timeframe.value} on 1m grid)",
            "Event flags (1 = detection bar on 1m grid)",
        ),
    )

    fig.add_trace(
        go.Candlestick(
            x=timestamps,
            open=frame.columns["open"],
            high=frame.columns["high"],
            low=frame.columns["low"],
            close=frame.columns["close"],
            name="OHLCV",
            increasing_line_color="#2ca02c",
            decreasing_line_color="#d62728",
            text=hover_texts,
            hoverinfo="text",
        ),
        row=1,
        col=1,
    )

    state_lines = (
        ("latest_swing_high_level_5m", "#ff7f0e", "latest swing high"),
        ("latest_swing_low_level_5m", "#1f77b4", "latest swing low"),
        ("latest_higher_high_level_5m", "#9467bd", "latest higher high"),
        ("latest_lower_high_level_5m", "#8c564b", "latest lower high"),
        ("latest_higher_low_level_5m", "#17becf", "latest higher low"),
        ("latest_lower_low_level_5m", "#bcbd22", "latest lower low"),
    )
    for column, color, label in state_lines:
        if column not in frame.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=frame.columns[column],
                mode="lines",
                name=label,
                line={"color": color, "width": 1.4, "shape": "hv"},
                connectgaps=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    for trace_kwargs in (
        _event_marker_points(
            frame,
            htf_grid,
            event_column="swing_high_event_5m",
            price_column="swing_high_price_5m",
            symbol="triangle-up",
            color="#c62828",
            name="swing high detected",
        ),
        _event_marker_points(
            frame,
            htf_grid,
            event_column="swing_low_event_5m",
            price_column="swing_low_price_5m",
            symbol="triangle-down",
            color="#1565c0",
            name="swing low detected",
        ),
        _observed_marker_points(
            frame,
            htf_grid,
            event_column="swing_high_event_5m",
            price_column="swing_high_price_5m",
            name="swing high observed (HTF bar)",
        ),
        _observed_marker_points(
            frame,
            htf_grid,
            event_column="swing_low_event_5m",
            price_column="swing_low_price_5m",
            name="swing low observed (HTF bar)",
        ),
    ):
        if trace_kwargs is not None:
            fig.add_trace(go.Scatter(**trace_kwargs), row=1, col=1)

    event_panel = (
        ("swing_high_event_5m", "#c62828"),
        ("swing_low_event_5m", "#1565c0"),
        ("higher_high_event_5m", "#6a1b9a"),
        ("lower_high_event_5m", "#ad1457"),
        ("higher_low_event_5m", "#00838f"),
        ("lower_low_event_5m", "#558b2f"),
    )
    for column, color in event_panel:
        if column not in frame.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=frame.columns[column],
                mode="lines",
                name=column.replace("_5m", ""),
                line={"color": color, "width": 1.2, "shape": "hv"},
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )

    for start, end in _rth_regions(frame):
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(46, 125, 50, 0.08)",
            line_width=0,
            row=1,
            col=1,
        )

    fig.update_layout(
        title="S005 MTF swing inspection — zoom/pan/hover for full frame columns",
        xaxis_rangeslider_visible=False,
        height=900,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        hovermode="x unified",
        template="plotly_white",
    )
    fig.update_yaxes(title_text="price", row=1, col=1)
    fig.update_yaxes(title_text="event", range=[-0.05, 1.15], row=2, col=1)
    fig.update_xaxes(title_text="timestamp (1m)", row=2, col=1)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output), include_plotlyjs="cdn", auto_open=False)
    print(f"Wrote {output.resolve()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect MTF swing structure interactively.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=FIXTURE,
        help="CSV fixture path (default: s005_swing_vertical_slice_1m.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("swing_inspection.html"),
        help="Interactive HTML output path (default: swing_inspection.html)",
    )
    parser.add_argument(
        "--pivot-range",
        type=int,
        default=1,
        help="structure.swing pivot_range parameter (default: 1)",
    )
    parser.add_argument(
        "--computation-timeframe",
        type=str,
        default="5m",
        help="HTF for swing computation (default: 5m)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the HTML report in the default browser",
    )
    args = parser.parse_args()

    computation_timeframe = Timeframe(args.computation_timeframe)
    with tempfile.TemporaryDirectory() as tmp:
        storage_root = Path(tmp)
        result = _run_inspection(
            storage_root=storage_root,
            csv_path=args.fixture,
            pivot_range=args.pivot_range,
            computation_timeframe=computation_timeframe,
        )
        htf_grid = _resolve_htf_grid(result)
        _print_text_report(result, htf_grid)
        _write_interactive_html(
            result,
            htf_grid,
            output=args.output,
            computation_timeframe=computation_timeframe,
        )
    if args.open:
        webbrowser.open(args.output.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
