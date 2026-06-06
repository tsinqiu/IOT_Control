import unittest

import pandas as pd

from backend.iot_control.part2_status_assessment.pump_health_assessment import assess_pump_health


class PumpHealthAssessmentTests(unittest.TestCase):
    def test_rolling_24h_and_shared_forebay_metrics(self):
        times = pd.date_range("2017-06-29 00:00:00", periods=5, freq="12h")
        operation = pd.DataFrame(
            [
                {
                    "timestamp": timestamp,
                    "pump_id": "P1",
                    "pump_station_id": "S1",
                    "startup_count_15min": 1,
                    "on_seconds_15min": 900,
                }
                for timestamp in times
            ]
            + [
                {
                    "timestamp": times[-1],
                    "pump_id": "P2",
                    "pump_station_id": "S1",
                    "startup_count_15min": 0,
                    "on_seconds_15min": 0,
                }
            ]
        )
        levels = pd.DataFrame(
            [
                {
                    "timestamp": timestamp,
                    "pump_station_id": "S1",
                    "forebay_node": "N1",
                    "depth_m": 1.0,
                    "head_m": 1.0,
                    "percent_full": 90.0,
                    "level_change_rate_m_per_min": 0.12,
                }
                for timestamp in times
            ]
        )

        result = assess_pump_health(operation, levels)
        p1_latest = result[(result["pump_id"] == "P1") & (result["timestamp"] == times[-1])].iloc[0]
        p2_latest = result[(result["pump_id"] == "P2") & (result["timestamp"] == times[-1])].iloc[0]

        self.assertEqual(p1_latest["startup_count_24h"], 2)
        self.assertEqual(p1_latest["runtime_min_24h"], 30)
        self.assertEqual(p2_latest["max_forebay_percent_full"], 90.0)
        self.assertEqual(p2_latest["max_abs_level_change_rate_m_per_min"], 0.12)

    def test_fatigue_index_and_deduction_fields(self):
        operation = pd.DataFrame(
            [
                {
                    "timestamp": "2017-06-29 00:00:00",
                    "pump_id": "P1",
                    "pump_station_id": "S1",
                    "startup_count_15min": 2,
                    "on_seconds_15min": 900,
                },
                {
                    "timestamp": "2017-06-29 00:15:00",
                    "pump_id": "P1",
                    "pump_station_id": "S1",
                    "startup_count_15min": 1,
                    "on_seconds_15min": 900,
                },
            ]
        )
        levels = pd.DataFrame(
            [
                {
                    "timestamp": "2017-06-29 00:15:00",
                    "pump_station_id": "S1",
                    "forebay_node": "N1",
                    "depth_m": 1.0,
                    "head_m": 1.0,
                    "percent_full": 98.0,
                    "level_change_rate_m_per_min": 0.2,
                }
            ]
        )

        result = assess_pump_health(operation, levels)
        row = result.iloc[-1]

        self.assertIn("repeated_start_count_30min", result.columns)
        self.assertIn("continuous_runtime_min", result.columns)
        self.assertIn("max_forebay_percent_full", result.columns)
        self.assertIn("max_abs_level_change_rate_m_per_min", result.columns)
        self.assertIn("deduction_detail", result.columns)
        self.assertAlmostEqual(row["fatigue_index"], 1 - row["health_score"] / 100)
        self.assertNotEqual(row["deduction_detail"], "none")

    def test_24h_runtime_load_deducts_long_running_pumps(self):
        operation = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp("2017-06-29 00:00:00") + pd.Timedelta(minutes=15 * i),
                    "pump_id": "P1",
                    "pump_station_id": "S1",
                    "startup_count_15min": 0,
                    "on_seconds_15min": 900,
                }
                for i in range(96)
            ]
        )
        levels = pd.DataFrame()

        result = assess_pump_health(operation, levels)
        row = result.iloc[-1]

        self.assertEqual(row["runtime_min_24h"], 1440)
        self.assertLess(row["health_score"], 85)
        self.assertIn("24h runtime load", row["deduction_detail"])


if __name__ == "__main__":
    unittest.main()
