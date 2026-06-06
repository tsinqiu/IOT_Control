import unittest
from pathlib import Path

import pandas as pd


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


class ParserTests(unittest.TestCase):
    def test_parse_rainfall_rows(self):
        from backend.iot_control.part1_data_foundation.parse_rainfall import parse_rainfall_file

        frame, stats = parse_rainfall_file(FIXTURE_ROOT / "rain.dat")

        self.assertEqual(list(frame.columns), ["timestamp", "rain_gage_id", "rainfall_mm", "time_interval_min", "source_file"])
        self.assertEqual(len(frame), 2)
        self.assertEqual(stats["unparsed_rows"], 1)
        self.assertAlmostEqual(frame["rainfall_mm"].sum(), 0.25)

    def test_forecast_scenario_is_minutely_for_full_horizon(self):
        from backend.iot_control.part1_data_foundation.parse_rainfall import build_forecast_scenario

        observed = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:00:00", "rain_gage_id": "RG1", "rainfall_mm": 1.5},
                {"timestamp": "2017-06-29 00:02:00", "rain_gage_id": "RG1", "rainfall_mm": 0.5},
            ]
        )

        forecast = build_forecast_scenario(observed, "2017-06-29 00:00:00", forecast_hours=1)

        self.assertEqual(len(forecast), 60)
        self.assertEqual(forecast["forecast_horizon_min"].iloc[0], 0)
        self.assertEqual(forecast["forecast_horizon_min"].iloc[-1], 59)
        self.assertAlmostEqual(forecast["forecast_rainfall_mm"].sum(), 2.0)
        self.assertAlmostEqual(forecast.loc[forecast["forecast_horizon_min"] == 1, "forecast_rainfall_mm"].iloc[0], 0.0)

    def test_parse_inp_sections_and_nodes(self):
        from backend.iot_control.part1_data_foundation.parse_inp import build_static_tables, parse_inp_file

        model = parse_inp_file(FIXTURE_ROOT / "model.inp")
        tables = build_static_tables(model)

        self.assertIn("JUNCTIONS", model.sections)
        self.assertEqual(tables["node_info"].shape[0], 4)
        self.assertEqual(tables["pump_info"].iloc[0]["pump_station_id"], "G70F11")
        self.assertAlmostEqual(tables["conduit_info"].iloc[0]["slope"], 0.01)

    def test_swmm_run_copy_dates_are_rewritten_from_config(self):
        from backend.iot_control.part1_data_foundation.run_swmm import _rewrite_swmm_datetime_options

        work = FIXTURE_ROOT.parent / "_tmp_rewrite_inp.inp"
        work.write_text(
            "[OPTIONS]\n"
            "START_DATE           06/29/2017\n"
            "START_TIME           00:01:00\n"
            "REPORT_START_DATE    06/29/2017\n"
            "REPORT_START_TIME    04:00:00\n"
            "END_DATE             06/30/2017\n"
            "END_TIME             00:00:00\n",
            encoding="utf-8",
        )

        _rewrite_swmm_datetime_options(work, "2017-06-29 00:00:00", "2017-07-03 23:59:59")
        content = work.read_text(encoding="utf-8")
        options = {
            line.split()[0]: line.split()[1]
            for line in content.splitlines()
            if line.strip() and not line.startswith("[")
        }

        self.assertEqual(options["START_TIME"], "00:00:00")
        self.assertEqual(options["REPORT_START_TIME"], "00:00:00")
        self.assertEqual(options["END_DATE"], "07/03/2017")
        self.assertEqual(options["END_TIME"], "23:59:59")


if __name__ == "__main__":
    unittest.main()
