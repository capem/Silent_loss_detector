"""
Core operational state logic for wind turbine classification.
This module implements the logic from Spec Version 1.6, Section 3.1.
"""

import pandas as pd
import numpy as np

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

    def _pre_calculate_reference_winds(self, data: pd.DataFrame) -> pd.DataFrame:
        """Pre-calculates reference wind speeds from metmasts and adjacent turbines."""
        if data.empty:
            for col in [
                "adj_turbine_ref_wind_avg",
                "metmast_ref_wind_avg",
                "combined_ref_wind_avg",
            ]:
                data[col] = np.nan
            for col in [
                "adj_turbine_ref_count",
                "metmast_ref_count",
                "combined_ref_count",
            ]:
                data[col] = 0
            return data

        # 1. Metmast Reference Wind
        metmast_cols = self.data_loader.get_metmast_columns()
        if metmast_cols:
            metmast_data_long = data[["TimeStamp"] + metmast_cols].melt(
                id_vars=["TimeStamp"],
                value_vars=metmast_cols,
                var_name="met_col",
                value_name="met_wind",
            )
            metmast_data_long.dropna(subset=["met_wind"], inplace=True)
            metmast_ref_ts = (
                metmast_data_long.groupby("TimeStamp")["met_wind"]
                .agg(metmast_ref_wind_avg="mean", metmast_ref_count="count")
                .reset_index()
            )
            data = pd.merge(data, metmast_ref_ts, on="TimeStamp", how="left")
            data["metmast_ref_wind_avg"] = data["metmast_ref_wind_avg"].fillna(
                np.nan
            )  # Redundant if already np.nan from merge
            data["metmast_ref_count"] = data["metmast_ref_count"].fillna(0).astype(int)
        else:
            data["metmast_ref_wind_avg"] = np.nan
            data["metmast_ref_count"] = 0

        # 2. Adjacent Turbine Reference Wind
        all_station_ids = data["StationId"].unique()
        adj_map = {
            sid: self.data_loader.get_adjacent_turbines(sid) for sid in all_station_ids
        }
        adj_list_expanded = []
        for station_id, adj_turbines in adj_map.items():
            for adj_turbine in adj_turbines:
                adj_list_expanded.append(
                    {"StationId": station_id, "AdjacentStationId": adj_turbine}
                )

        if not adj_list_expanded:
            data["adj_turbine_ref_wind_avg"] = np.nan
            data["adj_turbine_ref_count"] = 0
        else:
            adj_df = pd.DataFrame(adj_list_expanded)
            data_for_adj_lookup = data[
                ["TimeStamp", "StationId", "wtc_AcWindSp_mean"]
            ].rename(
                columns={
                    "StationId": "AdjacentStationId",
                    "wtc_AcWindSp_mean": "adj_wind_speed",
                }
            )
            merged_adj_data = pd.merge(
                data[["TimeStamp", "StationId"]].drop_duplicates(),
                adj_df,
                on="StationId",
                how="left",
            )
            merged_adj_data = pd.merge(
                merged_adj_data,
                data_for_adj_lookup,
                on=["TimeStamp", "AdjacentStationId"],
                how="left",
            )
            merged_adj_data.dropna(subset=["adj_wind_speed"], inplace=True)
            adj_turbine_ref_ts = (
                merged_adj_data.groupby(["TimeStamp", "StationId"])["adj_wind_speed"]
                .agg(adj_turbine_ref_wind_avg="mean", adj_turbine_ref_count="count")
                .reset_index()
            )
            data = pd.merge(
                data, adj_turbine_ref_ts, on=["TimeStamp", "StationId"], how="left"
            )
            data["adj_turbine_ref_wind_avg"] = data["adj_turbine_ref_wind_avg"].fillna(
                np.nan
            )  # Redundant
            data["adj_turbine_ref_count"] = (
                data["adj_turbine_ref_count"].fillna(0).astype(int)
            )

        # 3. Combine References
        total_ref_wind_sum = (
            data["adj_turbine_ref_wind_avg"].fillna(0) * data["adj_turbine_ref_count"]
            + data["metmast_ref_wind_avg"].fillna(0) * data["metmast_ref_count"]
        )
        total_ref_count = data["adj_turbine_ref_count"] + data["metmast_ref_count"]
        data["combined_ref_wind_avg"] = np.where(
            total_ref_count > 0, total_ref_wind_sum / total_ref_count, np.nan
        )
        data["combined_ref_count"] = total_ref_count
        return data

    def _pre_calculate_startup_conditions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Pre-calculates flags for startup sequences."""
        if (
            data.empty
            or "TimeStamp" not in data.columns
            or not pd.api.types.is_datetime64_any_dtype(data["TimeStamp"])
        ):
            data["is_startup_post_low_wind"] = False
            data["is_startup_post_alarm"] = False
            data["startup_reason_details"] = ""
            return data

        data = data.sort_values(["StationId", "TimeStamp"])

        # Post Low Wind Startup
        data["is_low_wind_event_point"] = data["wtc_AcWindSp_mean"] < CUT_IN_WIND_SPEED
        data["low_wind_event_time"] = data.loc[
            data["is_low_wind_event_point"], "TimeStamp"
        ]
        data["last_recorded_low_wind_time"] = data.groupby("StationId")[
            "low_wind_event_time"
        ].ffill()
        mask_last_lw_is_past = data["last_recorded_low_wind_time"] < data["TimeStamp"]
        time_since_lw_recovery = (
            data["TimeStamp"] - data["last_recorded_low_wind_time"]
        ).dt.total_seconds() / 60
        data["is_startup_post_low_wind"] = (
            mask_last_lw_is_past
            & (time_since_lw_recovery > 0)
            & (time_since_lw_recovery <= 20)
        )

        data["startup_reason_details"] = ""  # Initialize
        reason_lw_startup_series = (
            "Startup: "
            + time_since_lw_recovery.round(0).astype(str)
            + " min after low wind"
        )
        data.loc[data["is_startup_post_low_wind"], "startup_reason_details"] = (
            reason_lw_startup_series[data["is_startup_post_low_wind"]]
        )

        # Post Alarm Startup
        data["is_alarm_active_event_point"] = (
            data["EffectiveAlarmTime"] > ALARM_THRESHOLD_SECONDS
        )
        data["alarm_event_time"] = data.loc[
            data["is_alarm_active_event_point"], "TimeStamp"
        ]
        data["last_recorded_alarm_time"] = data.groupby("StationId")[
            "alarm_event_time"
        ].ffill()
        mask_last_alarm_is_past = data["last_recorded_alarm_time"] < data["TimeStamp"]
        time_since_alarm_clearance = (
            data["TimeStamp"] - data["last_recorded_alarm_time"]
        ).dt.total_seconds() / 60
        data["is_startup_post_alarm"] = (
            mask_last_alarm_is_past
            & (time_since_alarm_clearance > 0)
            & (time_since_alarm_clearance <= 15)
        )

        reason_alarm_startup_series = (
            "Startup: "
            + time_since_alarm_clearance.round(0).astype(str)
            + " min after alarm"
        )
        # Only set if not already set by low wind startup, and current is post_alarm_startup
        alarm_startup_reason_mask = data["is_startup_post_alarm"] & (
            data["startup_reason_details"] == ""
        )
        data.loc[alarm_startup_reason_mask, "startup_reason_details"] = (
            reason_alarm_startup_series[alarm_startup_reason_mask]
        )

        return data

    def _pre_calculate_wind_sensor_assessment(self, data: pd.DataFrame) -> pd.DataFrame:
        """Pre-calculates sensor error flags and wind condition categories."""
        if data.empty:
            for col in [
                "is_sensor_error",
                "sensor_error_type",
                "wind_condition",
                "assessment_reason",
            ]:
                data[col] = (
                    False if isinstance(False, type(data.get(col, False))) else pd.NA
                )
            return data

        turbine_wind = data["wtc_AcWindSp_mean"]
        avg_ref_wind = data["combined_ref_wind_avg"]
        ref_count = data["combined_ref_count"]

        data["is_sensor_error"] = False
        data["sensor_error_type"] = pd.NA
        data["wind_condition"] = pd.NA
        data["assessment_reason"] = ""  # Consolidated reason string

        # Cache formatted strings to avoid re-computation
        fmt_turbine_wind = turbine_wind.round(1).astype(str)
        fmt_avg_ref_wind = avg_ref_wind.round(1).astype(str)

        # Case 1: Turbine wind is NaN
        nan_mask = turbine_wind.isna()
        data.loc[nan_mask, "is_sensor_error"] = True
        data.loc[nan_mask, "sensor_error_type"] = "SENSOR_ERROR_ANOMALOUS"
        base_nan_reason = "Sensor error: Turbine wind speed data missing/invalid (NaN)."

        ref_exists_nan_mask = nan_mask & (ref_count > 0)
        ref_low_nan_mask = ref_exists_nan_mask & (avg_ref_wind < CUT_IN_WIND_SPEED)
        data.loc[ref_low_nan_mask, "wind_condition"] = "CONFIRMED_LOW_WIND"
        data.loc[ref_low_nan_mask, "assessment_reason"] = (
            base_nan_reason
            + " Refs ("
            + fmt_avg_ref_wind[ref_low_nan_mask]
            + " m/s) indicate low wind."
        )
        ref_suff_nan_mask = ref_exists_nan_mask & ~(avg_ref_wind < CUT_IN_WIND_SPEED)
        data.loc[ref_suff_nan_mask, "wind_condition"] = "SUFFICIENT_CONFIRMED"
        data.loc[ref_suff_nan_mask, "assessment_reason"] = (
            base_nan_reason
            + " Refs ("
            + fmt_avg_ref_wind[ref_suff_nan_mask]
            + " m/s) indicate sufficient wind."
        )

        no_ref_nan_mask = nan_mask & (ref_count == 0)
        data.loc[no_ref_nan_mask, "wind_condition"] = "SUFFICIENT_SUSPECTED"
        data.loc[no_ref_nan_mask, "assessment_reason"] = (
            base_nan_reason + " No references available to determine wind conditions."
        )

        # Case 2: Turbine wind is NOT NaN (and not already processed by nan_mask)
        valid_mask = ~nan_mask
        valid_ref_mask = valid_mask & (ref_count > 0)

        deviation = abs(turbine_wind - avg_ref_wind)
        err_dev_mask = valid_ref_mask & (deviation > WIND_SPEED_DEVIATION_THRESHOLD)
        data.loc[err_dev_mask, "is_sensor_error"] = True

        # Create reason strings for all rows potentially affected by err_dev_mask
        # These will be NaN where err_dev_mask is False, which is fine.
        err_low_mask = err_dev_mask & (
            turbine_wind < (avg_ref_wind - WIND_SPEED_DEVIATION_THRESHOLD)
        )
        err_anom_mask = err_dev_mask & ~(
            turbine_wind < (avg_ref_wind - WIND_SPEED_DEVIATION_THRESHOLD)
        )
        data.loc[err_low_mask, "sensor_error_type"] = "SENSOR_ERROR_LOW"
        data.loc[err_anom_mask, "sensor_error_type"] = "SENSOR_ERROR_ANOMALOUS"

        # Construct the base deviation reason for all rows where err_dev_mask is True
        # Initialize with a default or empty string
        reason_for_deviation_error = pd.Series("", index=data.index, dtype=str)

        # Populate for 'low' error type where err_low_mask is True
        reason_for_deviation_error.loc[err_low_mask] = (
            "Sensor error (low): Turbine "
            + fmt_turbine_wind[err_low_mask]
            + " vs Refs "
            + fmt_avg_ref_wind[err_low_mask]
            + "."
        )
        # Populate for 'anomalous' error type where err_anom_mask is True
        # This will overwrite if a row was somehow both, but err_low_mask and err_anom_mask should be mutually exclusive under err_dev_mask
        reason_for_deviation_error.loc[err_anom_mask] = (
            "Sensor error (anom): Turbine "
            + fmt_turbine_wind[err_anom_mask]
            + " vs Refs "
            + fmt_avg_ref_wind[err_anom_mask]
            + "."
        )

        # If sensor error by deviation, wind condition based on refs
        sensor_err_by_dev_ref_low = err_dev_mask & (avg_ref_wind < CUT_IN_WIND_SPEED)
        data.loc[sensor_err_by_dev_ref_low, "wind_condition"] = "CONFIRMED_LOW_WIND"
        data.loc[sensor_err_by_dev_ref_low, "assessment_reason"] = (
            reason_for_deviation_error[
                sensor_err_by_dev_ref_low
            ]  # Select the pre-calculated reason
            + " Refs indicate low wind; turbine sensor unreliable."
        )
        sensor_err_by_dev_ref_suff = err_dev_mask & ~(avg_ref_wind < CUT_IN_WIND_SPEED)
        data.loc[sensor_err_by_dev_ref_suff, "wind_condition"] = "SUFFICIENT_CONFIRMED"
        data.loc[sensor_err_by_dev_ref_suff, "assessment_reason"] = (
            reason_for_deviation_error[
                sensor_err_by_dev_ref_suff
            ]  # Select the pre-calculated reason
            + " Refs indicate sufficient wind; turbine sensor unreliable."
        )

        # No sensor error by deviation (but refs exist) - only apply if not already set by err_dev_mask
        no_err_dev_mask = (
            valid_ref_mask & ~err_dev_mask
        )  # Note: is_sensor_error could be true from NaN case

        # Both agree low
        cond_both_low = (
            no_err_dev_mask
            & (turbine_wind < CUT_IN_WIND_SPEED)
            & (avg_ref_wind < CUT_IN_WIND_SPEED)
        )
        data.loc[cond_both_low, "wind_condition"] = "CONFIRMED_LOW_WIND"
        data.loc[cond_both_low, "assessment_reason"] = (
            "Low wind: Turbine "
            + fmt_turbine_wind[cond_both_low]
            + ", Refs "
            + fmt_avg_ref_wind[cond_both_low]
            + ". Sensor consistent."
        )

        # Turbine low, refs high (no error)
        cond_turb_low_ref_high = (
            no_err_dev_mask
            & (turbine_wind < CUT_IN_WIND_SPEED)
            & ~(avg_ref_wind < CUT_IN_WIND_SPEED)
        )
        data.loc[cond_turb_low_ref_high, "wind_condition"] = "SUSPECTED_LOW_WIND"
        data.loc[cond_turb_low_ref_high, "assessment_reason"] = (
            "Turbine low ("
            + fmt_turbine_wind[cond_turb_low_ref_high]
            + "), refs higher ("
            + fmt_avg_ref_wind[cond_turb_low_ref_high]
            + "). Sensor reads low, refs higher (in tolerance)."
        )

        # Both agree sufficient
        cond_both_suff = (
            no_err_dev_mask
            & ~(turbine_wind < CUT_IN_WIND_SPEED)
            & ~(avg_ref_wind < CUT_IN_WIND_SPEED)
        )
        data.loc[cond_both_suff, "wind_condition"] = "SUFFICIENT_CONFIRMED"
        data.loc[cond_both_suff, "assessment_reason"] = (
            "Sufficient wind: Turbine "
            + fmt_turbine_wind[cond_both_suff]
            + ", Refs "
            + fmt_avg_ref_wind[cond_both_suff]
            + ". Sensor consistent."
        )

        # Turbine sufficient, refs low (no error)
        cond_turb_suff_ref_low = (
            no_err_dev_mask
            & ~(turbine_wind < CUT_IN_WIND_SPEED)
            & (avg_ref_wind < CUT_IN_WIND_SPEED)
        )
        data.loc[cond_turb_suff_ref_low, "wind_condition"] = (
            "SUFFICIENT_CONFIRMED"  # Trust turbine if no error
        )
        data.loc[cond_turb_suff_ref_low, "assessment_reason"] = (
            "Turbine sufficient ("
            + fmt_turbine_wind[cond_turb_suff_ref_low]
            + "), refs lower ("
            + fmt_avg_ref_wind[cond_turb_suff_ref_low]
            + "). Sensor reads sufficient, refs lower (in tolerance)."
        )

        # Valid turbine wind, NO references
        no_ref_mask = valid_mask & (ref_count == 0)
        data.loc[no_ref_mask, "sensor_reason"] = "No references to verify sensor."
        no_ref_turb_low = no_ref_mask & (turbine_wind < CUT_IN_WIND_SPEED)
        data.loc[no_ref_turb_low, "wind_condition"] = "SUSPECTED_LOW_WIND"
        data.loc[no_ref_turb_low, "assessment_reason"] = (
            "Suspected low wind on turbine sensor ("
            + fmt_turbine_wind[no_ref_turb_low]
            + "). No references to verify sensor or confirm wind."
        )
        no_ref_turb_suff = no_ref_mask & ~(turbine_wind < CUT_IN_WIND_SPEED)
        data.loc[no_ref_turb_suff, "wind_condition"] = "SUFFICIENT_SUSPECTED"
        data.loc[no_ref_turb_suff, "assessment_reason"] = (
            "Suspected sufficient wind on turbine sensor ("
            + fmt_turbine_wind[no_ref_turb_suff]
            + "). No references to verify sensor or confirm wind."
        )

        return data

    def classify_turbine_states(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Classify operational states for all turbines in the dataset.

        Args:
            data: DataFrame with turbine data

        Returns:
            DataFrame with added operational state columns
        """
        if data.empty:
            # Add empty state columns if data is empty but columns are expected
            for col in [
                "operational_state",
                "state_category",
                "state_subcategory",
                "state_reason",
            ]:
                data[col] = pd.NA
            data["is_producing"] = False
            return data

        # Work on a copy
        df = data.copy()

        if not pd.api.types.is_datetime64_any_dtype(data["TimeStamp"]):
            df["TimeStamp"] = pd.to_datetime(df["TimeStamp"])

        # Pre-calculate all necessary intermediate conditions
        df = self._pre_calculate_reference_winds(df)
        df = self._pre_calculate_startup_conditions(
            df
        )  # Needs sorted data by StationId, TimeStamp
        df = self._pre_calculate_wind_sensor_assessment(df)

        # Define base conditions
        cond_producing = df["wtc_ActPower_min"] > PRODUCTION_THRESHOLD_KW
        cond_alarm = df["EffectiveAlarmTime"] > ALARM_THRESHOLD_SECONDS
        cond_curtail_ext = df["wtc_PowerRed_timeon"] > CURTAILMENT_THRESHOLD_SECONDS
        cond_curtail_int = df["Duration 2006(s)"] > CURTAILMENT_THRESHOLD_SECONDS
        cond_curtailment = cond_curtail_ext | cond_curtail_int

        # Pre-calculated boolean conditions from helper functions
        cond_sensor_error = df["is_sensor_error"]
        cond_confirmed_low_wind = df["wind_condition"] == "CONFIRMED_LOW_WIND"
        cond_startup_post_lw = df["is_startup_post_low_wind"]
        cond_startup_post_alarm = df["is_startup_post_alarm"]
        cond_suspected_low_wind = df["wind_condition"] == "SUSPECTED_LOW_WIND"
        cond_sufficient_wind = (df["wind_condition"] == "SUFFICIENT_CONFIRMED") | (
            df["wind_condition"] == "SUFFICIENT_SUSPECTED"
        )

        # Hierarchical conditions for np.select
        conditions = [
            cond_producing,
            ~cond_producing & cond_alarm,
            ~cond_producing & ~cond_alarm & cond_curtailment,
            ~cond_producing & ~cond_alarm & ~cond_curtailment & cond_sensor_error,
            ~cond_producing
            & ~cond_alarm
            & ~cond_curtailment
            & ~cond_sensor_error
            & cond_confirmed_low_wind,
            ~cond_producing
            & ~cond_alarm
            & ~cond_curtailment
            & ~cond_sensor_error
            & ~cond_confirmed_low_wind
            & cond_startup_post_lw,
            ~cond_producing
            & ~cond_alarm
            & ~cond_curtailment
            & ~cond_sensor_error
            & ~cond_confirmed_low_wind
            & ~cond_startup_post_lw
            & cond_startup_post_alarm,
            ~cond_producing
            & ~cond_alarm
            & ~cond_curtailment
            & ~cond_sensor_error
            & ~cond_confirmed_low_wind
            & ~cond_startup_post_lw
            & ~cond_startup_post_alarm
            & cond_suspected_low_wind,
            ~cond_producing
            & ~cond_alarm
            & ~cond_curtailment
            & ~cond_sensor_error
            & ~cond_confirmed_low_wind
            & ~cond_startup_post_lw
            & ~cond_startup_post_alarm
            & ~cond_suspected_low_wind
            & cond_sufficient_wind,
        ]

        # Choices for each column
        O_S = OPERATIONAL_STATES  # Alias

        choices_op_state = [
            "PRODUCING",
            "NOT_PRODUCING_EXPLAINED",
            "NOT_PRODUCING_EXPLAINED",
            "NOT_PRODUCING_UNEXPECTED",
            "NOT_PRODUCING_EXPLAINED",
            "NOT_PRODUCING_EXPLAINED",
            "NOT_PRODUCING_EXPLAINED",
            "NOT_PRODUCING_VERIFICATION_PENDING",
            "NOT_PRODUCING_UNEXPECTED",
        ]
        choices_category = [
            O_S["PRODUCING"]["name"],
            O_S["NOT_PRODUCING_EXPLAINED"]["name"],
            O_S["NOT_PRODUCING_EXPLAINED"]["name"],
            O_S["NOT_PRODUCING_UNEXPECTED"]["name"],
            O_S["NOT_PRODUCING_EXPLAINED"]["name"],
            O_S["NOT_PRODUCING_EXPLAINED"]["name"],
            O_S["NOT_PRODUCING_EXPLAINED"]["name"],
            O_S["NOT_PRODUCING_VERIFICATION_PENDING"]["name"],
            O_S["NOT_PRODUCING_UNEXPECTED"]["name"],
        ]
        # For subcategory, sensor_error_type is a Series, np.select handles this.
        # Ensure it has a default for rows not matching the sensor_error condition but needing a default for this choice slot.
        default_sensor_subcategory = O_S["NOT_PRODUCING_UNEXPECTED"]["subcategories"][
            "SENSOR_ERROR_ANOMALOUS"
        ]
        sensor_error_type_choice = df["sensor_error_type"].fillna(
            default_sensor_subcategory
        )

        choices_subcategory = [
            O_S["PRODUCING"]["subcategory"],
            O_S["NOT_PRODUCING_EXPLAINED"]["subcategories"]["ALARM_ACTIVE"],
            O_S["NOT_PRODUCING_EXPLAINED"]["subcategories"]["CURTAILMENT_ACTIVE"],
            sensor_error_type_choice,  # Uses the Series
            O_S["NOT_PRODUCING_EXPLAINED"]["subcategories"]["CONFIRMED_LOW_WIND"],
            O_S["NOT_PRODUCING_EXPLAINED"]["subcategories"]["STARTUP_POST_LOW_WIND"],
            O_S["NOT_PRODUCING_EXPLAINED"]["subcategories"]["STARTUP_POST_ALARM"],
            O_S["NOT_PRODUCING_VERIFICATION_PENDING"]["subcategories"][
                "SUSPECTED_LOW_WIND"
            ],
            O_S["NOT_PRODUCING_UNEXPECTED"]["subcategories"][
                "MECHANICAL_CONTROL_ISSUE"
            ],
        ]
        choices_is_producing = [
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        ]

        # Default choices
        default_op_state = "NOT_PRODUCING_UNEXPECTED"
        default_cat = O_S["NOT_PRODUCING_UNEXPECTED"]["name"]
        default_subcat = O_S["NOT_PRODUCING_UNEXPECTED"]["subcategories"][
            "UNKNOWN_NON_PRODUCTION"
        ]
        default_prod = False

        df["operational_state"] = np.select(
            conditions, choices_op_state, default=default_op_state
        )
        df["state_category"] = np.select(
            conditions, choices_category, default=default_cat
        )
        df["state_subcategory"] = np.select(
            conditions, choices_subcategory, default=default_subcat
        )
        df["is_producing"] = np.select(
            conditions, choices_is_producing, default=default_prod
        )

        # Reason strings
        reason_producing = (
            "Minimum Power output: "
            + df["wtc_ActPower_min"].round(1).astype(str)
            + " kW"
        )
        reason_alarm = (
            "Active alarm: "
            + df["EffectiveAlarmTime"].round(0).astype(str)
            + "s - "
            + df["UK Text"].fillna("N/A").astype(str)
        )

        reason_curtailment = pd.Series("", index=df.index, dtype=str)
        reason_curtailment[cond_curtail_int] = "Internal (OEM) curtailment active"
        reason_curtailment[cond_curtail_ext] = (
            "External curtailment active"  # External takes precedence
        )

        # assessment_reason is now the primary source for wind/sensor related explanations
        assessment_reason_filled = df["assessment_reason"].fillna(
            "Assessment details not available"
        )

        reason_startup = df["startup_reason_details"].fillna(
            ""
        )  # Covers both startup types

        reason_mech_control = "Not producing despite " + assessment_reason_filled

        default_reason_str = (
            "Unknown non-production. Assessment: " + assessment_reason_filled
        )

        choices_reason = [
            reason_producing,
            reason_alarm,
            reason_curtailment,
            assessment_reason_filled,  # For cond_sensor_error
            assessment_reason_filled,  # For cond_confirmed_low_wind
            reason_startup,
            reason_startup,  # Startup reason covers both
            assessment_reason_filled,  # For cond_suspected_low_wind
            reason_mech_control,
        ]
        df["state_reason"] = np.select(
            conditions, choices_reason, default=default_reason_str
        )

        # Clean up temporary columns (adjust list as needed)
        temp_cols = [
            "adj_turbine_ref_wind_avg",
            "adj_turbine_ref_count",
            "metmast_ref_wind_avg",
            "metmast_ref_count",
            "combined_ref_wind_avg",
            "combined_ref_count",
            "is_low_wind_event_point",
            "low_wind_event_time",
            "last_recorded_low_wind_time",
            "is_alarm_active_event_point",
            "alarm_event_time",
            "last_recorded_alarm_time",
            "is_startup_post_low_wind",
            "is_startup_post_alarm",
            "startup_reason_details",
            "is_sensor_error",
            "sensor_error_type",
            "wind_condition",
            "assessment_reason",  # Add new consolidated reason to temp_cols to be dropped
        ]
        df.drop(columns=[col for col in temp_cols if col in df.columns], inplace=True)

        return df
