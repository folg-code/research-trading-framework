"""Tests for the declared score-condition reference (Sprint 058 T003)."""

from __future__ import annotations

import pytest

from trading_framework.strategy import ScoreConditionError, ScoreConditionSpec


def test_score_condition_spec_accepts_a_well_formed_declaration() -> None:
    spec = ScoreConditionSpec(artifact_fingerprint="a" * 64, threshold=0.6)

    assert spec.artifact_fingerprint == "a" * 64
    assert spec.threshold == 0.6


def test_score_condition_spec_strips_whitespace_from_fingerprint() -> None:
    spec = ScoreConditionSpec(artifact_fingerprint="  " + "a" * 64 + "  ", threshold=0.5)

    assert spec.artifact_fingerprint == "a" * 64


def test_score_condition_spec_rejects_empty_fingerprint() -> None:
    with pytest.raises(ScoreConditionError, match="non-empty artifact_fingerprint"):
        ScoreConditionSpec(artifact_fingerprint="", threshold=0.5)


def test_score_condition_spec_rejects_whitespace_only_fingerprint() -> None:
    with pytest.raises(ScoreConditionError, match="non-empty artifact_fingerprint"):
        ScoreConditionSpec(artifact_fingerprint="   ", threshold=0.5)
