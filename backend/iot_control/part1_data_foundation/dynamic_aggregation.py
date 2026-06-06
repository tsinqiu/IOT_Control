from __future__ import annotations

from typing import Any

import pandas as pd


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce") if column in frame.columns else pd.Series(dtype=float)


def _window_start(series: pd.Series, report_step_min: int) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.floor(f"{report_step_min}min")


def _risk_from_window(flooding_max: float, flooding_volume: float, depth_max: float, max_depth: Any) -> str:
    if flooding_max > 0 or flooding_volume > 0:
        return "red"
    try:
        max_depth_value = float(max_depth)
    except (TypeError, ValueError):
        return "green"
    if max_depth_value <= 0:
        return "green"
    ratio = depth_max / max_depth_value
    if ratio >= 0.9:
        return "orange"
    if ratio >= 0.7:
        return "yellow"
    return "green"


def aggregate_node_timeseries(
    raw_nodes: pd.DataFrame,
    node_info: pd.DataFrame,
    report_step_min: int,
    raw_sample_step_sec: int,
) -> pd.DataFrame:
    columns = [
        "timestamp",
        "node_id",
        "node_type",
        "depth_m_avg",
        "depth_m_max",
        "head_m_avg",
        "head_m_max",
        "flooding_cms_instant",
        "flooding_cms_max_15min",
        "flooding_volume_m3_15min",
        "total_inflow_cms_avg",
        "total_inflow_cms_max",
        "risk_level",
    ]
    if raw_nodes.empty:
        return pd.DataFrame(columns=columns)

    frame = raw_nodes.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["window"] = _window_start(frame["timestamp"], report_step_min)
    frame = frame.dropna(subset=["timestamp", "window"])
    for column in ["depth_m", "head_m", "flooding_cms", "total_inflow_cms"]:
        frame[column] = _numeric(frame, column).fillna(0.0)

    grouped = frame.sort_values("timestamp").groupby(["window", "node_id", "node_type"], as_index=False)
    result = grouped.agg(
        depth_m_avg=("depth_m", "mean"),
        depth_m_max=("depth_m", "max"),
        head_m_avg=("head_m", "mean"),
        head_m_max=("head_m", "max"),
        flooding_cms_instant=("flooding_cms", "last"),
        flooding_cms_max_15min=("flooding_cms", "max"),
        total_inflow_cms_avg=("total_inflow_cms", "mean"),
        total_inflow_cms_max=("total_inflow_cms", "max"),
        sample_count=("flooding_cms", "count"),
        flooding_sum=("flooding_cms", "sum"),
    )
    result["flooding_volume_m3_15min"] = result["flooding_sum"] * raw_sample_step_sec
    max_depth_map = {}
    if not node_info.empty and {"node_id", "max_depth"}.issubset(node_info.columns):
        max_depth_map = node_info.set_index("node_id")["max_depth"].to_dict()
    result["risk_level"] = result.apply(
        lambda row: _risk_from_window(
            float(row["flooding_cms_max_15min"]),
            float(row["flooding_volume_m3_15min"]),
            float(row["depth_m_max"]),
            max_depth_map.get(row["node_id"]),
        ),
        axis=1,
    )
    result = result.rename(columns={"window": "timestamp"})
    return result[columns].sort_values(["timestamp", "node_id"]).reset_index(drop=True)


def aggregate_pump_operation(raw_pumps: pd.DataFrame, report_step_min: int, raw_sample_step_sec: int) -> pd.DataFrame:
    columns = [
        "timestamp",
        "pump_id",
        "pump_station_id",
        "flow_cms_avg",
        "flow_cms_max",
        "setting_avg",
        "status",
        "on_seconds_15min",
        "is_startup",
        "is_shutdown",
        "startup_count_15min",
        "startup_count_cumulative",
        "runtime_min_cumulative",
    ]
    if raw_pumps.empty:
        return pd.DataFrame(columns=columns)

    frame = raw_pumps.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["window"] = _window_start(frame["timestamp"], report_step_min)
    frame["flow_cms"] = _numeric(frame, "flow_cms").fillna(0.0)
    frame["setting"] = _numeric(frame, "setting").fillna(0.0)
    frame["is_on"] = (frame["flow_cms"] > 1e-6) | (frame["setting"] > 0)
    frame = frame.dropna(subset=["timestamp", "window"]).sort_values(["pump_id", "timestamp"])
    frame["previous_is_on"] = frame.groupby("pump_id")["is_on"].shift(fill_value=False)
    frame["startup_event"] = frame["is_on"] & ~frame["previous_is_on"]
    frame["shutdown_event"] = ~frame["is_on"] & frame["previous_is_on"]

    grouped = frame.groupby(["window", "pump_id", "pump_station_id"], as_index=False).agg(
        flow_cms_avg=("flow_cms", "mean"),
        flow_cms_max=("flow_cms", "max"),
        setting_avg=("setting", "mean"),
        any_on=("is_on", "any"),
        on_samples=("is_on", "sum"),
        is_startup=("startup_event", "any"),
        is_shutdown=("shutdown_event", "any"),
        startup_count_15min=("startup_event", "sum"),
    )
    grouped["status"] = grouped["any_on"].map(lambda value: "ON" if bool(value) else "OFF")
    grouped["on_seconds_15min"] = grouped["on_samples"].astype(float) * raw_sample_step_sec
    grouped = grouped.rename(columns={"window": "timestamp"}).sort_values(["pump_id", "timestamp"])
    grouped["startup_count_cumulative"] = grouped.groupby("pump_id")["startup_count_15min"].cumsum()
    grouped["runtime_min_cumulative"] = grouped.groupby("pump_id")["on_seconds_15min"].cumsum() / 60
    return grouped[columns].sort_values(["timestamp", "pump_id"]).reset_index(drop=True)


def aggregate_pump_energy(
    raw_pumps: pd.DataFrame,
    raw_nodes: pd.DataFrame,
    pump_info: pd.DataFrame,
    report_step_min: int,
    pump_efficiency: float,
    default_design_head_m: dict[str, float],
) -> pd.DataFrame:
    columns = [
        "timestamp",
        "pump_id",
        "pump_station_id",
        "flow_cms_avg",
        "flow_cms_max",
        "inlet_head_m_avg",
        "outlet_head_m_avg",
        "pump_head_m",
        "head_source",
        "estimated_power_kw_avg",
        "energy_kwh_interval",
        "cumulative_energy_kwh",
        "unit_energy_kwh_per_kt",
    ]
    if raw_pumps.empty:
        return pd.DataFrame(columns=columns)

    pumps = raw_pumps.copy()
    pumps["timestamp"] = pd.to_datetime(pumps["timestamp"], errors="coerce")
    pumps["window"] = _window_start(pumps["timestamp"], report_step_min)
    pumps["flow_cms"] = _numeric(pumps, "flow_cms").fillna(0.0)

    heads = raw_nodes[["timestamp", "node_id", "head_m"]].copy() if not raw_nodes.empty else pd.DataFrame(columns=["timestamp", "node_id", "head_m"])
    heads["timestamp"] = pd.to_datetime(heads["timestamp"], errors="coerce")
    heads["head_m"] = _numeric(heads, "head_m")
    pumps = pumps.merge(
        heads.rename(columns={"node_id": "inlet_node", "head_m": "inlet_head_m"}),
        on=["timestamp", "inlet_node"],
        how="left",
    )
    pumps = pumps.merge(
        heads.rename(columns={"node_id": "outlet_node", "head_m": "outlet_head_m"}),
        on=["timestamp", "outlet_node"],
        how="left",
    )

    grouped = pumps.groupby(["window", "pump_id", "pump_station_id"], as_index=False).agg(
        flow_cms_avg=("flow_cms", "mean"),
        flow_cms_max=("flow_cms", "max"),
        inlet_head_m_avg=("inlet_head_m", "mean"),
        outlet_head_m_avg=("outlet_head_m", "mean"),
    )
    grouped["pump_head_m"] = (grouped["outlet_head_m_avg"] - grouped["inlet_head_m_avg"]).clip(lower=0).fillna(0.0)
    grouped["head_source"] = "simulated_node_head"
    for pump_id, design_head in default_design_head_m.items():
        mask = (grouped["pump_id"] == pump_id) & (grouped["pump_head_m"] <= 1e-9)
        grouped.loc[mask, "pump_head_m"] = float(design_head)
        grouped.loc[mask, "outlet_head_m_avg"] = grouped.loc[mask, "inlet_head_m_avg"].fillna(0.0) + float(design_head)
        grouped.loc[mask, "head_source"] = "default_design_head_m"
    grouped["estimated_power_kw_avg"] = 0.0
    if pump_efficiency:
        grouped["estimated_power_kw_avg"] = 9.81 * grouped["flow_cms_avg"] * grouped["pump_head_m"] / pump_efficiency
    grouped["energy_kwh_interval"] = grouped["estimated_power_kw_avg"] * (report_step_min / 60)
    grouped["interval_volume_m3"] = grouped["flow_cms_avg"].clip(lower=0) * report_step_min * 60
    grouped = grouped.rename(columns={"window": "timestamp"}).sort_values(["pump_id", "timestamp"])
    grouped["cumulative_energy_kwh"] = grouped.groupby("pump_id")["energy_kwh_interval"].cumsum()
    grouped["cumulative_volume_m3"] = grouped.groupby("pump_id")["interval_volume_m3"].cumsum()
    grouped["unit_energy_kwh_per_kt"] = grouped.apply(
        lambda row: row["cumulative_energy_kwh"] / (row["cumulative_volume_m3"] / 1000)
        if row["cumulative_volume_m3"] > 0
        else 0.0,
        axis=1,
    )
    return grouped[columns].sort_values(["timestamp", "pump_id"]).reset_index(drop=True)


def aggregate_pump_station_levels(
    raw_nodes: pd.DataFrame,
    pump_info: pd.DataFrame,
    node_info: pd.DataFrame,
    report_step_min: int,
) -> pd.DataFrame:
    columns = ["timestamp", "pump_station_id", "forebay_node", "depth_m", "head_m", "percent_full", "level_change_rate_m_per_min"]
    if raw_nodes.empty or pump_info.empty:
        return pd.DataFrame(columns=columns)
    forebays = pump_info[["pump_station_id", "inlet_node"]].drop_duplicates().rename(columns={"inlet_node": "node_id"})
    raw = raw_nodes.copy()
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], errors="coerce")
    raw["window"] = _window_start(raw["timestamp"], report_step_min)
    raw = raw.merge(forebays, on="node_id", how="inner")
    if raw.empty:
        return pd.DataFrame(columns=columns)
    result = raw.groupby(["window", "pump_station_id", "node_id"], as_index=False).agg(depth_m=("depth_m", "max"), head_m=("head_m", "max"))
    max_depth = node_info.set_index("node_id")["max_depth"].to_dict() if {"node_id", "max_depth"}.issubset(node_info.columns) else {}
    result["percent_full"] = result.apply(
        lambda row: (float(row["depth_m"]) / float(max_depth[row["node_id"]]) * 100)
        if row["node_id"] in max_depth and str(max_depth[row["node_id"]]) not in ("", "nan") and float(max_depth[row["node_id"]]) > 0
        else 0.0,
        axis=1,
    )
    result = result.rename(columns={"window": "timestamp", "node_id": "forebay_node"}).sort_values(["pump_station_id", "forebay_node", "timestamp"])
    result["level_change_rate_m_per_min"] = result.groupby(["pump_station_id", "forebay_node"])["depth_m"].diff().fillna(0.0) / report_step_min
    return result[columns].sort_values(["timestamp", "pump_station_id", "forebay_node"]).reset_index(drop=True)
