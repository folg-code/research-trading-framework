"""CLI tests for the Predictive Research dataset builder."""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest
from scripts.predictive_research import build_predictive_dataset as build_cli

from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import predictive_research_dataset_dir
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.time.models.timeframe import Timeframe


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> str:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="cli-predictive-research",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=csv_path,
            dataset_id=dataset_id,
            import_config=OhlcvImportConfig(
                column_mapping=OhlcvColumnMapping(
                    timestamp="timestamp",
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                ),
                timeframe=Timeframe("1m"),
                timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
                source_timezone=UTC,
            ),
            schema_version="ohlcv.v1",
            normalization_version="utc-interval-start.v1",
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    metadata = FileDatasetRegistry(storage_root).get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    return str(result.dataset_ref)


def _write_definition(path: Path, *, dataset_ref: str, start: str, end: str) -> None:
    dataset = DatasetRef.parse(dataset_ref)
    payload = {
        "study_id": "cli_predictive_research_test",
        "dataset_ref": {
            "dataset_id": dataset.dataset_id.canonical(),
            "version": dataset.version,
        },
        "time_range": {"start": start, "end": end},
        "evaluation_timeframe": "1m",
        "features": [
            {
                "component_id": "volatility.atr",
                "parameters": {"period": 2},
                "output_id": "value",
                "alias": "atr",
                "transform": "NONE",
            }
        ],
        "label": {"kind": "REGRESSION", "horizon": "5m"},
        "split": {
            "mode": "EXPANDING",
            "fold_count": 2,
            "test_span": "3h",
            "embargo_span": "15m",
            "min_train_rows": 10,
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_predictive_dataset_cli_missing_definition_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = build_cli.main(
        [
            "--storage-root",
            str(tmp_path / "workspace"),
            "--definition",
            str(tmp_path / "missing.json"),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "study file not found" in captured.err


def test_build_predictive_dataset_cli_persists_envelope(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(DatasetRef.parse(dataset_ref))
    definition_path = tmp_path / "study.json"
    _write_definition(
        definition_path,
        dataset_ref=dataset_ref,
        start=metadata.start_at.isoformat(),
        end=metadata.end_at.isoformat(),
    )

    exit_code = build_cli.main(
        [
            "--storage-root",
            str(storage_root),
            "--definition",
            str(definition_path),
            "--json",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(output)
    dataset_id = payload["dataset_id"]
    assert payload["persisted"] is True
    assert payload["labelled_rows"] > 0
    assert payload["fold_count"] == 2
    dataset_dir = predictive_research_dataset_dir(storage_root, dataset_id)
    assert (dataset_dir / "manifest.json").exists()
    assert (dataset_dir / "features.parquet").exists()
    assert (dataset_dir / "folds.json").exists()
