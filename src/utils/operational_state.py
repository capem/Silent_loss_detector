"""
Core operational state logic for wind turbine classification.
This module implements the logic from Spec Version 1.6, Section 3.1.
"""

import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime, timedelta

from .config import (
    PRODUCTION_THRESHOLD_KW, CUT_IN_WIND_SPEED, ALARM_THRESHOLD_SECONDS,
    CURTAILMENT_THRESHOLD_SECONDS, WIND_SPEED_DEVIATION_THRESHOLD,
    OPERATIONAL_STATES
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
        result_data['operational_state'] = 'UNKNOWN'
        result_data['state_category'] = 'Unknown'
        result_data['state_subcategory'] = 'Unknown'
        result_data['state_reason'] = 'Not classified'
        result_data['is_producing'] = False

        # Process each turbine separately to maintain temporal context
        for station_id in result_data['StationId'].unique():
            turbine_mask = result_data['StationId'] == station_id
            turbine_data = result_data[turbine_mask].copy()

            # Classify each timestamp for this turbine
            for idx, row in turbine_data.iterrows():
                state_info = self._classify_single_timestamp(row, turbine_data, result_data)

                # Update the result data
                result_data.loc[idx, 'operational_state'] = state_info['state']
                result_data.loc[idx, 'state_category'] = state_info['category']
                result_data.loc[idx, 'state_subcategory'] = state_info['subcategory']
                result_data.loc[idx, 'state_reason'] = state_info['reason']
                result_data.loc[idx, 'is_producing'] = state_info['is_producing']

        return result_data

    def _classify_single_timestamp(self, row: pd.Series, turbine_data: pd.DataFrame, all_data: pd.DataFrame) -> Dict[str, any]:
        """
        Classify operational state for a single timestamp.

        Args:
            row: Current timestamp data
            turbine_data: Historical data for this turbine
            all_data: All turbine data for reference comparisons

        Returns:
            Dictionary with state classification information
        """
        timestamp = row['TimeStamp']
        power_min = row['wtc_ActPower_min']

        # Step 1: Check if producing
        is_producing = power_min > PRODUCTION_THRESHOLD_KW

        if is_producing:
            return {
                'state': 'PRODUCING',
                'category': OPERATIONAL_STATES['PRODUCING']['name'],
                'subcategory': OPERATIONAL_STATES['PRODUCING']['subcategory'],
                'reason': f'Minimum Power output: {power_min:.1f} kW',
                'is_producing': True
            }

        # Step 2: Not producing - determine why
        # Check for active alarms (highest priority)
        if row['EffectiveAlarmTime'] > ALARM_THRESHOLD_SECONDS:
            return {
                'state': 'NOT_PRODUCING_EXPLAINED',
                'category': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['name'],
                'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['subcategories']['ALARM_ACTIVE'],
                'reason': f'Active alarm: {row["EffectiveAlarmTime"]:.0f}s - {row.get("UK Text", "N/A")}',
                'is_producing': False
            }

        # Check for curtailment
        if (row['wtc_PowerRed_timeon'] > CURTAILMENT_THRESHOLD_SECONDS or
            row['Duration 2006(s)'] > CURTAILMENT_THRESHOLD_SECONDS):
            curtailment_type = "External" if row['wtc_PowerRed_timeon'] > 0 else "Internal (OEM)"
            return {
                'state': 'NOT_PRODUCING_EXPLAINED',
                'category': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['name'],
                'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['subcategories']['CURTAILMENT_ACTIVE'],
                'reason': f'{curtailment_type} curtailment active',
                'is_producing': False
            }

        # Step 4: Assess wind conditions and sensor integrity
        wind_sensor_assessment = self._assess_wind_and_sensor(row, all_data, timestamp)

        # Step 5: Check for sensor errors first
        if wind_sensor_assessment['is_sensor_error']:
            return {
                'state': 'NOT_PRODUCING_UNEXPECTED',
                'category': OPERATIONAL_STATES['NOT_PRODUCING_UNEXPECTED']['name'],
                'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_UNEXPECTED']['subcategories'][wind_sensor_assessment['sensor_error_type']],
                'reason': wind_sensor_assessment['sensor_reason'],
                'is_producing': False
            }

        # Step 6: Check for low wind conditions (if sensor is okay)
        wind_cond = wind_sensor_assessment['wind_condition']
        wind_reason = wind_sensor_assessment['wind_reason']

        if wind_cond == 'CONFIRMED_LOW_WIND':
            return {
                'state': 'NOT_PRODUCING_EXPLAINED',
                'category': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['name'],
                'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['subcategories']['CONFIRMED_LOW_WIND'],
                'reason': wind_reason,
                'is_producing': False
            }

        # Step 7: Check for startup sequences
        startup_assessment = self._assess_startup_sequence(row, turbine_data, all_data)
        if startup_assessment['is_startup']:
            if startup_assessment['trigger'] == 'POST_LOW_WIND':
                return {
                    'state': 'NOT_PRODUCING_EXPLAINED',
                    'category': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['name'],
                    'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['subcategories']['STARTUP_POST_LOW_WIND'],
                    'reason': startup_assessment['reason'],
                    'is_producing': False
                }
            elif startup_assessment['trigger'] == 'POST_ALARM':
                return {
                    'state': 'NOT_PRODUCING_EXPLAINED',
                    'category': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['name'],
                    'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_EXPLAINED']['subcategories']['STARTUP_POST_ALARM'],
                    'reason': startup_assessment['reason'],
                    'is_producing': False
                }
            else:
                return {
                    'state': 'NOT_PRODUCING_VERIFICATION_PENDING',
                    'category': OPERATIONAL_STATES['NOT_PRODUCING_VERIFICATION_PENDING']['name'],
                    'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_VERIFICATION_PENDING']['subcategories']['STARTUP_UNCLEAR'],
                    'reason': startup_assessment['reason'],
                    'is_producing': False
                }

        # Step 8: If not sensor error, not confirmed low wind, and not startup,
        # now consider SUSPECTED_LOW_WIND from sensor_ok assessment.
        if wind_cond == 'SUSPECTED_LOW_WIND':
            return {
                'state': 'NOT_PRODUCING_VERIFICATION_PENDING',
                'category': OPERATIONAL_STATES['NOT_PRODUCING_VERIFICATION_PENDING']['name'],
                'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_VERIFICATION_PENDING']['subcategories']['SUSPECTED_LOW_WIND'],
                'reason': wind_reason,
                'is_producing': False
            }

        # Step 9: Check for mechanical/control issues (if wind is sufficient)
        is_wind_sufficient_for_production = (wind_cond == 'SUFFICIENT_CONFIRMED' or wind_cond == 'SUFFICIENT_SUSPECTED')
        if is_wind_sufficient_for_production:
            return {
                'state': 'NOT_PRODUCING_UNEXPECTED',
                'category': OPERATIONAL_STATES['NOT_PRODUCING_UNEXPECTED']['name'],
                'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_UNEXPECTED']['subcategories']['MECHANICAL_CONTROL_ISSUE'],
                'reason': f'Sufficient wind ({wind_sensor_assessment["turbine_wind"]:.1f} m/s, refs {wind_sensor_assessment["reference_wind_avg"]:.1f} m/s) but not producing. {wind_reason}',
                'is_producing': False
            }

        # Step 10: Default case - unknown non-production
        return {
            'state': 'NOT_PRODUCING_UNEXPECTED',
            'category': OPERATIONAL_STATES['NOT_PRODUCING_UNEXPECTED']['name'],
            'subcategory': OPERATIONAL_STATES['NOT_PRODUCING_UNEXPECTED']['subcategories']['UNKNOWN_NON_PRODUCTION'],
            'reason': f'Unable to determine cause. Wind: {wind_cond} ({wind_reason}). Sensor: {wind_sensor_assessment["sensor_reason"]}',
            'is_producing': False
        }

    def _assess_wind_and_sensor(self, row: pd.Series, all_data: pd.DataFrame,
                                timestamp: datetime) -> Dict[str, any]:
        """
        Assess wind conditions and sensor integrity using turbine sensor and reference data.

        Args:
            row: Current timestamp data
            all_data: All turbine data for reference
            timestamp: Current timestamp

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
        turbine_wind = row['wtc_AcWindSp_mean']
        station_id = row['StationId']
        ref_info = self._get_reference_wind_speeds(station_id, all_data, timestamp)
        avg_ref_wind = ref_info['avg_reference']
        ref_count = ref_info['count']

        result = {
            'is_sensor_error': False, 'sensor_error_type': None, 'sensor_reason': '',
            'wind_condition': '', 'wind_reason': '',
            'turbine_wind': turbine_wind, 'reference_wind_avg': avg_ref_wind, 'reference_count': ref_count
        }

        if ref_count > 0:
            deviation = abs(turbine_wind - avg_ref_wind)
            if deviation > WIND_SPEED_DEVIATION_THRESHOLD:
                result['is_sensor_error'] = True
                if turbine_wind < (avg_ref_wind - WIND_SPEED_DEVIATION_THRESHOLD):
                    result['sensor_error_type'] = 'SENSOR_ERROR_LOW'
                    result['sensor_reason'] = f'Sensor error suspected (low reading): Turbine {turbine_wind:.1f} m/s vs references {avg_ref_wind:.1f} m/s'
                else:
                    result['sensor_error_type'] = 'SENSOR_ERROR_ANOMALOUS'
                    result['sensor_reason'] = f'Sensor error suspected (anomalous reading): Turbine {turbine_wind:.1f} m/s vs references {avg_ref_wind:.1f} m/s'

                # If sensor error, wind condition is based on (presumably more reliable) references
                if avg_ref_wind < CUT_IN_WIND_SPEED:
                    result['wind_condition'] = 'CONFIRMED_LOW_WIND'
                    result['wind_reason'] = f'References ({avg_ref_wind:.1f} m/s) indicate low wind. Turbine sensor ({turbine_wind:.1f} m/s) reading is unreliable.'
                else:
                    result['wind_condition'] = 'SUFFICIENT_CONFIRMED'
                    result['wind_reason'] = f'References ({avg_ref_wind:.1f} m/s) indicate sufficient wind. Turbine sensor ({turbine_wind:.1f} m/s) reading is unreliable.'
                return result # Early exit if sensor error is definitive

            # No major sensor error detected, proceed with wind assessment using both turbine and ref
            if turbine_wind < CUT_IN_WIND_SPEED:
                if avg_ref_wind < CUT_IN_WIND_SPEED: # Both agree
                    result['wind_condition'] = 'CONFIRMED_LOW_WIND'
                    result['wind_reason'] = f'Low wind confirmed: Turbine {turbine_wind:.1f} m/s, References avg {avg_ref_wind:.1f} m/s.'
                    result['sensor_reason'] = 'Sensor reading consistent with references for low wind.'
                else: # Turbine low, refs high, but deviation not enough for error
                    result['wind_condition'] = 'SUSPECTED_LOW_WIND'
                    result['wind_reason'] = f'Turbine reads low wind ({turbine_wind:.1f} m/s), references higher ({avg_ref_wind:.1f} m/s) but deviation within tolerance. Suspected low wind at turbine.'
                    result['sensor_reason'] = 'Sensor shows low wind, references are higher but within tolerance.'
            else:
                if avg_ref_wind >= CUT_IN_WIND_SPEED: # Both agree
                    result['wind_condition'] = 'SUFFICIENT_CONFIRMED'
                    result['wind_reason'] = f'Sufficient wind confirmed: Turbine {turbine_wind:.1f} m/s, References avg {avg_ref_wind:.1f} m/s.'
                    result['sensor_reason'] = 'Sensor reading consistent with references for sufficient wind.'
                else: # Turbine high, refs low, but deviation not enough for error
                    result['wind_condition'] = 'SUFFICIENT_CONFIRMED' # Trust turbine if sensor not flagged as error
                    result['wind_reason'] = f'Turbine reads sufficient wind ({turbine_wind:.1f} m/s), references lower ({avg_ref_wind:.1f} m/s) but deviation within tolerance. Assuming sufficient wind at turbine.'
                    result['sensor_reason'] = 'Sensor shows sufficient wind, references are lower but within tolerance.'
        else:
            result['sensor_reason'] = 'No references available to verify sensor integrity.'
            if turbine_wind < CUT_IN_WIND_SPEED:
                result['wind_condition'] = 'SUSPECTED_LOW_WIND'
                result['wind_reason'] = f'Low wind suspected on turbine sensor ({turbine_wind:.1f} m/s). No references to confirm or check sensor.'
            else:
                result['wind_condition'] = 'SUFFICIENT_SUSPECTED'
                result['wind_reason'] = f'Sufficient wind suspected on turbine sensor ({turbine_wind:.1f} m/s). No references to confirm or check sensor.'

        return result

    def _get_reference_wind_speeds(self, station_id: str, all_data: pd.DataFrame,
                                 timestamp: datetime) -> Dict[str, float]:
        """Get reference wind speeds from adjacent turbines and metmasts."""
        # Get data for the same timestamp
        timestamp_data = all_data[all_data['TimeStamp'] == timestamp]

        reference_speeds = []

        # Get adjacent turbines
        adjacent_turbines = self.data_loader.get_adjacent_turbines(station_id)

        for adj_turbine in adjacent_turbines:
            adj_data = timestamp_data[timestamp_data['StationId'] == adj_turbine]
            if not adj_data.empty:
                adj_row = adj_data.iloc[0]
                reference_speeds.append(adj_row['wtc_AcWindSp_mean'])

        # Get metmast data
        metmast_cols = self.data_loader.get_metmast_columns()
        for col in metmast_cols:
            if col in timestamp_data.columns:
                metmast_values = timestamp_data[col].dropna()
                if not metmast_values.empty:
                    reference_speeds.extend(metmast_values.tolist())

        if reference_speeds:
            return {
                'avg_reference': np.mean(reference_speeds),
                'count': len(reference_speeds),
                'values': reference_speeds
            }
        else:
            return {
                'avg_reference': 0.0,
                'count': 0,
                'values': []
            }

    def _assess_startup_sequence(self, row: pd.Series, turbine_data: pd.DataFrame,
                               all_data: pd.DataFrame) -> Dict[str, any]:
        """Assess if turbine is in startup sequence."""
        current_time = row['TimeStamp']

        # Look at previous timestamps (last 30 minutes)
        lookback_time = current_time - timedelta(minutes=30)
        recent_data = turbine_data[
            (turbine_data['TimeStamp'] >= lookback_time) &
            (turbine_data['TimeStamp'] < current_time)
        ].sort_values('TimeStamp')

        if recent_data.empty:
            return {'is_startup': False, 'trigger': None, 'reason': 'No recent data'}

        # Check for recent low wind recovery
        recent_low_wind = recent_data[recent_data['wtc_AcWindSp_mean'] < CUT_IN_WIND_SPEED]
        if not recent_low_wind.empty:
            last_low_wind = recent_low_wind.iloc[-1]
            time_since_low_wind = (current_time - last_low_wind['TimeStamp']).total_seconds() / 60
            if time_since_low_wind <= 20:  # Within 20 minutes
                return {
                    'is_startup': True,
                    'trigger': 'POST_LOW_WIND',
                    'reason': f'Startup sequence: {time_since_low_wind:.0f} min after low wind recovery'
                }

        # Check for recent alarm clearance
        recent_alarms = recent_data[recent_data['EffectiveAlarmTime'] > 0]
        if not recent_alarms.empty:
            last_alarm = recent_alarms.iloc[-1]
            time_since_alarm = (current_time - last_alarm['TimeStamp']).total_seconds() / 60
            if time_since_alarm <= 15:  # Within 15 minutes
                return {
                    'is_startup': True,
                    'trigger': 'POST_ALARM',
                    'reason': f'Startup sequence: {time_since_alarm:.0f} min after alarm clearance'
                }

        return {'is_startup': False, 'trigger': None, 'reason': 'Not in startup sequence'}

