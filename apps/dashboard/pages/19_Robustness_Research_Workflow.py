"""Public Robustness Research workflow publication."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_workflow_publication

configure_page(title="Robustness Research Workflow")
render_app_chrome()
render_workflow_publication(
    "workflow-robustness-research",
    evidence_page="pages/4_Robustness_Analysis.py",
    evidence_label="Open Robustness Research technical evidence",
)
