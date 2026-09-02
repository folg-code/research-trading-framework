"""`trading-cli research run` (S046-T006/T007).

``research run predictive`` is the only *composed* command in this sprint: it
runs build -> run -> render as one call, passing identifiers between steps as
Python values (never through stdout), per the Sprint Goal diagram and the
`ResolvedPlan` design (SPRINT_046.md Sec1, Sec4 finding 1). It references the
existing `PredictiveStudySpec` / `EstimatorSpec` files by path only; their own
loaders parse them (D-S046-07) -- this module never re-encodes their schema.

``research run strategy`` runs a single Strategy Research simulation on a
published `DatasetRef`. **Sprint 047 (ADR-0027) closes the strategy-model
third of SPRINT_046.md Sec4 finding 2 / D-S046-03:** an optional
`research.strategy.strategy_file` config key names an operator-authored
Python file with a zero-argument `build_strategy() -> StrategyModelDefinition`
entry point (`trading_cli.strategy_loader`); when set, the loaded strategy
runs instead of the Sprint 013 canonical example. When absent, this command
keeps using `build_canonical_strategy_model()` exactly as before -- purely
additive, every Sprint 046 example config keeps working unchanged.
**TRUST MODEL (ADR-0027 Sec2, D-S047-09):** a `strategy_file` is loaded and
executed with no sandbox, no import restriction and no static analysis --
the same blast radius as running the file directly with
`uv run python <that file>`. `--dry-run`'s guarantee narrows accordingly: the
CLI itself performs no side effect, but the loaded module is operator code
and executes at import (ADR-0027 Sec4). The simulation assumptions and
session resolver remain hardcoded (the other two thirds of finding 2,
unchanged this sprint).

``research promote`` (S049-T009, D-S049-15) is a separate subcommand of the
same `research` group -- not a `research.kind` value -- that promotes the
last walk-forward fold of an existing Predictive Research run
(`research.promote.run_id`) into a content-addressed promoted artifact
(ADR-0029). It is a thin wrapper over
`application.predictive_research.promote_predictive_run`: no business logic
lives here, only config -> typed request -> typed result. Requires the `ml`
extra to actually run (the workflow reads the run's fitted joblib blob once);
this module itself does not import sklearn/joblib.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    PromotePredictiveRunRequest,
    RenderPredictiveReportRequest,
    RunPredictiveResearchRequest,
    build_predictive_dataset,
    promote_predictive_run,
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
from trading_framework.strategy import CANONICAL_STRATEGY_MODEL_ID, build_canonical_strategy_model
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, WorkflowError
from trading_cli.plan import ResolvedPlan
from trading_cli.strategy_loader import load_strategy_definition

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
    runtime_context: dict[str, Any] = {}
    if kind == "predictive":
        _require(kind_args, "definition", "research.predictive")
        _require(kind_args, "estimator", "research.predictive")
    else:
        _require(kind_args, "dataset_ref", "research.strategy")
        _resolve_strategy_source(kind_args, runtime_context)
    output_path = str(Path(config.storage_root) / "research" / kind)
    return ResolvedPlan(
        group="research",
        command="run",
        workflow=f"research.run.{kind}",
        arguments={"kind": kind, **kind_args},
        output_paths=(output_path,),
        storage_root=str(config.storage_root),
        implemented=True,
        runtime_context=runtime_context,
    )


def resolve_promote_plan(config: CliConfig) -> ResolvedPlan:
    """Resolve `research promote`'s plan from `research.promote.run_id`.

    Unrelated to the `research.kind` selector `research run` uses --
    `promote` is a sibling subcommand, not a `kind` value (D-S049-15).
    """
    if config.research is None:
        raise ConfigError("config is missing the 'research' block required by 'research promote'")
    promote_args = dict(config.research.get("promote") or {})
    _require(promote_args, "run_id", "research.promote")
    output_path = str(Path(config.storage_root) / "research" / "promoted")
    return ResolvedPlan(
        group="research",
        command="promote",
        workflow="research.promote",
        arguments={"run_id": promote_args["run_id"]},
        output_paths=(output_path,),
        storage_root=str(config.storage_root),
        implemented=True,
    )


def run_promote(plan: ResolvedPlan) -> dict[str, Any]:
    """Promote one existing Predictive Research run. Thin wrapper, no logic."""
    storage_root = Path(plan.storage_root)
    run_id = str(plan.arguments["run_id"])
    try:
        result = promote_predictive_run(
            PromotePredictiveRunRequest(
                run_ref=PredictiveRunRef(run_id=run_id),
                storage_root=storage_root,
            )
        )
    except (ValidationError, PredictiveSpecError, FileNotFoundError, FileExistsError) as exc:
        raise WorkflowError(f"'research promote' failed: {exc}") from exc
    return {
        "artifact_fingerprint": result.artifact_fingerprint,
        "directory": str(result.directory),
        "fold_id": result.fold_id,
    }


def _resolve_strategy_source(kind_args: dict[str, Any], runtime_context: dict[str, Any]) -> None:
    """Resolve `research.strategy.strategy_file`, or fall back to the canonical example.

    Loading happens here -- during `resolve_plan`, before any framework side
    effect (ADR-0027 Sec4) -- so a missing file, a typo'd entry-point name or
    a wrong return type fails pre-flight and `--dry-run` proves the file loads
    by printing the resolved `strategy_model_id`. `strategy_file` is optional
    (D-S047-05): its absence keeps producing the canonical example, exactly as
    on `main` today.
    """
    strategy_file = kind_args.get("strategy_file")
    if strategy_file is None:
        kind_args["strategy_model_id"] = CANONICAL_STRATEGY_MODEL_ID
        kind_args["strategy_source"] = "canonical"
        return
    if not isinstance(strategy_file, str):
        raise ConfigError(
            "'research.strategy.strategy_file' must be a string path; got "
            f"{type(strategy_file).__name__}"
        )
    loaded = load_strategy_definition(strategy_file)
    kind_args["strategy_file"] = str(loaded.strategy_file)
    kind_args["strategy_model_id"] = loaded.definition.strategy_model_id
    kind_args["strategy_source"] = "strategy_file"
    runtime_context["strategy_model"] = loaded.definition


def run(plan: ResolvedPlan) -> dict[str, Any]:
    kind = plan.arguments["kind"]
    storage_root = Path(plan.storage_root)
    try:
        if kind == "predictive":
            return _run_predictive(plan.arguments, storage_root)
        return _run_strategy(plan.arguments, plan.runtime_context, storage_root)
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


def _run_strategy(
    arguments: dict[str, Any], runtime_context: dict[str, Any], storage_root: Path
) -> dict[str, Any]:
    """Run one Strategy Research simulation (not composed with reporting).

    The strategy model is either the one `resolve_plan` already loaded from
    `research.strategy.strategy_file` (via `runtime_context`, loaded exactly
    once, pre-flight -- ADR-0027 Sec4) or, when no `strategy_file` was
    configured, `build_canonical_strategy_model()` (D-S047-05). The
    simulation assumptions and session resolver remain the same hardcoded
    defaults `scripts/strategy_research/run_strategy_research.py` uses
    (Sec4 finding 2, unchanged this sprint).
    """
    dataset_ref = DatasetRef.parse(arguments["dataset_ref"])
    timeframe = Timeframe(arguments.get("timeframe", "1m"))
    registry = FileDatasetRegistry(storage_root)
    metadata = registry.get(dataset_ref)

    strategy_model = runtime_context.get("strategy_model") or build_canonical_strategy_model()

    result = run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=timeframe,
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            strategy_model=strategy_model,
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
