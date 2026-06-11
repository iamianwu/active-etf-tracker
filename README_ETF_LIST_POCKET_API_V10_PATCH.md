# Active ETF List Pocket API V10 Patch

這版是修正 ETF 列表顯示 0.00 / 0.00% / 0 的問題。

## 為什麼會變成 0？

前一版主要靠 Yahoo Finance 補 ETF 行情，但台灣主動式 ETF 新代號不一定都有穩定回傳，所以 `etf_quotes` 沒有被正確補到。畫面就會看到 0.00、0.00%、0。

你原本 Google Sheets script 裡其實已經有 Pocket API：

- ETF 行情 API：`DtNo=60465380`
- ETF 基本資料 API：`DtNo=59971134`

所以這版改成用 Pocket API 補 ETF 列表資料。

## 這版新增

1. `backend/app/services/pocket_etf_market.py`
   - 抓 Pocket ETF 行情與基本資料
   - 計算股價、漲跌、漲跌幅、成交量、成交金額
   - 計算 1 週報酬、成立以來總報酬
   - 寫入 Supabase `etf_quotes`

2. `backend/app/jobs/update_etf_market.py`
   - 可以單獨更新 ETF market data

3. `.github/workflows/update-etf-market.yml`
   - 可以手動跑
   - 也會在台灣時間 18:20 自動跑

4. `frontend/app/etfs/page.tsx`
   - ETF 列表頁直接讀 Supabase `etf_quotes`
   - 如果 price 是 0，會當成無資料顯示 `-`，不再顯示 0.00

5. `frontend/components/EtfListClient.tsx`
   - 0 價格會顯示 `-`
   - 有資料後才顯示股價、漲跌幅、成交量、成交金額

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_list_pocket_api_v10_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend backend .github README_ETF_LIST_POCKET_API_V10_PATCH.md
git commit -m "Use Pocket API for ETF list market data"
git push
```

## 套用後要手動跑一次

到 GitHub：

```text
Actions → Update Pocket ETF Market Data → Run workflow
```

跑完後到 Supabase 查：

```sql
select etf_code, etf_name, price, change_pct, volume, amount, aum_billion, expense_ratio, region, updated_at
from etf_quotes
order by etf_code;
```

如果看到 price 有值，Vercel 重新整理後 ETF 列表就會正常。
