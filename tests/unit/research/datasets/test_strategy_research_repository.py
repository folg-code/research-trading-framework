"""Tests for Strategy Research dataset repository."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.strategy_research import (
    STRATEGY_RESEARCH_SCHEMA_VERSION,
    StrategyResearchDatasetRepository,
    StrategyResearchRunEnvelope,
    StrategyResearchRunManifest,
    StrategyResearchRunRef,
    derive_strategy_run_id,
)
from trading_framework.research.simulation.facts import (
    empty_equity_points_dataframe,
    empty_simulated_trades_dataframe,
)


def _sample_manifest(*, run_id: str) -> StrategyResearchRunManifest:
    return StrategyResearchRunManifest(
        run_id=run_id,
        schema_version=STRATEGY_RESEARCH_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        source_dataset_ref="ES.c.0:ohlcv:1m:csv:fixture@1",
        evaluation_timeframe="1m",
        strategy_model_id="high_vol_higher_low_fixed_exit",
        market_model_id="high_volatility",
        signal_model_id="higher_low_long",
        exit_model_id="fixed_bars",
        risk_model_id="fixed_quantity",
        simulation_assumptions_fingerprint="1aa6ee647c5cc636",
    )


def _sample_envelope(*, run_id: str) -> StrategyResearchRunEnvelope:
    return StrategyResearchRunEnvelope(
        manifest=_sample_manifest(run_id=run_id),
        trades=empty_simulated_trades_dataframe(),
        equity=empty_equity_points_dataframe(),
    )


def test_derive_strategy_run_id_is_stable() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)
    first = derive_strategy_run_id(
        strategy_model_id="strategy_a",
        market_model_id="market_a",
        signal_model_id="signal_a",
        exit_model_id="fixed_bars",
        exit_model_parameters="10",
        risk_model_id="fixed_quantity",
        position_quantity="1",
        source_dataset_ref="dataset@1",
        evaluation_timeframe="1m",
        requested_range_start=start,
        requested_range_end=end,
        framework_version=framework_version,
        simulation_assumptions_fingerprint="1aa6ee647c5cc636",
    )
    second = derive_strategy_run_id(
        strategy_model_id="strategy_a",
        market_model_id="market_a",
        signal_model_id="signal_a",
        exit_model_id="fixed_bars",
        exit_model_parameters="10",
        risk_model_id="fixed_quantity",
        position_quantity="1",
        source_dataset_ref="dataset@1",
        evaluation_timeframe="1m",
        requested_range_start=start,
        requested_range_end=end,
        framework_version=framework_version,
        simulation_assumptions_fingerprint="1aa6ee647c5cc636",
    )
    assert first == second


def test_derive_strategy_run_id_fixed_bars_payload_is_byte_identical() -> None:
    """Sprint 048 Correction 2 / D-S048-06 — the sprint's highest-risk item.

    ``exit_after_bars: int`` was generalized to ``exit_model_parameters: str``,
    but for ``FixedBarsExitModel`` the caller MUST still pass exactly
    ``str(exit_after_bars)``, so the hashed payload -- and therefore every
    existing persisted ``run_id`` -- is unchanged. This test reconstructs the
    pre-generalization payload independently of ``derive_strategy_run_id``'s
    internals and asserts the hash matches, proving the emitted payload
    substring is unchanged, not merely "some run_id that happens to match".
    """
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)
    exit_after_bars = 10
    common = {
        "strategy_model_id": "strategy_a",
        "market_model_id": "market_a",
        "signal_model_id": "signal_a",
        "exit_model_id": "fixed_bars",
        "risk_model_id": "fixed_quantity",
        "position_quantity": "1",
        "source_dataset_ref": "dataset@1",
        "evaluation_timeframe": "1m",
        "framework_version": framework_version,
        "simulation_assumptions_fingerprint": "1aa6ee647c5cc636",
    }

    actual = derive_strategy_run_id(
        exit_model_parameters=str(exit_after_bars),
        requested_range_start=start,
        requested_range_end=end,
        **common,
    )

    # The exact "|".join(...) shape derive_strategy_run_id hashed BEFORE this
    # sprint's generalization, with exit_after_bars hashed directly.
    expected_payload = "|".join(
        [
            "strategy_research",
            common["strategy_model_id"],
            common["market_model_id"],
            common["signal_model_id"],
            common["exit_model_id"],
            str(exit_after_bars),
            common["risk_model_id"],
            common["position_quantity"],
            common["source_dataset_ref"],
            common["evaluation_timeframe"],
            start.isoformat(),
            end.isoformat(),
            common["framework_version"],
            common["simulation_assumptions_fingerprint"],
        ]
    )
    expected = hashlib.sha256(expected_payload.encode()).hexdigest()[:16]
    assert actual == expected


def test_derive_strategy_run_id_does_not_collide_across_exit_models() -> None:
    """D-S048-06: two different exit models must never collide on one run_id.

    A test double proves the collision-safety property for the generalized
    ``exit_model_parameters: str`` signature without needing
    ``BracketExitModel`` to exist yet. ``FixedBarsExitModel`` encodes its one
    field as a bare digit string (``str(exit_after_bars)``); a naive,
    delimiter-free encoding of a second exit model's parameters could
    otherwise coincide by accident (e.g. fields ``1`` and ``10`` concatenated
    produce ``"110"``, identical to a FixedBars ``exit_after_bars=110``).
    """
    common: dict[str, Any] = {
        "strategy_model_id": "strategy_a",
        "market_model_id": "market_a",
        "signal_model_id": "signal_a",
        "risk_model_id": "fixed_quantity",
        "position_quantity": "1",
        "source_dataset_ref": "dataset@1",
        "evaluation_timeframe": "1m",
        "requested_range_start": datetime(2024, 1, 1, tzinfo=UTC),
        "requested_range_end": datetime(2024, 1, 2, tzinfo=UTC),
        "framework_version": framework_version,
        "simulation_assumptions_fingerprint": "1aa6ee647c5cc636",
    }

    fixed_bars_run_id = derive_strategy_run_id(
        exit_model_id="fixed_bars",
        exit_model_parameters="110",
        **common,
    )
    # A hypothetical second exit model ("bracket_like") whose two parameters,
    # naively concatenated without a delimiter, would collide with the
    # FixedBars digit string above -- but a well-formed encoding names its
    # fields, and its exit_model_id differs, so the payload (and the derived
    # run_id) must still differ.
    bracket_like_run_id = derive_strategy_run_id(
        exit_model_id="bracket_like",
        exit_model_parameters="field_a=1|field_b=10",
        **common,
    )
    assert fixed_bars_run_id != bracket_like_run_id

    # Different parameter values for the SAME exit_model_id must also not
    # collide with each other.
    bracket_like_run_id_other_params = derive_strategy_run_id(
        exit_model_id="bracket_like",
        exit_model_parameters="field_a=11|field_b=0",
        **common,
    )
    assert bracket_like_run_id != bracket_like_run_id_other_params


def test_strategy_research_repository_round_trip(tmp_path: Path) -> None:
    repository = StrategyResearchDatasetRepository(tmp_path)
    run_id = "abc123strategyrun"
    envelope = _sample_envelope(run_id=run_id)

    written = repository.write(envelope)
    loaded = repository.read(written)

    assert loaded.manifest.run_id == run_id
    assert loaded.trades.equals(envelope.trades)
    assert loaded.equity.equals(envelope.equity)


def test_strategy_research_repository_refuses_overwrite(tmp_path: Path) -> None:
    repository = StrategyResearchDatasetRepository(tmp_path)
    run_id = "duplicate-run"
    repository.write(_sample_envelope(run_id=run_id))

    with pytest.raises(FileExistsError):
        repository.write(_sample_envelope(run_id=run_id))


def test_strategy_research_repository_read_validates_manifest(tmp_path: Path) -> None:
    run_id = "broken-manifest"
    run_dir = tmp_path / "research" / "strategy_research" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "schema_version": "strategy_research.v0",
                "framework_version": framework_version,
                "created_at_utc": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
                "source_dataset_ref": "dataset@1",
                "evaluation_timeframe": "1m",
                "strategy_model_id": "s",
                "market_model_id": "m",
                "signal_model_id": "sig",
                "exit_model_id": "fixed_bars",
                "risk_model_id": "fixed_quantity",
                "simulation_assumptions_fingerprint": "abc",
            }
        ),
        encoding="utf-8",
    )
    empty_simulated_trades_dataframe().write_parquet(run_dir / "trades.parquet")
    empty_equity_points_dataframe().write_parquet(run_dir / "equity.parquet")

    repository = StrategyResearchDatasetRepository(tmp_path)
    with pytest.raises(ValidationError, match="unsupported schema version"):
        repository.read(StrategyResearchRunRef(run_id=run_id))
