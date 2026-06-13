import json
import unittest
from pathlib import Path

import pandas as pd

from backend.iot_control.part3_optimization.scenario_generator import (
    MANIFEST_COLUMNS,
    generate_candidate_scenarios,
)


class Part3ScenarioGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("tests/_tmp_part3_scenario_generator")
        self.root.mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / "part1_data_foundation.yaml"
        self.inp_path = self.root / "model.inp"
        self.rain_path = self.root / "historical.dat"
        self.swmm_run_dir = self.root / "swmm_runs"
        self.processed_dir = self.root / "processed_csv"

        self.inp_path.write_text(
            "\n".join(
                [
                    "[OPTIONS]",
                    "START_DATE           06/29/2017",
                    "START_TIME           00:00:00",
                    "END_DATE             07/03/2017",
                    "END_TIME             23:59:59",
                    "",
                    "[RAINGAGES]",
                    'rg5425           VOLUME    00:01    1        FILE       "old.dat" rg5425     MM',
                    'rg5427           VOLUME    00:01    1        FILE       "old.dat" rg5427     MM',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._write_historical_rainfall()
        self.config_path.write_text(
            "\n".join(
                [
                    "paths:",
                    f"  swmm_input: {self.inp_path.as_posix()}",
                    f"  rainfall_input: {self.rain_path.as_posix()}",
                    f"  csv_dir: {self.processed_dir.as_posix()}",
                    "  report_dir: outputs/reports/part1",
                    "  log_dir: outputs/logs",
                    f"  swmm_run_dir: {self.swmm_run_dir.as_posix()}",
                    "  interim_dir: data/interim/part1",
                    "  database_dir: database/part1",
                    "  docs_dir: docs/part1",
                    "simulation:",
                    '  start_datetime: "2017-06-29 00:00:00"',
                    '  end_datetime: "2017-07-03 23:59:59"',
                    "  raw_sample_step_sec: 900",
                    "  report_step_min: 15",
                    "forecast:",
                    "  hours: 72",
                ]
            ),
            encoding="utf-8",
        )

    def _write_historical_rainfall(self):
        lines = []
        events = [
            (pd.Timestamp("2016-06-01 00:00:00"), 6, 0.05),
            (pd.Timestamp("2016-06-10 06:00:00"), 12, 0.08),
            (pd.Timestamp("2016-07-01 12:00:00"), 6, 0.12),
            (pd.Timestamp("2016-07-20 00:00:00"), 12, 0.10),
        ]
        for start, hours, base in events:
            for minute in range(hours * 60):
                timestamp = start + pd.Timedelta(minutes=minute)
                for gage, factor in {"rg5425": 1.0, "rg5427": 0.7}.items():
                    value = base * factor
                    lines.append(
                        f"{gage} {timestamp.year} {timestamp.month} {timestamp.day} "
                        f"{timestamp.hour} {timestamp.minute} {value:.5f}"
                    )
        self.rain_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_generate_candidate_scenarios_writes_manifest_and_manual_inputs_only(self):
        manifest = generate_candidate_scenarios(self.config_path)

        self.assertEqual(len(manifest), 12)
        self.assertEqual(list(manifest.columns), MANIFEST_COLUMNS)
        self.assertEqual(set(manifest["manual_run_status"]), {"pending"})
        self.assertGreaterEqual(set(manifest["peak_day"]), {1, 2, 3})
        self.assertGreaterEqual(set(manifest["duration_hours"]), {6, 12})

        manifest_path = self.root / "processed_csv" / ".." / "part3_optimization" / "scenario_manifest.csv"
        self.assertTrue(manifest_path.resolve().exists())

        for row in manifest.itertuples(index=False):
            scenario_dir = Path(row.scenario_dir)
            self.assertTrue(scenario_dir.exists())
            self.assertTrue(Path(row.inp_path).exists())
            self.assertTrue(Path(row.rg5425_dat_path).exists())
            self.assertTrue(Path(row.rg5427_dat_path).exists())
            self.assertTrue((scenario_dir / "scenario_info.json").exists())
            info = json.loads((scenario_dir / "scenario_info.json").read_text(encoding="utf-8"))
            self.assertEqual(info["scenario_id"], row.scenario_id)
            self.assertEqual(info["manual_run_status"], "pending")
            inp_text = Path(row.inp_path).read_text(encoding="utf-8")
            self.assertIn(Path(row.rg5425_dat_path).name, inp_text)
            self.assertIn(Path(row.rg5427_dat_path).name, inp_text)
            self.assertFalse((scenario_dir / "node_level_timeseries.csv").exists())
            self.assertFalse((scenario_dir / "pump_energy_timeseries.csv").exists())


if __name__ == "__main__":
    unittest.main()
