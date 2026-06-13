# V27 Schema Fix

你的錯誤：

```text
psycopg.errors.UndefinedColumn: column "stock_name" of relation "stock_price_history" does not exist
```

原因：

`stock_price_history` 這張表以前已經建立過，但舊 schema 沒有 `stock_name` 欄位。
PostgreSQL 的 `CREATE TABLE IF NOT EXISTS` 不會幫既有表補欄位，所以要用 `ALTER TABLE ADD COLUMN IF NOT EXISTS`。

V27 修正 `backend/app/services/official_close_quotes.py`，會自動補齊：

```text
stock_name
open
high
low
close
change
change_pct
volume
amount
market
source
updated_at
```

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_official_close_quotes_v27_schema_fix_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/official_close_quotes.py README_OFFICIAL_CLOSE_QUOTES_V27_SCHEMA_FIX.md
git commit -m "Fix stock price history schema migration"
git push
```

然後重新跑：

```text
Actions → Update Official Close Quotes → Run workflow
```

## 也可以先在 Supabase 直接跑 SQL 立即修

```sql
alter table stock_price_history add column if not exists stock_name text;
alter table stock_price_history add column if not exists open double precision;
alter table stock_price_history add column if not exists high double precision;
alter table stock_price_history add column if not exists low double precision;
alter table stock_price_history add column if not exists close double precision;
alter table stock_price_history add column if not exists change double precision;
alter table stock_price_history add column if not exists change_pct double precision;
alter table stock_price_history add column if not exists volume double precision;
alter table stock_price_history add column if not exists amount double precision;
alter table stock_price_history add column if not exists market text;
alter table stock_price_history add column if not exists source text;
alter table stock_price_history add column if not exists updated_at text;
```
