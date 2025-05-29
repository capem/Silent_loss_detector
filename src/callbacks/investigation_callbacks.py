"""
Investigation panel callbacks for detailed turbine analysis.
"""

from dash import Input, Output, State, callback, ctx, html
import pandas as pd
from datetime import timedelta
import plotly.graph_objects as go

from ..layouts.investigation_panel import (
    create_power_analysis_chart,
    create_wind_comparison_chart,
    create_alarm_curtailment_chart,
)
from ..utils.config import OPERATIONAL_STATES


@callback(
    [
        Output("selected-turbine-status", "children"),
        Output("selected-turbine-metrics", "children"),
    ],
    [Input("selected-turbine-store", "data")],
    [State("filtered-data-store", "data")],
)
def update_turbine_status_and_metrics(selected_turbine, filtered_data):
    """Update selected turbine status and key metrics."""
    if not selected_turbine or not filtered_data:
        return "No turbine selected", "No data available"

    try:
        # Convert to DataFrame
        df = pd.DataFrame(filtered_data)
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Get latest data for selected turbine
        turbine_data = df[df["StationId"] == selected_turbine]
        if turbine_data.empty:
            return "No data for selected turbine", "No data available"

        latest_data = turbine_data.iloc[-1]

        # Status display
        state_info = OPERATIONAL_STATES.get(latest_data["operational_state"], {})
        status_color = state_info.get("color", "#6c757d")

        status_content = [
            html.Div(
                [
                    html.H6(
                        latest_data["state_category"],
                        style={"color": status_color, "margin-bottom": "5px"},
                    ),
                    html.P(
                        latest_data["state_subcategory"],
                        className="text-muted small mb-2",
                    ),
                    html.P(
                        latest_data["state_reason"],
                        className="small",
                        style={"font-style": "italic"},
                    ),
                ]
            )
        ]

        # Metrics display
        metrics_content = [
            html.Div(
                [
                    html.Div(
                        [
                            html.Strong("Power Output: "),
                            html.Span(f"{latest_data['wtc_ActPower_mean']:.1f} kW"),
                        ],
                        className="mb-2",
                    ),
                    html.Div(
                        [
                            html.Strong("Wind Speed: "),
                            html.Span(f"{latest_data['wtc_AcWindSp_mean']:.1f} m/s"),
                        ],
                        className="mb-2",
                    ),
                    html.Div(
                        [
                            html.Strong("Last Update: "),
                            html.Span(
                                latest_data["TimeStamp"].strftime("%Y-%m-%d %H:%M")
                            ),
                        ],
                        className="mb-2",
                    ),
                    html.Div(
                        [
                            html.Strong("Active Alarms: "),
                            html.Span(
                                "Yes" if latest_data["EffectiveAlarmTime"] > 0 else "No"
                            ),
                        ],
                        className="mb-2",
                    ),
                ]
            )
        ]

        return status_content, metrics_content

    except Exception as e:
        return f"Error: {str(e)}", "Error loading metrics"


@callback(
    Output("power-analysis-chart", "figure"),
    [
        Input("selected-turbine-store", "data"),
        Input("power-24h", "n_clicks"),
        Input("power-7d", "n_clicks"),
        Input("power-30d", "n_clicks"),
        Input("adjacent-turbines-selector", "value"),
    ],
    [State("filtered-data-store", "data")],
)
def update_power_analysis_chart(
    selected_turbine, btn_24h, btn_7d, btn_30d, adjacent_turbines, filtered_data
):
    """Update power analysis chart."""
    if not selected_turbine or not filtered_data:
        return go.Figure()

    try:
        # Convert to DataFrame
        df = pd.DataFrame(filtered_data)
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Determine time range
        triggered_id = (
            ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        )

        if triggered_id == "power-24h":
            hours = 24
        elif triggered_id == "power-7d":
            hours = 24 * 7
        elif triggered_id == "power-30d":
            hours = 24 * 30
        else:
            hours = 24  # Default

        # Filter data by time range
        end_time = df["TimeStamp"].max()
        start_time = end_time - timedelta(hours=hours)
        time_filtered_df = df[df["TimeStamp"] >= start_time]

        # Get turbine data
        turbine_data = time_filtered_df[
            time_filtered_df["StationId"] == selected_turbine
        ]

        # Get adjacent turbine data
        adjacent_data = None
        if adjacent_turbines:
            adjacent_data = time_filtered_df[
                time_filtered_df["StationId"].isin(adjacent_turbines)
            ]

        # Create chart
        fig = create_power_analysis_chart(turbine_data, adjacent_data, hours)

        return fig

    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )


@callback(
    Output("wind-comparison-chart", "figure"),
    [
        Input("selected-turbine-store", "data"),
        Input("wind-24h", "n_clicks"),
        Input("wind-7d", "n_clicks"),
        Input("wind-30d", "n_clicks"),
        Input("adjacent-turbines-selector", "value"),
        Input("metmast-selector", "value"),
    ],
    [State("filtered-data-store", "data")],
)
def update_wind_comparison_chart(
    selected_turbine,
    btn_24h,
    btn_7d,
    btn_30d,
    adjacent_turbines,
    metmast_columns,
    filtered_data,
):
    """Update wind speed comparison chart."""
    if not selected_turbine or not filtered_data:
        return go.Figure()

    try:
        # Convert to DataFrame
        df = pd.DataFrame(filtered_data)
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Determine time range
        triggered_id = (
            ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        )

        if triggered_id == "wind-24h":
            hours = 24
        elif triggered_id == "wind-7d":
            hours = 24 * 7
        elif triggered_id == "wind-30d":
            hours = 24 * 30
        else:
            hours = 24  # Default

        # Filter data by time range
        end_time = df["TimeStamp"].max()
        start_time = end_time - timedelta(hours=hours)
        time_filtered_df = df[df["TimeStamp"] >= start_time]

        # Get turbine data
        turbine_data = time_filtered_df[
            time_filtered_df["StationId"] == selected_turbine
        ]

        # Get adjacent turbine data
        adjacent_data = None
        if adjacent_turbines:
            adjacent_data = time_filtered_df[
                time_filtered_df["StationId"].isin(adjacent_turbines)
            ]

        # Get metmast data
        metmast_data = None
        if metmast_columns:
            metmast_data = time_filtered_df.set_index("TimeStamp")[
                metmast_columns
            ].dropna()

        # Create chart
        fig = create_wind_comparison_chart(turbine_data, adjacent_data, metmast_data)

        return fig

    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )


@callback(
    Output("alarm-curtailment-chart", "figure"),
    [Input("selected-turbine-store", "data")],
    [State("filtered-data-store", "data")],
)
def update_alarm_curtailment_chart(selected_turbine, filtered_data):
    """Update alarm and curtailment chart."""
    if not selected_turbine or not filtered_data:
        return go.Figure()

    try:
        # Convert to DataFrame
        df = pd.DataFrame(filtered_data)
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Get turbine data
        turbine_data = df[df["StationId"] == selected_turbine]

        # Create chart
        fig = create_alarm_curtailment_chart(turbine_data)

        return fig

    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )


@callback(
    Output("anomaly-analysis-content", "children"),
    [
        Input("selected-turbine-store", "data"),
        Input("adjacent-turbines-selector", "value"),
        Input("metmast-selector", "value"),
    ],
    [State("filtered-data-store", "data")],
)
def update_anomaly_analysis(
    selected_turbine, adjacent_turbines, metmast_columns, filtered_data
):
    """Update production anomaly analysis."""
    if not selected_turbine or not filtered_data:
        return "No data available"

    try:
        # Convert to DataFrame
        df = pd.DataFrame(filtered_data)
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Get latest data for analysis
        latest_time = df["TimeStamp"].max()
        latest_data = df[df["TimeStamp"] == latest_time]

        # Get selected turbine data
        turbine_row = latest_data[latest_data["StationId"] == selected_turbine]
        if turbine_row.empty:
            return "No current data for selected turbine"

        turbine_row = turbine_row.iloc[0]

        # Analyze production anomaly
        is_producing = turbine_row["is_producing"]
        turbine_wind = turbine_row["wtc_AcWindSp_mean"]
        turbine_power = turbine_row["wtc_ActPower_mean"]

        analysis_results = []

        # Check if turbine should be producing
        if not is_producing:
            # Check adjacent turbines
            adjacent_producing = 0
            adjacent_total = 0
            adjacent_avg_wind = 0
            adjacent_avg_power = 0

            if adjacent_turbines:
                adjacent_data = latest_data[
                    latest_data["StationId"].isin(adjacent_turbines)
                ]
                adjacent_total = len(adjacent_data)
                adjacent_producing = len(
                    adjacent_data[adjacent_data["is_producing"] == True]
                )

                if not adjacent_data.empty:
                    adjacent_avg_wind = adjacent_data["wtc_AcWindSp_mean"].mean()
                    adjacent_avg_power = adjacent_data["wtc_ActPower_mean"].mean()

            # Check metmasts
            metmast_avg_wind = 0
            metmast_count = 0

            if metmast_columns:
                metmast_values = []
                for col in metmast_columns:
                    if col in latest_data.columns:
                        values = latest_data[col].dropna()
                        if not values.empty:
                            metmast_values.extend(values.tolist())

                if metmast_values:
                    metmast_avg_wind = sum(metmast_values) / len(metmast_values)
                    metmast_count = len(metmast_values)

            # Generate analysis
            analysis_results.append(
                html.H6("🔍 Production Anomaly Analysis", className="text-primary")
            )

            analysis_results.append(
                html.Div(
                    [
                        html.Strong("Current Status: "),
                        html.Span("Not Producing", style={"color": "red"}),
                    ],
                    className="mb-2",
                )
            )

            analysis_results.append(
                html.Div(
                    [
                        html.Strong("Turbine Wind Speed: "),
                        html.Span(f"{turbine_wind:.1f} m/s"),
                    ],
                    className="mb-2",
                )
            )

            if adjacent_total > 0:
                analysis_results.append(
                    html.Div(
                        [
                            html.Strong("Adjacent Turbines: "),
                            html.Span(
                                f"{adjacent_producing}/{adjacent_total} producing"
                            ),
                        ],
                        className="mb-2",
                    )
                )

                analysis_results.append(
                    html.Div(
                        [
                            html.Strong("Adjacent Avg Wind: "),
                            html.Span(f"{adjacent_avg_wind:.1f} m/s"),
                        ],
                        className="mb-2",
                    )
                )

            if metmast_count > 0:
                analysis_results.append(
                    html.Div(
                        [
                            html.Strong("Metmast Avg Wind: "),
                            html.Span(f"{metmast_avg_wind:.1f} m/s"),
                        ],
                        className="mb-2",
                    )
                )

            # Anomaly assessment
            anomaly_detected = False
            anomaly_reasons = []

            if adjacent_total > 0 and adjacent_producing > adjacent_total * 0.5:
                if adjacent_avg_wind > 4.0:  # Sufficient wind
                    anomaly_detected = True
                    anomaly_reasons.append(
                        "Adjacent turbines producing with sufficient wind"
                    )

            if metmast_count > 0 and metmast_avg_wind > 4.0:
                anomaly_detected = True
                anomaly_reasons.append("Metmasts show sufficient wind")

            if anomaly_detected:
                analysis_results.append(html.Hr())
                analysis_results.append(
                    html.Div(
                        [
                            html.Strong("⚠️ ANOMALY DETECTED", style={"color": "red"}),
                            html.Ul([html.Li(reason) for reason in anomaly_reasons]),
                        ]
                    )
                )
            else:
                analysis_results.append(html.Hr())
                analysis_results.append(
                    html.Div(
                        [
                            html.Strong(
                                "✅ No Clear Anomaly", style={"color": "green"}
                            ),
                            html.P(
                                "Non-production appears justified based on available data"
                            ),
                        ]
                    )
                )

        else:
            analysis_results.append(
                html.Div(
                    [
                        html.H6(
                            "✅ Turbine Producing Normally", className="text-success"
                        ),
                        html.P(f"Power Output: {turbine_power:.1f} kW"),
                        html.P(f"Wind Speed: {turbine_wind:.1f} m/s"),
                    ]
                )
            )

        return analysis_results

    except Exception as e:
        return f"Error in anomaly analysis: {str(e)}"


@callback(
    [Output("detailed-data-table", "columns"), Output("detailed-data-table", "data")],
    [Input("selected-turbine-store", "data")],
    [State("filtered-data-store", "data")],
)
def update_detailed_data_table(selected_turbine, filtered_data):
    """Update detailed data table for selected turbine."""
    if not selected_turbine or not filtered_data:
        return [], []

    try:
        # Convert to DataFrame
        df = pd.DataFrame(filtered_data)
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Get turbine data
        turbine_data = df[df["StationId"] == selected_turbine].copy()

        if turbine_data.empty:
            return [], []

        # Select relevant columns for display
        display_columns = [
            "TimeStamp",
            "operational_state",
            "state_category",
            "state_subcategory",
            "wtc_ActPower_mean",
            "wtc_AcWindSp_mean",
            "EffectiveAlarmTime",
            "wtc_PowerRed_timeon",
            "Duration 2006(s)",
            "is_producing",
            "state_reason",
        ]

        # Filter to existing columns
        available_columns = [
            col for col in display_columns if col in turbine_data.columns
        ]
        table_data = turbine_data[available_columns].copy()

        # Format timestamp
        table_data["TimeStamp"] = table_data["TimeStamp"].dt.strftime("%Y-%m-%d %H:%M")

        # Sort by timestamp (newest first)
        table_data = table_data.sort_values("TimeStamp", ascending=False)

        # Define columns for DataTable
        columns = [
            {"name": "Time", "id": "TimeStamp", "type": "text"},
            {"name": "State", "id": "state_category", "type": "text"},
            {"name": "Subcategory", "id": "state_subcategory", "type": "text"},
            {
                "name": "Power (kW)",
                "id": "wtc_ActPower_mean",
                "type": "numeric",
                "format": {"specifier": ".1f"},
            },
            {
                "name": "Wind (m/s)",
                "id": "wtc_AcWindSp_mean",
                "type": "numeric",
                "format": {"specifier": ".1f"},
            },
            {
                "name": "Alarm (s)",
                "id": "EffectiveAlarmTime",
                "type": "numeric",
                "format": {"specifier": ".0f"},
            },
            {
                "name": "Ext Curt (s)",
                "id": "wtc_PowerRed_timeon",
                "type": "numeric",
                "format": {"specifier": ".0f"},
            },
            {
                "name": "Int Curt (s)",
                "id": "Duration 2006(s)",
                "type": "numeric",
                "format": {"specifier": ".0f"},
            },
            {"name": "Producing", "id": "is_producing", "type": "text"},
            {"name": "Reason", "id": "state_reason", "type": "text"},
        ]

        return columns, table_data.to_dict("records")

    except Exception as e:
        return [], []
