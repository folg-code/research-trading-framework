"""Generate a standalone Robustness Research HTML dashboard demo.

Default path uses the published NQ half-year continuous OHLCV storage and the same
canonical strategy as ``run_half_year_backtest`` (1,464 trades on ~177k bars).

    uv run python scripts/demo/run_robustness_demo.py --open
    uv run python scripts/demo/run_robustness_demo.py --fixture --open
"""

from __future__ import annotations

import argparse
import shutil
import sys
import webbrowser
from datetime import UTC
from decimal import Decimal
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_FIXTURE_CSV = _REPO_ROOT / "tests" / "fixtures" / "market_data" / "ohlcv_sample_1m.csv"
_DEFAULT_OUTPUT = _REPO_ROOT / "demo" / "output" / "07_robustness_dashboard.html"
_DEFAULT_HALF_YEAR_STORAGE = _REPO_ROOT / "user_data" / "storage_nq_half_year"
_HALF_YEAR_BASELINE_RUN_ID = "14e36fe5fbb5d9f2"
_DAY_SECONDS = 86_400


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate robustness HTML dashboard demo.")
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=None,
        help="Workspace for datasets and experiment artifacts (default: NQ half-year)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Output HTML path",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use committed OHLCV fixture instead of NQ half-year storage",
    )
    parser.add_argument("--open", action="store_true", help="Open report in default browser")
    return parser


def _write_published_fixture_dataset(storage_root: Path):
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.core.identifiers import Identifier
    from trading_framework.market.datasets import DatasetId
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics
    from trading_framework.time.models.timeframe import Timeframe

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="robustness-demo-fixture",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=_FIXTURE_CSV,
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


def _resolve_half_year_dataset(storage_root: Path):
    from trading_framework.core.exceptions import ValidationError
    from trading_framework.infrastructure.storage.metadata.discovery import (
        latest_published_dataset_ref,
    )
    from trading_framework.market.continuous.identity import continuous_instrument_id
    from trading_framework.market.continuous.policy import VOLUME_RTH_CLOSE_POLICY_SLUG
    from trading_framework.market.datasets import DatasetId
    from trading_framework.market.derivation import DERIVED_OHLCV_PROVIDER
    from trading_framework.time.models.timeframe import Timeframe

    if not storage_root.exists():
        msg = f"half-year storage not found: {storage_root}"
        raise ValidationError(msg)

    dataset_ref = latest_published_dataset_ref(
        storage_root,
        DatasetId(
            instrument_id=continuous_instrument_id("NQ"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider=DERIVED_OHLCV_PROVIDER,
            source_id=VOLUME_RTH_CLOSE_POLICY_SLUG,
        ),
    )
    if dataset_ref is None:
        msg = "no published continuous NQ OHLCV dataset in half-year storage"
        raise ValidationError(msg)
    return dataset_ref


def _build_demo_spec(
    *,
    experiment_id: str,
    dataset_ref,
    requested_range,
    half_year: bool,
):
    from trading_framework.research.robustness.diagnostics import StatisticalDiagnosticsSpec
    from trading_framework.research.robustness.experiment import (
        ParameterSweepAxis,
        ParameterSweepSpec,
        RobustnessExperimentSpec,
    )
    from trading_framework.research.robustness.kinds import RobustnessExperimentKind
    from trading_framework.research.robustness.monte_carlo import MonteCarloSpec
    from trading_framework.research.robustness.stress import (
        StressScenarioSpec,
        StressTestSpec,
    )
    from trading_framework.research.robustness.verdict_thresholds import VerdictThresholds
    from trading_framework.research.robustness.walk_forward import (
        WalkForwardSpec,
        WalkForwardWindowMode,
    )
    from trading_framework.strategy.canonical_examples import (
        CANONICAL_EXIT_AFTER_BARS,
        CANONICAL_STRATEGY_MODEL_ID,
    )

    baseline_exit_bars = str(CANONICAL_EXIT_AFTER_BARS)
    if half_year:
        walk_forward = WalkForwardSpec(
            window_mode=WalkForwardWindowMode.ROLLING,
            train_duration_seconds=45 * _DAY_SECONDS,
            oos_duration_seconds=14 * _DAY_SECONDS,
            step_duration_seconds=21 * _DAY_SECONDS,
        )
        mc_paths = 120
        mc_dd_threshold = Decimal("-1500")
    else:
        walk_forward = WalkForwardSpec(
            window_mode=WalkForwardWindowMode.ROLLING,
            train_duration_seconds=4 * 3600,
            oos_duration_seconds=3600,
            step_duration_seconds=2 * 3600,
        )
        mc_paths = 80
        mc_dd_threshold = Decimal("-500")

    parameter_sweep = ParameterSweepSpec(
        axes=(ParameterSweepAxis(name="exit_after_bars", values=("5", baseline_exit_bars)),)
    )
    return RobustnessExperimentSpec(
        experiment_id=experiment_id,
        kinds=(
            RobustnessExperimentKind.PARAMETER_SWEEP,
            RobustnessExperimentKind.WALK_FORWARD,
            RobustnessExperimentKind.STRESS_TEST,
            RobustnessExperimentKind.MONTE_CARLO,
            RobustnessExperimentKind.STATISTICAL_DIAGNOSTICS,
        ),
        dataset_ref=str(dataset_ref),
        timeframe="1m",
        requested_range_start=requested_range.start,
        requested_range_end=requested_range.end,
        strategy_template_id=CANONICAL_STRATEGY_MODEL_ID,
        evaluation_timeframe="1m",
        parameter_sweep=parameter_sweep,
        walk_forward=walk_forward,
        stress_test=StressTestSpec(
            scenarios=(
                StressScenarioSpec(
                    scenario_id="double_commission",
                    commission_multiplier=Decimal("2"),
                ),
                StressScenarioSpec(
                    scenario_id="remove_top_trade",
                    remove_top_n_trades=1,
                ),
            ),
            parameter_overrides={"exit_after_bars": baseline_exit_bars},
        ),
        monte_carlo=MonteCarloSpec(
            path_count=mc_paths,
            rng_seed=11,
            parameter_overrides={"exit_after_bars": baseline_exit_bars},
            max_drawdown_threshold=mc_dd_threshold,
        ),
        statistical_diagnostics=StatisticalDiagnosticsSpec(
            top_k_trades=5,
            top_k_days=5,
            parameter_overrides={"exit_after_bars": baseline_exit_bars},
        ),
        verdict_thresholds=VerdictThresholds(
            min_stitched_oos_net_pnl=Decimal("-5000"),
            min_oos_beats_train_ratio=Decimal("0"),
            max_worst_stress_delta_net_pnl=Decimal("-2000"),
            max_mc_loss_probability=Decimal("0.75"),
            max_top_trades_concentration=Decimal("0.85"),
            fail_on_isolated_optima=False,
        ),
    )


def _reset_experiment(storage_root: Path, experiment_id: str) -> None:
    experiment_dir = storage_root / "robustness_experiments" / experiment_id
    if experiment_dir.exists():
        shutil.rmtree(experiment_dir)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    from trading_framework.application.robustness_research import (
        AnalyzeRobustnessExperimentRequest,
        RenderRobustnessReportRequest,
        RunMonteCarloExperimentRequest,
        RunRobustnessExperimentRequest,
        RunStressExperimentRequest,
        RunWalkForwardExperimentRequest,
        analyze_robustness_experiment,
        render_robustness_experiment_report,
        run_monte_carlo_experiment,
        run_robustness_experiment,
        run_stress_experiment,
        run_walk_forward_experiment,
    )
    from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
    from trading_framework.market_analysis import TimeRange
    from trading_framework.research.analytics.strategy_summarize import summarize_strategy_run
    from trading_framework.research.datasets.strategy_research import (
        StrategyResearchDatasetRepository,
        StrategyResearchRunRef,
    )
    from trading_framework.research.simulation import SimulationAssumptions
    from trading_framework.time.models.timeframe import Timeframe
    from trading_framework.time.sessions import CmeEsRthSessionResolver

    use_fixture = args.fixture
    storage_root = (
        args.storage_root
        if args.storage_root is not None
        else (
            _REPO_ROOT / "demo" / "robustness_storage"
            if use_fixture
            else _DEFAULT_HALF_YEAR_STORAGE
        )
    )
    experiment_id = "demo-robustness-fixture" if use_fixture else "demo-robustness-nq-half-year"

    storage_root.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _reset_experiment(storage_root, experiment_id)

    print(f"[robustness-demo] mode: {'fixture' if use_fixture else 'nq-half-year'}")
    print(f"[robustness-demo] storage: {storage_root}")

    if use_fixture:
        dataset_ref = _write_published_fixture_dataset(storage_root)
    else:
        dataset_ref = _resolve_half_year_dataset(storage_root)
        strategy_repo = StrategyResearchDatasetRepository(storage_root)
        baseline_ref = StrategyResearchRunRef(run_id=_HALF_YEAR_BASELINE_RUN_ID)
        try:
            baseline = strategy_repo.read(baseline_ref)
            summary = summarize_strategy_run(trades=baseline.trades, equity=baseline.equity)
            print(
                "[robustness-demo] baseline half-year run "
                f"{_HALF_YEAR_BASELINE_RUN_ID}: "
                f"trades={summary.trade_count}, net_pnl={summary.net_pnl}"
            )
        except FileNotFoundError:
            print(
                "[robustness-demo] warning: baseline run "
                f"{_HALF_YEAR_BASELINE_RUN_ID} not found; continuing with fresh child runs"
            )

    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    print(
        f"[robustness-demo] dataset: {dataset_ref} "
        f"({metadata.row_count:,} bars, {requested_range.start.date()} .. "
        f"{requested_range.end.date()})"
    )

    spec = _build_demo_spec(
        experiment_id=experiment_id,
        dataset_ref=dataset_ref,
        requested_range=requested_range,
        half_year=not use_fixture,
    )

    common = dict(
        spec=spec,
        storage_root=storage_root,
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=requested_range,
        assumptions=SimulationAssumptions(),
        evaluation_timeframe=Timeframe("1m"),
        session_resolver=CmeEsRthSessionResolver(),
    )

    print("[robustness-demo] run parameter sweep...")
    sweep_result = run_robustness_experiment(RunRobustnessExperimentRequest(**common))
    print(
        "[robustness-demo] sweep completed="
        f"{sweep_result.completed_count}, skipped={sweep_result.skipped_count}"
    )

    print("[robustness-demo] run walk-forward...")
    run_walk_forward_experiment(RunWalkForwardExperimentRequest(**common))

    print("[robustness-demo] run stress test...")
    run_stress_experiment(RunStressExperimentRequest(**common))

    print("[robustness-demo] run monte carlo...")
    mc_result = run_monte_carlo_experiment(RunMonteCarloExperimentRequest(**common))
    print(
        "[robustness-demo] monte carlo reference_run_id="
        f"{mc_result.results.reference_strategy_run_id}"
    )

    print("[robustness-demo] analyze + verdict...")
    analyze_result = analyze_robustness_experiment(
        AnalyzeRobustnessExperimentRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
        )
    )
    print(f"[robustness-demo] verdict: {analyze_result.verdict.verdict.value}")
    summary = analyze_result.verdict.summary.encode("ascii", errors="replace").decode("ascii")
    print(f"[robustness-demo] summary: {summary}")

    print("[robustness-demo] render HTML dashboard...")
    render_result = render_robustness_experiment_report(
        RenderRobustnessReportRequest(
            experiment_id=experiment_id,
            storage_root=storage_root,
            output_path=args.output,
            persist_to_experiment_dir=True,
        )
    )
    print(f"[robustness-demo] wrote: {render_result.output_path}")

    if args.open:
        webbrowser.open(render_result.output_path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
