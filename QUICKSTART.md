# Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### 1. Generate Sample Data
```bash
python sample_data_generator.py
```
This creates:
- `sample_turbine_data.pkl` - Main turbine data file
- `sample_layout_data.csv` - Wind farm layout file

### 2. Start the Application
```bash
python app.py
```
The application will be available at: http://localhost:8050

### 3. Upload Data
1. **Upload Main Data**: Drag and drop `sample_turbine_data.pkl` into the first upload area
2. **Upload Layout** (Optional): Drag and drop `sample_layout_data.csv` into the second upload area
3. **Review Summary**: Check the data overview panel for successful loading

### 4. Explore Features

#### Main Dashboard
- **Time Range**: Use quick buttons (24h, 7d, 30d) or date picker
- **State Filter**: Filter turbines by operational state
- **Turbine Table**: Sort and filter the turbine list

#### Investigation Panel
1. **Select Turbine**: Click any row in the turbine table
2. **Review Status**: Check current operational state and metrics
3. **Compare Data**: Select adjacent turbines and metmasts for comparison
4. **Analyze Charts**: Review power output, wind speed, and alarm history
5. **Anomaly Detection**: Check for production anomalies

#### Wind Sensor Integrity Analysis
1. **Automatic Display**: The sensor analysis panel appears automatically when data is loaded
2. **Automatic Target**: When you select a turbine in the main table, it automatically becomes the target (🎯 indicator)
3. **Auto-Analysis**: Analysis runs automatically when a turbine is selected and references are chosen
4. **Reference Selection**: Adjacent turbines and metmasts are auto-selected, but you can modify them
5. **Real-time Results**: Charts and analysis update automatically as you change selections

#### Key Features to Test
- **Silent Loss Detection**: Look for turbines with "Unexpected" status
- **Wind Sensor Validation**: Use the dedicated sensor analysis tool
- **Alarm Analysis**: Review alarm patterns and their impact
- **Startup Sequences**: Identify post-alarm and post-low-wind startups
- **Data Export**: Export filtered data using the "📊 Export Data" button in the Data Overview section

## 📊 Understanding Operational States

### Color Coding
- 🟢 **Green**: Producing normally
- 🟡 **Yellow**: Not producing - explained (alarms, curtailment, low wind)
- 🟠 **Orange**: Not producing - verification pending (suspected issues)
- 🔴 **Red**: Not producing - unexpected (potential problems)
- ⚫ **Gray**: Offline/maintenance

### State Categories

#### 1. Producing
- Normal operation with power output > 1.0 kW

#### 2. Not Producing - Explained
- **Alarm Active**: Active alarms preventing operation
- **Curtailment Active**: External or internal power limitations
- **Confirmed Low Wind**: Wind speed below cut-in, confirmed by references
- **Startup Sequences**: Recovery from alarms or low wind conditions

#### 3. Not Producing - Verification Pending
- **Suspected Low Wind**: Low wind but references inconclusive
- **Startup Unclear**: Startup sequence with unclear trigger

#### 4. Not Producing - Unexpected
- **Sensor Error (Low)**: Wind sensor reading contradicted by references
- **Sensor Error (Anomalous)**: Implausible wind sensor readings
- **Mechanical/Control Issue**: Sufficient wind but not producing
- **Unknown**: Unable to determine cause

## 🔧 Configuration

Edit `src/utils/config.py` to adjust:

```python
# Production thresholds
PRODUCTION_THRESHOLD_KW = 1.0  # Power threshold for "producing"
CUT_IN_WIND_SPEED = 3.0        # Minimum wind speed for production

# Sensor validation
WIND_SPEED_DEVIATION_THRESHOLD = 2.0  # Max acceptable deviation (m/s)

# Adjacency
MAX_ADJACENT_TURBINES = 5      # Number of adjacent turbines to consider
```

## 🎯 Use Cases

### 1. Daily Operations
- Monitor turbine states in real-time
- Identify silent losses (unexpected non-production)
- Prioritize maintenance activities

### 2. Performance Analysis
- Compare turbine performance with neighbors
- Validate wind sensor accuracy
- Analyze alarm patterns and impacts

### 3. Troubleshooting
- Investigate specific turbine issues
- Compare with reference data
- Track startup sequences and recovery times

### 4. Reporting
- Generate operational state summaries
- Export detailed turbine data
- Create performance reports

## 🐛 Troubleshooting

### Common Issues

**Data Upload Fails**
- Ensure .pkl file contains a pandas DataFrame
- Check that required columns are present
- Verify file is not corrupted

**No Turbines Showing**
- Check time range selection
- Verify state filter is not too restrictive
- Ensure data was loaded successfully

**Investigation Panel Empty**
- Click on a turbine row to select it
- Ensure filtered data contains the selected turbine
- Check browser console for JavaScript errors

**Charts Not Loading**
- Verify adjacent turbines are selected
- Check that time range contains data
- Ensure metmast columns exist in data

### Performance Tips

- Use smaller time ranges for faster loading
- Limit adjacent turbine selections to 3-5 turbines
- Filter by specific operational states when analyzing issues

## 📝 Data Format Requirements

### Required Columns
- `StationId`: Turbine identifier
- `TimeStamp`: Datetime in 10-minute intervals
- `EffectiveAlarmTime`: Alarm duration in seconds
- `UK Text`: Alarm descriptions
- `Duration 2006(s)`: Internal curtailment duration
- `wtc_ActPower_mean`: Mean active power (kW)
- `wtc_AcWindSp_mean`: Mean wind speed (m/s)
- `wtc_PowerRed_timeon`: External curtailment duration

### Optional Columns
- `met_WindSpeedRot_mean_XX`: Metmast wind speeds
- Layout file: `StationId`, `X-Coordinate`, `Y-Coordinate`

## 🔄 Next Steps

1. **Test with Real Data**: Replace sample data with your actual turbine data
2. **Customize Configuration**: Adjust thresholds for your wind farm
3. **Extend Analysis**: Add custom operational state logic
4. **Integrate Systems**: Connect to your SCADA or data historian
5. **Automate Reports**: Schedule regular analysis runs

## 📞 Support

- Check the main README.md for detailed documentation
- Run `python test_application.py` to verify installation
- Review the application logs for error details
