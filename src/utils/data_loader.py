"""
Data loading and preprocessing module for wind farm turbine data.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict
import pickle
import os
from datetime import datetime

from .config import (
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
    MAX_ADJACENT_TURBINES,
    ADJACENCY_DISTANCE_THRESHOLD,
)


class DataLoader:
    """Handles loading and preprocessing of wind farm turbine data."""

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.layout_data: Optional[pd.DataFrame] = None
        self.data_loaded = False
        self.layout_loaded = False

    def load_pkl_data(self, file_path: str) -> Tuple[bool, str]:
        """
        Load turbine data from a pickle file.

        Args:
            file_path: Path to the .pkl file

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"

            if not file_path.lower().endswith((".pkl", ".pickle")):
                return False, "File must be a .pkl or .pickle file"

            # Load the pickle file
            with open(file_path, "rb") as f:
                data = pickle.load(f)

            # Convert to DataFrame if it's not already
            if not isinstance(data, pd.DataFrame):
                return False, "Pickle file must contain a pandas DataFrame"

            # Validate required columns
            missing_cols = [col for col in REQUIRED_COLUMNS if col not in data.columns]
            if missing_cols:
                return False, f"Missing required columns: {', '.join(missing_cols)}"

            # Store the data
            self.data = data.copy()

            # Preprocess the data
            success, message = self._preprocess_data()
            if not success:
                return False, f"Data preprocessing failed: {message}"

            self.data_loaded = True
            return (
                True,
                f"Successfully loaded {len(self.data)} records from {len(self.data['StationId'].unique())} turbines",
            )

        except Exception as e:
            return False, f"Error loading file: {str(e)}"

    def load_layout_data(self, file_path: str) -> Tuple[bool, str]:
        """
        Load wind farm layout data from a CSV file.

        Args:
            file_path: Path to the CSV file with columns: StationId, X-Coordinate, Y-Coordinate

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"

            if not file_path.lower().endswith(".csv"):
                return False, "Layout file must be a CSV file"

            # Load the CSV file
            layout_data = pd.read_csv(file_path)

            # Validate required columns for layout
            required_layout_cols = ["StationId", "X-Coordinate", "Y-Coordinate"]
            missing_cols = [
                col for col in required_layout_cols if col not in layout_data.columns
            ]
            if missing_cols:
                return (
                    False,
                    f"Missing required layout columns: {', '.join(missing_cols)}",
                )

            self.layout_data = layout_data.copy()
            self.layout_loaded = True

            return (
                True,
                f"Successfully loaded layout data for {len(self.layout_data)} turbines",
            )

        except Exception as e:
            return False, f"Error loading layout file: {str(e)}"

    def _preprocess_data(self) -> Tuple[bool, str]:
        """
        Preprocess the loaded data.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Convert TimeStamp to datetime
            if "TimeStamp" in self.data.columns:
                self.data["TimeStamp"] = pd.to_datetime(self.data["TimeStamp"])

            # Ensure numeric columns are properly typed
            numeric_columns = [
                "EffectiveAlarmTime",
                "Duration 2006(s)",
                "wtc_kWG1TotE_accum",
                "wtc_ActPower_mean",
                "wtc_ActPower_min",
                "wtc_ActPower_max",
                "wtc_AcWindSp_mean",
                "wtc_ActualWindDirection_mean",
                "wtc_PowerRed_timeon",
            ]

            for col in numeric_columns:
                if col in self.data.columns:
                    self.data[col] = pd.to_numeric(self.data[col], errors="coerce")

            # Handle metmast columns if they exist
            metmast_cols = [col for col in OPTIONAL_COLUMNS if col in self.data.columns]
            for col in metmast_cols:
                self.data[col] = pd.to_numeric(self.data[col], errors="coerce")

            # Sort by StationId and TimeStamp
            self.data = self.data.sort_values(["StationId", "TimeStamp"]).reset_index(
                drop=True
            )

            # Add derived columns
            self.data["Date"] = self.data["TimeStamp"].dt.date
            self.data["Hour"] = self.data["TimeStamp"].dt.hour

            return True, "Data preprocessing completed successfully"

        except Exception as e:
            return False, f"Preprocessing error: {str(e)}"

    def get_turbine_list(self) -> List[str]:
        """Get list of unique turbine IDs."""
        if not self.data_loaded:
            return []
        return sorted(self.data["StationId"].unique().tolist())

    def get_time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get the time range of the loaded data."""
        if not self.data_loaded:
            return None, None
        return self.data["TimeStamp"].min(), self.data["TimeStamp"].max()

    def filter_data_by_time(
        self, start_time: datetime, end_time: datetime
    ) -> pd.DataFrame:
        """
        Filter data by time range.

        Args:
            start_time: Start datetime
            end_time: End datetime

        Returns:
            Filtered DataFrame
        """
        if not self.data_loaded:
            return pd.DataFrame()

        mask = (self.data["TimeStamp"] >= start_time) & (
            self.data["TimeStamp"] <= end_time
        )
        return self.data[mask].copy()

    def get_turbine_data(
        self,
        station_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get data for a specific turbine.

        Args:
            station_id: Turbine ID
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Filtered DataFrame for the turbine
        """
        if not self.data_loaded:
            return pd.DataFrame()

        turbine_data = self.data[self.data["StationId"] == station_id].copy()

        if start_time and end_time:
            mask = (turbine_data["TimeStamp"] >= start_time) & (
                turbine_data["TimeStamp"] <= end_time
            )
            turbine_data = turbine_data[mask]

        return turbine_data

    def get_adjacent_turbines(self, station_id: str) -> List[str]:
        """
        Get adjacent turbines based on layout data or simple proximity logic.
        Uses MAX_ADJACENT_TURBINES and ADJACENCY_DISTANCE_THRESHOLD from config.

        Args:
            station_id: Target turbine ID

        Returns:
            List of adjacent turbine IDs
        """
        if self.layout_loaded and station_id in self.layout_data["StationId"].values:
            # Use layout data for spatial proximity
            target_row = self.layout_data[
                self.layout_data["StationId"] == station_id
            ].iloc[0]
            target_x, target_y = target_row["X-Coordinate"], target_row["Y-Coordinate"]

            # Calculate distances
            other_turbines = self.layout_data[
                self.layout_data["StationId"] != station_id
            ].copy()
            other_turbines["distance"] = np.sqrt(
                (other_turbines["X-Coordinate"] - target_x) ** 2
                + (other_turbines["Y-Coordinate"] - target_y) ** 2
            )

            # Filter by distance threshold
            adjacent_within_distance = other_turbines[
                other_turbines["distance"] <= ADJACENCY_DISTANCE_THRESHOLD
            ]

            # Return closest turbines up to the configured max count
            closest = adjacent_within_distance.nsmallest(
                MAX_ADJACENT_TURBINES, "distance"
            )
            return closest["StationId"].tolist()
        else:
            # Fallback: use simple string similarity or sequential IDs
            all_turbines = self.get_turbine_list()
            if station_id not in all_turbines:
                return []

            # Simple approach: return turbines with similar IDs
            try:
                # Try to extract numeric part and find nearby numbers
                import re

                match = re.search(r"(\d+)", station_id)
                if match:
                    base_num = int(match.group(1))
                    adjacent = []
                    for turbine in all_turbines:
                        if turbine != station_id:
                            turbine_match = re.search(r"(\d+)", turbine)
                            if turbine_match:
                                turbine_num = int(turbine_match.group(1))
                                if abs(turbine_num - base_num) <= MAX_ADJACENT_TURBINES:
                                    adjacent.append(turbine)
                    return adjacent[:MAX_ADJACENT_TURBINES]
            except:
                pass

            # Final fallback: return first few turbines
            other_turbines = [t for t in all_turbines if t != station_id]
            return other_turbines[:MAX_ADJACENT_TURBINES]

    def get_metmast_columns(self) -> List[str]:
        """Get available metmast wind speed columns."""
        if not self.data_loaded:
            return []
        return [
            col for col in self.data.columns if col.startswith("met_WindSpeedRot_mean_")
        ]

    def get_data_summary(self) -> Dict:
        """Get summary statistics of the loaded data."""
        if not self.data_loaded:
            return {}

        summary = {
            "total_records": len(self.data),
            "unique_turbines": len(self.data["StationId"].unique()),
            "time_range": self.get_time_range(),
            "data_columns": list(self.data.columns),
            "metmast_columns": self.get_metmast_columns(),
            "layout_available": self.layout_loaded,
        }

        return summary
