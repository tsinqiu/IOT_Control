# Frontend

第二部分现状评估仪表板原型，使用 Vue3 + Vite 实现。

先启动后端 API：

```powershell
.\.venv\Scripts\uvicorn backend.iot_control.api.main:app --reload
```

再启动前端：

```powershell
cd frontend
npm install
npm run dev
```

默认 API 地址为 `http://127.0.0.1:8000`。如需修改：

```powershell
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run dev
```
