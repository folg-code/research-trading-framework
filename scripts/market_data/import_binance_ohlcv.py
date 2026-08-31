"""Import a Binance USD-M historical OHLCV range into a published dataset version.

Thin CLI wrapper (ADR-0022 rule 3) around
``trading_framework.application.market_data.import_binance_futures_ohlcv``.
Parses arguments, builds an ``ImportBinanceFuturesOhlcvRequest`` and prints the
result -- it owns no lifecycle, validation or HTTP logic itself.

v1 supports only the ``1m`` interval: ``map_kline_payload`` (reused from the
live path) only decodes 1-minute klines today (TD-023). ``--interval`` is
exposed for forward compatibility with the D-S045-05 interval list, but any
value other than ``1m`` currently fails inside the reader/mapper -- that is a
known limitation, not a bug in this script.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from trading_framework.application.market_data import (
    ImportBinanceFuturesOhlcvRequest,
    import_binance_futures_ohlcv,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier

_DEFAULT_SCHEMA_VERSION = "market-bar-v1"
_DEFAULT_NORMALIZATION_VERSION = "binance-usdm-klines-v1"
_DEFAULT_SOURCE_ID = "binance-usdm-klines-v1"
_DEFAULT_PROVIDER = "binance"


def _parse_utc_datetime(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    return datetime.fromisoformat(text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Import a Binance USD-M historical OHLCV range and publish it as an "
            "ordinary DatasetRef (provider=binance)."
        ),
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Framework storage root for metadata and normalized bars",
    )
    parser.add_argument(
        "--instrument-id",
        required=True,
        help="Canonical framework instrument identifier (e.g. BTCUSDT.P)",
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Binance USD-M symbol (e.g. BTCUSDT)",
    )
    parser.add_argument(
        "--interval",
        default="1m",
        help=(
            "Binance kline interval. Only '1m' is supported today "
            "(map_kline_payload does not decode other intervals yet, TD-023); "
            "other values will fail during the import, not at parse time."
        ),
    )
    parser.add_argument(
        "--start",
        required=True,
        type=_parse_utc_datetime,
        help="Range start, inclusive, ISO-8601 UTC (e.g. 2024-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--end",
        required=True,
        type=_parse_utc_datetime,
        help="Range end, exclusive, ISO-8601 UTC (e.g. 2024-02-01T00:00:00Z)",
    )
    parser.add_argument(
        "--mode",
        default="ohlcv",
        help="Import mode; only 'ohlcv' is supported in v1 ('trades' is reserved)",
    )
    parser.add_argument(
        "--provider",
        default=_DEFAULT_PROVIDER,
        help="Dataset provider slug recorded on the published DatasetRef",
    )
    parser.add_argument(
        "--source-id",
        default=_DEFAULT_SOURCE_ID,
        help="Stable dataset source slug",
    )
    parser.add_argument(
        "--schema-version",
        default=_DEFAULT_SCHEMA_VERSION,
        help="Persisted bar schema version",
    )
    parser.add_argument(
        "--normalization-version",
        default=_DEFAULT_NORMALIZATION_VERSION,
        help="Normalization version recorded on imported datasets",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help=(
            "Optional Binance API key for public market-data GETs. "
            "Falls back to TRADING_FRAMEWORK_BINANCE_API_KEY when unset; "
            "anonymous requests work without either."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print import result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Binance historical OHLCV import CLI."""
    args = _build_parser().parse_args(argv)

    try:
        request = ImportBinanceFuturesOhlcvRequest(
            instrument_id=Identifier(args.instrument_id),
            symbol=args.symbol,
            interval=args.interval,
            start_at=args.start,
            end_at=args.end,
            schema_version=args.schema_version,
            normalization_version=args.normalization_version,
            mode=args.mode,
            provider=args.provider,
            source_id=args.source_id,
            api_key=args.api_key,
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        result = import_binance_futures_ohlcv(
            request,
            storage_root=args.storage_root,
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    manifest_payload = result.manifest.to_dict()
    payload = {
        "dataset_id": result.dataset_ref.dataset_id.canonical(),
        "dataset_ref": str(result.dataset_ref),
        "version": result.dataset_ref.version,
        "reused": result.reused,
        "validation_passed": result.validation_result.is_valid,
        "manifest": manifest_payload,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"dataset_ref: {payload['dataset_ref']}")
        print(f"reused: {payload['reused']}")
        print(f"validation_passed: {payload['validation_passed']}")
        print(f"page_count: {manifest_payload['page_count']}")
        print(f"rows_decoded: {manifest_payload['rows_decoded']}")
        print(f"rows_rejected: {manifest_payload['rows_rejected']}")
        print(f"gap_count: {len(result.manifest.gaps)}")
        print(f"api_key_used: {manifest_payload['api_key_used']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
