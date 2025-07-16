"""
Configuration settings for the Wind Farm Turbine Investigation Application.
"""

# Production thresholds
PRODUCTION_THRESHOLD_KW = 0.0  # kW - Below this is considered "Not Producing"
CUT_IN_WIND_SPEED = 4.0  # m/s - Minimum wind speed for production

# Time-based thresholds
ALARM_THRESHOLD_SECONDS = 0  # Any alarm time > 0 is considered active
CURTAILMENT_THRESHOLD_SECONDS = 0  # Any curtailment time > 0 is considered active

# Wind sensor validation thresholds
WIND_SPEED_DEVIATION_THRESHOLD = 2.0  # m/s - Max acceptable deviation from references
WIND_DIRECTION_DEVIATION_THRESHOLD = 30.0  # degrees - Max acceptable deviation

# Adjacency settings
MAX_ADJACENT_TURBINES = 5  # Maximum number of adjacent turbines to consider
ADJACENCY_DISTANCE_THRESHOLD = 300.0  # meters - Max distance for adjacency

# Data validation settings
REQUIRED_COLUMNS = [
    "StationId",
    "TimeStamp",
    "EffectiveAlarmTime",
    "UK Text",
    "Duration 2006(s)",
    "wtc_kWG1TotE_accum",
    "wtc_ActPower_mean",
    "wtc_ActPower_min",
    "wtc_ActPower_max",
    "wtc_AcWindSp_mean",
    "wtc_ActualWindDirection_mean",
    "wtc_PowerRed_timeon",
]

OPTIONAL_COLUMNS = [
    "met_WindSpeedRot_mean_38",
    "met_WindSpeedRot_mean_39",
    "met_WindSpeedRot_mean_246",
    "met_WinddirectionRot_mean_38",
    "met_WinddirectionRot_mean_39",
    "met_WinddirectionRot_mean_246",
]

# Operational state categories
OPERATIONAL_STATES = {
    "PRODUCING": {
        "code": 1,
        "name": "Producing",
        "subcategory": "Normal Operation",
        "color": "#28a745",  # Green
    },
    "NOT_PRODUCING_EXPLAINED": {
        "code": 2,
        "name": "Not Producing - Explained",
        "subcategories": {
            "ALARM_ACTIVE": "Alarm Active",
            "CURTAILMENT_ACTIVE": "Curtailment Active",
            "CONFIRMED_LOW_WIND": "Confirmed Low Wind",
            "STARTUP_POST_LOW_WIND": "Startup Sequence (Post-Low Wind)",
            "STARTUP_POST_ALARM": "Startup Sequence (Post-Alarm)",
        },
        "color": "#ffc107",  # Yellow
    },
    "NOT_PRODUCING_VERIFICATION_PENDING": {
        "code": 3,
        "name": "Not Producing - Verification Pending",
        "subcategories": {
            "SUSPECTED_LOW_WIND": "Suspected Low Wind",
            "STARTUP_UNCLEAR": "Startup Sequence (Trigger Unclear)",
        },
        "color": "#fd7e14",  # Orange
    },
    "NOT_PRODUCING_UNEXPECTED": {
        "code": 4,
        "name": "Not Producing - Unexpected",
        "subcategories": {
            "SENSOR_ERROR_LOW": "Suspected Sensor Error (Low Reading)",
            "SENSOR_ERROR_ANOMALOUS": "Suspected Sensor Error (Anomalous Reading)",
            "MECHANICAL_CONTROL_ISSUE": "Suspected Mechanical/Control Issue",
            "UNKNOWN_NON_PRODUCTION": "Unknown Non-Production",
        },
        "color": "#dc3545",  # Red
    },
    "DATA_MISSING": {
        "code": 5,
        "name": "Data Missing",
        "subcategories": {
            "WITH_ALARM": "Data Missing (Alarm Active)",
            "NO_ALARM": "Data Missing (No Alarm)",
        },
        "color": "#adb5bd",
    },
}

# UI Configuration
DEFAULT_TIME_RANGE_HOURS = 24
MAX_DISPLAY_ROWS = 1000
CHART_HEIGHT = 400
TABLE_PAGE_SIZE = 20

# File upload settings
MAX_FILE_SIZE_MB = 500
ALLOWED_FILE_EXTENSIONS = [".pkl", ".pickle"]
LAYOUT_FILE_EXTENSIONS = [".csv"]
