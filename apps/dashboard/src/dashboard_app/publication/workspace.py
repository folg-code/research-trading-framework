"""Build-time discovery of safely publishable research catalog entries.

This is the only publication helper that reads the private workspace. Public
Streamlit pages must consume the generated bundle and must never call this
module at request time.
"""

from __future__ import annotations

import json
from pathlib import Path

from dashboard_app.catalog.scanner import list_runs
from dashboard_app.contracts import RunSummary, WorkflowKind
from dashboard_app.publication.catalog import build_catalog_artifact_input
from dashboard_app.publication.errors import UnsafePublicIdentityError
from dashboard_app.publication.generator import RawArtifactInput
from dashboard_app.publication.table_loading import load_table, read_json_mapping, required_string

#: Phase 18, 18A Milestone 2a (Sprint 070) / D-P18-03. A per-bar dense
#: series (equity, exposure) can be 500K-1.3M rows for a real run --
#: publishing every point is impractical for a committed static bundle, so
#: it is bounded to a deterministic, endpoint-preserving sample. Trades and
#: analytics tables (one row per trade/episode/label) are never bounded --
#: sampling them would misrepresent the population a distribution or
#: exit-diagnostics view needs.
STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS = 2000

STRATEGY_RESEARCH_EVIDENCE_ROLE = "strategy_research_evidence"

_STRATEGY_RESEARCH_MANIFEST_FIELDS = (
    "run_id",
    "schema_version",
    "framework_version",
    "created_at_utc",
    "source_dataset_ref",
    "evaluation_timeframe",
    "strategy_model_id",
    "market_model_id",
    "signal_model_id",
    "exit_model_id",
    "risk_model_id",
    "experiment_id",
    "fill_policy_entry",
    "fill_policy_exit",
    "slippage_bps",
    "commission_per_side",
    "initial_capital",
    "strategy_source_ref",
)


def discover_catalog_inputs(storage_root: Path) -> tuple[list[RawArtifactInput], int]:
    """Return safe catalog inputs and the number of skipped unsafe/corrupt runs."""
    catalog = list_runs(storage_root)
    inputs: list[RawArtifactInput] = []
    skipped = len(catalog.issues)
    for summary in catalog.runs:
        try:
            inputs.append(
                build_catalog_artifact_input(
                    summary,
                    verdict=_load_persisted_verdict(summary),
                )
            )
        except UnsafePublicIdentityError:
            skipped += 1
    return inputs, skipped


def _load_persisted_verdict(summary: RunSummary) -> str | None:
    path = Path(summary.storage_path) / "verdict.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    verdict = payload.get("verdict")
    return str(verdict) if verdict is not None else None


def discover_strategy_research_evidence_inputs(
    storage_root: Path,
) -> tuple[list[RawArtifactInput], int]:
    """Return rich Strategy Research evidence for every safely discovered run.

    Phase 18, 18A Milestone 2a (Sprint 070) / D-P18-03. Sibling to
    ``discover_catalog_inputs``: same scanner, same build-time-only reading
    rule, but projects each run's richer per-run artifacts (KPI summary,
    equity curve, trades, drawdown episodes, context expectancy, exposure)
    instead of identity only. A run missing an optional artifact (e.g. no
    ``context_expectancy.parquet`` backfilled yet) simply omits that table,
    not an error; a run missing ``summary_metrics`` is skipped entirely.
    """
    catalog = list_runs(storage_root)
    inputs: list[RawArtifactInput] = []
    skipped = 0
    for summary in catalog.runs:
        if summary.workflow is not WorkflowKind.STRATEGY:
            continue
        try:
            inputs.append(_load_strategy_research_run(Path(summary.storage_path)))
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            skipped += 1
    return inputs, skipped


def _load_strategy_research_run(run_dir: Path) -> RawArtifactInput:
    manifest = read_json_mapping(run_dir / "manifest.json")
    run_id = required_string(manifest, "run_id")

    tables: dict[str, list[dict[str, object]]] = {}
    equity_rows = load_table(
        run_dir / "equity.parquet", max_points=STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS
    )
    if equity_rows is not None:
        tables["equity_curve"] = equity_rows
    trades_rows = load_table(run_dir / "trades.parquet")
    if trades_rows is not None:
        tables["trades"] = trades_rows

    analytics_dir = run_dir / "analytics"
    summary_rows = load_table(analytics_dir / "summary_metrics.parquet")
    if summary_rows is not None:
        tables["summary_metrics"] = summary_rows
    episode_rows = load_table(analytics_dir / "drawdown_episodes.parquet")
    if episode_rows is not None:
        tables["drawdown_episodes"] = episode_rows
    context_rows = load_table(analytics_dir / "context_expectancy.parquet")
    if context_rows is not None:
        tables["context_expectancy"] = context_rows
    exposure_rows = load_table(
        analytics_dir / "exposure.parquet",
        max_points=STRATEGY_RESEARCH_DENSE_TABLE_MAX_POINTS,
    )
    if exposure_rows is not None:
        tables["exposure"] = exposure_rows

    if "summary_metrics" not in tables:
        raise ValueError("strategy research evidence has no summary_metrics")

    raw_payload: dict[str, object] = {
        key: manifest[key] for key in _STRATEGY_RESEARCH_MANIFEST_FIELDS if key in manifest
    }
    raw_payload["tables"] = tables
    return RawArtifactInput(
        artifact_id=f"strategy-research-evidence-{run_id}",
        artifact_role=STRATEGY_RESEARCH_EVIDENCE_ROLE,
        raw_payload=raw_payload,
    )
