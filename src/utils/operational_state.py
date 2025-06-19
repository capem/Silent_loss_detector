"""
Core operational state logic for wind turbine classification.
This module implements the logic from Spec Version 1.6, Section 3.1.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

from .config import (
    PRODUCTION_THRESHOLD_KW,
    CUT_IN_WIND_SPEED,
    ALARM_THRESHOLD_SECONDS,
    CURTAILMENT_THRESHOLD_SECONDS,
    WIND_SPEED_DEVIATION_THRESHOLD,
    OPERATIONAL_STATES,
)


class OperationalStateClassifier:
    """Classifies turbine operational states based on sensor data and context."""

    def __init__(self, data_loader):
        self.data_loader = data_loader

    def classify_turbine_states(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Classify operational states for all turbines in the dataset.

        Args:
            data: DataFrame with turbine data

        Returns:
            DataFrame with added operational state columns
        """
        result_data = data.copy()

        # Initialize state columns
        result_data["operational_state"] = "UNKNOWN"
        result_data["state_category"] = "Unknown"
        result_data["state_subcategory"] = "Unknown"
        result_data["state_reason"] = "Not classified"
        result_data["is_producing"] = False

        if data.empty:
            return data  # Return early if data is empty

        # Work on a copy to avoid modifying the original DataFrame
        # Ensure TimeStamp is datetime for grouping and comparisons
        if not pd.api.types.is_datetime64_any_dtype(data["TimeStamp"]):
            data["TimeStamp"] = pd.to_datetime(data["TimeStamp"])

        # Pre-group all data by timestamp for efficient lookup in _get_reference_wind_speeds
        all_data_grouped_by_timestamp = {
            ts: group for ts, group in data.groupby("TimeStamp")
        }

        # Cache for data_loader calls that are constant per turbine or globally
        adjacent_turbines_cache = {}
        global_metmast_columns = self.data_loader.get_metmast_columns()

        processed_groups = []
        # Sort data by StationId and TimeStamp to ensure correct temporal order for startup sequences
        # and consistent processing.
        data_sorted_for_processing = data.sort_values(["StationId", "TimeStamp"])

        for station_id, group_df_original in data_sorted_for_processing.groupby(
            "StationId", sort=False
        ):
            # Work on a copy of the group to avoid SettingWithCopyWarning on slices
            group_df = group_df_original.copy()

            # Initialize result columns for the current group
            group_df["operational_state"] = "UNCLASSIFIED"  # Default placeholder
            group_df["state_category"] = OPERATIONAL_STATES["NOT_PRODUCING_UNEXPECTED"][
                "name"
            ]  # Default to an unknown/unexpected
            group_df["state_subcategory"] = OPERATIONAL_STATES[
                "NOT_PRODUCING_UNEXPECTED"
            ]["subcategories"]["UNKNOWN_NON_PRODUCTION"]
            group_df["state_reason"] = "Pre-classification pending"
            group_df["is_producing"] = False

            # --- Vectorized Step 1: Producing ---
            producing_mask = group_df["wtc_ActPower_min"] > PRODUCTION_THRESHOLD_KW
            group_df.loc[producing_mask, "operational_state"] = "PRODUCING"
            group_df.loc[producing_mask, "state_category"] = OPERATIONAL_STATES[
                "PRODUCING"
            ]["name"]
            group_df.loc[producing_mask, "state_subcategory"] = OPERATIONAL_STATES[
                "PRODUCING"
            ]["subcategory"]
            # Ensure wtc_ActPower_min is float for formatting; NaNs in wtc_ActPower_min make producing_mask False
            power_val_str = (
                group_df.loc[producing_mask, "wtc_ActPower_min"].round(1).astype(str)
            )
            group_df.loc[producing_mask, "state_reason"] = (
                "Minimum Power output: " + power_val_str + " kW"
            )
            group_df.loc[producing_mask, "is_producing"] = True

            # --- Vectorized Step 2: Alarm (only for non-producing rows) ---
            # Comparisons with NaN yield False, so alarm_condition_mask handles NaNs in EffectiveAlarmTime
            alarm_condition_mask = (
                group_df["EffectiveAlarmTime"] > ALARM_THRESHOLD_SECONDS
            )
            alarm_mask = (~producing_mask) & alarm_condition_mask

            group_df.loc[alarm_mask, "operational_state"] = "NOT_PRODUCING_EXPLAINED"
            group_df.loc[alarm_mask, "state_category"] = OPERATIONAL_STATES[
                "NOT_PRODUCING_EXPLAINED"
            ]["name"]
            group_df.loc[alarm_mask, "state_subcategory"] = OPERATIONAL_STATES[
                "NOT_PRODUCING_EXPLAINED"
            ]["subcategories"]["ALARM_ACTIVE"]
            alarm_time_str = (
                group_df.loc[alarm_mask, "EffectiveAlarmTime"].round(0).astype(str)
            )
            # 'UK Text' is a required column, fillna for safety in string concat
            uk_text_str = group_df.loc[alarm_mask, "UK Text"].fillna("N/A").astype(str)
            group_df.loc[alarm_mask, "state_reason"] = (
                "Active alarm: " + alarm_time_str + "s - " + uk_text_str
            )
            group_df.loc[alarm_mask, "is_producing"] = False

            # --- Vectorized Step 3: Curtailment (only for non-producing and non-alarm rows) ---
            curtailment_external_cond_mask = (
                group_df["wtc_PowerRed_timeon"] > CURTAILMENT_THRESHOLD_SECONDS
            )
            curtailment_internal_cond_mask = (
                group_df["Duration 2006(s)"] > CURTAILMENT_THRESHOLD_SECONDS
            )
            any_curtailment_cond_mask = (
                curtailment_external_cond_mask | curtailment_internal_cond_mask
            )
            curtailment_mask = (
                (~producing_mask) & (~alarm_mask) & any_curtailment_cond_mask
            )

            # Determine reason string vectorially for curtailment
            curtailment_reason_series = pd.Series("", index=group_df.index, dtype=str)
            # External reason takes precedence if both are true for a row
            curtailment_reason_series.loc[curtailment_internal_cond_mask] = (
                "Internal (OEM) curtailment active"
            )
            curtailment_reason_series.loc[curtailment_external_cond_mask] = (
                "External curtailment active"
            )

            group_df.loc[curtailment_mask, "operational_state"] = (
                "NOT_PRODUCING_EXPLAINED"
            )
            group_df.loc[curtailment_mask, "state_category"] = OPERATIONAL_STATES[
                "NOT_PRODUCING_EXPLAINED"
            ]["name"]
            group_df.loc[curtailment_mask, "state_subcategory"] = OPERATIONAL_STATES[
                "NOT_PRODUCING_EXPLAINED"
            ]["subcategories"]["CURTAILMENT_ACTIVE"]
            group_df.loc[curtailment_mask, "state_reason"] = curtailment_reason_series[
                curtailment_mask
            ]
            group_df.loc[curtailment_mask, "is_producing"] = False

            # --- Rows still needing classification (iterative part) ---
            # These are rows where 'operational_state' is still 'UNCLASSIFIED'
            unclassified_indices = group_df[
                group_df["operational_state"] == "UNCLASSIFIED"
            ].index

            if not unclassified_indices.empty:
                # Fetch adjacent turbines and metmast info if not already cached for this turbine
                if station_id not in adjacent_turbines_cache:
                    adjacent_turbines_cache[station_id] = (
                        self.data_loader.get_adjacent_turbines(station_id)
                    )
                current_adjacent_turbines = adjacent_turbines_cache[station_id]
                # global_metmast_columns is already fetched once

                for idx in unclassified_indices:
                    row_series = group_df.loc[idx]

                    # _classify_single_timestamp will re-check producing, alarm, curtailment.
                    # This is slightly inefficient but simpler than refactoring _classify_single_timestamp
                    # to start at a specific step. The main gain is from fewer iterations.
                    state_info = self._classify_single_timestamp(
                        row_series,
                        group_df,  # Pass the full group_df (which includes its own history sorted by time)
                        all_data_grouped_by_timestamp,
                        current_adjacent_turbines,
                        global_metmast_columns,
                    )
                    group_df.loc[idx, "operational_state"] = state_info["state"]
                    group_df.loc[idx, "state_category"] = state_info["category"]
                    group_df.loc[idx, "state_subcategory"] = state_info["subcategory"]
                    group_df.loc[idx, "state_reason"] = state_info["reason"]
                    group_df.loc[idx, "is_producing"] = state_info["is_producing"]

            processed_groups.append(group_df)  # Append the fully classified group

        if not processed_groups:
            # If data was not empty but no groups were processed (e.g., no StationId),
            # return the initial data copy with default classification columns.
            return result_data

        final_classified_data = pd.concat(processed_groups)
        return final_classified_data.reindex(
            result_data.index
        )  # Restore original index order using result_data's index

    def _classify_single_timestamp(
        self,
        row: pd.Series,
        turbine_specific_history: pd.DataFrame,
        all_data_grouped_by_timestamp: Dict,
        adjacent_turbine_ids_for_row_station: List[str],
        global_metmast_columns: List[str],
    ) -> Dict[str, any]:
        """
        Classify operational state for a single timestamp.

        Args:
            row: Current timestamp data
            turbine_specific_history: Historical data for this turbine (sorted by time)
            all_data_grouped_by_timestamp: All turbine data, pre-grouped by timestamp
            adjacent_turbine_ids_for_row_station: List of adjacent turbine IDs for the current row's station
            global_metmast_columns: List of all metmast column names

        Returns:
            Dictionary with state classification information
        """
        timestamp = row["TimeStamp"]
        power_min = row["wtc_ActPower_min"]

        # Step 1: Check if producing
        is_producing = power_min > PRODUCTION_THRESHOLD_KW

        if is_producing:
            return {
                "state": "PRODUCING",
                "category": OPERATIONAL_STATES["PRODUCING"]["name"],
                "subcategory": OPERATIONAL_STATES["PRODUCING"]["subcategory"],
                "reason": f"Minimum Power output: {power_min:.1f} kW",
                "is_producing": True,
            }

        # Step 2: Not producing - determine why
        # Check for active alarms (highest priority)
        if row["EffectiveAlarmTime"] > ALARM_THRESHOLD_SECONDS:
            return {
                "state": "NOT_PRODUCING_EXPLAINED",
                "category": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"]["name"],
                "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"][
                    "subcategories"
                ]["ALARM_ACTIVE"],
                "reason": f"Active alarm: {row['EffectiveAlarmTime']:.0f}s - {row.get('UK Text', 'N/A')}",
                "is_producing": False,
            }

        # Check for curtailment
        if (
            row["wtc_PowerRed_timeon"] > CURTAILMENT_THRESHOLD_SECONDS
            or row["Duration 2006(s)"] > CURTAILMENT_THRESHOLD_SECONDS
        ):
            curtailment_type = (
                "External" if row["wtc_PowerRed_timeon"] > 0 else "Internal (OEM)"
            )
            return {
                "state": "NOT_PRODUCING_EXPLAINED",
                "category": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"]["name"],
                "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"][
                    "subcategories"
                ]["CURTAILMENT_ACTIVE"],
                "reason": f"{curtailment_type} curtailment active",
                "is_producing": False,
            }

        # Step 4: Assess wind conditions and sensor integrity
        wind_sensor_assessment = self._assess_wind_and_sensor(
            row,
            all_data_grouped_by_timestamp,
            timestamp,
            adjacent_turbine_ids_for_row_station,
            global_metmast_columns,
        )

        # Step 5: Check for sensor errors first
        if wind_sensor_assessment["is_sensor_error"]:
            return {
                "state": "NOT_PRODUCING_UNEXPECTED",
                "category": OPERATIONAL_STATES["NOT_PRODUCING_UNEXPECTED"]["name"],
                "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_UNEXPECTED"][
                    "subcategories"
                ][wind_sensor_assessment["sensor_error_type"]],
                "reason": wind_sensor_assessment["wind_reason"],
                "is_producing": False,
            }

        # Step 6: Check for low wind conditions (if sensor is okay)
        wind_cond = wind_sensor_assessment["wind_condition"]
        wind_reason = wind_sensor_assessment["wind_reason"]

        if wind_cond == "CONFIRMED_LOW_WIND":
            return {
                "state": "NOT_PRODUCING_EXPLAINED",
                "category": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"]["name"],
                "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"][
                    "subcategories"
                ]["CONFIRMED_LOW_WIND"],
                "reason": wind_reason,
                "is_producing": False,
            }

        # Step 7: Check for startup sequences
        startup_assessment = self._assess_startup_sequence(
            row,
            turbine_specific_history,
            all_data_grouped_by_timestamp,  # Passed for future use, not currently used by method
        )
        if startup_assessment["is_startup"]:
            if startup_assessment["trigger"] == "POST_LOW_WIND":
                return {
                    "state": "NOT_PRODUCING_EXPLAINED",
                    "category": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"]["name"],
                    "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"][
                        "subcategories"
                    ]["STARTUP_POST_LOW_WIND"],
                    "reason": startup_assessment["reason"],
                    "is_producing": False,
                }
            elif startup_assessment["trigger"] == "POST_ALARM":
                return {
                    "state": "NOT_PRODUCING_EXPLAINED",
                    "category": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"]["name"],
                    "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_EXPLAINED"][
                        "subcategories"
                    ]["STARTUP_POST_ALARM"],
                    "reason": startup_assessment["reason"],
                    "is_producing": False,
                }
            else:
                return {
                    "state": "NOT_PRODUCING_VERIFICATION_PENDING",
                    "category": OPERATIONAL_STATES[
                        "NOT_PRODUCING_VERIFICATION_PENDING"
                    ]["name"],
                    "subcategory": OPERATIONAL_STATES[
                        "NOT_PRODUCING_VERIFICATION_PENDING"
                    ]["subcategories"]["STARTUP_UNCLEAR"],
                    "reason": startup_assessment["reason"],
                    "is_producing": False,
                }

        # Step 8: If not sensor error, not confirmed low wind, and not startup,
        # now consider SUSPECTED_LOW_WIND from sensor_ok assessment.
        if wind_cond == "SUSPECTED_LOW_WIND":
            return {
                "state": "NOT_PRODUCING_VERIFICATION_PENDING",
                "category": OPERATIONAL_STATES["NOT_PRODUCING_VERIFICATION_PENDING"][
                    "name"
                ],
                "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_VERIFICATION_PENDING"][
                    "subcategories"
                ]["SUSPECTED_LOW_WIND"],
                "reason": wind_reason,
                "is_producing": False,
            }

        # Step 9: Check for mechanical/control issues (if wind is sufficient)
        is_wind_sufficient_for_production = (
            wind_cond == "SUFFICIENT_CONFIRMED" or wind_cond == "SUFFICIENT_SUSPECTED"
        )
        if is_wind_sufficient_for_production:
            return {
                "state": "NOT_PRODUCING_UNEXPECTED",
                "category": OPERATIONAL_STATES["NOT_PRODUCING_UNEXPECTED"]["name"],
                "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_UNEXPECTED"][
                    "subcategories"
                ]["MECHANICAL_CONTROL_ISSUE"],
                "reason": f"Sufficient wind ({wind_sensor_assessment['turbine_wind']:.1f} m/s, refs {wind_sensor_assessment['reference_wind_avg']:.1f} m/s) but not producing. {wind_reason}",
                "is_producing": False,
            }

        # Step 10: Default case - unknown non-production
        return {
            "state": "NOT_PRODUCING_UNEXPECTED",
            "category": OPERATIONAL_STATES["NOT_PRODUCING_UNEXPECTED"]["name"],
            "subcategory": OPERATIONAL_STATES["NOT_PRODUCING_UNEXPECTED"][
                "subcategories"
            ]["UNKNOWN_NON_PRODUCTION"],
            "reason": f"Unable to determine cause. Wind: {wind_cond} ({wind_reason}). Sensor: {wind_sensor_assessment['sensor_reason']}",
            "is_producing": False,
        }

    def _assess_wind_and_sensor(
        self,
        row: pd.Series,
        all_data_grouped_by_timestamp: Dict,
        timestamp: datetime,
        adjacent_turbine_ids_for_row_station: List[str],
        global_metmast_columns: List[str],
    ) -> Dict[str, any]:
        """
        Assess wind conditions and sensor integrity using turbine sensor and reference data.

        Args:
            row: Current timestamp data
            all_data_grouped_by_timestamp: All data pre-grouped by timestamp
            timestamp: Current timestamp
            adjacent_turbine_ids_for_row_station: Adjacent turbine IDs for the current row's station
            global_metmast_columns: List of metmast column names

        Returns:
            Dictionary with wind and sensor assessment results:
            {
                'is_sensor_error': bool,
                'sensor_error_type': 'SENSOR_ERROR_LOW' | 'SENSOR_ERROR_ANOMALOUS' | None,
                'sensor_reason': str,
                'wind_condition': 'CONFIRMED_LOW_WIND' | 'SUSPECTED_LOW_WIND' |
                                  'SUFFICIENT_CONFIRMED' | 'SUFFICIENT_SUSPECTED',
                'wind_reason': str,
                'turbine_wind': float,
                'reference_wind_avg': float,
                'reference_count': int
            }
        """
        turbine_wind = row["wtc_AcWindSp_mean"]
        ref_info = self._get_reference_wind_speeds(
            all_data_grouped_by_timestamp,
            timestamp,
            adjacent_turbine_ids_for_row_station,
            global_metmast_columns,
        )
        avg_ref_wind = ref_info["avg_reference"]
        ref_count = ref_info["count"]

        result = {
            "is_sensor_error": False,
            "sensor_error_type": None,
            "sensor_reason": "",
            "wind_condition": "",
            "wind_reason": "",
            "turbine_wind": turbine_wind,
            "reference_wind_avg": avg_ref_wind,
            "reference_count": ref_count,
        }

        # Handle NaN turbine wind speed data
        turbine_wind_is_nan = pd.isna(turbine_wind)
        if turbine_wind_is_nan:
            # If turbine wind sensor is NaN, treat as sensor error and rely on references if available
            result["is_sensor_error"] = True
            result["sensor_error_type"] = "SENSOR_ERROR_ANOMALOUS"
            result["sensor_reason"] = (
                "Sensor error: Turbine wind speed data is missing/invalid (NaN)"
            )

            if ref_count > 0:
                # Use references to determine wind condition
                if avg_ref_wind < CUT_IN_WIND_SPEED:
                    result["wind_condition"] = "CONFIRMED_LOW_WIND"
                    result["wind_reason"] = (
                        f"Turbine sensor data is missing/invalid. References ({avg_ref_wind:.1f} m/s) indicate low wind."
                    )
                else:
                    result["wind_condition"] = "SUFFICIENT_CONFIRMED"
                    result["wind_reason"] = (
                        f"Turbine sensor data is missing/invalid. References ({avg_ref_wind:.1f} m/s) indicate sufficient wind."
                    )
            else:
                # No references available, cannot determine wind condition reliably
                result["wind_condition"] = (
                    "SUFFICIENT_SUSPECTED"  # Default to suspected sufficient to trigger investigation
                )
                result["wind_reason"] = (
                    "Turbine wind sensor data is missing/invalid (NaN). No references available to determine wind conditions."
                )

            return result

        # Continue with normal processing for non-NaN turbine wind values
        if ref_count > 0:
            deviation = abs(turbine_wind - avg_ref_wind)
            if deviation > WIND_SPEED_DEVIATION_THRESHOLD:
                result["is_sensor_error"] = True
                if turbine_wind < (avg_ref_wind - WIND_SPEED_DEVIATION_THRESHOLD):
                    result["sensor_error_type"] = "SENSOR_ERROR_LOW"
                    result["sensor_reason"] = (
                        f"Sensor error suspected (low reading): Turbine {turbine_wind:.1f} m/s vs references {avg_ref_wind:.1f} m/s"
                    )
                else:
                    result["sensor_error_type"] = "SENSOR_ERROR_ANOMALOUS"
                    result["sensor_reason"] = (
                        f"Sensor error suspected (anomalous reading): Turbine {turbine_wind:.1f} m/s vs references {avg_ref_wind:.1f} m/s"
                    )

                # If sensor error, wind condition is based on (presumably more reliable) references
                if avg_ref_wind < CUT_IN_WIND_SPEED:
                    result["wind_condition"] = "CONFIRMED_LOW_WIND"
                    result["wind_reason"] = (
                        f"References ({avg_ref_wind:.1f} m/s) indicate low wind. Turbine sensor ({turbine_wind:.1f} m/s) reading is unreliable."
                    )
                else:
                    result["wind_condition"] = "SUFFICIENT_CONFIRMED"
                    result["wind_reason"] = (
                        f"References ({avg_ref_wind:.1f} m/s) indicate sufficient wind. Turbine sensor ({turbine_wind:.1f} m/s) reading is unreliable."
                    )
                return result  # Early exit if sensor error is definitive

            # No major sensor error detected, proceed with wind assessment using both turbine and ref
            if turbine_wind < CUT_IN_WIND_SPEED:
                if avg_ref_wind < CUT_IN_WIND_SPEED:  # Both agree
                    result["wind_condition"] = "CONFIRMED_LOW_WIND"
                    result["wind_reason"] = (
                        f"Low wind confirmed: Turbine {turbine_wind:.1f} m/s, References avg {avg_ref_wind:.1f} m/s."
                    )
                    result["sensor_reason"] = (
                        "Sensor reading consistent with references for low wind."
                    )
                else:  # Turbine low, refs high, but deviation not enough for error
                    result["wind_condition"] = "SUSPECTED_LOW_WIND"
                    result["wind_reason"] = (
                        f"Turbine reads low wind ({turbine_wind:.1f} m/s), references higher ({avg_ref_wind:.1f} m/s) but deviation within tolerance. Suspected low wind at turbine."
                    )
                    result["sensor_reason"] = (
                        "Sensor shows low wind, references are higher but within tolerance."
                    )
            else:
                if avg_ref_wind >= CUT_IN_WIND_SPEED:  # Both agree
                    result["wind_condition"] = "SUFFICIENT_CONFIRMED"
                    result["wind_reason"] = (
                        f"Sufficient wind confirmed: Turbine {turbine_wind:.1f} m/s, References avg {avg_ref_wind:.1f} m/s."
                    )
                    result["sensor_reason"] = (
                        "Sensor reading consistent with references for sufficient wind."
                    )
                else:  # Turbine high, refs low, but deviation not enough for error
                    result["wind_condition"] = (
                        "SUFFICIENT_CONFIRMED"  # Trust turbine if sensor not flagged as error
                    )
                    result["wind_reason"] = (
                        f"Turbine reads sufficient wind ({turbine_wind:.1f} m/s), references lower ({avg_ref_wind:.1f} m/s) but deviation within tolerance. Assuming sufficient wind at turbine."
                    )
                    result["sensor_reason"] = (
                        "Sensor shows sufficient wind, references are lower but within tolerance."
                    )
        else:
            result["sensor_reason"] = (
                "No references available to verify sensor integrity."
            )
            if turbine_wind < CUT_IN_WIND_SPEED:
                result["wind_condition"] = "SUSPECTED_LOW_WIND"
                result["wind_reason"] = (
                    f"Low wind suspected on turbine sensor ({turbine_wind:.1f} m/s). No references to confirm or check sensor."
                )
            else:
                result["wind_condition"] = "SUFFICIENT_SUSPECTED"
                result["wind_reason"] = (
                    f"Sufficient wind suspected on turbine sensor ({turbine_wind:.1f} m/s). No references to confirm or check sensor."
                )

        return result

    def _get_reference_wind_speeds(
        self,
        all_data_grouped_by_timestamp: Dict,
        timestamp: datetime,
        adjacent_turbine_ids_list: List[str],
        metmast_column_names_list: List[str],
    ) -> Dict[str, float]:
        """Get reference wind speeds from adjacent turbines and metmasts."""

        timestamp_specific_data = all_data_grouped_by_timestamp.get(timestamp)
        if timestamp_specific_data is None or timestamp_specific_data.empty:
            return {"avg_reference": 0.0, "count": 0, "values": []}

        reference_speeds = []

        if timestamp_specific_data is not None:
            # Adjacent turbines wind speeds
            if (
                "StationId" in timestamp_specific_data.columns
                and "wtc_AcWindSp_mean" in timestamp_specific_data.columns
            ):
                adj_turbines_data_at_ts = timestamp_specific_data[
                    timestamp_specific_data["StationId"].isin(adjacent_turbine_ids_list)
                ]
                if not adj_turbines_data_at_ts.empty:
                    valid_speeds = adj_turbines_data_at_ts["wtc_AcWindSp_mean"].dropna()
                    if not valid_speeds.empty:
                        reference_speeds.extend(
                            valid_speeds.values
                        )  # Use .values for NumPy array

            # Get metmast data
            for met_col in metmast_column_names_list:
                if met_col in timestamp_specific_data.columns:
                    met_series_at_ts = timestamp_specific_data[met_col].dropna()
                    if not met_series_at_ts.empty:
                        # Take the first valid value directly as a scalar
                        reference_speeds.append(met_series_at_ts.iloc[0])

        if reference_speeds:
            avg_ref = np.mean(reference_speeds) if reference_speeds else 0.0
            return {
                "avg_reference": avg_ref,
                "count": len(reference_speeds),
                "values": reference_speeds,
            }

        return {"avg_reference": 0.0, "count": 0, "values": []}

    def _assess_startup_sequence(
        self,
        row: pd.Series,
        turbine_specific_history: pd.DataFrame,
        all_data_grouped_by_timestamp: Dict,
    ) -> Dict[
        str, any
    ]:  # all_data_grouped_by_timestamp not used by current logic but passed for consistency/future
        """Assess if turbine is in startup sequence."""
        current_time = row["TimeStamp"]

        # Look at previous timestamps (last 30 minutes)
        lookback_time = current_time - timedelta(
            minutes=30
        )  # turbine_specific_history is already sorted by TimeStamp
        recent_data = turbine_specific_history[
            (turbine_specific_history["TimeStamp"] >= lookback_time)
            & (turbine_specific_history["TimeStamp"] < current_time)
        ]

        if recent_data.empty:
            return {"is_startup": False, "trigger": None, "reason": "No recent data"}

        # Check for recent low wind recovery
        recent_low_wind = recent_data[
            recent_data["wtc_AcWindSp_mean"] < CUT_IN_WIND_SPEED
        ]
        if not recent_low_wind.empty:
            last_low_wind = recent_low_wind.iloc[-1]
            time_since_low_wind = (
                current_time - last_low_wind["TimeStamp"]
            ).total_seconds() / 60
            if time_since_low_wind <= 20:  # Within 20 minutes
                return {
                    "is_startup": True,
                    "trigger": "POST_LOW_WIND",
                    "reason": f"Startup sequence: {time_since_low_wind:.0f} min after low wind recovery",
                }

        # Check for recent alarm clearance
        recent_alarms = recent_data[recent_data["EffectiveAlarmTime"] > 0]
        if not recent_alarms.empty:
            last_alarm = recent_alarms.iloc[-1]
            time_since_alarm = (
                current_time - last_alarm["TimeStamp"]
            ).total_seconds() / 60
            if time_since_alarm <= 15:  # Within 15 minutes
                return {
                    "is_startup": True,
                    "trigger": "POST_ALARM",
                    "reason": f"Startup sequence: {time_since_alarm:.0f} min after alarm clearance",
                }

        return {
            "is_startup": False,
            "trigger": None,
            "reason": "Not in startup sequence",
        }
