"""Derive 1m OHLCV bars from a published trades dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.market_data import derive_ohlcv_from_trades
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.derivation import (
    DERIVED_OHLCV_PROVIDER,
    TRADES_TO_BARS_VERSION,
    DerivedOhlcvFromTradesConfig,
)
from trading_framework.time.models.timeframe import Timeframe


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive 1m OHLCV bars from a published trades dataset.",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Framework storage root for metadata and normalized datasets",
    )
    parser.add_argument(
        "--source-dataset-ref",
        required=True,
        help="Canonical published trades DatasetRef (e.g. nq|trades|tick|databento|slug@1)",
    )
    parser.add_argument(
        "--instrument-id",
        required=True,
        help="Canonical framework instrument identifier",
    )
    parser.add_argument(
        "--derived-source-id",
        required=True,
        help="Stable derived OHLCV dataset source slug",
    )
    parser.add_argument(
        "--schema-version",
        default="market-bar-v1",
        help="Persisted bar schema version",
    )
    parser.add_argument(
        "--normalization-version",
        default=TRADES_TO_BARS_VERSION,
        help="Derivation normalization version recorded on the dataset",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print derivation result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the derive-bars CLI."""
    args = _build_parser().parse_args(argv)

    try:
        source_dataset_ref = DatasetRef.parse(args.source_dataset_ref)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    config = DerivedOhlcvFromTradesConfig(
        source_dataset_ref=source_dataset_ref,
        target_dataset_id=DatasetId(
            instrument_id=Identifier(args.instrument_id),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider=DERIVED_OHLCV_PROVIDER,
            source_id=args.derived_source_id,
        ),
        schema_version=args.schema_version,
        normalization_version=args.normalization_version,
    )

    try:
        result = derive_ohlcv_from_trades(
            config,
            storage_root=args.storage_root,
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "dataset_ref": str(result.dataset_ref),
        "source_dataset_ref": str(result.source_dataset_ref),
        "validation_passed": result.validation_result.is_valid,
        "bar_count": result.bar_count,
        "lineage": config.lineage(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"dataset_ref: {payload['dataset_ref']}")
        print(f"source_dataset_ref: {payload['source_dataset_ref']}")
        print(f"validation_passed: {payload['validation_passed']}")
        print(f"bar_count: {payload['bar_count']}")

    return 0 if result.validation_result.is_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
