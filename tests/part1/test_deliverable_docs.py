import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


class DeliverableDocsTests(unittest.TestCase):
    def test_data_dictionary_contains_table_purpose_units_and_key_fields(self):
        from backend.iot_control.part1_data_foundation.quality_check import write_data_dictionary

        out_dir = ROOT / "tests" / "_tmp_deliverable_docs"
        tables = {
            "node_level_timeseries": pd.DataFrame(
                columns=[
                    "timestamp",
                    "node_id",
                    "depth_m_avg",
                    "depth_m_max",
                    "flooding_cms_max_15min",
                    "flooding_volume_m3_15min",
                ]
            ),
            "pump_energy_timeseries": pd.DataFrame(columns=["timestamp", "pump_id", "estimated_power_kw_avg"]),
        }

        write_data_dictionary(tables, out_dir)
        content = (out_dir / "data_dictionary.md").read_text(encoding="utf-8")

        self.assertIn("表用途", content)
        self.assertIn("单位说明", content)
        self.assertIn("15min 窗口内最大 flooding 流量", content)
        self.assertIn("15min 平均估算功率", content)

    def test_database_readme_contains_import_order_and_v2_notes(self):
        from backend.iot_control.part1_data_foundation.database_export import write_schema

        out_dir = ROOT / "tests" / "_tmp_deliverable_database"
        write_schema(out_dir)
        content = (out_dir / "README.md").read_text(encoding="utf-8")

        self.assertIn("导入顺序", content)
        self.assertIn("rainfall_observed.csv", content)
        self.assertIn("G71F320Pp1", content)
        self.assertIn("model_version", content)

    def test_quality_report_template_contains_coursework_delivery_sections(self):
        from backend.iot_control.part1_data_foundation.check_csv_quality import CheckResult, _write_report

        out_dir = ROOT / "tests" / "_tmp_deliverable_report"
        result = CheckResult(report_path=out_dir / "csv_quality_check_report.md")
        result.oks.extend(["Found rainfall_observed.csv"])
        tables = {"rainfall_observed": pd.DataFrame([{"timestamp": "2017-06-29 00:00:00", "rainfall_mm": 1.0}])}

        _write_report(
            result=result,
            tables=tables,
            ranges={},
            node_lines=["| node_id | max depth_m_max |", "| --- | ---: |"],
            pump_lines=["| pump_id | max flow_cms |", "| --- | ---: |"],
            schema_lines=["- OK: `rainfall_observed` has CREATE TABLE."],
            docs_report_path=None,
        )
        content = result.report_path.read_text(encoding="utf-8")

        self.assertIn("多源数据接入与质量评估报告", content)
        self.assertIn("六类基础数据覆盖关系", content)
        self.assertIn("第一部分验收结论", content)


if __name__ == "__main__":
    unittest.main()
