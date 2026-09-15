"""Regression guards for the maintained terminology foundation."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_WORKBENCH_COPY = (
    _ROOT / "apps/workbench/ui/app/layout.tsx",
    _ROOT / "apps/workbench/ui/app/page.tsx",
    _ROOT / "apps/workbench/ui/app/new/page.tsx",
)


def test_canonical_terminology_defines_lifecycle_and_compatibility_boundary() -> None:
    terminology = (_ROOT / "docs/reference/system/TERMINOLOGY.md").read_text(encoding="utf-8")

    for term in (
        "Research",
        "Methodology",
        "Workflow",
        "Use case",
        "Pipeline",
        "Definition / Spec",
        "Experiment",
        "Run",
        "Artifact",
        "Portfolio Study",
    ):
        assert f"| {term} |" in terminology

    for stable_identifier in (
        "SignalResearchDefinitionSpec",
        "trading-cli research run signal",
        "MARKET_MODEL_ONLY",
        "SIGNAL_MODEL_ONLY",
        "MARKET_AND_SIGNAL",
    ):
        assert stable_identifier in terminology


def test_workbench_uses_product_name_and_explicit_qualified_scopes() -> None:
    copy = "\n".join(path.read_text(encoding="utf-8") for path in _WORKBENCH_COPY)

    assert "New Market & Signal Study" in copy
    assert "Market Model-only" in copy
    assert "Signal Model-only" in copy
    assert "Market Model and Signal Model" in copy
    assert "Signal Model-only comparison" in copy
    assert "without Market Model context" in copy
    assert "New Signal Research study" not in copy
    assert 'label: "Market only"' not in copy
    assert 'label: "Signal only"' not in copy
    assert ">Name</h2>" not in copy
    assert ">Scope</h2>" not in copy


def test_workbench_scope_selects_its_compatible_comparison_baseline() -> None:
    page = (_ROOT / "apps/workbench/ui/app/new/page.tsx").read_text(encoding="utf-8")

    expected_baselines = {
        "SIGNAL_MODEL_ONLY": "AFTER_SIGNAL",
        "MARKET_MODEL_ONLY": "MODEL_ACTIVE",
        "MARKET_AND_SIGNAL": "SIGNAL_ONLY",
    }
    for scope, baseline in expected_baselines.items():
        assert re.search(
            rf'{scope}:\s*\{{\s*value:\s*"{baseline}"',
            page,
        )

    assert "next.baseline = { type: baselineTile.value }" in page
    assert "tiles={[baselineTile]}" in page
