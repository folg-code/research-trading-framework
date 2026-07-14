"""Inspect a local Databento DBN archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.infrastructure.importers.databento import DatabentoDBNInspector
from trading_framework.market.importers import compute_source_checksum_sha256


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a Databento DBN archive.")
    parser.add_argument(
        "--path",
        required=True,
        type=Path,
        help="Path to a local .dbn or .dbn.zst archive",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print inspection output as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the inspect CLI."""
    args = _build_parser().parse_args(argv)
    path = args.path
    if not path.exists():
        print(f"archive not found: {path}", file=sys.stderr)
        return 1

    inspector = DatabentoDBNInspector()
    result = inspector.inspect(path)
    checksum = compute_source_checksum_sha256(path)

    symbols = list(result.symbols)
    payload = {
        "path": str(result.path),
        "source_format": result.source_format.value,
        "vendor_schema": result.vendor_schema,
        "nbytes": result.nbytes,
        "dataset": result.dataset,
        "symbols": symbols,
        "start_at": None if result.start_at is None else result.start_at.isoformat(),
        "end_at": None if result.end_at is None else result.end_at.isoformat(),
        "row_estimate": result.row_estimate,
        "source_checksum_sha256": checksum,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"path: {payload['path']}")
    print(f"source_format: {payload['source_format']}")
    print(f"vendor_schema: {payload['vendor_schema']}")
    print(f"nbytes: {payload['nbytes']}")
    print(f"dataset: {payload['dataset']}")
    print(f"symbols: {', '.join(symbols)}")
    print(f"start_at: {payload['start_at']}")
    print(f"end_at: {payload['end_at']}")
    print(f"source_checksum_sha256: {payload['source_checksum_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
