"""
Investigation panel callbacks for detailed turbine analysis.
"""
import logging # Add logging
from dash import Input, Output, State, callback, html
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
    """Update selected turbine summary and analysis period metrics."""
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

        # Summary Card
        summary_content = html.Div([
            html.Div([html.Strong("Turbine ID: "), html.Span(selected_turbine_id)], className="mb-2"),
            html.Div([html.Strong("Analysis Period: "), html.Span(f"{start_datetime.strftime('%Y-%m-%d')} to {end_datetime.strftime('%Y-%m-%d')}")], className="mb-2"),
            html.Div([html.Strong("Data Points: "), html.Span(f"{len(turbine_data_in_range):,}")], className="mb-2"),
        ])

        # Metrics Card
        avg_power = turbine_data_in_range["wtc_ActPower_mean"].mean()
        avg_wind_speed = turbine_data_in_range["wtc_AcWindSp_mean"].mean()
        
        # Data Availability
        expected_points = (end_datetime - start_datetime).total_seconds() / 600  # 10-min intervals
        availability = (len(turbine_data_in_range) / expected_points) * 100 if expected_points > 0 else 0
        
        # Total Curtailment
        internal_curt = turbine_data_in_range["Duration 2006(s)"].sum() / 3600  # hours
        external_curt = turbine_data_in_range["wtc_PowerRed_timeon"].sum() / 3600 # hours
        total_curtailment = internal_curt + external_curt

        # Total Energy Production (MWh)
        # Assuming 10-minute intervals (1/6 hour)
        total_energy_mwh = (turbine_data_in_range["wtc_ActPower_mean"] * (10 / 60)).sum() / 1000


        metrics_content = html.Div([
            html.Div([html.Strong("Avg. Power Output: "), html.Span(f"{avg_power:.2f} kW")], className="mb-2"),
            html.Div([html.Strong("Avg. Wind Speed: "), html.Span(f"{avg_wind_speed:.2f} m/s")], className="mb-2"),
            html.Div([html.Strong("Data Availability: "), html.Span(f"{availability:.1f}%")], className="mb-2"),
            html.Div([html.Strong("Total Curtailment: "), html.Span(f"{total_curtailment:.1f} h")], className="mb-2"),
            html.Div([html.Strong("Total Energy: "), html.Span(f"{total_energy_mwh:.2f} MWh")], className="mb-2"),
        ])

        return summary_content, metrics_content

    except Exception as e:
        logger.error(f"Error in update_turbine_status_and_metrics: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", "Error loading metrics"


@callback(
    Output("power-analysis-chart", "figure"),
    [
        Input("selected-turbine-store", "data"), # selected_turbine_id
        Input("adjacent-turbines-selector", "value"),
        Input("date-picker-range", "start_date"), # Use main date pickers for overall range
        Input("date-picker-range", "end_date")
    ]
)
def update_power_analysis_chart(
    selected_turbine_id, adjacent_turbine_ids,
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

        # Use the main dashboard date range
        if not filter_start_date_str or not filter_end_date_str:
            return go.Figure().add_annotation(text="Please select a date range", showarrow=False)

        start_datetime = pd.to_datetime(filter_start_date_str)
        end_datetime = pd.to_datetime(filter_end_date_str) + timedelta(days=1)

        selected_turbine_history = df_all_turbines[df_all_turbines["StationId"] == selected_turbine_id]
        if selected_turbine_history.empty:
            return go.Figure().add_annotation(text=f"No data for turbine {selected_turbine_id}", showarrow=False)

        # Filter data for the selected time range
        turbine_data_for_chart = selected_turbine_history[
            (selected_turbine_history["TimeStamp"] >= start_datetime) &
            (selected_turbine_history["TimeStamp"] < end_datetime)
        ]

        if turbine_data_for_chart.empty:
            return go.Figure().add_annotation(text="No data in the selected date range", showarrow=False)

        # Get adjacent turbine data for the same time range
        adjacent_data = None
        if adjacent_turbine_ids:
            adjacent_data = df_all_turbines[
                (df_all_turbines["StationId"].isin(adjacent_turbine_ids)) &
                (df_all_turbines["TimeStamp"] >= start_datetime) &
                (df_all_turbines["TimeStamp"] < end_datetime)
            ]

        # Create chart
        fig = create_power_analysis_chart(turbine_data_for_chart, adjacent_data)

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


@callback(
    Output("wind-comparison-chart", "figure"),
    [
        Input("selected-turbine-store", "data"),
        Input("adjacent-turbines-selector", "value"),
        Input("metmast-selector", "value"),
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date")
    ]
)
def update_wind_comparison_chart(
    selected_turbine_id, # Renamed for clarity and consistency
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
        
        # Use the main dashboard date range
        if not filter_start_date_str or not filter_end_date_str:
            return go.Figure().add_annotation(text="Please select a date range", showarrow=False)

        start_datetime = pd.to_datetime(filter_start_date_str)
        end_datetime = pd.to_datetime(filter_end_date_str) + timedelta(days=1)

        selected_turbine_history = df_all_turbines[df_all_turbines["StationId"] == selected_turbine_id]
        if selected_turbine_history.empty:
            return go.Figure().add_annotation(text=f"No data for turbine {selected_turbine_id}", showarrow=False)

        # Filter data for the selected time range
        turbine_data_for_chart = selected_turbine_history[
            (selected_turbine_history["TimeStamp"] >= start_datetime) &
            (selected_turbine_history["TimeStamp"] < end_datetime)
        ]

        if turbine_data_for_chart.empty:
            return go.Figure().add_annotation(text="No data in the selected date range", showarrow=False)

        # Get adjacent turbine data for the same time range
        adjacent_data = None
        if adjacent_turbine_ids:
            adjacent_data = df_all_turbines[
                (df_all_turbines["StationId"].isin(adjacent_turbine_ids)) &
                (df_all_turbines["TimeStamp"] >= start_datetime) &
                (df_all_turbines["TimeStamp"] < end_datetime)
            ]

        # Get metmast data for the same time range
        metmast_data = None
        if metmast_columns:
            chart_time_filtered_df = df_all_turbines[
                (df_all_turbines["TimeStamp"] >= start_datetime) &
                (df_all_turbines["TimeStamp"] < end_datetime)
            ]
            # Sort by timestamp and remove duplicates to prevent loops
            chart_time_filtered_df = chart_time_filtered_df.sort_values("TimeStamp").drop_duplicates(subset=["TimeStamp"])
            metmast_data_for_chart = chart_time_filtered_df.set_index("TimeStamp")[
                metmast_columns
            ]
            # Don't use dropna() here as it removes entire rows - let individual columns handle NaN values
            metmast_data = metmast_data_for_chart

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
    [
        Input("selected-turbine-store", "data"), # selected_turbine_id
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date")
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
    [
        Input("selected-turbine-store", "data"), # selected_turbine_id
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date")
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
