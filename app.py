"""
Wind Farm Turbine Investigation Application
Main application entry point for the Silent Loss Detector.
"""

import dash
import dash_bootstrap_components as dbc

# Import layouts and callbacks
from src.layouts.main_dashboard import create_main_dashboard_layout

# Import callbacks to register them
from src.callbacks import main_callbacks, investigation_callbacks  # noqa: F401

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="Wind Farm Turbine Investigation",
    suppress_callback_exceptions=True,
)

# Set the layout
app.layout = create_main_dashboard_layout()

# Server for deployment
server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8050)
