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
_METHODOLOGY_PAGES = tuple(sorted((_ROOT / "docs/reference/workflows/methodologies").glob("*.md")))


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


def test_root_readme_uses_technical_name_for_signal_research_workflow() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")

    assert "| Signal Research (product: Market & Signal Study) |" in readme
    assert "MM --> SR[Signal Research]" in readme
    assert "SM --> SR" in readme
    assert "| Signal Research | Amortized reference-price lookup" in readme
    assert "MM --> MR[Market Research]" not in readme
    assert "| Signal / Market Research |" not in readme


def test_detailed_methodologies_use_qualified_explanatory_terms() -> None:
    copy = "\n".join(path.read_text(encoding="utf-8") for path in _METHODOLOGY_PAGES)

    for expanded_term in (
        "maximum favorable excursion (MFE)",
        "maximum adverse excursion (MAE)",
        "profit and loss (PnL)",
        "Market Model or Signal Model",
        "fitted estimator",
        "### Executable Predictive Research workflow",
    ):
        assert expanded_term in copy

    for retired_copy in (
        "### Workflow",
        "Market or Signal Model",
        "trained model",
        "Models do not trade",
        "methodology is executed",
        "methodological layer executed by",
    ):
        assert retired_copy not in copy


def test_strategy_authoring_maps_policy_terms_to_stable_contracts() -> None:
    copy = (_ROOT / "docs/reference/modules/STRATEGY_AUTHORING.md").read_text(encoding="utf-8")

    for explanatory_term in (
        "Strategy Definition",
        "Exit Policy",
        "Risk Policy",
    ):
        assert explanatory_term in copy

    for stable_boundary in (
        "StrategyModelDefinition",
        "ExitModel",
        "RiskModel",
        "trading-cli research run strategy",
        "research.strategy.strategy_file",
    ):
        assert stable_boundary in copy

    assert "writing your own Strategy Model" not in copy
    assert "unsupported Exit/Risk model combination" not in copy
    assert "Policy/Risk Policy" not in copy
    assert "ExitModel/RiskModel" not in copy
