# Active ETF UI V5 Patch

這版修正你這次提的 3 點：

1. 有些股票股價沒有出現  
   - 前端會先讀 `stock_quotes`
   - 如果 `stock_quotes` 沒有，會自動從 `stock_price_history` 找最新收盤價當備援
   - 如果兩張表都沒有該股票，才會顯示 `-`

2. 新增 / 刪除 / 加碼 / 減碼改成「可取消選取」篩選  
   - 預設四個都選取
   - 點一下「減碼」會取消減碼，只顯示其他三類
   - 再點一次會加回來

3. 股價 / 漲跌幅排序分開  
   - 表頭變成：
     - 股價 ▲▼
     - 漲跌幅 ▲▼
   - 可以分別排序股價或漲跌幅

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_ui_v5_patch.zip -d .

cat frontend/app/globals.css.addon.v5.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend README_UI_V5_PATCH.md
git commit -m "Improve signal filters and price fallback"
git push
```

Vercel 會自動重新部署。

## 注意

如果套用後仍有股票股價是 `-`，代表那檔股票在：
- `stock_quotes`
- `stock_price_history`

兩張表都沒有資料。這時候要再跑一次 GitHub Actions 更新 market data，或補盤中股價更新 job。
