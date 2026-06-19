"""Dataset lifecycle state and transitions."""

from enum import StrEnum

from trading_framework.core.exceptions import ValidationError


class DatasetLifecycleState(StrEnum):
    """Dataset lifecycle states for MVP workflows."""

    WORKING = "working"
    FINALIZED = "finalized"
    PUBLISHED = "published"
    INVALID = "invalid"
    SUPERSEDED = "superseded"


_LEGAL_TRANSITIONS: dict[DatasetLifecycleState, frozenset[DatasetLifecycleState]] = {
    DatasetLifecycleState.WORKING: frozenset(
        {DatasetLifecycleState.FINALIZED, DatasetLifecycleState.INVALID}
    ),
    DatasetLifecycleState.FINALIZED: frozenset(
        {DatasetLifecycleState.PUBLISHED, DatasetLifecycleState.INVALID}
    ),
    DatasetLifecycleState.PUBLISHED: frozenset({DatasetLifecycleState.SUPERSEDED}),
    DatasetLifecycleState.INVALID: frozenset(),
    DatasetLifecycleState.SUPERSEDED: frozenset(),
}


def transition_dataset_lifecycle(
    current: DatasetLifecycleState,
    target: DatasetLifecycleState,
) -> DatasetLifecycleState:
    """Return ``target`` when the lifecycle transition is legal."""
    if current is target:
        return target
    allowed = _LEGAL_TRANSITIONS[current]
    if target not in allowed:
        msg = f"illegal dataset lifecycle transition: {current.value} -> {target.value}"
        raise ValidationError(msg)
    return target


def assert_published_is_immutable(current: DatasetLifecycleState) -> None:
    """Reject mutations when a dataset version is already published."""
    if current is DatasetLifecycleState.PUBLISHED:
        msg = "published dataset versions are immutable"
        raise ValidationError(msg)
