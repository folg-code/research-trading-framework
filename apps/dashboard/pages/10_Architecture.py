"""Stable public Architecture page."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.overview import SHARED_DOMAIN_MERMAID
from dashboard_app.views.portfolio_content import render_static_content_page

configure_page(title="Architecture")
render_app_chrome()
render_static_content_page("architecture", architecture_diagram=SHARED_DOMAIN_MERMAID)
