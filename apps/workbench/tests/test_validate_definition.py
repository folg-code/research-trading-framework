"""Tests for preflight definition validation (Sprint 064 T008).

Real `trading-cli` subprocess -- ADR-0038 section 3's whole point is that
`--dry-run` is the framework's own validation, not a workbench-authored
reimplementation, so this exercises the actual command rather than a stub.
Tier 1-adjacent but slower than the rest of this suite for that reason.
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from pathlib import Path

from trading_framework.application.market_data import (
    ImportExternalDatasetRequest,
    finalize_dataset,
    import_external_dataset,
    publish_dataset,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId
from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.time.models.timeframe import Timeframe

from workbench_core.validate_definition import (
    ValidateSignalResearchDefinitionRequest,
    validate_signal_research_definition,
)


def _publish_dataset(storage_root: Path, *, csv_path: Path) -> str:
    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="workbench-validate-test",
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
    return str(result.dataset_ref)


def test_validate_valid_definition_returns_resolved_plan(
    tmp_path: Path, ohlcv_sample_1m_path: Path
) -> None:
    dataset_ref = _publish_dataset(tmp_path, csv_path=ohlcv_sample_1m_path)
    definition = {
        "research_id": "workbench_validate_test",
        "research_scope": "SIGNAL_MODEL_ONLY",
        "dataset_ref": dataset_ref,
        "time_range": {"start": "2018-12-31", "end": "2018-12-31"},
        "horizons": ["5m"],
        "signal_model": "higher_low_long",
        "baseline": {"type": "AFTER_SIGNAL"},
    }

    outcome = asyncio.run(
        validate_signal_research_definition(
            ValidateSignalResearchDefinitionRequest(definition=definition),
            storage_root=tmp_path,
        )
    )

    assert outcome.ok is True
    assert outcome.plan is not None
    assert outcome.plan["arguments"]["research_id"] == "workbench_validate_test"
    assert outcome.plan["arguments"]["definition_hash"]
    assert outcome.error_message is None


def test_validate_bad_definition_surfaces_frameworks_own_error(tmp_path: Path) -> None:
    definition = {
        "research_id": "workbench_validate_test",
        "research_scope": "SIGNAL_MODEL_ONLY",
        "dataset_ref": "not-a-real-dataset-ref",
        "time_range": {"start": "2018-12-31", "end": "2018-12-31"},
        "horizons": ["5m"],
        "signal_model": "higher_low_long",
        "baseline": {"type": "AFTER_SIGNAL"},
    }

    outcome = asyncio.run(
        validate_signal_research_definition(
            ValidateSignalResearchDefinitionRequest(definition=definition),
            storage_root=tmp_path,
        )
    )

    assert outcome.ok is False
    assert outcome.plan is None
    assert outcome.error_message
