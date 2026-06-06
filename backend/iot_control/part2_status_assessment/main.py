from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from backend.iot_control.part2_status_assessment.config import ensure_directories, load_config
    from backend.iot_control.part2_status_assessment.energy_assessment import assess_energy, build_energy_summary
    from backend.iot_control.part2_status_assessment.overflow_risk_assessment import assess_overflow_risk
    from backend.iot_control.part2_status_assessment.pump_health_assessment import assess_pump_health
    from backend.iot_control.part2_status_assessment.status_summary import build_system_summary
else:
    from .config import ensure_directories, load_config
    from .energy_assessment import assess_energy, build_energy_summary
    from .overflow_risk_assessment import assess_overflow_risk
    from .pump_health_assessment import assess_pump_health
    from .status_summary import build_system_summary


def _read_csv(input_dir: Path, name: str) -> pd.DataFrame:
    path = input_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required part1 CSV: {path}")
    return pd.read_csv(path, low_memory=False)


def write_outputs(tables: dict[str, pd.DataFrame], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, frame in tables.items():
        path = output_dir / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        paths[name] = path
    return paths


def build_all(config_path: str | Path | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    ensure_directories(config)

    pump_energy = _read_csv(config.input_csv_dir, "pump_energy_timeseries")
    pump_operation = _read_csv(config.input_csv_dir, "pump_operation_timeseries")
    pump_station_levels = _read_csv(config.input_csv_dir, "pump_station_level_timeseries")
    node_level = _read_csv(config.input_csv_dir, "node_level_timeseries")
    node_info = _read_csv(config.input_csv_dir, "node_info")
    rainfall_forecast = _read_csv(config.input_csv_dir, "rainfall_forecast_scenario")
    rainfall_observed = _read_csv(config.input_csv_dir, "rainfall_observed")

    energy = assess_energy(
        pump_energy,
        report_step_min=config.report_step_min,
        min_flow_cms=config.min_flow_cms,
        min_interval_volume_m3=config.min_interval_volume_m3,
    )
    health = assess_pump_health(pump_operation, pump_station_levels)
    overflow = assess_overflow_risk(node_level, node_info, rainfall_forecast, rainfall_observed)
    energy_summary = build_energy_summary(energy)
    summary = build_system_summary(energy, health, overflow)

    tables = {
        "energy_assessment_timeseries": energy,
        "pump_energy_summary": energy_summary,
        "pump_health_assessment": health,
        "overflow_risk_assessment": overflow,
        "system_status_summary": summary,
    }
    paths = write_outputs(tables, config.output_csv_dir)
    return {"tables": tables, "paths": paths, "config": config}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run part 2 status assessment models.")
    parser.add_argument("--all", action="store_true", help="Run all status assessment models.")
    parser.add_argument("--config", default=None, help="Path to part 2 config YAML.")
    args = parser.parse_args()

    if args.all:
        result = build_all(args.config)
        for name, frame in result["tables"].items():
            print(f"[OK] {name}.csv rows: {len(frame)}")
        print(f"[OK] Output directory: {result['config'].output_csv_dir}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
