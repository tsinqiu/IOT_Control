from __future__ import annotations

import pandas as pd


HEALTH_COLUMNS = [
    "timestamp",
    "pump_id",
    "pump_station_id",
    "startup_count_24h",
    "runtime_min_24h",
    "repeated_start_count_30min",
    "continuous_runtime_min",
    "max_forebay_percent_full",
    "max_abs_level_change_rate_m_per_min",
    "health_score",
    "fatigue_index",
    "safety_grade",
    "deduction_detail",
]


def grade_safety(score: float) -> str:
    if score >= 85:
        return "green"
    if score >= 70:
        return "yellow"
    if score >= 55:
        return "orange"
    return "red"


def _rolling_sum_by_time(frame: pd.DataFrame, group_col: str, value_col: str, window: str) -> pd.Series:
    pieces: list[pd.Series] = []
    for _, group in frame.sort_values("timestamp").groupby(group_col, sort=False):
        rolled = group.set_index("timestamp")[value_col].rolling(window, min_periods=1, closed="right").sum()
        pieces.append(pd.Series(rolled.to_numpy(), index=group.index))
    if not pieces:
        return pd.Series(dtype=float)
    return pd.concat(pieces).sort_index()


def _rolling_max_by_time(frame: pd.DataFrame, group_col: str, value_col: str, window: str) -> pd.Series:
    pieces: list[pd.Series] = []
    for _, group in frame.sort_values("timestamp").groupby(group_col, sort=False):
        rolled = group.set_index("timestamp")[value_col].rolling(window, min_periods=1, closed="right").max()
        pieces.append(pd.Series(rolled.to_numpy(), index=group.index))
    if not pieces:
        return pd.Series(dtype=float)
    return pd.concat(pieces).sort_index()


def _continuous_runtime(group: pd.DataFrame) -> pd.Series:
    total = 0.0
    values: list[float] = []
    for seconds in group["on_seconds_15min"].fillna(0.0):
        minutes = float(seconds) / 60.0
        if minutes > 0:
            total += minutes
        else:
            total = 0.0
        values.append(total)
    return pd.Series(values, index=group.index)


def _deduct(row: pd.Series) -> tuple[float, str]:
    deductions: list[tuple[float, str]] = []

    repeated = float(row.get("repeated_start_count_30min", 0.0) or 0.0)
    if repeated > 0:
        deductions.append((8.0 * repeated, f"30min repeated starts={repeated:.0f}"))

    starts_24h = float(row.get("startup_count_24h", 0.0) or 0.0)
    if starts_24h > 10:
        deductions.append((starts_24h - 10.0, f"24h starts={starts_24h:.0f}"))

    runtime_24h = float(row.get("runtime_min_24h", 0.0) or 0.0)
    if runtime_24h > 1320:
        deductions.append((15.0, f"24h runtime load>{runtime_24h:.0f}min"))
    elif runtime_24h > 1080:
        deductions.append((10.0, f"24h runtime load>{runtime_24h:.0f}min"))
    elif runtime_24h > 720:
        deductions.append((5.0, f"24h runtime load>{runtime_24h:.0f}min"))

    continuous = float(row.get("continuous_runtime_min", 0.0) or 0.0)
    if continuous > 480:
        deductions.append((12.0, f"continuous runtime>{continuous:.0f}min"))
    elif continuous > 240:
        deductions.append((5.0, f"continuous runtime>{continuous:.0f}min"))

    forebay = float(row.get("max_forebay_percent_full", 0.0) or 0.0)
    if forebay > 95:
        deductions.append((15.0, f"forebay>{forebay:.1f}%"))
    elif forebay > 80:
        deductions.append((8.0, f"forebay>{forebay:.1f}%"))

    level_rate = float(row.get("max_abs_level_change_rate_m_per_min", 0.0) or 0.0)
    if level_rate > 0.1:
        deductions.append((5.0, f"level change rate>{level_rate:.3f}m/min"))

    total = sum(value for value, _ in deductions)
    detail = "; ".join(text for _, text in deductions) if deductions else "none"
    return total, detail


def assess_pump_health(pump_operation: pd.DataFrame, pump_station_levels: pd.DataFrame) -> pd.DataFrame:
    if pump_operation.empty:
        return pd.DataFrame(columns=HEALTH_COLUMNS)

    operation = pump_operation.copy()
    operation["timestamp"] = pd.to_datetime(operation["timestamp"], errors="coerce")
    operation["startup_count_15min"] = pd.to_numeric(operation["startup_count_15min"], errors="coerce").fillna(0.0)
    operation["on_seconds_15min"] = pd.to_numeric(operation["on_seconds_15min"], errors="coerce").fillna(0.0)
    operation = operation.sort_values(["pump_id", "timestamp"]).reset_index(drop=True)

    operation["startup_count_24h"] = _rolling_sum_by_time(operation, "pump_id", "startup_count_15min", "24h")
    operation["runtime_min_interval"] = operation["on_seconds_15min"] / 60.0
    operation["runtime_min_24h"] = _rolling_sum_by_time(operation, "pump_id", "runtime_min_interval", "24h")
    operation["startup_count_30min"] = _rolling_sum_by_time(operation, "pump_id", "startup_count_15min", "30min")
    operation["repeated_start_count_30min"] = (operation["startup_count_30min"] - 1.0).clip(lower=0.0)
    continuous_parts = [_continuous_runtime(group) for _, group in operation.groupby("pump_id", sort=False)]
    operation["continuous_runtime_min"] = pd.concat(continuous_parts).sort_index()

    levels = pump_station_levels.copy()
    if not levels.empty:
        levels["timestamp"] = pd.to_datetime(levels["timestamp"], errors="coerce")
        levels["percent_full"] = pd.to_numeric(levels["percent_full"], errors="coerce").fillna(0.0)
        levels["level_change_rate_m_per_min"] = pd.to_numeric(
            levels["level_change_rate_m_per_min"], errors="coerce"
        ).fillna(0.0)
        levels["abs_level_change_rate_m_per_min"] = levels["level_change_rate_m_per_min"].abs()
        levels = levels.sort_values(["pump_station_id", "timestamp"]).reset_index(drop=True)
        levels["max_forebay_percent_full"] = _rolling_max_by_time(levels, "pump_station_id", "percent_full", "24h")
        levels["max_abs_level_change_rate_m_per_min"] = _rolling_max_by_time(
            levels, "pump_station_id", "abs_level_change_rate_m_per_min", "24h"
        )
        station_metrics = levels[
            ["timestamp", "pump_station_id", "max_forebay_percent_full", "max_abs_level_change_rate_m_per_min"]
        ]
        operation = operation.merge(station_metrics, on=["timestamp", "pump_station_id"], how="left")
    else:
        operation["max_forebay_percent_full"] = 0.0
        operation["max_abs_level_change_rate_m_per_min"] = 0.0

    operation["max_forebay_percent_full"] = operation["max_forebay_percent_full"].fillna(0.0)
    operation["max_abs_level_change_rate_m_per_min"] = operation["max_abs_level_change_rate_m_per_min"].fillna(0.0)

    deduction = operation.apply(_deduct, axis=1)
    operation["deduction"] = [item[0] for item in deduction]
    operation["deduction_detail"] = [item[1] for item in deduction]
    operation["health_score"] = (100.0 - operation["deduction"]).clip(lower=0.0, upper=100.0)
    operation["fatigue_index"] = 1.0 - operation["health_score"] / 100.0
    operation["safety_grade"] = operation["health_score"].map(grade_safety)

    return operation[HEALTH_COLUMNS].sort_values(["timestamp", "pump_id"]).reset_index(drop=True)
