"""Predictive score condition: a promoted-artifact scorer reference.

Sprint 058 T003 (Phase 16 increment 16C), ADR-0033 (predictive score
delivery boundary, ACCEPTED). A ``ScoreConditionSpec`` is a pure
declaration -- it names a promoted artifact by its content-addressed
``artifact_fingerprint`` and a decision ``threshold``, nothing more. It
never resolves anything itself: no filesystem access, no index, no
``latest`` pointer (ADR-0024 condition 5, unchanged).

Resolution -- confirming the fingerprint exists and names a promotable
model family -- is a separate, application-layer step
(``application/strategy_research/resolve_score_condition.py``), performed
once at config load time, never inside the simulation loop. Evaluating the
score itself (loading feature values, calling the pure-NumPy evaluator
under ``available_at``) is a later task (Sprint 058 T004); this module
declares the reference only.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError


class ScoreConditionError(ValidationError):
    """Raised when a ``ScoreConditionSpec`` is declared with an invalid shape."""


@dataclass(frozen=True, slots=True)
class ScoreConditionSpec:
    """Declares a predictive-score gate by promoted-artifact fingerprint only.

    ``artifact_fingerprint`` is the same identity ``PromotedArtifactRef``
    already defines (ADR-0029 §2) -- no alias, no run id, no index. A
    strategy carrying this condition asserts nothing about the referenced
    artifact until it is resolved (``resolve_score_condition``); this type
    cannot be constructed with an artifact that does not exist, because it
    never looks.
    """

    artifact_fingerprint: str
    threshold: float

    def __post_init__(self) -> None:
        normalized = self.artifact_fingerprint.strip()
        if not normalized:
            msg = "score condition requires a non-empty artifact_fingerprint"
            raise ScoreConditionError(msg)
        if normalized != self.artifact_fingerprint:
            object.__setattr__(self, "artifact_fingerprint", normalized)
