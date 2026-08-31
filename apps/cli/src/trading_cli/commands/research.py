"""`trading-cli research run` (S046-T006/T007).

``research run predictive`` is the only *composed* command in this sprint: it
runs build -> run -> render as one call, passing identifiers between steps as
Python values (never through stdout), per the Sprint Goal diagram and the
`ResolvedPlan` design (SPRINT_046.md Sec1, Sec4 finding 1). It references the
existing `PredictiveStudySpec` / `EstimatorSpec` files by path only; their own
loaders parse them (D-S046-07) -- this module never re-encodes their schema.

``research run strategy`` runs a single Strategy Research simulation on a
published `DatasetRef`. **Known limitation (SPRINT_046.md Sec4 finding 2,
D-S046-03):** `run_strategy_research.py` hardcodes the canonical strategy
model (`build_canonical_strategy_model()`), the simulation assumptions
(`SimulationAssumptions()`), and the session resolver
(`CmeEsRthSessionResolver()`) -- the underlying application workflow accepts
them as parameters, but no script or config surface ever exposed a way to
choose different ones. This CLI command inherits that limitation rather than
inventing a new strategy-model-from-YAML mechanism that does not exist
anywhere else in the framework. Selecting a different strategy model requires
a direct call to `run_strategy_research` in Python, or a follow-on increment
to the application layer (see ADR-0026 "Follow-up").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    RenderPredictiveReportRequest,
    RunPredictiveResearchRequest,
    build_predictive_dataset,
    render_predictive_research_report,
    run_predictive_research,
)
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.core.exceptions import ValidationError

# apps/cli boundary widening (documented in tests/unit/test_apps_boundaries.py
# and apps/cli/CLAUDE.md): each import below is either a typed identifier
# produced/consumed by an application workflow, a config/spec value object
# with its own loader, or (per Sec4 finding 2) the same hardcoded default the
# wrapped script already uses. None of it is research, simulation, or
# execution logic reimplemented in the CLI.
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.datasets.predictive import PredictiveDatasetRef
from trading_framework.research.datasets.predictive_run import PredictiveRunRef
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import EstimatorSpec
from trading_framework.research.predictive.spec import load_predictive_study_spec
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import build_canonical_strategy_model
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, WorkflowError
from trading_cli.plan import ResolvedPlan

_SUPPORTED_KINDS = ("predictive", "strategy")


def resolve_plan(config: CliConfig) -> ResolvedPlan:
    if config.research is None:
        raise ConfigError("config is missing the 'research' block required by 'research run'")
    kind = config.research.get("kind")
    if kind not in _SUPPORTED_KINDS:
        raise ConfigError(
            f"unsupported 'research.kind': {kind!r}; supported: {', '.join(_SUPPORTED_KINDS)}"
        )
    kind_args = dict(config.research.get(kind) or {})
    if kind == "predictive":
        _require(kind_args, "definition", "research.predictive")
        _require(kind_args, "estimator", "research.predictive")
    else:
        _require(kind_args, "dataset_ref", "research.strategy")
    output_path = str(Path(config.storage_root) / "research" / kind)
    return ResolvedPlan(
        group="research",
        command="run",
        workflow=f"research.run.{kind}",
        arguments={"kind": kind, **kind_args},
        output_paths=(output_path,),
        storage_root=str(config.storage_root),
        implemented=True,
    )


def run(plan: ResolvedPlan) -> dict[str, Any]:
    kind = plan.arguments["kind"]
    storage_root = Path(plan.storage_root)
    try:
        if kind == "predictive":
            return _run_predictive(plan.arguments, storage_root)
        return _run_strategy(plan.arguments, storage_root)
    except (ValidationError, PredictiveSpecError, FileNotFoundError, FileExistsError) as exc:
        raise WorkflowError(f"'research run {kind}' failed: {exc}") from exc


def _run_predictive(arguments: dict[str, Any], storage_root: Path) -> dict[str, Any]:
    """Compose build -> run -> render, passing typed results between steps."""
    spec = load_predictive_study_spec(Path(arguments["definition"]))
    estimator = _load_estimator_spec(Path(arguments["estimator"]))
    persist = bool(arguments.get("persist", True))
    render_report = bool(arguments.get("render_report", True))

    build_result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=persist,
            session_resolver=CmeEsRthSessionResolver(),
        )
    )

    run_result = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=PredictiveDatasetRef(dataset_id=build_result.dataset_id),
            estimator=estimator,
            storage_root=storage_root,
            persist=persist,
        )
    )

    payload: dict[str, Any] = {
        "dataset_id": build_result.dataset_id,
        "run_id": run_result.run_id,
        "persisted": run_result.persisted,
    }

    if render_report and persist:
        report_result = render_predictive_research_report(
            RenderPredictiveReportRequest(
                run_ref=PredictiveRunRef(run_id=run_result.run_id),
                storage_root=storage_root,
            )
        )
        payload["output_path"] = str(report_result.output_path)

    return payload


def _run_strategy(arguments: dict[str, Any], storage_root: Path) -> dict[str, Any]:
    """Run one Strategy Research simulation (not composed with reporting).

    Mirrors ``scripts/strategy_research/run_strategy_research.py``: the
    canonical strategy model, simulation assumptions, and session resolver
    are the same hardcoded defaults the script uses (Sec4 finding 2).
    """
    dataset_ref = DatasetRef.parse(arguments["dataset_ref"])
    timeframe = Timeframe(arguments.get("timeframe", "1m"))
    registry = FileDatasetRegistry(storage_root)
    metadata = registry.get(dataset_ref)

    result = run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=timeframe,
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            strategy_model=build_canonical_strategy_model(),
            assumptions=SimulationAssumptions(),
            evaluation_timeframe=timeframe,
            session_resolver=CmeEsRthSessionResolver(),
        )
    )
    return {
        "run_id": result.run_id,
        "strategy_model_id": result.manifest.strategy_model_id,
        "trade_count": len(result.trades),
        "equity_points": len(result.equity),
    }


def _require(args: dict[str, Any], key: str, block: str) -> None:
    if not args.get(key):
        raise ConfigError(f"config is missing '{block}.{key}' required by 'research run'")


def _load_estimator_spec(path: Path) -> EstimatorSpec:
    """Read an `EstimatorSpec` file by path and parse it with its own loader.

    Only file I/O happens here; `EstimatorSpec.from_dict` is the spec's own
    validating constructor (D-S046-07 -- referenced by path, never re-encoded).
    """
    if not path.is_file():
        raise ConfigError(f"estimator file not found: {path}")
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        raise ConfigError(f"unsupported estimator file extension: {suffix!r}")
    if not isinstance(payload, dict):
        raise ConfigError("estimator spec root must be a mapping")
    return EstimatorSpec.from_dict(payload)
