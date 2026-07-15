"""Tests for Binance futures reconnect backoff policy."""

from datetime import timedelta
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance import (
    DEFAULT_RECONNECT_BACKOFF_POLICY,
    ReconnectBackoffPolicy,
)


def test_default_reconnect_backoff_policy_is_bounded() -> None:
    assert DEFAULT_RECONNECT_BACKOFF_POLICY.delay_for_attempt(0) == timedelta(seconds=1)
    assert DEFAULT_RECONNECT_BACKOFF_POLICY.delay_for_attempt(1) == timedelta(seconds=2)
    assert DEFAULT_RECONNECT_BACKOFF_POLICY.delay_for_attempt(4) == timedelta(seconds=16)


def test_reconnect_backoff_policy_caps_at_max_delay() -> None:
    policy = ReconnectBackoffPolicy(
        initial_delay=timedelta(seconds=2),
        max_delay=timedelta(seconds=5),
        multiplier=Decimal("3"),
        max_attempts=4,
    )

    assert policy.delay_for_attempt(0) == timedelta(seconds=2)
    assert policy.delay_for_attempt(1) == timedelta(seconds=5)
    assert policy.delay_for_attempt(2) == timedelta(seconds=5)


def test_reconnect_backoff_policy_rejects_invalid_configuration() -> None:
    with pytest.raises(ValidationError, match="initial_delay"):
        ReconnectBackoffPolicy(initial_delay=timedelta(0))

    with pytest.raises(ValidationError, match="max_delay"):
        ReconnectBackoffPolicy(initial_delay=timedelta(seconds=5), max_delay=timedelta(seconds=1))

    with pytest.raises(ValidationError, match="multiplier"):
        ReconnectBackoffPolicy(multiplier=Decimal("0.5"))

    with pytest.raises(ValidationError, match="max_attempts"):
        ReconnectBackoffPolicy(max_attempts=0)


def test_reconnect_backoff_policy_rejects_invalid_attempt_index() -> None:
    policy = ReconnectBackoffPolicy(max_attempts=2)

    with pytest.raises(ValidationError, match="attempt_index"):
        policy.delay_for_attempt(-1)

    with pytest.raises(ValidationError, match="max_attempts"):
        policy.delay_for_attempt(2)
