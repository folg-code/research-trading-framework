"""CLI tests for bounded model-family experiments."""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from scripts.signal_research import run_model_family as run_model_family_cli

from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import signal_research_family_experiment_dir
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.time.models.timeframe import Timeframe


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> str:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.core.identifiers import Identifier
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="cli-model-family",
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


def _write_family_definition(path: Path, *, dataset_ref: str, start: str, end: str) -> None:
    dataset = DatasetRef.parse(dataset_ref)
    payload = {
        "research": {
            "id": "cli_signal_family",
            "scope": "SIGNAL_MODEL_ONLY",
            "dataset_ref": {
                "dataset_id": dataset.dataset_id.canonical(),
                "version": dataset.version,
            },
            "time_range": {"start": start, "end": end},
            "horizons": ["5m"],
            "candidate_bounds": {"max_candidates": 2},
            "model_family": {
                "id": "canonical_signal_family",
                "variants": [
                    {"id": "higher_low", "signal_model": "higher_low_long"},
                    {"id": "vol_edge", "signal_model": "high_volatility_long_edge"},
                    {"id": "combined", "signal_model": "high_vol_and_higher_low"},
                ],
            },
        }
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_run_model_family_cli_respects_candidate_bounds(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("plotly")
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(DatasetRef.parse(dataset_ref))
    definition_path = tmp_path / "family_definition.yaml"
    _write_family_definition(
        definition_path,
        dataset_ref=dataset_ref,
        start=metadata.start_at.date().isoformat(),
        end=metadata.end_at.date().isoformat(),
    )

    exit_code = run_model_family_cli.main(
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
    assert payload["candidates_generated"] == 3
    assert payload["candidates_evaluated"] == 2
    assert payload["candidates_skipped"] == 1
    assert payload["skipped_variant_ids"] == ["combined"]
    experiment_dir = signal_research_family_experiment_dir(
        storage_root,
        payload["experiment_id"],
    )
    assert (experiment_dir / "manifest.json").exists()
    assert (experiment_dir / "family_comparison.html").exists()
