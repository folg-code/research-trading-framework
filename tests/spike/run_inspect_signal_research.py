"""S008-T009 — interactive Signal Research occurrence / forward-path inspection.

Run manually:

    uv pip install plotly
    uv run python tests/spike/run_inspect_signal_research.py --generate --open
    uv run python tests/spike/run_inspect_signal_research.py \\
        --storage-root user_data/storage --run-id <run_id> \\
        --occurrence-index 0 --horizon 5 --open

The chart layer consumes a persisted run envelope (or one fresh ``run_signal_research``
result) plus historical OHLCV for the price window only. It does not evaluate models,
recompute outcomes or resample components.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import webbrowser
from datetime import UTC, timedelta
from pathlib import Path

_SPIKE_DIR = Path(__file__).resolve().parent
if str(_SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR))

from _fixture_paths import OHLCV_SAMPLE_1M
from _signal_research_inspection import (
    InspectionSelection,
    InspectionWindow,
    bars_to_window,
    build_inspection_selection,
    excursion_price_levels,
    is_complete_outcome,
    query_window_range,
)

from trading_framework.application.market_data import QueryHistoricalRequest, query_historical
from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.application.signal_research import (
    RunSignalResearchRequest,
    run_signal_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets import RunDatasetRef, SignalResearchDatasetRepository
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


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
        source_id="inspect-signal-research",
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


def _load_bars_for_selection(
    *,
    storage_root: Path,
    dataset_ref: DatasetRef,
    selection: InspectionSelection,
    padding_bars: int,
) -> InspectionWindow:
    bar_step = timedelta(minutes=1)
    start_at, end_at = query_window_range(
        detected_at=selection.detected_at,
        horizon_bars=selection.horizon_bars,
        padding_bars=padding_bars,
        bar_step=bar_step,
    )
    bars = query_historical(
        QueryHistoricalRequest(dataset_ref=dataset_ref, start_at=start_at, end_at=end_at),
        storage_root=storage_root,
    )
    return bars_to_window(
        bars,
        detected_at=selection.detected_at,
        horizon_bars=selection.horizon_bars,
        padding_bars=padding_bars,
    )


def _render_html(
    *,
    selection: InspectionSelection,
    window: InspectionWindow,
    output: Path,
) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    mfe_level, mae_level = excursion_price_levels(
        reference_price=selection.reference_price,
        direction=selection.direction,
        mfe=selection.mfe,
        mae=selection.mae,
    )

    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(
        go.Candlestick(
            x=list(window.timestamps),
            open=list(window.opens),
            high=list(window.highs),
            low=list(window.lows),
            close=list(window.closes),
            name="OHLCV",
            increasing_line_color="#2ca02c",
            decreasing_line_color="#d62728",
        )
    )

    marker_specs = [
        (selection.detected_at, "#1565c0", "detected_at"),
        (selection.available_at, "#6a1b9a", "available_at"),
    ]
    if window.horizon_end_timestamp is not None:
        marker_specs.append((window.horizon_end_timestamp, "#ef6c00", "horizon_end"))

    for timestamp, color, label in marker_specs:
        fig.add_vline(x=timestamp, line_width=1.2, line_dash="dash", line_color=color)
        fig.add_annotation(
            x=timestamp,
            y=1.04,
            yref="paper",
            text=label,
            showarrow=False,
            font={"size": 10, "color": color},
        )

    fig.add_hline(
        y=selection.reference_price,
        line_width=1.2,
        line_dash="dot",
        line_color="#424242",
        annotation_text="reference_price",
        annotation_position="top left",
    )

    if mfe_level is not None:
        fig.add_hline(
            y=mfe_level,
            line_width=1.0,
            line_dash="dashdot",
            line_color="#2e7d32",
            annotation_text="MFE",
            annotation_position="top right",
        )
    if mae_level is not None:
        fig.add_hline(
            y=mae_level,
            line_width=1.0,
            line_dash="dashdot",
            line_color="#c62828",
            annotation_text="MAE",
            annotation_position="bottom right",
        )
    if selection.terminal_price is not None:
        fig.add_hline(
            y=selection.terminal_price,
            line_width=1.4,
            line_color="#1565c0",
            annotation_text="terminal",
            annotation_position="bottom left",
        )

    outcome_summary = selection.outcome_status or "missing"
    if is_complete_outcome(selection) and selection.forward_return is not None:
        outcome_summary = (
            f"{selection.outcome_status}; "
            f"forward_return={selection.forward_return:.4f}; "
            f"mfe={selection.mfe:.4f}; mae={selection.mae:.4f}"
        )

    fig.update_layout(
        title=(
            f"S008 Signal Research inspection — {selection.signal_model_id} "
            f"({selection.occurrence_id}, horizon={selection.horizon_bars})"
        ),
        xaxis_rangeslider_visible=False,
        height=720,
        template="plotly_white",
        hovermode="x unified",
    )
    fig.add_annotation(
        text=outcome_summary,
        xref="paper",
        yref="paper",
        x=0,
        y=-0.18,
        showarrow=False,
        font={"size": 11},
        align="left",
    )
    fig.update_yaxes(title_text="price")
    fig.update_xaxes(title_text="timestamp")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output), include_plotlyjs="cdn", auto_open=False)
    print(f"Wrote {output.resolve()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect one Signal Research occurrence.")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run signal research on the committed fixture and inspect the first occurrence",
    )
    parser.add_argument("--storage-root", type=Path, default=None, help="Research storage root")
    parser.add_argument("--run-id", type=str, default=None, help="Persisted run_id to inspect")
    parser.add_argument("--occurrence-index", type=int, default=0)
    parser.add_argument("--occurrence-id", type=str, default=None)
    parser.add_argument("--horizon", type=int, default=5, help="Horizon bars to inspect")
    parser.add_argument("--padding-bars", type=int, default=20, help="Bars before/after window")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("signal_research_inspection.html"),
    )
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    if args.generate:
        with tempfile.TemporaryDirectory() as tmp:
            storage_root = Path(tmp) / "storage"
            storage_root.mkdir()
            dataset_ref = _write_published_dataset(storage_root, OHLCV_SAMPLE_1M)
            metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
            result = run_signal_research(
                RunSignalResearchRequest(
                    dataset_ref=dataset_ref,
                    timeframe=Timeframe("1m"),
                    requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                    storage_root=storage_root,
                    signal_models=(build_canonical_signal_higher_low_on_event(),),
                    horizons=(args.horizon,),
                    evaluation_timeframe=Timeframe("1m"),
                    session_resolver=CmeEsRthSessionResolver(),
                )
            )
            selection = build_inspection_selection(
                result.occurrences,
                result.outcomes,
                occurrence_index=args.occurrence_index,
                occurrence_id=args.occurrence_id,
                horizon_bars=args.horizon,
            )
            window = _load_bars_for_selection(
                storage_root=storage_root,
                dataset_ref=dataset_ref,
                selection=selection,
                padding_bars=args.padding_bars,
            )
            _render_html(selection=selection, window=window, output=args.output)
    else:
        if args.storage_root is None or args.run_id is None:
            parser.error("--storage-root and --run-id are required unless --generate is set")
        repository = SignalResearchDatasetRepository(args.storage_root)
        envelope = repository.read(RunDatasetRef(run_id=args.run_id))
        dataset_ref = DatasetRef.parse(envelope.manifest.source_dataset_ref)
        selection = build_inspection_selection(
            envelope.occurrences,
            envelope.outcomes,
            occurrence_index=args.occurrence_index,
            occurrence_id=args.occurrence_id,
            horizon_bars=args.horizon,
        )
        window = _load_bars_for_selection(
            storage_root=args.storage_root,
            dataset_ref=dataset_ref,
            selection=selection,
            padding_bars=args.padding_bars,
        )
        _render_html(selection=selection, window=window, output=args.output)

    if args.open:
        webbrowser.open(args.output.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
