"""End-to-end metric test for operator-authored strategy examples (S047-T012).

Proves, against a real CLI run over a committed fixture dataset, both halves
of the PRD's success metrics this sprint delivers:

1. the run manifest's ``strategy_model_id`` is the *loaded* strategy's, not
   the Sprint 013 canonical example's (PRD success metric 1) -- this fails
   loudly if the loader ever silently falls back to the canonical example;
2. the loaded strategy's Market Model actually composes one of the two new
   catalog components, ``candle.wick`` (PRD success metric 2, component
   half -- the Exit/Risk half is deferred with Wave 2, ADR-0028 declined).

No network. No ML/DL extra. Committed fixture data only
(``tests/fixtures/market_data/ohlcv_sample_1m.csv`` via ``ohlcv_sample_1m_path``).
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState
from trading_framework.model_expression.expressions import (
    AndExpression,
    BinaryCompareExpression,
    CompareExpression,
    Expression,
    NotExpression,
    OrExpression,
)
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.strategy import CANONICAL_STRATEGY_MODEL_ID

from trading_cli.cli import main
from trading_cli.errors import EXIT_SUCCESS
from trading_cli.strategy_loader import load_strategy_definition

_FIXTURE_STRATEGY = (
    Path(__file__).parent / "fixtures" / "strategies" / "uses_candle_wick.py"
).resolve()


def _component_ids(expression: Expression) -> set[str]:
    """Recursively collect every ``ComponentOutputReference.component_id`` used."""
    if isinstance(expression, CompareExpression):
        operand = expression.operand
        if isinstance(operand, ComponentOutputReference):
            return {str(operand.component_id)}
        return set()
    if isinstance(expression, BinaryCompareExpression):
        ids: set[str] = set()
        for operand in (expression.left, expression.right):
            if isinstance(operand, ComponentOutputReference):
                ids.add(str(operand.component_id))
        return ids
    if isinstance(expression, AndExpression | OrExpression):
        return _component_ids(expression.left) | _component_ids(expression.right)
    if isinstance(expression, NotExpression):
        return _component_ids(expression.operand)
    return set()


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> str:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics
    from trading_framework.time.models.timeframe import Timeframe

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="cli-authored-strategy-examples",
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


def test_fixture_strategy_market_model_composes_candle_wick() -> None:
    """PRD success metric 2 (component half): the loaded definition really
    uses the new component -- not just a strategy that happens to load."""
    loaded = load_strategy_definition(str(_FIXTURE_STRATEGY))

    market_component_ids = _component_ids(loaded.definition.market_model.expression)

    assert "candle.wick" in market_component_ids


def test_research_run_strategy_file_manifest_uses_loaded_id_not_canonical(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """PRD success metric 1: fails if the loader ever silently falls back to
    the canonical example."""
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "version: 1\n"
        f"storage_root: {storage_root.as_posix()}\n\n"
        "research:\n"
        "  kind: strategy\n"
        "  strategy:\n"
        f"    dataset_ref: '{dataset_ref}'\n"
        "    timeframe: 1m\n"
        f"    strategy_file: {_FIXTURE_STRATEGY.as_posix()}\n",
        encoding="utf-8",
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]
    assert result["run_id"]
    assert result["strategy_model_id"] == "fixture_candle_wick_strategy"
    assert result["strategy_model_id"] != CANONICAL_STRATEGY_MODEL_ID
