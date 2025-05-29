"""
Main dashboard callbacks for data loading, filtering, and turbine selection.
"""

from dash import Input, Output, State, callback, ctx
import pandas as pd
import base64
import io
from datetime import timedelta

from ..utils.data_loader import DataLoader
from ..utils.operational_state import OperationalStateClassifier
from ..layouts.main_dashboard import (
    create_state_summary_cards,
    create_data_summary_display,
)
from ..utils.config import OPERATIONAL_STATES


# Global data loader instance
data_loader = DataLoader()
state_classifier = OperationalStateClassifier(data_loader)


@callback(
    [
        Output("upload-status", "children"),
        Output("data-store", "data"),
        Output("data-summary", "children"),
    ],
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")],
)
def handle_data_upload(contents, filename):
    """Handle main data file upload."""
    if contents is None:
        return "", {}, "No data loaded"

    try:
        # Decode the uploaded file
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # Save temporarily and load
        temp_path = f"temp_{filename}"
        with open(temp_path, "wb") as f:
            f.write(decoded)

        # Load using data loader
        success, message = data_loader.load_pkl_data(temp_path)

        # Clean up temp file
        import os

        if os.path.exists(temp_path):
            os.remove(temp_path)

        if success:
            # Classify operational states
            classified_data = state_classifier.classify_turbine_states(data_loader.data)
            data_loader.data = classified_data

            # Get summary
            summary = data_loader.get_data_summary()

            # Convert datetime objects to strings for JSON serialization
            summary_copy = summary.copy()
            if "time_range" in summary_copy and summary_copy["time_range"]:
                time_range = summary_copy["time_range"]
                if time_range[0] and time_range[1]:
                    summary_copy["time_range"] = (
                        time_range[0].isoformat()
                        if hasattr(time_range[0], "isoformat")
                        else str(time_range[0]),
                        time_range[1].isoformat()
                        if hasattr(time_range[1], "isoformat")
                        else str(time_range[1]),
                    )

            # Store data with datetime conversion
            classified_data_copy = classified_data.copy()
            classified_data_copy["TimeStamp"] = classified_data_copy[
                "TimeStamp"
            ].astype(str)

            data_dict = {
                "data": classified_data_copy.to_dict("records"),
                "summary": summary_copy,
            }

            return (f"✅ {message}", data_dict, create_data_summary_display(summary))
        else:
            return f"❌ {message}", {}, "Failed to load data"

    except Exception as e:
        return f"❌ Error: {str(e)}", {}, "Error loading data"


@callback(
    [Output("layout-upload-status", "children"), Output("layout-store", "data")],
    [Input("upload-layout", "contents")],
    [State("upload-layout", "filename")],
)
def handle_layout_upload(contents, filename):
    """Handle layout file upload."""
    if contents is None:
        return "", {}

    try:
        # Decode the uploaded file
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # Read as CSV directly
        layout_df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))

        # Validate required columns for layout
        required_layout_cols = ["StationId", "X-Coordinate", "Y-Coordinate"]
        missing_cols = [
            col for col in required_layout_cols if col not in layout_df.columns
        ]
        if missing_cols:
            return f"❌ Missing required layout columns: {', '.join(missing_cols)}", {}

        # Store in data loader
        data_loader.layout_data = layout_df.copy()
        data_loader.layout_loaded = True

        message = f"Successfully loaded layout data for {len(layout_df)} turbines"
        return f"✅ {message}", layout_df.to_dict("records")

    except Exception as e:
        return f"❌ Error loading layout file: {str(e)}", {}


@callback(
    Output("date-picker-range", "start_date"),
    Output("date-picker-range", "end_date"),
    [
        Input("btn-24h", "n_clicks"),
        Input("btn-7d", "n_clicks"),
        Input("btn-30d", "n_clicks"),
        Input("btn-all", "n_clicks"),
        Input("data-store", "data"),
    ],
    prevent_initial_call=True,
)
def update_date_range(btn_24h, btn_7d, btn_30d, btn_all, data_store):
    """Update date range based on button clicks or data loading."""
    if not data_store:
        return None, None

    summary = data_store.get("summary", {})
    time_range = summary.get("time_range")

    if not time_range or not time_range[0] or not time_range[1]:
        return None, None

    # Convert string timestamps back to datetime objects
    if isinstance(time_range[0], str):
        start_time = pd.to_datetime(time_range[0])
        end_time = pd.to_datetime(time_range[1])
    else:
        start_time = time_range[0]
        end_time = time_range[1]

    # Determine which button was clicked
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    if triggered_id == "btn-24h":
        start_date = end_time - timedelta(hours=24)
    elif triggered_id == "btn-7d":
        start_date = end_time - timedelta(days=7)
    elif triggered_id == "btn-30d":
        start_date = end_time - timedelta(days=30)
    elif triggered_id == "btn-all":
        start_date = start_time
    else:
        # Default to last 24 hours when data is first loaded
        start_date = end_time - timedelta(hours=24)

    return start_date.date(), end_time.date()


@callback(
    [
        Output("filtered-data-store", "data"),
        Output("state-summary-cards", "children"),
        Output("turbine-table", "data"),
    ],
    [
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("state-filter", "value"),
        Input("data-store", "data"),
    ],
)
def update_filtered_data(start_date, end_date, state_filter, data_store):
    """Update filtered data based on date range and state filter."""
    if not data_store or not start_date or not end_date:
        return {}, "No data to display", []

    try:
        # Convert data back to DataFrame
        df = pd.DataFrame(data_store["data"])
        df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Filter by date range
        start_datetime = pd.to_datetime(start_date)
        end_datetime = pd.to_datetime(end_date) + timedelta(days=1)  # Include end date

        filtered_df = df[
            (df["TimeStamp"] >= start_datetime) & (df["TimeStamp"] < end_datetime)
        ]

        # Get latest state for each turbine
        latest_states = filtered_df.groupby("StationId").last().reset_index()

        # Filter by operational state if specified
        if state_filter and state_filter != "ALL":
            latest_states = latest_states[
                latest_states["operational_state"] == state_filter
            ]

        # Calculate state summary
        state_counts = {}
        total_turbines = len(latest_states)

        for state_key in OPERATIONAL_STATES.keys():
            count = len(latest_states[latest_states["operational_state"] == state_key])
            state_counts[state_key] = count
            state_counts[f"{state_key}_pct"] = (
                (count / total_turbines * 100) if total_turbines > 0 else 0
            )

        # Prepare table data
        table_data = latest_states[
            [
                "StationId",
                "state_category",
                "state_subcategory",
                "wtc_ActPower_mean",
                "wtc_AcWindSp_mean",
                "TimeStamp",
                "state_reason",
            ]
        ].to_dict("records")

        # Format timestamps for display
        for row in table_data:
            if row["TimeStamp"]:
                row["TimeStamp"] = pd.to_datetime(row["TimeStamp"]).strftime(
                    "%Y-%m-%d %H:%M"
                )

        return (
            filtered_df.to_dict("records"),
            create_state_summary_cards(state_counts),
            table_data,
        )

    except Exception as e:
        return {}, f"Error filtering data: {str(e)}", []


@callback(
    [
        Output("selected-turbine-store", "data"),
        Output("investigation-panel", "children"),
        Output("investigation-panel", "style"),
    ],
    [Input("turbine-table", "selected_rows")],
    [State("turbine-table", "data"), State("filtered-data-store", "data")],
    prevent_initial_call=True,
)
def handle_turbine_selection(selected_rows, table_data, filtered_data):
    """Handle turbine selection and show/hide investigation panel."""
    from ..layouts.investigation_panel import create_investigation_panel_layout

    if not selected_rows or not table_data:
        return None, [], {"display": "none"}

    try:
        # Get selected turbine
        selected_turbine = table_data[selected_rows[0]]["StationId"]

        # Create investigation panel
        panel_layout = create_investigation_panel_layout(selected_turbine)

        return (selected_turbine, panel_layout, {"display": "block"})

    except Exception as e:
        return None, f"Error: {str(e)}", {"display": "none"}


@callback(
    [
        Output("investigation-panel", "children", allow_duplicate=True),
        Output("investigation-panel", "style", allow_duplicate=True),
        Output("selected-turbine-store", "data", allow_duplicate=True),
    ],
    [Input("close-investigation", "n_clicks")],
    prevent_initial_call=True,
)
def close_investigation_panel(close_clicks):
    """Handle closing the investigation panel."""
    if close_clicks:
        return [], {"display": "none"}, None
    # Use dash exceptions to prevent updates
    from dash.exceptions import PreventUpdate

    raise PreventUpdate


@callback(
    Output("adjacent-turbines-selector", "options"),
    Output("adjacent-turbines-selector", "value"),
    [Input("selected-turbine-store", "data")],
    [State("data-store", "data")],
)
def update_adjacent_turbines_options(selected_turbine, data_store):
    """Update adjacent turbines selector options."""
    if not selected_turbine or not data_store:
        return [], []

    try:
        # Get adjacent turbines
        adjacent_turbines = data_loader.get_adjacent_turbines(selected_turbine)

        options = [
            {"label": turbine, "value": turbine} for turbine in adjacent_turbines
        ]

        # Auto-select first few
        default_selection = (
            adjacent_turbines[:3] if len(adjacent_turbines) >= 3 else adjacent_turbines
        )

        return options, default_selection

    except Exception as e:
        return [], []


@callback(
    Output("metmast-selector", "options"),
    Output("metmast-selector", "value"),
    [Input("selected-turbine-store", "data")],
    [State("data-store", "data")],
)
def update_metmast_options(selected_turbine, data_store):
    """Update metmast selector options."""
    if not selected_turbine or not data_store:
        return [], []

    try:
        # Get available metmast columns
        metmast_cols = data_loader.get_metmast_columns()

        options = []
        for col in metmast_cols:
            metmast_id = col.split("_")[-1]
            options.append({"label": f"Metmast {metmast_id}", "value": col})

        # Auto-select all available
        default_selection = metmast_cols

        return options, default_selection

    except Exception as e:
        return [], []


@callback(
    Output('export-data-btn', 'children'),
    [Input('export-data-btn', 'n_clicks')],
    [State('filtered-data-store', 'data')],
    prevent_initial_call=True
)
def export_data(n_clicks, filtered_data):
    """Export filtered data to CSV."""
    if n_clicks and filtered_data:
        try:
            # Convert to DataFrame
            df = pd.DataFrame(filtered_data)

            # Generate filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"turbine_data_export_{timestamp}.csv"

            # Export to CSV
            df.to_csv(filename, index=False)

            return f"✅ Exported to {filename}"

        except Exception as e:
            return f"❌ Export failed: {str(e)}"

    return "📊 Export Data"