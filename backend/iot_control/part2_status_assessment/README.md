# Part 2 Status Assessment

第二部分“现状评估”模块已实现。模块直接读取第一部分输出的 CSV，不使用 SQL Server，不重新生成第一部分基础数据。

## 模块边界

当前阶段冻结第二部分算法代码、API 和前端结构。后续只建议补充 README、报告截图和文字说明。

## 输入输出

输入目录：

```text
data/processed/part1_csv/
```

输出目录：

```text
data/processed/part2_assessment_csv/
```

主要输出：

- `energy_assessment_timeseries.csv`
- `pump_energy_summary.csv`
- `pump_health_assessment.csv`
- `overflow_risk_assessment.csv`
- `system_status_summary.csv`

## 生成评估 CSV

```powershell
.\.venv\Scripts\python.exe -m backend.iot_control.part2_status_assessment.main --all --config config\part2_status_assessment.yaml
```

## 启动 FastAPI

```powershell
.\.venv\Scripts\uvicorn backend.iot_control.api.main:app --host 127.0.0.1 --port 8010 --reload
```

主要接口：

- `GET /api/part2/summary?range=latest|24h|all`
- `GET /api/part2/energy?range=latest|24h|all`
- `GET /api/part2/pump-health?range=latest|24h|all`
- `GET /api/part2/overflow-risk?range=latest|24h|all`
- `GET /api/part2/energy-summary`

## 启动 Vue3 仪表板

```powershell
cd frontend
npm install
$env:VITE_API_BASE="http://127.0.0.1:8010"
npm run dev -- --host 127.0.0.1 --port 5173
```

浏览器访问：

```text
http://127.0.0.1:5173
```

仪表板包含：

- 系统总览
- 能耗评估
- 设备安全
- 漫溢风险

时间范围支持：

- `最新窗口`：展示当前时间窗口的评估结果。
- `过去24h`：展示过去 24h 内各对象的最不利记录或综合排名。
- `全周期`：展示全周期内各对象的最不利记录或综合排名。

## 字段说明

`pump_health_assessment.csv` 中的 `deduction_detail` 字段保留英文短语，便于后端规则追踪和复现实验结果。Vue3 前端已对常见扣分依据做中文化展示，例如：

- `24h runtime load>1440min`：`24h运行负荷过高`
- `continuous runtime>4215min`：`连续运行时间过长`
- `forebay>80.2%`：`前池液位超过80%`
- `level change rate>0.202m/min`：`液位变化率偏大`
- `24h starts=28`：`24h启停次数偏多`


