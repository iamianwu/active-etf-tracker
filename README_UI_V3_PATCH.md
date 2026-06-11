# Active ETF UI V3 Patch

這包是直接覆蓋用的 UI V3 修改檔。

## 這版改了什麼

1. 今日訊號標題加入資料日期  
   例如：`06/11 今日訊號`

2. 標題下方加入抓取進度  
   例如：`已抓取 22 / 22 檔 ETF，資料日期 2026-06-11`

3. 新增 / 刪除 / 加碼 / 減碼按鈕改成類似參考圖的圓角 outline pill

4. 四張焦點卡片改成：
   - 資金流入最多
   - 資金流出最多
   - 最多 ETF 加碼
   - 最多 ETF 減碼

   每張卡片都加入：
   - 資金動向：+17.0 億
   - 多空共識：買賣檔數 5:0

5. 資金交易明細表格加入可點擊排序 ▲ ▼

6. 個股頁的「持股主動式 ETF」表格也加入可點擊排序 ▲ ▼

7. 個股頁法人表格表頭加入 ▲ ▼ 視覺提示

8. 資金交易明細不再顯示「權重變動」，只顯示：
   - 新增
   - 刪除
   - 加碼
   - 減碼

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_ui_v3_patch.zip -d .

cat frontend/app/globals.css.addon.v3.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend backend README_UI_V3_PATCH.md
git commit -m "Improve signal UI and table sorting"
git push
```

Vercel 會自動重新部署。

## 注意

如果「資金動向」還是顯示張數或金額為空，代表 `stock_quotes.price` 還沒有完整更新。
等股價更新 job 補齊 stock_quotes 後，就會顯示估算金額。
