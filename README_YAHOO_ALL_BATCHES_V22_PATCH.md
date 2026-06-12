# Active ETF Yahoo All Batches V22 Patch

這版解決你的需求：

> 可以一次把全部跑一跑嗎，不然就分批，然後我不用強制優先補股票代號，因為我全都要

## 這版新增兩種跑法

### 1. 日常盤中跑前 120 檔

Workflow：

```text
Update Yahoo Priority Quotes
```

它還是每 15 分鐘跑，但只跑前 120 檔，避免 Yahoo 429。

### 2. 手動一次補全部

新增 Workflow：

```text
Update Yahoo All Quotes
```

它會自動分 3 批依序跑：

```text
batch 1：offset 0，抓第 1～120 檔
batch 2：offset 120，抓第 121～240 檔
batch 3：offset 240，抓第 241 檔以後
```

三批是 sequential，不是同時跑，避免同時打 Yahoo 被擋。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_yahoo_all_batches_v22_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/yahoo_priority_quotes.py backend/app/jobs/update_yahoo_priority_quotes.py .github/workflows/update-yahoo-priority-quotes.yml .github/workflows/update-yahoo-all-quotes.yml README_YAHOO_ALL_BATCHES_V22_PATCH.md
git commit -m "Add Yahoo all quotes batch workflow"
git push
```

## 手動補全部

到 GitHub：

```text
Actions → Update Yahoo All Quotes → Run workflow
```

`batch_codes` 填：

```text
120
```

不用填任何 extra codes。

## 查目前補了幾檔

Supabase SQL：

```sql
select count(*) as quote_count
from stock_quotes
where price is not null;

select count(*) as symbol_cache_count
from stock_quote_symbols;

select stock_code, stock_name, price, change_pct, volume, amount, market, source, updated_at
from stock_quotes
where price is not null
order by updated_at desc
limit 30;
```

## 如果還是有少數沒補到

先查缺哪些：

```sql
select h.stock_code, max(h.stock_name) as stock_name
from holdings h
left join stock_quotes q
  on q.stock_code = h.stock_code
where h.stock_code ~ '^[0-9]{4}$'
  and q.price is null
group by h.stock_code
order by h.stock_code;
```

有些可能是：

```text
停牌
Yahoo 不支援
代號不是一般上市櫃
那一批剛好被 Yahoo 擋
```

再次手動跑 `Update Yahoo All Quotes` 通常會慢慢補齊。
