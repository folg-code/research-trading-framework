"""Tutorial spike — build and evaluate declarative Market / Signal models.

Run manually:

    uv run python tests/spike/run_build_declarative_models_example.py
    uv run python tests/spike/run_build_declarative_models_example.py --catalog
    uv run python tests/spike/run_build_declarative_models_example.py --checklist
    uv run python tests/spike/run_build_declarative_models_example.py --json

Copy patterns to ``user_data/development/`` for local iteration.
Production API lives under ``src/trading_framework/``; this script is teaching material.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC
from pathlib import Path

import polars as pl

from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.model_expression.validation import validate_expression
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

_SPIKE_DIR = Path(__file__).resolve().parent
if str(_SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR))

from examples_component_catalog import (  # noqa: E402
    describe_component,
    list_mvp_components,
    print_component_build_checklist,
)
from examples_model_building import ExampleModelBundle, build_example_model_bundle  # noqa: E402

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "market_data"
    / "s005_swing_vertical_slice_1m.csv"
)


@dataclass(frozen=True, slots=True)
class ModelSummary:
    market_model_id: str
    true_bars: int
    total_bars: int


@dataclass(frozen=True, slots=True)
class SignalSummary:
    signal_model_id: str
    true_condition_bars: int
    emissions: int
    firing_policy: str


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
        source_id="build-models-example",
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


def _print_model_building_recipe() -> None:
    print(
        """
Building declarative models (Sprint 006 recipe)
===============================================
1. Pick component outputs (see --catalog) or canonical OHLCV fields.

2. Create references:
   ComponentOutputReference(
       component_id=...,
       parameters=component.parameter_schema.canonicalize({...}),
       output_id=OutputId("state"),
       computation_timeframe=Timeframe("5m"),  # optional MTF
   )
   MarketFieldReference(field=MarketField.CLOSE)

3. Build expression AST:
   CompareExpression(operand=..., operator=ComparisonOperator.EQ, value=1.0)
   AndExpression(left=..., right=...)

4. Wrap in definitions:
   MarketModelDefinition(market_model_id="...", expression=...)
   SignalModelDefinition(
       signal_model_id="...",
       expression=...,
       direction=SignalDirection.LONG,
       firing_policy=SignalFiringPolicy.ON_EVENT,  # or ON_TRUE_EDGE
   )

5. Validate before run:
   validate_expression(definition.expression, default_mvp_registry())

6. Evaluate (one shared run_analysis):
   evaluate_models(EvaluateModelsRequest(..., market_models=(...), signal_models=(...)))

See: tests/spike/examples_model_building.py
     src/trading_framework/application/model_evaluation/canonical_examples.py
"""
    )


def _print_catalog() -> None:
    print("MVP Market Analysis components\n==============================")
    for entry in list_mvp_components():
        print(describe_component(entry))
        print()


def _validate_bundle(bundle: ExampleModelBundle) -> None:
    registry = default_mvp_registry()
    for definition in bundle.market_models:
        validate_expression(definition.expression, registry)
        print(f"  validated market model: {definition.market_model_id}")
    for definition in bundle.signal_models:
        validate_expression(definition.expression, registry)
        print(f"  validated signal model: {definition.signal_model_id}")


def _run_example(*, fixture: Path) -> dict[str, object]:
    bundle = build_example_model_bundle()
    print("Step 1 — example model definitions")
    for definition in bundle.market_models:
        print(f"  market: {definition.market_model_id}")
    for definition in bundle.signal_models:
        print(
            f"  signal: {definition.signal_model_id} "
            f"({definition.direction.value}, {definition.firing_policy.value})"
        )

    print("\nStep 2 — validate expressions against registry")
    _validate_bundle(bundle)

    with tempfile.TemporaryDirectory() as tmp:
        storage_root = Path(tmp)
        dataset_ref = _write_published_dataset(storage_root, fixture)
        metadata = FileDatasetRegistry(storage_root).get(dataset_ref)

        print("\nStep 3 — evaluate_models (single run_analysis, deduplicated deps)")
        result = evaluate_models(
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

        market_summaries = [
            ModelSummary(
                market_model_id=model_id,
                true_bars=frame.filter(pl.col("model_result").eq(True)).height,
                total_bars=frame.height,
            )
            for model_id, frame in result.market_model_results.items()
        ]
        signal_summaries = [
            SignalSummary(
                signal_model_id=definition.signal_model_id,
                true_condition_bars=result.signal_model_conditions[definition.signal_model_id]
                .filter(pl.col("condition_met").eq(True))
                .height,
                emissions=result.signal_model_emissions[definition.signal_model_id].height,
                firing_policy=definition.firing_policy.value,
            )
            for definition in bundle.signal_models
        ]

        print("\nStep 4 — results")
        for summary in market_summaries:
            print(
                f"  market {summary.market_model_id}: "
                f"{summary.true_bars}/{summary.total_bars} true bars"
            )
        for summary in signal_summaries:
            print(
                f"  signal {summary.signal_model_id}: "
                f"{summary.true_condition_bars} true conditions, "
                f"{summary.emissions} emissions ({summary.firing_policy})"
            )

        component_runs = {
            analysis_result.computation_identity.component_id.value
            for analysis_result in result.analysis.workspace.result_store.results().values()
        }
        print(f"\n  unique components executed: {sorted(component_runs)}")

        return {
            "market_models": [asdict(item) for item in market_summaries],
            "signal_models": [asdict(item) for item in signal_summaries],
            "components_executed": sorted(component_runs),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tutorial: build and evaluate declarative models.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=FIXTURE,
        help="CSV fixture (default: s005_swing_vertical_slice_1m.csv)",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Print MVP component catalog and exit",
    )
    parser.add_argument(
        "--checklist",
        action="store_true",
        help="Print new-component checklist and exit",
    )
    parser.add_argument(
        "--recipe",
        action="store_true",
        help="Print model-building recipe and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit evaluation summary as JSON",
    )
    args = parser.parse_args()

    if args.catalog:
        _print_catalog()
        return 0
    if args.checklist:
        print_component_build_checklist()
        return 0
    if args.recipe:
        _print_model_building_recipe()
        return 0

    _print_model_building_recipe()
    print()
    payload = _run_example(fixture=args.fixture)
    if args.json:
        print(json.dumps(payload, indent=2))
    print("\nNext: inspect on chart with")
    print("  uv run python tests/spike/run_inspect_declarative_models.py --open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
