# Active ETF Yahoo Priority Quotes V21 Patch

這版是你說「好」後，我幫你做的 Yahoo 優先補股價版本。

它不是一次打全部 266 檔，而是：

```text
1. 先抓今日訊號有異動的股票
2. 再抓資金持股頁權重較高的股票
3. 最後才補其他股票
```

這樣比 V19 更不容易被 Yahoo 擋，而且畫面上最重要的股價會先補。

---

## 這包新增

```text
backend/app/services/yahoo_priority_quotes.py
backend/app/jobs/update_yahoo_priority_quotes.py
.github/workflows/update-yahoo-priority-quotes.yml
```

另外會把舊的：

```text
.github/workflows/update-stock-quotes.yml
```

改成 disabled，避免舊 workflow 又一直跑 Yahoo 全部股票造成 429。

---

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_yahoo_priority_quotes_v21_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/yahoo_priority_quotes.py backend/app/jobs/update_yahoo_priority_quotes.py .github/workflows/update-yahoo-priority-quotes.yml .github/workflows/update-stock-quotes.yml README_YAHOO_PRIORITY_QUOTES_V21_PATCH.md
git commit -m "Add Yahoo priority quote updater"
git push
```

---

## 第一次手動跑

到 GitHub：

```text
Actions → Update Yahoo Priority Quotes → Run workflow
```

輸入：

```text
max_codes = 80
extra_codes = 3090,3211,1560,1303,2059,6239,8021
```

先用 80 就好，確認不會 429。

如果成功，下次可試：

```text
max_codes = 120
```

---

## 查 Supabase

```sql
select stock_code, stock_name, price, change_pct, volume, amount, market, source, trade_date, updated_at
from stock_quotes
where stock_code in ('1303','1560','2059','3090','3211','6239','8021')
order by stock_code;

select count(*) as quote_count
from stock_quotes;

select count(*) as symbol_cache_count
from stock_quote_symbols;
```

---

## 重要說明

這版仍然是 Yahoo，所以：

```text
Yahoo 仍有機會 429。
```

但這版遇到 429 不會讓 workflow 失敗，會停止當輪更新並保留上一筆資料。

如果你想補某幾檔，可以用 Run workflow 的 `extra_codes` 強制優先補。
