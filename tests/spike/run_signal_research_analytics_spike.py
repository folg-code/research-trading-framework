"""S010-T001 spike — Signal Research analytics boundary validation.

Not production API; not collected by pytest.

Validates Wave 0 binding decisions before Wave 1 ``research/analytics/`` contracts:

- scope-aware analysis frame (entity_id + entity_kind)
- RunSummary with COMPLETE filter and sample diagnostics
- RTH_MEMBERSHIP and TIME_OF_DAY grouping
- conditional comparison on context_met (MARKET_AND_SIGNAL)
- metrics_eligible semantics
- read-only boundary (no model evaluation in analytics module)

Run:

    uv run python tests/spike/run_signal_research_analytics_spike.py
    uv run python tests/spike/run_signal_research_analytics_spike.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import polars as pl

_SPIKE_DIR = Path(__file__).resolve().parent
if str(_SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR))

from _fixture_paths import OHLCV_SAMPLE_1M
from _signal_research_analytics_spike import assert_read_only_analytics_package

from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
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
from trading_framework.research import ResearchScope, RunDatasetRef, SignalResearchDatasetRepository
from trading_framework.research.analytics import (
    ENTITY_KIND_OBSERVATION,
    ENTITY_KIND_SIGNAL,
    AnalyticsTimestampBasis,
    GroupDimension,
    OutcomeAnalyticsFilter,
    build_analysis_frame,
    compute_conditional_comparison,
    compute_grouped_summary,
    compute_run_summary,
)
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

FIXTURE = OHLCV_SAMPLE_1M
FIXTURE_VOLATILITY_THRESHOLD = 0.5
HORIZON = 5


@dataclass(frozen=True, slots=True)
class SpikeCheck:
    name: str
    passed: bool
    detail: str = ""


def _write_published_dataset(storage_root: Path, csv_path: Path) -> DatasetRef:
    from datetime import UTC

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
        source_id="s010-analytics-spike",
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


def _run_scope(
    *,
    storage_root: Path,
    dataset_ref: DatasetRef,
    requested_range: TimeRange,
    scope: ResearchScope,
) -> RunDatasetRef:
    market_model = build_canonical_market_model_high_volatility(
        threshold=FIXTURE_VOLATILITY_THRESHOLD
    )
    signal_model = build_canonical_signal_higher_low_on_event()
    if scope is ResearchScope.SIGNAL_MODEL_ONLY:
        request = RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            signal_models=(signal_model,),
            horizons=(HORIZON,),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    elif scope is ResearchScope.MARKET_MODEL_ONLY:
        request = RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            scope=scope,
            market_models=(market_model,),
            signal_models=(),
            horizons=(HORIZON,),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    else:
        request = RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            scope=ResearchScope.MARKET_AND_SIGNAL,
            market_models=(market_model,),
            signal_models=(signal_model,),
            horizons=(HORIZON,),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    result = run_signal_research(request)
    return result.run_ref


def run_checks() -> list[SpikeCheck]:
    checks: list[SpikeCheck] = []

    try:
        assert_read_only_analytics_package()
        read_only_ok = True
        read_only_detail = "no forbidden compute imports in research/analytics package"
    except Exception as exc:
        read_only_ok = False
        read_only_detail = str(exc)
    checks.append(
        SpikeCheck(name="read_only_analytics_module", passed=read_only_ok, detail=read_only_detail)
    )

    with tempfile.TemporaryDirectory() as tmp:
        storage_root = Path(tmp) / "storage"
        storage_root.mkdir()
        dataset_ref = _write_published_dataset(storage_root, FIXTURE)
        metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
        requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
        repository = SignalResearchDatasetRepository(storage_root)

        signal_ref = _run_scope(
            storage_root=storage_root,
            dataset_ref=dataset_ref,
            requested_range=requested_range,
            scope=ResearchScope.SIGNAL_MODEL_ONLY,
        )
        market_ref = _run_scope(
            storage_root=storage_root,
            dataset_ref=dataset_ref,
            requested_range=requested_range,
            scope=ResearchScope.MARKET_MODEL_ONLY,
        )
        combined_ref = _run_scope(
            storage_root=storage_root,
            dataset_ref=dataset_ref,
            requested_range=requested_range,
            scope=ResearchScope.MARKET_AND_SIGNAL,
        )

        signal_envelope = repository.read(signal_ref)
        market_envelope = repository.read(market_ref)
        combined_envelope = repository.read(combined_ref)

        signal_frame = build_analysis_frame(signal_envelope)
        market_frame = build_analysis_frame(market_envelope)
        combined_frame = build_analysis_frame(combined_envelope)

        signal_summary_df = compute_run_summary(
            signal_frame, horizon_bars=HORIZON, min_sample_size=1
        )
        signal_summary = signal_summary_df.row(0, named=True)
        checks.append(
            SpikeCheck(
                name="signal_only_v1_run_summary",
                passed=(
                    signal_summary["sample_size_complete"] > 0
                    and signal_summary["metrics_eligible"]
                    and signal_summary["hit_rate"] is not None
                    and 0.0 <= signal_summary["hit_rate"] <= 1.0
                ),
                detail=(
                    f"complete={signal_summary['sample_size_complete']} "
                    f"hit_rate={signal_summary['hit_rate']}"
                ),
            )
        )
        checks.append(
            SpikeCheck(
                name="signal_only_entity_kind",
                passed=signal_frame["entity_kind"].unique().to_list() == [ENTITY_KIND_SIGNAL],
                detail=f"kinds={signal_frame['entity_kind'].unique().to_list()}",
            )
        )

        market_summary = compute_run_summary(
            market_frame, horizon_bars=HORIZON, min_sample_size=1
        ).row(0, named=True)
        checks.append(
            SpikeCheck(
                name="market_only_run_summary",
                passed=(
                    market_summary["sample_size_complete"] > 0
                    and market_summary["metrics_eligible"]
                ),
                detail=f"complete={market_summary['sample_size_complete']}",
            )
        )
        checks.append(
            SpikeCheck(
                name="market_only_entity_kind",
                passed=market_frame["entity_kind"].unique().to_list() == [ENTITY_KIND_OBSERVATION],
                detail=f"kinds={market_frame['entity_kind'].unique().to_list()}",
            )
        )

        incomplete_count = combined_frame.filter(
            pl.col("outcome_status") != OutcomeStatus.COMPLETE.value
        ).height
        combined_summary = compute_run_summary(
            combined_frame, horizon_bars=HORIZON, min_sample_size=1
        ).row(0, named=True)
        completion_ok = (
            combined_summary["sample_size_total"]
            == combined_summary["sample_size_complete"] + combined_summary["sample_size_incomplete"]
        )
        checks.append(
            SpikeCheck(
                name="complete_filter_sample_diagnostics",
                passed=completion_ok and combined_summary["sample_size_complete"] > 0,
                detail=(
                    f"total={combined_summary['sample_size_total']} "
                    f"complete={combined_summary['sample_size_complete']} "
                    f"incomplete={combined_summary['sample_size_incomplete']} "
                    f"raw_incomplete_rows={incomplete_count}"
                ),
            )
        )

        conditional = compute_conditional_comparison(combined_frame, horizon_bars=HORIZON).row(
            0, named=True
        )
        split_total = (
            conditional["context_true_sample_size"]
            + conditional["context_false_sample_size"]
            + conditional["context_missing_sample_size"]
        )
        checks.append(
            SpikeCheck(
                name="conditional_context_split",
                passed=(
                    conditional["context_false_sample_size"] > 0
                    and split_total == combined_summary["sample_size_complete"]
                ),
                detail=(
                    f"true={conditional['context_true_sample_size']} "
                    f"false={conditional['context_false_sample_size']} "
                    f"missing={conditional['context_missing_sample_size']} "
                    f"status={conditional['comparison_status']}"
                ),
            )
        )
        checks.append(
            SpikeCheck(
                name="conditional_delta_direction",
                passed=(
                    conditional["forward_return_mean_delta"] is None
                    or conditional["forward_return_mean_true"] is not None
                ),
                detail=f"delta={conditional['forward_return_mean_delta']}",
            )
        )

        rth_groups = compute_grouped_summary(
            combined_frame,
            horizon_bars=HORIZON,
            dimension=GroupDimension.RTH_MEMBERSHIP,
            min_sample_size=1,
            outcome_filter=OutcomeAnalyticsFilter.complete_only(),
            timestamp_basis=AnalyticsTimestampBasis.AVAILABLE_AT,
        )
        checks.append(
            SpikeCheck(
                name="rth_membership_grouping",
                passed=len(rth_groups) >= 2,
                detail=f"buckets={rth_groups['group_value'].to_list()}",
            )
        )

        tod_groups = compute_grouped_summary(
            combined_frame,
            horizon_bars=HORIZON,
            dimension=GroupDimension.TIME_OF_DAY,
            min_sample_size=1,
            outcome_filter=OutcomeAnalyticsFilter.complete_only(),
            timestamp_basis=AnalyticsTimestampBasis.AVAILABLE_AT,
        )
        checks.append(
            SpikeCheck(
                name="time_of_day_grouping",
                passed=len(tod_groups) >= 2,
                detail=f"bucket_count={len(tod_groups)}",
            )
        )

        ineligible = compute_run_summary(
            combined_frame,
            horizon_bars=HORIZON,
            min_sample_size=999_999,
        ).row(0, named=True)
        checks.append(
            SpikeCheck(
                name="metrics_eligible_false_path",
                passed=(
                    not ineligible["metrics_eligible"]
                    and ineligible["forward_return_mean"] is None
                    and ineligible["sample_size_complete"] > 0
                ),
                detail=(
                    f"eligible={ineligible['metrics_eligible']} "
                    f"complete={ineligible['sample_size_complete']}"
                ),
            )
        )

        naive_mean = combined_frame.filter(
            pl.col("outcome_status") == OutcomeStatus.COMPLETE.value
        )["forward_return"].mean()
        filtered_mean = combined_summary["forward_return_mean"]
        checks.append(
            SpikeCheck(
                name="complete_only_mean_semantics",
                passed=filtered_mean == naive_mean,
                detail=f"summary_mean={filtered_mean} naive_complete_mean={naive_mean}",
            )
        )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Signal Research analytics Wave 0 spike")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = run_checks()
    all_passed = all(check.passed for check in checks)

    if args.json:
        payload = {
            "all_checks_pass": all_passed,
            "checks": [
                {"name": check.name, "passed": check.passed, "detail": check.detail}
                for check in checks
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            detail = f" ({check.detail})" if check.detail else ""
            print(f"{status}: {check.name}{detail}")
        print(f"\nChecklist: all_checks_pass={all_passed}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
