from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from backend.iot_control.part1_data_foundation.build_datasets import build_all
    from backend.iot_control.part1_data_foundation.config import ensure_directories, load_config
else:
    from .build_datasets import build_all
    from .config import ensure_directories, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SWMM and rainfall data to coursework CSV datasets.")
    parser.add_argument("--all", action="store_true", help="Run the full export pipeline.")
    parser.add_argument("--config", default=None, help="Path to config YAML.")
    args = parser.parse_args()

    config = load_config(args.config)
    ensure_directories(config)

    if args.all:
        result = build_all(config)
        print(f"CSV files written: {len(result['csv_paths'])}")
        if "raw_node_timeseries" in result.get("interim_paths", {}):
            print("[OK] Exported raw_node_timeseries.csv")
        if "raw_pump_timeseries" in result.get("interim_paths", {}):
            print("[OK] Exported raw_pump_timeseries.csv")
        if "node_level_timeseries" in result.get("csv_paths", {}):
            print("[OK] Aggregated node_level_timeseries.csv with 15min max/sum metrics")
        print(f"Rainfall rows: {result['rainfall_stats']['rows']}")
        print(f"SWMM status: {result['simulation_status']['swmm_status']}")
        print(f"SWMM message: {result['simulation_status']['message']}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
