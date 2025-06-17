"""
Investigation panel layout for detailed turbine analysis.
Module 3: Investigation Panel (Activates on Turbine Selection)
"""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..utils.config import CHART_HEIGHT


def create_investigation_panel_layout(selected_turbine: str = None):
    """Create the investigation panel layout for a selected turbine."""

    if not selected_turbine:
        return html.Div()

    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H4(
                                        f"Investigation Panel - {selected_turbine}",
                                        className="mb-0",
                                    )
                                ],
                                width=10,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "Close",
                                        id="close-investigation",
                                        color="secondary",
                                        size="sm",
                                    )
                                ],
                                width=2,
                                className="text-end",
                            ),
                        ]
                    )
                ]
            ),
            dbc.CardBody(
                [
                    # Turbine Status Overview
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                html.H5(
                                                    "Turbine Summary", className="mb-0"
                                                )
                                            ),
                                            dbc.CardBody(
                                                [html.Div(id="selected-turbine-status")]
                                            ),
                                        ]
                                    )
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                html.H5("Analysis Period Metrics", className="mb-0")
                                            ),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        id="selected-turbine-metrics"
                                                    )
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                html.H5(
                                                    "Analysis Controls",
                                                    className="mb-0",
                                                )
                                            ),
                                            dbc.CardBody(
                                                [
                                                    html.Label(
                                                        "Adjacent Turbines:",
                                                        className="form-label",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="adjacent-turbines-selector",
                                                        multi=True,
                                                        placeholder="Select adjacent turbines for comparison",
                                                    ),
                                                    html.Label(
                                                        "Reference Metmasts:",
                                                        className="form-label mt-2",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="metmast-selector",
                                                        multi=True,
                                                        placeholder="Select metmasts for comparison",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                width=4,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Time Series Charts
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    html.H5(
                                                                        "Power Output Analysis",
                                                                        className="mb-0",
                                                                    )
                                                                ],
                                                                width=8,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.ButtonGroup(
                                                                        [
                                                                            dbc.Button(
                                                                                "24h",
                                                                                id="power-24h",
                                                                                size="sm",
                                                                                outline=True,
                                                                            ),
                                                                            dbc.Button(
                                                                                "7d",
                                                                                id="power-7d",
                                                                                size="sm",
                                                                                outline=True,
                                                                            ),
                                                                            dbc.Button(
                                                                                "30d",
                                                                                id="power-30d",
                                                                                size="sm",
                                                                                outline=True,
                                                                            ),
                                                                        ],
                                                                        size="sm",
                                                                    )
                                                                ],
                                                                width=4,
                                                                className="text-end",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            ),
                                            dbc.CardBody(
                                                [
                                                    dcc.Graph(
                                                        id="power-analysis-chart",
                                                        style={
                                                            "height": f"{CHART_HEIGHT}px"
                                                        },
                                                    )
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                width=12,
                            )
                        ],
                        className="mb-4",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    html.H5(
                                                                        "Wind Speed Comparison",
                                                                        className="mb-0",
                                                                    )
                                                                ],
                                                                width=8,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.ButtonGroup(
                                                                        [
                                                                            dbc.Button(
                                                                                "24h",
                                                                                id="wind-24h",
                                                                                size="sm",
                                                                                outline=True,
                                                                            ),
                                                                            dbc.Button(
                                                                                "7d",
                                                                                id="wind-7d",
                                                                                size="sm",
                                                                                outline=True,
                                                                            ),
                                                                            dbc.Button(
                                                                                "30d",
                                                                                id="wind-30d",
                                                                                size="sm",
                                                                                outline=True,
                                                                            ),
                                                                        ],
                                                                        size="sm",
                                                                    )
                                                                ],
                                                                width=4,
                                                                className="text-end",
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            ),
                                            dbc.CardBody(
                                                [
                                                    dcc.Graph(
                                                        id="wind-comparison-chart",
                                                        style={
                                                            "height": f"{CHART_HEIGHT}px"
                                                        },
                                                    )
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                width=12,
                            )
                        ],
                        className="mb-4",
                    ),
                    # Alarm and Curtailment Analysis
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                html.H5(
                                                    "Alarm & Curtailment History",
                                                    className="mb-0",
                                                )
                                            ),
                                            dbc.CardBody(
                                                [
                                                    dcc.Graph(
                                                        id="alarm-curtailment-chart",
                                                        style={
                                                            "height": f"{CHART_HEIGHT}px"
                                                        },
                                                    )
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                width=12,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Detailed Data Table
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                html.H5(
                                                    "Detailed Data", className="mb-0"
                                                )
                                            ),
                                            dbc.CardBody(
                                                [
                                                    dash_table.DataTable(
                                                        id="detailed-data-table",
                                                        columns=[],
                                                        data=[],
                                                        sort_action="native",
                                                        filter_action="native",
                                                        page_action="native",
                                                        page_current=0,
                                                        page_size=10,
                                                        style_cell={
                                                            "textAlign": "left",
                                                            "padding": "8px",
                                                            "fontFamily": "Arial",
                                                            "fontSize": "12px",
                                                        },
                                                        style_header={
                                                            "backgroundColor": "rgb(230, 230, 230)",
                                                            "fontWeight": "bold",
                                                        },
                                                        style_data_conditional=[
                                                            {
                                                                "if": {
                                                                    "filter_query": "{is_producing} = true"
                                                                },
                                                                "backgroundColor": "#d4edda",
                                                            },
                                                            {
                                                                "if": {
                                                                    "filter_query": "{is_producing} = false"
                                                                },
                                                                "backgroundColor": "#f8d7da",
                                                            },
                                                        ],
                                                    )
                                                ]
                                            ),
                                        ]
                                    )
                                ],
                                width=12,
                            )
                        ]
                    ),
                ]
            ),
        ],
        className="mt-4",
    )


def create_power_analysis_chart(turbine_data, adjacent_data=None, time_range_hours=24):
    """Create power output analysis chart."""
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Power Output", "Operational State"),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
    )

    # Power output line
    fig.add_trace(
        go.Scatter(
            x=turbine_data["TimeStamp"],
            y=turbine_data["wtc_ActPower_mean"],
            mode="lines+markers",
            name="Power Output",
            line=dict(color="blue", width=2),
            marker=dict(size=4),
        ),
        row=1,
        col=1,
    )

    # Add adjacent turbines if provided
    if adjacent_data is not None and not adjacent_data.empty:
        for station_id in adjacent_data["StationId"].unique():
            adj_turbine_data = adjacent_data[adjacent_data["StationId"] == station_id]
            fig.add_trace(
                go.Scatter(
                    x=adj_turbine_data["TimeStamp"],
                    y=adj_turbine_data["wtc_ActPower_mean"],
                    mode="lines",
                    name=f"{station_id} (Adjacent)",
                    line=dict(width=1),
                    opacity=0.6,
                ),
                row=1,
                col=1,
            )

    # Operational state indicators
    state_colors = {
        "PRODUCING": "green",
        "NOT_PRODUCING_EXPLAINED": "yellow",
        "NOT_PRODUCING_VERIFICATION_PENDING": "orange",
        "NOT_PRODUCING_UNEXPECTED": "red",
        "OFFLINE_MAINTENANCE": "gray",
    }

    for state, color in state_colors.items():
        state_data = turbine_data[turbine_data["operational_state"] == state]
        if not state_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=state_data["TimeStamp"],
                    y=[1] * len(state_data),
                    mode="markers",
                    name=state.replace("_", " ").title(),
                    marker=dict(color=color, size=8, symbol="square"),
                    showlegend=True,
                ),
                row=2,
                col=1,
            )

    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Power (kW)", row=1, col=1)
    fig.update_yaxes(title_text="State", row=2, col=1, showticklabels=False)

    fig.update_layout(
        title="Power Output and Operational State Analysis",
        height=CHART_HEIGHT,
        hovermode="x unified",
    )

    return fig


def create_wind_comparison_chart(turbine_data, adjacent_data=None, metmast_data=None):
    """Create wind speed comparison chart."""
    fig = go.Figure()

    # Main turbine wind speed
    fig.add_trace(
        go.Scatter(
            x=turbine_data["TimeStamp"],
            y=turbine_data["wtc_AcWindSp_mean"],
            mode="lines+markers",
            name="Turbine Wind Speed",
            line=dict(color="blue", width=2),
            marker=dict(size=4),
        )
    )

    # Adjacent turbines
    if adjacent_data is not None and not adjacent_data.empty:
        for station_id in adjacent_data["StationId"].unique():
            adj_turbine_data = adjacent_data[adjacent_data["StationId"] == station_id]
            fig.add_trace(
                go.Scatter(
                    x=adj_turbine_data["TimeStamp"],
                    y=adj_turbine_data["wtc_AcWindSp_mean"],
                    mode="lines",
                    name=f"{station_id} Wind",
                    line=dict(width=1),
                    opacity=0.7,
                )
            )

    # Metmast data
    if metmast_data is not None:
        for col in metmast_data.columns:
            if col.startswith("met_WindSpeedRot_mean_"):
                metmast_id = col.split("_")[-1]
                fig.add_trace(
                    go.Scatter(
                        x=metmast_data.index,
                        y=metmast_data[col],
                        mode="lines",
                        name=f"Metmast {metmast_id}",
                        line=dict(dash="dash", width=2),
                    )
                )

    fig.update_layout(
        title="Wind Speed Comparison",
        xaxis_title="Time",
        yaxis_title="Wind Speed (m/s)",
        height=CHART_HEIGHT,
        hovermode="x unified",
    )

    return fig


def create_alarm_curtailment_chart(turbine_data):
    """Create alarm and curtailment analysis chart."""
    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=(
            "Alarm Duration",
            "External Curtailment",
            "Internal Curtailment",
        ),
        vertical_spacing=0.1,
    )

    # Alarm duration
    fig.add_trace(
        go.Bar(
            x=turbine_data["TimeStamp"],
            y=turbine_data["EffectiveAlarmTime"],
            name="Alarm Duration",
            marker_color="red",
        ),
        row=1,
        col=1,
    )

    # External curtailment
    fig.add_trace(
        go.Bar(
            x=turbine_data["TimeStamp"],
            y=turbine_data["wtc_PowerRed_timeon"],
            name="External Curtailment",
            marker_color="orange",
        ),
        row=2,
        col=1,
    )

    # Internal curtailment
    fig.add_trace(
        go.Bar(
            x=turbine_data["TimeStamp"],
            y=turbine_data["Duration 2006(s)"],
            name="Internal Curtailment",
            marker_color="yellow",
        ),
        row=3,
        col=1,
    )

    fig.update_xaxes(title_text="Time", row=3, col=1)
    fig.update_yaxes(title_text="Seconds", row=1, col=1)
    fig.update_yaxes(title_text="Seconds", row=2, col=1)
    fig.update_yaxes(title_text="Seconds", row=3, col=1)

    fig.update_layout(
        title="Alarm and Curtailment History", height=CHART_HEIGHT, showlegend=False
    )

    return fig
