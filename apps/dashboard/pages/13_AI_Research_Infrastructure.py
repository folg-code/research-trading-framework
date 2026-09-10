"""Stable public AI Research Infrastructure Future Idea page."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_static_content_page

configure_page(title="AI Research Infrastructure")
render_app_chrome()
render_static_content_page("future-ai-research-infrastructure")
