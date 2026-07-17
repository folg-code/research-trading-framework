"""Build six months of NQ continuous data and run Strategy Research."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from trading_framework.application.market_data import (
    build_continuous,
    finalize_dataset,
    publish_dataset,
)
from trading_framework.application.market_data.build_continuous import (
    BuildContinuousRequest,
    BuildContinuousResult,
)
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.observability.function_profiler import FunctionProfiler
from trading_framework.infrastructure.observability.memory_stats import process_rss_mb
from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
from trading_framework.infrastructure.observability.profile_context import phase_timer_context
from trading_framework.infrastructure.storage.metadata.discovery import (
    latest_published_dataset_ref,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.continuous.identity import continuous_instrument_id
from trading_framework.market.continuous.policy import VOLUME_RTH_CLOSE_POLICY_SLUG
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market.derivation import DERIVED_OHLCV_PROVIDER
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import build_canonical_strategy_model
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run half-year continuous build and backtest.")

    parser.add_argument("--storage-root", required=True, type=Path)

    parser.add_argument(
        "--contract-dataset-ref",
        action="append",
        default=None,
        dest="refs",
        help="Contract dataset ref; required unless --skip-build with published continuous OHLCV",
    )

    parser.add_argument("--product", default="NQ")

    parser.add_argument(
        "--policy-slug",
        default=VOLUME_RTH_CLOSE_POLICY_SLUG,
        help="Roll policy slug used to resolve continuous OHLCV when --skip-build",
    )

    parser.add_argument(
        "--continuous-ohlcv-dataset-ref",
        default=None,
        help=(
            "Published continuous OHLCV ref for strategy research "
            "(default: latest published when --skip-build)"
        ),
    )

    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip contract publish and build_continuous; run strategy research only",
    )

    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Run strategy research without writing the run envelope (safe for repeat profiling)",
    )

    parser.add_argument(
        "--profile",
        action="store_true",
        help="Emit per-phase timing report to stderr",
    )

    parser.add_argument(
        "--profile-deep",
        action="store_true",
        help="Enable cProfile function report in addition to phase timings",
    )

    parser.add_argument(
        "--profile-top",
        type=int,
        default=40,
        help="Number of top functions in --profile-deep report",
    )

    parser.add_argument("--json", action="store_true")

    return parser


def _continuous_ohlcv_dataset_id(product: str, policy_slug: str) -> DatasetId:
    return DatasetId(
        instrument_id=continuous_instrument_id(product),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider=DERIVED_OHLCV_PROVIDER,
        source_id=policy_slug,
    )


def resolve_continuous_ohlcv_dataset_ref(
    *,
    storage_root: Path,
    product: str,
    policy_slug: str,
    explicit_ref: str | None,
) -> DatasetRef:
    """Resolve the continuous OHLCV dataset used for strategy research."""
    if explicit_ref is not None:
        return DatasetRef.parse(explicit_ref)

    dataset_ref = latest_published_dataset_ref(
        storage_root,
        _continuous_ohlcv_dataset_id(product, policy_slug),
    )
    if dataset_ref is None:
        msg = (
            f"no published continuous OHLCV dataset for {product} "
            f"(policy={policy_slug}); pass --continuous-ohlcv-dataset-ref"
        )
        raise ValidationError(msg)
    return dataset_ref


def _log_step(timer: PhaseTimer, message: str, *, started_at: float) -> None:
    elapsed = time.perf_counter() - started_at

    rss_mb = process_rss_mb()

    rss_text = f" rss_mb={rss_mb:.1f}" if rss_mb is not None else ""

    timer.log(f"{message} done in {elapsed:.1f}s{rss_text}")


def _ensure_published_contract(
    dataset_ref: DatasetRef,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry,
    clock: SystemClock,
    timer: PhaseTimer,
    contract_code: str,
) -> None:
    metadata = registry.get(dataset_ref)
    if metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED:
        timer.log(f"{contract_code}: already published, skipping finalize/publish")
        return
    if metadata.lifecycle_status is DatasetLifecycleState.WORKING:
        finalize_dataset(dataset_ref, storage_root=storage_root, registry=registry)
    publish_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=clock,
    )


def main(argv: list[str] | None = None) -> int:
    """Finalize contract datasets, build continuous OHLCV and run strategy research."""

    args = _build_parser().parse_args(argv)

    if not args.skip_build and not args.refs:
        print(
            "at least one --contract-dataset-ref is required unless --skip-build is set",
            file=sys.stderr,
        )
        return 1

    try:
        contract_refs = (
            () if not args.refs else tuple(DatasetRef.parse(value) for value in args.refs)
        )
        continuous_ohlcv_ref: DatasetRef | None = None
        if args.skip_build or args.continuous_ohlcv_dataset_ref is not None:
            continuous_ohlcv_ref = resolve_continuous_ohlcv_dataset_ref(
                storage_root=args.storage_root,
                product=args.product,
                policy_slug=args.policy_slug,
                explicit_ref=args.continuous_ohlcv_dataset_ref,
            )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    profiling_enabled = args.profile or args.profile_deep

    timer = PhaseTimer(enabled=profiling_enabled)

    function_profiler = FunctionProfiler(enabled=args.profile_deep)

    registry = FileDatasetRegistry(args.storage_root)

    clock = SystemClock()

    build_result: BuildContinuousResult | None = None

    with function_profiler.session(), phase_timer_context(timer):
        timer.begin_session()

        timer.log(
            f"half_year_backtest: product={args.product} "
            f"contracts={len(contract_refs)} storage={args.storage_root} "
            f"skip_build={args.skip_build} persist={not args.no_persist}"
        )

        if not args.skip_build:
            with timer.phase("publish_contract_datasets"):
                for index, dataset_ref in enumerate(contract_refs, start=1):
                    contract_code = dataset_ref.dataset_id.instrument_id.value.split(".", 1)[-1]
                    step_started = time.perf_counter()
                    with timer.phase(f"publish.{contract_code}"):
                        _ensure_published_contract(
                            dataset_ref,
                            storage_root=args.storage_root,
                            registry=registry,
                            clock=clock,
                            timer=timer,
                            contract_code=contract_code,
                        )
                    timer.log(f"[{index}/{len(contract_refs)}] ready {contract_code}")
                    _log_step(timer, f"publish {contract_code}", started_at=step_started)

            build_started = time.perf_counter()

            with timer.phase("build_continuous"):
                build_result = build_continuous(
                    BuildContinuousRequest(
                        storage_root=args.storage_root,
                        product=args.product,
                        contract_dataset_refs=contract_refs,
                        policy_slug=args.policy_slug,
                        profile=profiling_enabled,
                    ),
                    registry=registry,
                    clock=clock,
                )
                continuous_ohlcv_ref = build_result.continuous_ohlcv_dataset_ref

            _log_step(timer, "build_continuous", started_at=build_started)

        if continuous_ohlcv_ref is None:
            print(
                "continuous OHLCV dataset ref was not resolved after build",
                file=sys.stderr,
            )
            return 1

        if args.skip_build:
            timer.log(f"skip_build: using continuous OHLCV ref={continuous_ohlcv_ref}")

        research_started = time.perf_counter()

        with timer.phase("strategy_research"):
            ohlcv_metadata = registry.get(continuous_ohlcv_ref)

            research_result = run_strategy_research(
                RunStrategyResearchRequest(
                    dataset_ref=continuous_ohlcv_ref,
                    timeframe=Timeframe("1m"),
                    requested_range=TimeRange(
                        start=ohlcv_metadata.start_at,
                        end=ohlcv_metadata.end_at,
                    ),
                    storage_root=args.storage_root,
                    strategy_model=build_canonical_strategy_model(),
                    assumptions=SimulationAssumptions(),
                    evaluation_timeframe=Timeframe("1m"),
                    session_resolver=CmeEsRthSessionResolver(),
                    persist=not args.no_persist,
                )
            )

        _log_step(timer, "strategy_research", started_at=research_started)

    timer.report(title="run_half_year_backtest phase report")

    if args.profile_deep:
        function_profiler.report(
            title="run_half_year_backtest function profile",
            top_n=args.profile_top,
        )

    payload: dict[str, object] = {
        "skipped_build": args.skip_build,
        "persisted": not args.no_persist,
        "continuous_ohlcv_dataset_ref": str(continuous_ohlcv_ref),
        "run_id": research_result.run_id,
        "strategy_model_id": research_result.manifest.strategy_model_id,
        "trade_count": len(research_result.trades),
        "equity_points": len(research_result.equity),
        "ohlcv_start_at": ohlcv_metadata.start_at.isoformat(),
        "ohlcv_end_at": ohlcv_metadata.end_at.isoformat(),
        "ohlcv_row_count": ohlcv_metadata.row_count,
    }
    if build_result is not None:
        payload.update(
            {
                "continuous_trades_dataset_ref": str(build_result.continuous_trades_dataset_ref),
                "roll_schedule_version": build_result.roll_schedule_version,
                "trades_reused": build_result.trades_reused,
                "ohlcv_reused": build_result.ohlcv_reused,
            }
        )

    if args.json:
        print(json.dumps(payload, indent=2))

    else:
        for key, value in payload.items():
            print(f"{key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
