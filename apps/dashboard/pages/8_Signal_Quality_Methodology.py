"""Signal Quality methodology page (Sprint 060 T004)."""

from __future__ import annotations

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_signal_quality_methodology

configure_page(title="Signal Quality Methodology")
render_app_chrome()

render_signal_quality_methodology()
