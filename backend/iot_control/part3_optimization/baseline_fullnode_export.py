from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from backend.iot_control.part1_data_foundation.config import PipelineConfig, load_config
from backend.iot_control.part1_data_foundation.parse_inp import build_static_tables, parse_inp_file
from backend.iot_control.part1_data_foundation.run_swmm import run_pyswmm
from backend.iot_control.part3_optimization.baseline_prepare import prepare_baseline


FULLNODE_OUTPUT_TABLES = [
    "node_level_timeseries",
    "pump_operation_timeseries",
    "pump_energy_timeseries",
    "pump_station_level_timeseries",
]


def _canonical_baseline_id(scenario: str) -> str:
    value = scenario.strip().lower()
    suffix = value.split("_", 1)[1] if value.startswith("scenario_") else value
    if suffix.isdigit():
        return f"scenario_{int(suffix)}"
    return value


def _canonical_source_id(scenario: str) -> str:
    value = scenario.strip().lower()
    suffix = value.split("_", 1)[1] if value.startswith("scenario_") else value
    if suffix.isdigit():
        return f"scenario_{int(suffix):02d}"
    return value


def _baseline_dir(config: PipelineConfig, scenario: str) -> Path:
    return config.swmm_run_dir / "part3_baseline" / _canonical_baseline_id(scenario)


def _result_dir(config: PipelineConfig, scenario: str) -> Path:
    return config.csv_dir.parent / "part3_optimization" / f"baseline_{_canonical_baseline_id(scenario)}"


def _find_one(path: Path, patterns: list[str], label: str) -> Path:
    for pattern in patterns:
        matches = sorted(path.glob(pattern))
        if matches:
            return matches[0]
    raise FileNotFoundError(f"{label} not found in {path}")


def _ensure_baseline_exists(config_path: str | Path | None, config: PipelineConfig, scenario: str) -> Path:
    baseline_dir = _baseline_dir(config, scenario)
    if baseline_dir.exists():
        return baseline_dir
    prepare_baseline(config_path, scenario)
    if not baseline_dir.exists():
        raise FileNotFoundError(f"Baseline directory not found after prepare_baseline: {baseline_dir}")
    return baseline_dir


def _copy_baseline_dat_files(baseline_dir: Path, run_dir: Path) -> tuple[Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    rg5425 = _find_one(baseline_dir, ["*rg5425*.dat"], "rg5425 DAT")
    rg5427 = _find_one(baseline_dir, ["*rg5427*.dat"], "rg5427 DAT")
    shutil.copy2(rg5425, run_dir / rg5425.name)
    shutil.copy2(rg5427, run_dir / rg5427.name)
    return rg5425, rg5427


def _write_fullnode_csvs(dynamic_tables: dict[str, pd.DataFrame], result_dir: Path) -> dict[str, Path]:
    result_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name in FULLNODE_OUTPUT_TABLES:
        frame = dynamic_tables.get(table_name, pd.DataFrame())
        path = result_dir / f"{table_name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        paths[table_name] = path
    return paths


def export_baseline_fullnode_csv(config_path: str | Path | None = None, scenario: str = "scenario_2") -> dict[str, Any]:
    config = load_config(config_path)
    baseline_id = _canonical_baseline_id(scenario)
    source_id = _canonical_source_id(scenario)
    baseline_dir = _ensure_baseline_exists(config_path, config, scenario)
    baseline_inp = _find_one(baseline_dir, [f"{source_id}.inp", "*.inp"], "baseline INP")
    run_dir = baseline_dir / "full_node_run"
    rg5425_dat, _ = _copy_baseline_dat_files(baseline_dir, run_dir)

    model = parse_inp_file(baseline_inp)
    static_tables = build_static_tables(model)
    dynamic_tables = run_pyswmm(
        swmm_input=baseline_inp,
        rainfall_input=rg5425_dat,
        run_dir=run_dir,
        static_tables=static_tables,
        start_datetime=config.start_datetime,
        end_datetime=config.end_datetime,
        raw_sample_step_sec=config.raw_sample_step_sec,
        report_step_min=config.report_step_min,
        pump_efficiency=config.pump_efficiency,
        default_design_head_m=config.default_design_head_m,
        target_nodes=["*"],
        save_raw_node_timeseries=False,
        raw_node_output_path=None,
    )

    result_dir = _result_dir(config, baseline_id)
    csv_paths = _write_fullnode_csvs(dynamic_tables, result_dir)
    assessment = prepare_baseline(config_path, baseline_id)
    return {
        "status": "exported",
        "baseline_id": baseline_id,
        "baseline_dir": baseline_dir,
        "run_dir": run_dir,
        "result_dir": result_dir,
        "csv_paths": csv_paths,
        "assessment": assessment,
    }


def _print_result(result: dict[str, Any]) -> None:
    print(f"Baseline full-node CSV directory: {result['result_dir']}")
    for table_name, path in result["csv_paths"].items():
        print(f"- {table_name}: {path}")
    assessment = result.get("assessment", {})
    print(f"Baseline assessment status: {assessment.get('status', 'unknown')}")
    if assessment.get("outputs"):
        for name, path in assessment["outputs"].items():
            print(f"- {name}: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the frozen Part 3 baseline with PySWMM and export full-node CSVs.")
    parser.add_argument("--config", default="config/part1_data_foundation.yaml", help="Path to part1_data_foundation.yaml")
    parser.add_argument("--scenario", default="scenario_2", help="Baseline scenario id, e.g. scenario_2 or scenario_02")
    args = parser.parse_args(argv)
    result = export_baseline_fullnode_csv(args.config, args.scenario)
    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
