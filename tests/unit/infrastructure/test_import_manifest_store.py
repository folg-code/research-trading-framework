"""Import manifest persistence tests."""

from datetime import UTC, datetime
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.import_manifest_store import (
    read_import_manifest,
    write_import_manifest,
)
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.importers import (
    MANIFEST_VERSION,
    ArchiveSourceFormat,
    ImportManifest,
)
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq_cme_trades_2025",
        ),
        version=1,
    )


def _manifest() -> ImportManifest:
    return ImportManifest(
        manifest_version=MANIFEST_VERSION,
        source_path="user_data/sample.dbn.zst",
        source_format=ArchiveSourceFormat.DATABENTO_DBN,
        source_checksum_sha256="abc123",
        vendor_schema="trades",
        symbol_mapping={"NQ.FUT": "nq"},
        decode_row_count=100,
        rejected_row_count=0,
        imported_at_utc=datetime(2025, 7, 13, 22, 0, tzinfo=UTC),
        normalization_version="databento-trades-v1",
        framework_version="0.1.0",
    )


def test_write_import_manifest_persists_json(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    dataset_ref = _dataset_ref()
    manifest = _manifest()

    path = write_import_manifest(storage_root, dataset_ref, manifest)

    assert path.exists()
    assert path.name == "import_manifest.json"
    loaded = read_import_manifest(storage_root, dataset_ref)
    assert loaded == manifest
