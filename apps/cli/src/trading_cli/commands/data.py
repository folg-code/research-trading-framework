"""`trading-cli data fetch` (S046-T009 databento; T010 binance is Wave 3).

**Naming caveat (D-S046-10):** ``data fetch databento`` is a local archive
*import*, not a network fetch. It reads a ``.dbn``/``.dbn.zst`` file already
on disk (config key ``data.databento.archive``) and publishes a ``DatasetRef``
from it, mirroring ``scripts/databento/import_trades.py``. ``data fetch
binance`` (Wave 3) is the opposite shape: it fetches over the network for a
``start``/``end`` date range. The two providers share a command name but not
a config shape, by design -- see ``--help`` on ``data fetch``.

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
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_framework.application.market_data import import_databento_trades_archive
from trading_framework.core.exceptions import ValidationError

# apps/cli boundary widening (documented in tests/unit/test_apps_boundaries.py
# and apps/cli/CLAUDE.md): config/identifier value objects for the archive
# import workflow, not research/execution logic.
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId
from trading_framework.market.importers import DatabentoTradesArchiveImportConfig, SymbolMapping
from trading_framework.time.models.timeframe import Timeframe

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, WorkflowError
from trading_cli.plan import ResolvedPlan

_SUPPORTED_PROVIDERS = ("binance", "databento")
_DEFAULT_SCHEMA_VERSION = "market-trade-v1"
_DEFAULT_NORMALIZATION_VERSION = "databento-trades-v1"


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
    output_path = str(Path(config.storage_root) / "market_data")
    return ResolvedPlan(
        group="data",
        command="fetch",
        workflow=f"data.fetch.{provider}",
        arguments={"provider": provider, **provider_args},
        output_paths=(output_path,),
        storage_root=str(config.storage_root),
        implemented=(provider == "databento"),
    )


def run(plan: ResolvedPlan) -> dict[str, Any]:
    provider = plan.arguments.get("provider")
    if provider != "databento":
        raise WorkflowError(
            f"'data fetch {provider}' is not implemented yet; "
            "see SPRINT_046.md Wave 3 (S046-T010, requires Sprint 045 on main)"
        )
    return _run_databento(plan.arguments, Path(plan.storage_root))


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
        schema_version=_DEFAULT_SCHEMA_VERSION,
        normalization_version=_DEFAULT_NORMALIZATION_VERSION,
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


def _require(args: dict[str, Any], key: str, block: str) -> None:
    if not args.get(key):
        raise ConfigError(f"config is missing '{block}.{key}' required by 'data fetch'")
