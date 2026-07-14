"""Import outright contracts from a Databento DBN trades archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.market_data import import_databento_contract_trades_archive
from trading_framework.market.contracts import MARKET_TRADE_CONTRACT_SCHEMA_VERSION
from trading_framework.market.importers import DatabentoContractTradesArchiveImportConfig


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import outright futures contracts from a Databento DBN trades archive.",
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
        "--product",
        required=True,
        help="Root futures product code (e.g. NQ)",
    )
    parser.add_argument(
        "--source-id",
        required=True,
        help="Stable dataset source slug shared across contracts from this archive",
    )
    parser.add_argument(
        "--schema-version",
        default=MARKET_TRADE_CONTRACT_SCHEMA_VERSION,
        help="Persisted contract trade schema version",
    )
    parser.add_argument(
        "--normalization-version",
        default="databento-contract-trades-v1",
        help="Normalization version recorded on imported datasets",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print import result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the contract trades import CLI."""
    args = _build_parser().parse_args(argv)
    if not args.path.exists():
        print(f"archive not found: {args.path}", file=sys.stderr)
        return 1

    config = DatabentoContractTradesArchiveImportConfig(
        path=args.path,
        product=args.product,
        source_id=args.source_id,
        schema_version=args.schema_version,
        normalization_version=args.normalization_version,
        lineage={"source_file": args.path.name},
    )
    result = import_databento_contract_trades_archive(
        config,
        storage_root=args.storage_root,
    )

    contracts_payload = [
        {
            "contract_code": contract.contract_code,
            "dataset_ref": str(contract.dataset_ref),
            "validation_passed": contract.validation_result.is_valid,
            "record_count": contract.record_count,
        }
        for contract in result.contracts
    ]
    all_valid = all(contract.validation_result.is_valid for contract in result.contracts)
    payload = {
        "contracts": contracts_payload,
        "rejected_spread_row_count": result.rejected_spread_row_count,
        "source_checksum_sha256": result.source_checksum_sha256,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"contracts_imported: {len(result.contracts)}")
        print(f"rejected_spread_row_count: {result.rejected_spread_row_count}")
        for contract in result.contracts:
            print(
                f"  {contract.contract_code}: {contract.dataset_ref} "
                f"rows={contract.record_count} "
                f"valid={contract.validation_result.is_valid}"
            )

    return 0 if all_valid and len(result.contracts) > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
