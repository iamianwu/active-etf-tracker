# Active ETF UI V4 Patch

這包是直接覆蓋用的 UI V4 修改檔。

## 這版修正

1. 資金交易明細不再重複同一檔股票  
   例如國巨被 4 檔 ETF 加碼，會合併成 1 列，ETF檔數顯示 4 檔。

2. 資金交易明細欄位改成：
   - 標的
   - 股價 / 漲跌幅
   - 狀態
   - 金額
   - ETF檔數
   - 變動張數
   - 變動幅度

3. 加碼 / 新增：
   - 金額與變動張數顯示 `+`

4. 減碼 / 刪除：
   - 金額與變動張數顯示 `-`

5. 漲停 / 跌停視覺提示：
   - 漲跌幅 >= 9.5% 時股價亮紅底
   - 漲跌幅 <= -9.5% 時股價亮綠底

6. 多空共識改成同一行：
   - `多空共識：買賣檔數 5:0`

7. 新增 / 刪除 / 加碼 / 減碼改成前端即時篩選，不換頁。

8. 所有表格欄位保留 ▲ ▼ 排序。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_ui_v4_patch.zip -d .

cat frontend/app/globals.css.addon.v4.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend backend README_UI_V4_PATCH.md
git commit -m "Improve signal table aggregation and filters"
git push
```

Vercel 會自動重新部署。
