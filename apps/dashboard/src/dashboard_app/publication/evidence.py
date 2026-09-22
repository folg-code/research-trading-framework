"""Build-time projection of rich Signal and Robustness research evidence.

This module is the only reader for the persisted analytics used by the public
workflow pages.  It runs during publication, converts selected Parquet/JSON
facts into sanitizer inputs, and never runs from Streamlit.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from dashboard_app.publication.generator import RawArtifactInput

SIGNAL_RESEARCH_EVIDENCE_ROLE = "signal_research_evidence"
ROBUSTNESS_RESEARCH_EVIDENCE_ROLE = "robustness_research_evidence"
LEGACY_ROBUSTNESS_EXPERIMENT_ID = "demo-robustness-nq-half-year"

_SIGNAL_TABLES = (
    "summary_metrics",
    "grouped_summaries",
    "distribution_summaries",
    "conditional_comparison",
    "join_diagnostics",
    "metric_histograms",
    "quality_warnings",
    # Phase 18, 18B Milestone 1 (Sprint 073) / D-P18B-03/04.
    "adjusted_forward_drift",
    "context_timeline",
    "context_persistence",
)
_ROBUSTNESS_TABLES = (
    "parameter_sweep_rankings",
    "parameter_sweep_heatmap",
    "walk_forward_folds",
    "walk_forward_equity",
    "stress_comparison",
    "monte_carlo_distributions",
    "monte_carlo_tails",
    # Phase 18, 18D Milestone 1 (Sprint 075) / D-P18D-01/02. Backfilled by
    # scripts/robustness_research/backfill_fold_stability.py -- computed
    # once in the research/analytics layer (never in the dashboard, which
    # may not import trading_framework.research at all, ADR-0022), then
    # read here like any other analytics/ table.
    "walk_forward_fold_geometry",
    "walk_forward_stability",
)
_WALK_FORWARD_EQUITY_MAX_POINTS = 1_200
#: Per-bar dense series (Sprint 073's context_timeline can be 300K+ rows
#: for a real run) -- bounded the same deterministic, endpoint-preserving
#: way walk_forward_equity already is.
_CONTEXT_TIMELINE_MAX_POINTS = 2_000
#: mfe_mae_pairs is read from the run's raw outcomes.parquet (sibling to
#: analytics/, not inside it) -- see _load_signal_run.
_MFE_MAE_PAIRS_MAX_POINTS = 2_000


def discover_research_evidence_inputs(research_root: Path) -> tuple[list[RawArtifactInput], int]:
    """Load supported evidence from a private research root at build time.

    Signal runs are discovered generically.  The robustness source is the one
    explicitly approved legacy demo; it is deliberately not emitted as a
    ``research_catalog_entry`` and therefore cannot enter Strategy grouping.
    """
    inputs: list[RawArtifactInput] = []
    skipped = 0

    signal_runs_root = research_root / "market_research" / "runs"
    for run_dir in sorted(signal_runs_root.iterdir()) if signal_runs_root.is_dir() else ():
        if not run_dir.is_dir():
            continue
        try:
            inputs.append(_load_signal_run(run_dir))
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            skipped += 1

    robustness_dir = (
        research_root / "strategy_robustness" / "experiments" / LEGACY_ROBUSTNESS_EXPERIMENT_ID
    )
    if robustness_dir.is_dir():
        try:
            inputs.append(_load_robustness_experiment(robustness_dir))
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            skipped += 1
    return inputs, skipped


def _load_signal_run(run_dir: Path) -> RawArtifactInput:
    manifest = _read_json_mapping(run_dir / "manifest.json")
    run_id = _required_string(manifest, "run_id")
    tables = _load_tables(run_dir / "analytics", _SIGNAL_TABLES)
    if "summary_metrics" not in tables:
        raise ValueError("signal evidence has no summary_metrics")
    mfe_mae_pairs = _load_mfe_mae_pairs(run_dir)
    if mfe_mae_pairs is not None:
        tables["mfe_mae_pairs"] = mfe_mae_pairs
    raw_payload = {
        key: manifest[key]
        for key in (
            "run_id",
            "schema_version",
            "framework_version",
            "created_at_utc",
            "source_dataset_ref",
            "evaluation_timeframe",
            "signal_model_ids",
            "market_model_ids",
            "horizon_bars_requested",
            "experiment_id",
            "research_scope",
            "research_question",
        )
        if key in manifest
    }
    raw_payload["tables"] = tables
    return RawArtifactInput(
        artifact_id=f"signal-research-evidence-{run_id}",
        artifact_role=SIGNAL_RESEARCH_EVIDENCE_ROLE,
        raw_payload=raw_payload,
    )


def _load_robustness_experiment(experiment_dir: Path) -> RawArtifactInput:
    manifest = _read_json_mapping(experiment_dir / "manifest.json")
    experiment_id = _required_string(manifest, "experiment_id")
    if experiment_id != LEGACY_ROBUSTNESS_EXPERIMENT_ID:
        raise ValueError("unsupported legacy robustness experiment")
    spec = manifest.get("spec")
    if not isinstance(spec, dict):
        raise TypeError("robustness manifest spec must be a mapping")
    analytics_root = experiment_dir / "analytics"
    tables = _load_tables(analytics_root, _ROBUSTNESS_TABLES)
    if "walk_forward_folds" not in tables:
        raise ValueError("robustness evidence has no walk_forward_folds")
    verdict = _read_json_mapping(analytics_root / "verdict.json")
    raw_payload = {
        "experiment_id": experiment_id,
        "schema_version": manifest.get("schema_version"),
        "framework_version": manifest.get("framework_version"),
        "created_at_utc": manifest.get("created_at_utc"),
        "source_dataset_ref": spec.get("dataset_ref"),
        "evaluation_timeframe": spec.get("evaluation_timeframe", spec.get("timeframe")),
        "requested_range_start": spec.get("requested_range_start"),
        "requested_range_end": spec.get("requested_range_end"),
        "strategy_template_id": spec.get("strategy_template_id"),
        "evidence_label": "DEMO · LEGACY",
        "verdict": verdict,
        "tables": tables,
    }

    # Phase 18, 18D Milestone 1 (Sprint 075) / D-P18D-01/02: window geometry
    # already sits in manifest["spec"]["walk_forward"] -- publish it rather
    # than dropping it. walk_forward_fold_geometry/walk_forward_stability
    # (in `tables`, from `_ROBUSTNESS_TABLES`) are computed and persisted by
    # scripts/robustness_research/backfill_fold_stability.py, not here --
    # the dashboard may not import trading_framework.research (ADR-0022).
    walk_forward_spec = spec.get("walk_forward")
    if isinstance(walk_forward_spec, dict):
        for key in (
            "window_mode",
            "train_duration_seconds",
            "oos_duration_seconds",
            "step_duration_seconds",
        ):
            if key in walk_forward_spec:
                raw_payload[key] = walk_forward_spec[key]
    return RawArtifactInput(
        artifact_id=f"robustness-research-evidence-{experiment_id}",
        artifact_role=ROBUSTNESS_RESEARCH_EVIDENCE_ROLE,
        raw_payload=raw_payload,
    )


_BOUNDED_TABLE_MAX_POINTS = {
    "walk_forward_equity": _WALK_FORWARD_EQUITY_MAX_POINTS,
    "context_timeline": _CONTEXT_TIMELINE_MAX_POINTS,
}


def _load_tables(analytics_root: Path, names: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {}
    for name in names:
        path = analytics_root / f"{name}.parquet"
        if not path.is_file():
            continue
        table = pq.read_table(path)  # type: ignore[no-untyped-call]
        max_points = _BOUNDED_TABLE_MAX_POINTS.get(name)
        if max_points is not None:
            table = table.take(_bounded_indexes(table.num_rows, max_points))
        rows = table.to_pylist()
        tables[name] = [_json_value(row) for row in rows]
    return tables


def _load_mfe_mae_pairs(run_dir: Path) -> list[dict[str, Any]] | None:
    """Bounded, straight copy of (horizon_bars, forward_return, mfe, mae) triples.

    Sourced from the run's raw ``outcomes.parquet`` (sibling to ``analytics/``,
    not inside it) -- Phase 18 18B Milestone 1 Goals: no new computation.
    """
    path = run_dir / "outcomes.parquet"
    if not path.is_file():
        return None
    table = pq.read_table(path)  # type: ignore[no-untyped-call]
    table = table.select(["horizon_bars", "forward_return", "mfe", "mae"])
    table = table.take(_bounded_indexes(table.num_rows, _MFE_MAE_PAIRS_MAX_POINTS))
    return [_json_value(row) for row in table.to_pylist()]


def _bounded_indexes(row_count: int, max_points: int) -> list[int]:
    """Select deterministic, ordered row indexes while retaining both endpoints."""
    if row_count <= max_points:
        return list(range(row_count))
    last = row_count - 1
    return sorted({round(index * last / (max_points - 1)) for index in range(max_points)})


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def _read_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path.name}")
    return payload


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing {key}")
    return value
