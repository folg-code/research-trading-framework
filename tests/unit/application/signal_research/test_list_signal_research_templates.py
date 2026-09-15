"""Tests for the application-layer template listing/apply wrapper (Sprint 064 T008).

Thin-wrapper coverage only: the research-layer catalog (collision rule,
malformed-file handling, model-alias resolution) already has its own tests
under tests/unit/research/signal_research/test_template_catalog.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from trading_framework.application.signal_research import (
    ApplySignalResearchTemplateRequest,
    SignalResearchTemplateNotFoundError,
    TemplateSource,
    TemplateStatus,
    apply_signal_research_template,
    list_signal_research_templates,
)

_FRAMEWORK_TEMPLATE_IDS = {
    "minimal-single-signal",
    "multi-horizon-baseline",
    "quality-rules-strict",
}

_OVERRIDES = {
    "research_id": "test_study",
    "dataset_ref": "ES.c.0|ohlcv|1m|csv|test@1",
    "time_range": {"start": "2024-01-01", "end": "2024-01-02"},
}


def test_list_returns_narrower_summary_with_no_path() -> None:
    summaries = list_signal_research_templates()

    ids = {summary.template_id for summary in summaries}
    assert ids == _FRAMEWORK_TEMPLATE_IDS
    for summary in summaries:
        assert not hasattr(summary, "path")
        assert summary.source is TemplateSource.FRAMEWORK
        assert summary.status is TemplateStatus.SUPPORTED


def test_apply_supported_template_merges_overrides() -> None:
    definition = apply_signal_research_template(
        ApplySignalResearchTemplateRequest(
            template_id="minimal-single-signal", overrides=_OVERRIDES
        )
    )

    assert definition["research_id"] == "test_study"
    assert definition["dataset_ref"] == "ES.c.0|ohlcv|1m|csv|test@1"


def test_apply_unknown_template_id_raises_not_found() -> None:
    with pytest.raises(SignalResearchTemplateNotFoundError):
        apply_signal_research_template(
            ApplySignalResearchTemplateRequest(template_id="does-not-exist", overrides={})
        )


def test_apply_shadowed_template_raises_with_reason(tmp_path: Path) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()
    (user_root / "colliding.yaml").write_text(
        "template_id: minimal-single-signal\n"
        "template_version: 1\n"
        "title: Colliding\n"
        "description: Same id as a framework template.\n"
        "definition:\n"
        "  research_id: placeholder\n",
        encoding="utf-8",
    )

    summaries = list_signal_research_templates(user_root)
    colliding = [
        summary
        for summary in summaries
        if summary.template_id == "minimal-single-signal" and summary.source is TemplateSource.USER
    ]
    assert len(colliding) == 1
    assert colliding[0].status is TemplateStatus.SHADOWED

    # The framework copy is still the one actually applied by template_id --
    # the collision never silently applies the shadowed user copy instead.
    definition = apply_signal_research_template(
        ApplySignalResearchTemplateRequest(
            template_id="minimal-single-signal", overrides=_OVERRIDES
        ),
        user_templates_root=user_root,
    )
    assert definition["research_id"] == "test_study"
