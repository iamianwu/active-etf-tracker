# Active ETF Holdings UI V8 Patch

這版修改「資金持股」頁。

## 修改內容

1. 表格加入排序 ▲▼  
   - 股票
   - 股價
   - 漲跌幅
   - 持股市值
   - 持股張數
   - 主動式檔數
   - 估個股比重

2. 欄位改成接近你附圖：
   - 股票
   - 股價 / 漲跌幅
   - 持股市值 / 持股張數
   - 主動式檔數 / 估個股比重

3. 原本「今日漲幅」改成：
   - 股價
   - 漲跌幅

4. 漲停 / 跌停亮燈：
   - 漲跌幅 >= 9.5%：股價紅底
   - 漲跌幅 <= -9.5%：股價綠底

5. 股價收紅 / 收綠：
   - 上漲紅色
   - 下跌綠色

6. `frontend/lib/api.ts` 的 `/holdings` 加入股價備援：
   - 先讀 `stock_quotes`
   - 若沒有，會從 `stock_price_history` 找最新收盤價

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_holdings_ui_v8_patch.zip -d .

cat frontend/app/globals.css.addon.holdings-v8.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend README_HOLDINGS_UI_V8_PATCH.md
git commit -m "Improve holdings page sorting and quote display"
git push
```

Vercel 會自動重新部署。
