# V39 Detail Clean Header + Operation Table Patch

這版修正你剛剛截圖的兩個問題：

1. 點進 ETF 或個股詳情頁時，不再顯示上方「🎯 主動式 ETF / 今日訊號 / 資金持股 / ETF列表」全站導覽列。
   - ETF 詳情頁會更接近你參考圖 2 的乾淨 App 版面。
   - `/etf/xxxx` 與 `/stock/xxxx` 都會套用。
2. 操作日報表格的表頭提高 z-index、加不透明背景與底線，避免「標的 / 狀態 / 持股變動 / 變動幅度 / 目前權重」往下滑時跟股票列視覺重疊。
3. 表格手機版字距再壓縮一點，讓同一頁可以看到更多內容。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_detail_clean_header_v39_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/app/layout.tsx frontend/components/AppShell.tsx frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_CLEAN_HEADER_V39_PATCH.md
git commit -m "Clean detail page header and fix sticky operation table"
git push
```

部署完成後測試：

- `/etf/00994A?tab=operation`
- `/stock/2330`

這兩種詳情頁都不應再出現上方全站導覽列。
