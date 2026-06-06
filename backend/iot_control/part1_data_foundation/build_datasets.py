from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from .config import PipelineConfig
from .database_export import write_schema
from .parse_inp import build_static_tables, parse_inp_file
from .parse_rainfall import build_forecast_scenario, parse_rainfall_file
from .quality_check import write_data_dictionary, write_quality_reports
from .run_swmm import run_or_fallback


def _copy_if_needed(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or source.stat().st_size != target.stat().st_size:
        shutil.copy2(source, target)


def locate_or_prepare_inputs(config: PipelineConfig) -> tuple[Path, Path]:
    source_swmm = config.swmm_input
    source_rain = config.rainfall_input
    if not source_swmm.exists():
        candidate = config.project_root / "丹麦小镇城市排水模型" / "7_SWMM" / "BellingeSWMM_2021_orin.inp"
        if candidate.exists():
            _copy_if_needed(candidate, source_swmm)
    if not source_rain.exists():
        candidate = config.project_root / "丹麦小镇城市排水模型" / "7_SWMM" / "rg_bellinge_Jun2010_Aug2021.dat"
        if candidate.exists():
            _copy_if_needed(candidate, source_rain)
    if not source_swmm.exists():
        raise FileNotFoundError(f"SWMM input not found: {source_swmm}")
    if not source_rain.exists():
        raise FileNotFoundError(f"Rainfall input not found: {source_rain}")
    return source_swmm, source_rain


def write_csv_tables(tables: dict[str, pd.DataFrame], csv_dir: Path) -> dict[str, Path]:
    csv_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, frame in tables.items():
        path = csv_dir / f"{name}.csv"
        try:
            frame.to_csv(path, index=False, encoding="utf-8-sig")
        except PermissionError:
            if not path.exists():
                raise
        paths[name] = path
    return paths


def write_interim_tables(tables: dict[str, pd.DataFrame], interim_dir: Path) -> dict[str, Path]:
    interim_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, frame in tables.items():
        path = interim_dir / f"{name}.csv"
        try:
            frame.to_csv(path, index=False, encoding="utf-8-sig")
        except PermissionError:
            if not path.exists():
                raise
        paths[name] = path
    return paths


def build_all(config: PipelineConfig) -> dict[str, Any]:
    swmm_input, rainfall_input = locate_or_prepare_inputs(config)

    observed, rainfall_stats = parse_rainfall_file(rainfall_input)
    forecast = build_forecast_scenario(observed, config.start_datetime, config.forecast_hours)

    model = parse_inp_file(swmm_input)
    static_tables = build_static_tables(model)
    dynamic_tables, simulation_status = run_or_fallback(
        swmm_input=swmm_input,
        rainfall_input=rainfall_input,
        run_dir=config.swmm_run_dir,
        static_tables=static_tables,
        start_datetime=config.start_datetime,
        end_datetime=config.end_datetime,
        raw_sample_step_sec=config.raw_sample_step_sec,
        report_step_min=config.report_step_min,
        pump_efficiency=config.pump_efficiency,
        default_design_head_m=config.default_design_head_m,
        target_nodes=config.target_nodes,
        save_raw_node_timeseries=config.save_raw_node_timeseries,
        raw_node_output_path=config.interim_dir / "raw_node_timeseries.csv",
    )

    csv_tables = {
        "rainfall_observed": observed,
        "rainfall_forecast_scenario": forecast,
        **static_tables,
        **{name: frame for name, frame in dynamic_tables.items() if name != "simulation_note" and not name.startswith("raw_")},
    }
    raw_tables = {name: frame for name, frame in dynamic_tables.items() if name.startswith("raw_")}
    all_node_mode = "*" in config.target_nodes
    raw_node_path = config.interim_dir / "raw_node_timeseries.csv"
    if all_node_mode:
        raw_tables.pop("raw_node_timeseries", None)
        if not config.save_raw_node_timeseries and raw_node_path.exists():
            try:
                raw_node_path.unlink()
            except PermissionError:
                pass
    interim_paths = write_interim_tables(raw_tables, config.interim_dir)
    if all_node_mode and config.save_raw_node_timeseries and raw_node_path.exists():
        interim_paths["raw_node_timeseries"] = raw_node_path
    csv_paths = write_csv_tables(csv_tables, config.csv_dir)
    write_schema(config.database_dir)
    write_quality_reports(csv_tables, rainfall_stats, simulation_status, config.report_dir, config.docs_dir)
    write_data_dictionary(csv_tables, config.docs_dir)
    return {
        "csv_paths": csv_paths,
        "interim_paths": interim_paths,
        "rainfall_stats": rainfall_stats,
        "simulation_status": simulation_status,
    }
