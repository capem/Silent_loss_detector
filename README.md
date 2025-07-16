# Wind Farm Turbine Investigation Application

A comprehensive Plotly Dash application for investigating wind turbines that are not producing energy, especially when no alarms are active ("silent non-production"). The application analyzes turbine operational states and helps identify root causes by comparing turbine data with adjacent turbines and meteorological masts.

## Features

### Core Modules

1. **Main Dashboard & Turbine Overview**
   - File upload for .pkl turbine data and optional CSV layout data
   - Time range filtering and quick selection buttons
   - Operational state summary with color-coded cards
   - Sortable and filterable turbine table
   - Real-time data validation and preprocessing

2. **Operational State Logic**
   - Automatic classification of turbine states based on Spec Version 1.6:
     - **Producing**: Normal operation
     - **Not Producing - Explained**: Alarm active, curtailment, confirmed low wind, startup sequences
     - **Not Producing - Verification Pending**: Suspected low wind, unclear startup
     - **Not Producing - Unexpected**: Sensor errors, mechanical issues, unknown causes
     - **Data Missing**: Data Missing
   - Configurable thresholds and parameters
   - Historical context analysis for startup sequences

3. **Investigation Panel**
   - Detailed turbine analysis with status overview and key metrics
   - Interactive time series charts for power output and wind speed
   - Comparison with adjacent turbines and metmasts
   - Alarm and curtailment history visualization
   - Production anomaly detection and analysis
   - Detailed data table with filtering and sorting

4. **Wind Sensor Integrity Analysis**
   - Integrated with main turbine selection (automatic target selection)
   - Target turbine selection with reference comparison
   - Multi-series wind speed comparison charts
   - Deviation analysis and correlation metrics
   - Anomaly detection with severity classification

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Silent_loss_detector
   ```

2. **Install dependencies using uv (recommended):**
   ```bash
   uv sync
   ```

   Or using pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   Open your browser and navigate to `http://localhost:8050`

## Data Requirements

### Primary Data File (.pkl)
The application expects a pickle file containing a pandas DataFrame with the following columns:

**Required Columns:**
- `StationId`: Turbine identifier
- `TimeStamp`: 10-minute interval timestamp
- `EffectiveAlarmTime`: Duration of any active alarm (seconds)
- `UK Text`: Alarm descriptions (multiple, | separated)
- `Duration 2006(s)`: Duration of internal curtailment warning "DG:Local power limit - OEM"
- `wtc_kWG1TotE_accum`: Exported energy per TimeStamp
- `wtc_ActPower_mean`: Mean active power (kW) - Primary indicator for "Not Producing" status
- `wtc_ActPower_min`: Minimum active power
- `wtc_ActPower_max`: Maximum active power
- `wtc_AcWindSp_mean`: Mean nacelle wind speed (m/s)
- `wtc_ActualWindDirection_mean`: Mean nacelle direction
- `wtc_PowerRed_timeon`: Duration of external curtailment (seconds)

**Optional Columns (Metmasts):**
- `met_WindSpeedRot_mean_38`, `met_WindSpeedRot_mean_39`, `met_WindSpeedRot_mean_246`: Metmast wind speeds
- `met_WinddirectionRot_mean_38`, `met_WinddirectionRot_mean_39`, `met_WinddirectionRot_mean_246`: Metmast wind directions

### Optional Layout File (.csv)
For enhanced spatial analysis and adjacency detection:
- `StationId`: Turbine identifier
- `X-Coordinate`: X coordinate in meters
- `Y-Coordinate`: Y coordinate in meters

## Configuration

Key configuration parameters can be modified in `src/utils/config.py`:

```python
# Production thresholds
PRODUCTION_THRESHOLD_KW = 1.0  # kW - Below this is considered "Not Producing"
CUT_IN_WIND_SPEED = 3.0  # m/s - Minimum wind speed for production

# Wind sensor validation thresholds
WIND_SPEED_DEVIATION_THRESHOLD = 2.0  # m/s - Max acceptable deviation from references
WIND_DIRECTION_DEVIATION_THRESHOLD = 30.0  # degrees - Max acceptable deviation

# Adjacency settings
MAX_ADJACENT_TURBINES = 5  # Maximum number of adjacent turbines to consider
ADJACENCY_DISTANCE_THRESHOLD = 1000.0  # meters - Max distance for adjacency
```

## Usage Guide

### 1. Data Loading
1. Upload your .pkl turbine data file using the drag-and-drop interface
2. Optionally upload a CSV layout file for enhanced spatial analysis
3. Review the data summary to ensure successful loading

### 2. Time Range Selection
- Use the date picker to select custom time ranges
- Use quick selection buttons (24h, 7d, 30d, All) for common ranges
- Filter data by operational state using the dropdown

### 3. Turbine Investigation
1. Click on any turbine row in the main table to open the investigation panel
2. Review the turbine's current status and key metrics
3. Select adjacent turbines and metmasts for comparison
4. Analyze time series charts for power output and wind speed patterns
5. Review alarm/curtailment history and anomaly analysis

### 4. Sensor Analysis
1. Navigate to the sensor analysis section
2. Select a target turbine for detailed sensor validation
3. Choose reference turbines and metmasts for comparison
4. Run the analysis to detect sensor anomalies and correlation issues

## Operational State Classification Logic

The application implements a hierarchical classification system:

1. **Check if producing** (Power > threshold)
2. **If not producing, check in order:**
   - Active alarms (highest priority)
   - Active curtailment (external or internal)
   - Low wind conditions (confirmed vs suspected)
   - Startup sequences (post-alarm, post-low wind, unclear)
   - Sensor errors (low readings, anomalous readings)
   - Mechanical/control issues (sufficient wind but not producing)
   - Unknown non-production (default case)

## Architecture

```
app.py                          # Main application entry point
src/
├── layouts/
│   ├── main_dashboard.py      # Main dashboard layout
│   ├── investigation_panel.py # Investigation panel layout
│   └── sensor_analysis.py     # Sensor analysis layout
├── callbacks/
│   ├── main_callbacks.py      # Main dashboard callbacks
│   ├── investigation_callbacks.py # Investigation panel callbacks
│   └── sensor_callbacks.py    # Sensor analysis callbacks (to be implemented)
└── utils/
    ├── config.py              # Configuration settings
    ├── helpers.py             # Helper functions and utilities
    ├── data_loader.py         # Data loading and preprocessing
    └── operational_state.py   # Core operational state classification logic
```

## Dependencies

- **dash**: Web application framework
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **plotly**: Interactive plotting
- **dash-bootstrap-components**: Bootstrap components for Dash

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For questions or issues, please [create an issue](link-to-issues) or contact [your-contact-info].