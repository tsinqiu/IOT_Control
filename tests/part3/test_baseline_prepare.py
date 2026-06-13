import json
import unittest
import uuid
from pathlib import Path

import pandas as pd

from backend.iot_control.part3_optimization.baseline_prepare import (
    BASELINE_METRIC_COLUMNS,
    KEY_NODE_COLUMNS,
    KEY_PUMP_COLUMNS,
    prepare_baseline,
)


class BaselinePrepareTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("tests/_tmp_part3_baseline_prepare") / f"{self._testMethodName}_{uuid.uuid4().hex}"
        self.config_path = self.root / "part1_data_foundation.yaml"
        self.csv_dir = self.root / "processed" / "part1_csv"
        self.swmm_run_dir = self.root / "swmm_runs"
        self.candidate_dir = self.swmm_run_dir / "part3_scenario_candidates" / "scenario_02"
        self.source_inp = self.candidate_dir / "scenario_02.inp"
        self.full_result_dir = self.csv_dir.parent / "part3_optimization" / "baseline_scenario_2"

        self.candidate_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self.source_inp.write_text("[TITLE]\nscenario_02\n", encoding="utf-8")
        (self.candidate_dir / "scenario_02_rg5425.dat").write_text("rg5425 2017 6 29 0 0 0.1\n", encoding="utf-8")
        (self.candidate_dir / "scenario_02_rg5427.dat").write_text("rg5427 2017 6 29 0 0 0.2\n", encoding="utf-8")
        (self.candidate_dir / "scenario_info.json").write_text(
            json.dumps(
                {
                    "scenario_id": "scenario_02",
                    "total_rainfall_mm": 38.54508,
                    "peak_minute_rainfall_mm": 0.33333,
                }
            ),
            encoding="utf-8",
        )
        self.config_path.write_text(
            "\n".join(
                [
                    "paths:",
                    f"  swmm_input: {self.source_inp.as_posix()}",
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
                    '  end_datetime: "2017-07-03 23:59:59"',
                ]
            ),
            encoding="utf-8",
        )
        self._write_static_tables()

    def _write_static_tables(self):
        pd.DataFrame(
            [
                {"node_id": "N1", "node_type": "junction", "max_depth": 1.0, "is_storage": False, "is_pump_station_forebay": False},
                {"node_id": "N2", "node_type": "storage", "max_depth": 2.0, "is_storage": True, "is_pump_station_forebay": False},
                {"node_id": "N3", "node_type": "junction", "max_depth": 1.0, "is_storage": False, "is_pump_station_forebay": False},
                {"node_id": "G71F320", "node_type": "storage", "max_depth": 3.0, "is_storage": True, "is_pump_station_forebay": True},
                {"node_id": "G_ADD", "node_type": "storage", "max_depth": 2.5, "is_storage": True, "is_pump_station_forebay": True},
            ]
        ).to_csv(self.csv_dir / "node_info.csv", index=False)
        pd.DataFrame(
            [
                {"pump_id": "P1", "inlet_node": "N1", "outlet_node": "N2"},
                {"pump_id": "P2", "inlet_node": "G71F320", "outlet_node": "G_ADD"},
            ]
        ).to_csv(self.csv_dir / "pump_info.csv", index=False)

    def _write_full_results(self):
        self.full_result_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:15:00", "node_id": "N1", "node_type": "junction", "depth_m_max": 0.7, "flooding_volume_m3_15min": 0.0, "risk_level": "orange"},
                {"timestamp": "2017-06-29 00:30:00", "node_id": "N1", "node_type": "junction", "depth_m_max": 0.9, "flooding_volume_m3_15min": 4.0, "risk_level": "red"},
                {"timestamp": "2017-06-29 00:15:00", "node_id": "N2", "node_type": "storage", "depth_m_max": 1.0, "flooding_volume_m3_15min": 0.0, "risk_level": "green"},
                {"timestamp": "2017-06-29 00:15:00", "node_id": "N3", "node_type": "junction", "depth_m_max": 0.8, "flooding_volume_m3_15min": 0.0, "risk_level": "yellow"},
                {"timestamp": "2017-06-29 00:15:00", "node_id": "G71F320", "node_type": "storage", "depth_m_max": 1.2, "flooding_volume_m3_15min": 0.0, "risk_level": "green"},
            ]
        ).to_csv(self.full_result_dir / "node_level_timeseries.csv", index=False)
        pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "P1", "on_seconds_15min": 900, "startup_count_15min": 1},
                {"timestamp": "2017-06-29 00:30:00", "pump_id": "P1", "on_seconds_15min": 900, "startup_count_15min": 1},
                {"timestamp": "2017-06-29 01:00:00", "pump_id": "P2", "on_seconds_15min": 300, "startup_count_15min": 1},
            ]
        ).to_csv(self.full_result_dir / "pump_operation_timeseries.csv", index=False)
        pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "P1", "energy_kwh_interval": 3.0, "unit_energy_kwh_per_kt": 2.0},
                {"timestamp": "2017-06-29 00:30:00", "pump_id": "P1", "energy_kwh_interval": 4.0, "unit_energy_kwh_per_kt": 3.0},
                {"timestamp": "2017-06-29 01:00:00", "pump_id": "P2", "energy_kwh_interval": 2.0, "unit_energy_kwh_per_kt": 1.0},
            ]
        ).to_csv(self.full_result_dir / "pump_energy_timeseries.csv", index=False)
        pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:15:00", "pump_station_id": "S1", "forebay_node": "N1", "percent_full": 90.0},
            ]
        ).to_csv(self.full_result_dir / "pump_station_level_timeseries.csv", index=False)

    def test_prepare_baseline_copies_scenario_and_writes_note_when_full_results_missing(self):
        result = prepare_baseline(self.config_path, "scenario_2")

        baseline_dir = self.swmm_run_dir / "part3_baseline" / "scenario_2"
        self.assertEqual(result["status"], "missing_full_results")
        self.assertTrue((baseline_dir / "scenario_02.inp").exists())
        self.assertTrue((baseline_dir / "scenario_02_rg5425.dat").exists())
        self.assertTrue((baseline_dir / "scenario_02_rg5427.dat").exists())
        self.assertTrue((baseline_dir / "scenario_info.json").exists())
        self.assertTrue((baseline_dir / "baseline_info.json").exists())
        self.assertTrue((baseline_dir / "manual_run_note.md").exists())
        self.assertFalse((self.csv_dir.parent / "part3_optimization" / "baseline_assessment" / "baseline_metrics.csv").exists())

    def test_prepare_baseline_generates_metrics_and_key_tables_when_full_results_exist(self):
        self._write_full_results()

        result = prepare_baseline(self.config_path, "scenario_2")

        assessment_dir = self.csv_dir.parent / "part3_optimization" / "baseline_assessment"
        metrics = pd.read_csv(assessment_dir / "baseline_metrics.csv")
        key_nodes = pd.read_csv(assessment_dir / "key_nodes_for_optimization.csv")
        key_pumps = pd.read_csv(assessment_dir / "key_pumps_for_optimization.csv")

        self.assertEqual(result["status"], "assessment_generated")
        self.assertEqual(list(metrics.columns), BASELINE_METRIC_COLUMNS)
        self.assertEqual(list(key_nodes.columns), KEY_NODE_COLUMNS)
        self.assertEqual(list(key_pumps.columns), KEY_PUMP_COLUMNS)
        row = metrics.iloc[0]
        self.assertEqual(row["scenario_id"], "scenario_2")
        self.assertAlmostEqual(row["max_node_depth_m"], 1.2)
        self.assertAlmostEqual(row["max_level_ratio"], 0.9)
        self.assertEqual(row["orange_red_node_count"], 1)
        self.assertEqual(row["flooded_node_count"], 1)
        self.assertEqual(row["flooding_window_count"], 1)
        self.assertAlmostEqual(row["total_flooding_volume_m3"], 4.0)
        self.assertAlmostEqual(row["total_pump_energy_kwh"], 9.0)
        self.assertEqual(row["total_startup_count"], 3)
        self.assertEqual(row["repeated_start_count_30min"], 1)
        self.assertEqual(row["worst_energy_pump"], "P1")
        self.assertEqual(row["worst_health_pump"], "P1")
        self.assertEqual(row["worst_risk_node"], "N1")
        self.assertIn("N1", set(key_nodes["node_id"]))
        self.assertIn("G71F320", set(key_nodes["node_id"]))
        self.assertIn("G_ADD", set(key_nodes["node_id"]))
        self.assertEqual(set(key_pumps["pump_id"]), {"P1", "P2"})


if __name__ == "__main__":
    unittest.main()
