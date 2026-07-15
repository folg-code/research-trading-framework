"""Unit tests for Monte Carlo contracts."""

from __future__ import annotations

from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.robustness.monte_carlo import (
    MonteCarloMethod,
    MonteCarloSpec,
)


def test_monte_carlo_spec_roundtrip_dict() -> None:
    spec = MonteCarloSpec(
        methods=(MonteCarloMethod.TRADE_SHUFFLE, MonteCarloMethod.TRADE_BOOTSTRAP),
        path_count=100,
        rng_seed=99,
        max_drawdown_threshold=Decimal("-1000"),
    )
    restored = MonteCarloSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_monte_carlo_spec_rejects_non_positive_path_count() -> None:
    with pytest.raises(ValidationError, match="path_count must be positive"):
        MonteCarloSpec(path_count=0)
