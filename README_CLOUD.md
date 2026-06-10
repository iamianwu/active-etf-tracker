# Pocket ETF Tracker — Cloud Database Version

這版支援兩種資料庫：

- 本機開發：不設定 `DATABASE_URL`，自動使用 SQLite。
- 雲端部署：設定 `DATABASE_URL`，自動使用 Supabase / Neon PostgreSQL。

## 1. 本機測試

Backend:

```bash
cd backend
/usr/local/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## 2. Supabase / Neon 設定

建立 PostgreSQL project 後，取得 connection string，填到：

```env
DATABASE_URL=postgresql://...
```

Supabase 建議使用 Transaction pooler 或 Session pooler 的 connection string。密碼中如果有特殊字元，請用 URL encoded password。

## 3. GitHub Secrets

到 GitHub repo:

```text
Settings → Secrets and variables → Actions → New repository secret
```

新增：

```text
DATABASE_URL = 你的 Supabase / Neon PostgreSQL connection string
```

之後 GitHub Actions 會每天台灣時間約 18:10 自動更新資料。

手動更新：

```text
Actions → Update ETF Data → Run workflow
```

## 4. Render 後端部署

Render Web Service 設定：

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```env
DATABASE_URL=postgresql://...
ADMIN_PASSWORD=你自己的密碼
CORS_ORIGINS=http://localhost:3000,https://你的前端.vercel.app
```

## 5. Vercel 前端部署

Vercel Project Root Directory 設定：

```text
frontend
```

Environment variables:

```env
NEXT_PUBLIC_API_BASE=https://你的-render-api.onrender.com
NEXT_PUBLIC_ADMIN_PASSWORD=你自己的密碼
```

注意：`NEXT_PUBLIC_ADMIN_PASSWORD` 會出現在前端，不適合正式公開高安全性用途。正式版建議把 `/admin` 做登入或只保留 GitHub Actions 更新，不開放前端 admin。

## 6. 建議正式公開前調整

- 關閉或保護 `/admin`。
- 使用 GitHub Actions 自動更新，不讓一般使用者觸發更新。
- 確認 Pocket / CMoney 資料使用條款。
- 加入錯誤監控與抓取失敗紀錄。
