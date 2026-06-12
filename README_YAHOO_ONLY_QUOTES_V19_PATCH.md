# Active ETF Yahoo-only Quotes V19 Patch

這版把股價來源簡化成：

```text
Yahoo Finance only
```

不再抓 TWSE / TPEx 官方資料。

## 為什麼這版比 V17 不容易 429

V17 一次查太多：

```text
266 檔 × .TW/.TWO = 532 symbols
```

所以很容易被 Yahoo 擋成 429。

V19 改成：

1. 第一次只先查 `.TW`
2. `.TW` 查不到的才查 `.TWO`
3. 成功後會建立 `stock_quote_symbols` 快取
4. 下次直接查正確 symbol，例如：
   - `2330.TW`
   - `6239.TWO`
5. 每批只查 15 個 symbols
6. 每批 sleep 3 秒
7. 遇到 429 不讓 GitHub Action 失敗，保留上一筆資料

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_yahoo_only_quotes_v19_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/stock_quotes_updater.py backend/app/jobs/update_stock_quotes.py .github/workflows/update-stock-quotes.yml README_YAHOO_ONLY_QUOTES_V19_PATCH.md
git commit -m "Use Yahoo only for stock quotes"
git push
```

## 跑一次

到 GitHub：

```text
Actions → Update Stock Quotes → Run workflow
```

跑完查 Supabase：

```sql
select count(*) as quote_count
from stock_quotes;

select stock_code, stock_name, price, change_pct, volume, amount, market, source, trade_date, updated_at
from stock_quotes
where stock_code in ('1303','1560','2059','2303','6239','8021')
order by stock_code;

select count(*) as symbol_cache_count
from stock_quote_symbols;
```

## 注意

這是 Yahoo-only，所以簡單很多，但還是有一個現實限制：

```text
Yahoo 有機會 429。
```

這版遇到 429 會停止本輪更新但不報錯，網站會保留上一筆股價。
