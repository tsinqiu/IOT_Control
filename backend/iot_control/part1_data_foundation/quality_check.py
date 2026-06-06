from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


TABLE_PURPOSES = {
    "rainfall_observed": "历史实测分钟级降雨序列，用于现状评估和仿真边界条件。",
    "rainfall_forecast_scenario": "基于历史片段构造的未来 72 小时分钟级降雨预报情景。",
    "node_info": "排水管网节点、泵站前池、出水口等地理空间与属性信息。",
    "conduit_info": "管渠拓扑、管径/断面、长度、坡度和糙率等管网结构信息。",
    "pump_info": "水泵静态信息、泵站归属、启停水位和 v2 新增对象标记。",
    "facility_info": "堰、孔口、出水口等控制设施和排放设施信息。",
    "subcatchment_info": "子汇水区面积、不透水率、坡度和出口节点信息。",
    "node_level_timeseries": "15min 对齐后的管网关键节点液位与漫溢风险指标。",
    "pump_station_level_timeseries": "15min 对齐后的泵站前池/集水井液位指标。",
    "pump_energy_timeseries": "15min 对齐后的水泵流量、扬程、功率和累计电耗。",
    "pump_operation_timeseries": "15min 对齐后的水泵启停、运行时长和启动次数。",
    "gate_operation_timeseries": "15min 对齐后的闸门/堰/孔口运行状态和流量。",
    "raw_node_timeseries": "PySWMM 60s 高频节点原始时序，用于捕捉短时 flooding 峰值。",
    "raw_pump_timeseries": "PySWMM 60s 高频水泵原始运行时序。",
    "raw_link_timeseries": "PySWMM 60s 高频设施/连通构筑物原始时序。",
}

KEY_FIELDS = {
    "timestamp": "时间戳，DATETIME2/ISO 时间格式。",
    "forecast_time": "预报发布时间。",
    "target_time": "预报目标时间。",
    "node_id": "节点唯一编号。",
    "pump_id": "水泵唯一编号。",
    "pump_station_id": "泵站编号，由泵名或进水节点归并得到。",
    "facility_id": "设施唯一编号。",
    "gate_id": "闸门、堰或孔口设施编号。",
    "rain_gage_id": "雨量站编号。",
    "depth_m_avg": "15min 窗口内平均水深，单位 m。",
    "depth_m_max": "15min 窗口内最大水深，单位 m。",
    "flooding_cms_max_15min": "15min 窗口内最大 flooding 流量，单位 m3/s。",
    "flooding_volume_m3_15min": "15min 窗口内 flooding 积分体积，单位 m3。",
    "total_inflow_cms_avg": "15min 窗口内平均节点总入流，单位 m3/s。",
    "total_inflow_cms_max": "15min 窗口内最大节点总入流，单位 m3/s。",
    "flow_cms_avg": "15min 平均流量，单位 m3/s。",
    "flow_cms_max": "15min 最大流量，单位 m3/s。",
    "on_seconds_15min": "15min 窗口内水泵处于 ON 状态的秒数。",
    "startup_count_15min": "15min 窗口内水泵启动次数。",
    "estimated_power_kw_avg": "15min 平均估算功率，单位 kW。",
    "energy_kwh_interval": "当前 15min 窗口电耗，单位 kWh。",
    "cumulative_energy_kwh": "累计电耗，单位 kWh。",
    "unit_energy_kwh_per_kt": "单位排水量电耗，单位 kWh/千吨。",
    "model_version": "对象来源模型版本，v2 新增对象标记为 v2，原始对象标记为 original。",
    "is_added": "是否为 v2 手动新增对象，1 表示新增，0 表示原始模型对象。",
}


def dataframe_summary(name: str, frame: pd.DataFrame) -> str:
    missing = int(frame.isna().sum().sum()) if not frame.empty else 0
    return f"| {name} | {len(frame)} | {len(frame.columns)} | {missing} |"


def write_quality_reports(
    csv_tables: dict[str, pd.DataFrame],
    rainfall_stats: dict[str, Any],
    simulation_status: dict[str, Any],
    report_dir: str | Path,
    docs_dir: str | Path,
) -> None:
    report_dir = Path(report_dir)
    docs_dir = Path(docs_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    rows = [dataframe_summary(name, frame) for name, frame in sorted(csv_tables.items())]
    content = "\n".join(
        [
            "# Data Quality Report",
            "",
            "## Rainfall",
            "",
            f"- Source file: {rainfall_stats.get('source_file', '')}",
            f"- Rows parsed: {rainfall_stats.get('rows', 0)}",
            f"- Unparsed rows: {rainfall_stats.get('unparsed_rows', 0)}",
            f"- Time range: {rainfall_stats.get('start_time', '')} to {rainfall_stats.get('end_time', '')}",
            f"- Total rainfall: {rainfall_stats.get('total_rainfall_mm', 0):.3f} mm",
            f"- Max minute rainfall: {rainfall_stats.get('max_minute_rainfall_mm', 0):.3f} mm",
            f"- Missing values: {rainfall_stats.get('missing_values', 0)}",
            "",
            "## SWMM Simulation",
            "",
            f"- Status: {simulation_status.get('swmm_status', '')}",
            f"- Message: {simulation_status.get('message', '')}",
            "",
            "## CSV Completeness",
            "",
            "| CSV | Rows | Columns | Missing cells |",
            "| --- | ---: | ---: | ---: |",
            *rows,
            "",
        ]
    )
    (report_dir / "data_quality_report.md").write_text(content, encoding="utf-8")
    (docs_dir / "data_quality_report.md").write_text(content, encoding="utf-8")


def write_data_dictionary(csv_tables: dict[str, pd.DataFrame], docs_dir: str | Path) -> None:
    docs_dir = Path(docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 基础数据集数据字典",
        "",
        "本数据字典对应第一部分“构建基础数据集”的结构化 CSV 交付物，说明每张表的用途、对象字段、时间字段、单位和关键指标。",
        "",
        "## 六类数据覆盖关系",
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
    ]
    for name, frame in sorted(csv_tables.items()):
        lines.append(f"## {name}.csv")
        lines.append("")
        lines.append(f"- 表用途：{TABLE_PURPOSES.get(name, '结构化基础数据表。')}")
        object_fields = [column for column in frame.columns if column.endswith("_id") or column in {"timestamp", "forecast_time", "target_time"}]
        lines.append(f"- 主键/对象字段：{', '.join(f'`{column}`' for column in object_fields) if object_fields else '无显式对象字段'}")
        time_fields = [column for column in frame.columns if column in {"timestamp", "forecast_time", "target_time"}]
        lines.append(f"- 时间字段：{', '.join(f'`{column}`' for column in time_fields) if time_fields else '静态表，无时间字段'}")
        lines.append("- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。")
        lines.append("")
        lines.append("| 字段 | 说明 |")
        lines.append("| --- | --- |")
        for column in frame.columns:
            lines.append(f"| `{column}` | {KEY_FIELDS.get(column, '原始模型或导出流程中的标准化字段。')} |")
        lines.append("")
    (docs_dir / "data_dictionary.md").write_text("\n".join(lines), encoding="utf-8")
