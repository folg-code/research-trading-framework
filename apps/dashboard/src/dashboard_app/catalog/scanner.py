"""Filesystem run catalog over mounted research artifacts."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dashboard_app.catalog.paths import (
    market_research_runs_dir,
    predictive_research_datasets_dir,
    predictive_research_runs_dir,
    robustness_experiments_dir,
    run_manifest_path,
    strategy_research_runs_dir,
)
from dashboard_app.catalog.predictive_quality import (
    evaluate_predictive_quality_flags,
    select_primary_metric,
)
from dashboard_app.contracts import (
    PRESENTATION_SCHEMA_VERSION,
    PredictiveDatasetSummary,
    PredictiveRunSummary,
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


@dataclass(frozen=True, slots=True)
class PredictiveCatalog:
    """Predictive Research scan result: datasets, all runs, and non-fatal issues.

    ``runs`` includes every run found, regardless of whether its ``metrics.json``
    is present or its ``dataset_id`` matches a scanned dataset — callers decide
    leaderboard filtering (D-S044-09: missing metrics omit a run from the
    leaderboard, but the run is still returned here).
    """

    datasets: tuple[PredictiveDatasetSummary, ...]
    runs: tuple[PredictiveRunSummary, ...]
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


def list_predictive_catalog(storage_root: Path) -> PredictiveCatalog:
    """Scan Predictive Research dataset and run envelopes under storage_root.

    Filesystem walk only (D-S044-04) — not a DuckDB registry. Missing
    directories are ignored. Corrupt or incomplete manifests are recorded as
    issues and omitted from ``datasets`` / ``runs``.
    """
    root = storage_root.expanduser().resolve()
    datasets: list[PredictiveDatasetSummary] = []
    dataset_issues: list[CatalogIssue] = []
    _scan_run_tree(
        predictive_research_datasets_dir(root),
        parser=_parse_predictive_dataset_manifest,
        summaries=datasets,
        issues=dataset_issues,
    )

    runs: list[PredictiveRunSummary] = []
    run_issues: list[CatalogIssue] = []
    runs_dir = predictive_research_runs_dir(root)
    if runs_dir.is_dir():
        for child in sorted(runs_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = run_manifest_path(child)
            if not manifest_path.is_file():
                run_issues.append(
                    CatalogIssue(path=str(manifest_path), reason="manifest.json missing")
                )
                continue
            payload = _read_json_object(manifest_path)
            if payload is None:
                run_issues.append(
                    CatalogIssue(
                        path=str(manifest_path), reason="manifest.json is not valid JSON object"
                    )
                )
                continue
            try:
                summary = _parse_predictive_run_manifest(payload, child, root, run_issues)
            except (KeyError, TypeError, ValueError) as exc:
                run_issues.append(CatalogIssue(path=str(manifest_path), reason=str(exc)))
                continue
            runs.append(summary)

    datasets.sort(
        key=lambda item: (
            item.created_at_utc.isoformat() if item.created_at_utc is not None else "",
            item.dataset_id,
        ),
        reverse=True,
    )
    runs.sort(
        key=lambda item: (
            item.created_at_utc.isoformat() if item.created_at_utc is not None else "",
            item.run_id,
        ),
        reverse=True,
    )
    return PredictiveCatalog(
        datasets=tuple(datasets),
        runs=tuple(runs),
        issues=tuple(dataset_issues) + tuple(run_issues),
    )


def load_predictive_run_identity(storage_root: Path, run_id: str) -> Mapping[str, Any] | None:
    """Load raw provenance fields for one Predictive Research run manifest.

    Predictive identity (estimator spec, preprocessing spec, library and
    version, dataset fingerprint) does not share the market/strategy/
    robustness identity key set, so this is a parallel reader rather than an
    extension of ``_identity_fields``.
    """
    catalog = list_predictive_catalog(storage_root)
    match = next((item for item in catalog.runs if item.run_id == run_id), None)
    if match is None:
        return None
    payload = _read_json_object(Path(match.storage_path) / "manifest.json")
    if payload is None:
        return None
    keys = (
        "run_id",
        "run_fingerprint",
        "dataset_id",
        "dataset_fingerprint",
        "estimator_spec",
        "preprocessing_spec",
        "library",
        "library_version",
        "framework_version",
        "created_at_utc",
        "schema_version",
    )
    return {key: payload[key] for key in keys if key in payload}


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
    signal_model_id = _optional_str(payload.get("signal_model_id"))
    title = f"Strategy · {strategy_model_id}"
    if signal_model_id:
        title = f"{title} · signal {signal_model_id}"
    return RunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        workflow=WorkflowKind.STRATEGY,
        run_id=run_id,
        created_at_utc=_parse_optional_datetime(payload.get("created_at_utc")),
        title=title,
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
    strategy_template: str | None = None
    kinds_label: str | None = None
    if isinstance(spec, dict):
        dataset_ref = _optional_str(spec.get("dataset_ref"))
        timeframe = _optional_str(spec.get("evaluation_timeframe") or spec.get("timeframe"))
        strategy_template = _optional_str(spec.get("strategy_template_id"))
        kinds_raw = spec.get("kinds")
        if isinstance(kinds_raw, list) and kinds_raw:
            kinds_label = ", ".join(str(item) for item in kinds_raw)
    title = _robustness_title(
        experiment_id=experiment_id,
        strategy_template=strategy_template,
        kinds_label=kinds_label,
        dataset_ref=dataset_ref,
        timeframe=timeframe,
    )
    return RunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        workflow=WorkflowKind.ROBUSTNESS,
        run_id=experiment_id,
        created_at_utc=_parse_optional_datetime(payload.get("created_at_utc")),
        title=title,
        storage_path=str(run_dir),
        source_dataset_ref=dataset_ref,
        evaluation_timeframe=timeframe,
        framework_version=_optional_str(payload.get("framework_version")),
        artifact_schema_version=_optional_str(payload.get("schema_version")),
        experiment_id=experiment_id,
    )


def _parse_predictive_dataset_manifest(
    payload: dict[str, Any], dataset_dir: Path
) -> PredictiveDatasetSummary:
    dataset_id = str(payload["dataset_id"])
    dataset_fingerprint = str(payload["dataset_fingerprint"])
    study_spec = payload.get("study_spec")
    label_kind: str | None = None
    horizon: str | None = None
    if isinstance(study_spec, dict):
        label = study_spec.get("label")
        if isinstance(label, dict):
            label_kind = _optional_str(label.get("kind"))
            horizon = _optional_str(label.get("horizon"))
    return PredictiveDatasetSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        dataset_id=dataset_id,
        dataset_fingerprint=dataset_fingerprint,
        created_at_utc=_parse_optional_datetime(payload.get("created_at_utc")),
        source_dataset_ref=_optional_str(payload.get("source_dataset_ref")),
        label_kind=label_kind,
        horizon=horizon,
        storage_path=str(dataset_dir),
    )


def _parse_predictive_run_manifest(
    payload: dict[str, Any], run_dir: Path, storage_root: Path, issues: list[CatalogIssue]
) -> PredictiveRunSummary:
    run_id = str(payload["run_id"])
    dataset_id = str(payload["dataset_id"])
    dataset_fingerprint = str(payload["dataset_fingerprint"])
    estimator_spec = payload.get("estimator_spec")
    family = (
        _optional_str(estimator_spec.get("family")) if isinstance(estimator_spec, dict) else None
    )

    metrics_path = run_dir / "metrics.json"
    metrics_payload: dict[str, Any] | None = None
    has_metrics = False
    if metrics_path.is_file():
        metrics_payload = _read_json_object(metrics_path)
        if metrics_payload is None:
            issues.append(
                CatalogIssue(path=str(metrics_path), reason="metrics.json is not valid JSON object")
            )
        else:
            has_metrics = True
    dataset_manifest_path = run_manifest_path(
        predictive_research_datasets_dir(storage_root) / dataset_id
    )
    dataset_manifest = _read_json_object(dataset_manifest_path)

    selection = select_primary_metric(metrics_payload) if metrics_payload is not None else None
    quality_flags = evaluate_predictive_quality_flags(
        dataset_manifest=dataset_manifest, metrics=metrics_payload
    )

    return PredictiveRunSummary(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        run_id=run_id,
        dataset_id=dataset_id,
        dataset_fingerprint=dataset_fingerprint,
        created_at_utc=_parse_optional_datetime(payload.get("created_at_utc")),
        family=family,
        task_type=selection.task_type if selection is not None else None,
        primary_metric_name=selection.primary_metric_name if selection is not None else None,
        primary_metric_value=selection.primary_metric_value if selection is not None else None,
        baseline_delta=selection.baseline_delta if selection is not None else None,
        quality_flags=quality_flags,
        storage_path=str(run_dir),
        has_metrics=has_metrics,
    )


def _robustness_title(
    *,
    experiment_id: str,
    strategy_template: str | None,
    kinds_label: str | None,
    dataset_ref: str | None,
    timeframe: str | None,
) -> str:
    """Prefer strategy/kinds over repeating the opaque experiment id."""
    if strategy_template:
        parts = [f"Robustness · {strategy_template}"]
        if kinds_label:
            parts.append(kinds_label)
    elif kinds_label:
        parts = [f"Robustness · {kinds_label}"]
    else:
        parts = [f"Robustness · {experiment_id}"]
    # Dataset/TF already shown in picker suffix via RunSummary fields; omit here
    # unless the title would otherwise be only the id and we have no other cue.
    _ = dataset_ref, timeframe
    return " · ".join(parts)


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
