from __future__ import annotations

import shutil
from contextlib import contextmanager
from os import chdir, getcwd
from pathlib import Path
from typing import Any

import pandas as pd

from .dynamic_aggregation import (
    aggregate_node_timeseries,
    aggregate_pump_energy,
    aggregate_pump_operation,
    aggregate_pump_station_levels,
)
from .extract_timeseries import empty_dynamic_tables, risk_level


KEY_NODE_IDS = {"G71F320", "G71F060", "G71F68Y", "G_ADD"}


@contextmanager
def _working_directory(path: Path):
    previous = getcwd()
    chdir(path)
    try:
        yield
    finally:
        chdir(previous)


def _swmm_date_time(value: str) -> tuple[str, str]:
    timestamp = pd.Timestamp(value)
    return timestamp.strftime("%m/%d/%Y"), timestamp.strftime("%H:%M:%S")


def _rewrite_swmm_datetime_options(inp_path: Path, start_datetime: str, end_datetime: str) -> None:
    start_date, start_time = _swmm_date_time(start_datetime)
    end_date, end_time = _swmm_date_time(end_datetime)
    replacements = {
        "START_DATE": start_date,
        "START_TIME": start_time,
        "REPORT_START_DATE": start_date,
        "REPORT_START_TIME": start_time,
        "END_DATE": end_date,
        "END_TIME": end_time,
    }
    lines = inp_path.read_text(encoding="utf-8", errors="replace").splitlines()
    rewritten: list[str] = []
    for line in lines:
        stripped = line.strip()
        key = stripped.split(None, 1)[0] if stripped else ""
        if key in replacements:
            rewritten.append(f"{key:<21}{replacements[key]}")
        else:
            rewritten.append(line)
    inp_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")


def _prepare_run_files(
    swmm_input: Path,
    rainfall_input: Path,
    run_dir: Path,
    start_datetime: str,
    end_datetime: str,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    target_inp = run_dir / swmm_input.name
    target_rain = run_dir / rainfall_input.name
    shutil.copy2(swmm_input, target_inp)
    shutil.copy2(rainfall_input, target_rain)
    _rewrite_swmm_datetime_options(target_inp, start_datetime, end_datetime)
    return target_inp


def _default_sample_node_ids(node_info: pd.DataFrame, pump_info: pd.DataFrame, target_nodes: list[str] | None) -> list[str]:
    if target_nodes and "*" in target_nodes:
        return list(node_info.index)
    if target_nodes:
        return [node_id for node_id in target_nodes if node_id in node_info.index]
    selected = set(KEY_NODE_IDS)
    if "node_type" in node_info.columns:
        selected.update(node_info[node_info["node_type"].astype(str).str.lower() == "storage"].index.astype(str))
    for column in ["inlet_node", "outlet_node"]:
        if column in pump_info.columns:
            selected.update(pump_info[column].dropna().astype(str))
    return sorted(node_id for node_id in selected if node_id in node_info.index)


def run_or_fallback(
    swmm_input: Path,
    rainfall_input: Path,
    run_dir: Path,
    static_tables: dict[str, pd.DataFrame],
    start_datetime: str,
    end_datetime: str,
    raw_sample_step_sec: int,
    report_step_min: int,
    pump_efficiency: float,
    default_design_head_m: dict[str, float] | None = None,
    target_nodes: list[str] | None = None,
    save_raw_node_timeseries: bool = True,
    raw_node_output_path: Path | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    try:
        dynamic = run_pyswmm(
            swmm_input=swmm_input,
            rainfall_input=rainfall_input,
            run_dir=run_dir,
            static_tables=static_tables,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            raw_sample_step_sec=raw_sample_step_sec,
            report_step_min=report_step_min,
            pump_efficiency=pump_efficiency,
            default_design_head_m=default_design_head_m or {},
            target_nodes=target_nodes,
            save_raw_node_timeseries=save_raw_node_timeseries,
            raw_node_output_path=raw_node_output_path,
        )
        return dynamic, {"swmm_status": "success", "message": "PySWMM simulation completed."}
    except Exception as exc:
        dynamic = empty_dynamic_tables(static_tables, start_datetime, end_datetime, report_step_min, pump_efficiency)
        return dynamic, {"swmm_status": "fallback", "message": f"PySWMM simulation failed: {exc}"}


def run_pyswmm(
    swmm_input: Path,
    rainfall_input: Path,
    run_dir: Path,
    static_tables: dict[str, pd.DataFrame],
    start_datetime: str,
    end_datetime: str,
    raw_sample_step_sec: int,
    report_step_min: int,
    pump_efficiency: float,
    default_design_head_m: dict[str, float] | None = None,
    target_nodes: list[str] | None = None,
    save_raw_node_timeseries: bool = True,
    raw_node_output_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    from pyswmm import Links, Nodes, Simulation

    run_inp = _prepare_run_files(swmm_input, rainfall_input, run_dir, start_datetime, end_datetime)
    node_info = static_tables["node_info"].set_index("node_id", drop=False)
    pump_info = static_tables["pump_info"]
    facility_info = static_tables.get("facility_info", pd.DataFrame())
    controllable_facilities = facility_info[
        facility_info.get("facility_type", pd.Series(dtype=str)).isin(["orifice", "weir", "outlet"])
    ] if not facility_info.empty else pd.DataFrame()
    default_design_head_m = default_design_head_m or {}
    node_ids = _default_sample_node_ids(node_info, pump_info, target_nodes)
    all_nodes_mode = bool(target_nodes and "*" in target_nodes)
    raw_node_output_path = raw_node_output_path if save_raw_node_timeseries else None
    if raw_node_output_path is not None:
        raw_node_output_path.parent.mkdir(parents=True, exist_ok=True)
        if raw_node_output_path.exists():
            raw_node_output_path.unlink()
    pump_related_node_ids = set()
    for column in ["inlet_node", "outlet_node"]:
        if column in pump_info.columns:
            pump_related_node_ids.update(pump_info[column].dropna().astype(str))

    node_rows: list[dict[str, Any]] = []
    node_window_rows: list[dict[str, Any]] = []
    node_level_chunks: list[pd.DataFrame] = []
    current_node_window: pd.Timestamp | None = None
    pump_rows: list[dict[str, Any]] = []
    link_rows: list[dict[str, Any]] = []

    def flush_node_window() -> None:
        nonlocal node_window_rows
        if not node_window_rows:
            return
        chunk = aggregate_node_timeseries(
            pd.DataFrame(node_window_rows),
            node_info.reset_index(drop=True),
            report_step_min,
            raw_sample_step_sec,
        )
        if not chunk.empty:
            node_level_chunks.append(chunk)
        if raw_node_output_path is not None:
            pd.DataFrame(node_window_rows).to_csv(
                raw_node_output_path,
                mode="a",
                header=not raw_node_output_path.exists(),
                index=False,
                encoding="utf-8-sig",
            )
        node_window_rows = []

    with _working_directory(run_dir), Simulation(run_inp.name) as sim:
        sim.step_advance(raw_sample_step_sec)
        nodes = Nodes(sim)
        links = Links(sim)
        for _ in sim:
            timestamp = pd.Timestamp(sim.current_time)
            node_window = timestamp.floor(f"{report_step_min}min")
            if all_nodes_mode and current_node_window is not None and node_window != current_node_window:
                flush_node_window()
            if all_nodes_mode:
                current_node_window = node_window
            for node_id in node_ids:
                if node_id not in node_info.index:
                    continue
                static = node_info.loc[node_id]
                depth = head = flooding = inflow = None
                try:
                    node = nodes[node_id]
                    depth = float(getattr(node, "depth", 0.0) or 0.0)
                    head = float(getattr(node, "head", 0.0) or 0.0)
                    flooding = float(getattr(node, "flooding", 0.0) or 0.0)
                    inflow = float(getattr(node, "total_inflow", 0.0) or 0.0)
                except Exception:
                    pass
                row = {
                    "timestamp": timestamp,
                    "node_id": node_id,
                    "node_type": static["node_type"],
                    "depth_m": depth,
                    "head_m": head,
                    "flooding_cms": flooding,
                    "total_inflow_cms": inflow,
                }
                if all_nodes_mode:
                    node_window_rows.append(row)
                    if node_id in pump_related_node_ids:
                        node_rows.append(row)
                else:
                    node_rows.append(row)

            for _, pump in pump_info.iterrows():
                flow = setting = 0.0
                try:
                    link = links[pump["pump_id"]]
                    flow = max(float(getattr(link, "flow", 0.0) or 0.0), 0.0)
                    setting = float(getattr(link, "target_setting", 0.0) or 0.0)
                except Exception:
                    pass
                status = "ON" if flow > 1e-6 or setting > 0 else "OFF"
                pump_rows.append(
                    {
                        "timestamp": timestamp,
                        "pump_id": pump["pump_id"],
                        "pump_station_id": pump["pump_station_id"],
                        "flow_cms": flow,
                        "setting": setting,
                        "status": status,
                        "inlet_node": pump["inlet_node"],
                        "outlet_node": pump["outlet_node"],
                    }
                )

            for _, facility in controllable_facilities.iterrows():
                facility_id = facility["facility_id"]
                flow = 0.0
                setting = 0.0
                status = "unknown"
                try:
                    link = links[facility_id]
                    flow = max(float(getattr(link, "flow", 0.0) or 0.0), 0.0)
                    setting = float(getattr(link, "target_setting", 0.0) or 0.0)
                    status = "open" if setting > 0 else "closed"
                except Exception:
                    status = "not_simulated"
                link_rows.append(
                    {
                        "timestamp": timestamp,
                        "link_id": facility_id,
                        "link_type": facility["facility_type"],
                        "flow_cms": flow,
                        "depth_m": 0.0,
                        "setting": setting,
                    }
                )

    if all_nodes_mode:
        flush_node_window()

    raw_nodes = pd.DataFrame(node_rows)
    raw_pumps = pd.DataFrame(pump_rows)
    raw_links = pd.DataFrame(link_rows)
    if all_nodes_mode:
        node_level = (
            pd.concat(node_level_chunks, ignore_index=True)
            if node_level_chunks
            else aggregate_node_timeseries(pd.DataFrame(), node_info.reset_index(drop=True), report_step_min, raw_sample_step_sec)
        )
    else:
        node_level = aggregate_node_timeseries(raw_nodes, node_info.reset_index(drop=True), report_step_min, raw_sample_step_sec)
    pump_operation = aggregate_pump_operation(raw_pumps, report_step_min, raw_sample_step_sec)
    pump_energy = aggregate_pump_energy(raw_pumps, raw_nodes, pump_info, report_step_min, pump_efficiency, default_design_head_m)
    pump_station_levels = aggregate_pump_station_levels(raw_nodes, pump_info, node_info.reset_index(drop=True), report_step_min)
    gate_operation = _aggregate_gate_operation(raw_links, controllable_facilities, report_step_min)
    output_raw_nodes = raw_nodes
    if all_nodes_mode and not save_raw_node_timeseries:
        output_raw_nodes = pd.DataFrame(
            columns=["timestamp", "node_id", "node_type", "depth_m", "head_m", "flooding_cms", "total_inflow_cms"]
        )

    return {
        "raw_node_timeseries": output_raw_nodes,
        "raw_pump_timeseries": raw_pumps,
        "raw_link_timeseries": raw_links,
        "node_level_timeseries": node_level,
        "pump_station_level_timeseries": pump_station_levels,
        "pump_energy_timeseries": pump_energy,
        "pump_operation_timeseries": pump_operation,
        "gate_operation_timeseries": gate_operation,
    }


def _aggregate_gate_operation(raw_links: pd.DataFrame, facility_info: pd.DataFrame, report_step_min: int) -> pd.DataFrame:
    columns = ["timestamp", "gate_id", "facility_type", "inlet_node", "outlet_node", "status", "setting", "flow_cms"]
    if raw_links.empty:
        return pd.DataFrame(columns=columns)
    frame = raw_links.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["window"] = frame["timestamp"].dt.floor(f"{report_step_min}min")
    grouped = frame.groupby(["window", "link_id", "link_type"], as_index=False).agg(
        setting=("setting", "mean"),
        flow_cms=("flow_cms", "max"),
    )
    grouped["status"] = grouped["setting"].map(lambda value: "open" if float(value) > 0 else "closed")
    grouped = grouped.rename(columns={"window": "timestamp", "link_id": "gate_id", "link_type": "facility_type"})
    if not facility_info.empty:
        grouped = grouped.merge(
            facility_info[["facility_id", "inlet_node", "outlet_node"]].rename(columns={"facility_id": "gate_id"}),
            on="gate_id",
            how="left",
        )
    else:
        grouped["inlet_node"] = ""
        grouped["outlet_node"] = ""
    return grouped[columns].sort_values(["timestamp", "gate_id"]).reset_index(drop=True)
