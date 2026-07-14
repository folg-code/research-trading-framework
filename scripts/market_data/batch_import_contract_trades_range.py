"""Import outright contracts from many Databento DBN archives into shared dataset versions."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.importers.databento import DatabentoDBNInspector
from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)
from trading_framework.infrastructure.importers.databento.contract_reader import (
    DatabentoDBNContractTradeReader,
)
from trading_framework.infrastructure.observability.function_profiler import FunctionProfiler
from trading_framework.infrastructure.observability.memory_stats import process_rss_mb
from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
from trading_framework.infrastructure.observability.profile_context import phase_timer_context
from trading_framework.infrastructure.storage.import_manifest_store import write_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.paths import dataset_contract_trades_partition_path
from trading_framework.infrastructure.validation.trade_validator import TradeBatchValidator
from trading_framework.market.contracts import (
    contract_instrument_id,
    trade_session_dates_from_ns,
    validate_contract_code,
    validate_product_code,
)
from trading_framework.market.contracts.storage_codec import utc_datetime_from_ns
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.importers import MANIFEST_VERSION, ImportManifest
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

_SLOW_ARCHIVE_SECONDS = 15.0


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)


def _archive_date(path: Path) -> datetime | None:
    marker = "glbx-mdp3-"
    if marker not in path.name:
        return None
    date_text = path.name.removeprefix(marker).split(".", maxsplit=1)[0]
    try:
        return datetime.strptime(date_text, "%Y%m%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def _group_indices_by_session_date(session_dates: list[date]) -> dict[date, list[int]]:
    groups: dict[date, list[int]] = defaultdict(list)
    for index, session_date in enumerate(session_dates):
        groups[session_date].append(index)
    return dict(groups)


def _write_archive_partitions(
    repository: ParquetContractTradeDatasetRepository,
    *,
    storage_root: Path,
    partitions: dict[
        tuple[DatasetRef, date],
        tuple[ContractChunkColumns, str, str, str],
    ],
    timer: PhaseTimer,
) -> None:
    for (dataset_ref, session_date), (
        columns,
        product,
        contract_code,
        source_file,
    ) in partitions.items():
        path = dataset_contract_trades_partition_path(storage_root, dataset_ref, session_date)
        phase_name = "write_merge_existing" if path.exists() else "write_new_partition"
        with timer.phase(phase_name):
            repository.write_session_partition_columns(
                dataset_ref,
                session_date,
                columns,
                product=product,
                contract_code=contract_code,
                source_file=source_file,
                merge_existing=path.exists(),
            )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch-import contract trades from DBN archives in a date range.",
    )
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--product", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD inclusive")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD inclusive")
    parser.add_argument("--schema-version", default="market-trade-contract-v1")
    parser.add_argument("--normalization-version", default="databento-contract-trades-v1")
    parser.add_argument("--log-every", type=int, default=1, help="Log every N archives")
    parser.add_argument("--max-archives", type=int, default=None, help="Limit archives (debug)")
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Emit per-phase timing report to stderr",
    )
    parser.add_argument(
        "--profile-deep",
        action="store_true",
        help="Enable cProfile function report in addition to phase timings",
    )
    parser.add_argument(
        "--profile-top",
        type=int,
        default=40,
        help="Number of top functions in --profile-deep report",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run batch contract import for one date range."""
    args = _build_parser().parse_args(argv)
    profiling_enabled = args.profile or args.profile_deep or args.log_every > 0
    timer = PhaseTimer(enabled=profiling_enabled)
    function_profiler = FunctionProfiler(enabled=args.profile_deep)
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)
    if end_date < start_date:
        print("end-date must not be before start-date", file=sys.stderr)
        return 1

    with timer.phase("discover_archives"):
        archives = sorted(
            path
            for path in args.archive_dir.rglob("*.dbn.zst")
            if (archive_date := _archive_date(path)) is not None
            and start_date <= archive_date <= end_date
        )
    if args.max_archives is not None:
        archives = archives[: args.max_archives]
    if not archives:
        print("no archives found in date range", file=sys.stderr)
        return 1

    timer.log(
        f"batch_import: {len(archives)} archives "
        f"from {args.start_date} to {args.end_date} "
        f"-> {args.storage_root}"
    )

    registry = FileDatasetRegistry(args.storage_root)
    repository = ParquetContractTradeDatasetRepository(args.storage_root)
    inspector = DatabentoDBNInspector()
    reader = DatabentoDBNContractTradeReader()
    validator = TradeBatchValidator()
    resolver = CmeEsRthSessionResolver()
    clock = SystemClock()

    dataset_refs: dict[str, DatasetRef] = {}
    record_counts: dict[str, int] = defaultdict(int)
    first_event: dict[str, datetime] = {}
    last_event: dict[str, datetime] = {}
    rejected_total = 0
    imported_archives = 0
    first_inspection = None
    first_checksum = ""

    import time as time_module

    with function_profiler.session(), phase_timer_context(timer):
        timer.begin_session()
        for archive_path in archives:
            archive_started = time_module.perf_counter()
            with timer.phase("inspect_archive"):
                inspection, source_checksum = inspector.inspect_with_checksum(archive_path)
            if first_inspection is None:
                first_inspection = inspection
                first_checksum = source_checksum

            with timer.phase("decode_archive"):
                columns_by_contract, rejected_spread_rows = reader.decode_contract_chunk_columns(
                    archive_path,
                    product=args.product,
                )
            rejected_total += rejected_spread_rows
            imported_archives += 1
            archive_rows = 0

            archive_partitions: dict[
                tuple[DatasetRef, date],
                tuple[ContractChunkColumns, str, str, str],
            ] = {}

            validated_product = validate_product_code(args.product)
            for contract_code in sorted(columns_by_contract):
                columns = columns_by_contract[contract_code]
                if len(columns) == 0:
                    continue
                archive_rows += len(columns)
                validated_contract_code = validate_contract_code(contract_code)

                with timer.phase("validate_trades"):
                    validation_result = validator.validate_storage_columns(columns)
                if not validation_result.is_valid:
                    msg = f"validation failed for {contract_code} in {archive_path.name}"
                    raise ValidationError(msg)

                if contract_code not in dataset_refs:
                    with timer.phase("allocate_dataset_ref"):
                        dataset_refs[contract_code] = registry.allocate_ref(
                            DatasetId(
                                instrument_id=contract_instrument_id(
                                    product=args.product,
                                    contract_code=contract_code,
                                ),
                                data_type="trades",
                                timeframe=Timeframe("tick"),
                                provider="databento",
                                source_id=args.source_id,
                            )
                        )

                with timer.phase("map.session_dates"):
                    session_dates = trade_session_dates_from_ns(
                        columns.ts_event_ns,
                        resolver=resolver,
                    )
                for session_date, indices in _group_indices_by_session_date(session_dates).items():
                    partition_key = (dataset_refs[contract_code], session_date)
                    subset = columns.take(indices)
                    existing = archive_partitions.get(partition_key)
                    if existing is None:
                        archive_partitions[partition_key] = (
                            subset,
                            validated_product,
                            validated_contract_code,
                            archive_path.name,
                        )
                    else:
                        existing[0].merge(subset)

                record_counts[contract_code] += len(columns)
                first = min(columns.ts_event_ns)
                last = max(columns.ts_event_ns)
                first_at = utc_datetime_from_ns(first)
                last_at = utc_datetime_from_ns(last)
                first_event[contract_code] = (
                    first_at
                    if contract_code not in first_event
                    else min(first_event[contract_code], first_at)
                )
                last_event[contract_code] = (
                    last_at
                    if contract_code not in last_event
                    else max(last_event[contract_code], last_at)
                )

            _write_archive_partitions(
                repository,
                storage_root=args.storage_root,
                partitions=archive_partitions,
                timer=timer,
            )

            archive_elapsed = time_module.perf_counter() - archive_started
            rss_mb = process_rss_mb()
            rss_text = f" rss_mb={rss_mb:.1f}" if rss_mb is not None else ""
            if archive_elapsed >= _SLOW_ARCHIVE_SECONDS:
                timer.log(
                    f"SLOW archive {archive_path.name}: {archive_elapsed:.1f}s "
                    f"rows={archive_rows} contracts={len(columns_by_contract)}{rss_text}"
                )
            if imported_archives % args.log_every == 0:
                timer.log(
                    f"[{imported_archives}/{len(archives)}] {archive_path.name} "
                    f"done in {archive_elapsed:.1f}s rows={archive_rows}{rss_text}"
                )

    imported_at = clock.now()
    with timer.phase("register_metadata"):
        assert first_inspection is not None
        for contract_code, dataset_ref in sorted(dataset_refs.items()):
            manifest = ImportManifest(
                manifest_version=MANIFEST_VERSION,
                source_path=str(archives[0]),
                source_format=first_inspection.source_format,
                source_checksum_sha256=first_checksum,
                vendor_schema=first_inspection.vendor_schema,
                symbol_mapping={contract_code: dataset_ref.dataset_id.instrument_id.value},
                decode_row_count=record_counts[contract_code],
                rejected_row_count=0,
                imported_at_utc=imported_at,
                normalization_version=args.normalization_version,
                framework_version=framework_version,
            )
            write_import_manifest(args.storage_root, dataset_ref, manifest)
            registry.register(
                DatasetMetadata(
                    dataset_ref=dataset_ref,
                    instrument_id=dataset_ref.dataset_id.instrument_id,
                    timeframe=dataset_ref.dataset_id.timeframe,
                    provider=dataset_ref.dataset_id.provider,
                    source_id=dataset_ref.dataset_id.source_id,
                    data_type=dataset_ref.dataset_id.data_type,
                    start_at=first_event[contract_code],
                    end_at=last_event[contract_code],
                    schema_version=args.schema_version,
                    normalization_version=args.normalization_version,
                    validation_status=ValidationStatus.PASSED,
                    lifecycle_status=DatasetLifecycleState.WORKING,
                    row_count=record_counts[contract_code],
                    checksum=first_checksum,
                    created_at=imported_at,
                    lineage={
                        "product": args.product,
                        "actual_contract": contract_code,
                        "batch_import": "true",
                        "archive_count": str(imported_archives),
                    },
                )
            )

    timer.report(title="batch_import_contract_trades_range phase report")
    if args.profile_deep:
        function_profiler.report(
            title="batch_import_contract_trades_range function profile",
            top_n=args.profile_top,
        )

    payload = {
        "archives_imported": imported_archives,
        "rejected_spread_row_count": rejected_total,
        "contracts": [
            {
                "contract_code": contract_code,
                "dataset_ref": str(dataset_refs[contract_code]),
                "record_count": record_counts[contract_code],
            }
            for contract_code in sorted(dataset_refs)
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"archives_imported: {payload['archives_imported']}")
        print(f"contracts: {len(payload['contracts'])}")
        for contract in payload["contracts"]:
            print(
                f"  {contract['contract_code']}: {contract['dataset_ref']} "
                f"rows={contract['record_count']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
