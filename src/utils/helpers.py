"""
Helper functions for the Wind Farm Turbine Investigation Application.
"""

import pandas as pd
from typing import Dict
from datetime import datetime


def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display."""
    if pd.isna(timestamp):
        return "N/A"
    return timestamp.strftime('%Y-%m-%d %H:%M')


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format."""
    if pd.isna(seconds) or seconds == 0:
        return "0s"
    
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def calculate_availability(data: pd.DataFrame, station_id: str = None) -> Dict[str, float]:
    """
    Calculate availability metrics for a turbine or all turbines.
    
    Args:
        data: DataFrame with operational state data
        station_id: Optional specific turbine ID
        
    Returns:
        Dictionary with availability metrics
    """
    if station_id:
        turbine_data = data[data['StationId'] == station_id]
    else:
        turbine_data = data
    
    if turbine_data.empty:
        return {}
    
    total_records = len(turbine_data)
    
    # Count different states
    producing = len(turbine_data[turbine_data['operational_state'] == 'PRODUCING'])
    explained_stop = len(turbine_data[turbine_data['operational_state'] == 'NOT_PRODUCING_EXPLAINED'])
    verification_pending = len(turbine_data[turbine_data['operational_state'] == 'NOT_PRODUCING_VERIFICATION_PENDING'])
    unexpected_stop = len(turbine_data[turbine_data['operational_state'] == 'NOT_PRODUCING_UNEXPECTED'])
    offline = len(turbine_data[turbine_data['operational_state'] == 'OFFLINE_MAINTENANCE'])
    
    return {
        'total_records': total_records,
        'producing_pct': (producing / total_records) * 100,
        'explained_stop_pct': (explained_stop / total_records) * 100,
        'verification_pending_pct': (verification_pending / total_records) * 100,
        'unexpected_stop_pct': (unexpected_stop / total_records) * 100,
        'offline_pct': (offline / total_records) * 100,
        'availability_pct': ((producing + explained_stop) / total_records) * 100,
        'unexplained_loss_pct': ((verification_pending + unexpected_stop) / total_records) * 100
    }


def generate_turbine_report(turbine_data: pd.DataFrame, station_id: str, 
                          adjacent_data: pd.DataFrame = None) -> Dict:
    """
    Generate a comprehensive report for a specific turbine.
    
    Args:
        turbine_data: Data for the specific turbine
        station_id: Turbine identifier
        adjacent_data: Optional data from adjacent turbines
        
    Returns:
        Dictionary with report data
    """
    if turbine_data.empty:
        return {'error': 'No data available for turbine'}
    
    # Basic statistics
    latest_data = turbine_data.iloc[-1]
    time_range = (turbine_data['TimeStamp'].min(), turbine_data['TimeStamp'].max())
    
    # Availability metrics
    availability = calculate_availability(turbine_data)
    
    # Alarm analysis
    alarm_records = turbine_data[turbine_data['EffectiveAlarmTime'] > 0]
    total_alarm_time = turbine_data['EffectiveAlarmTime'].sum()
    
    # Curtailment analysis
    ext_curtailment_time = turbine_data['wtc_PowerRed_timeon'].sum()
    int_curtailment_time = turbine_data['Duration 2006(s)'].sum()
    
    # Production analysis
    producing_records = turbine_data[turbine_data['is_producing'] == True]
    avg_power_when_producing = producing_records['wtc_ActPower_mean'].mean() if not producing_records.empty else 0
    
    # Wind analysis
    avg_wind_speed = turbine_data['wtc_AcWindSp_mean'].mean()
    
    # State distribution
    state_distribution = turbine_data['operational_state'].value_counts().to_dict()
    
    report = {
        'station_id': station_id,
        'time_range': time_range,
        'total_records': len(turbine_data),
        'latest_status': {
            'timestamp': latest_data['TimeStamp'],
            'operational_state': latest_data['operational_state'],
            'state_category': latest_data['state_category'],
            'power_output': latest_data['wtc_ActPower_mean'],
            'wind_speed': latest_data['wtc_AcWindSp_mean'],
            'is_producing': latest_data['is_producing']
        },
        'availability_metrics': availability,
        'alarm_analysis': {
            'total_alarm_records': len(alarm_records),
            'total_alarm_time_hours': total_alarm_time / 3600,
            'alarm_percentage': (len(alarm_records) / len(turbine_data)) * 100
        },
        'curtailment_analysis': {
            'external_curtailment_hours': ext_curtailment_time / 3600,
            'internal_curtailment_hours': int_curtailment_time / 3600,
            'total_curtailment_hours': (ext_curtailment_time + int_curtailment_time) / 3600
        },
        'production_analysis': {
            'producing_records': len(producing_records),
            'production_percentage': (len(producing_records) / len(turbine_data)) * 100,
            'avg_power_when_producing': avg_power_when_producing
        },
        'wind_analysis': {
            'avg_wind_speed': avg_wind_speed,
        },
        'state_distribution': state_distribution
    }
    
    return report


def create_summary_statistics_table(data: pd.DataFrame) -> pd.DataFrame:
    """
    Create summary statistics table for all turbines.
    
    Args:
        data: DataFrame with all turbine data
        
    Returns:
        DataFrame with summary statistics per turbine
    """
    summary_stats = []
    
    for station_id in data['StationId'].unique():
        turbine_data = data[data['StationId'] == station_id]
        
        if not turbine_data.empty:
            latest = turbine_data.iloc[-1]
            availability = calculate_availability(turbine_data)
            
            stats = {
                'StationId': station_id,
                'Current_State': latest['state_category'],
                'Current_Power_kW': latest['wtc_ActPower_mean'],
                'Current_Wind_ms': latest['wtc_AcWindSp_mean'],
                'Availability_Pct': availability.get('availability_pct', 0),
                'Producing_Pct': availability.get('producing_pct', 0),
                'Unexplained_Loss_Pct': availability.get('unexplained_loss_pct', 0),
                'Total_Records': len(turbine_data),
                'Last_Update': latest['TimeStamp']
            }
            
            summary_stats.append(stats)
    
    return pd.DataFrame(summary_stats)


def export_turbine_data(data: pd.DataFrame, station_id: str = None, 
                       file_format: str = 'csv') -> str:
    """
    Export turbine data to file.
    
    Args:
        data: DataFrame to export
        station_id: Optional specific turbine ID
        file_format: Export format ('csv', 'excel')
        
    Returns:
        Filename of exported file
    """
    if station_id:
        export_data = data[data['StationId'] == station_id]
        filename = f"turbine_{station_id}_data"
    else:
        export_data = data
        filename = "all_turbines_data"
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if file_format.lower() == 'csv':
        filename = f"{filename}_{timestamp}.csv"
        export_data.to_csv(filename, index=False)
    elif file_format.lower() == 'excel':
        filename = f"{filename}_{timestamp}.xlsx"
        export_data.to_excel(filename, index=False)
    
    return filename
