from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PART2_CSV_DIR = PROJECT_ROOT / "data" / "processed" / "part2_assessment_csv"

CSV_FILES = {
    "summary": "system_status_summary.csv",
    "energy": "energy_assessment_timeseries.csv",
    "energy_summary": "pump_energy_summary.csv",
    "pump_health": "pump_health_assessment.csv",
    "overflow_risk": "overflow_risk_assessment.csv",
}

GRADE_SEVERITY = {"no_data": 0, "green": 1, "yellow": 2, "orange": 3, "red": 4}


app = FastAPI(title="IOT Control Status Assessment API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _frame_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    cleaned = frame.copy()
    for column in cleaned.columns:
        if column.endswith("timestamp") or column == "timestamp":
            cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    cleaned = cleaned.where(pd.notna(cleaned), None)
    return cleaned.to_dict(orient="records")


def _load_csv(key: str) -> pd.DataFrame:
    path = PART2_CSV_DIR / CSV_FILES[key]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Assessment CSV not found: {path}")
    return pd.read_csv(path, low_memory=False)


def _latest_timestamp(*frames: pd.DataFrame) -> pd.Timestamp | None:
    latest_values: list[pd.Timestamp] = []
    for frame in frames:
        if "timestamp" in frame.columns and not frame.empty:
            latest = pd.to_datetime(frame["timestamp"], errors="coerce").max()
            if pd.notna(latest):
                latest_values.append(pd.Timestamp(latest))
    return min(latest_values) if latest_values else None


def _normalize_range(range_name: str, latest: bool = False) -> str:
    if latest:
        return "latest"
    normalized = str(range_name or "latest").lower()
    return normalized if normalized in {"latest", "24h", "all"} else "latest"


def _filter_time_range(frame: pd.DataFrame, range_name: str, latest: bool = False) -> pd.DataFrame:
    if "timestamp" not in frame.columns or frame.empty:
        return frame
    mode = _normalize_range(range_name, latest)
    filtered = frame.copy()
    times = pd.to_datetime(filtered["timestamp"], errors="coerce")
    if mode == "latest":
        return filtered[times == times.max()]
    if mode == "24h":
        latest_time = times.max()
        start = latest_time - pd.Timedelta(hours=24)
        return filtered[(times >= start) & (times <= latest_time)]
    return filtered


def _limit_records(frame: pd.DataFrame, limit: int, range_name: str = "latest", latest: bool = False) -> list[dict[str, Any]]:
    frame = _filter_time_range(frame, range_name, latest)
    if "timestamp" in frame.columns:
        frame = frame.sort_values("timestamp")
    return _frame_to_records(frame.tail(limit))


def _worst_grade(values: pd.Series) -> str:
    grades = values.dropna().astype(str)
    if grades.empty:
        return "no_data"
    return max(grades, key=lambda grade: GRADE_SEVERITY.get(grade, 0))


def _range_summary(energy: pd.DataFrame, health: pd.DataFrame, overflow: pd.DataFrame, range_name: str, latest: bool) -> dict[str, Any]:
    energy_range = _filter_time_range(energy, range_name, latest)
    health_range = _filter_time_range(health, range_name, latest)
    overflow_range = _filter_time_range(overflow, range_name, latest)
    latest_time = _latest_timestamp(energy_range, health_range, overflow_range)

    if not energy_range.empty:
        energy_worst = energy_range.groupby("pump_id")["energy_grade"].apply(_worst_grade)
        red_energy_count = int((energy_worst == "red").sum())
        orange_energy_count = int((energy_worst == "orange").sum())
    else:
        red_energy_count = 0
        orange_energy_count = 0
    low_health_pump_count = int(
        health_range.loc[pd.to_numeric(health_range.get("health_score"), errors="coerce") < 70, "pump_id"].nunique()
    ) if not health_range.empty else 0
    if not overflow_range.empty:
        overflow_worst = overflow_range.groupby("node_id")["risk_grade"].apply(_worst_grade)
        red_overflow_node_count = int((overflow_worst == "red").sum())
    else:
        red_overflow_node_count = 0

    top_energy_pump = ""
    if not energy_range.empty:
        energy_scores = pd.to_numeric(energy_range["interval_unit_energy_kwh_per_kt"], errors="coerce")
        if energy_scores.notna().any():
            top_energy_pump = str(energy_range.loc[energy_scores.idxmax(), "pump_id"])

    lowest_health_pump = ""
    if not health_range.empty:
        health_scores = pd.to_numeric(health_range["health_score"], errors="coerce")
        if health_scores.notna().any():
            lowest_health_pump = str(health_range.loc[health_scores.idxmin(), "pump_id"])

    highest_risk_node = ""
    if not overflow_range.empty:
        risk_scores = pd.to_numeric(overflow_range["overflow_risk_score"], errors="coerce")
        if risk_scores.notna().any():
            highest_risk_node = str(overflow_range.loc[risk_scores.idxmax(), "node_id"])

    return {
        "latest_timestamp": "" if latest_time is None else latest_time.strftime("%Y-%m-%d %H:%M:%S"),
        "red_energy_count": red_energy_count,
        "orange_energy_count": orange_energy_count,
        "low_health_pump_count": low_health_pump_count,
        "red_overflow_node_count": red_overflow_node_count,
        "top_energy_pump": top_energy_pump,
        "lowest_health_pump": lowest_health_pump,
        "highest_risk_node": highest_risk_node,
        "system_energy_grade": _worst_grade(energy_range.get("energy_grade", pd.Series(dtype=str))),
        "system_safety_grade": _worst_grade(health_range.get("safety_grade", pd.Series(dtype=str))),
        "system_overflow_grade": _worst_grade(overflow_range.get("risk_grade", pd.Series(dtype=str))),
    }


def _peak_overflow_by_node(frame: pd.DataFrame, limit: int, range_name: str, latest: bool = False) -> list[dict[str, Any]]:
    filtered = _filter_time_range(frame, range_name, latest)
    if filtered.empty:
        return []
    scores = pd.to_numeric(filtered["overflow_risk_score"], errors="coerce").fillna(-1.0)
    idx = scores.groupby(filtered["node_id"].astype(str)).idxmax()
    result = filtered.loc[idx].sort_values("overflow_risk_score").tail(limit)
    return _frame_to_records(result)


@app.get("/api/part2/summary")
def get_summary(
    range_name: str = Query(default="latest", alias="range", pattern="^(latest|24h|all)$"),
    latest: bool = Query(default=False),
) -> dict[str, Any]:
    return _range_summary(_load_csv("energy"), _load_csv("pump_health"), _load_csv("overflow_risk"), range_name, latest)


@app.get("/api/part2/energy")
def get_energy(
    limit: int = Query(default=5000, ge=1, le=5000),
    range_name: str = Query(default="latest", alias="range", pattern="^(latest|24h|all)$"),
    latest: bool = Query(default=False),
) -> list[dict[str, Any]]:
    return _limit_records(_load_csv("energy"), limit=limit, range_name=range_name, latest=latest)


@app.get("/api/part2/energy-summary")
def get_energy_summary() -> list[dict[str, Any]]:
    return _frame_to_records(_load_csv("energy_summary"))


@app.get("/api/part2/pump-health")
def get_pump_health(
    limit: int = Query(default=5000, ge=1, le=5000),
    range_name: str = Query(default="latest", alias="range", pattern="^(latest|24h|all)$"),
    latest: bool = Query(default=False),
) -> list[dict[str, Any]]:
    return _limit_records(_load_csv("pump_health"), limit=limit, range_name=range_name, latest=latest)


@app.get("/api/part2/overflow-risk")
def get_overflow_risk(
    limit: int = Query(default=5000, ge=1, le=5000),
    range_name: str = Query(default="latest", alias="range", pattern="^(latest|24h|all)$"),
    latest: bool = Query(default=False),
) -> list[dict[str, Any]]:
    return _peak_overflow_by_node(_load_csv("overflow_risk"), limit=limit, range_name=range_name, latest=latest)


@app.get("/api/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}
