# Active ETF Official Close Quotes V26 Patch

這版不使用 Google Sheets / Apps Script / GOOGLEFINANCE。
也不再用 Yahoo Finance 或 TWSE MIS 即時行情。

改用官方 OpenAPI 做收盤後補齊：

- TWSE：`https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL`
- TPEx：`https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes`

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_official_close_quotes_v26_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/official_close_quotes.py backend/app/jobs/update_official_close_quotes.py .github/workflows/update-official-close-quotes.yml .github/workflows/update-twse-mis-quotes.yml .github/workflows/fill-missing-yahoo-chart-quotes.yml .github/workflows/update-yahoo-all-quotes-slow.yml .github/workflows/update-yahoo-all-quotes.yml .github/workflows/update-yahoo-priority-quotes.yml .github/workflows/update-stock-quotes.yml README_OFFICIAL_CLOSE_QUOTES_V26_PATCH.md
git commit -m "Use official close quote OpenAPI"
git push
```

## 執行

GitHub：

```text
Actions → Update Official Close Quotes → Run workflow
```

## 查結果

```sql
select source, count(*) as cnt
from stock_quotes
group by source
order by cnt desc;

select stock_code, stock_name, price, change, change_pct, volume, amount, market, source, trade_date, updated_at
from stock_quotes
where stock_code in ('1102','1215','1216','1303','1560','2330','3090','6239')
order by stock_code;

select count(*) as quote_count
from stock_quotes
where price is not null;
```

成功後應該會看到 `twse_openapi` 和 `tpex_openapi`。
