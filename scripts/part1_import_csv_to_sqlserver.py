from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyodbc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "data" / "processed" / "part1_csv"

SERVER = r"localhost"
DATABASE = "IOT_Control_DB"
SCHEMA = "dbo"

PREFERRED_DRIVERS = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]
AVAILABLE_DRIVERS = pyodbc.drivers()
DRIVER = next((driver for driver in PREFERRED_DRIVERS if driver in AVAILABLE_DRIVERS), PREFERRED_DRIVERS[-1])

CONN_STR = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

SKIP_FILES: set[str] = set()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize CSV values before sending them to SQL Server."""
    df = df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    df = df.replace({np.nan: None, "": None})

    for column in df.columns:
        if column.lower() in {"timestamp", "forecast_time", "target_time"}:
            values = pd.to_datetime(df[column], errors="coerce")
            df[column] = values.dt.strftime("%Y-%m-%d %H:%M:%S")
            df[column] = df[column].where(df[column].notna(), None)

    return df


def get_table_columns(cursor: pyodbc.Cursor, table_name: str) -> list[str]:
    sql = """
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION
    """
    cursor.execute(sql, SCHEMA, table_name)
    return [row[0] for row in cursor.fetchall()]


def import_csv(cursor: pyodbc.Cursor, csv_path: Path) -> None:
    table_name = csv_path.stem
    print(f"\n[INFO] Importing {csv_path.name} -> {SCHEMA}.{table_name}")

    table_cols = get_table_columns(cursor, table_name)
    if not table_cols:
        print(f"[WARN] Table {SCHEMA}.{table_name} not found, skip.")
        return

    df = clean_dataframe(pd.read_csv(csv_path, encoding="utf-8-sig"))
    common_cols = [column for column in df.columns if column in table_cols]
    if not common_cols:
        print(f"[WARN] No matching columns for {table_name}, skip.")
        return

    missing_in_csv = [column for column in table_cols if column not in df.columns]
    if missing_in_csv:
        print(f"[WARN] Columns in table but missing in CSV: {missing_in_csv}")

    df = df[common_cols]
    if df.empty:
        print(f"[WARN] {csv_path.name} is empty, skip.")
        return

    cursor.execute(f"DELETE FROM {SCHEMA}.{table_name}")

    col_sql = ", ".join(f"[{column}]" for column in common_cols)
    placeholders = ", ".join("?" for _ in common_cols)
    insert_sql = f"INSERT INTO {SCHEMA}.{table_name} ({col_sql}) VALUES ({placeholders})"

    rows = list(df.itertuples(index=False, name=None))
    cursor.fast_executemany = True
    cursor.executemany(insert_sql, rows)
    print(f"[OK] Imported {len(rows)} rows into {SCHEMA}.{table_name}")


def main() -> None:
    if not CSV_DIR.exists():
        raise FileNotFoundError(f"CSV_DIR not found: {CSV_DIR}")

    csv_files = sorted(CSV_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {CSV_DIR}")

    print(f"[INFO] CSV_DIR: {CSV_DIR}")
    print(f"[INFO] SQL Server: {SERVER}, database: {DATABASE}, driver: {DRIVER}")

    conn = pyodbc.connect(CONN_STR)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        for csv_path in csv_files:
            if csv_path.name in SKIP_FILES:
                print(f"[SKIP] {csv_path.name}")
                continue
            import_csv(cursor, csv_path)

        conn.commit()
        print("\n[DONE] All CSV files imported successfully.")
    except Exception:
        conn.rollback()
        print("\n[ERROR] Import failed. Transaction rolled back.")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
