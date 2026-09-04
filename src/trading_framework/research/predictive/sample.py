"""Sample universe and research-task declaration for Predictive Research (ADR-0031).

Pure data types only. This module must gain no import of ``signal_model``,
``strategy``, or ``application`` (ADR-0023, this package's own ``CLAUDE.md``,
enforced by ``tests/unit/test_architecture_boundaries.py``). ``SampleSpec`` and
``PredictiveTask`` DECLARE the sample universe and research intent;
``application/predictive_research/`` RESOLVES a declared ``signal_occurrences``
sample into real rows (ADR-0031 Decision 3, D-S056-04). Resolution — calling
``evaluate_models`` / ``materialize_signal_occurrences`` — is out of scope here
(S056-T004).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, assert_never

from trading_framework.research.predictive.errors import (
    IncompatibleSampleTaskError,
    PredictiveSpecError,
    ReservedPredictiveTaskError,
    ReservedSampleKindError,
)


class SampleKind(StrEnum):
    """Which rows a predictive study's dataset is about (ADR-0031 §1).

    Only two kinds are SHIPPED. ``strategy_trades``, ``labelled_setups`` and
    ``sessions_or_windows`` are reserved names, refused at load time by
    :func:`parse_sample_kind` — they are deliberately not members of this
    enum, so a reserved value can never be represented in memory.
    """

    EVERY_BAR = "every_bar"
    SIGNAL_OCCURRENCES = "signal_occurrences"


class SampleDirection(StrEnum):
    """Occurrence direction filter for a ``signal_occurrences`` sample."""

    ANY = "ANY"
    LONG = "LONG"
    SHORT = "SHORT"


class PredictiveTask(StrEnum):
    """Research intent for a predictive study, distinct from ``LabelKind``.

    Only two tasks are SHIPPED. The reserved names in
    ``_RESERVED_PREDICTIVE_TASK_OWNERS`` are deliberately not members of this
    enum, so a reserved value can never be represented in memory.
    """

    FORWARD_RETURN = "FORWARD_RETURN"
    SIGNAL_QUALITY = "SIGNAL_QUALITY"


# Reserved sample kinds (ADR-0031 §1, D-S056-04): declared in the contract's
# design intent, refused at load time, never accepted as enum members.
_RESERVED_SAMPLE_KIND_OWNERS: dict[str, str] = {
    "strategy_trades": "16F",
    "labelled_setups": "16F",
    "sessions_or_windows": "later, unassigned",
}

# Reserved predictive tasks (ADR-0031 §5, D-S056-09).
_RESERVED_PREDICTIVE_TASK_OWNERS: dict[str, str] = {
    "TRADE_OUTCOME": "16F",
    "NO_TRADE_FILTER": "16F",
    "REGIME_CLASSIFICATION": "later, unassigned",
    "VOLATILITY_FORECAST": "later, unassigned",
    "DISCRETIONARY_SETUP_CLASSIFICATION": "later, unassigned",
}

# Sample-kind x task compatibility matrix (ADR-0031 §5, D-S056-09). Anything
# not listed here is refused with IncompatibleSampleTaskError.
_COMPATIBLE_SAMPLE_TASK_PAIRS: frozenset[tuple[SampleKind, PredictiveTask]] = frozenset(
    {
        (SampleKind.EVERY_BAR, PredictiveTask.FORWARD_RETURN),
        (SampleKind.SIGNAL_OCCURRENCES, PredictiveTask.FORWARD_RETURN),
        (SampleKind.SIGNAL_OCCURRENCES, PredictiveTask.SIGNAL_QUALITY),
    }
)


def parse_sample_kind(raw: str) -> SampleKind:
    """Parse a sample-kind string, refusing reserved names with a named error."""
    owner = _RESERVED_SAMPLE_KIND_OWNERS.get(raw)
    if owner is not None:
        msg = f"sample kind {raw!r} is reserved and not implemented (owned by {owner})"
        raise ReservedSampleKindError(msg)
    try:
        return SampleKind(raw)
    except ValueError as exc:
        msg = f"unknown sample kind: {raw!r}"
        raise PredictiveSpecError(msg) from exc


def parse_predictive_task(raw: str) -> PredictiveTask:
    """Parse a ``PredictiveTask`` string, refusing reserved names with a named error."""
    owner = _RESERVED_PREDICTIVE_TASK_OWNERS.get(raw)
    if owner is not None:
        msg = f"predictive task {raw!r} is reserved and not implemented (owned by {owner})"
        raise ReservedPredictiveTaskError(msg)
    try:
        return PredictiveTask(raw)
    except ValueError as exc:
        msg = f"unknown predictive task: {raw!r}"
        raise PredictiveSpecError(msg) from exc


def validate_sample_task_compatibility(sample: SampleSpec, task: PredictiveTask) -> None:
    """Refuse a sample-kind x task pairing outside ADR-0031 §5's matrix."""
    if (sample.kind, task) not in _COMPATIBLE_SAMPLE_TASK_PAIRS:
        msg = f"sample kind {sample.kind.value!r} is not compatible with task {task.value!r}"
        raise IncompatibleSampleTaskError(msg)


@dataclass(frozen=True, slots=True)
class SampleSpec:
    """Declared sample universe for a ``PredictiveStudySpec`` (ADR-0031 §1).

    ``every_bar`` is the default: one row per complete evaluation bar, today's
    behaviour made explicit. ``signal_occurrences`` references a Signal Model
    by declaration only (``signal_model_file`` + ``signal_model_id``), never by
    a run id or a persisted occurrence artifact (ADR-0024 condition 5). This
    type never resolves rows; it is a pure declaration.
    """

    kind: SampleKind
    signal_model_file: str | None = None
    signal_model_id: str | None = None
    direction: SampleDirection = SampleDirection.ANY

    def __post_init__(self) -> None:
        if self.kind is SampleKind.EVERY_BAR:
            if self.signal_model_file is not None or self.signal_model_id is not None:
                msg = "every_bar sample must not declare signal_model_file or signal_model_id"
                raise PredictiveSpecError(msg)
            if self.direction is not SampleDirection.ANY:
                msg = "every_bar sample must not declare a direction filter"
                raise PredictiveSpecError(msg)
            return
        if self.kind is SampleKind.SIGNAL_OCCURRENCES:
            if not self.signal_model_file:
                msg = "signal_occurrences sample requires signal_model_file"
                raise PredictiveSpecError(msg)
            if not self.signal_model_id:
                msg = "signal_occurrences sample requires signal_model_id"
                raise PredictiveSpecError(msg)
            return
        assert_never(self.kind)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind.value}
        if self.kind is SampleKind.SIGNAL_OCCURRENCES:
            payload["signal_model_file"] = self.signal_model_file
            payload["signal_model_id"] = self.signal_model_id
            if self.direction is not SampleDirection.ANY:
                payload["direction"] = self.direction.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SampleSpec:
        raw_kind = str(payload.get("kind", SampleKind.EVERY_BAR.value))
        kind = parse_sample_kind(raw_kind)
        raw_direction = str(payload.get("direction", SampleDirection.ANY.value))
        try:
            direction = SampleDirection(raw_direction)
        except ValueError as exc:
            msg = f"invalid sample direction: {raw_direction!r}"
            raise PredictiveSpecError(msg) from exc
        signal_model_file = payload.get("signal_model_file")
        signal_model_id = payload.get("signal_model_id")
        return cls(
            kind=kind,
            signal_model_file=str(signal_model_file) if signal_model_file is not None else None,
            signal_model_id=str(signal_model_id) if signal_model_id is not None else None,
            direction=direction,
        )


DEFAULT_SAMPLE_SPEC = SampleSpec(kind=SampleKind.EVERY_BAR)
