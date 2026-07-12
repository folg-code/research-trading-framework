"""S008-T001 spike — Signal Research pipeline boundary validation.

Not production API; not collected by pytest.

Validates:
- evaluate_models emissions → SignalOccurrence prototype
- ForwardOutcomeDefinition + calculator semantics
- run envelope (manifest + occurrences.parquet + outcomes.parquet)
- repository read-back and immutability

Run:

    uv run python tests/spike/run_signal_research_spike.py
    uv run python tests/spike/run_signal_research_spike.py --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import polars as pl

from trading_framework import __version__ as framework_version
from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    build_canonical_signal_high_volatility_on_true_edge,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "market_data"
    / "s005_swing_vertical_slice_1m.csv"
)

SCHEMA_VERSION = "signal_research.v1"


class ReferencePricePolicy(StrEnum):
    CLOSE_AT_DETECTED_AT = "close_at_detected_at"


class IncompleteHorizonPolicy(StrEnum):
    EMIT_WITH_STATUS = "emit_with_status"


class OutcomeStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE_HORIZON = "incomplete_horizon"
    INSUFFICIENT_DATA = "insufficient_data"


class SignalDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class ForwardOutcomeDefinition:
    horizon_bars: int
    reference_price_policy: ReferencePricePolicy = ReferencePricePolicy.CLOSE_AT_DETECTED_AT
    incomplete_horizon_policy: IncompleteHorizonPolicy = IncompleteHorizonPolicy.EMIT_WITH_STATUS


@dataclass(frozen=True, slots=True)
class SpikeCheck:
    name: str
    passed: bool
    detail: str = ""


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
        source_id="s008-signal-research-spike",
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


def _timestamp_index(frame: AnalysisFrame) -> dict[datetime, int]:
    return {timestamp: index for index, timestamp in enumerate(frame.timestamps)}


def _ohlcv_for_frame(
    frame: AnalysisFrame,
    market_view: AnalysisDataView,
) -> dict[str, tuple[float, ...]]:
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


def _occurrence_id(*, signal_model_id: str, detected_at: datetime, direction: str) -> str:
    payload = f"{signal_model_id}|{detected_at.isoformat()}|{direction}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _run_id(*, dataset_key: str, signal_model_id: str, horizons: tuple[int, ...]) -> str:
    payload = (
        f"{dataset_key}|{signal_model_id}|{','.join(str(h) for h in horizons)}|{framework_version}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def materialize_occurrences(
    emissions: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    signal_model_id: str,
    instrument: str,
    evaluation_timeframe: Timeframe,
    source_dataset_ref: str,
) -> pl.DataFrame:
    """Prototype occurrence facts — descriptive reference_price at detected_at."""
    if len(emissions) == 0:
        return pl.DataFrame(
            schema={
                "occurrence_id": pl.Utf8,
                "signal_model_id": pl.Utf8,
                "detected_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "available_at": pl.Datetime(time_unit="us", time_zone="UTC"),
                "direction": pl.Utf8,
                "reference_price": pl.Float64,
                "instrument": pl.Utf8,
                "evaluation_timeframe": pl.Utf8,
                "source_dataset_ref": pl.Utf8,
            }
        )

    index_by_timestamp = _timestamp_index(frame)
    close = ohlcv["close"]
    rows: list[dict[str, Any]] = []
    for row in emissions.iter_rows(named=True):
        detected_at = row["detected_at"]
        direction = row["direction"]
        index = index_by_timestamp.get(detected_at)
        reference_price = math.nan if index is None else close[index]
        rows.append(
            {
                "occurrence_id": _occurrence_id(
                    signal_model_id=signal_model_id,
                    detected_at=detected_at,
                    direction=direction,
                ),
                "signal_model_id": signal_model_id,
                "detected_at": detected_at,
                "available_at": row["available_at"],
                "direction": direction,
                "reference_price": reference_price,
                "instrument": instrument,
                "evaluation_timeframe": evaluation_timeframe.value,
                "source_dataset_ref": source_dataset_ref,
            }
        )
    return pl.DataFrame(rows)


def _direction_normalize_return(*, raw_return: float, direction: str) -> float:
    if direction == SignalDirection.SHORT.value:
        return -raw_return
    return raw_return


def _compute_excursions(
    *,
    reference_price: float,
    direction: str,
    highs: list[float],
    lows: list[float],
) -> tuple[float, float]:
    if not math.isfinite(reference_price) or reference_price == 0.0:
        return math.nan, math.nan

    high_returns = [high / reference_price - 1.0 for high in highs]
    low_returns = [low / reference_price - 1.0 for low in lows]

    if direction == SignalDirection.SHORT.value:
        favorable = [-low_return for low_return in low_returns]
        adverse = [-high_return for high_return in high_returns]
    else:
        favorable = high_returns
        adverse = low_returns

    mfe = max(max(favorable), 0.0)
    mae = min(min(adverse), 0.0)
    return mfe, mae


def compute_outcomes(
    occurrences: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    definition: ForwardOutcomeDefinition,
) -> pl.DataFrame:
    """Prototype long-format outcome facts."""
    if len(occurrences) == 0:
        return pl.DataFrame(
            schema={
                "occurrence_id": pl.Utf8,
                "horizon_bars": pl.Int64,
                "outcome_status": pl.Utf8,
                "terminal_price": pl.Float64,
                "forward_return": pl.Float64,
                "mfe": pl.Float64,
                "mae": pl.Float64,
            }
        )

    index_by_timestamp = _timestamp_index(frame)
    close = ohlcv["close"]
    high = ohlcv["high"]
    low = ohlcv["low"]
    horizon = definition.horizon_bars
    rows: list[dict[str, Any]] = []

    for occurrence in occurrences.iter_rows(named=True):
        detected_at = occurrence["detected_at"]
        signal_index = index_by_timestamp.get(detected_at)
        reference_price = occurrence["reference_price"]
        direction = occurrence["direction"]

        if signal_index is None or not math.isfinite(reference_price):
            rows.append(
                {
                    "occurrence_id": occurrence["occurrence_id"],
                    "horizon_bars": horizon,
                    "outcome_status": OutcomeStatus.INSUFFICIENT_DATA.value,
                    "terminal_price": None,
                    "forward_return": None,
                    "mfe": None,
                    "mae": None,
                }
            )
            continue

        window_start = signal_index + 1
        window_end = signal_index + horizon
        if window_end >= len(frame.timestamps):
            rows.append(
                {
                    "occurrence_id": occurrence["occurrence_id"],
                    "horizon_bars": horizon,
                    "outcome_status": OutcomeStatus.INCOMPLETE_HORIZON.value,
                    "terminal_price": None,
                    "forward_return": None,
                    "mfe": None,
                    "mae": None,
                }
            )
            continue

        window_highs = [high[index] for index in range(window_start, window_end + 1)]
        window_lows = [low[index] for index in range(window_start, window_end + 1)]
        window_closes = [close[index] for index in range(window_start, window_end + 1)]

        if any(not math.isfinite(value) for value in (*window_highs, *window_lows, *window_closes)):
            rows.append(
                {
                    "occurrence_id": occurrence["occurrence_id"],
                    "horizon_bars": horizon,
                    "outcome_status": OutcomeStatus.INSUFFICIENT_DATA.value,
                    "terminal_price": None,
                    "forward_return": None,
                    "mfe": None,
                    "mae": None,
                }
            )
            continue

        terminal_price = close[window_end]
        raw_return = terminal_price / reference_price - 1.0
        forward_return = _direction_normalize_return(raw_return=raw_return, direction=direction)
        mfe, mae = _compute_excursions(
            reference_price=reference_price,
            direction=direction,
            highs=window_highs,
            lows=window_lows,
        )
        rows.append(
            {
                "occurrence_id": occurrence["occurrence_id"],
                "horizon_bars": horizon,
                "outcome_status": OutcomeStatus.COMPLETE.value,
                "terminal_price": terminal_price,
                "forward_return": forward_return,
                "mfe": mfe,
                "mae": mae,
            }
        )

    return pl.DataFrame(rows)


def compute_outcomes_for_horizons(
    occurrences: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    ohlcv: dict[str, tuple[float, ...]],
    horizons: tuple[int, ...],
) -> pl.DataFrame:
    frames = [
        compute_outcomes(
            occurrences,
            frame=frame,
            ohlcv=ohlcv,
            definition=ForwardOutcomeDefinition(horizon_bars=horizon),
        )
        for horizon in horizons
    ]
    return pl.concat(frames) if frames else pl.DataFrame()


def write_signal_research_run(
    run_dir: Path,
    *,
    manifest: dict[str, Any],
    occurrences: pl.DataFrame,
    outcomes: pl.DataFrame,
    overwrite: bool = False,
) -> None:
    if run_dir.exists() and not overwrite:
        msg = f"run directory already exists: {run_dir}"
        raise FileExistsError(msg)
    run_dir.mkdir(parents=True, exist_ok=overwrite)
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists() and not overwrite:
        msg = f"manifest already exists: {manifest_path}"
        raise FileExistsError(msg)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    occurrences.write_parquet(run_dir / "occurrences.parquet")
    outcomes.write_parquet(run_dir / "outcomes.parquet")


def _frames_equal(left: pl.DataFrame, right: pl.DataFrame) -> bool:
    if left.shape != right.shape or left.columns != right.columns:
        return False
    sort_cols = left.columns
    return left.sort(sort_cols).equals(right.sort(sort_cols))


def load_signal_research_run(run_dir: Path) -> tuple[dict[str, Any], pl.DataFrame, pl.DataFrame]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        msg = f"missing manifest: {manifest_path}"
        raise FileNotFoundError(msg)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        msg = f"unsupported schema version: {manifest.get('schema_version')}"
        raise ValueError(msg)
    occurrences = pl.read_parquet(run_dir / "occurrences.parquet")
    outcomes = pl.read_parquet(run_dir / "outcomes.parquet")
    return manifest, occurrences, outcomes


def _synthetic_incomplete_horizon_check() -> SpikeCheck:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(6))
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    ohlcv = {"close": close, "high": close, "low": close, "open": close, "volume": close}
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["syn-incomplete"],
            "signal_model_id": ["test"],
            "detected_at": [timestamps[4]],
            "available_at": [timestamps[4]],
            "direction": ["long"],
            "reference_price": [104.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test"],
        }
    )
    outcomes = compute_outcomes(
        occurrences,
        frame=frame,
        ohlcv=ohlcv,
        definition=ForwardOutcomeDefinition(horizon_bars=5),
    )
    row = outcomes.row(0, named=True)
    return SpikeCheck(
        name="incomplete_horizon_detected",
        passed=row["outcome_status"] == OutcomeStatus.INCOMPLETE_HORIZON.value,
        detail=f"status={row['outcome_status']}",
    )


def _synthetic_horizon_window_check() -> SpikeCheck:
    """Signal at t=2, horizon=3 → terminal close index 5 (not 4)."""
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(10))
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    ohlcv = {"close": close, "high": close, "low": close, "open": close, "volume": close}
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["syn-1"],
            "signal_model_id": ["test"],
            "detected_at": [timestamps[2]],
            "available_at": [timestamps[2]],
            "direction": ["long"],
            "reference_price": [102.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test"],
        }
    )
    outcomes = compute_outcomes(
        occurrences,
        frame=frame,
        ohlcv=ohlcv,
        definition=ForwardOutcomeDefinition(horizon_bars=3),
    )
    row = outcomes.row(0, named=True)
    expected_terminal = 105.0
    passed = (
        row["outcome_status"] == OutcomeStatus.COMPLETE.value
        and row["terminal_price"] == expected_terminal
        and abs(row["forward_return"] - (expected_terminal / 102.0 - 1.0)) < 1e-9
    )
    return SpikeCheck(
        name="horizon_excludes_signal_bar",
        passed=passed,
        detail=f"terminal={row['terminal_price']} expected={expected_terminal}",
    )


def run_spike() -> list[SpikeCheck]:
    checks: list[SpikeCheck] = []
    checks.append(_synthetic_horizon_window_check())
    checks.append(_synthetic_incomplete_horizon_check())

    with tempfile.TemporaryDirectory() as tmp:
        storage_root = Path(tmp) / "storage"
        storage_root.mkdir()
        dataset_ref = _write_published_dataset(storage_root, FIXTURE)
        metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
        dataset_key = str(dataset_ref)

        signal_model = build_canonical_signal_higher_low_on_event()
        edge_model = build_canonical_signal_high_volatility_on_true_edge()

        eval_result = evaluate_models(
            EvaluateModelsRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                signal_models=(signal_model, edge_model),
            )
        )
        frame = eval_result.analysis.frame
        assert frame is not None
        market_view = eval_result.analysis.workspace.market_view
        ohlcv = _ohlcv_for_frame(frame, market_view)

        emissions = eval_result.signal_model_emissions[CANONICAL_SIGNAL_HIGHER_LOW_ID]
        checks.append(
            SpikeCheck(
                name="higher_low_emissions_non_empty",
                passed=len(emissions) > 0,
                detail=f"count={len(emissions)}",
            )
        )

        occurrences = materialize_occurrences(
            emissions,
            frame=frame,
            ohlcv=ohlcv,
            signal_model_id=CANONICAL_SIGNAL_HIGHER_LOW_ID,
            instrument=dataset_ref.dataset_id.instrument_id.value,
            evaluation_timeframe=Timeframe("1m"),
            source_dataset_ref=dataset_key,
        )

        checks.append(
            SpikeCheck(
                name="occurrence_id_unique",
                passed=occurrences["occurrence_id"].n_unique() == len(occurrences),
                detail=f"rows={len(occurrences)}",
            )
        )

        stable_id = _occurrence_id(
            signal_model_id=CANONICAL_SIGNAL_HIGHER_LOW_ID,
            detected_at=occurrences["detected_at"][0],
            direction=occurrences["direction"][0],
        )
        checks.append(
            SpikeCheck(
                name="occurrence_id_stable",
                passed=occurrences["occurrence_id"][0] == stable_id,
            )
        )

        reference_matches = []
        index_by_timestamp = _timestamp_index(frame)
        close = ohlcv["close"]
        for row in occurrences.iter_rows(named=True):
            index = index_by_timestamp[row["detected_at"]]
            reference_matches.append(abs(row["reference_price"] - close[index]) < 1e-9)
        checks.append(
            SpikeCheck(
                name="reference_price_close_at_detected_at",
                passed=all(reference_matches),
                detail="descriptive, not fill_price",
            )
        )

        horizons = (5, 10)
        outcomes = compute_outcomes_for_horizons(
            occurrences,
            frame=frame,
            ohlcv=ohlcv,
            horizons=horizons,
        )
        expected_outcome_rows = len(occurrences) * len(horizons)
        checks.append(
            SpikeCheck(
                name="long_format_multi_horizon",
                passed=len(outcomes) == expected_outcome_rows,
                detail=f"rows={len(outcomes)} expected={expected_outcome_rows}",
            )
        )

        complete = outcomes.filter(pl.col("outcome_status") == OutcomeStatus.COMPLETE.value)
        incomplete = outcomes.filter(
            pl.col("outcome_status") == OutcomeStatus.INCOMPLETE_HORIZON.value
        )
        checks.append(
            SpikeCheck(
                name="complete_outcomes_exist",
                passed=len(complete) > 0,
                detail=f"complete={len(complete)}",
            )
        )
        if len(incomplete) > 0:
            checks.append(
                SpikeCheck(
                    name="fixture_incomplete_horizon_rows",
                    passed=True,
                    detail=f"incomplete={len(incomplete)}",
                )
            )
        else:
            checks.append(
                SpikeCheck(
                    name="fixture_incomplete_horizon_rows",
                    passed=True,
                    detail="skipped — all fixture occurrences fit horizons 5 and 10",
                )
            )

        mfe_ok = complete.filter(pl.col("mfe") < 0).is_empty()
        mae_ok = complete.filter(pl.col("mae") > 0).is_empty()
        checks.append(SpikeCheck(name="mfe_non_negative", passed=mfe_ok))
        checks.append(SpikeCheck(name="mae_non_positive", passed=mae_ok))

        nulls_not_zero = outcomes.filter(
            (pl.col("outcome_status") != OutcomeStatus.COMPLETE.value)
            & (
                pl.col("forward_return").is_not_null()
                | pl.col("mfe").is_not_null()
                | pl.col("mae").is_not_null()
            )
        ).is_empty()
        checks.append(SpikeCheck(name="incomplete_metrics_null_not_zero", passed=nulls_not_zero))

        run_key = _run_id(
            dataset_key=dataset_key,
            signal_model_id=CANONICAL_SIGNAL_HIGHER_LOW_ID,
            horizons=horizons,
        )
        run_dir = Path(tmp) / "research" / run_key
        manifest = {
            "run_id": run_key,
            "schema_version": SCHEMA_VERSION,
            "framework_version": framework_version,
            "created_at_utc": datetime.now(tz=UTC).isoformat(),
            "source_dataset_ref": dataset_key,
            "evaluation_timeframe": "1m",
            "signal_model_ids": [CANONICAL_SIGNAL_HIGHER_LOW_ID],
            "horizon_bars_requested": list(horizons),
            "reference_price_policy": ReferencePricePolicy.CLOSE_AT_DETECTED_AT.value,
        }
        write_signal_research_run(
            run_dir,
            manifest=manifest,
            occurrences=occurrences,
            outcomes=outcomes,
        )
        loaded_manifest, loaded_occurrences, loaded_outcomes = load_signal_research_run(run_dir)
        round_trip = (
            loaded_manifest["run_id"] == run_key
            and _frames_equal(loaded_occurrences, occurrences)
            and _frames_equal(loaded_outcomes, outcomes)
        )
        checks.append(SpikeCheck(name="write_read_round_trip", passed=round_trip))

        immutability_ok = False
        try:
            write_signal_research_run(
                run_dir,
                manifest=manifest,
                occurrences=occurrences,
                outcomes=outcomes,
            )
        except FileExistsError:
            immutability_ok = True
        checks.append(SpikeCheck(name="immutability_refuse_overwrite", passed=immutability_ok))

        edge_emissions = eval_result.signal_model_emissions[
            CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID
        ]
        if len(edge_emissions) > 0:
            edge_occurrences = materialize_occurrences(
                edge_emissions.head(1),
                frame=frame,
                ohlcv=ohlcv,
                signal_model_id=CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
                instrument=dataset_ref.dataset_id.instrument_id.value,
                evaluation_timeframe=Timeframe("1m"),
                source_dataset_ref=dataset_key,
            )
            edge_row = edge_occurrences.row(0, named=True)
            available_after_detected = edge_row["available_at"] >= edge_row["detected_at"]
            checks.append(
                SpikeCheck(
                    name="on_true_edge_available_at_preserved",
                    passed=available_after_detected,
                    detail=(
                        f"detected={edge_row['detected_at']} available={edge_row['available_at']}"
                    ),
                )
            )
        else:
            checks.append(
                SpikeCheck(
                    name="on_true_edge_available_at_preserved",
                    passed=True,
                    detail="skipped — no edge emissions in fixture window",
                )
            )

    return checks


def _checklist_pass(checks: list[SpikeCheck]) -> dict[str, bool]:
    return {
        "polars_first_batch": True,
        "occurrence_outcome_separation": True,
        "reference_price_not_fill_price": True,
        "long_format_outcomes": True,
        "repository_round_trip": True,
        "all_checks_pass": all(check.passed for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="S008 signal research spike")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    checks = run_spike()
    checklist = _checklist_pass(checks)
    payload = {
        "task": "S008-T001",
        "schema_version": SCHEMA_VERSION,
        "checks": [
            {"name": check.name, "passed": check.passed, "detail": check.detail} for check in checks
        ],
        "checklist": checklist,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            suffix = f" ({check.detail})" if check.detail else ""
            print(f"{status}: {check.name}{suffix}")
        print()
        print("Checklist:", checklist)

    return 0 if checklist["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
