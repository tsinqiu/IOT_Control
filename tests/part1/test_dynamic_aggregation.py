import unittest

import pandas as pd


class DynamicAggregationTests(unittest.TestCase):
    def test_node_aggregation_captures_short_flooding_peak(self):
        from backend.iot_control.part1_data_foundation.dynamic_aggregation import aggregate_node_timeseries

        raw = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:01:00", "node_id": "N1", "node_type": "storage", "depth_m": 1.0, "head_m": 11.0, "flooding_cms": 0.0, "total_inflow_cms": 0.1},
                {"timestamp": "2017-06-29 00:02:00", "node_id": "N1", "node_type": "storage", "depth_m": 1.2, "head_m": 11.2, "flooding_cms": 0.5, "total_inflow_cms": 0.2},
                {"timestamp": "2017-06-29 00:03:00", "node_id": "N1", "node_type": "storage", "depth_m": 1.1, "head_m": 11.1, "flooding_cms": 0.0, "total_inflow_cms": 0.1},
            ]
        )
        node_info = pd.DataFrame([{"node_id": "N1", "max_depth": 2.0}])

        result = aggregate_node_timeseries(raw, node_info, report_step_min=15, raw_sample_step_sec=60)

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertAlmostEqual(row["flooding_cms_max_15min"], 0.5)
        self.assertAlmostEqual(row["flooding_volume_m3_15min"], 30.0)
        self.assertEqual(row["risk_level"], "red")

    def test_pump_operation_aggregation_counts_startup_and_runtime(self):
        from backend.iot_control.part1_data_foundation.dynamic_aggregation import aggregate_pump_operation

        raw = pd.DataFrame(
            [
                {"timestamp": "2017-06-29 00:01:00", "pump_id": "P1", "pump_station_id": "S1", "flow_cms": 0.0, "setting": 0.0, "status": "OFF"},
                {"timestamp": "2017-06-29 00:02:00", "pump_id": "P1", "pump_station_id": "S1", "flow_cms": 0.2, "setting": 1.0, "status": "ON"},
                {"timestamp": "2017-06-29 00:03:00", "pump_id": "P1", "pump_station_id": "S1", "flow_cms": 0.3, "setting": 1.0, "status": "ON"},
                {"timestamp": "2017-06-29 00:04:00", "pump_id": "P1", "pump_station_id": "S1", "flow_cms": 0.0, "setting": 0.0, "status": "OFF"},
            ]
        )

        result = aggregate_pump_operation(raw, report_step_min=15, raw_sample_step_sec=60)

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["status"], "ON")
        self.assertEqual(row["on_seconds_15min"], 120)
        self.assertEqual(row["startup_count_15min"], 1)
        self.assertEqual(row["startup_count_cumulative"], 1)
        self.assertAlmostEqual(row["runtime_min_cumulative"], 2.0)


if __name__ == "__main__":
    unittest.main()
