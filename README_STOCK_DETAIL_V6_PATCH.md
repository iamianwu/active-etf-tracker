# Active ETF Stock Detail V6 Patch

這包是個股詳情頁 V6 修改檔。

## 這版新增

1. 股票頁上方改成：
   - 今日股價
   - 成交量
   - 漲跌額
   - 漲跌幅
   - 量增 / 量減

2. 圖表標題改成：
   - 近三月股價走勢與報酬

3. 圖表下方新增：
   - 近 5 日報酬
   - 近 1 月報酬
   - 近 3 月報酬

4. 顏色邏輯：
   - 上漲 / 收紅：紅色
   - 下跌 / 收綠：綠色
   - 平盤：灰色

5. 圖表顏色也會跟著區間漲跌切換紅 / 綠。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_stock_detail_v6_patch.zip -d .

cat frontend/app/globals.css.addon.stock-v6.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend README_STOCK_DETAIL_V6_PATCH.md
git commit -m "Improve stock detail quote and returns"
git push
```

Vercel 會自動重新部署。

## 注意

成交量與量增/量減主要來自 `stock_price_history.volume`。
如果某檔沒有 volume，畫面會顯示 `-`。
