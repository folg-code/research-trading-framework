"""Archive import contract tests."""

from datetime import UTC, datetime
from pathlib import Path

from trading_framework.market.importers import (
    MANIFEST_VERSION,
    ArchiveInspectionResult,
    ArchiveSourceFormat,
    ImportManifest,
    compute_source_checksum_sha256,
)


def test_compute_source_checksum_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "sample.dbn"
    path.write_bytes(b"abc123")

    assert compute_source_checksum_sha256(path) == compute_source_checksum_sha256(path)
    assert len(compute_source_checksum_sha256(path)) == 64


def test_import_manifest_serializes_to_dict() -> None:
    manifest = ImportManifest(
        manifest_version=MANIFEST_VERSION,
        source_path="user_data/sample.dbn.zst",
        source_format=ArchiveSourceFormat.DATABENTO_DBN,
        source_checksum_sha256="abc",
        vendor_schema="trades",
        symbol_mapping={"NQH9": "nq"},
        decode_row_count=100,
        rejected_row_count=2,
        imported_at_utc=datetime(2025, 7, 13, 22, 0, tzinfo=UTC),
        normalization_version="databento-trades-v1",
        framework_version="0.1.0",
    )

    payload = manifest.to_dict()
    assert payload["source_format"] == "databento_dbn"
    assert payload["symbol_mapping"] == {"NQH9": "nq"}


def test_archive_inspection_result_fields() -> None:
    result = ArchiveInspectionResult(
        path=Path("sample.dbn.zst"),
        source_format=ArchiveSourceFormat.DATABENTO_DBN,
        vendor_schema="trades",
        nbytes=10,
        dataset="GLBX.MDP3",
        symbols=("NQ.FUT",),
        start_at=None,
        end_at=None,
        row_estimate=10,
    )
    assert result.vendor_schema == "trades"
