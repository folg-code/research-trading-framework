"""HTML report for bounded model-family comparisons."""

from __future__ import annotations

import html
from pathlib import Path

import polars as pl

from trading_framework.research.datasets.signal_research_family import (
    SignalResearchFamilyExperimentManifest,
)
from trading_framework.research.reporting.signal_research.formatting import (
    format_count,
    format_hit_rate,
    format_return,
)
from trading_framework.research.reporting.signal_research.plotly_figures import (
    build_family_comparison_chart,
    require_plotly,
)

_FAMILY_CSS = """
body { font-family: "Segoe UI", system-ui, sans-serif; margin: 1.5rem; color: #0f172a; }
table.data { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-top: 1rem; }
table.data th, table.data td { border: 1px solid #e2e8f0; padding: 0.45rem 0.55rem; }
table.data th { background: #f1f5f9; text-align: left; }
table.data td.num { text-align: right; font-variant-numeric: tabular-nums; }
.meta { color: #475569; margin-bottom: 1rem; }
"""


def render_model_family_comparison_html(
    *,
    manifest: SignalResearchFamilyExperimentManifest,
    family_comparison: pl.DataFrame,
    output_path: Path,
) -> Path:
    """Render one standalone model-family comparison dashboard."""
    go, pio, _ = require_plotly()
    rows = family_comparison.to_dicts()
    chart = build_family_comparison_chart(go, comparison_rows=rows)
    chart_html = pio.to_html(chart, full_html=False, include_plotlyjs=False)
    table = _comparison_table(rows)
    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Model Family — {html.escape(manifest.family_id)}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>{_FAMILY_CSS}</style>
</head>
<body>
  <h1>Model family comparison</h1>
  <div class="meta">
    Experiment: <strong>{html.escape(manifest.experiment_id)}</strong><br>
    Research: <strong>{html.escape(manifest.research_id)}</strong><br>
    Generated: {html.escape(str(manifest.candidates_generated))} ·
    Evaluated: {html.escape(str(manifest.candidates_evaluated))} ·
    Skipped: {html.escape(str(manifest.candidates_skipped))}
  </div>
  {table}
  <div>{chart_html}</div>
</body>
</html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _comparison_table(rows: list[dict[str, object]]) -> str:
    header = (
        "<thead><tr>"
        "<th>Variant</th><th>Run</th><th>Sample</th><th>Mean</th><th>Median</th>"
        "<th>Hit rate</th><th>MFE</th><th>MAE</th><th>Warnings</th>"
        "</tr></thead>"
    )
    body: list[str] = []
    for row in rows:
        if not row["metrics_eligible"]:
            metrics = ["—", "—", "—", "—", "—"]
        else:
            metrics = [
                format_return(float(row["forward_return_mean"])),  # type: ignore[arg-type]
                format_return(float(row["forward_return_median"])),  # type: ignore[arg-type]
                format_hit_rate(float(row["hit_rate"])),  # type: ignore[arg-type]
                format_return(float(row["mfe_mean"])),  # type: ignore[arg-type]
                format_return(float(row["mae_mean"])),  # type: ignore[arg-type]
            ]
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row['variant_id']))}</td>"
            f"<td>{html.escape(str(row['run_id']))}</td>"
            f"<td class='num'>{format_count(int(str(row['sample_size_complete'])))}</td>"
            + "".join(f"<td class='num'>{value}</td>" for value in metrics)
            + f"<td class='num'>{int(str(row['quality_warning_count']))}</td>"
            + "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body)}</tbody></table>"
