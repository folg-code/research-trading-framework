"""Sprint 048 golden-run regression test (S048-T001 / D-S048-07).

Binding acceptance criterion for Sprint 048's engine changes: the canonical
Sprint 013 strategy (``build_canonical_strategy_model()``), run on the
committed OHLCV fixture through ``run_strategy_research``, must produce a
byte-identical/value-identical trades DataFrame, equity DataFrame,
``manifest.run_id``, and the listed deterministic manifest fields, before and
after every task in this sprint.

The fixture under ``tests/fixtures/research/golden_run/`` was captured on the
UNMODIFIED tree (before any Sprint 048 engine change existed), using the
one-off generator reproduced in this file's module docstring below — never
pasted by hand. Per D-S048-07, if any assertion in this test ever drifts, THE
CHANGE IS WRONG, not this fixture: adjusting the fixture to match new output
is forbidden without a recorded maintainer decision in
``S048_WAVE0_DECISIONS.md``.

Reproduction (only ever run on a tree with zero Sprint 048 engine changes)::

    Same dataset-publish + run_strategy_research call as
    ``_write_published_dataset`` / ``test_golden_run_matches_captured_fixture``
    below, with ``persist=False``, writing:
        run_result.trades.write_parquet(FIXTURE_DIR / "trades.parquet")
        run_result.equity.write_parquet(FIXTURE_DIR / "equity.parquet")
        (FIXTURE_DIR / "manifest.json") <- the ten manifest fields below,
            via json.dumps(..., indent=2, sort_keys=True).
    using DatasetId(instrument_id=Identifier("ES.c.0"), data_type="ohlcv",
    timeframe=Timeframe("1m"), provider="csv",
    source_id="s048-golden-run") against
    tests/fixtures/market_data/ohlcv_sample_1m.csv.
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import polars as pl

from trading_framework.application.market_data import (
    ImportExternalDatasetRequest,
    finalize_dataset,
    import_external_dataset,
    publish_dataset,
)
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.market_analysis import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import build_canonical_strategy_model
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "research" / "golden_run"

# Must exactly match the identity used to capture the committed fixture —
# it feeds source_dataset_ref, which feeds manifest.run_id.
_GOLDEN_RUN_SOURCE_ID = "s048-golden-run"

# D-S048-07: these manifest fields are asserted byte-for-byte against the
# committed fixture. `created_at_utc` and `framework_version` are excluded
# below (never listed here) because they are legitimately nondeterministic:
# `created_at_utc` is `datetime.now(UTC)` at run time, and `framework_version`
# tracks the installed package version, not the strategy/engine behaviour
# under test.
_MANIFEST_FIELDS = (
    "run_id",
    "exit_model_id",
    "risk_model_id",
    "strategy_model_id",
    "market_model_id",
    "signal_model_id",
    "evaluation_timeframe",
    "source_dataset_ref",
    "schema_version",
    "simulation_assumptions_fingerprint",
)


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> DatasetRef:
    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id=_GOLDEN_RUN_SOURCE_ID,
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
    return result.dataset_ref


def test_golden_run_matches_captured_fixture(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    """The canonical Sprint 013 strategy must reproduce the committed golden run."""
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()

    result = run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            strategy_model=strategy_model,
            assumptions=SimulationAssumptions(),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            persist=False,
        )
    )

    expected_trades = pl.read_parquet(_FIXTURE_DIR / "trades.parquet")
    expected_equity = pl.read_parquet(_FIXTURE_DIR / "equity.parquet")
    expected_manifest = json.loads((_FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert set(expected_manifest) == set(_MANIFEST_FIELDS)

    # IDENTICAL — trades DataFrame, every column, every row, exact values.
    assert result.trades.equals(expected_trades)
    # IDENTICAL — equity DataFrame, every column, every row, exact values.
    assert result.equity.equals(expected_equity)

    manifest = result.manifest
    actual_manifest = {field: getattr(manifest, field) for field in _MANIFEST_FIELDS}
    assert actual_manifest == expected_manifest

    # manifest.run_id is asserted twice on purpose: once via `_MANIFEST_FIELDS`
    # above, once explicitly, because D-S048-06 names it the highest-risk field
    # (derive_strategy_run_id's payload change must never re-identify existing
    # persisted runs).
    assert manifest.run_id == expected_manifest["run_id"]
