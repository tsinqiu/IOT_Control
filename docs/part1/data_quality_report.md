# 多源数据接入与质量评估报告

## 项目背景与模型版本

- 作业部分：一、管网液位与泵站的联调联控模型，第一阶段“构建基础数据集”。
- 使用模型：`BellingeSWMM_2021_orin_v2.inp`。
- v2 模型说明：该模型为扩展模型，包含新增第五泵站水泵 `G71F320Pp1` 和新增 outfall `G_ADD`。
- 当前阶段边界：只完成基础数据接入、清洗、时间对齐、质量评估和数据库结构化交付，不实现优化算法或闭环控制。

## 六类基础数据覆盖关系

| 作业要求数据类型 | 对应 CSV |
| --- | --- |
| 气象数据 | `rainfall_observed.csv`, `rainfall_forecast_scenario.csv` |
| 地理空间与管网拓扑 | `node_info.csv`, `conduit_info.csv`, `pump_info.csv`, `facility_info.csv`, `subcatchment_info.csv` |
| 管网液位数据 | `raw_node_timeseries.csv`, `node_level_timeseries.csv` |
| 泵站液位数据 | `pump_station_level_timeseries.csv` |
| 水泵能耗数据 | `pump_energy_timeseries.csv` |
| 泵站运行时序数据 | `raw_pump_timeseries.csv`, `pump_operation_timeseries.csv`, `gate_operation_timeseries.csv` |

## 数据来源与处理流程

- SWMM 模型文件提供管网拓扑、泵站、设施、子汇水区等静态数据。
- 历史降雨 DAT 文件提供分钟级实测降雨序列。
- 未来 72 小时降雨预报情景由历史降雨片段构造。
- PySWMM 输出高频 raw 时序，再按 15min 聚合为正式结构化数据库表。
- 新增泵 `G71F320Pp1` 出口为 `G_ADD`，如出口 head 不适合直接计算扬程，则采用 `default_design_head_m = 2.0m` 估算能耗。

## CSV 行数、字段、时间范围与缺失值

| CSV | Rows | Columns | Missing cells | Time range |
| --- | ---: | ---: | ---: | --- |
| conduit_info.csv | 1 | 1 | 0 |  |
| facility_info.csv | 1 | 4 | 0 |  |
| gate_operation_timeseries.csv | 1 | 3 | 0 | 2012-06-29 00:01:00 to 2012-06-29 00:01:00 |
| node_info.csv | 2 | 5 | 1 |  |
| node_level_timeseries.csv | 1 | 5 | 0 | 2012-06-29 00:01:00 to 2012-06-29 00:01:00 |
| pump_energy_timeseries.csv | 1 | 9 | 0 | 2012-06-29 00:01:00 to 2012-06-29 00:01:00 |
| pump_info.csv | 1 | 4 | 0 |  |
| pump_operation_timeseries.csv | 1 | 6 | 0 | 2012-06-29 00:01:00 to 2012-06-29 00:01:00 |
| pump_station_level_timeseries.csv | 1 | 4 | 0 | 2012-06-29 00:01:00 to 2012-06-29 00:01:00 |
| rainfall_forecast_scenario.csv | 1 | 6 | 0 | 2012-06-29 00:01:00 to 2012-06-29 00:01:00 |
| rainfall_observed.csv | 1 | 5 | 0 | 2012-06-29 00:01:00 to 2012-06-29 00:01:00 |
| raw_node_timeseries.csv | 158378 | 7 | 0 | 2017-06-29 00:01:00 to 2017-07-03 23:59:00 |
| raw_pump_timeseries.csv | 50393 | 8 | 0 | 2017-06-29 00:01:00 to 2017-07-03 23:59:00 |
| subcatchment_info.csv | 1 | 1 | 0 |  |

## 时间对齐与采样检查

- `gate_operation_timeseries`: 2012-06-29 00:01:00 to 2012-06-29 00:01:00
- `node_level_timeseries`: 2012-06-29 00:01:00 to 2012-06-29 00:01:00
- `pump_energy_timeseries`: 2012-06-29 00:01:00 to 2012-06-29 00:01:00
- `pump_operation_timeseries`: 2012-06-29 00:01:00 to 2012-06-29 00:01:00
- `pump_station_level_timeseries`: 2012-06-29 00:01:00 to 2012-06-29 00:01:00
- `rainfall_observed`: 2012-06-29 00:01:00 to 2012-06-29 00:01:00
- `raw_node_timeseries`: 2017-06-29 00:01:00 to 2017-07-03 23:59:00
- `raw_pump_timeseries`: 2017-06-29 00:01:00 to 2017-07-03 23:59:00

## 新增对象检查

- `G71F320Pp1` 必须出现在水泵静态表、raw pump、泵运行表和能耗表。
- `G_ADD` 必须出现在节点表和/或设施表。

## 短时漫溢峰值采样修正说明

- 原始问题：15min 瞬时采样可能漏掉只持续 1-2 分钟的 flooding。
- 修正方法：PySWMM 先按 `raw_sample_step_sec` 高频采样，保存 `raw_node_timeseries.csv` 和 `raw_pump_timeseries.csv`，再按 15min 聚合正式表。
- 新增指标：`flooding_cms_max_15min`、`flooding_volume_m3_15min`、`depth_m_max`。
- 若修正后仍没有 flooding，可能原因包括：v2 新增 outfall 已削减 flooding；当前降雨工况未触发漫溢；或 PySWMM flooding 字段仍需和 SWMM Status Report 对照。

## 已捕获 flooding 摘要

| 节点 | flooding 窗口数 | 最大 flooding_cms_max_15min | flooding 体积 m3 |
| --- | ---: | ---: | ---: |
| 未检查 |  |  |  |

## 关键节点风险摘要

| node_id | max depth_m_max | max flooding_cms_max_15min | flooding volume m3 | flooding rows | risk counts |
| --- | ---: | ---: | ---: | ---: | --- |
| G71F320 | nan | nan | 0.000 | 0 | {'green': 1} |
| G71F060 | missing | missing | missing | missing | missing |
| G71F68Y | missing | missing | missing | missing | missing |
| G_ADD | missing | missing | missing | missing | missing |

## 关键泵站运行摘要

| pump_id | max flow_cms | avg flow_cms | flow>0 rows | starts | runtime min | cumulative kWh | unit kWh/kt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| G70F11Pp1 | missing | missing | missing | missing | missing | missing | missing |
| G70F11Pp2 | missing | missing | missing | missing | missing | missing | missing |
| G71F12Pp1 | missing | missing | missing | missing | missing | missing | missing |
| G71F12Pp2 | missing | missing | missing | missing | missing | missing | missing |
| G71F68Yp1 | missing | missing | missing | missing | missing | missing | missing |
| G80F13Pp1 | missing | missing | missing | missing | missing | missing | missing |
| G71F320Pp1 | nan | nan | 0 | 0 | 0.0 | 0.0000 | 0.0000 |

## 数据库建表脚本检查

- OK: `pump_info` has CREATE TABLE.

## WARN 解释

- `rainfall_observed.csv max time gap`：原始降雨 DAT 为事件型非连续记录，不代表仿真窗口无有效降雨。
- `repeated starts within 30 min`：质量检查按设备安全要求提示频繁启停风险，供后续智能优化阶段约束使用。

## 第一部分验收结论

- 已形成至少 6 类基础数据，覆盖气象、拓扑、管网液位、泵站液位、水泵能耗和泵站运行时序。
- 已完成数据接入、清洗、标准化、60s 高频采样和 15min 时间对齐聚合。
- 已生成 SQL Server 结构化数据库建表脚本和可复现的生成/质量检查流程。
- 当前质量检查 `ERROR` 为 0，剩余 `WARN` 均为可解释的质量提示或后续优化约束。

## OK / WARN / ERROR 分类汇总

- OK: 37
- WARN: 0
- ERROR: 33

### ERROR
- node_level_timeseries.csv missing aggregated fields: depth_m_avg, depth_m_max, flooding_cms_max_15min, flooding_volume_m3_15min, total_inflow_cms_avg, total_inflow_cms_max
- schema.sql missing CREATE TABLE for rainfall_observed
- schema.sql missing CREATE TABLE for rainfall_forecast_scenario
- schema.sql missing CREATE TABLE for node_info
- schema.sql missing CREATE TABLE for conduit_info
- schema.sql missing CREATE TABLE for facility_info
- schema.sql missing CREATE TABLE for subcatchment_info
- schema.sql missing CREATE TABLE for node_level_timeseries
- schema.sql missing CREATE TABLE for pump_station_level_timeseries
- schema.sql missing CREATE TABLE for pump_operation_timeseries
- schema.sql missing CREATE TABLE for pump_energy_timeseries
- schema.sql missing CREATE TABLE for gate_operation_timeseries
- schema.sql missing CREATE TABLE for raw_node_timeseries
- schema.sql missing CREATE TABLE for raw_pump_timeseries
- schema.sql missing CREATE TABLE for raw_link_timeseries
- schema.sql missing `timestamp`
- schema.sql missing `node_id`
- schema.sql missing `pump_station_id`
- schema.sql missing `facility_id`
- schema.sql missing `depth_m_avg`
- schema.sql missing `depth_m_max`
- schema.sql missing `flooding_cms_max_15min`
- schema.sql missing `flooding_volume_m3_15min`
- schema.sql missing `total_inflow_cms_avg`
- schema.sql missing `total_inflow_cms_max`
- schema.sql missing `flow_cms_avg`
- schema.sql missing `flow_cms_max`
- schema.sql missing `on_seconds_15min`
- schema.sql missing `startup_count_15min`
- schema.sql missing `estimated_power_kw_avg`
- schema.sql missing SQL Server type/index token `float`
- schema.sql missing SQL Server type/index token `datetime2`
- schema.sql missing SQL Server type/index token `int`

### WARN

### OK
- Found rainfall_observed.csv
- Found rainfall_forecast_scenario.csv
- Found node_info.csv
- Found conduit_info.csv
- Found pump_info.csv
- Found facility_info.csv
- Found subcatchment_info.csv
- Found node_level_timeseries.csv
- Found pump_station_level_timeseries.csv
- Found pump_operation_timeseries.csv
- Found pump_energy_timeseries.csv
- Found gate_operation_timeseries.csv
- Exported raw_node_timeseries.csv
- Exported raw_pump_timeseries.csv
- G71F320Pp1 found in pump_info.csv
- G_ADD found in node_info/facility_info
- G71F320Pp1 found in pump_operation_timeseries.csv
- G71F320Pp1 found in raw and aggregated pump operation data
- G71F320Pp1 found in pump_energy_timeseries.csv
- node_level_timeseries.csv timestamp parses as datetime
- Time step check passed for node_level_timeseries.csv
- pump_station_level_timeseries.csv timestamp parses as datetime
- Time step check passed for pump_station_level_timeseries.csv
- pump_operation_timeseries.csv timestamp parses as datetime
- Time step check passed for pump_operation_timeseries.csv
- pump_energy_timeseries.csv timestamp parses as datetime
- Time step check passed for pump_energy_timeseries.csv
- gate_operation_timeseries.csv timestamp parses as datetime
- Time step check passed for gate_operation_timeseries.csv
- rainfall_observed.csv timestamp parses as datetime
- Time step check passed for rainfall_observed.csv
- raw_node_timeseries.csv timestamp parses as datetime
- raw sample step passed for raw_node_timeseries.csv
- raw_pump_timeseries.csv timestamp parses as datetime
- raw sample step passed for raw_pump_timeseries.csv
- Rainfall total > 0 during simulation window: 1.000 mm
- Generated D:\A文件\A学习文件\4.实验报告\物联网控制技术\IOT_Control\tests\_tmp_quality\reports\csv_quality_check_report.md
