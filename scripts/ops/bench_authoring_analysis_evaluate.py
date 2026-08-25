"""Fixture-first microbench for authoring → analysis → evaluate.

Times P1 (DSL compile → IR), P2 (``run_analysis``), and P3 (``evaluate_models``
evaluation work excluding the nested analysis call) on synthetic bars.

Does not persist research runs. Does not redo S026/S027 harnesses.

Example::

    uv run python scripts/ops/bench_authoring_analysis_evaluate.py
    uv run python scripts/ops/bench_authoring_analysis_evaluate.py --json
    uv run python scripts/ops/bench_authoring_analysis_evaluate.py --bars 500
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
    build_canonical_signal_high_volatility_on_true_edge,
)
from trading_framework.application.model_evaluation.evaluate_models import (
    EvaluateModelsRequest,
    evaluate_models,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
from trading_framework.infrastructure.observability.profile_context import phase_timer_context
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_expression.planning import (
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

DEFAULT_BAR_COUNT = 250
_MIN_BARS = 32
_BAR_STEP = timedelta(minutes=1)
_SYNTHETIC_START = datetime(2024, 1, 16, 14, 30, tzinfo=UTC)
_P3_EVALUATION_PHASES = (
    "evaluate_models.validate",
    "evaluate_models.collect_dependencies",
    "evaluate_models.build_evaluation_table",
    "evaluate_models.market_models",
    "evaluate_models.signal_models",
)


@dataclass(frozen=True, slots=True)
class TimingResult:
    name: str
    wall_seconds: float
    peak_bytes: int | None


@dataclass(frozen=True, slots=True)
class NestedPhase:
    name: str
    inclusive_seconds: float
    call_count: int


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    bar_count: int
    market_model_ids: list[str]
    signal_model_ids: list[str]
    phases: list[TimingResult]
    nested_phases: list[NestedPhase]
    notes: list[str]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Microbench authoring compile, run_analysis, and evaluate_models "
            "on synthetic bars (no user_data I/O)."
        ),
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=DEFAULT_BAR_COUNT,
        help=f"Synthetic 1m bar count (default {DEFAULT_BAR_COUNT}; CI smoke uses a smaller value)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    return parser


def _timed[T](name: str, fn: Callable[[], T]) -> tuple[T, TimingResult]:
    tracemalloc.start()
    started = time.perf_counter()
    try:
        value = fn()
    finally:
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return value, TimingResult(name=name, wall_seconds=elapsed, peak_bytes=peak)


def _synthetic_column_batch(bar_count: int, *, seed: int = 42) -> OhlcvColumnBatch:
    rng = np.random.default_rng(seed)
    close = 20_000.0 + np.cumsum(rng.normal(0.0, 2.0, bar_count))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    spread = rng.uniform(0.5, 3.0, bar_count)
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.integers(100, 5_000, bar_count, dtype=np.int64).astype(np.float64)
    timestamps = tuple(_SYNTHETIC_START + _BAR_STEP * index for index in range(bar_count))
    available_at = tuple(timestamp + _BAR_STEP for timestamp in timestamps)
    return OhlcvColumnBatch(
        timestamps=timestamps,
        available_at=available_at,
        open=tuple(float(value) for value in open_),
        high=tuple(float(value) for value in high),
        low=tuple(float(value) for value in low),
        close=tuple(float(value) for value in close),
        volume=tuple(float(value) for value in volume),
    )


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="synthetic",
            source_id="bench-authoring-analysis-evaluate",
        ),
        version=1,
    )


def _compile_canonical_models() -> tuple[
    tuple[MarketModelDefinition, ...],
    tuple[SignalModelDefinition, ...],
]:
    return (
        (build_canonical_market_model_high_volatility(),),
        (build_canonical_signal_high_volatility_on_true_edge(),),
    )


def _phase_inclusive_seconds(timer: PhaseTimer, name: str) -> float:
    stats = timer._stats.get(name)
    if stats is None:
        return 0.0
    return stats.inclusive_seconds


def run_benchmark(bar_count: int) -> BenchmarkReport:
    """Compile canonical models, run analysis, and evaluate on synthetic bars."""
    notes = [
        "synthetic OHLCV via preloaded_column_batch; no user_data persistence",
        "P3 wall excludes nested evaluate_models.run_analysis (D-S036-02 split)",
        "P4-P6 research loops and P7 Parquet ingest are not timed",
    ]
    column_batch = _synthetic_column_batch(bar_count)
    dataset_ref = _dataset_ref()
    timeframe = Timeframe("1m")
    requested_range = TimeRange(start=column_batch.timestamps[0], end=column_batch.timestamps[-1])
    session_resolver = CmeEsRthSessionResolver()

    compiled, p1 = _timed("p1_compile", _compile_canonical_models)
    market_models, signal_models = compiled
    dependencies = collect_model_dependencies(
        market_models=market_models,
        signal_models=signal_models,
    )
    frame_request = build_analysis_frame_request(dependencies)

    with tempfile.TemporaryDirectory(prefix="bench-aae-") as tmp:
        storage_root = Path(tmp)

        def _run_p2() -> None:
            run_analysis(
                RunAnalysisRequest(
                    dataset_ref=dataset_ref,
                    timeframe=timeframe,
                    requested_range=requested_range,
                    storage_root=storage_root,
                    component_requests=dependencies.component_requests,
                    frame_request=frame_request,
                    evaluation_timeframe=timeframe,
                    session_resolver=session_resolver,
                    preloaded_column_batch=column_batch,
                )
            )

        _, p2 = _timed("p2_run_analysis", _run_p2)

        timer = PhaseTimer(enabled=True)

        def _run_p3() -> None:
            with phase_timer_context(timer):
                result = evaluate_models(
                    EvaluateModelsRequest(
                        dataset_ref=dataset_ref,
                        timeframe=timeframe,
                        requested_range=requested_range,
                        storage_root=storage_root,
                        market_models=market_models,
                        signal_models=signal_models,
                        evaluation_timeframe=timeframe,
                        session_resolver=session_resolver,
                        preloaded_column_batch=column_batch,
                    )
                )
            if result.analysis.frame is None:
                msg = "evaluate_models did not assemble an AnalysisFrame"
                raise RuntimeError(msg)
            if not result.market_model_results or not result.signal_model_conditions:
                msg = "evaluate_models returned empty model results"
                raise RuntimeError(msg)

        _, p3_call = _timed("p3_evaluate_models_call", _run_p3)

    p3_wall = sum(_phase_inclusive_seconds(timer, name) for name in _P3_EVALUATION_PHASES)
    p3 = TimingResult(name="p3_evaluate", wall_seconds=p3_wall, peak_bytes=p3_call.peak_bytes)
    nested = [
        NestedPhase(
            name=stats.name,
            inclusive_seconds=stats.inclusive_seconds,
            call_count=stats.call_count,
        )
        for stats in sorted(timer._stats.values(), key=lambda item: item.name)
        if stats.name.startswith("evaluate_models.") or stats.name.startswith("run_analysis.")
    ]
    notes.append(
        "P3 peak_bytes is tracemalloc peak of the evaluate_models call "
        "(includes nested run_analysis; production API has no skip hook)"
    )
    return BenchmarkReport(
        bar_count=bar_count,
        market_model_ids=[model.market_model_id for model in market_models],
        signal_model_ids=[model.signal_model_id for model in signal_models],
        phases=[p1, p2, p3],
        nested_phases=nested,
        notes=notes,
    )


def _print_human(report: BenchmarkReport) -> None:
    print(
        "bench_authoring_analysis_evaluate: "
        f"bars={report.bar_count} "
        f"market_models={report.market_model_ids} "
        f"signal_models={report.signal_model_ids}"
    )
    for item in report.phases:
        if item.peak_bytes is None:
            print(f"  {item.name}: {item.wall_seconds:.4f}s")
            continue
        print(
            f"  {item.name}: {item.wall_seconds:.4f}s, peak {item.peak_bytes / 1024 / 1024:.2f} MiB"
        )
    for note in report.notes:
        print(f"Note: {note}")


def main(argv: list[str] | None = None) -> int:
    """Run the authoring → analysis → evaluate microbench and print phase timings."""
    args = _build_parser().parse_args(argv)
    if args.bars < _MIN_BARS:
        print(f"bars must be >= {_MIN_BARS}")
        return 1

    report = run_benchmark(args.bars)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
        return 0
    _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
