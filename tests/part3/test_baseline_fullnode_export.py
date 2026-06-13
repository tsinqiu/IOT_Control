import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backend.iot_control.part3_optimization.baseline_fullnode_export import export_baseline_fullnode_csv


class BaselineFullNodeExportTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("tests/_tmp_part3_baseline_fullnode_export") / f"{self._testMethodName}_{uuid.uuid4().hex}"
        self.config_path = self.root / "part1_data_foundation.yaml"
        self.csv_dir = self.root / "processed" / "part1_csv"
        self.swmm_run_dir = self.root / "swmm_runs"
        self.baseline_dir = self.swmm_run_dir / "part3_baseline" / "scenario_2"
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        (self.baseline_dir / "scenario_02.inp").write_text("[TITLE]\nscenario_02\n", encoding="utf-8")
        (self.baseline_dir / "scenario_02_rg5425.dat").write_text("rg5425 2017 6 29 0 0 0.1\n", encoding="utf-8")
        (self.baseline_dir / "scenario_02_rg5427.dat").write_text("rg5427 2017 6 29 0 0 0.2\n", encoding="utf-8")
        (self.baseline_dir / "scenario_info.json").write_text(
            json.dumps({"scenario_id": "scenario_02", "total_rainfall_mm": 38.5, "peak_minute_rainfall_mm": 0.33}),
            encoding="utf-8",
        )
        (self.baseline_dir / "baseline_info.json").write_text(
            json.dumps({"baseline_scenario_id": "scenario_2", "source_scenario_id": "scenario_02"}),
            encoding="utf-8",
        )
        self.config_path.write_text(
            "\n".join(
                [
                    "paths:",
                    f"  swmm_input: {(self.baseline_dir / 'scenario_02.inp').as_posix()}",
                    "  rainfall_input: data/raw/rainfall/rg_bellinge_Jun2010_Aug2021.dat",
                    f"  csv_dir: {self.csv_dir.as_posix()}",
                    "  report_dir: outputs/reports/part1",
                    "  log_dir: outputs/logs",
                    f"  swmm_run_dir: {self.swmm_run_dir.as_posix()}",
                    "  interim_dir: data/interim/part1",
                    "  database_dir: database/part1",
                    "  docs_dir: docs/part1",
                    "simulation:",
                    '  start_datetime: "2017-06-29 00:00:00"',
                    '  end_datetime: "2017-06-29 01:00:00"',
                    "  raw_sample_step_sec: 900",
                    "  report_step_min: 15",
                ]
            ),
            encoding="utf-8",
        )

    def test_export_writes_four_csvs_copies_dat_files_and_runs_prepare(self):
        dynamic_tables = {
            "node_level_timeseries": pd.DataFrame(
                [{"timestamp": "2017-06-29 00:15:00", "node_id": "N1", "depth_m_max": 0.1}]
            ),
            "pump_operation_timeseries": pd.DataFrame(
                [{"timestamp": "2017-06-29 00:15:00", "pump_id": "P1", "startup_count_15min": 1}]
            ),
            "pump_energy_timeseries": pd.DataFrame(
                [{"timestamp": "2017-06-29 00:15:00", "pump_id": "P1", "energy_kwh_interval": 0.5}]
            ),
            "pump_station_level_timeseries": pd.DataFrame(
                [{"timestamp": "2017-06-29 00:15:00", "pump_station_id": "S1", "forebay_node": "N1"}]
            ),
            "raw_node_timeseries": pd.DataFrame([{"should": "not_be_written"}]),
        }

        with (
            patch(
                "backend.iot_control.part3_optimization.baseline_fullnode_export.parse_inp_file",
                return_value=object(),
            ),
            patch(
                "backend.iot_control.part3_optimization.baseline_fullnode_export.build_static_tables",
                return_value={"node_info": pd.DataFrame(), "pump_info": pd.DataFrame()},
            ),
            patch(
                "backend.iot_control.part3_optimization.baseline_fullnode_export.run_pyswmm",
                return_value=dynamic_tables,
            ) as run_mock,
            patch(
                "backend.iot_control.part3_optimization.baseline_fullnode_export.prepare_baseline",
                return_value={"status": "assessment_generated"},
            ) as prepare_mock,
        ):
            result = export_baseline_fullnode_csv(self.config_path, "scenario_02")

        result_dir = self.csv_dir.parent / "part3_optimization" / "baseline_scenario_2"
        run_dir = self.baseline_dir / "full_node_run"
        self.assertEqual(result["status"], "exported")
        self.assertTrue((run_dir / "scenario_02_rg5425.dat").exists())
        self.assertTrue((run_dir / "scenario_02_rg5427.dat").exists())
        for name in [
            "node_level_timeseries.csv",
            "pump_operation_timeseries.csv",
            "pump_energy_timeseries.csv",
            "pump_station_level_timeseries.csv",
        ]:
            self.assertTrue((result_dir / name).exists())
        self.assertFalse((result_dir / "raw_node_timeseries.csv").exists())
        kwargs = run_mock.call_args.kwargs
        self.assertEqual(kwargs["target_nodes"], ["*"])
        self.assertFalse(kwargs["save_raw_node_timeseries"])
        prepare_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
