from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from backend.iot_control.part1_data_foundation.config import PipelineConfig, load_config


REQUIRED_FULL_RESULT_FILES = [
    "node_level_timeseries.csv",
    "pump_operation_timeseries.csv",
    "pump_energy_timeseries.csv",
    "pump_station_level_timeseries.csv",
]

BASELINE_METRIC_COLUMNS = [
    "scenario_id",
    "total_rainfall_mm",
    "peak_minute_rainfall_mm",
    "max_node_depth_m",
    "max_level_ratio",
    "orange_red_node_count",
    "flooded_node_count",
    "flooding_window_count",
    "total_flooding_volume_m3",
    "total_pump_energy_kwh",
    "unit_energy_kwh_per_kt",
    "total_startup_count",
    "repeated_start_count_30min",
    "worst_energy_pump",
    "worst_health_pump",
    "worst_risk_node",
]

KEY_NODE_COLUMNS = [
    "node_id",
    "reason",
    "max_depth_m",
    "max_level_ratio",
    "total_flooding_volume_m3",
]

KEY_PUMP_COLUMNS = [
    "pump_id",
    "inlet_node",
    "outlet_node",
    "total_energy_kwh",
    "total_startup_count",
    "total_on_seconds",
    "reason",
]


def _canonical_source_id(scenario: str) -> str:
    value = scenario.strip().lower()
    if value.startswith("scenario_"):
        suffix = value.split("_", 1)[1]
    else:
        suffix = value
    if suffix.isdigit():
        return f"scenario_{int(suffix):02d}"
    return value


def _canonical_baseline_id(scenario: str) -> str:
    value = scenario.strip().lower()
    if value.startswith("scenario_"):
        suffix = value.split("_", 1)[1]
    else:
        suffix = value
    if suffix.isdigit():
        return f"scenario_{int(suffix)}"
    return value


def _relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_baseline_files(config: PipelineConfig, source_id: str, baseline_id: str) -> tuple[Path, Path]:
    source_dir = config.swmm_run_dir / "part3_scenario_candidates" / source_id
    if not source_dir.exists() and source_id == "scenario_02":
        alternate = config.swmm_run_dir / "part3_scenario_candidates" / "scenario_2"
        if alternate.exists():
            source_dir = alternate
    if not source_dir.exists():
        raise FileNotFoundError(f"Candidate scenario directory not found: {source_dir}")

    baseline_dir = config.swmm_run_dir / "part3_baseline" / baseline_id
    baseline_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.inp", "*rg5425*.dat", "*rg5427*.dat", "scenario_info.json"):
        for source_path in source_dir.glob(pattern):
            shutil.copy2(source_path, baseline_dir / source_path.name)
    scenario_info = _read_json(baseline_dir / "scenario_info.json")
    baseline_info = {
        "baseline_scenario_id": baseline_id,
        "source_scenario_id": scenario_info.get("scenario_id", source_id),
        "source_scenario_dir": _relative_or_absolute(source_dir, config.project_root),
        "baseline_dir": _relative_or_absolute(baseline_dir, config.project_root),
        "baseline_role": "part3_pre_optimization_baseline",
        "total_rainfall_mm": scenario_info.get("total_rainfall_mm", ""),
        "peak_minute_rainfall_mm": scenario_info.get("peak_minute_rainfall_mm", ""),
        "notes": "Frozen baseline scenario for Part 3 pre-optimization assessment. No optimization algorithm is run here.",
    }
    (baseline_dir / "baseline_info.json").write_text(
        json.dumps(baseline_info, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return source_dir, baseline_dir


def _full_result_dir(config: PipelineConfig, baseline_id: str) -> Path:
    return config.csv_dir.parent / "part3_optimization" / f"baseline_{baseline_id}"


def _assessment_dir(config: PipelineConfig) -> Path:
    return config.csv_dir.parent / "part3_optimization" / "baseline_assessment"


def _missing_full_result_files(result_dir: Path) -> list[str]:
    return [name for name in REQUIRED_FULL_RESULT_FILES if not (result_dir / name).exists()]


def _write_manual_run_note(baseline_dir: Path, result_dir: Path, missing: list[str], project_root: Path) -> Path:
    note_path = baseline_dir / "manual_run_note.md"
    note_path.write_text(
        "\n".join(
            [
                "# Manual full-node baseline run required",
                "",
                "The baseline scenario has been frozen, but full-node simulation CSV outputs were not found.",
                "",
                f"Expected result directory: `{_relative_or_absolute(result_dir, project_root)}`",
                "",
                "Missing CSV files:",
                *[f"- `{name}`" for name in missing],
                "",
                "Run the baseline scenario with full-node export first, then rerun `baseline_prepare`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return note_path


def _numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _load_static_tables(config: PipelineConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    node_path = config.csv_dir / "node_info.csv"
    pump_path = config.csv_dir / "pump_info.csv"
    nodes = pd.read_csv(node_path) if node_path.exists() else pd.DataFrame()
    pumps = pd.read_csv(pump_path) if pump_path.exists() else pd.DataFrame()
    return nodes, pumps


def _summarize_nodes(node_ts: pd.DataFrame, node_info: pd.DataFrame) -> pd.DataFrame:
    nodes = node_ts.copy()
    if "depth_m_max" not in nodes.columns and "depth_m_avg" in nodes.columns:
        nodes["depth_m_max"] = nodes["depth_m_avg"]
    if "flooding_volume_m3_15min" not in nodes.columns:
        nodes["flooding_volume_m3_15min"] = 0.0
    if "risk_level" not in nodes.columns:
        nodes["risk_level"] = "green"

    nodes["depth_m_max"] = _numeric(nodes["depth_m_max"])
    nodes["flooding_volume_m3_15min"] = _numeric(nodes["flooding_volume_m3_15min"])
    grouped = nodes.groupby("node_id", as_index=False).agg(
        max_depth_m=("depth_m_max", "max"),
        total_flooding_volume_m3=("flooding_volume_m3_15min", "sum"),
        flooding_window_count=("flooding_volume_m3_15min", lambda s: int((_numeric(s) > 0).sum())),
        worst_risk=("risk_level", lambda s: _worst_risk_value(s)),
    )

    if not node_info.empty and "node_id" in node_info.columns:
        static_cols = [col for col in ["node_id", "node_type", "max_depth", "is_storage", "is_pump_station_forebay"] if col in node_info.columns]
        grouped = grouped.merge(node_info[static_cols], on="node_id", how="left")
    else:
        grouped["max_depth"] = 0.0
        grouped["node_type"] = ""
        grouped["is_storage"] = False
        grouped["is_pump_station_forebay"] = False

    max_depth = _numeric(grouped.get("max_depth", pd.Series(0, index=grouped.index))).replace(0, pd.NA)
    grouped["max_level_ratio"] = (_numeric(grouped["max_depth_m"]) / max_depth).fillna(0.0)
    return grouped


def _worst_risk_value(values: pd.Series) -> str:
    order = {"green": 0, "yellow": 1, "orange": 2, "red": 3}
    labels = [str(value).lower() for value in values.dropna()]
    if not labels:
        return "green"
    return max(labels, key=lambda label: order.get(label, 0))


def _risk_rank(label: str) -> int:
    return {"green": 0, "yellow": 1, "orange": 2, "red": 3}.get(str(label).lower(), 0)


def _truthy(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _summarize_pumps(pump_operation: pd.DataFrame, pump_energy: pd.DataFrame, pump_info: pd.DataFrame) -> pd.DataFrame:
    pump_ids = set()
    for frame in (pump_info, pump_operation, pump_energy):
        if "pump_id" in frame.columns:
            pump_ids.update(frame["pump_id"].dropna().astype(str))
    summary = pd.DataFrame({"pump_id": sorted(pump_ids)})
    if not pump_info.empty and "pump_id" in pump_info.columns:
        cols = [col for col in ["pump_id", "inlet_node", "outlet_node"] if col in pump_info.columns]
        summary = summary.merge(pump_info[cols], on="pump_id", how="left")
    for col in ("inlet_node", "outlet_node"):
        if col not in summary.columns:
            summary[col] = ""

    if "pump_id" in pump_energy.columns:
        energy_col = "energy_kwh_interval" if "energy_kwh_interval" in pump_energy.columns else "estimated_power_kw_avg"
        energy = pump_energy.copy()
        energy[energy_col] = _numeric(energy[energy_col])
        energy_sum = energy.groupby("pump_id", as_index=False)[energy_col].sum().rename(columns={energy_col: "total_energy_kwh"})
        summary = summary.merge(energy_sum, on="pump_id", how="left")
    if "total_energy_kwh" not in summary.columns:
        summary["total_energy_kwh"] = 0.0

    if "pump_id" in pump_operation.columns:
        operation = pump_operation.copy()
        startup_col = "startup_count_15min" if "startup_count_15min" in operation.columns else "is_startup"
        on_col = "on_seconds_15min" if "on_seconds_15min" in operation.columns else None
        operation[startup_col] = _numeric(operation[startup_col])
        agg = operation.groupby("pump_id", as_index=False).agg(total_startup_count=(startup_col, "sum"))
        if on_col:
            operation[on_col] = _numeric(operation[on_col])
            on_seconds = operation.groupby("pump_id", as_index=False)[on_col].sum().rename(columns={on_col: "total_on_seconds"})
            agg = agg.merge(on_seconds, on="pump_id", how="left")
        summary = summary.merge(agg, on="pump_id", how="left")
    for col in ("total_startup_count", "total_on_seconds"):
        if col not in summary.columns:
            summary[col] = 0.0
    summary[["total_energy_kwh", "total_startup_count", "total_on_seconds"]] = summary[
        ["total_energy_kwh", "total_startup_count", "total_on_seconds"]
    ].fillna(0.0)
    return summary


def _count_repeated_starts_30min(pump_operation: pd.DataFrame) -> int:
    if "timestamp" not in pump_operation.columns or "pump_id" not in pump_operation.columns:
        return 0
    startup_col = "startup_count_15min" if "startup_count_15min" in pump_operation.columns else "is_startup"
    data = pump_operation.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    data[startup_col] = _numeric(data[startup_col])
    data = data[(data[startup_col] > 0) & data["timestamp"].notna()].sort_values(["pump_id", "timestamp"])
    repeated = 0
    for _, group in data.groupby("pump_id"):
        diffs = group["timestamp"].diff().dt.total_seconds().div(60)
        repeated += int(((diffs > 0) & (diffs <= 30)).sum())
    return repeated


def _unit_energy(pump_energy: pd.DataFrame, total_energy_kwh: float) -> float:
    if "unit_energy_kwh_per_kt" in pump_energy.columns:
        values = _numeric(pump_energy["unit_energy_kwh_per_kt"])
        positive = values[values > 0]
        if not positive.empty:
            return float(positive.mean())
    if {"flow_cms_avg", "energy_kwh_interval"}.issubset(pump_energy.columns):
        flow = _numeric(pump_energy["flow_cms_avg"])
        # Existing project dynamic tables are 15-minute intervals.
        volume_kt = float((flow * 900.0).sum() / 1000.0)
        if volume_kt > 0:
            return float(total_energy_kwh / volume_kt)
    return 0.0


def _build_key_nodes(node_summary: pd.DataFrame, pump_info: pd.DataFrame) -> pd.DataFrame:
    reasons: dict[str, set[str]] = {}

    def add(node_id: Any, reason: str) -> None:
        if pd.isna(node_id) or str(node_id) == "":
            return
        reasons.setdefault(str(node_id), set()).add(reason)

    for column in ("inlet_node",):
        if column in pump_info.columns:
            for node_id in pump_info[column].dropna():
                add(node_id, "pump_inlet_or_forebay")
    for _, row in node_summary.iterrows():
        node_id = row["node_id"]
        node_type = str(row.get("node_type", "")).lower()
        is_storage = _truthy(row.get("is_storage", False))
        is_forebay = _truthy(row.get("is_pump_station_forebay", False))
        if node_type == "storage" or is_storage:
            add(node_id, "storage_node")
        if is_forebay:
            add(node_id, "pump_station_forebay")
        if float(row.get("total_flooding_volume_m3", 0.0) or 0.0) > 0:
            add(node_id, "flooding_node")
        if _risk_rank(str(row.get("worst_risk", ""))) >= 2:
            add(node_id, "orange_red_risk_node")
    for node_id in node_summary.sort_values("max_level_ratio", ascending=False).head(30)["node_id"]:
        add(node_id, "top30_level_ratio")
    for node_id in ("G71F320", "G_ADD"):
        add(node_id, "added_pump_related_node")

    rows: list[dict[str, Any]] = []
    lookup = node_summary.set_index("node_id", drop=False) if "node_id" in node_summary.columns else pd.DataFrame()
    for node_id in sorted(reasons):
        if not lookup.empty and node_id in lookup.index:
            row = lookup.loc[node_id]
            rows.append(
                {
                    "node_id": node_id,
                    "reason": ";".join(sorted(reasons[node_id])),
                    "max_depth_m": round(float(row.get("max_depth_m", 0.0) or 0.0), 5),
                    "max_level_ratio": round(float(row.get("max_level_ratio", 0.0) or 0.0), 5),
                    "total_flooding_volume_m3": round(float(row.get("total_flooding_volume_m3", 0.0) or 0.0), 5),
                }
            )
        else:
            rows.append(
                {
                    "node_id": node_id,
                    "reason": ";".join(sorted(reasons[node_id])),
                    "max_depth_m": 0.0,
                    "max_level_ratio": 0.0,
                    "total_flooding_volume_m3": 0.0,
                }
            )
    return pd.DataFrame(rows, columns=KEY_NODE_COLUMNS)


def _build_key_pumps(pump_summary: pd.DataFrame) -> pd.DataFrame:
    if pump_summary.empty:
        return pd.DataFrame(columns=KEY_PUMP_COLUMNS)
    frame = pump_summary.copy()
    frame["reason"] = "all_pumps_retained_for_optimization"
    return frame[KEY_PUMP_COLUMNS].sort_values("pump_id").reset_index(drop=True)


def _generate_assessment(config: PipelineConfig, baseline_id: str, baseline_dir: Path) -> dict[str, Path]:
    result_dir = _full_result_dir(config, baseline_id)
    assessment_dir = _assessment_dir(config)
    assessment_dir.mkdir(parents=True, exist_ok=True)

    node_ts = pd.read_csv(result_dir / "node_level_timeseries.csv")
    pump_operation = pd.read_csv(result_dir / "pump_operation_timeseries.csv")
    pump_energy = pd.read_csv(result_dir / "pump_energy_timeseries.csv")
    _ = pd.read_csv(result_dir / "pump_station_level_timeseries.csv")
    node_info, pump_info = _load_static_tables(config)
    scenario_info = _read_json(baseline_dir / "scenario_info.json")

    node_summary = _summarize_nodes(node_ts, node_info)
    pump_summary = _summarize_pumps(pump_operation, pump_energy, pump_info)
    total_energy = float(pump_summary["total_energy_kwh"].sum()) if "total_energy_kwh" in pump_summary.columns else 0.0
    total_startups = int(round(float(pump_summary["total_startup_count"].sum()))) if "total_startup_count" in pump_summary.columns else 0

    orange_red = node_summary[node_summary["worst_risk"].map(_risk_rank) >= 2]
    flooded = node_summary[node_summary["total_flooding_volume_m3"] > 0]
    worst_risk_node = ""
    if not node_summary.empty:
        risk_sorted = node_summary.sort_values(
            ["worst_risk", "max_level_ratio", "total_flooding_volume_m3"],
            key=lambda s: s.map(_risk_rank) if s.name == "worst_risk" else s,
            ascending=[False, False, False],
        )
        worst_risk_node = str(risk_sorted.iloc[0]["node_id"])

    worst_energy_pump = ""
    worst_health_pump = ""
    if not pump_summary.empty:
        worst_energy_pump = str(pump_summary.sort_values("total_energy_kwh", ascending=False).iloc[0]["pump_id"])
        worst_health_pump = str(pump_summary.sort_values("total_startup_count", ascending=False).iloc[0]["pump_id"])

    metrics = pd.DataFrame(
        [
            {
                "scenario_id": baseline_id,
                "total_rainfall_mm": float(scenario_info.get("total_rainfall_mm", 0.0) or 0.0),
                "peak_minute_rainfall_mm": float(scenario_info.get("peak_minute_rainfall_mm", 0.0) or 0.0),
                "max_node_depth_m": round(float(node_summary["max_depth_m"].max()) if not node_summary.empty else 0.0, 5),
                "max_level_ratio": round(float(node_summary["max_level_ratio"].max()) if not node_summary.empty else 0.0, 5),
                "orange_red_node_count": int(len(orange_red)),
                "flooded_node_count": int(len(flooded)),
                "flooding_window_count": int(node_summary["flooding_window_count"].sum()) if "flooding_window_count" in node_summary else 0,
                "total_flooding_volume_m3": round(float(node_summary["total_flooding_volume_m3"].sum()) if not node_summary.empty else 0.0, 5),
                "total_pump_energy_kwh": round(total_energy, 5),
                "unit_energy_kwh_per_kt": round(_unit_energy(pump_energy, total_energy), 5),
                "total_startup_count": total_startups,
                "repeated_start_count_30min": _count_repeated_starts_30min(pump_operation),
                "worst_energy_pump": worst_energy_pump,
                "worst_health_pump": worst_health_pump,
                "worst_risk_node": worst_risk_node,
            }
        ],
        columns=BASELINE_METRIC_COLUMNS,
    )
    key_nodes = _build_key_nodes(node_summary, pump_info)
    key_pumps = _build_key_pumps(pump_summary)

    metrics_path = assessment_dir / "baseline_metrics.csv"
    key_nodes_path = assessment_dir / "key_nodes_for_optimization.csv"
    key_pumps_path = assessment_dir / "key_pumps_for_optimization.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    key_nodes.to_csv(key_nodes_path, index=False, encoding="utf-8-sig")
    key_pumps.to_csv(key_pumps_path, index=False, encoding="utf-8-sig")
    return {
        "baseline_metrics": metrics_path,
        "key_nodes": key_nodes_path,
        "key_pumps": key_pumps_path,
    }


def prepare_baseline(config_path: str | Path | None = None, scenario: str = "scenario_2") -> dict[str, Any]:
    config = load_config(config_path)
    source_id = _canonical_source_id(scenario)
    baseline_id = _canonical_baseline_id(scenario)
    _, baseline_dir = _copy_baseline_files(config, source_id, baseline_id)

    result_dir = _full_result_dir(config, baseline_id)
    missing = _missing_full_result_files(result_dir)
    if missing:
        note_path = _write_manual_run_note(baseline_dir, result_dir, missing, config.project_root)
        return {
            "status": "missing_full_results",
            "baseline_dir": baseline_dir,
            "full_result_dir": result_dir,
            "missing_files": missing,
            "manual_run_note": note_path,
        }

    outputs = _generate_assessment(config, baseline_id, baseline_dir)
    return {
        "status": "assessment_generated",
        "baseline_dir": baseline_dir,
        "full_result_dir": result_dir,
        "outputs": outputs,
    }


def _print_result(result: dict[str, Any]) -> None:
    print(f"Baseline directory: {result['baseline_dir']}")
    if result["status"] == "missing_full_results":
        print("Full-node baseline CSV outputs are missing:")
        for name in result["missing_files"]:
            print(f"- {name}")
        print(f"Manual run note: {result['manual_run_note']}")
        return
    print("Baseline assessment generated:")
    for name, path in result["outputs"].items():
        print(f"- {name}: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze Part 3 baseline scenario and summarize full-node results when available.")
    parser.add_argument("--config", default="config/part1_data_foundation.yaml", help="Path to part1_data_foundation.yaml")
    parser.add_argument("--scenario", default="scenario_2", help="Baseline scenario id, e.g. scenario_2 or scenario_02")
    args = parser.parse_args(argv)
    result = prepare_baseline(args.config, args.scenario)
    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
