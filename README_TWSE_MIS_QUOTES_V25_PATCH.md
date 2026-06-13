# Active ETF TWSE MIS Quotes V25 Patch

你現在的 log 是：

```text
Yahoo chart 429
The job has exceeded the maximum execution time
```

這代表 GitHub Actions 的 IP 已經被 Yahoo 限流。再把 Yahoo 切更小批也沒有意義，因為第一檔就 429。

V25 改成不用 Yahoo，改抓 TWSE MIS 盤中行情：

```text
https://mis.twse.com.tw/stock/api/getStockInfo.jsp
```

它會同時嘗試：

```text
tse_2330.tw
otc_6239.tw
```

所以不需要先知道股票是上市還是上櫃。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_twse_mis_quotes_v25_patch.zip -d .

cd frontend
npm run build
cd ..

git add backend/app/services/twse_mis_quotes.py backend/app/jobs/update_twse_mis_quotes.py .github/workflows/update-twse-mis-quotes.yml .github/workflows/fill-missing-yahoo-chart-quotes.yml .github/workflows/update-yahoo-all-quotes-slow.yml .github/workflows/update-yahoo-all-quotes.yml .github/workflows/update-yahoo-priority-quotes.yml README_TWSE_MIS_QUOTES_V25_PATCH.md
git commit -m "Use TWSE MIS for stock quotes"
git push
```

## 執行

GitHub：

```text
Actions → Update TWSE MIS Quotes → Run workflow
```

## 查結果

```sql
select count(*) as quote_count
from stock_quotes
where price is not null;

select stock_code, stock_name, price, change_pct, volume, amount, market, source, trade_date, updated_at
from stock_quotes
where stock_code in ('1102','1215','1216','1303','1560','2330','3090','6239')
order by stock_code;
```

## 注意

MIS 是盤中行情來源，適合你現在的畫面顯示股價、漲跌幅、成交量與金額。若個股當天完全沒有成交，程式會用昨收當作估值用價格，避免畫面顯示 `-`。
