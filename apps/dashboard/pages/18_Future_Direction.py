"""Stable public Future Direction index."""

from dashboard_app.ui import configure_page, render_app_chrome
from dashboard_app.views.portfolio_content import (
    render_future_direction_entries,
    render_static_content_page,
)

configure_page(title="Future Direction")
render_app_chrome()
render_static_content_page("future-direction")
render_future_direction_entries()
