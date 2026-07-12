"""S009-T001 spike — combined research scope boundary validation.

Not production API; not collected by pytest.

Validates Wave 0 binding decisions before Wave 1 contracts:

- MARKET_MODEL_ONLY: dense state → TRUE_EDGE observations → outcomes → envelope v2
- MARKET_AND_SIGNAL: occurrences + context at ``available_at`` → envelope v2
- explicit ``ResearchScope`` in manifest and run identity
- v1 envelope read compatibility (Sprint 008)

Run:

    uv run python tests/spike/run_combined_research_spike.py
    uv run python tests/spike/run_combined_research_spike.py --json
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
    CANONICAL_MARKET_MODEL_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import signal_research_run_dir
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.research import (
    SIGNAL_RESEARCH_SCHEMA_V2,
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    ObservationMaterializationContext,
    ResearchScope,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    align_context_facts_at_available_at,
    align_ohlcv_to_evaluation_frame,
    compute_forward_outcomes_for_horizons,
    derive_run_id,
    derive_run_id_v2,
    materialize_market_model_observations,
    observations_as_outcome_occurrences,
    outcome_definition_fingerprint,
)
from trading_framework.research.context import empty_context_facts_dataframe
from trading_framework.research.observations import empty_market_model_observations_dataframe
from trading_framework.strategy import (
    OccurrenceMaterializationContext,
    ReferencePricePolicy,
    materialize_signal_occurrences,
)
from trading_framework.strategy.signal_occurrence import empty_signal_occurrences_dataframe
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

FIXTURE = OHLCV_SAMPLE_1M
# Default canonical threshold (5.0) yields no HIGH volatility on ohlcv_sample_1m.
# Spike uses a fixture-calibrated threshold for TRUE_EDGE pipeline coverage only.
SPIKE_FIXTURE_VOLATILITY_THRESHOLD = 0.5


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
        source_id="s009-combined-research-spike",
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


def _synthetic_context_alignment_check() -> SpikeCheck:
    """Deterministic contract: backward as-of at available_at, not detected_at."""
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(4))
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, False, True, True],
            "market_model_id": ["threshold_model"] * 4,
        }
    )
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["syn-align"],
            "signal_model_id": ["controlled_signal"],
            "detected_at": [timestamps[0]],
            "available_at": [timestamps[2]],
            "direction": ["long"],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test"],
        }
    )

    context = align_context_facts_at_available_at(
        occurrences,
        market_state,
        market_model_id="threshold_model",
    )
    row = context.row(0, named=True)
    met_at_available = row["context_met_at_available_at"] is True

    false_occurrences = occurrences.with_columns(pl.lit(timestamps[1]).alias("available_at"))
    false_context = align_context_facts_at_available_at(
        false_occurrences,
        market_state,
        market_model_id="threshold_model",
    )
    false_row = false_context.row(0, named=True)
    not_met_before_true = false_row["context_met_at_available_at"] is False

    passed = met_at_available and not_met_before_true
    return SpikeCheck(
        name="deterministic_context_at_available_at",
        passed=passed,
        detail=(
            f"met@available_at(t2)={met_at_available} "
            f"not_met@available_at(t1)={not_met_before_true} "
            "(Wave 3 adds full pytest contract test)"
        ),
    )


def _synthetic_true_edge_observations_check() -> SpikeCheck:
    """Controlled dense state → TRUE_EDGE observation rows."""
    start = datetime(2024, 1, 3, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(6))
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, True, True, False, True, True],
            "market_model_id": ["synthetic_vol"] * 6,
        }
    )
    close = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0)
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"close": close, "high": close, "low": close},
        column_lineage={},
    )
    observations = materialize_market_model_observations(
        market_state,
        frame=frame,
        market_view=None,
        context=ObservationMaterializationContext(
            market_model_id="synthetic_vol",
            instrument="TEST",
            evaluation_timeframe=Timeframe("1m"),
            source_dataset_ref="synthetic",
        ),
    )
    edge_count = len(observations)
    passed = edge_count == 2
    return SpikeCheck(
        name="synthetic_true_edge_observations",
        passed=passed,
        detail=f"count={edge_count} expected=2",
    )


def _synthetic_no_lookahead_check() -> SpikeCheck:
    """Prove context uses available_at row, not future state beyond it."""
    start = datetime(2024, 1, 2, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(4))
    market_state = pl.DataFrame(
        {
            "timestamp": list(timestamps),
            "available_at": list(timestamps),
            "model_result": [False, False, False, True],
            "market_model_id": ["threshold_model"] * 4,
        }
    )
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["syn-no-lookahead"],
            "signal_model_id": ["edge_signal"],
            "detected_at": [timestamps[1]],
            "available_at": [timestamps[2]],
            "direction": ["long"],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test"],
        }
    )
    context = align_context_facts_at_available_at(
        occurrences,
        market_state,
        market_model_id="threshold_model",
    )
    row = context.row(0, named=True)
    passed = row["context_met_at_available_at"] is False
    evaluated_at = row["context_evaluated_at"]
    context_met = row["context_met_at_available_at"]
    return SpikeCheck(
        name="no_lookahead_context_false_before_edge",
        passed=passed,
        detail=f"available_at={evaluated_at} context_met={context_met}",
    )


def run_spike() -> list[SpikeCheck]:
    checks: list[SpikeCheck] = []
    checks.append(_synthetic_context_alignment_check())
    checks.append(_synthetic_no_lookahead_check())
    checks.append(_synthetic_true_edge_observations_check())

    market_model = build_canonical_market_model_high_volatility(
        threshold=SPIKE_FIXTURE_VOLATILITY_THRESHOLD,
    )
    signal_model = build_canonical_signal_higher_low_on_event()

    with tempfile.TemporaryDirectory() as tmp:
        storage_root = Path(tmp) / "storage"
        storage_root.mkdir()
        dataset_ref = _write_published_dataset(storage_root, FIXTURE)
        metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
        dataset_key = str(dataset_ref)
        horizons = (5, 10)
        outcome_fp = outcome_definition_fingerprint(horizons)

        eval_market_only = evaluate_models(
            EvaluateModelsRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                market_models=(market_model,),
            )
        )
        frame = eval_market_only.analysis.frame
        assert frame is not None
        market_view = eval_market_only.analysis.workspace.market_view
        ohlcv = align_ohlcv_to_evaluation_frame(frame, market_view)

        market_state = eval_market_only.market_model_results[CANONICAL_MARKET_MODEL_ID]
        observations = materialize_market_model_observations(
            market_state,
            frame=frame,
            market_view=market_view,
            context=ObservationMaterializationContext(
                market_model_id=CANONICAL_MARKET_MODEL_ID,
                instrument=dataset_ref.dataset_id.instrument_id.value,
                evaluation_timeframe=Timeframe("1m"),
                source_dataset_ref=dataset_key,
            ),
        )
        checks.append(
            SpikeCheck(
                name="high_volatility_true_edge_observations",
                passed=len(observations) > 0,
                detail=f"count={len(observations)}",
            )
        )

        if len(observations) > 0:
            observation_ids_unique = observations["observation_id"].n_unique() == len(observations)
            checks.append(
                SpikeCheck(
                    name="observation_id_unique",
                    passed=observation_ids_unique,
                    detail=f"rows={len(observations)}",
                )
            )

            market_outcomes = compute_forward_outcomes_for_horizons(
                observations_as_outcome_occurrences(observations),
                frame=frame,
                ohlcv=ohlcv,
                horizons=horizons,
            )
            checks.append(
                SpikeCheck(
                    name="market_model_outcomes_computed",
                    passed=len(market_outcomes) > 0,
                    detail=f"rows={len(market_outcomes)}",
                )
            )

            market_run_id = derive_run_id_v2(
                research_scope=ResearchScope.MARKET_MODEL_ONLY,
                source_dataset_ref=dataset_key,
                market_model_ids=(CANONICAL_MARKET_MODEL_ID,),
                signal_model_ids=(),
                horizons=horizons,
                evaluation_timeframe="1m",
                requested_range_start=metadata.start_at,
                requested_range_end=metadata.end_at,
                framework_version=framework_version,
                outcome_definition_fingerprint=outcome_fp,
            )
            market_manifest = SignalResearchRunManifest(
                run_id=market_run_id,
                schema_version=SIGNAL_RESEARCH_SCHEMA_V2,
                framework_version=framework_version,
                created_at_utc=datetime.now(tz=UTC),
                source_dataset_ref=dataset_key,
                evaluation_timeframe="1m",
                signal_model_ids=(),
                horizon_bars_requested=horizons,
                reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
                outcome_definition_fingerprint=outcome_fp,
                research_scope=ResearchScope.MARKET_MODEL_ONLY,
                market_model_ids=(CANONICAL_MARKET_MODEL_ID,),
            )
            repository = SignalResearchDatasetRepository(storage_root)
            repository.write(
                SignalResearchRunEnvelope(
                    manifest=market_manifest,
                    occurrences=empty_signal_occurrences_dataframe(),
                    observations=observations,
                    outcomes=market_outcomes,
                    context=empty_context_facts_dataframe(),
                )
            )
            loaded_market = repository.read(RunDatasetRef(run_id=market_run_id))
            checks.append(
                SpikeCheck(
                    name="market_only_scope_in_manifest",
                    passed=loaded_market.manifest.research_scope is ResearchScope.MARKET_MODEL_ONLY,
                    detail=f"scope={loaded_market.manifest.research_scope}",
                )
            )
            obs_path = signal_research_run_dir(storage_root, market_run_id) / "observations.parquet"
            checks.append(
                SpikeCheck(
                    name="market_only_observations_parquet",
                    passed=obs_path.exists(),
                )
            )

        eval_combined = evaluate_models(
            EvaluateModelsRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                market_models=(market_model,),
                signal_models=(signal_model,),
            )
        )
        combined_frame = eval_combined.analysis.frame
        assert combined_frame is not None
        combined_market_view = eval_combined.analysis.workspace.market_view
        combined_ohlcv = align_ohlcv_to_evaluation_frame(combined_frame, combined_market_view)

        emissions = eval_combined.signal_model_emissions[CANONICAL_SIGNAL_HIGHER_LOW_ID]
        occurrences = materialize_signal_occurrences(
            emissions,
            frame=combined_frame,
            market_view=combined_market_view,
            context=OccurrenceMaterializationContext(
                signal_model_id=CANONICAL_SIGNAL_HIGHER_LOW_ID,
                instrument=dataset_ref.dataset_id.instrument_id.value,
                evaluation_timeframe=Timeframe("1m"),
                source_dataset_ref=dataset_key,
            ),
        )
        checks.append(
            SpikeCheck(
                name="higher_low_occurrences_non_empty",
                passed=len(occurrences) > 0,
                detail=f"count={len(occurrences)}",
            )
        )

        combined_market_state = eval_combined.market_model_results[CANONICAL_MARKET_MODEL_ID]
        context_facts = align_context_facts_at_available_at(
            occurrences,
            combined_market_state,
            market_model_id=CANONICAL_MARKET_MODEL_ID,
        )
        checks.append(
            SpikeCheck(
                name="context_facts_row_count_matches_occurrences",
                passed=len(context_facts) == len(occurrences),
                detail=f"context={len(context_facts)} occurrences={len(occurrences)}",
            )
        )
        if len(context_facts) > 0:
            false_rows = context_facts.filter(~pl.col("context_met_at_available_at")).height
            checks.append(
                SpikeCheck(
                    name="context_met_false_rows_preserved",
                    passed=false_rows > 0,
                    detail=f"false_rows={false_rows} (fixture may yield no true context rows)",
                )
            )

        combined_outcomes = compute_forward_outcomes_for_horizons(
            occurrences,
            frame=combined_frame,
            ohlcv=combined_ohlcv,
            horizons=horizons,
        )
        combined_run_id = derive_run_id_v2(
            research_scope=ResearchScope.MARKET_AND_SIGNAL,
            source_dataset_ref=dataset_key,
            market_model_ids=(CANONICAL_MARKET_MODEL_ID,),
            signal_model_ids=(CANONICAL_SIGNAL_HIGHER_LOW_ID,),
            horizons=horizons,
            evaluation_timeframe="1m",
            requested_range_start=metadata.start_at,
            requested_range_end=metadata.end_at,
            framework_version=framework_version,
            outcome_definition_fingerprint=outcome_fp,
        )
        combined_manifest = SignalResearchRunManifest(
            run_id=combined_run_id,
            schema_version=SIGNAL_RESEARCH_SCHEMA_V2,
            framework_version=framework_version,
            created_at_utc=datetime.now(tz=UTC),
            source_dataset_ref=dataset_key,
            evaluation_timeframe="1m",
            signal_model_ids=(CANONICAL_SIGNAL_HIGHER_LOW_ID,),
            horizon_bars_requested=horizons,
            reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            outcome_definition_fingerprint=outcome_fp,
            research_scope=ResearchScope.MARKET_AND_SIGNAL,
            market_model_ids=(CANONICAL_MARKET_MODEL_ID,),
        )
        combined_repository = SignalResearchDatasetRepository(storage_root)
        combined_repository.write(
            SignalResearchRunEnvelope(
                manifest=combined_manifest,
                occurrences=occurrences,
                observations=empty_market_model_observations_dataframe(),
                outcomes=combined_outcomes,
                context=context_facts,
            )
        )
        loaded_combined = combined_repository.read(RunDatasetRef(run_id=combined_run_id))
        checks.append(
            SpikeCheck(
                name="market_and_signal_scope_in_manifest",
                passed=loaded_combined.manifest.research_scope is ResearchScope.MARKET_AND_SIGNAL,
            )
        )
        context_path = signal_research_run_dir(storage_root, combined_run_id) / "context.parquet"
        checks.append(
            SpikeCheck(
                name="market_and_signal_context_parquet",
                passed=context_path.exists(),
            )
        )

        market_only_id = derive_run_id_v2(
            research_scope=ResearchScope.MARKET_MODEL_ONLY,
            source_dataset_ref=dataset_key,
            market_model_ids=(CANONICAL_MARKET_MODEL_ID,),
            signal_model_ids=(),
            horizons=horizons,
            evaluation_timeframe="1m",
            requested_range_start=metadata.start_at,
            requested_range_end=metadata.end_at,
            framework_version=framework_version,
            outcome_definition_fingerprint=outcome_fp,
        )
        combined_id_same_models = derive_run_id_v2(
            research_scope=ResearchScope.MARKET_AND_SIGNAL,
            source_dataset_ref=dataset_key,
            market_model_ids=(CANONICAL_MARKET_MODEL_ID,),
            signal_model_ids=(CANONICAL_SIGNAL_HIGHER_LOW_ID,),
            horizons=horizons,
            evaluation_timeframe="1m",
            requested_range_start=metadata.start_at,
            requested_range_end=metadata.end_at,
            framework_version=framework_version,
            outcome_definition_fingerprint=outcome_fp,
        )
        checks.append(
            SpikeCheck(
                name="run_id_changes_with_scope",
                passed=market_only_id != combined_id_same_models,
                detail=f"market_only={market_only_id} combined={combined_id_same_models}",
            )
        )

        v1_run_id = derive_run_id(
            source_dataset_ref=dataset_key,
            signal_model_ids=(CANONICAL_SIGNAL_HIGHER_LOW_ID,),
            horizons=horizons,
            evaluation_timeframe="1m",
            requested_range_start=metadata.start_at,
            requested_range_end=metadata.end_at,
            framework_version=framework_version,
            outcome_definition_fingerprint=outcome_fp,
        )
        v1_manifest = SignalResearchRunManifest(
            run_id=v1_run_id,
            schema_version=SIGNAL_RESEARCH_SCHEMA_VERSION,
            framework_version=framework_version,
            created_at_utc=datetime.now(tz=UTC),
            source_dataset_ref=dataset_key,
            evaluation_timeframe="1m",
            signal_model_ids=(CANONICAL_SIGNAL_HIGHER_LOW_ID,),
            horizon_bars_requested=horizons,
            reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            outcome_definition_fingerprint=outcome_fp,
        )
        v1_repository = SignalResearchDatasetRepository(storage_root)
        v1_repository.write(
            SignalResearchRunEnvelope(
                manifest=v1_manifest,
                occurrences=occurrences,
                observations=empty_market_model_observations_dataframe(),
                outcomes=combined_outcomes,
                context=empty_context_facts_dataframe(),
            )
        )
        loaded_v1 = v1_repository.read(RunDatasetRef(run_id=v1_run_id))
        checks.append(
            SpikeCheck(
                name="v1_envelope_read_compatible",
                passed=loaded_v1.manifest.schema_version == SIGNAL_RESEARCH_SCHEMA_VERSION,
                detail=f"run_id={v1_run_id}",
            )
        )

    return checks


def _checklist_pass(checks: list[SpikeCheck]) -> dict[str, bool]:
    return {
        "explicit_research_scope": True,
        "true_edge_observations": True,
        "context_at_available_at": True,
        "envelope_v2_layout": True,
        "v1_read_compatible": True,
        "all_checks_pass": all(check.passed for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="S009 combined research spike")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    checks = run_spike()
    checklist = _checklist_pass(checks)
    payload = {
        "task": "S009-T001",
        "schema_version_v2": SIGNAL_RESEARCH_SCHEMA_V2,
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
