# Active ETF Stock Quotes Fill V17 Patch

這版是修「很多股票沒有股價 / 漲跌幅 / 金額」的資料層問題。

你的前端其實已經會顯示股價，但資料來自 Supabase 的：

```sql
stock_quotes
```

如果某檔股票在 `stock_quotes` 沒有資料，例如 1303、1560，就會顯示：

```text
-
-
金額 -
```

## 這包做什麼

新增一個後端 job：

```text
backend/app/jobs/update_stock_quotes.py
```

它會：

1. 從 holdings 抓出所有 4 碼股票代號
2. 同時查 `.TW` 和 `.TWO`
3. 找到有價格的那筆
4. 寫入 Supabase：
   - stock_quotes
   - stock_price_history

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_stock_quotes_fill_v17_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/stock_quotes_updater.py backend/app/jobs/update_stock_quotes.py .github/workflows/update-stock-quotes.yml README_STOCK_QUOTES_FILL_V17_PATCH.md
git commit -m "Fill missing stock quotes"
git push
```

## 部署後要做

到 GitHub：

```text
Actions → Update Stock Quotes → Run workflow
```

跑完後去 Supabase SQL Editor 查：

```sql
select count(*) as all_quotes
from stock_quotes;

select stock_code, stock_name, price, change_pct, trade_date, source, updated_at
from stock_quotes
where stock_code in ('1303','1560','2059','6239','8021')
order by stock_code;
```

如果有看到 price，重新整理網站後「股價 / 金額」就會出現。

## 為什麼有些股票還是可能沒有

通常原因是：

1. 該股票今天停牌 / 暫停交易
2. Yahoo 沒回資料
3. 股票代號不是一般 4 碼上市櫃股票
4. GitHub Action 還沒跑 `Update Stock Quotes`
5. Supabase RLS 沒開 public select policy

若要確認 RLS：

```sql
alter table stock_quotes enable row level security;

drop policy if exists "Public read stock_quotes" on stock_quotes;

create policy "Public read stock_quotes"
on stock_quotes for select
using (true);
```
