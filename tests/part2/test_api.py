import unittest
from pathlib import Path

import pandas as pd

from backend.iot_control.api import main as api_main


class ApiTests(unittest.TestCase):
    def test_part2_routes_return_json_and_cors_is_enabled(self):
        from fastapi.testclient import TestClient

        csv_dir = Path(__file__).resolve().parents[1] / "_tmp_part2_api"
        csv_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {
                    "latest_timestamp": "2017-06-29 00:15:00",
                    "red_energy_count": 0,
                    "orange_energy_count": 1,
                }
            ]
        ).to_csv(csv_dir / "system_status_summary.csv", index=False)
        pd.DataFrame(
            [
                {"timestamp": "2017-06-28 00:00:00", "pump_id": "P1", "energy_grade": "green", "interval_unit_energy_kwh_per_kt": 1},
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "P1", "energy_grade": "orange", "interval_unit_energy_kwh_per_kt": 2},
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "P2", "energy_grade": "red", "interval_unit_energy_kwh_per_kt": 3},
            ]
        ).to_csv(csv_dir / "energy_assessment_timeseries.csv", index=False)
        pd.DataFrame(
            [{"pump_id": "P1", "pump_station_id": "S1", "summary_energy_grade": "orange"}]
        ).to_csv(csv_dir / "pump_energy_summary.csv", index=False)
        pd.DataFrame(
            [
                {"timestamp": "2017-06-28 00:00:00", "pump_id": "P1", "health_score": 90, "safety_grade": "green"},
                {"timestamp": "2017-06-29 00:15:00", "pump_id": "P1", "health_score": 80, "safety_grade": "yellow"},
            ]
        ).to_csv(csv_dir / "pump_health_assessment.csv", index=False)
        pd.DataFrame(
            [
                {"timestamp": "2017-06-28 00:00:00", "node_id": "N1", "overflow_risk_score": 0.2, "risk_grade": "green"},
                {"timestamp": "2017-06-29 00:15:00", "node_id": "N1", "overflow_risk_score": 0.8, "risk_grade": "red"},
                {"timestamp": "2017-06-29 00:00:00", "node_id": "N1", "overflow_risk_score": 0.6, "risk_grade": "orange"},
            ]
        ).to_csv(csv_dir / "overflow_risk_assessment.csv", index=False)

        original = api_main.PART2_CSV_DIR
        api_main.PART2_CSV_DIR = csv_dir
        try:
            client = TestClient(api_main.app)
            summary = client.get("/api/part2/summary")
            energy = client.get("/api/part2/energy?range=latest")
            energy_all = client.get("/api/part2/energy?range=all")
            legacy = client.get("/api/part2/energy?latest=true")
            overflow = client.get("/api/part2/overflow-risk?range=all")
            options = client.options(
                "/api/part2/energy",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
        finally:
            api_main.PART2_CSV_DIR = original

        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["red_energy_count"], 1)
        self.assertEqual(energy.status_code, 200)
        self.assertEqual(len(energy.json()), 2)
        self.assertEqual(len(energy_all.json()), 3)
        self.assertEqual(len(legacy.json()), 2)
        self.assertEqual(overflow.json()[0]["overflow_risk_score"], 0.8)
        self.assertEqual(options.status_code, 200)
        self.assertEqual(options.headers["access-control-allow-origin"], "http://localhost:5173")


if __name__ == "__main__":
    unittest.main()
