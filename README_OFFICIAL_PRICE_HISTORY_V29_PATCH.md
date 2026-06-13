# V29 Official Price History Backfill

現在股價已經補齊，但個股頁仍顯示：

```text
尚無股價歷史資料，請先跑 GitHub Actions 更新 market data。
```

原因是 V28 只補今天收盤股價，`stock_price_history` 裡每檔最多只有 1 天資料，不足以畫近三月走勢。

V29 新增：

```text
Backfill Official Price History
```

它會從官方資料補 `stock_price_history`：

- TWSE 上市個股歷史月資料
- TPEx 上櫃個股歷史月資料
- 預設補最近 4 個月，足夠畫近三月圖
- 分成 4 個 matrix job 跑，避免 timeout

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_official_price_history_v29_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/official_price_history.py backend/app/jobs/backfill_official_price_history.py .github/workflows/backfill-official-price-history.yml README_OFFICIAL_PRICE_HISTORY_V29_PATCH.md
git commit -m "Backfill official stock price history"
git push
```

## 執行

到 GitHub：

```text
Actions → Backfill Official Price History → Run workflow
```

`months` 先填：

```text
4
```

## 查結果

```sql
select stock_code, count(*) as days, min(trade_date), max(trade_date)
from stock_price_history
where stock_code in ('1560','2330','3090','6239')
group by stock_code
order by stock_code;

select count(*) as history_rows
from stock_price_history;
```

## 成功後

個股頁的「近三月股價走勢與報酬」就會有圖。

如果前端有快取，請等 Vercel 重新部署後，或用瀏覽器強制重新整理。
