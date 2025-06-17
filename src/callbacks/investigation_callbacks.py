"""
Investigation panel callbacks for detailed turbine analysis.
"""
import logging # Add logging
from dash import Input, Output, State, callback, ctx, html
import pandas as pd
from datetime import timedelta
import plotly.graph_objects as go

# Import the global data_loader instance
from ..callbacks.main_callbacks import data_loader
from ..layouts.investigation_panel import (
    create_power_analysis_chart,
    create_wind_comparison_chart,
    create_alarm_curtailment_chart,
)
from ..utils.config import OPERATIONAL_STATES

logger = logging.getLogger(__name__) # Add a logger for this module

@callback(
    [
        Output("selected-turbine-status", "children"),
        Output("selected-turbine-metrics", "children"),
    ],
    [Input("selected-turbine-store", "data")], # This is the selected_turbine_id
    [
        State("date-picker-range", "start_date"),
        State("date-picker-range", "end_date")
    ]
)
def update_turbine_status_and_metrics(selected_turbine_id, start_date_str, end_date_str):
    """Update selected turbine status and key metrics."""
    if not selected_turbine_id or not start_date_str or not end_date_str:
        return "No turbine selected", "No data available"

    try:
        if not data_loader.data_loaded or data_loader.data is None:
            return "Overall data not loaded", "No data available"

        turbine_full_history_df = data_loader.get_turbine_data(selected_turbine_id)
        if turbine_full_history_df.empty:
            return f"No historical data for turbine {selected_turbine_id}", "No data available"

        if not pd.api.types.is_datetime64_any_dtype(turbine_full_history_df['TimeStamp']):
            turbine_full_history_df['TimeStamp'] = pd.to_datetime(turbine_full_history_df['TimeStamp'])

        start_datetime = pd.to_datetime(start_date_str)
        end_datetime = pd.to_datetime(end_date_str) + timedelta(days=1)

        turbine_data_in_range = turbine_full_history_df[
            (turbine_full_history_df["TimeStamp"] >= start_datetime) &
            (turbine_full_history_df["TimeStamp"] < end_datetime)
        ]

        if turbine_data_in_range.empty:
            return f"No data for {selected_turbine_id} in selected date range", "No data available"

        latest_data = turbine_data_in_range.sort_values(by="TimeStamp", ascending=False).iloc[0]

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
        logger.error(f"Error in update_turbine_status_and_metrics: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", "Error loading metrics"


@callback(
    Output("power-analysis-chart", "figure"),
    [
        Input("selected-turbine-store", "data"), # selected_turbine_id
        Input("power-24h", "n_clicks"),
        Input("power-7d", "n_clicks"),
        Input("power-30d", "n_clicks"),
        Input("adjacent-turbines-selector", "value"),
    ],
    [
        State("date-picker-range", "start_date"), # Use main date pickers for overall range
        State("date-picker-range", "end_date")
    ]
)
def update_power_analysis_chart(
    selected_turbine_id, btn_24h, btn_7d, btn_30d, adjacent_turbine_ids,
    filter_start_date_str, filter_end_date_str
):
    """Update power analysis chart."""
    if not selected_turbine_id:
        return go.Figure()

    if not data_loader.data_loaded or data_loader.data is None:
        return go.Figure().add_annotation(text="Overall data not loaded", showarrow=False)

    try:
        # Fetch all data for the selected turbine and adjacent ones
        df_all_turbines = data_loader.data # Full dataset
        if not pd.api.types.is_datetime64_any_dtype(df_all_turbines['TimeStamp']):
            df_all_turbines['TimeStamp'] = pd.to_datetime(df_all_turbines['TimeStamp'])

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

        # The chart's time range should be relative to the latest data point of the selected turbine
        # within the dashboard's overall filtered date range.
        selected_turbine_history = df_all_turbines[df_all_turbines["StationId"] == selected_turbine_id]
        if selected_turbine_history.empty:
            return go.Figure().add_annotation(text=f"No data for turbine {selected_turbine_id}", showarrow=False)

        # Determine the end_time for the chart (latest timestamp for the turbine)
        chart_end_time = selected_turbine_history["TimeStamp"].max()
        chart_start_time = chart_end_time - timedelta(hours=hours)

        # Filter data for the chart's specific time window
        chart_time_filtered_df = df_all_turbines[
            (df_all_turbines["TimeStamp"] >= chart_start_time) & (df_all_turbines["TimeStamp"] <= chart_end_time)
        ]

        turbine_data_for_chart = chart_time_filtered_df[
            chart_time_filtered_df["StationId"] == selected_turbine_id
        ]

        # Get adjacent turbine data
        adjacent_data = None
        if adjacent_turbine_ids:
            adjacent_data = chart_time_filtered_df[
                chart_time_filtered_df["StationId"].isin(adjacent_turbine_ids)
            ]

        # Create chart
        fig = create_power_analysis_chart(turbine_data_for_chart, adjacent_data, hours)

        return fig

    except Exception as e:
        logger.error(f"Error in update_power_analysis_chart: {str(e)}", exc_info=True)
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

# IMPORTANT: You'll need to apply a similar refactoring pattern (as shown in update_power_analysis_chart)
# to the following investigation panel callbacks:
# - update_wind_comparison_chart
# - update_alarm_curtailment_chart
# - update_detailed_data_table
#
# They all need to:
# 1. Remove `State("filtered-data-store", "data")`.
# 2. Potentially use `State("date-picker-range", "start_date")` and `State("date-picker-range", "end_date")`
#    if they need to respect the main dashboard's date filter, or calculate their own time windows
#    based on button clicks (24h, 7d, 30d) relative to the turbine's latest data.
# 3. Fetch data directly from `data_loader.data` using `selected_turbine_id` and then filter/process it.
# 4. Handle cases where `data_loader.data` might not be loaded.


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
    [
        State("date-picker-range", "start_date"),
        State("date-picker-range", "end_date")
    ]
)
def update_wind_comparison_chart(
    selected_turbine_id, # Renamed for clarity and consistency
    btn_24h,
    btn_7d,
    btn_30d,
    adjacent_turbine_ids, # Renamed for clarity and consistency
    metmast_columns,
    filter_start_date_str, # Correctly mapped from State
    filter_end_date_str    # Correctly mapped from State
):
    """Update wind speed comparison chart."""
    if not selected_turbine_id:
        return go.Figure()
    
    if not data_loader.data_loaded or data_loader.data is None:
        return go.Figure().add_annotation(text="Overall data not loaded", showarrow=False)
    # Note: filter_start_date_str and filter_end_date_str are available if needed to constrain chart context

    try:
        df_all_turbines = data_loader.data
        if not pd.api.types.is_datetime64_any_dtype(df_all_turbines['TimeStamp']):
            df_all_turbines['TimeStamp'] = pd.to_datetime(df_all_turbines['TimeStamp'])
        
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

        selected_turbine_history = df_all_turbines[df_all_turbines["StationId"] == selected_turbine_id]
        if selected_turbine_history.empty:
            return go.Figure().add_annotation(text=f"No data for turbine {selected_turbine_id}", showarrow=False)

        chart_end_time = selected_turbine_history["TimeStamp"].max()
        chart_start_time = chart_end_time - timedelta(hours=hours)

        chart_time_filtered_df = df_all_turbines[
            (df_all_turbines["TimeStamp"] >= chart_start_time) & (df_all_turbines["TimeStamp"] <= chart_end_time)
        ]

        turbine_data_for_chart = chart_time_filtered_df[
            chart_time_filtered_df["StationId"] == selected_turbine_id
        ]

        # Get adjacent turbine data
        adjacent_data = None
        if adjacent_turbine_ids:
            adjacent_data = chart_time_filtered_df[
                chart_time_filtered_df["StationId"].isin(adjacent_turbine_ids)
            ]

        # Get metmast data
        metmast_data = None
        if metmast_columns:
            # Metmast data should also be filtered by the chart's time window
            metmast_data_for_chart = chart_time_filtered_df.set_index("TimeStamp")[
                metmast_columns
            ].dropna()
            metmast_data = metmast_data_for_chart # Assign to the variable used by create_wind_comparison_chart

        # Create chart
        fig = create_wind_comparison_chart(turbine_data_for_chart, adjacent_data, metmast_data)

        return fig

    except Exception as e:
        logger.error(f"Error in update_wind_comparison_chart: {str(e)}", exc_info=True)
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
    [Input("selected-turbine-store", "data")], # selected_turbine_id
    [
        State("date-picker-range", "start_date"),
        State("date-picker-range", "end_date")
    ]
)
def update_alarm_curtailment_chart(selected_turbine_id, filter_start_date_str, filter_end_date_str):
    """Update alarm and curtailment chart."""
    if not selected_turbine_id or not filter_start_date_str or not filter_end_date_str:
        return go.Figure()

    if not data_loader.data_loaded or data_loader.data is None:
        return go.Figure().add_annotation(text="Overall data not loaded", showarrow=False)

    try:
        turbine_full_history_df = data_loader.get_turbine_data(selected_turbine_id)
        if turbine_full_history_df.empty:
            return go.Figure().add_annotation(text=f"No data for turbine {selected_turbine_id}", showarrow=False)

        if not pd.api.types.is_datetime64_any_dtype(turbine_full_history_df['TimeStamp']):
            turbine_full_history_df['TimeStamp'] = pd.to_datetime(turbine_full_history_df['TimeStamp'])

        start_datetime = pd.to_datetime(filter_start_date_str)
        end_datetime = pd.to_datetime(filter_end_date_str) + timedelta(days=1)

        turbine_data = turbine_full_history_df[
            (turbine_full_history_df["TimeStamp"] >= start_datetime) &
            (turbine_full_history_df["TimeStamp"] < end_datetime)
        ]
        if turbine_data.empty:
            return go.Figure().add_annotation(text=f"No data for {selected_turbine_id} in selected date range", showarrow=False)

        # Create chart
        fig = create_alarm_curtailment_chart(turbine_data)

        return fig

    except Exception as e:
        logger.error(f"Error in update_alarm_curtailment_chart: {str(e)}", exc_info=True)
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )


@callback(
    [Output("detailed-data-table", "columns"), Output("detailed-data-table", "data")],
    [Input("selected-turbine-store", "data")], # selected_turbine_id
    [
        State("date-picker-range", "start_date"),
        State("date-picker-range", "end_date")
    ]
)
def update_detailed_data_table(selected_turbine_id, filter_start_date_str, filter_end_date_str):
    """Update detailed data table for selected turbine."""
    if not selected_turbine_id or not filter_start_date_str or not filter_end_date_str:
        return [], []

    if not data_loader.data_loaded or data_loader.data is None:
        return [], []

    try:
        turbine_full_history_df = data_loader.get_turbine_data(selected_turbine_id)
        if turbine_full_history_df.empty:
            return [], []

        if not pd.api.types.is_datetime64_any_dtype(turbine_full_history_df['TimeStamp']):
            turbine_full_history_df['TimeStamp'] = pd.to_datetime(turbine_full_history_df['TimeStamp'])

        start_datetime = pd.to_datetime(filter_start_date_str)
        end_datetime = pd.to_datetime(filter_end_date_str) + timedelta(days=1)

        # Filter data for the selected turbine within the dashboard's date range
        df = turbine_full_history_df[
            (turbine_full_history_df["TimeStamp"] >= start_datetime) &
            (turbine_full_history_df["TimeStamp"] < end_datetime)
        ]

        # Get turbine data
        turbine_data = df.copy() # df is already filtered for the selected turbine and date range

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
        logger.error(f"Error in update_detailed_data_table: {str(e)}", exc_info=True)
        return [], []
