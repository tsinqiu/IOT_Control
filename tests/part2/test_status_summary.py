import unittest

import pandas as pd

from backend.iot_control.part2_status_assessment.status_summary import SUMMARY_COLUMNS, build_system_summary


class StatusSummaryTests(unittest.TestCase):
    def test_summary_uses_latest_window_only(self):
        energy = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:00:00", "pump_id": "old_red", "energy_grade": "red", "energy_redundancy_ratio": 9},
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "latest_orange", "energy_grade": "orange", "energy_redundancy_ratio": 0.4},
            ]
        )
        health = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "bad_pump", "health_score": 60, "safety_grade": "orange"},
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "good_pump", "health_score": 90, "safety_grade": "green"},
            ]
        )
        overflow = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:15:00", "node_id": "risk_node", "risk_grade": "red", "overflow_risk_score": 0.9},
                {"timestamp": "2017-06-29 00:15:00", "node_id": "safe_node", "risk_grade": "green", "overflow_risk_score": 0.1},
            ]
        )

        summary = build_system_summary(energy, health, overflow)
        row = summary.iloc[0]

        self.assertEqual(list(summary.columns), SUMMARY_COLUMNS)
        self.assertEqual(row["latest_timestamp"], pd.Timestamp("2017-06-29 00:15:00"))
        self.assertEqual(row["red_energy_count"], 0)
        self.assertEqual(row["orange_energy_count"], 1)
        self.assertEqual(row["low_health_pump_count"], 1)
        self.assertEqual(row["red_overflow_node_count"], 1)
        self.assertEqual(row["top_energy_pump"], "latest_orange")
        self.assertEqual(row["lowest_health_pump"], "bad_pump")
        self.assertEqual(row["highest_risk_node"], "risk_node")


if __name__ == "__main__":
    unittest.main()
