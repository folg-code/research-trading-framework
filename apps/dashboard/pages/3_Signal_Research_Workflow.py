"""Public Signal Research workflow publication."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_workflow_publication

configure_page(title="Signal Research Workflow")
render_app_chrome()
render_workflow_publication(
    "workflow-signal-research",
    evidence_page="pages/4_Market_and_Signal_Research.py",
    evidence_label="Open Signal Research technical evidence",
)
