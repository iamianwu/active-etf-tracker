# Active ETF Yahoo Slow All Quotes V23 Patch

你現在遇到的是：

```text
GitHub Actions 顯示 Success
但畫面上還是很多股票 price 是 -
```

這通常是因為 V22 遇到 Yahoo 限流或某批沒完整回資料，但程式設計成「不讓 workflow 失敗」，所以 GitHub 會顯示 Success。

V23 新增一個更慢、更保守的 workflow：

```text
Update Yahoo All Quotes Slow
```

它會分 7 批依序跑：

```text
offset 0
offset 40
offset 80
offset 120
offset 160
offset 200
offset 240
```

每批只抓 40 檔，每次 Yahoo request 只查 3 檔，而且每次間隔 12 秒。

這樣會比 V22 慢很多，但比較有機會把全部補齊。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_yahoo_slow_all_quotes_v23_patch.zip -d .

cd frontend
npm run build
cd ..

git add .github/workflows/update-yahoo-all-quotes-slow.yml README_YAHOO_SLOW_ALL_QUOTES_V23_PATCH.md
git commit -m "Add slow Yahoo all quotes workflow"
git push
```

## 執行

GitHub：

```text
Actions → Update Yahoo All Quotes Slow → Run workflow
```

`batch_codes` 保持：

```text
40
```

## 查看結果

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

## 重要

跑完一次後，若還缺少幾檔，再跑一次同一個 workflow。因為第一次會建立 `stock_quote_symbols` cache，第二次通常會更容易補到。
