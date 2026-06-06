# 基础数据集数据字典

本数据字典对应第一部分“构建基础数据集”的结构化 CSV 交付物，说明每张表的用途、对象字段、时间字段、单位和关键指标。

## 六类数据覆盖关系

| 作业要求数据类型 | 对应 CSV |
| --- | --- |
| 气象数据 | `rainfall_observed.csv`, `rainfall_forecast_scenario.csv` |
| 地理空间与管网拓扑 | `node_info.csv`, `conduit_info.csv`, `pump_info.csv`, `facility_info.csv`, `subcatchment_info.csv` |
| 管网液位数据 | `raw_node_timeseries.csv`, `node_level_timeseries.csv` |
| 泵站液位数据 | `pump_station_level_timeseries.csv` |
| 水泵能耗数据 | `pump_energy_timeseries.csv` |
| 泵站运行时序数据 | `raw_pump_timeseries.csv`, `pump_operation_timeseries.csv`, `gate_operation_timeseries.csv` |

## conduit_info.csv

- 表用途：管渠拓扑、管径/断面、长度、坡度和糙率等管网结构信息。
- 主键/对象字段：`link_id`
- 时间字段：静态表，无时间字段
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `link_id` | 原始模型或导出流程中的标准化字段。 |
| `link_type` | 原始模型或导出流程中的标准化字段。 |
| `inlet_node` | 原始模型或导出流程中的标准化字段。 |
| `outlet_node` | 原始模型或导出流程中的标准化字段。 |
| `length` | 原始模型或导出流程中的标准化字段。 |
| `roughness` | 原始模型或导出流程中的标准化字段。 |
| `shape` | 原始模型或导出流程中的标准化字段。 |
| `max_depth_or_diameter` | 原始模型或导出流程中的标准化字段。 |
| `inlet_offset` | 原始模型或导出流程中的标准化字段。 |
| `outlet_offset` | 原始模型或导出流程中的标准化字段。 |
| `slope` | 原始模型或导出流程中的标准化字段。 |
| `minor_loss_inlet` | 原始模型或导出流程中的标准化字段。 |
| `minor_loss_outlet` | 原始模型或导出流程中的标准化字段。 |
| `minor_loss_average` | 原始模型或导出流程中的标准化字段。 |
| `model_version` | 对象来源模型版本，v2 新增对象标记为 v2，原始对象标记为 original。 |
| `is_added` | 是否为 v2 手动新增对象，1 表示新增，0 表示原始模型对象。 |

## facility_info.csv

- 表用途：堰、孔口、出水口等控制设施和排放设施信息。
- 主键/对象字段：`facility_id`
- 时间字段：静态表，无时间字段
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `facility_id` | 设施唯一编号。 |
| `facility_type` | 原始模型或导出流程中的标准化字段。 |
| `inlet_node` | 原始模型或导出流程中的标准化字段。 |
| `outlet_node` | 原始模型或导出流程中的标准化字段。 |
| `crest_height` | 原始模型或导出流程中的标准化字段。 |
| `discharge_coefficient` | 原始模型或导出流程中的标准化字段。 |
| `initial_setting` | 原始模型或导出流程中的标准化字段。 |
| `curve_or_rating` | 原始模型或导出流程中的标准化字段。 |
| `model_version` | 对象来源模型版本，v2 新增对象标记为 v2，原始对象标记为 original。 |
| `is_added` | 是否为 v2 手动新增对象，1 表示新增，0 表示原始模型对象。 |

## gate_operation_timeseries.csv

- 表用途：15min 对齐后的闸门/堰/孔口运行状态和流量。
- 主键/对象字段：`timestamp`, `gate_id`
- 时间字段：`timestamp`
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 时间戳，DATETIME2/ISO 时间格式。 |
| `gate_id` | 闸门、堰或孔口设施编号。 |
| `facility_type` | 原始模型或导出流程中的标准化字段。 |
| `inlet_node` | 原始模型或导出流程中的标准化字段。 |
| `outlet_node` | 原始模型或导出流程中的标准化字段。 |
| `status` | 原始模型或导出流程中的标准化字段。 |
| `setting` | 原始模型或导出流程中的标准化字段。 |
| `flow_cms` | 原始模型或导出流程中的标准化字段。 |

## node_info.csv

- 表用途：排水管网节点、泵站前池、出水口等地理空间与属性信息。
- 主键/对象字段：`node_id`
- 时间字段：静态表，无时间字段
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `node_id` | 节点唯一编号。 |
| `node_type` | 原始模型或导出流程中的标准化字段。 |
| `invert_elevation` | 原始模型或导出流程中的标准化字段。 |
| `max_depth` | 原始模型或导出流程中的标准化字段。 |
| `initial_depth` | 原始模型或导出流程中的标准化字段。 |
| `surcharge_depth` | 原始模型或导出流程中的标准化字段。 |
| `ponded_area` | 原始模型或导出流程中的标准化字段。 |
| `x_coord` | 原始模型或导出流程中的标准化字段。 |
| `y_coord` | 原始模型或导出流程中的标准化字段。 |
| `is_storage` | 原始模型或导出流程中的标准化字段。 |
| `is_outfall` | 原始模型或导出流程中的标准化字段。 |
| `is_pump_station_forebay` | 原始模型或导出流程中的标准化字段。 |
| `model_version` | 对象来源模型版本，v2 新增对象标记为 v2，原始对象标记为 original。 |
| `is_added` | 是否为 v2 手动新增对象，1 表示新增，0 表示原始模型对象。 |

## node_level_timeseries.csv

- 表用途：15min 对齐后的管网关键节点液位与漫溢风险指标。
- 主键/对象字段：`timestamp`, `node_id`
- 时间字段：`timestamp`
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 时间戳，DATETIME2/ISO 时间格式。 |
| `node_id` | 节点唯一编号。 |
| `node_type` | 原始模型或导出流程中的标准化字段。 |
| `depth_m_avg` | 15min 窗口内平均水深，单位 m。 |
| `depth_m_max` | 15min 窗口内最大水深，单位 m。 |
| `head_m_avg` | 原始模型或导出流程中的标准化字段。 |
| `head_m_max` | 原始模型或导出流程中的标准化字段。 |
| `flooding_cms_instant` | 原始模型或导出流程中的标准化字段。 |
| `flooding_cms_max_15min` | 15min 窗口内最大 flooding 流量，单位 m3/s。 |
| `flooding_volume_m3_15min` | 15min 窗口内 flooding 积分体积，单位 m3。 |
| `total_inflow_cms_avg` | 15min 窗口内平均节点总入流，单位 m3/s。 |
| `total_inflow_cms_max` | 15min 窗口内最大节点总入流，单位 m3/s。 |
| `risk_level` | 原始模型或导出流程中的标准化字段。 |

## pump_energy_timeseries.csv

- 表用途：15min 对齐后的水泵流量、扬程、功率和累计电耗。
- 主键/对象字段：`timestamp`, `pump_id`, `pump_station_id`
- 时间字段：`timestamp`
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 时间戳，DATETIME2/ISO 时间格式。 |
| `pump_id` | 水泵唯一编号。 |
| `pump_station_id` | 泵站编号，由泵名或进水节点归并得到。 |
| `flow_cms_avg` | 15min 平均流量，单位 m3/s。 |
| `flow_cms_max` | 15min 最大流量，单位 m3/s。 |
| `inlet_head_m_avg` | 原始模型或导出流程中的标准化字段。 |
| `outlet_head_m_avg` | 原始模型或导出流程中的标准化字段。 |
| `pump_head_m` | 原始模型或导出流程中的标准化字段。 |
| `head_source` | 原始模型或导出流程中的标准化字段。 |
| `estimated_power_kw_avg` | 15min 平均估算功率，单位 kW。 |
| `energy_kwh_interval` | 当前 15min 窗口电耗，单位 kWh。 |
| `cumulative_energy_kwh` | 累计电耗，单位 kWh。 |
| `unit_energy_kwh_per_kt` | 单位排水量电耗，单位 kWh/千吨。 |

## pump_info.csv

- 表用途：水泵静态信息、泵站归属、启停水位和 v2 新增对象标记。
- 主键/对象字段：`pump_id`, `pump_station_id`
- 时间字段：静态表，无时间字段
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `pump_id` | 水泵唯一编号。 |
| `pump_station_id` | 泵站编号，由泵名或进水节点归并得到。 |
| `inlet_node` | 原始模型或导出流程中的标准化字段。 |
| `outlet_node` | 原始模型或导出流程中的标准化字段。 |
| `pump_curve` | 原始模型或导出流程中的标准化字段。 |
| `initial_status` | 原始模型或导出流程中的标准化字段。 |
| `startup_depth` | 原始模型或导出流程中的标准化字段。 |
| `shutoff_depth` | 原始模型或导出流程中的标准化字段。 |
| `is_parallel_pump` | 原始模型或导出流程中的标准化字段。 |
| `curve_points` | 原始模型或导出流程中的标准化字段。 |
| `model_version` | 对象来源模型版本，v2 新增对象标记为 v2，原始对象标记为 original。 |
| `is_added` | 是否为 v2 手动新增对象，1 表示新增，0 表示原始模型对象。 |

## pump_operation_timeseries.csv

- 表用途：15min 对齐后的水泵启停、运行时长和启动次数。
- 主键/对象字段：`timestamp`, `pump_id`, `pump_station_id`
- 时间字段：`timestamp`
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 时间戳，DATETIME2/ISO 时间格式。 |
| `pump_id` | 水泵唯一编号。 |
| `pump_station_id` | 泵站编号，由泵名或进水节点归并得到。 |
| `flow_cms_avg` | 15min 平均流量，单位 m3/s。 |
| `flow_cms_max` | 15min 最大流量，单位 m3/s。 |
| `setting_avg` | 原始模型或导出流程中的标准化字段。 |
| `status` | 原始模型或导出流程中的标准化字段。 |
| `on_seconds_15min` | 15min 窗口内水泵处于 ON 状态的秒数。 |
| `is_startup` | 原始模型或导出流程中的标准化字段。 |
| `is_shutdown` | 原始模型或导出流程中的标准化字段。 |
| `startup_count_15min` | 15min 窗口内水泵启动次数。 |
| `startup_count_cumulative` | 原始模型或导出流程中的标准化字段。 |
| `runtime_min_cumulative` | 原始模型或导出流程中的标准化字段。 |

## pump_station_level_timeseries.csv

- 表用途：15min 对齐后的泵站前池/集水井液位指标。
- 主键/对象字段：`timestamp`, `pump_station_id`
- 时间字段：`timestamp`
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 时间戳，DATETIME2/ISO 时间格式。 |
| `pump_station_id` | 泵站编号，由泵名或进水节点归并得到。 |
| `forebay_node` | 原始模型或导出流程中的标准化字段。 |
| `depth_m` | 原始模型或导出流程中的标准化字段。 |
| `head_m` | 原始模型或导出流程中的标准化字段。 |
| `percent_full` | 原始模型或导出流程中的标准化字段。 |
| `level_change_rate_m_per_min` | 原始模型或导出流程中的标准化字段。 |

## rainfall_forecast_scenario.csv

- 表用途：基于历史片段构造的未来 72 小时分钟级降雨预报情景。
- 主键/对象字段：`forecast_time`, `target_time`, `rain_gage_id`
- 时间字段：`forecast_time`, `target_time`
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `forecast_time` | 预报发布时间。 |
| `target_time` | 预报目标时间。 |
| `rain_gage_id` | 雨量站编号。 |
| `forecast_horizon_min` | 原始模型或导出流程中的标准化字段。 |
| `forecast_rainfall_mm` | 原始模型或导出流程中的标准化字段。 |
| `source` | 原始模型或导出流程中的标准化字段。 |

## rainfall_observed.csv

- 表用途：历史实测分钟级降雨序列，用于现状评估和仿真边界条件。
- 主键/对象字段：`timestamp`, `rain_gage_id`
- 时间字段：`timestamp`
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 时间戳，DATETIME2/ISO 时间格式。 |
| `rain_gage_id` | 雨量站编号。 |
| `rainfall_mm` | 原始模型或导出流程中的标准化字段。 |
| `time_interval_min` | 原始模型或导出流程中的标准化字段。 |
| `source_file` | 原始模型或导出流程中的标准化字段。 |

## subcatchment_info.csv

- 表用途：子汇水区面积、不透水率、坡度和出口节点信息。
- 主键/对象字段：`subcatchment_id`, `rain_gage_id`
- 时间字段：静态表，无时间字段
- 单位说明：水深/扬程为 m，流量为 m3/s，降雨为 mm，功率为 kW，电耗为 kWh，时间步为 60s raw 或 15min 聚合。

| 字段 | 说明 |
| --- | --- |
| `subcatchment_id` | 原始模型或导出流程中的标准化字段。 |
| `rain_gage_id` | 雨量站编号。 |
| `outlet_node` | 原始模型或导出流程中的标准化字段。 |
| `area` | 原始模型或导出流程中的标准化字段。 |
| `impervious_percent` | 原始模型或导出流程中的标准化字段。 |
| `width` | 原始模型或导出流程中的标准化字段。 |
| `slope` | 原始模型或导出流程中的标准化字段。 |
| `curb_length` | 原始模型或导出流程中的标准化字段。 |
| `snow_pack` | 原始模型或导出流程中的标准化字段。 |
| `polygon_points` | 原始模型或导出流程中的标准化字段。 |
| `subarea_params` | 原始模型或导出流程中的标准化字段。 |
| `infiltration_params` | 原始模型或导出流程中的标准化字段。 |
| `model_version` | 对象来源模型版本，v2 新增对象标记为 v2，原始对象标记为 original。 |
| `is_added` | 是否为 v2 手动新增对象，1 表示新增，0 表示原始模型对象。 |
