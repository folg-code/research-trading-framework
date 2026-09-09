"""Generate the public projection bundle for the BTC Signal Quality study.

Reads the real, already-persisted Phase 16C artifacts T001 froze
(docs/planning/sprints/SPRINT_060_T001_FIELD_INVENTORY.md) and writes the
sanitized, deny-by-default ``PublicProjectionBundle`` to
``apps/dashboard/publication_data/projection.json``. Per ADR-0034 S1.2,
this runs at build time -- never inside a Streamlit page render -- and its
output is committed (maintainer decision, Sprint 060 T003): the study's
artifacts are fixed, already-sanitized, and intentionally public, so
committing lets the dashboard render this study without the private
workspace mounted.

    uv run python scripts/dashboard/generate_btc_signal_quality_projection.py
    uv run python scripts/dashboard/generate_btc_signal_quality_projection.py \\
        --storage-root user_data/workspace
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DASHBOARD_SRC = _REPO_ROOT / "apps" / "dashboard" / "src"
if str(_DASHBOARD_SRC) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_SRC))

# dashboard_app.publication is library-free (stdlib + this package's own
# dataclasses only, per its own module docstrings) -- unlike scripts/ops's
# convention of deferring heavy trading_framework imports inside functions,
# these imports are cheap and safe at module load time.
from dashboard_app.publication.generator import (  # noqa: E402
    RawArtifactInput,
    build_projection_bundle,
)
from dashboard_app.publication.paths import projection_bundle_path  # noqa: E402

#: The real BTC Signal Quality study's identifiers (docs/reference/BTC_SIGNAL_QUALITY_STUDY.md).
_PREDICTIVE_RUN_ID = "2ef6426b3cc06463"
_PROMOTED_ARTIFACT_FINGERPRINT = "00e919cc8f950eb8da7217b9e00f8bfb463642c4f2e114d325372404b9b368a3"
_STRATEGY_BASELINE_RUN_ID = "8d050f623a034a58"
_STRATEGY_SCORED_RUN_ID = "4dbf98822e6ae591"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=_REPO_ROOT / "user_data" / "workspace",
        help="Workspace root containing research/",
    )
    return parser


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"expected a JSON object in {path}, got {type(payload).__name__}"
        raise TypeError(msg)
    return payload


def _read_parquet_row(path: Path) -> dict[str, object]:
    import polars as pl

    frame = pl.read_parquet(path)
    rows = frame.to_dicts()
    if not rows:
        msg = f"expected at least one row in {path}"
        raise ValueError(msg)
    return rows[0]


def build_raw_artifact_inputs(storage_root: Path) -> list[RawArtifactInput]:
    predictive_run_dir = (
        storage_root / "research" / "predictive_research" / "runs" / _PREDICTIVE_RUN_ID
    )
    promoted_dir = (
        storage_root
        / "research"
        / "predictive_research"
        / "promoted"
        / _PROMOTED_ARTIFACT_FINGERPRINT
    )
    strategy_runs_dir = storage_root / "research" / "strategy_research" / "runs"

    return [
        RawArtifactInput(
            artifact_id=f"predictive-run-verdict-{_PREDICTIVE_RUN_ID}",
            artifact_role="predictive_run_verdict",
            raw_payload=_read_json_object(predictive_run_dir / "verdict.json"),
        ),
        RawArtifactInput(
            artifact_id=f"predictive-run-metrics-{_PREDICTIVE_RUN_ID}",
            artifact_role="predictive_run_metrics",
            raw_payload=_read_json_object(predictive_run_dir / "metrics.json"),
        ),
        RawArtifactInput(
            artifact_id=f"predictive-threshold-sensitivity-{_PREDICTIVE_RUN_ID}",
            artifact_role="predictive_threshold_sensitivity",
            raw_payload=_read_json_object(predictive_run_dir / "threshold_sensitivity.json"),
        ),
        RawArtifactInput(
            artifact_id=f"promoted-artifact-{_PROMOTED_ARTIFACT_FINGERPRINT}",
            artifact_role="promoted_artifact_identity",
            raw_payload=_read_json_object(promoted_dir / "manifest.json"),
        ),
        RawArtifactInput(
            artifact_id=f"strategy-research-run-{_STRATEGY_BASELINE_RUN_ID}",
            artifact_role="strategy_research_run_summary",
            raw_payload=_read_parquet_row(
                strategy_runs_dir
                / _STRATEGY_BASELINE_RUN_ID
                / "analytics"
                / "summary_metrics.parquet"
            ),
        ),
        RawArtifactInput(
            artifact_id=f"strategy-research-run-{_STRATEGY_SCORED_RUN_ID}",
            artifact_role="strategy_research_run_summary",
            raw_payload=_read_parquet_row(
                strategy_runs_dir
                / _STRATEGY_SCORED_RUN_ID
                / "analytics"
                / "summary_metrics.parquet"
            ),
        ),
    ]


def main() -> int:
    args = _build_parser().parse_args()

    raw_artifacts = build_raw_artifact_inputs(args.storage_root)
    bundle = build_projection_bundle(raw_artifacts, generated_at_utc=datetime.now(UTC))

    output_path = projection_bundle_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    print(f"wrote {len(bundle.artifacts)} artifacts to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
