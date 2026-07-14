"""Import a Databento DBN trades archive into framework storage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.market_data import import_databento_trades_archive
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId
from trading_framework.market.importers import DatabentoTradesArchiveImportConfig, SymbolMapping
from trading_framework.time.models.timeframe import Timeframe


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a Databento DBN trades archive into WORKING dataset storage.",
    )
    parser.add_argument(
        "--path",
        required=True,
        type=Path,
        help="Path to a local trades .dbn or .dbn.zst archive",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Framework storage root for metadata and normalized trades",
    )
    parser.add_argument(
        "--instrument-id",
        required=True,
        help="Canonical framework instrument identifier",
    )
    parser.add_argument(
        "--source-id",
        required=True,
        help="Stable dataset source slug",
    )
    parser.add_argument(
        "--provider-symbol",
        required=True,
        help="Provider symbol to import from the archive",
    )
    parser.add_argument(
        "--schema-version",
        default="market-trade-v1",
        help="Persisted trade schema version",
    )
    parser.add_argument(
        "--normalization-version",
        default="databento-trades-v1",
        help="Normalization version recorded on the dataset",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print import result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the trades import CLI."""
    args = _build_parser().parse_args(argv)
    if not args.path.exists():
        print(f"archive not found: {args.path}", file=sys.stderr)
        return 1

    config = DatabentoTradesArchiveImportConfig(
        path=args.path,
        dataset_id=DatasetId(
            instrument_id=Identifier(args.instrument_id),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id=args.source_id,
        ),
        symbol_mapping=SymbolMapping(
            provider_symbol=args.provider_symbol,
            instrument_id=Identifier(args.instrument_id),
        ),
        schema_version=args.schema_version,
        normalization_version=args.normalization_version,
        lineage={"source_file": args.path.name},
    )

    result = import_databento_trades_archive(
        config,
        storage_root=args.storage_root,
    )

    payload = {
        "dataset_ref": str(result.dataset_ref),
        "validation_passed": result.validation_result.is_valid,
        "decode_row_count": result.manifest.decode_row_count,
        "rejected_row_count": result.manifest.rejected_row_count,
        "source_checksum_sha256": result.manifest.source_checksum_sha256,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"dataset_ref: {payload['dataset_ref']}")
        print(f"validation_passed: {payload['validation_passed']}")
        print(f"decode_row_count: {payload['decode_row_count']}")
        print(f"rejected_row_count: {payload['rejected_row_count']}")
        print(f"source_checksum_sha256: {payload['source_checksum_sha256']}")

    return 0 if result.validation_result.is_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
