import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SsmsImportSchemaTests(unittest.TestCase):
    def test_schema_uses_text_for_blank_prone_optional_fields(self):
        from backend.iot_control.part1_data_foundation.database_export import write_schema

        out_dir = ROOT / "tests" / "_tmp_ssms_schema"
        write_schema(out_dir)
        sql = (out_dir / "schema.sql").read_text(encoding="utf-8")

        self.assertIn("minor_loss_inlet NVARCHAR(64) NULL", sql)
        self.assertIn("minor_loss_outlet NVARCHAR(64) NULL", sql)
        self.assertIn("minor_loss_average NVARCHAR(64) NULL", sql)
        self.assertIn("surcharge_depth NVARCHAR(64) NULL", sql)
        self.assertIn("discharge_coefficient NVARCHAR(64) NULL", sql)
        self.assertIn("is_startup NVARCHAR(8) NULL", sql)
        self.assertIn("is_parallel_pump NVARCHAR(8) NULL", sql)

    def test_database_readme_explains_direct_ssms_import(self):
        from backend.iot_control.part1_data_foundation.database_export import write_schema

        out_dir = ROOT / "tests" / "_tmp_ssms_schema"
        write_schema(out_dir)
        readme = (out_dir / "README.md").read_text(encoding="utf-8")

        self.assertIn("SSMS 导入向导", readme)
        self.assertIn("可直接导入", readme)
        self.assertIn("TRY_CONVERT", readme)

    def test_existing_schema_patch_is_generated(self):
        from backend.iot_control.part1_data_foundation.database_export import write_schema

        out_dir = ROOT / "tests" / "_tmp_ssms_schema"
        write_schema(out_dir)
        patch_sql = (out_dir / "ssms_import_compat_patch.sql").read_text(encoding="utf-8")

        self.assertIn("ALTER TABLE dbo.conduit_info ALTER COLUMN minor_loss_inlet NVARCHAR(64) NULL", patch_sql)
        self.assertIn("ALTER TABLE dbo.pump_operation_timeseries ALTER COLUMN is_startup NVARCHAR(8) NULL", patch_sql)


if __name__ == "__main__":
    unittest.main()
