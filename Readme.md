# IOT Control SWMM Data Export

This project exports structured CSV datasets from the Bellinge SWMM model and historical rainfall data.

## Run

Use the virtual environment in this folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m backend.iot_control.part1_data_foundation.main --all --config config\part1_data_foundation.yaml
```

The command writes part 1 CSV files to `data/processed/part1_csv/`, reports to `outputs/reports/part1/`, documentation to `docs/part1/`, and SQL Server DDL to `database/part1/schema.sql`.

## CSV outputs

- `rainfall_observed.csv`: minute rainfall observations from `rg_bellinge_Jun2010_Aug2021.dat`, in millimeters.
- `rainfall_forecast_scenario.csv`: a 72 hour forecast scenario built from historical rainfall around the configured start time.
- `node_info.csv`: junction, storage, and outfall attributes from the SWMM INP file.
- `conduit_info.csv`: conduit topology, shape, roughness, offsets, and estimated slope.
- `pump_info.csv`: pump links, pump station grouping, startup/shutoff depths, and curve points.
- `facility_info.csv`: orifices, weirs, outlets, and outfalls.
- `subcatchment_info.csv`: catchment, imperviousness, outlet, and polygon metadata.
- `node_level_timeseries.csv`: simulated or fallback node depth/head/flooding values.
- `pump_station_level_timeseries.csv`: forebay level series by pump station.
- `pump_energy_timeseries.csv`: estimated power and energy by pump.
- `pump_operation_timeseries.csv`: pump on/off, runtime, starts, and flow.

PySWMM is attempted for dynamic time series. If the local SWMM runtime cannot execute the model, the pipeline writes zero baseline time series over the configured period and records the reason in `docs/part1/data_quality_report.md`.
