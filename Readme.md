# IOT Control

This project builds a staged drainage-network and pump-station control analysis workflow from the Bellinge SWMM model.

- Part 1 builds the multi-source, cleaned, time-aligned base dataset.
- Part 2 evaluates current energy efficiency, pump safety, and overflow risk from the Part 1 CSV outputs.

## Part 1 Data Foundation

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

## Part 2 Status Assessment

Part 2 reads the Part 1 CSV files directly from `data/processed/part1_csv/` and writes assessment outputs to `data/processed/part2_assessment_csv/`. It does not use SQL Server.

Generate assessment CSV files:

```powershell
.\.venv\Scripts\python.exe -m backend.iot_control.part2_status_assessment.main --all --config config\part2_status_assessment.yaml
```

Generated Part 2 CSV outputs:

- `energy_assessment_timeseries.csv`: pump energy-efficiency assessment by time window.
- `pump_energy_summary.csv`: full-period pump energy summary and ranking.
- `pump_health_assessment.csv`: pump safety and health assessment by time window.
- `overflow_risk_assessment.csv`: node overflow-risk assessment by time window.
- `system_status_summary.csv`: latest system summary.

Start the FastAPI backend:

```powershell
.\.venv\Scripts\uvicorn backend.iot_control.api.main:app --host 127.0.0.1 --port 8010 --reload
```

Start the Vue3 dashboard:

```powershell
cd frontend
npm install
$env:VITE_API_BASE="http://127.0.0.1:8010"
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

The dashboard supports `最新窗口`, `过去24h`, and `全周期` views. For range views, the tables show each object's worst record or summary ranking within the selected range.

Note: `pump_health_assessment.csv` keeps the backend `deduction_detail` field in English for reproducibility. The Vue3 dashboard translates these deduction details into Chinese for report screenshots and presentation.
