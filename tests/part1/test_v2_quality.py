import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


class V2QualityTests(unittest.TestCase):
    def test_static_tables_mark_v2_added_objects(self):
        from backend.iot_control.part1_data_foundation.parse_inp import build_static_tables, parse_inp_file

        model = parse_inp_file(FIXTURE_ROOT / "model.inp")
        tables = build_static_tables(model)

        pump = tables["pump_info"].set_index("pump_id").loc["G71F320Pp1"]
        self.assertEqual(pump["model_version"], "v2")
        self.assertEqual(int(pump["is_added"]), 1)

        node = tables["node_info"].set_index("node_id").loc["G_ADD"]
        self.assertEqual(node["model_version"], "v2")
        self.assertEqual(int(node["is_added"]), 1)

        facility = tables["facility_info"].set_index("facility_id").loc["G_ADD"]
        self.assertEqual(facility["model_version"], "v2")
        self.assertEqual(int(facility["is_added"]), 1)

    def test_quality_checker_reports_added_objects(self):
        from backend.iot_control.part1_data_foundation.check_csv_quality import run_quality_check

        work = ROOT / "tests" / "_tmp_quality"
        csv_dir = work / "csv"
        report_dir = work / "reports"
        schema_path = work / "schema.sql"
        csv_dir.mkdir(parents=True, exist_ok=True)

        pd.DataFrame(
            [{"timestamp": "2012-06-29 00:01", "rain_gage_id": "rg1", "rainfall_mm": 1.0, "time_interval_min": 1, "source_file": "rain.dat"}]
        ).to_csv(csv_dir / "rainfall_observed.csv", index=False)
        pd.DataFrame(
            [{"forecast_time": "2012-06-29 00:01", "target_time": "2012-06-29 00:01", "rain_gage_id": "rg1", "forecast_horizon_min": 0, "forecast_rainfall_mm": 1.0, "source": "test"}]
        ).to_csv(csv_dir / "rainfall_forecast_scenario.csv", index=False)
        pd.DataFrame(
            [
                {"node_id": "G71F320", "node_type": "storage", "depth_m": 0, "model_version": "v2", "is_added": 1},
                {"node_id": "G_ADD", "node_type": "outfall", "model_version": "v2", "is_added": 1},
            ]
        ).to_csv(csv_dir / "node_info.csv", index=False)
        pd.DataFrame([{"link_id": "C1"}]).to_csv(csv_dir / "conduit_info.csv", index=False)
        pd.DataFrame([{"pump_id": "G71F320Pp1", "pump_station_id": "G71F320", "model_version": "v2", "is_added": 1}]).to_csv(csv_dir / "pump_info.csv", index=False)
        pd.DataFrame([{"facility_id": "G_ADD", "facility_type": "outfall", "model_version": "v2", "is_added": 1}]).to_csv(csv_dir / "facility_info.csv", index=False)
        pd.DataFrame([{"subcatchment_id": "S1"}]).to_csv(csv_dir / "subcatchment_info.csv", index=False)
        pd.DataFrame(
            [{"timestamp": "2012-06-29 00:01", "node_id": "G71F320", "depth_m": 0, "flooding_cms": 0, "risk_level": "green"}]
        ).to_csv(csv_dir / "node_level_timeseries.csv", index=False)
        pd.DataFrame(
            [{"timestamp": "2012-06-29 00:01", "pump_station_id": "G71F320", "forebay_node": "G71F320", "depth_m": 0}]
        ).to_csv(csv_dir / "pump_station_level_timeseries.csv", index=False)
        pd.DataFrame(
            [{"timestamp": "2012-06-29 00:01", "pump_id": "G71F320Pp1", "pump_station_id": "G71F320", "flow_cms": 0, "startup_count_cumulative": 0, "runtime_min_cumulative": 0}]
        ).to_csv(csv_dir / "pump_operation_timeseries.csv", index=False)
        pd.DataFrame(
            [{"timestamp": "2012-06-29 00:01", "pump_id": "G71F320Pp1", "pump_station_id": "G71F320", "flow_cms": 0, "estimated_power_kw": 0, "pump_head_m": 0, "energy_kwh_interval": 0, "cumulative_energy_kwh": 0, "unit_energy_kwh_per_kt": 0}]
        ).to_csv(csv_dir / "pump_energy_timeseries.csv", index=False)
        pd.DataFrame(
            [{"timestamp": "2012-06-29 00:01", "gate_id": "GATE1", "status": "closed"}]
        ).to_csv(csv_dir / "gate_operation_timeseries.csv", index=False)
        schema_path.write_text("CREATE TABLE pump_info (pump_id NVARCHAR(128), model_version NVARCHAR(32), is_added BIT);\nCREATE INDEX IX_pump_info_pump_id ON pump_info(pump_id);\n", encoding="utf-8")

        result = run_quality_check(csv_dir=csv_dir, report_path=report_dir / "csv_quality_check_report.md", schema_path=schema_path)

        self.assertTrue(result.report_path.exists())
        self.assertIn("[OK] G71F320Pp1 found in pump_info.csv", result.console_lines)
        self.assertIn("[OK] G_ADD found in node_info/facility_info", result.console_lines)


if __name__ == "__main__":
    unittest.main()
