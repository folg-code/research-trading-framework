"""Generate a sanitized public projection for every safely identifiable run.

The command scans a private workspace only at build/deploy time. It appends
generic catalog entries to an optional validated base bundle (the committed
Signal Quality evidence bundle by default) and writes one projection without
ever copying a workspace path.

    uv run python scripts/dashboard/generate_public_projection.py \
        --storage-root user_data/workspace \
        --output artifacts/demo/public-projection.json
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

from dashboard_app.publication.evidence import (  # noqa: E402
    discover_research_evidence_inputs,
)
from dashboard_app.publication.generator import (  # noqa: E402
    build_projection_bundle,
    refresh_publication_projection_bundle,
)
from dashboard_app.publication.paths import projection_bundle_path  # noqa: E402
from dashboard_app.publication.projection import PublicProjectionBundle  # noqa: E402
from dashboard_app.publication.validation import (  # noqa: E402
    PublicationUnavailable,
    load_projection_bundle_from_path,
)
from dashboard_app.publication.workspace import (  # noqa: E402
    discover_catalog_inputs,
    discover_strategy_research_evidence_inputs,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=_REPO_ROOT / "user_data" / "research",
        help="Private research root read only during generation.",
    )
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=_REPO_ROOT / "user_data" / "workspace",
        help="Private workspace root read only during generation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "artifacts" / "demo" / "public-projection.json",
        help="Destination bundle. Production supplies a versioned host path.",
    )
    parser.add_argument(
        "--base-bundle",
        type=Path,
        default=projection_bundle_path(),
        help="Validated projection whose curated study artifacts are retained.",
    )
    parser.add_argument(
        "--without-base-bundle",
        action="store_true",
        help="Generate discovered catalog and workflow-evidence entries only.",
    )
    return parser


def _load_base_bundle(path: Path) -> PublicProjectionBundle:
    result = load_projection_bundle_from_path(path)
    if isinstance(result, PublicationUnavailable):
        msg = f"base projection unavailable: {result.reason}: {result.detail}"
        raise ValueError(msg)
    return result


def _write_bundle_atomic(path: Path, bundle: PublicProjectionBundle) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(bundle.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    args = _build_parser().parse_args()
    generated_at = datetime.now(UTC)
    # Phase 18, 18B Milestone 1 (Sprint 072) / D-P18B-01: Signal Research
    # identity lives under a different physical root than Strategy
    # Research's --storage-root -- scan both for catalog identity, not
    # only storage_root. discover_catalog_inputs (via catalog/paths.py's
    # research_root) expects "the workspace root", appending "research/"
    # itself -- unlike discover_research_evidence_inputs, which expects
    # --evidence-root to already BE that research/ directory. Passing
    # evidence_root's parent gives discover_catalog_inputs the same
    # "workspace root" shape it expects (verified directly: this is the
    # same value scripts/signal_research/analyze_signal_research.py's
    # --storage-root already uses for these same runs).
    raw_inputs, skipped = discover_catalog_inputs(args.storage_root)
    evidence_catalog_inputs, evidence_catalog_skipped = discover_catalog_inputs(
        args.evidence_root.parent
    )
    raw_inputs.extend(evidence_catalog_inputs)
    skipped += evidence_catalog_skipped
    evidence_inputs, evidence_skipped = discover_research_evidence_inputs(args.evidence_root)
    raw_inputs.extend(evidence_inputs)
    strategy_evidence_inputs, strategy_evidence_skipped = (
        discover_strategy_research_evidence_inputs(args.storage_root)
    )
    raw_inputs.extend(strategy_evidence_inputs)
    skipped += strategy_evidence_skipped
    # A 4th real Strategy Research run was found living under the same
    # second root as Signal Research during 18B's Milestone 1 work
    # (f4f3093ec5ec3f3a, predates all 3 runs 18A ever knew about) --
    # 18A's PRD assumption that "Strategy Research's root is already
    # correct" was wrong. Same fix, same root value, applied here too.
    evidence_strategy_inputs, evidence_strategy_skipped = (
        discover_strategy_research_evidence_inputs(args.evidence_root.parent)
    )
    raw_inputs.extend(evidence_strategy_inputs)
    skipped += evidence_strategy_skipped
    if args.without_base_bundle:
        bundle = build_projection_bundle(raw_inputs, generated_at_utc=generated_at)
    else:
        bundle = refresh_publication_projection_bundle(
            _load_base_bundle(args.base_bundle),
            raw_inputs,
            generated_at_utc=generated_at,
        )
    _write_bundle_atomic(args.output, bundle)
    print(
        f"wrote {len(bundle.artifacts)} artifacts "
        f"({len(raw_inputs)} projected inputs, "
        f"{skipped + evidence_skipped} skipped) to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
