"""Offline HTML assembly for Predictive Research reports.

Plotly is embedded inline on the first figure. Do not copy Signal Research's CDN.
"""

from __future__ import annotations

import html
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trading_framework.research.reporting.predictive.formatting import format_metric
from trading_framework.research.reporting.predictive.panels import (
    PanelStatus,
    ResolvedPanel,
    resolve_report_panels,
)
from trading_framework.research.reporting.predictive.plotly_figures import (
    build_panel_figure,
    require_plotly,
)
from trading_framework.research.reporting.predictive.view_models import PredictiveReportViewModel

_REPORT_CSS = """
:root {
  color-scheme: light;
  font-family: "Segoe UI", system-ui, sans-serif;
  line-height: 1.45;
  --bg: #f8fafc;
  --card: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --muted: #475569;
}
body { margin: 0; background: var(--bg); color: var(--text); }
.container { max-width: 1240px; margin: 0 auto; padding: 1.5rem 1.25rem 2.5rem; }
header { margin-bottom: 1.25rem; }
header h1 { margin: 0 0 0.35rem; font-size: 1.55rem; }
header .meta { color: var(--muted); font-size: 0.92rem; }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin: 0.85rem 0 0;
}
.kpi-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.8rem 0.9rem;
  background: #fff;
}
.kpi-card .label { color: var(--muted); font-size: 0.82rem; margin-bottom: 0.2rem; }
.kpi-card .value { font-size: 1.05rem; font-weight: 600; }
section {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}
section h2 { margin: 0 0 0.5rem; font-size: 1.05rem; }
section p.intro, section p.note { margin: 0 0 0.75rem; color: var(--muted); font-size: 0.9rem; }
.chart-block { margin-top: 0.5rem; }
.warning {
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.75rem;
  color: #9a3412;
}
.warning strong { display: block; margin-bottom: 0.25rem; }
.warning .threshold { color: #7c2d12; font-size: 0.85rem; margin-top: 0.3rem; }
"""


@dataclass
class _PlotlyEmbedState:
    include_plotlyjs: str | bool = "inline"
    used: bool = field(default=False)

    def consume(self) -> str | bool:
        if self.used:
            return False
        self.used = True
        return self.include_plotlyjs


def render_predictive_research_report_html(
    view: PredictiveReportViewModel,
    output_path: Path,
) -> Path:
    """Write a standalone offline HTML report from a view model."""
    go, pio, make_subplots = require_plotly()
    embed = _PlotlyEmbedState()
    sections = [
        _render_panel(panel, view, go, pio, make_subplots, embed)
        for panel in resolve_report_panels(view)
    ]
    document = _document(view, sections)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _render_panel(
    panel: ResolvedPanel,
    view: PredictiveReportViewModel,
    go: Any,
    pio: Any,
    make_subplots: Any,
    embed: _PlotlyEmbedState,
) -> str:
    intro = f'<p class="intro">{html.escape(panel.intro)}</p>'
    if panel.status is PanelStatus.SKIP:
        reason = panel.skip_reason or "Skipped."
        body = f'<p class="note">{html.escape(reason)}</p>'
    else:
        renderer = PANEL_BODY_RENDERERS.get(panel.panel_id)
        if renderer is None:
            body = '<p class="note">No renderer registered for this panel.</p>'
        else:
            body = renderer(view, go, pio, make_subplots, embed)
    return (
        f'<section id="{html.escape(panel.panel_id)}">'
        f"<h2>{html.escape(panel.title)}</h2>"
        f"{intro}{body}</section>"
    )


def _plotly_body(panel_id: str) -> Callable[..., str]:
    def render(
        view: PredictiveReportViewModel,
        go: Any,
        pio: Any,
        make_subplots: Any,
        embed: _PlotlyEmbedState,
    ) -> str:
        figure = build_panel_figure(panel_id, go, make_subplots, view)
        if figure is None:
            return '<p class="note">No figure registered for this panel.</p>'
        chart = pio.to_html(
            figure,
            full_html=False,
            include_plotlyjs=embed.consume(),
        )
        return f'<div class="chart-block">{chart}</div>'

    return render


def _quality_flags_body(
    view: PredictiveReportViewModel,
    go: Any,
    pio: Any,
    make_subplots: Any,
    embed: _PlotlyEmbedState,
) -> str:
    del go, pio, make_subplots, embed
    if not view.quality_warnings:
        return '<p class="note">No quality flags triggered for the declared thresholds.</p>'
    blocks: list[str] = []
    for warning in view.quality_warnings:
        blocks.append(
            '<div class="warning">'
            f"<strong>{html.escape(warning.code.value)}</strong>"
            f"{html.escape(warning.message)}"
            '<div class="threshold">'
            f"threshold={html.escape(format_metric(warning.threshold))} "
            f"observed={html.escape(format_metric(warning.observed))}"
            "</div></div>"
        )
    return "".join(blocks)


PANEL_BODY_RENDERERS: dict[str, Callable[..., str]] = {
    "fold_timeline": _plotly_body("fold_timeline"),
    "metric_stability": _plotly_body("metric_stability"),
    "model_vs_baselines": _plotly_body("model_vs_baselines"),
    "prediction_quality": _plotly_body("prediction_quality"),
    "discrimination": _plotly_body("discrimination"),
    "calibration": _plotly_body("calibration"),
    "prediction_buckets": _plotly_body("prediction_buckets"),
    "sample_composition": _plotly_body("sample_composition"),
    "quality_flags": _quality_flags_body,
    "feature_importance": _plotly_body("feature_importance"),
    "leaderboard": _plotly_body("leaderboard"),
    "selection_trace": _plotly_body("selection_trace"),
    "learning_curves": _plotly_body("learning_curves"),
    "window_accounting": _plotly_body("window_accounting"),
}


def _document(view: PredictiveReportViewModel, sections: list[str]) -> str:
    generated = view.generated_at_utc.isoformat()
    return (
        "<!DOCTYPE html>\n<html lang='en'><head><meta charset='utf-8'>"
        f"<title>Predictive Research {html.escape(view.run_id)}</title>"
        f"<style>{_REPORT_CSS}</style></head><body><div class='container'>"
        "<header><h1>Predictive Research report</h1>"
        f"<div class='meta'>Generated {html.escape(generated)}</div>"
        "<div class='kpi-grid'>"
        f"{_kpi('Run', view.run_id)}"
        f"{_kpi('Dataset', view.dataset_id)}"
        f"{_kpi('Task', view.task_type.value)}"
        f"{_kpi(view.primary_metric, format_metric(view.pooled_model))}"
        "</div></header>"
        f"{''.join(sections)}</div></body></html>\n"
    )


def _kpi(label: str, value: str) -> str:
    return (
        '<div class="kpi-card">'
        f'<div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div>'
        "</div>"
    )
