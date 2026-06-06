from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


RAINFALL_COLUMNS = ["timestamp", "rain_gage_id", "rainfall_mm", "time_interval_min", "source_file"]


def parse_rainfall_file(path: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = Path(path)
    rows: list[dict[str, Any]] = []
    bad_rows: list[str] = []

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith(";"):
                continue
            parts = line.split()
            if len(parts) < 7:
                bad_rows.append(f"{line_number}: {line}")
                continue
            try:
                gage = parts[0]
                year, month, day, hour, minute = map(int, parts[1:6])
                value = float(parts[6])
                timestamp = pd.Timestamp(year=year, month=month, day=day, hour=hour, minute=minute)
            except (TypeError, ValueError) as exc:
                bad_rows.append(f"{line_number}: {line} ({exc})")
                continue
            rows.append(
                {
                    "timestamp": timestamp,
                    "rain_gage_id": gage,
                    "rainfall_mm": value,
                    "source_file": path.name,
                }
            )

    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=RAINFALL_COLUMNS)
    else:
        frame = frame.sort_values(["rain_gage_id", "timestamp"]).reset_index(drop=True)
        diffs = frame.groupby("rain_gage_id")["timestamp"].diff().dt.total_seconds().div(60)
        frame["time_interval_min"] = diffs.fillna(1).clip(lower=1).round().astype(int)
        frame = frame.sort_values(["timestamp", "rain_gage_id"]).reset_index(drop=True)
        frame = frame[RAINFALL_COLUMNS]

    stats = {
        "source_file": path.name,
        "rows": int(len(frame)),
        "unparsed_rows": len(bad_rows),
        "bad_rows_sample": bad_rows[:20],
        "start_time": "" if frame.empty else str(frame["timestamp"].min()),
        "end_time": "" if frame.empty else str(frame["timestamp"].max()),
        "total_rainfall_mm": 0.0 if frame.empty else float(frame["rainfall_mm"].sum()),
        "max_minute_rainfall_mm": 0.0 if frame.empty else float(frame["rainfall_mm"].max()),
        "missing_values": int(frame.isna().sum().sum()),
    }
    return frame, stats


def build_forecast_scenario(
    observed: pd.DataFrame,
    start_datetime: str,
    forecast_hours: int = 72,
) -> pd.DataFrame:
    columns = [
        "forecast_time",
        "target_time",
        "rain_gage_id",
        "forecast_horizon_min",
        "forecast_rainfall_mm",
        "source",
    ]
    if observed.empty:
        return pd.DataFrame(columns=columns)

    forecast_time = pd.Timestamp(start_datetime)
    periods = int(forecast_hours * 60)
    if periods <= 0:
        return pd.DataFrame(columns=columns)

    target_index = pd.date_range(start=forecast_time, periods=periods, freq="min")
    horizon_end = target_index[-1]
    observed = observed.copy()
    observed["timestamp"] = pd.to_datetime(observed["timestamp"], errors="coerce").dt.floor("min")
    observed["rainfall_mm"] = pd.to_numeric(observed["rainfall_mm"], errors="coerce").fillna(0.0)
    gages = sorted(observed["rain_gage_id"].dropna().astype(str).unique())
    if not gages:
        return pd.DataFrame(columns=columns)

    frames: list[pd.DataFrame] = []
    for gage in gages:
        gage_rows = observed[observed["rain_gage_id"].astype(str) == gage].copy()
        window = gage_rows[(gage_rows["timestamp"] >= forecast_time) & (gage_rows["timestamp"] <= horizon_end)].copy()
        source = "historical_window_minutely"
        if window.empty:
            first = gage_rows["timestamp"].min()
            if pd.isna(first):
                values = pd.Series(0.0, index=target_index)
                source = "zero_filled"
            else:
                fallback_end = first + pd.Timedelta(minutes=periods - 1)
                window = gage_rows[(gage_rows["timestamp"] >= first) & (gage_rows["timestamp"] <= fallback_end)].copy()
                window["timestamp"] = forecast_time + (window["timestamp"] - first)
                source = "historical_shifted_minutely"
                values = window.groupby("timestamp")["rainfall_mm"].sum().reindex(target_index, fill_value=0.0)
        else:
            values = window.groupby("timestamp")["rainfall_mm"].sum().reindex(target_index, fill_value=0.0)

        frame = pd.DataFrame(
            {
                "forecast_time": forecast_time,
                "target_time": target_index,
                "rain_gage_id": gage,
                "forecast_horizon_min": range(periods),
                "forecast_rainfall_mm": values.to_numpy(),
                "source": source,
            }
        )
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)[columns]
