"""
Sample data generator for testing the Wind Farm Turbine Investigation Application.
This script creates realistic sample data that matches the expected format.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import random


def generate_sample_data(num_turbines=20, num_days=7, interval_minutes=10):
    """
    Generate sample wind farm data for testing.

    Args:
        num_turbines: Number of turbines to simulate
        num_days: Number of days of data to generate
        interval_minutes: Data interval in minutes

    Returns:
        DataFrame with sample turbine data
    """

    # Generate time series
    start_time = datetime.now() - timedelta(days=num_days)
    end_time = datetime.now()
    time_range = pd.date_range(
        start=start_time, end=end_time, freq=f"{interval_minutes}min"
    )

    # Generate turbine IDs
    turbine_ids = [f"WTG_{i:03d}" for i in range(1, num_turbines + 1)]

    # Create base DataFrame
    data_rows = []

    for turbine_id in turbine_ids:
        for timestamp in time_range:
            # Simulate realistic wind patterns (diurnal and weather variations)
            hour = timestamp.hour
            day_factor = 0.8 + 0.4 * np.sin(2 * np.pi * hour / 24)  # Diurnal pattern
            weather_factor = 0.5 + 0.5 * np.sin(
                2 * np.pi * timestamp.day / 30
            )  # Monthly variation
            base_wind = (
                6.0 + 4.0 * day_factor * weather_factor + np.random.normal(0, 1.5)
            )
            base_wind = max(0, base_wind)  # Ensure non-negative

            # Simulate turbine-specific variations
            turbine_factor = 0.9 + 0.2 * np.random.random()
            wind_speed = base_wind * turbine_factor

            # Simulate power output based on wind speed (simplified power curve)
            if wind_speed < 3.0:  # Below cut-in
                power = 0
            elif wind_speed < 12.0:  # Ramp-up region
                power = min(2000, (wind_speed - 3) ** 2.5 * 50)
            else:  # Rated power region
                power = 2000 + np.random.normal(0, 50)

            power = max(0, power)

            # Simulate occasional issues
            has_alarm = False
            alarm_time = 0
            alarm_text = ""
            curtailment_ext = 0
            curtailment_int = 0

            # Random alarms (5% chance)
            if np.random.random() < 0.05:
                has_alarm = True
                alarm_time = np.random.randint(60, 600)  # 1-10 minutes
                alarm_types = [
                    "High vibration detected",
                    "Generator temperature high",
                    "Grid fault detected",
                    "Hydraulic pressure low",
                    "Communication error",
                ]
                alarm_text = random.choice(alarm_types)
                power = 0  # No power during alarm

            # Random curtailment (3% chance)
            if np.random.random() < 0.03 and not has_alarm:
                if np.random.random() < 0.7:  # External curtailment
                    curtailment_ext = np.random.randint(300, 600)
                    power *= 0.3  # Reduced power
                else:  # Internal curtailment
                    curtailment_int = np.random.randint(180, 400)
                    power *= 0.5

            # Simulate sensor errors (1% chance)
            if np.random.random() < 0.01:
                if np.random.random() < 0.5:
                    wind_speed *= 0.3  # Low reading error
                else:
                    wind_speed *= 1.8  # High reading error

            # Create data row
            row = {
                "StationId": turbine_id,
                "TimeStamp": timestamp,
                "EffectiveAlarmTime": alarm_time,
                "UK Text": alarm_text,
                "Duration 2006(s)": curtailment_int,
                "wtc_kWG1TotE_accum": power * interval_minutes / 60,  # Energy in kWh
                "wtc_ActPower_mean": power,
                "wtc_ActPower_min": max(0, power - np.random.uniform(0, 50)),
                "wtc_ActPower_max": power + np.random.uniform(0, 50),
                "wtc_AcWindSp_mean": wind_speed,
                "wtc_ActualWindDirection_mean": 180
                + 60 * np.sin(2 * np.pi * timestamp.hour / 24)
                + np.random.normal(0, 15),
                "wtc_PowerRed_timeon": curtailment_ext,
            }

            data_rows.append(row)

    # Create DataFrame
    df = pd.DataFrame(data_rows)

    # Add metmast data (3 metmasts)
    for metmast_id in [38, 39, 246]:
        timestamp_to_wind = {}
        timestamp_to_direction = {}

        for timestamp in time_range:
            # Metmasts should be more reliable than turbine sensors
            hour = timestamp.hour
            day_factor = 0.8 + 0.4 * np.sin(2 * np.pi * hour / 24)
            weather_factor = 0.5 + 0.5 * np.sin(2 * np.pi * timestamp.day / 30)
            base_wind = (
                6.0 + 4.0 * day_factor * weather_factor + np.random.normal(0, 1.0)
            )
            base_wind = max(0, base_wind)
            timestamp_to_wind[timestamp] = base_wind

            base_direction = (
                180
                + 60 * np.sin(2 * np.pi * timestamp.hour / 24)
                + np.random.normal(0, 10)
            )
            timestamp_to_direction[timestamp] = base_direction

        # Map the timestamp-specific values to the DataFrame
        df[f"met_WindSpeedRot_mean_{metmast_id}"] = df['TimeStamp'].map(timestamp_to_wind)
        df[f"met_WinddirectionRot_mean_{metmast_id}"] = df['TimeStamp'].map(timestamp_to_direction)

    return df


def generate_layout_data(num_turbines=20):
    """
    Generate sample wind farm layout data.

    Args:
        num_turbines: Number of turbines

    Returns:
        DataFrame with layout coordinates
    """
    layout_data = []

    # Create a simple grid layout with some randomness
    grid_size = int(np.ceil(np.sqrt(num_turbines)))
    spacing = 500  # meters between turbines

    for i in range(num_turbines):
        turbine_id = f"WTG_{i + 1:03d}"

        # Grid position with some randomness
        row = i // grid_size
        col = i % grid_size

        x = col * spacing + np.random.normal(0, 50)
        y = row * spacing + np.random.normal(0, 50)

        layout_data.append(
            {"StationId": turbine_id, "X-Coordinate": x, "Y-Coordinate": y}
        )

    return pd.DataFrame(layout_data)


if __name__ == "__main__":
    print("Generating sample wind farm data...")

    # Generate main turbine data
    turbine_data = generate_sample_data(num_turbines=20, num_days=7)

    # Save as pickle file
    with open("sample_turbine_data.pkl", "wb") as f:
        pickle.dump(turbine_data, f)

    print(
        f"✅ Generated {len(turbine_data)} records for {len(turbine_data['StationId'].unique())} turbines"
    )
    print(
        f"   Time range: {turbine_data['TimeStamp'].min()} to {turbine_data['TimeStamp'].max()}"
    )
    print("Saved as: sample_turbine_data.pkl")

    # Generate layout data
    layout_data = generate_layout_data(num_turbines=20)
    layout_data.to_csv("sample_layout_data.csv", index=False)

    print(f"✅ Generated layout data for {len(layout_data)} turbines")
    print("Saved as: sample_layout_data.csv")

    # Display sample statistics
    print("\n📊 Sample Data Statistics:")
    print(f"   Total records: {len(turbine_data):,}")
    print(f"   Unique turbines: {len(turbine_data['StationId'].unique())}")
    print(
        f"   Records with alarms: {len(turbine_data[turbine_data['EffectiveAlarmTime'] > 0])}"
    )
    print(
        f"   Records with external curtailment: {len(turbine_data[turbine_data['wtc_PowerRed_timeon'] > 0])}"
    )
    print(
        f"   Records with internal curtailment: {len(turbine_data[turbine_data['Duration 2006(s)'] > 0])}"
    )
    print(f"   Average power output: {turbine_data['wtc_ActPower_mean'].mean():.1f} kW")
    print(f"   Average wind speed: {turbine_data['wtc_AcWindSp_mean'].mean():.1f} m/s")

    print("\n🚀 You can now upload these files to the application:")
    print("   1. Upload 'sample_turbine_data.pkl' as the main data file")
    print("   2. Upload 'sample_layout_data.csv' as the optional layout file")
    print("   3. Explore the turbine investigation features!")
