from __future__ import annotations

from typing import Any

import pandas as pd


def risk_level(depth: float | None, max_depth: float | None, flooding: float | None) -> str:
    flooding_value = flooding or 0.0
    if flooding_value > 0:
        return "red"
    if depth is None or max_depth in (None, 0, ""):
        return "green"
    ratio = depth / float(max_depth)
    if ratio >= 0.9:
        return "orange"
    if ratio >= 0.7:
        return "yellow"
    return "green"


def empty_dynamic_tables(
    static_tables: dict[str, pd.DataFrame],
    start_datetime: str,
    end_datetime: str,
    report_step_min: int,
    pump_efficiency: float,
) -> dict[str, pd.DataFrame]:
    timestamps = pd.date_range(start=start_datetime, end=end_datetime, freq=f"{report_step_min}min")
    nodes = static_tables["node_info"]
    pumps = static_tables["pump_info"]

    node_rows: list[dict[str, Any]] = []
    for timestamp in timestamps:
        for _, node in nodes.iterrows():
            node_rows.append(
                {
                    "timestamp": timestamp,
                    "node_id": node["node_id"],
                    "node_type": node["node_type"],
                    "depth_m": 0.0,
                    "head_m": node["invert_elevation"] if node["invert_elevation"] != "" else 0.0,
                    "flooding_cms": 0.0,
                    "total_inflow_cms": 0.0,
                    "risk_level": "green",
                }
            )
    node_level = pd.DataFrame(node_rows)

    station_rows: list[dict[str, Any]] = []
    forebays = pumps[["pump_station_id", "inlet_node"]].drop_duplicates()
    for timestamp in timestamps:
        for _, pump in forebays.iterrows():
            station_rows.append(
                {
                    "timestamp": timestamp,
                    "pump_station_id": pump["pump_station_id"],
                    "forebay_node": pump["inlet_node"],
                    "depth_m": 0.0,
                    "head_m": 0.0,
                    "percent_full": 0.0,
                    "level_change_rate_m_per_min": 0.0,
                }
            )

    energy_rows: list[dict[str, Any]] = []
    operation_rows: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    facility_info = static_tables.get("facility_info", pd.DataFrame())
    for timestamp in timestamps:
        for _, pump in pumps.iterrows():
            energy_rows.append(
                {
                    "timestamp": timestamp,
                    "pump_id": pump["pump_id"],
                    "pump_station_id": pump["pump_station_id"],
                    "flow_cms": 0.0,
                    "inlet_head_m": 0.0,
                    "outlet_head_m": 0.0,
                    "pump_head_m": 0.0,
                    "estimated_power_kw": 0.0,
                    "energy_kwh_interval": 0.0,
                    "cumulative_energy_kwh": 0.0,
                    "unit_energy_kwh_per_kt": 0.0,
                }
            )
            operation_rows.append(
                {
                    "timestamp": timestamp,
                    "pump_id": pump["pump_id"],
                    "pump_station_id": pump["pump_station_id"],
                    "status": "off",
                    "setting": 0.0,
                    "flow_cms": 0.0,
                    "start_event": False,
                    "stop_event": False,
                    "runtime_min_interval": 0.0,
                    "cumulative_runtime_min": 0.0,
                    "runtime_min_cumulative": 0.0,
                    "start_count_cumulative": 0,
                    "startup_count_cumulative": 0,
                }
            )
        if not facility_info.empty:
            for _, facility in facility_info[facility_info["facility_type"].isin(["orifice", "weir", "outlet"])].iterrows():
                gate_rows.append(
                    {
                        "timestamp": timestamp,
                        "gate_id": facility["facility_id"],
                        "facility_type": facility["facility_type"],
                        "inlet_node": facility["inlet_node"],
                        "outlet_node": facility["outlet_node"],
                        "status": "not_simulated",
                        "setting": 0.0,
                        "flow_cms": 0.0,
                    }
                )

    return {
        "node_level_timeseries": node_level,
        "pump_station_level_timeseries": pd.DataFrame(station_rows),
        "pump_energy_timeseries": pd.DataFrame(energy_rows),
        "pump_operation_timeseries": pd.DataFrame(operation_rows),
        "gate_operation_timeseries": pd.DataFrame(gate_rows),
        "simulation_note": pd.DataFrame(
            [{"status": "fallback", "message": f"PySWMM data unavailable; zero baseline generated with efficiency={pump_efficiency}."}]
        ),
    }
