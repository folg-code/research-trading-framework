"""Public Strategy Research workflow publication."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_workflow_publication

configure_page(title="Strategy Research Workflow")
render_app_chrome()
render_workflow_publication(
    "workflow-strategy-research",
    evidence_page="pages/3_Strategy_Research.py",
    evidence_label="Open Strategy Research technical evidence",
)
