"""Public Predictive Research workflow publication."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_workflow_publication

configure_page(title="Predictive Research Workflow")
render_app_chrome()
render_workflow_publication(
    "workflow-predictive-research",
    evidence_page="pages/6_Predictive_Research.py",
    evidence_label="Open Predictive Research technical evidence",
)
