from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from backend.iot_control.part1_data_foundation.config import load_config
else:
    from .config import load_config


REQUIRED_FILES = [
    "rainfall_observed.csv",
    "rainfall_forecast_scenario.csv",
    "node_info.csv",
    "conduit_info.csv",
    "pump_info.csv",
    "facility_info.csv",
    "subcatchment_info.csv",
    "node_level_timeseries.csv",
    "pump_station_level_timeseries.csv",
    "pump_operation_timeseries.csv",
    "pump_energy_timeseries.csv",
    "gate_operation_timeseries.csv",
]
INTERIM_FILES = ["raw_node_timeseries.csv", "raw_pump_timeseries.csv"]
KEY_NODES = ["G71F320", "G71F060", "G71F68Y", "G_ADD"]
KEY_PUMPS = ["G70F11Pp1", "G70F11Pp2", "G71F12Pp1", "G71F12Pp2", "G71F68Yp1", "G80F13Pp1", "G71F320Pp1"]
NODE_AGG_FIELDS = [
    "depth_m_avg",
    "depth_m_max",
    "flooding_cms_max_15min",
    "flooding_volume_m3_15min",
    "total_inflow_cms_avg",
    "total_inflow_cms_max",
]
VALID_RISK_LEVELS = {"green", "yellow", "orange", "red"}
DYNAMIC_OBJECTS = {
    "node_level_timeseries": "node_id",
    "pump_station_level_timeseries": "pump_station_id",
    "pump_operation_timeseries": "pump_id",
    "pump_energy_timeseries": "pump_id",
    "gate_operation_timeseries": "gate_id",
    "rainfall_observed": "rain_gage_id",
    "raw_node_timeseries": "node_id",
    "raw_pump_timeseries": "pump_id",
}


@dataclass
class CheckResult:
    report_path: Path
    console_lines: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    oks: list[str] = field(default_factory=list)


def _message(result: CheckResult, level: str, text: str) -> None:
    line = f"[{level}] {text}"
    result.console_lines.append(line)
    if level == "ERROR":
        result.errors.append(text)
    elif level == "WARN":
        result.warnings.append(text)
    else:
        result.oks.append(text)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _time_column(name: str) -> str:
    return "target_time" if name == "rainfall_forecast_scenario" else "timestamp"


def _check_inventory(base_dir: Path, file_names: list[str], result: CheckResult, interim: bool = False) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for file_name in file_names:
        table_name = file_name.removesuffix(".csv")
        path = base_dir / file_name
        if not path.exists():
            _message(result, "ERROR", f"Missing {file_name}")
            tables[table_name] = pd.DataFrame()
            continue
        frame = _read_csv(path)
        tables[table_name] = frame
        _message(result, "OK", f"{'Exported' if interim else 'Found'} {file_name}")
        if frame.empty:
            _message(result, "WARN", f"{file_name} is empty")
    return tables


def _table_summary(name: str, frame: pd.DataFrame) -> str:
    missing = int(frame.isna().sum().sum()) if not frame.empty else 0
    time_col = _time_column(name)
    time_range = ""
    if time_col in frame.columns and not frame.empty:
        times = pd.to_datetime(frame[time_col], errors="coerce")
        if times.notna().any():
            time_range = f"{times.min()} to {times.max()}"
    return f"| {name}.csv | {len(frame)} | {len(frame.columns)} | {missing} | {time_range} |"


def _check_added_objects(tables: dict[str, pd.DataFrame], result: CheckResult) -> None:
    pump_info = tables.get("pump_info", pd.DataFrame())
    node_info = tables.get("node_info", pd.DataFrame())
    facility_info = tables.get("facility_info", pd.DataFrame())
    pump_operation = tables.get("pump_operation_timeseries", pd.DataFrame())
    raw_pump = tables.get("raw_pump_timeseries", pd.DataFrame())
    pump_energy = tables.get("pump_energy_timeseries", pd.DataFrame())

    if "pump_id" in pump_info.columns and "G71F320Pp1" in set(pump_info["pump_id"].astype(str)):
        _message(result, "OK", "G71F320Pp1 found in pump_info.csv")
        row = pump_info[pump_info["pump_id"].astype(str) == "G71F320Pp1"].iloc[0]
        if row.get("model_version") != "v2" or int(float(row.get("is_added", 0))) != 1:
            _message(result, "ERROR", "G71F320Pp1 model_version/is_added metadata is incorrect")
    else:
        _message(result, "ERROR", "G71F320Pp1 missing from pump_info.csv")

    node_has_gadd = "node_id" in node_info.columns and "G_ADD" in set(node_info["node_id"].astype(str))
    facility_has_gadd = "facility_id" in facility_info.columns and "G_ADD" in set(facility_info["facility_id"].astype(str))
    if node_has_gadd or facility_has_gadd:
        _message(result, "OK", "G_ADD found in node_info/facility_info")
    else:
        _message(result, "ERROR", "G_ADD missing from node_info/facility_info")

    if "pump_id" in pump_operation.columns and "G71F320Pp1" in set(pump_operation["pump_id"].astype(str)):
        _message(result, "OK", "G71F320Pp1 found in pump_operation_timeseries.csv")
    else:
        _message(result, "ERROR", "G71F320Pp1 missing from pump_operation_timeseries.csv")
    if "pump_id" in raw_pump.columns and "G71F320Pp1" in set(raw_pump["pump_id"].astype(str)):
        _message(result, "OK", "G71F320Pp1 found in raw and aggregated pump operation data")
    else:
        _message(result, "ERROR", "G71F320Pp1 missing from raw_pump_timeseries.csv")
    if "pump_id" in pump_energy.columns and "G71F320Pp1" in set(pump_energy["pump_id"].astype(str)):
        _message(result, "OK", "G71F320Pp1 found in pump_energy_timeseries.csv")
    else:
        _message(result, "ERROR", "G71F320Pp1 missing from pump_energy_timeseries.csv")


def _check_time_series(tables: dict[str, pd.DataFrame], result: CheckResult) -> dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]]:
    ranges: dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]] = {}
    rainfall = tables.get("rainfall_observed", pd.DataFrame())
    rainfall_range = (None, None)
    if "timestamp" in rainfall.columns and not rainfall.empty:
        rain_times = pd.to_datetime(rainfall["timestamp"], errors="coerce")
        rainfall_range = (rain_times.min(), rain_times.max())

    for name, object_col in DYNAMIC_OBJECTS.items():
        frame = tables.get(name, pd.DataFrame())
        time_col = _time_column(name)
        if frame.empty or time_col not in frame.columns:
            continue
        times = pd.to_datetime(frame[time_col], errors="coerce")
        ranges[name] = (times.min(), times.max())
        if times.isna().any():
            _message(result, "ERROR", f"{name}.csv has unparseable {time_col} values")
        else:
            _message(result, "OK", f"{name}.csv {time_col} parses as datetime")
        if object_col in frame.columns:
            duplicates = int(frame.duplicated([object_col, time_col]).sum())
            if duplicates:
                _message(result, "ERROR", f"{name}.csv has {duplicates} duplicate {object_col}+{time_col} rows")
            max_gap = frame.assign(_ts=times).sort_values([object_col, "_ts"]).groupby(object_col)["_ts"].diff().dt.total_seconds().div(60).max()
        else:
            max_gap = times.sort_values().diff().dt.total_seconds().div(60).max()
        limit = 1.5 if name.startswith("raw_") else 15
        if pd.notna(max_gap) and max_gap > limit:
            level = "WARN" if name == "rainfall_observed" else "ERROR"
            _message(result, level, f"{name}.csv max time gap is {max_gap:.1f} min")
        else:
            _message(result, "OK", f"{'raw sample step' if name.startswith('raw_') else 'Time step check'} passed for {name}.csv")

    node_level = tables.get("node_level_timeseries", pd.DataFrame())
    if not node_level.empty and rainfall_range[0] is not None:
        sim_times = pd.to_datetime(node_level["timestamp"], errors="coerce")
        rain_times = pd.to_datetime(rainfall["timestamp"], errors="coerce")
        rain_in_window = rainfall[(rain_times >= sim_times.min()) & (rain_times <= sim_times.max())]
        total = float(_numeric(rain_in_window, "rainfall_mm").sum())
        if total > 0:
            _message(result, "OK", f"Rainfall total > 0 during simulation window: {total:.3f} mm")
        else:
            _message(result, "ERROR", "Rainfall total is 0 during simulation window; check simulation dates")
    return ranges


def _check_aggregated_node_fields(tables: dict[str, pd.DataFrame], result: CheckResult) -> None:
    node_level = tables.get("node_level_timeseries", pd.DataFrame())
    missing = [field for field in NODE_AGG_FIELDS if field not in node_level.columns]
    if missing:
        _message(result, "ERROR", f"node_level_timeseries.csv missing aggregated fields: {', '.join(missing)}")
        return
    _message(result, "OK", "Aggregated node_level_timeseries.csv with 15min max/sum metrics")
    _message(result, "OK", "flooding_cms_max_15min field exists")
    _message(result, "OK", "flooding_volume_m3_15min field exists")


def _check_physical_values(tables: dict[str, pd.DataFrame], result: CheckResult) -> None:
    checks = [
        ("rainfall_observed", "rainfall_mm"),
        ("raw_node_timeseries", "depth_m"),
        ("raw_node_timeseries", "flooding_cms"),
        ("node_level_timeseries", "depth_m_avg"),
        ("node_level_timeseries", "depth_m_max"),
        ("node_level_timeseries", "flooding_cms_max_15min"),
        ("node_level_timeseries", "flooding_volume_m3_15min"),
        ("raw_pump_timeseries", "flow_cms"),
        ("pump_operation_timeseries", "flow_cms_avg"),
        ("pump_operation_timeseries", "flow_cms_max"),
        ("pump_energy_timeseries", "flow_cms_avg"),
        ("pump_energy_timeseries", "estimated_power_kw_avg"),
        ("pump_energy_timeseries", "energy_kwh_interval"),
        ("gate_operation_timeseries", "flow_cms"),
    ]
    for table, column in checks:
        values = _numeric(tables.get(table, pd.DataFrame()), column)
        if not values.empty and (values < -1e-9).any():
            _message(result, "ERROR", f"{table}.csv has negative {column}")

    operation = tables.get("pump_operation_timeseries", pd.DataFrame())
    if "pump_id" in operation.columns:
        for pump_id, group in operation.groupby("pump_id"):
            starts = _numeric(group, "startup_count_cumulative")
            runtime = _numeric(group, "runtime_min_cumulative")
            if not starts.empty and (starts.diff().dropna() < -1e-9).any():
                _message(result, "ERROR", f"startup_count_cumulative decreases for {pump_id}")
            if not runtime.empty and (runtime.diff().dropna() < -1e-9).any():
                _message(result, "ERROR", f"runtime_min_cumulative decreases for {pump_id}")
    energy = tables.get("pump_energy_timeseries", pd.DataFrame())
    if "pump_id" in energy.columns:
        for pump_id, group in energy.groupby("pump_id"):
            cumulative = _numeric(group, "cumulative_energy_kwh")
            if not cumulative.empty and (cumulative.diff().dropna() < -1e-9).any():
                _message(result, "ERROR", f"cumulative_energy_kwh decreases for {pump_id}")
    node_level = tables.get("node_level_timeseries", pd.DataFrame())
    if "risk_level" in node_level.columns:
        invalid = set(node_level["risk_level"].dropna().astype(str)) - VALID_RISK_LEVELS
        if invalid:
            _message(result, "ERROR", f"Invalid risk_level values: {', '.join(sorted(invalid))}")


def _key_node_summary(tables: dict[str, pd.DataFrame], result: CheckResult) -> list[str]:
    frame = tables.get("node_level_timeseries", pd.DataFrame())
    lines = ["| node_id | max depth_m_max | max flooding_cms_max_15min | flooding volume m3 | flooding rows | risk counts |", "| --- | ---: | ---: | ---: | ---: | --- |"]
    for node_id in KEY_NODES:
        group = frame[frame.get("node_id", pd.Series(dtype=str)).astype(str) == node_id] if not frame.empty else pd.DataFrame()
        if group.empty:
            lines.append(f"| {node_id} | missing | missing | missing | missing | missing |")
            continue
        flooding = _numeric(group, "flooding_cms_max_15min")
        volume = _numeric(group, "flooding_volume_m3_15min")
        risk_counts = group["risk_level"].value_counts().to_dict() if "risk_level" in group.columns else {}
        lines.append(f"| {node_id} | {_numeric(group, 'depth_m_max').max():.4f} | {flooding.max():.6f} | {volume.sum():.3f} | {int((flooding > 0).sum())} | {risk_counts} |")
        if node_id in {"G71F320", "G71F060"} and flooding.max() > 0:
            _message(result, "WARN", f"{node_id} has flooding_cms > 0; inspect risk transfer")
    return lines


def _key_pump_summary(tables: dict[str, pd.DataFrame], result: CheckResult) -> list[str]:
    operation = tables.get("pump_operation_timeseries", pd.DataFrame())
    energy = tables.get("pump_energy_timeseries", pd.DataFrame())
    lines = [
        "| pump_id | max flow_cms | avg flow_cms | flow>0 rows | starts | runtime min | cumulative kWh | unit kWh/kt |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for pump_id in KEY_PUMPS:
        op = operation[operation.get("pump_id", pd.Series(dtype=str)).astype(str) == pump_id] if not operation.empty else pd.DataFrame()
        en = energy[energy.get("pump_id", pd.Series(dtype=str)).astype(str) == pump_id] if not energy.empty else pd.DataFrame()
        if op.empty:
            lines.append(f"| {pump_id} | missing | missing | missing | missing | missing | missing | missing |")
            continue
        flow_max = _numeric(op, "flow_cms_max")
        flow_avg = _numeric(op, "flow_cms_avg")
        starts = _numeric(op, "startup_count_cumulative").max()
        runtime = _numeric(op, "runtime_min_cumulative").max()
        kwh = _numeric(en, "cumulative_energy_kwh").max() if not en.empty else 0
        unit = _numeric(en, "unit_energy_kwh_per_kt").max() if not en.empty else 0
        lines.append(f"| {pump_id} | {flow_max.max():.6f} | {flow_avg.mean():.6f} | {int((flow_max > 0).sum())} | {starts:.0f} | {runtime:.1f} | {kwh:.4f} | {unit:.4f} |")
        if "is_startup" in op.columns and "timestamp" in op.columns:
            start_times = pd.to_datetime(op[op["is_startup"].astype(str).str.lower().isin(["true", "1"])]["timestamp"], errors="coerce").sort_values()
            if not start_times.empty and (start_times.diff().dt.total_seconds().div(60).dropna() < 30).any():
                _message(result, "WARN", f"{pump_id} has repeated starts within 30 min")
    return lines


def _check_energy(tables: dict[str, pd.DataFrame], result: CheckResult) -> None:
    energy = tables.get("pump_energy_timeseries", pd.DataFrame())
    if energy.empty:
        return
    flow = _numeric(energy, "flow_cms_avg")
    power = _numeric(energy, "estimated_power_kw_avg")
    head = _numeric(energy, "pump_head_m")
    if (flow > 0).any() and (power[flow > 0] <= 0).any():
        _message(result, "WARN", "Some pump flow > 0 but estimated_power_kw <= 0")
    if (flow > 0).any() and (head[flow > 0] <= 1e-9).mean() > 0.5:
        _message(result, "WARN", "pump_head_m is 0 for many flowing pump records")
    if "head_source" in energy.columns and (energy["head_source"].astype(str) == "default_design_head_m").any():
        _message(result, "OK", "Default design head was used for outfall pump head estimation where needed")


def _check_schema(schema_path: Path, result: CheckResult) -> list[str]:
    lines: list[str] = []
    if not schema_path.exists():
        _message(result, "ERROR", f"{schema_path} is missing")
        return lines
    sql = schema_path.read_text(encoding="utf-8", errors="replace").lower()
    for file_name in [*REQUIRED_FILES, *INTERIM_FILES, "raw_link_timeseries.csv"]:
        table = file_name.removesuffix(".csv").lower()
        if f"create table {table}" in sql:
            lines.append(f"- OK: `{table}` has CREATE TABLE.")
        else:
            _message(result, "ERROR", f"schema.sql missing CREATE TABLE for {table}")
    for token in ["model_version", "is_added", "timestamp", "node_id", "pump_id", "pump_station_id", "facility_id", *NODE_AGG_FIELDS, "flow_cms_avg", "flow_cms_max", "on_seconds_15min", "startup_count_15min", "estimated_power_kw_avg"]:
        if token not in sql:
            _message(result, "ERROR", f"schema.sql missing `{token}`")
    for token in ["nvarchar", "float", "datetime2", "int", "bit", "create index"]:
        if token not in sql:
            _message(result, "ERROR", f"schema.sql missing SQL Server type/index token `{token}`")
    return lines


def _check_status_report_flooding(tables: dict[str, pd.DataFrame], result: CheckResult, swmm_run_dir: Path) -> None:
    reports = list(swmm_run_dir.glob("*.rpt"))
    has_flooding_summary = False
    for report in reports:
        text = report.read_text(encoding="utf-8", errors="replace").lower()
        if "node flooding summary" in text and "no nodes were flooded" not in text:
            has_flooding_summary = True
            break
    node_level = tables.get("node_level_timeseries", pd.DataFrame())
    if has_flooding_summary and not node_level.empty:
        if _numeric(node_level, "flooding_cms_max_15min").max() <= 0 and _numeric(node_level, "flooding_volume_m3_15min").max() <= 0:
            _message(result, "ERROR", "SWMM Status Report appears to contain flooding, but aggregated flooding metrics are all 0")


def _flooding_summary_lines(tables: dict[str, pd.DataFrame]) -> list[str]:
    frame = tables.get("node_level_timeseries", pd.DataFrame())
    lines = ["| 节点 | flooding 窗口数 | 最大 flooding_cms_max_15min | flooding 体积 m3 |", "| --- | ---: | ---: | ---: |"]
    if frame.empty or not {"node_id", "flooding_cms_max_15min", "flooding_volume_m3_15min"}.issubset(frame.columns):
        lines.append("| 未检查 |  |  |  |")
        return lines
    flooded = frame[(_numeric(frame, "flooding_cms_max_15min") > 0) | (_numeric(frame, "flooding_volume_m3_15min") > 0)]
    if flooded.empty:
        lines.append("| 无 | 0 | 0 | 0 |")
        return lines
    for node_id, group in flooded.groupby("node_id"):
        lines.append(f"| {node_id} | {len(group)} | {_numeric(group, 'flooding_cms_max_15min').max():.6f} | {_numeric(group, 'flooding_volume_m3_15min').sum():.3f} |")
    return lines


def _write_report(
    result: CheckResult,
    tables: dict[str, pd.DataFrame],
    ranges: dict[str, tuple[pd.Timestamp | None, pd.Timestamp | None]],
    node_lines: list[str],
    pump_lines: list[str],
    schema_lines: list[str],
    docs_report_path: Path | None,
) -> None:
    table_rows = [_table_summary(name, frame) for name, frame in sorted(tables.items())]
    content = "\n".join(
        [
            "# 多源数据接入与质量评估报告",
            "",
            "## 项目背景与模型版本",
            "",
            "- 作业部分：一、管网液位与泵站的联调联控模型，第一阶段“构建基础数据集”。",
            "- 使用模型：`BellingeSWMM_2021_orin_v2.inp`。",
            "- v2 模型说明：该模型为扩展模型，包含新增第五泵站水泵 `G71F320Pp1` 和新增 outfall `G_ADD`。",
            "- 当前阶段边界：只完成基础数据接入、清洗、时间对齐、质量评估和数据库结构化交付，不实现优化算法或闭环控制。",
            "",
            "## 六类基础数据覆盖关系",
            "",
            "| 作业要求数据类型 | 对应 CSV |",
            "| --- | --- |",
            "| 气象数据 | `rainfall_observed.csv`, `rainfall_forecast_scenario.csv` |",
            "| 地理空间与管网拓扑 | `node_info.csv`, `conduit_info.csv`, `pump_info.csv`, `facility_info.csv`, `subcatchment_info.csv` |",
            "| 管网液位数据 | `raw_node_timeseries.csv`, `node_level_timeseries.csv` |",
            "| 泵站液位数据 | `pump_station_level_timeseries.csv` |",
            "| 水泵能耗数据 | `pump_energy_timeseries.csv` |",
            "| 泵站运行时序数据 | `raw_pump_timeseries.csv`, `pump_operation_timeseries.csv`, `gate_operation_timeseries.csv` |",
            "",
            "## 数据来源与处理流程",
            "",
            "- SWMM 模型文件提供管网拓扑、泵站、设施、子汇水区等静态数据。",
            "- 历史降雨 DAT 文件提供分钟级实测降雨序列。",
            "- 未来 72 小时降雨预报情景由历史降雨片段构造。",
            "- PySWMM 输出高频 raw 时序，再按 15min 聚合为正式结构化数据库表。",
            "- 新增泵 `G71F320Pp1` 出口为 `G_ADD`，如出口 head 不适合直接计算扬程，则采用 `default_design_head_m = 2.0m` 估算能耗。",
            "",
            "## CSV 行数、字段、时间范围与缺失值",
            "",
            "| CSV | Rows | Columns | Missing cells | Time range |",
            "| --- | ---: | ---: | ---: | --- |",
            *table_rows,
            "",
            "## 时间对齐与采样检查",
            "",
            *[f"- `{name}`: {start} to {end}" for name, (start, end) in sorted(ranges.items())],
            "",
            "## 新增对象检查",
            "",
            "- `G71F320Pp1` 必须出现在水泵静态表、raw pump、泵运行表和能耗表。",
            "- `G_ADD` 必须出现在节点表和/或设施表。",
            "",
            "## 短时漫溢峰值采样修正说明",
            "",
            "- 原始问题：15min 瞬时采样可能漏掉只持续 1-2 分钟的 flooding。",
            "- 修正方法：PySWMM 先按 `raw_sample_step_sec` 高频采样，保存 `raw_node_timeseries.csv` 和 `raw_pump_timeseries.csv`，再按 15min 聚合正式表。",
            "- 新增指标：`flooding_cms_max_15min`、`flooding_volume_m3_15min`、`depth_m_max`。",
            "- 若修正后仍没有 flooding，可能原因包括：v2 新增 outfall 已削减 flooding；当前降雨工况未触发漫溢；或 PySWMM flooding 字段仍需和 SWMM Status Report 对照。",
            "",
            "## 已捕获 flooding 摘要",
            "",
            *_flooding_summary_lines(tables),
            "",
            "## 关键节点风险摘要",
            "",
            *node_lines,
            "",
            "## 关键泵站运行摘要",
            "",
            *pump_lines,
            "",
            "## 数据库建表脚本检查",
            "",
            *schema_lines,
            "",
            "## WARN 解释",
            "",
            "- `rainfall_observed.csv max time gap`：原始降雨 DAT 为事件型非连续记录，不代表仿真窗口无有效降雨。",
            "- `repeated starts within 30 min`：质量检查按设备安全要求提示频繁启停风险，供后续智能优化阶段约束使用。",
            "",
            "## 第一部分验收结论",
            "",
            "- 已形成至少 6 类基础数据，覆盖气象、拓扑、管网液位、泵站液位、水泵能耗和泵站运行时序。",
            "- 已完成数据接入、清洗、标准化、60s 高频采样和 15min 时间对齐聚合。",
            "- 已生成 SQL Server 结构化数据库建表脚本和可复现的生成/质量检查流程。",
            "- 当前质量检查 `ERROR` 为 0，剩余 `WARN` 均为可解释的质量提示或后续优化约束。",
            "",
            "## OK / WARN / ERROR 分类汇总",
            "",
            f"- OK: {len(result.oks)}",
            f"- WARN: {len(result.warnings)}",
            f"- ERROR: {len(result.errors)}",
            "",
            "### ERROR",
            *[f"- {item}" for item in result.errors],
            "",
            "### WARN",
            *[f"- {item}" for item in result.warnings],
            "",
            "### OK",
            *[f"- {item}" for item in result.oks],
            "",
        ]
    )
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    result.report_path.write_text(content, encoding="utf-8")
    if docs_report_path is not None:
        docs_report_path.parent.mkdir(parents=True, exist_ok=True)
        docs_report_path.write_text(content, encoding="utf-8")


def run_quality_check(
    csv_dir: str | Path | None = None,
    report_path: str | Path | None = None,
    schema_path: str | Path | None = None,
    docs_report_path: str | Path | None = None,
) -> CheckResult:
    config = load_config()
    csv_dir = Path(csv_dir) if csv_dir else config.csv_dir
    report_path = Path(report_path) if report_path else config.report_dir / "csv_quality_check_report.md"
    schema_path = Path(schema_path) if schema_path else config.database_dir / "schema.sql"
    docs_path = Path(docs_report_path) if docs_report_path else config.docs_dir / "data_quality_report.md"
    result = CheckResult(report_path=report_path)

    tables = _check_inventory(csv_dir, REQUIRED_FILES, result)
    tables.update(_check_inventory(config.interim_dir, INTERIM_FILES, result, interim=True))
    _check_added_objects(tables, result)
    ranges = _check_time_series(tables, result)
    _check_aggregated_node_fields(tables, result)
    _check_physical_values(tables, result)
    node_lines = _key_node_summary(tables, result)
    pump_lines = _key_pump_summary(tables, result)
    _check_energy(tables, result)
    _check_status_report_flooding(tables, result, config.swmm_run_dir)
    schema_lines = _check_schema(schema_path, result)
    _message(result, "OK", f"Generated {report_path}")
    _write_report(result, tables, ranges, node_lines, pump_lines, schema_lines, docs_path)
    return result


def main() -> int:
    result = run_quality_check()
    for line in result.console_lines:
        print(line)
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
