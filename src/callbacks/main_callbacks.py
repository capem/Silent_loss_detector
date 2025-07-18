"""
Main dashboard callbacks for data loading, filtering, and turbine selection.
"""

from dash import Input, Output, State, callback, ctx
import base64
import io
import logging
import os
from datetime import timedelta
from typing import Tuple
import pandas as pd

from ..utils.data_loader import DataLoader
from ..utils.operational_state import OperationalStateClassifier
from ..layouts.main_dashboard import create_data_summary_display
from ..utils.config import OPERATIONAL_STATES
from ..utils.logging_utils import (
    log_callback_execution,
    log_file_operation,  # This will now be used
    log_user_action,
    log_error_with_context,
    log_data_summary
)


# Global data loader instance
data_loader = DataLoader()
state_classifier = OperationalStateClassifier(data_loader)

# Helper function for processing uploaded data file
@log_file_operation
def _save_uploaded_file(decoded_content: bytes, filename: str) -> Tuple[bool, str, str]:
    """
    Saves decoded file content to a temporary file.
    Returns success status, message, and the path to the temporary file.
    """
    logger = logging.getLogger("callbacks.data_upload_helper")
    temp_path = f"temp_{filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(decoded_content)
        logger.debug(f"Temporary data file created: {temp_path}")
        return True, f"File {filename} uploaded successfully.", temp_path
    except Exception as e:
        logger.error(f"Error saving temporary file: {e}", exc_info=True)
        return False, f"Error saving file: {e}", ""

def _execute_calculation(temp_path: str, data_loader_instance: DataLoader, state_classifier_instance: OperationalStateClassifier):
    """
    Loads data from a temporary file, classifies states, and cleans up the file.
    """
    logger = logging.getLogger("callbacks.calculation_helper")
    try:
        success, message = data_loader_instance.load_pkl_data(temp_path)
        if success:
            logger.info("Data loaded successfully, starting classification")
            classified_data = state_classifier_instance.classify_turbine_states(data_loader_instance.data)
            data_loader_instance.data = classified_data
            log_data_summary(classified_data, "operational state classification")
            summary = data_loader_instance.get_data_summary()
            logger.info(f"Data summary generated: {summary.get('total_records', 0)} records")
            return True, "Calculation complete.", summary
        else:
            logger.error(f"Data loading failed: {message}")
            return False, message, {}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.debug(f"Temporary data file {temp_path} cleaned up")

# Helper function for processing uploaded layout file
@log_file_operation
def _process_uploaded_layout_file(decoded_content: bytes, filename: str, data_loader_instance: DataLoader):
    """Helper function to process decoded layout file content."""
    logger = logging.getLogger("callbacks.layout_upload_helper")
    try:
        layout_df = pd.read_csv(io.StringIO(decoded_content.decode("utf-8")))
        log_data_summary(layout_df, "layout file load (processed by helper)")

        required_layout_cols = ["StationId", "X-Coordinate", "Y-Coordinate"]
        missing_cols = [col for col in required_layout_cols if col not in layout_df.columns]
        if missing_cols:
            error_msg = f"Missing required layout columns: {', '.join(missing_cols)}"
            logger.error(error_msg)
            return False, error_msg, None

        data_loader_instance.layout_data = layout_df.copy()
        data_loader_instance.layout_loaded = True
        message = f"Successfully loaded layout data for {len(layout_df)} turbines"
        logger.info(message)
        return True, message, layout_df
    except Exception as e:
        logger.error(f"Error processing layout file in helper: {str(e)}", exc_info=True)
        return False, f"Error processing layout file: {str(e)}", None

@callback(
    [
        Output("upload-status", "children"),
        Output("temp-file-path-store", "data"),
        Output("run-calculation-btn", "disabled"),
    ],
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")],
)
@log_callback_execution
def handle_data_upload(contents, filename):
    """Handle main data file upload by saving it to a temporary location."""
    logger = logging.getLogger("callbacks.data_upload")
    if contents is None:
        logger.debug("No file contents provided")
        return "No file selected.", "", True

    try:
        log_user_action("File upload started", {"filename": filename})
        logger.info(f"Processing file upload: {filename}")
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        logger.debug(f"File decoded, size: {len(decoded)} bytes")

        success, message, temp_path = _save_uploaded_file(decoded, filename)

        if success:
            log_user_action("File upload completed successfully", {"filename": filename})
            return f"✅ {filename} uploaded. Ready for calculation.", temp_path, False
        else:
            log_user_action("File upload failed", {"filename": filename, "error": message})
            return f"❌ {message}", "", True

    except Exception as e:
        logger.error(f"Exception during data file upload callback: {str(e)}", exc_info=True)
        log_error_with_context(e, {"filename": filename, "operation": "data_upload_callback"})
        log_user_action("File upload error", {"filename": filename, "error": str(e)})
        return f"❌ Error: {str(e)}", "", True


@callback(
    [
        Output("data-store", "data"),
        Output("data-summary", "children"),
    ],
    [Input("run-calculation-btn", "n_clicks")],
    [State("temp-file-path-store", "data")],
    prevent_initial_call=True,
)
@log_callback_execution
def run_calculation(n_clicks, temp_path):
    """Triggered by the 'Run Calculation' button to process the uploaded data."""
    logger = logging.getLogger("callbacks.run_calculation")
    if not n_clicks or not temp_path:
        logger.debug("Calculation run skipped: no clicks or temp_path.")
        return {}, "No data loaded"

    try:
        log_user_action("Calculation started", {"temp_path": temp_path})
        logger.info(f"Starting calculation for {temp_path}")

        success, message, summary = _execute_calculation(temp_path, data_loader, state_classifier)

        if success:
            from datetime import datetime
            store_payload = {
                "summary": summary,
                "data_loaded_timestamp": datetime.now().isoformat()
            }
            record_count = summary.get('total_records', 0)
            turbine_count = summary.get('unique_turbines', 0)
            log_user_action("Calculation completed successfully", {
                "records": record_count,
                "turbines": turbine_count
            })
            return store_payload, create_data_summary_display(summary)
        else:
            log_user_action("Calculation failed", {"error": message})
            return {}, "Failed to process data"

    except Exception as e:
        logger.error(f"Exception during calculation callback: {str(e)}", exc_info=True)
        log_error_with_context(e, {"temp_path": temp_path, "operation": "run_calculation_callback"})
        log_user_action("Calculation error", {"error": str(e)})
        return {}, "Error processing data"


@callback(
    [Output("layout-upload-status", "children"), Output("layout-store", "data")],
    [Input("upload-layout", "contents")],
    [State("upload-layout", "filename")],
)
@log_callback_execution
def handle_layout_upload(contents, filename):
    """Handle layout file upload."""
    logger = logging.getLogger("callbacks.layout_upload")

    if contents is None:
        logger.debug("No layout file contents provided")
        return "", {}

    try:
        log_user_action("Layout file upload started", {"filename": filename})
        logger.info(f"Processing layout file upload: {filename}")

        # Decode the uploaded file
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        logger.debug(f"Layout file decoded, size: {len(decoded)} bytes")

        # Call helper function for layout file processing
        success, message, layout_df = _process_uploaded_layout_file(
            decoded, filename, data_loader
        )

        if success:
            log_user_action("Layout file upload completed", {
                "filename": filename,
                "turbines": len(layout_df) if layout_df is not None else 0
            })
            return f"✅ {message}", layout_df.to_dict("records") if layout_df is not None else {}
        else:
            action_details = {"filename": filename, "error": message}
            if "Missing required layout columns" in message:
                log_user_action("Layout file validation failed", action_details)
            else:
                log_user_action("Layout file processing error", action_details)
            return f"❌ {message}", {}

    except Exception as e:
        # This catches errors outside the helper, e.g., base64 decoding
        logger.error(f"Exception during layout file upload callback: {str(e)}", exc_info=True)
        log_error_with_context(e, {"filename": filename, "operation": "layout_upload_callback"})
        log_user_action("Layout file upload error", {"filename": filename, "error": str(e)})
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
    """Update date range based on button clicks or data loading.
       Defaults to full data range (min to max) when data is first loaded.
       Ensures NaT values from summary are handled gracefully.
    """
    if not data_store or "summary" not in data_store:
        return None, None

    summary = data_store.get("summary", {})
    time_range_str_tuple = summary.get("time_range")

    if not time_range_str_tuple or not time_range_str_tuple[0] or not time_range_str_tuple[1]:
        return None, None

    try:
        min_ts_from_data = pd.to_datetime(time_range_str_tuple[0], errors='coerce')
        max_ts_from_data = pd.to_datetime(time_range_str_tuple[1], errors='coerce')
    except Exception: # Catch any parsing errors
        return None, None

    if pd.isna(max_ts_from_data):
        return None, None

    end_date_dt = max_ts_from_data

    # Determine which button was clicked
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    is_data_load_trigger = any(item['prop_id'] == 'data-store.data' for item in ctx.triggered) if ctx.triggered else False

    if triggered_id == "btn-24h":
        start_date_dt = end_date_dt - timedelta(hours=24)
    elif triggered_id == "btn-7d":
        start_date_dt = end_date_dt - timedelta(days=7)
    elif triggered_id == "btn-30d":
        start_date_dt = end_date_dt - timedelta(days=30)
    elif triggered_id == "btn-all":
        if pd.isna(min_ts_from_data):
            return None, None
        start_date_dt = min_ts_from_data
    elif is_data_load_trigger and (not triggered_id or not triggered_id.startswith("btn-")):
        # Default to full data range when data is first loaded and no specific button was the primary trigger
        if pd.isna(min_ts_from_data):
            return None, None
        start_date_dt = min_ts_from_data
    else:
        # Fallback or if a button was clicked (already handled above)
        # If triggered_id is a button, it's fine. If not, default to full range.
        if pd.isna(min_ts_from_data):
            return None, None
        start_date_dt = min_ts_from_data

    if pd.isna(start_date_dt):
        return None, None

    return start_date_dt.date(), end_date_dt.date()


@callback(
    [
        Output("operational-state-breakdown-table", "data"),
        Output("operational-state-breakdown-table", "columns"),
    ],
    [
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("data-store", "data"),
    ],
)
def update_breakdown_table(start_date, end_date, data_store):
    """Update the operational state breakdown table based on the selected date range."""
    logger = logging.getLogger("callbacks.update_breakdown_table")
    if not data_loader.data_loaded or data_loader.data is None or data_loader.data.empty or not start_date or not end_date:
        return [], []

    try:
        df = data_loader.data
        if not pd.api.types.is_datetime64_any_dtype(df['TimeStamp']):
            df['TimeStamp'] = pd.to_datetime(df['TimeStamp'])

        start_datetime = pd.to_datetime(start_date)
        end_datetime = pd.to_datetime(end_date) + timedelta(days=1)

        filtered_df = df[
            (df["TimeStamp"] >= start_datetime) & (df["TimeStamp"] < end_datetime)
        ]

        if filtered_df.empty:
            return [], []

        # Group by turbine and operational state to count occurrences
        breakdown = filtered_df.groupby(['StationId', 'operational_state']).size().reset_index(name='count')
        
        # Pivot the table to have states as columns
        pivot_table = breakdown.pivot(index='StationId', columns='operational_state', values='count').fillna(0).astype(int)
        
        # Add a total column
        pivot_table['Total'] = pivot_table.sum(axis=1)
        
        # Reset index to make StationId a column again
        pivot_table.reset_index(inplace=True)

        # Prepare columns for DataTable
        columns = [{"name": "Station ID", "id": "StationId"}]
        for state_key, state_info in OPERATIONAL_STATES.items():
            if state_key in pivot_table.columns:
                columns.append({"name": state_info['name'], "id": state_key})
        columns.append({"name": "Total Occurrences", "id": "Total"})
        
        return pivot_table.to_dict('records'), columns

    except Exception as e:
        logger.error(f"Error in update_breakdown_table: {str(e)}", exc_info=True)
        return [], []


@callback(
    [
        Output("selected-turbine-store", "data"),
        Output("investigation-panel", "children"),
        Output("investigation-panel", "style"),
    ],
    [Input("operational-state-breakdown-table", "selected_rows")],
    [State("operational-state-breakdown-table", "data")],
    prevent_initial_call=True,
)
@log_callback_execution
def handle_turbine_selection(selected_rows, table_data):
    """Handle turbine selection and show/hide investigation panel."""
    from ..layouts.investigation_panel import create_investigation_panel_layout

    logger = logging.getLogger("callbacks.turbine_selection")

    if not selected_rows or not table_data:
        logger.debug("No turbine selected or no table data available")
        return None, [], {"display": "none"}

    try:
        # Get selected turbine
        selected_turbine = table_data[selected_rows[0]]["StationId"]
        logger.info(f"Turbine selected for investigation: {selected_turbine}")

        log_user_action("Turbine selected for investigation", {
            "turbine_id": selected_turbine,
            "row_index": selected_rows[0]
        })

        # Create investigation panel
        panel_layout = create_investigation_panel_layout(selected_turbine)
        logger.debug(f"Investigation panel created for turbine: {selected_turbine}")

        return (selected_turbine, panel_layout, {"display": "block"})

    except Exception as e:
        logger.error(f"Error handling turbine selection: {str(e)}", exc_info=True)
        log_error_with_context(e, {
            "selected_rows": selected_rows,
            "operation": "turbine_selection"
        })
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
    [State('filter-params-store', 'data')], # Changed from filtered-data-store
    prevent_initial_call=True
)
def export_data(n_clicks, filter_params):
    """Export filtered data (latest states within date range) to CSV."""
    logger = logging.getLogger("callbacks.export_data")
    if not n_clicks or not filter_params:
        return "📊 Export Data"

    if not data_loader.data_loaded or data_loader.data is None or data_loader.data.empty:
        logger.warning("Export attempted but no data loaded in data_loader.")
        return "❌ No data to export"

    start_date_str = filter_params.get("start_date")
    end_date_str = filter_params.get("end_date")
    # visible_turbine_ids = filter_params.get("visible_turbine_ids") # Could be used for more precise export

    if not start_date_str or not end_date_str:
        logger.warning("Export attempted but date range not found in filter_params.")
        return "❌ Date range not set"

    try:
        df_to_export = data_loader.data.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_to_export['TimeStamp']):
            df_to_export['TimeStamp'] = pd.to_datetime(df_to_export['TimeStamp'])

        start_datetime = pd.to_datetime(start_date_str)
        end_datetime = pd.to_datetime(end_date_str) + timedelta(days=1)

        # Filter by date range
        df_filtered_by_date = df_to_export[
            (df_to_export["TimeStamp"] >= start_datetime) & (df_to_export["TimeStamp"] < end_datetime)
        ]

        if df_filtered_by_date.empty:
            return "ℹ️ No data in selected range to export"

        # For simplicity, exporting all columns of the latest states, similar to turbine-table logic
        # If you need all records, not just latest states, remove the groupby().last()
        latest_states_to_export = df_filtered_by_date.loc[df_filtered_by_date.groupby("StationId")["TimeStamp"].idxmax()]

        from datetime import datetime
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"turbine_data_export_{timestamp_str}.csv"
        latest_states_to_export.to_csv(filename, index=False)
        logger.info(f"Data exported successfully to {filename}")
        return f"✅ Exported to {filename}"

    except Exception as e:
        logger.error(f"Error during data export: {str(e)}", exc_info=True)
        return f"❌ Export failed: {str(e)}"