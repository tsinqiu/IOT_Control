import unittest

import pandas as pd

from backend.iot_control.part2_status_assessment.energy_assessment import assess_energy, build_energy_summary


class EnergyAssessmentTests(unittest.TestCase):
    def test_interval_volume_uses_configured_report_step(self):
        frame = pd.DataFrame(
            [
                {
                    "timestamp": "2017-06-29 00:00:00",
                    "pump_id": "P1",
                    "pump_station_id": "S1",
                    "flow_cms_avg": 0.01,
                    "energy_kwh_interval": 1.0,
                }
            ]
        )

        result = assess_energy(frame, report_step_min=30)

        self.assertAlmostEqual(result.loc[0, "interval_volume_m3"], 18.0)

    def test_small_flow_windows_do_not_compute_unit_energy(self):
        frame = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:00:00", "pump_id": "P1", "pump_station_id": "S1", "flow_cms_avg": 0.0005, "energy_kwh_interval": 1.0},
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "P1", "pump_station_id": "S1", "flow_cms_avg": 0.01, "energy_kwh_interval": 1.0},
            ]
        )

        result = assess_energy(frame, report_step_min=15)

        self.assertTrue(pd.isna(result.loc[0, "interval_unit_energy_kwh_per_kt"]))
        self.assertEqual(result.loc[0, "energy_grade"], "no_data")
        self.assertFalse(pd.isna(result.loc[1, "interval_unit_energy_kwh_per_kt"]))

    def test_p25_baseline_uses_valid_interval_unit_energy(self):
        rows = []
        for i, unit in enumerate([10.0, 20.0, 30.0, 40.0]):
            flow = 1.0
            volume = flow * 15 * 60
            rows.append(
                {
                    "timestamp": pd.Timestamp("2017-06-29") + pd.Timedelta(minutes=15 * i),
                    "pump_id": "P1",
                    "pump_station_id": "S1",
                    "flow_cms_avg": flow,
                    "energy_kwh_interval": unit * (volume / 1000),
                }
            )

        result = assess_energy(pd.DataFrame(rows), report_step_min=15)

        self.assertAlmostEqual(result["baseline_unit_energy_kwh_per_kt"].dropna().iloc[0], 17.5)

    def test_cross_unit_energy_grade_can_escalate_final_energy_grade(self):
        rows = []
        for pump_id, unit in [("P1", 10.0), ("P2", 20.0), ("P3", 60.0)]:
            volume = 1.0 * 15 * 60
            rows.append(
                {
                    "timestamp": "2017-06-29 00:00:00",
                    "pump_id": pump_id,
                    "pump_station_id": "S1",
                    "flow_cms_avg": 1.0,
                    "energy_kwh_interval": unit * (volume / 1000),
                }
            )

        result = assess_energy(pd.DataFrame(rows), report_step_min=15)
        high = result[result["pump_id"] == "P3"].iloc[0]

        self.assertEqual(high["unit_energy_rank_in_window"], 1)
        self.assertEqual(high["unit_energy_rank_count"], 3)
        self.assertEqual(high["cross_unit_energy_grade"], "red")
        self.assertEqual(high["energy_grade"], "red")

    def test_energy_summary_keeps_all_pumps_and_ranks_valid_units(self):
        rows = []
        for pump_id, flow, unit in [("P1", 1.0, 10.0), ("P2", 1.0, 60.0), ("P3", 0.0, 0.0)]:
            volume = flow * 15 * 60
            rows.append(
                {
                    "timestamp": "2017-06-29 00:00:00",
                    "pump_id": pump_id,
                    "pump_station_id": "S1",
                    "flow_cms_avg": flow,
                    "energy_kwh_interval": unit * (volume / 1000) if volume else 0.0,
                }
            )

        energy = assess_energy(pd.DataFrame(rows), report_step_min=15)
        summary = build_energy_summary(energy)

        self.assertEqual(set(summary["pump_id"]), {"P1", "P2", "P3"})
        self.assertEqual(summary[summary["pump_id"] == "P3"].iloc[0]["summary_energy_grade"], "no_data")
        self.assertEqual(summary[summary["pump_id"] == "P2"].iloc[0]["unit_energy_rank_overall"], 1)


if __name__ == "__main__":
    unittest.main()
