"""Contract and regression tests for the BTC Signal Quality study view (Sprint 060 T005).

These tests target the four acceptance properties T005 adds beyond T003's
happy-path coverage:

1. **Traceability** -- every number the study renders (verdict, ROC AUC,
   threshold points, trade disposition) equals the resolved artifact field
   verbatim, both against synthetic sentinel data and against the real
   committed projection bundle.
2. **Negative / non-``INCONCLUSIVE`` evidence** -- the view renders any
   persisted verdict value the same way; it is not hard-coded to the one
   verdict the real study happens to carry today.
3. **Absent optional artifacts** -- a study manifest that omits a role
   degrades that one section, not the whole page (ADR-0034 S2.4 governs the
   *dangling*-reference case; this is the *legitimately absent* case).
4. **No dashboard-side verdict/metric logic** -- the verdict badge's color
   is a source-level literal, never a value derived from the verdict text
   (D060-03).

``render_btc_signal_quality_study`` always loads the real, committed study
end to end -- there is no injection seam by design (ADR-0034 S1.6: the
public path reads only the committed bundle/manifest, nothing else). Tests
that need synthetic evidence therefore monkeypatch
``dashboard_app.views.study.load_btc_signal_quality_evidence`` via pytest's
``monkeypatch`` fixture -- scoped to one test and auto-restored on
teardown, unlike mutating the module attribute directly, which would leak
into every other test sharing this process (``AppTest`` executes each
script in-process, against the same cached module object).
"""

from __future__ import annotations

import json
import re
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from dashboard_app.publication.paths import projection_bundle_path, study_manifest_path
from dashboard_app.publication.projection import ProjectedArtifact
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    StudyEvidence,
    load_study_manifest_from_path,
)
from dashboard_app.views.study import STUDY_SLUG

_STUDY_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "dashboard_app" / "views" / "study.py"
).read_text(encoding="utf-8")

_RENDER_APP_SCRIPT = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, {src!r})
    from dashboard_app.views.study import render_btc_signal_quality_study
    render_btc_signal_quality_study()
    """
)

#: Full six-role synthetic evidence with easily-recognizable sentinel values
#: -- distinct from any real persisted number, so a test failure cannot be
#: confused with a real-data coincidence. Verdict is deliberately NOT
#: "INCONCLUSIVE" (property 2).
_FULL_SENTINEL_ARTIFACTS: dict[str, dict[str, Any]] = {
    "verdict": {
        "artifact_id": "verdict-1",
        "artifact_role": "predictive_run_verdict",
        "fields": {"verdict": "REJECTED_OVERFIT", "rule_set_version": "verdict_rules.v1"},
    },
    "predictive_metrics": {
        "artifact_id": "metrics-1",
        "artifact_role": "predictive_run_metrics",
        "fields": {
            "decision_threshold": 0.918273,
            "seed": 415926,
            "pooled": {
                "MODEL": {"statistical": {"roc_auc": 0.611111}},
                "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.522222}},
            },
            "folds": {
                "0": {
                    "MODEL": {"statistical": {"roc_auc": 0.633333}},
                    "RANDOM_PERMUTATION": {"statistical": {"roc_auc": 0.544444}},
                }
            },
        },
    },
    "threshold_sensitivity": {
        "artifact_id": "threshold-1",
        "artifact_role": "predictive_threshold_sensitivity",
        "fields": {
            "points": [
                {"threshold": 0.101, "finance": {"coverage": 0.909, "hit_rate": 0.717}},
                {"threshold": 0.202, "finance": {"coverage": 0.808, "hit_rate": 0.626}},
            ]
        },
    },
    "promoted_artifact": {
        "artifact_id": "promoted-1",
        "artifact_role": "promoted_artifact_identity",
        "fields": {"artifact_fingerprint": "sentinelfingerprint000000000000"},
    },
    "strategy_baseline": {
        "artifact_id": "baseline-1",
        "artifact_role": "strategy_research_run_summary",
        "fields": {
            "run_id": "sentinel-baseline-run",
            "trade_count": 4242,
            "win_rate": 0.535353,
            "net_pnl": 313131.31,
        },
    },
    "strategy_scored": {
        "artifact_id": "scored-1",
        "artifact_role": "strategy_research_run_summary",
        "fields": {
            "run_id": "sentinel-scored-run",
            "trade_count": 4141,
            "win_rate": 0.545454,
            "net_pnl": 323232.32,
        },
    },
}


def _run_synthetic_study_app(
    monkeypatch: pytest.MonkeyPatch, resolved_artifacts: dict[str, dict[str, Any]]
) -> AppTest:
    import dashboard_app.views.study as study_module

    def _fake_load_evidence() -> StudyEvidence | PublicationUnavailable:
        return StudyEvidence(
            manifest=object(),  # type: ignore[arg-type]  # never read; only .resolved_artifacts is
            resolved_artifacts={
                role: ProjectedArtifact(**kwargs) for role, kwargs in resolved_artifacts.items()
            },
        )

    # A plain module-attribute assignment would leak into every other test
    # sharing this process, because AppTest executes the script below
    # in-process against the same cached `dashboard_app.views.study` module
    # object -- `monkeypatch` restores the original function on teardown.
    monkeypatch.setattr(study_module, "load_btc_signal_quality_evidence", _fake_load_evidence)

    dashboard_src = str(Path(__file__).resolve().parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "study_contract_app.py"
        script_path.write_text(_RENDER_APP_SCRIPT.format(src=dashboard_src), encoding="utf-8")
        app = AppTest.from_file(str(script_path))
        app.run(timeout=30)
        return app


def _figure_y_values(app: AppTest) -> list[list[float]]:
    """Extract every trace's ``y`` series from each rendered Plotly chart.

    ``AppTest`` has no dedicated Plotly wrapper (it falls back to
    ``UnknownElement``, whose generic ``.value`` accessor does not apply to
    this proto shape) -- ``proto.spec`` is the JSON-serialized
    ``{data, frames, layout}`` dict Streamlit's own ``PlotlyChart`` proto
    documents, so this reads it directly.
    """
    y_values: list[list[float]] = []
    for chart in app.get("plotly_chart"):
        spec = json.loads(chart.proto.spec)
        for trace in spec.get("data", []):
            y = trace.get("y")
            if y is not None:
                y_values.append(list(y))
    return y_values


# --- Property 4: no dashboard-side verdict/metric logic ---------------------------


def _extract_balanced_call(source: str, call_prefix: str) -> str:
    """Return the full ``prefix(...)`` call text, matching nested parens."""
    start = source.index(call_prefix)
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "(":
            depth += 1
        elif source[index] == ")":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unbalanced parens while extracting {call_prefix!r}")


def test_verdict_badge_color_is_a_source_level_literal_never_derived_from_verdict() -> None:
    """D060-03: the badge must not map verdict text to a color -- a future
    "make INCONCLUSIVE red" change would be a real regression this catches."""
    badge_call = _extract_balanced_call(_STUDY_SOURCE, "st.badge(")
    # The color argument must be a plain string literal, never an f-string,
    # ternary, or dict/variable lookup keyed by the verdict text.
    assert re.search(r'color\s*=\s*["\']gray["\']\s*,?\s*\)\s*$', badge_call)


# --- Properties 1 + 2: traceability, and non-INCONCLUSIVE evidence ----------------


def test_synthetic_non_inconclusive_verdict_renders_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_synthetic_study_app(monkeypatch, _FULL_SENTINEL_ARTIFACTS)

    assert not app.exception
    badge_markdown = "\n".join(entry.value for entry in app.markdown)
    assert ":gray-badge[REJECTED_OVERFIT]" in badge_markdown
    assert "INCONCLUSIVE" not in badge_markdown


def test_synthetic_sentinel_values_trace_exactly_into_the_charts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every plotted number must equal the resolved artifact field verbatim --
    proof the view/chart layer copies rather than recomputes (ADR-0034 S1.4)."""
    app = _run_synthetic_study_app(monkeypatch, _FULL_SENTINEL_ARTIFACTS)

    assert not app.exception
    all_y_values = {round(value, 6) for series in _figure_y_values(app) for value in series}

    expected = {
        0.611111,
        0.522222,
        0.633333,
        0.544444,  # ROC AUC (pooled + one fold, MODEL/RANDOM_PERMUTATION)
        0.909,
        0.808,
        0.717,
        0.626,  # threshold coverage/hit_rate
        4242.0,
        4141.0,
        0.535353,
        0.545454,
        313131.31,
        323232.32,  # trade disposition
    }
    assert expected <= all_y_values

    full_text = "\n".join(entry.value for entry in app.caption)
    assert "0.918273" in full_text  # decision_threshold caption, verbatim
    assert "415926" in full_text  # seed caption, verbatim


def _real_resolved_artifacts_by_sentinel_role() -> dict[str, dict[str, Any]]:
    """Map every sentinel role name onto its real committed artifact.

    Uses the real, committed study manifest's own ``artifact_roles`` (role
    name -> artifact id) to resolve each role -- the same lookup
    ``resolve_study_evidence`` performs in production. Matching on
    ``artifact_role`` string alone would be ambiguous: the real bundle has
    *two* artifacts sharing ``artifact_role: "strategy_research_run_summary"``
    (baseline and scored), which a role-string match cannot tell apart.
    """
    manifest = load_study_manifest_from_path(study_manifest_path(STUDY_SLUG))
    assert not isinstance(manifest, PublicationUnavailable), manifest
    raw_bundle = json.loads(projection_bundle_path().read_text(encoding="utf-8"))

    return {
        role: raw_bundle["artifacts"][manifest.artifact_roles[role]]
        for role in _FULL_SENTINEL_ARTIFACTS
    }


def test_study_traceability_against_the_real_committed_bundle() -> None:
    """The real study's rendered numbers must equal the real committed
    manifest/bundle's raw fields exactly -- a regression guard against any
    future rounding, normalization or recomputation creeping into the view.

    Runs the real, unmocked render path end to end (no monkeypatching) --
    this is what ``test_study_acceptance.py`` already does; this test adds
    the explicit byte-for-byte comparison against the raw committed JSON
    that acceptance test does not make.
    """
    real_artifacts = _real_resolved_artifacts_by_sentinel_role()
    metrics_fields = real_artifacts["predictive_metrics"]["fields"]
    expected_pooled_model = metrics_fields["pooled"]["MODEL"]["statistical"]["roc_auc"]
    expected_pooled_permutation = metrics_fields["pooled"]["RANDOM_PERMUTATION"]["statistical"][
        "roc_auc"
    ]
    expected_baseline_trade_count = real_artifacts["strategy_baseline"]["fields"]["trade_count"]
    expected_scored_trade_count = real_artifacts["strategy_scored"]["fields"]["trade_count"]
    assert expected_baseline_trade_count != expected_scored_trade_count, (
        "fixture sanity check: baseline and scored must be genuinely distinct real artifacts"
    )

    dashboard_src = str(Path(__file__).resolve().parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "study_real_data_app.py"
        script_path.write_text(_RENDER_APP_SCRIPT.format(src=dashboard_src), encoding="utf-8")
        app = AppTest.from_file(str(script_path))
        app.run(timeout=30)

    assert not app.exception
    all_y_values = {value for series in _figure_y_values(app) for value in series}
    assert expected_pooled_model in all_y_values
    assert expected_pooled_permutation in all_y_values
    assert float(expected_baseline_trade_count) in all_y_values
    assert float(expected_scored_trade_count) in all_y_values


# --- Property 3: absent optional artifacts -----------------------------------------


def test_study_degrades_one_section_when_a_role_is_absent_from_the_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A study manifest that never declares ``threshold_sensitivity`` (a
    role legitimately absent, not a dangling reference) must still render
    the verdict and the other two charts -- never the whole-page
    ``PublicationUnavailable`` warning ADR-0034 S2.4 reserves for a
    resolution failure."""
    partial_artifacts = {
        role: kwargs
        for role, kwargs in _FULL_SENTINEL_ARTIFACTS.items()
        if role != "threshold_sensitivity"
    }
    app = _run_synthetic_study_app(monkeypatch, partial_artifacts)

    assert not app.exception
    subheaders = {entry.value for entry in app.subheader}
    assert "Persisted verdict" in subheaders
    assert "Model vs. random-permutation ROC AUC" in subheaders
    assert "Baseline vs. scored trade disposition" in subheaders
    assert "Threshold sensitivity" not in subheaders
    assert len(app.get("plotly_chart")) == 2

    full_text = "\n".join(entry.value for entry in app.warning)
    assert not full_text, "an absent optional role must not surface a page-level warning"
