"""Filesystem run catalog over mounted research artifacts."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dashboard_app.catalog.paths import (
    market_research_runs_dir,
    robustness_experiments_dir,
    run_manifest_path,
    strategy_research_runs_dir,
)
from dashboard_app.contracts import (
    PRESENTATION_SCHEMA_VERSION,
    RunManifest,
    RunSummary,
    WorkflowKind,
)


@dataclass(frozen=True, slots=True)
class CatalogIssue:
    """One skipped or corrupt artifact encountered while scanning."""

    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class RunCatalog:
    """Catalog scan result: usable summaries plus non-fatal issues."""

    runs: tuple[RunSummary, ...]
    issues: tuple[CatalogIssue, ...]


def list_runs(storage_root: Path) -> RunCatalog:
    """Scan MARKET / SIGNAL / STRATEGY / ROBUSTNESS artifacts under storage_root.

    Missing directories are ignored. Corrupt or incomplete manifests are recorded
    as issues and omitted from ``runs``.
    """
    root = storage_root.expanduser().resolve()
    summaries: list[RunSummary] = []
    issues: list[CatalogIssue] = []

    _scan_run_tree(
        market_research_runs_dir(root),
        parser=_parse_market_signal_manifest,
        summaries=summaries,
        issues=issues,
    )
    _scan_run_tree(
        strategy_research_runs_dir(root),
        parser=_parse_strategy_manifest,
        summaries=summaries,
        issues=issues,
    )
    _scan_run_tree(
        robustness_experiments_dir(root),
        parser=_parse_robustness_manifest,
        summaries=summaries,
        issues=issues,
    )

    summaries.sort(
        key=lambda item: (
            item.created_at_utc.isoformat() if item.created_at_utc is not None else "",
            item.run_id,
        ),
        reverse=True,
    )
    return RunCatalog(runs=tuple(summaries), issues=tuple(issues))


def load_run_manifest(storage_root: Path, run_id: str) -> RunManifest | None:
    """Load one presentation manifest by run/experiment id, if present."""
    catalog = list_runs(storage_root)
    match = next((item for item in catalog.runs if item.run_id == run_id), None)
    if match is None:
        return None
    path = Path(match.storage_path) / "manifest.json"
    payload = _read_json_object(path)
    if payload is None:
        return None
    identity = _identity_fields(payload)
    return RunManifest(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        summary=match,
        identity=identity,
    )


def _scan_run_tree(
    runs_dir: Path,
    *,
    parser: Callable[[dict[str, Any], Path], RunSummary],
    summaries: list[RunSummary],
    issues: list[CatalogIssue],
) -> None:
    if not runs_dir.is_dir():
        return
    for child in sorted(runs_dir.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = run_manifest_path(child)
        if not manifest_path.is_file():
            issues.append(CatalogIssue(path=str(manifest_path), reason="manifest.json missing"))
            continue
        payload = _read_json_object(manifest_path)
        if payload is None:
            issues.append(
                CatalogIssue(
                    path=str(manifest_path), reason="manifest.json is not valid JSON object"
                )
            )
            continue
        try:
            summary = parser(payload, child)
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(CatalogIssue(path=str(manifest_path), reason=str(exc)))
            continue
        summaries.append(summary)


def _parse_market_signal_manifest(payload: dict[str, Any], run_dir: Path) -> RunSummary:
    run_id = str(payload["run_id"])
    scope = payload.get("research_scope")
    scope_str = str(scope) if scope is not None else None
    workflow = _workflow_for_research_scope(scope_str)
    title = _market_signal_title(payload, workflow=workflow, scope=scope_str)
    return RunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        workflow=workflow,
        run_id=run_id,
        created_at_utc=_parse_optional_datetime(payload.get("created_at_utc")),
        title=title,
        storage_path=str(run_dir),
        source_dataset_ref=_optional_str(payload.get("source_dataset_ref")),
        evaluation_timeframe=_optional_str(payload.get("evaluation_timeframe")),
        framework_version=_optional_str(payload.get("framework_version")),
        artifact_schema_version=_optional_str(payload.get("schema_version")),
        research_scope=scope_str,
        experiment_id=_optional_str(payload.get("experiment_id")),
    )


def _parse_strategy_manifest(payload: dict[str, Any], run_dir: Path) -> RunSummary:
    run_id = str(payload["run_id"])
    strategy_model_id = str(payload.get("strategy_model_id") or "strategy")
    return RunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        workflow=WorkflowKind.STRATEGY,
        run_id=run_id,
        created_at_utc=_parse_optional_datetime(payload.get("created_at_utc")),
        title=f"Strategy · {strategy_model_id}",
        storage_path=str(run_dir),
        source_dataset_ref=_optional_str(payload.get("source_dataset_ref")),
        evaluation_timeframe=_optional_str(payload.get("evaluation_timeframe")),
        framework_version=_optional_str(payload.get("framework_version")),
        artifact_schema_version=_optional_str(payload.get("schema_version")),
        experiment_id=_optional_str(payload.get("experiment_id")),
    )


def _parse_robustness_manifest(payload: dict[str, Any], run_dir: Path) -> RunSummary:
    experiment_id = str(payload["experiment_id"])
    spec = payload.get("spec")
    dataset_ref: str | None = None
    timeframe: str | None = None
    if isinstance(spec, dict):
        dataset_ref = _optional_str(spec.get("dataset_ref"))
        timeframe = _optional_str(spec.get("evaluation_timeframe") or spec.get("timeframe"))
    return RunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        workflow=WorkflowKind.ROBUSTNESS,
        run_id=experiment_id,
        created_at_utc=_parse_optional_datetime(payload.get("created_at_utc")),
        title=f"Robustness · {experiment_id}",
        storage_path=str(run_dir),
        source_dataset_ref=dataset_ref,
        evaluation_timeframe=timeframe,
        framework_version=_optional_str(payload.get("framework_version")),
        artifact_schema_version=_optional_str(payload.get("schema_version")),
        experiment_id=experiment_id,
    )


def _workflow_for_research_scope(scope: str | None) -> WorkflowKind:
    if scope == "market_model_only":
        return WorkflowKind.MARKET
    # signal_model_only, market_and_signal, and legacy (missing) → SIGNAL
    return WorkflowKind.SIGNAL


def _market_signal_title(
    payload: dict[str, Any],
    *,
    workflow: WorkflowKind,
    scope: str | None,
) -> str:
    if workflow is WorkflowKind.MARKET:
        models = payload.get("market_model_ids") or []
        label = ", ".join(str(item) for item in models) if models else "market"
        return f"Market · {label}"
    signals = payload.get("signal_model_ids") or []
    label = ", ".join(str(item) for item in signals) if signals else "signal"
    scope_suffix = f" ({scope})" if scope and scope != "signal_model_only" else ""
    return f"Signal · {label}{scope_suffix}"


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _identity_fields(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "experiment_id",
        "schema_version",
        "framework_version",
        "created_at_utc",
        "source_dataset_ref",
        "evaluation_timeframe",
        "research_scope",
        "signal_model_ids",
        "market_model_ids",
        "strategy_model_id",
        "market_model_id",
        "signal_model_id",
        "exit_model_id",
        "risk_model_id",
        "simulation_assumptions_fingerprint",
    )
    return {key: payload[key] for key in keys if key in payload}
