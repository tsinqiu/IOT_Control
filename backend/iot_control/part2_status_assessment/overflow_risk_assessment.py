from __future__ import annotations

import pandas as pd


OVERFLOW_COLUMNS = [
    "timestamp",
    "node_id",
    "x_coord",
    "y_coord",
    "level_ratio",
    "level_score",
    "rainfall_next_1h_mm",
    "rainfall_next_2h_mm",
    "rainfall_source_1h",
    "rainfall_source_2h",
    "rain_1h_score",
    "rain_2h_score",
    "flooding_history_score",
    "overflow_risk_score",
    "risk_grade",
]


def grade_overflow(score: float) -> str:
    if score >= 0.80:
        return "red"
    if score >= 0.60:
        return "orange"
    if score >= 0.30:
        return "yellow"
    return "green"


def _rainfall_lookup(rainfall_forecast: pd.DataFrame) -> pd.DataFrame:
    if rainfall_forecast.empty:
        return pd.DataFrame(columns=["timestamp", "rainfall_mm"])
    rain = rainfall_forecast.copy()
    rain["target_time"] = pd.to_datetime(rain["target_time"], errors="coerce").dt.floor("min")
    rain["forecast_rainfall_mm"] = pd.to_numeric(rain["forecast_rainfall_mm"], errors="coerce").fillna(0.0)
    minute = (
        rain.groupby("target_time")["forecast_rainfall_mm"]
        .mean()
        .rename("rainfall_mm")
        .reset_index()
        .rename(columns={"target_time": "timestamp"})
        .sort_values("timestamp")
    )
    return minute


def _observed_rainfall_lookup(rainfall_observed: pd.DataFrame | None) -> pd.DataFrame:
    if rainfall_observed is None or rainfall_observed.empty:
        return pd.DataFrame(columns=["timestamp", "rainfall_mm"])
    rain = rainfall_observed.copy()
    rain["timestamp"] = pd.to_datetime(rain["timestamp"], errors="coerce").dt.floor("min")
    rain["rainfall_mm"] = pd.to_numeric(rain["rainfall_mm"], errors="coerce").fillna(0.0)
    return rain.groupby("timestamp")["rainfall_mm"].mean().reset_index().sort_values("timestamp")


def _sum_rainfall(minute: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    if minute.empty:
        return 0.0
    mask = (minute["timestamp"] >= start) & (minute["timestamp"] < end)
    return float(minute.loc[mask, "rainfall_mm"].sum())


def _future_rainfall_by_window(
    timestamps: pd.Series,
    rainfall_forecast: pd.DataFrame,
    hours: int,
    rainfall_observed: pd.DataFrame | None = None,
) -> tuple[dict[pd.Timestamp, float], dict[pd.Timestamp, str]]:
    forecast_minute = _rainfall_lookup(rainfall_forecast)
    observed_minute = _observed_rainfall_lookup(rainfall_observed)
    result: dict[pd.Timestamp, float] = {}
    source: dict[pd.Timestamp, str] = {}
    unique_times = pd.to_datetime(timestamps.dropna().unique())
    for timestamp in unique_times:
        start = pd.Timestamp(timestamp)
        end = start + pd.Timedelta(hours=hours)
        forecast_covers = (
            not forecast_minute.empty
            and forecast_minute["timestamp"].min() <= start
            and forecast_minute["timestamp"].max() >= end - pd.Timedelta(minutes=1)
        )
        if forecast_covers:
            result[start] = _sum_rainfall(forecast_minute, start, end)
            source[start] = "forecast"
        elif not observed_minute.empty:
            result[start] = _sum_rainfall(observed_minute, start, end)
            source[start] = "observed_replay"
        else:
            result[start] = 0.0
            source[start] = "missing"
    return result, source


def assess_overflow_risk(
    node_level: pd.DataFrame,
    node_info: pd.DataFrame,
    rainfall_forecast: pd.DataFrame,
    rainfall_observed: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if node_level.empty:
        return pd.DataFrame(columns=OVERFLOW_COLUMNS)

    frame = node_level.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["depth_m_max"] = pd.to_numeric(frame["depth_m_max"], errors="coerce").fillna(0.0)
    frame["flooding_cms_max_15min"] = pd.to_numeric(frame["flooding_cms_max_15min"], errors="coerce").fillna(0.0)

    info = node_info.copy()
    info["max_depth_numeric"] = pd.to_numeric(info.get("max_depth", 0.0), errors="coerce").fillna(0.0)
    info["node_type"] = info.get("node_type", "").astype(str)
    frame = frame.merge(
        info[["node_id", "node_type", "max_depth_numeric", "x_coord", "y_coord"]],
        on="node_id",
        how="left",
        suffixes=("", "_info"),
    )
    if "node_type_info" in frame.columns:
        frame["node_type"] = frame["node_type_info"].fillna(frame["node_type"])

    valid_depth = (frame["max_depth_numeric"] > 0) & (frame["node_type"].astype(str).str.lower() != "outfall")
    frame["level_ratio"] = 0.0
    frame.loc[valid_depth, "level_ratio"] = frame.loc[valid_depth, "depth_m_max"] / frame.loc[valid_depth, "max_depth_numeric"]
    frame["level_ratio"] = pd.to_numeric(frame["level_ratio"], errors="coerce").fillna(0.0)
    frame["level_score"] = frame["level_ratio"].clip(lower=0.0, upper=1.0)

    rain_1h, rain_source_1h = _future_rainfall_by_window(frame["timestamp"], rainfall_forecast, 1, rainfall_observed)
    rain_2h, rain_source_2h = _future_rainfall_by_window(frame["timestamp"], rainfall_forecast, 2, rainfall_observed)
    frame["rainfall_next_1h_mm"] = frame["timestamp"].map(rain_1h).fillna(0.0)
    frame["rainfall_next_2h_mm"] = frame["timestamp"].map(rain_2h).fillna(0.0)
    frame["rainfall_source_1h"] = frame["timestamp"].map(rain_source_1h).fillna("missing")
    frame["rainfall_source_2h"] = frame["timestamp"].map(rain_source_2h).fillna("missing")
    frame["rain_1h_score"] = (frame["rainfall_next_1h_mm"] / 10.0).clip(lower=0.0, upper=1.0)
    frame["rain_2h_score"] = (frame["rainfall_next_2h_mm"] / 20.0).clip(lower=0.0, upper=1.0)

    flooded_nodes = set(frame.loc[frame["flooding_cms_max_15min"] > 0, "node_id"].astype(str))
    current_flooding = frame["flooding_cms_max_15min"] > 0
    frame["flooding_history_score"] = frame["node_id"].astype(str).map(lambda node_id: 0.5 if node_id in flooded_nodes else 0.0)
    frame.loc[current_flooding, "flooding_history_score"] = 1.0

    frame["overflow_risk_score"] = (
        0.45 * frame["level_score"]
        + 0.20 * frame["rain_1h_score"]
        + 0.15 * frame["rain_2h_score"]
        + 0.20 * frame["flooding_history_score"]
    ).clip(lower=0.0, upper=1.0)
    frame.loc[current_flooding, "overflow_risk_score"] = frame.loc[current_flooding, "overflow_risk_score"].clip(lower=0.80)
    frame["risk_grade"] = frame["overflow_risk_score"].map(grade_overflow)
    frame.loc[current_flooding, "risk_grade"] = "red"

    return frame[OVERFLOW_COLUMNS].sort_values(["timestamp", "node_id"]).reset_index(drop=True)
