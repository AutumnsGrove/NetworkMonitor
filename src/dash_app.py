"""
Main Dash application for Network Monitor dashboard.
Provides interactive web interface for visualizing network usage data.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

from src.dashboard.app_instance import app
from src.dashboard.components import create_navbar, create_footer
from src.dashboard.layouts import (
    overview_layout,
    applications_layout,
    domains_layout,
    history_layout,
    config_layout,
)

# Define the main layout with navigation and page content area
app.layout = html.Div([
    # URL location component for routing
    dcc.Location(id="url", refresh=False),

    # Navigation bar
    create_navbar(),

    # Content area - pages will be rendered here
    html.Div(id="page-content"),

    # Footer
    create_footer(),
])


# Callback for page routing
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    """
    Route to the appropriate page based on URL pathname.

    Args:
        pathname (str): Current URL pathname

    Returns:
        Component: Layout for the requested page
    """
    # Normalize pathname - handle both /dashboard/ and /dashboard/overview
    if pathname == "/dashboard/" or pathname == "/dashboard/overview":
        return overview_layout()
    elif pathname == "/dashboard/applications":
        return applications_layout()
    elif pathname == "/dashboard/domains":
        return domains_layout()
    elif pathname == "/dashboard/history":
        return history_layout()
    elif pathname == "/dashboard/config":
        return config_layout()
    else:
        # 404 page
        return dbc.Container([
            html.H1("404: Page Not Found", className="text-danger mb-4"),
            html.Hr(),
            html.P(f"The page '{pathname}' does not exist."),
            dbc.Button("Go to Overview", href="/dashboard/", color="primary"),
        ])


# Import and register callbacks AFTER layout is defined
from src.dashboard import callbacks

# Export server instance for WSGI integration with FastAPI
from src.dashboard.app_instance import server
