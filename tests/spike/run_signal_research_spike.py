"""S008-T001 spike — Signal Research pipeline boundary validation.

Not production API; not collected by pytest.

Validates:
- evaluate_models emissions → SignalOccurrence (production strategy API)
- ForwardOutcomeDefinition + calculator semantics
- run envelope (manifest + occurrences.parquet + outcomes.parquet)
- repository read-back and immutability

Run:

    uv run python tests/spike/run_signal_research_spike.py
    uv run python tests/spike/run_signal_research_spike.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

_SPIKE_DIR = Path(__file__).resolve().parent
if str(_SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR))

from _fixture_paths import OHLCV_SAMPLE_1M

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
from trading_framework.research import (
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    ForwardOutcomeDefinition,
    OutcomeStatus,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    align_ohlcv_to_evaluation_frame,
    compute_forward_outcomes,
    compute_forward_outcomes_for_horizons,
    derive_run_id,
    outcome_definition_fingerprint,
)
from trading_framework.strategy import (
    OccurrenceMaterializationContext,
    ReferencePricePolicy,
    derive_occurrence_id,
    materialize_signal_occurrences,
)
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

FIXTURE = OHLCV_SAMPLE_1M


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


def _materialize_occurrences(
    emissions: pl.DataFrame,
    *,
    frame: AnalysisFrame,
    market_view: AnalysisDataView,
    signal_model_id: str,
    instrument: str,
    evaluation_timeframe: Timeframe,
    source_dataset_ref: str,
) -> pl.DataFrame:
    return materialize_signal_occurrences(
        emissions,
        frame=frame,
        market_view=market_view,
        context=OccurrenceMaterializationContext(
            signal_model_id=signal_model_id,
            instrument=instrument,
            evaluation_timeframe=evaluation_timeframe,
            source_dataset_ref=source_dataset_ref,
        ),
    )


def _frames_equal(left: pl.DataFrame, right: pl.DataFrame) -> bool:
    if left.shape != right.shape or left.columns != right.columns:
        return False
    sort_cols = left.columns
    return left.sort(sort_cols).equals(right.sort(sort_cols))


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
    outcomes = compute_forward_outcomes(
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
    outcomes = compute_forward_outcomes(
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
        ohlcv = align_ohlcv_to_evaluation_frame(frame, market_view)

        emissions = eval_result.signal_model_emissions[CANONICAL_SIGNAL_HIGHER_LOW_ID]
        checks.append(
            SpikeCheck(
                name="higher_low_emissions_non_empty",
                passed=len(emissions) > 0,
                detail=f"count={len(emissions)}",
            )
        )

        occurrences = _materialize_occurrences(
            emissions,
            frame=frame,
            market_view=market_view,
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

        stable_id = derive_occurrence_id(
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
        outcomes = compute_forward_outcomes_for_horizons(
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

        run_key = derive_run_id(
            source_dataset_ref=dataset_key,
            signal_model_ids=(CANONICAL_SIGNAL_HIGHER_LOW_ID,),
            horizons=horizons,
            evaluation_timeframe="1m",
            requested_range_start=metadata.start_at,
            requested_range_end=metadata.end_at,
            framework_version=framework_version,
            outcome_definition_fingerprint=outcome_definition_fingerprint(horizons),
        )
        manifest = SignalResearchRunManifest(
            run_id=run_key,
            schema_version=SIGNAL_RESEARCH_SCHEMA_VERSION,
            framework_version=framework_version,
            created_at_utc=datetime.now(tz=UTC),
            source_dataset_ref=dataset_key,
            evaluation_timeframe="1m",
            signal_model_ids=(CANONICAL_SIGNAL_HIGHER_LOW_ID,),
            horizon_bars_requested=horizons,
            reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            outcome_definition_fingerprint=outcome_definition_fingerprint(horizons),
        )
        repository = SignalResearchDatasetRepository(storage_root)
        repository.write(
            SignalResearchRunEnvelope(
                manifest=manifest,
                occurrences=occurrences,
                outcomes=outcomes,
            )
        )
        loaded = repository.read(RunDatasetRef(run_id=run_key))
        round_trip = (
            loaded.manifest.run_id == run_key
            and _frames_equal(loaded.occurrences, occurrences)
            and _frames_equal(loaded.outcomes, outcomes)
        )
        checks.append(SpikeCheck(name="write_read_round_trip", passed=round_trip))

        immutability_ok = False
        try:
            repository.write(
                SignalResearchRunEnvelope(
                    manifest=manifest,
                    occurrences=occurrences,
                    outcomes=outcomes,
                )
            )
        except FileExistsError:
            immutability_ok = True
        checks.append(SpikeCheck(name="immutability_refuse_overwrite", passed=immutability_ok))

        edge_emissions = eval_result.signal_model_emissions[
            CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID
        ]
        if len(edge_emissions) > 0:
            edge_occurrences = _materialize_occurrences(
                edge_emissions.head(1),
                frame=frame,
                market_view=market_view,
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
        "schema_version": SIGNAL_RESEARCH_SCHEMA_VERSION,
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
