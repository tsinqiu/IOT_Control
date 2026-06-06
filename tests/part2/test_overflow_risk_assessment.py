import unittest

import pandas as pd

from backend.iot_control.part2_status_assessment.overflow_risk_assessment import assess_overflow_risk


class OverflowRiskAssessmentTests(unittest.TestCase):
    def test_level_ratio_handles_outfall_and_depth_zero(self):
        node_level = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:00:00", "node_id": "O1", "node_type": "outfall", "depth_m_max": 10, "flooding_cms_max_15min": 0},
                {"timestamp": "2017-06-29 00:00:00", "node_id": "N1", "node_type": "junction", "depth_m_max": 10, "flooding_cms_max_15min": 0},
            ]
        )
        node_info = pd.DataFrame(
            [
                {"node_id": "O1", "node_type": "outfall", "max_depth": 0, "x_coord": 1, "y_coord": 1},
                {"node_id": "N1", "node_type": "junction", "max_depth": 5, "x_coord": 2, "y_coord": 2},
            ]
        )
        rain = pd.DataFrame(columns=["target_time", "rain_gage_id", "forecast_rainfall_mm"])

        result = assess_overflow_risk(node_level, node_info, rain)

        self.assertEqual(result[result["node_id"] == "O1"].iloc[0]["level_ratio"], 0)
        self.assertEqual(result[result["node_id"] == "N1"].iloc[0]["level_score"], 1)

    def test_rain_scores_history_and_current_flooding_rules(self):
        node_level = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:00:00", "node_id": "N1", "node_type": "junction", "depth_m_max": 0.5, "flooding_cms_max_15min": 0},
                {"timestamp": "2017-06-29 00:15:00", "node_id": "N1", "node_type": "junction", "depth_m_max": 0.5, "flooding_cms_max_15min": 0.1},
                {"timestamp": "2017-06-29 00:30:00", "node_id": "N2", "node_type": "junction", "depth_m_max": 0.5, "flooding_cms_max_15min": 0},
            ]
        )
        node_info = pd.DataFrame(
            [
                {"node_id": "N1", "node_type": "junction", "max_depth": 1, "x_coord": 1, "y_coord": 1},
                {"node_id": "N2", "node_type": "junction", "max_depth": 1, "x_coord": 2, "y_coord": 2},
            ]
        )
        rain = pd.DataFrame(
            [
                {"target_time": pd.Timestamp("2017-06-29 00:00:00") + pd.Timedelta(minutes=i), "rain_gage_id": "R1", "forecast_rainfall_mm": 1.0}
                for i in range(120)
            ]
        )

        result = assess_overflow_risk(node_level, node_info, rain)
        current = result[(result["node_id"] == "N1") & (result["timestamp"] == pd.Timestamp("2017-06-29 00:15:00"))].iloc[0]
        history = result[(result["node_id"] == "N1") & (result["timestamp"] == pd.Timestamp("2017-06-29 00:00:00"))].iloc[0]
        no_history = result[result["node_id"] == "N2"].iloc[0]

        self.assertIn("overflow_risk_score", result.columns)
        self.assertNotIn("overflow_probability", result.columns)
        self.assertEqual(history["rain_1h_score"], 1)
        self.assertEqual(history["rain_2h_score"], 1)
        self.assertEqual(history["flooding_history_score"], 0.5)
        self.assertEqual(no_history["flooding_history_score"], 0)
        self.assertEqual(current["flooding_history_score"], 1)
        self.assertEqual(current["risk_grade"], "red")
        self.assertGreaterEqual(current["overflow_risk_score"], 0.80)

    def test_observed_rainfall_replay_is_used_when_forecast_does_not_cover_window(self):
        node_level = pd.DataFrame(
            [
                {
                    "timestamp": "2017-07-03 23:45:00",
                    "node_id": "N1",
                    "node_type": "junction",
                    "depth_m_max": 0.0,
                    "flooding_cms_max_15min": 0,
                }
            ]
        )
        node_info = pd.DataFrame(
            [{"node_id": "N1", "node_type": "junction", "max_depth": 1, "x_coord": 1, "y_coord": 1}]
        )
        forecast = pd.DataFrame(
            [
                {
                    "target_time": pd.Timestamp("2017-07-03 23:45:00") + pd.Timedelta(minutes=i),
                    "rain_gage_id": "R1",
                    "forecast_rainfall_mm": 0.0,
                }
                for i in range(30)
            ]
        )
        observed = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp("2017-07-03 23:45:00") + pd.Timedelta(minutes=i),
                    "rain_gage_id": "R1",
                    "rainfall_mm": 1.0,
                }
                for i in range(120)
            ]
        )

        result = assess_overflow_risk(node_level, node_info, forecast, observed)
        row = result.iloc[0]

        self.assertEqual(row["rainfall_source_1h"], "observed_replay")
        self.assertEqual(row["rainfall_source_2h"], "observed_replay")
        self.assertEqual(row["rain_1h_score"], 1)
        self.assertEqual(row["rain_2h_score"], 1)


if __name__ == "__main__":
    unittest.main()
