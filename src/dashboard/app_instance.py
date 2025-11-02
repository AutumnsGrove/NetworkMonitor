"""
Dash app instance.
This module contains only the app instance to avoid circular imports.
"""
import dash
import dash_bootstrap_components as dbc

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    requests_pathname_prefix="/dashboard/",
    suppress_callback_exceptions=True,
)

# Server instance for WSGI integration with FastAPI
server = app.server
