from __future__ import annotations

import pandas as pd


ENERGY_COLUMNS = [
    "timestamp",
    "pump_id",
    "pump_station_id",
    "flow_cms_avg",
    "energy_kwh_interval",
    "interval_volume_m3",
    "interval_unit_energy_kwh_per_kt",
    "baseline_unit_energy_kwh_per_kt",
    "energy_redundancy_ratio",
    "self_redundancy_grade",
    "unit_energy_rank_in_window",
    "unit_energy_rank_count",
    "unit_energy_percentile_in_window",
    "cross_unit_energy_grade",
    "energy_grade",
]

ENERGY_SUMMARY_COLUMNS = [
    "pump_id",
    "pump_station_id",
    "valid_window_count",
    "active_window_count",
    "runtime_min_total",
    "total_volume_m3",
    "total_energy_kwh",
    "avg_unit_energy_kwh_per_kt",
    "median_unit_energy_kwh_per_kt",
    "p75_unit_energy_kwh_per_kt",
    "baseline_p25_unit_energy_kwh_per_kt",
    "red_window_count",
    "orange_window_count",
    "unit_energy_rank_overall",
    "summary_energy_grade",
]

GRADE_SEVERITY = {"no_data": 0, "green": 1, "yellow": 2, "orange": 3, "red": 4}


def grade_energy(redundancy_ratio: float | None) -> str:
    if pd.isna(redundancy_ratio):
        return "no_data"
    if redundancy_ratio <= 0.10:
        return "green"
    if redundancy_ratio <= 0.30:
        return "yellow"
    if redundancy_ratio <= 0.60:
        return "orange"
    return "red"


def grade_cross_unit_energy(value: float | None, p50: float, p75: float, p90: float) -> str:
    if pd.isna(value):
        return "no_data"
    if value <= p50:
        return "green"
    if value <= p75:
        return "yellow"
    if value <= p90:
        return "orange"
    return "red"


def worst_grade(*grades: str) -> str:
    candidates = [grade for grade in grades if grade in GRADE_SEVERITY]
    if not candidates:
        return "no_data"
    return max(candidates, key=lambda grade: GRADE_SEVERITY[grade])


def grade_summary_energy(row: pd.Series) -> str:
    if int(row.get("valid_window_count", 0) or 0) <= 0:
        return "no_data"
    if int(row.get("red_window_count", 0) or 0) > 0:
        return "red"
    if int(row.get("orange_window_count", 0) or 0) > 0:
        return "orange"
    percentile = row.get("overall_unit_energy_percentile", pd.NA)
    if pd.notna(percentile) and float(percentile) >= 0.75:
        return "orange"
    if pd.notna(percentile) and float(percentile) >= 0.50:
        return "yellow"
    return "green"


def assess_energy(
    pump_energy: pd.DataFrame,
    report_step_min: int = 15,
    min_flow_cms: float = 0.001,
    min_interval_volume_m3: float = 1.0,
) -> pd.DataFrame:
    if pump_energy.empty:
        return pd.DataFrame(columns=ENERGY_COLUMNS)

    frame = pump_energy.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["flow_cms_avg"] = pd.to_numeric(frame["flow_cms_avg"], errors="coerce").fillna(0.0)
    frame["energy_kwh_interval"] = pd.to_numeric(frame["energy_kwh_interval"], errors="coerce").fillna(0.0)
    frame["interval_volume_m3"] = frame["flow_cms_avg"] * float(report_step_min) * 60.0

    valid = (frame["flow_cms_avg"] > min_flow_cms) & (frame["interval_volume_m3"] > min_interval_volume_m3)
    frame["interval_unit_energy_kwh_per_kt"] = pd.NA
    frame.loc[valid, "interval_unit_energy_kwh_per_kt"] = (
        frame.loc[valid, "energy_kwh_interval"] / (frame.loc[valid, "interval_volume_m3"] / 1000.0)
    )
    frame["interval_unit_energy_kwh_per_kt"] = pd.to_numeric(frame["interval_unit_energy_kwh_per_kt"], errors="coerce")

    baseline = (
        frame.loc[valid]
        .groupby("pump_id")["interval_unit_energy_kwh_per_kt"]
        .quantile(0.25)
        .rename("baseline_unit_energy_kwh_per_kt")
    )
    frame = frame.merge(baseline, on="pump_id", how="left")

    frame["energy_redundancy_ratio"] = pd.NA
    usable = valid & frame["baseline_unit_energy_kwh_per_kt"].notna() & (frame["baseline_unit_energy_kwh_per_kt"] > 0)
    frame.loc[usable, "energy_redundancy_ratio"] = (
        (frame.loc[usable, "interval_unit_energy_kwh_per_kt"] - frame.loc[usable, "baseline_unit_energy_kwh_per_kt"])
        / frame.loc[usable, "baseline_unit_energy_kwh_per_kt"]
    )
    frame["energy_redundancy_ratio"] = pd.to_numeric(frame["energy_redundancy_ratio"], errors="coerce")
    frame["self_redundancy_grade"] = frame["energy_redundancy_ratio"].map(grade_energy)

    frame["unit_energy_rank_in_window"] = pd.NA
    frame["unit_energy_rank_count"] = pd.NA
    frame["unit_energy_percentile_in_window"] = pd.NA
    if valid.any():
        rank_source = frame.loc[valid, ["timestamp", "interval_unit_energy_kwh_per_kt"]].copy()
        frame.loc[valid, "unit_energy_rank_in_window"] = rank_source.groupby("timestamp")[
            "interval_unit_energy_kwh_per_kt"
        ].rank(method="min", ascending=False)
        frame.loc[valid, "unit_energy_rank_count"] = rank_source.groupby("timestamp")[
            "interval_unit_energy_kwh_per_kt"
        ].transform("count")
        frame.loc[valid, "unit_energy_percentile_in_window"] = rank_source.groupby("timestamp")[
            "interval_unit_energy_kwh_per_kt"
        ].rank(method="max", pct=True, ascending=True)

    valid_units = frame.loc[valid, "interval_unit_energy_kwh_per_kt"].dropna()
    if valid_units.empty:
        p50 = p75 = p90 = float("nan")
    else:
        p50 = float(valid_units.quantile(0.50))
        p75 = float(valid_units.quantile(0.75))
        p90 = float(valid_units.quantile(0.90))
    frame["cross_unit_energy_grade"] = frame["interval_unit_energy_kwh_per_kt"].map(
        lambda value: grade_cross_unit_energy(value, p50, p75, p90)
    )
    frame["energy_grade"] = [
        worst_grade(self_grade, cross_grade)
        for self_grade, cross_grade in zip(frame["self_redundancy_grade"], frame["cross_unit_energy_grade"])
    ]
    for column in ["unit_energy_rank_in_window", "unit_energy_rank_count", "unit_energy_percentile_in_window"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame[ENERGY_COLUMNS].sort_values(["timestamp", "pump_id"]).reset_index(drop=True)


def build_energy_summary(energy_assessment: pd.DataFrame) -> pd.DataFrame:
    if energy_assessment.empty:
        return pd.DataFrame(columns=ENERGY_SUMMARY_COLUMNS)

    frame = energy_assessment.copy()
    frame["interval_unit_energy_kwh_per_kt"] = pd.to_numeric(
        frame["interval_unit_energy_kwh_per_kt"], errors="coerce"
    )
    frame["interval_volume_m3"] = pd.to_numeric(frame["interval_volume_m3"], errors="coerce").fillna(0.0)
    frame["energy_kwh_interval"] = pd.to_numeric(frame["energy_kwh_interval"], errors="coerce").fillna(0.0)
    frame["flow_cms_avg"] = pd.to_numeric(frame["flow_cms_avg"], errors="coerce").fillna(0.0)
    valid = frame["interval_unit_energy_kwh_per_kt"].notna()
    frame["is_valid_window"] = valid
    frame["is_active_window"] = frame["flow_cms_avg"] > 0.001
    frame["runtime_min_interval"] = 0.0
    active = frame["flow_cms_avg"] > 0.001
    frame.loc[active, "runtime_min_interval"] = (
        frame.loc[active, "interval_volume_m3"] / frame.loc[active, "flow_cms_avg"] / 60.0
    )
    frame["is_red"] = frame["energy_grade"].astype(str) == "red"
    frame["is_orange"] = frame["energy_grade"].astype(str) == "orange"

    grouped = frame.groupby(["pump_id", "pump_station_id"], as_index=False).agg(
        valid_window_count=("is_valid_window", "sum"),
        active_window_count=("is_active_window", "sum"),
        runtime_min_total=("runtime_min_interval", "sum"),
        total_volume_m3=("interval_volume_m3", "sum"),
        total_energy_kwh=("energy_kwh_interval", "sum"),
        avg_unit_energy_kwh_per_kt=("interval_unit_energy_kwh_per_kt", "mean"),
        median_unit_energy_kwh_per_kt=("interval_unit_energy_kwh_per_kt", "median"),
        p75_unit_energy_kwh_per_kt=("interval_unit_energy_kwh_per_kt", lambda value: value.quantile(0.75)),
        baseline_p25_unit_energy_kwh_per_kt=("baseline_unit_energy_kwh_per_kt", "first"),
        red_window_count=("is_red", "sum"),
        orange_window_count=("is_orange", "sum"),
    )
    valid_summary = grouped["avg_unit_energy_kwh_per_kt"].notna()
    grouped["unit_energy_rank_overall"] = pd.NA
    grouped.loc[valid_summary, "unit_energy_rank_overall"] = grouped.loc[valid_summary, "avg_unit_energy_kwh_per_kt"].rank(
        method="min", ascending=False
    )
    grouped["overall_unit_energy_percentile"] = pd.NA
    grouped.loc[valid_summary, "overall_unit_energy_percentile"] = grouped.loc[
        valid_summary, "avg_unit_energy_kwh_per_kt"
    ].rank(method="max", pct=True, ascending=True)
    grouped["summary_energy_grade"] = grouped.apply(grade_summary_energy, axis=1)
    grouped["unit_energy_rank_overall"] = pd.to_numeric(grouped["unit_energy_rank_overall"], errors="coerce")
    return grouped[ENERGY_SUMMARY_COLUMNS].sort_values(
        ["summary_energy_grade", "unit_energy_rank_overall", "pump_id"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
