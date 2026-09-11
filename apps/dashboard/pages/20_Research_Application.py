"""Stable public Research Application Future Idea page."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import render_static_content_page

configure_page(title="Research Application")
render_app_chrome()
render_static_content_page("future-research-application")
