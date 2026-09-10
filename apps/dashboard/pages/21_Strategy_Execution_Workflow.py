"""Public Strategy Execution workflow publication."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_workflow_publication

configure_page(title="Strategy Execution Workflow")
render_app_chrome()
render_workflow_publication(
    "workflow-strategy-execution",
    evidence_page="pages/5_Live_Paper_Trading.py",
    evidence_label="Open DRY_RUN operational evidence",
)
