# V42 成分股頁手機排版修正

這版針對 ETF 詳情頁的「成分股」頁面：

1. 上方圓餅圖改成手機版左右並排：左邊圓餅、右邊成分股名稱與權重。
2. 新增「成分股 / 產業分布」膠囊按鈕樣式與更新時間，讓畫面更接近參考 App。
3. 下方成分股明細不再用 table，改成 div grid。
4. 手機固定 4 欄：標的｜持股市值/張數｜權重｜股價/漲跌幅。
5. 欄寬壓縮在單一手機畫面內，避免左右滑與欄位間距過大。
6. 成分股表頭可 sticky，往下滑時仍看得到欄位名稱。

套用方式：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud
unzip -o ~/Downloads/active_etf_holdings_compact_v42_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_HOLDINGS_COMPACT_V42_PATCH.md
git commit -m "Compact ETF holdings mobile layout"
git push
```

測試頁面：

```text
/etf/00994A?tab=holdings
/etf/00403A?tab=holdings
/etf/00981A?tab=holdings
```
