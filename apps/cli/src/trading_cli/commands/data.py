"""`trading-cli data fetch` (S046-T009 databento; S046-T010 binance).

**Naming caveat (D-S046-10):** ``data fetch databento`` is a local archive
*import*, not a network fetch. It reads a ``.dbn``/``.dbn.zst`` file already
on disk (config key ``data.databento.archive``) and publishes a ``DatasetRef``
from it, mirroring ``scripts/databento/import_trades.py``. ``data fetch
binance`` is the opposite shape: it fetches over the network for a
``start``/``end`` date range, mirroring
``scripts/market_data/import_binance_ohlcv.py``. The two providers share a
command name but not a config shape, by design -- see ``--help`` on
``data fetch``.

**Config-schema limitation:** D-S046-07 locks ``data.databento`` to exactly
``archive`` and ``instrument_id``. The underlying workflow
(``import_databento_trades_archive``) also needs ``source_id`` and
``provider_symbol``. Rather than reopening the locked schema, this command
uses the same fixed defaults ``scripts/databento/import_trades.py`` uses for
``schema_version``/``normalization_version``, plus one CLI-owned convention:
``provider_symbol`` and ``source_id`` default from ``instrument_id``. This
covers the common case (an archive already keyed by the framework's
instrument id); an archive with a distinct provider symbol or a shared
``source_id`` across contracts needs the existing script directly.

**Binance interval limitation (TD-023, binding):** the historical reader
reuses the live-path kline mapper, which only decodes ``interval="1m"``
today; any other interval fails one layer down, inside the mapper, not at
this command's own validation. Rather than let an operator hit that
confusing failure, ``resolve_plan`` rejects a non-``1m`` interval itself --
*before* any side effect -- naming ``data.binance.interval`` and pointing at
TD-023, exactly the "validate eagerly with a clear error" option
SPRINT_046.md Wave 3 calls for.

**Binance credentials:** the CLI never reads or forwards an API key. The
config loader already rejects any credential-shaped key anywhere in the
document (D-S046-08); ``data.binance`` additionally has no ``api_key`` key in
its locked schema (D-S046-07) to reject in the first place.
``import_binance_futures_ohlcv`` is always called with ``api_key=None``, and
the underlying fetch resolves ``TRADING_FRAMEWORK_BINANCE_API_KEY`` from the
environment itself if it is set.

**``publish`` limitation:** the underlying workflow always finalizes and
publishes (there is no draft-only import path), so ``data.binance.publish``
can only be left at its default (``true``); an explicit ``false`` is a
config error naming the same limitation, rather than a value that is silently
ignored.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from trading_framework.application.market_data import (
    ImportBinanceFuturesOhlcvRequest,
    import_binance_futures_ohlcv,
    import_databento_trades_archive,
)
from trading_framework.core.exceptions import ValidationError

# apps/cli boundary widening (documented in tests/unit/test_apps_boundaries.py
# and apps/cli/CLAUDE.md): config/identifier value objects for the archive
# and Binance import workflows, not research/execution logic.
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId
from trading_framework.market.importers import DatabentoTradesArchiveImportConfig, SymbolMapping
from trading_framework.time.models.timeframe import Timeframe

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, WorkflowError
from trading_cli.plan import ResolvedPlan

_SUPPORTED_PROVIDERS = ("binance", "databento")
_DEFAULT_DATABENTO_SCHEMA_VERSION = "market-trade-v1"
_DEFAULT_DATABENTO_NORMALIZATION_VERSION = "databento-trades-v1"

#: TD-023 -- the historical reader reuses the live-path kline mapper, which
#: only decodes 1-minute klines today. Enforced eagerly in `resolve_plan`.
_SUPPORTED_BINANCE_INTERVALS = ("1m",)
_DEFAULT_BINANCE_MODE = "ohlcv"
_DEFAULT_BINANCE_SCHEMA_VERSION = "market-bar-v1"
_DEFAULT_BINANCE_NORMALIZATION_VERSION = "binance-usdm-klines-v1"
_DEFAULT_BINANCE_SOURCE_ID = "binance-usdm-klines-v1"


def resolve_plan(config: CliConfig) -> ResolvedPlan:
    if config.data is None:
        raise ConfigError("config is missing the 'data' block required by 'data fetch'")
    provider = config.data.get("provider")
    if provider not in _SUPPORTED_PROVIDERS:
        raise ConfigError(
            f"unsupported 'data.provider': {provider!r}; "
            f"supported: {', '.join(_SUPPORTED_PROVIDERS)}"
        )
    provider_args = dict(config.data.get(provider) or {})
    if provider == "databento":
        _require(provider_args, "archive", "data.databento")
        _require(provider_args, "instrument_id", "data.databento")
    else:
        _require(provider_args, "symbol", "data.binance")
        _require(provider_args, "instrument_id", "data.binance")
        _require(provider_args, "start", "data.binance")
        _require(provider_args, "end", "data.binance")
        interval = str(provider_args.get("interval") or "1m")
        if interval not in _SUPPORTED_BINANCE_INTERVALS:
            raise ConfigError(
                f"unsupported 'data.binance.interval': {interval!r}; "
                f"only {_SUPPORTED_BINANCE_INTERVALS!r} is supported today "
                "(TD-023: the historical reader reuses the live-path kline "
                "mapper, which only decodes 1-minute klines)"
            )
        if provider_args.get("publish", True) is False:
            raise ConfigError(
                "'data.binance.publish: false' is not supported; "
                "import_binance_futures_ohlcv always finalizes and publishes "
                "-- there is no draft-only import path in v1"
            )
    output_path = str(Path(config.storage_root) / "market_data")
    return ResolvedPlan(
        group="data",
        command="fetch",
        workflow=f"data.fetch.{provider}",
        arguments={"provider": provider, **provider_args},
        output_paths=(output_path,),
        storage_root=str(config.storage_root),
        implemented=True,
    )


def run(plan: ResolvedPlan) -> dict[str, Any]:
    provider = plan.arguments.get("provider")
    storage_root = Path(plan.storage_root)
    if provider == "databento":
        return _run_databento(plan.arguments, storage_root)
    if provider == "binance":
        return _run_binance(plan.arguments, storage_root)
    raise WorkflowError(f"'data fetch {provider}' is not implemented")


def _run_databento(arguments: dict[str, Any], storage_root: Path) -> dict[str, Any]:
    archive_path = Path(arguments["archive"])
    if not archive_path.is_file():
        raise ConfigError(f"archive not found: {archive_path}")
    instrument_id = str(arguments["instrument_id"])
    source_id = str(arguments.get("source_id") or instrument_id)
    provider_symbol = str(arguments.get("provider_symbol") or instrument_id)

    config = DatabentoTradesArchiveImportConfig(
        path=archive_path,
        dataset_id=DatasetId(
            instrument_id=Identifier(instrument_id),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id=source_id,
        ),
        symbol_mapping=SymbolMapping(
            provider_symbol=provider_symbol,
            instrument_id=Identifier(instrument_id),
        ),
        schema_version=_DEFAULT_DATABENTO_SCHEMA_VERSION,
        normalization_version=_DEFAULT_DATABENTO_NORMALIZATION_VERSION,
        lineage={"source_file": archive_path.name},
    )

    try:
        result = import_databento_trades_archive(config, storage_root=storage_root)
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        raise WorkflowError(f"'data fetch databento' failed: {exc}") from exc

    return {
        "dataset_ref": str(result.dataset_ref),
        "validation_passed": result.validation_result.is_valid,
        "decode_row_count": result.manifest.decode_row_count,
        "rejected_row_count": result.manifest.rejected_row_count,
    }


def _run_binance(arguments: dict[str, Any], storage_root: Path) -> dict[str, Any]:
    instrument_id = str(arguments["instrument_id"])
    symbol = str(arguments["symbol"])
    interval = str(arguments.get("interval") or "1m")
    mode = str(arguments.get("mode") or _DEFAULT_BINANCE_MODE)
    start_at = _parse_utc_datetime(arguments["start"], key="data.binance.start")
    end_at = _parse_utc_datetime(arguments["end"], key="data.binance.end")

    request = ImportBinanceFuturesOhlcvRequest(
        instrument_id=Identifier(instrument_id),
        symbol=symbol,
        interval=interval,
        start_at=start_at,
        end_at=end_at,
        schema_version=_DEFAULT_BINANCE_SCHEMA_VERSION,
        normalization_version=_DEFAULT_BINANCE_NORMALIZATION_VERSION,
        mode=mode,
        source_id=_DEFAULT_BINANCE_SOURCE_ID,
        # Never read from config -- resolved from TRADING_FRAMEWORK_BINANCE_API_KEY
        # by the fetch layer itself (D-S046-08). The CLI holds no key of its own.
        api_key=None,
    )

    try:
        result = import_binance_futures_ohlcv(request, storage_root=storage_root)
    except ValidationError as exc:
        raise WorkflowError(f"'data fetch binance' failed: {exc}") from exc

    manifest_payload = result.manifest.to_dict()
    return {
        "dataset_ref": str(result.dataset_ref),
        "reused": result.reused,
        "validation_passed": result.validation_result.is_valid,
        "page_count": manifest_payload["page_count"],
        "rows_decoded": manifest_payload["rows_decoded"],
        "rows_rejected": manifest_payload["rows_rejected"],
        "gap_count": len(result.manifest.gaps),
        "api_key_used": manifest_payload["api_key_used"],
    }


def _parse_utc_datetime(value: Any, *, key: str) -> datetime:
    """Parse a `start`/`end` value into a UTC-aware `datetime`.

    PyYAML's safe loader already parses an unquoted ISO-8601 timestamp (e.g.
    ``2025-01-01T00:00:00Z``) into a `datetime` -- this handles that case
    directly and falls back to string parsing for a quoted value.
    """
    if isinstance(value, datetime):
        candidate = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            candidate = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ConfigError(f"invalid ISO-8601 UTC timestamp for '{key}': {value!r}") from exc
    if candidate.tzinfo is None:
        raise ConfigError(f"'{key}' must be timezone-aware ISO-8601 UTC (e.g. ...Z): {value!r}")
    return candidate


def _require(args: dict[str, Any], key: str, block: str) -> None:
    if not args.get(key):
        raise ConfigError(f"config is missing '{block}.{key}' required by 'data fetch'")
