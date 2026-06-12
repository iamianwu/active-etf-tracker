# Active ETF Mobile Fit V14 Patch

這版是針對你最新說的重點：

> 手機版圖 1 / 圖 3 還是欄寬太大，不需要間隔這麼大，希望像圖 2 / 圖 4 一樣，資料可以直接在單一頁面看到。

## 這版修改

1. 資金持股表格
   - 不再使用超大 `min-width`
   - 手機版改成 4 欄直接塞進螢幕：
     - 股票
     - 股價 / 漲跌幅
     - 持股市值 / 持股張數
     - 主動式檔數 / 估個股比重
   - 第一欄保留 sticky，但不再撐出很大的空白

2. ETF 列表
   - 即時 / 報酬 / 基本 與「ETF列表」標題同列
   - 不再讓股票欄佔太大寬度
   - 即時模式 4 欄直接塞進手機：
     - 股票
     - 股價
     - 漲跌幅
     - 今成交量 / 成交金額
   - 報酬、基本模式也同樣壓縮欄寬

3. 字體與列高再次壓縮
   - 比 V13 再小一點
   - 盡量接近 App 一頁看更多資訊的感覺

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_mobile_fit_v14_patch.zip -d .

cat frontend/app/globals.css.addon.mobile-v14.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend/components/EtfListClient.tsx frontend/app/globals.css frontend/app/globals.css.addon.mobile-v14.css README_MOBILE_FIT_V14_PATCH.md
git commit -m "Fit mobile ETF and holdings tables to screen"
git push
```

如果手機 Safari 還是看到舊版，請用無痕或清快取後再看。
