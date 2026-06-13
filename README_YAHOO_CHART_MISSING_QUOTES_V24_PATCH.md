# Active ETF Yahoo Chart Missing Quotes V24 Patch

你目前 `quote_count = 69`，代表 Supabase 裡真的只有 69 檔有 price。這不是前端排版問題。

V24 不再用 Yahoo quote 批次 endpoint，而是改用 Yahoo chart endpoint 單檔慢慢補：

```text
/v8/finance/chart/2330.TW
/v8/finance/chart/6239.TWO
```

而且它只補目前缺股價的股票。每一 pass 會重新查 Supabase，所以第 1 pass 補完後，第 2 pass 會自動接著補下一批缺的。

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_yahoo_chart_missing_v24_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/yahoo_chart_missing_quotes.py backend/app/jobs/fill_missing_yahoo_chart_quotes.py .github/workflows/fill-missing-yahoo-chart-quotes.yml README_YAHOO_CHART_MISSING_QUOTES_V24_PATCH.md
git commit -m "Fill missing quotes with Yahoo chart"
git push
```

## 跑

GitHub：

```text
Actions → Fill Missing Yahoo Chart Quotes → Run workflow
```

`max_codes` 先用：

```text
50
```

## 查

```sql
select count(*) as holding_stock_count
from (
  select distinct stock_code
  from holdings
  where stock_code ~ '^[0-9]{4}$'
) x;

select count(*) as quote_count
from stock_quotes
where price is not null;

select h.stock_code, max(h.stock_name) as stock_name
from holdings h
left join stock_quotes q
  on q.stock_code = h.stock_code
where h.stock_code ~ '^[0-9]{4}$'
  and q.price is null
group by h.stock_code
order by h.stock_code;
```

如果 quote_count 有增加但還沒滿，就再跑一次同一個 workflow。
