"""CLI tests for Signal Research production scripts."""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from scripts.signal_research import (
    analyze_signal_research as analyze_signal_research_cli,
)
from scripts.signal_research import (
    render_signal_research_report as render_signal_research_report_cli,
)
from scripts.signal_research import run_signal_research as run_signal_research_cli

from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import (
    signal_research_analytics_summary_path,
    signal_research_report_path,
)
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
        source_id="cli-signal-research",
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
        "research": {
            "id": "cli_signal_research_test",
            "scope": "SIGNAL_MODEL_ONLY",
            "dataset_ref": {
                "dataset_id": dataset.dataset_id.canonical(),
                "version": dataset.version,
            },
            "time_range": {"start": start, "end": end},
            "signal_model": "higher_low_long",
            "horizons": ["5m"],
        }
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_signal_research_cli_run_analyze_render_pipeline(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("plotly")
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(DatasetRef.parse(dataset_ref))

    definition_path = tmp_path / "definition.yaml"
    _write_definition(
        definition_path,
        dataset_ref=dataset_ref,
        start=metadata.start_at.date().isoformat(),
        end=metadata.end_at.date().isoformat(),
    )

    run_exit = run_signal_research_cli.main(
        [
            "--storage-root",
            str(storage_root),
            "--definition",
            str(definition_path),
            "--json",
        ]
    )
    run_output = capsys.readouterr().out
    assert run_exit == 0
    run_id = json.loads(run_output)["run_id"]

    analyze_exit = analyze_signal_research_cli.main(
        [
            "--storage-root",
            str(storage_root),
            "--run-id",
            run_id,
            "--definition",
            str(definition_path),
            "--persist-analytics",
            "--json",
        ]
    )
    capsys.readouterr()
    assert analyze_exit == 0
    assert signal_research_analytics_summary_path(storage_root, run_id).exists()

    render_exit = render_signal_research_report_cli.main(
        [
            "--storage-root",
            str(storage_root),
            "--run-id",
            run_id,
            "--json",
        ]
    )
    render_output = capsys.readouterr().out
    assert render_exit == 0
    payload = json.loads(render_output)
    assert payload["used_cached_analytics"] is True
    report_path = Path(payload["output_path"])
    assert report_path.exists()
    assert report_path == signal_research_report_path(storage_root, run_id)
    assert "Signal Research Report" in report_path.read_text(encoding="utf-8")
