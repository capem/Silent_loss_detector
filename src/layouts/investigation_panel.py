"""
Investigation panel layout for detailed turbine analysis.
Module 3: Investigation Panel (Activates on Turbine Selection)
"""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
                                                html.H5(
                                                    "Analysis Period Metrics",
                                                    className="mb-0",
                                                )
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
                                                    html.H5(
                                                        "Comprehensive Time Series Analysis",
                                                        className="mb-0",
                                                    )
                                                ],
                                                className="sticky-top bg-light",  # Make header sticky if chart scrolls
                                            ),
                                            dbc.CardBody(
                                                [
                                                    dcc.Graph(
                                                        id="combined-investigation-chart",
                                                        # Height will be set in the figure layout by the callback
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
                    # This section is now part of the combined chart above.
                    # If specific non-graphical elements related to alarms/curtailments are needed,
                    # they can be added here or elsewhere.
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


def create_combined_investigation_chart(
    turbine_data, adjacent_data=None, metmast_data=None
):
    """
    Create a combined investigation chart with Power, Operational State, Wind Speed,
    and Alarm/Curtailment data as subplots sharing the same x-axis.
    """
    if turbine_data is None or turbine_data.empty:
        return go.Figure()  # Return empty figure if no data

    # Define subplot titles and row heights
    # Adjusted CHART_HEIGHT to be a bit taller for the combined view.
    # Each original chart was CHART_HEIGHT (e.g., 450px).
    # For 6 subplots, we need a taller figure. Let's aim for ~1000-1200px.
    total_height = 1200  # Increased height for 6 subplots
    row_heights = [
        0.22,
        0.13,
        0.22,
        0.11,
        0.11,
        0.11,
    ]  # Sum to 0.9, leaves space for titles/spacing

    fig = make_subplots(
        rows=6,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,  # Slightly increased spacing for better legend placement
        subplot_titles=(
            "Power Output (kW)",
            "Operational State",
            "Wind Speed (m/s)",
            "Alarm Duration (s)",
            "External Curtailment (s)",
            "Internal Curtailment (s)",
        ),
        row_heights=row_heights,
    )

    # --- Row 1: Power Output ---
    fig.add_trace(
        go.Scatter(
            x=turbine_data["TimeStamp"],
            y=turbine_data["wtc_ActPower_mean"],
            mode="lines+markers",
            name=f"{turbine_data['StationId'].iloc[0]} Power",
            line=dict(color="blue", width=2),
            marker=dict(size=4),
            legendgroup="power",
            legendgrouptitle_text="Power Output",
        ),
        row=1,
        col=1,
    )
    if adjacent_data is not None and not adjacent_data.empty:
        for station_id in adjacent_data["StationId"].unique():
            adj_turbine_data = adjacent_data[adjacent_data["StationId"] == station_id]
            fig.add_trace(
                go.Scatter(
                    x=adj_turbine_data["TimeStamp"],
                    y=adj_turbine_data["wtc_ActPower_mean"],
                    mode="lines",
                    name=f"{station_id} Power (Adj.)",
                    line=dict(width=1),
                    opacity=0.6,
                    legendgroup="power",
                ),
                row=1,
                col=1,
            )
    fig.update_yaxes(title_text="Power (kW)", row=1, col=1)

    # --- Row 2: Operational State ---
    state_colors = {
        "PRODUCING": "green",
        "NOT_PRODUCING_EXPLAINED": "gold",
        "NOT_PRODUCING_VERIFICATION_PENDING": "orange",
        "NOT_PRODUCING_UNEXPECTED": "red",
        "DATA_MISSING": "gray",
    }
    for state, color in state_colors.items():
        state_data = turbine_data[turbine_data["operational_state"] == state]
        if not state_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=state_data["TimeStamp"],
                    y=[1] * len(state_data),  # Plot on a simple y-axis
                    mode="markers",
                    name=state.replace("_", " ").title(),
                    marker=dict(color=color, size=8, symbol="square"),
                    legendgroup="operational_state",
                    legendgrouptitle_text="Operational State",
                ),
                row=2,
                col=1,
            )
    fig.update_yaxes(title_text="State", showticklabels=False, row=2, col=1)

    # --- Row 3: Wind Speed ---
    fig.add_trace(
        go.Scatter(
            x=turbine_data["TimeStamp"],
            y=turbine_data["wtc_AcWindSp_mean"],
            mode="lines+markers",
            name=f"{turbine_data['StationId'].iloc[0]} Wind",
            line=dict(color="blue", width=2),
            marker=dict(size=4),
            legendgroup="wind_speed",
            legendgrouptitle_text="Wind Speed",
        ),
        row=3,
        col=1,
    )
    if adjacent_data is not None and not adjacent_data.empty:
        for station_id in adjacent_data["StationId"].unique():
            adj_turbine_data = adjacent_data[adjacent_data["StationId"] == station_id]
            fig.add_trace(
                go.Scatter(
                    x=adj_turbine_data["TimeStamp"],
                    y=adj_turbine_data["wtc_AcWindSp_mean"],
                    mode="lines",
                    name=f"{station_id} Wind (Adj.)",
                    line=dict(width=1),
                    opacity=0.7,
                    legendgroup="wind_speed",
                ),
                row=3,
                col=1,
            )
    if metmast_data is not None:
        for col in metmast_data.columns:
            if col.startswith("met_WindSpeedRot_mean_"):
                metmast_id = col.split("_")[-1]
                fig.add_trace(
                    go.Scatter(
                        x=metmast_data.index,  # Assuming metmast_data index is TimeStamp
                        y=metmast_data[col],
                        mode="lines",
                        name=f"Metmast {metmast_id}",
                        line=dict(dash="dash", width=2),
                        connectgaps=False,
                        legendgroup="wind_speed",
                    ),
                    row=3,
                    col=1,
                )
    fig.update_yaxes(title_text="Wind (m/s)", row=3, col=1)

    # --- Row 4: Alarm Duration ---
    fig.add_trace(
        go.Bar(
            x=turbine_data["TimeStamp"],
            y=turbine_data["EffectiveAlarmTime"],
            name="Alarm Duration",
            marker_color="red",
            showlegend=False,  # Subplot title is enough
        ),
        row=4,
        col=1,
    )
    fig.update_yaxes(title_text="Seconds", row=4, col=1)

    # --- Row 5: External Curtailment ---
    fig.add_trace(
        go.Bar(
            x=turbine_data["TimeStamp"],
            y=turbine_data["wtc_PowerRed_timeon"],
            name="External Curtailment",
            marker_color="orange",
            showlegend=False,
        ),
        row=5,
        col=1,
    )
    fig.update_yaxes(title_text="Seconds", row=5, col=1)

    # --- Row 6: Internal Curtailment ---
    fig.add_trace(
        go.Bar(
            x=turbine_data["TimeStamp"],
            y=turbine_data["Duration 2006(s)"],
            name="Internal Curtailment",
            marker_color="gold",  # Changed from yellow
            showlegend=False,
        ),
        row=6,
        col=1,
    )
    fig.update_yaxes(title_text="Seconds", row=6, col=1)

    # --- General Layout Updates ---
    fig.update_xaxes(
        title_text="Time", row=6, col=1
    )  # Show x-axis title only on the last subplot
    fig.update_layout(
        height=total_height,
        hovermode="x unified",  # Unified hover for all subplots
        legend=dict(
            orientation="v",  # Vertical orientation for better grouping
            yanchor="top",
            y=0.98,  # Position near the top
            xanchor="left",
            x=1.02,  # Position to the right of the chart
            bgcolor="rgba(255,255,255,0.8)",  # Semi-transparent background
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
            font=dict(size=10),  # Smaller font for compact legend
            itemsizing="constant",  # Consistent item sizing
            groupclick="toggleitem",  # Allow toggling individual items within groups
        ),
        margin=dict(t=60, b=50, l=70, r=150),  # Increased right margin for legend space
        showlegend=True,
    )

    return fig
