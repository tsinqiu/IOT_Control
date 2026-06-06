from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .run_swmm import _rewrite_swmm_datetime_options, _working_directory


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GAGES = ["rg5425", "rg5427"]
SCENARIO_COLUMNS = ["scenario_id", "timestamp", "rain_gage_id", "rainfall_mm"]
MANIFEST_COLUMNS = [
    "scenario_id",
    "display_name",
    "start_datetime",
    "duration_min",
    "total_rainfall_mm",
    "peak_minute_rainfall_mm",
    "csv_file",
    "dat_file",
]


@dataclass(frozen=True)
class RainfallScenarioSpec:
    scenario_id: str
    display_name: str
    duration_min: int
    total_rainfall_mm: float
    pattern: str


DEFAULT_SCENARIOS = [
    RainfallScenarioSpec("light_rain", "小雨", 24 * 60, 8.0, "steady"),
    RainfallScenarioSpec("moderate_rain", "中雨", 12 * 60, 20.0, "front_loaded"),
    RainfallScenarioSpec("heavy_rain", "大雨", 6 * 60, 45.0, "center_peak"),
    RainfallScenarioSpec("short_intense_rain", "短历时强降雨", 60, 30.0, "short_intense"),
]


def _weights(duration_min: int, pattern: str) -> list[float]:
    if duration_min <= 0:
        return []
    values: list[float] = []
    center = 0.4 if pattern == "short_intense" else 0.5
    for index in range(duration_min):
        position = index / max(duration_min - 1, 1)
        if pattern == "steady":
            weight = 1.0
        elif pattern == "front_loaded":
            weight = max(0.2, 1.3 - position)
        else:
            spread = 0.16 if pattern == "short_intense" else 0.22
            weight = 0.15 + max(0.0, 1.0 - abs(position - center) / spread)
        values.append(weight)
    total = sum(values) or 1.0
    return [value / total for value in values]


def build_scenario_frame(
    spec: RainfallScenarioSpec,
    start_datetime: str | pd.Timestamp,
    gages: list[str] | None = None,
) -> pd.DataFrame:
    start = pd.Timestamp(start_datetime)
    gage_ids = gages or DEFAULT_GAGES
    weights = _weights(spec.duration_min, spec.pattern)
    rainfall = [round(spec.total_rainfall_mm * weight, 5) for weight in weights]
    diff = round(spec.total_rainfall_mm - sum(rainfall), 5)
    if rainfall:
        rainfall[-1] = round(rainfall[-1] + diff, 5)

    rows: list[dict[str, Any]] = []
    for gage in gage_ids:
        for offset, value in enumerate(rainfall):
            rows.append(
                {
                    "scenario_id": spec.scenario_id,
                    "timestamp": start + pd.Timedelta(minutes=offset),
                    "rain_gage_id": gage,
                    "rainfall_mm": value,
                }
            )
    return pd.DataFrame(rows, columns=SCENARIO_COLUMNS)


def write_bellinge_dat(frame: pd.DataFrame, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    data = frame.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data = data.sort_values(["rain_gage_id", "timestamp"])
    for row in data.itertuples(index=False):
        timestamp = pd.Timestamp(row.timestamp)
        lines.append(
            f"{row.rain_gage_id} {timestamp.year} {timestamp.month} {timestamp.day} "
            f"{timestamp.hour} {timestamp.minute} {float(row.rainfall_mm):.5f}".rstrip("0").rstrip(".")
        )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def generate_default_scenarios(
    output_dir: str | Path | None = None,
    start_datetime: str = "2017-06-29 00:00:00",
    gages: list[str] | None = None,
) -> dict[str, Path]:
    out_dir = Path(output_dir) if output_dir else PROJECT_ROOT / "data" / "scenarios" / "rainfall"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_frames: list[pd.DataFrame] = []
    manifest_rows: list[dict[str, Any]] = []

    for spec in DEFAULT_SCENARIOS:
        frame = build_scenario_frame(spec, start_datetime, gages)
        csv_path = out_dir / f"{spec.scenario_id}.csv"
        dat_path = out_dir / f"{spec.scenario_id}.dat"
        frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
        write_bellinge_dat(frame, dat_path)
        all_frames.append(frame)
        manifest_rows.append(
            {
                "scenario_id": spec.scenario_id,
                "display_name": spec.display_name,
                "start_datetime": str(pd.Timestamp(start_datetime)),
                "duration_min": spec.duration_min,
                "total_rainfall_mm": spec.total_rainfall_mm,
                "peak_minute_rainfall_mm": float(frame.groupby("timestamp")["rainfall_mm"].mean().max()),
                "csv_file": csv_path.name,
                "dat_file": dat_path.name,
            }
        )

    combined = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame(columns=SCENARIO_COLUMNS)
    manifest = pd.DataFrame(manifest_rows, columns=MANIFEST_COLUMNS)
    combined_path = out_dir / "rainfall_scenarios.csv"
    manifest_path = out_dir / "scenario_manifest.csv"
    combined.to_csv(combined_path, index=False, encoding="utf-8-sig")
    manifest.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    paths = {row["scenario_id"]: out_dir / row["dat_file"] for row in manifest_rows}
    paths["rainfall_scenarios"] = combined_path
    paths["scenario_manifest"] = manifest_path
    return paths


def rewrite_raingage_files(inp_path: str | Path, rainfall_file_name: str) -> None:
    path = Path(inp_path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_raingages = False
    rewritten: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_raingages = stripped.upper() == "[RAINGAGES]"
        if in_raingages and " FILE " in f" {line} ":
            line = re.sub(r'"[^"]+\.dat"', f'"{rainfall_file_name}"', line)
        rewritten.append(line)
    path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")


def _first_model_node_id(inp_path: Path) -> str:
    section = ""
    for line in inp_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped.upper()
            continue
        if section in {"[JUNCTIONS]", "[STORAGE]", "[OUTFALLS]"}:
            return stripped.split()[0]
    return ""


def run_scenario_smoke_test(
    swmm_input: str | Path,
    scenario_dat: str | Path,
    run_dir: str | Path,
    start_datetime: str = "2017-06-29 00:00:00",
    end_datetime: str = "2017-06-29 02:00:00",
    sample_node_id: str | None = None,
) -> dict[str, Any]:
    from pyswmm import Nodes, Simulation

    source_inp = Path(swmm_input)
    source_dat = Path(scenario_dat)
    target_dir = Path(run_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_inp = target_dir / source_inp.name
    target_dat = target_dir / source_dat.name
    shutil.copy2(source_inp, target_inp)
    shutil.copy2(source_dat, target_dat)
    rewrite_raingage_files(target_inp, target_dat.name)
    _rewrite_swmm_datetime_options(target_inp, start_datetime, end_datetime)

    depths: list[float] = []
    steps = 0
    with _working_directory(target_dir), Simulation(target_inp.name) as sim:
        sim.step_advance(300)
        nodes = Nodes(sim)
        node_id = sample_node_id or _first_model_node_id(target_inp)
        for _ in sim:
            steps += 1
            try:
                depths.append(float(getattr(nodes[node_id], "depth", 0.0) or 0.0))
            except Exception:
                depths.append(0.0)

    depth_change = (max(depths) - min(depths)) if depths else 0.0
    return {
        "status": "success" if steps > 0 and bool(depths) else "failed",
        "steps": steps,
        "sample_node_id": sample_node_id or "",
        "max_depth_change_m": float(depth_change),
        "scenario_dat": str(target_dat),
        "run_inp": str(target_inp),
    }
