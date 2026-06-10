# Pocket ETF Fullstack Tracker

這版不是 Streamlit 假 App，而是完整的資料庫前台骨架：

- Backend：FastAPI + SQLite
- Frontend：Next.js / React
- 每個 ETF、股票、訊號都可以點進下一頁
- URL 可分享：`/etf/00403A`、`/stock/2330`、`/signals/increased`

## 1. 啟動 Backend

```bash
cd backend
/usr/local/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API 測試：

```text
http://127.0.0.1:8000
```

## 2. 建立 Demo 資料

開另一個 Terminal：

```bash
curl -X POST http://127.0.0.1:8000/admin/seed-demo
```

或等前端開起來後，到：

```text
http://localhost:3000/admin
```

按「建立 Demo 資料」。

## 3. 啟動 Frontend

```bash
cd frontend
npm install
npm run dev
```

開啟：

```text
http://localhost:3000
```

## 4. 更新真實 Pocket 資料

後端啟動後：

```bash
curl -X POST "http://127.0.0.1:8000/admin/update-all?dt_range=1"
```

回補 90 天：

```bash
curl -X POST "http://127.0.0.1:8000/admin/update-all?dt_range=90"
```

回補 5000 天：

```bash
curl -X POST "http://127.0.0.1:8000/admin/update-all?dt_range=5000"
```

注意：回補很多天會比較久，建議先從 `dt_range=1` 或 `90` 測試。

## 目前已經有的頁面

- `/signals`：今日訊號
- `/signals/added`：新增清單
- `/signals/removed`：刪除清單
- `/signals/increased`：加碼清單
- `/signals/decreased`：減碼清單
- `/holdings`：資金持股 / Constituent Summary
- `/etfs`：ETF 列表
- `/etf/[code]`：ETF 詳情，有總覽、即時、操作日報、成分股、折溢價分頁
- `/stock/[code]`：個股詳情，顯示哪些 ETF 持有、權重、張數、歷史紀錄
- `/admin`：建立 Demo 資料、更新資料

## 下一步可以補強

1. 接 Pocket ETF 日資訊 API，補齊股價、成交量、折溢價、NAV。
2. 接 ETF 基本資料 API，補齊資產規模、內扣費用、成立日期、持股人數。
3. 接 TWSE/TPEx 股價 API，補齊個股股價與漲跌幅。
4. 把 SQLite 改成 Supabase/PostgreSQL，方便部署到雲端。
5. 加入登入密碼，避免公開網址被別人亂更新。
