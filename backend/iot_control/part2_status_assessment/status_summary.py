from __future__ import annotations

import pandas as pd


SUMMARY_COLUMNS = [
    "latest_timestamp",
    "red_energy_count",
    "orange_energy_count",
    "low_health_pump_count",
    "red_overflow_node_count",
    "top_energy_pump",
    "lowest_health_pump",
    "highest_risk_node",
    "system_energy_grade",
    "system_safety_grade",
    "system_overflow_grade",
]


GRADE_ORDER = {"no_data": -1, "green": 0, "yellow": 1, "orange": 2, "red": 3}


def _latest_common_timestamp(*frames: pd.DataFrame) -> pd.Timestamp | None:
    latest_values: list[pd.Timestamp] = []
    for frame in frames:
        if frame.empty:
            continue
        time_col = "timestamp" if "timestamp" in frame.columns else "latest_timestamp"
        times = pd.to_datetime(frame[time_col], errors="coerce")
        if times.notna().any():
            latest_values.append(pd.Timestamp(times.max()))
    if not latest_values:
        return None
    return min(latest_values)


def _worst_grade(series: pd.Series) -> str:
    if series.empty:
        return "no_data"
    return max(series.fillna("no_data").astype(str), key=lambda grade: GRADE_ORDER.get(grade, -1))


def build_system_summary(energy: pd.DataFrame, health: pd.DataFrame, overflow: pd.DataFrame) -> pd.DataFrame:
    latest = _latest_common_timestamp(energy, health, overflow)
    if latest is None:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    energy_latest = energy[pd.to_datetime(energy["timestamp"], errors="coerce") == latest].copy() if not energy.empty else pd.DataFrame()
    health_latest = health[pd.to_datetime(health["timestamp"], errors="coerce") == latest].copy() if not health.empty else pd.DataFrame()
    overflow_latest = overflow[pd.to_datetime(overflow["timestamp"], errors="coerce") == latest].copy() if not overflow.empty else pd.DataFrame()

    top_energy_pump = ""
    if not energy_latest.empty:
        energy_latest["energy_rank_value"] = pd.to_numeric(
            energy_latest["energy_redundancy_ratio"], errors="coerce"
        ).fillna(-999.0)
        top_energy_pump = str(energy_latest.sort_values("energy_rank_value", ascending=False).iloc[0]["pump_id"])

    lowest_health_pump = ""
    if not health_latest.empty:
        health_latest["health_score_numeric"] = pd.to_numeric(health_latest["health_score"], errors="coerce").fillna(999.0)
        lowest_health_pump = str(health_latest.sort_values("health_score_numeric").iloc[0]["pump_id"])

    highest_risk_node = ""
    if not overflow_latest.empty:
        overflow_latest["risk_score_numeric"] = pd.to_numeric(overflow_latest["overflow_risk_score"], errors="coerce").fillna(-1.0)
        highest_risk_node = str(overflow_latest.sort_values("risk_score_numeric", ascending=False).iloc[0]["node_id"])

    row = {
        "latest_timestamp": latest,
        "red_energy_count": int((energy_latest.get("energy_grade", pd.Series(dtype=str)) == "red").sum()),
        "orange_energy_count": int((energy_latest.get("energy_grade", pd.Series(dtype=str)) == "orange").sum()),
        "low_health_pump_count": int(pd.to_numeric(health_latest.get("health_score", pd.Series(dtype=float)), errors="coerce").lt(70).sum()),
        "red_overflow_node_count": int((overflow_latest.get("risk_grade", pd.Series(dtype=str)) == "red").sum()),
        "top_energy_pump": top_energy_pump,
        "lowest_health_pump": lowest_health_pump,
        "highest_risk_node": highest_risk_node,
        "system_energy_grade": _worst_grade(energy_latest.get("energy_grade", pd.Series(dtype=str))),
        "system_safety_grade": _worst_grade(health_latest.get("safety_grade", pd.Series(dtype=str))),
        "system_overflow_grade": _worst_grade(overflow_latest.get("risk_grade", pd.Series(dtype=str))),
    }
    return pd.DataFrame([row], columns=SUMMARY_COLUMNS)
