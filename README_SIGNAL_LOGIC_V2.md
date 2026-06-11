# Active ETF Signal Logic V2

這包是直接覆蓋用的修改檔。

## 修正內容

1. 「資金流入最多」和「最多 ETF 加碼」分開：
   - 資金流入最多：以 `變動股數 × 股價 ÷ 1億` 估算金額排序。
   - 最多 ETF 加碼：以同一檔股票被幾檔 ETF 加碼排序。

2. 「資金交易明細」只顯示：
   - 新增
   - 刪除
   - 加碼
   - 減碼

3. 不再把「權重變動」列入資金交易明細。

## 套用方法

在 Terminal 執行：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_signal_logic_v2.zip -d .

cd frontend
npm run build
cd ..

git add frontend backend README_SIGNAL_LOGIC_V2.md
git commit -m "Fix signal logic"
git push
```

Vercel 會自動重新部署。

## 注意

如果「資金流入最多」仍顯示變動張數，而不是估算金額，代表 `stock_quotes.price` 還沒有完整資料。
等盤中股價或 stock price history job 更新後，就會顯示估算金額。
