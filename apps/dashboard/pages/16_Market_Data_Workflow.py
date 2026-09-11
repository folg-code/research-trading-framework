"""Public Market Data workflow publication."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_workflow_publication

configure_page(title="Market Data Workflow")
render_app_chrome()
render_workflow_publication(
    "workflow-market-data",
    evidence_page="pages/2_Market_and_Signal_Research.py",
    evidence_label="Open Market Data technical evidence",
)
