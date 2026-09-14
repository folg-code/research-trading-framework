"""Unit tests for Signal Research templates (Sprint 064 T003, ADR-0038 section 4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trading_framework.research.signal_research.definition import SignalResearchDefinitionSpec
from trading_framework.research.signal_research.template_catalog import (
    TemplateApplicationError,
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


def test_lists_all_three_framework_templates_with_no_user_root() -> None:
    summaries = list_signal_research_templates()

    ids = {summary.template_id for summary in summaries}
    assert ids == _FRAMEWORK_TEMPLATE_IDS
    for summary in summaries:
        assert summary.source is TemplateSource.FRAMEWORK
        assert summary.status is TemplateStatus.SUPPORTED
        assert summary.template_version == 1
        assert summary.unresolvable_model_aliases == ()


def test_lists_all_three_framework_templates_with_empty_user_root(tmp_path: Path) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()

    summaries = list_signal_research_templates(user_root)

    ids = {summary.template_id for summary in summaries}
    assert ids == _FRAMEWORK_TEMPLATE_IDS


def test_user_template_without_collision_is_supported(tmp_path: Path) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()
    (user_root / "my_template.yaml").write_text(
        "template_id: my-custom-template\n"
        "template_version: 1\n"
        "title: My Custom Template\n"
        "description: A user-authored template.\n"
        "definition:\n"
        "  research_scope: SIGNAL_MODEL_ONLY\n"
        "  signal_model: higher_low_long\n"
        "  baseline:\n"
        "    type: AFTER_SIGNAL\n"
        "  horizons:\n"
        "    - 5m\n",
        encoding="utf-8",
    )

    summaries = list_signal_research_templates(user_root)

    user_summaries = [s for s in summaries if s.source is TemplateSource.USER]
    assert len(user_summaries) == 1
    assert user_summaries[0].template_id == "my-custom-template"
    assert user_summaries[0].status is TemplateStatus.SUPPORTED


def test_user_template_collision_is_shadowed_not_hidden(tmp_path: Path) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()
    (user_root / "colliding.yaml").write_text(
        "template_id: minimal-single-signal\n"
        "template_version: 1\n"
        "title: A stale local copy\n"
        "description: Should never silently win or silently disappear.\n"
        "definition:\n"
        "  research_scope: SIGNAL_MODEL_ONLY\n"
        "  signal_model: higher_low_long\n"
        "  baseline:\n"
        "    type: AFTER_SIGNAL\n"
        "  horizons:\n"
        "    - 5m\n",
        encoding="utf-8",
    )

    summaries = list_signal_research_templates(user_root)

    framework_entry = next(
        s
        for s in summaries
        if s.template_id == "minimal-single-signal" and s.source is TemplateSource.FRAMEWORK
    )
    user_entry = next(
        s
        for s in summaries
        if s.template_id == "minimal-single-signal" and s.source is TemplateSource.USER
    )
    assert framework_entry.status is TemplateStatus.SUPPORTED
    assert user_entry.status is TemplateStatus.SHADOWED
    assert user_entry.reason is not None
    assert "minimal-single-signal" in user_entry.reason


def test_shadowed_user_template_cannot_be_applied(tmp_path: Path) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()
    (user_root / "colliding.yaml").write_text(
        "template_id: minimal-single-signal\n"
        "template_version: 1\n"
        "title: A stale local copy\n"
        "description: desc\n"
        "definition:\n"
        "  research_scope: SIGNAL_MODEL_ONLY\n"
        "  signal_model: higher_low_long\n"
        "  baseline:\n"
        "    type: AFTER_SIGNAL\n"
        "  horizons:\n"
        "    - 5m\n",
        encoding="utf-8",
    )
    summaries = list_signal_research_templates(user_root)
    shadowed = next(
        s
        for s in summaries
        if s.template_id == "minimal-single-signal" and s.source is TemplateSource.USER
    )

    with pytest.raises(TemplateApplicationError, match="SHADOWED"):
        apply_signal_research_template(shadowed, overrides=_OVERRIDES)


def test_malformed_user_template_is_unsupported_and_does_not_break_listing(
    tmp_path: Path,
) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()
    (user_root / "broken.yaml").write_text("{not: valid: yaml::", encoding="utf-8")
    (user_root / "missing_keys.yaml").write_text(
        "template_id: incomplete\ntitle: Incomplete\n", encoding="utf-8"
    )

    summaries = list_signal_research_templates(user_root)

    framework_ids = {s.template_id for s in summaries if s.source is TemplateSource.FRAMEWORK}
    assert framework_ids == _FRAMEWORK_TEMPLATE_IDS

    broken = next(s for s in summaries if s.path.name == "broken.yaml")
    assert broken.status is TemplateStatus.UNSUPPORTED
    assert broken.reason is not None

    incomplete = next(s for s in summaries if s.path.name == "missing_keys.yaml")
    assert incomplete.status is TemplateStatus.UNSUPPORTED
    assert incomplete.template_id == "incomplete"
    assert incomplete.reason is not None
    assert "template_version" in incomplete.reason


def test_unsupported_template_cannot_be_applied(tmp_path: Path) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()
    (user_root / "broken.yaml").write_text("{not: valid: yaml::", encoding="utf-8")
    summaries = list_signal_research_templates(user_root)
    broken = next(s for s in summaries if s.path.name == "broken.yaml")

    with pytest.raises(TemplateApplicationError, match="UNSUPPORTED"):
        apply_signal_research_template(broken, overrides=_OVERRIDES)


def test_template_referencing_unknown_model_alias_is_flagged_not_hidden(
    tmp_path: Path,
) -> None:
    user_root = tmp_path / "templates"
    user_root.mkdir()
    (user_root / "bad_alias.yaml").write_text(
        "template_id: unknown-alias-template\n"
        "template_version: 1\n"
        "title: Unknown Alias\n"
        "description: desc\n"
        "definition:\n"
        "  research_scope: SIGNAL_MODEL_ONLY\n"
        "  signal_model: this_alias_does_not_exist\n"
        "  baseline:\n"
        "    type: AFTER_SIGNAL\n"
        "  horizons:\n"
        "    - 5m\n",
        encoding="utf-8",
    )

    summaries = list_signal_research_templates(user_root)

    entry = next(s for s in summaries if s.template_id == "unknown-alias-template")
    assert entry.status is TemplateStatus.SUPPORTED
    assert entry.unresolvable_model_aliases == ("this_alias_does_not_exist",)


@pytest.mark.parametrize("template_id", sorted(_FRAMEWORK_TEMPLATE_IDS))
def test_applied_framework_template_validates(template_id: str) -> None:
    summaries = {s.template_id: s for s in list_signal_research_templates()}

    payload = apply_signal_research_template(summaries[template_id], overrides=_OVERRIDES)
    spec = SignalResearchDefinitionSpec.from_dict(payload)

    assert spec.research_id == "test_study"
    assert spec.horizons


def test_apply_does_not_mutate_template_file_on_disk(tmp_path: Path) -> None:
    """Applying a template must never edit the template itself (D-S064-06: templates
    are never edited in place across a version)."""
    summaries = list_signal_research_templates()
    template = next(s for s in summaries if s.template_id == "minimal-single-signal")
    before = template.path.read_text(encoding="utf-8")

    apply_signal_research_template(template, overrides=_OVERRIDES)

    after = template.path.read_text(encoding="utf-8")
    assert before == after
