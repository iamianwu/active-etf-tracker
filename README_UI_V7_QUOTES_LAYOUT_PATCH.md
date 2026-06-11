# Active ETF UI V7 Quotes + Compact Layout Patch

這版修正：

1. 很多股票沒有股價 / 漲跌幅 / 金額  
   - 新增 `backend/app/services/realtime_quotes.py`
   - 新增 `backend/app/jobs/update_quotes.py`
   - 新增 `.github/workflows/update-live-quotes.yml`
   - 跑 GitHub Actions 後會補 `stock_quotes`，前端就會有股價、漲跌幅、金額。

2. 資金交易明細表格太寬，需要左滑  
   - 改成 compact table
   - 標的欄寬縮小
   - 欄位名稱縮短：ETF、張數、幅度
   - 桌機寬度下盡量不需左滑

3. 表頭要釘選  
   - 資金交易明細表頭 sticky
   - 往下滑時會固定在上方

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_ui_v7_quotes_layout_patch.zip -d .

cat frontend/app/globals.css.addon.v7.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend backend .github README_UI_V7_QUOTES_LAYOUT_PATCH.md
git commit -m "Add live quotes and compact sticky signal table"
git push
```

## 補股價資料

部署後到 GitHub：

```text
Actions → Update Live Quotes → Run workflow
```

第一次手動跑完後，回到 Supabase 可以查：

```sql
select count(*) from stock_quotes where price is not null;
```

之後盤中會自動每 5 分鐘跑一次。

## 注意

若某檔股票在 Yahoo `.TW` / `.TWO` 都抓不到，仍可能顯示 `-`。
但大部分上市櫃四碼股票會被補進 `stock_quotes`。
