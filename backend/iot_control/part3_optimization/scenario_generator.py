from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from backend.iot_control.part1_data_foundation.config import PipelineConfig, load_config
from backend.iot_control.part1_data_foundation.parse_rainfall import parse_rainfall_file
from backend.iot_control.part1_data_foundation.rainfall_scenario_generator import write_bellinge_dat
from backend.iot_control.part1_data_foundation.run_swmm import _rewrite_swmm_datetime_options


GAGES = ["rg5425", "rg5427"]
INTENSITY_SCALES = [0.8, 1.0, 1.2, 1.5]
PEAK_DAYS = [1, 2, 3]
MANIFEST_COLUMNS = [
    "scenario_id",
    "scenario_dir",
    "inp_path",
    "rg5425_dat_path",
    "rg5427_dat_path",
    "source_start_time",
    "simulation_start_time",
    "duration_hours",
    "intensity_scale",
    "peak_day",
    "total_rainfall_mm",
    "peak_minute_rainfall_mm",
    "manual_run_status",
    "notes",
]


@dataclass(frozen=True)
class SourceFragment:
    source_start_time: pd.Timestamp
    duration_hours: int
    total_rainfall_mm: float
    peak_minute_rainfall_mm: float
    peak_offset_min: int


def _relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _build_minute_rainfall(rainfall_input: Path, gages: list[str]) -> pd.DataFrame:
    observed, _ = parse_rainfall_file(rainfall_input)
    if observed.empty:
        raise ValueError(f"No rainfall records found in {rainfall_input}")

    data = observed[observed["rain_gage_id"].astype(str).isin(gages)].copy()
    if data.empty:
        raise ValueError(f"No rainfall records found for gages: {', '.join(gages)}")

    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce").dt.floor("min")
    data["rainfall_mm"] = pd.to_numeric(data["rainfall_mm"], errors="coerce").fillna(0.0)
    pivot = (
        data.pivot_table(
            index="timestamp",
            columns="rain_gage_id",
            values="rainfall_mm",
            aggfunc="sum",
            fill_value=0.0,
        )
        .sort_index()
        .rename_axis(None, axis=1)
    )
    for gage in gages:
        if gage not in pivot.columns:
            pivot[gage] = 0.0
    pivot = pivot[gages]
    full_index = pd.date_range(pivot.index.min(), pivot.index.max(), freq="min")
    return pivot.reindex(full_index, fill_value=0.0)


def _select_source_fragments(rainfall: pd.DataFrame, count: int = 4) -> list[SourceFragment]:
    total = rainfall.sum(axis=1)
    selected: list[SourceFragment] = []
    selected_ranges: list[tuple[pd.Timestamp, pd.Timestamp]] = []

    def add_best_windows(duration_hours: int, target_for_duration: int) -> None:
        added = 0
        duration_min = duration_hours * 60
        rolling = total.rolling(duration_min, min_periods=duration_min).sum()
        for end_time, window_total in rolling.sort_values(ascending=False).items():
            if added >= target_for_duration or len(selected) >= count:
                break
            if not pd.notna(window_total) or float(window_total) <= 0.0:
                continue
            source_start = pd.Timestamp(end_time) - pd.Timedelta(minutes=duration_min - 1)
            source_end = pd.Timestamp(end_time)
            overlaps = any(source_start <= end and source_end >= start for start, end in selected_ranges)
            if overlaps:
                continue
            window = rainfall.loc[source_start:source_end]
            minute_totals = window.sum(axis=1)
            peak_time = pd.Timestamp(minute_totals.idxmax())
            selected.append(
                SourceFragment(
                    source_start_time=source_start,
                    duration_hours=duration_hours,
                    total_rainfall_mm=float(window.sum().mean()),
                    peak_minute_rainfall_mm=float(window.max(axis=1).max()),
                    peak_offset_min=int((peak_time - source_start).total_seconds() // 60),
                )
            )
            selected_ranges.append((source_start, source_end))
            added += 1

    for duration_hours in (6, 12):
        add_best_windows(duration_hours, max(1, count // 2))

    for duration_hours in (6, 12):
        if len(selected) >= count:
            break
        add_best_windows(duration_hours, count - len(selected))

    if not selected:
        raise ValueError("Historical rainfall has no positive 6h/12h rainy fragments")
    return selected


def _target_rain_start(
    simulation_start: pd.Timestamp,
    simulation_end: pd.Timestamp,
    duration_hours: int,
    peak_offset_min: int,
    peak_day: int,
) -> pd.Timestamp:
    duration = pd.Timedelta(hours=duration_hours)
    peak_anchor = simulation_start.normalize() + pd.Timedelta(days=peak_day - 1, hours=12)
    candidate = peak_anchor - pd.Timedelta(minutes=peak_offset_min)
    latest = simulation_end - duration + pd.Timedelta(minutes=1)
    if candidate < simulation_start:
        candidate = simulation_start
    if candidate > latest:
        candidate = latest
    return candidate.floor("min")


def _rewrite_raingage_files_by_gage(inp_path: Path, dat_file_names: dict[str, str]) -> None:
    lines = inp_path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_raingages = False
    rewritten: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_raingages = stripped.upper() == "[RAINGAGES]"
            rewritten.append(line)
            continue
        if in_raingages and stripped and not stripped.startswith(";"):
            parts = stripped.split()
            gage = parts[0] if parts else ""
            if gage in dat_file_names:
                line = re.sub(r'"[^"]*\.dat"', f'"{dat_file_names[gage]}"', line)
        rewritten.append(line)
    inp_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")


def _build_shifted_frame(
    scenario_id: str,
    source_fragment: SourceFragment,
    rainfall: pd.DataFrame,
    simulation_start_time: pd.Timestamp,
    intensity_scale: float,
) -> pd.DataFrame:
    duration_min = source_fragment.duration_hours * 60
    source_index = pd.date_range(source_fragment.source_start_time, periods=duration_min, freq="min")
    target_index = pd.date_range(simulation_start_time, periods=duration_min, freq="min")
    source_values = rainfall.reindex(source_index, fill_value=0.0)[GAGES].reset_index(drop=True) * intensity_scale

    frames: list[pd.DataFrame] = []
    for gage in GAGES:
        frames.append(
            pd.DataFrame(
                {
                    "scenario_id": scenario_id,
                    "timestamp": target_index,
                    "rain_gage_id": gage,
                    "rainfall_mm": source_values[gage].round(5).to_numpy(),
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def _write_scenario_files(
    config: PipelineConfig,
    scenario_id: str,
    scenario_dir: Path,
    scenario_frame: pd.DataFrame,
) -> tuple[Path, Path, Path]:
    scenario_dir.mkdir(parents=True, exist_ok=True)
    inp_path = scenario_dir / f"{scenario_id}.inp"
    rg5425_dat = scenario_dir / f"{scenario_id}_rg5425.dat"
    rg5427_dat = scenario_dir / f"{scenario_id}_rg5427.dat"

    shutil.copy2(config.swmm_input, inp_path)
    write_bellinge_dat(scenario_frame[scenario_frame["rain_gage_id"] == "rg5425"], rg5425_dat)
    write_bellinge_dat(scenario_frame[scenario_frame["rain_gage_id"] == "rg5427"], rg5427_dat)
    _rewrite_swmm_datetime_options(inp_path, config.start_datetime, config.end_datetime)
    _rewrite_raingage_files_by_gage(
        inp_path,
        {
            "rg5425": rg5425_dat.name,
            "rg5427": rg5427_dat.name,
        },
    )
    return inp_path, rg5425_dat, rg5427_dat


def generate_candidate_scenarios(config_path: str | Path | None = None) -> pd.DataFrame:
    config = load_config(config_path)
    rainfall = _build_minute_rainfall(config.rainfall_input, GAGES)
    fragments = _select_source_fragments(rainfall)

    candidate_root = config.swmm_run_dir / "part3_scenario_candidates"
    manifest_dir = config.csv_dir.parent / "part3_optimization"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    candidate_root.mkdir(parents=True, exist_ok=True)

    simulation_start = pd.Timestamp(config.start_datetime)
    simulation_end = pd.Timestamp(config.end_datetime)
    rows: list[dict[str, Any]] = []
    scenario_number = 1

    for peak_day in PEAK_DAYS:
        for scale_index, intensity_scale in enumerate(INTENSITY_SCALES):
            scenario_id = f"scenario_{scenario_number:02d}"
            fragment = fragments[(scenario_number + scale_index - 1) % len(fragments)]
            rain_start = _target_rain_start(
                simulation_start,
                simulation_end,
                fragment.duration_hours,
                fragment.peak_offset_min,
                peak_day,
            )
            scenario_frame = _build_shifted_frame(scenario_id, fragment, rainfall, rain_start, intensity_scale)
            scenario_dir = candidate_root / scenario_id
            inp_path, rg5425_dat, rg5427_dat = _write_scenario_files(config, scenario_id, scenario_dir, scenario_frame)

            gage_totals = scenario_frame.groupby("rain_gage_id")["rainfall_mm"].sum().round(5).to_dict()
            minute_totals = scenario_frame.pivot_table(
                index="timestamp",
                columns="rain_gage_id",
                values="rainfall_mm",
                aggfunc="sum",
                fill_value=0.0,
            ).sum(axis=1)
            total_rainfall_mm = float(pd.Series(gage_totals).mean())
            peak_minute_rainfall_mm = float(minute_totals.max() / len(GAGES))
            peak_timestamp = pd.Timestamp(minute_totals.idxmax())
            actual_peak_day = int((peak_timestamp.normalize() - simulation_start.normalize()).days + 1)
            notes = "manual PySWMM run required; no automatic simulation output generated"

            row = {
                "scenario_id": scenario_id,
                "scenario_dir": _relative_or_absolute(scenario_dir, config.project_root),
                "inp_path": _relative_or_absolute(inp_path, config.project_root),
                "rg5425_dat_path": _relative_or_absolute(rg5425_dat, config.project_root),
                "rg5427_dat_path": _relative_or_absolute(rg5427_dat, config.project_root),
                "source_start_time": str(fragment.source_start_time),
                "simulation_start_time": str(rain_start),
                "duration_hours": fragment.duration_hours,
                "intensity_scale": intensity_scale,
                "peak_day": actual_peak_day,
                "total_rainfall_mm": round(total_rainfall_mm, 5),
                "peak_minute_rainfall_mm": round(peak_minute_rainfall_mm, 5),
                "manual_run_status": "pending",
                "notes": notes,
            }
            rows.append(row)

            scenario_info = {
                **row,
                "simulation_end_time": str(rain_start + pd.Timedelta(hours=fragment.duration_hours) - pd.Timedelta(minutes=1)),
                "source_end_time": str(fragment.source_start_time + pd.Timedelta(hours=fragment.duration_hours) - pd.Timedelta(minutes=1)),
                "gage_totals_mm": {key: float(value) for key, value in gage_totals.items()},
            }
            (scenario_dir / "scenario_info.json").write_text(
                json.dumps(scenario_info, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            scenario_number += 1

    manifest = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    manifest_path = manifest_dir / "scenario_manifest.csv"
    manifest.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    return manifest


def _print_manifest_summary(manifest: pd.DataFrame) -> None:
    columns = [
        "scenario_id",
        "peak_day",
        "duration_hours",
        "intensity_scale",
        "total_rainfall_mm",
        "peak_minute_rainfall_mm",
        "inp_path",
    ]
    print("\nPart 3 candidate rainfall scenarios:")
    print(manifest[columns].to_string(index=False))
    print("\nmanual_run_status defaults to pending. Run each listed INP manually, then provide the 12 reports for baseline selection.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate 12 manual-run rainfall scenario candidates for Part 3.")
    parser.add_argument(
        "--config",
        default="config/part1_data_foundation.yaml",
        help="Path to part1_data_foundation.yaml",
    )
    args = parser.parse_args(argv)
    manifest = generate_candidate_scenarios(args.config)
    _print_manifest_summary(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
