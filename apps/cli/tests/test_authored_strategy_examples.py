"""End-to-end metric tests for operator-authored strategy examples.

Proves, against real CLI runs over a committed fixture dataset, the PRD
success metrics that Sprints 047 and 048 deliver:

1. the run manifest's ``strategy_model_id`` is the *loaded* strategy's, not
   the Sprint 013 canonical example's (PRD success metric 1, Sprint 047) --
   this fails loudly if the loader ever silently falls back to the
   canonical example;
2. the loaded strategy's Market Model actually composes one of the two new
   catalog components, ``candle.wick`` (PRD success metric 2, component
   half, Sprint 047 -- the Exit/Risk half was deferred with Wave 2 there,
   ADR-0028 declined for that sprint);
3. a bracket strategy loaded through ``strategy_file`` produces a run whose
   trades table contains more than one distinct ``exit_reason``, and whose
   manifest carries ``exit_model_id == "bracket"`` (PRD success metric 1,
   Sprint 048 -- S048-T012). This fails if the run silently falls back to a
   fixed-bars path, or if only one exit reason ever appears.
4. the rule-based half of PRD success metric 1 for Sprint 051 (S051-T009):
   a strategy loaded through the unmodified ``strategy_file`` loader
   composes at least two of Sprint 051's six new components
   (``momentum.rsi`` gated by ``volatility.relative_volatility``), the run's
   ``strategy_model_id`` is the loaded strategy's, and -- the acceptance
   criterion that distinguishes this from "the run merely succeeded" -- both
   new components genuinely appear in the run's analysis lineage
   (``AnalysisResult.computation_identity`` for every component the
   evaluation actually computed), not just in the loaded expression tree.

No network. No ML/DL extra. Committed fixture data only
(``tests/fixtures/market_data/ohlcv_sample_1m.csv`` via ``ohlcv_sample_1m_path``).
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest
from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.model_expression.expressions import (
    AndExpression,
    BinaryCompareExpression,
    CompareExpression,
    Expression,
    NotExpression,
    OrExpression,
)
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
)
from trading_framework.strategy import CANONICAL_STRATEGY_MODEL_ID
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

from trading_cli.cli import main
from trading_cli.errors import EXIT_SUCCESS
from trading_cli.strategy_loader import load_strategy_definition

_FIXTURE_STRATEGY = (
    Path(__file__).parent / "fixtures" / "strategies" / "uses_candle_wick.py"
).resolve()

_BRACKET_FIXTURE_STRATEGY = (
    Path(__file__).parent / "fixtures" / "strategies" / "uses_bracket_exit.py"
).resolve()

_RSI_RELATIVE_VOLATILITY_FIXTURE_STRATEGY = (
    Path(__file__).parent / "fixtures" / "strategies" / "uses_rsi_relative_volatility.py"
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


def test_research_run_bracket_strategy_produces_multiple_exit_reasons(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """PRD success metric 1 (Sprint 048, S048-T012): a ``BracketExitModel``
    strategy loaded through ``strategy_file`` produces a run whose trades
    table contains more than one distinct ``exit_reason``, and whose
    manifest carries ``exit_model_id == "bracket"``.

    Fails if the run silently falls back to a fixed-bars path (only
    ``exit_model_id == "fixed_bars"`` and a single ``fixed_bars`` reason
    would ever appear) or if the bracket kernel only ever times out (only
    one distinct ``exit_reason`` would appear).
    """
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
        f"    strategy_file: {_BRACKET_FIXTURE_STRATEGY.as_posix()}\n",
        encoding="utf-8",
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]
    assert result["run_id"]
    assert result["strategy_model_id"] == "fixture_bracket_exit_strategy"

    repository = StrategyResearchDatasetRepository(storage_root)
    envelope = repository.read(StrategyResearchRunRef(run_id=result["run_id"]))

    assert envelope.manifest.exit_model_id == "bracket"

    distinct_exit_reasons = set(envelope.trades["exit_reason"].to_list())
    assert len(distinct_exit_reasons) > 1, (
        f"expected more than one distinct exit_reason, got {distinct_exit_reasons!r}"
    )
    assert distinct_exit_reasons <= {"stop_loss", "take_profit", "max_bars"}


def test_fixture_strategy_composes_rsi_and_relative_volatility() -> None:
    """PRD success metric 1 (rule-based half, S051-T009): the loaded
    definition really uses both new components -- not just a strategy that
    happens to load. ``momentum.rsi`` gates the Signal Model;
    ``volatility.relative_volatility`` gates the Market Model."""
    loaded = load_strategy_definition(str(_RSI_RELATIVE_VOLATILITY_FIXTURE_STRATEGY))

    market_component_ids = _component_ids(loaded.definition.market_model.expression)
    signal_component_ids = _component_ids(loaded.definition.signal_model.expression)

    assert "volatility.relative_volatility" in market_component_ids
    assert "momentum.rsi" in signal_component_ids


def test_research_run_strategy_file_manifest_uses_rsi_relative_volatility_id(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """PRD success metric 1 (S051-T009): fails if the loader ever silently
    falls back to the canonical example, or to a different fixture."""
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
        f"    strategy_file: {_RSI_RELATIVE_VOLATILITY_FIXTURE_STRATEGY.as_posix()}\n",
        encoding="utf-8",
    )

    exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    result = payload["result"]
    assert result["run_id"]
    assert result["strategy_model_id"] == "fixture_rsi_relative_volatility_strategy"
    assert result["strategy_model_id"] != CANONICAL_STRATEGY_MODEL_ID


def test_rsi_and_relative_volatility_appear_in_run_analysis_lineage(
    tmp_path: Path, ohlcv_sample_1m_path: Path
) -> None:
    """The acceptance criterion that distinguishes this from "the run merely
    succeeded" (S051-T009): both new components genuinely appear in the
    analysis lineage that evaluating the *loaded* strategy's Market and
    Signal Models actually produced -- not merely in the static expression
    tree (the previous test) and not merely a successful CLI exit code.

    Mirrors S051-T003's ``test_authored_rsi_evaluates_on_fixture``
    (``tests/unit/model_authoring/test_momentum_rsi_dsl.py``), one level up:
    the strategy is loaded through the real, unmodified ``strategy_file``
    loader (``load_strategy_definition``) first, and *that* loaded
    definition's Market/Signal Models are what gets evaluated here -- the
    same evaluation ``run_strategy_research`` performs internally for a full
    CLI run (``application/strategy_research/run_strategy_research.py``,
    ``_resolve_evaluation_inputs``).
    """
    storage_root = tmp_path / "storage"
    dataset_ref = DatasetRef.parse(
        _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    )
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)

    loaded = load_strategy_definition(str(_RSI_RELATIVE_VOLATILITY_FIXTURE_STRATEGY))

    result = evaluate_models(
        EvaluateModelsRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            market_models=(loaded.definition.market_model,),
            signal_models=(loaded.definition.signal_model,),
        )
    )

    assert result.analysis.frame is not None
    computed_component_ids = {
        analysis_result.computation_identity.component_id.value
        for analysis_result in result.analysis.workspace.result_store.results().values()
    }
    assert "momentum.rsi" in computed_component_ids
    assert "volatility.relative_volatility" in computed_component_ids
