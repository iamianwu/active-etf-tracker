# V28 Fast Save Patch

這次 log 顯示官方 OpenAPI 抓取成功，但在寫入 Supabase 時被取消：

```text
TWSE parsed=1177
TPEX parsed=887
Error: The operation was canceled.
```

原因是前一版把全部上市櫃 2000 多檔都寫進 Supabase，但網站只需要 active ETF 持股中出現的股票，大約 266 檔。

V28 改成：

```text
1. 先從 holdings 找目前所有 4 碼股票
2. 官方 OpenAPI 照常抓全部上市櫃
3. 只保留 holdings 內出現的股票
4. 只寫入約 266 檔
5. workflow timeout 從 10 分鐘提高到 20 分鐘
```

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_official_close_quotes_v28_fast_save_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/official_close_quotes.py .github/workflows/update-official-close-quotes.yml README_OFFICIAL_CLOSE_QUOTES_V28_FAST_SAVE.md
git commit -m "Speed up official close quote updater"
git push
```

## 執行

```text
Actions → Update Official Close Quotes → Run workflow
```

## 成功時 log 應該類似

```text
Holding stock codes=266
TWSE parsed=1177, kept_for_holdings=xxx
TPEX parsed=887, kept_for_holdings=xxx
Official quotes kept for holdings=xxx
Saved quotes: 50/xxx
Official close quotes saved=xxx, missing_holdings=xx
```

## 查結果

```sql
select source, count(*) as cnt
from stock_quotes
group by source
order by cnt desc;

select count(*) as quote_count
from stock_quotes
where price is not null;
```
