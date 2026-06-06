# SQL Server 数据库交付说明

`schema.sql` 包含第一部分基础数据集所有 CSV 的 SQL Server 建表语句与关键索引。

该版本已针对 SSMS 导入向导做兼容处理：CSV 中可能为空的可选数值字段，以及 `True/False` 布尔显示字段，使用 `NVARCHAR` 作为接入层类型，因此可直接导入，避免空字符串转换 `FLOAT` 或 `BIT` 失败。

如果已经用旧版 `schema.sql` 建过表，可以先在 `IOT_Control` 数据库中执行 `ssms_import_compat_patch.sql`，只修改相关列类型；如果库里还没有有效数据，也可以直接重新执行新版 `schema.sql` 重建表。

v2 扩展模型字段 `model_version` 和 `is_added` 用于标记新增对象，包括新增第五泵站水泵 `G71F320Pp1` 和新增 outfall `G_ADD`。

## 导入顺序

建议先导入静态基础表，再导入气象表，最后导入动态时序表：

1. `node_info.csv`
2. `conduit_info.csv`
3. `pump_info.csv`
4. `facility_info.csv`
5. `subcatchment_info.csv`
6. `rainfall_observed.csv`
7. `rainfall_forecast_scenario.csv`
8. `raw_node_timeseries.csv`, `raw_pump_timeseries.csv`, `raw_link_timeseries.csv`
9. `node_level_timeseries.csv`
10. `pump_station_level_timeseries.csv`
11. `pump_operation_timeseries.csv`
12. `pump_energy_timeseries.csv`
13. `gate_operation_timeseries.csv`

## 表说明

- 静态表用于描述管网拓扑、泵站和设施对象。
- raw 时序表保留 PySWMM 60s 高频采样数据。
- 正式时序表为 15min 对齐聚合结果，满足课程采集频率要求。
- 所有时序表均保留 `timestamp`，并对关键字段建立索引。

## 数值查询建议

对于使用 `NVARCHAR` 保存的可选数值字段，查询或分析时可使用 `TRY_CONVERT` 转为数值，例如：

```sql
SELECT
    link_id,
    TRY_CONVERT(FLOAT, NULLIF(minor_loss_inlet, '')) AS minor_loss_inlet_value
FROM dbo.conduit_info;
```
