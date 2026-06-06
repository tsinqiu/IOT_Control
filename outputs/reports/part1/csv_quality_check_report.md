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
| conduit_info.csv | 1015 | 16 | 3039 |  |
| facility_info.csv | 33 | 10 | 67 |  |
| gate_operation_timeseries.csv | 11040 | 8 | 0 | 2017-06-29 00:00:00 to 2017-07-03 23:45:00 |
| node_info.csv | 1021 | 14 | 56 |  |
| node_level_timeseries.csv | 10560 | 13 | 0 | 2017-06-29 00:00:00 to 2017-07-03 23:45:00 |
| pump_energy_timeseries.csv | 3360 | 13 | 0 | 2017-06-29 00:00:00 to 2017-07-03 23:45:00 |
| pump_info.csv | 7 | 12 | 0 |  |
| pump_operation_timeseries.csv | 3360 | 13 | 0 | 2017-06-29 00:00:00 to 2017-07-03 23:45:00 |
| pump_station_level_timeseries.csv | 2400 | 7 | 0 | 2017-06-29 00:00:00 to 2017-07-03 23:45:00 |
| rainfall_forecast_scenario.csv | 8640 | 6 | 0 | 2017-06-29 00:00:00 to 2017-07-01 23:59:00 |
| rainfall_observed.csv | 749401 | 5 | 0 | 2009-01-04 14:39:00 to 2021-08-19 00:11:00 |
| raw_node_timeseries.csv | 158378 | 7 | 0 | 2017-06-29 00:01:00 to 2017-07-03 23:59:00 |
| raw_pump_timeseries.csv | 50393 | 8 | 0 | 2017-06-29 00:01:00 to 2017-07-03 23:59:00 |
| subcatchment_info.csv | 713 | 14 | 713 |  |

## 时间对齐与采样检查

- `gate_operation_timeseries`: 2017-06-29 00:00:00 to 2017-07-03 23:45:00
- `node_level_timeseries`: 2017-06-29 00:00:00 to 2017-07-03 23:45:00
- `pump_energy_timeseries`: 2017-06-29 00:00:00 to 2017-07-03 23:45:00
- `pump_operation_timeseries`: 2017-06-29 00:00:00 to 2017-07-03 23:45:00
- `pump_station_level_timeseries`: 2017-06-29 00:00:00 to 2017-07-03 23:45:00
- `rainfall_observed`: 2009-01-04 14:39:00 to 2021-08-19 00:11:00
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
| G70F100 | 17 | 0.061146 | 22.123 |
| G70F11P | 1 | 0.000050 | 0.003 |

## 关键节点风险摘要

| node_id | max depth_m_max | max flooding_cms_max_15min | flooding volume m3 | flooding rows | risk counts |
| --- | ---: | ---: | ---: | ---: | --- |
| G71F320 | 2.8556 | 0.000000 | 0.000 | 0 | {'green': 473, 'yellow': 7} |
| G71F060 | 0.5387 | 0.000000 | 0.000 | 0 | {'green': 480} |
| G71F68Y | 4.4982 | 0.000000 | 0.000 | 0 | {'green': 480} |
| G_ADD | 0.0000 | 0.000000 | 0.000 | 0 | {'green': 480} |

## 关键泵站运行摘要

| pump_id | max flow_cms | avg flow_cms | flow>0 rows | starts | runtime min | cumulative kWh | unit kWh/kt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| G70F11Pp1 | 0.043416 | 0.002549 | 455 | 39 | 6754.0 | 15.3390 | 15.2726 |
| G70F11Pp2 | 0.044447 | 0.000508 | 30 | 36 | 245.0 | 2.6471 | 15.0636 |
| G71F12Pp1 | 0.015000 | 0.000610 | 121 | 200 | 293.0 | 6.1396 | 23.2854 |
| G71F12Pp2 | 0.004000 | 0.000022 | 5 | 2 | 40.0 | 0.2235 | 23.2862 |
| G71F68Yp1 | 0.080000 | 0.004080 | 35 | 21 | 402.0 | 22.3576 | 16.3077 |
| G80F13Pp1 | 0.026000 | 0.004131 | 280 | 375 | 1144.0 | 107.5563 | 60.2963 |
| G71F320Pp1 | 0.080000 | 0.007383 | 76 | 1 | 7199.0 | 24.8309 | 7.7857 |

## 数据库建表脚本检查

- OK: `rainfall_observed` has CREATE TABLE.
- OK: `rainfall_forecast_scenario` has CREATE TABLE.
- OK: `node_info` has CREATE TABLE.
- OK: `conduit_info` has CREATE TABLE.
- OK: `pump_info` has CREATE TABLE.
- OK: `facility_info` has CREATE TABLE.
- OK: `subcatchment_info` has CREATE TABLE.
- OK: `node_level_timeseries` has CREATE TABLE.
- OK: `pump_station_level_timeseries` has CREATE TABLE.
- OK: `pump_operation_timeseries` has CREATE TABLE.
- OK: `pump_energy_timeseries` has CREATE TABLE.
- OK: `gate_operation_timeseries` has CREATE TABLE.
- OK: `raw_node_timeseries` has CREATE TABLE.
- OK: `raw_pump_timeseries` has CREATE TABLE.
- OK: `raw_link_timeseries` has CREATE TABLE.

## WARN 解释

- `rainfall_observed.csv max time gap`：原始降雨 DAT 为事件型非连续记录，不代表仿真窗口无有效降雨。
- `repeated starts within 30 min`：质量检查按设备安全要求提示频繁启停风险，供后续智能优化阶段约束使用。

## 第一部分验收结论

- 已形成至少 6 类基础数据，覆盖气象、拓扑、管网液位、泵站液位、水泵能耗和泵站运行时序。
- 已完成数据接入、清洗、标准化、60s 高频采样和 15min 时间对齐聚合。
- 已生成 SQL Server 结构化数据库建表脚本和可复现的生成/质量检查流程。
- 当前质量检查 `ERROR` 为 0，剩余 `WARN` 均为可解释的质量提示或后续优化约束。

## OK / WARN / ERROR 分类汇总

- OK: 40
- WARN: 6
- ERROR: 0

### ERROR

### WARN
- rainfall_observed.csv max time gap is 50283.0 min
- G70F11Pp1 has repeated starts within 30 min
- G70F11Pp2 has repeated starts within 30 min
- G71F12Pp1 has repeated starts within 30 min
- G71F68Yp1 has repeated starts within 30 min
- G80F13Pp1 has repeated starts within 30 min

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
- raw_node_timeseries.csv timestamp parses as datetime
- raw sample step passed for raw_node_timeseries.csv
- raw_pump_timeseries.csv timestamp parses as datetime
- raw sample step passed for raw_pump_timeseries.csv
- Rainfall total > 0 during simulation window: 63.393 mm
- Aggregated node_level_timeseries.csv with 15min max/sum metrics
- flooding_cms_max_15min field exists
- flooding_volume_m3_15min field exists
- Default design head was used for outfall pump head estimation where needed
- Generated D:\A文件\A学习文件\4.实验报告\物联网控制技术\IOT_Control\outputs\reports\part1\csv_quality_check_report.md
