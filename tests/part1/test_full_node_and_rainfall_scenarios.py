import unittest
from pathlib import Path

import pandas as pd

from backend.iot_control.part1_data_foundation.config import load_config
from backend.iot_control.part1_data_foundation.rainfall_scenario_generator import (
    DEFAULT_SCENARIOS,
    build_scenario_frame,
    generate_default_scenarios,
    run_scenario_smoke_test,
    write_bellinge_dat,
)
from backend.iot_control.part1_data_foundation.run_swmm import _default_sample_node_ids


class FullNodeAndRainfallScenarioTests(unittest.TestCase):
    def test_target_star_selects_all_nodes_and_defaults_raw_off(self):
        config = load_config("config/part1_data_foundation.yaml")
        node_info = pd.DataFrame(
            [
                {"node_id": "N1", "node_type": "junction"},
                {"node_id": "N2", "node_type": "storage"},
            ]
        ).set_index("node_id", drop=False)
        pump_info = pd.DataFrame()

        selected = _default_sample_node_ids(node_info, pump_info, ["*"])

        self.assertEqual(selected, ["N1", "N2"])
        self.assertIn("*", config.target_nodes)
        self.assertFalse(config.save_raw_node_timeseries)

    def test_bellinge_dat_format_and_gages(self):
        frame = build_scenario_frame(DEFAULT_SCENARIOS[0], "2017-06-29 00:00:00", ["rg5425", "rg5427"])
        out_dir = Path("tests/_tmp_rainfall_scenarios")
        path = write_bellinge_dat(frame, out_dir / "light_rain.dat")
        lines = path.read_text(encoding="utf-8").splitlines()

        self.assertTrue(lines)
        self.assertRegex(lines[0], r"^rg5425 \d{4} \d{1,2} \d{1,2} \d{1,2} \d{1,2} [0-9.]+$")
        self.assertEqual({line.split()[0] for line in lines}, {"rg5425", "rg5427"})
        for line in lines[:20]:
            self.assertEqual(len(line.split()), 7)

    def test_generate_default_scenarios_totals(self):
        out_dir = Path("tests/_tmp_rainfall_scenarios")
        paths = generate_default_scenarios(out_dir, "2017-06-29 00:00:00", ["rg5425", "rg5427"])

        manifest = pd.read_csv(paths["scenario_manifest"])
        self.assertEqual(set(manifest["scenario_id"]), {spec.scenario_id for spec in DEFAULT_SCENARIOS})
        for spec in DEFAULT_SCENARIOS:
            frame = pd.read_csv(out_dir / f"{spec.scenario_id}.csv")
            totals = frame.groupby("rain_gage_id")["rainfall_mm"].sum()
            self.assertTrue(all(abs(total - spec.total_rainfall_mm) < 0.01 for total in totals))
            self.assertTrue((out_dir / f"{spec.scenario_id}.dat").exists())

    def test_short_intense_scenario_swmm_smoke(self):
        try:
            import pyswmm  # noqa: F401
        except Exception as exc:
            self.skipTest(f"PySWMM unavailable: {exc}")

        swmm_input = Path("data/raw/swmm/BellingeSWMM_2021_orin_v2.inp")
        if not swmm_input.exists():
            self.skipTest("v2 SWMM input not available")

        out_dir = Path("tests/_tmp_rainfall_scenarios")
        paths = generate_default_scenarios(out_dir, "2017-06-29 00:00:00", ["rg5425", "rg5427"])
        result = run_scenario_smoke_test(
            swmm_input=swmm_input,
            scenario_dat=paths["short_intense_rain"],
            run_dir=Path("tests/_tmp_swmm_scenario_smoke"),
            start_datetime="2017-06-29 00:00:00",
            end_datetime="2017-06-29 02:00:00",
            sample_node_id="G70F100",
        )

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["steps"], 0)
        self.assertGreater(result["max_depth_change_m"], 0.0)


if __name__ == "__main__":
    unittest.main()
