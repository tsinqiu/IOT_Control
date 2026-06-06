from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class PipelineConfig:
    project_root: Path
    swmm_input: Path
    rainfall_input: Path
    csv_dir: Path
    report_dir: Path
    log_dir: Path
    swmm_run_dir: Path
    interim_dir: Path
    database_dir: Path
    docs_dir: Path
    start_datetime: str
    end_datetime: str
    raw_sample_step_sec: int
    report_step_min: int
    forecast_hours: int
    pump_efficiency: float
    default_design_head_m: dict[str, float]
    target_nodes: list[str]
    save_raw_node_timeseries: bool


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def load_config(path: str | Path | None = None) -> PipelineConfig:
    root = PROJECT_ROOT
    config_path = Path(path) if path else root / "config" / "part1_data_foundation.yaml"
    data: dict[str, Any] = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    paths = data.get("paths", {})
    simulation = data.get("simulation", {})
    forecast = data.get("forecast", {})
    pump = data.get("pump", {})
    pump_energy = data.get("pump_energy", {})

    target_nodes = list(simulation.get("target_nodes", []))
    save_raw_default = False if "*" in target_nodes else True

    return PipelineConfig(
        project_root=root,
        swmm_input=_resolve(root, paths.get("swmm_input", "data/raw/swmm/BellingeSWMM_2021_orin.inp")),
        rainfall_input=_resolve(root, paths.get("rainfall_input", "data/raw/rainfall/rg_bellinge_Jun2010_Aug2021.dat")),
        csv_dir=_resolve(root, paths.get("csv_dir", "data/processed/part1_csv")),
        report_dir=_resolve(root, paths.get("report_dir", "outputs/reports/part1")),
        log_dir=_resolve(root, paths.get("log_dir", "outputs/logs")),
        swmm_run_dir=_resolve(root, paths.get("swmm_run_dir", "outputs/swmm_runs")),
        interim_dir=_resolve(root, paths.get("interim_dir", "data/interim/part1")),
        database_dir=_resolve(root, paths.get("database_dir", "database/part1")),
        docs_dir=_resolve(root, paths.get("docs_dir", "docs/part1")),
        start_datetime=str(simulation.get("start_datetime", "2012-06-29 00:01:00")),
        end_datetime=str(simulation.get("end_datetime", "2012-06-30 00:00:00")),
        raw_sample_step_sec=int(simulation.get("raw_sample_step_sec", 60)),
        report_step_min=int(simulation.get("report_step_min", 15)),
        forecast_hours=int(forecast.get("hours", 72)),
        pump_efficiency=float(pump_energy.get("default_efficiency", pump.get("efficiency", 0.70))),
        default_design_head_m={key: float(value) for key, value in dict(pump_energy.get("default_design_head_m", {})).items()},
        target_nodes=target_nodes,
        save_raw_node_timeseries=bool(simulation.get("save_raw_node_timeseries", save_raw_default)),
    )


def ensure_directories(config: PipelineConfig) -> None:
    directories = [
        config.csv_dir,
        config.report_dir,
        config.log_dir,
        config.swmm_run_dir,
        config.interim_dir,
        config.database_dir,
        config.docs_dir,
        config.project_root / "data" / "raw" / "swmm",
        config.project_root / "data" / "raw" / "rainfall",
        config.project_root / "outputs" / "figures",
        config.project_root / "notebooks",
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
