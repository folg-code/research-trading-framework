"""Dataset lifecycle tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import (
    DatasetLifecycleState,
    assert_published_is_immutable,
    transition_dataset_lifecycle,
)


def test_working_to_finalized_is_allowed() -> None:
    result = transition_dataset_lifecycle(
        DatasetLifecycleState.WORKING,
        DatasetLifecycleState.FINALIZED,
    )
    assert result is DatasetLifecycleState.FINALIZED


def test_finalized_to_published_is_allowed() -> None:
    result = transition_dataset_lifecycle(
        DatasetLifecycleState.FINALIZED,
        DatasetLifecycleState.PUBLISHED,
    )
    assert result is DatasetLifecycleState.PUBLISHED


def test_working_to_published_is_rejected() -> None:
    with pytest.raises(ValidationError):
        transition_dataset_lifecycle(
            DatasetLifecycleState.WORKING,
            DatasetLifecycleState.PUBLISHED,
        )


def test_published_versions_are_immutable() -> None:
    with pytest.raises(ValidationError):
        assert_published_is_immutable(DatasetLifecycleState.PUBLISHED)
